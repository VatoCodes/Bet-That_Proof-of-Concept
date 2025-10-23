#!/bin/bash
#
# Emergency Rollback Script
#
# Quickly rollback v2 deployment to a target percentage (usually 0%)
# Usage:
#   ./scripts/emergency_rollback.sh --target 0
#   ./scripts/emergency_rollback.sh --target 10
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TARGET_PCT=0
SKIP_CONFIRMATION=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET_PCT="$2"
            shift 2
            ;;
        --yes|-y)
            SKIP_CONFIRMATION=true
            shift
            ;;
        --help|-h)
            echo "Emergency Rollback Script"
            echo ""
            echo "Usage:"
            echo "  ./scripts/emergency_rollback.sh --target 0"
            echo "  ./scripts/emergency_rollback.sh --target 10 --yes"
            echo ""
            echo "Options:"
            echo "  --target <pct>   Target rollout percentage (default: 0)"
            echo "  --yes, -y        Skip confirmation prompt"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Emergency rollback to 0% (all users on v1)"
            echo "  ./scripts/emergency_rollback.sh --target 0"
            echo ""
            echo "  # Gradual rollback to 10% (canary)"
            echo "  ./scripts/emergency_rollback.sh --target 10"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate target percentage
if ! [[ "$TARGET_PCT" =~ ^[0-9]+$ ]] || [ "$TARGET_PCT" -lt 0 ] || [ "$TARGET_PCT" -gt 100 ]; then
    echo -e "${RED}❌ Error: Target percentage must be between 0 and 100${NC}"
    exit 1
fi

# Banner
echo ""
echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║           🚨 EMERGENCY ROLLBACK INITIATED 🚨              ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get current configuration
echo -e "${BLUE}📊 Checking current deployment status...${NC}"
echo ""

# Get current rollout percentage (simplified - read from config.py)
CURRENT_PCT=$(python3 -c "from utils.config import get_config; print(get_config('v2_rollout_percentage', 0))" 2>/dev/null || echo "unknown")

echo "Current Rollout: ${CURRENT_PCT}%"
echo "Target Rollout:  ${TARGET_PCT}%"
echo ""

# Confirmation
if [ "$SKIP_CONFIRMATION" = false ]; then
    echo -e "${YELLOW}⚠️  WARNING: This will immediately change the v2 rollout percentage${NC}"
    echo -e "${YELLOW}   from ${CURRENT_PCT}% to ${TARGET_PCT}%.${NC}"
    echo ""

    if [ "$TARGET_PCT" -eq 0 ]; then
        echo -e "${YELLOW}   Target 0% = All users will be on v1 (v2 disabled)${NC}"
    elif [ "$TARGET_PCT" -eq 10 ]; then
        echo -e "${YELLOW}   Target 10% = Canary rollout (minimal user impact)${NC}"
    elif [ "$TARGET_PCT" -eq 50 ]; then
        echo -e "${YELLOW}   Target 50% = Staged rollout (moderate user impact)${NC}"
    fi

    echo ""
    read -p "Continue with rollback? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ] && [ "$CONFIRM" != "y" ]; then
        echo ""
        echo -e "${BLUE}ℹ️  Rollback cancelled by user${NC}"
        echo ""
        exit 0
    fi
fi

# Execute rollback
echo ""
echo -e "${BLUE}⏳ Executing rollback...${NC}"
echo ""

# Step 1: Update feature flag
echo "Step 1/3: Updating v2_rollout_percentage to ${TARGET_PCT}%"
python3 scripts/set_feature_flag.py --flag v2_rollout_percentage --value "$TARGET_PCT" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Feature flag updated${NC}"
else
    echo -e "${RED}  ❌ Failed to update feature flag${NC}"
    exit 1
fi

# Step 2: Verify rollback
echo ""
echo "Step 2/3: Verifying rollback"

NEW_PCT=$(python3 -c "from utils.config import get_config; print(get_config('v2_rollout_percentage', -1))" 2>/dev/null || echo "-1")

if [ "$NEW_PCT" -eq "$TARGET_PCT" ]; then
    echo -e "${GREEN}  ✅ Rollback verified (current: ${NEW_PCT}%)${NC}"
else
    echo -e "${RED}  ❌ Verification failed (expected: ${TARGET_PCT}%, current: ${NEW_PCT}%)${NC}"
    exit 1
fi

# Step 3: Restart application (if needed)
echo ""
echo "Step 3/3: Application restart (optional)"
echo -e "${YELLOW}  ⚠️  Manual restart may be required for changes to take effect${NC}"
echo -e "${YELLOW}     (Depends on application architecture)${NC}"

# Success summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅ ROLLBACK COMPLETED SUCCESSFULLY              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Summary:"
echo "  Previous Rollout: ${CURRENT_PCT}%"
echo "  Current Rollout:  ${NEW_PCT}%"

if [ "$TARGET_PCT" -eq 0 ]; then
    echo "  Status: ⚪ v2 DISABLED (all users on v1)"
elif [ "$TARGET_PCT" -eq 10 ]; then
    echo "  Status: 🟡 CANARY (10% of users on v2)"
elif [ "$TARGET_PCT" -eq 50 ]; then
    echo "  Status: 🟠 STAGED (50% of users on v2)"
elif [ "$TARGET_PCT" -eq 100 ]; then
    echo "  Status: 🟢 FULL ROLLOUT (100% of users on v2)"
else
    echo "  Status: 🔷 CUSTOM (${TARGET_PCT}% of users on v2)"
fi

echo ""
echo "Next Steps:"
echo "  1. Monitor logs: tail -f logs/v2_calculations.jsonl"
echo "  2. Check dashboard: Verify v2_calculations_per_min metric"
echo "  3. Communicate: Post rollback status to #engineering-alerts"
echo ""

if [ "$TARGET_PCT" -eq 0 ]; then
    echo "  4. Investigate: Determine root cause of issue"
    echo "  5. Fix: Apply fixes and re-test in staging"
    echo "  6. Redeploy: Follow phased rollout strategy when ready"
fi

echo ""
echo -e "${BLUE}Timestamp: $(date +'%Y-%m-%d %H:%M:%S %Z')${NC}"
echo ""
