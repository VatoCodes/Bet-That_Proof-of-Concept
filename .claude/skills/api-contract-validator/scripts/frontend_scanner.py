#!/usr/bin/env python3
"""
Frontend Scanner - Finds all API calls in templates/JavaScript
Helps identify what fields frontend expects from API
"""

import re
from pathlib import Path
from typing import List, Dict, Any


class FrontendScanner:
    """Scans frontend files for API usage"""

    def __init__(self, frontend_paths: List[str] = None):
        """
        Initialize scanner

        Args:
            frontend_paths: Glob patterns for frontend files to scan
        """
        if frontend_paths is None:
            base_path = Path(__file__).parent.parent.parent.parent / "dashboard"
            frontend_paths = [
                str(base_path / "templates" / "*.html"),
                str(base_path / "static" / "js" / "*.js")
            ]

        self.frontend_paths = frontend_paths
        self.api_calls = []

    def scan_templates(self) -> List[Dict[str, Any]]:
        """
        Scan all frontend files for API calls

        Returns:
            List of API call information dictionaries
        """
        print(f"\n{'='*60}")
        print("🔍 Scanning Frontend for API Calls")
        print(f"{'='*60}\n")

        self.api_calls = []

        for pattern in self.frontend_paths:
            pattern_path = Path(pattern)
            parent_dir = pattern_path.parent

            if not parent_dir.exists():
                print(f"⚠️  Directory not found: {parent_dir}")
                continue

            for file_path in parent_dir.glob(pattern_path.name):
                if file_path.is_file() and file_path.suffix in ['.html', '.js']:
                    self._scan_file(file_path)

        print(f"\n✅ Found {len(self.api_calls)} API calls\n")

        return self.api_calls

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single file for API calls"""
        print(f"Scanning: {file_path.name}")

        try:
            content = file_path.read_text()
        except Exception as e:
            print(f"  ⚠️  Error reading {file_path}: {e}")
            return

        # Find fetch() calls
        fetch_pattern = r'fetch\s*\(\s*[`"\']([^`"\']+)[`"\']'
        for match in re.finditer(fetch_pattern, content):
            api_url = match.group(1)

            # Extract endpoint (remove domain if present)
            if '/api/' in api_url:
                endpoint = '/api/' + api_url.split('/api/')[1].split('?')[0].split('`')[0]

                # Find line number
                line_num = content[:match.start()].count('\n') + 1

                # Find fields accessed
                fields = self._extract_fields_accessed(content, match.start())

                self.api_calls.append({
                    'file': str(file_path),
                    'line': line_num,
                    'endpoint': endpoint,
                    'raw_call': match.group(0),
                    'fields_accessed': fields,
                    'type': 'fetch'
                })

        # Find axios calls (if used)
        axios_pattern = r'axios\.(?:get|post|put|delete)\s*\(\s*[`"\']([^`"\']+)[`"\']'
        for match in re.finditer(axios_pattern, content):
            api_url = match.group(1)

            if '/api/' in api_url:
                endpoint = '/api/' + api_url.split('/api/')[1].split('?')[0].split('`')[0]
                line_num = content[:match.start()].count('\n') + 1
                fields = self._extract_fields_accessed(content, match.start())

                self.api_calls.append({
                    'file': str(file_path),
                    'line': line_num,
                    'endpoint': endpoint,
                    'raw_call': match.group(0),
                    'fields_accessed': fields,
                    'type': 'axios'
                })

    def _extract_fields_accessed(self, content: str, start_pos: int) -> List[str]:
        """
        Extract field names accessed after API call

        Args:
            content: File content
            start_pos: Position where API call starts

        Returns:
            List of field names accessed
        """
        fields = []

        # Look at next 500 characters for field access patterns
        snippet = content[start_pos:start_pos + 500]

        # Common patterns:
        # data.field_name
        # data['field_name']
        # data["field_name"]
        # response.field_name
        # result.field_name

        patterns = [
            r'(?:data|response|result)\.(\w+)',
            r'(?:data|response|result)\[[\'"]([\w_]+)[\'"]\]'
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, snippet):
                field = match.group(1)
                if field not in ['then', 'catch', 'finally', 'json', 'text']:
                    fields.append(field)

        return list(set(fields))  # Remove duplicates

    def generate_usage_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate map of which files use which endpoints

        Returns:
            Dictionary mapping endpoints to usage locations
        """
        usage_map = {}

        for call in self.api_calls:
            endpoint = call['endpoint']
            if endpoint not in usage_map:
                usage_map[endpoint] = []

            usage_map[endpoint].append({
                'file': call['file'],
                'line': call['line'],
                'fields': call['fields_accessed']
            })

        return usage_map

    def print_usage_report(self) -> None:
        """Print a formatted usage report"""
        usage_map = self.generate_usage_map()

        print(f"\n{'='*60}")
        print("📊 API Usage Report")
        print(f"{'='*60}\n")

        for endpoint, usages in sorted(usage_map.items()):
            print(f"\n{endpoint}")
            print(f"  Used in {len(usages)} location(s):")

            for usage in usages:
                file_short = Path(usage['file']).name
                print(f"    • {file_short}:{usage['line']}")
                if usage['fields']:
                    print(f"      Fields: {', '.join(usage['fields'])}")

    def save_usage_map(self, output_path: str) -> None:
        """Save usage map to JSON file"""
        import json
        usage_map = self.generate_usage_map()
        Path(output_path).write_text(json.dumps(usage_map, indent=2))
        print(f"📄 Usage map saved to: {output_path}")


def main():
    """Command-line interface"""
    scanner = FrontendScanner()
    scanner.scan_templates()
    scanner.print_usage_report()


if __name__ == "__main__":
    main()
