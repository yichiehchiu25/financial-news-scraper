"""
database.py
PostgreSQL connection, insert, dedup helpers, and cleanup.
"""

import os
import psycopg2
from datetime import datetime, timezone


def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'financial_news'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
    )


def url_exists(url: str) -> bool:
    """Return True if the URL already exists in the DB."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM news_articles WHERE url = %s LIMIT 1", (url,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def get_recent_titles(limit: int = 500) -> list:
    """Return list of (title, tier) for the most recent articles."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT title, tier FROM news_articles
        ORDER BY fetched_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_by_title(title: str):
    """Delete an article by exact title match (used in similarity dedup)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM news_articles WHERE title = %s", (title,))
    conn.commit()
    cur.close()
    conn.close()


def insert_articles(articles: list):
    """Bulk insert with ON CONFLICT (url) DO NOTHING."""
    if not articles:
        return
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    for a in articles:
        try:
            cur.execute("""
                INSERT INTO news_articles (
                    title, url, source, tier, published_at,
                    keywords_matched, content_snippet,
                    signal_type, event_type,
                    is_flagged, source_note,
                    urgency_flag, relevance_score, entity_count
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (url) DO NOTHING
            """, (
                a.get('title'),
                a.get('url'),
                a.get('source'),
                a.get('tier'),
                a.get('published_at'),
                a.get('keywords_matched', []),
                a.get('content_snippet'),
                a.get('signal_type', 'General'),
                a.get('event_type', 'General'),
                a.get('is_flagged', False),
                a.get('source_note'),
                a.get('urgency_flag', 'Background'),
                a.get('relevance_score'),
                a.get('entity_count'),
            ))
            inserted += cur.rowcount
        except Exception as e:
            print(f"    [DB] Insert error for '{a.get('title', '')[:50]}': {e}")
            conn.rollback()
            continue
    conn.commit()
    cur.close()
    conn.close()
    print(f"    [DB] Inserted {inserted} new articles")


def get_event_count_today(event_type: str) -> int:
    """
    Returns count of articles with given event_type published today (UTC).
    Used by enrich.py to calculate novelty_score.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM news_articles
        WHERE event_type = %s
        AND published_at::date = CURRENT_DATE
    """, (event_type,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return max(count, 1)


def run_cleanup():
    """
    Daily maintenance:
      - Delete tier>=4 articles older than 90 days
      - Null out snippets older than 7 days (save space)
      - Delete all articles older than 180 days
    """
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M UTC')}] Running DB cleanup...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM news_articles
        WHERE published_at < NOW() - INTERVAL '90 days'
        AND tier >= 4
    """)
    deleted_social = cur.rowcount

    cur.execute("""
        UPDATE news_articles
        SET content_snippet = NULL
        WHERE published_at < NOW() - INTERVAL '7 days'
        AND content_snippet IS NOT NULL
    """)
    nulled = cur.rowcount

    cur.execute("""
        DELETE FROM news_articles
        WHERE published_at < NOW() - INTERVAL '180 days'
    """)
    deleted_old = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Cleanup: deleted {deleted_social} old social, nulled {nulled} snippets, deleted {deleted_old} ancient")
