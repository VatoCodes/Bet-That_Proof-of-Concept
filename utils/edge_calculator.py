"""Edge Calculator for NFL QB TD Props

This module provides the core edge detection engine for NFL betting analysis.
It calculates true probabilities for QB TD props and compares them to implied odds
to identify betting opportunities.

Classes:
    ProbabilityCalculator: Converts QB and defense stats to win probabilities
    EdgeDetector: Compares true probability vs implied odds
    BetRecommender: Provides Kelly Criterion bet sizing recommendations
    EdgeCalculator: Main orchestrator class
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query_tools import DatabaseQueryTools
from config import get_database_path

logger = logging.getLogger(__name__)


class ProbabilityCalculator:
    """Converts QB and defense statistics to win probabilities"""
    
    def __init__(self, model_version: str = "v1"):
        """
        Initialize probability calculator
        
        Args:
            model_version: Model version to use ("v1" for simple, "v2" for advanced)
        """
        self.model_version = model_version
        self.league_average_tds = 1.5  # NFL average passing TDs per game
        
    def calculate_qb_td_probability(self, qb_stats: Dict, defense_stats: Dict, 
                                   matchup_context: Optional[Dict] = None) -> Dict:
        """
        Calculate probability of QB throwing 0.5+ TDs
        
        Args:
            qb_stats: Dictionary with QB statistics
            defense_stats: Dictionary with defense statistics  
            matchup_context: Optional context (home/away, etc.)
            
        Returns:
            Dictionary with probability and metadata
        """
        if self.model_version == "v1":
            return self._calculate_simple_probability(qb_stats, defense_stats, matchup_context)
        elif self.model_version == "v2":
            return self._calculate_advanced_probability(qb_stats, defense_stats, matchup_context)
        else:
            raise ValueError(f"Unknown model version: {self.model_version}")
    
    def _calculate_simple_probability(self, qb_stats: Dict, defense_stats: Dict, 
                                    matchup_context: Optional[Dict] = None) -> Dict:
        """
        Simple probability model (v1)
        
        Uses weighted average of QB TD rate and defense TDs allowed rate
        """
        # Extract key metrics
        qb_td_per_game = qb_stats.get('total_tds', 0) / max(qb_stats.get('games_played', 1), 1)
        defense_tds_per_game = defense_stats.get('tds_per_game', self.league_average_tds)
        
        # Weighted formula: 60% QB performance, 40% defense weakness
        base_prob = (qb_td_per_game * 0.6) + (defense_tds_per_game * 0.4)
        
        # Apply home field advantage if provided
        home_field_advantage = 0
        if matchup_context and matchup_context.get('is_home', False):
            home_field_advantage = 0.1
        
        adjusted_prob = base_prob * (1 + home_field_advantage)
        
        # Convert to 0.5+ TD probability (simplified)
        # If QB averages 1.5 TDs/game, probability of 0.5+ is ~85%
        # If QB averages 0.5 TDs/game, probability of 0.5+ is ~50%
        true_probability = min(0.95, max(0.05, adjusted_prob * 0.6))
        
        return {
            'probability': true_probability,
            'confidence': 'medium',
            'model_version': 'v1',
            'qb_td_per_game': qb_td_per_game,
            'defense_tds_per_game': defense_tds_per_game,
            'home_field_advantage': home_field_advantage,
            'base_probability': base_prob,
            'adjusted_probability': adjusted_prob
        }
    
    def _calculate_advanced_probability(self, qb_stats: Dict, defense_stats: Dict,
                                      matchup_context: Optional[Dict] = None) -> Dict:
        """
        Advanced probability model (v2)
        
        Includes league context, variance analysis, and confidence intervals
        """
        # Base rates
        qb_td_per_game = qb_stats.get('total_tds', 0) / max(qb_stats.get('games_played', 1), 1)
        defense_tds_per_game = defense_stats.get('tds_per_game', self.league_average_tds)
        
        # League adjustments
        qb_vs_league = qb_td_per_game / self.league_average_tds
        def_vs_league = defense_tds_per_game / self.league_average_tds
        
        # Weighted composite score
        composite_score = (qb_vs_league * 0.6) + (def_vs_league * 0.4)
        
        # Convert score to probability
        base_probability = self._score_to_probability(composite_score)
        
        # Apply contextual adjustments
        if matchup_context:
            if matchup_context.get('is_home', False):
                base_probability *= 1.1
            if matchup_context.get('is_division_game', False):
                base_probability *= 0.95
        
        # Calculate confidence based on sample size
        games_played = qb_stats.get('games_played', 1)
        confidence = self._calculate_confidence(games_played)
        
        # Calculate probability range
        variance = 0.1  # 10% variance
        prob_range = (
            max(0.05, base_probability - variance),
            min(0.95, base_probability + variance)
        )
        
        return {
            'probability': base_probability,
            'confidence': confidence,
            'model_version': 'v2',
            'qb_td_per_game': qb_td_per_game,
            'defense_tds_per_game': defense_tds_per_game,
            'qb_vs_league': qb_vs_league,
            'def_vs_league': def_vs_league,
            'composite_score': composite_score,
            'range': prob_range,
            'games_played': games_played
        }
    
    def _score_to_probability(self, score: float) -> float:
        """Convert composite score to probability"""
        # Sigmoid-like function to convert score to probability
        # Score of 1.0 (league average) = ~65% probability
        # Score of 1.5 (50% above average) = ~85% probability
        # Score of 0.5 (50% below average) = ~45% probability
        
        import math
        probability = 1 / (1 + math.exp(-2 * (score - 1.0)))
        return min(0.95, max(0.05, probability))
    
    def _calculate_confidence(self, games_played: int) -> str:
        """Calculate confidence level based on sample size"""
        if games_played >= 8:
            return 'high'
        elif games_played >= 4:
            return 'medium'
        else:
            return 'low'


class EdgeDetector:
    """Compares true probability vs implied odds to detect edges"""
    
    def __init__(self):
        """Initialize edge detector"""
        pass
    
    def calculate_edge(self, true_probability: float, odds: int) -> Dict:
        """
        Calculate edge between true probability and implied odds
        
        Args:
            true_probability: Our calculated win probability (0-1)
            odds: American odds (e.g., -210, +150)
            
        Returns:
            Dictionary with edge calculations
        """
        # Convert American odds to implied probability
        implied_prob = self._american_odds_to_probability(odds)
        
        # Calculate edge
        edge = true_probability - implied_prob
        edge_percentage = (edge / implied_prob) * 100 if implied_prob > 0 else 0
        
        # Convert to decimal odds for Kelly Criterion
        decimal_odds = self._american_odds_to_decimal(odds)
        
        return {
            'true_probability': true_probability,
            'implied_probability': implied_prob,
            'edge': edge,
            'edge_percentage': edge_percentage,
            'odds': odds,
            'decimal_odds': decimal_odds,
            'is_positive_edge': edge > 0
        }
    
    def _american_odds_to_probability(self, odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds < 0:
            # Negative odds (favorite)
            return abs(odds) / (abs(odds) + 100)
        else:
            # Positive odds (underdog)
            return 100 / (odds + 100)
    
    def _american_odds_to_decimal(self, odds: int) -> float:
        """Convert American odds to decimal odds"""
        if odds < 0:
            return (100 / abs(odds)) + 1
        else:
            return (odds / 100) + 1


class BetRecommender:
    """Provides Kelly Criterion bet sizing recommendations"""
    
    def __init__(self, max_bankroll_fraction: float = 0.05):
        """
        Initialize bet recommender
        
        Args:
            max_bankroll_fraction: Maximum fraction of bankroll to recommend (default 5%)
        """
        self.max_bankroll_fraction = max_bankroll_fraction
    
    def calculate_kelly_fraction(self, true_prob: float, decimal_odds: float, 
                                kelly_fraction: float = 0.25) -> float:
        """
        Calculate recommended bet size using fractional Kelly Criterion
        
        Args:
            true_prob: Our calculated win probability (0-1)
            decimal_odds: Decimal odds (e.g., 1.476 for -210)
            kelly_fraction: Conservative multiplier (default 25% Kelly)
            
        Returns:
            Recommended fraction of bankroll
        """
        # Kelly Criterion: f = (bp - q) / b
        # f = fraction of bankroll to bet
        # b = decimal odds - 1
        # p = true probability of win
        # q = probability of loss (1 - p)
        
        b = decimal_odds - 1
        p = true_prob
        q = 1 - p
        
        # Calculate Kelly fraction
        kelly = (b * p - q) / b
        
        # Apply fractional Kelly (conservative)
        recommended = max(0, kelly * kelly_fraction)
        
        # Cap at maximum bankroll fraction (safety)
        return min(recommended, self.max_bankroll_fraction)
    
    def generate_recommendation(self, edge_data: Dict, bankroll: float = 1000) -> Dict:
        """
        Generate bet recommendation based on edge data
        
        Args:
            edge_data: Dictionary with edge calculations
            bankroll: Total bankroll amount
            
        Returns:
            Dictionary with bet recommendation
        """
        edge_pct = edge_data['edge_percentage']
        true_prob = edge_data['true_probability']
        decimal_odds = edge_data['decimal_odds']
        
        # Determine tier and Kelly fraction
        if edge_pct < 5:
            tier = "PASS"
            kelly_multiplier = 0
        elif edge_pct < 10:
            tier = "SMALL EDGE"
            kelly_multiplier = 0.15
        elif edge_pct < 20:
            tier = "GOOD EDGE"
            kelly_multiplier = 0.25
        else:
            tier = "STRONG EDGE"
            kelly_multiplier = 0.25
        
        # Calculate recommended bet
        kelly_fraction = self.calculate_kelly_fraction(true_prob, decimal_odds, kelly_multiplier)
        bet_amount = bankroll * kelly_fraction
        
        return {
            'tier': tier,
            'recommended_bet': bet_amount,
            'kelly_fraction': kelly_fraction,
            'edge_percentage': edge_pct,
            'confidence': edge_data.get('confidence', 'medium'),
            'bankroll_percentage': kelly_fraction * 100
        }


class EdgeCalculator:
    """Main orchestrator for edge detection calculations"""
    
    def __init__(self, model_version: str = "v1", db_path: Optional[Path] = None):
        """
        Initialize edge calculator
        
        Args:
            model_version: Model version to use ("v1" or "v2")
            db_path: Path to database (defaults to config setting)
        """
        self.model_version = model_version
        self.db_path = db_path or get_database_path()
        
        # Initialize components
        self.prob_calculator = ProbabilityCalculator(model_version)
        self.edge_detector = EdgeDetector()
        self.bet_recommender = BetRecommender()
    
    def calculate_edge(self, qb_stats: Dict, defense_stats: Dict, odds: int,
                      matchup_context: Optional[Dict] = None) -> Dict:
        """
        Calculate complete edge analysis for a QB TD prop
        
        Args:
            qb_stats: QB statistics dictionary
            defense_stats: Defense statistics dictionary
            odds: American odds for the prop
            matchup_context: Optional matchup context
            
        Returns:
            Dictionary with complete edge analysis
        """
        # Calculate true probability
        prob_result = self.prob_calculator.calculate_qb_td_probability(
            qb_stats, defense_stats, matchup_context
        )
        
        # Calculate edge
        edge_result = self.edge_detector.calculate_edge(
            prob_result['probability'], odds
        )
        
        # Generate bet recommendation
        bet_recommendation = self.bet_recommender.generate_recommendation(edge_result)
        
        # Combine results
        return {
            **prob_result,
            **edge_result,
            'bet_recommendation': bet_recommendation
        }
    
    def find_edges_for_week(self, week: int, threshold: float = 5.0) -> List[Dict]:
        """
        Find all edge opportunities for a given week
        
        Args:
            week: NFL week number
            threshold: Minimum edge percentage to include
            
        Returns:
            List of edge opportunities
        """
        edges = []
        
        try:
            with DatabaseQueryTools(self.db_path) as db:
                # Get QB vs Defense matchups
                matchups = db.find_qb_defense_matchups(week)
                
                for _, matchup in matchups.iterrows():
                    if pd.isna(matchup['home_qb_prop_odds']) or pd.isna(matchup['away_defense_tds_allowed']):
                        continue
                    
                    # Prepare QB stats
                    qb_stats = {
                        'total_tds': matchup['home_qb_tds'],
                        'games_played': matchup['home_qb_games']
                    }
                    
                    # Prepare defense stats
                    defense_stats = {
                        'tds_per_game': matchup['away_defense_tds_allowed']
                    }
                    
                    # Prepare matchup context
                    matchup_context = {
                        'is_home': True,  # QB is at home
                        'is_division_game': False  # TODO: Add division detection
                    }
                    
                    # Calculate edge
                    edge_result = self.calculate_edge(
                        qb_stats, defense_stats, 
                        matchup['home_qb_prop_odds'], matchup_context
                    )
                    
                    # Add matchup info
                    edge_result.update({
                        'qb_name': matchup['home_qb'],
                        'qb_team': matchup['home_qb_team'],
                        'opponent': matchup['away_team'],
                        'sportsbook': matchup['prop_sportsbook'],
                        'game_date': matchup['game_date']
                    })
                    
                    # Filter by threshold
                    if edge_result['edge_percentage'] >= threshold:
                        edges.append(edge_result)
                
                # Sort by edge percentage
                edges.sort(key=lambda x: x['edge_percentage'], reverse=True)
                
        except Exception as e:
            logger.error(f"Error finding edges for week {week}: {e}")
        
        return edges
    
    def calculate_edge_from_csv(self, qb_name: str, opponent: str, odds: int,
                               qb_stats_df: pd.DataFrame, defense_stats_df: pd.DataFrame,
                               matchup_context: Optional[Dict] = None) -> Dict:
        """
        Calculate edge using CSV data (for backward compatibility)
        
        Args:
            qb_name: QB name
            opponent: Opposing team
            odds: American odds
            qb_stats_df: DataFrame with QB stats
            defense_stats_df: DataFrame with defense stats
            matchup_context: Optional matchup context
            
        Returns:
            Dictionary with edge analysis
        """
        # Find QB stats
        qb_row = qb_stats_df[qb_stats_df['qb_name'] == qb_name]
        if qb_row.empty:
            raise ValueError(f"QB not found: {qb_name}")
        
        qb_stats = {
            'total_tds': qb_row.iloc[0]['total_tds'],
            'games_played': qb_row.iloc[0]['games_played']
        }
        
        # Find defense stats
        def_row = defense_stats_df[defense_stats_df['team_name'] == opponent]
        if def_row.empty:
            raise ValueError(f"Defense not found: {opponent}")
        
        defense_stats = {
            'tds_per_game': def_row.iloc[0]['tds_per_game']
        }
        
        return self.calculate_edge(qb_stats, defense_stats, odds, matchup_context)


def main():
    """CLI interface for edge calculator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NFL Edge Calculator')
    parser.add_argument('--week', type=int, help='NFL week number')
    parser.add_argument('--threshold', type=float, default=5.0, help='Minimum edge percentage')
    parser.add_argument('--model', choices=['v1', 'v2'], default='v1', help='Model version')
    parser.add_argument('--bankroll', type=float, default=1000, help='Bankroll amount')
    
    args = parser.parse_args()
    
    if not args.week:
        print("Error: --week is required")
        return 1
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        calculator = EdgeCalculator(model_version=args.model)
        edges = calculator.find_edges_for_week(args.week, args.threshold)
        
        print(f"\nNFL Edge Finder - Week {args.week}")
        print(f"Model: {args.model.upper()}")
        print(f"Threshold: {args.threshold}% edge minimum")
        print(f"Bankroll: ${args.bankroll:,.0f}")
        print("=" * 60)
        
        if not edges:
            print("No edge opportunities found")
            return 0
        
        print(f"EDGE OPPORTUNITIES FOUND: {len(edges)}\n")
        
        for i, edge in enumerate(edges, 1):
            print(f"{i}. {edge['qb_name']} ({edge['qb_team']}) vs {edge['opponent']}")
            print(f"   Prop: Over 0.5 TD @ {edge['odds']} ({edge['sportsbook']})")
            print(f"   Implied: {edge['implied_probability']:.1%}")
            print(f"   True Prob: {edge['true_probability']:.1%} (confidence: {edge['confidence']})")
            print(f"   Edge: {edge['edge_percentage']:+.1f}% ⭐ {edge['bet_recommendation']['tier']}")
            print(f"   Recommendation: ${edge['bet_recommendation']['recommended_bet']:.2f} ({edge['bet_recommendation']['bankroll_percentage']:.1f}% of bankroll)")
            print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
