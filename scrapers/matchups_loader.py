"""
Load NFL schedule from hardcoded JSON file with API fallback
Hybrid approach: Primary = Hardcoded, Fallback = ESPN API
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

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


class HybridMatchupsScraper:
    """
    Hybrid scraper with multiple fallbacks
    Priority: Hardcoded JSON → ESPN API
    """

    def __init__(self):
        self.loader = MatchupsLoader()

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
    scraper = HybridMatchupsScraper()
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
