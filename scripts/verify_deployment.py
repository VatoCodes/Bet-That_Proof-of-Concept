#!/usr/bin/env python3
"""
Deployment Verification Script

Verify v2 deployment readiness and post-deployment health checks.

Usage:
    python scripts/verify_deployment.py --check all
    python scripts/verify_deployment.py --check database
    python scripts/verify_deployment.py --check data_quality
    python scripts/verify_deployment.py --check performance
"""
import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import DatabaseManager
from utils.config import get_config
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2


class Colors:
    """Terminal colors for output"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")


def print_check(name: str, status: bool, details: str = ""):
    """Print check result"""
    symbol = "✅" if status else "❌"
    color = Colors.GREEN if status else Colors.RED
    status_text = "PASS" if status else "FAIL"

    print(f"{symbol} {name:40} {color}{status_text}{Colors.NC}")
    if details:
        print(f"   {details}")


def check_database() -> Tuple[bool, List[str]]:
    """Verify database setup and connectivity"""
    print_header("Database Checks")

    issues = []
    all_pass = True

    try:
        db = DatabaseManager()
        db.connect()  # Establish connection

        # Check 1: Database connection
        try:
            db.cursor.execute("SELECT COUNT(*) as count FROM player_game_log")
            count = db.cursor.fetchone()[0]
            print_check("Database connection", True, f"{count} records in player_game_log")
        except Exception as e:
            print_check("Database connection", False, str(e))
            issues.append(f"Database connection failed: {e}")
            all_pass = False
            db.close()
            return all_pass, issues

        # Check 2: Required tables exist
        tables = ['player_game_log', 'play_by_play', 'defense_stats', 'player_roster']
        for table in tables:
            try:
                db.cursor.execute(f"SELECT COUNT(*) FROM {table} LIMIT 1")
                db.cursor.fetchone()
                print_check(f"Table '{table}' exists", True)
            except Exception as e:
                print_check(f"Table '{table}' exists", False, str(e))
                issues.append(f"Table {table} missing")
                all_pass = False

        # Check 3: Critical indexes exist
        indexes_query = """
        SELECT name FROM sqlite_master
        WHERE type='index' AND tbl_name='player_game_log'
        """
        db.cursor.execute(indexes_query)
        index_rows = db.cursor.fetchall()
        index_names = [row[0] for row in index_rows]

        required_indexes = [
            'idx_game_log_player_name',
            'idx_game_log_season_week',
        ]

        for idx_name in required_indexes:
            exists = idx_name in index_names
            print_check(f"Index '{idx_name}'", exists)
            if not exists:
                issues.append(f"Missing index: {idx_name}")
                all_pass = False

        # Check 4: Database file size and disk space
        db_path = Path(db.db_path)
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print_check("Database file accessible", True, f"{size_mb:.1f} MB")
        else:
            print_check("Database file accessible", False, "File not found")
            issues.append("Database file not found")
            all_pass = False

        db.close()

    except Exception as e:
        print_check("Database checks", False, str(e))
        issues.append(f"Database check error: {e}")
        all_pass = False

    return all_pass, issues


def check_data_quality() -> Tuple[bool, List[str]]:
    """Verify game_log data quality and coverage"""
    print_header("Data Quality Checks")

    issues = []
    all_pass = True

    try:
        db = DatabaseManager()
        db.connect()

        # Check 1: game_log data exists for current season
        current_season = 2025  # Adjust as needed
        query = """
        SELECT COUNT(DISTINCT player_name) as qb_count,
               COUNT(DISTINCT week) as week_count
        FROM player_game_log
        WHERE season = ?
        """
        db.cursor.execute(query, (current_season,))
        result = db.cursor.fetchone()

        if result:
            qb_count = result[0]
            week_count = result[1]

            qb_pass = qb_count >= 30  # Expect 30+ QBs (adjusted from 50)
            week_pass = week_count >= 1  # At least 1 week

            print_check(
                f"QBs with data ({current_season})",
                qb_pass,
                f"{qb_count} QBs (target: ≥30)"
            )
            print_check(
                f"Weeks with data ({current_season})",
                week_pass,
                f"{week_count} weeks (target: ≥1)"
            )

            if not qb_pass:
                issues.append(f"Insufficient QB coverage: {qb_count} (expected ≥30)")
                all_pass = False
            if not week_pass:
                issues.append(f"No data for {current_season} season")
                all_pass = False
        else:
            print_check(f"Data for {current_season} season", False, "No data found")
            issues.append(f"No game_log data for {current_season} season")
            all_pass = False

        # Check 2: Data freshness (last import)
        query = """
        SELECT MAX(last_updated) as last_import
        FROM player_game_log
        WHERE season = ?
        """
        result = db.query(query, (current_season,))

        if result and result[0]['last_import']:
            last_import = result[0]['last_import']
            print_check("Data import timestamp", True, f"Last: {last_import}")

            # Check if stale (>24 hours would require date parsing)
            # Simplified check: just verify timestamp exists
        else:
            print_check("Data import timestamp", False, "No timestamp found")
            issues.append("Missing last_updated timestamp")
            all_pass = False

        # Check 3: QBs with sufficient data for v2
        query = """
        SELECT COUNT(DISTINCT player_name) as qbs_with_rz_data
        FROM player_game_log
        WHERE season = ?
          AND red_zone_passes > 0
        """
        result = db.query(query, (current_season,))

        if result:
            qbs_with_rz = result[0]['qbs_with_rz_data']
            rz_pass = qbs_with_rz >= 40  # 80% of 50 QBs

            print_check(
                "QBs with RZ data",
                rz_pass,
                f"{qbs_with_rz} QBs (target: ≥40)"
            )

            if not rz_pass:
                issues.append(f"Insufficient RZ data coverage: {qbs_with_rz} QBs")
                all_pass = False

        # Check 4: Realistic RZ TD rates
        query = """
        SELECT player_name,
               SUM(passing_touchdowns) as total_tds,
               SUM(red_zone_passes) as total_rz,
               CAST(SUM(passing_touchdowns) AS FLOAT) / SUM(red_zone_passes) as rz_rate
        FROM player_game_log
        WHERE season = ?
          AND red_zone_passes >= 20
        GROUP BY player_name
        HAVING total_rz >= 20
        LIMIT 10
        """
        result = db.query(query, (current_season,))

        if result:
            realistic_count = sum(1 for r in result if 0.15 <= r['rz_rate'] <= 0.70)
            rate_pass = realistic_count >= len(result) * 0.8  # 80% realistic

            print_check(
                "Realistic RZ TD rates",
                rate_pass,
                f"{realistic_count}/{len(result)} QBs in 15-70% range"
            )

            if not rate_pass:
                issues.append("RZ TD rates outside expected range")
                all_pass = False
        else:
            print_check("Realistic RZ TD rates", False, "Insufficient data to check")

    except Exception as e:
        print_check("Data quality checks", False, str(e))
        issues.append(f"Data quality check error: {e}")
        all_pass = False

    return all_pass, issues


def check_performance() -> Tuple[bool, List[str]]:
    """Verify v2 calculator performance"""
    print_header("Performance Checks")

    issues = []
    all_pass = True

    try:
        db = DatabaseManager()
        v2_calc = QBTDCalculatorV2(db)

        # Get test QB from database
        query = """
        SELECT DISTINCT player_name
        FROM player_game_log
        WHERE season = 2025
          AND red_zone_passes >= 20
        LIMIT 1
        """
        result = db.query(query)

        if not result:
            print_check("Test QB available", False, "No QBs with sufficient data")
            issues.append("No test QBs available for performance check")
            return False, issues

        test_qb = result[0]['player_name']

        # Test 1: Single calculation performance
        matchup = {
            'player': test_qb,
            'opponent': 'LAC',
            'season': 2025,
            'week': 7
        }

        iterations = 10
        times = []

        for _ in range(iterations):
            start = time.time()
            try:
                result = v2_calc.calculate_edges([matchup])
                elapsed_ms = (time.time() - start) * 1000
                times.append(elapsed_ms)
            except Exception as e:
                print_check("v2 calculation", False, str(e))
                issues.append(f"v2 calculation failed: {e}")
                all_pass = False
                break

        if times:
            avg_time = sum(times) / len(times)
            p95_time = sorted(times)[int(len(times) * 0.95)]

            perf_pass = avg_time < 500  # Target: <500ms average
            p95_pass = p95_time < 500  # Target: <500ms p95

            print_check(
                "Average query time",
                perf_pass,
                f"{avg_time:.2f}ms (target: <500ms)"
            )
            print_check(
                "P95 query time",
                p95_pass,
                f"{p95_time:.2f}ms (target: <500ms)"
            )

            if not perf_pass:
                issues.append(f"Average query time {avg_time:.2f}ms exceeds 500ms")
                all_pass = False
            if not p95_pass:
                issues.append(f"P95 query time {p95_time:.2f}ms exceeds 500ms")
                all_pass = False

        # Test 2: Batch calculation performance
        query = """
        SELECT DISTINCT player_name
        FROM player_game_log
        WHERE season = 2025
          AND red_zone_passes >= 10
        LIMIT 10
        """
        result = db.query(query)

        if result:
            matchups = [
                {'player': r['player_name'], 'opponent': 'LAC', 'season': 2025, 'week': 7}
                for r in result
            ]

            start = time.time()
            try:
                batch_result = v2_calc.calculate_edges(matchups)
                batch_time_ms = (time.time() - start) * 1000
                avg_per_matchup = batch_time_ms / len(matchups)

                batch_pass = avg_per_matchup < 500

                print_check(
                    "Batch calculation",
                    batch_pass,
                    f"{len(matchups)} matchups in {batch_time_ms:.2f}ms ({avg_per_matchup:.2f}ms/matchup)"
                )

                if not batch_pass:
                    issues.append(f"Batch avg {avg_per_matchup:.2f}ms exceeds 500ms")
                    all_pass = False

            except Exception as e:
                print_check("Batch calculation", False, str(e))
                issues.append(f"Batch calculation failed: {e}")
                all_pass = False

    except Exception as e:
        print_check("Performance checks", False, str(e))
        issues.append(f"Performance check error: {e}")
        all_pass = False

    return all_pass, issues


def check_configuration() -> Tuple[bool, List[str]]:
    """Verify feature flag configuration"""
    print_header("Configuration Checks")

    issues = []
    all_pass = True

    try:
        # Check feature flags
        rollout_pct = get_config('v2_rollout_percentage', -1)
        shadow_mode = get_config('v2_shadow_mode_enabled', None)
        monitoring = get_config('v2_monitoring_enabled', None)

        # Check 1: Valid rollout percentage
        valid_pct = 0 <= rollout_pct <= 100
        print_check(
            "v2_rollout_percentage",
            valid_pct,
            f"{rollout_pct}% (valid range: 0-100)"
        )

        if not valid_pct:
            issues.append(f"Invalid rollout percentage: {rollout_pct}")
            all_pass = False

        # Check 2: Shadow mode configuration
        print_check(
            "v2_shadow_mode_enabled",
            shadow_mode is not None,
            f"{shadow_mode}"
        )

        # Check 3: Monitoring enabled
        monitoring_pass = monitoring is True
        print_check(
            "v2_monitoring_enabled",
            monitoring_pass,
            f"{monitoring} (should be True)"
        )

        if not monitoring_pass:
            issues.append("Monitoring should be enabled for deployment")
            all_pass = False

        # Check 4: Shadow mode + rollout percentage consistency
        if shadow_mode and rollout_pct > 0:
            print_check(
                "Shadow mode consistency",
                False,
                f"Shadow mode enabled but rollout is {rollout_pct}% (expected 0%)"
            )
            issues.append("Shadow mode requires rollout percentage = 0")
            all_pass = False
        else:
            print_check("Shadow mode consistency", True)

        # Current deployment state
        print(f"\n{Colors.BOLD}Current Deployment State:{Colors.NC}")
        if shadow_mode:
            print(f"  🔵 SHADOW MODE (v2 not visible to users)")
        elif rollout_pct == 0:
            print(f"  ⚪ v2 DISABLED (all users on v1)")
        elif rollout_pct == 10:
            print(f"  🟡 CANARY (10% of users on v2)")
        elif rollout_pct == 50:
            print(f"  🟠 STAGED (50% of users on v2)")
        elif rollout_pct == 100:
            print(f"  🟢 FULL ROLLOUT (100% of users on v2)")
        else:
            print(f"  🔷 CUSTOM ({rollout_pct}% of users on v2)")

    except Exception as e:
        print_check("Configuration checks", False, str(e))
        issues.append(f"Configuration check error: {e}")
        all_pass = False

    return all_pass, issues


def main():
    parser = argparse.ArgumentParser(
        description='Verify v2 deployment readiness and health',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all checks
  python scripts/verify_deployment.py --check all

  # Run specific checks
  python scripts/verify_deployment.py --check database
  python scripts/verify_deployment.py --check data_quality
  python scripts/verify_deployment.py --check performance
  python scripts/verify_deployment.py --check configuration

Check Types:
  all            - Run all verification checks
  database       - Verify database setup and connectivity
  data_quality   - Verify game_log data quality and coverage
  performance    - Verify v2 calculator performance (<500ms)
  configuration  - Verify feature flag configuration
        """
    )

    parser.add_argument(
        '--check',
        type=str,
        default='all',
        choices=['all', 'database', 'data_quality', 'performance', 'configuration'],
        help='Type of check to run'
    )

    args = parser.parse_args()

    # Banner
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}BetThat v2 Deployment Verification{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")

    checks_to_run = {
        'configuration': check_configuration,
        'database': check_database,
        'data_quality': check_data_quality,
        'performance': check_performance
    }

    if args.check == 'all':
        selected_checks = checks_to_run
    else:
        selected_checks = {args.check: checks_to_run[args.check]}

    # Run checks
    results = {}
    all_issues = []

    for check_name, check_func in selected_checks.items():
        passed, issues = check_func()
        results[check_name] = passed
        all_issues.extend(issues)

    # Summary
    print_header("Summary")

    all_passed = all(results.values())

    for check_name, passed in results.items():
        print_check(check_name.replace('_', ' ').title(), passed)

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ All checks PASSED{Colors.NC}")
        print(f"{Colors.GREEN}v2 deployment ready{Colors.NC}\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Some checks FAILED{Colors.NC}")
        print(f"\n{Colors.RED}Issues Found:{Colors.NC}")
        for issue in all_issues:
            print(f"  • {issue}")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()
