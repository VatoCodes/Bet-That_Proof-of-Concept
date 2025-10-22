---
name: bet-edge-analyzer
description: AI-powered edge analysis with natural language queries and dashboard integration. Enhanced edge detection workflow with conversational interface for parameter refinement and recommendation generation. Use when analyzing betting opportunities, refining analysis parameters, or getting personalized recommendations.
allowed-tools: [bash_tool, read_file]
---

# Bet Edge Analyzer

AI-powered edge analysis with natural language queries and conversational refinement.

## What It Does

Provides enhanced edge detection workflow with:
- **Natural Language Queries**: "Find edges for Chiefs in week 7"
- **Conversational Refinement**: Iterative parameter adjustment
- **Personalized Recommendations**: Based on user preferences
- **Dashboard Integration**: Seamless UI integration
- **Advanced Analysis**: Multi-model comparison and insights

## When to Use

- "Analyze edges for Chiefs in week 7"
- "Find the best QB TD props for this week"
- "Show me edges with at least 15% advantage"
- "Compare v1 vs v2 model results"
- "What's the optimal bet size for my bankroll?"

## How It Works

1. **Parse Query**: Extract parameters from natural language
2. **Run Analysis**: Execute edge detection with parsed parameters
3. **Present Results**: Show edges with recommendations
4. **Refine Parameters**: Allow user to adjust criteria
5. **Re-analyze**: Run analysis with new parameters
6. **Generate Insights**: Provide actionable recommendations

## Natural Language Examples

### Basic Queries
- "Find edges for week 7"
- "Show me STRONG edges only"
- "Analyze Chiefs vs Giants"
- "What are the best QB TD props?"

### Advanced Queries
- "Find edges for week 7 with at least 15% advantage using v2 model"
- "Show me edges for teams playing at home with good weather"
- "Analyze edges for QBs with recent injury concerns"
- "Find edges for games with high total points"

### Refinement Queries
- "Increase the minimum edge to 20%"
- "Switch to v1 model"
- "Only show edges for AFC teams"
- "Filter out games with bad weather"

## Parameter Parsing

### Supported Parameters
- **Week**: "week 7", "this week", "next week"
- **Model**: "v1 model", "v2 model", "advanced model"
- **Edge Threshold**: "at least 15%", "minimum 10% edge"
- **Teams**: "Chiefs", "Bengals", "AFC teams"
- **Bankroll**: "with $1000 bankroll", "5% of bankroll"
- **Confidence**: "high confidence", "conservative"

### Example Parsing
```
Input: "Find edges for Chiefs in week 7 with at least 15% advantage using v2 model"

Parsed Parameters:
{
  "week": 7,
  "teams": ["Chiefs"],
  "min_edge": 0.15,
  "model": "v2",
  "bankroll": 1000,
  "confidence": "medium"
}
```

## Integration

- `utils/edge_calculator.py` - Edge detection engine
- `utils/query_tools.py` - Database queries
- `dashboard/app.py` - Dashboard integration
- `find_edges.py` - CLI edge detection

## Usage Examples

### Basic Analysis
```bash
# Natural language query
python scripts/conversational_analyzer.py "Find edges for week 7"

# With specific parameters
python scripts/conversational_analyzer.py "Show me STRONG edges for Chiefs"
```

### Conversational Refinement
```python
from scripts.conversational_analyzer import ConversationalAnalyzer

analyzer = ConversationalAnalyzer()

# Initial query
results = analyzer.analyze("Find edges for week 7")
print(results.summary)

# Refinement
refined_results = analyzer.refine("Increase minimum edge to 20%")
print(refined_results.summary)

# Further refinement
final_results = analyzer.refine("Only show AFC teams")
print(final_results.recommendations)
```

### Dashboard Integration
```javascript
// Frontend integration
async function analyzeEdges(query) {
    const response = await fetch('/api/analyze-edges', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query })
    });
    
    const results = await response.json();
    displayResults(results);
}

// Usage
analyzeEdges("Find edges for Chiefs in week 7");
```

