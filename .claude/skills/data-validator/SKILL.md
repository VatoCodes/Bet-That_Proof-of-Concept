---
name: data-validator
description: ML-powered anomaly detection and data quality insights beyond basic validation. Statistical analysis of data patterns, outlier detection, and automated quality reporting. Use when validating data quality, detecting anomalies, or ensuring data integrity.
allowed-tools: [bash_tool, read_file]
---

# Data Validator

ML-powered anomaly detection and data quality insights beyond basic validation.

## What It Does

Provides comprehensive data validation with:
- **Schema Validation**: Basic structure and type checking
- **Statistical Analysis**: Pattern detection and trend analysis
- **Anomaly Detection**: Outlier identification and classification
- **Quality Scoring**: Automated data quality assessment
- **Insight Generation**: Actionable recommendations for data issues

## When to Use

- "Validate data for week 7"
- "Check data quality and find anomalies"
- "Detect outliers in QB stats"
- "Analyze data patterns for week 8"
- "Generate data quality report"

## How It Works

1. **Load Data**: Access data for specified week
2. **Schema Validation**: Check structure and types
3. **Statistical Analysis**: Calculate patterns and trends
4. **Anomaly Detection**: Identify outliers and anomalies
5. **Quality Scoring**: Assess overall data quality
6. **Report Generation**: Create actionable insights

## Validation Types

### 1. Schema Validation
- **Column Structure**: Verify expected columns exist
- **Data Types**: Check numeric, string, date formats
- **Required Fields**: Ensure critical fields are present
- **Value Ranges**: Validate data within expected ranges

### 2. Statistical Analysis
- **Distribution Analysis**: Check data distribution patterns
- **Trend Detection**: Identify unusual trends or patterns
- **Correlation Analysis**: Find unexpected correlations
- **Variance Analysis**: Detect unusual variance in data

### 3. Anomaly Detection
- **Outlier Detection**: Identify statistical outliers
- **Pattern Breaks**: Detect breaks in expected patterns
- **Missing Data**: Find gaps in data collection
- **Duplicate Detection**: Identify duplicate records

### 4. Quality Scoring
- **Completeness**: Percentage of complete records
- **Accuracy**: Data accuracy assessment
- **Consistency**: Cross-reference validation
- **Timeliness**: Data freshness evaluation

## Integration

- `utils/data_validator.py` - Basic validation
- `utils/week_manager.py` - Week tracking
- `utils/db_manager.py` - Database operations
- `data/historical/` - Historical data access

## Usage Examples

### Basic Validation
```bash
# Validate data for specific week
python scripts/validation_orchestrator.py --week 7

# Validate all available weeks
python scripts/validation_orchestrator.py --all-weeks

# Generate quality report
python scripts/validation_orchestrator.py --week 7 --report
```

### Anomaly Detection
```bash
# Detect anomalies in QB stats
python scripts/anomaly_detector.py --week 7 --table qb_stats

# Detect anomalies across all tables
python scripts/anomaly_detector.py --week 7 --all-tables

# Custom anomaly thresholds
python scripts/anomaly_detector.py --week 7 --threshold 2.5
```

### Advanced Analysis
```python
from scripts.validation_orchestrator import ValidationOrchestrator
from scripts.anomaly_detector import AnomalyDetector

# Comprehensive validation
validator = ValidationOrchestrator(week=7)
results = validator.validate_all()

# Anomaly detection
detector = AnomalyDetector(week=7)
anomalies = detector.detect_anomalies()

# Quality scoring
quality_score = validator.calculate_quality_score()
print(f"Data Quality Score: {quality_score:.2f}/10")
```

## Output Format

