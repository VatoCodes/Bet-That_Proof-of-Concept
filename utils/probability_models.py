"""Advanced Probability Models for NFL Edge Detection

This module provides sophisticated probability calculations that go beyond
the simple weighted model in edge_calculator.py. These models include
league context adjustments, variance analysis, and confidence intervals.

Classes:
    AdvancedProbabilityModel: Sophisticated probability calculations
    LeagueContextAnalyzer: League-wide statistical analysis
    VarianceCalculator: Statistical variance and confidence analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.query_tools import DatabaseQueryTools
from config import get_database_path

logger = logging.getLogger(__name__)


class LeagueContextAnalyzer:
    """Analyzes league-wide statistics for context adjustment"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize league context analyzer
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path or get_database_path()
        self._league_stats_cache = None
    
    def get_league_average_tds(self, year: int = 2025) -> float:
        """
        Get league average passing TDs per game
        
        Args:
            year: NFL season year
            
        Returns:
            League average TDs per game
        """
        try:
            with DatabaseQueryTools(self.db_path) as db:
                qb_stats = db.get_qb_stats(year)
                
                if qb_stats.empty:
                    return 1.5  # Default fallback
                
                # Calculate weighted average (more weight to starters)
                starters = qb_stats[qb_stats['is_starter'] == 1]
                if not starters.empty:
                    total_tds = starters['total_tds'].sum()
                    total_games = starters['games_played'].sum()
                    return total_tds / max(total_games, 1)
                
                # Fallback to all QBs
                total_tds = qb_stats['total_tds'].sum()
                total_games = qb_stats['games_played'].sum()
                return total_tds / max(total_games, 1)
                
        except Exception as e:
            logger.warning(f"Error calculating league average: {e}")
            return 1.5
    
    def get_league_defense_average(self, week: int) -> float:
        """
        Get league average TDs allowed per game
        
        Args:
            week: NFL week number
            
        Returns:
            League average TDs allowed per game
        """
        try:
            with DatabaseQueryTools(self.db_path) as db:
                defense_stats = db.get_defense_stats(week)
                
                if defense_stats.empty:
                    return 1.5  # Default fallback
                
                return defense_stats['tds_per_game'].mean()
                
        except Exception as e:
            logger.warning(f"Error calculating league defense average: {e}")
            return 1.5
    
    def get_league_stats(self, week: int, year: int = 2025) -> Dict:
        """
        Get comprehensive league statistics
        
        Args:
            week: NFL week number
            year: NFL season year
            
        Returns:
            Dictionary with league statistics
        """
        return {
            'qb_tds_per_game': self.get_league_average_tds(year),
            'defense_tds_allowed_per_game': self.get_league_defense_average(week),
            'week': week,
            'year': year
        }


