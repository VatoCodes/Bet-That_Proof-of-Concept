---
name: dashboard-tester
description: Automated browser testing for Bet-That Flask dashboard using Chrome DevTools MCP. Tests all pages (index, edges, stats, tracker), API endpoints, filters, export functionality, and responsive design. Use when validating dashboard changes, running regression tests, or debugging UI issues.
allowed-tools: [chrome-devtools:*]
---

# Dashboard Tester

Comprehensive browser automation for Flask dashboard quality assurance.

## What It Does

Automates testing of all dashboard features:
- **Page Rendering**: All 4 pages load correctly
- **API Integration**: Endpoints return data properly
- **UI Interactions**: Filters, buttons, forms work
- **Data Export**: CSV downloads function
- **Error Handling**: Graceful failure states
- **Performance**: Page load times, Core Web Vitals
- **Responsive Design**: Mobile/tablet/desktop layouts

## When to Use

- "Test the dashboard"
- "Run regression tests on all pages"
- "Validate edges page filtering works"
- "Check dashboard performance"
- "Screenshot all pages for documentation"

## Test Coverage

### Pages Tested (4 total)
1. **Main Dashboard** (`/`)
   - Overview stats display
   - Current week indicator
   - Quick stats cards
   - Navigation links

2. **Edges Page** (`/edges`)
   - Edge list loading
   - Filter controls (week, model, min_edge)
   - CSV export button
   - Edge tier badges

3. **Stats Page** (`/stats`)
   - Database statistics
   - Data validation status
   - System health indicators
   - Table record counts

4. **Tracker Page** (`/tracker`)
   - Bet list display (local storage)
   - Add bet form
   - Bet history
   - Performance metrics

### API Endpoints Tested (5 total)
- `/api/current-week` - Week number
- `/api/edges` - Edge opportunities
- `/api/weak-defenses` - Defense analysis
- `/api/stats/summary` - DB statistics
- `/api/data-status` - Data validation

## How It Works

1. **Navigate** to `http://localhost:5001`
2. **Take Snapshot** of page structure
3. **Validate Elements** exist and contain data
4. **Interact** with filters/forms
5. **Monitor Network** requests
6. **Check Console** for errors
7. **Screenshot** final state
8. **Generate Report** with pass/fail status

## Example Test Flow

```python
# Test edges page filtering
1. navigate_page("http://localhost:5001/edges")
2. wait_for("Edge Opportunities")
3. take_snapshot()  # Get element UIDs
4. fill_form([
     {"uid": "week-select", "value": "7"},
     {"uid": "model-select", "value": "v2"},
     {"uid": "min-edge-input", "value": "10"}
   ])
5. click("filter-button")
6. wait_for("Filtered results")
7. list_network_requests()  # Verify API call
8. take_screenshot("edges_filtered.png")
9. Assert: response contains filtered data
```

## Test Scenarios

See `scenarios/test_flows.json`:

```json
{
  "smoke_tests": {
    "all_pages_load": [
      "navigate_page('http://localhost:5001')",
      "wait_for('Current Week')",
      "take_snapshot()",
      "assert_page_loaded()"
    ],
    "all_apis_respond": [
      "navigate_page('http://localhost:5001/api/current-week')",
      "take_snapshot()",
      "assert_json_response()"
    ]
  },
  "functional_tests": {
    "edges_filtering": [
      "navigate_page('http://localhost:5001/edges')",
      "fill_form([{'uid': 'week-select', 'value': '7'}])",
      "click('apply-filters-btn')",
      "wait_for('Filtered results')",
      "assert_data_updated()"
    ],
    "csv_export": [
      "navigate_page('http://localhost:5001/edges')",
      "click('export-csv-btn')",
      "list_network_requests()",
      "assert_download_initiated()"
    ],
    "bet_tracking": [
      "navigate_page('http://localhost:5001/tracker')",
      "fill_form([{'uid': 'bet-form', 'value': 'test bet'}])",
      "click('add-bet-btn')",
      "wait_for('Bet added')",
      "assert_bet_in_list()"
    ]
  },
  "performance_tests": {
    "page_load_times": [
      "performance_start_trace()",
      "navigate_page('http://localhost:5001')",
      "wait_for('Current Week')",
      "performance_stop_trace()",
      "performance_analyze_insight()",
      "assert_load_time_under_2s()"
    ],
    "core_web_vitals": [
      "performance_start_trace()",
      "navigate_page('http://localhost:5001/edges')",
      "wait_for('Edge Opportunities')",
      "performance_stop_trace()",
      "assert_lcp_under_2_5s()",
      "assert_fid_under_100ms()",
      "assert_cls_under_0_1()"
    ]
  },
  "error_handling": {
    "api_failure": [
      "emulate_network('offline')",
      "navigate_page('http://localhost:5001/edges')",
      "wait_for('Error message')",
      "assert_error_displayed()"
    ],
    "network_timeout": [
      "emulate_network('slow-3g')",
      "navigate_page('http://localhost:5001')",
      "wait_for('Loading...')",
      "assert_loading_state()"
    ]
  }
}
```

