# Shadow Mode Monitoring Checklist

**Deployment Date:** 2025-10-22
**Phase:** Shadow Mode (Day 0-2)
**Status:** 🔵 ACTIVE
**Rollout:** 0% (v2 runs but not visible to users)

---

## Quick Status Check

```bash
# Check current deployment status
python3 scripts/set_feature_flag.py --verify

# Expected output:
# Status: 🔵 SHADOW MODE (v2 not visible to users)
# Rollout Percentage: 0%
# Shadow Mode: ENABLED
# Monitoring: ENABLED
```

---

## Daily Monitoring Schedule (Days 0-2)

### Day 0 (2025-10-22) - Deployment Day
- [x] 15:00 PST - Shadow Mode deployed
- [ ] 18:00 PST - First check (3 hours post-deployment)
- [ ] 23:00 PST - End-of-day check

### Day 1 (2025-10-23)
- [ ] 09:00 PST - Morning check
- [ ] 15:00 PST - Afternoon check
- [ ] 21:00 PST - Evening check

### Day 2 (2025-10-24)
- [ ] 09:00 PST - Morning check
- [ ] 15:00 PST - GO/NO-GO decision for Phase 5.5

---

## Monitoring Checklist (Run Every Check)

### 1. System Health ✅

```bash
# Check database connectivity
sqlite3 data/database/nfl_betting.db "SELECT COUNT(*) FROM player_game_log;"
# Expected: 868+ records

# Check table existence
sqlite3 data/database/nfl_betting.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
# Expected: player_game_log, play_by_play, defense_stats, etc.
```

**Criteria:**
- ✅ Database accessible
- ✅ All required tables exist
- ✅ No corruption errors

**Action if FAIL:** Emergency rollback to 0% Shadow Mode disabled

---

### 2. Feature Flag Configuration ✅

```bash
# Verify shadow mode enabled
python3 scripts/set_feature_flag.py --verify
```

**Criteria:**
- ✅ Shadow Mode: ENABLED
- ✅ Rollout Percentage: 0%
- ✅ Monitoring: ENABLED
- ✅ Status: 🔵 SHADOW MODE

**Action if FAIL:** Run `python3 scripts/set_feature_flag.py --flag v2_shadow_mode_enabled --value true`

---

### 3. v2 Calculator Functionality ✅

```bash
# Test v2 calculator with sample QB
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
python3 -c "
from utils.db_manager import DatabaseManager
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2

db = DatabaseManager()
calc = QBTDCalculatorV2(db)

# Test with Week 7, 2025
edges = calc.calculate_edges(week=7, season=2025, min_edge_threshold=2.0)
print(f'v2 calculated {len(edges)} edges')
for e in edges[:3]:
    print(f\"  {e.get('qb_name', 'Unknown')}: {e.get('edge_percentage', 0):.1f}%\")
"
```

**Criteria:**
- ✅ No exceptions/crashes
- ✅ Returns edges (even if empty list is okay)
- ✅ Edge structure valid (qb_name, edge_percentage, etc.)

**Action if FAIL:** Investigate error logs, consider rollback if critical

---

### 4. Error Rate Monitoring 🎯

**Target:** 0% errors (MUST PASS)

```bash
# Check for v2 calculation errors in application logs
# (Adjust log path as needed)
tail -100 logs/application.log | grep -i "v2.*error\|v2.*exception\|v2.*fail" || echo "No v2 errors found"
```

**Criteria:**
- ✅ Zero unhandled exceptions
- ✅ Zero calculation failures
- ⚠️ Fallback to v1 is okay (tracked separately)

**Action if errors >0%:**
- Review error logs
- Identify root cause
- If SEV-1: Emergency rollback
- If SEV-2: Fix and redeploy

---

### 5. Performance Monitoring 🎯

**Target:** P95 <500ms (MUST PASS)

