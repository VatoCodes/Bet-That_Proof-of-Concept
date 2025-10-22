# Edge Calculator Guide

**Version**: Phase 2 Implementation  
**Date**: October 21, 2025  
**Purpose**: Complete guide to the NFL Edge Finder edge detection system

---

## Overview

The Edge Calculator is the core component of Phase 2 that replaces the 90% placeholder probability with real mathematical models for calculating QB TD prop probabilities. It compares these calculated probabilities to sportsbook implied odds to identify betting opportunities.

### Key Features

- **Dual Model System**: Simple (v1) and Advanced (v2) probability models
- **Kelly Criterion Bet Sizing**: Conservative fractional Kelly with 5% bankroll cap
- **Database Integration**: Seamless integration with Phase 1 database system
- **Confidence Intervals**: Statistical confidence measures for predictions
- **Export Capabilities**: CSV export for analysis and tracking

---

## Probability Models

### Simple Model (v1)

The simple model uses a weighted combination of QB performance and defense weakness:

```python
# Base probability calculation
qb_td_per_game = qb_total_tds / qb_games_played
defense_tds_per_game = defense_tds_allowed_per_game

# Weighted formula: 60% QB performance, 40% defense weakness
base_prob = (qb_td_per_game * 0.6) + (defense_tds_per_game * 0.4)

# Apply home field advantage
if is_home:
    adjusted_prob = base_prob * 1.1
else:
    adjusted_prob = base_prob

# Convert to 0.5+ TD probability
true_probability = min(0.95, max(0.05, adjusted_prob * 0.6))
```

**Model Characteristics:**
- Fast calculation
- Easy to understand
- Good baseline performance
- Suitable for quick analysis

### Advanced Model (v2)

The advanced model includes league context, variance analysis, and confidence intervals:

```python
# League context adjustments
qb_vs_league = qb_td_per_game / league_average_tds
def_vs_league = defense_tds_per_game / league_average_tds

# Composite score
composite_score = (qb_vs_league * 0.6) + (def_vs_league * 0.4)

# Sigmoid conversion to probability
probability = 1 / (1 + exp(-2 * (composite_score - 1.0)))

# Contextual adjustments
if is_home: probability *= 1.1
if is_division_game: probability *= 0.95
if is_prime_time: probability *= 1.05

# Confidence calculation
confidence = calculate_confidence(games_played, variance_score)
```

**Model Characteristics:**
- More sophisticated analysis
- League context awareness
- Confidence intervals
- Better calibration potential

---

## Edge Detection

### Odds Conversion

The system converts American odds to implied probabilities:

```python
# American odds to probability
if odds < 0:
    implied_prob = abs(odds) / (abs(odds) + 100)
else:
    implied_prob = 100 / (odds + 100)

# Calculate edge
edge = true_probability - implied_prob
edge_percentage = (edge / implied_prob) * 100
```

### Edge Classification

Edges are classified into tiers based on percentage:

| Tier | Edge % | Kelly Fraction | Description |
|------|--------|----------------|-------------|
| PASS | < 5% | 0% | Insufficient edge |
| SMALL EDGE | 5-10% | 15% Kelly | Small but positive edge |
| GOOD EDGE | 10-20% | 25% Kelly | Good betting opportunity |
| STRONG EDGE | > 20% | 25% Kelly | Exceptional opportunity |

---

## Kelly Criterion Bet Sizing

### Formula

The Kelly Criterion calculates optimal bet size:

```
f = (bp - q) / b

Where:
f = fraction of bankroll to bet
b = decimal odds - 1
p = true probability of win
q = probability of loss (1 - p)
```

### Conservative Implementation

We use fractional Kelly for safety:

```python
# Calculate Kelly fraction
kelly = (b * p - q) / b

# Apply fractional Kelly (25% Kelly)
recommended = max(0, kelly * 0.25)

# Cap at 5% of bankroll (safety)
final_fraction = min(recommended, 0.05)
```

### Bet Sizing Examples

| True Prob | Odds | Kelly % | 25% Kelly | Bet ($1000) |
|-----------|------|---------|-----------|-------------|
| 70% | -200 | 20% | 5% | $50 |
| 60% | -150 | 10% | 2.5% | $25 |
| 50% | +100 | 0% | 0% | $0 |

---

## Usage

### Command Line Interface

The `find_edges.py` tool provides a user-friendly interface:

```bash
# Basic usage
python find_edges.py --week 8

# Advanced options
python find_edges.py --week 8 --threshold 10 --bankroll 1000 --model v2

# Export results
python find_edges.py --week 8 --export edges_week8.csv

# Filter by confidence
python find_edges.py --week 8 --min-confidence high
```

### Programmatic Usage

```python
from utils.edge_calculator import EdgeCalculator

# Initialize calculator
calculator = EdgeCalculator(model_version="v2")

# Calculate edge for specific matchup
edge_result = calculator.calculate_edge(
    qb_stats={'total_tds': 20, 'games_played': 10},
    defense_stats={'tds_per_game': 2.0},
    odds=-200,
    matchup_context={'is_home': True}
)

# Find all edges for a week
edges = calculator.find_edges_for_week(week=8, threshold=5.0)
```

---

## Model Accuracy Expectations

### Brier Score Targets

The Brier Score measures prediction accuracy (lower is better):

