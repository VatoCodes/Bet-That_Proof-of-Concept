# Database Setup Guide

**Version**: Phase 1 Implementation  
**Date**: October 21, 2025  
**Purpose**: Complete guide to the NFL Edge Finder database system

---

## Overview

The NFL Edge Finder now includes a SQLite database system for persistent data storage and historical tracking. This replaces CSV-only storage with a scalable foundation for edge detection and line movement analysis.

### Key Features

- **SQLite Database**: Single-file, portable database with 8 tables
- **Historical Snapshots**: Timestamped CSV backups for line movement analysis
- **Backward Compatibility**: CSV output continues to work alongside database
- **Query Tools**: Python helpers for edge detection queries
- **Automated Archiving**: Weekly ZIP archives for storage efficiency

---

## Database Schema

### Core Tables

#### 1. `defense_stats`
Team defense statistics with weekly tracking.

```sql
CREATE TABLE defense_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    pass_tds_allowed INTEGER,
    games_played INTEGER,
    tds_per_game REAL,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_name, week, scraped_at)
);
```

**Purpose**: Track how many passing TDs each team allows per game  
**Key Fields**: `team_name`, `tds_per_game`, `week`  
**Indexes**: `idx_defense_week`, `idx_defense_team`

#### 2. `qb_stats`
Quarterback statistics by season.

```sql
CREATE TABLE qb_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qb_name TEXT NOT NULL,
    team TEXT,
    total_tds INTEGER,
    games_played INTEGER,
    is_starter BOOLEAN,
    year INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(qb_name, team, year, scraped_at)
);
```

**Purpose**: Track QB performance metrics for edge calculation  
**Key Fields**: `qb_name`, `total_tds`, `is_starter`, `year`  
**Indexes**: `idx_qb_year`, `idx_qb_name`

#### 3. `matchups`
Weekly game schedules and matchups.

```sql
CREATE TABLE matchups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_date DATE,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(home_team, away_team, week, scraped_at)
);
```

**Purpose**: Link QBs to their opposing defenses  
**Key Fields**: `home_team`, `away_team`, `week`  
**Indexes**: `idx_matchups_week`

#### 4. `odds_spreads`
Point spread betting lines.

```sql
CREATE TABLE odds_spreads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game TEXT,
    home_team TEXT,
    away_team TEXT,
    team TEXT,
    spread REAL,
    odds INTEGER,
    sportsbook TEXT,
    game_time TIMESTAMP,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Track point spread movements  
**Key Fields**: `spread`, `odds`, `sportsbook`, `week`  
**Indexes**: `idx_spreads_week`, `idx_spreads_sportsbook`

#### 5. `odds_totals`
Over/under betting lines.

```sql
CREATE TABLE odds_totals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game TEXT,
    home_team TEXT,
    away_team TEXT,
    line_type TEXT,
    total REAL,
    odds INTEGER,
    sportsbook TEXT,
    game_time TIMESTAMP,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Track over/under line movements  
**Key Fields**: `total`, `odds`, `sportsbook`, `week`  
**Indexes**: `idx_totals_week`, `idx_totals_sportsbook`

#### 6. `qb_props`
QB passing TD player props.

```sql
CREATE TABLE qb_props (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qb_name TEXT,
    odds_over_05_td INTEGER,
    sportsbook TEXT,
    game TEXT,
    home_team TEXT,
    away_team TEXT,
    game_time TIMESTAMP,
    week INTEGER,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Track QB TD prop odds for edge detection  
**Key Fields**: `qb_name`, `odds_over_05_td`, `sportsbook`, `week`  
**Indexes**: `idx_props_week`, `idx_props_qb`

#### 7. `scrape_runs`
Execution tracking and monitoring.

```sql
CREATE TABLE scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    week INTEGER,
    files_scraped INTEGER,
    api_requests_used INTEGER,
    status TEXT,
    error_message TEXT
);
```

**Purpose**: Monitor system health and API usage  
**Key Fields**: `week`, `files_scraped`, `api_requests_used`, `status`  
**Indexes**: `idx_scrape_runs_week`, `idx_scrape_runs_timestamp`

---

## Database Operations

### Initialization

```bash
# Initialize database with schema
python utils/db_manager.py --init

# Check database statistics
python utils/db_manager.py --stats
```

### Data Import

```bash
# Import specific CSV file
python utils/db_manager.py --import-csv data/raw/defense_stats_week_7.csv --table defense_stats --week 7

# Import QB stats (year-based)
python utils/db_manager.py --import-csv data/raw/qb_stats_2025.csv --table qb_stats --year 2025
```

### Query Operations

```bash
# Find weak defenses
python utils/query_tools.py --week 7 --weak-defenses --threshold 1.7

