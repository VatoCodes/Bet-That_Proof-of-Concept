"""
v2 Deployment Configuration Module

Manages feature flags for v2 QB TD Calculator phased rollout.

Rollout Phases:
- Shadow Mode: v2_rollout_percentage=0, v2_shadow_mode_enabled=True
- Canary (10%): v2_rollout_percentage=10
- Staged (50%): v2_rollout_percentage=50
- Full (100%): v2_rollout_percentage=100
"""

import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# V2 Rollout Configuration
# These values control the phased deployment of v2 QB TD Calculator
V2_ROLLOUT_CONFIG = {
    # Rollout percentage (0-100)
    # 0 = v2 disabled, 10 = canary, 50 = staged, 100 = full
    'v2_rollout_percentage': 0,

    # Shadow mode: Run v2 alongside v1 but don't serve v2 results
    # Used for validation in production without user impact
    # ✅ SHADOW MODE ENABLED - Day 0 (2025-10-22)
    'v2_shadow_mode_enabled': True,

    # Enable monitoring and metrics collection for v2
    'v2_monitoring_enabled': True,

    # Fallback to v1 when v2 data insufficient
    'v2_fallback_to_v1_enabled': True,

    # Log all v2 calculations for analysis
    'v2_logging_enabled': True,

    # Performance thresholds
    'v2_max_query_time_ms': 500,  # P95 target: <500ms

    # Data quality thresholds
    'v2_min_game_log_games': 3,  # Minimum games required for v2 calculation
    'v2_min_red_zone_attempts': 10,  # Minimum RZ attempts for reliable rate
}


def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    # Check environment variable override first
    env_key = key.upper()
    env_value = os.environ.get(env_key)

    if env_value is not None:
        # Parse environment variable to correct type
        if env_value.lower() in ('true', 'yes', '1'):
            return True
        elif env_value.lower() in ('false', 'no', '0'):
            return False
        try:
            return int(env_value)
        except ValueError:
            try:
                return float(env_value)
            except ValueError:
                return env_value

    # Fall back to config dict
    return V2_ROLLOUT_CONFIG.get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    Set a configuration value (in-memory only)

    Args:
        key: Configuration key
        value: New value

    Note:
        This only updates the in-memory config. For persistent changes,
        update V2_ROLLOUT_CONFIG directly or use environment variables.
    """
    if key in V2_ROLLOUT_CONFIG:
        old_value = V2_ROLLOUT_CONFIG[key]
        V2_ROLLOUT_CONFIG[key] = value
        logger.info(f"Config updated: {key} = {value} (was: {old_value})")
    else:
        logger.warning(f"Unknown config key: {key}")
        V2_ROLLOUT_CONFIG[key] = value


def get_all_config() -> Dict[str, Any]:
    """
    Get all configuration values

    Returns:
        Dictionary of all config values
    """
    return V2_ROLLOUT_CONFIG.copy()


def is_shadow_mode() -> bool:
    """
    Check if shadow mode is enabled

    Returns:
        True if shadow mode enabled
    """
    return get_config('v2_shadow_mode_enabled', False)


def get_rollout_percentage() -> int:
    """
    Get current rollout percentage

    Returns:
        Rollout percentage (0-100)
    """
    return get_config('v2_rollout_percentage', 0)


def should_use_v2(user_id: str = None) -> bool:
    """
    Determine if v2 should be used for this request

    Args:
        user_id: Optional user identifier for consistent A/B assignment

    Returns:
        True if v2 should be used, False otherwise
    """
    # If shadow mode, always calculate v2 but don't serve it
    if is_shadow_mode():
        return False  # Return False so we don't serve v2 results

    rollout_pct = get_rollout_percentage()

    # 0% = disabled
    if rollout_pct == 0:
        return False

    # 100% = full rollout
    if rollout_pct == 100:
        return True

    # For partial rollout, use consistent hashing if user_id provided
    if user_id:
        # Simple hash-based A/B assignment (consistent for same user_id)
        hash_value = hash(user_id) % 100
        return hash_value < rollout_pct

    # Without user_id, use simple random assignment
    import random
    return random.randint(0, 99) < rollout_pct


def should_calculate_v2_in_shadow() -> bool:
    """
    Check if v2 should be calculated in shadow mode

    Returns:
        True if we should calculate v2 (even if not serving it)
    """
    return is_shadow_mode() or get_rollout_percentage() > 0


# Deployment state helpers
def get_deployment_phase() -> str:
    """
    Get current deployment phase name

    Returns:
        Phase name: 'SHADOW', 'CANARY', 'STAGED', 'FULL', or 'DISABLED'
    """
    if is_shadow_mode():
        return 'SHADOW'

    pct = get_rollout_percentage()
    if pct == 0:
        return 'DISABLED'
    elif pct <= 10:
        return 'CANARY'
    elif pct <= 50:
        return 'STAGED'
    elif pct == 100:
        return 'FULL'
    else:
        return f'CUSTOM_{pct}%'


def print_deployment_status() -> None:
    """Print current deployment status"""
    phase = get_deployment_phase()
    pct = get_rollout_percentage()
    shadow = is_shadow_mode()
    monitoring = get_config('v2_monitoring_enabled')

    print("\n" + "="*60)
    print("v2 QB TD Calculator Deployment Status")
    print("="*60)
    print(f"Phase: {phase}")
    print(f"Rollout Percentage: {pct}%")
    print(f"Shadow Mode: {'ENABLED' if shadow else 'DISABLED'}")
    print(f"Monitoring: {'ENABLED' if monitoring else 'DISABLED'}")
    print("="*60 + "\n")
