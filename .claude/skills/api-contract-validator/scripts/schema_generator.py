#!/usr/bin/env python3
"""
Schema Generator - Auto-generates API contracts from live API responses
Creates schema definitions from actual API responses
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class SchemaGenerator:
    """Generates API schemas from live responses"""

    def __init__(self, backend_url: str = "http://localhost:5001"):
        """
        Initialize schema generator

        Args:
            backend_url: Base URL for API calls
        """
        self.backend_url = backend_url
        self.schemas = {}

    def generate_from_api(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate schema from actual API response

        Args:
            endpoint: API endpoint to test
            params: Optional query parameters

        Returns:
            Generated schema definition
        """
        print(f"Generating schema for {endpoint}...")

        try:
            url = f"{self.backend_url}{endpoint}"
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return {
                    'error': f"HTTP {response.status_code}",
                    'message': response.text[:200]
                }

            data = response.json()
            schema = self._analyze_response(data, endpoint, params)

            self.schemas[endpoint] = schema
            return schema

        except requests.exceptions.RequestException as e:
            return {'error': f"Request failed: {str(e)}"}
        except json.JSONDecodeError as e:
            return {'error': f"Invalid JSON: {str(e)}"}
        except Exception as e:
            return {'error': f"Unexpected error: {str(e)}"}

    def _analyze_response(self, data: Any, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze response structure and generate schema

        Args:
            data: Response data
            endpoint: API endpoint
            params: Query parameters used

        Returns:
            Schema definition
        """
        schema = {
            'description': f'Schema for {endpoint}',
            'required_params': list(params.keys()) if params else [],
            'required_fields': [],
            'field_types': {},
            'nested_arrays': {},
            'generated_at': datetime.now().isoformat()
        }

        if isinstance(data, dict):
            # Analyze top-level fields
            for field, value in data.items():
                schema['required_fields'].append(field)
                schema['field_types'][field] = self._infer_type(value)

                # Check for nested arrays
                if isinstance(value, list) and len(value) > 0:
                    item = value[0]
                    if isinstance(item, dict):
                        array_schema = {
                            'required_fields': list(item.keys()),
                            'field_types': {}
                        }
                        for item_field, item_value in item.items():
                            array_schema['field_types'][item_field] = self._infer_type(item_value)

                        schema['nested_arrays'][field] = array_schema

        return schema

    def _infer_type(self, value: Any) -> str:
        """
        Infer type from value

        Args:
            value: Python value

        Returns:
            Type name as string
        """
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            return 'str'
        elif isinstance(value, list):
            return 'list'
        elif isinstance(value, dict):
            return 'dict'
        else:
            return 'object'

    def save_contract(self, schema: Dict[str, Any], endpoint: str, output_path: Optional[str] = None) -> str:
        """
        Save generated schema to contracts file

        Args:
            schema: Generated schema
            endpoint: API endpoint
            output_path: Optional custom output path

        Returns:
            Path where contract was saved
        """
        if output_path is None:
            output_path = Path(__file__).parent.parent / "resources" / "api_contracts.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing contracts
        if output_path.exists():
            with open(output_path, 'r') as f:
                contracts = json.load(f)
        else:
            contracts = {}

        # Update with new schema
        contracts[endpoint] = schema

        # Save
        with open(output_path, 'w') as f:
            json.dump(contracts, f, indent=2)

        print(f"💾 Contract saved: {endpoint} -> {output_path}")
        return str(output_path)

    def generate_all_endpoints(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate schemas for multiple endpoints

        Args:
            endpoints: List of endpoint definitions with optional params
                Example: [
                    {'endpoint': '/api/edges', 'params': {'week': 7}},
                    {'endpoint': '/api/current-week', 'params': {}}
                ]

        Returns:
            Dictionary of generated schemas
        """
        print(f"\n{'='*60}")
        print("🔄 Generating schemas for all endpoints")
        print(f"{'='*60}\n")

        results = {}

        for endpoint_def in endpoints:
            endpoint = endpoint_def.get('endpoint')
            params = endpoint_def.get('params')

            schema = self.generate_from_api(endpoint, params)
            results[endpoint] = schema

        print(f"\n✅ Generated {len(results)} schemas\n")

        return results


def main():
    """Command-line interface"""
    import sys

    generator = SchemaGenerator()

    # Default endpoints to scan
    endpoints_to_scan = [
        {'endpoint': '/api/current-week', 'params': {}},
        {'endpoint': '/api/edges', 'params': {'week': 7}},
        {'endpoint': '/api/edges/counts', 'params': {'week': 7}},
        {'endpoint': '/api/week-range', 'params': {}},
        {'endpoint': '/api/weak-defenses', 'params': {'week': 7}},
        {'endpoint': '/api/stats/summary', 'params': {}},
        {'endpoint': '/api/data-status', 'params': {}}
    ]

    if len(sys.argv) > 1:
        # Generate schema for specific endpoint
        endpoint = sys.argv[1]
        schema = generator.generate_from_api(endpoint)
        print(json.dumps(schema, indent=2))

        if '--save' in sys.argv:
            generator.save_contract(schema, endpoint)
    else:
        # Generate all schemas
        results = generator.generate_all_endpoints(endpoints_to_scan)

        # Save all
        contracts_path = Path(__file__).parent.parent / "resources" / "api_contracts.json"
        contracts_path.parent.mkdir(parents=True, exist_ok=True)

        with open(contracts_path, 'w') as f:
            json.dump(generator.schemas, f, indent=2)

        print(f"💾 All contracts saved to: {contracts_path}")


if __name__ == "__main__":
    main()
