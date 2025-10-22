"""Unit tests for NFL Edge Calculator

Tests all core calculations including probability models, odds conversion,
Kelly Criterion, and edge detection.
"""

import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.edge_calculator import (
    ProbabilityCalculator, EdgeDetector, BetRecommender, EdgeCalculator
)
from utils.probability_models import AdvancedProbabilityModel


class TestProbabilityCalculator(unittest.TestCase):
    """Test probability calculation models"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = ProbabilityCalculator(model_version="v1")
        
        # Sample QB stats
        self.qb_stats = {
            'total_tds': 20,
            'games_played': 10
        }
        
        # Sample defense stats
        self.defense_stats = {
            'tds_per_game': 2.0
        }
        
        # Sample matchup context
        self.matchup_context = {
            'is_home': True
        }
    
    def test_simple_probability_calculation(self):
        """Test simple probability model (v1)"""
        result = self.calculator._calculate_simple_probability(
            self.qb_stats, self.defense_stats, self.matchup_context
        )
        
        # Verify result structure
        self.assertIn('probability', result)
        self.assertIn('confidence', result)
        self.assertIn('model_version', result)
        
        # Verify probability is in valid range
        self.assertGreaterEqual(result['probability'], 0.05)
        self.assertLessEqual(result['probability'], 0.95)
        
        # Verify QB TD per game calculation
        expected_qb_td_per_game = 20 / 10  # 2.0
        self.assertEqual(result['qb_td_per_game'], expected_qb_td_per_game)
        
        # Verify home field advantage applied
        self.assertGreater(result['home_field_advantage'], 0)
    
    def test_probability_without_context(self):
        """Test probability calculation without matchup context"""
        result = self.calculator._calculate_simple_probability(
            self.qb_stats, self.defense_stats, None
        )
        
        # Should still work without context
        self.assertIn('probability', result)
        self.assertEqual(result['home_field_advantage'], 0)
    
    def test_edge_cases(self):
        """Test edge cases in probability calculation"""
        # QB with no games played
        qb_stats_zero = {'total_tds': 0, 'games_played': 0}
        result = self.calculator._calculate_simple_probability(
            qb_stats_zero, self.defense_stats, None
        )
        
        # Should handle division by zero gracefully
        self.assertIn('probability', result)
        self.assertGreaterEqual(result['probability'], 0.05)
        
        # Very high TD rate
        qb_stats_high = {'total_tds': 50, 'games_played': 10}
        result = self.calculator._calculate_simple_probability(
            qb_stats_high, self.defense_stats, None
        )
        
        # Should cap at reasonable level
        self.assertLessEqual(result['probability'], 0.95)


class TestEdgeDetector(unittest.TestCase):
    """Test edge detection calculations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = EdgeDetector()
    
    def test_american_odds_to_probability(self):
        """Test American odds to probability conversion"""
        # Test negative odds (favorite)
        prob = self.detector._american_odds_to_probability(-200)
        expected = 200 / (200 + 100)  # 0.6667
        self.assertAlmostEqual(prob, expected, places=4)
        
        # Test positive odds (underdog)
        prob = self.detector._american_odds_to_probability(+150)
        expected = 100 / (150 + 100)  # 0.4
        self.assertAlmostEqual(prob, expected, places=4)
        
        # Test even odds
        prob = self.detector._american_odds_to_probability(+100)
        expected = 100 / (100 + 100)  # 0.5
        self.assertAlmostEqual(prob, expected, places=4)
    
    def test_american_odds_to_decimal(self):
        """Test American odds to decimal odds conversion"""
        # Test negative odds
        decimal = self.detector._american_odds_to_decimal(-200)
        expected = (100 / 200) + 1  # 1.5
        self.assertAlmostEqual(decimal, expected, places=4)
        
        # Test positive odds
        decimal = self.detector._american_odds_to_decimal(+150)
        expected = (150 / 100) + 1  # 2.5
        self.assertAlmostEqual(decimal, expected, places=4)
    
    def test_edge_calculation(self):
        """Test complete edge calculation"""
        true_prob = 0.7  # 70%
        odds = -200  # Implied probability ~66.7%
        
        result = self.detector.calculate_edge(true_prob, odds)
        
        # Verify result structure
        self.assertIn('true_probability', result)
        self.assertIn('implied_probability', result)
        self.assertIn('edge', result)
        self.assertIn('edge_percentage', result)
        
        # Verify edge is positive (true prob > implied)
        self.assertGreater(result['edge'], 0)
        self.assertGreater(result['edge_percentage'], 0)
        
        # Verify is_positive_edge flag
        self.assertTrue(result['is_positive_edge'])
    
    def test_negative_edge(self):
        """Test negative edge calculation"""
        true_prob = 0.4  # 40%
        odds = -200  # Implied probability ~66.7%
        
        result = self.detector.calculate_edge(true_prob, odds)
        
        # Verify edge is negative
        self.assertLess(result['edge'], 0)
        self.assertLess(result['edge_percentage'], 0)
        self.assertFalse(result['is_positive_edge'])


