#!/usr/bin/env python3
"""
Feature Flag Management Script

Update v2 rollout percentage and other feature flags for gradual deployment.

Usage:
    python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10
    python scripts/set_feature_flag.py --flag v2_shadow_mode_enabled --value true
    python scripts/set_feature_flag.py --list  # Show current values
"""
import argparse
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import V2_ROLLOUT_CONFIG, set_config, get_config


def parse_value(value_str: str):
    """Parse string value to appropriate type"""
    # Boolean
    if value_str.lower() in ('true', 'yes', '1'):
        return True
    if value_str.lower() in ('false', 'no', '0'):
        return False

    # Integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Float
    try:
        return float(value_str)
    except ValueError:
        pass

    # String
    return value_str


def list_flags():
    """Display all current feature flag values"""
    print("\n" + "="*60)
    print("Current Feature Flag Configuration")
    print("="*60 + "\n")

    for key, value in V2_ROLLOUT_CONFIG.items():
        print(f"{key:30} = {value}")

    print("\n" + "="*60)
    # Fix f-string syntax by extracting status text first
    if V2_ROLLOUT_CONFIG['v2_shadow_mode_enabled']:
        status_text = 'SHADOW MODE'
    else:
        status_text = f"{V2_ROLLOUT_CONFIG['v2_rollout_percentage']}% ROLLOUT"
    print(f"Status: {status_text}")
    print("="*60 + "\n")


def set_flag(flag_name: str, value):
    """Set a feature flag value"""
    if flag_name not in V2_ROLLOUT_CONFIG:
        print(f"❌ Error: Unknown flag '{flag_name}'")
        print(f"\nAvailable flags:")
        for key in V2_ROLLOUT_CONFIG.keys():
            print(f"  - {key}")
        sys.exit(1)

    # Validate rollout percentage
    if flag_name == 'v2_rollout_percentage':
        if not isinstance(value, int) or value < 0 or value > 100:
            print(f"❌ Error: v2_rollout_percentage must be an integer between 0 and 100")
            sys.exit(1)

    # Get old value for comparison
    old_value = get_config(flag_name)

    # Set new value
    set_config(flag_name, value)

    # Confirmation
    print(f"\n✅ Feature flag updated successfully!")
    print(f"\nFlag: {flag_name}")
    print(f"Old Value: {old_value}")
    print(f"New Value: {value}")

    # Special messaging for rollout percentage
    if flag_name == 'v2_rollout_percentage':
        if value == 0:
            print(f"\n🔵 Shadow Mode: v2 not visible to users")
        elif value == 10:
            print(f"\n🟡 Canary Rollout: 10% of users on v2")
        elif value == 50:
            print(f"\n🟠 Staged Rollout: 50% of users on v2")
        elif value == 100:
            print(f"\n🟢 Full Rollout: 100% of users on v2")
        else:
            print(f"\n🔷 Custom Rollout: {value}% of users on v2")

    # Warning for shadow mode
    if flag_name == 'v2_shadow_mode_enabled' and value:
        print(f"\n⚠️  Shadow Mode Enabled: v2 will run but not serve results to users")
        print(f"    (Ensure v2_rollout_percentage = 0 for true shadow mode)")

    print(f"\n⚠️  IMPORTANT: Changes take effect immediately in-memory.")
    print(f"    For persistent changes, update utils/config.py")
    print()


def verify_deployment():
    """Verify deployment configuration is valid"""
    print("\n" + "="*60)
    print("Deployment Configuration Verification")
    print("="*60 + "\n")

    issues = []
    warnings = []

    rollout_pct = get_config('v2_rollout_percentage')
    shadow_mode = get_config('v2_shadow_mode_enabled')
    monitoring = get_config('v2_monitoring_enabled')

    # Check: Shadow mode + rollout percentage
    if shadow_mode and rollout_pct > 0:
        warnings.append(f"Shadow mode enabled but rollout percentage is {rollout_pct}% (expected 0%)")

    # Check: Monitoring disabled
    if not monitoring:
        warnings.append("Monitoring is disabled - metrics will not be collected")

    # Check: Invalid rollout percentage
    if rollout_pct < 0 or rollout_pct > 100:
        issues.append(f"Invalid rollout percentage: {rollout_pct}% (must be 0-100)")

    # Results
    if issues:
        print("❌ ISSUES FOUND:\n")
        for issue in issues:
            print(f"  • {issue}")
        print()
        return False

    if warnings:
        print("⚠️  WARNINGS:\n")
        for warning in warnings:
            print(f"  • {warning}")
        print()

    if not issues and not warnings:
        print("✅ Configuration valid - no issues found\n")

    # Current state
    print("Current Deployment State:")
    print(f"  Rollout Percentage: {rollout_pct}%")
    print(f"  Shadow Mode: {'ENABLED' if shadow_mode else 'DISABLED'}")
    print(f"  Monitoring: {'ENABLED' if monitoring else 'DISABLED'}")

    if shadow_mode:
        print(f"\n  Status: 🔵 SHADOW MODE (v2 not visible to users)")
    elif rollout_pct == 0:
        print(f"\n  Status: ⚪ v2 DISABLED (all users on v1)")
    elif rollout_pct == 10:
        print(f"\n  Status: 🟡 CANARY (10% of users on v2)")
    elif rollout_pct == 50:
        print(f"\n  Status: 🟠 STAGED (50% of users on v2)")
    elif rollout_pct == 100:
        print(f"\n  Status: 🟢 FULL ROLLOUT (100% of users on v2)")
    else:
        print(f"\n  Status: 🔷 CUSTOM ({rollout_pct}% of users on v2)")

    print("\n" + "="*60 + "\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Manage v2 rollout feature flags',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all flags
  python scripts/set_feature_flag.py --list

  # Set rollout percentage to 10% (Canary)
  python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10

  # Enable shadow mode
  python scripts/set_feature_flag.py --flag v2_shadow_mode_enabled --value true

  # Disable v2 (rollback to v1)
  python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 0

  # Verify configuration
  python scripts/set_feature_flag.py --verify

Rollout Stages:
  0%   = Shadow Mode (v2 runs but not visible to users)
  10%  = Canary (small subset of users)
  50%  = Staged (half of users)
  100% = Full Rollout (all users)
        """
    )

    parser.add_argument('--flag', type=str, help='Feature flag name to update')
    parser.add_argument('--value', type=str, help='New value for the flag')
    parser.add_argument('--list', action='store_true', help='List all current flag values')
    parser.add_argument('--verify', action='store_true', help='Verify deployment configuration')

    args = parser.parse_args()

    # List flags
    if args.list:
        list_flags()
        return

    # Verify configuration
    if args.verify:
        verify_deployment()
        return

    # Set flag
    if args.flag and args.value:
        value = parse_value(args.value)
        set_flag(args.flag, value)
        return

    # No valid action
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
