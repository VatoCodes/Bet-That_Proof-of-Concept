#!/bin/bash
# Supervisord Installation Script for Bet-That Schedulers

set -e  # Exit on error

echo "=========================================="
echo "Bet-That Supervisord Installation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if supervisord is installed
if ! command -v supervisord &> /dev/null; then
    echo -e "${YELLOW}Supervisord not found. Installing...${NC}"

    # Check if Homebrew is available (macOS)
    if command -v brew &> /dev/null; then
        echo "Installing via Homebrew..."
        brew install supervisor
    # Check if pip is available
    elif command -v pip &> /dev/null; then
        echo "Installing via pip..."
        pip install supervisor
    else
        echo -e "${RED}Error: Neither Homebrew nor pip found. Please install supervisord manually.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Supervisord already installed${NC}"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p /usr/local/var/log
mkdir -p /usr/local/etc
mkdir -p logs

echo -e "${GREEN}✓ Directories created${NC}"

# Copy configuration file
echo ""
echo "Installing configuration..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp "$SCRIPT_DIR/supervisord.conf" /usr/local/etc/supervisord.conf

echo -e "${GREEN}✓ Configuration installed to /usr/local/etc/supervisord.conf${NC}"

# Check if supervisord is already running
if pgrep -x supervisord > /dev/null; then
    echo ""
    echo -e "${YELLOW}Supervisord is already running. Reloading configuration...${NC}"
    supervisorctl reread
    supervisorctl update
else
    # Start supervisord
    echo ""
    echo "Starting supervisord..."
    supervisord -c /usr/local/etc/supervisord.conf
    sleep 2
fi

# Check status
echo ""
echo "Checking service status..."
supervisorctl status

echo ""
echo -e "${GREEN}=========================================="
echo "Installation Complete!"
echo "==========================================${NC}"
echo ""
echo "Services are now running and will auto-start on system boot."
echo ""
echo "Management Commands:"
echo "  supervisorctl status              - Check status"
echo "  supervisorctl start all           - Start all services"
echo "  supervisorctl stop all            - Stop all services"
echo "  supervisorctl restart all         - Restart all services"
echo "  supervisorctl tail -f <service>   - Follow logs"
echo ""
echo "Web Dashboard:"
echo "  URL: http://localhost:9001"
echo "  Username: admin"
echo "  Password: betthat_admin_2025"
echo ""