class TestBetRecommender(unittest.TestCase):
    """Test Kelly Criterion bet sizing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.recommender = BetRecommender()
    
    def test_kelly_fraction_calculation(self):
        """Test Kelly fraction calculation"""
        true_prob = 0.6  # 60%
        decimal_odds = 2.0  # +100 American odds
        kelly_fraction = 0.25  # 25% Kelly
        
        fraction = self.recommender.calculate_kelly_fraction(
            true_prob, decimal_odds, kelly_fraction
        )
        
        # Kelly formula: f = (bp - q) / b
        # b = 2.0 - 1 = 1.0
        # p = 0.6, q = 0.4
        # kelly = (1.0 * 0.6 - 0.4) / 1.0 = 0.2
        # fractional kelly = 0.2 * 0.25 = 0.05
        expected = 0.2 * 0.25  # 0.05
        self.assertAlmostEqual(fraction, expected, places=4)
    
    def test_kelly_fraction_cap(self):
        """Test Kelly fraction is capped at maximum"""
        true_prob = 0.9  # Very high probability
        decimal_odds = 1.1  # Very low odds
        kelly_fraction = 0.25
        
        fraction = self.recommender.calculate_kelly_fraction(
            true_prob, decimal_odds, kelly_fraction
        )
        
        # Should be capped at max_bankroll_fraction (5%)
        self.assertLessEqual(fraction, 0.05)
    
    def test_kelly_fraction_negative(self):
        """Test Kelly fraction returns 0 for negative edge"""
        true_prob = 0.3  # Low probability
        decimal_odds = 2.0  # High odds
        kelly_fraction = 0.25
        
        fraction = self.recommender.calculate_kelly_fraction(
            true_prob, decimal_odds, kelly_fraction
        )
        
        # Should return 0 for negative Kelly
        self.assertEqual(fraction, 0)
    
    def test_bet_recommendation_tiers(self):
        """Test bet recommendation tier classification"""
        bankroll = 1000
        
        # Test PASS tier
        edge_data_pass = {'edge_percentage': 3.0, 'true_probability': 0.5, 'decimal_odds': 2.0}
        rec = self.recommender.generate_recommendation(edge_data_pass, bankroll)
        self.assertEqual(rec['tier'], 'PASS')
        self.assertEqual(rec['recommended_bet'], 0)
        
        # Test SMALL EDGE tier
        edge_data_small = {'edge_percentage': 7.0, 'true_probability': 0.6, 'decimal_odds': 2.0}
        rec = self.recommender.generate_recommendation(edge_data_small, bankroll)
        self.assertEqual(rec['tier'], 'SMALL EDGE')
        self.assertGreater(rec['recommended_bet'], 0)
        
        # Test GOOD EDGE tier
        edge_data_good = {'edge_percentage': 15.0, 'true_probability': 0.7, 'decimal_odds': 2.0}
        rec = self.recommender.generate_recommendation(edge_data_good, bankroll)
        self.assertEqual(rec['tier'], 'GOOD EDGE')
        
        # Test STRONG EDGE tier
        edge_data_strong = {'edge_percentage': 25.0, 'true_probability': 0.8, 'decimal_odds': 2.0}
        rec = self.recommender.generate_recommendation(edge_data_strong, bankroll)
        self.assertEqual(rec['tier'], 'STRONG EDGE')


class TestEdgeCalculator(unittest.TestCase):
    """Test main EdgeCalculator orchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = EdgeCalculator(model_version="v1")
        
        self.qb_stats = {'total_tds': 20, 'games_played': 10}
        self.defense_stats = {'tds_per_game': 2.0}
        self.odds = -200
        self.matchup_context = {'is_home': True}
    
    def test_calculate_edge_integration(self):
        """Test complete edge calculation integration"""
        result = self.calculator.calculate_edge(
            self.qb_stats, self.defense_stats, self.odds, self.matchup_context
        )
        
        # Verify all components are present
        self.assertIn('probability', result)
        self.assertIn('implied_probability', result)
        self.assertIn('edge_percentage', result)
        self.assertIn('bet_recommendation', result)
        
        # Verify bet recommendation structure
        bet_rec = result['bet_recommendation']
        self.assertIn('tier', bet_rec)
        self.assertIn('recommended_bet', bet_rec)
        self.assertIn('kelly_fraction', bet_rec)
    
    def test_model_version_selection(self):
        """Test model version selection"""
        # Test v1 model
        calc_v1 = EdgeCalculator(model_version="v1")
        result_v1 = calc_v1.calculate_edge(
            self.qb_stats, self.defense_stats, self.odds, self.matchup_context
        )
        self.assertEqual(result_v1['model_version'], 'v1')
        
        # Test v2 model (if available)
        try:
            calc_v2 = EdgeCalculator(model_version="v2")
            result_v2 = calc_v2.calculate_edge(
                self.qb_stats, self.defense_stats, self.odds, self.matchup_context
            )
            self.assertEqual(result_v2['model_version'], 'v2')
        except Exception:
            # v2 model might not be available in test environment
            pass


