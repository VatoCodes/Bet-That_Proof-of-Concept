# Scraper Best Practices

## Overview

This document outlines best practices for writing scrapers in the NFL Edge Finder system, with a focus on idempotency and data quality.

## Core Principles

### 1. Idempotency

**Definition:** Running a scraper multiple times should produce the same result as running it once.

**Why Important:**
- Prevents duplicate data in operational database
- Allows safe re-running of scrapers for debugging
- Enables automated scheduling without data corruption

**Implementation Pattern: Snapshot-Then-Upsert**

```python
def save_to_database(self, df: pd.DataFrame, week: int) -> bool:
    """Save data using snapshot-then-upsert pattern"""
    
    # 1. Save CSV snapshot to historical storage FIRST
    csv_path = self.save_to_csv(df, week)
    historical = HistoricalStorage()
    snapshot_path = historical.save_snapshot(csv_path, week, snapshot_type='auto')
    
    # 2. Upsert to operational database (DELETE old + INSERT new)
    from utils.db_manager import DatabaseManager
    
    db = DatabaseManager()
    db.connect()
    
    try:
        rows_inserted = db.insert_dataframe('table_name', df, week=week)
        db.conn.commit()
        
        logger.info(f"✅ Upserted {rows_inserted} records to database")
        logger.info(f"📸 Historical snapshot saved to {snapshot_path}")
        
        return True
        
    except Exception as e:
        db.conn.rollback()
        logger.error(f"❌ Database upsert failed: {e}")
        return False
    finally:
        db.close()
```

### 2. Two-Tier Storage Architecture

**Operational Database (`data/database/nfl_betting.db`)**
- Purpose: Current state for live queries
- Characteristics: One record per entity, fast queries
- UNIQUE constraints on natural keys (not timestamps)

**Historical Snapshots (`data/historical/{year}/week_{week}/`)**
- Purpose: Complete audit trail of all scrapes
- Characteristics: Timestamped CSV files, preserves all data
- Used for analysis, debugging, rollback

### 3. Natural Key Design

**Correct UNIQUE Constraints:**
```sql
-- Defense stats: one CURRENT record per (team, week)
CREATE UNIQUE INDEX idx_defense_stats_unique 
ON defense_stats(team_name, week);

-- Matchups: one CURRENT record per game
CREATE UNIQUE INDEX idx_matchups_unique 
ON matchups(home_team, away_team, week);

-- QB props: one CURRENT record per (qb, week, sportsbook)
CREATE UNIQUE INDEX idx_qb_props_unique 
ON qb_props(qb_name, week, sportsbook);
```

**Incorrect (causes duplicates):**
```sql
-- WRONG: Includes scraped_at timestamp
UNIQUE(team_name, week, scraped_at)
```

## Scraper Implementation Guide

### Step 1: Basic Scraper Structure

```python
class ExampleScraper:
    """Scrapes data from external source"""
    
    def __init__(self, year: int = CURRENT_YEAR):
        self.year = year
        self.url = URL_TEMPLATE.format(year=year)
        self.headers = {"User-Agent": USER_AGENT}
    
    def scrape(self) -> Optional[pd.DataFrame]:
        """Scrape data from external source"""
        # Implementation here
        pass
    
    def save_to_csv(self, df: pd.DataFrame, week: int) -> str:
        """Save DataFrame to CSV file"""
        # Implementation here
        pass
    
    def run(self, week: int, save_to_db: bool = False) -> Optional[str]:
        """Run complete scraping workflow"""
        df = self.scrape()
        
        if df is not None and not df.empty:
            if save_to_db:
                success = self.save_to_database(df, week)
                return self.save_to_csv(df, week) if success else None
            else:
                return self.save_to_csv(df, week)
        else:
            logger.error("Failed to scrape data")
            return None
```

### Step 2: Add Database Integration

```python
def save_to_database(self, df: pd.DataFrame, week: int) -> bool:
    """Save data using snapshot-then-upsert pattern"""
    try:
        # 1. Save CSV snapshot FIRST
        csv_path = self.save_to_csv(df, week)
        historical = HistoricalStorage()
        snapshot_path = historical.save_snapshot(csv_path, week, snapshot_type='auto')
        
        if not snapshot_path:
            logger.error("Failed to save historical snapshot")
            return False
        
        # 2. Upsert to operational database
        from utils.db_manager import DatabaseManager
        
        db = DatabaseManager()
        db.connect()
        
        try:
            rows_inserted = db.insert_dataframe('table_name', df, week=week)
            db.conn.commit()
            
            logger.info(f"✅ Upserted {rows_inserted} records to database")
            logger.info(f"📸 Historical snapshot saved to {snapshot_path}")
            
            return True
            
        except Exception as e:
            db.conn.rollback()
            logger.error(f"❌ Database upsert failed: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error in save_to_database: {e}")
        return False
```

### Step 3: Error Handling

