# API Contract Validator Skill

## Quick Start

```bash
cd /Users/vato/work/Bet-That_\(Proof\ of\ Concept\)

# Generate API contracts from live API
python .claude/skills/api-contract-validator/scripts/schema_generator.py

# Validate all endpoints
python .claude/skills/api-contract-validator/scripts/contract_validator.py

# Scan frontend for API usage
python .claude/skills/api-contract-validator/scripts/frontend_scanner.py
```

## Features

- ✅ Validates 8+ API endpoints
- ✅ Detects missing/changed fields
- ✅ Scans frontend templates for API calls
- ✅ Auto-generates schemas
- ✅ Suggests field name mappings
- ✅ HTML validation reports

## Files

- `contract_validator.py` - Main validation engine
- `frontend_scanner.py` - Scans templates/JS for API usage
- `schema_generator.py` - Auto-generates contracts from API
- `resources/api_contracts.json` - Expected API schemas
- `resources/validation_config.json` - Configuration
- `resources/field_mappings.json` - Field name mappings

## Integration

```python
from .claude.skills.api_contract_validator.scripts.contract_validator import APIContractValidator

validator = APIContractValidator()
results = validator.validate_all_endpoints()

if results['failed']:
    print(f"❌ {len(results['failed'])} endpoints failed validation")
```

See SKILL.md for detailed documentation.
