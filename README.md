# NFL Data Scraping Pipeline - Betting POC

Automated data collection system for NFL betting analysis. Scrapes defense stats, QB stats, matchups, and odds data on a weekly schedule.

## Features

- **Automated Twice-Daily Scraping**:
  - 9:00 AM: All data (stats, matchups, odds)
  - 3:00 PM: Odds only (line movement tracking)
- **Week Management System**:
  - Single source of truth for current NFL week
  - Automatic data validation and staleness detection
  - Manual override and week advancement
  - Prevents data synchronization issues
- **Database Storage (Phase 1)**:
  - SQLite database for persistent data storage
  - Historical snapshots with timestamped backups
  - Query tools for edge detection analysis
  - Backward compatibility with CSV output
- **Edge Calculator (Phase 2)**:
  - Real probability models (simple v1, advanced v2)
  - Kelly Criterion bet sizing with 5% bankroll cap
  - Edge detection and opportunity classification
  - Model calibration and performance tracking
- **Schema Fixes (Phase 2.5)**:
  - Fixed QB stats unique constraint to include team column
  - Resolved database insertion conflicts for QB trades
  - Validated schema integrity and data migration
- **Web Dashboard (Phase 3)**:
  - Flask-based web interface with modern UI
  - Real-time edge detection and analysis
  - Interactive charts and visualizations
  - Bet tracking and performance metrics
  - CSV export functionality
  - Responsive design with Tailwind CSS
- **Multi-Source Data Collection**:
  - Pro Football Reference (defense & QB stats)
  - ESPN (weekly matchups)
  - The Odds API (QB TD props, spreads, totals)
- **Smart API Key Management**: Uses 6 free keys (3,000 requests) + 1 paid key (20,000 requests)
- **Multi-Market Odds**: Fetches QB TD props, point spreads, and totals in one run
- **CSV Export**: All data saved to `/data/raw/` in CSV format
- **Comprehensive Logging**: Full audit trail for debugging and monitoring

## Quick Start

### 1. Installation

```bash
# Clone or navigate to project directory
cd "Bet-That_(Proof of Concept)"

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database (Phase 1)

```bash
# Initialize SQLite database with schema
python utils/db_manager.py --init

# Check database status
python utils/db_manager.py --stats
```

### 3. Test Edge Detection (Phase 2)

```bash
# Find betting edges for current week
python find_edges.py --week 7

# Use advanced model with custom bankroll
python find_edges.py --week 7 --model v2 --bankroll 1000 --threshold 10

# Export results for analysis
python find_edges.py --week 7 --export edges_week7.csv

# Test with real data (replaces 90% placeholder)
python test_edge_detection.py
```

### 4. Set Current NFL Week

```bash
# Check current week
python utils/week_manager.py

# Set to current week (e.g., Week 8)
python utils/week_manager.py --set-week 8 --status in_progress

# Validate data files for current week
python utils/week_manager.py --validate
```

See [WEEK_MANAGEMENT.md](WEEK_MANAGEMENT.md) for full week management guide.

### 5. Configure API Keys

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Get your API keys from [The Odds API](https://the-odds-api.com/):
- Sign up for 6 free accounts (use different emails) → 500 requests/month each
- Sign up for 1 paid account → 20,000 requests/month
- Copy all 7 API keys into `.env` file (ODDS_API_KEY_1 through ODDS_API_KEY_6, plus ODDS_API_KEY_PAID)

### 6. Run Manual Test

```bash
# Test all scrapers for Week 7 (all data sources)
python main.py --week 7

# Test with database and snapshots (Phase 1)
python main.py --week 7 --save-to-db --save-snapshots

# Test only stats (defense + QB stats only)
python main.py --week 7 --stats-only

# Test only odds (matchups + all odds markets)
python main.py --week 7 --odds-only

# Test database queries
python utils/query_tools.py --week 7 --weak-defenses
python utils/query_tools.py --week 7 --edges

# Test edge detection (Phase 2)
python find_edges.py --week 7
python find_edges.py --week 7 --model v2 --bankroll 1000
```

### 7. Start Web Dashboard (Phase 3)

```bash
# Start the Flask dashboard
python3 dashboard/app.py

# Access dashboard in browser
open http://localhost:5001

# Note: Port 5001 used due to macOS AirPlay Receiver using port 5000
```

**Dashboard Features:**
- **Main Dashboard** (`/`): Overview stats and edge opportunities
- **Edges Page** (`/edges`): Filterable edge detection with export
- **Stats Page** (`/stats`): Database statistics and system health
- **Tracker Page** (`/tracker`): Bet tracking and performance metrics

**API Endpoints:**
- `GET /api/current-week` - Get current NFL week
- `GET /api/edges` - Find edge opportunities with filters
- `GET /api/weak-defenses` - Get weak defenses analysis
- `GET /api/stats/summary` - Database statistics

### 8. Start Automated Schedulers

```bash
# Start main scheduler (9am - all data)
python scheduler.py

