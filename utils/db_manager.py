"""Database Manager for NFL Edge Finder"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import argparse
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for NFL betting data"""
    
    def __init__(self, db_path='data/database/nfl_betting.db'):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        logger.info(f"✅ Connected to: {self.db_path}")
    
    def create_tables(self):
        """Create all database tables with proper schema"""

        # Player game log table (NEW - for v2 calculator)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_game_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                week INTEGER NOT NULL,
                season INTEGER NOT NULL,
                position TEXT,
                team TEXT,
                opponent TEXT,

                -- Passing stats
                passing_attempts INTEGER DEFAULT 0,
                passing_completions INTEGER DEFAULT 0,
                passing_yards INTEGER DEFAULT 0,
                passing_touchdowns INTEGER DEFAULT 0,
                interceptions INTEGER DEFAULT 0,

                -- Red zone stats (critical for v2 calculator)
                red_zone_passes INTEGER DEFAULT 0,
                red_zone_completions INTEGER DEFAULT 0,

                -- Advanced stats
                deep_ball_attempts INTEGER DEFAULT 0,
                pressured_attempts INTEGER DEFAULT 0,

                -- Rushing stats
                rushing_attempts INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                rushing_touchdowns INTEGER DEFAULT 0,

                -- Metadata
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Unique constraint: one record per player per game
                UNIQUE(player_id, season, week)
            )
        """)

        # Defense stats table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS defense_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                pass_tds_allowed INTEGER,
                games_played INTEGER,
                tds_per_game REAL,
                week INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_name, week, scraped_at)
            )
        """)
        
        # QB stats table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qb_stats (
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
        
        # Matchups table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS matchups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                game_date DATE,
                week INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(home_team, away_team, week, scraped_at)
            )
        """)
        
        # Spreads table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS odds_spreads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game TEXT,
                home_team TEXT,
                away_team TEXT,
                team TEXT,
                spread REAL,
                odds INTEGER,
                sportsbook TEXT,
                game_time TIMESTAMP,
                week INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Totals table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS odds_totals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game TEXT,
                home_team TEXT,
                away_team TEXT,
                line_type TEXT,
                total REAL,
                odds INTEGER,
                sportsbook TEXT,
                game_time TIMESTAMP,
                week INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # QB props table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qb_props (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qb_name TEXT,
                odds_over_05_td INTEGER,
                sportsbook TEXT,
                game TEXT,
                home_team TEXT,
                away_team TEXT,
                game_time TIMESTAMP,
                week INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Scrape runs tracking table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                week INTEGER,
                files_scraped INTEGER,
                api_requests_used INTEGER,
                status TEXT,
                error_message TEXT
            )
        """)
        
        # Create indexes for performance
        indexes = [
            # Player game log indexes (NEW - critical for v2 calculator performance)
            "CREATE INDEX IF NOT EXISTS idx_game_log_player_name ON player_game_log(player_name)",
            "CREATE INDEX IF NOT EXISTS idx_game_log_season_week ON player_game_log(season, week)",
            "CREATE INDEX IF NOT EXISTS idx_game_log_player_season ON player_game_log(player_name, season)",

            # Existing indexes
            "CREATE INDEX IF NOT EXISTS idx_defense_week ON defense_stats(week)",
            "CREATE INDEX IF NOT EXISTS idx_defense_team ON defense_stats(team_name)",
            "CREATE INDEX IF NOT EXISTS idx_qb_year ON qb_stats(year)",
            "CREATE INDEX IF NOT EXISTS idx_qb_name ON qb_stats(qb_name)",
            "CREATE INDEX IF NOT EXISTS idx_matchups_week ON matchups(week)",
            "CREATE INDEX IF NOT EXISTS idx_spreads_week ON odds_spreads(week)",
            "CREATE INDEX IF NOT EXISTS idx_spreads_sportsbook ON odds_spreads(sportsbook)",
            "CREATE INDEX IF NOT EXISTS idx_totals_week ON odds_totals(week)",
            "CREATE INDEX IF NOT EXISTS idx_totals_sportsbook ON odds_totals(sportsbook)",
            "CREATE INDEX IF NOT EXISTS idx_props_week ON qb_props(week)",
            "CREATE INDEX IF NOT EXISTS idx_props_qb ON qb_props(qb_name)",
            "CREATE INDEX IF NOT EXISTS idx_scrape_runs_week ON scrape_runs(week)",
            "CREATE INDEX IF NOT EXISTS idx_scrape_runs_timestamp ON scrape_runs(run_timestamp)"
        ]
        
        for index_sql in indexes:
            self.cursor.execute(index_sql)
        
        self.conn.commit()
        logger.info("✅ Database schema created with indexes")
    
    def insert_from_csv(self, table_name, csv_path, week=None, year=None):
        """
        Insert data from CSV file into database table
        
        Args:
            table_name: Target database table
            csv_path: Path to CSV file
            week: Week number (if applicable)
            year: Year (if applicable)
            
        Returns:
            Number of rows inserted
        """
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            logger.warning(f"⚠️  CSV file not found: {csv_path}")
            return 0
        
        try:
            df = pd.read_csv(csv_path)
            
            # Add metadata columns
            df['scraped_at'] = datetime.now().isoformat()
            
            if week is not None:
                df['week'] = week
            if year is not None:
                df['year'] = year
            
            # Filter columns to match database schema
            if table_name == 'odds_totals':
                # Only keep columns that exist in database schema
                df = df[['game', 'home_team', 'away_team', 'total', 'odds', 'sportsbook', 'game_time']]
            
            # Insert data
            df.to_sql(table_name, self.conn, if_exists='append', index=False)
            
            rows_inserted = len(df)
            logger.info(f"✅ Inserted {rows_inserted} rows into {table_name}")
            return rows_inserted
            
        except Exception as e:
            logger.error(f"❌ Error inserting {csv_path} into {table_name}: {e}")
            return 0
    
    def insert_dataframe(self, table_name, df, week=None, year=None):
        """
        Insert DataFrame with idempotent upsert pattern
        
        For time-series tables, this REPLACES existing records for the
        same natural key. Historical data is preserved in CSV snapshots.
        
        Args:
            table_name: Target database table
            df: pandas DataFrame
            week: Week number (if applicable)
            year: Year (if applicable)
            
        Returns:
            Number of rows inserted
        """
        try:
            # Create a copy to avoid modifying original
            df_copy = df.copy()
            
            # Add metadata columns
            df_copy['scraped_at'] = datetime.now().isoformat()
            
            if week is not None:
                df_copy['week'] = week
            if year is not None:
                df_copy['year'] = year
            
            # Determine natural key based on table
            natural_keys = {
                'defense_stats': ['team_name', 'week'],
                'matchups': ['home_team', 'away_team', 'week'],
                'qb_props': ['qb_name', 'week', 'sportsbook'],
                # odds tables have no unique constraint (multiple books)
            }
            
            # Delete existing records if natural key exists
            if table_name in natural_keys and week:
                keys = natural_keys[table_name]
                for _, row in df_copy.iterrows():
                    where_clause = ' AND '.join([f"{key} = ?" for key in keys])
                    values = [row[key] for key in keys]
                    self.cursor.execute(
                        f"DELETE FROM {table_name} WHERE {where_clause}",
                        values
                    )
            
            # Insert new records
            df_copy.to_sql(table_name, self.conn, if_exists='append', index=False)
            
            rows_inserted = len(df_copy)
            logger.info(f"✅ Upserted {rows_inserted} rows into {table_name}")
            return rows_inserted
            
        except Exception as e:
            logger.error(f"❌ Error upserting DataFrame into {table_name}: {e}")
            return 0
    
    def log_scrape_run(self, week, files_scraped, api_requests_used, status='success', error_message=None):
        """
        Log a scrape run to the database
        
        Args:
            week: NFL week number
            files_scraped: Number of files successfully scraped
            api_requests_used: Number of API requests used
            status: Run status ('success', 'partial', 'failed')
            error_message: Error message if applicable
        """
        try:
            self.cursor.execute("""
                INSERT INTO scrape_runs (week, files_scraped, api_requests_used, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (week, files_scraped, api_requests_used, status, error_message))
            
            self.conn.commit()
            logger.info(f"✅ Logged scrape run: Week {week}, {files_scraped} files, {api_requests_used} API calls")
            
        except Exception as e:
            logger.error(f"❌ Error logging scrape run: {e}")
    
    def get_table_info(self, table_name):
        """
        Get information about a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        try:
            # Get row count
            self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = self.cursor.fetchone()[0]
            
            # Get column info
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = self.cursor.fetchall()
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'columns': [col[1] for col in columns]  # Column names
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting table info for {table_name}: {e}")
            return None
    
    def get_database_stats(self):
        """
        Get overall database statistics
        
        Returns:
            Dictionary with database statistics
        """
        tables = ['defense_stats', 'qb_stats', 'matchups', 'odds_spreads', 'odds_totals', 'qb_props', 'scrape_runs']
        
        stats = {
            'database_path': str(self.db_path),
            'database_size_mb': self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0,
            'tables': {}
        }
        
        for table in tables:
            table_info = self.get_table_info(table)
            if table_info:
                stats['tables'][table] = table_info
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("✅ Database connection closed")

    # ========================================================================
    # PLAYERPROFILE DATA METHODS (Phase 1 - Migration 002)
    # ========================================================================

    def _get_connection(self):
        """Get database connection (create if needed)"""
        if not self.conn:
            self.connect()
        return self.conn

    def upsert_play_by_play(self, df):
        """
        Insert or update play-by-play data (upsert on play_id)

        Args:
            df: DataFrame with play-by-play data

        Returns:
            int: Number of rows inserted
        """
        conn = self._get_connection()

        # SQLite UPSERT: DELETE existing rows with same play_id, then INSERT
        play_ids = df['play_id'].tolist()
        if play_ids:
            placeholders = ','.join('?' * len(play_ids))
            conn.execute(f"DELETE FROM play_by_play WHERE play_id IN ({placeholders})", play_ids)

        # Insert new records
        df.to_sql('play_by_play', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✅ Upserted {len(df)} plays into play_by_play")
        return len(df)

    def upsert_team_metrics(self, df):
        """
        Insert or update team metrics (upsert on team_name, season, week)

        Args:
            df: DataFrame with team metrics

        Returns:
            int: Number of rows inserted
        """
        conn = self._get_connection()

        # Delete existing rows for (team, season, week) tuples
        for _, row in df.iterrows():
            conn.execute(
                "DELETE FROM team_metrics WHERE team_name=? AND season=? AND week=?",
                (row['team_name'], row['season'], row['week'])
            )

        # Insert new records
        df.to_sql('team_metrics', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✅ Upserted {len(df)} team metrics into team_metrics")
        return len(df)

    def upsert_kicker_stats(self, df):
        """
        Insert or update kicker stats (upsert on kicker_name, team, season)

        Args:
            df: DataFrame with kicker stats

        Returns:
            int: Number of rows inserted
        """
        conn = self._get_connection()

        # Delete existing rows for (kicker, team, season) tuples
        for _, row in df.iterrows():
            conn.execute(
                "DELETE FROM kicker_stats WHERE kicker_name=? AND team=? AND season=?",
                (row['kicker_name'], row['team'], row['season'])
            )

        # Insert new records
        df.to_sql('kicker_stats', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✅ Upserted {len(df)} kicker stats into kicker_stats")
        return len(df)

    def upsert_qb_stats_enhanced(self, df):
        """
        Insert or update enhanced QB stats (upsert on qb_name, team, season)

        Args:
            df: DataFrame with enhanced QB stats

        Returns:
            int: Number of rows inserted
        """
        conn = self._get_connection()

        # Delete existing rows for (qb, team, season) tuples
        for _, row in df.iterrows():
            conn.execute(
                "DELETE FROM qb_stats_enhanced WHERE qb_name=? AND team=? AND season=?",
                (row['qb_name'], row['team'], row['season'])
            )

        # Insert new records
        df.to_sql('qb_stats_enhanced', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✅ Upserted {len(df)} QB stats into qb_stats_enhanced")
        return len(df)

    def upsert_player_roster(self, df):
        """
        Insert or update player roster (upsert on player_name, team, season, week)

        Args:
            df: DataFrame with player roster data

        Returns:
            int: Number of rows inserted
        """
        conn = self._get_connection()

        # Delete existing rows for (player, team, season, week) tuples
        for _, row in df.iterrows():
            conn.execute(
                "DELETE FROM player_roster WHERE player_name=? AND team=? AND season=? AND week=?",
                (row['player_name'], row['team'], row['season'], row['week'])
            )

        # Insert new records
        df.to_sql('player_roster', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✅ Upserted {len(df)} roster entries into player_roster")
        return len(df)

    def get_team_metrics(self, team_name, season, week):
        """
        Retrieve team metrics for edge calculations

        Args:
            team_name: Team name
            season: Season year
            week: Week number

        Returns:
            dict or None: Team metrics dictionary or None if not found
        """
        query = """
            SELECT * FROM team_metrics
            WHERE team_name = ? AND season = ? AND week = ?
        """
        conn = self._get_connection()
        result = pd.read_sql_query(query, conn, params=(team_name, season, week))

        if not result.empty:
            return result.to_dict('records')[0]
        return None

    def get_kicker_stats(self, kicker_name, season):
        """
        Retrieve kicker stats for edge calculations

        Args:
            kicker_name: Kicker name
            season: Season year

        Returns:
            dict or None: Kicker stats dictionary or None if not found
        """
        query = """
            SELECT * FROM kicker_stats
            WHERE kicker_name = ? AND season = ?
        """
        conn = self._get_connection()
        result = pd.read_sql_query(query, conn, params=(kicker_name, season))

        if not result.empty:
            return result.to_dict('records')[0]
        return None

    def get_qb_stats_enhanced(self, qb_name, season):
        """
        Retrieve enhanced QB stats for v2 calculator

        Args:
            qb_name: QB name
            season: Season year

        Returns:
            dict or None: QB stats dictionary or None if not found
        """
        query = """
            SELECT * FROM qb_stats_enhanced
            WHERE qb_name = ? AND season = ?
        """
        conn = self._get_connection()
        result = pd.read_sql_query(query, conn, params=(qb_name, season))

        if not result.empty:
            return result.to_dict('records')[0]
        return None

    def get_active_players(self, position, week, season):
        """
        Get active players for given position/week (uses roster table)

        Args:
            position: Position code (QB, K, RB, WR, TE)
            week: Week number
            season: Season year

        Returns:
            list: List of dictionaries with player_name and team
        """
        query = """
            SELECT player_name, team FROM player_roster
            WHERE position = ? AND week = ? AND season = ? AND status = 'Active'
        """
        conn = self._get_connection()
        result = pd.read_sql_query(query, conn, params=(position, week, season))

        return result.to_dict('records')

    def upsert_player_game_log(self, df):
        """
        Insert or update player game log data (upsert on player_id, season, week)

        Args:
            df: DataFrame with player game log data

        Returns:
            int: Number of rows inserted
        """
        conn = self._get_connection()

        # Delete existing rows for (player_id, season, week) tuples
        for _, row in df.iterrows():
            conn.execute(
                "DELETE FROM player_game_log WHERE player_id=? AND season=? AND week=?",
                (row['player_id'], row['season'], row['week'])
            )

        # Insert new records
        df.to_sql('player_game_log', conn, if_exists='append', index=False)
        conn.commit()

        logger.info(f"✅ Upserted {len(df)} game log entries into player_game_log")
        return len(df)

    def get_player_game_log(self, player_name, season, weeks_back=4):
        """
        Retrieve player game log data for last N weeks

        Args:
            player_name: Player name
            season: Season year
            weeks_back: Number of weeks to look back (default: 4)

        Returns:
            DataFrame with game log data or empty DataFrame if not found
        """
        query = """
            SELECT *
            FROM player_game_log
            WHERE player_name = ? AND season = ?
            ORDER BY week DESC
            LIMIT ?
        """
        conn = self._get_connection()
        result = pd.read_sql_query(query, conn, params=(player_name, season, weeks_back))

        return result

    def get_player_game_log_by_week_range(self, player_name, season, start_week, end_week):
        """
        Retrieve player game log data for specific week range

        Args:
            player_name: Player name
            season: Season year
            start_week: Start week (inclusive)
            end_week: End week (inclusive)

        Returns:
            DataFrame with game log data or empty DataFrame if not found
        """
        query = """
            SELECT *
            FROM player_game_log
            WHERE player_name = ? AND season = ? AND week BETWEEN ? AND ?
            ORDER BY week ASC
        """
        conn = self._get_connection()
        result = pd.read_sql_query(query, conn, params=(player_name, season, start_week, end_week))

        return result


def main():
    """CLI interface for database management"""
    parser = argparse.ArgumentParser(description='NFL Database Manager')
    parser.add_argument('--init', action='store_true', help='Initialize database with schema')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--import-csv', help='Import CSV file to database')
    parser.add_argument('--table', help='Target table for CSV import')
    parser.add_argument('--week', type=int, help='Week number for CSV import')
    parser.add_argument('--year', type=int, help='Year for CSV import')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    db = DatabaseManager()
    
    try:
        db.connect()
        
        if args.init:
            db.create_tables()
            print("✅ Database initialized successfully")
        
        elif args.stats:
            stats = db.get_database_stats()
            print("\n" + "=" * 60)
            print("DATABASE STATISTICS")
            print("=" * 60)
            print(f"Database: {stats['database_path']}")
            print(f"Size: {stats['database_size_mb']:.2f} MB")
            print("\nTables:")
            for table_name, table_info in stats['tables'].items():
                print(f"  {table_name}: {table_info['row_count']} rows")
            print("=" * 60)
        
        elif args.import_csv and args.table:
            rows_inserted = db.insert_from_csv(args.table, args.import_csv, args.week, args.year)
            print(f"✅ Imported {rows_inserted} rows from {args.import_csv} to {args.table}")
        
        else:
            # Default: show help
            parser.print_help()
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1
    
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
