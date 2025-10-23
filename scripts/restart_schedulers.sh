#!/bin/bash
# Safe scheduler restart script
# Ensures clean shutdown and restart with no duplicates

set -e  # Exit on error

PROJECT_DIR="/Users/vato/work/Bet-That_(Proof of Concept)"
cd "$PROJECT_DIR"

echo "================================================"
echo "Scheduler Restart Script"
echo "================================================"
echo ""

# Step 1: Kill existing schedulers
echo "[1/4] Stopping existing schedulers..."

# Find and kill scheduler.py processes
SCHEDULER_PIDS=$(ps aux | grep "[s]cheduler.py" | awk '{print $2}')
if [ ! -z "$SCHEDULER_PIDS" ]; then
    echo "  Killing scheduler.py (PIDs: $SCHEDULER_PIDS)"
    kill $SCHEDULER_PIDS 2>/dev/null || true
else
    echo "  No scheduler.py processes found"
fi

# Find and kill scheduler_odds.py processes
ODDS_PIDS=$(ps aux | grep "[s]cheduler_odds.py" | awk '{print $2}')
if [ ! -z "$ODDS_PIDS" ]; then
    echo "  Killing scheduler_odds.py (PIDs: $ODDS_PIDS)"
    kill $ODDS_PIDS 2>/dev/null || true
else
    echo "  No scheduler_odds.py processes found"
fi

# Wait for processes to terminate
echo "  Waiting for processes to terminate..."
sleep 3

# Force kill if still running
REMAINING=$(ps aux | grep -E "[s]cheduler(_odds)?.py" | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "  Force killing remaining processes..."
    pkill -9 -f "scheduler.*.py" 2>/dev/null || true
    sleep 2
fi

# Clean up lock files
echo "  Cleaning up lock files..."
rm -f /tmp/bet_that_scheduler_*.lock

echo "  ✓ All schedulers stopped"
echo ""

# Step 2: Rotate logs
echo "[2/4] Rotating logs..."

if [ -f "scheduler.log" ]; then
    mv scheduler.log "scheduler_$(date +%Y%m%d_%H%M%S).log.backup"
    echo "  ✓ Backed up scheduler.log"
fi

if [ -f "scheduler_odds.log" ]; then
    mv scheduler_odds.log "scheduler_odds_$(date +%Y%m%d_%H%M%S).log.backup"
    echo "  ✓ Backed up scheduler_odds.log"
fi

echo ""

# Step 3: Start schedulers
echo "[3/4] Starting schedulers..."

# Start main scheduler (9am full scrape)
nohup python3 scheduler.py > scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo "  ✓ Started scheduler.py (PID: $SCHEDULER_PID)"

# Wait a moment before starting second scheduler
sleep 2

# Start odds scheduler (3pm odds-only)
nohup python3 scheduler_odds.py > scheduler_odds.log 2>&1 &
ODDS_PID=$!
echo "  ✓ Started scheduler_odds.py (PID: $ODDS_PID)"

echo ""

# Step 4: Verify
echo "[4/4] Verifying schedulers..."
sleep 2

RUNNING=$(ps aux | grep -E "[s]cheduler(_odds)?.py" | wc -l)

if [ $RUNNING -eq 2 ]; then
    echo "  ✓ Exactly 2 scheduler processes running"
    echo ""
    echo "Active schedulers:"
    ps aux | grep -E "[s]cheduler(_odds)?.py" | grep -v grep
    echo ""
    echo "================================================"
    echo "✓ Schedulers restarted successfully"
    echo "================================================"
    exit 0
else
    echo "  ✗ Expected 2 schedulers, found $RUNNING"
    echo ""
    ps aux | grep -E "[s]cheduler(_odds)?.py" | grep -v grep || true
    echo ""
    echo "================================================"
    echo "✗ Scheduler restart failed"
    echo "================================================"
    exit 1
fi
