"""
Odds Scraper using The Odds API
Fetches QB passing TD prop odds (over 0.5 TDs) from sportsbooks
"""
import logging
import time
import sys
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import requests
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    ODDS_API_BASE_URL,
    ODDS_API_KEYS,
    ODDS_API_KEY_PAID,
    ODDS_SPORT,
    ODDS_REGIONS,
    ODDS_MARKETS,
    ODDS_MARKETS_FALLBACK,
    ODDS_BOOKMAKERS,
    REQUEST_TIMEOUT,
    DATA_DIR,
    ODDS_FILE_TEMPLATE,
    FREE_TIER_MAX_REQUESTS,
    PAID_TIER_MAX_REQUESTS
)
from utils.api_key_rotator import APIKeyRotator
from utils.week_manager import WeekManager

logger = logging.getLogger(__name__)


class OddsScraper:
    """Scrapes QB TD prop odds using The Odds API"""

    def __init__(self):
        """Initialize the odds scraper"""
        if not ODDS_API_KEYS:
            raise ValueError("No Odds API keys configured. Please set ODDS_API_KEY_1 through ODDS_API_KEY_6 in .env file")

        # Pass the paid key and limits to the rotator
        self.api_rotator = APIKeyRotator(
            ODDS_API_KEYS,
            paid_key=ODDS_API_KEY_PAID,
            free_tier_limit=FREE_TIER_MAX_REQUESTS,
            paid_tier_limit=PAID_TIER_MAX_REQUESTS
        )
        self.week_manager = WeekManager()

        free_count = len(ODDS_API_KEYS) - (1 if ODDS_API_KEY_PAID else 0)
        logger.info(f"Initialized with {len(ODDS_API_KEYS)} API keys ({free_count} free tier, {1 if ODDS_API_KEY_PAID else 0} paid tier)")

        # Check if paid key is available for player props
        if not ODDS_API_KEY_PAID:
            logger.warning("No paid tier API key configured - player props will not be available")
            logger.warning(f"Will use fallback market: {ODDS_MARKETS_FALLBACK}")

    def fetch_odds_by_market(self, market: str) -> Optional[List[Dict]]:
        """
        Fetch odds for a specific market from The Odds API

        Args:
            market: Market type (e.g., 'player_pass_tds', 'spreads', 'totals')

        Returns:
            List of odds data dictionaries or None if failed
        """
        logger.info(f"Fetching odds for market: {market}")

        # Determine which key to use based on market type
        player_prop_markets = ['player_pass_tds', 'alternate_spreads', 'alternate_totals']

        if market in player_prop_markets:
            # Player props and alternates require paid tier
            api_key = self.api_rotator.get_paid_key()
            if not api_key:
                logger.error(f"Paid tier API key required for {market} market")
                return None
        else:
            # Spreads, totals, h2h can use free tier
            api_key = self.api_rotator.get_next_key()
            if not api_key:
                logger.error("No available API keys (all exhausted)")
                return None

        # Build API request URL
        url = f"{ODDS_API_BASE_URL}/sports/{ODDS_SPORT}/odds"

        params = {
            'apiKey': api_key,
            'regions': ODDS_REGIONS,
            'markets': market,
            'bookmakers': ODDS_BOOKMAKERS,
            'oddsFormat': 'american'  # American odds format (e.g., -350)
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            # Increment API key usage
            self.api_rotator.increment_usage(api_key)

            # Parse response
            data = response.json()

            # Log remaining requests
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            logger.info(f"API request successful. Requests remaining for this key: {remaining}")

            # Return raw data (will be parsed by caller based on market type)
            logger.info(f"Successfully fetched {len(data)} games for {market} market")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching odds: {e}")
            return None

    def _parse_odds_response(self, data: List[Dict]) -> List[Dict]:
        """
        Parse The Odds API response to extract QB TD props

        Args:
            data: Raw API response data

        Returns:
            List of parsed odds dictionaries
        """
        odds_list = []

        for game in data:
            try:
                # Extract game info
                home_team = game.get('home_team', '')
                away_team = game.get('away_team', '')
                commence_time = game.get('commence_time', '')

                # Extract bookmaker odds
                bookmakers = game.get('bookmakers', [])

                for bookmaker in bookmakers:
                    bookmaker_name = bookmaker.get('title', '')

                    # Extract markets (player props)
                    markets = bookmaker.get('markets', [])

                    for market in markets:
                        if market.get('key') == ODDS_MARKETS:
                            # This is the QB passing TD market
                            outcomes = market.get('outcomes', [])

                            for outcome in outcomes:
                                player_name = outcome.get('description', '')
                                point = outcome.get('point', 0.5)  # Usually 0.5 for over/under 0.5 TDs
                                odds = outcome.get('price', None)
                                outcome_type = outcome.get('name', '')  # 'Over' or 'Under'

                                # We only want 'Over 0.5 TD' props
                                if outcome_type == 'Over' and point == 0.5:
                                    # Determine which team the QB plays for
                                    qb_team = self._determine_qb_team(player_name, home_team, away_team)

                                    odds_list.append({
                                        'qb_name': player_name,
                                        'team': qb_team,
                                        'opponent': away_team if qb_team == home_team else home_team,
                                        'odds_over_05_td': odds,
                                        'sportsbook': bookmaker_name,
                                        'game_time': commence_time
                                    })

            except Exception as e:
                logger.debug(f"Error parsing game odds: {e}")
                continue

        return odds_list

    def _determine_qb_team(self, qb_name: str, home_team: str, away_team: str) -> str:
        """
        Determine which team a QB plays for
        This is a simplified version - in production, you'd want a QB-to-team mapping

        Args:
            qb_name: Name of the quarterback
            home_team: Home team name
            away_team: Away team name

        Returns:
            Team name (best guess)
        """
        # For now, return empty - you'll need to implement team mapping
        # or fetch this from your QB stats data
        return ""

    def save_to_csv(self, odds_data: List[Dict], week: int) -> str:
        """
        Save odds data to CSV file

        Args:
            odds_data: List of odds dictionaries
            week: NFL week number

        Returns:
            Path to saved CSV file
        """
        df = pd.DataFrame(odds_data)

        filename = ODDS_FILE_TEMPLATE.format(week=week)
        filepath = DATA_DIR / filename

        df.to_csv(filepath, index=False)
        logger.info(f"Saved QB TD odds to {filepath}")

        return str(filepath)

    def fetch_player_props_for_all_events(self) -> List[Dict]:
        """
        Fetch player props for all NFL events
        Player props require per-event API calls

        Returns:
            List of player prop dictionaries
        """
        logger.info("Fetching events list to get player props...")

        # First, get all events
        events_url = f"{ODDS_API_BASE_URL}/sports/{ODDS_SPORT}/events"

        # Use paid key for player props
        api_key = self.api_rotator.get_paid_key()
        if not api_key:
            logger.error("Paid tier API key required for player props")
            return []

        try:
            response = requests.get(
                events_url,
                params={'apiKey': api_key},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            self.api_rotator.increment_usage(api_key)

            events = response.json()
            logger.info(f"Found {len(events)} upcoming NFL events")

            # Now fetch player props for each event
            all_props = []

            for event in events:
                event_id = event.get('id')
                home_team = event.get('home_team')
                away_team = event.get('away_team')
                commence_time = event.get('commence_time')

                logger.info(f"Fetching player props for {away_team} @ {home_team}...")

                # Get player props for this event
                event_props_url = f"{ODDS_API_BASE_URL}/sports/{ODDS_SPORT}/events/{event_id}/odds"

                params = {
                    'apiKey': api_key,
                    'regions': ODDS_REGIONS,
                    'markets': 'player_pass_tds',
                    'bookmakers': ODDS_BOOKMAKERS,
                    'oddsFormat': 'american'
                }

                try:
                    prop_response = requests.get(event_props_url, params=params, timeout=REQUEST_TIMEOUT)
                    prop_response.raise_for_status()
                    self.api_rotator.increment_usage(api_key)

                    event_data = prop_response.json()

                    # Parse player props from this event
                    props = self._parse_event_player_props(event_data)
                    all_props.extend(props)

                    logger.info(f"  ✓ Found {len(props)} QB props")

                except Exception as e:
                    logger.warning(f"  ✗ Failed to fetch props for this event: {e}")
                    continue

            return all_props

        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def _parse_event_player_props(self, event_data: Dict) -> List[Dict]:
        """
        Parse player props from a single event response

        Args:
            event_data: API response for a single event

        Returns:
            List of player prop dictionaries
        """
        props_list = []

        home_team = event_data.get('home_team', '')
        away_team = event_data.get('away_team', '')
        commence_time = event_data.get('commence_time', '')

        # Calculate week from commence_time instead of using parameter
        calculated_week = None
        if commence_time:
            try:
                # Parse ISO 8601 datetime string
                game_datetime = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                calculated_week = self.week_manager.calculate_week_from_game_date(game_datetime)
                logger.debug(f"Calculated week {calculated_week} from commence_time {commence_time}")
            except Exception as e:
                logger.warning(f"Could not parse commence_time '{commence_time}': {e}")

        bookmakers = event_data.get('bookmakers', [])

        for bookmaker in bookmakers:
            bookmaker_name = bookmaker.get('title', '')
            markets = bookmaker.get('markets', [])

            for market in markets:
                if market.get('key') == 'player_pass_tds':
                    outcomes = market.get('outcomes', [])

                    # Group by player (over/under pairs)
                    player_props = {}

                    for outcome in outcomes:
                        qb_name = outcome.get('description', '')
                        over_under = outcome.get('name', '')
                        point = outcome.get('point', 0)
                        price = outcome.get('price', 0)

                        if over_under == 'Over' and point == 0.5:
                            # This is "Over 0.5 TDs" which we want
                            if qb_name not in player_props:
                                player_props[qb_name] = {}

                            player_props[qb_name]['qb_name'] = qb_name
                            player_props[qb_name]['odds_over_05_td'] = price
                            player_props[qb_name]['sportsbook'] = bookmaker_name
                            player_props[qb_name]['game'] = f"{away_team} @ {home_team}"
                            player_props[qb_name]['home_team'] = home_team
                            player_props[qb_name]['away_team'] = away_team
                            player_props[qb_name]['game_time'] = commence_time
                            if calculated_week is not None:
                                player_props[qb_name]['week'] = calculated_week

                    props_list.extend(player_props.values())

        return props_list

    def fetch_all_odds(self, week: int) -> Dict[str, Optional[str]]:
        """
        Fetch all odds markets and save to separate CSV files

        Args:
            week: NFL week number

        Returns:
            Dictionary mapping market type to saved file path
        """
        results = {}

        # Market configurations
        markets_to_fetch = {
            'spreads': 'odds_spreads_week_{week}.csv',
            'totals': 'odds_totals_week_{week}.csv',
        }

        # Fetch regular markets (spreads, totals)
        for market, filename_template in markets_to_fetch.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Fetching {market} market")
            logger.info(f"{'='*60}")

            odds_data = self.fetch_odds_by_market(market)

            if odds_data and len(odds_data) > 0:
                # Parse and save based on market type
                if market in ['spreads', 'totals']:
                    parsed_data = self._parse_game_lines(odds_data, market)
                else:
                    parsed_data = odds_data

                if parsed_data:
                    filename = filename_template.format(week=week)
                    filepath = DATA_DIR / filename
                    df = pd.DataFrame(parsed_data)
                    df.to_csv(filepath, index=False)
                    logger.info(f"✓ Saved {len(parsed_data)} records to {filepath}")
                    results[market] = str(filepath)
                else:
                    logger.warning(f"✗ No data parsed for {market}")
                    results[market] = None
            else:
                logger.warning(f"✗ Failed to fetch {market}")
                results[market] = None

        # Fetch player props (requires per-event fetching)
        logger.info(f"\n{'='*60}")
        logger.info(f"Fetching player_pass_tds market (per-event)")
        logger.info(f"{'='*60}")

        player_props = self.fetch_player_props_for_all_events()

        if player_props and len(player_props) > 0:
            filename = 'odds_qb_td_week_{week}.csv'.format(week=week)
            filepath = DATA_DIR / filename
            df = pd.DataFrame(player_props)
            df.to_csv(filepath, index=False)
            logger.info(f"✓ Saved {len(player_props)} QB TD props to {filepath}")
            results['player_pass_tds'] = str(filepath)
        else:
            logger.warning(f"✗ No player props data found")
            results['player_pass_tds'] = None

        return results

    def _parse_game_lines(self, data: List[Dict], market_type: str) -> List[Dict]:
        """
        Parse spreads or totals from The Odds API response

        Args:
            data: Raw API response data
            market_type: 'spreads' or 'totals'

        Returns:
            List of parsed game line dictionaries
        """
        lines_list = []

        for game in data:
            try:
                home_team = game.get('home_team', '')
                away_team = game.get('away_team', '')
                commence_time = game.get('commence_time', '')

                bookmakers = game.get('bookmakers', [])

                for bookmaker in bookmakers:
                    bookmaker_name = bookmaker.get('title', '')
                    markets = bookmaker.get('markets', [])

                    for market in markets:
                        if market.get('key') == market_type:
                            outcomes = market.get('outcomes', [])

                            if market_type == 'spreads':
                                # Spreads have outcomes for each team
                                for outcome in outcomes:
                                    team = outcome.get('name', '')
                                    point = outcome.get('point', 0)
                                    price = outcome.get('price', 0)

                                    lines_list.append({
                                        'game': f"{away_team} @ {home_team}",
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'team': team,
                                        'spread': point,
                                        'odds': price,
                                        'sportsbook': bookmaker_name,
                                        'game_time': commence_time
                                    })

                            elif market_type == 'totals':
                                # Totals have Over/Under outcomes
                                for outcome in outcomes:
                                    over_under = outcome.get('name', '')  # 'Over' or 'Under'
                                    point = outcome.get('point', 0)
                                    price = outcome.get('price', 0)

                                    lines_list.append({
                                        'game': f"{away_team} @ {home_team}",
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'total': point,
                                        'over_under': over_under,
                                        'odds': price,
                                        'sportsbook': bookmaker_name,
                                        'game_time': commence_time
                                    })

            except Exception as e:
                logger.debug(f"Error parsing game line: {e}")
                continue

        return lines_list

    def run(self, week: int) -> Optional[Dict[str, str]]:
        """
        Run the complete odds fetching workflow (fetches all markets)

        Args:
            week: NFL week number

        Returns:
            Dictionary with market names and their CSV file paths, or None if failed
        """
        # Fetch all markets (spreads, totals, player props)
        results = self.fetch_all_odds(week)

        if results and all(results.values()):
            # Return the dictionary of file paths
            return results

        logger.error("Failed to fetch all odds data")
        return None

    def get_usage_report(self) -> Dict:
        """
        Get API usage statistics

        Returns:
            Dictionary with usage stats
        """
        return self.api_rotator.get_status_report()


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

    try:
        scraper = OddsScraper()

        # Show initial status
        status = scraper.get_usage_report()
        print(f"\nAPI Keys available: {status['total_keys']}")
        print(f"Total requests remaining: {status['remaining_requests']}\n")

        # Fetch ALL odds data
        results = scraper.fetch_all_odds(week)

        # Show results
        print(f"\n{'='*60}")
        print("ODDS DATA COLLECTION SUMMARY")
        print(f"{'='*60}")

        success_count = sum(1 for path in results.values() if path)
        total_count = len(results)

        for market, filepath in results.items():
            status_icon = "✓" if filepath else "✗"
            print(f"{status_icon} {market:20s}: {filepath if filepath else 'FAILED'}")

        # Show final API usage
        final_status = scraper.get_usage_report()
        print(f"\n{'='*60}")
        print("API USAGE")
        print(f"{'='*60}")
        print(f"Requests used: {final_status['total_requests']}")
        print(f"Requests remaining: {final_status['remaining_requests']}")
        print(f"{'='*60}\n")

        if success_count == total_count:
            print(f"✓ SUCCESS: All {total_count} markets fetched successfully!")
            sys.exit(0)
        elif success_count > 0:
            print(f"⚠ PARTIAL: {success_count}/{total_count} markets fetched")
            sys.exit(0)
        else:
            print(f"✗ FAILED: No markets fetched successfully")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