## Usage Examples

### Basic Testing
```bash
# Run full test suite
python scripts/test_orchestrator.py --suite full

# Test specific page
python scripts/test_orchestrator.py --page edges

# Test specific functionality
python scripts/test_orchestrator.py --test filtering
```

### Performance Testing
```bash
# Run performance tests
python scripts/test_orchestrator.py --suite performance

# Test with different network conditions
python scripts/test_orchestrator.py --network slow-3g

# Test responsive design
python scripts/test_orchestrator.py --responsive
```

### Debugging
```bash
# Run with verbose output
python scripts/test_orchestrator.py --verbose

# Take screenshots on failure
python scripts/test_orchestrator.py --screenshot-on-failure

# Check console logs
python scripts/test_orchestrator.py --console-logs
```

## Integration

- `dashboard/app.py` - Flask app under test
- `tests/browser/test_dashboard_e2e.py` - pytest integration
- Chrome DevTools MCP - Browser automation
- CI/CD pipeline - Automated regression testing

## Test Data Requirements

### Mock Data
- Sample edge detection results
- Test database with known data
- Mock API responses
- Test CSV files for export

### Test Environment
- Flask app running on localhost:5001
- Test database with sample data
- Chrome browser with DevTools enabled
- Network conditions simulation

## Error Handling

### Common Issues
- **Page Load Failures**: Check Flask app is running
- **Element Not Found**: Verify element UIDs in snapshots
- **Network Timeouts**: Adjust timeout settings
- **Browser Crashes**: Restart Chrome instance

### Troubleshooting
```bash
# Check Flask app status
curl http://localhost:5001/api/current-week

# Verify Chrome DevTools MCP
npx -y chrome-devtools-mcp@latest --help

# Check test logs
tail -f logs/dashboard_tests.log

# Run single test for debugging
python scripts/test_orchestrator.py --test edges_page_load --verbose
```

## Performance

- **Test Duration**: <2 minutes for full suite
- **Pass Rate**: >95% tests passing consistently
- **Flakiness**: <5% flaky tests
- **Coverage**: >80% of dashboard features tested

## Success Metrics

- **Test Coverage**: >80% of dashboard features
- **Pass Rate**: >95% tests passing consistently
- **Reliability**: <5% flaky tests
- **Duration**: Full suite <2 minutes

## CI/CD Integration

### GitHub Actions
```yaml
name: Dashboard Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start Flask app
        run: python dashboard/app.py &
      - name: Run dashboard tests
        run: python scripts/test_orchestrator.py --suite full
      - name: Upload screenshots
        uses: actions/upload-artifact@v2
        with:
          name: test-screenshots
          path: screenshots/
```

### Test Reports
- **JUnit XML**: For CI/CD integration
- **HTML Reports**: For detailed analysis
- **Screenshots**: On test failures
- **Console Logs**: For debugging

## Future Enhancements

- **Cross-browser Testing**: Firefox, Safari support
- **Visual Regression Testing**: Screenshot comparison
- **Accessibility Testing**: WCAG compliance
- **Load Testing**: Multiple concurrent users
