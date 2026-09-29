ALTER TABLE news_articles
  ADD COLUMN IF NOT EXISTS relevance_score    FLOAT,
  ADD COLUMN IF NOT EXISTS novelty_score      FLOAT,
  ADD COLUMN IF NOT EXISTS entity_count       INTEGER,
  ADD COLUMN IF NOT EXISTS market_impact_flag BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS event_type         TEXT;

CREATE INDEX IF NOT EXISTS idx_event_type    ON news_articles (event_type);
CREATE INDEX IF NOT EXISTS idx_market_impact ON news_articles (market_impact_flag);
