#!/usr/bin/env python3
"""
Field Mapper - Maps backend fields to frontend field expectations
Validates frontend correctly extracts backend response fields
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class FieldMapper:
    """Maps and validates field extraction from API responses"""

    def __init__(self, mapping_config_path: Optional[str] = None):
        """
        Initialize field mapper

        Args:
            mapping_config_path: Path to field mappings configuration
        """
        if mapping_config_path is None:
            mapping_config_path = Path(__file__).parent.parent.parent / \
                                  "api-contract-validator/resources/field_mappings.json"

        try:
            with open(mapping_config_path, 'r') as f:
                self.field_mappings = json.load(f)
        except FileNotFoundError:
            self.field_mappings = {}

    def validate_field_extraction(self, api_response: Dict[str, Any],
                                  expected_fields: List[str],
                                  endpoint: str) -> Dict[str, Any]:
        """
        Validate that frontend can extract expected fields from API response

        Args:
            api_response: Actual API response
            expected_fields: Fields that frontend expects to extract
            endpoint: API endpoint being tested

        Returns:
            Validation result with mismatches
        """
        result = {
            'endpoint': endpoint,
            'status': 'pass',
            'extracted_fields': [],
            'missing_fields': [],
            'type_mismatches': [],
            'suggestions': []
        }

        # Check each expected field
        for expected_field in expected_fields:
            if expected_field in api_response:
                result['extracted_fields'].append(expected_field)
            else:
                # Try to find similar field
                similar = self._find_similar_field(expected_field, api_response.keys())
                if similar:
                    result['missing_fields'].append({
                        'expected': expected_field,
                        'found': similar
                    })
                    result['suggestions'].append(
                        f"Field '{expected_field}' not found, but '{similar}' exists. "
                        f"Frontend should use '{similar}' instead."
                    )
                else:
                    result['missing_fields'].append({
                        'expected': expected_field,
                        'found': None
                    })

        # Set status based on findings
        if result['missing_fields']:
            result['status'] = 'warning'

        return result

    def _find_similar_field(self, target: str, available_fields: List[str]) -> Optional[str]:
        """
        Find similar field name using string matching

        Args:
            target: Target field name
            available_fields: Available field names to search

        Returns:
            Most similar field name or None
        """
        target_lower = target.lower()

        # Exact match after lowercasing
        for field in available_fields:
            if target_lower == field.lower():
                return field

        # Check field mappings
        if target in self.field_mappings:
            for alternate in self.field_mappings[target]:
                for field in available_fields:
                    if alternate.lower() == field.lower():
                        return field

        # Partial matches
        best_match = None
        best_score = 0

        for field in available_fields:
            field_lower = field.lower()
            # Simple scoring based on common substrings
            if target_lower in field_lower:
                score = len(target_lower)
                if score > best_score:
                    best_match = field
                    best_score = score
            elif field_lower in target_lower:
                score = len(field_lower)
                if score > best_score:
                    best_match = field
                    best_score = score

        return best_match

    def map_response_to_frontend(self, api_response: Dict[str, Any],
                                endpoint: str) -> Dict[str, Any]:
        """
        Map API response fields to frontend-expected names

        Args:
            api_response: API response data
            endpoint: API endpoint

        Returns:
            Mapped response suitable for frontend
        """
        mapped = {}

        for key, value in api_response.items():
            # Check if we have mappings for any field
            mapped[key] = value

            # Also add alternative names from mappings
            for mapped_field, alternatives in self.field_mappings.items():
                for alt in alternatives:
                    if alt.lower() == key.lower():
                        mapped[mapped_field] = value

        return mapped

    def generate_field_mapping_report(self, test_results: List[Dict[str, Any]]) -> str:
        """
        Generate report of field mapping issues

        Args:
            test_results: List of test results from multiple endpoints

        Returns:
            Formatted report
        """
        report = "📊 Field Mapping Report\n"
        report += "=" * 60 + "\n\n"

        for result in test_results:
            endpoint = result['endpoint']
            status = result['status']

            if status == 'pass':
                report += f"✅ {endpoint}\n"
                report += f"   All {len(result['extracted_fields'])} fields extracted correctly\n\n"
            else:
                report += f"⚠️  {endpoint}\n"

                if result['extracted_fields']:
                    report += f"   Extracted: {', '.join(result['extracted_fields'])}\n"

                if result['missing_fields']:
                    report += f"   Missing:\n"
                    for missing in result['missing_fields']:
                        expected = missing['expected']
                        found = missing['found']
                        if found:
                            report += f"     - {expected} (could be {found})\n"
                        else:
                            report += f"     - {expected} (NOT FOUND)\n"

                if result['suggestions']:
                    report += f"   Suggestions:\n"
                    for suggestion in result['suggestions']:
                        report += f"     • {suggestion}\n"

                report += "\n"

        return report


def main():
    """Command-line interface for field mapping"""
    mapper = FieldMapper()

    # Test with sample response
    sample_response = {
        'success': True,
        'edges': [
            {
                'matchup': 'KC vs SF',
                'strategy': 'passing',
                'line': '-4.5',
                'recommendation': 'PLAY',
                'edge_pct': 12.5,
                'confidence': 'HIGH'
            }
        ]
    }

    expected_fields = ['success', 'edges', 'count']
    result = mapper.validate_field_extraction(sample_response, expected_fields, '/api/edges')

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
