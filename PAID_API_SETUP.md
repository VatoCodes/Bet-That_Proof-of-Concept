# Setting Up Paid API Key for Player Props

## Overview

**IMPORTANT:** QB TD player props require a **paid tier API key**.

Your system is configured to:
1. **Always use PAID key for player props** (QB TD over/under 0.5)
2. **Use free tier keys for game lines** (spreads, totals, moneylines) if needed
3. **Paid tier limit: 20,000 requests/month**

### Why Paid Tier is Required

- **Player props (player_pass_tds)** = Paid tier only
- **Game lines (h2h, spreads, totals)** = Free tier available
- The system will **automatically use your paid key** when fetching QB TD odds

## How to Configure Your .env File

Open your `.env` file and add your paid API key:

```bash
# The Odds API Keys - Free Tier (500 requests/month each)
# These will be used first to maximize free tier usage
ODDS_API_KEY_1=4ca910d2311753e38ea231e015144a3e
ODDS_API_KEY_2=921268942df80267cd852ad5d867d3e5
ODDS_API_KEY_3=b148d8971076ecd9fbe9abd5ffb5f709
ODDS_API_KEY_4=464120bb51ecae963284c5fc51f5cdb8
ODDS_API_KEY_5=10ce170b84f1c6fb0592ff6496cbd74b
ODDS_API_KEY_6=b417c3191e041c940bdcfc774d4e593a

# Paid Tier API Key (Fallback)
# Replace YOUR_PAID_TIER_KEY_HERE with your actual paid tier key
ODDS_API_KEY_PAID=YOUR_PAID_TIER_KEY_HERE
```

## How It Works

### Priority System

1. **Keys 1-6** (Free tier): Used first, 500 requests each
2. **Paid Key** (Last): Used only after all free keys hit 500 requests

### API Usage Flow

**For QB TD Player Props (player_pass_tds):**
```
ALL requests use ODDS_API_KEY_PAID (20K limit/month)
```

**For Game Lines (h2h, spreads, totals) - if you use them:**
```
Request 1-500:    Uses ODDS_API_KEY_1 (free)
Request 501-1000: Uses ODDS_API_KEY_2 (free)
Request 1001-1500: Uses ODDS_API_KEY_3 (free)
Request 1501-2000: Uses ODDS_API_KEY_4 (free)
Request 2001-2500: Uses ODDS_API_KEY_5 (free)
Request 2501-3000: Uses ODDS_API_KEY_6 (free)
Request 3001+:    Uses ODDS_API_KEY_PAID (if free keys exhausted)
```

### Logging

The system will log which type of key is being used:

```
- "Using FREE tier API key index 0 (used 245/500)"
- "Using FREE tier API key index 1 (used 12/500)"
- "Using PAID tier API key (unlimited requests, 45 used so far)"
```

## Testing

Test the configuration:

```bash
# Test odds scraper (will use free keys first)
python3 scrapers/odds_scraper.py 7

# Full pipeline
python3 main.py --week 7
```

## Cost Optimization

### To maximize free tier usage:

1. **Monday-Thursday**: Run stats collection (no API calls needed)
   ```bash
   python3 main.py --stats-only
   ```

2. **Thursday/Friday**: Run odds collection (uses API keys)
   ```bash
   python3 main.py --odds-only
   ```

3. **Monitor usage**:
   - Free tier: 3,000 requests/month total
   - Each weekly odds fetch ≈ 10-50 requests depending on games
   - You can run ~60-300 odds fetches per month on free tier alone

### Monthly Request Estimate

**For QB TD Player Props (your primary use case):**

- **Scenario 1**: Weekly odds fetch (Thursday/Sunday)
  - 2 fetches/week × 4 weeks = ~8 API calls/month
  - Each call fetches all QB props for the week
  - **Usage**: ~8-80 requests/month (well under 20K limit)

- **Scenario 2**: Daily odds monitoring
  - 1 fetch/day × 30 days = ~30 API calls/month
  - **Usage**: ~30-300 requests/month (still well under 20K)

- **Scenario 3**: Multiple daily updates (morning, afternoon, evening)
  - 3 fetches/day × 30 days = ~90 API calls/month
  - **Usage**: ~90-900 requests/month (easily within 20K limit)

**Bottom line:** Your paid tier key (20K requests/month) should handle:
- ✅ Daily QB TD prop monitoring
- ✅ Multiple daily updates if needed
- ✅ Full season coverage with room to spare

## Important Notes

- **Paid tier limit**: 20,000 requests/month (not unlimited)
- **Player props ALWAYS use paid key** - free keys won't work for QB TD props
- **Free keys are optional** - only needed if you want game lines (h2h, spreads, totals)
- **All limits reset monthly** by The Odds API
- The system **logs all usage** to help you track consumption
- **If paid key hits 20K limit**, the scraper will warn you and stop

## Questions?

Check the logs to see which keys are being used:
```bash
tail -f data/scraper.log | grep "API key"
```

Or check usage programmatically:
```python
from scrapers.odds_scraper import OddsScraper

scraper = OddsScraper()
status = scraper.get_usage_report()
print(status)
```

---

**Ready to use!** Just add your paid API key to `.env` and you're all set.
