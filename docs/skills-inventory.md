# Skills Inventory - Bet-That Implementation

**Date:** October 21, 2025  
**Status:** Phase 1 Complete - Ready for Implementation  
**Version:** 1.0  

## Overview

This document provides detailed specifications for all Skills to be implemented for the Bet-That NFL betting analysis system. Skills are prioritized based on business impact and implementation complexity.

## Priority 1: Core Skills (Addressing Remaining Issues)

### 1. line_movement_tracker

**Name:** `line_movement_tracker`  
**Description:** Analyze NFL betting line movements between morning (9am) and afternoon (3pm) data scrapes. Detects sharp money, steam moves, reverse line movement, and closing line value opportunities. Use when analyzing odds changes, tracking line movement patterns, or identifying valuable betting signals from market movement.  
**Pattern:** Prompt Chaining  
**Token Budget:** ~6,100 tokens (4k instructions + 2k execution)  
**Priority:** 1a (Highest)  

**Trigger Conditions:**
- User requests line movement analysis
- Keywords: "line movement", "steam moves", "sharp money", "odds changes"
- Context: Week number or date range specified

**Tool Dependencies:**
- `bash_tool` - Execute Python scripts
- `read_file` - Access CSV data files
- `grep` - Search for specific data patterns

**Integration Points:**
- `utils/historical_storage.py` - Access timestamped snapshots
- `data/historical/2025/week_X/` - Historical data directory
- `scripts/compare_snapshots.py` - Data comparison logic
- `scripts/movement_analyzer.py` - Movement classification

**Success Metrics:**
- **Accuracy:** >90% of steam moves correctly identified
- **Latency:** Analysis completes in <10 seconds
- **Insight Quality:** Generates actionable recommendations
- **False Positives:** <10% of flagged movements are noise

**Resource Files:**
- `movement_thresholds.json` - Configurable thresholds
- `sharp_money_indicators.json` - Detection rules

---

### 2. edge_alerter

**Name:** `edge_alerter`  
**Description:** Monitor betting edge opportunities and send proactive notifications via email, SMS, or dashboard alerts when STRONG or GOOD edges are detected. Use when setting up automated monitoring, configuring alert preferences, or troubleshooting notification delivery.  
**Pattern:** Orchestrator-Workers  
**Token Budget:** ~5,100 tokens (3.5k instructions + 1.5k execution)  
**Priority:** 1b (High)  

**Trigger Conditions:**
- Scheduled monitoring (every 15 minutes)
- User requests alert configuration
- Keywords: "alerts", "notifications", "monitor edges"

**Tool Dependencies:**
- `bash_tool` - Execute edge detection and notification scripts
- `read_file` - Access configuration files

**Integration Points:**
- `find_edges.py` - Edge detection CLI
- `scripts/notifications/email_sender.py` - Email delivery
- `scripts/notifications/sms_sender.py` - SMS delivery
- `dashboard/app.py` - In-app alerts

**Success Metrics:**
- **Delivery Success:** >99% notification delivery rate
- **Latency:** Alerts sent within 60 seconds of edge detection
- **Relevance:** <5% false alerts (user feedback)
- **Coverage:** Captures 100% of STRONG edges

**Resource Files:**
- `alert_config.json` - Notification preferences
- `notification_templates.json` - Message templates

---

### 3. dashboard_tester

**Name:** `dashboard_tester`  
**Description:** Automated browser testing for Bet-That Flask dashboard using Chrome DevTools MCP. Tests all pages (index, edges, stats, tracker), API endpoints, filters, export functionality, and responsive design. Use when validating dashboard changes, running regression tests, or debugging UI issues.  
**Pattern:** Parallelization  
**Token Budget:** ~12,100 tokens (8k instructions + 4k execution)  
**Priority:** 1c (High)  

**Trigger Conditions:**
- User requests dashboard testing
- Keywords: "test dashboard", "regression tests", "UI validation"
- Context: Specific pages or features to test

**Tool Dependencies:**
- `chrome-devtools:*` - All 27 browser automation tools

**Integration Points:**
- `dashboard/app.py` - Flask app under test
- `tests/browser/test_dashboard_e2e.py` - pytest integration
- Chrome DevTools MCP - Browser automation

