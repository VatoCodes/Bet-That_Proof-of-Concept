# Scheduler Status & Setup Summary

**Date**: October 22, 2025
**Status**: ✅ BOTH SCHEDULERS RUNNING

---

## 📊 Current Status

### Running Processes
- ✅ **Main Scheduler** (PID: 32500) - Started at 12:59 PM
- ✅ **Odds Scheduler** (PID: 32553) - Started at 12:59 PM

### Next Scheduled Run
- **Today at 3:00 PM** - Odds scrape (QB TD props, spreads, totals)
- **Tomorrow at 9:00 AM** - Full scrape (all data + odds)

### Recent Activity
- Last scrapes: October 21, 2025 at 11:43 PM (Week 7)
- Database size: 15 MB
- All recent scrapes: ✅ Success

---

## 🔄 Scheduled Scraping (Twice Daily)

### Morning Run - 9:00 AM
**Scheduler**: `scheduler.py`
**Frequency**: Monday through Saturday
**Collects**:
- Defense stats
- QB stats
- Matchups
- Odds (QB TD props, spreads, totals)

### Afternoon Run - 3:00 PM
**Scheduler**: `scheduler_odds.py`
**Frequency**: Monday through Saturday
**Collects**:
- QB TD props
- Spreads
- Totals (odds ONLY)

**Purpose**: Track line movement between morning and afternoon for betting edge analysis

---

## 🚀 Auto-Start on System Boot

### ✅ Framework Installed (Ready to Enable)

Three solutions are ready to deploy:

#### Option 1: Launchd (RECOMMENDED for macOS)
**Location**: `deployment/launchd/`
**Status**: Ready to install
**Install**: See [deployment/launchd/INSTALL.md](deployment/launchd/INSTALL.md)

```bash
# Quick install:
cp deployment/launchd/*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.plist
launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
```

**Features**:
- ✅ Auto-start on boot
- ✅ Auto-restart on crash
- ✅ Native macOS integration
- ✅ Excellent logging

#### Option 2: Cron (Backup)
**Location**: `deployment/cron/`
**Status**: Documented
**Install**: See [deployment/cron/BACKUP_CRON_SOLUTION.md](deployment/cron/BACKUP_CRON_SOLUTION.md)

**Use when**: Launchd isn't working or you prefer simplicity

#### Option 3: Supervisord (Production)
**Location**: `deployment/supervisord/`
**Status**: Ready to install
**Install**: Run `./deployment/supervisord/install.sh`

**Features**:
- ✅ Web dashboard (http://localhost:9001)
- ✅ Advanced process monitoring
- ✅ Email alerts on failure
- ✅ Cross-platform

---

## 📝 Monitoring

### Quick Status Check
```bash
./scripts/monitor_schedulers.sh
```

Shows:
- Process status
- Recent logs
- Database activity
- Next scheduled run
- Storage usage

### Manual Checks
```bash
# Check running processes
ps -ef | grep scheduler | grep -v grep

# View logs in real-time
tail -f scheduler.log
tail -f scheduler_odds.log

# Check recent scrapes
sqlite3 data/database/nfl_betting.db "SELECT * FROM scrape_runs ORDER BY run_timestamp DESC LIMIT 5"
```

---

## 📂 Important Files

### Schedulers
- `scheduler.py` - Main scheduler (9am)
- `scheduler_odds.py` - Odds scheduler (3pm)
- `main.py` - Actual scraper script (called by schedulers)

### Configuration
- `config.py` - All settings (times, days, API keys, etc.)
- `.env` - API keys and secrets

### Logs
- `scheduler.log` - Main scheduler logs
- `scheduler_odds.log` - Odds scheduler logs
- `logs/` - Additional logs from launchd/supervisord

### Database
- `data/database/nfl_betting.db` - Main database
- Tables: `qb_props`, `odds_spreads`, `odds_totals`, `scrape_runs`, etc.

---

## 🛠️ Common Commands

### Start Schedulers Manually
```bash
# Background (current setup)
nohup python scheduler.py >> scheduler.log 2>&1 &
nohup python scheduler_odds.py >> scheduler_odds.log 2>&1 &

# Foreground (for debugging)
python scheduler.py
python scheduler_odds.py
```

### Stop Schedulers
```bash
# Find and kill processes
pkill -f scheduler.py
pkill -f scheduler_odds.py

# Or by PID
kill 32500  # Main scheduler
kill 32553  # Odds scheduler
```

### Test Scraping
```bash
# Test full scrape
python main.py

# Test odds-only scrape
python main.py --odds-only

# Test scheduler (dry run)
python scheduler.py --test
python scheduler_odds.py --test
```

---

## ⚠️ Important Notes

### API Usage
- Uses The Odds API (free + paid tiers)
- Free tier: 500 requests/month per key (6 keys configured)
- Paid tier: 20,000 requests/month (fallback)
- Current usage tracked in database

### Week Management
- Current week auto-detected by `utils/week_manager.py`
- Weeks 1-18 regular season
- Manual override available if needed

### Data Retention
- Historical data kept for 30 days (configurable)
- Auto-archive completed weeks
- Database backups created before major changes

---

## 🔮 Future Enhancements

Potential improvements:
- [ ] Email/SMS alerts on scrape failures
- [ ] Slack/Discord notifications for STRONG edges
- [ ] API usage monitoring dashboard
- [ ] Automated database backups
- [ ] Health check endpoints
- [ ] Metrics export for monitoring tools

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| **Check status** | `./scripts/monitor_schedulers.sh` |
| **View logs** | `tail -f scheduler.log` |
| **Stop all** | `pkill -f scheduler.py` |
| **Start manually** | `nohup python scheduler.py >> scheduler.log 2>&1 &` |
| **Test scrape** | `python main.py --odds-only` |
| **Check database** | `sqlite3 data/database/nfl_betting.db` |
| **Enable auto-start** | See [deployment/README.md](deployment/README.md) |

---

**Last Updated**: October 22, 2025 at 1:03 PM MDT
**Next Action**: Install launchd for auto-start on boot (optional but recommended)
