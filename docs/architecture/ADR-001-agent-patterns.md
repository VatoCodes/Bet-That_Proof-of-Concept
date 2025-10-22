# ADR-001: Agent Patterns for Remaining Issues

**Date:** October 21, 2025  
**Status:** Accepted  
**Deciders:** Technical Architecture Team  

## Context

Following Phase 3 completion of the Bet-That Flask dashboard, we identified several remaining issues that can be addressed through Claude Skills and Agent architecture. This ADR documents the agent pattern selection for each remaining issue, following the decision tree approach from Anthropic's engineering guidelines.

## Decision Drivers

- **Token Efficiency:** Must stay under 20k tokens per workflow
- **Integration Complexity:** Minimize changes to existing codebase
- **Business Impact:** Address highest-value pain points first
- **Maintainability:** Patterns should be understandable and maintainable
- **Scalability:** Architecture should support future enhancements

## Considered Options

### Option 1: Single Pattern for All Issues
- **Pros:** Consistent approach, easier to implement
- **Cons:** Suboptimal for different problem types, one-size-fits-all approach

### Option 2: Custom Pattern per Issue
- **Pros:** Optimized for each specific problem
- **Cons:** High complexity, difficult to maintain, inconsistent patterns

### Option 3: Hybrid Approach with Standard Patterns
- **Pros:** Balanced approach, uses proven patterns, maintainable
- **Cons:** Requires pattern selection expertise

## Decision Outcome

**Chosen:** Option 3 - Hybrid Approach with Standard Patterns

We will use the standard agent patterns from Anthropic's decision tree, selecting the most appropriate pattern for each remaining issue based on its characteristics.

## Pattern Selection Analysis

### 1. Line Movement Analysis

**Problem:** Compare 9am vs 3pm data snapshots to identify line movements

**Decision Tree Analysis:**
- Can task be decomposed into fixed steps? → **YES**
- **Pattern:** Prompt Chaining
- **Rationale:** Sequential workflow with predictable steps

**Workflow:**
1. Load 9am data snapshot
2. Load 3pm data snapshot  
3. Calculate deltas for each market
4. Identify significant movements (>1.5 points spreads, >2.0 points totals)
5. Classify movement types (steam moves, sharp money, reverse line movement)
6. Generate actionable insights

**Token Budget:** ~6,100 tokens (4k instructions + 2k execution)
**Integration:** `utils/historical_storage.py`, CSV comparison logic

### 2. Alert System

**Problem:** Monitor edge detection and send notifications when strong edges appear

**Decision Tree Analysis:**
- Dynamic subtask breakdown needed? → **YES**
- **Pattern:** Orchestrator-Workers
- **Rationale:** Orchestrator monitors edges, workers handle different notification channels

**Architecture:**
- **Orchestrator:** Edge monitoring coordinator
- **Workers:** Email sender, SMS sender, dashboard notifier, duplicate detector

**Workflow:**
1. Orchestrator runs edge detection on schedule
2. Filters edges by tier (STRONG/GOOD)
3. Checks for duplicates (avoid re-alerting)
4. Routes to appropriate workers based on configuration
5. Workers handle delivery via their respective channels
6. Orchestrator logs delivery status

**Token Budget:** ~5,100 tokens (3.5k instructions + 1.5k execution)
**Integration:** `find_edges.py`, notification services (Twilio, SMTP)

### 3. Dashboard Testing

**Problem:** Automated testing of Flask dashboard functionality

**Decision Tree Analysis:**
- Can parallelize? → **YES**
- **Pattern:** Parallelization
- **Rationale:** Multiple dashboard pages and API endpoints can be tested concurrently

**Architecture:**
- **Test Coordinator:** Orchestrates parallel test execution
- **Parallel Workers:** Page testers, API testers, performance testers

**Workflow:**
1. Test coordinator identifies test scenarios
2. Parallel workers execute tests simultaneously:
   - Page load tests (4 pages)
   - API endpoint tests (5 endpoints)
   - Performance tests (Core Web Vitals)
3. Results aggregated and reported
4. Screenshots and logs captured for failures

**Token Budget:** ~12,100 tokens (8k instructions + 4k execution)
**Integration:** Chrome DevTools MCP, pytest framework

### 4. Enhanced Edge Detection

**Problem:** Conversational interface for edge analysis with parameter refinement

**Decision Tree Analysis:**
- Iterative refinement with feedback? → **YES**
- **Pattern:** Evaluator-Optimizer
- **Rationale:** User provides parameters → system suggests edges → user refines → system re-analyzes

**Workflow:**
1. User provides natural language query
2. System parses parameters (week, model, threshold, bankroll)
3. Evaluator runs edge detection with parsed parameters
4. Optimizer presents results with recommendations
5. User provides feedback or refinement requests
6. System adjusts parameters and re-analyzes
7. Iterative refinement until user satisfied

**Token Budget:** ~10,100 tokens (6k instructions + 4k execution)
**Integration:** `utils/edge_calculator.py`, conversational prompt chaining

### 5. Data Validation Intelligence

**Problem:** ML-powered anomaly detection and data quality insights

**Decision Tree Analysis:**
- Can be decomposed into fixed steps? → **YES**
- **Pattern:** Prompt Chaining
- **Rationale:** Sequential validation workflow with statistical analysis

