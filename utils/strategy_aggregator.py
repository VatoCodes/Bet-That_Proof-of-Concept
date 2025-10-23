"""
Strategy Aggregator - Unified wrapper for all betting edge calculators.

This module provides a single interface for accessing edges from multiple
betting strategies, standardizing outputs and handling errors gracefully.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_manager import DatabaseManager
from utils.calculators.first_half_total_calculator import FirstHalfTotalCalculator
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2

logger = logging.getLogger(__name__)


class StrategyAggregator:
    """
    Unified interface for all betting edge calculators.

    Responsibilities:
    - Call all calculators with standardized parameters
    - Normalize output format across strategies
    - Handle errors gracefully (don't let one strategy fail all)
    - Provide quick count queries for UI badges
    """

    def __init__(self, db_path: str = "data/database/nfl_betting.db"):
        """Initialize with database connection."""
        self.db_path = db_path

        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(db_path)

            # Initialize calculators
            self.first_half_calc = FirstHalfTotalCalculator(self.db_manager)
            self.qb_td_calc_v2 = QBTDCalculatorV2(self.db_manager)

            logger.info("StrategyAggregator initialized with 2 calculators")

        except Exception as e:
            logger.error(f"Error initializing StrategyAggregator: {e}")
            raise

    def get_all_edges(
        self,
        week: int,
        season: int = 2024,
        min_edge: float = 5.0,
        strategy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all edges from all strategies for a given week.

        Args:
            week: NFL week number (1-18)
            season: NFL season year
            min_edge: Minimum edge percentage (default: 5.0)
            strategy: Optional filter - "first_half", "qb_td_v1", "qb_td_v2", or None for all

        Returns:
            List of edge dictionaries in standardized format
        """
        all_edges = []

        # Determine which strategies to run
        strategies_to_run = []
        if strategy is None or strategy == 'all':
            strategies_to_run = ['first_half', 'qb_td_v1', 'qb_td_v2']
        else:
            strategies_to_run = [strategy]

        # Run each strategy
        if 'first_half' in strategies_to_run:
            all_edges.extend(self._get_first_half_edges(week, season, min_edge))

        if 'qb_td_v1' in strategies_to_run:
            all_edges.extend(self._get_qb_td_v1_edges(week, season, min_edge))

        if 'qb_td_v2' in strategies_to_run:
            all_edges.extend(self._get_qb_td_v2_edges(week, season, min_edge))

        # Note: Kicker strategy not yet implemented (kicker_stats table empty)

        # Sort by edge percentage (highest first)
        all_edges.sort(key=lambda x: x['edge_pct'], reverse=True)

        return all_edges

    def get_edge_counts(
        self,
        week: int,
        season: int = 2024
    ) -> Dict[str, int]:
        """
        Quick count of edges per strategy (for tab badges).

        Args:
            week: NFL week number
            season: NFL season year

        Returns:
            Dict with strategy counts: {"first_half": 3, "qb_td_v1": 5, "qb_td_v2": 4, "total": 12}
        """
        # Get full edges (could optimize with count-only queries later)
        edges = self.get_all_edges(week, season, min_edge=0.0)  # Get all, regardless of edge

        counts = {
            "first_half": 0,
            "qb_td_v1": 0,
            "qb_td_v2": 0,
            "kicker": 0,
            "total": 0
        }

        for edge in edges:
            strategy = edge.get('strategy', '')
            if 'First Half' in strategy:
                counts['first_half'] += 1
            elif 'Enhanced v2' in strategy or '(Enhanced v2)' in strategy or 'v2' in strategy.lower():
                counts['qb_td_v2'] += 1
            elif '(Simple v1)' in strategy or 'v1' in strategy.lower():
                counts['qb_td_v1'] += 1
            elif 'Kicker' in strategy:
                counts['kicker'] += 1

        counts['total'] = len(edges)

        return counts

    def _get_first_half_edges(
        self,
        week: int,
        season: int,
        min_edge: float
    ) -> List[Dict[str, Any]]:
        """Get edges from First Half Total Under calculator."""
        try:
            # Call calculator
            edges = self.first_half_calc.calculate_edges(week, season)

            # Standardize format
            standardized = []
            for edge in edges:
                # Map calculator output to standard format
                std_edge = {
                    "matchup": edge.get('matchup', 'Unknown'),
                    "strategy": "First Half Total Under",
                    "line": edge.get('line', 0.0),
                    "recommendation": edge.get('recommendation', f"UNDER {edge.get('line', 0.0)}"),
                    "edge_pct": edge.get('edge_pct', 0.0),
                    "confidence": edge.get('confidence', 'MEDIUM'),
                    "reasoning": edge.get('reasoning', 'No reasoning provided')
                }

                # Only include if meets minimum edge
                if std_edge['edge_pct'] >= min_edge:
                    standardized.append(std_edge)

            logger.info(f"First Half Total: {len(standardized)} edges found (week {week})")
            return standardized

        except Exception as e:
            logger.error(f"Error getting First Half Total edges: {e}")
            return []

    def _get_qb_td_v1_edges(
        self,
        week: int,
        season: int,
        min_edge: float
    ) -> List[Dict[str, Any]]:
        """Get edges from QB TD v1 Simple calculator with v2 metrics for comparison."""
        try:
            # Use the base EdgeCalculator directly with v1 model
            from utils.edge_calculator import EdgeCalculator
            from pathlib import Path
            v1_calc = EdgeCalculator(model_version="v1", db_path=Path(self.db_path))

            # Call v1 calculator
            edges = v1_calc.find_edges_for_week(week, threshold=0.0)  # Get all, we'll filter by min_edge below

            # Standardize format
            standardized = []
            for edge in edges:
                # Map calculator output to standard format
                qb_name = edge.get('qb_name', 'Unknown')
                opponent = edge.get('opponent', 'Unknown')
                matchup = f"{qb_name} vs {opponent}"

                # Build reasoning if not present
                reasoning = edge.get('reasoning', '')
                if not reasoning:
                    true_prob = edge.get('true_probability', 0.0)
                    implied_prob = edge.get('implied_probability', 0.0)
                    reasoning = (
                        f"{qb_name} has true probability of {true_prob:.1%} "
                        f"vs market implied probability of {implied_prob:.1%} "
                        f"({opponent} defense). "
                        f"Edge: {edge.get('edge_percentage', 0.0):.1f}%"
                    )

                v1_edge_pct = edge.get('edge_percentage', 0.0)

                # Calculate v2 metrics for comparison
                v2_edge_pct = None
                red_zone_td_rate = None
                try:
                    red_zone_td_rate = self.qb_td_calc_v2._calculate_red_zone_td_rate(qb_name, season)
                    opp_defense_quality = self.qb_td_calc_v2._get_opponent_defense_quality(opponent, season)
                    v2_edge_pct = self.qb_td_calc_v2._adjust_edge_with_v2_metrics(
                        base_edge_pct=v1_edge_pct,
                        qb_stats={},  # Not used in adjustment
                        red_zone_td_rate=red_zone_td_rate,
                        opp_defense_quality=opp_defense_quality
                    )
                except Exception as e:
                    logger.debug(f"Could not calculate v2 metrics for {qb_name}: {e}")

                std_edge = {
                    "matchup": matchup,
                    "strategy": "QB TD 0.5+ (Simple v1)",
                    "line": edge.get('line', 0.5),
                    "recommendation": f"OVER {edge.get('line', 0.5)} TD",
                    "edge_pct": v1_edge_pct,
                    "confidence": edge.get('confidence', 'MEDIUM').upper(),
                    "reasoning": reasoning,
                    "opponent": opponent,

                    # v2 comparison fields
                    "v2_edge_pct": v2_edge_pct,
                    "red_zone_td_rate": red_zone_td_rate
                }

                # Only include if meets minimum edge
                if std_edge['edge_pct'] >= min_edge:
                    standardized.append(std_edge)

            logger.info(f"QB TD v1: {len(standardized)} edges found (week {week})")
            return standardized

        except Exception as e:
            logger.error(f"Error getting QB TD v1 edges: {e}")
            return []

    def _get_qb_td_v2_edges(
        self,
        week: int,
        season: int,
        min_edge: float
    ) -> List[Dict[str, Any]]:
        """Get edges from QB TD v2 Enhanced calculator."""
        try:
            # Call calculator
            edges = self.qb_td_calc_v2.calculate_edges(
                week=week,
                season=season,
                min_edge_threshold=0.0  # Get all, we'll filter by min_edge below
            )

            # Standardize format
            standardized = []
            for edge in edges:
                # Map calculator output to standard format
                # QB TD v2 returns edges with qb_name, opponent, etc from EdgeCalculator
                qb_name = edge.get('qb_name', 'Unknown')
                opponent = edge.get('opponent', 'Unknown')
                matchup = f"{qb_name} vs {opponent}"

                # Build reasoning if not present
                reasoning = edge.get('reasoning', '')
                if not reasoning:
                    true_prob = edge.get('true_probability', 0.0)
                    implied_prob = edge.get('implied_probability', 0.0)
                    reasoning = (
                        f"{qb_name} has true probability of {true_prob:.1%} "
                        f"vs market implied probability of {implied_prob:.1%} "
                        f"({opponent} defense). "
                        f"Edge: {edge.get('edge_percentage', 0.0):.1f}%"
                    )

                std_edge = {
                    "matchup": matchup,
                    "strategy": edge.get('strategy', 'QB TD 0.5+ (Enhanced v2)'),  # Use actual strategy from calculator
                    "line": edge.get('line', 0.5),
                    "recommendation": f"OVER {edge.get('line', 0.5)} TD",
                    "edge_pct": edge.get('edge_percentage', 0.0),
                    "confidence": edge.get('confidence', 'MEDIUM').upper(),
                    "reasoning": reasoning,

                    # v2-specific fields
                    "v1_edge_pct": edge.get('v1_edge_percentage'),
                    "red_zone_td_rate": edge.get('v2_metrics', {}).get('red_zone_td_rate'),
                    "opponent": opponent
                }

                # Only include if meets minimum edge
                if std_edge['edge_pct'] >= min_edge:
                    standardized.append(std_edge)

            logger.info(f"QB TD v2: {len(standardized)} edges found (week {week})")
            return standardized

        except Exception as e:
            logger.error(f"Error getting QB TD v2 edges: {e}")
            return []

    def get_available_strategies(self) -> List[str]:
        """
        Get list of currently available strategies.

        Returns:
            List of strategy identifiers: ["first_half", "qb_td_v1", "qb_td_v2"]
        """
        return ["first_half", "qb_td_v1", "qb_td_v2"]
        # Note: "kicker" will be added when kicker_stats data is ready

    def validate_week(self, week: int, season: int = 2024) -> bool:
        """
        Check if week data exists in database.

        Args:
            week: NFL week number (1-18)
            season: NFL season year

        Returns:
            True if week has data, False otherwise
        """
        try:
            # Quick check if any team metrics exist for this week
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM matchups
                WHERE week = ?
            """, (week,))

            count = cursor.fetchone()[0]
            return count > 0

        except Exception as e:
            logger.error(f"Error validating week {week}: {e}")
            return False
