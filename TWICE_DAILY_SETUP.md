# Twice-Daily Scraping Setup Guide

**Version 2.5** - Line Movement Tracking Enabled

---

## Overview

Your system now runs **TWICE DAILY** to track line movements:
- **9:00 AM**: Full scrape (all data)
- **3:00 PM**: Odds-only scrape (line movement tracking)

---

## Quick Start

### 1. Set Current Week First

**IMPORTANT: Always set the current week before starting schedulers**

```bash
# Check current week
python utils/week_manager.py

# Set to current NFL week (e.g., Week 8)
python utils/week_manager.py --set-week 8 --status in_progress

# Validate that you have (or need) data for this week
python utils/week_manager.py --validate
```

See [WEEK_MANAGEMENT.md](WEEK_MANAGEMENT.md) for complete week tracking guide.

### 2. Start Both Schedulers

```bash
# Option A: Two terminals
# Terminal 1
python scheduler.py

# Terminal 2
python scheduler_odds.py
```

```bash
# Option B: Background (recommended for production)
nohup python scheduler.py > scheduler_main.log 2>&1 &
nohup python scheduler_odds.py > scheduler_odds_output.log 2>&1 &
```

### 3. Verify They're Running

```bash
# Check processes
ps aux | grep scheduler

# Check logs
tail -f scheduler.log        # 9am runs
tail -f scheduler_odds.log   # 3pm runs
tail -f scraper.log          # Actual scraping output
```

### 4. Stop Schedulers

```bash
# Find process IDs
ps aux | grep scheduler

# Kill processes
kill <PID_main_scheduler>
kill <PID_odds_scheduler>
```

---

## Weekly Workflow

### Monday Morning - Week Transition

```bash
# 1. Advance to next week
python utils/week_manager.py --advance

# 2. Verify week was updated
python utils/week_manager.py

# Output should show new week (e.g., Week 9)
```

### Before Any Scrape - Validate Current Week

```bash
# Check what week we're tracking
python utils/week_manager.py

# Validate data files exist for current week
python utils/week_manager.py --validate

# If missing files, you'll see warnings:
# ⚠️  Missing files for Week 8:
#   - defense_stats_week_8.csv
#   - matchups_week_8.csv
#   ...
```

---

## What Runs When

### Morning (9:00 AM) - Full Scrape
**Files Created:**
- `defense_stats_week_7.csv`
- `qb_stats_2025.csv`
- `matchups_week_7.csv`
- `odds_spreads_week_7.csv`
- `odds_totals_week_7.csv`
- `odds_qb_td_week_7.csv`

**API Calls:** ~19 per run

### Afternoon (3:00 PM) - Odds Only
**Files Created:**
- `matchups_week_7.csv` (refreshed)
- `odds_spreads_week_7_3pm.csv` ⭐ New
- `odds_totals_week_7_3pm.csv` ⭐ New
- `odds_qb_td_week_7_3pm.csv` ⭐ New

**API Calls:** ~19 per run

---

## Line Movement Analysis

Compare 9am vs 3pm odds to see how lines moved:

```python
import pandas as pd

# Load morning odds
spreads_9am = pd.read_csv('data/raw/odds_spreads_week_7.csv')

# Load afternoon odds
spreads_3pm = pd.read_csv('data/raw/odds_spreads_week_7_3pm.csv')

# Compare
for idx, row in spreads_9am.iterrows():
    game = row['game']
    team = row['team']
    spread_9am = row['spread']

    # Find matching 3pm line
    match = spreads_3pm[(spreads_3pm['game'] == game) &
                        (spreads_3pm['team'] == team)]

    if not match.empty:
        spread_3pm = match.iloc[0]['spread']
        movement = spread_3pm - spread_9am

        if movement != 0:
            print(f"{game} - {team}: {spread_9am} → {spread_3pm} ({movement:+.1f})")
```

---

## API Usage

### Daily Usage
- Morning run: ~19 calls
- Afternoon run: ~19 calls
- **Total per day: ~38 calls**

### Weekly Usage
- 6 days × 38 calls = **~228 calls/week**

### Monthly Usage
- 228 × 4.3 weeks = **~980 calls/month**
- **Utilization: 4.3%** of 23,000 capacity
- **Remaining: 95.7%** (22,020 requests)

