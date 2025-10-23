"""
Optimize database with indexes and cleanup
Improves query performance for common access patterns
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def optimize_database(db_path='data/database/nfl_betting.db'):
    """
    Add indexes and optimize database

    Args:
        db_path: Path to database file
    """
    logger.info(f"\n{'='*60}")
    logger.info("Database Optimization")
    logger.info(f"{'='*60}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing indexes
    logger.info("Checking existing indexes...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing_indexes = [row[0] for row in cursor.fetchall()]
    logger.info(f"Found {len(existing_indexes)} existing indexes")

    # Indexes to create
    indexes = [
        # Matchups table indexes
        ("idx_matchups_week", "CREATE INDEX IF NOT EXISTS idx_matchups_week ON matchups(week)"),
        ("idx_matchups_teams", "CREATE INDEX IF NOT EXISTS idx_matchups_teams ON matchups(home_team, away_team)"),
        ("idx_matchups_date", "CREATE INDEX IF NOT EXISTS idx_matchups_date ON matchups(game_date)"),

        # Common query patterns - add more as needed based on your queries
        # Example: If you frequently query by team name
        ("idx_matchups_home_team", "CREATE INDEX IF NOT EXISTS idx_matchups_home_team ON matchups(home_team)"),
        ("idx_matchups_away_team", "CREATE INDEX IF NOT EXISTS idx_matchups_away_team ON matchups(away_team)"),
    ]

    created_count = 0
    skipped_count = 0

    for index_name, create_sql in indexes:
        if index_name in existing_indexes:
            logger.info(f"  ⊘ Skipping {index_name} (already exists)")
            skipped_count += 1
        else:
            try:
                cursor.execute(create_sql)
                logger.info(f"  ✓ Created {index_name}")
                created_count += 1
            except Exception as e:
                logger.error(f"  ✗ Failed to create {index_name}: {e}")

    # Analyze tables to update statistics
    logger.info("\nAnalyzing tables to update statistics...")
    cursor.execute("ANALYZE")
    logger.info("  ✓ Analysis complete")

    # Vacuum to reclaim space and defragment
    logger.info("\nVacuuming database...")
    cursor.execute("VACUUM")
    logger.info("  ✓ Vacuum complete")

    conn.commit()
    conn.close()

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("Optimization Summary")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Created {created_count} new indexes")
    logger.info(f"⊘ Skipped {skipped_count} existing indexes")
    logger.info(f"✓ Database analyzed and vacuumed")
    logger.info(f"{'='*60}\n")

    # Show database stats
    db_size = Path(db_path).stat().st_size / 1024 / 1024  # MB
    logger.info(f"Database size: {db_size:.2f} MB")


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/database/nfl_betting.db'
    optimize_database(db_path)
