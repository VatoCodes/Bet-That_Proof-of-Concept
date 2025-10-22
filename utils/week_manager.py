#!/usr/bin/env python3
"""
Week Manager - Single Source of Truth for NFL Week Tracking

This module manages the current NFL week across all scrapers and prevents
data synchronization issues. It provides:
- Manual week override via current_week.json
- Automatic week detection from NFL season dates
- Week validation and status tracking
- CLI interface for week management

Usage:
    from utils.week_manager import WeekManager

    wm = WeekManager()
    current_week = wm.get_current_week()

Command Line:
    python utils/week_manager.py                    # Show current week
    python utils/week_manager.py --set-week 8       # Set week manually
    python utils/week_manager.py --advance          # Move to next week
    python utils/week_manager.py --validate         # Check data consistency
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class WeekManager:
    """Manages NFL week tracking and data synchronization"""

    # NFL 2025 season configuration
    SEASON_YEAR = 2025
    SEASON_START = datetime(2025, 9, 5)  # Week 1 starts Sept 5, 2025
    REGULAR_SEASON_WEEKS = 18

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the week manager

        Args:
            config_path: Path to current_week.json (default: project root)
        """
        if config_path is None:
            self.config_path = Path(__file__).parent.parent / "current_week.json"
        else:
            self.config_path = config_path

        self.data_dir = Path(__file__).parent.parent / "data" / "raw"

    def get_current_week(self) -> int:
        """
        Get the current NFL week number

        Priority:
        1. Check current_week.json (manual override)
        2. Calculate from season start date

        Returns:
            Current NFL week number (1-18)
        """
        # Try to load from config file first
        config = self._load_config()
        if config and 'current_week' in config:
            week = config['current_week']
            logger.info(f"Week loaded from config: {week}")
            return week

        # Fall back to date-based calculation
        week = self._calculate_week_from_date()
        logger.info(f"Week calculated from date: {week}")
        return week

    def get_week_info(self) -> Dict:
        """
        Get detailed information about the current week

        Returns:
            Dictionary with week metadata
        """
        config = self._load_config()

        if config:
            return config

        # Generate info from date calculation
        week = self._calculate_week_from_date()
        start_date, end_date = self._get_week_dates(week)

        return {
            'current_week': week,
            'season_year': self.SEASON_YEAR,
            'week_start_date': start_date.strftime('%Y-%m-%d'),
            'week_end_date': end_date.strftime('%Y-%m-%d'),
            'status': self._get_week_status(start_date, end_date),
            'last_updated': datetime.now().isoformat(),
            'source': 'auto_calculated'
        }

    def set_week(self, week: int, status: str = 'in_progress') -> bool:
        """
        Manually set the current week

        Args:
            week: NFL week number (1-18)
            status: Week status ('upcoming', 'in_progress', 'completed')

        Returns:
            True if successful
        """
        if not 1 <= week <= self.REGULAR_SEASON_WEEKS:
            logger.error(f"Invalid week number: {week}. Must be 1-{self.REGULAR_SEASON_WEEKS}")
            return False

        if status not in ['upcoming', 'in_progress', 'completed']:
            logger.error(f"Invalid status: {status}")
            return False

        start_date, end_date = self._get_week_dates(week)

        config = {
            'current_week': week,
            'season_year': self.SEASON_YEAR,
            'week_start_date': start_date.strftime('%Y-%m-%d'),
            'week_end_date': end_date.strftime('%Y-%m-%d'),
            'status': status,
            'last_updated': datetime.now().isoformat(),
            'source': 'manual'
        }

        return self._save_config(config)

    def advance_week(self) -> Tuple[int, bool]:
        """
        Advance to the next week

        Returns:
            Tuple of (new_week_number, success)
        """
        current_week = self.get_current_week()
        next_week = current_week + 1

        if next_week > self.REGULAR_SEASON_WEEKS:
            logger.warning(f"Already at final week ({self.REGULAR_SEASON_WEEKS})")
            return current_week, False

        success = self.set_week(next_week, status='upcoming')
        return next_week, success

    def validate_data_files(self) -> Dict:
        """
        Check if data files match the current week

        Returns:
            Dictionary with validation results
        """
        current_week = self.get_current_week()
        results = {
            'current_week': current_week,
            'files_checked': 0,
            'files_current': 0,
            'files_outdated': 0,
            'missing_files': [],
            'outdated_files': []
        }

        # Expected files for current week
        expected_files = [
            f"defense_stats_week_{current_week}.csv",
            f"matchups_week_{current_week}.csv",
            f"odds_qb_td_week_{current_week}.csv",
            f"odds_spreads_week_{current_week}.csv",
            f"odds_totals_week_{current_week}.csv"
        ]

        for filename in expected_files:
            filepath = self.data_dir / filename
            results['files_checked'] += 1

            if filepath.exists():
                results['files_current'] += 1
            else:
                results['missing_files'].append(filename)

        # Check for old week files
        if current_week > 1:
            for old_week in range(1, current_week):
                for pattern in ['defense_stats', 'matchups', 'odds_qb_td', 'odds_spreads', 'odds_totals']:
                    old_file = self.data_dir / f"{pattern}_week_{old_week}.csv"
                    if old_file.exists():
                        results['outdated_files'].append(old_file.name)
                        results['files_outdated'] += 1

        return results

    def _calculate_week_from_date(self) -> int:
        """
        Calculate NFL week from current date

        Returns:
            Week number (1-18)
        """
        now = datetime.now()

        # Before season starts
        if now < self.SEASON_START:
            return 1

        # During season
        days_since_start = (now - self.SEASON_START).days
        week = (days_since_start // 7) + 1

        # Cap at final week
        return min(week, self.REGULAR_SEASON_WEEKS)

    def _get_week_dates(self, week: int) -> Tuple[datetime, datetime]:
        """
        Get start and end dates for a given week

        Args:
            week: NFL week number

        Returns:
            Tuple of (start_date, end_date)
        """
        week_offset = week - 1
        start_date = self.SEASON_START + timedelta(weeks=week_offset)
        end_date = start_date + timedelta(days=6)

        return start_date, end_date

    def _get_week_status(self, start_date: datetime, end_date: datetime) -> str:
        """
        Determine week status based on dates

        Args:
            start_date: Week start date
            end_date: Week end date

        Returns:
            Status string
        """
        now = datetime.now()

        if now < start_date:
            return 'upcoming'
        elif now <= end_date:
            return 'in_progress'
        else:
            return 'completed'

    def _load_config(self) -> Optional[Dict]:
        """
        Load week configuration from JSON file

        Returns:
            Config dictionary or None if not found
        """
        if not self.config_path.exists():
            return None

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return None

    def _save_config(self, config: Dict) -> bool:
        """
        Save week configuration to JSON file

        Args:
            config: Configuration dictionary

        Returns:
            True if successful
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Week config saved: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False


def main():
    """CLI interface for week manager"""
    import argparse

    parser = argparse.ArgumentParser(
        description='NFL Week Manager - Single source of truth for week tracking'
    )

    parser.add_argument(
        '--set-week',
        type=int,
        metavar='WEEK',
        help='Set the current week manually (1-18)'
    )

    parser.add_argument(
        '--status',
        choices=['upcoming', 'in_progress', 'completed'],
        default='in_progress',
        help='Week status (default: in_progress)'
    )

    parser.add_argument(
        '--advance',
        action='store_true',
        help='Advance to next week'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate data files match current week'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    wm = WeekManager()

    # Handle commands
    if args.set_week:
        success = wm.set_week(args.set_week, args.status)
        if success:
            print(f"✓ Week set to {args.set_week} (status: {args.status})")
        else:
            print(f"✗ Failed to set week")
            return 1

    elif args.advance:
        new_week, success = wm.advance_week()
        if success:
            print(f"✓ Advanced to Week {new_week}")
        else:
            print(f"✗ Already at final week")
            return 1

    elif args.validate:
        results = wm.validate_data_files()

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"DATA FILE VALIDATION - Week {results['current_week']}")
            print(f"{'='*60}")
            print(f"\nFiles checked: {results['files_checked']}")
            print(f"Current files: {results['files_current']}")
            print(f"Missing files: {len(results['missing_files'])}")
            print(f"Outdated files: {results['files_outdated']}")

            if results['missing_files']:
                print(f"\n⚠️  Missing files for Week {results['current_week']}:")
                for f in results['missing_files']:
                    print(f"  - {f}")

            if results['outdated_files']:
                print(f"\n📦 Outdated files (from previous weeks):")
                for f in results['outdated_files']:
                    print(f"  - {f}")

            if not results['missing_files'] and not results['outdated_files']:
                print(f"\n✓ All data files are current!")

            print(f"{'='*60}\n")

    else:
        # Default: show current week info
        info = wm.get_week_info()

        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"CURRENT NFL WEEK INFO")
            print(f"{'='*60}")
            print(f"Week:        {info['current_week']}")
            print(f"Season:      {info['season_year']}")
            print(f"Start Date:  {info['week_start_date']}")
            print(f"End Date:    {info['week_end_date']}")
            print(f"Status:      {info['status']}")
            print(f"Source:      {info.get('source', 'config')}")
            print(f"Updated:     {info['last_updated']}")
            print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
