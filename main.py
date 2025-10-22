#!/usr/bin/env python3
"""
Main orchestrator for NFL data scraping
Runs all scrapers and handles data collection workflow
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from scrapers.defense_stats_scraper import DefenseStatsScraper
from scrapers.qb_stats_scraper import QBStatsScraper
from scrapers.matchups_scraper import MatchupsScraper
from scrapers.odds_scraper import OddsScraper
from config import LOG_LEVEL, LOG_FORMAT, DATA_DIR
from utils.db_manager import DatabaseManager
from utils.historical_storage import HistoricalStorage
from utils.data_validator import DataValidator


# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DATA_DIR.parent / 'scraper.log')
    ]
)

logger = logging.getLogger(__name__)


class DataPipeline:
    """Main data collection pipeline orchestrator"""

    def __init__(self, week: int, year: int = 2025, save_to_db: bool = False, save_snapshots: bool = False):
        """
        Initialize the data pipeline

        Args:
            week: NFL week number
            year: NFL season year
            save_to_db: Whether to save data to database
            save_snapshots: Whether to save historical snapshots
        """
        self.week = week
        self.year = year
        self.save_to_db = save_to_db
        self.save_snapshots = save_snapshots
        self.results = {
            'defense_stats': None,
            'qb_stats': None,
            'matchups': None,
            'odds': None
        }
        
        # Initialize database and historical storage if needed
        self.db_manager = None
        self.historical_storage = None
        
        if self.save_to_db:
            self.db_manager = DatabaseManager()
            self.db_manager.connect()
        
        if self.save_snapshots:
            self.historical_storage = HistoricalStorage()

    def run_defense_stats(self) -> bool:
        """
        Run defense stats scraper

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("STEP 1: Scraping Defense Stats")
        logger.info("=" * 60)

        try:
            scraper = DefenseStatsScraper(year=self.year)
            result = scraper.run(week=self.week)

            if result:
                self.results['defense_stats'] = result
                logger.info(f"✓ Defense stats saved: {result}")
                
                # Save to database if enabled
                if self.save_to_db and self.db_manager:
                    try:
                        rows_inserted = self.db_manager.insert_from_csv('defense_stats', result, week=self.week)
                        logger.info(f"✓ Saved {rows_inserted} defense stats to database")
                    except Exception as e:
                        logger.error(f"✗ Error saving defense stats to database: {e}")
                
                # Save historical snapshot if enabled
                if self.save_snapshots and self.historical_storage:
                    try:
                        snapshot_path = self.historical_storage.save_snapshot(result, self.week)
                        if snapshot_path:
                            logger.info(f"✓ Saved defense stats snapshot: {snapshot_path}")
                    except Exception as e:
                        logger.error(f"✗ Error saving defense stats snapshot: {e}")
                
                return True
            else:
                logger.error("✗ Failed to scrape defense stats")
                return False

        except Exception as e:
            logger.error(f"✗ Error in defense stats scraper: {e}")
            return False

    def run_qb_stats(self) -> bool:
        """
        Run QB stats scraper

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("STEP 2: Scraping QB Stats")
        logger.info("=" * 60)

        try:
            scraper = QBStatsScraper(year=self.year)
            result = scraper.run()

            if result:
                self.results['qb_stats'] = result
                logger.info(f"✓ QB stats saved: {result}")
                
                # Save to database if enabled
                if self.save_to_db and self.db_manager:
                    try:
                        rows_inserted = self.db_manager.insert_from_csv('qb_stats', result, year=self.year)
                        logger.info(f"✓ Saved {rows_inserted} QB stats to database")
                    except Exception as e:
                        logger.error(f"✗ Error saving QB stats to database: {e}")
                
                # Save historical snapshot if enabled
                if self.save_snapshots and self.historical_storage:
                    try:
                        snapshot_path = self.historical_storage.save_snapshot(result, self.week)
                        if snapshot_path:
                            logger.info(f"✓ Saved QB stats snapshot: {snapshot_path}")
                    except Exception as e:
                        logger.error(f"✗ Error saving QB stats snapshot: {e}")
                
                return True
            else:
                logger.error("✗ Failed to scrape QB stats")
                return False

        except Exception as e:
            logger.error(f"✗ Error in QB stats scraper: {e}")
            return False

    def run_matchups(self) -> bool:
        """
        Run matchups scraper

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("STEP 3: Scraping Matchups")
        logger.info("=" * 60)

        try:
            scraper = MatchupsScraper()
            result = scraper.run(week=self.week)

            if result:
                self.results['matchups'] = result
                logger.info(f"✓ Matchups saved: {result}")
                
                # Save to database if enabled
                if self.save_to_db and self.db_manager:
                    try:
                        rows_inserted = self.db_manager.insert_from_csv('matchups', result, week=self.week)
                        logger.info(f"✓ Saved {rows_inserted} matchups to database")
                    except Exception as e:
                        logger.error(f"✗ Error saving matchups to database: {e}")
                
                # Save historical snapshot if enabled
                if self.save_snapshots and self.historical_storage:
                    try:
                        snapshot_path = self.historical_storage.save_snapshot(result, self.week)
                        if snapshot_path:
                            logger.info(f"✓ Saved matchups snapshot: {snapshot_path}")
                    except Exception as e:
                        logger.error(f"✗ Error saving matchups snapshot: {e}")
                
                return True
            else:
                logger.error("✗ Failed to scrape matchups")
                return False

        except Exception as e:
            logger.error(f"✗ Error in matchups scraper: {e}")
            return False

    def run_odds(self) -> bool:
        """
        Run odds scraper (fetches all markets: spreads, totals, player props)

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("STEP 4: Fetching All Odds Data")
        logger.info("=" * 60)

        try:
            scraper = OddsScraper()

            # Show API usage before fetching
            status = scraper.get_usage_report()
            logger.info(f"API Keys: {status['total_keys']} | Remaining requests: {status['remaining_requests']}")

            result = scraper.run(week=self.week)

            if result:
                # Result is now a dictionary with market names and file paths
                self.results['odds'] = result
                logger.info(f"✓ Odds saved:")
                for market, path in result.items():
                    logger.info(f"  - {market}: {path}")
                
                # Save to database if enabled
                if self.save_to_db and self.db_manager:
                    try:
                        # Save each market to appropriate table
                        for market, path in result.items():
                            if market == 'spreads':
                                rows_inserted = self.db_manager.insert_from_csv('odds_spreads', path, week=self.week)
                                logger.info(f"✓ Saved {rows_inserted} spreads to database")
                            elif market == 'totals':
                                rows_inserted = self.db_manager.insert_from_csv('odds_totals', path, week=self.week)
                                logger.info(f"✓ Saved {rows_inserted} totals to database")
                            elif market == 'player_pass_tds':
                                rows_inserted = self.db_manager.insert_from_csv('qb_props', path, week=self.week)
                                logger.info(f"✓ Saved {rows_inserted} QB props to database")
                    except Exception as e:
                        logger.error(f"✗ Error saving odds to database: {e}")
                
                # Save historical snapshots if enabled
                if self.save_snapshots and self.historical_storage:
                    try:
                        for market, path in result.items():
                            snapshot_path = self.historical_storage.save_snapshot(path, self.week)
                            if snapshot_path:
                                logger.info(f"✓ Saved {market} snapshot: {snapshot_path}")
                    except Exception as e:
                        logger.error(f"✗ Error saving odds snapshots: {e}")

                # Show final API usage
                final_status = scraper.get_usage_report()
                logger.info(f"API requests used: {final_status['total_requests']} | Remaining: {final_status['remaining_requests']}")
                return True
            else:
                logger.error("✗ Failed to fetch odds")
                return False

        except Exception as e:
            logger.error(f"✗ Error in odds scraper: {e}")
            return False
    
    def cleanup(self):
        """Clean up database connections"""
        if self.db_manager:
            self.db_manager.close()

    def run_all(self, skip_odds: bool = False) -> bool:
        """
        Run all scrapers in sequence

        Args:
            skip_odds: Whether to skip odds scraping (useful for Tuesday runs)

        Returns:
            True if all succeeded, False otherwise
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"NFL DATA COLLECTION PIPELINE - Week {self.week}")
        logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60 + "\n")

        # Pre-scrape validation: Check if week already has data
        if self.save_to_db:
            logger.info("🔍 Pre-scrape validation...")
            validator = DataValidator()
            available_weeks = validator.get_available_weeks()

            if self.week in available_weeks:
                logger.warning(f"⚠️  WARNING: Week {self.week} already has data in database!")
                response = input("   Overwrite existing data? (yes/no): ").strip().lower()
                if response != 'yes':
                    logger.info("   ❌ Scraping cancelled by user")
                    return False
                else:
                    logger.info("   ✅ User confirmed - proceeding with scrape")

        success = True

        # Run scrapers
        success &= self.run_defense_stats()
        success &= self.run_qb_stats()
        success &= self.run_matchups()

        if not skip_odds:
            success &= self.run_odds()
        else:
            logger.info("\n" + "=" * 60)
            logger.info("STEP 4: Skipping odds (run manually on Thursday)")
            logger.info("=" * 60)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)

        files_scraped = 0
        api_requests_used = 0

        for name, path in self.results.items():
            if path:
                # Handle odds result (which is now a dict)
                if name == 'odds' and isinstance(path, dict):
                    logger.info(f"✓ {name.replace('_', ' ').title()}:")
                    files_scraped += len(path)
                    for market, market_path in path.items():
                        logger.info(f"    - {market}: {market_path}")
                else:
                    logger.info(f"✓ {name.replace('_', ' ').title()}: {path}")
                    files_scraped += 1
            else:
                logger.info(f"✗ {name.replace('_', ' ').title()}: FAILED")

        # Log scrape run to database if enabled
        if self.save_to_db and self.db_manager:
            try:
                status = 'success' if success else 'partial'
                self.db_manager.log_scrape_run(
                    week=self.week,
                    files_scraped=files_scraped,
                    api_requests_used=api_requests_used,
                    status=status
                )
            except Exception as e:
                logger.error(f"✗ Error logging scrape run: {e}")

        logger.info("=" * 60)
        logger.info(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Status: {'SUCCESS' if success else 'FAILED'}")
        logger.info("=" * 60 + "\n")

        # Clean up database connections
        self.cleanup()

        return success


def get_current_nfl_week() -> int:
    """
    Get current NFL week from WeekManager (single source of truth)

    Returns:
        Current NFL week number
    """
    from utils.week_manager import WeekManager
    wm = WeekManager()
    return wm.get_current_week()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='NFL Data Scraping Pipeline for Betting POC'
    )

    parser.add_argument(
        '--week',
        type=int,
        help='NFL week number to scrape (default: auto-detect current week)'
    )

    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='NFL season year (default: 2025)'
    )

    parser.add_argument(
        '--skip-odds',
        action='store_true',
        help='Skip odds scraping (useful for Tuesday stats-only runs)'
    )

    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Run only defense and QB stats (Tuesday workflow)'
    )

    parser.add_argument(
        '--odds-only',
        action='store_true',
        help='Run only odds scraping (Thursday workflow)'
    )

    parser.add_argument(
        '--save-to-db',
        action='store_true',
        help='Save data to database (Phase 1 feature)'
    )

    parser.add_argument(
        '--save-snapshots',
        action='store_true',
        help='Save historical snapshots (Phase 1 feature)'
    )

    args = parser.parse_args()

    # Determine week
    week = args.week if args.week else get_current_nfl_week()

    logger.info(f"Running pipeline for Week {week}, {args.year} season")

    # Create pipeline
    pipeline = DataPipeline(
        week=week, 
        year=args.year, 
        save_to_db=args.save_to_db, 
        save_snapshots=args.save_snapshots
    )

    # Run appropriate workflow
    if args.stats_only:
        logger.info("Running TUESDAY workflow (stats only)")
        success = pipeline.run_defense_stats() and pipeline.run_qb_stats()

    elif args.odds_only:
        logger.info("Running THURSDAY workflow (odds only)")
        success = pipeline.run_matchups() and pipeline.run_odds()

    else:
        logger.info("Running FULL workflow")
        success = pipeline.run_all(skip_odds=args.skip_odds)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
