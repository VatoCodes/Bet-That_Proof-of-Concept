# Scheduler Deployment & Auto-Start Solutions

This directory contains three different solutions for automatically starting the Bet-That NFL schedulers on system boot.

## 📋 Quick Overview

| Solution | Platform | Complexity | Features | Recommended For |
|----------|----------|------------|----------|-----------------|
| **Launchd** | macOS | Low | Auto-start, auto-restart, logging | macOS users (RECOMMENDED) |
| **Cron** | macOS/Linux | Low | Auto-start only | Simple setups, Linux |
| **Supervisord** | Cross-platform | Medium | Full process management, web UI | Production environments |

## 🎯 Which Solution to Use?

### Use Launchd if:
- ✅ You're on macOS (you are!)
- ✅ You want native macOS integration
- ✅ You want auto-restart on crash
- ✅ You prefer simple setup

**→ Start here: [launchd/INSTALL.md](launchd/INSTALL.md)**

### Use Cron if:
- ✅ Launchd isn't working
- ✅ You're on Linux
- ✅ You want the simplest possible solution
- ✅ You don't need auto-restart

**→ See: [cron/BACKUP_CRON_SOLUTION.md](cron/BACKUP_CRON_SOLUTION.md)**

### Use Supervisord if:
- ✅ You need production-grade monitoring
- ✅ You want a web dashboard
- ✅ You need email alerts on failures
- ✅ You're managing multiple services

**→ See: [supervisord/BACKUP_SUPERVISORD_SOLUTION.md](supervisord/BACKUP_SUPERVISORD_SOLUTION.md)**

## 📁 Directory Structure

```
deployment/
├── README.md                           # This file
├── launchd/                            # RECOMMENDED for macOS
│   ├── INSTALL.md                      # Installation guide
│   ├── com.betthat.scheduler.plist     # Main scheduler config
│   └── com.betthat.scheduler.odds.plist # Odds scheduler config
├── cron/                               # Backup solution 1
│   └── BACKUP_CRON_SOLUTION.md         # Cron setup guide
└── supervisord/                        # Backup solution 2
    ├── BACKUP_SUPERVISORD_SOLUTION.md  # Supervisord guide
    ├── supervisord.conf                # Config file
    └── install.sh                      # Automated installer
```

## 🚀 Quick Start (Recommended Path)

### Current Status
✅ **Both schedulers are currently running manually** (started at system time 12:59 PM)

### For Automatic Startup on Reboot:

1. **Install Launchd** (5 minutes):
   ```bash
   # Copy plist files
   cp deployment/launchd/*.plist ~/Library/LaunchAgents/

   # Load services
   launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.plist
   launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
   ```

2. **Verify**:
   ```bash
   launchctl list | grep betthat
   ```

3. **Done!** Services will now auto-start on boot and auto-restart if they crash.

Full instructions: [launchd/INSTALL.md](launchd/INSTALL.md)

## 📊 Monitoring

### Check Scheduler Status
```bash
# Run the monitoring script
./scripts/monitor_schedulers.sh
```

This shows:
- ✅ Process status (running/stopped)
- 📝 Recent log activity
- 🗄️ Recent scrape activity from database
- ⏰ Next scheduled run
- 💾 Storage usage

### Manual Process Check
```bash
# Check if schedulers are running
ps -ef | grep scheduler | grep -v grep

# View logs
tail -f scheduler.log
tail -f scheduler_odds.log
```

## 🔄 The Two Schedulers

### Main Scheduler (`scheduler.py`)
- **Schedule**: Monday-Saturday at 9:00 AM
- **Collects**: Defense stats, QB stats, matchups, AND odds
- **Purpose**: Full daily data collection

### Odds Scheduler (`scheduler_odds.py`)
- **Schedule**: Monday-Saturday at 3:00 PM
- **Collects**: QB TD props, spreads, totals (odds ONLY)
- **Purpose**: Track line movement between morning and afternoon

## 📝 Logs

Each solution creates different log files:

### Application Logs (always created)
- `scheduler.log` - Main scheduler application logs
- `scheduler_odds.log` - Odds scheduler application logs

### Launchd Logs
- `logs/scheduler.stdout.log`
- `logs/scheduler.stderr.log`
- `logs/scheduler_odds.stdout.log`
- `logs/scheduler_odds.stderr.log`

### Supervisord Logs
- `logs/scheduler.out.log`
- `logs/scheduler.err.log`
- `logs/scheduler_odds.out.log`
- `logs/scheduler_odds.err.log`

## ⚙️ Configuration

### Schedule Times
Edit [config.py](../config.py):
```python
SCRAPE_TIME = "09:00"       # Main scrape
ODDS_SCRAPE_TIME = "15:00"  # Odds scrape
```

### Days
```python
SCRAPE_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
```

## 🔧 Troubleshooting

### Schedulers not running after reboot
1. Check which solution you installed
2. Verify installation:
   - **Launchd**: `launchctl list | grep betthat`
   - **Cron**: `crontab -l`
   - **Supervisord**: `supervisorctl status`

### Services crashing
1. Check error logs (see Logs section above)
2. Verify Python path: `which python3`
3. Test manual run: `python3 scheduler.py --test`

### Permissions issues on macOS
1. System Preferences → Security & Privacy → Privacy
2. Grant "Full Disk Access" to Terminal
3. Restart Terminal and retry

## 🎓 Learn More

- [Launchd Documentation](https://www.launchd.info/)
- [Supervisord Documentation](http://supervisord.org/)
- [Cron Guide](https://man7.org/linux/man-pages/man5/crontab.5.html)

## 📞 Need Help?

1. Run the monitor: `./scripts/monitor_schedulers.sh`
2. Check the specific solution's documentation
3. Review log files for errors
4. Test manual execution first: `python3 scheduler.py --test`

## 🔮 Future Enhancements

Potential improvements documented in each solution:
- Email alerts on failures (Supervisord)
- Slack/Discord notifications
- Prometheus metrics export
- Health check endpoints
- Automated testing before deployment
