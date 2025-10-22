#!/usr/bin/env python3
"""
Odds-only Scheduler for automated NFL odds scraping
Runs odds scraper daily Monday through Saturday at 3pm:
- Odds data only: QB TD props, spreads, totals
- Complements main scheduler (which runs at 9am with all data)
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
    ODDS_SCRAPE_TIME,
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
        logging.FileHandler(DATA_DIR.parent / 'scheduler_odds.log')
    ]
)

logger = logging.getLogger(__name__)


class NFLOddsScheduler:
    """Scheduler for automated NFL odds collection (afternoon runs)"""

    def __init__(self):
        """Initialize the odds scheduler"""
        self.main_script = Path(__file__).parent / "main.py"

        if not self.main_script.exists():
            raise FileNotFoundError(f"Main script not found: {self.main_script}")

        logger.info("NFL Odds Scheduler initialized")

    def run_odds_collection(self):
        """Run odds-only data collection"""
        logger.info("\n" + "=" * 80)
        logger.info(f"ODDS DATA COLLECTION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Run main.py with --odds-only flag
            result = subprocess.run(
                [sys.executable, str(self.main_script), '--odds-only'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout (odds-only is faster)
            )

            # Log output
            if result.stdout:
                logger.info(result.stdout)

            if result.stderr:
                logger.error(result.stderr)

            if result.returncode == 0:
                logger.info("✓ Odds collection completed successfully")
            else:
                logger.error(f"✗ Odds collection failed with code {result.returncode}")

        except subprocess.TimeoutExpired:
            logger.error("✗ Odds collection timed out")
        except Exception as e:
            logger.error(f"✗ Error running odds collection: {e}")

    def setup_schedule(self):
        """Configure the daily odds schedule"""
        # Schedule for each day: Monday through Saturday at 3pm
        for day in SCRAPE_DAYS:
            getattr(schedule.every(), day).at(ODDS_SCRAPE_TIME).do(
                self.run_odds_collection
            )

        logger.info("Odds schedule configured:")
        logger.info(f"  - {', '.join([day.title() for day in SCRAPE_DAYS])} at {ODDS_SCRAPE_TIME}")
        logger.info(f"  - Collects: QB TD props, spreads, totals (odds only)")

    def run(self):
        """Run the scheduler (blocking)"""
        self.setup_schedule()

        logger.info("\n" + "=" * 80)
        logger.info("NFL ODDS SCHEDULER STARTED")
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
            logger.info("ODDS SCHEDULER STOPPED BY USER")
            logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Automated scheduler for NFL odds scraping (afternoon runs)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Run odds collection immediately (for testing)'
    )

    args = parser.parse_args()

    scheduler = NFLOddsScheduler()

    # Handle test mode
    if args.test:
        logger.info("TEST MODE: Running odds collection immediately")
        scheduler.run_odds_collection()
        return

    # Normal mode: run scheduler
    scheduler.run()


if __name__ == "__main__":
    main()
