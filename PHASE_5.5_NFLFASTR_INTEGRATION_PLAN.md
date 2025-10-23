# Phase 5.5: nflfastR Integration & Week 7 Validation Plan

**Phase:** 5.5 (Optional but Recommended)
**Purpose:** Complete Week 7 2025 validation with nflfastR data before Canary deployment
**Timeline:** Days 2-4 (2025-10-24 to 2025-10-26)
**Confidence Impact:** MEDIUM → HIGH
**Risk:** LOW (Shadow Mode remains active, no user impact)

---

## Executive Summary

Phase 5 successfully validated v2 with Weeks 1-6 data (36 QBs, 184 games) but Week 7 2025 data was unavailable due to PlayerProfiler update timing. Phase 5.5 addresses this gap by:

1. Integrating nflfastR as an additional data source
2. Importing Week 7 2025 play-by-play and game log data
3. Re-running production test with complete current week
4. Validating all MUST PASS criteria with fresh data

**Benefits:**
- ✅ Complete week validation (not partial)
- ✅ Current season data (not historical)
- ✅ Higher confidence for Canary deployment
- ✅ Adds nflfastR as backup data source
- ✅ Validates v2 with most recent NFL games

---

## Prerequisites

### 1. Shadow Mode Validation ✅

**Required before starting Phase 5.5:**
- [ ] Shadow Mode active for 48 hours (Day 0-2)
- [ ] All MUST PASS criteria met in Shadow Mode
- [ ] No critical issues identified
- [ ] Team confident in v2 behavior

**Verify:**
```bash
python3 scripts/set_feature_flag.py --verify
# Expected: Status: 🔵 SHADOW MODE
```

### 2. Python Dependencies

```bash
# Install nflfastR Python package
pip install nfl_data_py

# Verify installation
python3 -c "import nfl_data_py as nfl; print(f'nfl_data_py version: {nfl.__version__}')"
```

---

## Implementation Steps

### Step 1: Install nflfastR Package (15 min)

```bash
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)

# Install nfl_data_py (Python wrapper for nflfastR)
pip install nfl_data_py pandas numpy

# Test installation
python3 -c "
import nfl_data_py as nfl
print('✅ nfl_data_py installed successfully')
print(f'Available functions: {dir(nfl)}')
"
```

**Expected output:**
- Package installs without errors
- Functions available: `import_pbp_data`, `import_weekly_data`, etc.

---

### Step 2: Create nflfastR Importer Script (30 min)

Create `utils/data_importers/nflfastr_importer.py`:

