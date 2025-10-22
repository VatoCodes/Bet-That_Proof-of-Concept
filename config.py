"""
Configuration file for NFL data scraping automation
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"
DATABASE_DIR = BASE_DIR / "data" / "database"
HISTORICAL_DIR = BASE_DIR / "data" / "historical"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

# Pro Football Reference URLs
PFR_BASE_URL = "https://www.pro-football-reference.com"
PFR_DEFENSE_URL_TEMPLATE = "https://www.pro-football-reference.com/years/{year}/opp.htm"
PFR_QB_URL_TEMPLATE = "https://www.pro-football-reference.com/years/{year}/passing.htm"

# ESPN URLs
ESPN_SCHEDULE_URL = "https://www.espn.com/nfl/schedule"

# The Odds API Configuration
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# Free tier API keys (500 requests/month each) - These will be used first
ODDS_API_KEYS_FREE = [
    os.getenv("ODDS_API_KEY_1"),
    os.getenv("ODDS_API_KEY_2"),
    os.getenv("ODDS_API_KEY_3"),
    os.getenv("ODDS_API_KEY_4"),
    os.getenv("ODDS_API_KEY_5"),
    os.getenv("ODDS_API_KEY_6"),
]

# Paid tier API key (fallback when free tier exhausted)
ODDS_API_KEY_PAID = os.getenv("ODDS_API_KEY_PAID")

# Filter out None values from free tier keys
ODDS_API_KEYS_FREE = [key for key in ODDS_API_KEYS_FREE if key]

# Build final key list: Free tier first, then paid tier as fallback
ODDS_API_KEYS = ODDS_API_KEYS_FREE.copy()
if ODDS_API_KEY_PAID:
    ODDS_API_KEYS.append(ODDS_API_KEY_PAID)

# Odds API settings
ODDS_SPORT = "americanfootball_nfl"
ODDS_REGIONS = "us"
# Player props (QB TD) require paid tier and will always use paid API key
ODDS_MARKETS = "player_pass_tds"  # QB passing TD props (requires paid tier)
ODDS_MARKETS_FALLBACK = "h2h"  # Fallback to game lines if paid key not available
ODDS_BOOKMAKERS = "draftkings,fanduel"  # Primary sportsbooks

# API Request Limits
FREE_TIER_MAX_REQUESTS = 500    # 500 requests per month per free key
PAID_TIER_MAX_REQUESTS = 20000  # 20K requests per month for paid tier

# Current NFL season
CURRENT_YEAR = 2025

# Week management - Import WeekManager for centralized week tracking
# Note: Import happens at runtime to avoid circular dependencies
def get_current_week() -> int:
    """
    Get the current NFL week from WeekManager

    Returns:
        Current NFL week number
    """
    from utils.week_manager import WeekManager
    wm = WeekManager()
    return wm.get_current_week()

# Database Configuration
DATABASE_PATH = DATABASE_DIR / "nfl_betting.db"

# Historical Storage Configuration
HISTORICAL_RETENTION_DAYS = 30  # Keep snapshots for 30 days
HISTORICAL_AUTO_ARCHIVE = True  # Auto-archive completed weeks

# User Agent for web scraping
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Request settings
REQUEST_TIMEOUT = 30  # seconds
REQUEST_DELAY = 2  # seconds between requests to be polite

# Schedule settings - Daily scraping Monday through Saturday
SCRAPE_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
SCRAPE_TIME = "09:00"  # 9am - Full scrape (stats + matchups + odds)
ODDS_SCRAPE_TIME = "15:00"  # 3pm - Odds-only scrape (line movement tracking)

# File naming templates
DEFENSE_FILE_TEMPLATE = "defense_stats_week_{week}.csv"
QB_FILE_TEMPLATE = "qb_stats_{year}.csv"
MATCHUPS_FILE_TEMPLATE = "matchups_week_{week}.csv"
ODDS_FILE_TEMPLATE = "odds_qb_td_week_{week}.csv"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# Database Helper Functions
def get_database_path() -> Path:
    """
    Get the database file path
    
    Returns:
        Path to SQLite database file
    """
    return DATABASE_PATH


def get_historical_dir() -> Path:
    """
    Get the historical storage directory path
    
    Returns:
        Path to historical storage directory
    """
    return HISTORICAL_DIR


def get_database_dir() -> Path:
    """
    Get the database directory path
    
    Returns:
        Path to database directory
    """
    return DATABASE_DIR
