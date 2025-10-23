"""PlayerProfiler Game Log Importer

Imports game-by-game QB statistics from PlayerProfiler's Advanced Game Log.
This provides pre-aggregated stats like passing_touchdowns and red_zone_passes
that aren't available in play-by-play data.

Key Data:
- Passing touchdowns (actual TD flags, not derived)
- Red zone passes and completions
- Clean pocket attempts
- Deep ball attempts
- Game-level aggregated stats

Usage:
    from utils.data_importers.game_log_importer import GameLogImporter

    importer = GameLogImporter(db_manager)
    count = importer.import_season(2024, csv_path)
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.db_manager import DatabaseManager
from utils.name_normalizer import normalize_player_name

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GameLogImporter:
    """Imports PlayerProfiler game log data into player_game_log table"""

    # Map CSV columns to database columns
    COLUMN_MAPPING = {
        'player': 'player_id',           # PlayerProfiler player ID
        'name': 'player_name',
        'week': 'week',
        'position': 'position',
        'team': 'team',
        'opponent': 'opponent',

        # Passing stats
        'pass_attempts': 'passing_attempts',
        'completions': 'passing_completions',
        'passing_yards': 'passing_yards',
        'passing_touchdowns': 'passing_touchdowns',
        'interceptions': 'interceptions',

        # Red zone stats
        'red_zone_passes': 'red_zone_passes',
        'red_zone_completions': 'red_zone_completions',

        # Advanced stats
        'deep_ball_attempts': 'deep_ball_attempts',
        'throws_under_duress': 'pressured_attempts',

        # Rushing stats
        'carries': 'rushing_attempts',
        'rushing_yards': 'rushing_yards',
        'rushing_touchdowns': 'rushing_touchdowns',

        # Clean pocket (NOTE: This is total snaps, not specifically clean pocket)
        # We'll use pass_attempts as proxy for clean pocket attempts
        # PlayerProfiler doesn't have explicit "clean pocket attempts" in game log
    }

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize game log importer

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager

    def import_season(self, season: int, csv_path: Path) -> int:
        """
        Import game log data for entire season

        Args:
            season: Season year (e.g., 2024)
            csv_path: Path to game log CSV file

        Returns:
            Number of records imported
        """
        logger.info(f"📊 Importing game log data for {season} season...")
        logger.info(f"   Source: {csv_path}")

        if not csv_path.exists():
            logger.error(f"❌ File not found: {csv_path}")
            return 0

        try:
            # Load CSV
            df_raw = pd.read_csv(csv_path)
            logger.info(f"   Loaded {len(df_raw)} rows from CSV")

            # Filter to QBs only
            df_qbs = df_raw[df_raw['position'] == 'QB'].copy()
            logger.info(f"   Filtered to {len(df_qbs)} QB game log entries")

            if len(df_qbs) == 0:
                logger.warning("⚠️  No QB records found in CSV")
                return 0

            # Rename columns to match database schema
            df_clean = pd.DataFrame()
            for csv_col, db_col in self.COLUMN_MAPPING.items():
                if csv_col in df_qbs.columns:
                    df_clean[db_col] = df_qbs[csv_col]
                else:
                    logger.warning(f"⚠️  Column not found in CSV: {csv_col}")
                    # Set default values for missing columns
                    if db_col in ['deep_ball_attempts', 'pressured_attempts']:
                        df_clean[db_col] = 0

            # Add season
            df_clean['season'] = season

            # Add import timestamp
            df_clean['imported_at'] = datetime.now().isoformat()

            # Data quality: Fill NaN values with 0 for numeric columns
            numeric_cols = [
                'passing_attempts', 'passing_completions', 'passing_yards',
                'passing_touchdowns', 'interceptions', 'red_zone_passes',
                'red_zone_completions', 'deep_ball_attempts', 'pressured_attempts',
                'rushing_attempts', 'rushing_yards', 'rushing_touchdowns'
            ]
            for col in numeric_cols:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].fillna(0).astype(int)

            # Clean and normalize player names
            # 1. Strip whitespace
            df_clean['player_name'] = df_clean['player_name'].str.strip()
            df_clean = df_clean[df_clean['player_name'].notna()]
            df_clean = df_clean[df_clean['player_name'] != '']

            # 2. Normalize names (remove suffixes like Jr., II, III, extra spaces)
            # Store original names for logging
            original_names = df_clean['player_name'].unique()
            df_clean['player_name'] = df_clean['player_name'].apply(normalize_player_name)
            normalized_names = df_clean['player_name'].unique()

            # Log normalization changes
            name_changes = 0
            for orig, norm in zip(sorted(original_names), sorted(normalized_names)):
                if orig != norm:
                    name_changes += 1

            if name_changes > 0:
                logger.info(f"   Normalized {name_changes} player names (removed suffixes/extra spaces)")

            # Validate weeks (1-18 for NFL)
            df_clean = df_clean[(df_clean['week'] >= 1) & (df_clean['week'] <= 18)]

            logger.info(f"   Cleaned to {len(df_clean)} valid QB game log entries")

            # Save historical snapshot
            self._save_historical_snapshot(df_clean, season)

            # Upsert to database
            rows_imported = self.db_manager.upsert_player_game_log(df_clean)

            logger.info(f"✅ Game log import complete: {rows_imported} QB game records")

            # Summary stats
            unique_qbs = df_clean['player_name'].nunique()
            weeks = df_clean['week'].nunique()
            logger.info(f"   {unique_qbs} unique QBs across {weeks} weeks")

            return rows_imported

        except Exception as e:
            logger.error(f"❌ Error importing game log: {e}")
            raise

    def _save_historical_snapshot(self, df: pd.DataFrame, season: int):
        """
        Save historical snapshot of imported data

        Args:
            df: DataFrame to snapshot
            season: Season year
        """
        snapshot_dir = Path('data/historical/playerprofile_imports')
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_path = snapshot_dir / f'game_log_{season}_{timestamp}.csv'

        df.to_csv(snapshot_path, index=False)
        logger.info(f"   📸 Snapshot saved: {snapshot_path}")

    def import_multiple_seasons(self, seasons: list, base_path: Path) -> dict:
        """
        Import game logs for multiple seasons

        Args:
            seasons: List of season years (e.g., [2020, 2021, 2022, 2023, 2024, 2025])
            base_path: Base directory containing game log CSVs

        Returns:
            Dictionary with import summary
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 Multi-season game log import")
        logger.info(f"{'='*70}\n")

        summary = {
            'total_records': 0,
            'seasons': {}
        }

        for season in seasons:
            csv_path = base_path / f'{season}-Advanced-Gamelog.csv'

            if not csv_path.exists():
                logger.warning(f"⚠️  Skipping {season}: File not found")
                summary['seasons'][season] = {'status': 'file_not_found', 'records': 0}
                continue

            try:
                count = self.import_season(season, csv_path)
                summary['total_records'] += count
                summary['seasons'][season] = {'status': 'success', 'records': count}
            except Exception as e:
                logger.error(f"❌ Failed to import {season}: {e}")
                summary['seasons'][season] = {'status': 'error', 'records': 0, 'error': str(e)}

        logger.info(f"\n{'='*70}")
        logger.info(f"🎉 Multi-season import complete")
        logger.info(f"{'='*70}")
        logger.info(f"   Total records imported: {summary['total_records']:,}")
        logger.info(f"   Seasons processed: {len([s for s in summary['seasons'].values() if s['status'] == 'success'])}/{len(seasons)}")
        logger.info(f"{'='*70}\n")

        return summary


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Import PlayerProfiler game log data')
    parser.add_argument('--season', type=int, help='Single season to import')
    parser.add_argument('--seasons', nargs='+', type=int,
                       help='Multiple seasons to import (e.g., --seasons 2024 2025)')
    parser.add_argument('--all', action='store_true',
                       help='Import all available seasons (2020-2025)')
    parser.add_argument('--base-path',
                       default='/Users/vato/work/Bet-That/storage/imports/PlayerProfiler/Game Log',
                       help='Base path to game log CSV files')

    args = parser.parse_args()

    # Initialize database
    db = DatabaseManager()
    db.connect()
    importer = GameLogImporter(db)

    base_path = Path(args.base_path)

    try:
        if args.all:
            # Import all seasons 2020-2025
            seasons = [2020, 2021, 2022, 2023, 2024, 2025]
            summary = importer.import_multiple_seasons(seasons, base_path)
            logger.info(f"\n✅ Imported {summary['total_records']} total records")
            return 0

        elif args.seasons:
            # Import multiple specified seasons
            summary = importer.import_multiple_seasons(args.seasons, base_path)
            logger.info(f"\n✅ Imported {summary['total_records']} total records")
            return 0

        elif args.season:
            # Import single season
            csv_path = base_path / f'{args.season}-Advanced-Gamelog.csv'
            count = importer.import_season(args.season, csv_path)
            logger.info(f"\n✅ Imported {count} records for {args.season} season")
            return 0

        else:
            parser.print_help()
            return 1

    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    exit(main())
