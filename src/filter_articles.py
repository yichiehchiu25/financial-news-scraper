"""
filter_articles.py
Runs all 7 filter layers on raw article dicts from scraper.py.
"""

import json
import difflib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import database

# ── Load watchlist ────────────────────────────────────────────────────────────
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

TICKERS, ALL_KEYWORDS = _load_watchlist()

# ── Signal type map (12 types) ────────────────────────────────────────────────
SIGNAL_MAP = {
    "Earnings Catalyst":       ["beat","miss","EPS","revenue","guidance","earnings","quarterly","profit"],
    "Policy / Macro Shock":    ["Fed","rate hike","rate cut","CPI","tariff","inflation","FOMC","monetary policy"],
    "Institutional Flow":      ["dark pool","block trade","13F","stake raised","institutional buying"],
    "Retail Sentiment Spike":  ["short squeeze","YOLO","WSB","moon","diamond hands","gamma squeeze"],
    "Analyst Revision":        ["upgrade","downgrade","price target","overweight","underweight","buy rating"],
    "M&A / Corporate Event":   ["merger","acquisition","IPO","buyback","spinoff","tender offer","takeover"],
    "Regulatory / Legal Risk": ["SEC","DOJ","antitrust","fine","ban","lawsuit","investigation","regulation"],
    "Geopolitical Risk":       ["war","conflict","Taiwan","PLA","export ban","trade restriction","sanction"],
    "Crypto Signal":           ["whale","ETF flow","stablecoin","hash rate","exchange inflow","Bitcoin","blockchain"],
    "Fear / Panic Signal":     ["crash","collapse","circuit breaker","margin call","liquidation","plunge"],
    "Executive Change":        ["resign","appointment","CEO","CFO","chairman","director","named","stepping down"],
    "Product Launch":          ["launch","release","unveil","announce","debut","introduce","new product"],
}

NOISE_PHRASES = [
    "sponsored", "advertorial", "press release", "top 10",
    "5 reasons", "listicle", "partner content", "buy now",
    "shop now", "discount"
]

URGENCY_IMMEDIATE = ["breaking", "just in", "now", "alert", "flash", "today"]
URGENCY_DEVELOPING = ["says", "reports", "sources", "reveals", "signals", "warns"]


# ── Helper functions ──────────────────────────────────────────────────────────

def _classify_signal(text: str) -> str:
    t = text.lower()
    for signal, kws in SIGNAL_MAP.items():
        if any(k.lower() in t for k in kws):
            return signal
    return "General"


def _compute_urgency(text: str) -> str:
    t = text.lower()
    if any(w in t for w in URGENCY_IMMEDIATE):
        return "Immediate"
    if any(w in t for w in URGENCY_DEVELOPING):
        return "Developing"
    return "Background"


def _compute_relevance(text: str) -> float:
    t = text.lower()
    kw_hits = sum(1 for k in ALL_KEYWORDS if k.lower() in t)
    tick_hits = sum(1 for tk in TICKERS if tk.lower() in t)
    return min(round((kw_hits / 10) + (tick_hits * 0.2), 3), 1.0)


def _compute_entity_count(text: str) -> int:
    t = text.lower()
    return len(set(k for k in ALL_KEYWORDS if k.lower() in t))


def _title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _is_noise(title: str, snippet: str) -> bool:
    combined = (title + " " + snippet).lower()
    return any(p in combined for p in NOISE_PHRASES)


# ── Main filter pipeline ──────────────────────────────────────────────────────

def run_all_filters(articles: list) -> list:
    """Run all 7 filter layers. Returns filtered + enriched article dicts."""

    # Reload watchlist on every run
    global TICKERS, ALL_KEYWORDS
    TICKERS, ALL_KEYWORDS = _load_watchlist()

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=24)

    # ── Filter 0: Time ────────────────────────────────────────────────────────
    passed = []
    for a in articles:
        pub = a.get('published_at')
        if pub is None:
            continue
        if isinstance(pub, str):
            try:
                pub = datetime.fromisoformat(pub)
            except Exception:
                continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub >= cutoff:
            a['published_at'] = pub
            passed.append(a)
    print(f"    [F0 Time]      {len(articles)} → {len(passed)}")
    articles = passed

    # ── Filter 1: Noise exclusion ─────────────────────────────────────────────
    passed = [a for a in articles
              if not _is_noise(str(a.get('title', '')), str(a.get('content_snippet', '')))]
    print(f"    [F1 Noise]     {len(articles)} → {len(passed)}")
    articles = passed

    # ── Filter 2: Keyword match ───────────────────────────────────────────────
    passed = []
    for a in articles:
        text = str(a.get('title', '')) + ' ' + str(a.get('content_snippet', ''))
        matched = list(set(k for k in ALL_KEYWORDS if k.lower() in text.lower()))
        if matched:
            a['keywords_matched'] = matched
            passed.append(a)
    print(f"    [F2 Keywords]  {len(articles)} → {len(passed)}")
    articles = passed

    # ── Filter 3: URL dedup (check DB) ────────────────────────────────────────
    passed = [a for a in articles if not database.url_exists(str(a.get('url', '')))]
    print(f"    [F3 URL Dedup] {len(articles)} → {len(passed)}")
    articles = passed

    # ── Filter 4: Title similarity dedup ─────────────────────────────────────
    recent_titles = database.get_recent_titles(limit=500)  # list of (title, tier)
    keep = []
    for a in articles:
        title = str(a.get('title', ''))
        tier = int(a.get('tier', 5))
        duplicate = False
        for (stored_title, stored_tier) in recent_titles:
            if _title_similarity(title, stored_title) > 0.85:
                if tier >= stored_tier:
                    duplicate = True
                    break
                else:
                    database.delete_by_title(stored_title)
        if not duplicate:
            keep.append(a)
    print(f"    [F4 TitleDedup]{len(articles)} → {len(keep)}")
    articles = keep

    # ── Filter 5: Signal type + enrichment fields ─────────────────────────────
    for a in articles:
        text = str(a.get('title', '')) + ' ' + str(a.get('content_snippet', ''))
        a['signal_type'] = _classify_signal(text)
        a['event_type']  = a['signal_type']
        a['urgency_flag'] = _compute_urgency(text)
        a['relevance_score'] = _compute_relevance(text)
        a['entity_count'] = _compute_entity_count(text)

    # ── Filter 6: Reliability flag ────────────────────────────────────────────
    for a in articles:
        tier = int(a.get('tier', 5))
        source_type = str(a.get('source_type', ''))
        if tier >= 4 or source_type == 'reddit':
            a['is_flagged'] = True
            a['source_note'] = 'SOCIAL_HIGH_NOISE — verify with Tier 1–2 source before acting'
        else:
            a['is_flagged'] = False
            a['source_note'] = None

    print(f"    [F5/F6 Enrich] {len(articles)} articles classified and scored")
    return articles
