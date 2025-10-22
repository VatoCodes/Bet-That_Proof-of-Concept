# ADR-002: MCP Integration Strategy for Dashboard Testing

**Date:** October 21, 2025  
**Status:** Accepted  
**Deciders:** Technical Architecture Team  

## Context

The Bet-That Flask dashboard requires automated testing to ensure UI functionality, API integration, and browser compatibility. We need to choose between Selenium and Chrome DevTools MCP for browser automation, considering the existing MCP configuration and project requirements.

## Decision Drivers

- **Existing Infrastructure:** Chrome DevTools MCP already configured
- **Integration Complexity:** Minimize setup and maintenance overhead
- **Test Reliability:** Stable, non-flaky test execution
- **Development Speed:** Fast test development and execution
- **Team Expertise:** Leverage existing MCP knowledge
- **Cost:** Minimize additional dependencies and costs

## Considered Options

### Option 1: Selenium WebDriver
- **Pros:** Mature ecosystem, extensive documentation, wide browser support
- **Cons:** Complex setup, additional dependencies, maintenance overhead, flaky tests

### Option 2: Chrome DevTools MCP
- **Pros:** Already configured, native Claude integration, lightweight, stable
- **Cons:** Chrome-only, newer technology, limited ecosystem

### Option 3: Playwright
- **Pros:** Modern API, good reliability, multi-browser support
- **Cons:** Additional setup, learning curve, maintenance overhead

### Option 4: Manual Testing Only
- **Pros:** No automation complexity
- **Cons:** Time-consuming, error-prone, not scalable

## Decision Outcome

**Chosen:** Option 2 - Chrome DevTools MCP

We will use Chrome DevTools MCP for dashboard testing automation, leveraging the existing configuration and Claude's native integration capabilities.

## Decision Rationale

### Existing Infrastructure Advantage
- Chrome DevTools MCP already configured at `/Users/vato/Library/Application Support/Code/User/mcp.json`
- NPX package cached at `/Users/vato/.npm/_npx/15c61037b1978c83/node_modules/chrome-devtools-mcp`
- Node.js v24.8.0 already installed and compatible
- No additional setup or configuration required

### Integration Benefits
- **Native Claude Integration:** Skills can directly use MCP tools
- **Token Efficiency:** No additional API calls or external dependencies
- **Unified Environment:** All testing within Claude Code ecosystem
- **Version Control:** Test scripts committed with Skills repository

### Technical Advantages
- **Stability:** Chrome DevTools Protocol is mature and stable
- **Performance:** Direct browser communication, no WebDriver overhead
- **Debugging:** Rich debugging capabilities with DevTools integration
- **Reliability:** Less flaky than Selenium due to direct protocol communication

## Chrome DevTools MCP Capabilities

### Available Tools (27 total)

**Navigation & Interaction:**
- `navigate_page(url)` - Navigate to URLs
- `click(uid)` - Click elements by uid
- `fill` / `fill_form` - Fill form inputs
- `hover` - Hover over elements
- `drag` - Drag and drop operations
- `upload_file` - File uploads
- `handle_dialog` - Handle browser dialogs
- `wait_for` - Wait for text/elements

**Inspection & Testing:**
- `take_snapshot` - Text-based page snapshot with element uids
- `take_screenshot` - Visual screenshots (full page or element)
- `list_console_messages` - Monitor console logs
- `list_network_requests` - Analyze network traffic
- `get_network_request` - Inspect specific requests

**Page Management:**
- `list_pages` - See all open tabs
- `new_page` - Open new tabs
- `select_page` - Switch between tabs
- `close_page` - Close tabs
- `navigate_page_history` - Back/forward navigation
- `resize_page` - Set viewport dimensions

**Advanced Features:**
- `evaluate_script` - Execute JavaScript in page context
- `performance_start_trace` / `performance_stop_trace` - Performance profiling
- `performance_analyze_insight` - Analyze Core Web Vitals
- `emulate_cpu` / `emulate_network` - Simulate conditions

## Dashboard Testing Requirements

### Pages to Test (4 total)
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

### API Endpoints to Test (5 total)
- `GET /api/current-week` - Week number
- `GET /api/edges?week=X&min_edge=Y&model=Z` - Edge opportunities
- `GET /api/weak-defenses?week=X&threshold=Y` - Defense analysis
- `GET /api/stats/summary` - Database statistics
- `GET /api/data-status` - Data validation status

