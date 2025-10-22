# QB TD 0.5+ Edge Models: v1 vs v2 Comparison

## Overview

The NFL Edge Finder dashboard now displays **both v1 and v2 QB TD edge opportunities** as separate strategy tabs, allowing you to compare the two models side-by-side. This document explains why they exist, how they differ, and their respective confidence levels.

## What Changed

### Before
- Only "QB TD 0.5+ (v2)" edges were visible
- Removed the non-functional "Model" dropdown that confused users
- v1 was hidden - only used internally as a baseline for v2 calculations

### After
- **Two separate tabs**: "QB TD 0.5+ (v1)" and "QB TD 0.5+ (v2)"
- Each tab shows distinct edge opportunities from that specific model
- Clear descriptions explain the differences between models
- Both models are now available for comparison and analysis

## Model Comparison

### v1: Simple Model (Baseline)

**Formula:**
```
base_prob = (QB_TD_per_game × 0.6) + (Defense_TDs_allowed_per_game × 0.4)
adjusted_prob = base_prob × (1 + home_field_bonus)
true_probability = adjusted_prob × 0.6  (clamped to 5%-95%)
```

**Confidence Level:**
- Always "MEDIUM" - no variance based on edge strength or other factors

**Expected Output:**
- 10-15 edges per week (more liberal threshold)
- Target win rate: ~90%
- Simple, explainable logic

**Why Use v1:**
- More opportunities to find edges
- Good starting point for analysis
- Easy to understand and verify calculations manually
- Baseline for understanding market inefficiencies

---

### v2: Enhanced Model (Advanced)

**Formula:**
```
Start with v1 edges, then apply adjustments:

1. RED ZONE ACCURACY ADJUSTMENT:
   - TD rate > 15%  → +15% boost (excellent red zone efficiency)
   - TD rate > 10%  → +8% boost  (good red zone performance)
   - TD rate < 5%   → -8% penalty (poor red zone performance)

2. OPPONENT DEFENSE ADJUSTMENT:
   - Weak defense (<1.2 TDs/game)  → +10% boost
   - Strong defense (>1.8 TDs/game) → -12% penalty
   - Average defense                → no adjustment

3. FINAL CALCULATION:
   v2_edge = v1_edge × (red_zone_multiplier) × (defense_multiplier)
```

**Confidence Level:**
- Dynamic, based on multiple factors:
  - **HIGH**: edge ≥20% AND red_zone_rate >12% OR edge ≥15% OR red_zone_rate >15%
  - **MEDIUM**: edge ≥10%
  - **LOW**: edge <10%

**Expected Output:**
- 5-10 edges per week (more selective - filters down from v1)
- Target win rate: 95%+ (highest confidence)
- More conservative with higher accuracy

**Why Use v2:**
- Higher confidence predictions
- Incorporates real-world red zone efficiency data
- Considers specific defensive matchups
- Better long-term ROI through selectivity

---

## Key Differences Table

| Aspect | v1 (Simple) | v2 (Enhanced) |
|--------|-----------|-------------|
| **Input Variables** | QB TD rate, Defense TD rate | v1 + Red zone TD rate + Defense strength |
| **Calculation Complexity** | Simple weighted average | Multi-factor adjustment model |
| **Confidence Level** | Always "MEDIUM" | Dynamic (HIGH/MEDIUM/LOW) |
| **Weekly Edges** | 10-15 opportunities | 5-10 opportunities (filtered) |
| **Win Rate Target** | ~90% | 95%+ |
| **Edge Percentage** | Raw calculation | Adjusted up/down based on metrics |
| **Reasoning Detail** | Basic probability explanation | Detailed breakdown with adjustments |
| **Best For** | Volume, exploration | Quality, long-term ROI |

## Why Different Confidence Levels?

### v1 Confidence (Always "MEDIUM")
v1 uses only basic statistics:
- QB's seasonal TD average
- Defense's seasonal TD average allowed
- Home field advantage

