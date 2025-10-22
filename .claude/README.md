# Bet-That Claude Skills & Agents Implementation

This document provides a comprehensive overview of the Claude Skills and Agents implementation for the Bet-That NFL betting analysis system.

## 🎯 Overview

The Bet-That Claude Skills implementation provides intelligent automation and analysis capabilities for NFL betting edge detection. The system consists of five core skills that work together to provide comprehensive betting analysis, data validation, and automated testing.

## 🏗️ Architecture

### Core Skills

1. **Line Movement Tracker** (`line-movement-tracker`)
   - Monitors betting line movements across different sportsbooks
   - Detects significant changes in odds
   - Provides alerts for line movement opportunities

2. **Edge Alerter** (`edge-alerter`)
   - Continuously monitors for new betting edge opportunities
   - Sends notifications via email and SMS
   - Implements smart alerting with cooldown periods

3. **Dashboard Tester** (`dashboard-tester`)
   - Automated browser testing using Chrome DevTools MCP
   - API endpoint validation
   - UI interaction testing

4. **Bet Edge Analyzer** (`bet-edge-analyzer`)
   - Conversational analysis of betting opportunities
   - Natural language explanations of edge calculations
   - Detailed risk assessments and recommendations

5. **Data Validator** (`data-validator`)
   - ML-powered anomaly detection
   - Comprehensive data quality scoring
   - Schema validation and consistency checks

### Integration Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Validator │    │  Line Movement  │    │   Edge Alerter  │
│                 │    │    Tracker      │    │                 │
│ • Anomaly Det.  │    │ • Snapshot Comp.│    │ • Edge Monitor   │
│ • Quality Score │    │ • Movement Anal. │    │ • Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Skills           │
                    │ Orchestrator     │
                    │                 │
                    │ • Coordination   │
                    │ • Scheduling     │
                    │ • Error Handling │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Bet Edge        │
                    │ Analyzer        │
                    │                 │
                    │ • Conversational │
                    │ • Risk Analysis  │
                    │ • Recommendations│
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Dashboard       │
                    │ Tester          │
                    │                 │
                    │ • Browser Tests  │
                    │ • API Tests      │
                    │ • Chrome MCP     │
                    └─────────────────┘
```

## 📁 File Structure

```
.claude/
├── skills/
│   ├── line-movement-tracker/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── compare_snapshots.py
│   │   │   └── movement_analyzer.py
│   │   └── resources/
│   │       └── movement_thresholds.json
│   ├── edge-alerter/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── edge_monitor.py
│   │   │   ├── notification_system.py
│   │   │   └── notifications/
│   │   │       ├── email_sender.py
│   │   │       └── sms_sender.py
│   │   └── resources/
│   │       ├── alert_config.json
│   │       └── notification_templates.json
│   ├── dashboard-tester/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── test_orchestrator.py
│   │   │   └── chrome_devtools_mcp.py
│   │   └── scenarios/
│   │       ├── test_flows.json
│   │       └── api_test_suite.json
│   ├── bet-edge-analyzer/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── conversational_analyzer.py
│   │   └── resources/
│   │       └── model_configs.json
│   └── data-validator/
│       ├── SKILL.md
│       ├── scripts/
│       │   └── enhanced_validator.py
│       └── resources/
│           └── validation_rules.json
├── skills_orchestrator.py
├── test_suite.py
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Chrome browser (for dashboard testing)
- Bet-That system running
- Required Python packages (see requirements.txt)

### Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd Bet-That_(Proof of Concept)
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Chrome DevTools**:
   - Ensure Chrome is installed
   - Chrome will be automatically launched with DevTools enabled

4. **Configure notifications** (optional):
   - Edit `.claude/skills/edge-alerter/resources/alert_config.json`
   - Add email/SMS configuration

### Basic Usage

1. **Run the skills orchestrator**:
   ```bash
   python .claude/skills_orchestrator.py --status
   ```

2. **Execute a specific skill**:
   ```bash
   python .claude/skills_orchestrator.py --skill data_validator --operation validate_all
   ```

3. **Run scheduled tasks**:
   ```bash
   python .claude/skills_orchestrator.py --scheduled
   ```

## 🔧 Skill Details

### Line Movement Tracker

**Purpose**: Monitor betting line movements and detect significant changes.

**Key Features**:
- Snapshot comparison between different time periods
- Movement analysis with configurable thresholds
- Integration with historical data storage

**Usage**:
```python
from .claude.skills.line_movement_tracker.scripts.compare_snapshots import SnapshotComparator

comparator = SnapshotComparator()
result = await comparator.compare_snapshots(week=1, snapshot_type="odds")
```

### Edge Alerter

**Purpose**: Continuously monitor for betting edge opportunities and send alerts.

**Key Features**:
- Real-time edge monitoring
- Email and SMS notifications
- Smart alerting with cooldown periods
- Configurable alert thresholds

**Usage**:
```python
from .claude.skills.edge_alerter.scripts.edge_monitor import EdgeMonitor

monitor = EdgeMonitor()
result = await monitor.monitor_edges(week=1, threshold=0.05)
```

### Dashboard Tester

**Purpose**: Automated testing of the Bet-That dashboard using browser automation.

**Key Features**:
- Chrome DevTools MCP integration
- Browser interaction testing
- API endpoint validation
- Screenshot capture

**Usage**:
```python
from .claude.skills.dashboard_tester.scripts.chrome_devtools_mcp import ChromeDevToolsMCP

chrome_mcp = ChromeDevToolsMCP()
result = await chrome_mcp.run_full_test_suite()
```

### Bet Edge Analyzer

**Purpose**: Provide conversational analysis of betting opportunities.

**Key Features**:
- Natural language explanations
- Detailed risk assessments
- Historical context analysis
- Betting recommendations

