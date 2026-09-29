"""
api.py
FastAPI query interface for news_articles.
"""

import re
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from database import get_connection

app = FastAPI(title="Financial News API", version="2.0")

OUTPUT_DIR = Path(__file__).parent.parent / 'output'


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/news")
def get_news(
    tier: Optional[int] = None,
    signal_type: Optional[str] = None,
    event_type: Optional[str] = None,
    keyword: Optional[str] = None,
    hours_ago: int = 24,
    limit: int = 50,
):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, title, url, source, tier, published_at,
               keywords_matched, content_snippet, signal_type, event_type,
               is_flagged, urgency_flag, relevance_score, novelty_score,
               entity_count, market_impact_flag
        FROM news_articles
        WHERE published_at > NOW() - INTERVAL '%s hours'
    """
    params = [hours_ago]

    if tier is not None:
        query += " AND tier = %s"
        params.append(tier)
    if signal_type:
        query += " AND signal_type = %s"
        params.append(signal_type)
    if event_type:
        query += " AND event_type = %s"
        params.append(event_type)
    if keyword:
        query += " AND (title ILIKE %s OR content_snippet ILIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    query += " ORDER BY published_at DESC LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    cur.close()
    conn.close()

    return [dict(zip(columns, row)) for row in rows]


@app.get("/news/flagged")
def get_flagged():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, url, source, tier, published_at,
               keywords_matched, content_snippet, event_type,
               is_flagged, source_note, urgency_flag,
               relevance_score, market_impact_flag
        FROM news_articles
        WHERE is_flagged = TRUE
        AND published_at > NOW() - INTERVAL '24 hours'
        ORDER BY published_at DESC
    """)
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


@app.post("/watchlist")
def add_watchlist(payload: dict):
    keyword = payload.get('keyword', '').strip()
    category = payload.get('category', 'ticker')
    if not keyword:
        return {"error": "keyword is required"}
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO watchlist_config (keyword, category)
        VALUES (%s, %s)
        ON CONFLICT (keyword) DO UPDATE SET active = TRUE
    """, (keyword, category))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "ok", "keyword": keyword, "category": category}


@app.delete("/watchlist/{keyword}")
def remove_watchlist(keyword: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE watchlist_config SET active = FALSE WHERE keyword = %s
    """, (keyword,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "deactivated", "keyword": keyword}


@app.get("/briefing/latest")
def list_briefings():
    """
    Scan output/ folder, return available report files sorted by timestamp DESC.
    """
    if not OUTPUT_DIR.exists():
        return []

    results = []
    pattern = re.compile(r'news-briefing_(\d{8})_(\d{4})_(\w+)\.html$')

    for f in OUTPUT_DIR.glob('news-briefing_*.html'):
        m = pattern.match(f.name)
        if m:
            date_str, time_str, run_label = m.groups()
            timestamp = f"{date_str}_{time_str}"

            csv_name = f'news_enriched_{timestamp}_{run_label}.csv'
            csv_path = OUTPUT_DIR / csv_name
            article_count = None
            if csv_path.exists():
                with open(csv_path, encoding='utf-8') as cf:
                    article_count = sum(1 for _ in cf) - 1

            results.append({
                "filename":      f.name,
                "run_label":     run_label,
                "date":          date_str,
                "time":          time_str,
                "timestamp":     timestamp,
                "article_count": article_count,
                "html_path":     str(f),
                "csv_path":      str(csv_path) if csv_path.exists() else None,
            })

    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results
