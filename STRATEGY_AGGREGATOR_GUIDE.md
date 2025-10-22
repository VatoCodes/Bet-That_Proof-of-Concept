# Strategy Aggregator - Quick Reference Guide

## Overview

The `StrategyAggregator` class provides a unified interface to access betting edges from multiple strategies (First Half Total Under, QB TD v2, etc.) with a standardized output format.

## Installation

The Strategy Aggregator is already integrated into the codebase and requires no additional dependencies beyond what's already installed.

## Basic Usage

### Initialize the Aggregator

```python
from utils.strategy_aggregator import StrategyAggregator

# Initialize with default database path
agg = StrategyAggregator()

# Or specify a custom database path
agg = StrategyAggregator(db_path="path/to/database.db")
```

### Get All Edges

```python
# Get all edges for Week 7 with default parameters
edges = agg.get_all_edges(week=7, season=2024)

# Get edges with minimum 10% edge threshold
edges = agg.get_all_edges(week=7, season=2024, min_edge=10.0)

# Filter by specific strategy
first_half_edges = agg.get_all_edges(week=7, strategy='first_half')
qb_td_edges = agg.get_all_edges(week=7, strategy='qb_td_v2')
```

### Get Edge Counts

```python
# Get quick counts for tab badges
counts = agg.get_edge_counts(week=7, season=2024)

print(f"First Half: {counts['first_half']}")
print(f"QB TD v2: {counts['qb_td_v2']}")
print(f"Kicker: {counts['kicker']}")
print(f"Total: {counts['total']}")
```

## Edge Object Structure

All edges follow this standardized format:

```python
{
    "matchup": str,           # "Jaxson Dart vs New York Giants"
    "strategy": str,          # "First Half Total Under" | "QB TD 0.5+ (Enhanced v2)"
    "line": float,            # 0.5, 23.5, etc.
    "recommendation": str,    # "OVER 0.5 TD" | "UNDER 23.5"
    "edge_pct": float,        # 18.5 (percentage)
    "confidence": str,        # "HIGH" | "MEDIUM" | "LOW"
    "reasoning": str,         # Detailed explanation with probabilities

    # Optional QB TD v2-specific fields
    "v1_edge_pct": float | None,      # Original v1 edge for comparison
    "red_zone_td_rate": float | None, # 0.15 = 15%
    "opponent": str | None             # "BAL"
}
```

## Available Methods

### `get_all_edges(week, season=2024, min_edge=5.0, strategy=None)`

Retrieve edges from all strategies for a given week.

**Parameters:**
- `week` (int): NFL week number (1-18)
- `season` (int): NFL season year (default: 2024)
- `min_edge` (float): Minimum edge percentage to include (default: 5.0)
- `strategy` (str): Filter by strategy - "first_half", "qb_td_v2", or None for all

**Returns:**
- List of edge dictionaries sorted by edge percentage (highest first)

### `get_edge_counts(week, season=2024)`

Quick count of edges per strategy (useful for tab badges).

**Parameters:**
- `week` (int): NFL week number
- `season` (int): NFL season year (default: 2024)

**Returns:**
- Dictionary with counts: `{"first_half": 3, "qb_td_v2": 5, "kicker": 0, "total": 8}`

### `get_available_strategies()`

Get list of currently available strategies.

**Returns:**
- List of strategy identifiers: `["first_half", "qb_td_v2"]`

### `validate_week(week, season=2024)`

Check if week data exists in database.

**Parameters:**
- `week` (int): NFL week number
- `season` (int): NFL season year

**Returns:**
- Boolean: True if week has data, False otherwise

## Usage Examples

### Example 1: Display All Edges for Week 7

```python
from utils.strategy_aggregator import StrategyAggregator

agg = StrategyAggregator()
edges = agg.get_all_edges(week=7, season=2024, min_edge=5.0)

print(f"\n🏈 Week 7 Edges\n")
for edge in edges:
    print(f"{edge['matchup']}")
    print(f"  {edge['strategy']}: {edge['recommendation']}")
    print(f"  Edge: {edge['edge_pct']:.1f}% | Confidence: {edge['confidence']}")
    print(f"  Reasoning: {edge['reasoning']}\n")
```