**Usage**:
```python
from .claude.skills.bet_edge_analyzer.scripts.conversational_analyzer import ConversationalAnalyzer

analyzer = ConversationalAnalyzer()
analysis = analyzer.analyze_edge_opportunity(edge_data)
```

### Data Validator

**Purpose**: Comprehensive data validation with ML-powered anomaly detection.

**Key Features**:
- Schema validation
- Anomaly detection using Isolation Forest
- Quality scoring
- Cross-table consistency checks

**Usage**:
```python
from .claude.skills.data_validator.scripts.enhanced_validator import EnhancedDataValidator

validator = EnhancedDataValidator()
result = validator.validate_all()
```

## 🧪 Testing

### Running Tests

1. **Unit Tests**:
   ```bash
   python .claude/test_suite.py --unit
   ```

2. **Integration Tests**:
   ```bash
   python .claude/test_suite.py --integration
   ```

3. **Comprehensive Test Suite**:
   ```bash
   python .claude/test_suite.py --comprehensive
   ```

### Test Coverage

The test suite covers:
- Individual skill functionality
- Skill integration
- Error handling
- Data validation
- Browser automation
- Notification systems

## 📊 Monitoring & Logging

### Logging Configuration

All skills use Python's logging module with configurable levels:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Execution History

The orchestrator maintains execution history for monitoring:

```python
orchestrator = BetThatSkillsOrchestrator()
history = orchestrator.get_execution_history(limit=50)
```

### System Status

Get overall system status:

```python
status = await orchestrator.get_system_status()
```

## 🔧 Configuration

### Skill Configuration

Each skill can be configured through its respective configuration files:

- **Line Movement Tracker**: `movement_thresholds.json`
- **Edge Alerter**: `alert_config.json`, `notification_templates.json`
- **Dashboard Tester**: `test_flows.json`, `api_test_suite.json`
- **Bet Edge Analyzer**: `model_configs.json`
- **Data Validator**: `validation_rules.json`

### Orchestrator Configuration

The orchestrator configuration is defined in `skills_orchestrator.py`:

```python
self.config = {
    "skills": {
        "line_movement_tracker": {
            "enabled": True,
            "schedule": "every_6_hours",
            "dependencies": ["data_validator"]
        },
        # ... other skills
    },
    "execution": {
        "max_concurrent_skills": 3,
        "timeout_seconds": 300,
        "retry_attempts": 3
    }
}
```

## 🚨 Error Handling

### Skill Error Handling

Each skill implements comprehensive error handling:

```python
try:
    # Skill operation
    result = await skill_operation()
    return {"status": "success", "result": result}
except Exception as e:
    logger.error(f"Skill operation failed: {e}")
    return {"status": "error", "message": str(e)}
```

### Orchestrator Error Handling

The orchestrator handles skill failures gracefully:

- Retries failed operations
- Continues execution of other skills
- Logs detailed error information
- Maintains execution history

## 📈 Performance Considerations

### Token Efficiency

Skills are designed with token efficiency in mind:

- **Level 1**: Metadata (~100 tokens)
- **Level 2**: Instructions (<5k tokens)
- **Level 3**: Resources (unlimited)

### Concurrent Execution

The orchestrator supports concurrent skill execution:

```python
max_concurrent_skills = 3
timeout_seconds = 300
```

### Resource Management

- Temporary files are cleaned up automatically
- Database connections are properly managed
- Browser sessions are terminated after use

## 🔒 Security Considerations

### API Key Management

- API keys are stored securely
- Rotation is handled automatically
- No hardcoded credentials

### Data Privacy

- No sensitive data is logged
- User data is handled securely
- Database access is controlled

## 🚀 Deployment

### Production Deployment

1. **Set up production database**
2. **Configure production notification settings**
3. **Set up monitoring and alerting**
4. **Deploy to production environment**

### Docker Deployment

```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", ".claude/skills_orchestrator.py", "--scheduled"]
```

## 📚 API Reference

### Skills Orchestrator API

#### `execute_skill(skill_name, operation, **kwargs)`

Execute a specific skill operation.

**Parameters**:
- `skill_name` (str): Name of the skill to execute
- `operation` (str): Specific operation to perform
- `**kwargs`: Additional parameters for the operation

**Returns**: Dictionary with execution results

#### `run_scheduled_tasks()`

Run all scheduled tasks.

**Returns**: Dictionary with execution results

#### `get_system_status()`

Get overall system status.

**Returns**: Dictionary with system status information

### Skill APIs

Each skill exposes specific APIs documented in their respective `SKILL.md` files.

## 🤝 Contributing

### Development Guidelines

1. **Follow PEP 8** for Python code style
2. **Add comprehensive tests** for new features
3. **Update documentation** for API changes
4. **Use type hints** for better code clarity

### Adding New Skills

1. **Create skill directory** with `SKILL.md` file
2. **Implement skill scripts** in `scripts/` directory
3. **Add configuration** in `resources/` directory
4. **Update orchestrator** to include new skill
5. **Add tests** for new skill functionality

## 📞 Support

### Troubleshooting

1. **Check logs** for error messages
2. **Verify configuration** files
3. **Run tests** to identify issues
4. **Check system status** for overall health

### Common Issues

1. **Chrome not starting**: Ensure Chrome is installed and accessible
2. **Database connection errors**: Check database path and permissions
3. **Notification failures**: Verify email/SMS configuration
4. **Test failures**: Check if Bet-That system is running

## 📄 License

This implementation is part of the Bet-That project and follows the same licensing terms.

## 🎉 Acknowledgments

- Claude Skills and Agents framework
- Chrome DevTools Protocol
- Bet-That development team
- Open source contributors

---

**Last Updated**: January 2025
**Version**: 1.0.0
**Status**: Production Ready
