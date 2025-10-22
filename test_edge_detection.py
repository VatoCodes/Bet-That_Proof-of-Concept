# test_edge_detection.py
import pandas as pd
from datetime import datetime
from pathlib import Path
from utils.week_manager import WeekManager

# Initialize week manager
wm = WeekManager()
current_week = wm.get_current_week()
week_info = wm.get_week_info()

print("=" * 60)
print("NFL EDGE FINDER — QUICK TEST")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Testing Week: {current_week} ({week_info['status']})")
print("=" * 60)

# Load your existing CSVs using current week
print(f"\n📂 Loading data from data/raw/ (Week {current_week})...")
data_dir = Path('data/raw')

# Try to load files for current week, with fallback to any available week
def load_csv_with_fallback(pattern: str, week: int) -> pd.DataFrame:
    """Load CSV for specific week, falling back to latest available if not found"""
    filepath = data_dir / pattern.format(week=week)

    if filepath.exists():
        print(f"  ✓ Found: {filepath.name}")
        return pd.read_csv(filepath)

    # Fallback: find any week file
    import glob
    fallback_pattern = pattern.replace('week_{week}', 'week_*')
    matches = sorted(glob.glob(str(data_dir / fallback_pattern)))

    if matches:
        fallback_file = Path(matches[-1])  # Get most recent
        print(f"  ⚠️  Using fallback: {fallback_file.name} (Week {current_week} data not found)")
        return pd.read_csv(fallback_file)

    raise FileNotFoundError(f"No data found for pattern: {pattern}")

try:
    defense = load_csv_with_fallback('defense_stats_week_{week}.csv', current_week)
    qb_stats = pd.read_csv(data_dir / 'qb_stats_2025.csv')
    print(f"  ✓ Found: qb_stats_2025.csv")
    matchups = load_csv_with_fallback('matchups_week_{week}.csv', current_week)
    odds = load_csv_with_fallback('odds_qb_td_week_{week}.csv', current_week)
except FileNotFoundError as e:
    print(f"\n❌ ERROR: {e}")
    print("\nRun the scraper first:")
    print(f"  python main.py --week {current_week}")
    exit(1)

print(f"✅ Defense stats: {len(defense)} teams")
print(f"✅ QB stats: {len(qb_stats)} QBs")
print(f"✅ Matchups: {len(matchups)} games")
print(f"✅ Odds: {len(odds)} QB props")

# Find weak defenses (1.7+ TDs/game)
print("\n🎯 Finding weak pass defenses (1.7+ TDs/game)...")
weak_defenses = defense[defense['tds_per_game'] >= 1.7].sort_values('tds_per_game', ascending=False)
print(f"Found {len(weak_defenses)} weak defenses:\n")
for _, team in weak_defenses.iterrows():
    print(f"  • {team['team_name']}: {team['tds_per_game']:.1f} TDs/game")

# If you have odds data, calculate sample edges using real EdgeCalculator
if len(odds) > 0:
    print("\n💰 Sample edge calculations:")
    
    # Import EdgeCalculator
    try:
        from utils.edge_calculator import EdgeCalculator
        calculator = EdgeCalculator(model_version="v1")
        
        for _, prop in odds.head(3).iterrows():
            qb_name = prop['qb_name']
            odds_value = prop['odds_over_05_td']
            
            # Find QB stats
            qb_row = qb_stats[qb_stats['qb_name'] == qb_name]
            if qb_row.empty:
                print(f"\n  {qb_name}: QB stats not found")
                continue
            
            # Find opponent defense (simplified - would need matchup data for accuracy)
            # For demo, use worst defense from our weak defenses list
            if len(weak_defenses) > 0:
                worst_defense = weak_defenses.iloc[0]
                opponent = worst_defense['team_name']
                def_row = defense_stats[defense_stats['team_name'] == opponent]
            else:
                print(f"\n  {qb_name}: No defense data available")
                continue
            
            if def_row.empty:
                print(f"\n  {qb_name}: Defense stats not found")
                continue
            
            # Calculate edge using real calculator
            try:
                edge_result = calculator.calculate_edge_from_csv(
                    qb_name=qb_name,
                    opponent=opponent,
                    odds=odds_value,
                    qb_stats_df=qb_stats,
                    defense_stats_df=defense_stats,
                    matchup_context={'is_home': True}  # Assume home for demo
                )
                
                true_prob = edge_result['true_probability'] * 100
                implied_prob = edge_result['implied_probability'] * 100
                edge_pct = edge_result['edge_percentage']
                tier = edge_result['bet_recommendation']['tier']
                
                print(f"\n  {qb_name} vs {opponent}:")
                print(f"    Odds: {odds_value} → Implied: {implied_prob:.1f}%")
                print(f"    True Prob: {true_prob:.1f}% (confidence: {edge_result['confidence']})")
                print(f"    Edge: {edge_pct:+.1f}%")
                print(f"    Tier: {tier}")
                
                if edge_pct >= 10:
                    print(f"    ⭐ POTENTIAL EDGE!")
                elif edge_pct >= 5:
                    print(f"    📈 Small edge")
                else:
                    print(f"    ❌ No edge")
                    
            except Exception as e:
                print(f"\n  {qb_name}: Error calculating edge - {e}")
                
    except ImportError as e:
        print(f"\n⚠️  EdgeCalculator not available: {e}")
        print("Using placeholder calculations...")
        
        # Fallback to placeholder
        for _, prop in odds.head(3).iterrows():
            qb_name = prop['qb_name']
            odds_value = prop['odds_over_05_td']

            # Calculate implied probability
            if odds_value < 0:
                implied_prob = (-odds_value) / ((-odds_value) + 100) * 100
            else:
                implied_prob = 100 / (odds_value + 100) * 100

            # Placeholder true probability
            true_prob = 90.0
            edge = true_prob - implied_prob

            print(f"\n  {qb_name}:")
            print(f"    Odds: {odds_value} → Implied: {implied_prob:.1f}%")
            print(f"    True Prob: {true_prob:.1f}% (placeholder)")
            print(f"    Edge: {edge:+.1f}%")
            if edge >= 10:
                print(f"    ⭐ POTENTIAL EDGE!")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
