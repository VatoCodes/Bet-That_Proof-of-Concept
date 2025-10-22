---
name: frontend-integration-tester
description: Automated browser-based testing of API integration between backend and frontend using Chrome DevTools. Tests real browser API calls, validates DOM population, and detects JavaScript errors to catch integration issues before production.
allowed-tools: [chrome-devtools:*, bash:*, python:*]
---

# Frontend Integration Tester Skill

## Purpose

Automated browser-based testing of API integration between backend and frontend. Captures actual API requests/responses from the browser, validates frontend correctly extracts backend fields, and detects JavaScript errors from API issues.

This skill complements the API Contract Validator by testing the full integration flow: backend API → network → browser → JavaScript extraction → DOM rendering.

## When to Use

- Before deploying frontend or backend changes
- After modifying API response structures
- When debugging data display issues
- In CI/CD as integration test suite
- After contract violations detected by api-contract-validator
- When investigating why data doesn't appear on dashboard

## Capabilities

1. **Browser Automation**: Uses Chrome DevTools to test real browser behavior
2. **Network Inspection**: Captures actual API requests/responses in browser
3. **Field Mapping Validation**: Verifies frontend correctly extracts backend fields
4. **JavaScript Checks**: Detects errors in API response handling
5. **DOM Validation**: Verifies page renders data correctly
6. **Screenshots**: Captures page state on failures
7. **Test Scenarios**: Configurable test flows for different pages

## Usage Examples

### Run All Integration Tests

```bash
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py
```

Output:
```
============================================================
🧪 Running Integration Tests
============================================================

Running: Edges Page API Integration
  ✅ PASS

Running: Dashboard Page API Integration
  ✅ PASS

============================================================
✅ Passed: 2
❌ Failed: 0
⏭️  Skipped: 0
⏱️  Duration: 15.23s
============================================================
```

### List Available Test Scenarios

```bash
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py --list
```

Output:
```
📋 Available Test Scenarios:

  Edges Page API Integration
    File: edges_api_test.json
    URL: /edges

  Dashboard Page API Integration
    File: dashboard_api_test.json
    URL: /
```

### Run Specific Scenario

```bash
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py \
  --scenario edges_api_test
```

### Inspect Network Traffic

```python
from .claude.skills.frontend_integration_tester.scripts.response_inspector import ResponseInspector

config = {
    "backend_url": "http://localhost:5001",
    "chrome_options": {"headless": False}
}

inspector = ResponseInspector(config)
inspector.start_chrome()
inspector.navigate("http://localhost:5001/edges")
inspector.wait_for_page_load()

api_calls = inspector.get_api_calls_with_responses()

for call in api_calls:
    print(f"URL: {call['url']}")
    print(f"Status: {call['status']}")
    print(f"Response Fields: {list(call['response'].keys())}")

inspector.stop_chrome()
```

### Validate Field Extraction

```python
from .claude.skills.frontend_integration_tester.scripts.field_mapper import FieldMapper

mapper = FieldMapper()

api_response = {
    'success': True,
    'edges': [],
    'count': 0,
    'week': 7
}

expected_fields = ['success', 'edges', 'count', 'week']
result = mapper.validate_field_extraction(api_response, expected_fields, '/api/edges')

if result['missing_fields']:
    print("❌ Missing fields:")
    for missing in result['missing_fields']:
        print(f"  - {missing['expected']}")
else:
    print("✅ All fields extracted correctly")
```

## Configuration

Edit `.claude/skills/frontend-integration-tester/resources/integration_config.json`:

```json
{
  "backend_url": "http://localhost:5001",
  "chrome_options": {
    "headless": false,
    "window_size": "1920x1080"
  },
  "timeout_seconds": 30,
  "screenshot_on_failure": true,
  "screenshot_dir": ".claude/skills/frontend-integration-tester/screenshots",
  "alert_on_failure": true
}
```

**Configuration Options:**

- `backend_url`: URL where Flask app is running
- `chrome_options.headless`: Run browser in headless mode
- `chrome_options.window_size`: Browser window size
- `timeout_seconds`: Maximum time to wait for page load
- `screenshot_on_failure`: Capture screenshots when tests fail
- `alert_on_failure`: Send alerts on test failures

## Test Scenarios

Test scenarios are defined in JSON files in `scenarios/` directory. Each scenario defines:

- **name**: Test name
- **url**: Page URL to test
- **wait_for_selector**: Element to wait for before validating
- **expected_api_calls**: API calls page should make
- **expected_dom_elements**: DOM elements that should exist
- **javascript_checks**: JavaScript expressions that should evaluate to true
- **assertions**: Custom assertions to validate

### Example Scenario: Edges Page