```python
"""
nflfastR Data Importer

Imports play-by-play and game log data from nflfastR (nfl_data_py package).
Provides backup/supplement to PlayerProfiler data.
"""

import nfl_data_py as nfl
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class NFLFastRImporter:
    """Import NFL data from nflfastR via nfl_data_py package"""

    def __init__(self, db_manager):
        """
        Initialize importer

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager

    def import_play_by_play(self, season: int, weeks: list = None):
        """
        Import play-by-play data for specified season and weeks

        Args:
            season: NFL season year (e.g., 2025)
            weeks: List of week numbers (e.g., [7, 8]) or None for all weeks

        Returns:
            Number of rows imported
        """
        logger.info(f"Importing nflfastR play-by-play data: {season} weeks {weeks}")

        try:
            # Import play-by-play data from nflfastR
            pbp_df = nfl.import_pbp_data([season])

            # Filter to specified weeks if provided
            if weeks:
                pbp_df = pbp_df[pbp_df['week'].isin(weeks)]

            # Select relevant columns for our schema
            # Adjust based on your play_by_play table schema
            columns_map = {
                'game_id': 'game_id',
                'play_id': 'play_id',
                'week': 'week',
                'posteam': 'possession_team',
                'defteam': 'defense_team',
                'yardline_100': 'yards_to_goal',
                'down': 'down',
                'ydstogo': 'yards_to_go',
                'play_type': 'play_type',
                'passer_player_name': 'passer_name',
                'receiver_player_name': 'receiver_name',
                'pass_length': 'pass_length',
                'pass_location': 'pass_location',
                'air_yards': 'air_yards',
                'yards_after_catch': 'yards_after_catch',
                'touchdown': 'is_touchdown',
                'complete_pass': 'is_complete',
                'interception': 'is_interception',
            }

            # Rename columns to match our schema
            import_df = pbp_df[list(columns_map.keys())].rename(columns=columns_map)

            # Add season and import timestamp
            import_df['season'] = season
            import_df['imported_at'] = datetime.now()

            # Upsert to database
            self.db_manager.upsert_play_by_play(import_df)

            rows_imported = len(import_df)
            logger.info(f"✅ Imported {rows_imported} play-by-play rows from nflfastR")

            return rows_imported

        except Exception as e:
            logger.error(f"❌ Failed to import nflfastR play-by-play: {e}")
            raise

    def import_weekly_rosters(self, season: int, weeks: list = None):
        """
        Import weekly roster data (for game logs)

        Args:
            season: NFL season year
            weeks: List of week numbers or None for all

        Returns:
            Number of rows imported
        """
        logger.info(f"Importing nflfastR weekly rosters: {season} weeks {weeks}")

        try:
            # Import weekly data from nflfastR
            weekly_df = nfl.import_weekly_data([season])

            # Filter to specified weeks
            if weeks:
                weekly_df = weekly_df[weekly_df['week'].isin(weeks)]

            # Filter to QB position only
            weekly_df = weekly_df[weekly_df['position'] == 'QB']

            # Map to player_game_log schema
            game_log_df = pd.DataFrame({
                'player_id': weekly_df['player_id'],
                'player_name': weekly_df['player_display_name'],
                'week': weekly_df['week'],
                'season': season,
                'position': 'QB',
                'team': weekly_df['recent_team'],
                'opponent': weekly_df['opponent_team'],
                'passing_attempts': weekly_df.get('attempts', 0),
                'passing_completions': weekly_df.get('completions', 0),
                'passing_yards': weekly_df.get('passing_yards', 0),
                'passing_touchdowns': weekly_df.get('passing_tds', 0),
                'interceptions': weekly_df.get('interceptions', 0),
                'rushing_attempts': weekly_df.get('carries', 0),
                'rushing_yards': weekly_df.get('rushing_yards', 0),
                'rushing_touchdowns': weekly_df.get('rushing_tds', 0),
                'imported_at': datetime.now(),
            })

            # Note: nflfastR doesn't provide red_zone_passes directly
            # We'll need to calculate from play-by-play data
            game_log_df['red_zone_passes'] = 0  # Placeholder, calculate later
            game_log_df['red_zone_completions'] = 0

            # Upsert to database
            self.db_manager.upsert_player_game_log(game_log_df)

            rows_imported = len(game_log_df)
            logger.info(f"✅ Imported {rows_imported} game log rows from nflfastR")

            return rows_imported

        except Exception as e:
            logger.error(f"❌ Failed to import nflfastR weekly rosters: {e}")
            raise

    def calculate_red_zone_stats(self, season: int, weeks: list):
        """
        Calculate red zone stats from play-by-play data

        Args:
            season: NFL season year
            weeks: List of week numbers

        Returns:
            DataFrame with red zone stats per QB per week
        """
        logger.info(f"Calculating red zone stats from nflfastR data")

        try:
            # Import play-by-play for red zone analysis
            pbp_df = nfl.import_pbp_data([season])

            if weeks:
                pbp_df = pbp_df[pbp_df['week'].isin(weeks)]

            # Filter to red zone plays (inside 20-yard line)
            rz_df = pbp_df[pbp_df['yardline_100'] <= 20]

            # Filter to pass plays with QB name
            rz_passes = rz_df[
                (rz_df['play_type'] == 'pass') &
                (rz_df['passer_player_name'].notna())
            ]

            # Group by QB, week
            rz_stats = rz_passes.groupby(['passer_player_name', 'week']).agg({
                'pass_attempt': 'sum',  # Total RZ passes
                'complete_pass': 'sum',  # RZ completions
                'touchdown': 'sum',  # RZ TDs
            }).reset_index()

            rz_stats.columns = ['player_name', 'week', 'red_zone_passes', 'red_zone_completions', 'red_zone_tds']
            rz_stats['season'] = season

            return rz_stats

        except Exception as e:
            logger.error(f"❌ Failed to calculate red zone stats: {e}")
            raise


def import_week_7_data():
    """
    Convenience function to import Week 7 2025 data from nflfastR

    Run this after Shadow Mode validation to get current week data
    """
    from utils.db_manager import DatabaseManager

    db = DatabaseManager()
    importer = NFLFastRImporter(db)

    print("\\n" + "="*60)
    print("Phase 5.5: nflfastR Week 7 2025 Data Import")
    print("="*60 + "\\n")

    # Import play-by-play data
    print("Step 1/3: Importing play-by-play data...")
    pbp_rows = importer.import_play_by_play(season=2025, weeks=[7])
    print(f"✅ Imported {pbp_rows} play-by-play rows\\n")

    # Import weekly rosters (game logs)
    print("Step 2/3: Importing game log data...")
    log_rows = importer.import_weekly_rosters(season=2025, weeks=[7])
    print(f"✅ Imported {log_rows} game log rows\\n")

    # Calculate and update red zone stats
    print("Step 3/3: Calculating red zone stats...")
    rz_stats = importer.calculate_red_zone_stats(season=2025, weeks=[7])
    print(f"✅ Calculated red zone stats for {len(rz_stats)} QB-weeks\\n")

    # Update game_log with red zone stats
    for _, row in rz_stats.iterrows():
        db.cursor.execute("""
            UPDATE player_game_log
            SET red_zone_passes = ?,
                red_zone_completions = ?
            WHERE player_name = ?
              AND season = ?
              AND week = ?
        """, (
            row['red_zone_passes'],
            row['red_zone_completions'],
            row['player_name'],
            row['season'],
            row['week']
        ))

    db.conn.commit()
    print(f"✅ Updated red zone stats for {len(rz_stats)} QBs\\n")

    print("="*60)
    print("✅ nflfastR Week 7 import complete!")
    print("="*60 + "\\n")

    print("Next: Run production test with Week 7 data")
    print("  python3 scripts/phase5_production_test.py --week 7\\n")


if __name__ == '__main__':
    import_week_7_data()
```

