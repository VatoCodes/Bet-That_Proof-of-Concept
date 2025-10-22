# System Architecture & Design

## Overview

This is an automated NFL data scraping system designed to collect betting data for two strategies:
1. **QB TD Edge Strategy** - Find value in QB passing TD props
2. **Key Numbers Strategy** - Exploit key numbers in spreads and totals

## Data Storage Architecture

### Two-Tier Storage System

The system uses a two-tier storage architecture to balance performance, data integrity, and historical preservation:

#### Tier 1: Operational Database (SQLite)
**Location:** `data/database/nfl_betting.db`
**Purpose:** Current state for live queries
**Characteristics:**
- One record per entity (team, matchup, QB)
- Fast queries for dashboard and edge detection
- UNIQUE constraints on natural keys (not timestamps)
- `scraped_at` for audit purposes only

#### Tier 2: Historical Snapshots (CSV)
**Location:** `data/historical/{year}/week_{week}/`
**Purpose:** Complete audit trail of all scrapes
**Characteristics:**
- Timestamped CSV files for every scrape
- Preserves data even if re-scraped
- Used for analysis, debugging, rollback
- Compresses well for long-term storage

### Duplicate Prevention Strategy

#### Problem Solved
The original system had duplicate records because UNIQUE constraints included `scraped_at` timestamps:
```sql
-- WRONG: Allows duplicates because scraped_at changes each run
UNIQUE(team_name, week, scraped_at)
```

#### Solution Implemented
Fixed UNIQUE constraints to use natural keys only:
```sql
-- CORRECT: Prevents duplicates based on business logic
UNIQUE(team_name, week)
```

#### Scraper Pattern: Snapshot-Then-Upsert
Every scraper follows this pattern:
1. **Scrape** - Get latest data from source
2. **Save CSV** - Write to `data/raw/`
3. **Snapshot** - Copy to `data/historical/` with timestamp
4. **Upsert DB** - DELETE old + INSERT new into operational database