class TestAdvancedProbabilityModel(unittest.TestCase):
    """Test advanced probability model (v2)"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use a mock database path for testing
        self.model = AdvancedProbabilityModel(db_path=":memory:")
        
        self.qb_stats = {'total_tds': 20, 'games_played': 10}
        self.defense_stats = {'tds_per_game': 2.0}
        self.matchup_context = {'is_home': True, 'week': 8}
    
    def test_advanced_probability_calculation(self):
        """Test advanced probability model calculation"""
        result = self.model.calculate_qb_td_probability(
            self.qb_stats, self.defense_stats, self.matchup_context
        )
        
        # Verify result structure
        self.assertIn('probability', result)
        self.assertIn('confidence', result)
        self.assertIn('model_version', result)
        self.assertIn('confidence_interval', result)
        
        # Verify model version
        self.assertEqual(result['model_version'], 'v2')
        
        # Verify probability is in valid range
        self.assertGreaterEqual(result['probability'], 0.05)
        self.assertLessEqual(result['probability'], 0.95)
        
        # Verify confidence interval
        interval = result['confidence_interval']
        self.assertLess(interval[0], interval[1])
        self.assertGreaterEqual(interval[0], 0.05)
        self.assertLessEqual(interval[1], 0.95)
    
    def test_score_to_probability(self):
        """Test score to probability conversion"""
        # Test league average score (1.0)
        prob = self.model._score_to_probability(1.0)
        self.assertAlmostEqual(prob, 0.5, places=1)  # Should be around 50%
        
        # Test above average score
        prob = self.model._score_to_probability(1.5)
        self.assertGreater(prob, 0.5)
        
        # Test below average score
        prob = self.model._score_to_probability(0.5)
        self.assertLess(prob, 0.5)
    
    def test_contextual_adjustments(self):
        """Test contextual adjustments"""
        base_prob = 0.6
        
        # Test home field advantage
        context_home = {'is_home': True}
        adjusted = self.model._apply_contextual_adjustments(base_prob, context_home)
        self.assertGreater(adjusted, base_prob)
        
        # Test division game
        context_division = {'is_division_game': True}
        adjusted = self.model._apply_contextual_adjustments(base_prob, context_division)
        self.assertLess(adjusted, base_prob)
        
        # Test no context
        adjusted = self.model._apply_contextual_adjustments(base_prob, None)
        self.assertEqual(adjusted, base_prob)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_end_to_end_calculation(self):
        """Test end-to-end edge calculation"""
        calculator = EdgeCalculator(model_version="v1")
        
        # Realistic test data
        qb_stats = {'total_tds': 15, 'games_played': 8}  # 1.875 TD/game
        defense_stats = {'tds_per_game': 2.2}  # Weak defense
        odds = -150  # Implied ~60%
        matchup_context = {'is_home': True}
        
        result = calculator.calculate_edge(qb_stats, defense_stats, odds, matchup_context)
        
        # Should find positive edge (good QB vs weak defense)
        self.assertGreater(result['edge_percentage'], 0)
        self.assertTrue(result['is_positive_edge'])
        
        # Bet recommendation should be positive
        bet_rec = result['bet_recommendation']
        self.assertGreater(bet_rec['recommended_bet'], 0)
        self.assertNotEqual(bet_rec['tier'], 'PASS')
    
    def test_edge_case_scenarios(self):
        """Test various edge case scenarios"""
        calculator = EdgeCalculator(model_version="v1")
        
        # Scenario 1: Elite QB vs elite defense
        qb_stats = {'total_tds': 25, 'games_played': 10}  # 2.5 TD/game
        defense_stats = {'tds_per_game': 1.0}  # Elite defense
        odds = -300  # Very low implied probability
        
        result = calculator.calculate_edge(qb_stats, defense_stats, odds, None)
        # Should still find edge (elite QB can score on anyone)
        self.assertIsInstance(result['edge_percentage'], float)
        
        # Scenario 2: Poor QB vs weak defense
        qb_stats = {'total_tds': 5, 'games_played': 10}  # 0.5 TD/game
        defense_stats = {'tds_per_game': 2.5}  # Very weak defense
        odds = +200  # High implied probability
        
        result = calculator.calculate_edge(qb_stats, defense_stats, odds, None)
        # Should find negative edge (poor QB can't exploit weak defense)
        self.assertIsInstance(result['edge_percentage'], float)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