# Show QB props
python utils/query_tools.py --week 7 --qb-props

# Calculate edge opportunities
python utils/query_tools.py --week 7 --edges

# Export week data
python utils/query_tools.py --week 7 --export data/exports/
```

---

## Historical Storage

### Snapshot System

Historical snapshots provide timestamped backups for line movement analysis.

#### Directory Structure
```
data/historical/
├── 2025/
│   ├── week_7/
│   │   ├── defense_stats_20251021_090023_auto.csv
│   │   ├── defense_stats_20251021_090023_auto.json
│   │   ├── qb_stats_20251021_090023_auto.csv
│   │   ├── qb_stats_20251021_090023_auto.json
│   │   └── ...
│   └── week_8/
├── archives/
│   ├── 2025_week_7.zip
│   └── 2025_week_7.json
```

#### Snapshot Operations

```bash
# Save snapshot of specific file
python utils/historical_storage.py --snapshot data/raw/defense_stats_week_7.csv --week 7

# Save all snapshots for current week
python utils/historical_storage.py --snapshot-all --week 7

# Create ZIP archive
python utils/historical_storage.py --archive 7

# Show storage statistics
python utils/historical_storage.py --stats

# Clean up old files (30+ days)
python utils/historical_storage.py --cleanup 30
```

---

## Integration with Main Pipeline

### Command Line Options

The main pipeline now supports database and snapshot features:

```bash
# Run with database saves
python main.py --week 7 --save-to-db

# Run with historical snapshots
python main.py --week 7 --save-snapshots

# Run with both features
python main.py --week 7 --save-to-db --save-snapshots

# Stats-only workflow with database
python main.py --stats-only --save-to-db

# Odds-only workflow with snapshots
python main.py --odds-only --save-snapshots
```

### Automatic Integration

When `--save-to-db` is enabled:
1. Each scraper saves to CSV (existing behavior)
2. CSV data is automatically imported to database
3. Scrape run is logged to `scrape_runs` table
4. Database connections are properly cleaned up

When `--save-snapshots` is enabled:
1. Each CSV file gets timestamped snapshot
2. Metadata JSON files track snapshot details
3. Snapshots organized by year/week structure

---

## Query Examples

### Python API Usage

```python
from utils.query_tools import DatabaseQueryTools

# Context manager for automatic connection handling
with DatabaseQueryTools() as db:
    # Get weak defenses
    weak_defenses = db.get_weak_defenses(week=7, threshold=1.7)
    print(weak_defenses)
    
    # Get QB props
    qb_props = db.get_qb_props(week=7, sportsbook='FanDuel')
    print(qb_props)
    
    # Calculate edge opportunities
    edges = db.calculate_edge_opportunities(week=7)
    print(edges)
    
    # Get line movement data
    movement = db.get_line_movement(week=7, hours_back=24)
    print(movement['qb_props'])
```

### Common Queries

#### Find Best Edge Opportunities
```python
with DatabaseQueryTools() as db:
    edges = db.calculate_edge_opportunities(week=7)
    best_edges = edges[edges['edge'] > 0.05]  # 5%+ edge
    print(best_edges[['qb_name', 'team', 'opponent', 'edge', 'odds']])
```

#### Track Line Movement
```python
with DatabaseQueryTools() as db:
    movement = db.get_line_movement(week=7, hours_back=48)
    
    # Group by QB to see odds changes
    qb_movement = movement['qb_props'].groupby('qb_name')['odds_over_05_td'].agg(['min', 'max'])
    qb_movement['movement'] = qb_movement['max'] - qb_movement['min']
    print(qb_movement.sort_values('movement', ascending=False))
```

#### Compare Sportsbooks
```python
with DatabaseQueryTools() as db:
    qb_props = db.get_qb_props(week=7)
    
    # Pivot to compare DraftKings vs FanDuel
    comparison = qb_props.pivot_table(
        index='qb_name', 
        columns='sportsbook', 
        values='odds_over_05_td'
    )
    print(comparison)
```

---

## Performance Considerations

### Database Size
- **Typical Week**: ~500 rows across all tables
- **Full Season**: ~8,000 rows (16 weeks)
- **Database Size**: ~2-5 MB per season
- **Historical Snapshots**: ~50 MB per season

### Query Performance
- All tables have appropriate indexes
- Common queries (by week, by team) are optimized
- Context manager handles connection pooling
- Large exports use pandas for efficiency

### Storage Management
- Snapshots auto-cleanup after 30 days (configurable)
- Weekly archives compress old snapshots
- Database grows linearly with usage
- No performance degradation expected

---

## Backup and Recovery

### Database Backup
```bash
# Simple file copy (SQLite is single-file)
cp data/database/nfl_betting.db backups/nfl_betting_backup_$(date +%Y%m%d).db

