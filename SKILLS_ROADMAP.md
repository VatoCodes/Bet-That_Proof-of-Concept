# Bet-That Claude Skills Roadmap

## Current Status (Phase 3A - Testing)

### Core Skills (5) ✅ Active
These skills are implemented and available for use via the skills orchestrator.

#### 1. Dashboard Tester
- **Status**: Active
- **Purpose**: Automated browser testing for Flask dashboard
- **Coverage**: All 4 pages, API endpoints, filters, export functionality
- **Location**: `.claude/skills/dashboard-tester/`
- **Usage**: `python .claude/skills_orchestrator.py --skill dashboard_tester --operation run_api_tests`

#### 2. Line Movement Tracker
- **Status**: Active
- **Purpose**: Analyze 9am vs 3pm odds snapshots for sharp money signals
- **Features**: Steam moves, reverse line movement, closing line value
- **Location**: `.claude/skills/line-movement-tracker/`
- **Usage**: `python .claude/skills_orchestrator.py --skill line_movement_tracker --operation compare_snapshots`

#### 3. Edge Alerter
- **Status**: Active
- **Purpose**: Proactive notifications for STRONG/GOOD edges
- **Channels**: Email, SMS, push notifications
- **Location**: `.claude/skills/edge-alerter/`
- **Usage**: `python .claude/skills_orchestrator.py --skill edge_alerter --operation monitor_edges`

#### 4. Bet Edge Analyzer
- **Status**: Active
- **Purpose**: AI-powered conversational edge analysis
- **Features**: Natural language queries, parameter refinement, recommendations
- **Location**: `.claude/skills/bet-edge-analyzer/`
- **Usage**: `python .claude/skills_orchestrator.py --skill bet_edge_analyzer --operation analyze_edge`

#### 5. Data Validator
- **Status**: Active
- **Purpose**: ML-powered anomaly detection and data quality scoring
- **Features**: Schema validation, statistical analysis, outlier detection
- **Location**: `.claude/skills/data-validator/`
- **Usage**: `python .claude/skills_orchestrator.py --skill data_validator --operation validate_all`

---

## Future Skills (4) 🚧 Planning Phase

These skills are planned but not yet implemented. They are removed from the orchestrator to keep the codebase clean during Phase 3.

### 1. Pipeline Health Monitor
- **Priority**: Medium
- **Purpose**: Validate data pipeline health across scrapers, migrations, and snapshots
- **Operations Planned**:
  - `check_freshness`: Verify latest files/DB tables updated within expected windows
  - `check_integrity`: Run validations via `utils/scheduled_validator.py`
  - `summarize_health`: Aggregate results into OK/WARN/ERROR with remediation steps
- **KPIs**: >90% check coverage, <10% false alarms, <10s runtime
- **Location**: `.claude/skills/pipeline_health_monitor/`
- **Prerequisites**:
  - Implement `health_monitor.py` script
  - Define freshness and integrity check rules
  - Integration with existing validators

### 2. Alert Calibration Manager
- **Priority**: Medium
- **Purpose**: Tune alert thresholds using historical outcomes
- **Operations Planned**:
  - `analyze_precision`: Compute precision/recall by current thresholds
  - `recommend_thresholds`: Bayesian calibration for 90% CI
  - `apply_calibration`: Apply recommended thresholds (dry-run default)
  - `backtest_thresholds`: Simulate on last 4-8 weeks
- **Dependencies**: `utils/model_calibration.py` (OutcomeTracker)
- **Location**: `.claude/skills/alert_calibration_manager/`
- **Prerequisites**:
  - Implement `calibration_manager.py` script
  - Create historical outcomes tracking system
  - Set up precision/recall analysis

### 3. Edge Explanation Service
- **Priority**: High
- **Purpose**: Provide dashboard-ready explanations for detected edges
- **Operations Planned**:
  - `explain_edge`: 2-3 sentence explanation for edge_id
  - `list_edge_factors`: Top 3 contributors summing to 100%
  - `generate_confidence_breakdown`: Confidence weights
  - `format_for_dashboard`: JSON payload ready for UI
- **Integration**: Reuse bet_edge_analyzer outputs, cache for 15 minutes
- **Location**: `.claude/skills/edge_explanation_service/`
- **Prerequisites**:
  - Implement `explanation_service.py` script
  - Create Flask route `/api/edge/explain/<edge_id>`
  - Set up 15-minute caching mechanism

### 4. Week Rollover Operator
- **Priority**: Medium
- **Purpose**: Automate weekly data lifecycle with safety checks
- **Operations Planned**:
  - `prepare_rollover`: Validate data integrity and preconditions
  - `execute_rollover`: Backup DB, archive last week, create new week tables
  - `rollback_rollover`: Restore from backup on failure
  - `schedule_rollover`: Configure Tuesday 3am ET trigger
