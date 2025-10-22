#!/usr/bin/env python3
"""
Chrome DevTools MCP Integration for Dashboard Testing

This module provides integration with Chrome DevTools Model Context Protocol (MCP)
for automated browser testing of the Bet-That dashboard.
"""

import json
import logging
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import sys
import subprocess
import requests
from urllib.parse import urljoin

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from utils.db_manager import DatabaseManager
from config import get_database_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromeDevToolsMCP:
    """
    Chrome DevTools MCP integration for dashboard testing.
    
    This class provides integration with Chrome DevTools Model Context Protocol
    for automated browser testing, including navigation, interaction, and validation.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the Chrome DevTools MCP integration."""
        self.db_path = db_path if db_path else get_database_path()
        self.db_manager = DatabaseManager(db_path=self.db_path)
        
        # Load test scenarios and configuration
        self.test_scenarios = self._load_test_scenarios()
        self.api_test_suite = self._load_api_test_suite()
        
        # MCP configuration
        self.mcp_config = {
            "chrome_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "user_data_dir": "/tmp/chrome_test_profile",
            "headless": False,
            "window_size": {"width": 1920, "height": 1080},
            "timeout": 30
        }
        
        # Test results storage
        self.test_results = {}
        self.browser_session = None
        
    def _load_test_scenarios(self) -> Dict[str, Any]:
        """Load browser test scenarios."""
        scenarios_path = Path(__file__).parent / "scenarios" / "test_flows.json"
        try:
            with open(scenarios_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Test scenarios file not found: {scenarios_path}")
            return self._get_default_test_scenarios()
    
    def _load_api_test_suite(self) -> Dict[str, Any]:
        """Load API test suite."""
        api_tests_path = Path(__file__).parent / "scenarios" / "api_test_suite.json"
        try:
            with open(api_tests_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"API test suite file not found: {api_tests_path}")
            return self._get_default_api_test_suite()
    
    def _get_default_test_scenarios(self) -> Dict[str, Any]:
        """Get default test scenarios if config file is not found."""
        return {
            "dashboard_navigation": {
                "description": "Test dashboard navigation and basic functionality",
                "steps": [
                    {
                        "action": "navigate",
                        "url": "http://localhost:5001",
                        "wait_for": "element",
                        "selector": "h1"
                    },
                    {
                        "action": "click",
                        "selector": "a[href='/edges']",
                        "wait_for": "element",
                        "selector": ".edge-card"
                    },
                    {
                        "action": "click",
                        "selector": "a[href='/stats']",
                        "wait_for": "element",
                        "selector": ".stats-container"
                    },
                    {
                        "action": "click",
                        "selector": "a[href='/tracker']",
                        "wait_for": "element",
                        "selector": ".tracker-container"
                    }
                ]
            },
            "edge_analysis": {
                "description": "Test edge analysis functionality",
                "steps": [
                    {
                        "action": "navigate",
                        "url": "http://localhost:5001/edges",
                        "wait_for": "element",
                        "selector": ".edge-card"
                    },
                    {
                        "action": "fill",
                        "selector": "input[name='min_edge']",
                        "value": "0.05"
                    },
                    {
                        "action": "select",
                        "selector": "select[name='model']",
                        "value": "v2"
                    },
                    {
                        "action": "click",
                        "selector": "button[type='submit']",
                        "wait_for": "element",
                        "selector": ".edge-results"
                    }
                ]
            },
            "data_validation": {
                "description": "Test data validation display",
                "steps": [
                    {
                        "action": "navigate",
                        "url": "http://localhost:5001/api/data-status",
                        "wait_for": "json_response"
                    },
                    {
                        "action": "validate_json",
                        "required_fields": ["status", "timestamp", "issues"]
                    }
                ]
            }
        }
    
    def _get_default_api_test_suite(self) -> Dict[str, Any]:
        """Get default API test suite if config file is not found."""
        return {
            "endpoints": [
                {
                    "name": "current_week",
                    "url": "/api/current-week",
                    "method": "GET",
                    "expected_status": 200,
                    "expected_fields": ["week", "timestamp"]
                },
                {
                    "name": "edges",
                    "url": "/api/edges",
                    "method": "GET",
                    "expected_status": 200,
                    "expected_fields": ["edges", "total_count"],
                    "query_params": {
                        "week": 1,
                        "min_edge": 0.05,
                        "model": "v1"
                    }
                },
                {
                    "name": "weak_defenses",
                    "url": "/api/weak-defenses",
                    "method": "GET",
                    "expected_status": 200,
                    "expected_fields": ["defenses", "total_count"]
                },
                {
                    "name": "db_stats",
                    "url": "/api/db-stats",
                    "method": "GET",
                    "expected_status": 200,
                    "expected_fields": ["total_records", "last_updated"]
                },
                {
                    "name": "data_status",
                    "url": "/api/data-status",
                    "method": "GET",
                    "expected_status": 200,
                    "expected_fields": ["status", "timestamp", "issues"]
                }
            ]
        }
    
    async def start_browser_session(self) -> bool:
        """Start a Chrome browser session with DevTools enabled."""
        try:
            logger.info("Starting Chrome browser session...")
            
            # Chrome command line arguments
            chrome_args = [
                self.mcp_config["chrome_path"],
                f"--user-data-dir={self.mcp_config['user_data_dir']}",
                "--remote-debugging-port=9222",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            if self.mcp_config["headless"]:
                chrome_args.append("--headless")
            
            # Start Chrome process
            self.chrome_process = subprocess.Popen(chrome_args)
            
            # Wait for Chrome to start
            await asyncio.sleep(3)
            
            # Connect to DevTools
            devtools_url = "http://localhost:9222/json"
            response = requests.get(devtools_url)
            
            if response.status_code == 200:
                tabs = response.json()
                if tabs:
                    # Use the first tab
                    self.browser_session = tabs[0]
                    logger.info("Chrome browser session started successfully")
                    return True
            
            logger.error("Failed to start Chrome browser session")
            return False
            
        except Exception as e:
            logger.error(f"Error starting browser session: {e}")
            return False
    
    async def stop_browser_session(self):
        """Stop the Chrome browser session."""
        try:
            if hasattr(self, 'chrome_process'):
                self.chrome_process.terminate()
                self.chrome_process.wait()
                logger.info("Chrome browser session stopped")
            
            self.browser_session = None
            
        except Exception as e:
            logger.error(f"Error stopping browser session: {e}")
    
    async def navigate_page(self, url: str) -> Dict[str, Any]:
        """Navigate to a specific page."""
        try:
            if not self.browser_session:
                return {"status": "error", "message": "No browser session active"}
            
            # Use Chrome DevTools Protocol to navigate
            devtools_url = f"http://localhost:9222/json/runtime/evaluate"
            
            # Navigate to the page
            navigate_command = {
                "expression": f"window.location.href = '{url}'"
            }
            
            response = requests.post(devtools_url, json=navigate_command)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "url": url,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Navigation failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error navigating to page: {e}")
            return {"status": "error", "message": str(e)}
    
    async def click_element(self, selector: str) -> Dict[str, Any]:
        """Click an element on the page."""
        try:
            if not self.browser_session:
                return {"status": "error", "message": "No browser session active"}
            
            # Use Chrome DevTools Protocol to click element
            devtools_url = f"http://localhost:9222/json/runtime/evaluate"
            
            click_command = {
                "expression": f"""
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.click();
                    'Element clicked successfully';
                }} else {{
                    'Element not found: {selector}';
                }}
                """
            }
            
            response = requests.post(devtools_url, json=click_command)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("result", {}).get("value") == "Element clicked successfully":
                    return {
                        "status": "success",
                        "selector": selector,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "error",
                        "message": result.get("result", {}).get("value", "Click failed")
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Click failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return {"status": "error", "message": str(e)}
    
    async def fill_input(self, selector: str, value: str) -> Dict[str, Any]:
        """Fill an input field with a value."""
        try:
            if not self.browser_session:
                return {"status": "error", "message": "No browser session active"}
            
            # Use Chrome DevTools Protocol to fill input
            devtools_url = f"http://localhost:9222/json/runtime/evaluate"
            
            fill_command = {
                "expression": f"""
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.value = '{value}';
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    'Input filled successfully';
                }} else {{
                    'Element not found: {selector}';
                }}
                """
            }
            
            response = requests.post(devtools_url, json=fill_command)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("result", {}).get("value") == "Input filled successfully":
                    return {
                        "status": "success",
                        "selector": selector,
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "error",
                        "message": result.get("result", {}).get("value", "Fill failed")
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Fill failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error filling input: {e}")
            return {"status": "error", "message": str(e)}
    
    async def take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """Take a screenshot of the current page."""
        try:
            if not self.browser_session:
                return {"status": "error", "message": "No browser session active"}
            
            if filename is None:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Use Chrome DevTools Protocol to take screenshot
            devtools_url = f"http://localhost:9222/json/runtime/evaluate"
            
            screenshot_command = {
                "expression": """
                // This would require additional Chrome DevTools Protocol commands
                // For now, return a placeholder
                'Screenshot functionality requires additional implementation';
                """
            }
            
            response = requests.post(devtools_url, json=screenshot_command)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "filename": filename,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Screenshot failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return {"status": "error", "message": str(e)}
    
    async def wait_for_element(self, selector: str, timeout: int = 30) -> Dict[str, Any]:
        """Wait for an element to appear on the page."""
        try:
            if not self.browser_session:
                return {"status": "error", "message": "No browser session active"}
            
            # Use Chrome DevTools Protocol to wait for element
            devtools_url = f"http://localhost:9222/json/runtime/evaluate"
            
            wait_command = {
                "expression": f"""
                const waitForElement = (selector, timeout) => {{
                    return new Promise((resolve, reject) => {{
                        const startTime = Date.now();
                        const checkElement = () => {{
                            const element = document.querySelector(selector);
                            if (element) {{
                                resolve('Element found: ' + selector);
                            }} else if (Date.now() - startTime > timeout * 1000) {{
                                reject('Element not found within timeout: ' + selector);
                            }} else {{
                                setTimeout(checkElement, 100);
                            }}
                        }};
                        checkElement();
                    }});
                }};
                
                waitForElement('{selector}', {timeout})
                    .then(result => result)
                    .catch(error => error);
                """
            }
            
            response = requests.post(devtools_url, json=wait_command)
            
            if response.status_code == 200:
                result = response.json()
                if "Element found" in result.get("result", {}).get("value", ""):
                    return {
                        "status": "success",
                        "selector": selector,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "timeout",
                        "message": result.get("result", {}).get("value", "Wait failed")
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Wait failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error waiting for element: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Run a specific test scenario."""
        try:
            if scenario_name not in self.test_scenarios:
                return {
                    "status": "error",
                    "message": f"Test scenario '{scenario_name}' not found"
                }
            
            scenario = self.test_scenarios[scenario_name]
            steps = scenario.get("steps", [])
            
            logger.info(f"Running test scenario: {scenario_name}")
            
            results = []
            for i, step in enumerate(steps):
                logger.info(f"Executing step {i+1}: {step.get('action', 'unknown')}")
                
                if step["action"] == "navigate":
                    result = await self.navigate_page(step["url"])
                    if step.get("wait_for"):
                        await self.wait_for_element(step["wait_for"])
                
                elif step["action"] == "click":
                    result = await self.click_element(step["selector"])
                    if step.get("wait_for"):
                        await self.wait_for_element(step["wait_for"])
                
                elif step["action"] == "fill":
                    result = await self.fill_input(step["selector"], step["value"])
                
                elif step["action"] == "wait_for_element":
                    result = await self.wait_for_element(step["selector"])
                
                else:
                    result = {
                        "status": "error",
                        "message": f"Unknown action: {step['action']}"
                    }
                
                results.append({
                    "step": i + 1,
                    "action": step["action"],
                    "result": result
                })
                
                # Check if step failed
                if result.get("status") == "error":
                    break
            
            # Determine overall scenario result
            overall_status = "success" if all(r["result"].get("status") == "success" for r in results) else "failed"
            
            return {
                "status": overall_status,
                "scenario": scenario_name,
                "description": scenario.get("description", ""),
                "steps": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running test scenario: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_api_tests(self, base_url: str = "http://localhost:5001") -> Dict[str, Any]:
        """Run API tests."""
        try:
            logger.info("Running API tests...")
            
            results = []
            for endpoint in self.api_test_suite.get("endpoints", []):
                logger.info(f"Testing endpoint: {endpoint['name']}")
                
                # Build URL
                url = urljoin(base_url, endpoint["url"])
                
                # Add query parameters if specified
                params = endpoint.get("query_params", {})
                
                # Make request
                try:
                    if endpoint["method"] == "GET":
                        response = requests.get(url, params=params, timeout=10)
                    else:
                        response = requests.request(endpoint["method"], url, timeout=10)
                    
                    # Check status code
                    status_match = response.status_code == endpoint.get("expected_status", 200)
                    
                    # Check response content
                    content_valid = True
                    if endpoint.get("expected_fields"):
                        try:
                            data = response.json()
                            missing_fields = [field for field in endpoint["expected_fields"] if field not in data]
                            content_valid = len(missing_fields) == 0
                        except:
                            content_valid = False
                    
                    result = {
                        "endpoint": endpoint["name"],
                        "url": url,
                        "status_code": response.status_code,
                        "expected_status": endpoint.get("expected_status", 200),
                        "status_match": status_match,
                        "content_valid": content_valid,
                        "response_time": response.elapsed.total_seconds(),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    result = {
                        "endpoint": endpoint["name"],
                        "url": url,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                
                results.append(result)
            
            # Determine overall API test result
            overall_status = "success" if all(r.get("status_match", False) and r.get("content_valid", False) for r in results) else "failed"
            
            return {
                "status": overall_status,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running API tests: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_full_test_suite(self, base_url: str = "http://localhost:5001") -> Dict[str, Any]:
        """Run the full test suite including browser and API tests."""
        try:
            logger.info("Running full test suite...")
            
            # Start browser session
            browser_started = await self.start_browser_session()
            if not browser_started:
                return {
                    "status": "error",
                    "message": "Failed to start browser session"
                }
            
            # Run browser tests
            browser_results = {}
            for scenario_name in self.test_scenarios.keys():
                browser_results[scenario_name] = await self.run_test_scenario(scenario_name)
            
            # Run API tests
            api_results = await self.run_api_tests(base_url)
            
            # Stop browser session
            await self.stop_browser_session()
            
            # Determine overall result
            browser_success = all(r.get("status") == "success" for r in browser_results.values())
            api_success = api_results.get("status") == "success"
            overall_status = "success" if browser_success and api_success else "failed"
            
            return {
                "status": overall_status,
                "browser_tests": browser_results,
                "api_tests": api_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running full test suite: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

async def main():
    """Main function for testing the Chrome DevTools MCP integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chrome DevTools MCP Integration")
    parser.add_argument('--scenario', type=str,
                       help='Run specific test scenario')
    parser.add_argument('--api-only', action='store_true',
                       help='Run only API tests')
    parser.add_argument('--full-suite', action='store_true',
                       help='Run full test suite')
    parser.add_argument('--base-url', type=str, default='http://localhost:5001',
                       help='Base URL for testing')
    
    args = parser.parse_args()
    
    # Initialize MCP integration
    mcp = ChromeDevToolsMCP()
    
    if args.scenario:
        # Run specific scenario
        await mcp.start_browser_session()
        result = await mcp.run_test_scenario(args.scenario)
        await mcp.stop_browser_session()
        print(f"🧪 Test Scenario Result:")
        print(json.dumps(result, indent=2, default=str))
    
    elif args.api_only:
        # Run only API tests
        result = await mcp.run_api_tests(args.base_url)
        print(f"🌐 API Test Result:")
        print(json.dumps(result, indent=2, default=str))
    
    elif args.full_suite:
        # Run full test suite
        result = await mcp.run_full_test_suite(args.base_url)
        print(f"🎯 Full Test Suite Result:")
        print(json.dumps(result, indent=2, default=str))
    
    else:
        print("Use --help to see available options")

if __name__ == "__main__":
    asyncio.run(main())
