"""Play-by-Play Data Importer

Imports advanced play-by-play data from PlayerProfiler CSVs.
Stores subset of columns needed for team metrics calculation.
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class PlayByPlayImporter:
    """Import play-by-play data"""

    # CSV column name mapping to database columns
    COLUMN_MAPPING = {
        'playid': 'play_id',
        'season': 'season',
        'week': 'week',
        'gamekey_internal': 'game_key',
        'quarter': 'quarter',
        'offense': 'offense',
        'defense': 'defense',
        'play_type': 'play_type',
        'yards_gained': 'yards_gained',
        'down': 'down',
        'distance': 'to_go',
        'yards_to_endzone': 'yards_to_endzone',
        'shotgun': 'shotgun',
        'play_action': 'play_action',
        'redzone': 'red_zone_play',
        'first_down_gained': 'is_first_down',
        'over_under': 'over_under',
        'spread': 'spread'
    }

    def __init__(self, db_manager):
        """Initialize importer"""
        self.db_manager = db_manager

    def import_season(self, season, csv_path):
        """
        Import play-by-play data for given season

        Args:
            season: Season year
            csv_path: Path to PBP CSV file

        Returns:
            int: Number of plays imported
        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"PBP file not found: {csv_path}")

        logger.info(f"   Loading PBP data from {csv_path.name}...")

        # Load CSV
        df = pd.read_csv(csv_path, low_memory=False)
        original_count = len(df)

        # Select and rename columns
        cols_to_keep = [k for k in self.COLUMN_MAPPING.keys() if k in df.columns]
        df = df[cols_to_keep].copy()
        df.rename(columns=self.COLUMN_MAPPING, inplace=True)

        # Clean data
        df = self._clean_data(df)

        # Save historical snapshot
        self._save_snapshot(df, season)

        # Upsert to database
        self.db_manager.upsert_play_by_play(df)

        logger.info(f"   Processed {len(df):,} of {original_count:,} plays")

        return len(df)

    def _clean_data(self, df):
        """Clean and transform data"""
        # Convert boolean columns
        bool_cols = ['shotgun', 'play_action', 'red_zone_play', 'is_first_down']
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(bool)

        # Convert numeric columns
        numeric_cols = ['yards_gained', 'down', 'to_go', 'yards_to_endzone', 'quarter']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # Strip whitespace from team names
        if 'offense' in df.columns:
            df['offense'] = df['offense'].str.strip()
        if 'defense' in df.columns:
            df['defense'] = df['defense'].str.strip()

        # Detect touchdowns from play description (simplified)
        df['is_touchdown'] = False
        df['is_turnover'] = False

        # Add timestamp
        df['created_at'] = datetime.now().isoformat()

        # Remove rows with missing critical data
        df = df[df['play_id'].notna() & df['offense'].notna() & df['defense'].notna()]

        return df

    def _save_snapshot(self, df, season):
        """Save historical snapshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = Path('data/historical/playerprofile_imports')
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = snapshot_dir / f'play_by_play_{season}_{timestamp}.csv'
        df.to_csv(snapshot_path, index=False)

        logger.info(f"   Snapshot saved: {snapshot_path.name}")
