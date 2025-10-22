#!/usr/bin/env python3
"""
Comprehensive tests for duplicate prevention system

Tests the complete duplicate prevention pipeline:
1. Operational database has no duplicates
2. Historical snapshots preserve all scrapes
3. Scrapers are idempotent
4. UNIQUE constraints prevent duplicates
5. Data validator detects duplicates
"""

import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.data_validator import DataValidator
from utils.historical_storage import HistoricalStorage
from config import get_database_path


class TestDuplicatePrevention(unittest.TestCase):
    """Test suite for duplicate prevention system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test database
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db_path = self.test_dir / "test_nfl_betting.db"
        
        # Copy real database to test location
        real_db_path = get_database_path()
        if real_db_path.exists():
            shutil.copy2(real_db_path, self.test_db_path)
        
        # Initialize test database manager
        self.db = DatabaseManager(db_path=self.test_db_path)
        self.db.connect()
        
        # Initialize validator
        self.validator = DataValidator(project_root=self.test_dir)
        
        # Initialize historical storage
        self.historical = HistoricalStorage()
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'db'):
            self.db.close()
        
        # Remove temporary directory
        if hasattr(self, 'test_dir') and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_no_duplicates_in_operational_db(self):
        """Operational database should have no duplicates"""
        # Check defense_stats duplicates
        duplicates = self.db.cursor.execute("""
            SELECT team_name, COUNT(*) as count
            FROM defense_stats
            WHERE week = 7
            GROUP BY team_name
            HAVING COUNT(*) > 1
        """).fetchall()
        
        self.assertEqual(len(duplicates), 0, 
                        f"Found duplicates in defense_stats: {duplicates}")
        
        # Check matchups duplicates
        duplicates = self.db.cursor.execute("""
            SELECT home_team, away_team, COUNT(*) as count
            FROM matchups
            WHERE week = 7
            GROUP BY home_team, away_team
            HAVING COUNT(*) > 1
        """).fetchall()
        
        self.assertEqual(len(duplicates), 0, 
                        f"Found duplicates in matchups: {duplicates}")
        
        # Check qb_props duplicates
        duplicates = self.db.cursor.execute("""
            SELECT qb_name, week, sportsbook, COUNT(*) as count
            FROM qb_props
            WHERE week = 7
            GROUP BY qb_name, week, sportsbook
            HAVING COUNT(*) > 1
        """).fetchall()
        
        self.assertEqual(len(duplicates), 0, 
                        f"Found duplicates in qb_props: {duplicates}")
    
    def test_unique_constraints_prevent_duplicates(self):
        """UNIQUE constraints should prevent duplicate inserts"""
        # Test defense_stats constraint
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.cursor.execute("""
                INSERT INTO defense_stats (team_name, week, pass_tds_allowed, games_played, tds_per_game, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('Chiefs', 7, 20.0, 7, 2.9, datetime.now().isoformat()))
            
            self.db.cursor.execute("""
                INSERT INTO defense_stats (team_name, week, pass_tds_allowed, games_played, tds_per_game, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('Chiefs', 7, 21.0, 7, 3.0, datetime.now().isoformat()))
            
            self.db.conn.commit()
        
        # Test matchups constraint
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.cursor.execute("""
                INSERT INTO matchups (home_team, away_team, week, scraped_at)
                VALUES (?, ?, ?, ?)
            """, ('Chiefs', 'Bills', 7, datetime.now().isoformat()))
            
            self.db.cursor.execute("""
                INSERT INTO matchups (home_team, away_team, week, scraped_at)
                VALUES (?, ?, ?, ?)
            """, ('Chiefs', 'Bills', 7, datetime.now().isoformat()))
            
            self.db.conn.commit()
    
    def test_data_validator_detects_duplicates(self):
        """Data validator should detect duplicates"""
        # Insert a duplicate manually (bypassing constraints)
        self.db.cursor.execute("""
            INSERT INTO defense_stats (team_name, week, pass_tds_allowed, games_played, tds_per_game, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test Team', 7, 20.0, 7, 2.9, datetime.now().isoformat()))
        
        self.db.cursor.execute("""
            INSERT INTO defense_stats (team_name, week, pass_tds_allowed, games_played, tds_per_game, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Test Team', 7, 21.0, 7, 3.0, datetime.now().isoformat()))
        
        self.db.conn.commit()
        
        # Run validator
        results = self.validator.validate_all(week=7)
        
        # Check that duplicates were detected
        self.assertGreater(results['duplicates']['defense_duplicates'], 0,
                          "Validator should detect duplicates")
        
        # Clean up
        self.db.cursor.execute("DELETE FROM defense_stats WHERE team_name = 'Test Team'")
        self.db.conn.commit()
    
    def test_historical_snapshots_exist(self):
        """Historical storage should preserve all scrapes"""
        # Check that historical snapshots exist for week 7
        historical_dir = Path("data/historical/2025/week_7")
        
        if historical_dir.exists():
            # Count CSV files
            csv_files = list(historical_dir.glob("*.csv"))
            self.assertGreater(len(csv_files), 0, 
                             "Historical snapshots should exist")
            
            # Check for defense_stats snapshots
            defense_files = list(historical_dir.glob("defense_stats_*.csv"))
            self.assertGreater(len(defense_files), 0, 
                             "Defense stats snapshots should exist")
            
            # Check for matchups snapshots
            matchup_files = list(historical_dir.glob("matchups_*.csv"))
            self.assertGreater(len(matchup_files), 0, 
                             "Matchups snapshots should exist")
    
    def test_db_manager_idempotent_insert(self):
        """Database manager should handle idempotent inserts"""
        # Create test data
        test_data = pd.DataFrame({
            'team_name': ['Test Team 1', 'Test Team 2'],
            'pass_tds_allowed': [20.0, 25.0],
            'games_played': [7, 7],
            'tds_per_game': [2.9, 3.6]
        })
        
        # Insert data
        rows_inserted = self.db.insert_dataframe('defense_stats', test_data, week=7)
        self.assertEqual(rows_inserted, 2)
        
        # Insert same data again (should replace, not duplicate)
        rows_inserted = self.db.insert_dataframe('defense_stats', test_data, week=7)
        self.assertEqual(rows_inserted, 2)
        
        # Check that only 2 records exist (not 4)
        count = self.db.cursor.execute("""
            SELECT COUNT(*) FROM defense_stats 
            WHERE team_name IN ('Test Team 1', 'Test Team 2') AND week = 7
        """).fetchone()[0]
        
        self.assertEqual(count, 2, "Should have exactly 2 records, not 4")
        
        # Clean up
        self.db.cursor.execute("""
            DELETE FROM defense_stats 
            WHERE team_name IN ('Test Team 1', 'Test Team 2') AND week = 7
        """)
        self.db.conn.commit()
    
    def test_cleanup_script_functionality(self):
        """Test the cleanup script functionality"""
        # Insert duplicate data manually
        self.db.cursor.execute("""
            INSERT INTO defense_stats (team_name, week, pass_tds_allowed, games_played, tds_per_game, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Cleanup Test', 7, 20.0, 7, 2.9, '2025-10-21T10:00:00'))
        
        self.db.cursor.execute("""
            INSERT INTO defense_stats (team_name, week, pass_tds_allowed, games_played, tds_per_game, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('Cleanup Test', 7, 21.0, 7, 3.0, '2025-10-21T11:00:00'))
        
        self.db.conn.commit()
        
        # Verify duplicates exist
        count = self.db.cursor.execute("""
            SELECT COUNT(*) FROM defense_stats 
            WHERE team_name = 'Cleanup Test' AND week = 7
        """).fetchone()[0]
        self.assertEqual(count, 2)
        
        # Run cleanup script
        from scripts.cleanup_duplicates import DuplicateCleaner
        cleaner = DuplicateCleaner(db_path=self.test_db_path)
        cleaner.connect()
        
        result = cleaner.clean_table('defense_stats', week=7, dry_run=False)
        cleaner.close()
        
        # Verify cleanup worked
        count = self.db.cursor.execute("""
            SELECT COUNT(*) FROM defense_stats 
            WHERE team_name = 'Cleanup Test' AND week = 7
        """).fetchone()[0]
        self.assertEqual(count, 1, "Should have exactly 1 record after cleanup")
        
        # Clean up
        self.db.cursor.execute("""
            DELETE FROM defense_stats 
            WHERE team_name = 'Cleanup Test' AND week = 7
        """)
        self.db.conn.commit()
    
    def test_historical_storage_snapshot(self):
        """Test historical storage snapshot functionality"""
        # Create test CSV file
        test_data = pd.DataFrame({
            'team_name': ['Test Team'],
            'pass_tds_allowed': [20.0],
            'games_played': [7],
            'tds_per_game': [2.9]
        })
        
        test_csv_path = self.test_dir / "test_defense_stats.csv"
        test_data.to_csv(test_csv_path, index=False)
        
        # Save snapshot
        snapshot_path = self.historical.save_snapshot(
            test_csv_path, week=7, snapshot_type='test'
        )
        
        self.assertIsNotNone(snapshot_path, "Snapshot should be saved")
        self.assertTrue(Path(snapshot_path).exists(), "Snapshot file should exist")
        
        # Verify snapshot content
        snapshot_data = pd.read_csv(snapshot_path)
        pd.testing.assert_frame_equal(test_data, snapshot_data)
    
    def test_data_completeness_after_cleanup(self):
        """Data should be complete after cleanup"""
        # Check defense_stats completeness
        count = self.db.cursor.execute("""
            SELECT COUNT(*) FROM defense_stats WHERE week = 7
        """).fetchone()[0]
        
        unique_count = self.db.cursor.execute("""
            SELECT COUNT(DISTINCT team_name) FROM defense_stats WHERE week = 7
        """).fetchone()[0]
        
        self.assertEqual(count, unique_count, 
                        "Total count should equal unique count (no duplicates)")
        self.assertEqual(count, 32, "Should have exactly 32 teams")
        
        # Check matchups completeness
        count = self.db.cursor.execute("""
            SELECT COUNT(*) FROM matchups WHERE week = 7
        """).fetchone()[0]
        
        self.assertGreater(count, 0, "Should have at least one matchup")
    
    def test_edge_detection_data_quality(self):
        """Edge detection should use clean data"""
        # Query data as edge detection would
        weak_defenses = self.db.cursor.execute("""
            SELECT team_name, tds_per_game
            FROM defense_stats
            WHERE week = 7
            ORDER BY tds_per_game DESC
            LIMIT 5
        """).fetchall()
        
        self.assertEqual(len(weak_defenses), 5, "Should have exactly 5 weak defenses")
        
        # Verify no duplicate team names
        team_names = [row[0] for row in weak_defenses]
        self.assertEqual(len(team_names), len(set(team_names)), 
                        "Should have no duplicate team names")
    
    def test_schema_constraints_exist(self):
        """UNIQUE constraints should exist in database"""
        # Check that UNIQUE indexes exist
        indexes = self.db.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type = 'index' AND name LIKE 'idx_%_unique'
        """).fetchall()
        
        index_names = [row[0] for row in indexes]
        
        expected_indexes = [
            'idx_defense_stats_unique',
            'idx_matchups_unique', 
            'idx_qb_props_unique'
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_names, 
                         f"Missing UNIQUE index: {expected_index}")


class TestScraperIdempotency(unittest.TestCase):
    """Test scraper idempotency (requires working scrapers)"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db_path = self.test_dir / "test_nfl_betting.db"
        
        # Initialize test database manager
        self.db = DatabaseManager(db_path=self.test_db_path)
        self.db.connect()
        
        # Create test tables
        self.db.cursor.execute("""
            CREATE TABLE IF NOT EXISTS defense_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                pass_tds_allowed INTEGER,
                games_played INTEGER,
                tds_per_game REAL,
                week INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_name, week)
            )
        """)
        self.db.conn.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'db'):
            self.db.close()
        
        if hasattr(self, 'test_dir') and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_scraper_idempotency_pattern(self):
        """Test the scraper idempotency pattern"""
        # Create test data
        test_data = pd.DataFrame({
            'team_name': ['Chiefs', 'Bills', 'Dolphins'],
            'pass_tds_allowed': [20, 18, 22],
            'games_played': [7, 7, 7],
            'tds_per_game': [2.9, 2.6, 3.1]
        })
        
        # Simulate running scraper 3 times
        for i in range(3):
            rows_inserted = self.db.insert_dataframe('defense_stats', test_data, week=7)
            self.assertEqual(rows_inserted, 3)
        
        # Verify only 3 records exist (not 9)
        count = self.db.cursor.execute("""
            SELECT COUNT(*) FROM defense_stats WHERE week = 7
        """).fetchone()[0]
        
        self.assertEqual(count, 3, "Should have exactly 3 records after 3 runs")
        
        # Verify unique teams
        unique_count = self.db.cursor.execute("""
            SELECT COUNT(DISTINCT team_name) FROM defense_stats WHERE week = 7
        """).fetchone()[0]
        
        self.assertEqual(unique_count, 3, "Should have exactly 3 unique teams")


def run_comprehensive_tests():
    """Run all duplicate prevention tests"""
    print("🧪 Running Comprehensive Duplicate Prevention Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(TestDuplicatePrevention))
    suite.addTest(unittest.makeSuite(TestScraperIdempotency))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED - Duplicate prevention system working correctly")
    else:
        print("❌ SOME TESTS FAILED - Check duplicate prevention implementation")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
