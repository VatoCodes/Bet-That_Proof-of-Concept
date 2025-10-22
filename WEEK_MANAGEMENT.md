# Week Management System

## Overview

The Week Management system provides a **single source of truth** for tracking the current NFL week across all scrapers, preventing data synchronization issues.

## The Problem (Before)

- Each scraper calculated the week independently
- Hardcoded week numbers in file names
- No way to know if data was current or stale
- Defense stats might be Week 7, odds might be Week 8

## The Solution (Now)

**Three-component system:**

1. **`current_week.json`** - Configuration file (single source of truth)
2. **`utils/week_manager.py`** - Python module for week tracking
3. **Integration** - All scripts use WeekManager

## Quick Start

### Check Current Week
```bash
python utils/week_manager.py
```

Output:
```
============================================================
CURRENT NFL WEEK INFO
============================================================
Week:        8
Season:      2025
Start Date:  2025-10-24
End Date:    2025-10-30
Status:      in_progress
Source:      manual
Updated:     2025-10-21T15:49:14.706075
============================================================
```

### Set Current Week (Manual Override)
```bash
# Set to Week 8
python utils/week_manager.py --set-week 8

# Set with status
python utils/week_manager.py --set-week 9 --status upcoming
```

**Status values:**
- `upcoming` - Week hasn't started yet
- `in_progress` - Games are being played this week
- `completed` - Week is over

### Advance to Next Week
```bash
python utils/week_manager.py --advance
```

### Validate Data Files
```bash
python utils/week_manager.py --validate
```

Output shows:
- Which files exist for current week
- Which files are missing
- Which files are outdated (from previous weeks)

Example output:
```
============================================================
DATA FILE VALIDATION - Week 8
============================================================

Files checked: 5
Current files: 0
Missing files: 5
Outdated files: 5

⚠️  Missing files for Week 8:
  - defense_stats_week_8.csv
  - matchups_week_8.csv
  - odds_qb_td_week_8.csv
  - odds_spreads_week_8.csv
  - odds_totals_week_8.csv

📦 Outdated files (from previous weeks):
  - defense_stats_week_7.csv
  - matchups_week_7.csv
  - odds_qb_td_week_7.csv
  - odds_spreads_week_7.csv
  - odds_totals_week_7.csv
============================================================
```

## Weekly Workflow

### Monday Morning (Week Transition)
```bash
# Advance to next week
python utils/week_manager.py --advance

# Verify the change
python utils/week_manager.py
```

### Before Scraping (Any Day)
```bash
# Check current week
python utils/week_manager.py

# Validate data files
python utils/week_manager.py --validate
```

### Run Scrapers
```bash
# Main scraper now uses WeekManager automatically
python main.py

# Or specify week manually (overrides WeekManager)
python main.py --week 8
```

### Test Edge Detection
```bash
# Test script now uses WeekManager automatically
python test_edge_detection.py
```

## How It Works

### Automatic Week Detection

The system uses this priority order:

1. **Manual override** - `current_week.json` (set via CLI)
2. **Date calculation** - Based on season start date (Sept 5, 2025)

### File Structure

```
Bet-That_Proof_of_Concept/
├── current_week.json              # Week configuration (single source of truth)
├── utils/
│   └── week_manager.py            # Week management module
├── config.py                      # Uses WeekManager
├── main.py                        # Uses WeekManager
└── test_edge_detection.py         # Uses WeekManager with fallback
```

### `current_week.json` Format

```json
{
  "current_week": 8,
  "season_year": 2025,
  "week_start_date": "2025-10-24",
  "week_end_date": "2025-10-30",
  "status": "in_progress",
  "last_updated": "2025-10-21T15:49:14.706075",
  "source": "manual"
}
```

## Python API

### Basic Usage

```python
from utils.week_manager import WeekManager

wm = WeekManager()

# Get current week
week = wm.get_current_week()
print(f"Current week: {week}")

# Get detailed info
info = wm.get_week_info()
print(f"Week {info['current_week']} ({info['status']})")

# Set week manually
wm.set_week(8, status='in_progress')

# Advance to next week
new_week, success = wm.advance_week()

# Validate data files
results = wm.validate_data_files()
if results['missing_files']:
    print(f"Missing: {results['missing_files']}")
```

### Integration Example

```python
# In your scraper
from utils.week_manager import WeekManager

def scrape_data():
    wm = WeekManager()
    current_week = wm.get_current_week()

    # Use current week in filename
    filename = f"defense_stats_week_{current_week}.csv"

    # Validate before scraping
    validation = wm.validate_data_files()
    if validation['files_current'] > 0:
        print(f"⚠️  Week {current_week} data already exists")
```

## Benefits

### 1. **Single Source of Truth**
- All scripts use the same week number
- No more mismatched data files

### 2. **Clear Data Status**
- Know which week you're analyzing
- Identify stale data immediately

### 3. **Automated Validation**
- Check data completeness before analysis
- Prevent using mixed-week data

### 4. **Manual Override**
- Set week manually when needed
- Useful for testing or historical analysis

### 5. **Future-Proof**
- Easy to integrate with database (Phase 1)
- Supports historical week tracking

## Future Enhancements (Phase 1)

When building the database, add:

```sql
CREATE TABLE week_metadata (
    week INTEGER,
    season_year INTEGER,
    week_start_date DATE,
    week_end_date DATE,
    status TEXT,
    last_scraped TIMESTAMP,
    PRIMARY KEY (week, season_year)
);
```

This enables:
- Historical week tracking
- Scrape timestamps per week
- Line movement analysis across weeks
- Data quality metrics per week

## Troubleshooting

### "Week 8 data not found"
Run the scraper for current week:
```bash
python main.py --week 8
```

### "Already at final week"
Regular season has 18 weeks. Check if playoffs have started:
```bash
python utils/week_manager.py
```

### "Invalid week number"
Week must be between 1-18:
```bash
python utils/week_manager.py --set-week 8
```

### Data files from wrong week
The test script will show warnings:
```
⚠️  Using fallback: defense_stats_week_7.csv (Week 8 data not found)
```

Run scraper to get current week data.

## Summary

The Week Management system ensures:
- ✅ All scripts use the same week number
- ✅ Easy to identify current vs stale data
- ✅ Manual control when needed
- ✅ Automatic validation
- ✅ Clear error messages
- ✅ Ready for database integration (Phase 1)

**Key Command:**
```bash
# Always run this first to verify what week you're working with
python utils/week_manager.py
```
