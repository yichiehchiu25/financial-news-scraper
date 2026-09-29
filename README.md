# Financial News Intelligence Pipeline

A modular Python data pipeline that turns fragmented financial-news sources into structured, prioritised, and decision-ready HTML briefings.

Built as a portfolio project to demonstrate end-to-end data workflow design: data collection, quality filtering, database management, AI-assisted enrichment, scheduled automation, and stakeholder-focused reporting.

## Business Problem

Financial information is distributed across high-volume, time-sensitive sources. Reading each source manually makes it difficult to consistently identify relevant developments, remove duplicates, maintain a structured record, and share concise updates with decision-makers.

This project automates that workflow:

```text
News sources
    ↓
Data collection
    ↓
Relevance, recency, language and duplicate filtering
    ↓
Database storage
    ↓
AI-assisted enrichment
    ↓
HTML briefing for review and decision-making
```

Although the subject matter is financial news, the workflow is transferable to people analytics, labour-market intelligence, HR policy monitoring, employee-listening analysis, and other business-information contexts.

## What I Built

- A configurable multi-source collection layer for financial-news inputs.
- Rule-based filtering for relevance, article quality, language, recency, and duplicates.
- A database layer with an SQL schema and migration script to support structured storage and evolving enrichment fields.
- An AI enrichment step that generates structured summaries and metadata for new articles.
- An HTML reporting layer that turns processed records into a readable news briefing.
- A UTC-based scheduler that runs the pipeline three times daily and performs daily database cleanup.
- Environment-based configuration to separate secrets from source code.

## Employability Evidence

This project demonstrates skills relevant to data analyst, people analytics, HR technology, research analyst, operations analyst, and data-product roles.

| Capability | Evidence in this repository |
|---|---|
| Data pipeline design | Modular collection, filtering, persistence, enrichment, and reporting workflow |
| Data quality management | Relevance, recency, language, quality, and duplicate filtering logic |
| Data modelling | SQL schema, migration script, and database operations module |
| AI-enabled workflow design | LLM-supported article enrichment within an automated process |
| Automation | APScheduler runs scheduled pipeline jobs and database cleanup |
| Stakeholder communication | HTML briefing transforms processed data into a scannable output |
| Reproducibility and security | `requirements.txt`, `.env.example`, `.gitignore`, and configuration separation |
| Product thinking | The pipeline connects raw inputs to an end-user decision-support output |

## Technical Architecture

```text
main.py
├── scraper.py              Collects configured news sources
├── filter_articles.py      Applies data-quality and relevance rules
├── database.py             Stores articles and runs cleanup
├── enrich.py               Adds AI-generated summaries and metadata
└── report.py               Generates HTML briefing output
```

Supporting components:

- `config/` — source and watchlist configuration
- `sql/schema.sql` — database schema
- `sql/migrations/` — database schema evolution
- `src/api.py` — API-facing functionality
- `src/briefing_template_part*.html` — report presentation templates

## Tech Stack

- **Language:** Python
- **Automation:** APScheduler
- **Data collection:** Requests, BeautifulSoup, Feedparser
- **Data handling:** Pandas
- **Database:** SQL schema and Python database layer
- **AI integration:** OpenAI API
- **Reporting:** HTML templates
- **Configuration:** python-dotenv and JSON configuration files

## Repository Structure

```text
financial-news-scraper/
├── main.py
├── requirements.txt
├── .env.example
├── config/
│   ├── sources.json
│   └── watchlist.json
├── sql/
│   ├── schema.sql
│   └── migrations/
├── src/
│   ├── scraper.py
│   ├── filter_articles.py
│   ├── database.py
│   ├── enrich.py
│   ├── report.py
│   ├── api.py
│   └── briefing_template_part*.html
└── output/                 Generated locally; excluded from Git
```

## Local Setup

### 1. Clone the repository

```bash
git clone [https://github.com/yichiehchiu25/financial-news-scraper.git](https://github.com/yichiehchiu25/financial-news-scraper.git)
cd financial-news-scraper
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

For Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Add your own credentials and local database configuration to `.env`. Never commit this file.

### 5. Run the pipeline

```bash
python main.py
```

The application runs once at startup, then remains active to run scheduled jobs.

## Scheduled Workflow

| UTC time | Job |
|---|---|
| 02:00 | Database cleanup |
| 07:00 | Morning pipeline |
| 12:00 | Midday pipeline |
| 21:00 | Evening pipeline |

## Design Decisions

- **Modular components:** Collection, filtering, storage, enrichment, and reporting are separated so that individual stages can be maintained and extended independently.
- **Configurable inputs:** Sources and watchlist terms are stored outside the core application logic to reduce code changes when monitoring priorities change.
- **Data quality before enrichment:** Articles are filtered before AI processing to reduce unnecessary API usage and improve the relevance of final briefings.
- **Human-readable output:** HTML briefings make the pipeline output accessible to non-technical stakeholders.
- **Security by default:** Credentials are loaded through environment variables, while `.env` and generated output are excluded from version control.

## Future Improvements

- Add unit tests for filtering, deduplication, and database functions.
- Add structured logging, error alerts, and run-level monitoring.
- Containerise the application with Docker for reproducible deployment.
- Deploy scheduled execution with GitHub Actions or a cloud scheduler.
- Add a Streamlit dashboard to explore briefing history and filtering performance.
- Evaluate enrichment quality using a labelled sample of articles.
- Extend the data model for topic trends, source reliability, and time-series analysis.

## Author

YiChieh Chiu  
Postgraduate student in Human Resource Management, with interests in people analytics, HR technology, AI-enabled work, and data-driven decision support.