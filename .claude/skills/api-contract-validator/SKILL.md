---
name: api-contract-validator
description: Validates API responses match frontend expectations, preventing silent failures from API contract changes. Scans frontend files for API usage, auto-generates contracts, and detects field mismatches with helpful suggestions.
allowed-tools: [bash:*, python:*]
---

# API Contract Validator Skill

## Purpose

Validates that backend API responses match frontend expectations, preventing silent failures from API contract changes. This skill was created to prevent issues like the edge display bug discovered on 2025-10-22 where the frontend expected one API response format but the backend had changed the structure.

## When to Use

- After backend changes to API endpoints
- Before deploying frontend changes
- In CI/CD pipeline as pre-deployment check
- When adding new API endpoints
- During debugging of data display issues
- Daily validation as part of health monitoring

## Capabilities

1. **Contract Validation**: Compare actual API responses against expected contracts
2. **Frontend Scanning**: Automatically find all API calls in templates/JavaScript
3. **Schema Generation**: Auto-generate contracts from current API responses
4. **Diff Detection**: Show exactly what changed between API versions
5. **Field Mapping**: Suggest field name mappings for common mismatches
6. **HTML Reporting**: Generate visual validation reports

## Usage Examples

### Validate All Endpoints

```bash
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
python .claude/skills/api-contract-validator/scripts/contract_validator.py
```

Output:
```
============================================================
🔍 API Contract Validation Starting
============================================================

Testing: /api/edges
  ✅ PASS
Testing: /api/edges/counts
  ✅ PASS
...
============================================================
✅ Passed: 8
❌ Failed: 0
⚠️  Warnings: 0
============================================================
```

### Validate Specific Endpoint

```python
from .claude.skills.api_contract_validator.scripts.contract_validator import APIContractValidator

validator = APIContractValidator()
result = validator.validate_specific_endpoint("/api/edges", params={"week": 7})

if result['status'] == 'fail':
    print(f"❌ Validation failed:")
    for mismatch in result['mismatches']:
        print(f"  - {mismatch}")
```

### Scan Frontend for API Usage

```bash
python .claude/skills/api-contract-validator/scripts/frontend_scanner.py
```

Output:
```
============================================================
🔍 Scanning Frontend for API Calls
============================================================

Scanning: edges.html
Scanning: index.html

✅ Found 12 API calls

============================================================
📊 API Usage Report
============================================================

/api/edges
  Used in 2 location(s):
    • edges.html:740
      Fields: matchup, strategy, line, edge_pct, recommendation
    • index.html:451
      Fields: edges, count

/api/edges/counts
  Used in 1 location(s):
    • edges.html:812
      Fields: counts
```

### Generate Contract from Current API

```bash
python .claude/skills/api-contract-validator/scripts/schema_generator.py
```

This auto-generates schemas for all known endpoints and saves them to `api_contracts.json`.

### Generate Contract for Specific Endpoint

```bash
python .claude/skills/api-contract-validator/scripts/schema_generator.py /api/edges --save
```

## Configuration

Edit `.claude/skills/api-contract-validator/resources/validation_config.json`:

```json
{
  "backend_url": "http://localhost:5001",
  "frontend_paths": [
    "dashboard/templates/*.html",
    "dashboard/static/js/*.js"
  ],
  "validation_mode": "strict",
  "auto_fix_suggestions": true,
  "alert_on_failure": true,
  "alert_recipients": ["dev@example.com"]
}
```

**Configuration Options:**

- `backend_url`: URL where Flask app is running
- `frontend_paths`: Glob patterns for files to scan
- `validation_mode`: "strict" (fail on any mismatch), "warning" (warn but pass)
- `auto_fix_suggestions`: Show field name suggestions
- `alert_on_failure`: Send alerts when validation fails

## API Endpoints Validated

Current contracts validate these 8 endpoints:

| Endpoint | Purpose | Validation Status |
|----------|---------|-------------------|
| `/api/edges` | Edge opportunities | ✅ Validated |
| `/api/edges/counts` | Edge count badges | ✅ Validated |
| `/api/current-week` | Current week number | ✅ Validated |
| `/api/week-range` | Available weeks | ✅ Validated |
| `/api/weak-defenses` | Defense analysis | ✅ Validated |
| `/api/stats/summary` | Database statistics | ✅ Validated |
| `/api/data-status` | Data validation status | ✅ Validated |
| `/api/edge/explain` | Edge explanations | ✅ Validated |

