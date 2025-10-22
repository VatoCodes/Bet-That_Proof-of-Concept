#!/usr/bin/env python3
"""
NFL Edge Finder - Data Validator

Validates data completeness and consistency across the NFL Edge Finder system.
Checks for common issues like week mismatches, missing team assignments, and
insufficient data coverage.

Usage:
    python3 utils/data_validator.py --check           # Check data quality
    python3 utils/data_validator.py --fix             # Auto-fix issues
    python3 utils/data_validator.py --check --week 7  # Check specific week
"""

import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any


class DataValidator:
    """Validates NFL Edge Finder data completeness and consistency"""

    # Acceptable thresholds for "good enough" data
    THRESHOLDS = {
        'qb_props_coverage': 0.66,  # 66% coverage = 20+ QBs out of 30
        'defense_coverage': 0.90,   # 90% coverage = 29+ teams out of 32
        'matchup_coverage': 0.80,   # 80% coverage = 13+ games out of 16
    }

    def __init__(self, project_root: Path = None):
        """Initialize validator

        Args:
            project_root: Path to project root (auto-detected if not provided)
        """
        if project_root is None:
            # Auto-detect project root
            current_file = Path(__file__).resolve()
            self.project_root = current_file.parent.parent
        else:
            self.project_root = Path(project_root)

        self.db_path = self.project_root / 'data' / 'database' / 'nfl_betting.db'
        self.config_path = self.project_root / 'current_week.json'

        # Track issues and warnings
        self.issues = []
        self.warnings = []

    def get_configured_week(self) -> int:
        """Get currently configured week from config file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config['current_week']
        except Exception as e:
            self.issues.append(f"Cannot read current_week.json: {e}")
            return None

    def get_available_weeks(self, table: str = 'defense_stats') -> List[int]:
        """Get list of weeks with data in database

        Args:
            table: Table to check (default: defense_stats)

        Returns:
            List of week numbers with data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT week FROM {table} ORDER BY week')
            weeks = [row[0] for row in cursor.fetchall()]
            conn.close()
            return weeks
        except Exception as e:
            self.warnings.append(f"Cannot query {table}: {e}")
            return []

    def check_week_mismatch(self) -> Tuple[int, List[int]]:
        """Check if configured week matches available data

        Returns:
            Tuple of (configured_week, available_weeks)
        """
        configured_week = self.get_configured_week()
        available_weeks = self.get_available_weeks()

        return configured_week, available_weeks

    def check_qb_team_assignments(self, week: int = None) -> Dict[str, Any]:
        """Check if QB stats have team assignments

        Args:
            week: Week to check (checks all if None)

        Returns:
            Dict with total QBs, missing teams count, and examples
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Count total and missing
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN team IS NULL OR team = '' THEN 1 ELSE 0 END) as missing
                FROM qb_stats
            """)
            total, missing = cursor.fetchone()

            # Get examples of QBs with missing teams
            cursor.execute("""
                SELECT qb_name, team, total_tds, games_played
                FROM qb_stats
                WHERE team IS NULL OR team = ''
                ORDER BY total_tds DESC
                LIMIT 5
            """)
            examples = cursor.fetchall()

            conn.close()

            return {
                'total': total,
                'missing': missing,
                'percentage_missing': (missing / total * 100) if total > 0 else 0,
                'examples': examples
            }
        except Exception as e:
            self.warnings.append(f"Cannot check QB team assignments: {e}")
            return {'total': 0, 'missing': 0, 'percentage_missing': 0, 'examples': []}

    def check_qb_props_coverage(self, week: int) -> Dict[str, Any]:
        """Check QB props coverage for a specific week

        Args:
            week: Week to check

        Returns:
            Dict with coverage stats
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Count unique QBs with props
            cursor.execute("""
                SELECT COUNT(DISTINCT qb_name)
                FROM qb_props
                WHERE week = ?
            """, (week,))
            unique_qbs = cursor.fetchone()[0]

            # Get list of QBs
            cursor.execute("""
                SELECT DISTINCT qb_name
                FROM qb_props
                WHERE week = ?
                ORDER BY qb_name
            """, (week,))
            qb_names = [row[0] for row in cursor.fetchall()]

            conn.close()

            expected_qbs = 32  # ~32 starting QBs in NFL
            coverage_ratio = unique_qbs / expected_qbs if expected_qbs > 0 else 0

            return {
                'unique_qbs': unique_qbs,
                'expected': expected_qbs,
                'coverage_ratio': coverage_ratio,
                'qb_names': qb_names,
                'is_acceptable': coverage_ratio >= self.THRESHOLDS['qb_props_coverage']
            }
        except Exception as e:
            self.warnings.append(f"Cannot check QB props coverage: {e}")
            return {
                'unique_qbs': 0,
                'expected': 32,
                'coverage_ratio': 0,
                'qb_names': [],
                'is_acceptable': False
            }

    def check_data_completeness(self, week: int) -> Dict[str, Dict[str, Any]]:
        """Check data completeness for all tables

        Args:
            week: Week to check

        Returns:
            Dict of table stats
        """
        tables = {
            'defense_stats': 32,  # 32 NFL teams
            'matchups': 16,       # ~16 games per week
            'qb_props': 32,       # ~32 starting QBs
            'qb_stats': None      # No week column
        }

        results = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for table, expected_count in tables.items():
                if table == 'qb_stats':
                    # qb_stats doesn't have week column
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    count = cursor.fetchone()[0]
                    results[table] = {
                        'count': count,
                        'expected': 'N/A (no week column)',
                        'complete': count > 0
                    }
                else:
                    cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE week = ?', (week,))
                    count = cursor.fetchone()[0]

                    if expected_count:
                        coverage_ratio = count / expected_count
                        threshold_key = f'{table.replace("_stats", "").replace("_props", "")}_coverage'
                        threshold = self.THRESHOLDS.get(threshold_key, 0.90)
                        is_acceptable = coverage_ratio >= threshold
                    else:
                        is_acceptable = count > 0

                    results[table] = {
                        'count': count,
                        'expected': expected_count,
                        'complete': count >= expected_count if expected_count else count > 0,
                        'acceptable': is_acceptable if expected_count else count > 0
                    }

            conn.close()

        except Exception as e:
            self.warnings.append(f"Cannot check data completeness: {e}")

        return results

    def check_duplicate_records(self, week: int) -> Dict[str, Any]:
        """Check for duplicate records in operational database
        
        Note: This checks the operational DB only. Historical snapshots
        in data/historical/ are SUPPOSED to have multiple timestamps.
        
        Args:
            week: Week to check
            
        Returns:
            Dict with duplicate information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check defense_stats duplicates
            cursor.execute("""
                SELECT team_name, COUNT(*) as count
                FROM defense_stats
                WHERE week = ?
                GROUP BY team_name
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """, (week,))
            defense_dupes = cursor.fetchall()
            
            # Check matchups duplicates
            cursor.execute("""
                SELECT home_team, away_team, COUNT(*) as count
                FROM matchups
                WHERE week = ?
                GROUP BY home_team, away_team
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """, (week,))
            matchup_dupes = cursor.fetchall()
            
            # Check qb_props duplicates
            cursor.execute("""
                SELECT qb_name, week, sportsbook, COUNT(*) as count
                FROM qb_props
                WHERE week = ?
                GROUP BY qb_name, week, sportsbook
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """, (week,))
            qb_props_dupes = cursor.fetchall()
            
            conn.close()
            
            # Add warnings if duplicates found
            if defense_dupes:
                self.warnings.append(
                    f"⚠️ {len(defense_dupes)} teams have duplicate defense_stats "
                    f"(examples: {', '.join([d[0] for d in defense_dupes[:3]])})"
                )
            
            if matchup_dupes:
                self.warnings.append(
                    f"⚠️ {len(matchup_dupes)} matchups have duplicates"
                )
            
            if qb_props_dupes:
                self.warnings.append(
                    f"⚠️ {len(qb_props_dupes)} QB props have duplicates"
                )
            
            return {
                'defense_duplicates': len(defense_dupes),
                'matchup_duplicates': len(matchup_dupes),
                'qb_props_duplicates': len(qb_props_dupes),
                'defense_examples': defense_dupes[:5],
                'matchup_examples': matchup_dupes[:5],
                'qb_props_examples': qb_props_dupes[:5]
            }
        except Exception as e:
            self.warnings.append(f"Cannot check duplicates: {e}")
            return {
                'defense_duplicates': 0,
                'matchup_duplicates': 0,
                'qb_props_duplicates': 0,
                'defense_examples': [],
                'matchup_examples': [],
                'qb_props_examples': []
            }
    
    def validate_all(self, week: int = None) -> Dict[str, Any]:
        """Run all validation checks

        Args:
            week: Week to validate (uses configured week if None)

        Returns:
            Dict with all validation results
        """
        # Clear previous results
        self.issues = []
        self.warnings = []

        # Get week to check
        if week is None:
            week = self.get_configured_week()

        if week is None:
            return {'error': 'Cannot determine week to validate'}

        # Run all checks
        configured_week, available_weeks = self.check_week_mismatch()
        qb_teams = self.check_qb_team_assignments()
        qb_props = self.check_qb_props_coverage(week)
        completeness = self.check_data_completeness(week)
        duplicates = self.check_duplicate_records(week)

        # Evaluate issues
        # CRITICAL: Week mismatch prevents any data from showing
        if configured_week not in available_weeks:
            self.issues.append(
                f"Week mismatch: Config shows week {configured_week}, "
                f"but only weeks {available_weeks} have data"
            )

        # WARNING: QB team assignments affect edge calculation but don't prevent dashboard
        if qb_teams['missing'] > 0:
            self.warnings.append(
                f"{qb_teams['missing']} QBs missing team assignments "
                f"({qb_teams['percentage_missing']:.1f}%) - Edge detection may be limited"
            )

        # WARNING: QB props affect edge opportunities but don't prevent dashboard
        if not qb_props['is_acceptable']:
            self.warnings.append(
                f"Only {qb_props['unique_qbs']} QBs with props "
                f"(expected ~{qb_props['expected']}) - Edge opportunities may be limited"
            )

        # Return comprehensive results
        return {
            'week_mismatch': {
                'configured': configured_week,
                'available_weeks': available_weeks,
                'has_configured_week': configured_week in available_weeks
            },
            'qb_teams': qb_teams,
            'qb_props': qb_props,
            'completeness': completeness,
            'duplicates': duplicates,
            'issues': self.issues,
            'warnings': self.warnings
        }

    def auto_fix(self) -> Dict[str, Any]:
        """Automatically fix common issues

        Returns:
            Dict with fix results
        """
        fixes_applied = []

        # Check for week mismatch
        configured_week, available_weeks = self.check_week_mismatch()

        if configured_week not in available_weeks and available_weeks:
            # Fix: Use the latest available week
            new_week = max(available_weeks)

            try:
                # Read config
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                # Update week
                old_week = config['current_week']
                config['current_week'] = new_week
                config['last_updated'] = datetime.now().isoformat()
                config['source'] = 'auto-fix'

                # Write back
                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)

                fixes_applied.append(f"Updated current_week: {old_week} → {new_week}")

            except Exception as e:
                self.issues.append(f"Cannot auto-fix week mismatch: {e}")

        return {
            'fixes_applied': fixes_applied,
            'issues': self.issues
        }

    def print_report(self, results: Dict[str, Any], verbose: bool = True):
        """Print formatted validation report

        Args:
            results: Validation results from validate_all()
            verbose: Show detailed information
        """
        print()
        print("🔍 NFL Edge Finder - Data Validation Report")
        print("=" * 60)
        print(f"Configured Week: {results['week_mismatch']['configured']}")
        print(f"Checking Week: {results['week_mismatch']['configured']}")
        print("=" * 60)
        print()

        # Check 1: Week Configuration
        print("📅 Check 1: Week Configuration")
        wm = results['week_mismatch']
        if wm['has_configured_week']:
            print(f"   ✅ Week {wm['configured']} has data")
        else:
            print(f"   ❌ ISSUE: Week {wm['configured']} has no data")
            print(f"   ℹ️  Available weeks: {wm['available_weeks']}")
            if wm['available_weeks']:
                print(f"   💡 Suggestion: Use week {max(wm['available_weeks'])}")
        print()

        # Check 2: QB Team Assignments
        print("👥 Check 2: QB Team Assignments")
        qb = results['qb_teams']
        if qb['missing'] == 0:
            print(f"   ✅ All {qb['total']} QBs have team assignments")
        else:
            print(f"   ❌ ISSUE: {qb['missing']} QBs missing teams ({qb['percentage_missing']:.1f}%)")
            if verbose and qb['examples']:
                print("   Examples:")
                for qb_name, team, tds, games in qb['examples'][:3]:
                    print(f"      - {qb_name}: team='{team}', TDs={tds}, games={games}")
            print("   💡 Suggestion: Re-scrape QB stats with team extraction")
        print()

        # Check 3: QB Props Coverage
        print("🎯 Check 3: QB Props Coverage")
        props = results['qb_props']
        if props['is_acceptable']:
            print(f"   ✅ {props['unique_qbs']} QBs with props (acceptable)")
        else:
            print(f"   ❌ ISSUE: Only {props['unique_qbs']} QBs with props (expected ~{props['expected']})")
            if verbose and props['qb_names']:
                print(f"   QBs with props: {', '.join(props['qb_names'][:5])}")
            print(f"   💡 Suggestion: Scrape QB TD props for week {wm['configured']}")
        print()

        # Check 4: Data Completeness
        if verbose:
            print("📊 Check 4: Data Completeness")
            for table, stats in results['completeness'].items():
                count = stats['count']
                expected = stats['expected']
                if expected == 'N/A (no week column)':
                    print(f"   {table:20} {count} records")
                else:
                    status = "✅" if stats.get('acceptable', stats['complete']) else "⚠️"
                    print(f"   {status} {table:20} {count}/{expected}")
            print()

        # Summary
        print("=" * 60)
        if not results['issues']:
            print("✅ No critical issues found")
        else:
            print(f"❌ {len(results['issues'])} critical issue(s) found:")
            for issue in results['issues']:
                print(f"   - {issue}")

        if results['warnings']:
            print(f"⚠️  {len(results['warnings'])} warning(s):")
            for warning in results['warnings']:
                print(f"   - {warning}")
        print("=" * 60)
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate NFL Edge Finder data quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 utils/data_validator.py --check           # Check current week
  python3 utils/data_validator.py --check --week 7  # Check specific week
  python3 utils/data_validator.py --fix             # Auto-fix issues
        """
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check data quality'
    )

    parser.add_argument(
        '--fix',
        action='store_true',
        help='Auto-fix common issues'
    )

    parser.add_argument(
        '--week',
        type=int,
        help='Week to validate (defaults to configured week)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        default=True,
        help='Show detailed information (default: True)'
    )

    args = parser.parse_args()

    # Create validator
    validator = DataValidator()

    # Run checks
    if args.check:
        results = validator.validate_all(week=args.week)
        validator.print_report(results, verbose=args.verbose)

        # Exit with error code if issues found
        if validator.issues:
            exit(1)

    elif args.fix:
        print()
        print("🔧 Auto-Fix Mode")
        print("=" * 60)

        # Run validation first
        results = validator.validate_all(week=args.week)
        validator.print_report(results, verbose=False)

        # Apply fixes
        print("🔧 Applying fixes...")
        print()
        fix_results = validator.auto_fix()

        if fix_results['fixes_applied']:
            for fix in fix_results['fixes_applied']:
                print(f"   ✅ {fix}")
            print()
            print("📋 Auto-Fix Summary")
            print("=" * 60)
            print("   Fixes applied:")
            for fix in fix_results['fixes_applied']:
                print(f"      ✅ {fix}")
            print("   🎉 Auto-fix complete! Restart dashboard to see changes.")
        else:
            print("   ℹ️  No automatic fixes available")
            print()
            print("📋 Manual Actions Required")
            print("=" * 60)
            for issue in validator.issues:
                print(f"   - {issue}")

        print("=" * 60)
        print()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
