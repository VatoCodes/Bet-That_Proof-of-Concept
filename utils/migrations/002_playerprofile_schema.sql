-- ============================================================================
-- PlayerProfiler Integration Schema Migration
-- Version: 002
-- Date: 2025-10-22
-- Purpose: Add 5 new tables for First Half Totals, Kicker Points, and QB TD v2
-- ============================================================================

-- ============================================
-- PLAY-BY-PLAY DATA (AGGREGATED, NOT RAW)
-- ============================================
-- Store play-level data for granular analysis
-- DO NOT store all 100K+ rows - aggregate first, then store derived metrics
-- Use this table for: calculating yards per play, first half scoring, situational stats

CREATE TABLE IF NOT EXISTS play_by_play (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    play_id TEXT UNIQUE NOT NULL,          -- Unique play identifier (game_key + play_number)
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    game_key TEXT NOT NULL,                -- Links plays to specific games
    quarter INTEGER NOT NULL,              -- 1-4 (5 for OT)
    offense TEXT NOT NULL,                 -- Team with possession
    defense TEXT NOT NULL,                 -- Team defending
    play_type TEXT,                        -- 'Pass', 'Run', 'Field Goal', 'Punt', etc.
    yards_gained INTEGER,                  -- Result of play (-20 to +99)
    down INTEGER,                          -- 1-4
    to_go INTEGER,                         -- Yards to first down
    yards_to_endzone INTEGER,              -- Field position context

    -- QB-specific columns (NULL if not a pass play)
    qb_name TEXT,
    pass_location TEXT,                    -- 'Left', 'Middle', 'Right'
    pass_depth TEXT,                       -- 'Behind LOS', 'Short', 'Deep'
    accurate_throw BOOLEAN,                -- TRUE if catchable
    clean_pocket BOOLEAN,                  -- TRUE if no pressure
    under_pressure BOOLEAN,                -- TRUE if QB hit/hurried

    -- Run-specific columns (NULL if not a run play)
    rusher_name TEXT,
    run_location TEXT,                     -- 'Left', 'Middle', 'Right'
    defenders_in_box INTEGER,              -- 6-9 typically

    -- Game situation
    shotgun BOOLEAN,                       -- Formation
    play_action BOOLEAN,                   -- Fake handoff
    red_zone_play BOOLEAN,                 -- Within 20 yards of endzone

    -- Result flags
    is_touchdown BOOLEAN,                  -- Any TD (pass, run, return)
    is_first_down BOOLEAN,                 -- Converted 1st down
    is_turnover BOOLEAN,                   -- INT or fumble lost

    -- Betting context
    spread REAL,                           -- Point spread at game time
    over_under REAL,                       -- Total line at game time

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pbp_offense_season_week ON play_by_play (offense, season, week);
CREATE INDEX idx_pbp_defense_season_week ON play_by_play (defense, season, week);
CREATE INDEX idx_pbp_game_key ON play_by_play (game_key);
CREATE INDEX idx_pbp_quarter ON play_by_play (quarter);              -- For first half filtering
CREATE INDEX idx_pbp_qb_name ON play_by_play (qb_name);              -- For QB analysis
CREATE INDEX idx_pbp_play_type ON play_by_play (play_type);          -- For type-specific aggregation

-- ============================================
-- TEAM METRICS (CALCULATED FROM PLAY-BY-PLAY)
-- ============================================
-- Pre-calculated team performance metrics (refresh weekly)
-- This is a MATERIALIZED VIEW pattern adapted to SQLite
-- Use this table for: First Half Total edge detection, team rankings

CREATE TABLE IF NOT EXISTS team_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,                 -- Metrics calculated through this week

    -- Offensive metrics (calculated from offense = team_name plays)
    offensive_plays INTEGER DEFAULT 0,
    offensive_yards INTEGER DEFAULT 0,
    offensive_yards_per_play REAL,         -- KEY METRIC for First Half Totals
    offensive_first_downs INTEGER DEFAULT 0,
    offensive_touchdowns INTEGER DEFAULT 0,

    -- First half specific (critical for strategy)
    first_half_points_avg REAL,            -- Average points scored in quarters 1+2
    first_half_yards_avg REAL,             -- Average yards in first half
    first_half_scoring_plays INTEGER DEFAULT 0,  -- TD + FG count in first half

    -- Red zone efficiency
    red_zone_attempts INTEGER DEFAULT 0,   -- Plays inside opponent 20
    red_zone_touchdowns INTEGER DEFAULT 0,
    red_zone_efficiency_pct REAL,          -- TDs / attempts

    -- Defensive metrics (calculated from defense = team_name plays)
    defensive_plays INTEGER DEFAULT 0,
    defensive_yards_allowed INTEGER DEFAULT 0,
    defensive_yards_per_play REAL,         -- KEY METRIC for First Half Totals
    defensive_touchdowns_allowed INTEGER DEFAULT 0,
    defensive_first_downs_allowed INTEGER DEFAULT 0,

    -- Special teams (kicker related)
    fg_attempts INTEGER DEFAULT 0,
    fg_made INTEGER DEFAULT 0,
    fg_pct REAL,
    kicker_points_avg REAL,                -- Average kicker points per game
    fg_blocks_allowed INTEGER DEFAULT 0,   -- Blocked field goals (defensive metric)

    -- Calculated rankings (percentile within week, 0-100)
    offensive_ypp_percentile INTEGER,      -- Used for First Half edge: need bottom 5-8
    defensive_ypp_percentile INTEGER,      -- Used for First Half edge: need top 5-8

    UNIQUE(team_name, season, week)
);

