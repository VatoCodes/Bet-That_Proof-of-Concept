# Complete Odds Data Collection - Ready to Use

## What We Built

Your system now fetches **ALL the odds data you need** for both betting strategies:

### Data Collection Capabilities

| Market | Data Type | CSV Output | API Tier | Status |
|--------|-----------|------------|----------|--------|
| `player_pass_tds` | QB TD Props (O/U 0.5) | `odds_qb_td_week_X.csv` | Paid | ✅ Ready |
| `spreads` | Point Spreads | `odds_spreads_week_X.csv` | Free/Paid | ✅ Ready |
| `totals` | Over/Under Totals | `odds_totals_week_X.csv` | Free/Paid | ✅ Ready |

## How to Use

### Quick Start (Fetch All Odds Data)

```bash
# Make sure your paid API key is in .env
python3 scrapers/odds_scraper.py 7
```

This will fetch and save:
1. **QB TD Props** → `data/raw/odds_qb_td_week_7.csv`
2. **Spreads** → `data/raw/odds_spreads_week_7.csv`
3. **Totals** → `data/raw/odds_totals_week_7.csv`

### What You'll Get

**1. QB TD Props (`odds_qb_td_week_7.csv`)**
```csv
qb_name,team,opponent,odds_over_05_td,sportsbook,game_time
Patrick Mahomes,Chiefs,Giants,-420,DraftKings,2025-10-27T13:00:00Z
Joe Burrow,Bengals,Panthers,-380,DraftKings,2025-10-27T13:00:00Z
```

**2. Spreads (`odds_spreads_week_7.csv`)**
```csv
game,home_team,away_team,team,spread,odds,sportsbook,game_time
Chiefs vs Giants,Chiefs,Giants,Chiefs,-7.0,-110,DraftKings,2025-10-27T13:00:00Z
Chiefs vs Giants,Chiefs,Giants,Giants,7.0,-110,DraftKings,2025-10-27T13:00:00Z
```

**3. Totals (`odds_totals_week_7.csv`)**
```csv
game,home_team,away_team,total,over_under,odds,sportsbook,game_time
Chiefs vs Giants,Chiefs,Giants,48.5,Over,-110,DraftKings,2025-10-27T13:00:00Z
Chiefs vs Giants,Chiefs,Giants,48.5,Under,-110,DraftKings,2025-10-27T13:00:00Z
```

## Complete Data Set

After running the scraper, you'll have ALL the data needed for your strategies:

```
data/raw/
├── defense_stats_week_7.csv      ✅ (Defense Pass TDs allowed)
├── qb_stats_2025.csv             ✅ (QB passing stats)
├── matchups_week_7.csv           ✅ (This week's games)
├── odds_qb_td_week_7.csv         🔜 (QB TD prop odds - needs paid API)
├── odds_spreads_week_7.csv       🔜 (Point spreads - needs API)
└── odds_totals_week_7.csv        🔜 (Over/under totals - needs API)
```

## Setup Required

### Add Your Paid API Key

```bash
# Edit .env file
nano .env

# Add your paid tier key (replace the placeholder):
ODDS_API_KEY_PAID=your_actual_paid_api_key_here
```

### Test the System

```bash
# Test all markets
python3 scrapers/odds_scraper.py 7

# You should see:
# ✓ player_pass_tds: /path/to/odds_qb_td_week_7.csv
# ✓ spreads: /path/to/odds_spreads_week_7.csv
# ✓ totals: /path/to/odds_totals_week_7.csv
```

## API Usage & Costs

### Per Weekly Run:
- **QB TD Props**: ~1-10 requests (paid key)
- **Spreads**: ~1-5 requests (can use free keys)
- **Totals**: ~1-5 requests (can use free keys)
- **Total**: ~3-20 requests per week

### Monthly Usage Estimate:
- 4 weeks × 20 requests = **~80 requests/month**
- Your paid tier limit: **20,000 requests/month**
- **Utilization: <0.5%** (plenty of headroom!)

## Strategy Support

### QB TD Edge Strategy (Phase 1)
**Data Needed:**
- ✅ Defense stats (Pass TDs allowed)
- ✅ QB stats (TD history)
- ✅ Matchups (who plays who)
- ✅ QB TD odds (over 0.5 TDs) ← `odds_qb_td_week_7.csv`

### Key Numbers Strategy (Phase 2)
**Data Needed:**
- ✅ Spreads ← `odds_spreads_week_7.csv`
- ✅ Totals ← `odds_totals_week_7.csv`
- Find value in key numbers (3, 7, 10 for spreads; 41, 44, 47 for totals)

## Troubleshooting

### "422 Client Error" for player_pass_tds
- **Cause**: API doesn't support player props yet for upcoming games
- **Solution**: Player props usually become available closer to game time (Thursdays/Fridays)
- **Alternative**: Run scraper on Thursday/Friday when props are posted

### "No data" for spreads/totals
- **Cause**: Lines not posted yet for future games
- **Solution**: Run closer to game day when sportsbooks post lines

### "Paid tier API key required"
- **Cause**: `ODDS_API_KEY_PAID` not set in `.env`
- **Solution**: Add your paid API key to `.env` file

## Integration with Main Pipeline

The main pipeline (`main.py`) can be updated to use the new multi-market scraper:

```python
# In main.py, the odds scraper will automatically fetch all markets
python3 main.py --odds-only  # Fetches QB TD, spreads, and totals
```

## Next Steps

1. **Add your paid API key** to `.env`
2. **Test on Thursday/Friday** when odds are available
3. **Verify CSV outputs** match your analysis needs
4. **Build your edge detection algorithms** using the complete dataset

---

**You now have everything needed to collect all betting odds data automatically!** 🎉
