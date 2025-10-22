"""Custom Reports Importer - Kicker and QB Stats

Imports kicker and QB stats from PlayerProfiler Custom Reports CSVs.
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CustomReportsImporter:
    """Import kicker and QB stats from custom reports"""

    def __init__(self, db_manager):
        """Initialize importer"""
        self.db_manager = db_manager

    def import_season(self, season, csv_path):
        """
        Import custom reports for given season

        Args:
            season: Season year
            csv_path: Path to custom reports CSV

        Returns:
            tuple: (kicker_count, qb_count)
        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"Custom reports file not found: {csv_path}")

        logger.info(f"   Loading custom reports from {csv_path.name}...")

        # Load CSV
        df = pd.read_csv(csv_path, low_memory=False)

        # Import kickers
        kicker_count = self._import_kickers(df, season)

        # Import QBs
        qb_count = self._import_qbs(df, season)

        return kicker_count, qb_count

    def _import_kickers(self, df, season):
        """Import kicker stats"""
        # Filter to kickers
        kickers = df[df['position'] == 'K'].copy()

        if kickers.empty:
            logger.warning("   No kickers found in custom reports")
            return 0

        # Helper function to safely get column with fallback
        def safe_get(col_name, default=0):
            if col_name in kickers.columns:
                return kickers[col_name].fillna(default)
            else:
                return default

        # Extract relevant columns (many kicker columns may not exist)
        kicker_stats = pd.DataFrame({
            'kicker_name': kickers['name'],
            'team': kickers['current_team'],
            'season': season,
            'fg_attempts': safe_get('field_goal_attempts', 0),
            'fg_made': safe_get('field_goals_made', 0),
            'fg_pct': safe_get('field_goal_percentage', 0) / 100 if 'field_goal_percentage' in kickers.columns else 0,
            'long_fg': safe_get('longest_field_goal', 0),
            'points_total': safe_get('fantasy_points', 0),
            'points_per_game': safe_get('fantasy_points_per_game', 0),
            'attempts_per_game': safe_get('field_goal_attempts_per_game', 0),
            'games_played': safe_get('games_played', 0),
            'fg_pct_percentile': 50,  # Will calculate later
            'points_per_game_percentile': 50  # Will calculate later
        })

        # Remove duplicates (keep first occurrence)
        kicker_stats = kicker_stats.drop_duplicates(subset=['kicker_name', 'team', 'season'], keep='first')

        # Calculate percentiles
        if len(kicker_stats) > 0:
            kicker_stats['fg_pct_percentile'] = kicker_stats['fg_pct'].rank(pct=True) * 100
            kicker_stats['points_per_game_percentile'] = kicker_stats['points_per_game'].rank(pct=True) * 100
            logger.info(f"   Found {len(kicker_stats)} unique kickers")

        # Save snapshot
        self._save_snapshot(kicker_stats, 'kicker_stats', season)

        # Upsert to database
        self.db_manager.upsert_kicker_stats(kicker_stats)

        return len(kicker_stats)

    def _import_qbs(self, df, season):
        """Import QB enhanced stats"""
        # Filter to QBs
        qbs = df[df['position'] == 'QB'].copy()

        if qbs.empty:
            logger.warning("   No QBs found in custom reports")
            return 0

        # Helper function to safely get column with fallback
        def safe_get(col_name, default=0):
            if col_name in qbs.columns:
                return qbs[col_name].fillna(default)
            else:
                return default

        # Calculate passing TDs per game if column exists
        if 'passing_touchdowns' in qbs.columns and 'games_played' in qbs.columns:
            passing_tds_per_game = (qbs['passing_touchdowns'].fillna(0) / qbs['games_played'].fillna(1)).replace([float('inf'), float('-inf')], 0)
        else:
            passing_tds_per_game = 0

        # Extract relevant columns
        qb_stats = pd.DataFrame({
            'qb_name': qbs['name'],
            'team': qbs['current_team'],
            'season': season,
            'games_played': safe_get('games_played', 0),
            'total_pass_attempts': safe_get('pass_attempts', 0),
            'total_completions': safe_get('completions', 0),
            'total_pass_yards': safe_get('pass_yards', 0),
            'total_pass_tds': safe_get('passing_touchdowns', 0),
            'passing_tds_per_game': passing_tds_per_game,
            'red_zone_accuracy_rating': safe_get('red_zone_accuracy_rating', 0),
            'deep_ball_completion_pct': safe_get('deep_ball_completion_percentage', 0) / 100 if 'deep_ball_completion_percentage' in qbs.columns else 0,
            'clean_pocket_accuracy': safe_get('clean_pocket_accuracy_rating', 0) / 100 if 'clean_pocket_accuracy_rating' in qbs.columns else 0,
            'pressured_completion_pct': safe_get('pressured_completion_percentage', 0) / 100 if 'pressured_completion_percentage' in qbs.columns else 0,
            'avg_depth_of_target': safe_get('average_depth_of_target', 0),
            'first_half_tds': 0,  # Will calculate from PBP later
            'first_half_td_rate': 0,
            'third_down_conversion_pct': safe_get('third_down_conversion_rate', 0) / 100 if 'third_down_conversion_rate' in qbs.columns else 0,
            'fourth_quarter_tds': 0,
            'td_rate_vs_top10_defenses': 0,
            'td_rate_vs_bottom10_defenses': 0
        })

        # Remove duplicates (keep first occurrence)
        qb_stats = qb_stats.drop_duplicates(subset=['qb_name', 'team', 'season'], keep='first')
        logger.info(f"   Found {len(qb_stats)} unique QBs")

        # Save snapshot
        self._save_snapshot(qb_stats, 'qb_stats_enhanced', season)

        # Upsert to database
        self.db_manager.upsert_qb_stats_enhanced(qb_stats)

        return len(qb_stats)

    def _save_snapshot(self, df, table_name, season):
        """Save historical snapshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = Path('data/historical/playerprofile_imports')
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = snapshot_dir / f'{table_name}_{season}_{timestamp}.csv'
        df.to_csv(snapshot_path, index=False)

        logger.info(f"   Snapshot saved: {snapshot_path.name}")
