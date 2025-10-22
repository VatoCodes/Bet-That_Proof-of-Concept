#!/usr/bin/env python3
"""
Main Scheduler for automated NFL data scraping
Runs scrapers daily Monday through Saturday at 9am:
- All data: Defense stats, QB stats, matchups, and odds
- Companion to scheduler_odds.py (which runs odds-only at 3pm)
"""
import schedule
import time
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import (
    SCRAPE_DAYS,
    SCRAPE_TIME,
    LOG_FORMAT,
    LOG_LEVEL,
    DATA_DIR
)

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DATA_DIR.parent / 'scheduler.log')
    ]
)

logger = logging.getLogger(__name__)


class NFLDataScheduler:
    """Scheduler for automated NFL data collection"""

    def __init__(self):
        """Initialize the scheduler"""
        self.main_script = Path(__file__).parent / "main.py"

        if not self.main_script.exists():
            raise FileNotFoundError(f"Main script not found: {self.main_script}")

        logger.info("NFL Data Scheduler initialized")

    def run_daily_collection(self):
        """Run daily data collection (all data sources)"""
        logger.info("\n" + "=" * 80)
        logger.info(f"DAILY DATA COLLECTION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Run main.py (collects all data by default)
            result = subprocess.run(
                [sys.executable, str(self.main_script)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout (needs more time for all data)
            )

            # Log output
            if result.stdout:
                logger.info(result.stdout)

            if result.stderr:
                logger.error(result.stderr)

            if result.returncode == 0:
                logger.info("✓ Daily data collection completed successfully")
            else:
                logger.error(f"✗ Daily data collection failed with code {result.returncode}")

        except subprocess.TimeoutExpired:
            logger.error("✗ Daily data collection timed out")
        except Exception as e:
            logger.error(f"✗ Error running daily data collection: {e}")

    def setup_schedule(self):
        """Configure the daily schedule"""
        # Schedule for each day: Tuesday through Saturday at 9am
        for day in SCRAPE_DAYS:
            getattr(schedule.every(), day).at(SCRAPE_TIME).do(
                self.run_daily_collection
            )

        logger.info("Schedule configured:")
        logger.info(f"  - {', '.join([day.title() for day in SCRAPE_DAYS])} at {SCRAPE_TIME}")
        logger.info(f"  - Collects: Defense stats, QB stats, matchups, and odds")
        logger.info(f"  - Note: Odds-only scraper also runs at 3pm (see scheduler_odds.py)")

    def run(self):
        """Run the scheduler (blocking)"""
        self.setup_schedule()

        logger.info("\n" + "=" * 80)
        logger.info("NFL DATA SCHEDULER STARTED")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80 + "\n")

        logger.info("Waiting for scheduled tasks...")
        logger.info("Press Ctrl+C to stop\n")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("\n" + "=" * 80)
            logger.info("SCHEDULER STOPPED BY USER")
            logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Automated scheduler for NFL data scraping'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Run daily data collection immediately (for testing)'
    )

    args = parser.parse_args()

    scheduler = NFLDataScheduler()

    # Handle test mode
    if args.test:
        logger.info("TEST MODE: Running daily data collection immediately")
        scheduler.run_daily_collection()
        return

    # Normal mode: run scheduler
    scheduler.run()


if __name__ == "__main__":
    main()
