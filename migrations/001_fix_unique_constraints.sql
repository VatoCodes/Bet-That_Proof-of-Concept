-- Migration 001: Fix UNIQUE Constraints for Duplicate Prevention
-- Date: 2025-10-21
-- Purpose: Prevent duplicate records in operational database by enforcing natural keys

-- Defense stats: one CURRENT record per (team, week)
-- Remove the old constraint that included scraped_at (which allowed duplicates)
DROP INDEX IF EXISTS sqlite_autoindex_defense_stats_1;

-- Create new UNIQUE constraint on natural key only
CREATE UNIQUE INDEX idx_defense_stats_unique 
ON defense_stats(team_name, week);

-- Matchups: one CURRENT record per game
-- Remove the old constraint that included scraped_at
DROP INDEX IF EXISTS sqlite_autoindex_matchups_1;

-- Create new UNIQUE constraint on natural key only
CREATE UNIQUE INDEX idx_matchups_unique 
ON matchups(home_team, away_team, week);

-- QB props: one CURRENT record per (qb, week, sportsbook)
-- This table didn't have a UNIQUE constraint before, so we're adding one
CREATE UNIQUE INDEX IF NOT EXISTS idx_qb_props_unique 
ON qb_props(qb_name, week, sportsbook);

-- Note: scraped_at still exists for auditing purposes, but is NOT part of UNIQUE constraint
-- This allows us to track when data was last updated while preventing duplicates

-- Verify constraints were created
SELECT 
    name, 
    sql 
FROM sqlite_master 
WHERE type = 'index' 
  AND name LIKE 'idx_%_unique'
ORDER BY name;