# Start odds scheduler (3pm - odds only)
python scheduler_odds.py

# Or test schedulers immediately
python scheduler.py --test        # Test full data collection
python scheduler_odds.py --test   # Test odds-only collection
```

## Edge Detection (Phase 2)

The Edge Calculator finds betting opportunities by comparing calculated probabilities to sportsbook odds:

### Quick Edge Detection

```bash
# Find edges for current week
python find_edges.py --week 8

# Advanced analysis with custom settings
python find_edges.py --week 8 --model v2 --threshold 10 --bankroll 1000

# Export results for tracking
python find_edges.py --week 8 --export edges_week8.csv
```

### Model Versions

- **v1 (Simple)**: Fast, weighted QB + defense model
- **v2 (Advanced)**: League context, confidence intervals, variance analysis

### Bet Sizing

The system uses Kelly Criterion with conservative fractional approach:
- Maximum 25% Kelly fraction
- Capped at 5% of bankroll per bet
- Tier-based recommendations (PASS/SMALL/GOOD/STRONG)

### Model Calibration

Track prediction accuracy and improve models:

```bash
# Analyze recent performance
python utils/model_calibration.py --analyze --weeks-back 4

# Record game outcomes
python utils/model_calibration.py --record-outcome PREDICTION_ID --outcome win
```

See [EDGE_CALCULATOR.md](EDGE_CALCULATOR.md) for complete guide.

## Usage

### Week Management

The system uses a centralized week tracking system to ensure all data is synchronized:

```bash
# Check current week
python utils/week_manager.py

# Set week manually
python utils/week_manager.py --set-week 8 --status in_progress

# Advance to next week (Monday mornings)
python utils/week_manager.py --advance

# Validate data files exist for current week
python utils/week_manager.py --validate
```

**Status values:**
- `upcoming` - Week hasn't started
- `in_progress` - Games being played this week
- `completed` - Week finished

See [WEEK_MANAGEMENT.md](WEEK_MANAGEMENT.md) for complete documentation.

### Manual Data Collection

Run specific scrapers manually (automatically uses current week from WeekManager):

```bash
# Full pipeline (uses current week from WeekManager)
python main.py

# Override week manually (bypasses WeekManager)
python main.py --week 8 --year 2025

# Tuesday workflow (stats only)
python main.py --stats-only

# Thursday workflow (odds only)
python main.py --odds-only

# Skip odds scraping
python main.py --skip-odds
```

### Individual Scraper Testing

Test each scraper independently:

```bash
# Defense stats
python scrapers/defense_stats_scraper.py 7

# QB stats
python scrapers/qb_stats_scraper.py 2025

# Matchups
python scrapers/matchups_scraper.py 7

# Odds (requires API keys)
python scrapers/odds_scraper.py 7
```

### Automated Scheduling

The system uses **TWO schedulers** for comprehensive data collection:

#### Main Scheduler (9:00 AM)
- **Runs:** Monday-Saturday at 9:00 AM
- **Collects:** All data (defense stats, QB stats, matchups, odds)

#### Odds Scheduler (3:00 PM)
- **Runs:** Monday-Saturday at 3:00 PM
- **Collects:** Odds only (spreads, totals, QB TD props)
- **Purpose:** Track line movements throughout the day

```bash
# Start both schedulers (run in separate terminals)
python scheduler.py          # Terminal 1: 9am full scrape
python scheduler_odds.py     # Terminal 2: 3pm odds-only

# Test schedulers immediately
python scheduler.py --test         # Test full workflow
python scheduler_odds.py --test    # Test odds-only workflow
```

**To run both in background (macOS/Linux):**

```bash
# Using nohup (both schedulers)
nohup python scheduler.py > scheduler_main.log 2>&1 &
nohup python scheduler_odds.py > scheduler_odds_output.log 2>&1 &

# Or using screen (both schedulers)
screen -S nfl_main
python scheduler.py
# Press Ctrl+A then D to detach

screen -S nfl_odds
python scheduler_odds.py
# Press Ctrl+A then D to detach

# View running screens
screen -ls
```

```

## Database Queries (Phase 1)

The system now includes a SQLite database for persistent storage and advanced querying capabilities.

### Database Operations

```bash
# Initialize database
python utils/db_manager.py --init

# Check database statistics
python utils/db_manager.py --stats

# Import existing CSV data
python utils/db_manager.py --import-csv data/raw/defense_stats_week_7.csv --table defense_stats --week 7
```

### Query Tools

```bash
# Find weak defenses (allowing high TDs per game)
python utils/query_tools.py --week 7 --weak-defenses --threshold 1.7

# Show QB TD props
python utils/query_tools.py --week 7 --qb-props

# Calculate edge opportunities
python utils/query_tools.py --week 7 --edges

# Export week data to CSV
python utils/query_tools.py --week 7 --export data/exports/
```

