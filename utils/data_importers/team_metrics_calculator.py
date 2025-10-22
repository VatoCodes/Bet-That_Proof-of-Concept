"""Team Metrics Calculator

Calculates team performance metrics from play-by-play data.
This is a materialized view pattern - pre-calculate metrics for fast edge detection.
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class TeamMetricsCalculator:
    """Calculate team metrics from play-by-play data"""

    def __init__(self, db_manager):
        """Initialize calculator"""
        self.db_manager = db_manager

    def calculate_all_weeks(self, season):
        """
        Calculate team metrics for all weeks in season

        Args:
            season: Season year

        Returns:
            int: Total number of team-week metrics calculated
        """
        total_metrics = 0

        # Calculate metrics for weeks 1-18
        for week in range(1, 19):
            try:
                metrics_df = self.calculate_for_week(season, week)
                if metrics_df is not None and not metrics_df.empty:
                    total_metrics += len(metrics_df)
            except Exception as e:
                logger.warning(f"   Could not calculate metrics for Week {week}: {e}")

        return total_metrics

    def calculate_for_week(self, season, week):
        """
        Calculate team metrics from play-by-play data up through given week

        Args:
            season: Season year
            week: Week number (metrics calculated through this week)

        Returns:
            DataFrame: Team metrics
        """
        conn = self.db_manager._get_connection()

        # Get all plays for season up to and including this week
        plays_df = pd.read_sql_query(
            """
            SELECT * FROM play_by_play
            WHERE season = ? AND week <= ?
            """,
            conn,
            params=(season, week)
        )

        if plays_df.empty:
            logger.warning(f"      No play-by-play data for Week {week}")
            return None

        # Get unique teams
        teams = pd.concat([plays_df['offense'], plays_df['defense']]).unique()
        metrics_list = []

        for team in teams:
            metrics = self._calculate_team_metrics(team, plays_df, season, week)
            if metrics:
                metrics_list.append(metrics)

        if not metrics_list:
            return None

        metrics_df = pd.DataFrame(metrics_list)

        # Calculate percentiles
        if len(metrics_df) > 1:
            metrics_df['offensive_ypp_percentile'] = metrics_df['offensive_yards_per_play'].rank(pct=True) * 100
            metrics_df['defensive_ypp_percentile'] = metrics_df['defensive_yards_per_play'].rank(pct=True, ascending=False) * 100
        else:
            metrics_df['offensive_ypp_percentile'] = 50
            metrics_df['defensive_ypp_percentile'] = 50

        # Save snapshot
        self._save_snapshot(metrics_df, season, week)

        # Upsert to database
        self.db_manager.upsert_team_metrics(metrics_df)

        return metrics_df

    def _calculate_team_metrics(self, team, plays_df, season, week):
        """Calculate metrics for a single team"""
        # Offensive metrics (team as offense)
        team_offense = plays_df[plays_df['offense'] == team]
        off_plays = len(team_offense)
        off_yards = team_offense['yards_gained'].sum()
        off_ypp = off_yards / off_plays if off_plays > 0 else 0

        # First half specific (quarters 1-2)
        first_half = team_offense[team_offense['quarter'].isin([1, 2])]
        fh_yards = first_half['yards_gained'].sum()
        games_played = team_offense['game_key'].nunique()
        fh_points_avg = 0  # Simplified - would need TD/FG data

        # Defensive metrics (team as defense)
        team_defense = plays_df[plays_df['defense'] == team]
        def_plays = len(team_defense)
        def_yards = team_defense['yards_gained'].sum()
        def_ypp = def_yards / def_plays if def_plays > 0 else 0

        return {
            'team_name': team,
            'season': season,
            'week': week,
            'offensive_plays': off_plays,
            'offensive_yards': off_yards,
            'offensive_yards_per_play': round(off_ypp, 2),
            'offensive_first_downs': 0,
            'offensive_touchdowns': 0,
            'first_half_points_avg': round(fh_points_avg, 2),
            'first_half_yards_avg': round(fh_yards / max(games_played, 1), 2),
            'first_half_scoring_plays': 0,
            'red_zone_attempts': 0,
            'red_zone_touchdowns': 0,
            'red_zone_efficiency_pct': 0,
            'defensive_plays': def_plays,
            'defensive_yards_allowed': def_yards,
            'defensive_yards_per_play': round(def_ypp, 2),
            'defensive_touchdowns_allowed': 0,
            'defensive_first_downs_allowed': 0,
            'fg_attempts': 0,
            'fg_made': 0,
            'fg_pct': 0,
            'kicker_points_avg': 0,
            'fg_blocks_allowed': 0,
            'offensive_ypp_percentile': 50,  # Will calculate later
            'defensive_ypp_percentile': 50   # Will calculate later
        }

    def _save_snapshot(self, df, season, week):
        """Save historical snapshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = Path('data/historical/playerprofile_imports')
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = snapshot_dir / f'team_metrics_{season}_week{week}_{timestamp}.csv'
        df.to_csv(snapshot_path, index=False)
