import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dotenv import load_dotenv
load_dotenv()

import scraper
import filter_articles
import database
import enrich
import report

from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler(timezone='UTC')


def run_full_pipeline():
    start = datetime.now(timezone.utc)
    print(f"\n[{start.strftime('%Y-%m-%d %H:%M:%S UTC')}] ── Pipeline START ──")
    try:
        print("[1/5] Fetching articles...")
        articles = scraper.fetch_all_sources()
        print(f"      Fetched {len(articles)} raw articles")

        print("[2/5] Filtering...")
        filtered = filter_articles.run_all_filters(articles)
        print(f"      Kept {len(filtered)} after filters")

        print("[3/5] Inserting into database...")
        database.insert_articles(filtered)

        print("[4/5] Enriching new articles...")
        enrich.run_enrichment()

        print("[5/5] Generating briefing report...")
        report.generate_briefing()

        elapsed = (datetime.now(timezone.utc) - start).seconds
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] ── Pipeline COMPLETE ({elapsed}s) ──\n")

    except Exception as e:
        print(f"[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("=" * 60)
    print("  Financial News Scraper — Starting")
    print("=" * 60)

    # Scheduled runs: 07:00, 12:00, 21:00 UTC daily
    scheduler.add_job(run_full_pipeline, 'cron', hour=7,  minute=0, id='morning', name='Morning Run')
    scheduler.add_job(run_full_pipeline, 'cron', hour=12, minute=0, id='midday',  name='Midday Run')
    scheduler.add_job(run_full_pipeline, 'cron', hour=21, minute=0, id='evening', name='Evening Run')

    # Daily cleanup at 02:00 UTC
    scheduler.add_job(database.run_cleanup, 'cron', hour=2, minute=0, id='cleanup', name='Daily Cleanup')

    print("Scheduled jobs:")
    print("  07:00 UTC — Morning pipeline")
    print("  12:00 UTC — Midday pipeline")
    print("  21:00 UTC — Evening pipeline")
    print("  02:00 UTC — Daily DB cleanup")
    print("\nPress Ctrl+C to stop.\n")
    # 啟動時立即跑一次
    run_full_pipeline()
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
