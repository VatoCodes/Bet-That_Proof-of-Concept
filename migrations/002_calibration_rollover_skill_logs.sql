-- Migration 002: Add calibration, rollover, and skill execution logs
-- Date: 2025-10-22
-- Purpose: Support Phase 2 skills with required history/log tables

-- Table: calibration_history
CREATE TABLE IF NOT EXISTS calibration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    params_json TEXT,
    recommendations_json TEXT,
    applied INTEGER DEFAULT 0,
    notes TEXT
);

-- Table: rollover_history
CREATE TABLE IF NOT EXISTS rollover_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    from_week INTEGER,
    to_week INTEGER,
    backup_path TEXT,
    status TEXT,
    details_json TEXT
);

-- Table: skill_execution_log
CREATE TABLE IF NOT EXISTS skill_execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    skill_id TEXT,
    operation TEXT,
    params_json TEXT,
    status TEXT,
    message TEXT
);

-- Indexes for quick querying
CREATE INDEX IF NOT EXISTS idx_calibration_history_run_ts ON calibration_history(run_ts);
CREATE INDEX IF NOT EXISTS idx_rollover_history_run_ts ON rollover_history(run_ts);
CREATE INDEX IF NOT EXISTS idx_skill_execution_log_ts ON skill_execution_log(ts);