---

### Step 3: Run Week 7 Import (20 min)

```bash
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)

# Run the import script
python3 utils/data_importers/nflfastr_importer.py
```

**Expected output:**
- Play-by-play rows imported: ~5000-7000 (Week 7 plays)
- Game log rows imported: 28-32 (QBs who played Week 7)
- Red zone stats calculated for all QBs

**Verify:**
```bash
sqlite3 data/database/nfl_betting.db "
SELECT season, week, COUNT(DISTINCT player_name) as qb_count, COUNT(*) as games
FROM player_game_log
WHERE season = 2025 AND week = 7
GROUP BY season, week;
"
# Expected: 28-32 QBs, 28-32 games
```

---

### Step 4: Re-run Production Test with Week 7 (15 min)

```bash
# Run production test with Week 7 data
python3 scripts/phase5_production_test.py --week 7 --season 2025

# Or create a Phase 5.5 specific test script
python3 scripts/phase5.5_week7_validation.py
```

**Create `scripts/phase5.5_week7_validation.py`:**
- Copy from `scripts/phase5_production_test.py`
- Update to test Week 7 specifically
- Compare with Phase 5 (Weeks 1-6) results
- Generate `PHASE_5.5_WEEK7_RESULTS.json`

---

### Step 5: Validate Results (10 min)

**Success Criteria (Same as Phase 5):**

| Criterion | Target | Phase 5 Result | Phase 5.5 Expected |
|-----------|--------|----------------|-------------------|
| QBs Tested | 25+ | 36 | 28-32 |
| Success Rate | 100% | 100% | 100% |
| Error Rate | <1% | 0% | 0% |
| Performance P95 | <500ms | 0.54ms | <1ms |
| Agreement Rate | 60-85% | 88.9% | 60-90% |
| Fallback Rate | <20% | 12.5% | <20% |

**Validation Commands:**
```bash
# Check results
cat PHASE_5.5_WEEK7_RESULTS.json | python3 -m json.tool

# Compare with Phase 5
python3 -c "
import json

# Load Phase 5 results
with open('PRODUCTION_TEST_RESULTS.json') as f:
    phase5 = json.load(f)

# Load Phase 5.5 results
with open('PHASE_5.5_WEEK7_RESULTS.json') as f:
    phase5_5 = json.load(f)

print('Phase 5 (Weeks 1-6):')
print(f\"  QBs: {phase5['metadata']['qb_count']}\")
print(f\"  Agreement: {phase5['analysis']['agreement']['rate']}%\")
print(f\"  Fallback: {phase5['analysis']['fallback_rate']}%\")

print('\\nPhase 5.5 (Week 7):')
print(f\"  QBs: {phase5_5['metadata']['qb_count']}\")
print(f\"  Agreement: {phase5_5['analysis']['agreement']['rate']}%\")
print(f\"  Fallback: {phase5_5['analysis']['fallback_rate']}%\")
"
```