```bash
# Run performance test
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
python3 -c "
import time
from utils.db_manager import DatabaseManager
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2

db = DatabaseManager()
calc = QBTDCalculatorV2(db)

times = []
for i in range(10):
    start = time.time()
    edges = calc.calculate_edges(week=7, season=2025)
    elapsed_ms = (time.time() - start) * 1000
    times.append(elapsed_ms)

times.sort()
p95 = times[int(len(times) * 0.95)]
avg = sum(times) / len(times)

print(f'Average: {avg:.2f}ms')
print(f'P95: {p95:.2f}ms')
print(f'Target: <500ms')
print(f'Status: {\"✅ PASS\" if p95 < 500 else \"❌ FAIL\"}')
"
```

**Criteria:**
- ✅ P95 <500ms
- ✅ Average <100ms preferred
- ⚠️ Max <1000ms acceptable

**Action if FAIL:**
- Check database indexes
- Review query optimization
- If P95 >1000ms: Emergency rollback

---

### 6. Agreement Rate Monitoring 🎯

**Target:** 60-85% agreement with v1 (SHOULD PASS)
**Phase 5 Result:** 88.9% (acceptable, monitor for consistency)

```bash
# Run v1 vs v2 comparison
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
python3 scripts/compare_v1_v2_edges.py --week 7 --season 2025
```

**Criteria:**
- ✅ Agreement rate 60-90% (some variance okay)
- ⚠️ Agreement rate <60%: May indicate v2 calculation issue
- ⚠️ Agreement rate >95%: May indicate insufficient differentiation

**Action if outside range:**
- Review edge calculation logic
- Check game_log data quality
- Compare with Phase 5 validation results

---

### 7. Fallback Rate Monitoring 🎯

**Target:** <20% (MUST PASS)
**Phase 5 Result:** 12.5%

```bash
# Check fallback rate
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
python3 -c "
from utils.db_manager import DatabaseManager
from utils.calculators.qb_td_calculator_v2 import QBTDCalculatorV2

db = DatabaseManager()
calc = QBTDCalculatorV2(db)

edges = calc.calculate_edges(week=7, season=2025)
total = len(edges)
fallbacks = sum(1 for e in edges if e.get('model_version') == 'v2_fallback')

fallback_pct = (fallbacks / total * 100) if total > 0 else 0
print(f'Total edges: {total}')
print(f'Fallbacks to v1: {fallbacks}')
print(f'Fallback rate: {fallback_pct:.1f}%')
print(f'Target: <20%')
print(f'Status: {\"✅ PASS\" if fallback_pct < 20 else \"❌ FAIL\"}')
"
```

**Criteria:**
- ✅ Fallback rate <20%
- ⚠️ Fallback rate 20-30%: Investigate data quality
- ❌ Fallback rate >30%: Data quality issue

**Action if >20%:**
- Check game_log data completeness
- Re-run PlayerProfiler imports if needed
- Verify minimum data thresholds (v2_min_game_log_games = 3)

---

### 8. Data Quality Validation 🎯

```bash
# Check 2025 season data coverage
sqlite3 data/database/nfl_betting.db "
SELECT
  season,
  COUNT(DISTINCT player_name) as qb_count,
  COUNT(DISTINCT week) as week_count,
  MAX(week) as latest_week,
  COUNT(*) as total_games
FROM player_game_log
WHERE season = 2025
GROUP BY season;
"
```

**Criteria:**
- ✅ QBs: 30+ (Phase 5 had 36)
- ✅ Weeks: 6+ (Phase 5 tested Weeks 1-6)
- ✅ Games: 150+ (Phase 5 had 184)

**Action if FAIL:**
- Re-import game_log data
- Check PlayerProfiler for updates
- Consider Phase 5.5 with nflfastR

---

## Success Criteria for Shadow Mode ✅

**MUST PASS (All Required):**
- [ ] Zero unhandled exceptions in 48 hours
- [ ] v2 completes 100% of calculations (even if fallback)
- [ ] Performance P95 <500ms
- [ ] Agreement rate 60-90%
- [ ] Fallback rate <20%