## Key Outputs

### Validation Report HTML

Generated at: `.claude/skills/api-contract-validator/validation_report.html`

Example report shows:
- Summary: Passed/Failed/Warnings count
- Failed validations with detailed mismatches
- Response sample snapshots
- Field type mismatches
- Suggestions for similar field names

### Frontend Usage Map

Generated when scanning frontend files, shows:
- Which endpoints are used where
- Which fields are accessed from responses
- File locations and line numbers

## Dependencies

- **requests**: For HTTP calls to API
- **pathlib**: File path handling (stdlib)
- **json**: JSON parsing (stdlib)
- **re**: Regex for frontend scanning (stdlib)

## Integration Points

- **Flask App**: Tests against `http://localhost:5001`
- **Orchestrator**: `.claude/skills_orchestrator.py` for centralized execution
- **Scheduler**: Can be scheduled to run daily/hourly
- **Edge Alerter**: Sends alerts on contract violations
- **Dashboard Tester**: Companion skill for browser testing

## Common Scenarios

### Scenario 1: Backend Changed Field Name

**Before:**
```json
{
  "edges": [
    {"confidence": "High", ...}
  ]
}
```

**After:**
```json
{
  "edges": [
    {"confidence_level": "High", ...}
  ]
}
```

**Validator Output:**
```
❌ Missing field in edges[]: 'confidence'
💡 Did you mean: confidence_level?
```

### Scenario 2: API Added New Required Field

**Before:**
```json
{
  "success": true,
  "edges": [...]
}
```

**After:**
```json
{
  "success": true,
  "edges": [...],
  "metadata": {...}  // NEW
}
```

Frontend won't break (no changes needed), but validator tracks it:
```
⚠️ Array 'edges' is empty - cannot validate structure
```

### Scenario 3: Field Type Changed

**Before:**
```json
{
  "edge_pct": 12.5
}
```

**After:**
```json
{
  "edge_pct": "12.5%"
}
```

**Validator Output:**
```
❌ Type mismatch for 'edge_pct': expected float, got str
```

## Pre-Deployment Workflow

Create `.github/workflows/pre-deploy.yml`:

```yaml
name: Pre-Deployment Validation
on: [push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Validate API contracts
        run: |
          python .claude/skills/api-contract-validator/scripts/contract_validator.py
```

## Troubleshooting

### Issue: "No contracts defined"

**Solution:** Run schema generator first:
```bash
python .claude/skills/api-contract-validator/scripts/schema_generator.py
```

### Issue: "Backend URL connection refused"

**Solution:** Ensure Flask app is running:
```bash
# Terminal 1
python dashboard/app.py

# Terminal 2 (run validator)
python .claude/skills/api-contract-validator/scripts/contract_validator.py
```

### Issue: "No API calls found" when scanning

**Solution:** Check frontend_paths in validation_config.json:
```json
{
  "frontend_paths": [
    "dashboard/templates/*.html",
    "dashboard/static/js/*.js"
  ]
}
```

### Issue: False positives on type validation

**Solution:** Update api_contracts.json with actual types:
```json
{
  "field_name": {
    "expected": "str",  // Was "int", but API returns string
    ...
  }
}
```

## Success Metrics

After implementation:
- ✅ All 8 API endpoints have defined contracts
- ✅ Validator runs in <5 seconds
- ✅ Frontend scanner finds 10+ API calls
- ✅ Validation report generates HTML
- ✅ Type mismatches detected with suggestions
- ✅ No false positives on valid responses

## Future Enhancements

- [ ] GraphQL schema validation
- [ ] OpenAPI/Swagger integration
- [ ] Automated field mapping detection
- [ ] API response versioning
- [ ] Contract evolution tracking
- [ ] Breaking change detection
- [ ] Slack/email notifications

## Related Documentation

- **Original Bug**: Edges display failed 2025-10-22 due to API response format change
- **Skills Audit**: `SCRIPTS_AND_AGENTS_AUDIT.md`
- **Skills Roadmap**: `SKILLS_ROADMAP.md`
- **Implementation Prompt**: `ClaudeCode_API_Integration_Skills_Implementation_Prompt.md`

## Support

For issues or improvements:
1. Check configuration in `resources/validation_config.json`
2. Review generated contracts in `resources/api_contracts.json`
3. Check Flask app logs for API errors
4. Run schema generator to update contracts
5. Check validation report HTML for detailed errors