- **Safety**: Transactional writes, DB locking, auto-rollback on failure
- **Location**: `.claude/skills/week_rollover_operator/`
- **Prerequisites**:
  - Implement `rollover_operator.py` script
  - Set up automated backup system
  - Create archive management system
  - Implement rollback mechanism

---

## Implementation Phases

### Phase 3A (Current) ✅
- Clean up orchestrator to use only 5 working skills
- Document planned skills in this roadmap
- Prepare codebase for Phase 3B

### Phase 3B (Q4 2025)
- **Goal**: Implement 1-2 highest priority future skills
- **Recommended Order**:
  1. Edge Explanation Service (high priority, UI-facing)
  2. Pipeline Health Monitor (medium priority, operational)
- **Effort**: ~20 hours per skill
- **Testing**: Unit tests + integration tests

### Phase 4 (Q1 2026)
- Implement remaining 2 skills
- Full system integration testing
- Production deployment

---

## Activation Instructions

### When Ready to Activate a Future Skill:

1. **Implement the skill scripts**
   ```bash
   # Example for Edge Explanation Service
   touch .claude/skills/edge_explanation_service/scripts/explanation_service.py
   # Implement the service methods
   ```

2. **Update the orchestrator imports**
   ```python
   # In .claude/skills_orchestrator.py line 36-41
   # Uncomment the import for the skill
   ```

3. **Initialize the skill**
   ```python
   # In __init__ method, uncomment skill initialization
   # Add to self.skills dictionary
   ```

4. **Add routing logic**
   ```python
   # In _execute_skill_operation, uncomment skill routing
   # Implement specific execution methods (uncomment from lines 248-273)
   ```

5. **Update configuration**
   ```python
   # In _load_config, uncomment skill configuration
   # Set enabled=True and appropriate schedule
   ```

6. **Test thoroughly**
   ```bash
   python .claude/skills_orchestrator.py --status
   python .claude/skills_orchestrator.py --skill <name> --operation <op>
   ```

---

## Skill Implementation Checklist

For each future skill, ensure:

- [ ] SKILL.md documentation exists
- [ ] Python script implementation in `scripts/` directory
- [ ] Configuration file in `resources/` directory (if needed)
- [ ] Error handling and logging
- [ ] Unit tests
- [ ] Integration tests with orchestrator
- [ ] Documentation with examples
- [ ] Comments for uncommenting in orchestrator

---

## Monitoring Current Skills

### Skill Execution
```bash
# Check system status
python .claude/skills_orchestrator.py --status

# View execution history
python .claude/skills_orchestrator.py --history

# Execute specific skill
python .claude/skills_orchestrator.py --skill data_validator --operation validate_all

# Run all scheduled tasks
python .claude/skills_orchestrator.py --scheduled
```

### Logs
- Dashboard Tester: `logs/dashboard_tests.log`
- Edge Alerter: `logs/edge_alerts.log`
- Data Validator: `logs/data_validation.log`
- Orchestrator: Console output + logging

---

## Integration Points

### Flask Dashboard Integration
The following future skills need Flask routes:
- **Edge Explanation Service**: `/api/edge/explain/<edge_id>`
- **Pipeline Health Monitor**: `/api/system/health`

### Database Integration
- Alert Calibration Manager: Requires outcome tracking in database
- Week Rollover Operator: Requires backup/archive tables

### External Services
- Edge Alerter: Email (SMTP), SMS (Twilio)
- Other skills: Database only

---

## Performance Targets

| Skill | Response Time | Token Usage | Accuracy |
|-------|---------------|-------------|----------|
| Dashboard Tester | <2 min | ~8,000 | >95% pass rate |
| Line Movement Tracker | <10 sec | ~6,100 | >90% accuracy |
| Edge Alerter | <60 sec | ~5,100 | >99% delivery |
| Bet Edge Analyzer | <30 sec | ~10,100 | 100% match CLI |
| Data Validator | <5 sec | ~7,100 | >95% detection |

---

## Known Issues & Notes

### Current (Phase 3A)
- 4 future skills removed from active orchestrator to prevent import errors
- Placeholder SKILL.md files exist for documentation purposes
- All 5 core skills are production-ready

### Future Considerations
- May need to optimize token usage for faster skill execution
- Consider caching frequently accessed data (e.g., edge explanations)
- Monitor database performance as skills multiply concurrent operations
- Plan for skill execution queuing if >3 concurrent skills needed

---

## Questions or Updates?

Update this roadmap when:
- A future skill is activated
- New skills are planned
- Priorities change based on user feedback
- Technical implementation approaches change

---

**Last Updated**: October 22, 2025
**Maintained By**: Claude Code
**Status**: Active
