"""
scraper.py
Fetches articles from RSS feeds and Reddit.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import requests
import praw
from bs4 import BeautifulSoup

_CONFIG_DIR = Path(__file__).parent.parent / 'config'


def load_watchlist():
    with open(_CONFIG_DIR / 'watchlist.json', encoding='utf-8') as f:
        wl = json.load(f)
    tickers = wl.get('tickers', [])
    full_names = wl.get('full_names', [])
    topics = wl.get('fixed_topics', {})
    all_keywords = list(set(
        tickers + full_names +
        [kw for group in topics.values() for kw in group]
    ))
    return all_keywords


def load_sources():
    with open(_CONFIG_DIR / 'sources.json', encoding='utf-8') as f:
        return json.load(f)


def fetch_full_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'lxml')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True)
        return text[:800]
    except Exception:
        return ''


def _parse_date(entry) -> datetime:
    for attr in ('published_parsed', 'updated_parsed', 'created_parsed'):
        t = getattr(entry, attr, None)
        if t:
            try:
                import calendar
                return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def fetch_rss(source: dict) -> list:
    articles = []
    try:
        feed = feedparser.parse(source['rss_url'])
        for entry in feed.entries:
            url = entry.get('link', '')
            snippet = entry.get('summary', '')[:800]
            if source.get('full_text') and url:
                full = fetch_full_text(url)
                if full:
                    snippet = full
            articles.append({
                'title':           entry.get('title', '').strip(),
                'url':             url,
                'source':          source['name'].lower().replace(' ', '_'),
                'tier':            source['tier'],
                'published_at':    _parse_date(entry),
                'content_snippet': snippet,
                'keywords_matched': [],
                'source_type':     'rss',
            })
    except Exception as e:
        print(f"    [scraper] RSS error ({source['name']}): {e}")
    return articles


def fetch_reddit(source: dict) -> list:
    articles = []
    try:
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'financial-news-scraper/1.0'),
        )
        subreddit = reddit.subreddit(source['subreddit'])
        min_upvotes = source.get('min_upvotes', 50)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for post in subreddit.hot(limit=100):
            if post.score < min_upvotes:
                continue
            pub = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if pub < cutoff:
                continue
            articles.append({
                'title':           post.title.strip(),
                'url':             f'https://reddit.com{post.permalink}',
                'source':          f'reddit/{source["subreddit"]}',
                'tier':            source['tier'],
                'published_at':    pub,
                'content_snippet': (post.selftext or '')[:800],
                'keywords_matched': [],
                'source_type':     'reddit',
            })
    except Exception as e:
        print(f"    [scraper] Reddit error ({source.get('subreddit')}): {e}")
    return articles


def fetch_all_sources() -> list:
    sources = load_sources()
    all_articles = []
    for source in sources:
        if source['source_type'] == 'rss':
            articles = fetch_rss(source)
        elif source['source_type'] == 'reddit':
            articles = fetch_reddit(source)
        else:
            continue
        all_articles.extend(articles)
        print(f"    [scraper] {source['name']}: {len(articles)} articles")
    return all_articles
