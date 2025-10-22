# PlayerProfiler Data Importers - Phase 1

This module contains importers for integrating PlayerProfiler CSV data into the Bet-That database.

## Status: ✅ READY FOR TESTING

### Completed Components

1. **Database Schema** (`utils/migrations/002_playerprofile_schema.sql`)
   - 5 new tables: play_by_play, team_metrics, kicker_stats, qb_stats_enhanced, player_roster
   - 23 indexes (19 explicit + 4 auto from UNIQUE constraints)
   - All validations passing

2. **Database Manager Extensions** (`utils/db_manager.py`)
   - Added 9 new methods for PlayerProfiler data:
     - `upsert_play_by_play()`, `upsert_team_metrics()`, `upsert_kicker_stats()`, etc.
     - `get_team_metrics()`, `get_kicker_stats()`, `get_qb_stats_enhanced()`, etc.

3. **Data Importers**:
   - `playerprofile_importer.py` - Main orchestrator
   - `play_by_play_importer.py` - Imports play-by-play data
   - `custom_reports_importer.py` - Imports kicker & QB stats
   - `roster_importer.py` - Imports weekly roster availability
   - `team_metrics_calculator.py` - Calculates team metrics from PBP

## Usage

### Import 2024 Season Data

```bash
cd "/Users/vato/work/Bet-That_(Proof of Concept)"

# Run importer for 2024 season
python3 -m utils.data_importers.playerprofile_importer --season 2024
```

### Verify Import

```bash
# Check database stats
python3 utils/db_manager.py --stats

# Should show:
#   play_by_play: ~50,000+ rows
#   team_metrics: ~576 rows (32 teams × 18 weeks)
#   kicker_stats: 32-64 rows
#   qb_stats_enhanced: 64-96 rows
#   player_roster: 1,500+ rows per week
```

## Architecture Pattern

All importers follow the existing **snapshot-then-upsert** pattern:

1. **Load CSV** - Read PlayerProfiler data
2. **Clean/Transform** - Map columns, handle nulls, type conversions
3. **Save Snapshot** - Historical backup to `data/historical/playerprofile_imports/`
4. **Upsert DB** - DELETE existing + INSERT new (idempotent)

## Data Flow

```
PlayerProfiler CSVs
        ↓
[Load & Clean]
        ↓
Historical Snapshot (timestamped CSV)
        ↓
Database Upsert (idempotent)
```

## Important Notes

### Column Mappings

**Play-by-Play**: Maps PlayerProfiler columns to simplified schema
- `playid` → `play_id`
- `gamekey_internal` → `game_key`
- `yards_gained` → `yards_gained`
- etc.

**Custom Reports**: Extracts position-specific stats
- Kickers: Filtered by `position == 'K'`, extracts FG%, points/game
- QBs: Filtered by `position == 'QB'`, extracts red zone accuracy, deep ball %

**Roster**: Tracks player availability by week
- Maps status codes: ACT → Active, IR → IR, etc.

### Known Limitations (MVP Phase 1)

1. **Simplified Metrics**: Team metrics calculator uses basic aggregations
   - First half scoring not fully implemented (would need TD/FG detection)
   - Red zone stats simplified
   - Kicker FG attempts per team not fully tracked

2. **2024 Season Only**: Current implementation focuses on 2024 data
   - Historical import (2020-2023) is Phase 2

3. **Column Availability**: Some PlayerProfiler columns may vary by year
   - Importers handle missing columns gracefully with `.get()` and `.fillna()`

## Troubleshooting

### Import Fails with "File Not Found"

Check file paths match:
```bash
ls "/Users/vato/work/Bet-That/storage/imports/PlayerProfiler/Advanced Play by Play/"
ls "/Users/vato/work/Bet-That/storage/imports/PlayerProfiler/Custom Reports/"
ls "/Users/vato/work/Bet-That/storage/imports/PlayerProfiler/Weekly Roster Key/"
```

### Column Name Mismatch

PlayerProfiler column names may change. Check first row:
```bash
head -1 "/path/to/file.csv"
```

Update column mappings in respective importer if needed.

### Database Locked

If SQLite complains about locked database:
```bash
# Check for open connections
lsof /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)/data/database/nfl_betting.db

# Close any Python processes
```

## Next Steps (After Import Completes)

1. **Create Edge Calculators** (Step C)
   - `utils/calculators/first_half_total_calculator.py`
   - `utils/calculators/kicker_points_calculator.py`
   - `utils/calculators/qb_td_calculator_v2.py`

2. **Extend Dashboard** (Step D)
   - Add API routes in `dashboard/app.py`
   - Update `templates/edges.html` with multi-strategy tabs

3. **End-to-End Testing**
   - Verify edge detection works
   - Manual spot-check edges against sportsbook lines

## Rollback

If import fails, rollback schema:
```bash
sqlite3 data/database/nfl_betting.db < utils/migrations/002_playerprofile_schema_rollback.sql
```

This will DROP all 5 new tables. Historical snapshots in `data/historical/` are preserved.
