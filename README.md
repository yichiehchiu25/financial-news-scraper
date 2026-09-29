# financial-news-scraper

Automated financial news scraper with 4-layer enrichment pipeline.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your DB credentials and Reddit API keys

# 3. Create database
psql -U postgres -c "CREATE DATABASE financial_news;"

# 4. Run schema (first time only)
psql -U postgres -d financial_news -f sql/schema.sql

# 5. Run migration (if upgrading existing DB)
psql -U postgres -d financial_news -f sql/migrations/001_add_enrichment_fields.sql

# 6. Start
python main.py
```

## Schedule

- **07:00 UTC** — Morning pipeline
- **12:00 UTC** — Midday pipeline
- **21:00 UTC** — Evening pipeline
- **02:00 UTC** — Daily DB cleanup

## Output

Each run produces two files in `output/`:
- `news-briefing_{date}_{time}_{run}.html` — Interactive dashboard
- `news_enriched_{date}_{time}_{run}.csv`  — Full enriched dataset

## API

Start with: `uvicorn src.api:app --reload`

- `GET /news` — Query articles
- `GET /news/flagged` — High-noise articles
- `GET /briefing/latest` — List report files
- `POST /watchlist` — Add keyword
- `DELETE /watchlist/{keyword}` — Remove keyword

## Template files

`src/briefing_template_part1.html` and `briefing_template_part2.html` are
split from `news-briefing.html`. See README for how to regenerate them.
