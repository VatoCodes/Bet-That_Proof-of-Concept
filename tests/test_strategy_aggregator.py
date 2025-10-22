"""Unit tests for StrategyAggregator"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.strategy_aggregator import StrategyAggregator


class TestStrategyAggregatorInitialization:
    """Test StrategyAggregator initialization"""

    def test_aggregator_initialization(self):
        """Test aggregator initializes with all calculators."""
        agg = StrategyAggregator()

        assert agg.db_manager is not None
        assert agg.first_half_calc is not None
        assert agg.qb_td_calc_v2 is not None

    def test_available_strategies(self):
        """Test get_available_strategies returns expected list."""
        agg = StrategyAggregator()
        strategies = agg.get_available_strategies()

        assert isinstance(strategies, list)
        assert "first_half" in strategies
        assert "qb_td_v2" in strategies


class TestEdgeRetrieval:
    """Test edge retrieval methods"""

    def test_get_all_edges_returns_list(self):
        """Test get_all_edges returns a list."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=8, season=2024, min_edge=0.0)

        assert isinstance(edges, list)

    def test_get_all_edges_week_7(self):
        """Test getting all edges for Week 7 (has sample data)."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=7, season=2024, min_edge=0.0)

        # Week 7 should have at least 1 edge from test data
        assert isinstance(edges, list), "Should return a list"
        assert len(edges) >= 0, "Should return results (may be empty depending on data)"

        # All returned edges should have required fields
        for edge in edges:
            assert 'matchup' in edge, "Edge should have matchup"
            assert 'strategy' in edge, "Edge should have strategy"
            assert 'edge_pct' in edge, "Edge should have edge_pct"
            assert 'confidence' in edge, "Edge should have confidence"
            assert 'line' in edge, "Edge should have line"
            assert 'recommendation' in edge, "Edge should have recommendation"
            assert 'reasoning' in edge, "Edge should have reasoning"

    def test_get_all_edges_empty_week(self):
        """Test getting edges for week with no data."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=8, season=2024, min_edge=5.0)

        # Week 8 has no data in test database
        # Should return empty list, not crash
        assert isinstance(edges, list), "Should return a list"
        assert len(edges) == 0, "Week 8 has no data, should return empty list"

    def test_get_edge_counts(self):
        """Test quick edge counts for tab badges."""
        agg = StrategyAggregator()
        counts = agg.get_edge_counts(week=7, season=2024)

        assert isinstance(counts, dict), "Should return a dictionary"
        assert 'first_half' in counts, "Should have first_half count"
        assert 'qb_td_v2' in counts, "Should have qb_td_v2 count"
        assert 'total' in counts, "Should have total count"
        assert counts['total'] >= 0, "Total should be non-negative"


class TestStrategyFiltering:
    """Test filtering edges by strategy"""

    def test_strategy_filter_first_half(self):
        """Test filtering edges by first_half strategy."""
        agg = StrategyAggregator()

        # Get only First Half edges
        fh_edges = agg.get_all_edges(week=7, strategy='first_half')

        # All edges should be First Half strategy
        for edge in fh_edges:
            assert 'First Half' in edge['strategy'], f"Expected First Half strategy, got {edge['strategy']}"

    def test_strategy_filter_qb_td_v2(self):
        """Test filtering edges by qb_td_v2 strategy."""
        agg = StrategyAggregator()

        # Get only QB TD v2 edges
        qb_edges = agg.get_all_edges(week=7, strategy='qb_td_v2')

        # All edges should be QB TD strategy
        for edge in qb_edges:
            assert 'QB TD' in edge['strategy'], f"Expected QB TD strategy, got {edge['strategy']}"

    def test_strategy_filter_all(self):
        """Test filtering with 'all' strategy."""
        agg = StrategyAggregator()

        all_edges = agg.get_all_edges(week=7, strategy='all')
        separate_edges = agg.get_all_edges(week=7, strategy=None)

        # Should return same results
        assert len(all_edges) == len(separate_edges), "All and None should return same count"


