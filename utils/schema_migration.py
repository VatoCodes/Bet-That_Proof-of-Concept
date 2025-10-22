"""Schema Migration for Critical Fixes"""

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil
import logging

logger = logging.getLogger(__name__)


class SchemaMigration:
    def __init__(self, db_path='data/database/nfl_betting.db'):
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
    
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✅ Connected to: {self.db_path}")
    
    def backup_database(self):
        """Create backup before migration"""
        backup_dir = Path('data/database/backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f'nfl_betting_backup_{timestamp}.db'
        
        # Copy database file
        shutil.copy2(self.db_path, backup_path)
        print(f"📦 Backup created: {backup_path}")
        return backup_path
    
    def fix_qb_stats_schema(self):
        """Fix QB stats unique constraint"""
        print("\n🔧 Fixing QB stats schema...")
        
        # 1. Export existing data
        self.cursor.execute("SELECT * FROM qb_stats")
        existing_data = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        print(f"📊 Exported {len(existing_data)} rows")
        
        # 2. Drop old table
        self.cursor.execute("DROP TABLE IF EXISTS qb_stats_old")
        self.cursor.execute("ALTER TABLE qb_stats RENAME TO qb_stats_old")
        print("🗑️  Renamed old table")
        
        # 3. Create new table with correct schema
        self.cursor.execute("""
            CREATE TABLE qb_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qb_name TEXT NOT NULL,
                team TEXT,
                total_tds INTEGER,
                games_played INTEGER,
                is_starter BOOLEAN,
                year INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(qb_name, team, year, scraped_at)
            )
        """)
        print("✅ Created new table with team in unique constraint")
        
        # 4. Re-import data
        if existing_data:
            placeholders = ','.join(['?' for _ in columns])
            self.cursor.executemany(
                f"INSERT INTO qb_stats ({','.join(columns)}) VALUES ({placeholders})",
                existing_data
            )
            print(f"✅ Re-imported {len(existing_data)} rows")
        
        # 5. Drop old table
        self.cursor.execute("DROP TABLE qb_stats_old")
        print("🗑️  Dropped old table")
        
        self.conn.commit()
        print("✅ QB stats schema fixed!\n")
    
    def validate_schema(self):
        """Validate schema after migration"""
        print("🔍 Validating schema...")
        
        # Check QB stats
        self.cursor.execute("PRAGMA table_info(qb_stats)")
        qb_columns = {row[1]: row[2] for row in self.cursor.fetchall()}
        
        assert 'qb_name' in qb_columns
        assert 'team' in qb_columns
        print("✅ QB stats schema valid")
        
        # Check totals (confirm total column exists)
        self.cursor.execute("PRAGMA table_info(odds_totals)")
        totals_columns = {row[1]: row[2] for row in self.cursor.fetchall()}
        
        assert 'total' in totals_columns
        print("✅ Totals schema valid")
        
        # Check unique constraints
        self.cursor.execute("SELECT sql FROM sqlite_master WHERE name='qb_stats'")
        qb_schema = self.cursor.fetchone()[0]
        assert 'team' in qb_schema.split('UNIQUE')[1]
        print("✅ QB stats unique constraint includes team")
        
        print("\n✅ All schema validations passed!")
    
    def close(self):
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    print("🔧 NFL Edge Finder - Schema Migration\n")
    
    migration = SchemaMigration()
    migration.connect()
    
    # Backup first
    backup = migration.backup_database()
    
    # Apply fixes
    migration.fix_qb_stats_schema()
    
    # Validate
    migration.validate_schema()
    
    migration.close()
    
    print("\n✅ Migration complete!")
    print(f"📦 Backup available at: {backup}")
