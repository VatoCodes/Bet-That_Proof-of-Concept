#!/usr/bin/env python3
"""
Phase 5: Production Testing & Go/No-Go Decision
Test v2 calculator with real Week 7 2025 matchups
"""

import pandas as pd
import numpy as np
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.edge_calculator import EdgeCalculator
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2


class ProductionTester:
    """Execute Phase 5 production testing"""

    def __init__(self, season: int = 2025, week: int = 7):
        self.season = season
        self.week = week
        self.db = DatabaseManager()
        self.calc_v1 = EdgeCalculator(self.db)
        self.calc_v2 = QBTDCalculatorV2(self.db)
        self.results = []

    def load_matchups(self) -> pd.DataFrame:
        """Load Week 7 matchup data"""
        matchup_file = f'data/raw/matchups_week_{self.week}.csv'

        print(f"\n{'='*70}")
        print(f"PHASE 5: PRODUCTION TESTING - Week {self.week} ({self.season} Season)")
        print(f"{'='*70}\n")

        try:
            matchups_raw = pd.read_csv(matchup_file)
            print(f"✅ Loaded {len(matchups_raw)} games from {matchup_file}")
        except FileNotFoundError:
            print(f"❌ Matchup file not found: {matchup_file}")
            sys.exit(1)

        # Get starting QBs for each team from database
        # We'll extract QBs from the most recent weeks
        qb_query = """
            SELECT DISTINCT
                pr.player_name,
                pr.team,
                pr.position
            FROM player_roster pr
            WHERE pr.season = ?
                AND pr.position = 'QB'
                AND pr.week = (
                    SELECT MAX(week) FROM player_roster
                    WHERE season = ? AND position = 'QB'
                )
            ORDER BY pr.team
        """

        conn = self.db.get_connection()
        qbs_df = pd.read_sql_query(qb_query, conn, params=(self.season, self.season))

        print(f"✅ Found {len(qbs_df)} QBs from roster data")

        # Create team abbreviation mapping
        team_abbrev_map = {
            'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
            'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
        }

        # Build matchup list with QBs
        matchups = []
        for _, game in matchups_raw.iterrows():
            home_team = game['home_team']
            away_team = game['away_team']

            home_abbrev = team_abbrev_map.get(home_team, home_team)
            away_abbrev = team_abbrev_map.get(away_team, away_team)

            # Find starting QBs for each team
            home_qbs = qbs_df[qbs_df['team'] == home_abbrev]
            away_qbs = qbs_df[qbs_df['team'] == away_abbrev]

            if len(home_qbs) > 0:
                home_qb = home_qbs.iloc[0]['player_name']  # Take first QB (starter)
                matchups.append({
                    'qb_name': home_qb,
                    'team': home_abbrev,
                    'opponent': away_abbrev,
                    'is_home': True
                })

            if len(away_qbs) > 0:
                away_qb = away_qbs.iloc[0]['player_name']
                matchups.append({
                    'qb_name': away_qb,
                    'team': away_abbrev,
                    'opponent': home_abbrev,
                    'is_home': False
                })

        matchups_df = pd.DataFrame(matchups)
        print(f"✅ Created {len(matchups_df)} QB matchups\n")

        return matchups_df

    def run_calculations(self, matchups: pd.DataFrame) -> List[Dict]:
        """Calculate v1 and v2 edges for all matchups"""
        print(f"{'='*70}")
        print(f"CALCULATING EDGES")
        print(f"{'='*70}\n")

        results = []

        for idx, matchup in matchups.iterrows():
            qb = matchup['qb_name']
            team = matchup['team']
            opp = matchup['opponent']

            print(f"[{idx+1}/{len(matchups)}] {qb:20} ({team}) @ {opp}")

            # Calculate v1
            start = time.time()
            try:
                edge_v1 = self.calc_v1.calculate_qb_td_edge(
                    player_name=qb,
                    opponent_abbrev=opp,
                    season=self.season,
                    week=self.week
                )
                v1_time = (time.time() - start) * 1000
                v1_error = None
                print(f"  v1: {edge_v1:+.4f} ({v1_time:.1f}ms)")
            except Exception as e:
                print(f"  v1: ❌ ERROR - {str(e)}")
                edge_v1 = None
                v1_time = 0
                v1_error = str(e)

            # Calculate v2
            start = time.time()
            try:
                edge_v2 = self.calc_v2.calculate_qb_td_edge(
                    player_name=qb,
                    opponent_abbrev=opp,
                    season=self.season,
                    week=self.week
                )
                v2_time = (time.time() - start) * 1000
                v2_meta = self.calc_v2.get_last_calculation_metadata()
                v2_error = None

                fallback_flag = " [FALLBACK]" if v2_meta.get('fallback_to_v1', False) else ""
                rz_td_rate = v2_meta.get('red_zone_td_rate', 0) or 0
                print(f"  v2: {edge_v2:+.4f} ({v2_time:.1f}ms) [RZ: {rz_td_rate:.1%}]{fallback_flag}")

            except Exception as e:
                print(f"  v2: ❌ ERROR - {str(e)}")
                edge_v2 = None
                v2_time = 0
                v2_meta = {}
                v2_error = str(e)

            # Comparison
            if edge_v1 is not None and edge_v2 is not None:
                diff = edge_v2 - edge_v1
                diff_pct = (diff / abs(edge_v1) * 100) if edge_v1 != 0 else 0
                agreement = self._classify_agreement(diff_pct)
                print(f"  Δ: {diff:+.4f} ({diff_pct:+.1f}%) - {agreement}\n")
            else:
                diff = None
                diff_pct = None
                agreement = 'ERROR'
                print(f"  Δ: N/A (error in calculation)\n")

            # Store result
            results.append({
                'qb_name': qb,
                'team': team,
                'opponent': opp,
                'is_home': matchup['is_home'],
                'v1_edge': edge_v1,
                'v1_time_ms': v1_time,
                'v1_error': v1_error,
                'v2_edge': edge_v2,
                'v2_time_ms': v2_time,
                'v2_metadata': v2_meta,
                'v2_error': v2_error,
                'difference': diff,
                'difference_pct': diff_pct,
                'agreement': agreement
            })

        self.results = results
        return results

    def _classify_agreement(self, diff_pct: float) -> str:
        """Classify agreement level between v1 and v2"""
        abs_diff = abs(diff_pct)
        if abs_diff < 5:
            return 'EXACT'
        elif abs_diff < 15:
            return 'CLOSE'
        elif abs_diff < 30:
            return 'MODERATE'
        else:
            return 'OUTLIER'

    def _classify_edge(self, edge: float) -> str:
        """Classify edge betting value"""
        if edge > 0.05:
            return "STRONG OVER"
        elif edge > 0.02:
            return "LEAN OVER"
        elif edge > -0.02:
            return "NEUTRAL"
        elif edge > -0.05:
            return "LEAN UNDER"
        else:
            return "STRONG UNDER"

    def analyze_results(self) -> Dict:
        """Analyze edge quality and performance"""
        print(f"\n{'='*70}")
        print("RESULTS ANALYSIS")
        print(f"{'='*70}\n")

        # Filter successful calculations
        v1_valid = [r for r in self.results if r['v1_edge'] is not None]
        v2_valid = [r for r in self.results if r['v2_edge'] is not None]
        both_valid = [r for r in self.results if r['v1_edge'] is not None and r['v2_edge'] is not None]

        v1_edges = [r['v1_edge'] for r in v1_valid]
        v2_edges = [r['v2_edge'] for r in v2_valid]
        v2_times = [r['v2_time_ms'] for r in v2_valid]

        # Error rates
        v1_error_rate = (len(self.results) - len(v1_valid)) / len(self.results) * 100
        v2_error_rate = (len(self.results) - len(v2_valid)) / len(self.results) * 100

        print(f"📊 Calculation Success:")
        print(f"  v1: {len(v1_valid)}/{len(self.results)} ({100-v1_error_rate:.1f}%)")
        print(f"  v2: {len(v2_valid)}/{len(self.results)} ({100-v2_error_rate:.1f}%)")

        # Performance metrics
        if v2_times:
            print(f"\n⚡ Performance (v2):")
            print(f"  Average: {np.mean(v2_times):.1f}ms")
            print(f"  Median: {np.median(v2_times):.1f}ms")
            print(f"  P95: {np.percentile(v2_times, 95):.1f}ms")
            print(f"  P99: {np.percentile(v2_times, 99):.1f}ms")
            print(f"  Max: {max(v2_times):.1f}ms")
            print(f"  Target: <500ms ✅" if np.percentile(v2_times, 95) < 500 else "  Target: <500ms ❌")

        # Edge statistics
        if v1_edges:
            print(f"\n📈 Edge Statistics (v1):")
            print(f"  Mean: {np.mean(v1_edges):+.4f}")
            print(f"  Median: {np.median(v1_edges):+.4f}")
            print(f"  Std Dev: {np.std(v1_edges):.4f}")
            print(f"  Range: [{min(v1_edges):+.4f}, {max(v1_edges):+.4f}]")

        if v2_edges:
            print(f"\n📈 Edge Statistics (v2):")
            print(f"  Mean: {np.mean(v2_edges):+.4f}")
            print(f"  Median: {np.median(v2_edges):+.4f}")
            print(f"  Std Dev: {np.std(v2_edges):.4f}")
            print(f"  Range: [{min(v2_edges):+.4f}, {max(v2_edges):+.4f}]")

        # Actionability
        if v1_edges:
            v1_actionable = sum(1 for e in v1_edges if abs(e) > 0.02)
            v1_actionable_pct = v1_actionable / len(v1_edges) * 100
        else:
            v1_actionable_pct = 0

        if v2_edges:
            v2_actionable = sum(1 for e in v2_edges if abs(e) > 0.02)
            v2_actionable_pct = v2_actionable / len(v2_edges) * 100
        else:
            v2_actionable_pct = 0

        print(f"\n🎯 Actionable Edges (>±2%):")
        print(f"  v1: {v1_actionable}/{len(v1_edges)} ({v1_actionable_pct:.1f}%)" if v1_edges else "  v1: N/A")
        print(f"  v2: {v2_actionable}/{len(v2_edges)} ({v2_actionable_pct:.1f}%)" if v2_edges else "  v2: N/A")

        # Agreement analysis
        if both_valid:
            agreement_counts = {}
            for r in both_valid:
                agreement_counts[r['agreement']] = agreement_counts.get(r['agreement'], 0) + 1

            total_agree = agreement_counts.get('EXACT', 0) + agreement_counts.get('CLOSE', 0)
            agreement_rate = total_agree / len(both_valid) * 100

            print(f"\n🤝 Agreement (v1 vs v2):")
            print(f"  EXACT (<5% diff): {agreement_counts.get('EXACT', 0)}")
            print(f"  CLOSE (<15% diff): {agreement_counts.get('CLOSE', 0)}")
            print(f"  MODERATE (<30% diff): {agreement_counts.get('MODERATE', 0)}")
            print(f"  OUTLIER (>30% diff): {agreement_counts.get('OUTLIER', 0)}")
            print(f"  Total Agreement Rate: {agreement_rate:.1f}% (target: 60-85%)")

            # Correlation
            v1_edges_paired = [r['v1_edge'] for r in both_valid]
            v2_edges_paired = [r['v2_edge'] for r in both_valid]
            correlation = np.corrcoef(v1_edges_paired, v2_edges_paired)[0, 1]
            print(f"  Correlation: {correlation:.3f}")

        # Fallback analysis
        fallback_count = sum(1 for r in v2_valid if r['v2_metadata'].get('fallback_to_v1', False))
        fallback_rate = fallback_count / len(v2_valid) * 100 if v2_valid else 0

        print(f"\n🔄 Fallback Analysis:")
        print(f"  Fallback to v1: {fallback_count}/{len(v2_valid)} ({fallback_rate:.1f}%)")
        print(f"  Target: <20% {'✅' if fallback_rate < 20 else '❌'}")

        # Edge range validation
        all_edges = v1_edges + v2_edges
        outlier_edges = [e for e in all_edges if abs(e) > 0.20]

        print(f"\n⚠️ Edge Range Validation:")
        print(f"  Edges >±20%: {len(outlier_edges)}")
        print(f"  Status: {'✅ All edges within range' if len(outlier_edges) == 0 else '❌ Outliers detected'}")

        return {
            'total_matchups': len(self.results),
            'v1_success_count': len(v1_valid),
            'v2_success_count': len(v2_valid),
            'v1_error_rate': v1_error_rate,
            'v2_error_rate': v2_error_rate,
            'v2_performance': {
                'avg_ms': float(np.mean(v2_times)) if v2_times else None,
                'median_ms': float(np.median(v2_times)) if v2_times else None,
                'p95_ms': float(np.percentile(v2_times, 95)) if v2_times else None,
                'p99_ms': float(np.percentile(v2_times, 99)) if v2_times else None,
                'max_ms': float(max(v2_times)) if v2_times else None
            },
            'edge_statistics': {
                'v1': {
                    'mean': float(np.mean(v1_edges)) if v1_edges else None,
                    'median': float(np.median(v1_edges)) if v1_edges else None,
                    'std': float(np.std(v1_edges)) if v1_edges else None,
                    'min': float(min(v1_edges)) if v1_edges else None,
                    'max': float(max(v1_edges)) if v1_edges else None
                },
                'v2': {
                    'mean': float(np.mean(v2_edges)) if v2_edges else None,
                    'median': float(np.median(v2_edges)) if v2_edges else None,
                    'std': float(np.std(v2_edges)) if v2_edges else None,
                    'min': float(min(v2_edges)) if v2_edges else None,
                    'max': float(max(v2_edges)) if v2_edges else None
                }
            },
            'actionability': {
                'v1_actionable_pct': v1_actionable_pct,
                'v2_actionable_pct': v2_actionable_pct
            },
            'agreement': {
                'rate_pct': agreement_rate if both_valid else None,
                'exact_count': agreement_counts.get('EXACT', 0) if both_valid else None,
                'close_count': agreement_counts.get('CLOSE', 0) if both_valid else None,
                'moderate_count': agreement_counts.get('MODERATE', 0) if both_valid else None,
                'outlier_count': agreement_counts.get('OUTLIER', 0) if both_valid else None,
                'correlation': float(correlation) if both_valid else None
            },
            'fallback_rate_pct': fallback_rate,
            'edge_range_outliers': len(outlier_edges)
        }

    def save_results(self, analysis: Dict):
        """Save results to JSON file"""
        output = {
            'metadata': {
                'phase': 'Phase 5 - Production Testing',
                'timestamp': datetime.utcnow().isoformat(),
                'season': self.season,
                'week': self.week,
                'matchup_count': len(self.results)
            },
            'results': self.results,
            'analysis': analysis
        }

        output_file = 'PRODUCTION_TEST_RESULTS.json'
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n✅ Results saved to {output_file}\n")


def main():
    """Main execution function"""
    tester = ProductionTester(season=2025, week=7)

    # Load matchups
    matchups = tester.load_matchups()

    # Run calculations
    results = tester.run_calculations(matchups)

    # Analyze results
    analysis = tester.analyze_results()

    # Save results
    tester.save_results(analysis)

    print(f"{'='*70}")
    print("PHASE 5 PRODUCTION TESTING COMPLETE")
    print(f"{'='*70}\n")
    print(f"Next step: Review results and execute GO/NO-GO decision framework")


if __name__ == '__main__':
    main()
