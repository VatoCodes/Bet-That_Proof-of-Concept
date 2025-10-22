"""
QB Stats Scraper for Pro Football Reference
Scrapes quarterback passing statistics including touchdown passes
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
    PFR_QB_URL_TEMPLATE,
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    DATA_DIR,
    QB_FILE_TEMPLATE,
    CURRENT_YEAR
)

logger = logging.getLogger(__name__)


class QBStatsScraper:
    """Scrapes NFL QB stats from Pro Football Reference"""

    def __init__(self, year: int = CURRENT_YEAR):
        """
        Initialize the QB stats scraper

        Args:
            year: NFL season year
        """
        self.year = year
        self.url = PFR_QB_URL_TEMPLATE.format(year=year)
        self.headers = {"User-Agent": USER_AGENT}

    def scrape(self) -> Optional[pd.DataFrame]:
        """
        Scrape QB stats from Pro Football Reference

        Returns:
            DataFrame with QB stats or None if failed
        """
        logger.info(f"Scraping QB stats for {self.year} season from {self.url}")

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

            # Find the passing stats table
            table = soup.find('table', {'id': 'passing'})

            if not table:
                logger.error("Could not find QB stats table on page")
                return None

            # Parse table into DataFrame
            df = pd.read_html(str(table))[0]

            # Clean up the DataFrame
            df = self._clean_dataframe(df)

            logger.info(f"Successfully scraped {len(df)} QB records")
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

        # Make a copy
        df = df.copy()

        # Remove rows that are actually headers
        df = df[df['Player'].astype(str) != 'Player'].copy()

        # Convert numeric columns (handle duplicates if they exist)
        numeric_cols = ['TD', 'G', 'GS']
        for col in numeric_cols:
            if col in df.columns:
                col_data = df[col]
                # If it's a Series, convert directly
                if isinstance(col_data, pd.Series):
                    df[col] = pd.to_numeric(col_data, errors='coerce')
                # If it's a DataFrame (duplicate columns), take the first one
                elif isinstance(col_data, pd.DataFrame):
                    df[col] = pd.to_numeric(col_data.iloc[:, 0], errors='coerce')

        # Determine if player is a starter (has games started > 0)
        if 'GS' in df.columns:
            df['is_starter'] = df['GS'] > 0
        else:
            df['is_starter'] = False

        # Rename columns to match our template
        column_mapping = {
            'Player': 'qb_name',
            'Tm': 'team',
            'TD': 'total_tds',
            'G': 'games_played',
            'is_starter': 'is_starter'
        }

        # Handle 'Tm' if it's a DataFrame (duplicate column)
        if 'Tm' in df.columns:
            tm_data = df['Tm']
            if isinstance(tm_data, pd.DataFrame):
                df['Tm'] = tm_data.iloc[:, 0]

        df = df.rename(columns=column_mapping)

        # Select only the columns we need
        required_cols = ['qb_name', 'team', 'total_tds', 'games_played', 'is_starter']
        df = df[[col for col in required_cols if col in df.columns]].copy()

        # Remove rows with missing critical data (only check columns that exist)
        dropna_cols = [col for col in ['qb_name', 'team'] if col in df.columns]
        if dropna_cols:
            df = df.dropna(subset=dropna_cols)

        # Fill NaN values for numeric columns with 0
        numeric_cols_final = ['total_tds', 'games_played']
        for col in numeric_cols_final:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(int)

        # Sort by total TDs (descending)
        if 'total_tds' in df.columns:
            df = df.sort_values('total_tds', ascending=False)

        # Reset index
        df = df.reset_index(drop=True)

        return df

    def save_to_csv(self, df: pd.DataFrame) -> str:
        """
        Save DataFrame to CSV file

        Args:
            df: DataFrame with QB stats

        Returns:
            Path to saved CSV file
        """
        filename = QB_FILE_TEMPLATE.format(year=self.year)
        filepath = DATA_DIR / filename

        df.to_csv(filepath, index=False)
        logger.info(f"Saved QB stats to {filepath}")

        return str(filepath)

    def run(self) -> Optional[str]:
        """
        Run the complete scraping workflow

        Returns:
            Path to saved CSV file, or None if failed
        """
        df = self.scrape()

        if df is not None and not df.empty:
            return self.save_to_csv(df)
        else:
            logger.error("Failed to scrape QB stats")
            return None


def main():
    """Main function for testing"""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get year from command line or use current year
    year = int(sys.argv[1]) if len(sys.argv) > 1 else CURRENT_YEAR

    scraper = QBStatsScraper(year)
    result = scraper.run()

    if result:
        print(f"Success! Saved to: {result}")
    else:
        print("Failed to scrape QB stats")
        sys.exit(1)


if __name__ == "__main__":
    main()
