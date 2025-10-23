# BetThat v2 QB TD Calculator — Production Deployment Runbook

**Version:** 1.0
**Last Updated:** 2025-10-22
**Phase:** Phase 4 Complete — Ready for Production Testing
**Authors:** Drew Romero, Claude Code Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phased Rollout Strategy](#phased-rollout-strategy)
3. [Feature Flag Implementation](#feature-flag-implementation)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Rollback Procedures](#rollback-procedures)
6. [Success Criteria & Stage Gates](#success-criteria--stage-gates)
7. [Incident Response Playbook](#incident-response-playbook)
8. [Common Scenarios & Resolutions](#common-scenarios--resolutions)
9. [Pre-Deployment Checklist](#pre-deployment-checklist)
10. [Deployment Timeline](#deployment-timeline)

---

## Executive Summary

### Purpose

This runbook provides step-by-step procedures for safely deploying the v2 QB TD Calculator to production using a phased rollout strategy. The v2 calculator introduces a dual-source architecture (play_by_play + player_game_log) that resolves the critical `is_touchdown=0` blocker in v1.

### Validation Status

**Phase 2 Results:**
- ✅ **Agreement Rate:** 90% with v1 baseline (target: 60-85%)
- ✅ **Performance:** 0.5ms average, 0.54ms p95 (target: <500ms) — **1000x faster**
- ✅ **Data Quality:** 685 QB-weeks (2024) + 227 QB-games (2025) validated
- ✅ **Fallback Rate:** 12.5% (target: <20%)
- ✅ **Error Rate:** 0% in validation (target: <1%)
- ✅ **Decision:** GO for production deployment

### Deployment Philosophy

**Hybrid Approach:** Conservative validation gates with rapid progression when metrics are excellent.

**Key Principles:**
1. **Safety First** — Easy rollback, comprehensive monitoring, clear go/no-go criteria
2. **Gradual Exposure** — Shadow → Canary (10%) → Staged (50%) → Full (100%)
3. **Data-Driven Decisions** — Real-time metrics inform each stage gate
4. **Graceful Degradation** — v2 automatically falls back to v1 when data insufficient

### Timeline

```
Day 0-1:   Shadow Mode      (0% user impact, v2 validation in production)
Day 2-4:   Canary (10%)     (Minimal user impact, A/B testing)
Day 5-7:   Staged (50%)     (Moderate user impact, scale validation)
Day 8+:    Full Rollout (100%) (Complete migration, ongoing monitoring)
```

**Total Duration:** 8-10 days from Shadow to Full (100%)

---

## Phased Rollout Strategy

### Phase 0: Shadow Mode (Day 0-1)

#### Purpose
Run v2 calculator alongside v1 in production environment, validate behavior without user impact.

#### Implementation

**Configuration:**
```python
# Set in config.py or environment variables
V2_ROLLOUT_PERCENTAGE = 0
V2_SHADOW_MODE_ENABLED = True
V2_MONITORING_ENABLED = True
```

**Behavior:**
- Calculate both v1 and v2 edges for every matchup
- Log all v2 calculations (edges, metadata, timing, fallback events)
- **Serve only v1 edges** to users (no user impact)
- Monitor for crashes, errors, timeouts, data quality issues

**What to Monitor:**
- v2 completion rate (should be 100%, even if using fallback)
- Exception/error rate (target: 0%)
- Performance (p95 <500ms)
- Fallback rate (target: <20%)
- Agreement rate with v1 (target: 60-85%)

#### Success Criteria

**Must Pass ✅ (All Required):**
- [ ] Zero unhandled exceptions in 24 hours
- [ ] v2 completes 100% of calculations (even if fallback to v1)
- [ ] Performance p95 <500ms
- [ ] Agreement rate 60-85% (matches Phase 2 validation)
- [ ] Fallback rate <20%

**Should Pass ⚠️ (1+ Required):**
- [ ] v2 performance comparable to v1 (<2x overhead)
- [ ] No database connection errors
- [ ] Logs and monitoring working correctly
- [ ] Shadow mode metrics match validation results

**Blockers ❌:**
- ANY critical errors → Fix before proceeding
- Performance p95 >1000ms → Investigate and optimize
- Agreement rate outside 50-90% → Data quality issue
- Fallback rate >30% → game_log data incomplete

#### Duration
**24 hours minimum** — Longer if issues detected

#### User Impact
**None** — v2 calculations not visible to users

#### Rollback Procedure
```bash
# Disable v2 shadow mode
python scripts/set_feature_flag.py --flag v2_shadow_mode_enabled --value false

# Or via config
V2_SHADOW_MODE_ENABLED = False
```

---

### Phase 1: Canary (10%) (Day 2-4)

#### Purpose
Serve v2 edges to small subset of users, validate production behavior with real user traffic.

#### Implementation

**Configuration:**
```python
V2_ROLLOUT_PERCENTAGE = 10  # 10% of users get v2
V2_SHADOW_MODE_ENABLED = False  # No longer shadow mode
V2_MONITORING_ENABLED = True
```

**Behavior:**
- 10% of users get v2 edges (deterministic A/B test by user_id hash)
- 90% continue with v1 edges (control group)
- Track: conversion rates, user feedback, error rates, edge quality
- Monitor: performance, fallback rate, agreement rate

**What to Monitor:**
- **Business Metrics:** Conversion rate (v2 vs v1), user complaints
- **Technical Metrics:** Error rate, performance, fallback rate
- **Data Quality:** game_log freshness, v2 data coverage

#### Success Criteria

**Must Pass ✅ (All Required):**
- [ ] Error rate <1% for 48 hours
- [ ] Conversion rate ≥95% of v1 baseline
- [ ] Zero user complaints attributable to v2
- [ ] Fallback rate <20%
- [ ] Performance p95 <500ms

**Should Pass ⚠️ (2+ Required):**
- [ ] Conversion rate ≥100% of v1 baseline
- [ ] v2 edges perceived as higher quality (user feedback)
- [ ] System stable under canary load
- [ ] No incidents requiring rollback

**Blockers ❌:**
- Conversion rate <90% of baseline → Edge quality issue, investigate
- Error rate >2% → Code or data problem, rollback and fix
- Multiple rollbacks in canary → Not ready for scale, re-validate

#### Duration
**48-72 hours minimum** — Longer if metrics borderline

#### User Impact
**Minimal** — 10% of users see v2 edges

#### Rollback Procedure
```bash
# Fast rollback to Shadow Mode (0%)
python scripts/emergency_rollback.sh --target 0

# Or gradual rollback to Shadow Mode
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 0
```

**Rollback Decision Matrix:**
| Error Rate | Conversion | Performance | Action |
|-----------|-----------|-------------|--------|
| >5% | <80% baseline | p95 >1000ms | Emergency rollback to 0% |
| 2-5% | 80-90% baseline | p95 500-1000ms | Investigate, reduce to 5% |
| <2% | >90% baseline | p95 <500ms | Monitor, proceed |

---

### Phase 2: Staged (50%) (Day 5-7)

#### Purpose
Expand rollout to 50% of users, validate system performance at scale.

#### Implementation

**Configuration:**
```python
V2_ROLLOUT_PERCENTAGE = 50  # 50% of users get v2
V2_MONITORING_ENABLED = True
```

**Behavior:**
- 50% of users get v2 edges
- 50% continue with v1 edges (control group)
- Comprehensive monitoring (all metrics)
- Daily review of key metrics with team

**What to Monitor:**
- **Performance at Scale:** Database load, query times, connection pool
- **Business Metrics:** Conversion rate stable vs v1
- **Data Quality:** game_log coverage sufficient for 50% traffic

#### Success Criteria

**Must Pass ✅ (All Required):**
- [ ] Error rate <0.5% for 72 hours
- [ ] Conversion rate ≥95% of v1 baseline (at scale)
- [ ] Zero critical incidents in staged period
- [ ] Fallback rate <20%
- [ ] Performance p95 <500ms under 50% load
- [ ] Team confidence: "Ready for production"

**Should Pass ⚠️ (2+ Required):**
- [ ] Conversion rate ≥100% of baseline
- [ ] User satisfaction maintained or improved
- [ ] Cost per calculation comparable to v1
- [ ] Documentation complete

**Blockers ❌:**
- ANY critical incidents in staged → Investigate thoroughly
- Performance degradation at 50% → Not ready for 100%
- Data quality regressions → Fix before full rollout
- Team not confident → Address concerns before proceeding

#### Duration
**72 hours minimum** — Longer if metrics need stabilization

#### User Impact
**Moderate** — 50% of users see v2 edges

#### Rollback Procedure
```bash
# Gradual rollback to Canary (10%)
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10

# If issue persists: Emergency rollback to Shadow (0%)
python scripts/emergency_rollback.sh --target 0
```

**Rollback Decision Matrix:**
| Severity | Error Rate | Performance | Conversion | Action |
|----------|-----------|-------------|------------|--------|
| CRITICAL | >10% | p95 >2000ms | <80% baseline | Emergency rollback to 0% |
| HIGH | 5-10% | p95 1000-2000ms | 80-90% | Gradual rollback to 10% |
| MEDIUM | 2-5% | p95 500-1000ms | 90-95% | Reduce to 25%, investigate |
| LOW | <2% | p95 <500ms | 95-100% | Monitor, no action |

---

### Phase 3: Full Rollout (100%) (Day 8+)

#### Purpose
Complete migration to v2 as primary calculator for all users.

#### Implementation

**Configuration:**
```python
V2_ROLLOUT_PERCENTAGE = 100  # All users get v2
V2_MONITORING_ENABLED = True
V2_FALLBACK_TO_V1_ENABLED = True  # v2 can still fallback to v1 internally
```

**Behavior:**
- 100% of users get v2 edges
- v1 EdgeCalculator still available as fallback (within v2)
- Continue monitoring for 2 weeks
- After 2 weeks of stability: Consider deprecating standalone v1 API

**What to Monitor:**
- All Phase 2 metrics (ongoing)
- Long-term trends: fallback rate, performance, data quality
- User feedback and satisfaction

#### Success Criteria

**Must Pass ✅ (All Required):**
- [ ] All Phase 2 criteria maintained at 100% load
- [ ] System stable for 2+ weeks
- [ ] Team confident in v2 performance and reliability
- [ ] Documentation complete and up-to-date
- [ ] Operations team trained on monitoring and troubleshooting

**Should Pass ⚠️:**
- [ ] User satisfaction improved vs v1 baseline
- [ ] Cost per calculation maintained or reduced
- [ ] Fallback rate decreasing over time (data coverage improving)

**Ongoing Monitoring:**
- Weekly review of key metrics
- Monthly retrospective on v2 performance
- Quarterly review of v1 deprecation timeline

#### Duration
**Ongoing** — Monitor indefinitely

#### User Impact
**Full** — All users see v2 edges

#### Rollback Procedure
```bash
# Gradual rollback to Staged (50%)
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 50

# If issue persists: Further rollback to Canary (10%)
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10

# Emergency: Full rollback to Shadow (0%)
python scripts/emergency_rollback.sh --target 0
```

---

## Feature Flag Implementation

### Feature Flag System

The v2 rollout is controlled by a simple percentage-based feature flag system that deterministically assigns users to v1 or v2 based on user_id hash.

### Implementation Code

#### 1. Feature Flag Manager

Create `utils/feature_flags.py`:

```python
"""
Feature flag management for gradual v2 rollout
"""
import hashlib
import random
from typing import Optional
from utils.config import get_config


class FeatureFlags:
    """Manage feature flags for calculator version selection"""

    @staticmethod
    def get_calculator_version(user_id: Optional[str] = None) -> str:
        """
        Determine which calculator version to use

        Args:
            user_id: Optional user identifier for deterministic A/B testing
                    If None, random assignment is used

        Returns:
            'v1' or 'v2' based on current rollout percentage

        Examples:
            >>> FeatureFlags.get_calculator_version("user_12345")
            'v2'  # If user hashes into v2 bucket

            >>> FeatureFlags.get_calculator_version()
            'v1'  # Random assignment
        """
        # Get current rollout percentage from config
        rollout_pct = get_config('v2_rollout_percentage', default=0)

        # Special cases
        if rollout_pct == 0:
            return 'v1'  # Shadow mode or v2 disabled

        if rollout_pct == 100:
            return 'v2'  # Full rollout

        # A/B test: hash user_id to deterministic bucket (0-99)
        if user_id:
            # MD5 hash of user_id to get deterministic value
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            bucket = hash_val % 100

            # User assigned to v2 if bucket < rollout_pct
            return 'v2' if bucket < rollout_pct else 'v1'

        # No user_id: random assignment (for testing or anonymous users)
        return 'v2' if random.randint(1, 100) <= rollout_pct else 'v1'

    @staticmethod
    def should_run_shadow_mode() -> bool:
        """Check if shadow mode is enabled (run v2 even if not serving)"""
        return get_config('v2_shadow_mode_enabled', default=False)

    @staticmethod
    def is_monitoring_enabled() -> bool:
        """Check if v2 monitoring/logging is enabled"""
        return get_config('v2_monitoring_enabled', default=True)


# Convenience functions
def get_calculator_version(user_id: Optional[str] = None) -> str:
    """Wrapper for FeatureFlags.get_calculator_version()"""
    return FeatureFlags.get_calculator_version(user_id)


def should_run_shadow_mode() -> bool:
    """Wrapper for FeatureFlags.should_run_shadow_mode()"""
    return FeatureFlags.should_run_shadow_mode()
```

#### 2. Configuration Management

Add to `utils/config.py`:

```python
"""
v2 Rollout Configuration
"""

# v2 Feature Flags
V2_ROLLOUT_CONFIG = {
    # Rollout percentage (0-100)
    # 0 = Shadow mode or disabled
    # 10 = Canary (10% of users)
    # 50 = Staged (50% of users)
    # 100 = Full rollout
    'v2_rollout_percentage': 0,

    # Shadow mode: Run v2 calculations even if not serving to users
    # Set to True during Phase 0 (Shadow Mode)
    'v2_shadow_mode_enabled': True,

    # Enable comprehensive logging and monitoring for v2
    'v2_monitoring_enabled': True,

    # Allow v2 to fallback to v1 when data insufficient
    'v2_fallback_enabled': True,
}


def get_config(key: str, default=None):
    """Get configuration value with fallback to default"""
    return V2_ROLLOUT_CONFIG.get(key, default)


def set_config(key: str, value):
    """Update configuration value (in-memory)"""
    V2_ROLLOUT_CONFIG[key] = value
```

#### 3. Integration with Edge Calculator

Modify edge calculation endpoint to use feature flags:

```python
"""
Example integration in API endpoint or main calculation flow
"""
from utils.feature_flags import get_calculator_version, should_run_shadow_mode
from utils.calculators.edge_calculator import EdgeCalculator  # v1
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2  # v2
from utils.logging_config import V2CalculationLogger

# Initialize calculators
v1_calculator = EdgeCalculator(db)
v2_calculator = QBTDCalculatorV2(db)
logger = V2CalculationLogger()


def calculate_edge(player_name: str, opponent: str, user_id: str = None):
    """
    Calculate edge using v1 or v2 based on feature flag

    Args:
        player_name: QB name
        opponent: Opponent team abbreviation
        user_id: User identifier for A/B testing

    Returns:
        Edge calculation result with metadata
    """
    import time

    # Determine which version to serve to user
    calculator_version = get_calculator_version(user_id)
    shadow_mode = should_run_shadow_mode()

    # Shadow Mode: Run both v1 and v2, but serve only v1
    if shadow_mode:
        # Calculate v1 (serving to user)
        start = time.time()
        v1_result = v1_calculator.calculate_edges(matchups)
        v1_time = (time.time() - start) * 1000

        # Calculate v2 (shadow, for validation)
        start = time.time()
        v2_result = v2_calculator.calculate_edges(matchups)
        v2_time = (time.time() - start) * 1000

        # Log v2 calculation for monitoring
        logger.log_calculation(
            player_name=player_name,
            calculator_version='v2_shadow',
            edge=v2_result['edges'][0]['edge'],
            metadata=v2_result['edges'][0]['metadata'],
            elapsed_ms=v2_time
        )

        # Serve v1 to user
        return {
            'edge': v1_result['edges'][0]['edge'],
            'calculator_version': 'v1',
            'metadata': v1_result['edges'][0]['metadata']
        }

    # Production Mode: Serve assigned version
    if calculator_version == 'v2':
        start = time.time()
        result = v2_calculator.calculate_edges(matchups)
        elapsed_ms = (time.time() - start) * 1000

        # Log v2 calculation
        logger.log_calculation(
            player_name=player_name,
            calculator_version='v2',
            edge=result['edges'][0]['edge'],
            metadata=result['edges'][0]['metadata'],
            elapsed_ms=elapsed_ms
        )

        return {
            'edge': result['edges'][0]['edge'],
            'calculator_version': 'v2',
            'metadata': result['edges'][0]['metadata']
        }
    else:
        # Use v1
        result = v1_calculator.calculate_edges(matchups)
        return {
            'edge': result['edges'][0]['edge'],
            'calculator_version': 'v1',
            'metadata': result['edges'][0]['metadata']
        }
```

---

## Monitoring & Alerting

### Monitoring Dashboard

#### Key Metrics (Real-Time, 5-min intervals)

**1. Calculator Usage**
```
Metric: v2_calculations_per_min
Description: Number of v2 calculations per minute
Target: Scales with rollout percentage
Alert: Drop to 0 during active rollout

Metric: v1_calculations_per_min
Description: Number of v1 calculations per minute
Target: Decreases as v2 rollout increases

Metric: v2_fallback_rate_pct
Description: % of v2 calculations falling back to v1
Target: <20%
Alert: >25% (data quality issue)

Metric: v2_rollout_percentage
Description: Current rollout percentage
Values: 0 (shadow), 10 (canary), 50 (staged), 100 (full)
```

**2. Performance**
```
Metric: v2_avg_query_time_ms
Description: Average v2 query time
Target: <500ms
Alert: >500ms for 5+ minutes

Metric: v2_p95_query_time_ms
Description: 95th percentile v2 query time
Target: <500ms
Alert: >500ms (critical threshold)

Metric: v2_p99_query_time_ms
Description: 99th percentile v2 query time
Target: <1000ms
Alert: >1000ms (performance degradation)

Metric: v1_avg_query_time_ms
Description: v1 baseline for comparison
```

**3. Data Quality**
```
Metric: qbs_with_v2_data_pct
Description: % of QBs with sufficient v2 data (2+ weeks, 5+ RZ attempts)
Target: >80%
Alert: <70% (data coverage issue)

Metric: qbs_falling_back_to_v1_pct
Description: % of QBs requiring fallback to v1
Target: <20%
Alert: >25%

Metric: weeks_of_data_available
Description: Number of weeks of game_log data for current season
Target: Current week number

Metric: last_game_log_import_hours_ago
Description: Hours since last game_log data import
Target: <24 hours
Alert: >24 hours (stale data)
```

**4. Errors & Exceptions**
```
Metric: v2_error_rate_pct
Description: % of v2 calculations with errors
Target: <1%
Alert: >1% (investigate), >5% (rollback)

Metric: db_connection_failures_per_min
Description: Database connection errors
Target: 0
Alert: >0 (critical)

Metric: v2_timeouts_per_min
Description: v2 queries exceeding 500ms
Target: <1% of queries
Alert: >5% of queries

Metric: v2_unhandled_exceptions_per_min
Description: Uncaught exceptions in v2 calculator
Target: 0
Alert: >0 (critical)
```

**5. Business Metrics**
```
Metric: v2_conversion_rate_pct
Description: Conversion rate for v2 users
Target: ≥95% of v1 baseline

Metric: v1_conversion_rate_pct
Description: Baseline conversion rate (control group)

Metric: user_complaints_mentioning_edge
Description: Support tickets mentioning "edge" or "TD"
Target: No increase vs baseline
Alert: +20% increase

Metric: avg_edge_difference_v2_vs_v1
Description: Average absolute difference between v2 and v1 edges
Target: Informational (track trend)
```

#### Daily Aggregates

```
Metric: total_calculations_24h
Description: Total v1 + v2 calculations in last 24 hours

Metric: agreement_rate_pct_24h
Description: % agreement between v2 and v1 (shadow mode)
Target: 60-85%

Metric: fallback_reasons_breakdown_24h
Description: Count by reason (insufficient weeks, insufficient RZ attempts, etc.)

Metric: top_10_qbs_by_volume_24h
Description: Most calculated QBs in last 24 hours

Metric: system_uptime_pct_24h
Description: System availability
Target: >99.9%
```

### Alert Configuration

Create `monitoring/v2_alerts.yaml`:

```yaml
# v2 Production Alert Rules

alerts:
  # CRITICAL Alerts (Page on-call immediately)

  - name: v2_database_connection_failure
    condition: db_connection_errors > 0
    severity: CRITICAL
    notification: pagerduty, slack
    description: Cannot connect to database for v2 calculations
    action: |
      1. Immediate emergency rollback to v1 (scripts/emergency_rollback.sh)
      2. Check database status and connectivity
      3. Verify connection pool settings
      4. Review database logs for errors

  - name: v2_very_high_error_rate
    condition: v2_error_rate > 10%
    severity: CRITICAL
    notification: pagerduty, slack
    description: v2 calculator error rate exceeds 10% (critical threshold)
    action: |
      1. Emergency rollback to previous rollout percentage
      2. Review error logs for root cause
      3. Check recent code or data changes
      4. Verify game_log data quality

  # HIGH Alerts (Notify on-call within 30 min)

  - name: v2_high_error_rate
    condition: v2_error_rate > 5%
    severity: HIGH
    notification: slack, email
    description: v2 calculator error rate exceeds 5%
    action: |
      1. Gradual rollback (reduce rollout percentage by 50%)
      2. Investigate error logs and patterns
      3. Check for specific QBs or matchups causing errors
      4. Review recent deployments or data imports

  - name: v2_performance_degradation_critical
    condition: v2_p95_query_time > 1000ms
    severity: HIGH
    notification: slack
    description: v2 p95 query time exceeds 1 second (2x target)
    action: |
      1. Check database indexes (see ARCHITECTURE_V2.md §8)
      2. Review database load and query patterns
      3. Consider gradual rollback if persistent
      4. Run VACUUM and ANALYZE on database

  - name: v2_conversion_rate_drop
    condition: v2_conversion_rate < v1_baseline * 0.95
    severity: HIGH
    notification: slack, email
    description: v2 conversion rate 5%+ below v1 baseline
    action: |
      1. Compare v2 vs v1 edges for recent matchups
      2. Analyze edge quality (are v2 edges consistently higher/lower?)
      3. Review V2_CONFIG parameters (efficiency thresholds)
      4. Consider gradual rollback if conversion drops >10%

  # MEDIUM Alerts (Action required, non-urgent)

  - name: v2_slow_queries
    condition: v2_p95_query_time > 500ms
    severity: MEDIUM
    notification: slack
    description: v2 queries slower than 500ms target
    action: |
      1. Check database indexes exist and are optimal
      2. Review query execution plans (EXPLAIN QUERY PLAN)
      3. Monitor database load
      4. Consider caching for high-volume QBs

  - name: v2_high_fallback_rate
    condition: v2_fallback_rate > 25%
    severity: MEDIUM
    notification: slack
    description: v2 fallback rate exceeds target (>25%)
    action: |
      1. Check game_log data completeness (scripts/verify_deployment.py)
      2. Verify last import timestamp (<24 hours)
      3. Run game_log importer for current week
      4. Investigate specific QBs falling back

  - name: v2_moderate_error_rate
    condition: v2_error_rate > 2%
    severity: MEDIUM
    notification: slack
    description: v2 error rate above normal but below critical (2-5%)
    action: |
      1. Monitor closely, no immediate rollback
      2. Review error logs for patterns
      3. Create ticket and assign to team
      4. Fix within 1-2 business days

  # LOW Alerts (Informational, fix in next sprint)

  - name: v2_data_freshness
    condition: last_game_log_import > 24 hours
    severity: LOW
    notification: slack
    description: game_log data may be stale (>24 hours since import)
    action: |
      1. Run game_log importer manually
      2. Check importer cron job status
      3. Verify no importer errors in recent runs

  - name: v2_low_data_coverage
    condition: qbs_with_v2_data_pct < 70%
    severity: LOW
    notification: slack
    description: Less than 70% of QBs have sufficient v2 data
    action: |
      1. Verify game_log data for current season
      2. Check for missing weeks in imports
      3. Review data quality validator results
      4. May be expected early in season
```

### Structured Logging

Create `monitoring/v2_logging_config.py`:

```python
"""
Structured logging configuration for v2 calculator monitoring
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


class V2CalculationLogger:
    """Structured logging for v2 calculations and monitoring"""

    def __init__(self, log_file: str = 'logs/v2_calculations.jsonl'):
        """
        Initialize v2 calculation logger

        Args:
            log_file: Path to JSONL log file
        """
        self.logger = logging.getLogger('v2_calculator')
        self.logger.setLevel(logging.INFO)

        # JSON Lines format for easy aggregation
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

        # Also log to console for debugging
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        self.logger.addHandler(console)

    def log_calculation(
        self,
        player_name: str,
        calculator_version: str,
        edge: float,
        metadata: Dict[str, Any],
        elapsed_ms: float,
        user_id: Optional[str] = None
    ):
        """
        Log a single edge calculation

        Args:
            player_name: QB name
            calculator_version: 'v1', 'v2', or 'v2_shadow'
            edge: Calculated edge percentage
            metadata: Calculator metadata (data_source, rz_td_rate, etc.)
            elapsed_ms: Query time in milliseconds
            user_id: Optional user identifier
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'player_name': player_name,
            'calculator_version': calculator_version,
            'edge': round(edge, 2),
            'elapsed_ms': round(elapsed_ms, 2),
            'user_id': user_id,
            'metadata': {
                'data_source': metadata.get('data_source'),
                'red_zone_td_rate': metadata.get('red_zone_td_rate'),
                'weeks_data': metadata.get('weeks_data'),
                'rz_attempts': metadata.get('rz_attempts'),
                'fallback_to_v1': metadata.get('fallback_to_v1', False),
                'fallback_reason': metadata.get('fallback_reason'),
                'efficiency_adjustment': metadata.get('efficiency_adjustment'),
                'defense_adjustment': metadata.get('defense_adjustment')
            }
        }

        # Structured JSON logging for aggregation
        self.logger.info(json.dumps(log_entry))

        # Alerts for anomalies
        if elapsed_ms > 500:
            self.logger.warning(
                f"Slow query: {elapsed_ms:.2f}ms for {player_name} "
                f"(version: {calculator_version})"
            )

        if metadata.get('fallback_to_v1'):
            self.logger.info(
                f"Fallback to v1 for {player_name}: {metadata.get('fallback_reason')}"
            )

    def log_error(
        self,
        player_name: str,
        calculator_version: str,
        error_type: str,
        error_message: str,
        elapsed_ms: Optional[float] = None
    ):
        """
        Log a calculation error

        Args:
            player_name: QB name
            calculator_version: 'v1' or 'v2'
            error_type: Error class name
            error_message: Error description
            elapsed_ms: Optional query time before error
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'player_name': player_name,
            'calculator_version': calculator_version,
            'error_type': error_type,
            'error_message': error_message,
            'elapsed_ms': elapsed_ms,
            'level': 'ERROR'
        }

        self.logger.error(json.dumps(log_entry))

    def log_shadow_comparison(
        self,
        player_name: str,
        v1_edge: float,
        v2_edge: float,
        v2_metadata: Dict[str, Any]
    ):
        """
        Log shadow mode comparison (v1 vs v2)

        Args:
            player_name: QB name
            v1_edge: v1 calculated edge
            v2_edge: v2 calculated edge
            v2_metadata: v2 metadata
        """
        difference = abs(v2_edge - v1_edge)
        agreement = 'EXACT' if difference < 1 else ('CLOSE' if difference < 3 else 'MODERATE')

        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'player_name': player_name,
            'mode': 'shadow',
            'v1_edge': round(v1_edge, 2),
            'v2_edge': round(v2_edge, 2),
            'difference': round(difference, 2),
            'difference_pct': round((difference / v1_edge * 100) if v1_edge > 0 else 0, 1),
            'agreement': agreement,
            'v2_metadata': v2_metadata
        }

        self.logger.info(json.dumps(log_entry))


# Global logger instance
v2_logger = V2CalculationLogger()
```

---

## Rollback Procedures

### Emergency Rollback (5 minutes)

**When to Use:**
- Critical errors (error rate >5%)
- Database failures
- Performance degradation (p95 >1000ms)
- User-impacting bugs

**Steps:**

#### 1. Disable v2 via Feature Flag (1 min)

```bash
# Option A: Command line script
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 0

# Option B: Emergency rollback script (recommended)
./scripts/emergency_rollback.sh --target 0

# Option C: Manual config edit (if scripts fail)
# Edit utils/config.py:
# V2_ROLLOUT_CONFIG['v2_rollout_percentage'] = 0
# Restart application
```

#### 2. Verify Rollback (2 min)

```bash
# Check logs for v2 calculations (should be 0)
tail -f logs/v2_calculations.jsonl | grep '"calculator_version"'

# Check monitoring dashboard
# Verify: v2_calculations_per_min = 0

# Test endpoint manually
curl https://api.betthat.com/api/edges \
  -H "Content-Type: application/json" \
  -d '{"player": "Patrick Mahomes", "opponent": "LAC"}' \
  | jq '.metadata.calculator_version'

# Expected output: "v1"
```

#### 3. Communicate Incident (2 min)

```
# Post to #engineering-alerts Slack channel
🚨 v2 ROLLBACK EXECUTED
- Time: [timestamp]
- Reason: [brief description]
- Rollout: 100% → 0% (all users on v1)
- User Impact: [None/Minimal/Moderate]
- ETA for Resolution: [estimate]
- Incident Lead: [name]

# Update status page (if user-facing issue)
# Brief stakeholders on severity and timeline
```

#### 4. Root Cause Analysis (After rollback)

- Review error logs and monitoring metrics
- Identify trigger event and failure mode
- Document in incident report
- Plan fix and re-deployment strategy

---

### Gradual Rollback (1 hour)

**When to Use:**
- Non-critical issues (performance concerns, conversion rate drop)
- Data quality concerns
- Want to investigate before full rollback

**Steps:**

#### 1. Reduce Rollout Percentage (10 min)

```bash
# From 100% → 50%
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 50

# Monitor for 30 minutes, observe metrics

# If issue persists: 50% → 10%
python scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10

# Monitor for 30 minutes

# If issue persists: 10% → 0% (full rollback)
./scripts/emergency_rollback.sh --target 0
```

#### 2. Compare Metrics (20 min)

- Compare v2 users vs v1 users (control group)
- Isolate issue to v2 specifically
- Determine if issue is percentage-dependent (load-related)

**Key Questions:**
- Does error rate decrease with lower rollout percentage?
- Is performance better at lower scale?
- Is conversion rate issue consistent across all v2 users?

#### 3. Investigation (30 min)

```bash
# Review logs for patterns
grep -E "ERROR|fallback" logs/v2_calculations.jsonl | tail -100

# Test specific problematic QBs
python scripts/test_v2_calculator.py --qb "Patrick Mahomes"

# Check data quality for recent imports
python utils/data_quality_validator.py --season 2025 --week current

# Compare v1 vs v2 edges
python scripts/compare_v1_v2_edges.py --week current --output investigation.json
```

#### 4. Decision

**Fix Available:**
- Apply fix
- Re-test in development/staging
- Resume gradual rollout (10% → 50% → 100%)

**No Fix Yet:**
- Maintain reduced percentage
- Schedule fix for next sprint
- Monitor closely

**Major Issue:**
- Full rollback to 0%
- Extensive investigation required
- Re-validate before re-deployment

---

### Rollback Decision Matrix

| Severity | Error Rate | Performance (p95) | Conversion vs Baseline | Action |
|----------|-----------|-------------------|----------------------|--------|
| **CRITICAL** | >10% | >2000ms | <80% | Emergency rollback to 0% |
| **HIGH** | 5-10% | 1000-2000ms | 80-90% | Gradual rollback to 10% |
| **MEDIUM** | 2-5% | 500-1000ms | 90-95% | Reduce to 50%, investigate |
| **LOW** | <2% | <500ms | 95-100% | Monitor, no action needed |

---

## Success Criteria & Stage Gates

### Shadow Mode → Canary Gate

**Must Pass ✅ (All Required):**
- [ ] Zero unhandled exceptions in 24 hours
- [ ] v2 completes 100% of calculations (even if fallback)
- [ ] Performance p95 <500ms
- [ ] Agreement rate 60-85% (matches validation)
- [ ] Fallback rate <20%

**Should Pass ⚠️ (1+ Required):**
- [ ] v2 performance comparable to v1 (<2x overhead)
- [ ] No database connection errors
- [ ] Logs and monitoring working correctly

**Blockers ❌:**
- ANY critical errors → Fix before proceeding
- Performance p95 >1000ms → Investigate and optimize
- Agreement rate outside 50-90% → Data quality issue

**Decision:** GO / NO-GO / CONDITIONAL

---

### Canary (10%) → Staged (50%) Gate

**Must Pass ✅ (All Required):**
- [ ] Error rate <1% for 48 hours
- [ ] Conversion rate ≥95% of v1 baseline
- [ ] Zero user complaints attributable to v2
- [ ] Fallback rate <20%
- [ ] Performance p95 <500ms

**Should Pass ⚠️ (2+ Required):**
- [ ] Conversion rate ≥100% of v1 baseline
- [ ] v2 edges perceived as higher quality (user feedback)
- [ ] System stable under canary load
- [ ] No incidents requiring rollback

**Blockers ❌:**
- Conversion rate <90% of baseline → Edge quality issue
- Error rate >2% → Code or data problem
- Multiple rollbacks in canary → Not ready for scale

**Decision:** GO / NO-GO / CONDITIONAL

---

### Staged (50%) → Full (100%) Gate

**Must Pass ✅ (All Required):**
- [ ] Error rate <0.5% for 72 hours
- [ ] Conversion rate ≥95% of v1 baseline (at scale)
- [ ] Zero critical incidents in staged period
- [ ] Fallback rate <20%
- [ ] Performance p95 <500ms under 50% load
- [ ] Team confidence: "Ready for production"

**Should Pass ⚠️ (2+ Required):**
- [ ] Conversion rate ≥100% of baseline
- [ ] User satisfaction maintained or improved
- [ ] Cost per calculation comparable to v1
- [ ] Documentation complete

**Blockers ❌:**
- ANY critical incidents in staged → Investigate thoroughly
- Performance degradation at 50% → Not ready for 100%
- Data quality regressions → Fix before full rollout

**Decision:** GO / NO-GO / CONDITIONAL

---

## Incident Response Playbook

### Severity Levels

#### SEV-1 (CRITICAL) — 🚨 Immediate Action Required

**Examples:**
- Database unavailable
- v2 error rate >10%
- User-facing outage
- Data corruption

**Response:**
1. **Page on-call engineer** (immediately)
2. **Emergency rollback to v1** (5 min target)
3. **Assign incident commander**
4. **Stakeholder notification** (exec team, product team)
5. **Post-incident review** (within 24 hours)

**Timeline:**
- Detection → Response: <5 minutes
- Rollback: <5 minutes
- Communication: <10 minutes
- Resolution: Variable

---

#### SEV-2 (HIGH) — ⚠️ Urgent Action Required

**Examples:**
- Error rate 5-10%
- Performance degradation (p95 >1000ms)
- Conversion rate drop >10%
- Partial data quality issues

**Response:**
1. **Notify on-call engineer** (within 30 min)
2. **Gradual rollback** (reduce rollout percentage, within 1 hour)
3. **Investigation and triage**
4. **Status updates every 2 hours**
5. **Post-mortem** (within 1 week)

**Timeline:**
- Detection → Response: <30 minutes
- Rollback: <1 hour
- Investigation: 2-4 hours
- Resolution: Same day or next business day

---

#### SEV-3 (MEDIUM) — ℹ️ Action Required (Non-Urgent)

**Examples:**
- Error rate 2-5%
- Performance slightly degraded (p95 500-1000ms)
- Fallback rate 20-30%
- Minor conversion rate variance

**Response:**
1. **Create ticket and assign** to team
2. **Monitor closely**, no immediate rollback
3. **Investigate during business hours**
4. **Fix within 1-2 days**
5. **Brief summary in weekly report**

**Timeline:**
- Detection → Ticket: <2 hours
- Investigation: 1-2 business days
- Fix: Next sprint or hotfix

---

#### SEV-4 (LOW) — 📝 Informational

**Examples:**
- Error rate <2%
- Minor performance variance
- Cosmetic issues
- Expected data quality variations

**Response:**
1. **Log for future reference**
2. **Fix in next sprint**
3. **No immediate action required**

**Timeline:**
- Fix: Next sprint

---

## Common Scenarios & Resolutions

### Scenario 1: High Fallback Rate (>25%)

**Likely Cause:** game_log data incomplete or stale

**Investigation:**

```sql
-- Check data completeness for current season
SELECT season, week, COUNT(DISTINCT player_name) as qb_count
FROM player_game_log
WHERE season = 2025
GROUP BY season, week
ORDER BY week DESC;

-- Expected: 50-70 QBs per week for NFL season
-- If low: Run importer for missing weeks
```

```bash
# Check last import timestamp
sqlite3 data/database/nfl_betting.db \
  "SELECT MAX(last_updated) FROM player_game_log WHERE season = 2025"

# Expected: Within last 24 hours
```

**Resolution:**

```bash
# 1. Run game_log importer for current week
python utils/data_importers/game_log_importer.py --season 2025 --week current

# 2. Verify data imported successfully
python scripts/verify_deployment.py --check game_log_coverage

# 3. Monitor fallback rate for 1 hour
# Check: v2_fallback_rate_pct metric in dashboard

# 4. If still high: Investigate specific QBs falling back
python -c "
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2
from utils.db_manager import DatabaseManager

db = DatabaseManager()
v2_calc = QBTDCalculatorV2(db)

# Test specific QB
result = v2_calc.calculate_edges([{'player': 'Patrick Mahomes', 'opponent': 'LAC'}])
print(result['edges'][0]['metadata'])
# Check: fallback_to_v1, fallback_reason
"
```

---

### Scenario 2: Slow Queries (p95 >500ms)

**Likely Cause:** Missing indexes or database load

**Investigation:**

```sql
-- Check index existence
SELECT name, sql
FROM sqlite_master
WHERE type='index' AND tbl_name='player_game_log';

-- Expected indexes:
-- idx_game_log_player_name
-- idx_game_log_season_week
-- idx_game_log_composite

-- Profile slow query
EXPLAIN QUERY PLAN
SELECT
  SUM(passing_touchdowns) as total_tds,
  SUM(red_zone_passes) as total_rz_attempts,
  COUNT(DISTINCT week) as weeks_with_data
FROM player_game_log
WHERE player_name = 'Patrick Mahomes'
  AND season = 2025
  AND week >= 3
  AND week <= 7;

-- Should show: SEARCH using INDEX idx_game_log_composite
```

```bash
# Check database size and fragmentation
ls -lh data/database/nfl_betting.db

# Run VACUUM to defragment
sqlite3 data/database/nfl_betting.db "VACUUM;"

# Run ANALYZE to update query planner statistics
sqlite3 data/database/nfl_betting.db "ANALYZE;"
```

**Resolution:**

```bash
# 1. Verify critical indexes exist (see ARCHITECTURE_V2.md §8.1)
python -c "
from utils.db_manager import DatabaseManager
db = DatabaseManager()
db._create_game_log_indexes()  # Recreate if missing
"

# 2. Run VACUUM and ANALYZE
sqlite3 data/database/nfl_betting.db "VACUUM; ANALYZE;"

# 3. Test query performance
python -c "
import time
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2
from utils.db_manager import DatabaseManager

db = DatabaseManager()
v2_calc = QBTDCalculatorV2(db)

start = time.time()
result = v2_calc.calculate_edges([{'player': 'Patrick Mahomes', 'opponent': 'LAC'}])
elapsed_ms = (time.time() - start) * 1000

print(f'Query time: {elapsed_ms:.2f}ms')
# Expected: <10ms
"

# 4. If persistent: Consider caching for high-volume QBs
# Add caching layer in qb_td_calculator_v2.py (see §8.3)
```

---

### Scenario 3: Conversion Rate Drop (>5%)

**Likely Cause:** v2 edges worse quality than v1, over/under-estimating

**Investigation:**

```bash
# Compare v2 vs v1 edges for recent matchups
python scripts/compare_v1_v2_edges.py \
  --week current \
  --output investigation.json

# Analyze results
python -c "
import json

with open('investigation.json') as f:
    data = json.load(f)

# Are v2 edges consistently higher or lower?
edges = [(e['v1_edge'], e['v2_edge']) for e in data['edges']]
avg_v1 = sum(e[0] for e in edges) / len(edges)
avg_v2 = sum(e[1] for e in edges) / len(edges)

print(f'Average v1 edge: {avg_v1:.2f}%')
print(f'Average v2 edge: {avg_v2:.2f}%')
print(f'Difference: {avg_v2 - avg_v1:.2f}%')

# Are outliers affecting conversion?
outliers = [e for e in data['edges'] if abs(e['v2_edge'] - e['v1_edge']) > 5]
print(f'Outliers (>5% diff): {len(outliers)}')
for e in outliers:
    print(f\"  {e['player']}: v1={e['v1_edge']:.2f}%, v2={e['v2_edge']:.2f}%\")
"
```

**Resolution:**

```bash
# 1. Review edge calculation logic (RZ TD rate impact)
# Check: Are efficiency adjustments too aggressive?
# See: qb_td_calculator_v2.py _adjust_edge_with_v2_metrics()

# 2. Consider tuning V2_CONFIG parameters
python -c "
from utils.calculators.qb_td_calculator_v2 import V2_CONFIG
print(V2_CONFIG)

# Current thresholds:
# high_efficiency_threshold: 0.15 (15%)
# low_efficiency_threshold: 0.05 (5%)
# high_efficiency_boost: 1.15 (+15%)
# low_efficiency_penalty: 0.92 (-8%)

# If v2 edges too high: Reduce boost/penalty
# If v2 edges too low: Increase boost/penalty
"

# 3. If major issue: Gradual rollback to 10%
./scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10

# 4. Fix configuration, re-test in staging
python scripts/validate_v2_calculator.py --output retest_results.json

# 5. Resume rollout after validation
./scripts/set_feature_flag.py --flag v2_rollout_percentage --value 50
```

---

### Scenario 4: Database Connection Errors

**Likely Cause:** Connection pool exhausted, database locked, permissions issue

**Investigation:**

```bash
# Check database accessibility
sqlite3 data/database/nfl_betting.db "SELECT COUNT(*) FROM player_game_log;"

# Check file permissions
ls -l data/database/nfl_betting.db

# Expected: -rw-r--r-- (readable by application)

# Check disk space
df -h data/database/

# Expected: >10% free space
```

**Resolution:**

```bash
# 1. IMMEDIATE: Emergency rollback to v1
./scripts/emergency_rollback.sh --target 0

# 2. Check database file integrity
sqlite3 data/database/nfl_betting.db "PRAGMA integrity_check;"
# Expected: ok

# 3. Check for database locks
lsof data/database/nfl_betting.db

# 4. Fix permissions if needed
chmod 644 data/database/nfl_betting.db

# 5. Verify connection after fix
python -c "
from utils.db_manager import DatabaseManager
db = DatabaseManager()
result = db.query('SELECT COUNT(*) FROM player_game_log')
print(f'Test query successful: {result}')
"

# 6. Resume deployment after verification
./scripts/set_feature_flag.py --flag v2_rollout_percentage --value 10
```

---

## Pre-Deployment Checklist

### Before Starting Shadow Mode (Phase 0)

**Code & Configuration:**
- [ ] Feature flag system implemented and tested
- [ ] V2_ROLLOUT_PERCENTAGE set to 0
- [ ] V2_SHADOW_MODE_ENABLED set to True
- [ ] V2_MONITORING_ENABLED set to True
- [ ] Logging configuration deployed (v2_logging_config.py)

**Data Quality:**
- [ ] game_log data current (last import <24 hours)
- [ ] game_log data complete (50-70 QBs per week)
- [ ] Data quality validator passing (17/18 weeks or better)
- [ ] Name normalization applied (99.994% cross-table consistency)

**Database:**
- [ ] All required indexes exist (player_name, season_week, composite)
- [ ] Database vacuumed and analyzed
- [ ] Database file permissions correct (644)
- [ ] Sufficient disk space (>10% free)

**Monitoring:**
- [ ] Monitoring dashboard configured
- [ ] Alert rules deployed (v2_alerts.yaml)
- [ ] Logs directory exists and writable
- [ ] Test alerts working (send test notification)

**Deployment Scripts:**
- [ ] set_feature_flag.py tested in staging
- [ ] emergency_rollback.sh tested in staging
- [ ] verify_deployment.py functional
- [ ] All scripts have proper error handling

**Team Readiness:**
- [ ] Operations team trained on monitoring dashboard
- [ ] On-call engineer aware of deployment schedule
- [ ] Runbook reviewed and questions answered
- [ ] Incident response procedures understood
- [ ] Rollback procedures tested (dry run)

**Documentation:**
- [ ] ARCHITECTURE_V2.md finalized
- [ ] V2_DEPLOYMENT_RUNBOOK.md (this document) reviewed
- [ ] Troubleshooting playbook accessible
- [ ] Contact list updated (on-call, stakeholders)

---

## Deployment Timeline

### Week 1: Shadow Mode & Canary

**Day 0 (Monday):**
- 9:00 AM: Pre-deployment checklist review
- 10:00 AM: Deploy Shadow Mode (v2_rollout_percentage = 0, shadow_mode = true)
- 10:30 AM: Verify shadow mode running (check logs)
- 12:00 PM: First metrics review (2 hours of data)
- 5:00 PM: End of day review, check overnight plan
- **Overnight:** Shadow mode continues, monitor for exceptions

**Day 1 (Tuesday):**
- 9:00 AM: Shadow mode 24-hour review
  - Check: Zero exceptions, 100% completion, p95 <500ms, agreement 60-85%
- 10:00 AM: **Stage Gate Decision: Shadow → Canary**
  - GO: Proceed to Canary (10%)
  - NO-GO: Fix issues, continue shadow mode
- 11:00 AM: Deploy Canary (v2_rollout_percentage = 10)
- 12:00 PM: Verify 10% rollout (check user_id hashing)
- 3:00 PM: Mid-day metrics review
- 5:00 PM: End of day review
- **Overnight:** Canary continues, monitor for issues

**Day 2 (Wednesday):**
- 9:00 AM: Canary 24-hour review
  - Check: Error rate <1%, conversion ≥95% baseline, zero complaints
- 3:00 PM: Mid-day check
- 5:00 PM: End of day review
- **Overnight:** Canary continues

**Day 3 (Thursday):**
- 9:00 AM: Canary 48-hour review
- 10:00 AM: **Stage Gate Decision: Canary → Staged**
  - GO: Proceed to Staged (50%)
  - NO-GO: Continue canary or rollback
- 11:00 AM: Deploy Staged (v2_rollout_percentage = 50)
- 3:00 PM: Mid-day metrics review (check scale)
- 5:00 PM: End of day review
- **Overnight:** Staged (50%) continues

**Day 4 (Friday):**
- 9:00 AM: Staged 24-hour review
- 3:00 PM: Mid-day check
- 5:00 PM: Week 1 summary, plan for Week 2
- **Weekend:** Staged (50%) continues, on-call monitoring

---

### Week 2: Staged Validation & Full Rollout

**Day 5-6 (Saturday-Sunday):**
- On-call monitoring of Staged (50%)
- No active changes planned

**Day 7 (Monday):**
- 9:00 AM: Staged 72-hour review (Weekend + weekdays)
  - Check: Error rate <0.5%, conversion ≥95%, no critical incidents
- 10:00 AM: **Stage Gate Decision: Staged → Full**
  - GO: Proceed to Full (100%)
  - NO-GO: Continue staged or gradual rollback
- 11:00 AM: Deploy Full Rollout (v2_rollout_percentage = 100)
- 12:00 PM: Verify 100% rollout
- 3:00 PM: Mid-day metrics review
- 5:00 PM: End of day review
- **Overnight:** Full rollout (100%) continues

**Day 8-14 (Tuesday-Monday):**
- Daily metrics review (9:00 AM)
- Monitor for stability
- Weekly retrospective (Friday)
- After 2 weeks stable: Consider v1 deprecation planning

---

### Rollback Timeline (If Needed)

**Emergency Rollback:**
- Detection → Response: <5 minutes
- Rollback execution: <5 minutes
- Verification: <2 minutes
- Communication: <10 minutes
- **Total:** <20 minutes to full rollback

**Gradual Rollback:**
- Detection → Decision: <30 minutes
- Reduce percentage (e.g., 100% → 50%): <5 minutes
- Monitor period: 30 minutes
- Further reduction if needed: <5 minutes
- **Total:** 1-2 hours to incremental rollback

---

## Summary

This runbook provides comprehensive procedures for safely deploying the v2 QB TD Calculator to production. Key takeaways:

1. **Phased Rollout:** Shadow (0%) → Canary (10%) → Staged (50%) → Full (100%)
2. **Duration:** 8-10 days from start to full rollout
3. **Safety First:** Clear stage gates, easy rollback, comprehensive monitoring
4. **Data-Driven:** Real-time metrics inform every decision
5. **Team Readiness:** Operations trained, on-call aware, documentation complete

**Next Steps:**
1. Complete Pre-Deployment Checklist
2. Review runbook with team
3. Test monitoring and alerting in staging
4. Execute **Phase 5: Production Testing & Go/No-Go**
5. Begin Shadow Mode deployment per timeline

---

**Document Status:** ✅ Complete — Ready for Phase 5
**Last Updated:** 2025-10-22
**Version:** 1.0
**Next Phase:** Phase 5 - Production Testing & Go/No-Go Decision
