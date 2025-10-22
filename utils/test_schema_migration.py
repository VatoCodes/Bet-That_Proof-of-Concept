"""Test script for PlayerProfiler schema migration

This script validates that the 002 migration:
1. Creates all 5 new tables successfully
2. Creates all 20+ indexes
3. Maintains backward compatibility with existing tables
4. Has proper UNIQUE constraints on natural keys
"""

import sqlite3
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def validate_schema(db_path='data/database/nfl_betting.db'):
    """
    Validate schema migration

    Args:
        db_path: Path to database file

    Returns:
        bool: True if all validations pass
    """
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATING PLAYERPROFILE SCHEMA MIGRATION (002)")
    logger.info("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    all_passed = True

    # Test 1: Check all 5 new tables exist
    logger.info("\n✓ Test 1: Checking new tables exist...")
    expected_tables = ['play_by_play', 'team_metrics', 'kicker_stats', 'qb_stats_enhanced', 'player_roster']
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]

    for table in expected_tables:
        if table in existing_tables:
            logger.info(f"  ✅ Table '{table}' exists")
        else:
            logger.error(f"  ❌ Table '{table}' MISSING")
            all_passed = False

    # Test 2: Check indexes exist (includes both explicit and autoindexes from UNIQUE constraints)
    logger.info("\n✓ Test 2: Checking indexes...")
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index'
        AND (name LIKE 'idx_%' OR name LIKE 'sqlite_autoindex_%')
        AND (name LIKE '%pbp%' OR name LIKE '%team_metrics%' OR name LIKE '%kicker%'
             OR name LIKE '%qb_enhanced%' OR name LIKE '%roster%'
             OR name LIKE '%kicker_stats%' OR name LIKE '%player_roster%' OR name LIKE '%qb_stats_enhanced%')
    """)
    indexes = [row[0] for row in cursor.fetchall()]

    if len(indexes) >= 20:
        logger.info(f"  ✅ {len(indexes)} indexes created (expected 20+, includes autoindexes from UNIQUE constraints)")
    else:
        logger.error(f"  ❌ Only {len(indexes)} indexes found (expected 20+)")
        all_passed = False

    # Test 3: Check UNIQUE constraints on natural keys
    logger.info("\n✓ Test 3: Checking UNIQUE constraints...")

    unique_constraints = {
        'play_by_play': 'play_id',
        'team_metrics': '(team_name, season, week)',
        'kicker_stats': '(kicker_name, team, season)',
        'qb_stats_enhanced': '(qb_name, team, season)',
        'player_roster': '(player_name, team, season, week)'
    }

    for table, constraint in unique_constraints.items():
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        result = cursor.fetchone()
        if result and 'UNIQUE' in result[0]:
            logger.info(f"  ✅ Table '{table}' has UNIQUE constraint")
        else:
            logger.error(f"  ❌ Table '{table}' missing UNIQUE constraint")
            all_passed = False

    # Test 4: Backward compatibility - existing tables still work
    logger.info("\n✓ Test 4: Checking backward compatibility...")

    existing_core_tables = ['defense_stats', 'qb_stats', 'matchups', 'odds_spreads', 'odds_totals', 'qb_props']

    for table in existing_core_tables:
        if table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"  ✅ Existing table '{table}' functional ({count} rows)")
        else:
            logger.error(f"  ❌ Existing table '{table}' NOT FOUND")
            all_passed = False

    # Test 5: Check specific critical columns exist
    logger.info("\n✓ Test 5: Checking critical columns...")

    critical_columns = {
        'team_metrics': ['offensive_yards_per_play', 'defensive_yards_per_play', 'first_half_points_avg'],
        'kicker_stats': ['points_per_game', 'fg_pct', 'points_per_game_percentile'],
        'qb_stats_enhanced': ['red_zone_accuracy_rating', 'deep_ball_completion_pct', 'clean_pocket_accuracy'],
        'player_roster': ['status', 'position']
    }

    for table, columns in critical_columns.items():
        cursor.execute(f"PRAGMA table_info({table})")
        table_columns = [col[1] for col in cursor.fetchall()]

        for col in columns:
            if col in table_columns:
                logger.info(f"  ✅ {table}.{col} exists")
            else:
                logger.error(f"  ❌ {table}.{col} MISSING")
                all_passed = False

    # Test 6: Check database file size (should be minimal with no data yet)
    logger.info("\n✓ Test 6: Checking database size...")
    db_path_obj = Path(db_path)
    if db_path_obj.exists():
        size_mb = db_path_obj.stat().st_size / (1024 * 1024)
        logger.info(f"  ℹ️  Database size: {size_mb:.2f} MB")

    conn.close()

    # Final summary
    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("✅ ALL VALIDATION TESTS PASSED")
        logger.info("=" * 70)
        logger.info("\nSchema migration 002 is valid and ready for data import.")
        logger.info("\nNext steps:")
        logger.info("  1. Run importers to populate tables with 2024 data")
        logger.info("  2. Run calculator tests to validate edge detection")
        logger.info("  3. Test dashboard integration")
        return True
    else:
        logger.error("❌ VALIDATION FAILED - SEE ERRORS ABOVE")
        logger.error("=" * 70)
        logger.error("\nPlease fix schema issues before proceeding.")
        logger.error("To rollback:")
        logger.error("  sqlite3 data/database/nfl_betting.db < utils/migrations/002_playerprofile_schema_rollback.sql")
        return False


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate PlayerProfiler schema migration')
    parser.add_argument('--db', default='data/database/nfl_betting.db',
                       help='Database path (default: data/database/nfl_betting.db)')
    parser.add_argument('--apply', action='store_true',
                       help='Apply migration before validation')

    args = parser.parse_args()

    if args.apply:
        logger.info("\n📥 Applying migration...")
        import subprocess
        result = subprocess.run(
            ['sqlite3', args.db, '.read utils/migrations/002_playerprofile_schema.sql'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("✅ Migration applied successfully")
        else:
            logger.error(f"❌ Migration failed: {result.stderr}")
            return 1

    # Run validation
    success = validate_schema(args.db)

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
