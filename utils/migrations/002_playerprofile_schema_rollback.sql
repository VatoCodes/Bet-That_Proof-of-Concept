-- ============================================================================
-- PlayerProfiler Integration Schema Rollback
-- Version: 002
-- Date: 2025-10-22
-- Purpose: Rollback migration 002 by dropping all new tables
-- ============================================================================

-- WARNING: This will DELETE all PlayerProfiler data from the database
-- Historical snapshots in data/historical/ will be preserved

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS player_roster;
DROP TABLE IF EXISTS qb_stats_enhanced;
DROP TABLE IF EXISTS kicker_stats;
DROP TABLE IF EXISTS team_metrics;
DROP TABLE IF EXISTS play_by_play;

-- ============================================================================
-- Rollback Complete
-- ============================================================================
-- Tables dropped: 5
-- Indexes dropped: Automatically dropped with tables
-- Existing tables preserved: defense_stats, qb_stats, matchups, odds_spreads, odds_totals, qb_props
-- ============================================================================
