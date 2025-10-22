"""
Defense Stats Scraper for Pro Football Reference
Scrapes passing touchdowns allowed per game by each NFL team
"""
import logging
import time
import sys
from pathlib import Path
from typing import Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PFR_DEFENSE_URL_TEMPLATE,
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    DATA_DIR,
    DEFENSE_FILE_TEMPLATE,
    CURRENT_YEAR
)

logger = logging.getLogger(__name__)
    """Scrapes NFL defense stats from Pro Football Reference"""

    def __init__(self, year: int = CURRENT_YEAR):
        """
        Initialize the defense stats scraper

        Args:
            year: NFL season year
        """
        self.year = year
        self.url = PFR_DEFENSE_URL_TEMPLATE.format(year=year)
        self.headers = {"User-Agent": USER_AGENT}

    def scrape(self) -> Optional[pd.DataFrame]:
        """
        Scrape defense stats from Pro Football Reference

        Returns:
            DataFrame with defense stats or None if failed
        """
        logger.info(f"Scraping defense stats for {self.year} season from {self.url}")

        try:
            # Make request with delay to be polite
            time.sleep(REQUEST_DELAY)
            response = requests.get(
                self.url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Find the Team Defense & Special Teams table
            # The table ID is typically 'team_stats' or contains 'opp'
            table = soup.find('table', {'id': 'team_stats'})

            if not table:
                # Try alternate table ID
                table = soup.find('table', {'id': 'passing'})

            if not table:
                logger.error("Could not find defense stats table on page")
                return None

            # Parse table into DataFrame
            df = pd.read_html(str(table))[0]

            # Clean up the DataFrame
            df = self._clean_dataframe(df)

            logger.info(f"Successfully scraped {len(df)} teams")
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}", exc_info=True)
            return None

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and transform the raw dataframe

        Args:
            df: Raw DataFrame from Pro Football Reference

        Returns:
            Cleaned DataFrame with required columns
        """
        # Remove any multi-level column headers
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(0)

        # Debug: print columns
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"Available columns: {df.columns.tolist()}")

        # Check if 'Tm' column exists
        if 'Tm' not in df.columns:
            logger.error(f"Expected column 'Tm' not found in dataframe")
            raise ValueError("Expected column 'Tm' not found in dataframe")

        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()

        # Remove rows that are actually headers (Pro Football Reference sometimes repeats headers)
        df = df[df['Tm'].astype(str) != 'Tm'].copy()
        df = df[df['Tm'].astype(str) != 'Avg Team'].copy()
        df = df[df['Tm'].astype(str) != 'League Total'].copy()

        # Handle duplicate column names - Pro Football Reference has multiple 'TD', 'Yds', etc.
        # Rename columns to make them unique
        new_cols = []
        col_counts = {}
        for col in df.columns:
            if col in col_counts:
                col_counts[col] += 1
                new_cols.append(f"{col}_{col_counts[col]}")
            else:
                col_counts[col] = 0
                new_cols.append(col)
        df.columns = new_cols

        # Now 'TD' is the first TD column (passing TDs allowed)
        # Convert numeric columns
        df['G'] = pd.to_numeric(df['G'], errors='coerce')
        df['TD'] = pd.to_numeric(df['TD'], errors='coerce')

        # Calculate TDs per game
        df['TD_Per_Game'] = (df['TD'] / df['G']).round(2)

        # Rename columns to match our template
        column_mapping = {
            'Tm': 'team_name',
            'TD': 'pass_tds_allowed',
            'G': 'games_played',
            'TD_Per_Game': 'tds_per_game'
        }

        df = df.rename(columns=column_mapping)

        # Select only the columns we need
        required_cols = ['team_name', 'pass_tds_allowed', 'games_played', 'tds_per_game']
        df = df[[col for col in required_cols if col in df.columns]].copy()

        # Remove any NaN values
        df = df.dropna()

        # Sort by TDs allowed (ascending - best defenses first)
        if 'tds_per_game' in df.columns and len(df) > 0:
            try:
                df = df.sort_values(by='tds_per_game', ascending=True)
            except Exception as e:
                logger.warning(f"Could not sort dataframe: {e}")

        # Reset index
        df = df.reset_index(drop=True)

        return df

    def save_to_csv(self, df: pd.DataFrame, week: int) -> str:
        """
        Save DataFrame to CSV file

        Args:
            df: DataFrame with defense stats
            week: Current NFL week number

        Returns:
            Path to saved CSV file
        """
        filename = DEFENSE_FILE_TEMPLATE.format(week=week)
        filepath = DATA_DIR / filename

        df.to_csv(filepath, index=False)
        logger.info(f"Saved defense stats to {filepath}")

        return str(filepath)

    def save_to_database(self, df: pd.DataFrame, week: int) -> bool:
        """
        Save data using snapshot-then-upsert pattern
        
        Args:
            df: DataFrame with defense stats
            week: Current NFL week number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # 1. Save CSV snapshot to historical storage FIRST
            csv_path = self.save_to_csv(df, week)
            historical = HistoricalStorage()
            snapshot_path = historical.save_snapshot(csv_path, week, snapshot_type='auto')
            
            if not snapshot_path:
                logger.error("Failed to save historical snapshot")
                return False
            
            # 2. Upsert to operational database using db_manager
            from utils.db_manager import DatabaseManager
            
            db = DatabaseManager()
            db.connect()
            
            try:
                rows_inserted = db.insert_dataframe('defense_stats', df, week=week)
                db.conn.commit()
                
                logger.info(f"✅ Upserted {rows_inserted} records to database")
                logger.info(f"📸 Historical snapshot saved to {snapshot_path}")
                
                return True
                
            except Exception as e:
                db.conn.rollback()
                logger.error(f"❌ Database upsert failed: {e}")
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error in save_to_database: {e}")
            return False

    def run(self, week: int, save_to_db: bool = False) -> Optional[str]:
        """
        Run the complete scraping workflow

        Args:
            week: Current NFL week number
            save_to_db: If True, save to database using snapshot-then-upsert pattern

        Returns:
            Path to saved CSV file, or None if failed
        """
        df = self.scrape()

        if df is not None and not df.empty:
            if save_to_db:
                # Use snapshot-then-upsert pattern
                success = self.save_to_database(df, week)
                if success:
                    # Return CSV path for compatibility
                    return self.save_to_csv(df, week)
                else:
                    logger.error("Failed to save to database")
                    return None
            else:
                # Just save CSV (legacy behavior)
                return self.save_to_csv(df, week)
        else:
            logger.error("Failed to scrape defense stats")
            return None


def main():
    """Main function for testing"""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get week from command line or default to 7
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    scraper = DefenseStatsScraper()
    result = scraper.run(week)

    if result:
        print(f"Success! Saved to: {result}")
    else:
        print("Failed to scrape defense stats")
        sys.exit(1)


if __name__ == "__main__":
    main()