**Success Metrics:**
- **Coverage:** >80% of dashboard features tested
- **Pass Rate:** >95% tests passing consistently
- **Reliability:** <5% flaky tests
- **Speed:** Full suite <2 minutes

**Resource Files:**
- `test_flows.json` - Test scenarios
- `api_test_suite.json` - API endpoint tests

---

## Priority 2: Enhancement Skills

### 4. bet_edge_analyzer

**Name:** `bet_edge_analyzer`  
**Description:** AI-powered edge analysis with natural language queries and dashboard integration. Enhanced edge detection workflow with conversational interface for parameter refinement and recommendation generation. Use when analyzing betting opportunities, refining analysis parameters, or getting personalized recommendations.  
**Pattern:** Evaluator-Optimizer  
**Token Budget:** ~10,100 tokens (6k instructions + 4k execution)  
**Priority:** 2a (Medium)  

**Trigger Conditions:**
- User requests edge analysis with natural language
- Keywords: "analyze edges", "find opportunities", "betting analysis"
- Context: Specific teams, weeks, or parameters mentioned

**Tool Dependencies:**
- `bash_tool` - Execute edge calculation scripts
- `read_file` - Access model configurations

**Integration Points:**
- `utils/edge_calculator.py` - Edge detection engine
- `utils/query_tools.py` - Database queries
- `dashboard/app.py` - Dashboard integration

**Success Metrics:**
- **Usability:** Natural language queries work >90% of time
- **Accuracy:** Matches CLI results 100%
- **Latency:** Responses in <30 seconds
- **User Satisfaction:** Positive qualitative feedback

**Resource Files:**
- `model_configs.json` - Edge calculator parameters

---

### 5. data_validator

**Name:** `data_validator`  
**Description:** ML-powered anomaly detection and data quality insights beyond basic validation. Statistical analysis of data patterns, outlier detection, and automated quality reporting. Use when validating data quality, detecting anomalies, or ensuring data integrity.  
**Pattern:** Prompt Chaining  
**Token Budget:** ~7,100 tokens (4.5k instructions + 2.5k execution)  
**Priority:** 2b (Medium)  

**Trigger Conditions:**
- User requests data validation
- Keywords: "validate data", "check quality", "find anomalies"
- Context: Specific week or data type mentioned

**Tool Dependencies:**
- `bash_tool` - Execute validation scripts
- `read_file` - Access data files

**Integration Points:**
- `utils/data_validator.py` - Basic validation
- `utils/week_manager.py` - Week tracking
- `utils/db_manager.py` - Database operations

**Success Metrics:**
- **Detection Rate:** Catches >95% of known anomalies
- **False Positives:** <15% of flagged anomalies are normal variance
- **Latency:** Validation completes in <5 seconds
- **Coverage:** All data tables validated

**Resource Files:**
- `validation_rules.json` - Validation rules and thresholds

---

## Priority 3: Future Skills (Later Implementation)

### 6. api_error_handler

**Name:** `api_error_handler`  
**Description:** Intelligent API error recovery and user guidance for frontend resilience. Smart error categorization, automatic retry logic, and user-friendly error messages. Use when handling API failures, debugging frontend issues, or improving user experience during errors.  
**Pattern:** Routing  
**Token Budget:** ~4,000 tokens (3k instructions + 1k execution)  
**Priority:** 3a (Future)  

### 7. model_calibrator

**Name:** `model_calibrator`  
**Description:** Automated model calibration tracking and performance monitoring. Outcome tracking, accuracy measurement, and model improvement recommendations. Use when tracking model performance, calibrating predictions, or improving edge detection accuracy.  
**Pattern:** Prompt Chaining  
**Token Budget:** ~6,000 tokens (4k instructions + 2k execution)  
**Priority:** 3b (Future)  

### 8. qb_matchup_analyzer