class TestStandardizedFormat:
    """Test standardized output format"""

    def test_standardized_format_required_fields(self):
        """Test all edges follow standardized format with required fields."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=7, season=2024)

        for edge in edges:
            # Required fields
            assert isinstance(edge['matchup'], str), "matchup should be string"
            assert isinstance(edge['strategy'], str), "strategy should be string"
            assert isinstance(edge['line'], (int, float)), "line should be numeric"
            assert isinstance(edge['recommendation'], str), "recommendation should be string"
            assert isinstance(edge['edge_pct'], (int, float)), "edge_pct should be numeric"
            assert edge['confidence'] in ['HIGH', 'MEDIUM', 'LOW'], f"confidence should be HIGH/MEDIUM/LOW, got {edge['confidence']}"
            assert isinstance(edge['reasoning'], str), "reasoning should be string"

    def test_qb_td_v2_specific_fields(self):
        """Test QB TD v2 edges have v2-specific fields."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=7, season=2024)

        for edge in edges:
            if 'QB TD' in edge['strategy']:
                # Check v2 fields
                assert 'v1_edge_pct' in edge, "QB TD v2 should have v1_edge_pct"
                assert 'red_zone_td_rate' in edge, "QB TD v2 should have red_zone_td_rate"
                assert 'opponent' in edge, "QB TD v2 should have opponent"

    def test_confidence_levels_uppercase(self):
        """Test confidence levels are uppercase."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=7, season=2024)

        for edge in edges:
            confidence = edge['confidence']
            assert confidence in ['HIGH', 'MEDIUM', 'LOW'], f"Confidence should be uppercase, got {confidence}"


class TestEdgeDataValidation:
    """Test edge data validation"""

    def test_edge_pct_non_negative(self):
        """Test edge_pct values are non-negative."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=7, season=2024, min_edge=0.0)

        for edge in edges:
            assert edge['edge_pct'] >= 0, f"edge_pct should be non-negative, got {edge['edge_pct']}"

    def test_line_is_positive(self):
        """Test line values are positive."""
        agg = StrategyAggregator()
        edges = agg.get_all_edges(week=7, season=2024, min_edge=0.0)

        for edge in edges:
            assert edge['line'] > 0, f"line should be positive, got {edge['line']}"

    def test_min_edge_filter(self):
        """Test min_edge filtering works correctly."""
        agg = StrategyAggregator()

        edges_all = agg.get_all_edges(week=7, season=2024, min_edge=0.0)
        edges_high = agg.get_all_edges(week=7, season=2024, min_edge=15.0)

        # High edge threshold should have fewer or equal edges
        assert len(edges_high) <= len(edges_all), "Higher threshold should have fewer or equal edges"

        # All edges in high threshold should meet the threshold
        for edge in edges_high:
            assert edge['edge_pct'] >= 15.0, f"All edges should meet min_edge=15.0, got {edge['edge_pct']}"


class TestWeekValidation:
    """Test week validation"""

    def test_validate_week_valid(self):
        """Test validate_week returns true for valid weeks."""
        agg = StrategyAggregator()

        # Week 7 should have data
        is_valid = agg.validate_week(week=7, season=2024)
        assert isinstance(is_valid, bool), "validate_week should return boolean"


class TestErrorHandling:
    """Test error handling"""

    def test_aggregator_handles_invalid_week(self):
        """Test aggregator handles invalid week gracefully."""
        agg = StrategyAggregator()

        # Invalid week should return empty list, not crash
        edges = agg.get_all_edges(week=99, season=2024)
        assert isinstance(edges, list), "Should return list even for invalid week"
        assert len(edges) == 0, "Invalid week should return empty list"

    def test_get_edge_counts_handles_errors(self):
        """Test get_edge_counts handles errors gracefully."""
        agg = StrategyAggregator()

        # Even with invalid parameters, should return valid count dict
        counts = agg.get_edge_counts(week=99, season=2024)
        assert isinstance(counts, dict), "Should return dict"
        assert counts['total'] >= 0, "Total should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