This ensures:
- History is never lost (step 3)
- Database stays current (step 4)
- Idempotency (re-running replaces, doesn't duplicate)

#### Database Schema Design

**defense_stats Table:**
```sql
CREATE TABLE defense_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    pass_tds_allowed INTEGER,
    games_played INTEGER,
    tds_per_game REAL,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_name, week)  -- Natural key constraint
);
```

**matchups Table:**
```sql
CREATE TABLE matchups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_date DATE,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(home_team, away_team, week)  -- Natural key constraint
);
```

**qb_props Table:**
```sql
CREATE TABLE qb_props (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qb_name TEXT NOT NULL,
    week INTEGER,
    sportsbook TEXT NOT NULL,
    over_odds INTEGER,
    under_odds INTEGER,
    over_line REAL,
    under_line REAL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(qb_name, week, sportsbook)  -- Natural key constraint
);
```

#### Why Not Store History in Database?

**Considered:** Adding `is_current` flag or separate `historical_` tables
**Rejected because:**
1. Performance - Queries would need `WHERE is_current = 1` everywhere
2. Complexity - Migration from current schema is complex
3. Size - Database would grow indefinitely
4. CSV benefits - Snapshots are portable, compressible, inspectable

#### Query Guidelines

**Dashboard/API queries:**
```python
# Just query directly - no duplicate filtering needed
df = pd.read_sql("SELECT * FROM defense_stats WHERE week = ?", conn, (week,))
```

**Historical analysis:**
```python
# Load specific snapshot from historical storage
snapshot_path = "data/historical/2025/week_7/defense_stats_20251021_174306_auto.csv"
df = pd.read_csv(snapshot_path)
```

## System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   WEEK MANAGER                               │
│  current_week.json - Single source of truth                 │
│  ├── Current week: 8                                        │
│  ├── Status: in_progress                                    │
│  └── Validates data files                                   │
└────────────────┬────────────────────────────────────────────┘
                 │ (all components query for current week)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      SCHEDULER                               │
│  Runs: Monday-Saturday at 9:00 AM & 3:00 PM                │
│  Triggers: main.py (full/odds-only data collection)         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      MAIN.PY                                 │
│  Orchestrates all scrapers in sequence                      │
│  Uses WeekManager to get current week                       │
│  Optional: --save-to-db, --save-snapshots                  │
└─┬────────┬────────┬────────┬─────────────────────────────┘
  │        │        │        │
  │        │        │        │
  ▼        ▼        ▼        ▼
┌───┐   ┌───┐   ┌───┐   ┌─────────────────────────────┐
│ 1 │   │ 2 │   │ 3 │   │ 4                            │
│DEF│   │ QB│   │MTH│   │ODDS (3 markets)              │
│   │   │   │   │   │   │  - Spreads                   │
│   │   │   │   │   │   │  - Totals                    │
│   │   │   │   │   │   │  - QB TD Props               │
└───┘   └───┘   └───┘   └─────────────────────────────┘
  │        │        │        │
  │        │        │        │
  ▼        ▼        ▼        ▼
┌─────────────────────────────────────────────────────────────┐
│                    CSV OUTPUT FILES                          │
│  data/raw/                                                   │
│    ├── defense_stats_week_8.csv                             │
│    ├── qb_stats_2025.csv                                    │
│    ├── matchups_week_8.csv                                  │
│    ├── odds_spreads_week_8.csv                              │
│    ├── odds_totals_week_8.csv                               │
│    └── odds_qb_td_week_8.csv                                │
└────────────────┬────────────────────────────────────────────┘
                 │ (if --save-to-db flag enabled)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE STORAGE                          │
│  data/database/nfl_betting.db                               │
│  ├── defense_stats (team defense metrics)                   │
│  ├── qb_stats (QB performance data)                         │
│  ├── matchups (game schedules)                             │
│  ├── odds_spreads (point spreads)                          │
│  ├── odds_totals (over/under lines)                        │
│  ├── qb_props (QB TD player props)                         │
│  └── scrape_runs (execution tracking)                      │
└────────────────┬────────────────────────────────────────────┘
                 │ (if --save-snapshots flag enabled)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 HISTORICAL SNAPSHOTS                         │
│  data/historical/2025/week_8/                               │
│  ├── defense_stats_20251021_090023_auto.csv                │
│  ├── qb_stats_20251021_090023_auto.csv                     │
│  ├── matchups_20251021_090023_auto.csv                     │
│  ├── odds_spreads_20251021_090023_auto.csv                 │
│  ├── odds_totals_20251021_090023_auto.csv                  │
│  └── qb_props_20251021_090023_auto.csv                     │
└────────────────┬────────────────────────────────────────────┘
                 │ (Phase 2: Edge Detection)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    EDGE CALCULATOR                           │
│  utils/edge_calculator.py                                   │
│  ├── ProbabilityCalculator (v1/v2 models)                   │
│  ├── EdgeDetector (odds conversion)                         │
│  ├── BetRecommender (Kelly Criterion)                       │
│  └── EdgeCalculator (main orchestrator)                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    EDGE OPPORTUNITIES                        │
│  find_edges.py CLI tool                                     │
│  ├── Tier classification (PASS/SMALL/GOOD/STRONG)            │
│  ├── Bet sizing recommendations                             │
│  ├── CSV export for tracking                                │
│  └── Model calibration tools                                │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 0. Week Manager (`utils/week_manager.py`)

**Purpose**: Centralized week tracking to prevent data synchronization issues

**Pseudocode**:
```
CLASS WeekManager:
    INITIALIZE():
        - Set config_file path to current_week.json
        - Set data_dir to data/raw/
        - Load existing config (or create default)

    FUNCTION get_current_week() -> int:
        """Get current NFL week number"""
        IF current_week.json exists AND has manual override:
            RETURN config['current_week']
        ELSE:
            RETURN calculate_week_from_date()

    FUNCTION calculate_week_from_date(reference_date=None) -> int:
        """Calculate week based on season start date"""
        season_start = datetime(2025, 9, 5)  # Sept 5, 2025
        IF reference_date is None:
            reference_date = datetime.now()

        days_since_start = (reference_date - season_start).days
        week = (days_since_start // 7) + 1

        IF week < 1:
            RETURN 1
        IF week > 18:
            RETURN 18

        RETURN week

    FUNCTION get_week_info() -> Dict:
        """Get detailed week information"""
        RETURN {
            'current_week': get_current_week(),
            'season_year': config['season_year'],
            'week_start_date': config['week_start_date'],
            'week_end_date': config['week_end_date'],
            'status': config['status'],
            'last_updated': config['last_updated'],
            'source': config['source']  # 'manual' or 'calculated'
        }

    FUNCTION set_week(week, status='in_progress') -> bool:
        """Manually set current week"""
        IF week < 1 OR week > 18:
            RAISE "Week must be between 1-18"

        # Calculate week dates
        season_start = datetime(2025, 9, 5)
        week_start = season_start + timedelta(days=(week-1) * 7)
        week_end = week_start + timedelta(days=6)

        config = {
            'current_week': week,
            'season_year': 2025,
            'week_start_date': week_start.strftime('%Y-%m-%d'),
            'week_end_date': week_end.strftime('%Y-%m-%d'),
            'status': status,
            'last_updated': datetime.now().isoformat(),
            'source': 'manual'
        }

        - Save config to current_week.json
        RETURN True

    FUNCTION advance_week() -> Tuple[int, bool]:
        """Advance to next week"""
        current = get_current_week()

        IF current >= 18:
            LOG "Already at final week (18)"
            RETURN (current, False)

        new_week = current + 1
        set_week(new_week, status='upcoming')

        RETURN (new_week, True)

    FUNCTION validate_data_files() -> Dict:
        """Check which data files exist for current week"""
        current_week = get_current_week()

        expected_files = [
            f"defense_stats_week_{current_week}.csv",
            f"matchups_week_{current_week}.csv",
            f"odds_qb_td_week_{current_week}.csv",
            f"odds_spreads_week_{current_week}.csv",
            f"odds_totals_week_{current_week}.csv"
        ]

        results = {
            'current_week': current_week,
            'files_checked': len(expected_files),
            'files_current': 0,
            'missing_files': [],
            'outdated_files': []
        }

        FOR EACH filename IN expected_files:
            file_path = data_dir / filename

            IF file_path.exists():
                results['files_current'] += 1
            ELSE:
                results['missing_files'].append(filename)

                # Check for older week versions
                FOR week IN range(1, 18):
                    IF week == current_week:
                        CONTINUE

                    old_filename = filename.replace(
                        f"week_{current_week}",
                        f"week_{week}"
                    )
                    old_path = data_dir / old_filename

                    IF old_path.exists():
                        results['outdated_files'].append(old_filename)

        RETURN results

    FUNCTION main():
        """CLI interface"""
        parser = ArgumentParser()
        parser.add_argument('--set-week', type=int)
        parser.add_argument('--status', choices=['upcoming', 'in_progress', 'completed'])
        parser.add_argument('--advance', action='store_true')
        parser.add_argument('--validate', action='store_true')

        args = parser.parse_args()

        wm = WeekManager()

        IF args.set_week:
            wm.set_week(args.set_week, args.status or 'in_progress')
            print(f"✓ Set to Week {args.set_week}")

        IF args.advance:
            new_week, success = wm.advance_week()
            IF success:
                print(f"✓ Advanced to Week {new_week}")

        IF args.validate:
            results = wm.validate_data_files()
            print(f"Current Week: {results['current_week']}")
            print(f"Files found: {results['files_current']}/{results['files_checked']}")
            IF results['missing_files']:
                print(f"⚠️  Missing: {', '.join(results['missing_files'])}")

        # Default: show current week info
        IF NOT any([args.set_week, args.advance, args.validate]):
            info = wm.get_week_info()
            print("=" * 60)
            print("CURRENT NFL WEEK INFO")
            print("=" * 60)
            print(f"Week:        {info['current_week']}")
            print(f"Season:      {info['season_year']}")
            print(f"Start Date:  {info['week_start_date']}")
            print(f"End Date:    {info['week_end_date']}")
            print(f"Status:      {info['status']}")
            print(f"Source:      {info['source']}")
            print(f"Updated:     {info['last_updated']}")
            print("=" * 60)
```

**Key Features**:
- Single source of truth via `current_week.json`
- Automatic week calculation from season start date
- Manual override capability
- Data file validation (detects missing/stale files)
- CLI interface for week management
- Prevents data synchronization issues

**Integration Points**:
- `config.py` - Provides `get_current_week()` helper
- `main.py` - Uses WeekManager for default week
- `test_edge_detection.py` - Uses WeekManager with fallback

---

### 1. Main Scheduler (`scheduler.py`)

**Purpose**: Automated task scheduling for morning full data collection (9am)

**Pseudocode**:
```
CLASS NFLDataScheduler:
    INITIALIZE:
        - Verify main.py exists
        - Set up logging

    FUNCTION run_daily_collection():
        LOG "Starting daily data collection"
        TRY:
            - Execute main.py subprocess
            - Set timeout to 10 minutes
            - Capture stdout/stderr
            IF successful:
                LOG "✓ Daily collection completed"
            ELSE:
                LOG "✗ Daily collection failed"
        CATCH timeout:
            LOG "✗ Collection timed out"
        CATCH error:
            LOG "✗ Error: {error}"

    FUNCTION setup_schedule():
        FOR EACH day IN ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
            - Schedule run_daily_collection() at 09:00

    FUNCTION run():
        - Setup schedule
        WHILE True:
            - Check for pending tasks every 60 seconds
            - Execute tasks when scheduled time arrives
```

**Key Features**:
- Runs Monday-Saturday at 9:00 AM (6 days/week)
- 10-minute timeout for complete data collection
- Comprehensive logging to `scheduler.log`
- Test mode: `python scheduler.py --test`

---

### 1b. Odds Scheduler (`scheduler_odds.py`)

**Purpose**: Automated task scheduling for afternoon odds-only collection (3pm)

**Pseudocode**:
```
CLASS NFLOddsScheduler:
    INITIALIZE:
        - Verify main.py exists
        - Set up logging to scheduler_odds.log

    FUNCTION run_odds_collection():
        LOG "Starting odds-only collection"
        TRY:
            - Execute main.py --odds-only subprocess
            - Set timeout to 5 minutes (odds-only is faster)
            - Capture stdout/stderr
            IF successful:
                LOG "✓ Odds collection completed"
            ELSE:
                LOG "✗ Odds collection failed"
        CATCH timeout:
            LOG "✗ Collection timed out"
        CATCH error:
            LOG "✗ Error: {error}"

    FUNCTION setup_schedule():
        FOR EACH day IN ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
            - Schedule run_odds_collection() at 15:00 (3pm)

    FUNCTION run():
        - Setup schedule
        WHILE True:
            - Check for pending tasks every 60 seconds
            - Execute tasks when scheduled time arrives
```

**Key Features**:
- Runs Monday-Saturday at 3:00 PM (6 days/week)
- 5-minute timeout (odds-only is faster than full scrape)
- Separate logging to `scheduler_odds.log`
- Test mode: `python scheduler_odds.py --test`
- **Purpose**: Line movement tracking - captures odds changes throughout the day

---

### 2. Main Orchestrator (`main.py`)

**Purpose**: Coordinates all scrapers and handles workflow logic

**Pseudocode**:
```
CLASS DataPipeline:
    INITIALIZE(week, year):
        - Store week/year
        - Initialize results dictionary

    FUNCTION run_defense_stats() -> bool:
        TRY:
            - Create DefenseStatsScraper
            - Scrape data for year
            - Save to CSV with week number
            - Store file path in results['defense_stats']
            RETURN True
        CATCH error:
            LOG error
            RETURN False

    FUNCTION run_qb_stats() -> bool:
        TRY:
            - Create QBStatsScraper
            - Scrape season data
            - Save to CSV
            - Store file path in results['qb_stats']
            RETURN True
        CATCH error:
            LOG error
            RETURN False

    FUNCTION run_matchups() -> bool:
        TRY:
            - Create MatchupsScraper
            - Scrape ESPN schedule for week
            - Save to CSV
            - Store file path in results['matchups']
            RETURN True
        CATCH error:
            LOG error
            RETURN False

    FUNCTION run_odds() -> bool:
        TRY:
            - Create OddsScraper
            - Display initial API usage
            - Fetch ALL markets (spreads, totals, QB TD props)
            - Results is DICTIONARY with 3 file paths
            - Store dictionary in results['odds']
            - Display final API usage
            RETURN True
        CATCH error:
            LOG error
            RETURN False

    FUNCTION run_all(skip_odds=False) -> bool:
        success = True
        success &= run_defense_stats()
        success &= run_qb_stats()
        success &= run_matchups()
        IF NOT skip_odds:
            success &= run_odds()

        - Print summary report
        RETURN success
```

**Command Line Options**:
- `--week N` - Specify NFL week
- `--year YYYY` - Specify season year
- `--stats-only` - Run only defense + QB stats
- `--odds-only` - Run only matchups + odds
- `--skip-odds` - Run all except odds

---

### 3. Defense Stats Scraper (`scrapers/defense_stats_scraper.py`)

**Purpose**: Scrape Pro Football Reference for team defense statistics

**Pseudocode**:
```
CLASS DefenseStatsScraper:
    INITIALIZE(year):
        - Store year
        - Set URL to Pro Football Reference

    FUNCTION scrape() -> DataFrame:
        - Fetch HTML from PFR
        - Wait REQUEST_DELAY seconds (polite scraping)
        - Find "team_stats" table

        - Parse table with pandas.read_html()
        - Handle DUPLICATE column names:
            FOR EACH column:
                IF column name seen before:
                    Rename to "{column}_{count}"

        - Extract columns:
            * team_name (from "Tm" column)
            * pass_tds_allowed (from "TD" passing column)
            * games_played (from "G" column)
            * Calculate: tds_per_game = pass_tds_allowed / games_played

        RETURN cleaned DataFrame

    FUNCTION save_to_csv(data, week) -> str:
        - Create filename: defense_stats_week_{week}.csv
        - Save to data/raw/ directory
        RETURN file path

    FUNCTION run(week) -> str:
        - data = scrape()
        IF data is not empty:
            RETURN save_to_csv(data, week)
        ELSE:
            RETURN None
```

**Data Source**: https://www.pro-football-reference.com/years/2025/opp.htm

**Challenge Solved**: Pro Football Reference has duplicate column names (multiple "TD" columns). Solution: Rename duplicates before processing.

---

### 4. QB Stats Scraper (`scrapers/qb_stats_scraper.py`)

**Purpose**: Scrape Pro Football Reference for QB passing statistics

**Pseudocode**:
```
CLASS QBStatsScraper:
    INITIALIZE(year):
        - Store year
        - Set URL to PFR QB stats

    FUNCTION scrape() -> DataFrame:
        - Fetch HTML from PFR
        - Wait REQUEST_DELAY seconds
        - Find "passing" table

        - Parse table with pandas.read_html()
        - Handle duplicate columns (same as defense scraper)

        - Extract columns:
            * qb_name (from "Player" column)
            * team (from "Tm" column - handle if DataFrame)
            * total_tds (from "TD" column)
            * games_played (from "G" column)
            * is_starter (based on games_played > threshold)

        - Filter: Remove rows where qb_name is "Player" (header repeats)

        RETURN cleaned DataFrame

    FUNCTION save_to_csv(data, year) -> str:
        - Create filename: qb_stats_{year}.csv
        - Save to data/raw/
        RETURN file path

    FUNCTION run() -> str:
        - data = scrape()
        IF data is not empty:
            RETURN save_to_csv(data, year)
        ELSE:
            RETURN None
```

**Data Source**: https://www.pro-football-reference.com/years/2025/passing.htm

---

### 5. Matchups Scraper (`scrapers/matchups_scraper.py`)

**Purpose**: Scrape ESPN for weekly NFL schedule/matchups

**Pseudocode**:
```
CLASS MatchupsScraper:
    INITIALIZE():
        - Set URL to ESPN schedule

    FUNCTION scrape(week) -> List[Dict]:
        - Fetch ESPN schedule page
        - Parse HTML with BeautifulSoup

        matchups = []
        FOR EACH game element:
            - Extract home_team
            - Extract away_team
            - Extract game_date
            - Append to matchups list

        RETURN matchups

    FUNCTION save_to_csv(matchups, week) -> str:
        - Create filename: matchups_week_{week}.csv
        - Convert to DataFrame
        - Save to data/raw/
        RETURN file path

    FUNCTION run(week) -> str:
        - matchups = scrape(week)
        IF matchups not empty:
            RETURN save_to_csv(matchups, week)
        ELSE:
            RETURN None
```

**Data Source**: https://www.espn.com/nfl/schedule

---

### 6. Odds Scraper (`scrapers/odds_scraper.py`)

**Purpose**: Fetch odds from The Odds API for multiple markets

**Architecture**: This is the most complex scraper with API key management

**Pseudocode**:
```
CLASS OddsScraper:
    INITIALIZE():
        - Load API keys from config (6 free + 1 paid)
        - Create APIKeyRotator with free/paid tier support
        - Set bookmakers: DraftKings, FanDuel

    FUNCTION fetch_odds_by_market(market, use_paid=False) -> List:
        """
        Fetch odds for spreads or totals
        URL: /v4/sports/americanfootball_nfl/odds
        """
        IF use_paid:
            key = api_rotator.get_paid_key()
        ELSE:
            key = api_rotator.get_next_key()

        params = {
            'apiKey': key,
            'regions': 'us',
            'markets': market,  # "spreads" or "totals"
            'bookmakers': 'draftkings,fanduel',
            'oddsFormat': 'american'
        }

        response = requests.get(url, params)
        IF response.ok:
            - Track remaining requests
            RETURN response.json()
        ELSE:
            LOG error
            RETURN empty list

    FUNCTION fetch_player_props_for_all_events() -> List:
        """
        Fetch QB TD props - REQUIRES PER-EVENT API CALLS
        Cannot use general /odds endpoint for player props
        """
        # Step 1: Get all NFL events
        events_url = "/v4/sports/americanfootball_nfl/events"
        key = api_rotator.get_paid_key()  # ALWAYS use paid key

        response = requests.get(events_url, params={'apiKey': key})
        events = response.json()

        all_props = []

        # Step 2: Fetch player props for EACH event
        FOR EACH event IN events:
            event_id = event['id']
            props_url = f"/v4/sports/.../events/{event_id}/odds"

            params = {
                'apiKey': key,  # Same paid key
                'regions': 'us',
                'markets': 'player_pass_tds',
                'bookmakers': 'draftkings,fanduel',
                'oddsFormat': 'american'
            }

            response = requests.get(props_url, params)
            IF response.ok:
                props = _parse_event_player_props(response.json())
                all_props.extend(props)

        RETURN all_props

    FUNCTION _parse_event_player_props(event_data) -> List:
        """
        Parse player props from event response
        Structure: event -> bookmakers -> markets -> outcomes
        """
        props = []

        home_team = event_data['home_team']
        away_team = event_data['away_team']
        commence_time = event_data['commence_time']

        FOR EACH bookmaker IN event_data['bookmakers']:
            bookmaker_name = bookmaker['title']

            FOR EACH market IN bookmaker['markets']:
                IF market['key'] == 'player_pass_tds':

                    FOR EACH outcome IN market['outcomes']:
                        IF outcome['name'] == 'Over':
                            qb_name = outcome['description']  # "Justin Herbert Over 0.5"
                            qb_name = extract_qb_name(qb_name)
                            odds = outcome['price']

                            props.append({
                                'qb_name': qb_name,
                                'odds_over_05_td': odds,
                                'sportsbook': bookmaker_name,
                                'game': f"{away_team} @ {home_team}",
                                'home_team': home_team,
                                'away_team': away_team,
                                'game_time': commence_time
                            })

        RETURN props

    FUNCTION _parse_spreads(data) -> List:
        """Parse spreads from general odds response"""
        spreads = []

        FOR EACH game IN data:
            home_team = game['home_team']
            away_team = game['away_team']

            FOR EACH bookmaker IN game['bookmakers']:
                FOR EACH market IN bookmaker['markets']:
                    IF market['key'] == 'spreads':
                        FOR EACH outcome IN market['outcomes']:
                            spreads.append({
                                'team': outcome['name'],
                                'spread': outcome['point'],
                                'odds': outcome['price'],
                                'sportsbook': bookmaker['title'],
                                ...
                            })

        RETURN spreads

    FUNCTION _parse_totals(data) -> List:
        """Parse totals from general odds response"""
        # Similar to spreads parsing
        # Extract Over/Under lines and odds

    FUNCTION fetch_all_odds(week) -> Dict[str, str]:
        """
        Main function - fetches ALL markets
        Returns: Dictionary with 3 CSV file paths
        """
        results = {}

        # Market 1: Spreads (use free keys)
        spreads_data = fetch_odds_by_market('spreads', use_paid=False)
        spreads_list = _parse_spreads(spreads_data)
        results['spreads'] = save_spreads_csv(spreads_list, week)

        # Market 2: Totals (use free keys)
        totals_data = fetch_odds_by_market('totals', use_paid=False)
        totals_list = _parse_totals(totals_data)
        results['totals'] = save_totals_csv(totals_list, week)

        # Market 3: QB TD Props (ALWAYS use paid key, per-event fetching)
        props_list = fetch_player_props_for_all_events()
        results['player_pass_tds'] = save_qb_td_csv(props_list, week)

        RETURN results

    FUNCTION run(week) -> Dict[str, str]:
        """Entry point called by main.py"""
        RETURN fetch_all_odds(week)
```

**API Endpoints Used**:
1. `/v4/sports/americanfootball_nfl/odds` - For spreads & totals
2. `/v4/sports/americanfootball_nfl/events` - List all games
3. `/v4/sports/americanfootball_nfl/events/{eventId}/odds` - Per-game player props

**Key Design Decisions**:
- **Player props require per-event calls** - Cannot bulk fetch like spreads/totals
- **Always use paid key for player props** - Most valuable data
- **Free keys for spreads/totals** - Conserve paid key quota
- **Three separate CSV files** - Easier analysis than single combined file

---

### 7. API Key Rotator (`utils/api_key_rotator.py`)

**Purpose**: Smart API key rotation with free/paid tier management

**Pseudocode**:
```
CLASS APIKeyRotator:
    INITIALIZE(api_keys, paid_key, free_limit=500, paid_limit=20000):
        - Store all keys (free keys first, paid key last)
        - Track request count for each key
        - Track max limits per tier
        - Identify paid_key_index
        - current_index = 0

    FUNCTION get_next_key() -> str:
        """
        Get next available FREE tier key
        Rotates through keys when one hits limit
        Falls back to paid key if all free keys exhausted
        """
        attempts = 0

        WHILE attempts < len(free_keys):
            key = api_keys[current_index]

            IF current_index == paid_key_index:
                # Skip paid key in normal rotation
                current_index = (current_index + 1) % len(api_keys)
                CONTINUE

            IF request_counts[key] < free_tier_limit:
                RETURN key

            # Key exhausted, try next
            current_index = (current_index + 1) % len(api_keys)
            attempts += 1

        # All free keys exhausted - fallback to paid
        LOG "All free keys exhausted, using paid key"
        RETURN get_paid_key()

    FUNCTION get_paid_key() -> str:
        """
        Get the paid tier key
        Always available for player props
        """
        IF paid_key_index is None:
            RAISE "No paid API key configured"

        paid_key = api_keys[paid_key_index]

        IF request_counts[paid_key] >= paid_tier_limit:
            RAISE "Paid tier limit reached (20,000 requests)"

        RETURN paid_key

    FUNCTION track_request(key, remaining):
        """Update request counts after API call"""
        requests_used = calculate_used(remaining)
        request_counts[key] = requests_used

    FUNCTION get_status_report() -> Dict:
        """
        Generate usage report
        Returns: {
            'total_keys': 7,
            'total_requests': 30,
            'remaining_requests': 22970,
            'per_key_usage': {...}
        }
        """
        total_used = sum(request_counts.values())
        total_capacity = (6 * free_limit) + paid_limit

        RETURN {
            'total_keys': len(api_keys),
            'total_requests': total_used,
            'remaining_requests': total_capacity - total_used,
            'max_requests': total_capacity,
            'per_key_usage': request_counts
        }
```

**Key Features**:
- Automatic rotation among free keys
- Fallback to paid key when free exhausted
- Direct paid key access for player props
- Request tracking with detailed reporting

---

### 8. Database Manager (`utils/db_manager.py`)

**Purpose**: SQLite database operations and schema management

**Key Features**:
- Single-file SQLite database for portability
- Comprehensive schema with 8 tables
- Performance indexes on common query fields
- CSV-to-database bulk import functionality
- Scrape run tracking and monitoring
- Database statistics and health reporting

**Integration**: Used by main.py when `--save-to-db` flag is enabled

---

### 9. Historical Storage (`utils/historical_storage.py`)

**Purpose**: Timestamped snapshot management and archiving

**Key Features**:
- Timestamped CSV snapshots with metadata
- Organized directory structure by year/week
- ZIP archiving for storage efficiency
- Automatic cleanup of old files
- JSON metadata tracking for each snapshot

**Integration**: Used by main.py when `--save-snapshots` flag is enabled

---

### 10. Query Tools (`utils/query_tools.py`)

**Purpose**: Database query helpers for edge detection and analysis

**Key Features**:
- Context manager for automatic connection handling
- Weak defense detection with configurable thresholds
- QB prop analysis and edge calculation
- Line movement tracking over time
- Data export functionality for analysis
- Comprehensive query interface for edge detection

**Integration**: Standalone CLI tool and Python API for edge detection queries

---

## Data Flow Example

### Typical Monday-Saturday Runs (Twice Daily)

```
=== MORNING RUN (9:00 AM) - FULL SCRAPE ===
09:00:00 - Main Scheduler wakes up
09:00:01 - Executes main.py (full workflow)
09:00:02 - main.py starts DataPipeline(week=7, year=2025)

Step 1: Defense Stats
09:00:03 - Fetch Pro Football Reference
09:00:05 - Parse 32 team defenses
09:00:06 - Save defense_stats_week_7.csv
          ✓ Success (32 records)

Step 2: QB Stats
09:00:08 - Fetch Pro Football Reference
09:00:10 - Parse 71 QBs
09:00:11 - Save qb_stats_2025.csv
          ✓ Success (71 records)

Step 3: Matchups
09:00:13 - Fetch ESPN schedule
09:00:15 - Parse week 7 games
09:00:16 - Save matchups_week_7.csv
          ✓ Success (27 matchups)

Step 4: Odds (Multi-Market)
09:00:18 - Initialize OddsScraper
          API Status: 7 keys, 22,970 requests remaining

  4a: Spreads
  09:00:19 - Call /odds API with markets=spreads
           - Uses free key #1 (490 requests remaining)
  09:00:20 - Received 27 games from DraftKings + FanDuel
  09:00:21 - Parse spreads (52 home + 52 away = 104 records)
  09:00:22 - Save odds_spreads_week_7.csv
           ✓ Success (104 records)

  4b: Totals
  09:00:23 - Call /odds API with markets=totals
           - Uses free key #1 (489 requests remaining)
  09:00:24 - Received 27 games from DraftKings + FanDuel
  09:00:25 - Parse totals (52 over + 52 under = 104 records)
  09:00:26 - Save odds_totals_week_7.csv
           ✓ Success (104 records)

  4c: QB TD Player Props (Per-Event)
  09:00:27 - Call /events API to list games
           - Uses PAID key (19,999 requests remaining)
  09:00:28 - Found 27 events
  09:00:29 - FOR EACH event (27 iterations):
             * Call /events/{id}/odds with markets=player_pass_tds
             * Uses PAID key (decrementing remaining)
             * Parse QB names and "Over 0.5" odds
  09:00:57 - Completed all 27 events (28 total API calls)
           - Paid key: 19,972 requests remaining
  09:00:58 - Collected 1 QB prop (Jaxson Dart)
           Note: Most props not yet available
  09:00:59 - Save odds_qb_td_week_7.csv
           ✓ Success (1 record)

09:01:00 - Final API Status: 30 requests used, 22,970 remaining

SUMMARY:
✓ Defense Stats: defense_stats_week_7.csv
✓ QB Stats: qb_stats_2025.csv
✓ Matchups: matchups_week_7.csv
✓ Odds:
    - spreads: odds_spreads_week_7.csv
    - totals: odds_totals_week_7.csv
    - player_pass_tds: odds_qb_td_week_7.csv

09:01:01 - main.py exits with status 0
09:01:02 - Main scheduler logs success
09:01:03 - Main scheduler returns to waiting state

=== AFTERNOON RUN (3:00 PM) - ODDS ONLY ===
15:00:00 - Odds Scheduler wakes up
15:00:01 - Executes main.py --odds-only
15:00:02 - main.py starts DataPipeline(week=7, year=2025)

Step 1: Matchups (needed for odds context)
15:00:03 - Fetch ESPN schedule
15:00:05 - Parse week 7 games
15:00:06 - Save matchups_week_7.csv
          ✓ Success (27 matchups)

Step 2: Odds (All Markets)
15:00:08 - Initialize OddsScraper
          API Status: 7 keys, 22,942 requests remaining (after morning run)

  2a: Spreads
  15:00:09 - Call /odds API with markets=spreads
           - Uses free key #1 (488 requests remaining)
  15:00:10 - Received 27 games, parse spreads
  15:00:11 - Save odds_spreads_week_7_3pm.csv
           ✓ Success (104 records)

  2b: Totals
  15:00:12 - Call /odds API with markets=totals
           - Uses free key #1 (487 requests remaining)
  15:00:13 - Parse totals
  15:00:14 - Save odds_totals_week_7_3pm.csv
           ✓ Success (104 records)

  2c: QB TD Player Props
  15:00:15 - Call /events API
           - Uses PAID key (19,971 requests remaining)
  15:00:16 - Found 27 events
  15:00:17 - Fetch props for all 27 events (per-event calls)
  15:00:45 - Collected 15 QB props (more available at 3pm than 9am!)
  15:00:46 - Save odds_qb_td_week_7_3pm.csv
           ✓ Success (15 records)

15:00:47 - Final API Status: 19 more requests used, 22,923 remaining
15:00:48 - main.py exits with status 0
15:00:49 - Odds scheduler logs success
15:00:50 - Odds scheduler returns to waiting state

DAILY SUMMARY (Both Runs):
- Total API calls: 38 (19 morning + 19 afternoon)
- Total time: ~2 minutes (morning + afternoon combined)
- Line movement data: 2 snapshots per day (9am baseline, 3pm update)
```

---

## Error Handling Strategy

### Pro Football Reference Scraping
```
TRY:
    Fetch HTML
CATCH connection error:
    LOG "Network error accessing PFR"
    RETRY with exponential backoff (3 attempts)

TRY:
    Parse table
CATCH table not found:
    LOG "Could not find expected table - PFR structure changed"
    NOTIFY user to update scraper

IF duplicate columns detected:
    Rename columns before processing
    LOG "Handled duplicate columns"
```

### The Odds API
```
TRY:
    Make API request
CATCH 429 (rate limit):
    LOG "Rate limited - switching to next key"
    Rotate to next available key
    RETRY request

CATCH 422 (unprocessable):
    IF market == 'player_pass_tds':
        LOG "Player props not available yet (normal for early week)"
        Return empty list
    ELSE:
        LOG "API validation error"
        Return None

CATCH 401 (unauthorized):
    LOG "Invalid API key"
    Remove key from rotation
    Continue with remaining keys

IF all keys exhausted:
    LOG "All API keys have reached their limits"
    IF paid key available:
        Fallback to paid key
    ELSE:
        Return error
```

---

## Configuration Management

All configuration in `config.py`:

```python
# Data Sources
PFR_BASE_URL = "https://www.pro-football-reference.com"
ESPN_SCHEDULE_URL = "https://www.espn.com/nfl/schedule"
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# API Keys (from .env)
ODDS_API_KEYS_FREE = [key1, key2, ..., key6]  # 6 free keys
ODDS_API_KEY_PAID = paid_key                   # 1 paid key

# API Limits
FREE_TIER_MAX_REQUESTS = 500
PAID_TIER_MAX_REQUESTS = 20000

# Scheduling - Twice daily
SCRAPE_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
SCRAPE_TIME = "09:00"        # Morning - full scrape (all data)
ODDS_SCRAPE_TIME = "15:00"   # Afternoon - odds only (line movements)

# Request Settings
REQUEST_TIMEOUT = 30  # seconds
REQUEST_DELAY = 2     # seconds between requests (polite scraping)

# Output
DATA_DIR = BASE_DIR / "data" / "raw"
```

---

## Testing Strategy

### Unit Testing Individual Scrapers
```bash
# Test defense stats
python scrapers/defense_stats_scraper.py 7

# Test QB stats
python scrapers/qb_stats_scraper.py 2025

# Test matchups
python scrapers/matchups_scraper.py 7

# Test odds (all markets)
python scrapers/odds_scraper.py 7
```

### Integration Testing
```bash
# Test full pipeline
python main.py --week 7

# Test both schedulers immediately
python scheduler.py --test         # Morning run (all data)
python scheduler_odds.py --test    # Afternoon run (odds only)
```

### Manual Verification
```bash
# Check output files
ls -lh data/raw/

# Verify CSV contents
head data/raw/defense_stats_week_7.csv
head data/raw/odds_spreads_week_7.csv

# Check API usage
python -c "
from scrapers.odds_scraper import OddsScraper
s = OddsScraper()
print(s.get_usage_report())
"
```

---

## Performance Considerations

### Request Throttling
- **Pro Football Reference**: 2-second delay between requests (respectful scraping)
- **The Odds API**: No delay needed (we're below rate limits)
- **ESPN**: 2-second delay between requests

### Memory Usage
- All scraping done with streaming (no full page loads in memory)
- DataFrames cleared after writing to CSV
- Typical memory footprint: <100MB

### API Quota Management
**Weekly Usage Estimate (6 days/week × 2 runs/day)**:
- Morning runs (9am): 6 × 19 calls = 114 requests/week
- Afternoon runs (3pm): 6 × 19 calls = 114 requests/week
- **Total: ~228 requests/week**

**Monthly Capacity**:
- 228 req/week × 4.3 weeks = ~980 requests/month
- Available: 23,000 requests/month
- **Utilization: 4.3%** (massive headroom - still 95.7% available)

---

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
├── test_edge_detection.py         # Phase 0 validation script
├── requirements.txt               # Python dependencies
├── .env                           # API keys (create from .env.example)
├── .env.example                   # Template for .env
├── README.md                      # User guide
├── ARCHITECTURE.md                # This file - system design
├── DATABASE_SETUP.md              # Database guide (Phase 1)
├── WEEK_MANAGEMENT.md             # Week tracking guide
├── SYSTEM_STATUS.md               # System status report
└── TWICE_DAILY_SETUP.md           # Scheduler setup guide
```

---

## Future Enhancements

### Phase 2 Features
1. ✅ ~~**Data Validation**~~ - (COMPLETE - `python utils/week_manager.py --validate`)
2. **Edge Detection**: Calculate betting edges automatically
3. ✅ ~~**Line Movement Tracking**~~ - (COMPLETE - Twice-daily runs)
4. **Alert System**: Email/SMS when edges found
5. **Database Storage**: PostgreSQL instead of CSV
6. **Web Dashboard**: Visualize data and edges

### Scalability
- Add more sportsbooks (currently DraftKings + FanDuel)
- Add more markets (alternate lines, player props)
- Support multiple sports (NBA, MLB)
- Cloud deployment (AWS Lambda scheduled functions)

---

## Troubleshooting Guide

### "No data collected"
CHECK:
1. Internet connection working?
2. API keys in .env file?
3. Check logs: `tail -f scraper.log`

### "Player props returning empty"
REASON: Sportsbooks post player props Thursday/Friday
SOLUTION: Run scraper Thursday-Saturday when props available

### "All API keys exhausted"
REASON: Used all 23,000 monthly requests
SOLUTION: Wait for next month or reduce scraping frequency

### "PFR structure changed"
REASON: Pro Football Reference updated their HTML
SOLUTION: Update table selectors in scraper files

---

**Last Updated**: October 2025
**Version**: 2.0 (Daily Scheduler + Multi-Market Odds)