### Historical Snapshots

```bash
# Save snapshots of all current data
python utils/historical_storage.py --snapshot-all --week 7

# Create ZIP archive for week
python utils/historical_storage.py --archive 7

# Check storage statistics
python utils/historical_storage.py --stats

# Clean up old files (30+ days)
python utils/historical_storage.py --cleanup 30
```

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for complete database documentation.

## Data Output

All data is saved to `/data/raw/` in CSV format:

```
data/raw/
├── defense_stats_week_7.csv      # Defense pass TDs allowed
├── qb_stats_2025.csv              # QB season statistics
├── matchups_week_7.csv            # Weekly matchups
├── odds_qb_td_week_7.csv          # QB TD prop odds (over 0.5)
├── odds_spreads_week_7.csv        # Point spreads
└── odds_totals_week_7.csv         # Over/under totals
```

### CSV Formats

**defense_stats_week_X.csv**
```csv
team_name,pass_tds_allowed,games_played,tds_per_game
Giants,21,10,2.1
Panthers,19,10,1.9
```

**qb_stats_2025.csv**
```csv
qb_name,team,total_tds,games_played,is_starter
Patrick Mahomes,Chiefs,18,10,TRUE
Joe Burrow,Bengals,16,10,TRUE
```

**matchups_week_X.csv**
```csv
week,home_team,away_team,game_date
7,Giants,Chiefs,2025-10-27
7,Panthers,Bengals,2025-10-27
```

**odds_qb_td_week_X.csv**
```csv
qb_name,odds_over_05_td,sportsbook,game,home_team,away_team,game_time
Patrick Mahomes,-420,DraftKings,Chiefs vs Giants,Chiefs,Giants,2025-10-27T13:00:00Z
Joe Burrow,-380,DraftKings,Bengals vs Panthers,Bengals,Panthers,2025-10-27T13:00:00Z
```

**odds_spreads_week_X.csv**
```csv
game,home_team,away_team,team,spread,odds,sportsbook,game_time
Chiefs vs Giants,Chiefs,Giants,Chiefs,-7.0,-110,DraftKings,2025-10-27T13:00:00Z
Chiefs vs Giants,Chiefs,Giants,Giants,7.0,-110,DraftKings,2025-10-27T13:00:00Z
```

**odds_totals_week_X.csv**
```csv
game,home_team,away_team,total,over_under,odds,sportsbook,game_time
Chiefs vs Giants,Chiefs,Giants,48.5,Over,-110,DraftKings,2025-10-27T13:00:00Z
Chiefs vs Giants,Chiefs,Giants,48.5,Under,-110,DraftKings,2025-10-27T13:00:00Z
```

## API Key Management

The system uses **7 API keys** from The Odds API with smart rotation:

- **Free tier**: 6 keys × 500 requests = 3,000 requests/month
- **Paid tier**: 1 key × 20,000 requests = 20,000 requests/month
- **Total capacity**: 23,000 requests/month
- **Smart rotation**:
  - Free keys used first for spreads & totals
  - Paid key **always used** for player props (QB TD)
  - Automatic fallback to paid key if free keys exhausted

### Check API Usage

```python
from scrapers.odds_scraper import OddsScraper

scraper = OddsScraper()
status = scraper.get_usage_report()

print(status)
# Output:
# {
#   'total_keys': 7,
#   'total_requests': 30,
#   'remaining_requests': 22970,
#   'max_requests': 23000,
#   'per_key_usage': {...}
# }
```

## Configuration

Edit `config.py` to customize:

```python
# Scheduling - Twice-daily scraping Monday through Saturday
SCRAPE_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
SCRAPE_TIME = "09:00"        # 9am - Full scrape (all data)
ODDS_SCRAPE_TIME = "15:00"   # 3pm - Odds-only scrape (line movements)

# Current season
CURRENT_YEAR = 2025

# Request settings
REQUEST_TIMEOUT = 30  # seconds
REQUEST_DELAY = 2     # seconds between requests

# API Limits
FREE_TIER_MAX_REQUESTS = 500    # Per key per month
PAID_TIER_MAX_REQUESTS = 20000  # Paid key per month
```

## Logging

Logs are saved to:
- `scraper.log` - Main pipeline logs
- `scheduler.log` - Main scheduler activity (9am runs)
- `scheduler_odds.log` - Odds scheduler activity (3pm runs)
- Console output - Real-time progress

View logs:
```bash
tail -f scraper.log          # Pipeline execution logs
tail -f scheduler.log        # Main scheduler (9am)
tail -f scheduler_odds.log   # Odds scheduler (3pm)
```

## Troubleshooting

