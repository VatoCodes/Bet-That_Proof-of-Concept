#!/usr/bin/env python3
"""
Scheduled Data Validator - Runs automatically via cron

Logs validation results for monitoring and trend analysis.
Can be configured to send alerts when critical issues are detected.

Usage:
    python3 utils/scheduled_validator.py

Schedule with cron:
    # Check data quality every day at 8am
    0 8 * * * cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\) && python3 utils/scheduled_validator.py
"""

from pathlib import Path
from datetime import datetime
import json
import sys
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_validator import DataValidator
from utils.data_quality_validator import DataQualityValidator


def validate_game_log_health(week: int, season: int, db_path: str = 'data/database/nfl_betting.db') -> dict:
    """
    Check game log data health for current week (v2 dual-source monitoring)

    Args:
        week: NFL week number
        season: NFL season year
        db_path: Path to database

    Returns:
        Dictionary with game log health metrics
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check 1: Recent import timestamp
        cursor.execute("""
            SELECT MAX(imported_at)
            FROM player_game_log
            WHERE season = ? AND week = ?
        """, (season, week))

        last_import = cursor.fetchone()[0]

        # Check 2: QB count
        cursor.execute("""
            SELECT COUNT(DISTINCT player_name)
            FROM player_game_log
            WHERE season = ? AND week = ?
        """, (season, week))

        qb_count = cursor.fetchone()[0]

        # Check 3: Data completeness (QBs with red zone data)
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN red_zone_passes > 0 THEN 1 ELSE 0 END) as has_rz,
                SUM(passing_touchdowns) as total_tds,
                AVG(passing_touchdowns) as avg_tds
            FROM player_game_log
            WHERE season = ? AND week = ?
            AND passing_attempts > 10
        """, (season, week))

        total, has_rz, total_tds, avg_tds = cursor.fetchone()

        # Check 4: Red zone TD rate sanity check
        cursor.execute("""
            SELECT
                SUM(passing_touchdowns) as tds,
                SUM(red_zone_passes) as rz_attempts
            FROM player_game_log
            WHERE season = ? AND week = ?
        """, (season, week))

        tds, rz_attempts = cursor.fetchone()
        rz_td_rate = (tds / rz_attempts * 100) if rz_attempts and rz_attempts > 0 else 0

        return {
            'last_import': last_import,
            'qb_count': qb_count,
            'completeness': (has_rz / total * 100) if total and total > 0 else 0,
            'total_tds': total_tds if total_tds else 0,
            'avg_tds_per_qb': avg_tds if avg_tds else 0,
            'rz_td_rate': rz_td_rate
        }


def log_validation_results(validator, results, game_log_health=None):
    """Log validation results to file for monitoring

    Args:
        validator: DataValidator instance with results
        results: Validation results dictionary
        game_log_health: Game log health metrics (v2 dual-source)
    """
    log_file = Path(__file__).parent.parent / 'data' / 'validation_log.jsonl'

    # Ensure data directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'configured_week': results['week_mismatch']['configured'],
        'has_data': results['week_mismatch']['has_configured_week'],
        'issue_count': len(validator.issues),
        'warning_count': len(validator.warnings),
        'issues': validator.issues,
        'warnings': validator.warnings,
        'qb_props_count': results['qb_props']['unique_qbs'],
        'completeness': {
            table: data['count']
            for table, data in results['completeness'].items()
        }
    }

    # Add game log health metrics (v2 dual-source)
    if game_log_health:
        log_entry['game_log'] = game_log_health

    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

    return log_file


def send_alert(validator, results):
    """Send alert if critical issues detected

    Args:
        validator: DataValidator instance with results
        results: Validation results dictionary

    Note:
        Currently logs to console. In production, integrate with:
        - Email (SMTP)
        - Slack webhook
        - PagerDuty
        - Custom alerting system
    """
    if validator.issues:
        print("\n🚨 ALERT: Critical data issues detected!")
        print("=" * 60)
        print(f"Week: {results['week_mismatch']['configured']}")
        print(f"Issues: {len(validator.issues)}")
        print()
        for issue in validator.issues:
            print(f"  - {issue}")
        print("=" * 60)
        print()

        # TODO: Implement email/Slack notification
        # Example:
        # send_email(
        #     subject="NFL Edge Finder: Critical Data Issues",
        #     body="\n".join(validator.issues)
        # )


def main():
    """Main entry point for scheduled validator"""
    print()
    print("🔍 Scheduled Data Validation (v2 Dual-Source)")
    print("=" * 60)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # Run validation
    validator = DataValidator()
    results = validator.validate_all()

    # Get current week from results
    current_week = results['week_mismatch']['configured']
    current_season = 2024  # TODO: Make this dynamic based on current date

    # Validate game log health (v2 dual-source)
    print("\n📊 Game Log Health Check (v2):")
    try:
        game_log_health = validate_game_log_health(current_week, current_season)

        print(f"   Week {current_week}, {current_season} Season:")
        print(f"   - QBs in game_log: {game_log_health['qb_count']}")
        print(f"   - RZ data completeness: {game_log_health['completeness']:.1f}%")
        print(f"   - Total TDs: {game_log_health['total_tds']}")
        print(f"   - Avg TDs/QB: {game_log_health['avg_tds_per_qb']:.2f}")
        print(f"   - RZ TD rate: {game_log_health['rz_td_rate']:.1f}%")
        if game_log_health['last_import']:
            print(f"   - Last import: {game_log_health['last_import']}")

        # Check for game log issues
        if game_log_health['qb_count'] < 20:
            print(f"   ⚠️  WARNING: Low QB count ({game_log_health['qb_count']} < 20)")
        if game_log_health['completeness'] < 70:
            print(f"   ⚠️  WARNING: Low RZ completeness ({game_log_health['completeness']:.1f}% < 70%)")
        if game_log_health['qb_count'] >= 20 and game_log_health['completeness'] >= 70:
            print(f"   ✅ Game log health: GOOD")

    except Exception as e:
        print(f"   ❌ Error checking game log health: {e}")
        game_log_health = None

    # Log results (including game log)
    log_file = log_validation_results(validator, results, game_log_health)
    print(f"\n✅ Results logged to: {log_file}")

    # Print summary
    if validator.issues:
        print(f"\n❌ {len(validator.issues)} critical issue(s) found:")
        for issue in validator.issues:
            print(f"   - {issue}")

        # Send alert
        send_alert(validator, results)
    else:
        print("\n✅ No critical issues found")

    if validator.warnings:
        print(f"\n⚠️  {len(validator.warnings)} warning(s):")
        for warning in validator.warnings:
            print(f"   - {warning}")

    print()
    print("=" * 60)
    print(f"Validation complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
