# edge_explanation_service

Purpose: Provide concise, dashboard-ready explanations for detected betting edges.

## Operations
- explain_edge: 2–3 sentence explanation for an edge_id (styles: simple|detailed|technical)
- list_edge_factors: Top 3 contributors summing to 100%
- generate_confidence_breakdown: Confidence contributors/weights
- format_for_dashboard: JSON payload with explanation, factors, confidence, recommendations

## Integration
- Input: edge_id from detected_edges (or analyzer output)
- Reuse existing bet_edge_analyzer outputs; avoid recomputation
- Cache results for 15 minutes

## Flask
- Route: /api/edge/explain/<edge_id> → orchestrator → this skill

## Example
```
{
  "operation": "explain_edge",
  "edge_id": "W7_QB_TD_Mahomes",
  "style": "simple"
}
```