✅ **Still massive headroom!**

---

## Testing

### Pre-Test: Set Week
```bash
# ALWAYS set week before testing
python utils/week_manager.py --set-week 8 --status in_progress
```

### Test Morning Scheduler
```bash
python scheduler.py --test
```

Expected output:
- All 6 CSV files created (for Week 8)
- ~19 API calls used
- Run completes in ~1 minute

### Test Afternoon Scheduler
```bash
python scheduler_odds.py --test
```

Expected output:
- 3 odds CSV files created (with `_3pm` suffix for Week 8)
- ~19 API calls used
- Run completes in ~45 seconds

### Validate Results
```bash
# Check that data files were created for current week
python utils/week_manager.py --validate

# Expected: All files should now exist
# Files found: 5/5
```

---

## Monitoring

### Check Logs
```bash
# Main scheduler (9am)
tail -f scheduler.log

# Odds scheduler (3pm)
tail -f scheduler_odds.log

# Pipeline execution (both)
tail -f scraper.log
```

### Check API Usage
```bash
python -c "
from scrapers.odds_scraper import OddsScraper
s = OddsScraper()
status = s.get_usage_report()
print(f\"Requests used: {status['total_requests']}\")
print(f\"Requests remaining: {status['remaining_requests']}\")
"
```

### Verify Output Files
```bash
# List all odds files
ls -lh data/raw/odds_*.csv

# Should see both 9am and 3pm versions
# odds_spreads_week_7.csv       (9am)
# odds_spreads_week_7_3pm.csv   (3pm)
```

---

## Troubleshooting

### Only one scheduler running?
- Check both processes: `ps aux | grep scheduler`
- You should see TWO Python processes

### No 3pm files created?
- Check `scheduler_odds.log` for errors
- Verify `scheduler_odds.py` is running
- Test manually: `python scheduler_odds.py --test`

### API usage growing too fast?
- Should be ~38 calls/day = ~228/week
- Check logs for unexpected runs
- Verify only ONE instance of each scheduler is running

---

## Benefits of Twice-Daily

### 1. Line Movement Tracking ⭐
See how odds shift throughout the day:
- Opening lines (9am)
- Closing lines (3pm, closer to games)
- Identify sharp money movements

### 2. More Player Props
Player props often post mid-day:
- 9am: Might only have 1-5 props
- 3pm: Often have 15-30+ props

### 3. Better Data Coverage
12 data points/week vs 6:
- More snapshots = better trend analysis
- Catch odds when they're most valuable

---

## File Naming Convention

### Morning Files (9am)
- Standard names: `odds_spreads_week_7.csv`

### Afternoon Files (3pm)
- Suffix: `_3pm`: `odds_spreads_week_7_3pm.csv`

This makes it easy to:
- Identify which run created the file
- Compare morning vs afternoon data
- Keep historical snapshots organized

---

## Next Steps

1. ✅ **Set current week** (`python utils/week_manager.py --set-week 8`)
2. ✅ **Start both schedulers** (see Quick Start above)
3. ✅ **Let them run for a week** to collect data
4. 🔄 **Monday mornings**: Advance week (`python utils/week_manager.py --advance`)
5. ✅ **Analyze line movements** (compare 9am vs 3pm)
6. 🔜 **Build edge detection** that uses line movement data
7. 🔜 **Create alerts** for significant line moves

---

## Summary

You now have **professional-grade line movement tracking + week management**:
- Single source of truth for current NFL week
- Automatic data validation and staleness detection
- 2 snapshots per day
- 12 data points per week
- Only 4.3% API usage
- Automatic CSV export
- Separate logs for easy monitoring

**Setup checklist:**

1. Set current week: `python utils/week_manager.py --set-week 8`
2. Start both schedulers:
   ```bash
   # Production command (macOS/Linux)
   nohup python scheduler.py > scheduler_main.log 2>&1 &
   nohup python scheduler_odds.py > scheduler_odds_output.log 2>&1 &
   ```
3. Monday mornings: `python utils/week_manager.py --advance`

**See also:**
- [WEEK_MANAGEMENT.md](WEEK_MANAGEMENT.md) - Complete week tracking guide
- [README.md](README.md) - Main documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design details

---

**Last Updated:** October 21, 2025
**Status:** ✅ Production Ready
