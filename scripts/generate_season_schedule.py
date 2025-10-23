"""
Generate full NFL season schedule from ESPN API
Run once per season to create hardcoded schedule JSON
"""

import requests
import json
from pathlib import Path
from datetime import datetime

def generate_season_schedule(season_year=2025):
    """Generate complete season schedule from ESPN API"""

    schedule = {
        "season": season_year,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "ESPN API",
        "weeks": {}
    }

    print(f"\nGenerating {season_year} NFL Season Schedule")
    print("=" * 60)

    # Scrape all 18 weeks
    for week in range(1, 19):
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&seasontype=2&dates={season_year}"

        try:
            print(f"Fetching Week {week}...", end=" ")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            week_matchups = []
            for event in data.get('events', []):
                try:
                    competition = event['competitions'][0]
                    competitors = competition['competitors']

                    home_team = None
                    away_team = None

                    for comp in competitors:
                        team_name = comp['team']['displayName']
                        if comp['homeAway'] == 'home':
                            home_team = team_name
                        else:
                            away_team = team_name

                    game_date = event['date'][:10]  # YYYY-MM-DD
                    game_time = event['date'][11:19]  # HH:MM:SS

                    if home_team and away_team:
                        week_matchups.append({
                            'home_team': home_team,
                            'away_team': away_team,
                            'game_date': game_date,
                            'game_time': game_time,
                            'week': week
                        })
                except (KeyError, IndexError) as e:
                    print(f"\n  Warning: Could not parse event: {e}")
                    continue

            schedule['weeks'][str(week)] = week_matchups
            print(f"✓ {len(week_matchups)} games")

        except Exception as e:
            print(f"✗ Error: {e}")
            schedule['weeks'][str(week)] = []

    # Save to file
    output_file = Path("data/schedules/nfl_2025_schedule.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(schedule, f, indent=2)

    print("\n" + "=" * 60)
    print(f"✓ Schedule saved to {output_file}")

    # Print summary
    total_games = sum(len(games) for games in schedule['weeks'].values())
    print(f"✓ Total games: {total_games}")
    print(f"✓ Weeks with data: {sum(1 for games in schedule['weeks'].values() if games)}/18")
    print("=" * 60 + "\n")

    return schedule


if __name__ == "__main__":
    import sys

    season_year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    generate_season_schedule(season_year)
