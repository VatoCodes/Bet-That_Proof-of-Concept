# alert_calibration_manager

Purpose: Tune alert thresholds (edge_threshold, confidence_threshold, min_hold_days) using historical outcomes to improve precision while preserving recall.

## Operations
- analyze_precision: Compute precision/recall by current thresholds
- recommend_thresholds: Bayesian calibration to propose thresholds with 90% CI
- apply_calibration: Apply recommended thresholds (dry-run by default) and log
- backtest_thresholds: Simulate thresholds on last 4–8 weeks and report deltas

## Inputs/Outputs
- Input: Historical outcomes from utils/model_calibration.py (OutcomeTracker)
- Output: {status, data|message}; logs to calibration_history

## Safety
- Dry-run default on writes
- Transactional DB writes
- Clear error messages

## Triggers
- Weekly (post-games) and on-demand

## Example
```
{
  "operation": "recommend_thresholds",
  "weeks_back": 6,
  "precision_target": 0.7
}
```
