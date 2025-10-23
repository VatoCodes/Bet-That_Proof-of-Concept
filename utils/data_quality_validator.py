"""
Data quality validation for NFL betting pipeline
Ensures data completeness before analysis
"""

import logging
import sqlite3
from typing import Dict, List, Tuple
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.name_normalizer import normalize_player_name, fuzzy_match_names

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Validates data quality across the pipeline"""

    # Expected ranges for NFL data
    EXPECTED_MATCHUPS_PER_WEEK = (12, 16)  # Min 12 (bye weeks), Max 16
    EXPECTED_TEAMS = 32
    MIN_ODDS_COVERAGE = 0.85  # 85% of games should have odds

    # Game log data expectations (v2 dual-source architecture)
    MIN_STARTING_QBS_PER_WEEK = 20  # Expect ~20-30 starting QBs
    MIN_GAME_LOG_COVERAGE = 0.70  # 70% of starting QBs should have game log data
    MAX_TDS_PER_GAME = 6  # Realistic max TDs in a single game
    MIN_RZ_ATTEMPTS_THRESHOLD = 10  # QBs with 10+ attempts should have RZ data

    def __init__(self, db_path='data/database/nfl_betting.db'):
        """
        Initialize validator

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def _execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Execute a query and return results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def validate_week(self, week: int, season: int = 2025) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for a week's data

        Args:
            week: NFL week number
            season: NFL season year

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check 1: Matchup count
        matchup_count = self._execute_query(
            "SELECT COUNT(*) FROM matchups WHERE week = ?",
            (week,)
        )[0][0]

        if matchup_count < self.EXPECTED_MATCHUPS_PER_WEEK[0]:
            issues.append(
                f"Insufficient matchups: {matchup_count} games "
                f"(expected {self.EXPECTED_MATCHUPS_PER_WEEK[0]}-{self.EXPECTED_MATCHUPS_PER_WEEK[1]})"
            )
        elif matchup_count > self.EXPECTED_MATCHUPS_PER_WEEK[1]:
            issues.append(
                f"Too many matchups: {matchup_count} games "
                f"(expected {self.EXPECTED_MATCHUPS_PER_WEEK[0]}-{self.EXPECTED_MATCHUPS_PER_WEEK[1]})"
            )

        # Check 2: Data freshness (matchups)
        latest_scrape = self._execute_query(
            "SELECT MAX(scraped_at) FROM matchups WHERE week = ?",
            (week,)
        )[0][0]

        if latest_scrape:
            try:
                latest_dt = datetime.fromisoformat(latest_scrape)
                hours_old = (datetime.now() - latest_dt).total_seconds() / 3600

                if hours_old > 48:  # More than 2 days old
                    issues.append(
                        f"Stale matchup data: last scrape {hours_old:.1f} hours ago"
                    )
            except Exception as e:
                issues.append(f"Could not parse scraped_at timestamp: {e}")

        is_valid = len(issues) == 0

        if is_valid:
            logger.info(f"Week {week} data quality: PASS ✓")
        else:
            logger.warning(f"Week {week} data quality: FAIL - {len(issues)} issues")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_valid, issues

    def validate_game_log_completeness(self, week: int, season: int = 2025) -> Tuple[bool, List[str]]:
        """
        Validate game log data completeness for a week (v2 dual-source validation)

        Args:
            week: NFL week number
            season: NFL season year

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check 1: Game log entries exist for current week
        result = self._execute_query("""
            SELECT COUNT(DISTINCT player_name)
            FROM player_game_log
            WHERE season = ? AND week = ?
        """, (season, week))

        game_log_qb_count = result[0][0] if result else 0

        if game_log_qb_count < self.MIN_STARTING_QBS_PER_WEEK:
            issues.append(
                f"Low game log coverage: {game_log_qb_count} QBs "
                f"(expected {self.MIN_STARTING_QBS_PER_WEEK}+ starting QBs)"
            )

        # Check 2: Red zone passes > 0 for QBs with significant passing attempts
        # NOTE: 0 RZ attempts can be legitimate - some QBs never reach red zone
        result = self._execute_query("""
            SELECT COUNT(*)
            FROM player_game_log
            WHERE season = ? AND week = ?
            AND passing_attempts >= ?
            AND red_zone_passes = 0
        """, (season, week, self.MIN_RZ_ATTEMPTS_THRESHOLD))

        zero_rz_count = result[0][0] if result else 0

        # More lenient threshold - only flag if excessive (>8 QBs)
        # Some games legitimately have QBs with 0 RZ attempts
        if zero_rz_count > 8:
            issues.append(
                f"Note: {zero_rz_count} QBs with {self.MIN_RZ_ATTEMPTS_THRESHOLD}+ attempts "
                f"but 0 RZ attempts (may be legitimate - some teams never reach red zone)"
            )

        # Check 3: Realistic TD counts (0-6 per game)
        result = self._execute_query("""
            SELECT COUNT(*), MAX(passing_touchdowns)
            FROM player_game_log
            WHERE season = ? AND week = ?
            AND (passing_touchdowns < 0 OR passing_touchdowns > ?)
        """, (season, week, self.MAX_TDS_PER_GAME))

        if result:
            invalid_tds, max_tds = result[0]
            if invalid_tds > 0:
                issues.append(
                    f"Invalid TD counts: {invalid_tds} QBs "
                    f"(max found: {max_tds}, expected 0-{self.MAX_TDS_PER_GAME})"
                )

        # Check 4: Data freshness (game log)
        result = self._execute_query("""
            SELECT MAX(imported_at)
            FROM player_game_log
            WHERE season = ? AND week = ?
        """, (season, week))

        latest_import = result[0][0] if result and result[0][0] else None

        if latest_import:
            try:
                latest_dt = datetime.fromisoformat(latest_import)
                hours_old = (datetime.now() - latest_dt).total_seconds() / 3600

                if hours_old > 72:  # More than 3 days old for game log
                    issues.append(
                        f"Stale game log data: last import {hours_old:.1f} hours ago"
                    )
            except Exception as e:
                issues.append(f"Could not parse game log imported_at timestamp: {e}")
        elif game_log_qb_count == 0:
            issues.append(f"No game log data found for Week {week}, {season}")

        is_valid = len(issues) == 0

        if is_valid:
            logger.info(f"Week {week} game log quality: PASS ✓ ({game_log_qb_count} QBs)")
        else:
            logger.warning(f"Week {week} game log quality: FAIL - {len(issues)} issues")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_valid, issues

    def validate_dual_source_consistency(self, week: int, season: int = 2025) -> Tuple[bool, List[str]]:
        """
        Validate consistency between play_by_play and player_game_log (dual-source check)

        Args:
            week: NFL week number
            season: NFL season year

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check 1: QBs in game_log should exist in roster
        # Use fuzzy matching to handle name variations (e.g., "Gardner Minshew" vs "Gardner Minshew II")
        result_orphans = self._execute_query("""
            SELECT DISTINCT gl.player_name
            FROM player_game_log gl
            LEFT JOIN player_roster pr
              ON gl.player_name = pr.player_name
              AND gl.season = pr.season
              AND gl.week = pr.week
            WHERE gl.season = ? AND gl.week = ?
            AND pr.player_name IS NULL
        """, (season, week))

        orphan_names = [row[0] for row in result_orphans]

        # Get all roster names for this week to check fuzzy matches
        result_roster = self._execute_query("""
            SELECT DISTINCT player_name
            FROM player_roster
            WHERE season = ? AND week = ? AND position = 'QB'
        """, (season, week))

        roster_names = [row[0] for row in result_roster]

        # Filter out orphans that have fuzzy matches in roster
        true_orphans = []
        for orphan in orphan_names:
            has_fuzzy_match = any(fuzzy_match_names(orphan, roster_name) for roster_name in roster_names)
            if not has_fuzzy_match:
                true_orphans.append(orphan)

        orphan_qbs = len(true_orphans)

        if orphan_qbs > 0:
            issues.append(
                f"Orphan QBs in game_log: {orphan_qbs} QBs not found in roster "
                f"(after fuzzy name matching)"
            )

        # Check 2: QBs with play_by_play data should have game_log data
        result = self._execute_query("""
            SELECT COUNT(DISTINCT pbp.qb_name)
            FROM play_by_play pbp
            LEFT JOIN player_game_log gl
              ON pbp.qb_name = gl.player_name
              AND pbp.season = gl.season
              AND pbp.week = gl.week
            WHERE pbp.week = ? AND pbp.season = ?
            AND pbp.qb_name IS NOT NULL
            AND pbp.qb_name != ''
            AND pbp.play_type = 'PASS'
            AND gl.player_name IS NULL
        """, (week, season))

        missing_game_log = result[0][0] if result else 0

        if missing_game_log > 3:  # Allow some backup QBs to be missing
            issues.append(
                f"QBs in play_by_play missing from game_log: {missing_game_log} QBs"
            )

        # Check 3: Basic data alignment - week should have both sources if recent
        pbp_count = self._execute_query(
            "SELECT COUNT(DISTINCT qb_name) FROM play_by_play WHERE week = ? AND season = ? AND qb_name IS NOT NULL",
            (week, season)
        )[0][0]

        gl_count = self._execute_query(
            "SELECT COUNT(DISTINCT player_name) FROM player_game_log WHERE week = ? AND season = ?",
            (week, season)
        )[0][0]

        if pbp_count > 0 and gl_count == 0:
            issues.append(
                f"Data imbalance: play_by_play has {pbp_count} QBs but game_log has none"
            )
        elif gl_count > 0 and pbp_count == 0:
            issues.append(
                f"Data imbalance: game_log has {gl_count} QBs but play_by_play has none"
            )

        is_valid = len(issues) == 0

        if is_valid:
            logger.info(f"Week {week} dual-source consistency: PASS ✓")
        else:
            logger.warning(f"Week {week} dual-source consistency: FAIL - {len(issues)} issues")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_valid, issues

    def validate_all_weeks(self, season: int = 2025) -> Dict[int, List[str]]:
        """
        Validate all weeks in the season

        Args:
            season: NFL season year

        Returns:
            Dictionary mapping week numbers to lists of issues (only failed weeks)
        """
        results = {}

        for week in range(1, 19):
            is_valid, issues = self.validate_week(week, season)
            if not is_valid:
                results[week] = issues

        return results

    def get_summary_report(self, season: int = 2025, include_game_log: bool = True) -> str:
        """
        Generate a summary report of data quality

        Args:
            season: NFL season year
            include_game_log: Include game log validation (v2 dual-source)

        Returns:
            Formatted report string
        """
        report = [f"\n{'='*60}"]
        report.append(f"DATA QUALITY REPORT - {season} Season")
        if include_game_log:
            report.append("v2 Dual-Source Validation (play_by_play + game_log)")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"{'='*60}\n")

        # Validate matchups and play_by_play (existing validation)
        all_issues = self.validate_all_weeks(season)

        if not all_issues:
            report.append("✓ All weeks passed matchup validation")
        else:
            report.append(f"✗ {len(all_issues)} weeks have matchup issues:\n")

            for week, issues in sorted(all_issues.items()):
                report.append(f"Week {week}:")
                for issue in issues:
                    report.append(f"  - {issue}")
                report.append("")

        # Add game log validation (v2)
        if include_game_log:
            report.append(f"\n{'='*60}")
            report.append("GAME LOG VALIDATION (v2)")
            report.append(f"{'='*60}\n")

            game_log_issues = {}
            for week in range(1, 19):
                is_valid, issues = self.validate_game_log_completeness(week, season)
                if not is_valid:
                    game_log_issues[week] = issues

            if not game_log_issues:
                report.append("✓ All weeks passed game log validation")
            else:
                report.append(f"✗ {len(game_log_issues)} weeks have game log issues:\n")

                for week, issues in sorted(game_log_issues.items()):
                    report.append(f"Week {week}:")
                    for issue in issues:
                        report.append(f"  - {issue}")
                    report.append("")

            # Add dual-source consistency validation
            report.append(f"\n{'='*60}")
            report.append("DUAL-SOURCE CONSISTENCY (v2)")
            report.append(f"{'='*60}\n")

            consistency_issues = {}
            for week in range(1, 19):
                is_valid, issues = self.validate_dual_source_consistency(week, season)
                if not is_valid:
                    consistency_issues[week] = issues

            if not consistency_issues:
                report.append("✓ All weeks passed dual-source consistency validation")
            else:
                report.append(f"✗ {len(consistency_issues)} weeks have consistency issues:\n")

                for week, issues in sorted(consistency_issues.items()):
                    report.append(f"Week {week}:")
                    for issue in issues:
                        report.append(f"  - {issue}")
                    report.append("")

        report.append(f"\n{'='*60}")

        return "\n".join(report)