### "No Odds API keys configured"
- Make sure `.env` file exists (copy from `.env.example`)
- Add at least one `ODDS_API_KEY_X` to `.env`

### "Could not find defense stats table"
- Pro Football Reference may have changed their HTML structure
- Check the URL manually: https://www.pro-football-reference.com/years/2025/opp.htm
- Update table selectors in `defense_stats_scraper.py` if needed

### "Failed to scrape matchups"
- ESPN's schedule page structure may have changed
- Verify URL: https://www.espn.com/nfl/schedule
- Update parsing logic in `matchups_scraper.py` if needed

### "All API keys exhausted"
- You've used all 3,000 requests for the month
- Wait until next month, or upgrade to paid tier
- Check usage: `python scrapers/odds_scraper.py` shows remaining requests

### Rate limiting / 429 errors
- Increase `REQUEST_DELAY` in `config.py`
- Pro Football Reference may block if requests are too frequent

## Daily Workflow

The system runs **TWICE DAILY, Monday through Saturday**:

### Monday Morning - Week Transition
```bash
# Advance to next week
python utils/week_manager.py --advance

# Verify the change
python utils/week_manager.py
```

### Before First Scrape (Any Day)
```bash
# Validate current week and data files
python utils/week_manager.py --validate
```

### Morning Run (9:00 AM) - Full Scrape
Collects ALL data:
1. **Defense stats** (Pass TDs allowed per game)
2. **QB stats** (Season totals, starting status)
3. **Matchups** (This week's games)
4. **Odds data** (All markets):
   - QB TD props (over 0.5)
   - Point spreads
   - Over/under totals

### Afternoon Run (3:00 PM) - Odds Only
Collects ODDS data only:
- QB TD props (over 0.5)
- Point spreads
- Over/under totals

### Why Twice Daily (12 Runs/Week)?
- **9am Morning Run:**
  - Fresh stats after overnight updates
  - Monday: First scrape after weekend games
  - Tuesday: Stats after Monday Night Football
  - Early odds capture (opening lines)

- **3pm Afternoon Run:**
  - **Line movement tracking**: See how odds shift throughout the day
  - **More player props**: Props often post/update during afternoon
  - **Pre-game final**: Saturday 3pm = last update before evening games

### Automated (Set and Forget)
```bash
# Start both schedulers (keep both running)
python scheduler.py          # 9am - all data
python scheduler_odds.py     # 3pm - odds only
```

## Project Structure

```
Bet-That_(Proof of Concept)/
├── scrapers/
│   ├── __init__.py
│   ├── defense_stats_scraper.py   # Pro Football Reference defense
│   ├── qb_stats_scraper.py        # Pro Football Reference QBs
│   ├── matchups_scraper.py        # ESPN schedule
│   └── odds_scraper.py            # The Odds API
├── utils/
│   ├── __init__.py
│   ├── api_key_rotator.py         # API key rotation logic
│   ├── week_manager.py            # Week tracking module
│   ├── db_manager.py              # Database operations (Phase 1)
│   ├── historical_storage.py      # Snapshot management (Phase 1)
│   └── query_tools.py             # Database queries (Phase 1)
├── data/
│   ├── raw/                       # CSV output directory
│   ├── database/                  # SQLite database (Phase 1)
│   │   └── nfl_betting.db
│   └── historical/                # Timestamped snapshots (Phase 1)
│       ├── archives/              # ZIP backups
│       └── 2025/week_7/          # Weekly snapshots
├── config.py                      # Configuration settings
├── main.py                        # Main orchestrator
├── scheduler.py                   # Main scheduler (9am - all data)
├── scheduler_odds.py              # Odds scheduler (3pm - odds only)
├── current_week.json              # Current week configuration
├── requirements.txt               # Python dependencies
├── .env                           # API keys (create from .env.example)
├── .env.example                   # Template for .env
├── README.md                      # This file
├── DATABASE_SETUP.md              # Database guide (Phase 1)
└── WEEK_MANAGEMENT.md             # Week management guide
```

## Next Steps / Enhancements

**Phase 1 Complete:**
✅ Database storage with SQLite  
✅ Historical snapshots and archiving  
✅ Query tools for edge detection  
✅ Backward compatibility with CSV output  

**Phase 2 Improvements:**
1. Advanced edge detection algorithms
2. Real-time line movement analysis
3. Automated alert system
4. Web dashboard for data visualization

**Production Deployment:**
- Deploy to cloud (AWS, Heroku, etc.)
- Use cron jobs instead of Python scheduler
- Set up monitoring alerts

## Support

For issues or questions:
1. Check logs: `scraper.log` and `scheduler.log`
2. Test individual scrapers first
3. Verify `.env` file is configured
4. Check internet connection and API quotas

## License

For personal use only. Respect rate limits and Terms of Service for all data sources.

---

**Built for Bet-That POC** | Last updated: October 2025
