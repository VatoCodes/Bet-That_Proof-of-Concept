"""
Backfill all missing weeks with historical data
Loads from hardcoded schedule and populates database
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.matchups_loader import MatchupsLoader
from utils.data_quality_validator import DataQualityValidator
import sqlite3
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backfill_week(week: int, db_path='data/database/nfl_betting.db'):
    """
    Backfill data for a single week from hardcoded schedule

    Args:
        week: NFL week number (1-18)
        db_path: Path to database

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Backfilling Week {week}")
    logger.info(f"{'='*60}")

    try:
        # Load matchups from hardcoded schedule
        loader = MatchupsLoader()
        matchups = loader.get_week_matchups(week)

        if not matchups:
            logger.error(f"No matchups found for week {week}")
            return False

        logger.info(f"Found {len(matchups)} matchups in schedule")

        # Connect to database
        conn = sqlite3.connect(db_path)

        # Check if week already has data
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM matchups WHERE week = ?",
            (week,)
        ).fetchone()[0]

        if existing_count >= 12:
            logger.info(f"Week {week} already has {existing_count} matchups, skipping")
            conn.close()
            return True

        # Clear existing incomplete data
        if existing_count > 0:
            conn.execute("DELETE FROM matchups WHERE week = ?", (week,))
            logger.info(f"Cleared {existing_count} incomplete matchups")

        # Prepare data for insertion
        df = pd.DataFrame(matchups)
        # Keep only columns that exist in database
        df_db = df[['home_team', 'away_team', 'game_date', 'week']].copy()
        df_db['scraped_at'] = datetime.now().isoformat()

        # Insert into database
        df_db.to_sql('matchups', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✓ Inserted {len(df_db)} matchups for week {week}")

        # Validate
        validator = DataQualityValidator(db_path)
        is_valid, issues = validator.validate_week(week)

        if not is_valid:
            logger.warning(f"Week {week} validation failed: {issues}")
        else:
            logger.info(f"✓ Week {week} validation passed")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to backfill week {week}: {e}")
        return False


def backfill_all_missing(db_path='data/database/nfl_betting.db'):
    """Find and backfill all missing weeks"""

    logger.info(f"\n{'='*60}")
    logger.info("Backfilling All Missing Weeks")
    logger.info(f"{'='*60}\n")

    # Find which weeks need data
    validator = DataQualityValidator(db_path)
    all_issues = validator.validate_all_weeks()

    missing_weeks = sorted(all_issues.keys())

    if not missing_weeks:
        logger.info("✓ No missing weeks found - all data complete!")
        return

    logger.info(f"Found {len(missing_weeks)} weeks with missing/incomplete data:")
    logger.info(f"Weeks: {missing_weeks}\n")

    # Backfill all missing weeks
    success_count = 0
    failed_weeks = []

    for week in missing_weeks:
        if backfill_week(week, db_path):
            success_count += 1
        else:
            failed_weeks.append(week)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("Backfill Summary")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Success: {success_count}/{len(missing_weeks)} weeks")
    if failed_weeks:
        logger.info(f"✗ Failed:  {failed_weeks}")
    logger.info(f"{'='*60}\n")

    # Final validation
    logger.info("Running final validation...")
    validator = DataQualityValidator(db_path)
    final_issues = validator.validate_all_weeks()

    if not final_issues:
        logger.info("✓ All weeks now have complete data!")
    else:
        logger.warning(f"⚠ {len(final_issues)} weeks still have issues:")
        for week, issues in sorted(final_issues.items()):
            logger.warning(f"  Week {week}: {issues}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Backfill missing NFL matchup data')
    parser.add_argument('--week', type=int, help='Backfill specific week')
    parser.add_argument('--all', action='store_true', help='Backfill all missing weeks')
    parser.add_argument('--db', default='data/database/nfl_betting.db', help='Database path')

    args = parser.parse_args()

    if args.week:
        success = backfill_week(args.week, args.db)
        sys.exit(0 if success else 1)
    elif args.all:
        backfill_all_missing(args.db)
    else:
        parser.print_help()