## Output Format

### Standard Output
```
🎯 EDGE ANALYSIS RESULTS

Query: "Find edges for Chiefs in week 7 with at least 15% advantage"

Parameters Used:
- Week: 7
- Teams: Chiefs
- Minimum Edge: 15%
- Model: v2
- Bankroll: $1000

📊 EDGES FOUND (2 total)

1. Patrick Mahomes Over 0.5 TD vs Giants
   Edge: +18.2% | Tier: STRONG EDGE
   True Probability: 92% | Implied Odds: 77.3%
   Recommendation: $48.00 bet (4.8% of bankroll)
   Kelly Fraction: 19.2% Kelly (conservative)

2. Travis Kelce Over 0.5 TD vs Giants
   Edge: +12.5% | Tier: GOOD EDGE
   True Probability: 78% | Implied Odds: 69.2%
   Recommendation: $25.00 bet (2.5% of bankroll)
   Kelly Fraction: 12.5% Kelly (conservative)

💡 INSIGHTS
- Chiefs have favorable matchup against Giants defense
- Home field advantage adds +10% to probabilities
- Weather conditions are optimal for passing game
- Recent injury reports show no concerns

🔄 REFINEMENT OPTIONS
- "Increase minimum edge to 20%"
- "Switch to v1 model"
- "Show only STRONG edges"
- "Analyze other teams"
```

### Conversational Flow
```
User: "Find edges for week 7"
System: "Found 15 edges for week 7. 3 STRONG, 8 GOOD, 4 WEAK. Would you like to refine?"

User: "Only show STRONG edges"
System: "Found 3 STRONG edges. All involve QB TD props. Would you like to see details?"

User: "Show me the best one"
System: "Patrick Mahomes Over 0.5 TD vs Giants has 18.2% edge. Recommend $48 bet. Want to analyze further?"

User: "What about the weather?"
System: "Weather is optimal - 72°F, clear skies, 5mph winds. No impact on passing game."
```

## Configuration

See `resources/model_configs.json`:

```json
{
  "models": {
    "v1": {
      "description": "Simple probability model",
      "parameters": {
        "league_average_tds": 1.5,
        "home_advantage": 0.1
      }
    },
    "v2": {
      "description": "Advanced probability model",
      "parameters": {
        "league_average_tds": 1.5,
        "home_advantage": 0.1,
        "weather_factor": 0.05,
        "injury_factor": 0.15,
        "recent_form_weight": 0.3
      }
    }
  },
  "defaults": {
    "week": "current",
    "model": "v2",
    "min_edge": 0.1,
    "bankroll": 1000,
    "confidence": "medium"
  }
}
```

## Error Handling

### Common Issues
- **Invalid Week**: Check if week is within NFL season
- **Team Not Found**: Verify team name spelling
- **No Data**: Check if data exists for specified week
- **Model Errors**: Verify model parameters

### Troubleshooting
```bash
# Test parameter parsing
python scripts/conversational_analyzer.py --test-parse "Find edges for week 7"

# Check available data
python scripts/conversational_analyzer.py --list-weeks

# Verify model configuration
python scripts/conversational_analyzer.py --check-models
```

## Performance

- **Response Time**: <30 seconds per analysis
- **Accuracy**: Matches CLI results 100%
- **Usability**: >90% natural language query success
- **Token Usage**: ~10,100 tokens per analysis

## Success Metrics

- **Usability**: Natural language queries work >90% of time
- **Accuracy**: Matches CLI results 100%
- **Latency**: Responses in <30 seconds
- **User Satisfaction**: Positive qualitative feedback

## Future Enhancements

- **Machine Learning**: Improved parameter parsing
- **Context Awareness**: Remember previous queries
- **Multi-language Support**: Spanish, French queries
- **Voice Interface**: Speech-to-text integration
- **Advanced Insights**: Weather, injury, trend analysis
