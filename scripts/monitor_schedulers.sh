#!/bin/bash
# Scheduler Monitoring Script
# Checks health of both schedulers and provides status information

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "Bet-That Scheduler Monitor"
echo "==========================================${NC}"
echo ""

# Check if schedulers are running
echo -e "${BLUE}Process Status:${NC}"

SCHEDULER_PID=$(pgrep -f "scheduler.py" | head -1 || echo "")
ODDS_SCHEDULER_PID=$(pgrep -f "scheduler_odds.py" | head -1 || echo "")

if [ -n "$SCHEDULER_PID" ]; then
    echo -e "  ${GREEN}✓${NC} Main Scheduler (PID: $SCHEDULER_PID) - RUNNING"
else
    echo -e "  ${RED}✗${NC} Main Scheduler - NOT RUNNING"
fi

if [ -n "$ODDS_SCHEDULER_PID" ]; then
    echo -e "  ${GREEN}✓${NC} Odds Scheduler (PID: $ODDS_SCHEDULER_PID) - RUNNING"
else
    echo -e "  ${RED}✗${NC} Odds Scheduler - NOT RUNNING"
fi

echo ""

# Check log files
echo -e "${BLUE}Recent Log Activity:${NC}"

if [ -f "scheduler.log" ]; then
    LAST_LOG=$(tail -1 scheduler.log 2>/dev/null || echo "No logs")
    echo -e "  Main Scheduler: ${LAST_LOG:0:100}"
else
    echo -e "  ${YELLOW}⚠${NC} Main Scheduler log not found"
fi

if [ -f "scheduler_odds.log" ]; then
    LAST_LOG=$(tail -1 scheduler_odds.log 2>/dev/null || echo "No logs")
    echo -e "  Odds Scheduler: ${LAST_LOG:0:100}"
else
    echo -e "  ${YELLOW}⚠${NC} Odds Scheduler log not found"
fi

echo ""

# Check database for recent scrapes
echo -e "${BLUE}Recent Scrape Activity:${NC}"

DB_PATH="data/database/nfl_betting.db"

if [ -f "$DB_PATH" ]; then
    RECENT_SCRAPES=$(sqlite3 "$DB_PATH" "SELECT run_timestamp, week, status FROM scrape_runs ORDER BY run_timestamp DESC LIMIT 3" 2>/dev/null || echo "")

    if [ -n "$RECENT_SCRAPES" ]; then
        echo "$RECENT_SCRAPES" | while IFS='|' read -r timestamp week status; do
            if [ "$status" = "success" ]; then
                echo -e "  ${GREEN}✓${NC} Week $week - $timestamp"
            else
                echo -e "  ${RED}✗${NC} Week $week - $timestamp - $status"
            fi
        done
    else
        echo -e "  ${YELLOW}⚠${NC} No recent scrape data found"
    fi
else
    echo -e "  ${RED}✗${NC} Database not found at $DB_PATH"
fi

echo ""

# Check next scheduled run
echo -e "${BLUE}Schedule Information:${NC}"
echo "  Main Scheduler: Mon-Sat at 9:00 AM (Full scrape)"
echo "  Odds Scheduler: Mon-Sat at 3:00 PM (Odds only)"

# Current time
CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
CURRENT_HOUR=$(date "+%H")
CURRENT_DAY=$(date "+%u")  # 1=Monday, 7=Sunday

echo ""
echo -e "${BLUE}Current Status:${NC}"
echo "  Time: $CURRENT_TIME"

if [ "$CURRENT_DAY" -eq 7 ]; then
    echo "  Day: Sunday (No scrapes scheduled)"
elif [ "$CURRENT_HOUR" -lt 9 ]; then
    echo "  Next run: Today at 9:00 AM (Main scrape)"
elif [ "$CURRENT_HOUR" -lt 15 ]; then
    echo "  Next run: Today at 3:00 PM (Odds scrape)"
else
    echo "  Next run: Tomorrow at 9:00 AM (Main scrape)"
fi

echo ""

# Disk space check
echo -e "${BLUE}Storage:${NC}"
DB_SIZE=$(du -h "$DB_PATH" 2>/dev/null | cut -f1 || echo "N/A")
LOG_SIZE=$(du -sh logs/ 2>/dev/null | cut -f1 || echo "N/A")

echo "  Database size: $DB_SIZE"
echo "  Logs size: $LOG_SIZE"

echo ""

# Quick actions
echo -e "${BLUE}Quick Actions:${NC}"
echo "  View logs:      tail -f scheduler.log"
echo "  View odds logs: tail -f scheduler_odds.log"
echo "  Stop services:  pkill -f scheduler.py && pkill -f scheduler_odds.py"
echo "  Start main:     python scheduler.py &"
echo "  Start odds:     python scheduler_odds.py &"

echo ""
