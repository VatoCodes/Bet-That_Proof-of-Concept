# Edges Tab UI Changes - Quick Reference

## What Changed

### Filter Section
**Before:**
```
Week | Model (v1/v2) | Min Edge (%) | Export CSV
```

**After:**
```
Week | Min Edge (%) | Export CSV
```
- Removed the non-functional Model dropdown
- The model/version selection moved to the strategy tabs below

---

## Strategy Tabs (NEW)

The Edges tab now displays **5 strategy tabs** instead of 4:

### Desktop View (Horizontal Tabs)
```
┌─────────────┬─────────────┬──────────┬──────────┬──────────┐
│ All Strat.  │ First Half  │ QB TD v1 │ QB TD v2 │ Kicker   │
│ (Total)     │ Total (3)   │ (12)     │ (8)      │ (0)      │
└─────────────┴─────────────┴──────────┴──────────┴──────────┘
```

### Mobile View (Stacked)
```
┌─────────────────────────┐
│ All Strategies     (23) │
├─────────────────────────┤
│ First Half Total   (3)  │
├─────────────────────────┤
│ QB TD 0.5+ (v1)   (12)  │
├─────────────────────────┤
│ QB TD 0.5+ (v2)    (8)  │
├─────────────────────────┤
│ Kicker Points      (0)  │
└─────────────────────────┘
```

---

## Tab Descriptions

When you click on a tab, a colored info box appears below explaining that strategy:

### QB TD 0.5+ (v1) Tab
```
ℹ️ QB TD 0.5+ (Simple v1): Baseline model using 60% QB
   performance + 40% defense weakness. Win rate target: 90%.
   More edges (10-15/week) but lower confidence.
```

### QB TD 0.5+ (v2) Tab
```
ℹ️ QB TD 0.5+ (Enhanced v2): Advanced model with red zone
   accuracy and defensive strength analysis. Win rate target: 95%+.
   More selective (5-10/week) with higher confidence.
```

---

## Edge Cards Display

### v1 Edges
Each card shows:
- Matchup: "Patrick Mahomes vs Kansas City Chiefs"
- Strategy badge: "QB TD 0.5+ (Simple v1)" (blue)
- Line: "0.5"
- Recommendation: "OVER 0.5 TD"
- Edge: "8.5%" (blue/yellow/green based on size)
- Confidence: "MEDIUM"
- Reasoning: "Patrick Mahomes has true probability of 75% vs market implied probability of 66.5%..."

### v2 Edges
Same as v1, PLUS a comparison box:
```
┌──────────────────────────────────────────┐
│ v1 Edge: 8.5% → v2 Edge: 9.2%            │
│ (+0.7% improvement)                      │
│                                          │
│ Red Zone TD Rate: 18.2%                  │
└──────────────────────────────────────────┘
```

This box shows:
- Original v1 edge percentage
- Enhanced v2 edge percentage
- The improvement (or reduction) from adjustments
- Red zone efficiency percentage

---

## Badge Counts Explained

The number next to each tab shows edges available for that strategy:

```
All Strategies (23)     = Total edges across all strategies
First Half Total (3)    = 3 qualifying First Half Under edges
QB TD 0.5+ (v1) (12)    = 12 QB TD edges using simple model
QB TD 0.5+ (v2) (8)     = 8 QB TD edges using enhanced model
Kicker Points (0)       = 0 kicker edges (data pending)
```

**Example:** If there are 15 QB TDs detected, v1 shows all 15, but v2 (more selective) shows 8.

---

## CSV Export

The export filename now includes the strategy:
```
Before: edges_week5_v2.csv
After:  edges_week5_qb_td_v1.csv  (when exporting from v1 tab)
        edges_week5_qb_td_v2.csv  (when exporting from v2 tab)
        edges_week5_all.csv       (when exporting from All tab)
```

---

## Key Differences at a Glance

| Aspect | v1 | v2 |
|--------|----|----|
| Tab Label | QB TD 0.5+ (v1) | QB TD 0.5+ (v2) |
| Strategy Name | Simple v1 | Enhanced v2 |
| Edges per Week | 10-15 | 5-10 |
| Confidence | Always MEDIUM | Dynamic (HIGH/MED/LOW) |
| Shows v1 Comparison | No | Yes |
| Red Zone Data | No | Yes |
| Defense Quality Analysis | No | Yes |

---

## Example Workflow

### Finding Your Best Edges
1. Click "QB TD 0.5+ (v2)" tab → See 8 high-confidence edges
2. Click "QB TD 0.5+ (v1)" tab → See 12 total edges
3. Compare the two lists:
   - Edges in both? Very likely to be good
   - Edges only in v1? Lower confidence, more speculative
   - Edges only in v2? High-confidence additions from advanced metrics

### Exporting Data
1. Select week using the filter
2. Click desired tab (v1, v2, or All)
3. Click "📊 Export CSV"
4. Filename shows which strategy was exported

---

## Technical Notes

### Backend
- `/api/edges?week=1&strategy=qb_td_v1` → v1 edges
- `/api/edges?week=1&strategy=qb_td_v2` → v2 edges
- `/api/edges?week=1&strategy=all` → both v1 and v2

### Edge Counts API
- `/api/edges/counts?week=1` returns: `{first_half: 3, qb_td_v1: 12, qb_td_v2: 8, total: 23}`

### Legacy Support
Old API calls with `?model=v1` or `?model=v2` still work (automatically mapped to strategies)

---

## Summary

The Edges tab is now **more transparent and powerful**:
- ✅ Both v1 and v2 are equally visible
- ✅ Clear explanations of what each model does
- ✅ Easy comparison between models
- ✅ Better data for decision-making
- ✅ No confusion about why edges appear/disappear
