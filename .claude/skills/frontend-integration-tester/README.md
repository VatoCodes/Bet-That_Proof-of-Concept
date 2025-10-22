# Frontend Integration Tester Skill

## Quick Start

```bash
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)

# List available test scenarios
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py --list

# Run all integration tests
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py

# Run specific scenario
python .claude/skills/frontend-integration-tester/scripts/api_integration_test_runner.py --scenario edges_api_test
```

## Features

- ✅ Browser automation with Chrome DevTools
- ✅ Network inspection & API call capture
- ✅ Field extraction validation
- ✅ JavaScript error detection
- ✅ DOM population verification
- ✅ Screenshots on failures
- ✅ Configurable test scenarios

## Files

- `api_integration_test_runner.py` - Main test orchestrator
- `response_inspector.py` - Chrome network inspector
- `field_mapper.py` - Field extraction validator
- `scenarios/edges_api_test.json` - Edges page test
- `scenarios/dashboard_api_test.json` - Dashboard test
- `resources/integration_config.json` - Configuration

## Integration

```python
from .claude.skills.frontend_integration_tester.scripts.api_integration_test_runner import IntegrationTestRunner

runner = IntegrationTestRunner()
results = runner.run_all_tests()

if results['failed']:
    print(f"❌ {len(results['failed'])} tests failed")
```

See SKILL.md for detailed documentation.