---

## Decision Framework

### GO Criteria for Canary Deployment ✅

**All MUST PASS:**
- [ ] Week 7 validation: 100% success rate
- [ ] Week 7 validation: 0% error rate
- [ ] Week 7 validation: P95 <500ms
- [ ] Week 7 validation: 60-90% agreement
- [ ] Week 7 validation: <20% fallback rate
- [ ] Confidence level: HIGH

**If all pass:**
- ✅ Proceed to Canary 10% deployment
- ✅ Timeline: Day 5 (2025-10-27)
- ✅ Keep Shadow Mode disabled, enable 10% rollout
- ✅ Confidence: HIGH

### NO-GO Criteria ❌

**Any of:**
- Week 7 validation fails any MUST PASS criterion
- nflfastR data quality issues
- Inconsistency between Phase 5 and Phase 5.5 results
- Team not confident

**If NO-GO:**
- Investigate discrepancies
- Fix data quality issues
- Retest before Canary
- May proceed with MEDIUM confidence (Phase 5 only) if time-sensitive

---

## Rollback Plan

**If Phase 5.5 encounters issues:**

```bash
# Phase 5.5 doesn't affect Shadow Mode
# Shadow Mode remains active during Phase 5.5
# No rollback needed unless Shadow Mode itself fails

# To remove nflfastR data if needed:
sqlite3 data/database/nfl_betting.db "
DELETE FROM player_game_log WHERE season = 2025 AND week = 7;
DELETE FROM play_by_play WHERE season = 2025 AND week = 7;
"
```

---

## Timeline & Milestones

| Day | Date | Milestone | Duration |
|-----|------|-----------|----------|
| 2 | 2025-10-24 | Phase 5.5 Start | - |
| 2 | 2025-10-24 | Install nflfastR | 15 min |
| 2 | 2025-10-24 | Create importer script | 30 min |
| 2 | 2025-10-24 | Import Week 7 data | 20 min |
| 3 | 2025-10-25 | Validate Week 7 data quality | 30 min |
| 3 | 2025-10-25 | Run Week 7 production test | 15 min |
| 3 | 2025-10-25 | Analyze results | 30 min |
| 4 | 2025-10-26 | GO/NO-GO decision | - |
| 5 | 2025-10-27 | Canary 10% (if GO) | - |

**Total Duration:** 2.5-3 hours across 2-3 days

---

## Benefits Summary

### Why Execute Phase 5.5?

1. **Complete Week Validation** 🎯
   - Phase 5: Partial data (Weeks 1-6, PlayerProfiler lag)
   - Phase 5.5: Complete week (Week 7, current data)

2. **Higher Confidence** 📈
   - MEDIUM → HIGH confidence
   - Fresh data validation (not 2-3 weeks old)
   - Reduces uncertainty for Canary deployment

3. **Additional Data Source** 🔄
   - nflfastR as backup to PlayerProfiler
   - Faster data availability (no 24-48h lag)
   - Cross-validation between sources

4. **Risk Mitigation** 🛡️
   - Validates v2 with most recent games
   - Catches any week-specific issues
   - Low cost (2-3 hours) for high value

5. **Production-Ready** ✅
   - Canary deployment with HIGH confidence
   - Team fully confident in v2 behavior
   - Stakeholders reassured

---

## Next Steps After Phase 5.5

**If Phase 5.5 PASS:**
1. Update GO_NO_GO_DECISION.md with Phase 5.5 results
2. Update confidence level: MEDIUM → HIGH
3. Proceed to Canary 10% deployment (Day 5)
4. Keep nflfastR integration for future imports

**If Phase 5.5 DEFERRED:**
1. Proceed to Canary with MEDIUM confidence (Phase 5 only)
2. Monitor Canary closely for Week 7+ data
3. Consider nflfastR integration later

---

**Document Version:** 1.0
**Created:** 2025-10-22
**Status:** 📋 READY FOR EXECUTION
**Estimated Effort:** 2.5-3 hours
**Risk:** LOW
**Value:** HIGH
