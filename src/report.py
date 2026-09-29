"""
report.py
Generates news_enriched_{timestamp}_{run}.csv and
news-briefing_{timestamp}_{run}.html from DB data.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from database import get_connection

OUTPUT_DIR = Path(__file__).parent.parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

TEMPLATE_PART1 = Path(__file__).parent / 'briefing_template_part1.html'
TEMPLATE_PART2 = Path(__file__).parent / 'briefing_template_part2.html'


def generate_briefing():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, url, source, tier, published_at,
               keywords_matched, content_snippet, event_type,
               is_flagged, relevance_score, novelty_score,
               entity_count, market_impact_flag, urgency_flag
        FROM news_articles
        WHERE published_at > NOW() - INTERVAL '24 hours'
        AND relevance_score IS NOT NULL
        ORDER BY tier ASC, relevance_score DESC
    """)
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    cur.close()
    conn.close()

    articles = [dict(zip(columns, row)) for row in rows]
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')
    hour = datetime.now(timezone.utc).hour
    if hour < 10:
        run_label = 'morning'
    elif hour < 15:
        run_label = 'midday'
    else:
        run_label = 'evening'

    # ── CSV ──────────────────────────────────────────────────────────────────
    csv_path = OUTPUT_DIR / f'news_enriched_{timestamp}_{run_label}.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for a in articles:
            writer.writerow({k: str(v) if v is not None else '' for k, v in a.items()})

    # ── Stats for HTML ────────────────────────────────────────────────────────
    stats = {
        "total": len(articles),
        "market_impact": sum(1 for a in articles if a.get('market_impact_flag')),
        "sources": {},
        "event_types": {},
        "urgency": {"Immediate": 0, "Developing": 0, "Background": 0},
    }
    top_per_event = {}
    for a in articles:
        s = a.get('source', 'Unknown')
        stats["sources"][s] = stats["sources"].get(s, 0) + 1
        et = a.get('event_type', 'General')
        stats["event_types"][et] = stats["event_types"].get(et, 0) + 1
        u = a.get('urgency_flag', 'Background')
        if u in stats["urgency"]:
            stats["urgency"][u] += 1
        if et not in top_per_event:
            top_per_event[et] = []
        if len(top_per_event[et]) < 5:
            top_per_event[et].append(a)

    # ── Build HTML by injecting data into template ────────────────────────────
    data_js = f"""
const STATS = {json.dumps(stats, default=str)};
const TOP_PER_EVENT = {json.dumps(top_per_event, default=str)};
const FEED = {json.dumps(articles, default=str)};
const RUN_LABEL = "{run_label}";
const RUN_TIME = "{timestamp}";
"""
    part1 = TEMPLATE_PART1.read_text(encoding='utf-8')
    part2 = TEMPLATE_PART2.read_text(encoding='utf-8')
    html_content = part1 + "\n" + data_js + "\n" + part2

    html_path = OUTPUT_DIR / f'news-briefing_{timestamp}_{run_label}.html'
    html_path.write_text(html_content, encoding='utf-8')

    print(f"    [report] Saved: {csv_path.name}")
    print(f"    [report] Saved: {html_path.name}")