class VarianceCalculator:
    """Calculates statistical variance and confidence measures"""
    
    def __init__(self):
        """Initialize variance calculator"""
        pass
    
    def calculate_qb_consistency(self, qb_stats: Dict) -> Dict:
        """
        Calculate QB consistency metrics
        
        Args:
            qb_stats: QB statistics dictionary
            
        Returns:
            Dictionary with consistency metrics
        """
        games_played = qb_stats.get('games_played', 1)
        total_tds = qb_stats.get('total_tds', 0)
        
        # Simple consistency based on sample size
        # More games = higher confidence
        if games_played >= 8:
            consistency_score = 0.9
            confidence_level = 'high'
        elif games_played >= 4:
            consistency_score = 0.7
            confidence_level = 'medium'
        else:
            consistency_score = 0.5
            confidence_level = 'low'
        
        # Adjust for TD rate consistency (simplified)
        tds_per_game = total_tds / max(games_played, 1)
        if 0.5 <= tds_per_game <= 2.5:  # Reasonable range
            consistency_score *= 1.1
        
        return {
            'consistency_score': min(1.0, consistency_score),
            'confidence_level': confidence_level,
            'sample_size': games_played,
            'tds_per_game': tds_per_game
        }
    
    def calculate_defense_variance(self, defense_stats: Dict) -> Dict:
        """
        Calculate defense variance metrics
        
        Args:
            defense_stats: Defense statistics dictionary
            
        Returns:
            Dictionary with variance metrics
        """
        tds_per_game = defense_stats.get('tds_per_game', 1.5)
        games_played = defense_stats.get('games_played', 1)
        
        # Defense variance based on TDs allowed
        # Higher TDs allowed = more variance (boom/bust)
        if tds_per_game >= 2.0:
            variance_score = 0.8  # High variance
            predictability = 'low'
        elif tds_per_game >= 1.5:
            variance_score = 0.6  # Medium variance
            predictability = 'medium'
        else:
            variance_score = 0.4  # Low variance
            predictability = 'high'
        
        # Adjust for sample size
        if games_played >= 6:
            variance_score *= 0.9  # More reliable with more games
        
        return {
            'variance_score': variance_score,
            'predictability': predictability,
            'tds_per_game': tds_per_game,
            'games_played': games_played
        }
    
    def calculate_confidence_interval(self, probability: float, variance_score: float, 
                                   consistency_score: float) -> Tuple[float, float]:
        """
        Calculate confidence interval for probability
        
        Args:
            probability: Base probability
            variance_score: Defense variance score
            consistency_score: QB consistency score
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Combine variance and consistency for overall uncertainty
        uncertainty = (variance_score + (1 - consistency_score)) / 2
        
        # Calculate interval width (10-30% of probability)
        interval_width = probability * (0.1 + uncertainty * 0.2)
        
        lower_bound = max(0.05, probability - interval_width)
        upper_bound = min(0.95, probability + interval_width)
        
        return lower_bound, upper_bound


class AdvancedProbabilityModel:
    """Advanced probability model with league context and variance analysis"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize advanced probability model
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path or get_database_path()
        self.league_analyzer = LeagueContextAnalyzer(db_path)
        self.variance_calculator = VarianceCalculator()
    
    def calculate_qb_td_probability(self, qb_stats: Dict, defense_stats: Dict,
                                  matchup_context: Optional[Dict] = None) -> Dict:
        """
        Calculate advanced QB TD probability
        
        Args:
            qb_stats: QB statistics dictionary
            defense_stats: Defense statistics dictionary
            matchup_context: Optional matchup context
            
        Returns:
            Dictionary with advanced probability analysis
        """
        # Get league context
        week = matchup_context.get('week', 1) if matchup_context else 1
        league_stats = self.league_analyzer.get_league_stats(week)
        
        # Base rates
        qb_td_per_game = qb_stats.get('total_tds', 0) / max(qb_stats.get('games_played', 1), 1)
        defense_tds_per_game = defense_stats.get('tds_per_game', league_stats['defense_tds_allowed_per_game'])
        
        # League adjustments
        qb_vs_league = qb_td_per_game / league_stats['qb_tds_per_game']
        def_vs_league = defense_tds_per_game / league_stats['defense_tds_allowed_per_game']
        
        # Weighted composite score
        composite_score = (qb_vs_league * 0.6) + (def_vs_league * 0.4)
        
        # Convert to base probability
        base_probability = self._score_to_probability(composite_score)
        
        # Apply contextual adjustments
        adjusted_probability = self._apply_contextual_adjustments(
            base_probability, matchup_context
        )
        
        # Calculate variance and consistency
        qb_consistency = self.variance_calculator.calculate_qb_consistency(qb_stats)
        defense_variance = self.variance_calculator.calculate_defense_variance(defense_stats)
        
        # Calculate confidence interval
        confidence_interval = self.variance_calculator.calculate_confidence_interval(
            adjusted_probability, defense_variance['variance_score'], 
            qb_consistency['consistency_score']
        )
        
        # Determine overall confidence
        overall_confidence = self._determine_overall_confidence(
            qb_consistency['confidence_level'], defense_variance['predictability']
        )
        
        return {
            'probability': adjusted_probability,
            'confidence': overall_confidence,
            'model_version': 'v2',
            'qb_td_per_game': qb_td_per_game,
            'defense_tds_per_game': defense_tds_per_game,
            'qb_vs_league': qb_vs_league,
            'def_vs_league': def_vs_league,
            'composite_score': composite_score,
            'base_probability': base_probability,
            'adjusted_probability': adjusted_probability,
            'confidence_interval': confidence_interval,
            'qb_consistency': qb_consistency,
            'defense_variance': defense_variance,
            'league_context': league_stats
        }
    
    def _score_to_probability(self, score: float) -> float:
        """Convert composite score to probability using sigmoid function"""
        import math
        
        # Sigmoid function: 1 / (1 + e^(-2*(score-1)))
        # Score of 1.0 (league average) = ~65% probability
        # Score of 1.5 (50% above average) = ~85% probability
        # Score of 0.5 (50% below average) = ~45% probability
        
        probability = 1 / (1 + math.exp(-2 * (score - 1.0)))
        return min(0.95, max(0.05, probability))
    
    def _apply_contextual_adjustments(self, base_probability: float, 
                                    matchup_context: Optional[Dict]) -> float:
        """Apply contextual adjustments to base probability"""
        if not matchup_context:
            return base_probability
        
        adjusted_prob = base_probability
        
        # Home field advantage
        if matchup_context.get('is_home', False):
            adjusted_prob *= 1.1
        
        # Division games (typically more defensive)
        if matchup_context.get('is_division_game', False):
            adjusted_prob *= 0.95
        
        # Prime time games (higher scoring)
        if matchup_context.get('is_prime_time', False):
            adjusted_prob *= 1.05
        
        # Weather adjustments (if available)
        weather_factor = matchup_context.get('weather_factor', 1.0)
        adjusted_prob *= weather_factor
        
        return min(0.95, max(0.05, adjusted_prob))
    
    def _determine_overall_confidence(self, qb_confidence: str, defense_predictability: str) -> str:
        """Determine overall confidence level"""
        confidence_scores = {
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        predictability_scores = {
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        qb_score = confidence_scores.get(qb_confidence, 2)
        def_score = predictability_scores.get(defense_predictability, 2)
        
        combined_score = (qb_score + def_score) / 2
        
        if combined_score >= 2.5:
            return 'high'
        elif combined_score >= 1.5:
            return 'medium'
        else:
            return 'low'


def main():
    """CLI interface for advanced probability models"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced NFL Probability Models')
    parser.add_argument('--week', type=int, help='NFL week number')
    parser.add_argument('--analyze-league', action='store_true', help='Analyze league statistics')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        if args.analyze_league and args.week:
            analyzer = LeagueContextAnalyzer()
            stats = analyzer.get_league_stats(args.week)
            
            print(f"\nLeague Statistics - Week {args.week}")
            print("=" * 40)
            print(f"QB TDs per game: {stats['qb_tds_per_game']:.2f}")
            print(f"Defense TDs allowed per game: {stats['defense_tds_allowed_per_game']:.2f}")
            print(f"Year: {stats['year']}")
            
        else:
            print("Use --analyze-league --week <number> to analyze league statistics")
            
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