**Name:** `qb_matchup_analyzer`  
**Description:** Deep QB vs defense matchup analysis with advanced statistical modeling. Historical performance analysis, weather impact, injury reports, and matchup-specific insights. Use when analyzing specific QB matchups, getting detailed insights, or preparing for games.  
**Pattern:** Evaluator-Optimizer  
**Token Budget:** ~8,000 tokens (5k instructions + 3k execution)  
**Priority:** 3c (Future)  

### 9. performance_monitor

**Name:** `performance_monitor`  
**Description:** Dashboard performance monitoring and optimization recommendations. Core Web Vitals tracking, performance bottleneck identification, and optimization suggestions. Use when monitoring dashboard performance, identifying issues, or optimizing user experience.  
**Pattern:** Parallelization  
**Token Budget:** ~5,000 tokens (3k instructions + 2k execution)  
**Priority:** 3d (Future)  

---

## Implementation Summary

### Token Budget Analysis

**Priority 1 Skills (3 total):**
- Line Movement Tracker: 6,100 tokens
- Edge Alerter: 5,100 tokens
- Dashboard Tester: 12,100 tokens
- **Total:** 23,300 tokens
- **Average:** 7,767 tokens per Skill

**Priority 2 Skills (2 total):**
- Bet Edge Analyzer: 10,100 tokens
- Data Validator: 7,100 tokens
- **Total:** 17,200 tokens
- **Average:** 8,600 tokens per Skill

**Priority 3 Skills (4 total):**
- API Error Handler: 4,000 tokens
- Model Calibrator: 6,000 tokens
- QB Matchup Analyzer: 8,000 tokens
- Performance Monitor: 5,000 tokens
- **Total:** 23,000 tokens
- **Average:** 5,750 tokens per Skill

**Overall Summary:**
- **Total Skills:** 9
- **Total Token Budget:** 63,500 tokens
- **Average per Skill:** 7,056 tokens
- **Maximum per Skill:** 12,100 tokens
- **Target Budget:** <20k tokens per workflow ✅

### Implementation Timeline

**Week 1-2: Priority 1 Skills**
- Day 1-2: Line Movement Tracker
- Day 3-4: Edge Alerter
- Day 5-6: Dashboard Tester
- Day 7-8: Integration testing

**Week 3: Priority 2 Skills**
- Day 9-10: Bet Edge Analyzer
- Day 11-12: Data Validator
- Day 13-14: Integration testing

**Week 4+: Priority 3 Skills**
- As needed based on user feedback
- Model Calibrator (Phase 3.5)
- Additional Skills based on usage patterns

### Success Metrics

**Technical Metrics:**
- **Token Efficiency:** All Skills under 20k token budget
- **Response Latency:** <30 seconds per analysis
- **Test Coverage:** >80% of dashboard features
- **Alert Delivery:** >99% success rate

**Business Metrics:**
- **Time Savings:** >50% reduction in analysis time
- **Opportunity Capture:** <2% missed STRONG edges
- **Quality Improvement:** 3x more data issues caught
- **Testing Efficiency:** 20x faster regression testing

**User Experience Metrics:**
- **Usability:** >90% natural language query success
- **Satisfaction:** Positive qualitative feedback
- **Adoption:** Daily usage by team members
- **Error Rate:** <5% false alerts/analysis

### Risk Assessment

**High Risk:**
- **Token Usage Exceeds Budget:** Dashboard tester at 12.1k tokens
- **Mitigation:** Optimize instructions, progressive disclosure

**Medium Risk:**
- **Pattern Complexity:** Orchestrator-Workers for alerts
- **Mitigation:** Start simple, iterate based on feedback

**Low Risk:**
- **Integration Issues:** Most patterns integrate well
- **Mitigation:** Wrapper functions, minimal code changes

### Next Steps

1. **Approve Skills Inventory** - Review and confirm specifications
2. **Begin Implementation** - Start with Priority 1 Skills
3. **Create File Structure** - Set up `.claude/skills/` directory
4. **Implement SKILL.md Files** - Complete YAML frontmatter and instructions
5. **Develop Scripts** - Create Python scripts for each Skill
6. **Test and Refine** - Iterate based on testing results

---

**Document Status:** Complete  
**Next Review:** After Priority 1 implementation  
**Approved by:** Technical Architecture Team  
**Date:** October 21, 2025
