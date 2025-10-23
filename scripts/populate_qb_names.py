#!/usr/bin/env python3
"""
Populate qb_name in play_by_play table using player_roster data

This script fixes the CRITICAL data gap where qb_name is missing from play_by_play.
It joins play_by_play.qb_id with player_roster.player_id to get player names.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager

def populate_qb_names(db_path='data/database/nfl_betting.db'):
    """
    Populate qb_name column in play_by_play using player_roster lookup

    Args:
        db_path: Path to database

    Returns:
        dict: Summary of updates
    """
    print("\n" + "="*70)
    print("🔧 Populating QB Names in Play-by-Play Data")
    print("="*70 + "\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Check current state
    print("📊 Checking current data quality...\n")

    cursor.execute("SELECT COUNT(*) FROM play_by_play")
    total_plays = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM play_by_play WHERE qb_name IS NOT NULL AND qb_name != ''")
    qb_name_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM play_by_play WHERE qb_id IS NOT NULL AND qb_id != ''")
    has_qb_id = cursor.fetchone()[0]

    print(f"   Total plays: {total_plays:,}")
    print(f"   Plays with qb_name BEFORE: {qb_name_before:,} ({qb_name_before/total_plays*100:.1f}%)")
    print(f"   Plays with qb_id: {has_qb_id:,} ({has_qb_id/total_plays*100:.1f}%)")
    print()

    # Step 2: Update qb_name using player_roster lookup
    print("🔄 Updating qb_name from player_roster...\n")

    update_query = """
    UPDATE play_by_play
    SET qb_name = (
        SELECT player_roster.player_name
        FROM player_roster
        WHERE player_roster.player_id = play_by_play.qb_id
          AND player_roster.position = 'QB'
          AND player_roster.week = play_by_play.week
          AND player_roster.season = play_by_play.season
        LIMIT 1
    )
    WHERE play_by_play.qb_id IS NOT NULL
      AND play_by_play.qb_id != ''
      AND (play_by_play.qb_name IS NULL OR play_by_play.qb_name = '')
    """

    cursor.execute(update_query)
    updated_count = cursor.rowcount
    conn.commit()

    print(f"   Updated {updated_count:,} records")
    print()

    # Step 3: Check results
    print("✅ Verifying results...\n")

    cursor.execute("SELECT COUNT(*) FROM play_by_play WHERE qb_name IS NOT NULL AND qb_name != ''")
    qb_name_after = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM play_by_play
        WHERE qb_id IS NOT NULL
          AND qb_id != ''
          AND (qb_name IS NULL OR qb_name = '')
    """)
    unmatched = cursor.fetchone()[0]

    print(f"   Plays with qb_name AFTER: {qb_name_after:,} ({qb_name_after/total_plays*100:.1f}%)")
    print(f"   Improvement: +{qb_name_after - qb_name_before:,} records")
    print(f"   Unmatched qb_id entries: {unmatched:,}")
    print()

    # Step 4: Sample results
    print("📋 Sample updated records:\n")

    cursor.execute("""
        SELECT qb_id, qb_name, offense, week, play_type
        FROM play_by_play
        WHERE qb_name IS NOT NULL AND qb_name != ''
        LIMIT 10
    """)

    for row in cursor.fetchall():
        qb_id, qb_name, offense, week, play_type = row
        print(f"   {qb_id} → {qb_name:20s} | {offense:3s} Week {week} ({play_type})")

    print()

    # Step 5: Check for common unmatched QBs (debugging)
    if unmatched > 0:
        print("⚠️  Most common unmatched qb_id values:\n")

        cursor.execute("""
            SELECT qb_id, COUNT(*) as cnt
            FROM play_by_play
            WHERE qb_id IS NOT NULL
              AND qb_id != ''
              AND (qb_name IS NULL OR qb_name = '')
            GROUP BY qb_id
            ORDER BY cnt DESC
            LIMIT 5
        """)

        for row in cursor.fetchall():
            qb_id, count = row
            # Try to find in roster without week/season match
            cursor.execute("""
                SELECT player_name, team, week
                FROM player_roster
                WHERE player_id = ?
                  AND position = 'QB'
                LIMIT 1
            """, (qb_id,))

            roster_info = cursor.fetchone()
            if roster_info:
                name, team, week = roster_info
                print(f"   {qb_id}: {count:,} plays (Found in roster: {name} - {team} Week {week})")
            else:
                print(f"   {qb_id}: {count:,} plays (NOT in roster)")
        print()

    conn.close()

    summary = {
        'total_plays': total_plays,
        'qb_name_before': qb_name_before,
        'qb_name_after': qb_name_after,
        'updated_count': updated_count,
        'unmatched': unmatched,
        'success_rate': (qb_name_after / total_plays * 100) if total_plays > 0 else 0
    }

    print("="*70)
    print("🎉 QB Name Population Complete!")
    print("="*70)
    print(f"   Success rate: {summary['success_rate']:.1f}%")
    print(f"   Records updated: {updated_count:,}")
    print("="*70 + "\n")

    return summary


if __name__ == '__main__':
    try:
        summary = populate_qb_names()
        exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
