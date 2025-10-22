"""First Half Total Calculator for NFL Betting Edge Detection

This module detects First Half Total Under edges using team offensive/defensive efficiency.
Strategy targets games where BOTH teams are inefficient offensively AND face strong defenses.

Based on LinemakerSports educational content - 92%+ win rate target.
"""

import pandas as pd
import sqlite3
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FirstHalfTotalCalculator:
    """
    Detects First Half Total Under edges using team offensive/defensive efficiency

    Strategy: Target games where BOTH teams are inefficient offensively AND
    face strong defenses (yards per play metrics)

    Expected Output: 2-4 edges per week (8-16 games per season)
    Win Rate Target: 92%+ (LinemakerSports claimed)
    """

    # Team name mapping: full name -> abbreviation
    TEAM_NAME_MAP = {
        'Arizona Cardinals': 'ARI', 'Arizona': 'ARI',
        'Atlanta Falcons': 'ATL', 'Atlanta': 'ATL',
        'Baltimore Ravens': 'BAL', 'Baltimore': 'BAL',
        'Buffalo Bills': 'BUF', 'Buffalo': 'BUF',
        'Carolina Panthers': 'CAR', 'Carolina': 'CAR',
        'Chicago Bears': 'CHI', 'Chicago': 'CHI',
        'Cincinnati Bengals': 'CIN', 'Cincinnati': 'CIN',
        'Cleveland Browns': 'CLE', 'Cleveland': 'CLE',
        'Dallas Cowboys': 'DAL', 'Dallas': 'DAL',
        'Denver Broncos': 'DEN', 'Denver': 'DEN',
        'Detroit Lions': 'DET', 'Detroit': 'DET',
        'Green Bay Packers': 'GB', 'Green Bay': 'GB',
        'Houston Texans': 'HOU', 'Houston': 'HOU',
        'Indianapolis Colts': 'IND', 'Indianapolis': 'IND',
        'Jacksonville Jaguars': 'JAX', 'Jacksonville': 'JAX',
        'Kansas City Chiefs': 'KC', 'Kansas City': 'KC',
        'Las Vegas Raiders': 'LV', 'Las Vegas': 'LV',
        'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR',
        'Miami Dolphins': 'MIA', 'Miami': 'MIA',
        'Minnesota Vikings': 'MIN', 'Minnesota': 'MIN',
        'New England Patriots': 'NE', 'New England': 'NE',
        'New Orleans Saints': 'NO', 'New Orleans': 'NO',
        'New York Giants': 'NYG',
        'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI', 'Philadelphia': 'PHI',
        'Pittsburgh Steelers': 'PIT', 'Pittsburgh': 'PIT',
        'San Francisco 49ers': 'SF', 'San Francisco': 'SF',
        'Seattle Seahawks': 'SEA', 'Seattle': 'SEA',
        'Tampa Bay Buccaneers': 'TB', 'Tampa Bay': 'TB',
        'Tennessee Titans': 'TEN', 'Tennessee': 'TEN',
        'Washington Commanders': 'WAS', 'Washington': 'WAS',
    }

    def __init__(self, db_manager):
        """
        Initialize First Half Total calculator

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager

    def _normalize_team_name(self, team_name: str) -> str:
        """
        Normalize team name to abbreviation format

        Args:
            team_name: Team name (full or abbreviation)

        Returns:
            Team abbreviation
        """
        # If already an abbreviation, return as is
        if len(team_name) <= 3:
            return team_name

        # Look up in mapping
        return self.TEAM_NAME_MAP.get(team_name, team_name)

    def calculate_edges(self, week: int, season: int = 2024,
                       offensive_threshold: int = 8,
                       defensive_threshold: int = 12) -> List[Dict]:
        """
        Find First Half Total Under edges for given week

        Args:
            week: NFL week number
            season: NFL season year
            offensive_threshold: Bottom N teams for offense (default 8)
            defensive_threshold: Top N teams for defense (default 12)

        Returns:
            List of edge dicts with structure:
            {
                'matchup': 'DEN @ LV',
                'strategy': 'First Half Total Under',
                'line': 23.5,
                'recommendation': 'UNDER 23.5',
                'edge_pct': 12.3,
                'confidence': 'HIGH',
                'reasoning': 'Both offenses rank bottom 8 in yards/play...'
            }
        """
        edges = []

        try:
            # Get matchups for the week
            matchups = self._get_matchups(week, season)

            if matchups.empty:
                logger.warning(f"No matchups found for Week {week}, Season {season}")
                return edges

            # Get team rankings for this week
            rankings = self._calculate_team_rankings(week, season)

            if rankings.empty:
                logger.warning(f"No team metrics found for Week {week}, Season {season}")
                return edges

            # Analyze each matchup
            for _, matchup in matchups.iterrows():
                home_team = self._normalize_team_name(matchup['home_team'])
                away_team = self._normalize_team_name(matchup['away_team'])

                # Get rankings for both teams
                home_rankings = rankings[rankings['team_name'] == home_team]
                away_rankings = rankings[rankings['team_name'] == away_team]

                if home_rankings.empty or away_rankings.empty:
                    logger.debug(f"Missing rankings for {home_team} vs {away_team}")
                    continue

                home_off_rank = home_rankings.iloc[0]['offensive_rank']
                home_def_rank = home_rankings.iloc[0]['defensive_rank']
                away_off_rank = away_rankings.iloc[0]['offensive_rank']
                away_def_rank = away_rankings.iloc[0]['defensive_rank']

                # Edge detection criteria:
                # Both offenses rank bottom 8 (rank 25-32 out of 32)
                # Both defenses rank top 12 (rank 1-12 out of 32)
                both_weak_offense = (home_off_rank >= (32 - offensive_threshold + 1) and
                                    away_off_rank >= (32 - offensive_threshold + 1))
                both_strong_defense = (home_def_rank <= defensive_threshold and
                                      away_def_rank <= defensive_threshold)

                if both_weak_offense and both_strong_defense:
                    edge = self._create_edge_recommendation(
                        matchup=matchup,
                        home_off_rank=home_off_rank,
                        home_def_rank=home_def_rank,
                        away_off_rank=away_off_rank,
                        away_def_rank=away_def_rank,
                        home_metrics=home_rankings.iloc[0],
                        away_metrics=away_rankings.iloc[0],
                        week=week
                    )
                    edges.append(edge)
                    logger.info(f"Edge found: {home_team} vs {away_team} - {edge['edge_pct']:.1f}%")

            logger.info(f"Found {len(edges)} First Half Total Under edges for Week {week}")

        except Exception as e:
            logger.error(f"Error calculating First Half Total edges: {e}", exc_info=True)

        return edges

    def _get_matchups(self, week: int, season: int) -> pd.DataFrame:
        """
        Get all matchups for week from matchups table

        Args:
            week: NFL week number
            season: NFL season year

        Returns:
            DataFrame with matchup data
        """
        conn = self.db_manager._get_connection()

        query = """
            SELECT home_team, away_team, game_date
            FROM matchups
            WHERE week = ?
            ORDER BY game_date
        """

        matchups = pd.read_sql_query(query, conn, params=(week,))
        return matchups

    def _calculate_team_rankings(self, week: int, season: int) -> pd.DataFrame:
        """
        Calculate team rankings for offensive and defensive yards per play

        Rankings are calculated for the given week using cumulative season stats.
        Lower offensive yards/play = worse offense = higher rank number
        Lower defensive yards/play = better defense = lower rank number

        Args:
            week: NFL week number
            season: NFL season year

        Returns:
            DataFrame with team rankings
        """
        conn = self.db_manager._get_connection()

        # Get team metrics for all teams at this point in the season
        # Use the latest available data up to this week
        query = """
            SELECT
                team_name,
                offensive_yards_per_play,
                defensive_yards_per_play,
                week
            FROM team_metrics
            WHERE season = ? AND week <= ?
        """

        metrics = pd.read_sql_query(query, conn, params=(season, week))

        if metrics.empty:
            return pd.DataFrame()

        # Get the most recent metrics for each team
        latest_metrics = metrics.sort_values('week', ascending=False).groupby('team_name').first().reset_index()

        # Rank teams (1 = best, 32 = worst)
        # For offense: Higher yards/play is better, so descending order
        latest_metrics['offensive_rank'] = latest_metrics['offensive_yards_per_play'].rank(
            ascending=False, method='min'
        ).astype(int)

        # For defense: Lower yards/play allowed is better, so ascending order
        latest_metrics['defensive_rank'] = latest_metrics['defensive_yards_per_play'].rank(
            ascending=True, method='min'
        ).astype(int)

        return latest_metrics

    def _create_edge_recommendation(self, matchup: pd.Series,
                                   home_off_rank: int, home_def_rank: int,
                                   away_off_rank: int, away_def_rank: int,
                                   home_metrics: pd.Series, away_metrics: pd.Series,
                                   week: int) -> Dict:
        """
        Build structured edge recommendation dict

        Args:
            matchup: Matchup data series
            home_off_rank: Home team offensive rank
            home_def_rank: Home team defensive rank
            away_off_rank: Away team offensive rank
            away_def_rank: Away team defensive rank
            home_metrics: Home team metrics
            away_metrics: Away team metrics
            week: NFL week number

        Returns:
            Dictionary with edge recommendation
        """
        home_team = matchup['home_team']
        away_team = matchup['away_team']

        # Calculate edge percentage based on how extreme the rankings are
        # More extreme rankings (worse offense, better defense) = higher edge
        avg_off_rank = (home_off_rank + away_off_rank) / 2
        avg_def_rank = (home_def_rank + away_def_rank) / 2

        # Edge formula: Higher offense rank (worse) and lower defense rank (better) = more edge
        # Normalize to percentage: Perfect scenario (32 off, 1 def) = ~20% edge
        edge_pct = ((avg_off_rank / 32) * 10) + ((1 - avg_def_rank / 32) * 10)

        # Determine confidence level
        if edge_pct >= 15:
            confidence = 'HIGH'
        elif edge_pct >= 10:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'

        # Build reasoning text
        reasoning = (
            f"{away_team} offense ranks #{away_off_rank} (bottom 8) with "
            f"{away_metrics['offensive_yards_per_play']:.2f} yards/play. "
            f"{home_team} offense ranks #{home_off_rank} (bottom 8) with "
            f"{home_metrics['offensive_yards_per_play']:.2f} yards/play. "
            f"{away_team} defense ranks #{away_def_rank} (top 12) allowing "
            f"{away_metrics['defensive_yards_per_play']:.2f} yards/play. "
            f"{home_team} defense ranks #{home_def_rank} (top 12) allowing "
            f"{home_metrics['defensive_yards_per_play']:.2f} yards/play. "
            f"Low-scoring first half expected."
        )

        # Estimate first half total line (NFL average is ~24 points)
        # Adjust based on offensive efficiency
        avg_yards_per_play = (
            home_metrics['offensive_yards_per_play'] +
            away_metrics['offensive_yards_per_play']
        ) / 2

        # NFL average yards/play is ~5.5, each point below reduces total by ~2 points
        line_adjustment = (5.5 - avg_yards_per_play) * 2
        estimated_line = 24 + line_adjustment

        return {
            'matchup': f"{away_team} @ {home_team}",
            'home_team': home_team,
            'away_team': away_team,
            'strategy': 'First Half Total Under',
            'line': round(estimated_line, 1),
            'recommendation': f"UNDER {round(estimated_line, 1)}",
            'edge_pct': round(edge_pct, 1),
            'confidence': confidence,
            'week': week,
            'game_date': matchup.get('game_date'),
            'reasoning': reasoning,
            'metrics': {
                'home_offensive_rank': home_off_rank,
                'home_defensive_rank': home_def_rank,
                'away_offensive_rank': away_off_rank,
                'away_defensive_rank': away_def_rank,
                'home_yards_per_play': round(home_metrics['offensive_yards_per_play'], 2),
                'away_yards_per_play': round(away_metrics['offensive_yards_per_play'], 2),
                'home_def_yards_per_play': round(home_metrics['defensive_yards_per_play'], 2),
                'away_def_yards_per_play': round(away_metrics['defensive_yards_per_play'], 2)
            }
        }


def main():
    """CLI interface for First Half Total calculator"""
    import argparse
    import sys
    import os

    # Add parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    from utils.db_manager import DatabaseManager

    parser = argparse.ArgumentParser(description='First Half Total Under Edge Calculator')
    parser.add_argument('--week', type=int, required=True, help='NFL week number')
    parser.add_argument('--season', type=int, default=2024, help='NFL season year')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        db = DatabaseManager()
        calculator = FirstHalfTotalCalculator(db)
        edges = calculator.calculate_edges(args.week, args.season)

        print(f"\n🏈 First Half Total Under Edge Finder - Week {args.week}, {args.season}")
        print("=" * 70)

        if not edges:
            print("❌ No edge opportunities found")
            return 0

        print(f"✅ {len(edges)} EDGE OPPORTUNITIES FOUND\n")

        for i, edge in enumerate(edges, 1):
            print(f"{i}. {edge['matchup']}")
            print(f"   Strategy: {edge['strategy']}")
            print(f"   Recommendation: {edge['recommendation']}")
            print(f"   Edge: {edge['edge_pct']:.1f}% | Confidence: {edge['confidence']}")
            print(f"   Reasoning: {edge['reasoning']}")
            print(f"   Rankings:")
            print(f"     {edge['away_team']} Offense: #{edge['metrics']['away_offensive_rank']} | Defense: #{edge['metrics']['away_defensive_rank']}")
            print(f"     {edge['home_team']} Offense: #{edge['metrics']['home_offensive_rank']} | Defense: #{edge['metrics']['home_defensive_rank']}")
            print()

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
