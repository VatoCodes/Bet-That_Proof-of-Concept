# QB TD Player Props - Quick Setup Guide

## TL;DR

✅ **Paid API key required for QB TD props**
✅ **20,000 requests/month limit**
✅ **System automatically uses paid key for player props**

## Setup (2 minutes)

1. **Add your paid API key to `.env`:**
   ```bash
   ODDS_API_KEY_PAID=your_actual_paid_key_here
   ```

2. **That's it!** The system will automatically:
   - Use your paid key for QB TD props (player_pass_tds market)
   - Track usage against the 20K/month limit
   - Warn you if approaching the limit

## Usage

```bash
# Fetch QB TD props for current week
python3 main.py --odds-only

# Full pipeline (stats + QB TD props)
python3 main.py --week 8
```

## What You'll Get

The odds scraper will fetch:
- **QB Name**: e.g., "Patrick Mahomes"
- **Team**: e.g., "Chiefs"
- **Opponent**: e.g., "Giants"
- **Odds (Over 0.5 TD)**: e.g., "-420" (DraftKings/FanDuel)
- **Game Time**: When the game starts

## Request Usage

**Typical weekly workflow:**
- Thursday evening: Fetch QB TD props → ~10-50 requests
- Sunday morning: Re-fetch for line movement → ~10-50 requests
- **Total**: ~20-100 requests/week
- **Monthly**: ~80-400 requests (way under 20K limit)

## Monitoring Usage

Check your usage anytime:

```python
from scrapers.odds_scraper import OddsScraper

scraper = OddsScraper()
status = scraper.get_usage_report()
print(f"Paid key used: {status['total_requests']} / 20,000")
```

Or check the logs:
```bash
tail -f data/scraper.log | grep "PAID tier"
```

You'll see logs like:
```
Using PAID tier API key for player props (used 45/20,000)
```

## Free Tier Keys (Optional)

The 6 free tier keys are **optional** for your use case. They're only useful if you want to fetch:
- Game moneylines (h2h)
- Spreads
- Totals

For QB TD props specifically, you only need the paid key.

## Troubleshooting

**"No paid tier API key available - player props require paid tier"**
→ Add `ODDS_API_KEY_PAID` to your `.env` file

**"Paid tier API key has reached monthly limit (20,000 requests)"**
→ Wait for monthly reset or upgrade your plan

**"API request failed: 422 Client Error"**
→ Check that your paid key is valid and active

## Cost vs Value

**Your paid API tier:**
- Limit: 20,000 requests/month
- Your usage: ~400 requests/month (conservative estimate)
- **Utilization: ~2% of your limit**

You have plenty of headroom for:
- ✅ Multiple daily updates
- ✅ Line movement tracking
- ✅ Historical data collection
- ✅ Experimenting with different markets

---

**Questions?** Check `PAID_API_SETUP.md` for detailed documentation.