# CLI interface
if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Data Quality Validator - v2 Dual-Source')
    parser.add_argument('--week', type=int, help='Validate specific week')
    parser.add_argument('--season', type=int, default=2025, help='NFL season year (default: 2025)')
    parser.add_argument('--game-log', action='store_true', help='Validate game log for specific week')
    parser.add_argument('--consistency', action='store_true', help='Validate dual-source consistency for specific week')
    parser.add_argument('--no-game-log', action='store_true', help='Skip game log validation in summary report')

    args = parser.parse_args()

    validator = DataQualityValidator()

    if args.week:
        # Validate specific week
        print(f"\n{'='*60}")
        print(f"Week {args.week} Validation - {args.season} Season")
        print(f"{'='*60}\n")

        # Matchup validation
        print("Matchup Validation:")
        is_valid, issues = validator.validate_week(args.week, args.season)
        if not is_valid:
            print(f"  FAILED:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"  PASSED ✓")

        # Game log validation (if requested or by default)
        if args.game_log or not args.no_game_log:
            print("\nGame Log Validation:")
            is_valid_gl, issues_gl = validator.validate_game_log_completeness(args.week, args.season)
            if not is_valid_gl:
                print(f"  FAILED:")
                for issue in issues_gl:
                    print(f"    - {issue}")
            else:
                print(f"  PASSED ✓")

        # Dual-source consistency (if requested or by default)
        if args.consistency or not args.no_game_log:
            print("\nDual-Source Consistency:")
            is_valid_ds, issues_ds = validator.validate_dual_source_consistency(args.week, args.season)
            if not is_valid_ds:
                print(f"  FAILED:")
                for issue in issues_ds:
                    print(f"    - {issue}")
            else:
                print(f"  PASSED ✓")

        print()

        # Exit with error if any validation failed
        if not is_valid or (not args.no_game_log and not is_valid_gl) or (args.consistency and not is_valid_ds):
            sys.exit(1)
    else:
        # Full season summary
        print(validator.get_summary_report(args.season, include_game_log=not args.no_game_log))
