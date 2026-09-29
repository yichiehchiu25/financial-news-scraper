CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS news_articles (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title               TEXT NOT NULL,
  url                 TEXT UNIQUE NOT NULL,
  source              TEXT,
  tier                INTEGER,
  published_at        TIMESTAMPTZ,
  fetched_at          TIMESTAMPTZ DEFAULT NOW(),
  keywords_matched    TEXT[],
  content_snippet     TEXT,
  signal_type         TEXT,
  event_type          TEXT,
  is_flagged          BOOLEAN DEFAULT FALSE,
  source_note         TEXT,
  raw_metadata        JSONB,
  urgency_flag        TEXT,
  relevance_score     FLOAT,
  novelty_score       FLOAT,
  entity_count        INTEGER,
  market_impact_flag  BOOLEAN DEFAULT FALSE,
  sentiment_direction TEXT,
  sentiment_strength  TEXT
);

CREATE INDEX IF NOT EXISTS idx_published_at   ON news_articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_tier           ON news_articles (tier);
CREATE INDEX IF NOT EXISTS idx_signal_type    ON news_articles (signal_type);
CREATE INDEX IF NOT EXISTS idx_event_type     ON news_articles (event_type);
CREATE INDEX IF NOT EXISTS idx_market_impact  ON news_articles (market_impact_flag);
CREATE INDEX IF NOT EXISTS idx_keywords       ON news_articles USING GIN (keywords_matched);

CREATE TABLE IF NOT EXISTS watchlist_config (
  id        SERIAL PRIMARY KEY,
  keyword   TEXT UNIQUE NOT NULL,
  category  TEXT,
  active    BOOLEAN DEFAULT TRUE,
  added_at  TIMESTAMPTZ DEFAULT NOW()
);