### Test Scenarios

**Critical Path Tests:**
1. User visits dashboard → sees current week data
2. User navigates to edges page → filters by week 7, model v2, min 10% edge
3. User exports edges to CSV → file downloads successfully
4. User adds bet to tracker → bet appears in list
5. All API endpoints return 200 status codes

**Error State Tests:**
1. Dashboard starts with database offline → displays error banner
2. API endpoint returns 500 error → shows user-friendly message
3. Network timeout occurs → retry mechanism activates
4. Invalid week number provided → validation error shown

**Performance Tests:**
1. Main dashboard loads in <2 seconds
2. API calls complete in <500ms
3. No JavaScript console errors
4. Core Web Vitals: LCP <2.5s, FID <100ms, CLS <0.1

**Responsive Design Tests:**
1. Mobile layout (375px width)
2. Tablet layout (768px width)
3. Desktop layout (1200px width)
4. Breakpoint transitions

## Implementation Architecture

### Test Structure
```
tests/browser/
├── test_dashboard_e2e.py          # Main E2E test suite
├── conftest.py                    # pytest configuration
├── fixtures/
│   ├── test_data.json            # Mock data for tests
│   └── expected_responses.json   # Expected API responses
└── utils/
    ├── chrome_mcp_client.py      # MCP client wrapper
    └── test_helpers.py           # Common test utilities
```

### Test Execution Flow
1. **Setup:** Start Flask app, initialize Chrome DevTools MCP
2. **Navigation:** Navigate to dashboard URL
3. **Snapshot:** Take page snapshot to get element UIDs
4. **Interaction:** Fill forms, click buttons, test filters
5. **Validation:** Verify API calls, check console logs
6. **Screenshot:** Capture final state for documentation
7. **Cleanup:** Close browser, stop Flask app

### Example Test Implementation
```python
def test_edges_page_filtering(chrome_mcp):
    # Navigate to edges page
    chrome_mcp.navigate_page("http://localhost:5001/edges")
    chrome_mcp.wait_for("Edge Opportunities")
    
    # Take snapshot to get element UIDs
    snapshot = chrome_mcp.take_snapshot()
    
    # Fill filter form
    chrome_mcp.fill_form([
        {"uid": "week-select", "value": "7"},
        {"uid": "model-select", "value": "v2"},
        {"uid": "min-edge-input", "value": "10"}
    ])
    
    # Apply filters
    chrome_mcp.click("apply-filters-btn")
    chrome_mcp.wait_for("Filtered results")
    
    # Verify API call
    requests = chrome_mcp.list_network_requests()
    assert any("/api/edges" in req for req in requests)
    
    # Take screenshot
    chrome_mcp.take_screenshot("edges_filtered.png")
```

## Security and Sandboxing Considerations

### Security Measures
- **Isolated Environment:** Tests run in separate Chrome instance
- **No Production Data:** Tests use mock data only
- **Controlled Access:** MCP tools have limited scope
- **Cleanup:** Automatic cleanup after test completion

### Sandboxing Strategy
- **Test Database:** Separate test database for testing
- **Mock APIs:** Mock external API calls during testing
- **Isolated Network:** Tests run on localhost only
- **Resource Limits:** Memory and CPU limits for test processes

## Performance Considerations

### Test Execution Speed
- **Parallel Execution:** Multiple tests can run concurrently
- **Selective Testing:** Run only changed tests during development
- **Caching:** Cache page snapshots and element UIDs
- **Optimization:** Minimize wait times with smart waiting

### Resource Usage
- **Memory:** Chrome DevTools MCP is lightweight
- **CPU:** Minimal overhead compared to Selenium
- **Network:** Local testing only, no external calls
- **Storage:** Screenshots and logs stored locally

## Monitoring and Debugging

### Test Monitoring
- **Pass Rate:** Track test success rate over time
- **Execution Time:** Monitor test duration trends
- **Flakiness:** Identify and fix flaky tests
- **Coverage:** Measure test coverage of dashboard features

### Debugging Capabilities
- **Screenshots:** Automatic screenshots on test failure
- **Console Logs:** Capture JavaScript console messages
- **Network Logs:** Monitor API calls and responses
- **Element Snapshots:** Text-based page structure for debugging

