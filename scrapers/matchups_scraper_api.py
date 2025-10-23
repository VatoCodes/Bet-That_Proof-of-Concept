"""
ESPN API-based matchup scraper
Replaces fragile HTML parsing with stable JSON endpoint
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MatchupsScraperAPI:
    """Scrapes NFL matchups from ESPN API endpoint"""

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

    def __init__(self, year: int = 2025):
        self.year = year

    def scrape_week(self, week: int) -> List[Dict]:
        """
        Scrape all matchups for a given week

        Args:
            week: NFL week number (1-18)

        Returns:
            List of matchup dictionaries with home_team, away_team, game_date
        """
        try:
            # ESPN API accepts week parameter
            # seasontype=2 is regular season
            url = f"{self.BASE_URL}?week={week}&seasontype=2&dates={self.year}"

            logger.info(f"Fetching matchups from ESPN API: week {week}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            matchups = self._parse_response(data, week)

            logger.info(f"Successfully scraped {len(matchups)} matchups for week {week}")
            return matchups

        except requests.RequestException as e:
            logger.error(f"Failed to fetch from ESPN API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing ESPN API response: {e}")
            raise

    def _parse_response(self, data: Dict, week: int) -> List[Dict]:
        """Parse ESPN API JSON response into matchup format"""
        matchups = []

        events = data.get('events', [])

        if not events:
            logger.warning(f"No events found in ESPN API response for week {week}")
            return matchups

        for event in events:
            try:
                competition = event['competitions'][0]
                competitors = competition['competitors']

                # ESPN API returns home/away in 'homeAway' field
                home_team = None
                away_team = None

                for competitor in competitors:
                    team_name = competitor['team']['displayName']
                    if competitor['homeAway'] == 'home':
                        home_team = team_name
                    else:
                        away_team = team_name

                # Parse game date
                game_date_str = event['date']  # ISO format
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))

                if home_team and away_team:
                    matchup = {
                        'home_team': home_team,
                        'away_team': away_team,
                        'game_date': game_date.strftime('%Y-%m-%d'),
                        'week': week
                    }
                    matchups.append(matchup)
                else:
                    logger.warning(f"Could not identify home/away teams for event: {event.get('name')}")

            except (KeyError, IndexError) as e:
                logger.warning(f"Could not parse event: {e}")
                continue

        return matchups

    def validate_matchups(self, matchups: List[Dict], week: int) -> bool:
        """
        Validate that we got a reasonable number of games

        NFL typically has 14-16 games per week (some weeks have byes)
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
    """
    scraper = MatchupsScraperAPI()
    matchups = scraper.scrape_week(week)

    # Validate before returning
    if not scraper.validate_matchups(matchups, week):
        logger.warning(f"Matchup validation failed for week {week}, but returning data anyway")

    return matchups


if __name__ == "__main__":
    # Test the scraper
    import sys

    week = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    logging.basicConfig(level=logging.INFO)
    print(f"\nTesting ESPN API scraper for week {week}...")
    matchups = scrape_matchups(week)

    print(f"\nFound {len(matchups)} matchups:")
    for m in matchups:
        print(f"  {m['away_team']} @ {m['home_team']} - {m['game_date']}")
