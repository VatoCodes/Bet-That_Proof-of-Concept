"""
Matchups Scraper for ESPN NFL Schedule
Scrapes current week's NFL matchups
"""
import logging
import time
import sys
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    ESPN_SCHEDULE_URL,
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    DATA_DIR,
    MATCHUPS_FILE_TEMPLATE
)
from utils.week_manager import WeekManager

logger = logging.getLogger(__name__)


class MatchupsScraper:
    """Scrapes NFL matchups from ESPN schedule"""

    def __init__(self):
        """Initialize the matchups scraper"""
        self.url = ESPN_SCHEDULE_URL
        self.headers = {"User-Agent": USER_AGENT}
        self.week_manager = WeekManager()

    def scrape(self, week: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Scrape matchups from ESPN schedule

        Args:
            week: Specific week number to scrape (optional)

        Returns:
            DataFrame with matchups or None if failed
        """
        url = f"{self.url}/_/week/{week}" if week else self.url
        logger.info(f"Scraping matchups from {url}")

        try:
            # Make request with delay to be polite
            time.sleep(REQUEST_DELAY)
            response = requests.get(
                url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract matchups
            matchups = self._parse_matchups(soup, week)

            if not matchups:
                logger.error("No matchups found on page")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(matchups)

            logger.info(f"Successfully scraped {len(df)} matchups")
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            return None

    def _parse_matchups(self, soup: BeautifulSoup, week: Optional[int]) -> List[Dict]:
        """
        Parse matchups from ESPN schedule page

        Args:
            soup: BeautifulSoup object of the page
            week: Week number

        Returns:
            List of matchup dictionaries
        """
        matchups = []

        # ESPN schedule structure: Look for game containers
        # This structure may vary, so we'll try multiple approaches

        # Approach 1: Find schedule tables or game containers
        schedule_section = soup.find('div', class_='ScheduleTables')

        if not schedule_section:
            # Approach 2: Try finding individual games
            schedule_section = soup.find('section', class_='Schedule')

        if not schedule_section:
            logger.warning("Could not find schedule section, trying alternative parsing")
            return self._parse_matchups_alternative(soup, week)

        # Find all game entries
        games = schedule_section.find_all('div', class_='Table__TR')

        if not games:
            games = schedule_section.find_all('tr', class_='Table__TR')

        for game in games:
            try:
                # Extract team names
                teams = game.find_all('span', class_='Table__Team')

                if len(teams) < 2:
                    # Try alternative structure
                    teams = game.find_all('div', class_='ScoreCell__TeamName')

                if len(teams) >= 2:
                    away_team = teams[0].get_text(strip=True)
                    home_team = teams[1].get_text(strip=True)

                    # Extract date (if available)
                    date_elem = game.find('span', class_='Table__GameDate')
                    if not date_elem:
                        date_elem = game.find('div', class_='ScoreCell__GameDate')

                    game_date_str = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime('%Y-%m-%d')

                    # Calculate week from game date instead of trusting parameter
                    try:
                        # Parse the date string to datetime
                        game_date = datetime.strptime(game_date_str, '%Y-%m-%d')
                        calculated_week = self.week_manager.calculate_week_from_game_date(game_date)
                        logger.debug(f"Calculated week {calculated_week} from game date {game_date_str}")
                    except Exception as e:
                        # Fall back to provided week if date parsing fails
                        logger.warning(f"Could not parse game date '{game_date_str}', using provided week {week}: {e}")
                        calculated_week = week

                    matchups.append({
                        'week': calculated_week,
                        'home_team': self._clean_team_name(home_team),
                        'away_team': self._clean_team_name(away_team),
                        'game_date': game_date_str
                    })
            except Exception as e:
                logger.debug(f"Error parsing game: {e}")
                continue

        return matchups

    def _parse_matchups_alternative(self, soup: BeautifulSoup, week: Optional[int]) -> List[Dict]:
        """
        Alternative parsing method for ESPN schedule

        Args:
            soup: BeautifulSoup object
            week: Week number

        Returns:
            List of matchup dictionaries
        """
        matchups = []

        # Look for team abbreviations in schedule
        team_links = soup.find_all('a', class_='AnchorLink')

        teams_in_games = []
        for link in team_links:
            if '/nfl/team/' in link.get('href', ''):
                team_name = link.get_text(strip=True)
                teams_in_games.append(team_name)

        # Group teams into pairs (away vs home)
        for i in range(0, len(teams_in_games) - 1, 2):
            if i + 1 < len(teams_in_games):
                # Use current date to calculate week
                current_date = datetime.now()
                calculated_week = self.week_manager.calculate_week_from_game_date(current_date)

                matchups.append({
                    'week': calculated_week,
                    'home_team': self._clean_team_name(teams_in_games[i+1]),
                    'away_team': self._clean_team_name(teams_in_games[i]),
                    'game_date': current_date.strftime('%Y-%m-%d')
                })

        return matchups

    def _clean_team_name(self, team_name: str) -> str:
        """
        Clean and standardize team names

        Args:
            team_name: Raw team name from ESPN

        Returns:
            Cleaned team name
        """
        # Remove extra whitespace
        team_name = team_name.strip()

        # Team name mappings (ESPN abbreviations to full names)
        team_mapping = {
            'ARI': 'Cardinals',
            'ATL': 'Falcons',
            'BAL': 'Ravens',
            'BUF': 'Bills',
            'CAR': 'Panthers',
            'CHI': 'Bears',
            'CIN': 'Bengals',
            'CLE': 'Browns',
            'DAL': 'Cowboys',
            'DEN': 'Broncos',
            'DET': 'Lions',
            'GB': 'Packers',
            'HOU': 'Texans',
            'IND': 'Colts',
            'JAX': 'Jaguars',
            'KC': 'Chiefs',
            'LAC': 'Chargers',
            'LAR': 'Rams',
            'LV': 'Raiders',
            'MIA': 'Dolphins',
            'MIN': 'Vikings',
            'NE': 'Patriots',
            'NO': 'Saints',
            'NYG': 'Giants',
            'NYJ': 'Jets',
            'PHI': 'Eagles',
            'PIT': 'Steelers',
            'SEA': 'Seahawks',
            'SF': '49ers',
            'TB': 'Buccaneers',
            'TEN': 'Titans',
            'WAS': 'Commanders'
        }

        return team_mapping.get(team_name, team_name)

    def save_to_csv(self, df: pd.DataFrame, week: int) -> str:
        """
        Save DataFrame to CSV file

        Args:
            df: DataFrame with matchups
            week: NFL week number

        Returns:
            Path to saved CSV file
        """
        filename = MATCHUPS_FILE_TEMPLATE.format(week=week)
        filepath = DATA_DIR / filename

        df.to_csv(filepath, index=False)
        logger.info(f"Saved matchups to {filepath}")

        return str(filepath)

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


def main():
    """Main function for testing"""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get week from command line or default to current week from WeekManager
    if len(sys.argv) > 1:
        week = int(sys.argv[1])
    else:
        week_manager = WeekManager()
        week = week_manager.get_current_week()
        logger.info(f"Using current week from WeekManager: {week}")

    scraper = MatchupsScraper()
    result = scraper.run(week)

    if result:
        print(f"Success! Saved to: {result}")
    else:
        print("Failed to scrape matchups")
        sys.exit(1)


if __name__ == "__main__":
    main()
