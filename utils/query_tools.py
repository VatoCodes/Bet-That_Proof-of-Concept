"""Database Query Tools for NFL Edge Finder"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_database_path

logger = logging.getLogger(__name__)


class DatabaseQueryTools:
    """Provides database query helpers for edge detection and analysis"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize query tools
        
        Args:
            db_path: Path to database file (defaults to config setting)
        """
        self.db_path = db_path or get_database_path()
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        logger.debug(f"Connected to database: {self.db_path}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def get_defense_stats(self, week: int) -> pd.DataFrame:
        """
        Get defense stats for a specific week
        
        Args:
            week: NFL week number
            
        Returns:
            DataFrame with defense statistics
        """
        query = """
            SELECT team_name, pass_tds_allowed, games_played, tds_per_game, scraped_at
            FROM defense_stats 
            WHERE week = ?
            ORDER BY tds_per_game DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(week,))
        return df
    
    def get_weak_defenses(self, week: int, threshold: float = 1.7) -> pd.DataFrame:
        """
        Get teams with weak pass defense (allowing high TDs per game)
        
        Args:
            week: NFL week number
            threshold: Minimum TDs per game to consider "weak"
            
        Returns:
            DataFrame with weak defense teams
        """
        query = """
            SELECT team_name, pass_tds_allowed, games_played, tds_per_game, scraped_at
            FROM defense_stats 
            WHERE week = ? AND tds_per_game >= ?
            ORDER BY tds_per_game DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(week, threshold))
        return df
    
    def get_qb_stats(self, year: int = 2025) -> pd.DataFrame:
        """
        Get QB statistics for a specific year
        
        Args:
            year: NFL season year
            
        Returns:
            DataFrame with QB statistics
        """
        query = """
            SELECT qb_name, team, total_tds, games_played, is_starter, scraped_at
            FROM qb_stats 
            WHERE year = ?
            ORDER BY total_tds DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(year,))
        return df
    
    def get_starting_qbs(self, year: int = 2025) -> pd.DataFrame:
        """
        Get starting QBs only
        
        Args:
            year: NFL season year
            
        Returns:
            DataFrame with starting QB statistics
        """
        query = """
            SELECT qb_name, team, total_tds, games_played, scraped_at
            FROM qb_stats 
            WHERE year = ? AND is_starter = 1
            ORDER BY total_tds DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(year,))
        return df
    
    def get_matchups(self, week: int) -> pd.DataFrame:
        """
        Get matchups for a specific week
        
        Args:
            week: NFL week number
            
        Returns:
            DataFrame with game matchups
        """
        query = """
            SELECT home_team, away_team, game_date, scraped_at
            FROM matchups 
            WHERE week = ?
            ORDER BY game_date
        """
        
        df = pd.read_sql_query(query, self.conn, params=(week,))
        return df
    
    def get_qb_props(self, week: int, sportsbook: Optional[str] = None) -> pd.DataFrame:
        """
        Get QB TD props for a specific week
        
        Args:
            week: NFL week number
            sportsbook: Filter by specific sportsbook (optional)
            
        Returns:
            DataFrame with QB TD props
        """
        query = """
            SELECT qb_name, odds_over_05_td, sportsbook, game, home_team, away_team, 
                   game_time, scraped_at
            FROM qb_props 
            WHERE week = ?
        """
        
        params = [week]
        
        if sportsbook:
            query += " AND sportsbook = ?"
            params.append(sportsbook)
        
        query += " ORDER BY qb_name, sportsbook"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df
    
    def get_spreads(self, week: int, sportsbook: Optional[str] = None) -> pd.DataFrame:
        """
        Get point spreads for a specific week
        
        Args:
            week: NFL week number
            sportsbook: Filter by specific sportsbook (optional)
            
        Returns:
            DataFrame with point spreads
        """
        query = """
            SELECT game, home_team, away_team, team, spread, odds, sportsbook, 
                   game_time, scraped_at
            FROM odds_spreads 
            WHERE week = ?
        """
        
        params = [week]
        
        if sportsbook:
            query += " AND sportsbook = ?"
            params.append(sportsbook)
        
        query += " ORDER BY game, sportsbook"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df
    
    def get_totals(self, week: int, sportsbook: Optional[str] = None) -> pd.DataFrame:
        """
        Get over/under totals for a specific week
        
        Args:
            week: NFL week number
            sportsbook: Filter by specific sportsbook (optional)
            
        Returns:
            DataFrame with totals
        """
        query = """
            SELECT game, home_team, away_team, line_type, total, odds, sportsbook, 
                   game_time, scraped_at
            FROM odds_totals 
            WHERE week = ?
        """
        
        params = [week]
        
        if sportsbook:
            query += " AND sportsbook = ?"
            params.append(sportsbook)
        
        query += " ORDER BY game, sportsbook"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df
    
    def get_line_movement(self, week: int, hours_back: int = 24) -> Dict[str, pd.DataFrame]:
        """
        Get line movement data for a specific week
        
        Args:
            week: NFL week number
            hours_back: How many hours back to look for movement
            
        Returns:
            Dictionary with DataFrames for each market type
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        cutoff_str = cutoff_time.isoformat()
        
        movement_data = {}
        
        # QB Props movement
        query = """
            SELECT qb_name, odds_over_05_td, sportsbook, scraped_at
            FROM qb_props 
            WHERE week = ? AND scraped_at >= ?
            ORDER BY qb_name, sportsbook, scraped_at
        """
        
        movement_data['qb_props'] = pd.read_sql_query(
            query, self.conn, params=(week, cutoff_str)
        )
        
        # Spreads movement
        query = """
            SELECT game, team, spread, odds, sportsbook, scraped_at
            FROM odds_spreads 
            WHERE week = ? AND scraped_at >= ?
            ORDER BY game, sportsbook, scraped_at
        """
        
        movement_data['spreads'] = pd.read_sql_query(
            query, self.conn, params=(week, cutoff_str)
        )
        
        # Totals movement
        query = """
            SELECT game, line_type, total, odds, sportsbook, scraped_at
            FROM odds_totals 
            WHERE week = ? AND scraped_at >= ?
            ORDER BY game, sportsbook, scraped_at
        """
        
        movement_data['totals'] = pd.read_sql_query(
            query, self.conn, params=(week, cutoff_str)
        )
        
        return movement_data
    
    def get_latest_snapshots(self, week: int) -> Dict[str, datetime]:
        """
        Get the latest snapshot time for each data type in a week
        
        Args:
            week: NFL week number
            
        Returns:
            Dictionary mapping table names to latest snapshot times
        """
        tables = ['defense_stats', 'qb_stats', 'matchups', 'odds_spreads', 'odds_totals', 'qb_props']
        latest_times = {}
        
        for table in tables:
            query = f"""
                SELECT MAX(scraped_at) as latest_time
                FROM {table}
                WHERE week = ?
            """
            
            result = pd.read_sql_query(query, self.conn, params=(week,))
            if not result.empty and result['latest_time'].iloc[0]:
                latest_times[table] = pd.to_datetime(result['latest_time'].iloc[0])
            else:
                latest_times[table] = None
        
        return latest_times
    
    def get_scrape_run_history(self, weeks_back: int = 4) -> pd.DataFrame:
        """
        Get scrape run history for recent weeks
        
        Args:
            weeks_back: Number of weeks to look back
            
        Returns:
            DataFrame with scrape run history
        """
        query = """
            SELECT run_timestamp, week, files_scraped, api_requests_used, status, error_message
            FROM scrape_runs
            WHERE week >= (SELECT MAX(week) - ? FROM scrape_runs)
            ORDER BY run_timestamp DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(weeks_back,))
        return df
    
    def find_qb_defense_matchups(self, week: int) -> pd.DataFrame:
        """
        Find QB vs Defense matchups for edge detection
        
        Args:
            week: NFL week number
            
        Returns:
            DataFrame with QB-Defense matchups and key metrics
        """
        query = """
            SELECT 
                m.home_team,
                m.away_team,
                m.game_date,
                qb.qb_name as home_qb,
                qb.team as home_qb_team,
                qb.total_tds as home_qb_tds,
                qb.games_played as home_qb_games,
                def_home.tds_per_game as home_defense_tds_allowed,
                def_away.tds_per_game as away_defense_tds_allowed,
                prop.odds_over_05_td as home_qb_prop_odds,
                prop.sportsbook as prop_sportsbook
            FROM matchups m
            LEFT JOIN qb_stats qb ON qb.team = m.home_team AND qb.year = 2025 AND qb.is_starter = 1
            LEFT JOIN defense_stats def_home ON def_home.team_name = m.home_team AND def_home.week = ?
            LEFT JOIN defense_stats def_away ON def_away.team_name = m.away_team AND def_away.week = ?
            LEFT JOIN qb_props prop ON prop.qb_name = qb.qb_name AND prop.week = ? AND prop.sportsbook = 'FanDuel'
            WHERE m.week = ?
            ORDER BY def_away.tds_per_game DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(week, week, week, week))
        return df
    
    def calculate_edge_opportunities(self, week: int) -> pd.DataFrame:
        """
        Calculate potential edge opportunities for QB TD props
        
        Args:
            week: NFL week number
            
        Returns:
            DataFrame with edge calculations
        """
        # Get QB vs Defense matchups
        matchups = self.find_qb_defense_matchups(week)
        
        if matchups.empty:
            return pd.DataFrame()
        
        edges = []
        
        for _, row in matchups.iterrows():
            if pd.isna(row['home_qb_prop_odds']) or pd.isna(row['away_defense_tds_allowed']):
                continue
            
            # Calculate implied probability from odds
            odds = row['home_qb_prop_odds']
            if odds > 0:
                implied_prob = odds / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
            
            # Calculate true probability based on defense weakness
            # This is a simplified calculation - Phase 2 will have more sophisticated models
            defense_tds_allowed = row['away_defense_tds_allowed']
            qb_tds_per_game = row['home_qb_tds'] / row['home_qb_games'] if row['home_qb_games'] > 0 else 0
            
            # Simple probability calculation (Phase 2 will improve this)
            true_prob = min(0.95, max(0.05, (qb_tds_per_game + defense_tds_allowed) / 2))
            
            # Calculate edge
            edge = true_prob - implied_prob
            
            edges.append({
                'qb_name': row['home_qb'],
                'team': row['home_qb_team'],
                'opponent': row['away_team'],
                'odds': odds,
                'implied_prob': implied_prob,
                'true_prob': true_prob,
                'edge': edge,
                'defense_tds_allowed': defense_tds_allowed,
                'qb_tds_per_game': qb_tds_per_game,
                'sportsbook': row['prop_sportsbook']
            })
        
        return pd.DataFrame(edges).sort_values('edge', ascending=False)
    
    def export_week_data(self, week: int, output_dir: Path) -> Dict[str, Path]:
        """
        Export all data for a week to CSV files
        
        Args:
            week: NFL week number
            output_dir: Directory to save CSV files
            
        Returns:
            Dictionary mapping data type to file path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        exported_files = {}
        
        # Export each data type
        data_types = {
            'defense_stats': self.get_defense_stats(week),
            'qb_stats': self.get_qb_stats(),
            'matchups': self.get_matchups(week),
            'qb_props': self.get_qb_props(week),
            'spreads': self.get_spreads(week),
            'totals': self.get_totals(week)
        }
        
        for data_type, df in data_types.items():
            if not df.empty:
                filename = f"{data_type}_week_{week}.csv"
                filepath = output_dir / filename
                df.to_csv(filepath, index=False)
                exported_files[data_type] = filepath
                logger.info(f"Exported {len(df)} rows to {filepath}")
        
        return exported_files


def main():
    """CLI interface for database queries"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NFL Database Query Tools')
    parser.add_argument('--week', type=int, help='NFL week number')
    parser.add_argument('--weak-defenses', action='store_true', help='Show weak defenses')
    parser.add_argument('--qb-props', action='store_true', help='Show QB props')
    parser.add_argument('--matchups', action='store_true', help='Show matchups')
    parser.add_argument('--edges', action='store_true', help='Calculate edge opportunities')
    parser.add_argument('--export', help='Export week data to directory')
    parser.add_argument('--threshold', type=float, default=1.7, help='Weak defense threshold')
    
    args = parser.parse_args()
    
    if not args.week:
        print("Error: --week is required")
        return 1
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        with DatabaseQueryTools() as db:
            if args.weak_defenses:
                weak_defenses = db.get_weak_defenses(args.week, args.threshold)
                print(f"\nWeak Defenses (Week {args.week}, threshold >= {args.threshold}):")
                print(weak_defenses.to_string(index=False))
            
            if args.qb_props:
                qb_props = db.get_qb_props(args.week)
                print(f"\nQB Props (Week {args.week}):")
                print(qb_props.to_string(index=False))
            
            if args.matchups:
                matchups = db.get_matchups(args.week)
                print(f"\nMatchups (Week {args.week}):")
                print(matchups.to_string(index=False))
            
            if args.edges:
                edges = db.calculate_edge_opportunities(args.week)
                print(f"\nEdge Opportunities (Week {args.week}):")
                if not edges.empty:
                    print(edges.to_string(index=False))
                else:
                    print("No edge opportunities found")
            
            if args.export:
                export_dir = Path(args.export)
                exported = db.export_week_data(args.week, export_dir)
                print(f"\nExported {len(exported)} files to {export_dir}")
                for data_type, filepath in exported.items():
                    print(f"  {data_type}: {filepath}")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
