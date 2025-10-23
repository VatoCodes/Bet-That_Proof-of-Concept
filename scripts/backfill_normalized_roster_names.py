#!/usr/bin/env python3
"""Backfill Normalized Player Names in player_roster Table

This script updates existing player_roster records to use normalized names,
removing suffixes like Jr., II, III and extra spaces.

This completes the name normalization across all tables to ensure consistency.

Usage:
    python3 scripts/backfill_normalized_roster_names.py --dry-run  # Preview changes
    python3 scripts/backfill_normalized_roster_names.py           # Apply changes
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

    # Get all unique player names from player_roster
    cursor.execute("""
        SELECT DISTINCT player_name
        FROM player_roster
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
        FROM player_roster
        WHERE player_name = ?
    """, (original_name,))

    return cursor.fetchone()[0]


def backfill_normalized_names(conn, dry_run=True):
    """
    Update player_roster table with normalized names

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
    print(f"🔍 Player Roster Name Normalization Analysis")
    print(f"{'='*70}\n")

    print(f"Found {len(changes)} player names that need normalization:\n")

    # Group by position for better visibility
    cursor = conn.cursor()
    qb_changes = {}
    other_changes = {}

    for original, normalized in changes.items():
        cursor.execute("""
            SELECT DISTINCT position
            FROM player_roster
            WHERE player_name = ?
            LIMIT 1
        """, (original,))

        result = cursor.fetchone()
        position = result[0] if result else 'Unknown'

        if position == 'QB':
            qb_changes[original] = normalized
        else:
            other_changes[original] = normalized

    total_records = 0

    if qb_changes:
        print(f"📊 QB Names ({len(qb_changes)}):")
        for original, normalized in sorted(qb_changes.items()):
            count = count_affected_records(conn, original)
            total_records += count
            print(f"  '{original}' -> '{normalized}' ({count} records)")
        print()

    if other_changes:
        print(f"📊 Other Positions ({len(other_changes)}):")
        for original, normalized in sorted(other_changes.items()):
            count = count_affected_records(conn, original)
            total_records += count
            print(f"  '{original}' -> '{normalized}' ({count} records)")
        print()

    print(f"{'='*70}")
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
            UPDATE player_roster
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


def verify_consistency(conn):
    """
    Verify that game_log and roster now have matching names
    """
    cursor = conn.cursor()

    print("\n{'='*70}")
    print("🔍 Verifying Cross-Table Name Consistency")
    print(f"{'='*70}\n")

    # Check for remaining orphan QBs
    cursor.execute("""
        SELECT DISTINCT gl.player_name, gl.season, gl.week
        FROM player_game_log gl
        LEFT JOIN player_roster pr
          ON gl.player_name = pr.player_name
          AND gl.season = pr.season
          AND gl.week = pr.week
        WHERE pr.player_name IS NULL
        ORDER BY gl.season, gl.week, gl.player_name
        LIMIT 10
    """)

    orphans = cursor.fetchall()

    if orphans:
        print(f"⚠️  Found {len(orphans)} orphan QBs (game_log not in roster):")
        for player, season, week in orphans:
            print(f"  - {player} (Season {season}, Week {week})")
        print("\nThese are likely backup QBs not in the starting roster.\n")
    else:
        print("✅ No orphan QBs found - perfect consistency!\n")

    return len(orphans) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Backfill normalized player names in player_roster table'
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
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify consistency after update'
    )

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        return 1

    print(f"\n{'='*70}")
    print(f"Player Roster Name Normalization Tool")
    print(f"{'='*70}")
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'LIVE (will apply changes)'}")
    print(f"{'='*70}\n")

    try:
        conn = get_db_connection(args.db)

        # Run backfill
        result = backfill_normalized_names(conn, dry_run=args.dry_run)

        # If changes were applied or verify flag set, check consistency
        if (not result['dry_run'] and result['total_records_updated'] > 0) or args.verify:
            verify_consistency(conn)

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
