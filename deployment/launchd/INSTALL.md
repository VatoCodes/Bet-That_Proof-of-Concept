# Launchd Auto-Start Installation Guide

This is the **recommended** method for auto-starting schedulers on macOS.

## Features
- ✅ Auto-starts on system boot
- ✅ Auto-restarts on crash
- ✅ Separate logging for stdout/stderr
- ✅ Native macOS integration
- ✅ Proper process management

## Installation

### 1. Copy plist files to LaunchAgents directory

```bash
# Copy both scheduler plist files
cp deployment/launchd/com.betthat.scheduler.plist ~/Library/LaunchAgents/
cp deployment/launchd/com.betthat.scheduler.odds.plist ~/Library/LaunchAgents/
```

### 2. Load the services

```bash
# Load main scheduler (9am - full scrape)
launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.plist

# Load odds scheduler (3pm - odds only)
launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
```

### 3. Verify services are running

```bash
# Check if services are loaded
launchctl list | grep betthat

# Expected output:
# -       0       com.betthat.scheduler.odds
# -       0       com.betthat.scheduler
```

### 4. Start services immediately (without waiting for reboot)

```bash
# Start main scheduler
launchctl start com.betthat.scheduler

# Start odds scheduler
launchctl start com.betthat.scheduler.odds
```

## Management Commands

### Check service status
```bash
launchctl list | grep betthat
```

### Stop services
```bash
launchctl stop com.betthat.scheduler
launchctl stop com.betthat.scheduler.odds
```

### Unload services (disable auto-start)
```bash
launchctl unload ~/Library/LaunchAgents/com.betthat.scheduler.plist
launchctl unload ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
```

### Reload services (after plist changes)
```bash
launchctl unload ~/Library/LaunchAgents/com.betthat.scheduler.plist
launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.plist

launchctl unload ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
launchctl load ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
```

## Logs

Launchd creates separate log files:

- **Main scheduler stdout**: `logs/scheduler.stdout.log`
- **Main scheduler stderr**: `logs/scheduler.stderr.log`
- **Odds scheduler stdout**: `logs/scheduler_odds.stdout.log`
- **Odds scheduler stderr**: `logs/scheduler_odds.stderr.log`

Additionally, each scheduler has its own application log:
- `scheduler.log` - Main scheduler application logs
- `scheduler_odds.log` - Odds scheduler application logs

### View real-time logs
```bash
# Main scheduler
tail -f logs/scheduler.stdout.log
tail -f scheduler.log

# Odds scheduler
tail -f logs/scheduler_odds.stdout.log
tail -f scheduler_odds.log
```

## Troubleshooting

### Services not starting
1. Check log files for errors
2. Verify paths in plist files are correct
3. Ensure Python is at `/usr/bin/python3`
4. Check permissions: `ls -l ~/Library/LaunchAgents/com.betthat.*`

### Services crashing
- Check stderr logs: `cat logs/scheduler.stderr.log`
- Services will auto-restart after 60 seconds (ThrottleInterval)

### Remove completely
```bash
# Unload services
launchctl unload ~/Library/LaunchAgents/com.betthat.scheduler.plist
launchctl unload ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist

# Remove plist files
rm ~/Library/LaunchAgents/com.betthat.scheduler.plist
rm ~/Library/LaunchAgents/com.betthat.scheduler.odds.plist
```

## What Happens on System Boot

1. macOS reads plist files from `~/Library/LaunchAgents/`
2. Services with `RunAtLoad` set to `true` start automatically
3. Services run in background with logging to specified paths
4. If a service crashes, it waits 60 seconds then restarts (KeepAlive)

## Schedule Details

- **Main Scheduler**: Runs Mon-Sat at 9:00 AM
  - Collects: Defense stats, QB stats, matchups, odds

- **Odds Scheduler**: Runs Mon-Sat at 3:00 PM
  - Collects: QB TD props, spreads, totals (odds only)
  - Tracks line movement between morning and afternoon
