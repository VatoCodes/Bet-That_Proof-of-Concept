"""
Re-scrape specific weeks and populate database
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.matchups_scraper import MatchupsScraper
from utils.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rescrape_week(week: int):
    """
    Re-scrape a specific week and save to database

    Args:
        week: NFL week number
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Re-scraping Week {week}")
    logger.info(f"{'=' * 60}")

    try:
        # Initialize scraper and database
        scraper = MatchupsScraper()
        db_manager = DatabaseManager()
        db_manager.connect()  # Must connect before using

        # Run scraper (saves to CSV)
        csv_path = scraper.run(week=week)

        if not csv_path:
            logger.error(f"Failed to scrape week {week}")
            return False

        logger.info(f"✓ Scraped matchups saved to {csv_path}")

        # Save to database
        try:
            rows_inserted = db_manager.insert_from_csv('matchups', csv_path, week=week)
            logger.info(f"✓ Saved {rows_inserted} matchups to database for week {week}")
            return True
        except Exception as e:
            logger.error(f"✗ Error saving to database: {e}")
            return False

    except Exception as e:
        logger.error(f"✗ Error re-scraping week {week}: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\nUsage: python3 scripts/rescrape_weeks.py <week1> [week2] [week3] ...")
        print("Example: python3 scripts/rescrape_weeks.py 7 8")
        sys.exit(1)

    weeks = [int(w) for w in sys.argv[1:]]

    logger.info(f"\nRe-scraping {len(weeks)} weeks: {weeks}")

    success_count = 0
    for week in weeks:
        if rescrape_week(week):
            success_count += 1

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Summary: {success_count}/{len(weeks)} weeks successfully re-scraped")
    logger.info(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
