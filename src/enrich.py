"""
enrich.py
Post-insert enrichment: computes novelty_score, market_impact_flag
for articles inserted in the last 2 hours that haven't been enriched yet.
"""

import json
from pathlib import Path
from database import get_connection, get_event_count_today

_WATCHLIST_PATH = Path(__file__).parent.parent / 'config' / 'watchlist.json'


def _load_watchlist():
    with open(_WATCHLIST_PATH, encoding='utf-8') as f:
        wl = json.load(f)
    tickers = wl.get('tickers', [])
    full_names = wl.get('full_names', [])
    topics = wl.get('fixed_topics', {})
    all_keywords = list(set(
        tickers + full_names +
        [kw for group in topics.values() for kw in group]
    ))
    return tickers, all_keywords


def run_enrichment():
    """
    Fetch articles inserted in last 2 hours with NULL novelty_score.
    Compute and UPDATE: novelty_score, market_impact_flag.
    (relevance_score, entity_count, event_type are already set by filter_articles.py)
    """
    TICKERS, ALL_KEYWORDS = _load_watchlist()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, content_snippet, tier, urgency_flag, event_type,
               relevance_score, entity_count
        FROM news_articles
        WHERE novelty_score IS NULL
        AND fetched_at > NOW() - INTERVAL '2 hours'
    """)
    rows = cur.fetchall()

    if not rows:
        print(f"    [enrich] No new articles to enrich.")
        cur.close()
        conn.close()
        return

    updated = 0
    for row in rows:
        id_, title, snippet, tier, urgency, event_type, relevance, entity_count = row
        text = (title or '') + ' ' + (snippet or '')

        # novelty_score: 1 / count of same event_type articles today
        day_count = get_event_count_today(event_type or 'General')
        novelty = round(min(1 / max(day_count, 1), 1.0), 4)

        # market_impact_flag: tier 1 sources OR Immediate urgency
        market_impact = bool((tier == 1) or (urgency == 'Immediate'))

        # If relevance_score somehow wasn't set by filter (shouldn't happen, safety net)
        if relevance is None:
            kw_hits = sum(1 for k in ALL_KEYWORDS if k.lower() in text.lower())
            tick_hits = sum(1 for t in TICKERS if t.lower() in text.lower())
            relevance = min(round((kw_hits / 10) + (tick_hits * 0.2), 3), 1.0)

        if entity_count is None:
            entity_count = len(set(k for k in ALL_KEYWORDS if k.lower() in text.lower()))

        cur.execute("""
            UPDATE news_articles
            SET novelty_score      = %s,
                market_impact_flag = %s,
                relevance_score    = COALESCE(relevance_score, %s),
                entity_count       = COALESCE(entity_count, %s)
            WHERE id = %s
        """, (novelty, market_impact, relevance, entity_count, id_))
        updated += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"    [enrich] Updated {updated} articles with novelty + market_impact scores")
