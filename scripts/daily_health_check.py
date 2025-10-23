"""
Daily health check for NFL betting system
Run via cron: 0 6 * * * (6am daily)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_quality_validator import DataQualityValidator
from utils.week_manager import WeekManager
from utils.alerting import AlertManager, ALERT_CONFIG_EXAMPLE


def main():
    """Run daily health check"""

    validator = DataQualityValidator()
    week_manager = WeekManager()
    alert_manager = AlertManager(ALERT_CONFIG_EXAMPLE)

    current_week = week_manager.get_current_week()

    print(f"\n{'='*60}")
    print(f"Daily Health Check - Week {current_week}")
    print(f"{'='*60}\n")

    # Validate current week
    is_valid, issues = validator.validate_week(current_week)

    if is_valid:
        print(f"✓ Week {current_week} data quality: PASS")
    else:
        print(f"✗ Week {current_week} data quality: FAIL")
        print("\nIssues:")
        for issue in issues:
            print(f"  - {issue}")

        # Send alert
        alert_manager.send_alert(
            title=f"Week {current_week} Failed Daily Health Check",
            message="\n".join(issues),
            severity="error"
        )

        sys.exit(1)

    # Check upcoming week too
    next_week = current_week + 1
    if next_week <= 18:
        is_valid_next, issues_next = validator.validate_week(next_week)

        if not is_valid_next:
            print(f"\n⚠ Week {next_week} (upcoming) has issues:")
            for issue in issues_next:
                print(f"  - {issue}")

            alert_manager.send_alert(
                title=f"Week {next_week} Data Incomplete (Upcoming)",
                message="\n".join(issues_next),
                severity="warning"
            )

    print(f"\n{'='*60}")
    print("Health check complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