```python
def scrape(self) -> Optional[pd.DataFrame]:
    """Scrape data with proper error handling"""
    try:
        response = requests.get(self.url, headers=self.headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Parse data
        df = self.parse_response(response)
        
        # Validate data
        if not self.validate_data(df):
            logger.error("Data validation failed")
            return None
        
        return df
        
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### Step 4: Data Validation

```python
def validate_data(self, df: pd.DataFrame) -> bool:
    """Validate scraped data"""
    if df.empty:
        logger.error("DataFrame is empty")
        return False
    
    # Check required columns
    required_columns = ['team_name', 'week']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"Missing required columns: {missing_columns}")
        return False
    
    # Check data types
    if not df['team_name'].dtype == 'object':
        logger.error("team_name should be string type")
        return False
    
    # Check for reasonable data ranges
    if 'pass_tds_allowed' in df.columns:
        if df['pass_tds_allowed'].min() < 0 or df['pass_tds_allowed'].max() > 100:
            logger.warning("pass_tds_allowed values seem unreasonable")
    
    return True
```

## Testing Scrapers

### Unit Tests

```python
def test_scraper_idempotency():
    """Test that running scraper multiple times produces same result"""
    scraper = ExampleScraper()
    
    # Run scraper 3 times
    result1 = scraper.run(7, save_to_db=True)
    result2 = scraper.run(7, save_to_db=True)
    result3 = scraper.run(7, save_to_db=True)
    
    # Verify: database has correct number of records
    db = DatabaseManager()
    db.connect()
    count = db.cursor.execute("SELECT COUNT(*) FROM table_name WHERE week = 7").fetchone()[0]
    assert count == 32  # Expected number of unique records
    
    # Verify: historical snapshots exist
    snapshots = list(Path("data/historical/2025/week_7").glob("table_name_*.csv"))
    assert len(snapshots) >= 3  # At least 3 snapshots
```

### Integration Tests

```python
def test_no_duplicates_in_operational_db():
    """Operational database should have no duplicates"""
    db = DatabaseManager()
    db.connect()
    
    # Check for duplicates
    duplicates = db.cursor.execute("""
        SELECT team_name, COUNT(*) as count
        FROM defense_stats
        WHERE week = 7
        GROUP BY team_name
        HAVING COUNT(*) > 1
    """).fetchall()
    
    assert len(duplicates) == 0, f"Found duplicates: {duplicates}"
```

## Common Pitfalls

### 1. Including Timestamps in UNIQUE Constraints

**Wrong:**
```sql
UNIQUE(team_name, week, scraped_at)
```

**Right:**
```sql
UNIQUE(team_name, week)
```

### 2. Not Saving Historical Snapshots First

**Wrong:**
```python
# Save to database first
db.insert_dataframe('table', df)
# Then save CSV
df.to_csv('file.csv')
```

**Right:**
```python
# Save CSV snapshot first
csv_path = self.save_to_csv(df, week)
historical.save_snapshot(csv_path, week)
# Then upsert to database
db.insert_dataframe('table', df, week=week)
```

### 3. Not Handling Database Transactions

**Wrong:**
```python
db.insert_dataframe('table', df)
# If this fails, database is left in inconsistent state
```

**Right:**
```python
try:
    db.insert_dataframe('table', df)
    db.conn.commit()
except Exception as e:
    db.conn.rollback()
    raise
```

## Performance Considerations

### 1. Batch Operations

```python
# Good: Batch insert
df.to_sql('table_name', conn, if_exists='append', index=False)

# Bad: Individual inserts
for _, row in df.iterrows():
    cursor.execute("INSERT INTO table_name VALUES (?, ?)", row.values)
```

### 2. Connection Management

```python
# Good: Use context manager
with DatabaseManager() as db:
    db.insert_dataframe('table', df)

# Bad: Manual connection management
conn = sqlite3.connect('db.db')
# ... operations ...
conn.close()  # Might be forgotten
```

### 3. Memory Management

```python
# Good: Process data in chunks for large datasets
def process_large_dataset(self, df: pd.DataFrame):
    chunk_size = 1000
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        self.process_chunk(chunk)
```

## Monitoring and Logging

### 1. Structured Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use structured log messages
logger.info(f"✅ Upserted {rows_inserted} records to {table_name}")
logger.error(f"❌ Database upsert failed: {e}")
logger.warning(f"⚠️ Data validation warning: {warning}")
```

### 2. Performance Metrics

```python
import time

def scrape(self) -> Optional[pd.DataFrame]:
    start_time = time.time()
    
    # ... scraping logic ...
    
    duration = time.time() - start_time
    logger.info(f"Scraping completed in {duration:.2f} seconds")
    
    return df
```

### 3. Data Quality Metrics

```python
def log_data_quality_metrics(self, df: pd.DataFrame):
    """Log data quality metrics"""
    logger.info(f"Scraped {len(df)} records")
    logger.info(f"Columns: {list(df.columns)}")
    logger.info(f"Data types: {df.dtypes.to_dict()}")
    
    # Check for missing values
    missing_counts = df.isnull().sum()
    if missing_counts.any():
        logger.warning(f"Missing values: {missing_counts[missing_counts > 0].to_dict()}")
```

## Conclusion

Following these best practices ensures:

1. **Data Integrity:** No duplicates, consistent data quality
2. **Reliability:** Scrapers can be safely re-run
3. **Auditability:** Complete historical record preserved
4. **Maintainability:** Clear patterns, good error handling
5. **Performance:** Efficient database operations

Remember: **Snapshot first, then upsert.**
