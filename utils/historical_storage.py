"""Historical Storage for NFL Edge Finder"""

from pathlib import Path
from datetime import datetime
import shutil
import zipfile
import logging
import json

logger = logging.getLogger(__name__)


class HistoricalStorage:
    """Manages historical snapshots and archiving of NFL data"""
    
    def __init__(self, base_dir='data/historical'):
        """
        Initialize historical storage
        
        Args:
            base_dir: Base directory for historical data
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_snapshot(self, csv_path, week, snapshot_type='auto'):
        """
        Save timestamped snapshot of a CSV file
        
        Args:
            csv_path: Path to CSV file to snapshot
            week: NFL week number
            snapshot_type: Type of snapshot ('auto', 'manual', 'scheduled')
            
        Returns:
            Path to saved snapshot or None if failed
        """
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            logger.warning(f"⚠️  File not found: {csv_path}")
            return None
        
        try:
            # Create directory structure: data/historical/2025/week_7/
            year = datetime.now().year
            snapshot_dir = self.base_dir / str(year) / f"week_{week}"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = csv_path.stem
            
            # Clean up week suffix if present
            if f'_week_{week}' in base_name:
                base_name = base_name.replace(f'_week_{week}', '')
            
            snapshot_name = f"{base_name}_{timestamp}_{snapshot_type}.csv"
            snapshot_path = snapshot_dir / snapshot_name
            
            # Copy file to snapshot location
            shutil.copy2(csv_path, snapshot_path)
            
            # Create metadata file
            metadata = {
                'original_file': str(csv_path),
                'snapshot_file': str(snapshot_path),
                'week': week,
                'year': year,
                'timestamp': timestamp,
                'snapshot_type': snapshot_type,
                'file_size_bytes': csv_path.stat().st_size,
                'created_at': datetime.now().isoformat()
            }
            
            metadata_path = snapshot_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"📸 Saved snapshot: {snapshot_path}")
            return snapshot_path
            
        except Exception as e:
            logger.error(f"❌ Error saving snapshot of {csv_path}: {e}")
            return None
    
    def save_all_snapshots(self, week, snapshot_type='auto'):
        """
        Save snapshots of all CSV files for a given week
        
        Args:
            week: NFL week number
            snapshot_type: Type of snapshot
            
        Returns:
            List of saved snapshot paths
        """
        raw_dir = Path('data/raw')
        csv_files = [
            f'defense_stats_week_{week}.csv',
            f'qb_stats_2025.csv',  # QB stats are year-based, not week-based
            f'matchups_week_{week}.csv',
            f'odds_spreads_week_{week}.csv',
            f'odds_totals_week_{week}.csv',
            f'odds_qb_td_week_{week}.csv'
        ]
        
        saved_snapshots = []
        
        for csv_file in csv_files:
            csv_path = raw_dir / csv_file
            if csv_path.exists():
                snapshot = self.save_snapshot(csv_path, week, snapshot_type)
                if snapshot:
                    saved_snapshots.append(snapshot)
            else:
                logger.warning(f"⚠️  Expected file not found: {csv_path}")
        
        logger.info(f"✅ Saved {len(saved_snapshots)} snapshots for Week {week}")
        return saved_snapshots
    
    def archive_week(self, week, year=None):
        """
        Create ZIP archive of all snapshots for a week
        
        Args:
            week: NFL week number
            year: Year (defaults to current year)
            
        Returns:
            Path to archive file or None if failed
        """
        if year is None:
            year = datetime.now().year
        
        week_dir = self.base_dir / str(year) / f"week_{week}"
        
        if not week_dir.exists():
            logger.warning(f"⚠️  Week directory not found: {week_dir}")
            return None
        
        try:
            # Create archives directory
            archive_dir = self.base_dir / 'archives'
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Create archive filename
            archive_name = f"{year}_week_{week}.zip"
            archive_path = archive_dir / archive_name
            
            # Create ZIP archive
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all CSV files
                for csv_file in week_dir.glob('*.csv'):
                    zipf.write(csv_file, csv_file.name)
                
                # Add all metadata files
                for json_file in week_dir.glob('*.json'):
                    zipf.write(json_file, json_file.name)
            
            # Create archive metadata
            archive_metadata = {
                'archive_file': str(archive_path),
                'week': week,
                'year': year,
                'created_at': datetime.now().isoformat(),
                'files_included': len(list(week_dir.glob('*.csv'))),
                'archive_size_bytes': archive_path.stat().st_size
            }
            
            metadata_path = archive_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(archive_metadata, f, indent=2)
            
            logger.info(f"📦 Created archive: {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"❌ Error creating archive for Week {week}: {e}")
            return None
    
    def get_week_snapshots(self, week, year=None):
        """
        Get list of all snapshots for a given week
        
        Args:
            week: NFL week number
            year: Year (defaults to current year)
            
        Returns:
            List of snapshot information dictionaries
        """
        if year is None:
            year = datetime.now().year
        
        week_dir = self.base_dir / str(year) / f"week_{week}"
        
        if not week_dir.exists():
            return []
        
        snapshots = []
        
        # Find all CSV files and their metadata
        for csv_file in week_dir.glob('*.csv'):
            metadata_file = csv_file.with_suffix('.json')
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    snapshots.append(metadata)
                except Exception as e:
                    logger.warning(f"⚠️  Error reading metadata for {csv_file}: {e}")
        
        # Sort by timestamp
        snapshots.sort(key=lambda x: x.get('timestamp', ''))
        
        return snapshots
    
    def cleanup_old_snapshots(self, keep_days=30):
        """
        Clean up old snapshots to save space
        
        Args:
            keep_days: Number of days to keep snapshots
        """
        cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        cleaned_count = 0
        
        # Walk through all year directories
        for year_dir in self.base_dir.glob('[0-9][0-9][0-9][0-9]'):
            if not year_dir.is_dir():
                continue
            
            for week_dir in year_dir.glob('week_*'):
                if not week_dir.is_dir():
                    continue
                
                # Check each file in the week directory
                for file_path in week_dir.iterdir():
                    if file_path.stat().st_mtime < cutoff_date:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                            logger.info(f"🗑️  Cleaned up old file: {file_path}")
                        except Exception as e:
                            logger.warning(f"⚠️  Error cleaning up {file_path}: {e}")
        
        logger.info(f"✅ Cleaned up {cleaned_count} old snapshot files")
        return cleaned_count
    
    def get_storage_stats(self):
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'base_directory': str(self.base_dir),
            'total_size_mb': 0,
            'years': {},
            'total_snapshots': 0,
            'total_archives': 0
        }
        
        # Calculate total size
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file():
                stats['total_size_mb'] += file_path.stat().st_size
        
        stats['total_size_mb'] = round(stats['total_size_mb'] / (1024 * 1024), 2)
        
        # Count snapshots by year
        for year_dir in self.base_dir.glob('[0-9][0-9][0-9][0-9]'):
            if not year_dir.is_dir():
                continue
            
            year = year_dir.name
            year_stats = {
                'weeks': 0,
                'snapshots': 0,
                'size_mb': 0
            }
            
            for week_dir in year_dir.glob('week_*'):
                if week_dir.is_dir():
                    year_stats['weeks'] += 1
                    
                    # Count CSV files (snapshots)
                    csv_count = len(list(week_dir.glob('*.csv')))
                    year_stats['snapshots'] += csv_count
                    stats['total_snapshots'] += csv_count
                    
                    # Calculate size
                    for file_path in week_dir.iterdir():
                        if file_path.is_file():
                            year_stats['size_mb'] += file_path.stat().st_size
            
            year_stats['size_mb'] = round(year_stats['size_mb'] / (1024 * 1024), 2)
            stats['years'][year] = year_stats
        
        # Count archives
        archive_dir = self.base_dir / 'archives'
        if archive_dir.exists():
            stats['total_archives'] = len(list(archive_dir.glob('*.zip')))
        
        return stats


def main():
    """CLI interface for historical storage management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NFL Historical Storage Manager')
    parser.add_argument('--snapshot', help='Save snapshot of specific CSV file')
    parser.add_argument('--week', type=int, help='Week number for snapshot')
    parser.add_argument('--snapshot-all', action='store_true', help='Save snapshots of all current week files')
    parser.add_argument('--archive', type=int, help='Create archive for specific week')
    parser.add_argument('--stats', action='store_true', help='Show storage statistics')
    parser.add_argument('--cleanup', type=int, help='Clean up files older than N days')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    storage = HistoricalStorage()
    
    try:
        if args.snapshot and args.week:
            snapshot_path = storage.save_snapshot(args.snapshot, args.week)
            if snapshot_path:
                print(f"✅ Snapshot saved: {snapshot_path}")
            else:
                print("❌ Failed to save snapshot")
        
        elif args.snapshot_all and args.week:
            snapshots = storage.save_all_snapshots(args.week)
            print(f"✅ Saved {len(snapshots)} snapshots for Week {args.week}")
        
        elif args.archive:
            archive_path = storage.archive_week(args.archive)
            if archive_path:
                print(f"✅ Archive created: {archive_path}")
            else:
                print("❌ Failed to create archive")
        
        elif args.stats:
            stats = storage.get_storage_stats()
            print("\n" + "=" * 60)
            print("HISTORICAL STORAGE STATISTICS")
            print("=" * 60)
            print(f"Base Directory: {stats['base_directory']}")
            print(f"Total Size: {stats['total_size_mb']} MB")
            print(f"Total Snapshots: {stats['total_snapshots']}")
            print(f"Total Archives: {stats['total_archives']}")
            print("\nBy Year:")
            for year, year_stats in stats['years'].items():
                print(f"  {year}: {year_stats['weeks']} weeks, {year_stats['snapshots']} snapshots, {year_stats['size_mb']} MB")
            print("=" * 60)
        
        elif args.cleanup:
            cleaned = storage.cleanup_old_snapshots(args.cleanup)
            print(f"✅ Cleaned up {cleaned} old files")
        
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