### Error Handling
- **Retry Logic:** Automatic retry for transient failures
- **Timeout Handling:** Configurable timeouts for different operations
- **Graceful Degradation:** Continue test suite on single test failure
- **Error Reporting:** Detailed error messages with context

## Limitations and Workarounds

### Chrome-Only Limitation
- **Impact:** Tests only run in Chrome browser
- **Workaround:** Manual testing in other browsers for critical features
- **Mitigation:** Chrome represents >60% of browser market share

### MCP Tool Limitations
- **File Downloads:** Cannot verify actual file downloads
- **Workaround:** Check console logs and network requests for download initiation
- **Alternative:** Use API testing for download functionality

### Element Identification
- **Challenge:** Element UIDs may change with UI updates
- **Workaround:** Use stable selectors (data-testid attributes)
- **Mitigation:** Regular test maintenance and updates

## Integration with CI/CD

### Continuous Integration
- **GitHub Actions:** Run tests on every pull request
- **Test Reports:** Generate and publish test results
- **Screenshots:** Upload failure screenshots as artifacts
- **Notifications:** Alert team on test failures

### Deployment Pipeline
- **Pre-deployment:** Run full test suite before deployment
- **Post-deployment:** Smoke tests after deployment
- **Rollback:** Automatic rollback on test failures
- **Monitoring:** Continuous monitoring of dashboard health

## Success Metrics

### Test Coverage
- **Target:** >80% of dashboard features tested
- **Measurement:** Feature coverage analysis
- **Reporting:** Coverage reports in CI/CD

### Test Reliability
- **Target:** >95% test pass rate consistently
- **Measurement:** Pass rate over time
- **Action:** Fix flaky tests immediately

### Test Speed
- **Target:** Full suite <2 minutes
- **Measurement:** Test execution time
- **Optimization:** Parallel execution, selective testing

### Debugging Efficiency
- **Target:** <5 minutes to identify test failure cause
- **Measurement:** Time from failure to root cause identification
- **Tools:** Screenshots, logs, snapshots

## Alternatives Considered

### Alternative 1: Selenium WebDriver
- **Rejected:** Complex setup, maintenance overhead, flaky tests
- **Reason:** Chrome DevTools MCP provides better integration and reliability

### Alternative 2: Playwright
- **Rejected:** Additional setup, learning curve
- **Reason:** Chrome DevTools MCP already configured and integrated

### Alternative 3: Manual Testing
- **Rejected:** Not scalable, error-prone, time-consuming
- **Reason:** Automated testing provides better coverage and reliability

## Implementation Timeline

### Week 1: Setup and Basic Tests
- Day 1: Verify MCP configuration and setup
- Day 2: Implement basic page load tests
- Day 3: Implement API endpoint tests
- Day 4: Implement form interaction tests

### Week 2: Advanced Tests and Integration
- Day 5: Implement performance tests
- Day 6: Implement responsive design tests
- Day 7: Implement error handling tests
- Day 8: Integrate with CI/CD pipeline

### Week 3: Optimization and Maintenance
- Day 9: Optimize test execution speed
- Day 10: Implement test monitoring and reporting
- Day 11: Documentation and training
- Day 12: Handoff and maintenance procedures

## Consequences

### Positive
- **Leverages Existing Infrastructure:** No additional setup required
- **Native Integration:** Seamless integration with Claude Skills
- **High Reliability:** Chrome DevTools Protocol is stable and mature
- **Rich Debugging:** Comprehensive debugging capabilities
- **Cost Effective:** No additional licensing or infrastructure costs

### Negative
- **Chrome Only:** Limited to Chrome browser testing
- **Learning Curve:** Team needs to learn MCP tool usage
- **Newer Technology:** Less community support than Selenium
- **Maintenance:** Regular updates needed for UI changes

### Neutral
- **Development Time:** Similar to Selenium setup time
- **Test Writing:** Different approach but similar complexity
- **Documentation:** Comprehensive documentation required

## Review and Updates

This ADR will be reviewed:
- After Week 1 implementation
- After Week 2 integration
- Monthly during active development
- Quarterly for ongoing optimization

Updates will be made based on:
- Test reliability metrics
- Performance benchmarks
- Team feedback
- New requirements

---

**Approved by:** Technical Architecture Team  
**Date:** October 21, 2025  
**Next Review:** November 21, 2025
