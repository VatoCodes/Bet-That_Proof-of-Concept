"""Weekly Roster Key Importer

Imports player availability tracking from PlayerProfiler weekly roster CSVs.
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class RosterImporter:
    """Import weekly roster key"""

    def __init__(self, db_manager):
        """Initialize importer"""
        self.db_manager = db_manager

    def import_season(self, season, csv_path):
        """
        Import roster data for given season

        Args:
            season: Season year
            csv_path: Path to roster CSV

        Returns:
            int: Number of player-week entries imported
        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"Roster file not found: {csv_path}")

        logger.info(f"   Loading roster data from {csv_path.name}...")

        # Load CSV
        df = pd.read_csv(csv_path, low_memory=False)
        original_count = len(df)

        # Clean and transform
        df = self._clean_data(df, season)

        # Save snapshot
        self._save_snapshot(df, season)

        # Upsert to database
        self.db_manager.upsert_player_roster(df)

        logger.info(f"   Processed {len(df):,} of {original_count:,} roster entries")

        return len(df)

    def _clean_data(self, df, season):
        """Clean and transform roster data"""
        # Rename columns to match database schema
        column_map = {
            'player_name': 'player_name',
            'name': 'player_name',
            'position': 'position',
            'team': 'team',
            'week': 'week',
            'status': 'status',
            'player_id': 'player_id'
        }

        # Use only columns that exist
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)

        # Ensure required columns exist
        required_cols = ['player_name', 'position', 'team', 'week', 'status']
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"   Missing column: {col}")
                df[col] = 'Unknown' if col == 'status' else ''

        # Add season
        df['season'] = season

        # Standardize status values
        status_map = {
            'ACT': 'Active',
            'ACTIVE': 'Active',
            'IR': 'IR',
            'PUP': 'PUP',
            'SUSP': 'Suspended'
        }
        if 'status' in df.columns:
            df['status'] = df['status'].str.upper().map(status_map).fillna('Active')

        # Remove rows with missing critical data
        df = df[df['player_name'].notna() & df['team'].notna()]

        # Select only columns we need
        final_cols = ['player_id', 'player_name', 'position', 'team', 'season', 'week', 'status']
        df = df[[c for c in final_cols if c in df.columns]]

        # Add player_id if missing
        if 'player_id' not in df.columns:
            df['player_id'] = None

        return df

    def _save_snapshot(self, df, season):
        """Save historical snapshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = Path('data/historical/playerprofile_imports')
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = snapshot_dir / f'player_roster_{season}_{timestamp}.csv'
        df.to_csv(snapshot_path, index=False)

        logger.info(f"   Snapshot saved: {snapshot_path.name}")
