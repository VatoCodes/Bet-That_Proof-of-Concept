#!/usr/bin/env python3
"""
Test red zone TD rate calculation to verify SQL fixes

This tests the _calculate_red_zone_td_rate function directly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2

def test_red_zone_calculation():
    """Test red zone TD rate calculation for known QBs"""

    print("\n" + "="*70)
    print("🧪 Testing Red Zone TD Rate Calculation")
    print("="*70 + "\n")

    # Initialize
    db = DatabaseManager()
    db.connect()
    v2_calc = QBTDCalculatorV2(db)

    # Get some QBs to test (from game log table)
    conn = db._get_connection()
    import pandas as pd

    # Find QBs with red zone passes (from game log)
    query = """
        SELECT
            player_name as qb_name,
            season,
            SUM(red_zone_passes) as total_rz_passes,
            SUM(passing_touchdowns) as total_tds,
            COUNT(DISTINCT week) as weeks
        FROM player_game_log
        WHERE red_zone_passes > 0
        GROUP BY player_name, season
        ORDER BY total_rz_passes DESC
        LIMIT 10
    """

    qbs_with_rz_plays = pd.read_sql_query(query, conn)

    print(f"📊 Found {len(qbs_with_rz_plays)} QBs with red zone passes:\n")

    for _, row in qbs_with_rz_plays.iterrows():
        qb_name = row['qb_name']
        season = row['season']
        rz_passes = row['total_rz_passes']
        total_tds = row['total_tds']
        weeks = row['weeks']

        print(f"   {qb_name:20s} | Season {season} | {rz_passes} RZ passes, {total_tds} TDs over {weeks} weeks")

        # Test the calculation (using last 4 weeks)
        try:
            rz_td_rate = v2_calc._calculate_red_zone_td_rate(qb_name, season, weeks_back=4)
            print(f"      → Red Zone TD Rate (last 4 weeks): {rz_td_rate:.3f} ({rz_td_rate*100:.1f}%)")
        except Exception as e:
            print(f"      → ERROR: {e}")
            import traceback
            traceback.print_exc()

        print()

    # Manual verification query (from game log)
    print("🔍 Manual Verification - Sample Red Zone Data from Game Log:\n")

    verify_query = """
        SELECT
            player_name,
            season,
            SUM(passing_touchdowns) as total_tds,
            SUM(red_zone_passes) as total_rz_passes,
            ROUND(100.0 * SUM(passing_touchdowns) / SUM(red_zone_passes), 1) as td_pct
        FROM player_game_log
        WHERE red_zone_passes > 0
        GROUP BY player_name, season
        ORDER BY total_rz_passes DESC
        LIMIT 10
    """

    verification = pd.read_sql_query(verify_query, conn)

    for _, row in verification.iterrows():
        qb = row['player_name']
        season = row['season']
        tds = row['total_tds']
        rz_passes = row['total_rz_passes']
        pct = row['td_pct']

        print(f"   {qb:20s} | Season {season} | {tds}/{rz_passes} TDs ({pct}%)")

    db.close()

    print()
    print("="*70)
    print("🎉 Red Zone Calculation Test Complete")
    print("="*70 + "\n")

    return len(qbs_with_rz_plays) > 0


if __name__ == '__main__':
    try:
        success = test_red_zone_calculation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
