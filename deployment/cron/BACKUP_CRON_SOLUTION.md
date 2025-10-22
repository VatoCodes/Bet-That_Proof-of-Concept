# Backup Solution 1: Cron (Simple)

This is a **backup solution** if launchd doesn't work or you prefer traditional cron.

## ⚠️ Limitations on macOS
- Cron may have permission issues on modern macOS
- Launchd is the recommended macOS approach
- Consider this for Linux systems or fallback only

## Setup

### Option A: Auto-start on System Boot

Add to crontab:

```bash
crontab -e
```

Add these lines:

```cron
# Auto-start schedulers on system reboot
@reboot cd /Users/vato/work/Bet-That_(Proof\ of\ Concept) && /usr/bin/python3 scheduler.py >> /Users/vato/work/Bet-That_(Proof\ of\ Concept)/scheduler.log 2>&1 &

@reboot cd /Users/vato/work/Bet-That_(Proof\ of\ Concept) && /usr/bin/python3 scheduler_odds.py >> /Users/vato/work/Bet-That_(Proof\ of\ Concept)/scheduler_odds.log 2>&1 &
```

### Option B: Direct Scheduled Execution (Alternative Approach)

Instead of running persistent schedulers, have cron directly execute scrapes:

```cron
# Main scrape: Monday-Saturday at 9:00 AM
0 9 * * 1-6 cd /Users/vato/work/Bet-That_(Proof\ of\ Concept) && /usr/bin/python3 main.py >> logs/cron_scrape.log 2>&1

# Odds-only scrape: Monday-Saturday at 3:00 PM
0 15 * * 1-6 cd /Users/vato/work/Bet-That_(Proof\ of\ Concept) && /usr/bin/python3 main.py --odds-only >> logs/cron_odds.log 2>&1
```

## Pros & Cons

### Option A (@reboot with schedulers)
**Pros:**
- Uses existing scheduler scripts
- Schedulers handle their own timing
- Consistent with manual approach

**Cons:**
- Requires schedulers to stay running
- No auto-restart on crash
- Multiple Python processes

### Option B (Direct cron execution)
**Pros:**
- Simpler - no persistent processes
- Cron handles scheduling directly
- Each run is independent

**Cons:**
- Bypasses scheduler.py logic
- Less visibility into scheduler state
- Cron has limited logging

## Commands

### Edit crontab
```bash
crontab -e
```

### List current crontab
```bash
crontab -l
```

### Remove all cron jobs
```bash
crontab -r
```

### View cron logs (macOS)
```bash
log show --predicate 'process == "cron"' --last 1h
```

## macOS Permissions

On modern macOS, you may need to grant Terminal "Full Disk Access":

1. System Preferences → Security & Privacy → Privacy
2. Select "Full Disk Access"
3. Add Terminal (or iTerm)
4. Restart Terminal

## Why Launchd is Better for macOS

- ✅ Native macOS service
- ✅ Better logging
- ✅ Auto-restart on crash
- ✅ No permission issues
- ✅ Process management
- ✅ Environment variables

Use this cron solution only if:
- You're on Linux (not macOS)
- Launchd isn't working
- You prefer cron's simplicity
