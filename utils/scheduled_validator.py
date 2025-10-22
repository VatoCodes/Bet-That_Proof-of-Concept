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

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_validator import DataValidator


def log_validation_results(validator, results):
    """Log validation results to file for monitoring

    Args:
        validator: DataValidator instance with results
        results: Validation results dictionary
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
    print("🔍 Scheduled Data Validation")
    print("=" * 60)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # Run validation
    validator = DataValidator()
    results = validator.validate_all()

    # Log results
    log_file = log_validation_results(validator, results)
    print(f"✅ Results logged to: {log_file}")

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