CREATE INDEX idx_team_metrics_season_week ON team_metrics (season, week);
CREATE INDEX idx_team_metrics_team ON team_metrics (team_name);
CREATE INDEX idx_team_metrics_off_ypp ON team_metrics (offensive_yards_per_play);    -- For ranking
CREATE INDEX idx_team_metrics_def_ypp ON team_metrics (defensive_yards_per_play);    -- For ranking

-- ============================================
-- KICKER STATS (FROM CUSTOM REPORTS)
-- ============================================
-- Season-aggregated kicker performance
-- Use this table for: Kicker Points prop edge detection

CREATE TABLE IF NOT EXISTS kicker_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kicker_name TEXT NOT NULL,
    team TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Core kicker metrics
    fg_attempts INTEGER DEFAULT 0,
    fg_made INTEGER DEFAULT 0,
    fg_pct REAL,                           -- Made / Attempts
    long_fg INTEGER,                       -- Longest successful FG

    -- Scoring
    points_total INTEGER DEFAULT 0,        -- Fantasy points = FG*3 + XP*1
    points_per_game REAL,                  -- KEY METRIC for props

    -- Volume
    attempts_per_game REAL,                -- Indicates high-scoring offense
    games_played INTEGER DEFAULT 0,

    -- Calculated rankings
    fg_pct_percentile INTEGER,             -- 0-100, higher = better accuracy
    points_per_game_percentile INTEGER,    -- 0-100, higher = more volume

    UNIQUE(kicker_name, team, season)
);

CREATE INDEX idx_kicker_team_season ON kicker_stats (team, season);
CREATE INDEX idx_kicker_ppg ON kicker_stats (points_per_game);                       -- For ranking

-- ============================================
-- QB STATS ENHANCED (FROM CUSTOM REPORTS + PLAY-BY-PLAY)
-- ============================================
-- Advanced QB metrics beyond basic passing stats
-- Extends existing qb_stats table with PlayerProfiler metrics
-- Use this table for: Enhanced QB TD prop edge detection (v2 calculator)

CREATE TABLE IF NOT EXISTS qb_stats_enhanced (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qb_name TEXT NOT NULL,
    team TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Basic stats (from Custom Reports)
    games_played INTEGER DEFAULT 0,
    total_pass_attempts INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    total_pass_yards INTEGER DEFAULT 0,
    total_pass_tds INTEGER DEFAULT 0,
    passing_tds_per_game REAL,             -- Still useful baseline

    -- Advanced accuracy metrics (PlayerProfiler exclusives)
    red_zone_accuracy_rating REAL,         -- KEY: Predicts TD likelihood better than season TDs
    deep_ball_completion_pct REAL,         -- 20+ yard passes
    clean_pocket_accuracy REAL,            -- Completion % when not pressured
    pressured_completion_pct REAL,         -- Under duress
    avg_depth_of_target REAL,              -- Aggression metric

    -- Situational splits (from Play-by-Play aggregation)
    first_half_tds INTEGER DEFAULT 0,      -- TDs in quarters 1-2
    first_half_td_rate REAL,               -- TDs per first half game
    third_down_conversion_pct REAL,
    fourth_quarter_tds INTEGER DEFAULT 0,  -- Clutch metric

    -- Opponent-adjusted metrics
    td_rate_vs_top10_defenses REAL,        -- Performance against tough defenses
    td_rate_vs_bottom10_defenses REAL,     -- Exploit weak defenses

    UNIQUE(qb_name, team, season)
);

CREATE INDEX idx_qb_enhanced_team_season ON qb_stats_enhanced (team, season);
CREATE INDEX idx_qb_enhanced_name ON qb_stats_enhanced (qb_name);
CREATE INDEX idx_qb_enhanced_red_zone ON qb_stats_enhanced (red_zone_accuracy_rating);  -- For v2 calculator

-- ============================================
-- PLAYER ROSTER (FROM WEEKLY ROSTER KEY)
-- ============================================
-- Player availability and position tracking by week
-- This is a JOIN TABLE - use it to filter all queries
-- Use this table for: Ensuring players were active in target week, tracking position changes

CREATE TABLE IF NOT EXISTS player_roster (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,                        -- PlayerProfiler ID (may be NULL in older data)
    player_name TEXT NOT NULL,
    position TEXT NOT NULL,                -- QB, RB, WR, TE, K, DEF
    team TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    status TEXT NOT NULL,                  -- 'Active', 'Inactive', 'IR', 'PUP', 'Suspended'

    UNIQUE(player_name, team, season, week)
);

CREATE INDEX idx_roster_player_season_week ON player_roster (player_name, season, week);
CREATE INDEX idx_roster_team_season_week ON player_roster (team, season, week);
CREATE INDEX idx_roster_status ON player_roster (status);                             -- For active filtering
CREATE INDEX idx_roster_position ON player_roster (position);                         -- For position filtering

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- Tables created: 5
-- Indexes created: 20
-- Expected impact: No changes to existing tables
-- Rollback: See 002_playerprofile_schema_rollback.sql
-- ============================================================================