These provide a **solid but imperfect** prediction. Without considering recent performance (red zone efficiency, defensive matchup quality), confidence caps at "medium."

### v2 Confidence (Dynamic)
v2 adds crucial context:
- **Red Zone Efficiency**: Shows how well QB executes in scoring position
  - High red zone TD rate (>15%) = Higher confidence the edge is real
  - Low red zone TD rate (<5%) = Lower confidence, edge may be inflated

- **Defense Strength Analysis**: Shows if defense is actually weak or just mediocre
  - Weak defense facing strong QB = High confidence
  - Strong defense facing weak QB = Lower confidence

This additional data allows v2 to rate confidence more accurately.

## Example: Patrick Mahomes vs Weak Defense

### v1 Analysis
```
QB Stats: 25 TDs in 8 games → 3.125 TDs/game
Defense: Allows 2.0 TDs/game
Weighted: (3.125 × 0.6) + (2.0 × 0.4) = 2.675
Probability: 2.675 × 0.6 = 1.605 → clamped to 95%

v1 Edge: 8.5% → Confidence: MEDIUM
```

### v2 Analysis (Same QB & Defense)
```
Starting edge from v1: 8.5%

Red Zone Analysis:
  - Mahomes red zone TD rate: 22% (excellent!)
  - Adjustment: +15% boost → 8.5 × 1.15 = 9.775%

Defense Analysis:
  - Opponent allows only 1.1 TDs/game (Strong defense!)
  - Adjustment: -12% penalty → 9.775 × 0.88 = 8.60%

v2 Edge: 8.6% (LOWER than v1!)
Confidence: LOW (edge is weak despite strong QB)

Why? Strong defense negates even elite red zone efficiency.
```

## When to Use Each Model

### Use v1 if you want to:
- Maximize the number of edges to analyze
- Find opportunities with moderate confidence
- Explore broader betting angles
- Test hypotheses about market inefficiencies

### Use v2 if you want to:
- Prioritize quality over quantity
- Maximize win rate (minimize losses)
- Get higher confidence predictions
- Build long-term profitable betting strategy

## Implementation Details

### Database Queries
- **v1 edges**: Pulled directly from `EdgeCalculator.find_edges_for_week()`
- **v2 edges**: Enhanced version starts with v1, then applies additional metrics from:
  - `play_by_play` table (for red zone TD rates)
  - `defense_stats` table (for opponent strength analysis)

### API Endpoints
Both strategies are available through the same `/api/edges` endpoint:
```
# Get v1 edges
GET /api/edges?week=1&strategy=qb_td_v1&min_edge=5

# Get v2 edges
GET /api/edges?week=1&strategy=qb_td_v2&min_edge=5

# Get both
GET /api/edges?week=1&strategy=all&min_edge=5
```

### Frontend Display
- Separate tabs for each model
- Edge counts shown in tab badges
- v2 cards show v1 comparison: "v1 Edge: 8.5% → v2 Edge: 9.2% (+0.7% improvement)"
- Strategy descriptions explain each model's approach

## Backward Compatibility

The legacy "Model" dropdown has been removed. If you're using older API calls with `?model=v1` or `?model=v2`, they'll be automatically mapped to the new strategy parameter:
- `model=v1` → `strategy=qb_td_v1`
- `model=v2` → `strategy=qb_td_v2`

---

## Summary

**Both v1 and v2 models are now equally available and transparent:**

| Question | Answer |
|----------|--------|
| **Why only v2 before?** | It was the only frontend strategy implemented; v1 was backend-only |
| **Are both available now?** | Yes, as separate strategy tabs |
| **Why different confidence?** | v2 incorporates more data (red zone efficiency, defense strength) |
| **Which should I use?** | v1 for volume, v2 for quality - or use both for comparison |
| **Can I compare them?** | Yes, directly via separate tabs, and v2 cards show v1 edge for reference |

Both models are now transparent and equally available for your analysis!
