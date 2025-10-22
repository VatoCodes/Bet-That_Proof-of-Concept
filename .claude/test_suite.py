#!/usr/bin/env python3
"""
Comprehensive Test Suite for Bet-That Claude Skills

This module provides comprehensive testing for all Claude Skills,
including unit tests, integration tests, and end-to-end validation.
"""

import json
import logging
import asyncio
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import sys
import tempfile
import shutil

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.edge_calculator import EdgeCalculator
from utils.query_tools import DatabaseQueryTools
from config import get_database_path

# Import skill modules
from .claude.skills.line_movement_tracker.scripts.compare_snapshots import SnapshotComparator
from .claude.skills.line_movement_tracker.scripts.movement_analyzer import MovementAnalyzer
from .claude.skills.edge_alerter.scripts.edge_monitor import EdgeMonitor
from .claude.skills.edge_alerter.scripts.notification_system import NotificationSystem
from .claude.skills.dashboard_tester.scripts.test_orchestrator import TestOrchestrator
from .claude.skills.dashboard_tester.scripts.chrome_devtools_mcp import ChromeDevToolsMCP
from .claude.skills.bet_edge_analyzer.scripts.conversational_analyzer import ConversationalAnalyzer
from .claude.skills.data_validator.scripts.enhanced_validator import EnhancedDataValidator
from .claude.skills_orchestrator import BetThatSkillsOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestBetThatSkills(unittest.TestCase):
    """Test suite for Bet-That Claude Skills."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_bet_that.db"
        
        # Initialize test database
        self.db_manager = DatabaseManager(db_path=self.test_db_path)
        self.query_tools = DatabaseQueryTools(db_path=self.test_db_path)
        
        # Create test data
        self._create_test_data()
        
        # Initialize skills with test database
        self.skills = {
            "line_movement_tracker": {
                "snapshot_comparator": SnapshotComparator(db_path=self.test_db_path),
                "movement_analyzer": MovementAnalyzer(db_path=self.test_db_path)
            },
            "edge_alerter": {
                "edge_monitor": EdgeMonitor(db_path=self.test_db_path),
                "notification_system": NotificationSystem(db_path=self.test_db_path)
            },
            "dashboard_tester": {
                "test_orchestrator": TestOrchestrator(db_path=self.test_db_path),
                "chrome_mcp": ChromeDevToolsMCP(db_path=self.test_db_path)
            },
            "bet_edge_analyzer": {
                "conversational_analyzer": ConversationalAnalyzer(db_path=self.test_db_path)
            },
            "data_validator": {
                "enhanced_validator": EnhancedDataValidator(db_path=self.test_db_path)
            }
        }
        
        # Initialize orchestrator
        self.orchestrator = BetThatSkillsOrchestrator(db_path=self.test_db_path)
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_test_data(self):
        """Create test data for testing."""
        try:
            # Create test tables and insert sample data
            self.db_manager.create_tables()
            
            # Insert sample QB stats
            qb_stats_data = [
                {
                    "qb_name": "Test QB 1",
                    "team": "Test Team 1",
                    "week": 1,
                    "tds": 2,
                    "attempts": 30,
                    "completions": 20,
                    "passing_yards": 250
                },
                {
                    "qb_name": "Test QB 2",
                    "team": "Test Team 2",
                    "week": 1,
                    "tds": 1,
                    "attempts": 25,
                    "completions": 18,
                    "passing_yards": 200
                }
            ]
            
            for qb_stat in qb_stats_data:
                self.db_manager.insert_qb_stats(qb_stat)
            
            # Insert sample defense stats
            defense_stats_data = [
                {
                    "team": "Test Team 1",
                    "week": 1,
                    "tds_allowed": 1,
                    "attempts_faced": 25,
                    "completions_allowed": 15,
                    "passing_yards_allowed": 180
                },
                {
                    "team": "Test Team 2",
                    "week": 1,
                    "tds_allowed": 2,
                    "attempts_faced": 30,
                    "completions_allowed": 20,
                    "passing_yards_allowed": 250
                }
            ]
            
            for defense_stat in defense_stats_data:
                self.db_manager.insert_defense_stats(defense_stat)
            
            # Insert sample odds
            odds_data = [
                {
                    "qb_name": "Test QB 1",
                    "team": "Test Team 1",
                    "week": 1,
                    "over_odds": -110,
                    "under_odds": -110
                },
                {
                    "qb_name": "Test QB 2",
                    "team": "Test Team 2",
                    "week": 1,
                    "over_odds": -120,
                    "under_odds": -100
                }
            ]
            
            for odds in odds_data:
                self.db_manager.insert_odds(odds)
            
            # Insert sample matchups
            matchup_data = [
                {
                    "home_team": "Test Team 1",
                    "away_team": "Test Team 2",
                    "week": 1,
                    "game_time": "2025-01-01 20:00:00"
                }
            ]
            
            for matchup in matchup_data:
                self.db_manager.insert_matchup(matchup)
            
            logger.info("Test data created successfully")
            
        except Exception as e:
            logger.error(f"Error creating test data: {e}")
            raise
    
    def test_line_movement_tracker_snapshot_comparison(self):
        """Test line movement tracker snapshot comparison."""
        try:
            comparator = self.skills["line_movement_tracker"]["snapshot_comparator"]
            
            # Test snapshot comparison
            result = asyncio.run(comparator.compare_snapshots(
                week=1,
                snapshot_type="odds"
            ))
            
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("timestamp", result)
            
            logger.info("✅ Line movement tracker snapshot comparison test passed")
            
        except Exception as e:
            logger.error(f"❌ Line movement tracker snapshot comparison test failed: {e}")
            self.fail(f"Line movement tracker snapshot comparison test failed: {e}")
    
    def test_line_movement_tracker_movement_analysis(self):
        """Test line movement tracker movement analysis."""
        try:
            analyzer = self.skills["line_movement_tracker"]["movement_analyzer"]
            
            # Test movement analysis
            result = asyncio.run(analyzer.analyze_movements(
                week=1,
                threshold=0.05
            ))
            
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("timestamp", result)
            
            logger.info("✅ Line movement tracker movement analysis test passed")
            
        except Exception as e:
            logger.error(f"❌ Line movement tracker movement analysis test failed: {e}")
            self.fail(f"Line movement tracker movement analysis test failed: {e}")
    
    def test_edge_alerter_edge_monitoring(self):
        """Test edge alerter edge monitoring."""
        try:
            monitor = self.skills["edge_alerter"]["edge_monitor"]
            
            # Test edge monitoring
            result = asyncio.run(monitor.monitor_edges(
                week=1,
                threshold=0.05
            ))
            
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("timestamp", result)
            
            logger.info("✅ Edge alerter edge monitoring test passed")
            
        except Exception as e:
            logger.error(f"❌ Edge alerter edge monitoring test failed: {e}")
            self.fail(f"Edge alerter edge monitoring test failed: {e}")
    
    def test_edge_alerter_notification_system(self):
        """Test edge alerter notification system."""
        try:
            notification_system = self.skills["edge_alerter"]["notification_system"]
            
            # Test notification system status
            status = notification_system.get_notification_status()
            
            self.assertIsInstance(status, dict)
            self.assertIn("email", status)
            self.assertIn("sms", status)
            
            logger.info("✅ Edge alerter notification system test passed")
            
        except Exception as e:
            logger.error(f"❌ Edge alerter notification system test failed: {e}")
            self.fail(f"Edge alerter notification system test failed: {e}")
    
    def test_dashboard_tester_test_orchestrator(self):
        """Test dashboard tester test orchestrator."""
        try:
            test_orchestrator = self.skills["dashboard_tester"]["test_orchestrator"]
            
            # Test API tests
            result = asyncio.run(test_orchestrator.run_api_tests(
                base_url="http://localhost:5001"
            ))
            
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("timestamp", result)
            
            logger.info("✅ Dashboard tester test orchestrator test passed")
            
        except Exception as e:
            logger.error(f"❌ Dashboard tester test orchestrator test failed: {e}")
            self.fail(f"Dashboard tester test orchestrator test failed: {e}")
    
    def test_dashboard_tester_chrome_mcp(self):
        """Test dashboard tester Chrome MCP integration."""
        try:
            chrome_mcp = self.skills["dashboard_tester"]["chrome_mcp"]
            
            # Test Chrome MCP status
            status = chrome_mcp.get_notification_status()
            
            self.assertIsInstance(status, dict)
            
            logger.info("✅ Dashboard tester Chrome MCP test passed")
            
        except Exception as e:
            logger.error(f"❌ Dashboard tester Chrome MCP test failed: {e}")
            self.fail(f"Dashboard tester Chrome MCP test failed: {e}")
    
    def test_bet_edge_analyzer_conversational_analysis(self):
        """Test bet edge analyzer conversational analysis."""
        try:
            analyzer = self.skills["bet_edge_analyzer"]["conversational_analyzer"]
            
            # Test edge analysis
            test_edge_data = {
                "qb_name": "Test QB 1",
                "defense_name": "Test Defense 1",
                "week": 1,
                "true_probability": 0.65,
                "implied_probability": 0.55,
                "edge_percentage": 0.10,
                "confidence_level": "medium",
                "bet_size": 0.05,
                "expected_value": 50.0
            }
            
            result = analyzer.analyze_edge_opportunity(test_edge_data)
            
            self.assertIsInstance(result, str)
            self.assertIn("Betting Edge Analysis", result)
            
            logger.info("✅ Bet edge analyzer conversational analysis test passed")
            
        except Exception as e:
            logger.error(f"❌ Bet edge analyzer conversational analysis test failed: {e}")
            self.fail(f"Bet edge analyzer conversational analysis test failed: {e}")
    
    def test_data_validator_enhanced_validation(self):
        """Test data validator enhanced validation."""
        try:
            validator = self.skills["data_validator"]["enhanced_validator"]
            
            # Test enhanced validation
            result = validator.validate_all()
            
            self.assertIsInstance(result, dict)
            self.assertIn("timestamp", result)
            self.assertIn("overall_status", result)
            
            logger.info("✅ Data validator enhanced validation test passed")
            
        except Exception as e:
            logger.error(f"❌ Data validator enhanced validation test failed: {e}")
            self.fail(f"Data validator enhanced validation test failed: {e}")
    
    def test_orchestrator_skill_execution(self):
        """Test orchestrator skill execution."""
        try:
            # Test executing a specific skill
            result = asyncio.run(self.orchestrator.execute_skill(
                "data_validator",
                "validate_all"
            ))
            
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("timestamp", result)
            
            logger.info("✅ Orchestrator skill execution test passed")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator skill execution test failed: {e}")
            self.fail(f"Orchestrator skill execution test failed: {e}")
    
    def test_orchestrator_system_status(self):
        """Test orchestrator system status."""
        try:
            # Test getting system status
            status = asyncio.run(self.orchestrator.get_system_status())
            
            self.assertIsInstance(status, dict)
            self.assertIn("system_status", status)
            self.assertIn("timestamp", status)
            
            logger.info("✅ Orchestrator system status test passed")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator system status test failed: {e}")
            self.fail(f"Orchestrator system status test failed: {e}")
    
    def test_orchestrator_scheduled_tasks(self):
        """Test orchestrator scheduled tasks."""
        try:
            # Test running scheduled tasks
            result = asyncio.run(self.orchestrator.run_scheduled_tasks())
            
            self.assertIsInstance(result, dict)
            self.assertIn("status", result)
            self.assertIn("timestamp", result)
            
            logger.info("✅ Orchestrator scheduled tasks test passed")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator scheduled tasks test failed: {e}")
            self.fail(f"Orchestrator scheduled tasks test failed: {e}")

class TestSkillIntegration(unittest.TestCase):
    """Test integration between skills."""
    
    def setUp(self):
        """Set up integration test environment."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_bet_that.db"
        
        # Initialize orchestrator
        self.orchestrator = BetThatSkillsOrchestrator(db_path=self.test_db_path)
    
    def tearDown(self):
        """Clean up integration test environment."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_data_validator_to_edge_analyzer_integration(self):
        """Test integration between data validator and edge analyzer."""
        try:
            # Run data validation first
            validation_result = asyncio.run(self.orchestrator.execute_skill(
                "data_validator",
                "validate_all"
            ))
            
            self.assertEqual(validation_result["status"], "completed")
            
            # Then run edge analysis
            analysis_result = asyncio.run(self.orchestrator.execute_skill(
                "bet_edge_analyzer",
                "analyze_week_edges",
                week=1,
                threshold=0.05
            ))
            
            self.assertIsInstance(analysis_result, dict)
            
            logger.info("✅ Data validator to edge analyzer integration test passed")
            
        except Exception as e:
            logger.error(f"❌ Data validator to edge analyzer integration test failed: {e}")
            self.fail(f"Data validator to edge analyzer integration test failed: {e}")
    
    def test_line_movement_tracker_to_edge_alerter_integration(self):
        """Test integration between line movement tracker and edge alerter."""
        try:
            # Run line movement tracking
            movement_result = asyncio.run(self.orchestrator.execute_skill(
                "line_movement_tracker",
                "compare_snapshots",
                week=1
            ))
            
            self.assertIsInstance(movement_result, dict)
            
            # Then run edge monitoring
            monitoring_result = asyncio.run(self.orchestrator.execute_skill(
                "edge_alerter",
                "monitor_edges",
                week=1
            ))
            
            self.assertIsInstance(monitoring_result, dict)
            
            logger.info("✅ Line movement tracker to edge alerter integration test passed")
            
        except Exception as e:
            logger.error(f"❌ Line movement tracker to edge alerter integration test failed: {e}")
            self.fail(f"Line movement tracker to edge alerter integration test failed: {e}")
    
    def test_full_workflow_integration(self):
        """Test full workflow integration."""
        try:
            # Run full scheduled tasks
            result = asyncio.run(self.orchestrator.run_scheduled_tasks())
            
            self.assertEqual(result["status"], "completed")
            self.assertIn("results", result)
            
            # Check that all expected skills were executed
            expected_skills = ["data_validator", "line_movement_tracker", "edge_alerter", "dashboard_tester"]
            for skill in expected_skills:
                self.assertIn(skill, result["results"])
            
            logger.info("✅ Full workflow integration test passed")
            
        except Exception as e:
            logger.error(f"❌ Full workflow integration test failed: {e}")
            self.fail(f"Full workflow integration test failed: {e}")

def run_comprehensive_tests():
    """Run comprehensive test suite."""
    try:
        logger.info("🧪 Starting comprehensive test suite...")
        
        # Create test suite
        test_suite = unittest.TestSuite()
        
        # Add unit tests
        test_suite.addTest(unittest.makeSuite(TestBetThatSkills))
        
        # Add integration tests
        test_suite.addTest(unittest.makeSuite(TestSkillIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)
        
        # Print summary
        logger.info(f"📊 Test Summary:")
        logger.info(f"Tests run: {result.testsRun}")
        logger.info(f"Failures: {len(result.failures)}")
        logger.info(f"Errors: {len(result.errors)}")
        
        if result.failures:
            logger.error("❌ Test failures:")
            for test, traceback in result.failures:
                logger.error(f"  {test}: {traceback}")
        
        if result.errors:
            logger.error("❌ Test errors:")
            for test, traceback in result.errors:
                logger.error(f"  {test}: {traceback}")
        
        if result.wasSuccessful():
            logger.info("✅ All tests passed!")
            return True
        else:
            logger.error("❌ Some tests failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error running comprehensive tests: {e}")
        return False

def main():
    """Main function for running tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bet-That Claude Skills Test Suite")
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive test suite')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.unit:
        # Run unit tests only
        test_suite = unittest.TestSuite()
        test_suite.addTest(unittest.makeSuite(TestBetThatSkills))
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)
        
    elif args.integration:
        # Run integration tests only
        test_suite = unittest.TestSuite()
        test_suite.addTest(unittest.makeSuite(TestSkillIntegration))
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)
        
    elif args.comprehensive:
        # Run comprehensive test suite
        success = run_comprehensive_tests()
        sys.exit(0 if success else 1)
        
    else:
        print("Use --help to see available options")

if __name__ == "__main__":
    main()
