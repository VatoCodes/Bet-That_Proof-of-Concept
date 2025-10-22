"""PlayerProfiler Main Importer Orchestrator

This module orchestrates all PlayerProfiler data imports for a given season.
Follows the snapshot-then-upsert pattern from existing scrapers.
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.db_manager import DatabaseManager
from utils.data_importers.play_by_play_importer import PlayByPlayImporter
from utils.data_importers.custom_reports_importer import CustomReportsImporter
from utils.data_importers.roster_importer import RosterImporter
from utils.data_importers.team_metrics_calculator import TeamMetricsCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PlayerProfilerImporter:
    """Main orchestrator for PlayerProfiler data imports"""

    def __init__(self, imports_dir='/Users/vato/work/Bet-That/storage/imports', db_path='data/database/nfl_betting.db'):
        """
        Initialize importer

        Args:
            imports_dir: Path to PlayerProfiler CSV files
            db_path: Path to database
        """
        self.imports_dir = Path(imports_dir)
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.connect()

        # Verify imports directory exists
        if not self.imports_dir.exists():
            raise FileNotFoundError(f"Imports directory not found: {self.imports_dir}")

        logger.info(f"✅ Initialized PlayerProfiler importer")
        logger.info(f"   Imports directory: {self.imports_dir}")
        logger.info(f"   Database: {db_path}")

    def import_season(self, season=2024):
        """
        Import all PlayerProfiler data for given season

        This follows the existing scraper pattern:
        1. Load CSV data
        2. Clean/transform data
        3. Save historical snapshot
        4. Upsert to database

        Args:
            season: Season year to import

        Returns:
            dict: Import summary with counts
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 Starting PlayerProfiler import for {season} season")
        logger.info(f"{'='*70}\n")

        summary = {
            'season': season,
            'timestamp': datetime.now().isoformat(),
            'success': True,
            'imports': {}
        }

        try:
            # Step 1: Import play-by-play (foundation for team metrics)
            logger.info("📊 Step 1: Importing play-by-play data...")
            pbp_path = self.imports_dir / 'PlayerProfiler' / 'Advanced Play by Play' / f'{season}-Advanced-PBP-Data.csv'
            pbp_importer = PlayByPlayImporter(self.db_manager)
            pbp_count = pbp_importer.import_season(season, pbp_path)
            summary['imports']['play_by_play'] = pbp_count
            logger.info(f"✅ Play-by-play: {pbp_count} plays imported\n")

            # Step 2: Import custom reports (kicker, QB stats)
            logger.info("📊 Step 2: Importing custom reports (kicker & QB stats)...")
            custom_path = self.imports_dir / 'PlayerProfiler' / 'Custom Reports' / f'Custom Advanced Report (ALL_{season}).csv'
            custom_importer = CustomReportsImporter(self.db_manager)
            kicker_count, qb_count = custom_importer.import_season(season, custom_path)
            summary['imports']['kicker_stats'] = kicker_count
            summary['imports']['qb_stats_enhanced'] = qb_count
            logger.info(f"✅ Custom reports: {kicker_count} kickers, {qb_count} QBs imported\n")

            # Step 3: Import weekly roster
            logger.info("📊 Step 3: Importing weekly roster...")
            roster_path = self.imports_dir / 'PlayerProfiler' / 'Weekly Roster Key' / f'{season}-Weekly-Roster-Key.csv'
            roster_importer = RosterImporter(self.db_manager)
            roster_count = roster_importer.import_season(season, roster_path)
            summary['imports']['player_roster'] = roster_count
            logger.info(f"✅ Weekly roster: {roster_count} player-week entries imported\n")

            # Step 4: Calculate team metrics (aggregate play-by-play)
            logger.info("📊 Step 4: Calculating team metrics from play-by-play...")
            calculator = TeamMetricsCalculator(self.db_manager)
            metrics_count = calculator.calculate_all_weeks(season)
            summary['imports']['team_metrics'] = metrics_count
            logger.info(f"✅ Team metrics: {metrics_count} team-week metrics calculated\n")

        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            summary['success'] = False
            summary['error'] = str(e)
            raise

        # Final summary
        logger.info(f"{'='*70}")
        logger.info(f"🎉 PlayerProfiler import complete for {season}!")
        logger.info(f"{'='*70}")
        logger.info(f"   Play-by-play: {summary['imports'].get('play_by_play', 0):,} rows")
        logger.info(f"   Kicker stats: {summary['imports'].get('kicker_stats', 0):,} rows")
        logger.info(f"   QB enhanced:  {summary['imports'].get('qb_stats_enhanced', 0):,} rows")
        logger.info(f"   Roster:       {summary['imports'].get('player_roster', 0):,} rows")
        logger.info(f"   Team metrics: {summary['imports'].get('team_metrics', 0):,} rows")
        logger.info(f"{'='*70}\n")

        return summary

    def close(self):
        """Close database connection"""
        self.db_manager.close()


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Import PlayerProfiler data')
    parser.add_argument('--season', type=int, default=2024,
                       help='Season to import (default: 2024)')
    parser.add_argument('--imports-dir', default='/Users/vato/work/Bet-That/storage/imports',
                       help='Path to PlayerProfiler imports directory')

    args = parser.parse_args()

    importer = PlayerProfilerImporter(imports_dir=args.imports_dir)

    try:
        summary = importer.import_season(season=args.season)

        if summary['success']:
            logger.info("\n✅ Import completed successfully!")
            return 0
        else:
            logger.error("\n❌ Import failed!")
            return 1

    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        return 1

    finally:
        importer.close()


if __name__ == '__main__':
    exit(main())
