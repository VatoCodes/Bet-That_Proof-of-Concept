#!/usr/bin/env python3
"""
Duplicate Cleanup Script for NFL Edge Finder

Removes duplicate records from operational database while preserving
historical CSV snapshots. Keeps the most recent record per natural key.

Usage:
    python3 scripts/cleanup_duplicates.py --table defense_stats --week 7 --dry-run
    python3 scripts/cleanup_duplicates.py --table defense_stats --week 7 --execute
    python3 scripts/cleanup_duplicates.py --all-tables --week 7 --execute
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_database_path

logger = logging.getLogger(__name__)


class DuplicateCleaner:
    """Cleans duplicate records from operational database"""
    
    def __init__(self, db_path=None):
        """Initialize cleaner
        
        Args:
            db_path: Path to database file (defaults to config setting)
        """
        self.db_path = db_path or get_database_path()
        self.conn = None
        self.cursor = None
        
        # Define natural keys for each table
        self.natural_keys = {
            'defense_stats': ['team_name', 'week'],
            'matchups': ['home_team', 'away_team', 'week'],
            'qb_props': ['qb_name', 'week', 'sportsbook'],
            # odds tables don't have unique constraints (multiple sportsbooks)
        }
    
    def connect(self):
        """Establish database connection"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        logger.info(f"✅ Connected to database: {self.db_path}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def get_duplicates(self, table_name, week=None):
        """Get duplicate records for a table
        
        Args:
            table_name: Name of table to check
            week: Week to check (checks all if None)
            
        Returns:
            List of duplicate records
        """
        if table_name not in self.natural_keys:
            logger.warning(f"⚠️  No natural key defined for table: {table_name}")
            return []
        
        keys = self.natural_keys[table_name]
        
        # Build query to find duplicates
        select_clause = ', '.join(keys + ['COUNT(*) as count', 'MAX(scraped_at) as latest'])
        group_clause = ', '.join(keys)
        
        query = f"""
            SELECT {select_clause}
            FROM {table_name}
        """
        
        params = []
        if week is not None and 'week' in keys:
            query += " WHERE week = ?"
            params.append(week)
        
        query += f" GROUP BY {group_clause} HAVING COUNT(*) > 1 ORDER BY count DESC"
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_duplicate_details(self, table_name, week=None):
        """Get detailed information about duplicates
        
        Args:
            table_name: Name of table to check
            week: Week to check (checks all if None)
            
        Returns:
            Dict with duplicate information
        """
        if table_name not in self.natural_keys:
            return {'duplicates': [], 'total_records': 0, 'unique_records': 0}
        
        keys = self.natural_keys[table_name]
        
        # Get total records
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        params = []
        if week is not None and 'week' in keys:
            count_query += " WHERE week = ?"
            params.append(week)
        
        self.cursor.execute(count_query, params)
        total_records = self.cursor.fetchone()[0]
        
        # Get unique records - use subquery for multiple columns
        if len(keys) == 1:
            unique_query = f"SELECT COUNT(DISTINCT {keys[0]}) FROM {table_name}"
        else:
            unique_query = f"SELECT COUNT(*) FROM (SELECT DISTINCT {', '.join(keys)} FROM {table_name}"
            if week is not None and 'week' in keys:
                unique_query += " WHERE week = ?"
            unique_query += ")"
        
        self.cursor.execute(unique_query, params)
        unique_records = self.cursor.fetchone()[0]
        
        # Get duplicate groups
        duplicates = self.get_duplicates(table_name, week)
        
        return {
            'duplicates': duplicates,
            'total_records': total_records,
            'unique_records': unique_records,
            'duplicate_count': total_records - unique_records
        }
    
    def clean_table(self, table_name, week=None, dry_run=True):
        """Clean duplicates from a table
        
        Args:
            table_name: Name of table to clean
            week: Week to clean (cleans all if None)
            dry_run: If True, only show what would be deleted
            
        Returns:
            Dict with cleanup results
        """
        if table_name not in self.natural_keys:
            logger.warning(f"⚠️  Skipping {table_name} - no natural key defined")
            return {'deleted': 0, 'kept': 0, 'errors': []}
        
        keys = self.natural_keys[table_name]
        
        # Get duplicates
        duplicates = self.get_duplicates(table_name, week)
        
        if not duplicates:
            logger.info(f"✅ No duplicates found in {table_name}")
            return {'deleted': 0, 'kept': 0, 'errors': []}
        
        deleted_count = 0
        kept_count = 0
        errors = []
        
        logger.info(f"🔍 Found {len(duplicates)} duplicate groups in {table_name}")
        
        for duplicate_group in duplicates:
            # Extract natural key values
            key_values = duplicate_group[:-2]  # Exclude count and latest
            count = duplicate_group[-2]
            latest_scraped_at = duplicate_group[-1]
            
            # Build WHERE clause for deletion
            where_clause = ' AND '.join([f"{key} = ?" for key in keys])
            where_clause += " AND scraped_at < ?"
            
            # Count records to be deleted
            count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
            self.cursor.execute(count_query, tuple(key_values) + (latest_scraped_at,))
            records_to_delete = self.cursor.fetchone()[0]
            
            if dry_run:
                logger.info(f"   Would delete {records_to_delete} old records for {dict(zip(keys, key_values))}")
                deleted_count += records_to_delete
                kept_count += 1
            else:
                try:
                    # Delete old records
                    delete_query = f"DELETE FROM {table_name} WHERE {where_clause}"
                    self.cursor.execute(delete_query, tuple(key_values) + (latest_scraped_at,))
                    
                    deleted_count += self.cursor.rowcount
                    kept_count += 1
                    
                    logger.info(f"   ✅ Deleted {self.cursor.rowcount} old records for {dict(zip(keys, key_values))}")
                    
                except Exception as e:
                    error_msg = f"Error deleting duplicates for {dict(zip(keys, key_values))}: {e}"
                    logger.error(f"   ❌ {error_msg}")
                    errors.append(error_msg)
        
        if not dry_run:
            self.conn.commit()
        
        return {
            'deleted': deleted_count,
            'kept': kept_count,
            'errors': errors
        }
    
    def clean_all_tables(self, week=None, dry_run=True):
        """Clean duplicates from all tables
        
        Args:
            week: Week to clean (cleans all if None)
            dry_run: If True, only show what would be deleted
            
        Returns:
            Dict with cleanup results for all tables
        """
        results = {}
        
        for table_name in self.natural_keys.keys():
            logger.info(f"\n{'='*60}")
            logger.info(f"Cleaning {table_name}")
            logger.info(f"{'='*60}")
            
            # Get before stats
            before_stats = self.get_duplicate_details(table_name, week)
            logger.info(f"Before: {before_stats['total_records']} total, {before_stats['unique_records']} unique")
            
            if before_stats['duplicate_count'] > 0:
                # Clean duplicates
                cleanup_result = self.clean_table(table_name, week, dry_run)
                results[table_name] = cleanup_result
                
                # Get after stats
                after_stats = self.get_duplicate_details(table_name, week)
                logger.info(f"After:  {after_stats['total_records']} total, {after_stats['unique_records']} unique")
                
                if cleanup_result['errors']:
                    logger.warning(f"⚠️  {len(cleanup_result['errors'])} errors occurred")
            else:
                logger.info("✅ No duplicates to clean")
                results[table_name] = {'deleted': 0, 'kept': 0, 'errors': []}
        
        return results


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='Clean duplicate records from NFL Edge Finder database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/cleanup_duplicates.py --table defense_stats --week 7 --dry-run
  python3 scripts/cleanup_duplicates.py --table defense_stats --week 7 --execute
  python3 scripts/cleanup_duplicates.py --all-tables --week 7 --execute
        """
    )
    
    parser.add_argument('--table', help='Specific table to clean')
    parser.add_argument('--all-tables', action='store_true', help='Clean all tables')
    parser.add_argument('--week', type=int, help='Week to clean (cleans all if not specified)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted (default)')
    parser.add_argument('--execute', action='store_true', help='Actually delete duplicates')
    parser.add_argument('--db-path', help='Path to database file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Validate arguments
    if not args.table and not args.all_tables:
        parser.error("Must specify either --table or --all-tables")
    
    if args.execute and args.dry_run:
        parser.error("Cannot specify both --execute and --dry-run")
    
    # Default to dry-run if neither is specified
    if not args.execute and not args.dry_run:
        args.dry_run = True
    
    try:
        # Initialize cleaner
        cleaner = DuplicateCleaner(db_path=args.db_path)
        cleaner.connect()
        
        print("\n" + "="*60)
        print("NFL EDGE FINDER - DUPLICATE CLEANUP")
        print("="*60)
        print(f"Database: {cleaner.db_path}")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
        if args.week:
            print(f"Week: {args.week}")
        print("="*60)
        
        if args.table:
            # Clean specific table
            logger.info(f"Cleaning table: {args.table}")
            results = cleaner.clean_table(args.table, args.week, args.dry_run)
            
            print(f"\nResults for {args.table}:")
            print(f"  Records deleted: {results['deleted']}")
            print(f"  Groups kept: {results['kept']}")
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")
                for error in results['errors']:
                    print(f"    - {error}")
        
        elif args.all_tables:
            # Clean all tables
            logger.info("Cleaning all tables")
            results = cleaner.clean_all_tables(args.week, args.dry_run)
            
            print(f"\nSummary:")
            total_deleted = sum(r['deleted'] for r in results.values())
            total_errors = sum(len(r['errors']) for r in results.values())
            
            print(f"  Total records deleted: {total_deleted}")
            print(f"  Total errors: {total_errors}")
            
            for table_name, result in results.items():
                if result['deleted'] > 0 or result['errors']:
                    print(f"  {table_name}: {result['deleted']} deleted, {len(result['errors'])} errors")
        
        print("\n" + "="*60)
        if args.dry_run:
            print("✅ DRY RUN COMPLETE - No changes made")
            print("💡 Use --execute to actually delete duplicates")
        else:
            print("✅ CLEANUP COMPLETE - Duplicates removed")
            print("💡 Historical CSV snapshots preserved")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1
    
    finally:
        if 'cleaner' in locals():
            cleaner.close()


if __name__ == '__main__':
    exit(main())
