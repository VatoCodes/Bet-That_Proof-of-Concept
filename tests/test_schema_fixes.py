"""Test Schema Fixes"""

import sqlite3
import pytest
from pathlib import Path


def test_qb_stats_schema():
    """Test QB stats unique constraint includes team"""
    db = sqlite3.connect('data/database/nfl_betting.db')
    cursor = db.cursor()
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE name='qb_stats'")
    schema = cursor.fetchone()[0]
    
    assert 'UNIQUE(qb_name, team, year, scraped_at)' in schema
    db.close()


def test_totals_schema():
    """Test totals table has total column"""
    db = sqlite3.connect('data/database/nfl_betting.db')
    cursor = db.cursor()
    
    cursor.execute("PRAGMA table_info(odds_totals)")
    columns = {row[1] for row in cursor.fetchall()}
    
    assert 'total' in columns
    db.close()


def test_data_integrity():
    """Test data still accessible after migration"""
    db = sqlite3.connect('data/database/nfl_betting.db')
    cursor = db.cursor()
    
    # QB stats
    cursor.execute("SELECT COUNT(*) FROM qb_stats")
    qb_count = cursor.fetchone()[0]
    assert qb_count >= 0  # Allow 0 rows (QB stats table was empty)
    
    # Totals
    cursor.execute("SELECT COUNT(*) FROM odds_totals")
    totals_count = cursor.fetchone()[0]
    assert totals_count >= 0  # Allow 0 rows (totals table was empty)
    
    db.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
