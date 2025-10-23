#!/usr/bin/env python3
"""Backfill Normalized Player Names in player_game_log Table

This script updates existing player_game_log records to use normalized names,
removing suffixes like Jr., II, III and extra spaces.

This ensures consistency with newly imported data and fixes orphan QB issues.

Usage:
    python3 scripts/backfill_normalized_names.py --dry-run  # Preview changes
    python3 scripts/backfill_normalized_names.py           # Apply changes
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.name_normalizer import normalize_player_name


def get_db_connection(db_path='data/database/nfl_betting.db'):
    """Get database connection"""
    return sqlite3.connect(db_path)


def analyze_name_changes(conn):
    """
    Analyze which names will change after normalization

    Returns:
        dict: Mapping of original_name -> normalized_name
    """
    cursor = conn.cursor()

    # Get all unique player names from player_game_log
    cursor.execute("""
        SELECT DISTINCT player_name
        FROM player_game_log
        ORDER BY player_name
    """)

    names = [row[0] for row in cursor.fetchall()]

    # Build mapping of changes
    changes = {}
    for name in names:
        normalized = normalize_player_name(name)
        if name != normalized:
            changes[name] = normalized

    return changes


def count_affected_records(conn, original_name):
    """Count how many records will be affected by a name change"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM player_game_log
        WHERE player_name = ?
    """, (original_name,))

    return cursor.fetchone()[0]


def backfill_normalized_names(conn, dry_run=True):
    """
    Update player_game_log table with normalized names

    Args:
        conn: Database connection
        dry_run: If True, only preview changes without applying them

    Returns:
        dict: Summary of changes
    """
    changes = analyze_name_changes(conn)

    if not changes:
        print("✅ No name normalization needed - all names are already normalized!")
        return {'total_names_changed': 0, 'total_records_updated': 0, 'changes': {}}

    print(f"\n{'='*70}")
    print(f"🔍 Name Normalization Analysis")
    print(f"{'='*70}\n")

    print(f"Found {len(changes)} player names that need normalization:\n")

    total_records = 0
    for original, normalized in sorted(changes.items()):
        count = count_affected_records(conn, original)
        total_records += count
        print(f"  '{original}' -> '{normalized}' ({count} records)")

    print(f"\n{'='*70}")
    print(f"Total: {len(changes)} names, {total_records} records to update")
    print(f"{'='*70}\n")

    if dry_run:
        print("🔒 DRY RUN MODE - No changes applied")
        print("Run without --dry-run to apply changes\n")
        return {
            'total_names_changed': 0,
            'total_records_updated': 0,
            'changes': changes,
            'dry_run': True
        }

    # Apply changes
    print("🔄 Applying name normalization...\n")

    cursor = conn.cursor()
    updated_count = 0

    for original, normalized in changes.items():
        cursor.execute("""
            UPDATE player_game_log
            SET player_name = ?
            WHERE player_name = ?
        """, (normalized, original))

        rows_updated = cursor.rowcount
        updated_count += rows_updated
        print(f"  ✓ Updated {rows_updated} records: '{original}' -> '{normalized}'")

    conn.commit()

    print(f"\n{'='*70}")
    print(f"✅ Normalization complete!")
    print(f"{'='*70}")
    print(f"  Names changed: {len(changes)}")
    print(f"  Records updated: {updated_count}")
    print(f"{'='*70}\n")

    return {
        'total_names_changed': len(changes),
        'total_records_updated': updated_count,
        'changes': changes,
        'dry_run': False
    }


def verify_no_duplicates(conn):
    """
    Verify that normalization didn't create duplicate player_name entries
    for the same season/week combination
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT player_name, season, week, COUNT(*) as count
        FROM player_game_log
        GROUP BY player_name, season, week
        HAVING count > 1
    """)

    duplicates = cursor.fetchall()

    if duplicates:
        print(f"\n⚠️  WARNING: Found {len(duplicates)} duplicate entries after normalization:")
        for player, season, week, count in duplicates:
            print(f"  - {player} (Season {season}, Week {week}): {count} records")
        print("\nThis may indicate that both 'Name' and 'Name Jr.' existed for the same week.")
        print("Manual review recommended.\n")
        return False
    else:
        print("✅ No duplicates detected - normalization successful!\n")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Backfill normalized player names in player_game_log table'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    parser.add_argument(
        '--db',
        default='data/database/nfl_betting.db',
        help='Path to database file'
    )

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        return 1

    print(f"\n{'='*70}")
    print(f"Name Normalization Backfill Tool")
    print(f"{'='*70}")
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'LIVE (will apply changes)'}")
    print(f"{'='*70}\n")

    try:
        conn = get_db_connection(args.db)

        # Run backfill
        result = backfill_normalized_names(conn, dry_run=args.dry_run)

        # If changes were applied, verify no duplicates
        if not result['dry_run'] and result['total_records_updated'] > 0:
            verify_no_duplicates(conn)

        conn.close()

        if args.dry_run and result.get('changes'):
            print("Next step: Run without --dry-run to apply these changes\n")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