# Export to CSV for portability
python utils/query_tools.py --week 7 --export backups/week_7_export/
```

### Historical Data Recovery
```bash
# Restore from archive
unzip data/historical/archives/2025_week_7.zip -d restored_data/

# Import restored CSV files
python utils/db_manager.py --import-csv restored_data/defense_stats_20251021_090023_auto.csv --table defense_stats --week 7
```

### Disaster Recovery
1. **Database Lost**: Re-run scrapers with `--save-to-db`
2. **Snapshots Lost**: Re-run with `--save-snapshots`
3. **Both Lost**: Full pipeline run with both flags

---

## Troubleshooting

### Common Issues

#### Database Not Found
```bash
# Error: Database not found
# Solution: Initialize database
python utils/db_manager.py --init
```

#### Import Errors
```bash
# Error: CSV import failed
# Check: CSV file exists and has correct format
ls -la data/raw/
head data/raw/defense_stats_week_7.csv
```

#### Connection Issues
```bash
# Error: Database locked
# Solution: Check for other processes using database
lsof data/database/nfl_betting.db
```

#### Query Performance
```bash
# Slow queries: Check indexes
python utils/db_manager.py --stats

# Rebuild indexes if needed
sqlite3 data/database/nfl_betting.db "REINDEX;"
```

### Monitoring

#### Check System Health
```bash
# Database statistics
python utils/db_manager.py --stats

# Recent scrape runs
python utils/query_tools.py --week 7 --export /tmp/check/

# Storage usage
python utils/historical_storage.py --stats
```

#### Log Analysis
```bash
# Check for database errors
grep -i "database\|error" scraper.log

# Monitor API usage
grep "API requests used" scraper.log | tail -10
```

---

## Migration from CSV-Only

### Phase 1 Adoption Strategy

1. **Gradual Migration**: Use `--save-to-db` flag alongside existing CSV workflow
2. **Validation**: Compare database queries with CSV data
3. **Full Adoption**: Enable database by default in Phase 2
4. **CSV Deprecation**: Remove CSV-only mode in Phase 3

### Migration Commands

```bash
# Migrate existing CSV data
python utils/db_manager.py --import-csv data/raw/defense_stats_week_7.csv --table defense_stats --week 7
python utils/db_manager.py --import-csv data/raw/qb_stats_2025.csv --table qb_stats --year 2025
python utils/db_manager.py --import-csv data/raw/matchups_week_7.csv --table matchups --week 7

# Validate migration
python utils/query_tools.py --week 7 --weak-defenses
```

---

## Future Enhancements (Phase 2+)

### Planned Features
- **Real-time Edge Detection**: Continuous monitoring of line movements
- **Alert System**: Email/SMS notifications for significant edges
- **Advanced Analytics**: Machine learning models for probability calculation
- **Web Dashboard**: Visual interface for database queries
- **API Endpoints**: REST API for external integrations

### Database Schema Evolution
- **Performance Tables**: Cached edge calculations
- **Alert History**: Track notification history
- **User Preferences**: Customizable alert thresholds
- **Market Analysis**: Historical edge performance tracking

---

## Support

### Getting Help
1. **Check Logs**: `tail -f scraper.log`
2. **Database Stats**: `python utils/db_manager.py --stats`
3. **Query Test**: `python utils/query_tools.py --week 7 --weak-defenses`
4. **Storage Check**: `python utils/historical_storage.py --stats`

### Common Commands Reference
```bash
# Database Management
python utils/db_manager.py --init                    # Initialize
python utils/db_manager.py --stats                   # Statistics
python utils/db_manager.py --import-csv file.csv --table table_name --week 7

# Query Operations  
python utils/query_tools.py --week 7 --weak-defenses
python utils/query_tools.py --week 7 --qb-props
python utils/query_tools.py --week 7 --edges
python utils/query_tools.py --week 7 --export dir/

# Historical Storage
python utils/historical_storage.py --snapshot-all --week 7
python utils/historical_storage.py --archive 7
python utils/historical_storage.py --stats
python utils/historical_storage.py --cleanup 30

# Main Pipeline with Database
python main.py --week 7 --save-to-db --save-snapshots
```

---

**Last Updated**: October 21, 2025  
**Version**: Phase 1.0  
**Next Phase**: Edge Calculator (Phase 2)
