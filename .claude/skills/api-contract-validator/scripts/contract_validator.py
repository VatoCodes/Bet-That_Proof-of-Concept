#!/usr/bin/env python3
"""
API Contract Validator - Main validation logic
Validates API responses match expected contracts
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys


class APIContractValidator:
    """Validates API responses against defined contracts"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize validator with configuration

        Args:
            config_path: Path to validation_config.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "resources" / "validation_config.json"

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # Use defaults if config doesn't exist yet
            self.config = {
                "backend_url": "http://localhost:5001",
                "validation_mode": "strict"
            }

        self.contracts_path = Path(__file__).parent.parent / "resources" / "api_contracts.json"
        self.contracts = self._load_contracts()
        self.backend_url = self.config.get('backend_url', 'http://localhost:5001')
        self.validation_mode = self.config.get('validation_mode', 'strict')

    def _load_contracts(self) -> Dict[str, Any]:
        """Load API contracts from JSON file"""
        if not self.contracts_path.exists():
            return {}

        try:
            with open(self.contracts_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading contracts: {e}")
            return {}

    def validate_all_endpoints(self) -> Dict[str, Any]:
        """
        Validate all endpoints defined in contracts

        Returns:
            Dictionary with 'passed', 'failed', 'warnings' lists
        """
        print(f"\n{'='*60}")
        print("🔍 API Contract Validation Starting")
        print(f"{'='*60}\n")

        results = {
            "passed": [],
            "failed": [],
            "warnings": [],
            "timestamp": datetime.now().isoformat(),
            "validation_mode": self.validation_mode
        }

        if not self.contracts:
            print("⚠️  No contracts defined. Run schema_generator.py first.")
            return results

        for endpoint, contract in self.contracts.items():
            print(f"Testing: {endpoint}")
            result = self._test_endpoint(endpoint, contract)

            if result['status'] == 'pass':
                print(f"  ✅ PASS")
                results['passed'].append(result)
            elif result['status'] == 'fail':
                print(f"  ❌ FAIL - {len(result['mismatches'])} issues")
                results['failed'].append(result)
            else:
                print(f"  ⚠️  WARNING")
                results['warnings'].append(result)

        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ Passed: {len(results['passed'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        print(f"⚠️  Warnings: {len(results['warnings'])}")
        print(f"{'='*60}\n")

        return results

    def _test_endpoint(self, endpoint: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a single endpoint against its contract

        Args:
            endpoint: API endpoint path (e.g., "/api/edges")
            contract: Expected contract definition

        Returns:
            Validation result dictionary
        """
        result = {
            'endpoint': endpoint,
            'status': 'pass',
            'mismatches': [],
            'response_sample': None,
            'tested_at': datetime.now().isoformat()
        }

        try:
            # Build request URL with required params
            url = f"{self.backend_url}{endpoint}"
            params = self._build_test_params(contract)

            # Make API request
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                result['status'] = 'fail'
                result['mismatches'].append(
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )
                return result

            data = response.json()
            result['response_sample'] = self._truncate_sample(data)

            # Validate response structure
            self._validate_required_fields(data, contract, result)
            self._validate_field_types(data, contract, result)
            self._validate_nested_arrays(data, contract, result)

            # Set final status
            if result['mismatches']:
                result['status'] = 'fail' if self.validation_mode == 'strict' else 'warning'

        except requests.exceptions.RequestException as e:
            result['status'] = 'fail'
            result['mismatches'].append(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            result['status'] = 'fail'
            result['mismatches'].append(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            result['status'] = 'fail'
            result['mismatches'].append(f"Unexpected error: {str(e)}")

        return result

    def _build_test_params(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Build test parameters for API request"""
        params = {}

        # Add required parameters with default values
        for param in contract.get('required_params', []):
            if param == 'week':
                params[param] = 7  # Use week 7 for testing
            elif param == 'strategy':
                params[param] = 'all'
            elif param == 'min_edge':
                params[param] = 0

        return params

    def _validate_required_fields(self, data: Dict[str, Any],
                                   contract: Dict[str, Any],
                                   result: Dict[str, Any]) -> None:
        """Validate all required fields are present"""
        for field in contract.get('required_fields', []):
            if field not in data:
                result['mismatches'].append(
                    f"❌ Missing required field: '{field}'"
                )

                # Suggest similar field names
                suggestions = self._find_similar_fields(field, data.keys())
                if suggestions:
                    result['mismatches'].append(
                        f"   💡 Did you mean: {', '.join(suggestions)}?"
                    )

    def _validate_field_types(self, data: Dict[str, Any],
                               contract: Dict[str, Any],
                               result: Dict[str, Any]) -> None:
        """Validate field types match expectations"""
        for field, expected_type in contract.get('field_types', {}).items():
            if field not in data:
                continue

            actual_type = type(data[field]).__name__

            # Handle type aliases
            type_map = {
                'bool': 'bool',
                'boolean': 'bool',
                'int': 'int',
                'integer': 'int',
                'float': 'float',
                'number': 'float',
                'str': 'str',
                'string': 'str',
                'list': 'list',
                'array': 'list',
                'dict': 'dict',
                'object': 'dict'
            }

            expected_type_normalized = type_map.get(expected_type.lower(), expected_type)

            if actual_type != expected_type_normalized:
                result['mismatches'].append(
                    f"❌ Type mismatch for '{field}': "
                    f"expected {expected_type}, got {actual_type}"
                )

    def _validate_nested_arrays(self, data: Dict[str, Any],
                                 contract: Dict[str, Any],
                                 result: Dict[str, Any]) -> None:
        """Validate nested array structures (e.g., edges[])"""
        nested_arrays = contract.get('nested_arrays', {})

        for array_field, array_contract in nested_arrays.items():
            if array_field not in data:
                continue

            if not isinstance(data[array_field], list):
                result['mismatches'].append(
                    f"❌ Field '{array_field}' should be a list"
                )
                continue

            if len(data[array_field]) == 0:
                result['mismatches'].append(
                    f"⚠️  Array '{array_field}' is empty - cannot validate structure"
                )
                continue

            # Validate first item as sample
            item = data[array_field][0]

            for req_field in array_contract.get('required_fields', []):
                if req_field not in item:
                    result['mismatches'].append(
                        f"❌ Missing field in {array_field}[]: '{req_field}'"
                    )

                    # Suggest similar field names
                    suggestions = self._find_similar_fields(req_field, item.keys())
                    if suggestions:
                        result['mismatches'].append(
                            f"   💡 Did you mean: {', '.join(suggestions)}?"
                        )

            # Validate types in array items
            for field, expected_type in array_contract.get('field_types', {}).items():
                if field in item:
                    actual_type = type(item[field]).__name__
                    if actual_type != expected_type and expected_type.lower() != actual_type.lower():
                        result['mismatches'].append(
                            f"❌ Type mismatch in {array_field}[].{field}: "
                            f"expected {expected_type}, got {actual_type}"
                        )

    def _find_similar_fields(self, target: str, available: List[str]) -> List[str]:
        """Find similar field names using simple string matching"""
        suggestions = []
        target_lower = target.lower()

        for field in available:
            field_lower = field.lower()

            # Exact match after lowercasing
            if target_lower == field_lower:
                suggestions.append(field)
            # Contains target
            elif target_lower in field_lower or field_lower in target_lower:
                suggestions.append(field)
            # Similar with underscores
            elif target_lower.replace('_', '') == field_lower.replace('_', ''):
                suggestions.append(field)

        return suggestions[:3]  # Return top 3 suggestions

    def _truncate_sample(self, data: Any, max_length: int = 500) -> Any:
        """Truncate sample data for readability"""
        json_str = json.dumps(data, indent=2)
        if len(json_str) > max_length:
            return json_str[:max_length] + "\n... (truncated)"
        return data

    def validate_specific_endpoint(self, endpoint: str,
                                   params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate a specific endpoint with custom parameters

        Args:
            endpoint: API endpoint to test
            params: Optional query parameters

        Returns:
            Validation result
        """
        if endpoint not in self.contracts:
            return {
                'status': 'error',
                'message': f"No contract defined for {endpoint}"
            }

        contract = self.contracts[endpoint]

        # Override test params if provided
        if params:
            original_method = self._build_test_params
            self._build_test_params = lambda c: params

        result = self._test_endpoint(endpoint, contract)

        if params:
            self._build_test_params = original_method

        return result

    def generate_report(self, results: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Generate HTML report of validation results

        Args:
            results: Validation results from validate_all_endpoints()
            output_path: Optional path to save HTML report

        Returns:
            HTML report as string
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>API Contract Validation Report</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 40px; }}
        .pass {{ color: #22c55e; }}
        .fail {{ color: #ef4444; }}
        .warning {{ color: #f59e0b; }}
        .endpoint {{ margin: 20px 0; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px; }}
        .mismatch {{ background: #fef2f2; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        pre {{ background: #f3f4f6; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>API Contract Validation Report</h1>
    <p>Generated: {results['timestamp']}</p>
    <p>Mode: {results['validation_mode']}</p>

    <h2>Summary</h2>
    <ul>
        <li class="pass">✅ Passed: {len(results['passed'])}</li>
        <li class="fail">❌ Failed: {len(results['failed'])}</li>
        <li class="warning">⚠️  Warnings: {len(results['warnings'])}</li>
    </ul>
"""

        # Failed endpoints
        if results['failed']:
            html += "<h2>Failed Validations</h2>"
            for failure in results['failed']:
                html += f"""
                <div class="endpoint">
                    <h3 class="fail">❌ {failure['endpoint']}</h3>
                    <p><strong>Issues Found:</strong></p>
"""
                for mismatch in failure['mismatches']:
                    html += f'<div class="mismatch">{mismatch}</div>'

                if failure['response_sample']:
                    html += f"<p><strong>Response Sample:</strong></p>"
                    html += f"<pre>{json.dumps(failure['response_sample'], indent=2)}</pre>"

                html += "</div>"

        # Passed endpoints
        if results['passed']:
            html += "<h2>Passed Validations</h2>"
            for passed in results['passed']:
                html += f'<div class="endpoint"><h3 class="pass">✅ {passed["endpoint"]}</h3></div>'

        html += "</body></html>"

        if output_path:
            Path(output_path).write_text(html)
            print(f"📄 Report saved to: {output_path}")

        return html


def main():
    """Command-line interface for contract validation"""
    validator = APIContractValidator()

    if len(sys.argv) > 1:
        endpoint = sys.argv[1]
        result = validator.validate_specific_endpoint(endpoint)
        print(json.dumps(result, indent=2))
    else:
        results = validator.validate_all_endpoints()

        # Generate report
        report_path = Path(__file__).parent.parent / "validation_report.html"
        validator.generate_report(results, str(report_path))

        # Exit with error code if any failures
        sys.exit(1 if results['failed'] else 0)


if __name__ == "__main__":
    main()
