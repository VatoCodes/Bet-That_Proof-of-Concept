"""QB TD v2 Enhanced Calculator for NFL Betting Edge Detection

This module provides enhanced QB TD 0.5+ prop edge detection with advanced metrics:
- Red zone accuracy analysis
- Opponent defensive strength adjustment
- Recent form weighting (when available)

Improvements over v1: Target 95%+ accuracy (vs 90% for v1)
"""

import pandas as pd
import sqlite3
from typing import Dict, List, Optional
from pathlib import Path
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.edge_calculator import EdgeCalculator

logger = logging.getLogger(__name__)


class QBTDCalculatorV2:
    """
    Enhanced QB TD 0.5+ prop edge detection with advanced metrics

    Improvements over v1:
    - Red zone accuracy analysis from play-by-play
    - Opponent defensive strength adjustment
    - More selective recommendations (higher accuracy)

    Expected Output: 5-10 edges per week (more selective than v1's 10-15)
    Win Rate Target: 95%+ (vs 90% for v1)
    """

    def __init__(self, db_manager):
        """
        Initialize QB TD v2 calculator

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
        self.v1_calculator = EdgeCalculator(model_version="v1", db_path=db_manager.db_path)

    def calculate_edges(self, week: int, season: int = 2024,
                       min_edge_threshold: float = 5.0) -> List[Dict]:
        """
        Find QB TD 0.5+ edges with enhanced analysis

        Args:
            week: NFL week number
            season: NFL season year
            min_edge_threshold: Minimum edge percentage to include (default 5%)

        Returns:
            List of edge dicts with enhanced v2 metrics
        """
        edges = []

        try:
            # Start with v1 edges as baseline
            v1_edges = self.v1_calculator.find_edges_for_week(week, threshold=min_edge_threshold)

            if not v1_edges:
                logger.info(f"No v1 edges found for Week {week} - no v2 edges to enhance")
                return edges

            logger.info(f"Enhancing {len(v1_edges)} v1 edges with v2 metrics")

            # Enhance each edge with v2 metrics
            for edge in v1_edges:
                qb_name = edge['qb_name']
                opponent = edge['opponent']

                # Get enhanced QB stats
                qb_stats = self._get_qb_enhanced_stats(qb_name, season)

                if not qb_stats:
                    logger.warning(f"No enhanced stats found for {qb_name}, using v1 data only")
                    # Still include the edge but mark it as v1-only
                    edge['strategy'] = 'QB TD 0.5+ (v2 - limited data)'
                    edge['model_version'] = 'v2_fallback'
                    # Store the original v1 edge for comparison
                    edge['v1_edge_percentage'] = edge['edge_percentage']
                    # Initialize v2_metrics as empty since we don't have enhanced data
                    edge['v2_metrics'] = {
                        'red_zone_td_rate': None,
                        'opp_defense_rank': 'N/A',
                        'opp_pass_tds_allowed': 'N/A',
                        'v1_edge_pct': round(edge['edge_percentage'], 1)
                    }
                    edges.append(edge)
                    continue

                # Calculate red zone TD rate from play-by-play
                red_zone_td_rate = self._calculate_red_zone_td_rate(qb_name, season)

                # Get opponent defensive quality
                opp_defense_quality = self._get_opponent_defense_quality(opponent, season)

                # Adjust v1 edge percentage with new factors
                adjusted_edge_pct = self._adjust_edge_with_v2_metrics(
                    base_edge_pct=edge['edge_percentage'],
                    qb_stats=qb_stats,
                    red_zone_td_rate=red_zone_td_rate,
                    opp_defense_quality=opp_defense_quality
                )

                # Update edge recommendation with v2 enhancements
                edge['edge_percentage'] = adjusted_edge_pct
                edge['strategy'] = 'QB TD 0.5+ (Enhanced v2)'
                edge['model_version'] = 'v2'

                # Add v2-specific metrics
                edge['v2_metrics'] = {
                    'red_zone_td_rate': round(red_zone_td_rate, 3),
                    'opp_defense_rank': opp_defense_quality.get('rank', 'N/A'),
                    'opp_pass_tds_allowed': opp_defense_quality.get('tds_per_game', 'N/A'),
                    'v1_edge_pct': round(edge.get('v1_edge_percentage', edge['edge_percentage']), 1)
                }

                # Enhance reasoning with v2 details
                v2_reasoning = self._build_v2_reasoning(
                    qb_name=qb_name,
                    red_zone_td_rate=red_zone_td_rate,
                    opp_defense_quality=opp_defense_quality,
                    adjustment=adjusted_edge_pct - edge.get('v1_edge_percentage', edge['edge_percentage'])
                )

                # Store original v1 edge for comparison
                if 'v1_edge_percentage' not in edge:
                    edge['v1_edge_percentage'] = edge['edge_percentage']

                # Append v2 reasoning to original reasoning
                edge['reasoning'] = v2_reasoning

                # Recalculate confidence and tier based on adjusted edge
                edge['confidence'] = self._calculate_confidence(adjusted_edge_pct, red_zone_td_rate)
                edge['bet_recommendation']['tier'] = self._calculate_tier(adjusted_edge_pct)

                # Only include edges that still meet threshold after v2 adjustment
                if adjusted_edge_pct >= min_edge_threshold:
                    edges.append(edge)
                    logger.info(f"v2 edge: {qb_name} - {adjusted_edge_pct:.1f}% (v1: {edge['v1_edge_percentage']:.1f}%)")
                else:
                    logger.info(f"Filtered out {qb_name} - edge dropped to {adjusted_edge_pct:.1f}%")

            logger.info(f"Found {len(edges)} QB TD v2 edges (from {len(v1_edges)} v1 edges)")

        except Exception as e:
            logger.error(f"Error calculating QB TD v2 edges: {e}", exc_info=True)

        return edges

    def _get_qb_enhanced_stats(self, qb_name: str, season: int) -> Optional[Dict]:
        """
        Get enhanced QB statistics from qb_stats_enhanced table

        Args:
            qb_name: QB name
            season: NFL season year

        Returns:
            Dictionary with QB stats or None if not found
        """
        try:
            stats = self.db_manager.get_qb_stats_enhanced(qb_name, season)
            return stats if stats else None
        except Exception as e:
            logger.warning(f"Error getting enhanced stats for {qb_name}: {e}")
            return None

    def _calculate_red_zone_td_rate(self, qb_name: str, season: int) -> float:
        """
        Calculate QB's red zone TD conversion rate from play-by-play

        Args:
            qb_name: QB name
            season: NFL season year

        Returns:
            Red zone TD rate (0.0-1.0)
        """
        conn = self.db_manager._get_connection()

        query = """
            SELECT
                COUNT(CASE WHEN rushing_or_passing_touchdown = 1 THEN 1 END) as rz_tds,
                COUNT(*) as rz_attempts
            FROM play_by_play
            WHERE qb = ? AND season = ? AND red_zone_play = 1
                  AND (play_type = 'pass' OR play_type = 'run')
        """

        try:
            result = pd.read_sql_query(query, conn, params=(qb_name, season))

            if result.empty or result.iloc[0]['rz_attempts'] == 0:
                logger.debug(f"No red zone plays found for {qb_name}")
                return 0.0

            rz_tds = result.iloc[0]['rz_tds']
            rz_attempts = result.iloc[0]['rz_attempts']

            rate = rz_tds / rz_attempts if rz_attempts > 0 else 0.0
            logger.debug(f"{qb_name} red zone TD rate: {rate:.3f} ({rz_tds}/{rz_attempts})")

            return rate

        except Exception as e:
            logger.warning(f"Error calculating red zone TD rate for {qb_name}: {e}")
            return 0.0

    def _get_opponent_defense_quality(self, opponent: str, season: int) -> Dict:
        """
        Get opponent defensive quality metrics

        Args:
            opponent: Opponent team name
            season: NFL season year

        Returns:
            Dictionary with defensive quality metrics
        """
        conn = self.db_manager._get_connection()

        query = """
            SELECT
                team_name,
                pass_tds_allowed,
                games_played,
                tds_per_game
            FROM defense_stats
            WHERE team_name = ?
            ORDER BY scraped_at DESC
            LIMIT 1
        """

        try:
            result = pd.read_sql_query(query, conn, params=(opponent,))

            if result.empty:
                logger.warning(f"No defense stats found for {opponent}")
                return {'tds_per_game': 1.5, 'rank': 'N/A'}  # Use league average

            tds_per_game = result.iloc[0]['tds_per_game']

            # Calculate rank (simple approximation - could be enhanced)
            # NFL average is ~1.5 TDs/game
            # Strong defense: < 1.2 TDs/game (top 10)
            # Weak defense: > 1.8 TDs/game (bottom 10)
            if tds_per_game < 1.2:
                rank = 'Strong'
            elif tds_per_game > 1.8:
                rank = 'Weak'
            else:
                rank = 'Average'

            return {
                'tds_per_game': tds_per_game,
                'rank': rank,
                'pass_tds_allowed': result.iloc[0]['pass_tds_allowed']
            }

        except Exception as e:
            logger.warning(f"Error getting defense quality for {opponent}: {e}")
            return {'tds_per_game': 1.5, 'rank': 'N/A'}

    def _adjust_edge_with_v2_metrics(self, base_edge_pct: float,
                                    qb_stats: Dict,
                                    red_zone_td_rate: float,
                                    opp_defense_quality: Dict) -> float:
        """
        Adjust edge percentage using enhanced v2 metrics

        Args:
            base_edge_pct: Base edge percentage from v1
            qb_stats: Enhanced QB statistics
            red_zone_td_rate: QB's red zone TD conversion rate
            opp_defense_quality: Opponent defensive quality

        Returns:
            Adjusted edge percentage
        """
        adjusted_edge = base_edge_pct

        # Red zone efficiency adjustment
        # High red zone TD rate (> 0.15) adds confidence
        # Low rate (< 0.05) reduces confidence
        if red_zone_td_rate > 0.15:
            adjusted_edge *= 1.15  # +15% boost for excellent red zone performance
            logger.debug(f"Red zone boost: {red_zone_td_rate:.3f} > 0.15 → +15%")
        elif red_zone_td_rate > 0.10:
            adjusted_edge *= 1.08  # +8% boost for good red zone performance
            logger.debug(f"Red zone boost: {red_zone_td_rate:.3f} > 0.10 → +8%")
        elif red_zone_td_rate < 0.05 and red_zone_td_rate > 0:
            adjusted_edge *= 0.92  # -8% penalty for poor red zone performance
            logger.debug(f"Red zone penalty: {red_zone_td_rate:.3f} < 0.05 → -8%")

        # Opponent defense adjustment
        defense_rank = opp_defense_quality.get('rank', 'Average')
        if defense_rank == 'Weak':
            adjusted_edge *= 1.10  # +10% boost vs weak defense
            logger.debug("Weak defense boost: +10%")
        elif defense_rank == 'Strong':
            adjusted_edge *= 0.88  # -12% penalty vs strong defense
            logger.debug("Strong defense penalty: -12%")

        return round(adjusted_edge, 1)

    def _build_v2_reasoning(self, qb_name: str,
                           red_zone_td_rate: float,
                           opp_defense_quality: Dict,
                           adjustment: float) -> str:
        """
        Build enhanced v2 reasoning text

        Args:
            qb_name: QB name
            red_zone_td_rate: Red zone TD conversion rate
            opp_defense_quality: Opponent defensive quality
            adjustment: Edge adjustment amount

        Returns:
            Reasoning text string
        """
        reasoning_parts = [f"Enhanced v2 analysis for {qb_name}:"]

        # Red zone analysis
        if red_zone_td_rate > 0:
            rz_pct = red_zone_td_rate * 100
            if red_zone_td_rate > 0.15:
                reasoning_parts.append(
                    f"Excellent red zone efficiency ({rz_pct:.1f}% TD rate) adds confidence."
                )
            elif red_zone_td_rate > 0.10:
                reasoning_parts.append(
                    f"Good red zone performance ({rz_pct:.1f}% TD rate) supports edge."
                )
            else:
                reasoning_parts.append(
                    f"Limited red zone success ({rz_pct:.1f}% TD rate) reduces confidence."
                )
        else:
            reasoning_parts.append("No red zone data available for this QB.")

        # Defense analysis
        defense_rank = opp_defense_quality.get('rank', 'N/A')
        tds_per_game = opp_defense_quality.get('tds_per_game', 'N/A')

        if defense_rank == 'Weak':
            reasoning_parts.append(
                f"Opponent defense is weak (allows {tds_per_game:.1f} pass TDs/game)."
            )
        elif defense_rank == 'Strong':
            reasoning_parts.append(
                f"Opponent defense is strong (allows only {tds_per_game:.1f} pass TDs/game)."
            )
        else:
            reasoning_parts.append(
                f"Opponent defense is average (allows {tds_per_game:.1f} pass TDs/game)."
            )

        # Adjustment summary
        if adjustment > 0:
            reasoning_parts.append(f"v2 enhancement increased edge by {adjustment:.1f}%.")
        elif adjustment < 0:
            reasoning_parts.append(f"v2 analysis decreased edge by {abs(adjustment):.1f}%.")
        else:
            reasoning_parts.append("v2 metrics confirm v1 edge estimate.")

        return " ".join(reasoning_parts)

    def _calculate_confidence(self, edge_pct: float, red_zone_td_rate: float) -> str:
        """
        Calculate confidence level based on edge and red zone performance

        Args:
            edge_pct: Edge percentage
            red_zone_td_rate: Red zone TD rate

        Returns:
            Confidence level string
        """
        if edge_pct >= 20 and red_zone_td_rate > 0.12:
            return 'high'
        elif edge_pct >= 15 or red_zone_td_rate > 0.15:
            return 'high'
        elif edge_pct >= 10:
            return 'medium'
        else:
            return 'low'

    def _calculate_tier(self, edge_pct: float) -> str:
        """
        Calculate bet tier based on edge percentage

        Args:
            edge_pct: Edge percentage

        Returns:
            Tier string
        """
        if edge_pct < 5:
            return "PASS"
        elif edge_pct < 10:
            return "SMALL EDGE"
        elif edge_pct < 20:
            return "GOOD EDGE"
        else:
            return "STRONG EDGE"


def main():
    """CLI interface for QB TD v2 calculator"""
    import argparse
    from utils.db_manager import DatabaseManager

    parser = argparse.ArgumentParser(description='QB TD v2 Enhanced Edge Calculator')
    parser.add_argument('--week', type=int, required=True, help='NFL week number')
    parser.add_argument('--season', type=int, default=2024, help='NFL season year')
    parser.add_argument('--threshold', type=float, default=5.0, help='Minimum edge percentage')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        db = DatabaseManager()
        calculator = QBTDCalculatorV2(db)
        edges = calculator.calculate_edges(args.week, args.season, args.threshold)

        print(f"\n🏈 QB TD v2 Enhanced Edge Finder - Week {args.week}, {args.season}")
        print("=" * 70)

        if not edges:
            print("❌ No edge opportunities found")
            return 0

        print(f"✅ {len(edges)} EDGE OPPORTUNITIES FOUND\n")

        for i, edge in enumerate(edges, 1):
            print(f"{i}. {edge['qb_name']} ({edge['qb_team']}) vs {edge['opponent']}")
            print(f"   Strategy: {edge['strategy']}")
            print(f"   Odds: {edge['odds']} | Sportsbook: {edge.get('sportsbook', 'N/A')}")
            print(f"   True Prob: {edge['true_probability']:.1%} | Implied: {edge['implied_probability']:.1%}")
            v1_edge = edge.get('v1_edge_percentage', edge['edge_percentage'])
            v1_edge_str = f"{v1_edge:.1f}" if isinstance(v1_edge, (int, float)) else 'N/A'
            print(f"   Edge: {edge['edge_percentage']:.1f}% (v1: {v1_edge_str}%)")
            print(f"   Confidence: {edge['confidence']} | Tier: {edge['bet_recommendation']['tier']}")

            if 'v2_metrics' in edge:
                print(f"   v2 Metrics:")
                print(f"     Red Zone TD Rate: {edge['v2_metrics']['red_zone_td_rate']:.1%}")
                print(f"     Opp Defense: {edge['v2_metrics']['opp_defense_rank']} "
                      f"({edge['v2_metrics']['opp_pass_tds_allowed']} TDs/game)")

            if 'reasoning' in edge:
                print(f"   Reasoning: {edge['reasoning']}")
            print()

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