**Workflow:**
1. Load data for specified week
2. Run schema validation (existing)
3. Statistical analysis for anomalies
4. Pattern detection (outliers, trends, correlations)
5. Quality scoring and insights generation
6. Report generation with recommendations

**Token Budget:** ~7,100 tokens (4.5k instructions + 2.5k execution)
**Integration:** `utils/data_validator.py`, statistical analysis libraries

### 6. API Error Handling

**Problem:** Intelligent error recovery and user guidance for frontend

**Decision Tree Analysis:**
- Distinct categories needing routing? → **YES**
- **Pattern:** Routing
- **Rationale:** Different error types require different recovery strategies

**Error Categories:**
- **Network Errors:** Retry logic, offline mode
- **Validation Errors:** User guidance, field highlighting
- **Data Errors:** Fallback data, error messages
- **System Errors:** Graceful degradation, support contact

**Token Budget:** ~4,000 tokens (3k instructions + 1k execution)
**Integration:** Frontend error handling, Alpine.js components

## Implementation Strategy

### Phase 1: Core Skills (Priority 1)
1. **line-movement-tracker** (Prompt Chaining)
2. **edge-alerter** (Orchestrator-Workers)
3. **dashboard-tester** (Parallelization)

### Phase 2: Enhancement Skills (Priority 2)
4. **bet-edge-analyzer** (Evaluator-Optimizer)
5. **data-validator** (Prompt Chaining)

### Phase 3: Future Skills (Priority 3)
6. **api-error-handler** (Routing)

## Token Budget Analysis

**Per-Workflow Budgets:**
- Line Movement Tracker: 6,100 tokens
- Edge Alerter: 5,100 tokens
- Dashboard Tester: 12,100 tokens
- Bet Edge Analyzer: 10,100 tokens
- Data Validator: 7,100 tokens
- API Error Handler: 4,000 tokens

**Total Budget:** 44,400 tokens across all Skills
**Average per Workflow:** 7,400 tokens
**Maximum per Workflow:** 12,100 tokens
**Target Budget:** <20k tokens per workflow ✅

## Risk Assessment

### High Risk
- **Token Usage Exceeds Budget:** Dashboard tester at 12.1k tokens is close to limit
- **Mitigation:** Optimize instructions, use progressive disclosure, implement caching

### Medium Risk
- **Pattern Complexity:** Orchestrator-Workers pattern for alerts is complex
- **Mitigation:** Start with simple implementation, iterate based on feedback

### Low Risk
- **Integration Issues:** Most patterns integrate well with existing code
- **Mitigation:** Use wrapper functions, minimal code changes

## Monitoring and Metrics

### Pattern Effectiveness
- **Prompt Chaining:** Measure step completion rate and accuracy
- **Orchestrator-Workers:** Monitor worker success rate and coordination efficiency
- **Parallelization:** Track parallel execution time vs sequential
- **Evaluator-Optimizer:** Measure iteration count and user satisfaction
- **Routing:** Track error classification accuracy and recovery success

### Token Usage Monitoring
- Log token usage per Skill execution
- Alert when approaching budget limits
- Optimize heavy Skills first

## Consequences

### Positive
- **Appropriate Patterns:** Each issue gets optimal pattern for its characteristics
- **Token Efficiency:** All workflows under 20k token budget
- **Maintainability:** Standard patterns are well-documented and understood
- **Scalability:** Architecture supports future enhancements

### Negative
- **Complexity:** Multiple patterns require different implementation approaches
- **Learning Curve:** Team needs to understand multiple pattern types
- **Testing:** Different patterns require different testing strategies

### Neutral
- **Development Time:** Slightly longer due to pattern diversity
- **Documentation:** More comprehensive documentation required

## Alternatives Considered

### Alternative 1: All Prompt Chaining
- **Rejected:** Suboptimal for complex workflows like alerts and testing
- **Reason:** Would force simple patterns on complex problems

### Alternative 2: All Orchestrator-Workers
- **Rejected:** Overkill for simple sequential tasks
- **Reason:** Would add unnecessary complexity to simple workflows

### Alternative 3: Custom Patterns
- **Rejected:** High risk, unproven patterns
- **Reason:** Standard patterns are battle-tested and well-documented

## Implementation Timeline

### Week 1: Core Skills
- Day 1-2: line-movement-tracker (Prompt Chaining)
- Day 3-4: edge-alerter (Orchestrator-Workers)
- Day 5-6: dashboard-tester (Parallelization)

### Week 2: Enhancement Skills
- Day 7-8: bet-edge-analyzer (Evaluator-Optimizer)
- Day 9-10: data-validator (Prompt Chaining)

### Week 3: Future Skills
- Day 11-12: api-error-handler (Routing)

## Success Criteria

### Technical Success
- All patterns implemented and tested
- Token budgets met for all workflows
- Integration with existing codebase successful
- Test coverage >80% for all Skills

### Business Success
- Time savings >50% on analysis workflows
- Alert system captures >99% of STRONG edges
- Dashboard testing reduces regression time by >90%
- User satisfaction with enhanced workflows

## Review and Updates

This ADR will be reviewed:
- After Phase 1 completion (Week 1)
- After Phase 2 completion (Week 2)
- Monthly during implementation
- Quarterly for ongoing optimization

Updates will be made based on:
- Token usage patterns
- User feedback
- Performance metrics
- New requirements

---

**Approved by:** Technical Architecture Team  
**Date:** October 21, 2025  
**Next Review:** November 21, 2025
