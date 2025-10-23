#!/usr/bin/env python3
"""
Test v2 QB TD Calculator to verify it produces different edges than v1

This validates that the data quality fixes enable v2 differentiation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2
from config import get_current_week

def test_v2_calculator():
    """Test v2 calculator with current week data"""

    print("\n" + "="*70)
    print("🧪 Testing v2 QB TD Calculator")
    print("="*70 + "\n")

    # Initialize
    db = DatabaseManager()
    db.connect()
    v2_calc = QBTDCalculatorV2(db)

    current_week = get_current_week()
    season = 2025

    print(f"📅 Testing Week {current_week}, Season {season}\n")

    # Test v2 calculator
    print("🔬 Running v2 edge calculation...\n")
    v2_edges = v2_calc.calculate_edges(
        week=current_week,
        season=season,
        min_edge_threshold=0.0  # Get all edges to compare
    )

    print(f"✅ v2 Calculator Results:")
    print(f"   Total edges found: {len(v2_edges)}")
    print()

    if len(v2_edges) > 0:
        # Show top 5 edges
        print("📊 Top 5 v2 Edges:\n")
        for i, edge in enumerate(v2_edges[:5], 1):
            qb = edge.get('qb_name', 'Unknown')
            opponent = edge.get('opponent', 'Unknown')
            v1_prob = edge.get('v1_probability', 0)
            v2_prob = edge.get('v2_probability', 0)
            v2_edge = edge.get('edge_percentage', 0)
            line = edge.get('line', 0.5)

            print(f"   {i}. {qb:20s} vs {opponent:3s}")
            print(f"      v1 prob: {v1_prob:.3f} | v2 prob: {v2_prob:.3f}")
            print(f"      v2 edge: {v2_edge:+.1f}% | Line: {line}")
            print(f"      v2 adjustments: {edge.get('v2_adjustments', {})}")
            print()

        # Check if v1 and v2 are different
        same_count = sum(1 for e in v2_edges if abs(e.get('v1_probability', 0) - e.get('v2_probability', 0)) < 0.001)
        different_count = len(v2_edges) - same_count

        print(f"📈 v1/v2 Comparison:")
        print(f"   Edges where v2 = v1: {same_count}")
        print(f"   Edges where v2 ≠ v1: {different_count}")
        print()

        if different_count > 0:
            print("✅ SUCCESS: v2 is producing different probabilities than v1!")
            print("   The data quality fixes are working!")
        else:
            print("⚠️  WARNING: v2 still equals v1 for all edges")
            print("   Additional investigation needed")

        # Show a sample edge with details
        if different_count > 0:
            diff_edge = next((e for e in v2_edges if abs(e.get('v1_probability', 0) - e.get('v2_probability', 0)) >= 0.001), None)
            if diff_edge:
                print(f"\n📝 Sample Edge with v2 Differentiation:")
                print(f"   QB: {diff_edge.get('qb_name')}")
                print(f"   Opponent: {diff_edge.get('opponent')}")
                print(f"   v1 probability: {diff_edge.get('v1_probability'):.4f}")
                print(f"   v2 probability: {diff_edge.get('v2_probability'):.4f}")
                print(f"   Difference: {abs(diff_edge.get('v1_probability', 0) - diff_edge.get('v2_probability', 0)):.4f}")
                print(f"   v2 adjustments applied: {diff_edge.get('v2_adjustments')}")
                print()
    else:
        print("⚠️  No edges found for this week")
        print("   This may be expected if no games are scheduled or props aren't available")
        print()

    db.close()

    print("="*70)
    print("🎉 v2 Calculator Test Complete")
    print("="*70 + "\n")

    return len(v2_edges) > 0 and different_count > 0


if __name__ == '__main__':
    try:
        success = test_v2_calculator()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
