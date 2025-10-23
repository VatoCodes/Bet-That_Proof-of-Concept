"""
Load NFL schedule from hardcoded JSON file with API fallback
Hybrid approach: Primary = Hardcoded, Fallback = ESPN API
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import DATA_DIR, MATCHUPS_FILE_TEMPLATE
    from utils.week_manager import WeekManager
except ImportError:
    # Fallback for testing
    DATA_DIR = Path("data")
    MATCHUPS_FILE_TEMPLATE = "matchups_week_{week}.csv"
    WeekManager = None

logger = logging.getLogger(__name__)


class MatchupsLoader:
    """Loads matchups from pre-generated schedule file with API fallback"""

    SCHEDULE_FILE = Path("data/schedules/nfl_2025_schedule.json")

    def __init__(self):
        self.schedule = self._load_schedule()

    def _load_schedule(self) -> Dict:
        """Load schedule from JSON file"""
        try:
            if not self.SCHEDULE_FILE.exists():
                logger.warning(f"Schedule file not found: {self.SCHEDULE_FILE}")
                return {"weeks": {}}

            with open(self.SCHEDULE_FILE, 'r') as f:
                schedule = json.load(f)
                logger.info(f"Loaded schedule from {self.SCHEDULE_FILE}")
                return schedule
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schedule file: {e}")
            return {"weeks": {}}
        except Exception as e:
            logger.error(f"Error loading schedule file: {e}")
            return {"weeks": {}}

    def get_week_matchups(self, week: int) -> List[Dict]:
        """
        Get all matchups for a specific week

        Args:
            week: NFL week number (1-18)

        Returns:
            List of matchup dictionaries
        """
        week_str = str(week)

        if week_str not in self.schedule.get('weeks', {}):
            logger.warning(f"Week {week} not found in hardcoded schedule")
            return []

        matchups = self.schedule['weeks'][week_str]
        logger.info(f"Loaded {len(matchups)} matchups for week {week} from hardcoded schedule")

        return matchups


class MatchupsScraper:
    """
    Main scraper class compatible with existing pipeline
    Uses hybrid approach: hardcoded schedule + API fallback
    """

    def __init__(self):
        self.loader = MatchupsLoader()
        if WeekManager:
            self.week_manager = WeekManager()
        else:
            self.week_manager = None

    def scrape(self, week: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Scrape matchups for a given week

        Args:
            week: NFL week number (optional)

        Returns:
            DataFrame with matchups or None if failed
        """
        if week is None and self.week_manager:
            week = self.week_manager.get_current_week()

        matchups = self.scrape_week(week)

        if not matchups:
            logger.error("Failed to scrape matchups")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(matchups)
        logger.info(f"Successfully scraped {len(df)} matchups")
        return df

    def save_to_csv(self, df: pd.DataFrame, week: int) -> Optional[str]:
        """
        Save matchups DataFrame to CSV file

        Args:
            df: DataFrame with matchup data
            week: NFL week number

        Returns:
            Path to saved CSV file, or None if failed
        """
        try:
            # Ensure data directory exists
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            # Generate filename
            filename = MATCHUPS_FILE_TEMPLATE.format(week=week)
            filepath = DATA_DIR / filename

            # Save to CSV
            df.to_csv(filepath, index=False)
            logger.info(f"Saved matchups to {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save matchups to CSV: {e}")
            return None

    def run(self, week: int) -> Optional[str]:
        """
        Run the complete scraping workflow

        Args:
            week: NFL week number to scrape

        Returns:
            Path to saved CSV file, or None if failed
        """
        df = self.scrape(week)

        if df is not None and not df.empty:
            return self.save_to_csv(df, week)
        else:
            logger.error("Failed to scrape matchups")
            return None

    def scrape_week(self, week: int) -> List[Dict]:
        """
        Get matchups for a week using hybrid approach

        Args:
            week: NFL week number (1-18)

        Returns:
            List of matchup dictionaries
        """
        # Try hardcoded schedule first (fastest, most reliable)
        try:
            matchups = self.loader.get_week_matchups(week)
            if matchups and len(matchups) >= 12:
                logger.info(f"✓ Using hardcoded schedule for week {week}")
                return matchups
            else:
                logger.warning(f"Hardcoded schedule has insufficient data ({len(matchups)} games)")
        except Exception as e:
            logger.warning(f"Hardcoded schedule failed: {e}")

        # Fallback to ESPN API
        try:
            logger.info(f"Falling back to ESPN API for week {week}")
            from scrapers.matchups_scraper_api import MatchupsScraperAPI

            api_scraper = MatchupsScraperAPI()
            matchups = api_scraper.scrape_week(week)

            if matchups and len(matchups) >= 12:
                logger.info(f"✓ Using ESPN API for week {week}")
                return matchups
            else:
                logger.error(f"ESPN API returned insufficient data ({len(matchups)} games)")
        except Exception as e:
            logger.error(f"ESPN API failed: {e}")

        # If both failed, return empty list
        logger.error(f"All sources failed for week {week}")
        return []

    def validate_matchups(self, matchups: List[Dict], week: int) -> bool:
        """
        Validate that we got a reasonable number of games

        NFL typically has 12-16 games per week
        """
        game_count = len(matchups)

        if game_count < 12:
            logger.error(f"Week {week}: Only {game_count} games found (expected 12-16)")
            return False
        elif game_count > 17:
            logger.warning(f"Week {week}: {game_count} games found (expected 12-16)")
            return False
        else:
            logger.info(f"Week {week}: {game_count} games found ✓")
            return True


# Backwards compatibility - maintain same interface as old scraper
def scrape_matchups(week: int) -> List[Dict]:
    """
    Main entry point - maintains compatibility with existing code
    Uses hybrid approach: hardcoded primary, API fallback
    """
    scraper = MatchupsScraper()
    matchups = scraper.scrape_week(week)

    # Validate before returning
    if not scraper.validate_matchups(matchups, week):
        logger.warning(f"Matchup validation failed for week {week}")

    return matchups


if __name__ == "__main__":
    # Test the loader
    import sys

    week = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    logging.basicConfig(level=logging.INFO)
    print(f"\nTesting hybrid matchups scraper for week {week}...")
    matchups = scrape_matchups(week)

    print(f"\nFound {len(matchups)} matchups:")
    for m in matchups:
        print(f"  {m['away_team']} @ {m['home_team']} - {m['game_date']}")