### Validation Report
```
📊 DATA VALIDATION REPORT - Week 7

🔍 SCHEMA VALIDATION
✅ QB Stats: All columns present, types correct
✅ Defense Stats: All columns present, types correct
✅ Matchups: All columns present, types correct
⚠️ Odds Data: Missing 'closing_line' column in 2 files
❌ Weather Data: Missing entirely

📈 STATISTICAL ANALYSIS
✅ QB TD Distribution: Normal distribution (mean=1.5, std=0.8)
⚠️ Defense TD Allowed: Skewed distribution (outlier detected)
✅ Total Points: Normal distribution (mean=45.2, std=8.1)
✅ Spread Distribution: Normal distribution (mean=3.2, std=4.1)

🚨 ANOMALY DETECTION
1. QB Stats - Patrick Mahomes: 4.2 TD/game (3.5σ above mean)
   - Likely cause: Injury to backup QB, increased usage
   - Recommendation: Verify data source, check for data entry error

2. Defense Stats - Giants Defense: 0.1 TD/game allowed (2.8σ below mean)
   - Likely cause: Strong defensive performance, small sample size
   - Recommendation: Verify recent games, check for data accuracy

3. Odds Data - Missing closing lines for 3 games
   - Likely cause: Data collection issue, API timeout
   - Recommendation: Re-run data collection, check API status

📊 QUALITY SCORING
Overall Quality Score: 7.8/10

Breakdown:
- Completeness: 8.5/10 (85% complete records)
- Accuracy: 7.2/10 (2 anomalies detected)
- Consistency: 8.0/10 (cross-reference validation passed)
- Timeliness: 7.5/10 (data collected within 6 hours)

💡 RECOMMENDATIONS
1. Fix missing 'closing_line' column in odds data
2. Investigate Mahomes TD stats anomaly
3. Verify Giants defense data accuracy
4. Implement weather data collection
5. Set up automated anomaly alerts

🔄 NEXT STEPS
- Re-run data collection for missing closing lines
- Verify anomaly data with primary sources
- Update validation rules for detected patterns
- Schedule follow-up validation in 24 hours
```

### Anomaly Details
```
🚨 ANOMALY DETAILS

Anomaly #1: QB Stats - Patrick Mahomes
- Value: 4.2 TD/game
- Expected Range: 0.5 - 2.5 TD/game
- Z-Score: 3.5
- Severity: HIGH
- Impact: High (affects edge calculations)
- Action: Verify data source

Anomaly #2: Defense Stats - Giants Defense
- Value: 0.1 TD/game allowed
- Expected Range: 1.0 - 3.0 TD/game allowed
- Z-Score: -2.8
- Severity: MEDIUM
- Impact: Medium (affects probability calculations)
- Action: Check recent game data

Anomaly #3: Odds Data - Missing Closing Lines
- Missing: 3 games
- Expected: All games should have closing lines
- Severity: HIGH
- Impact: High (affects line movement analysis)
- Action: Re-run data collection
```

## Configuration

See `resources/validation_rules.json`:

```json
{
  "schema_validation": {
    "qb_stats": {
      "required_columns": ["player", "team", "week", "tds", "games"],
      "data_types": {
        "player": "string",
        "team": "string",
        "week": "integer",
        "tds": "float",
        "games": "integer"
      },
      "value_ranges": {
        "tds": [0, 10],
        "games": [1, 20]
      }
    },
    "defense_stats": {
      "required_columns": ["team", "week", "tds_allowed", "games"],
      "data_types": {
        "team": "string",
        "week": "integer",
        "tds_allowed": "float",
        "games": "integer"
      },
      "value_ranges": {
        "tds_allowed": [0, 10],
        "games": [1, 20]
      }
    }
  },
  "anomaly_detection": {
    "z_score_threshold": 2.5,
    "iqr_multiplier": 1.5,
    "min_samples": 10,
    "outlier_methods": ["z_score", "iqr", "isolation_forest"]
  },
  "quality_scoring": {
    "completeness_weight": 0.3,
    "accuracy_weight": 0.3,
    "consistency_weight": 0.2,
    "timeliness_weight": 0.2,
    "max_score": 10
  }
}
```

## Error Handling

### Common Issues
- **Missing Data Files**: Check if data exists for specified week
- **Invalid Week Number**: Verify week is within NFL season
- **Data Format Issues**: Ensure CSV files have expected structure
- **Anomaly Detection Errors**: Check statistical method parameters

### Troubleshooting
```bash
# Check available data
ls data/historical/2025/week_7/

# Verify data format
head -5 data/historical/2025/week_7/qb_stats_2025_20251021_090000_auto.csv

# Test validation rules
python scripts/validation_orchestrator.py --test-rules

# Debug anomaly detection
python scripts/anomaly_detector.py --week 7 --verbose --debug
```

## Performance

- **Validation Time**: <5 seconds per week
- **Anomaly Detection**: <2 seconds per table
- **Quality Scoring**: <1 second per week
- **Token Usage**: ~7,100 tokens per validation

## Success Metrics

- **Detection Rate**: Catches >95% of known anomalies
- **False Positives**: <15% of flagged anomalies are normal variance
- **Latency**: Validation completes in <5 seconds
- **Coverage**: All data tables validated

## Future Enhancements

- **Machine Learning**: Improved anomaly detection algorithms
- **Real-time Monitoring**: Continuous data quality monitoring
- **Predictive Analysis**: Predict data quality issues
- **Automated Fixes**: Auto-correct common data issues
- **Integration**: Real-time dashboard integration