```json
{
  "name": "Edges Page API Integration",
  "url": "/edges",
  "wait_for_selector": "[x-data]",
  "expected_api_calls": [
    {
      "endpoint": "/api/edges",
      "response_fields": ["success", "edges", "count"],
      "nested_fields": {
        "edges": ["matchup", "strategy", "line", "edge_pct"]
      }
    }
  ],
  "expected_dom_elements": [
    ".edge-card",
    "[x-show='edges.length > 0']"
  ],
  "javascript_checks": [
    "typeof edgesDashboard === 'function'",
    "document.querySelectorAll('.edge-card').length > 0"
  ],
  "assertions": [
    {
      "type": "api_response_extracted",
      "field": "edges",
      "message": "Frontend should extract edges from API response"
    },
    {
      "type": "dom_populated",
      "selector": ".edge-card",
      "min_count": 0,
      "message": "Edge cards should render (may be 0 if no edges)"
    }
  ]
}
```

## Key Outputs

### Test Results JSON

Contains:
- Test status (pass/fail/skip)
- API calls captured
- Fields extracted
- Assertions passed/failed
- Screenshot paths on failure

### Screenshots on Failure

Saved to: `.claude/skills/frontend-integration-tester/screenshots/`

Shows page state when test fails, useful for debugging:
- Empty data containers
- Missing elements
- Error messages displayed

### Console Logs

Captured browser console logs help identify:
- JavaScript errors
- Warning messages
- API response parsing issues
- Frontend framework errors

## Dependencies

- **Chrome/Chromium**: For browser automation (reuses dashboard-tester infrastructure)
- **Chrome DevTools Protocol**: Network inspection
- **Python**: Test orchestration and field mapping
- **Existing Skills**: Uses dashboard-tester's Chrome infrastructure

## Integration Points

- **Dashboard Tester**: Reuses Chrome automation setup
- **API Contract Validator**: Tests actual responses match contracts
- **Edge Alerter**: Sends alerts on test failures
- **Orchestrator**: Can be triggered via `.claude/skills_orchestrator.py`

## Common Scenarios

### Scenario 1: API Response Field Missing

**Test Failure:**
```
❌ FAIL: Missing field in edges[]: 'confidence'
💡 Did you mean: confidence_level?
```

**Investigation:**
1. Check API response with API Contract Validator
2. Verify frontend JavaScript is using correct field name
3. Update field mapping or API response

### Scenario 2: Empty Data Display

**Test Failure:**
```
⚠️  FAIL: Expected '.edge-card' but found 0 elements
```

**Investigation:**
1. Check if API call was made (inspect network)
2. Verify response contains data
3. Check JavaScript console for errors
4. Review field extraction in JavaScript

### Scenario 3: Slow API Response

**Test Failure:**
```
⏱️  Timeout waiting for element: .edge-card
```

**Investigation:**
1. Check API performance
2. Increase timeout in config
3. Verify database has data for week
4. Check network conditions

## Pre-Deployment Workflow

Create automated test runner before deployments:

```bash
#!/bin/bash
# scripts/pre_deploy_test.sh

echo "Running API integration tests..."

# Ensure Flask app is running
if ! curl -s http://localhost:5001/api/current-week > /dev/null; then
    echo "❌ Flask app not running on localhost:5001"
    exit 1
fi

# Run integration tests
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py

if [ $? -ne 0 ]; then
    echo "❌ Integration tests failed"
    exit 1
fi

echo "✅ All integration tests passed"
```

## Troubleshooting

### Issue: "Chrome not found"

**Solution:** Verify Chrome is installed:
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Linux
google-chrome --version
```

### Issue: "Timeout waiting for element"

**Solution:** Increase timeout in config:
```json
{
  "timeout_seconds": 60
}
```

### Issue: "API call not captured"

**Solution:** Verify endpoint in scenario matches actual requests:
```bash
# Check what API calls are actually made
curl http://localhost:5001/edges -v

# Update scenario with correct endpoint
```

### Issue: "Field extraction failing"

**Solution:** Use field mapper to debug:
```python
mapper = FieldMapper()
result = mapper.validate_field_extraction(response, expected_fields, endpoint)
print(mapper.generate_field_mapping_report([result]))
```

## Success Metrics

After implementation:
- ✅ All test scenarios pass consistently
- ✅ <2 minute full test suite duration
- ✅ >95% pass rate
- ✅ Screenshots captured on failures
- ✅ Field extraction validated
- ✅ DOM population verified

## Future Enhancements

- [ ] Visual regression testing (screenshot comparison)
- [ ] Performance metrics (page load time, Core Web Vitals)
- [ ] Mobile responsiveness testing
- [ ] Cross-browser testing (Firefox, Safari)
- [ ] Accessibility testing (WCAG compliance)
- [ ] Load testing (multiple concurrent users)
- [ ] Video recording of test execution

## Related Documentation

- **API Contract Validator**: Validates API responses
- **Dashboard Tester**: Browser automation framework
- **Skills Audit**: `SCRIPTS_AND_AGENTS_AUDIT.md`
- **Skills Roadmap**: `SKILLS_ROADMAP.md`

## Support

For issues or improvements:
1. Check configuration in `resources/integration_config.json`
2. Review test scenario in `scenarios/` directory
3. Run individual scenario: `--scenario edges_api_test`
4. Check Chrome console logs for JavaScript errors
5. Review screenshots in `screenshots/` directory
6. Run API Contract Validator to check response format
