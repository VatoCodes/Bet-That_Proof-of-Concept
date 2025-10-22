# pipeline_health_monitor

**Purpose:** Validate data pipeline health across scrapers, dedupe, migrations, and historical snapshots. Produce a concise health summary with severity and recommended fixes.

## Triggers
- Scheduled: hourly during active hours
- Manual: on-demand health check

## Inputs
- `data/scheduler.log`, `data/scraper.log`
- Database at `data/database/nfl_betting.db`
- Historical snapshots under `data/historical/`

## Operations
- `check_freshness`: Verify latest files and DB tables updated within expected windows
- `check_integrity`: Run validations via `utils/scheduled_validator.py` and `utils/data_validator.py`
- `summarize_health`: Aggregate results into OK/WARN/ERROR status with actions

## Outputs
- JSON health report with per-check status and remediation steps
- Optional: write summary to `SYSTEM_STATUS.md`

## KPIs
- Coverage of checks > 90%
- False alarms < 10%
- Runtime < 10s