### Example 2: Get Tab Badge Counts

```python
from utils.strategy_aggregator import StrategyAggregator

agg = StrategyAggregator()
counts = agg.get_edge_counts(week=7, season=2024)

# For dashboard tab display
badges = {
    "First Half": counts['first_half'],
    "QB TD v2": counts['qb_td_v2'],
    "Kicker": counts['kicker']
}
```

### Example 3: Filter by Strategy

```python
from utils.strategy_aggregator import StrategyAggregator

agg = StrategyAggregator()

# Get only QB TD v2 edges
qb_edges = agg.get_all_edges(week=7, strategy='qb_td_v2', min_edge=10.0)

for edge in qb_edges:
    print(f"{edge['matchup']}: {edge['edge_pct']:.1f}% edge")
    if edge['v1_edge_pct']:
        print(f"  (v1: {edge['v1_edge_pct']:.1f}%)")
```

### Example 4: Validate Data Before Processing

```python
from utils.strategy_aggregator import StrategyAggregator

agg = StrategyAggregator()

if agg.validate_week(week=7, season=2024):
    edges = agg.get_all_edges(week=7, season=2024)
    print(f"Found {len(edges)} edges for Week 7")
else:
    print("No data available for Week 7")
```

## Error Handling

The Strategy Aggregator is designed to be resilient:

- **If one calculator fails**, others will still return results
- **Invalid weeks** return empty lists (no exceptions)
- **Missing data fields** are handled gracefully with defaults
- **Database errors** are logged and don't crash the aggregator

```python
try:
    edges = agg.get_all_edges(week=999, season=2024)  # No data
    print(f"Found {len(edges)} edges")  # Returns 0, doesn't crash
except Exception as e:
    print(f"Error: {e}")  # This won't be reached
```

## Integration with Flask

The Strategy Aggregator is designed to integrate easily with Flask:

```python
from flask import Flask, jsonify, request
from utils.strategy_aggregator import StrategyAggregator

app = Flask(__name__)
agg = StrategyAggregator()

@app.route('/api/edges')
def api_edges():
    week = request.args.get('week', 7, type=int)
    min_edge = request.args.get('min_edge', 5.0, type=float)
    strategy = request.args.get('strategy', None)

    edges = agg.get_all_edges(week=week, min_edge=min_edge, strategy=strategy)
    return jsonify(edges)

@app.route('/api/edge-counts')
def api_edge_counts():
    week = request.args.get('week', 7, type=int)
    counts = agg.get_edge_counts(week=week)
    return jsonify(counts)
```

## Testing

Run the unit tests:

```bash
python3 -m pytest tests/test_strategy_aggregator.py -v
```

Run integration test:

```bash
python3 << 'EOF'
from utils.strategy_aggregator import StrategyAggregator

agg = StrategyAggregator()
edges = agg.get_all_edges(week=7, season=2024)
print(f"✓ Retrieved {len(edges)} edges")
EOF
```

## Performance Notes

- **Edge retrieval**: < 100ms for most weeks
- **Database queries**: Cached by calculator implementations
- **Error isolation**: Single calculator failure doesn't affect others
- **Memory usage**: Efficient streaming (no large intermediate lists)

## Troubleshooting

### "No enhanced stats found for QB"
This is a warning, not an error. The aggregator falls back to v1 data gracefully.

### Empty edge counts
This is normal if:
- Week has no matchups scheduled
- All edges filtered out by minimum edge threshold
- Data hasn't been imported yet

### Database connection errors
Check that `data/database/nfl_betting.db` exists and is readable.

## Future Enhancements

- Kicker Points Over strategy (when kicker_stats data available)
- Caching for frequently accessed weeks
- Parallel calculator execution
- Additional filtering options (confidence level, strategy-specific parameters)
