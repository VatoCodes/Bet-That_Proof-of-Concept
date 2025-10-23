"""
Comprehensive system verification script
Validates all components of the NFL data pipeline
"""

import sys
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_quality_validator import DataQualityValidator
from utils.week_manager import WeekManager
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def check_schedulers():
    """Check if exactly 2 schedulers are running"""
    import subprocess

    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    scheduler_lines = [line for line in result.stdout.split('\n')
                       if 'scheduler' in line and 'grep' not in line and 'python' in line]

    count = len(scheduler_lines)

    if count == 2:
        logger.info("✓ Schedulers: 2 processes running (correct)")
        return True
    else:
        logger.warning(f"⚠ Schedulers: {count} processes running (expected 2)")
        return False


def check_database_structure():
    """Check database tables and indexes"""
    db_path = Path('data/database/nfl_betting.db')

    if not db_path.exists():
        logger.error("✗ Database: File not found")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    required_tables = ['matchups']
    missing_tables = [t for t in required_tables if t not in tables]

    if missing_tables:
        logger.error(f"✗ Database: Missing tables: {missing_tables}")
        return False

    logger.info(f"✓ Database: {len(tables)} tables found")

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    required_indexes = ['idx_matchups_week', 'idx_matchups_teams']
    missing_indexes = [i for i in required_indexes if i not in indexes]

    if missing_indexes:
        logger.warning(f"⚠ Database: Missing recommended indexes: {missing_indexes}")
    else:
        logger.info(f"✓ Database: Performance indexes installed")

    conn.close()
    return True


def check_data_completeness():
    """Check data completeness for all weeks"""
    validator = DataQualityValidator()

    # Check all weeks
    all_issues = validator.validate_all_weeks()

    if not all_issues:
        logger.info("✓ Data: All 18 weeks have complete matchup data")
        return True
    else:
        logger.warning(f"⚠ Data: {len(all_issues)} weeks have issues")
        for week, issues in sorted(all_issues.items()):
            logger.warning(f"  Week {week}: {issues[0]}")
        return False


def check_schedule_file():
    """Check if hardcoded schedule exists"""
    schedule_file = Path('data/schedules/nfl_2025_schedule.json')

    if not schedule_file.exists():
        logger.error("✗ Schedule: Hardcoded schedule file not found")
        return False

    import json
    try:
        with open(schedule_file) as f:
            schedule = json.load(f)

        weeks = schedule.get('weeks', {})
        total_games = sum(len(games) for games in weeks.values())

        logger.info(f"✓ Schedule: Hardcoded schedule exists ({total_games} games)")
        return True
    except Exception as e:
        logger.error(f"✗ Schedule: Error reading schedule file: {e}")
        return False


def check_scrapers():
    """Check if scraper files exist"""
    scrapers_dir = Path('scrapers')

    required_scrapers = [
        'matchups_scraper.py',
        'matchups_scraper_api.py',
        'matchups_loader.py'
    ]

    missing = []
    for scraper in required_scrapers:
        if not (scrapers_dir / scraper).exists():
            missing.append(scraper)

    if missing:
        logger.error(f"✗ Scrapers: Missing files: {missing}")
        return False

    logger.info(f"✓ Scrapers: All scraper files present")
    return True


def check_monitoring():
    """Check if monitoring components exist"""
    monitoring_files = {
        'utils/data_quality_validator.py': 'Data quality validator',
        'utils/alerting.py': 'Alerting system',
        'scripts/daily_health_check.py': 'Daily health check'
    }

    all_exist = True
    for file_path, description in monitoring_files.items():
        if Path(file_path).exists():
            logger.info(f"✓ Monitoring: {description} installed")
        else:
            logger.warning(f"⚠ Monitoring: {description} not found")
            all_exist = False

    return all_exist


def main():
    """Run all system checks"""
    logger.info("\n" + "="*60)
    logger.info("BetThat NFL Data Pipeline - System Verification")
    logger.info("="*60 + "\n")

    checks = [
        ("Schedulers", check_schedulers),
        ("Database", check_database_structure),
        ("Data Completeness", check_data_completeness),
        ("Schedule File", check_schedule_file),
        ("Scrapers", check_scrapers),
        ("Monitoring", check_monitoring)
    ]

    results = {}
    for name, check_func in checks:
        logger.info(f"\n--- {name} ---")
        try:
            results[name] = check_func()
        except Exception as e:
            logger.error(f"✗ {name}: Error during check: {e}")
            results[name] = False

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Verification Summary")
    logger.info("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:8} - {name}")

    logger.info("\n" + "="*60)
    logger.info(f"Overall: {passed}/{total} checks passed")
    logger.info("="*60 + "\n")

    if passed == total:
        logger.info("✓ System is fully operational and optimized!")
        return 0
    else:
        logger.warning("⚠ Some checks failed - review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