**SHOULD PASS (Preferred):**
- [ ] No user-reported issues (Shadow Mode = no user visibility)
- [ ] Database stable (no performance degradation)
- [ ] Team confident in v2 behavior

---

## GO/NO-GO Decision for Phase 5.5 (Day 2)

**Decision Date:** 2025-10-24 15:00 PST

### GO Criteria ✅
- All MUST PASS criteria met for 48 hours
- No critical issues identified
- Team confident to proceed

### NO-GO Criteria ❌
- Any MUST PASS criterion failed
- Unresolved critical bugs
- Performance degradation
- Data quality concerns

**If GO:**
- Proceed to Phase 5.5 (nflfastR integration + Week 7 retest)
- Keep Shadow Mode enabled during Phase 5.5
- Target: Complete Phase 5.5 by Day 4 (2025-10-26)

**If NO-GO:**
- Disable Shadow Mode: `python3 scripts/set_feature_flag.py --flag v2_shadow_mode_enabled --value false`
- Investigate and fix issues
- Retest before re-enabling Shadow Mode

---

## Emergency Rollback Procedure 🚨

**Trigger:** Critical errors, performance issues, or data corruption

```bash
# Emergency rollback (disables Shadow Mode)
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
./scripts/emergency_rollback.sh --target 0 --yes

# Or manually:
python3 scripts/set_feature_flag.py --flag v2_shadow_mode_enabled --value false
python3 scripts/set_feature_flag.py --verify
```

**Post-Rollback:**
1. Document issue in incident log
2. Notify team via #engineering-alerts
3. Root cause analysis
4. Fix and retest before re-enabling

---

## Log Files & Monitoring

### Key Files to Monitor
```bash
# Application logs (adjust path as needed)
tail -f logs/application.log

# v2 calculation logs (if separate)
tail -f logs/v2_calculations.jsonl

# Database queries (if query logging enabled)
tail -f logs/database_queries.log
```

### Useful Queries

```bash
# Check v2 calculation count per week
sqlite3 data/database/nfl_betting.db "
SELECT week, COUNT(*) as edge_count
FROM (
  -- This would be from a v2_edges table if it exists
  -- Adjust as needed based on your schema
  SELECT 1 as week
)
GROUP BY week;
"

# Check recent game_log imports
sqlite3 data/database/nfl_betting.db "
SELECT season, week, COUNT(*) as games, MAX(imported_at) as last_import
FROM player_game_log
GROUP BY season, week
ORDER BY season DESC, week DESC
LIMIT 10;
"
```

---

## Communication Plan

### Daily Status Updates

**Template:**
```
🔵 Shadow Mode Status - Day X (YYYY-MM-DD)

✅ System Health: PASS
✅ Error Rate: 0%
✅ Performance P95: X.Xms (<500ms target)
✅ Agreement Rate: XX% (60-90% target)
✅ Fallback Rate: XX% (<20% target)

Next Check: [Time]
Next Decision: [Phase 5.5 GO/NO-GO on 2025-10-24]
```

### Escalation Contacts
- **Technical Lead:** [Name/Contact]
- **Deployment Lead:** [Name/Contact]
- **On-Call Engineer:** [Name/Contact]

---

## Next Steps After Shadow Mode

**If all criteria met (Day 2):**
1. ✅ Keep Shadow Mode enabled
2. Execute Phase 5.5 (nflfastR + Week 7 validation)
3. Target completion: Day 4 (2025-10-26)
4. GO/NO-GO for Canary 10%: Day 5 (2025-10-27)

**Phase 5.5 → Canary Transition:**
- Shadow Mode validation: 48 hours ✅
- Phase 5.5 Week 7 retest: Complete ✅
- Canary rollout: 10% users
- Duration: 48-72 hours
- Success criteria: Same as Shadow Mode but with user traffic

---

**Document Version:** 1.0
**Last Updated:** 2025-10-22 15:00 PST
**Status:** 🔵 ACTIVE MONITORING