| Score | Performance | Action |
|-------|-------------|--------|
| < 0.20 | Excellent | Continue current approach |
| 0.20-0.25 | Good | Minor adjustments |
| 0.25-0.30 | Fair | Significant improvements needed |
| > 0.30 | Poor | Major model revision required |

### Calibration Targets

Calibration error measures how well probabilities match actual outcomes:

| Error | Performance | Action |
|-------|-------------|--------|
| < 0.10 | Well calibrated | Maintain |
| 0.10-0.15 | Moderately calibrated | Minor adjustments |
| > 0.15 | Poorly calibrated | Recalibration needed |

---

## Model Version Changelog

### Version 1.0 (Simple Model)
- **Release**: Phase 2 Initial
- **Features**: Basic weighted QB + defense model
- **Performance**: Baseline accuracy
- **Use Case**: Quick analysis, testing

### Version 2.0 (Advanced Model)
- **Release**: Phase 2 Advanced
- **Features**: League context, confidence intervals, variance analysis
- **Performance**: Improved calibration
- **Use Case**: Production betting decisions

### Future Versions

**Version 3.0 (Contextual Model)**
- Weather adjustments
- Injury impact modeling
- Recent form weighting
- Division game adjustments

**Version 4.0 (Machine Learning)**
- Historical outcome training
- Feature engineering
- Ensemble methods
- Dynamic model selection

---

## Calibration Instructions

### Initial Calibration

1. **Collect Data**: Run predictions for 4+ weeks
2. **Record Outcomes**: Track actual QB TD results
3. **Analyze Performance**: Use `model_calibration.py`
4. **Adjust Parameters**: Modify model weights if needed

### Ongoing Calibration

```bash
# Analyze recent performance
python utils/model_calibration.py --analyze --weeks-back 4

# Export detailed report
python utils/model_calibration.py --export-report performance.json

# Record individual outcomes
python utils/model_calibration.py --record-outcome PREDICTION_ID --outcome win
```

### Calibration Metrics

- **Brier Score**: Overall prediction accuracy
- **Calibration Error**: Probability calibration quality
- **ROI**: Return on investment
- **Hit Rate**: Percentage of correct predictions

---

## Troubleshooting

### Common Issues

**No edges found:**
- Lower threshold: `--threshold 3`
- Use advanced model: `--model v2`
- Lower confidence: `--min-confidence low`

**Database errors:**
- Initialize database: `python utils/db_manager.py --init`
- Check data exists: `python utils/query_tools.py --week 8 --matchups`

**Import errors:**
- Check Python path
- Verify all dependencies installed
- Run from project root directory

### Performance Issues

**Slow calculations:**
- Use simple model (v1) for speed
- Reduce database query scope
- Cache league averages

**Memory usage:**
- Process weeks individually
- Clear DataFrames after use
- Use database queries instead of loading all data

---

## Best Practices

### Model Selection

- **Development**: Use v1 for rapid iteration
- **Production**: Use v2 for betting decisions
- **Analysis**: Compare both models

### Bet Sizing

- **Conservative**: Use 25% Kelly maximum
- **Bankroll Management**: Never exceed 5% per bet
- **Diversification**: Spread risk across multiple bets

### Data Quality

- **Fresh Data**: Use most recent stats
- **Validation**: Check for data anomalies
- **Backup**: Maintain historical snapshots

### Risk Management

- **Position Sizing**: Respect Kelly recommendations
- **Stop Losses**: Set maximum loss limits
- **Monitoring**: Track performance continuously

---

## Integration with Other Components

### Database Integration

The Edge Calculator seamlessly integrates with Phase 1 database:

```python
# Automatic database queries
edges = calculator.find_edges_for_week(week=8)

# Manual database access
with DatabaseQueryTools() as db:
    matchups = db.find_qb_defense_matchups(week=8)
```

### Historical Storage

Predictions are automatically tracked for calibration:

```python
# Record prediction for tracking
from utils.model_calibration import OutcomeTracker
tracker = OutcomeTracker()
prediction_id = tracker.record_prediction(
    week=8, qb_name="Mahomes", team="KC", opponent="DEN",
    predicted_prob=0.75, odds=-200, model_version="v2"
)
```

### Scheduler Integration

The Edge Calculator can be integrated with automated schedulers:

```python
# Daily edge detection
def daily_edge_check():
    calculator = EdgeCalculator(model_version="v2")
    edges = calculator.find_edges_for_week(get_current_week())
    
    # Send alerts for strong edges
    for edge in edges:
        if edge['bet_recommendation']['tier'] == 'STRONG EDGE':
            send_alert(edge)
```

---

## Future Enhancements

### Short-term (Phase 3)
- Web dashboard integration
- Real-time line movement tracking
- Automated alert system

### Medium-term (Phase 4)
- Weather data integration
- Injury impact modeling
- Advanced bankroll management

### Long-term (Phase 5+)
- Machine learning models
- Multi-sport expansion
- API for external integrations

---

## Support

For questions or issues:

1. **Check Documentation**: Review this guide and code comments
2. **Run Tests**: Execute `python tests/test_edge_calculator.py`
3. **Debug Mode**: Use `--verbose` flags for detailed output
4. **Performance Analysis**: Use calibration tools to diagnose issues

---

**Last Updated**: October 21, 2025  
**Next Review**: After Phase 3 completion
