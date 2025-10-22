#!/usr/bin/env python3
"""
Bet-That Claude Skills Integration Script

This module provides the main integration point for all Claude Skills,
orchestrating their execution and providing a unified interface.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import sys
import argparse

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_manager import DatabaseManager
from utils.edge_calculator import EdgeCalculator
from utils.query_tools import DatabaseQueryTools
from config import get_database_path, get_current_week

# Import skill modules - Original 5 implemented skills
from .claude.skills.line_movement_tracker.scripts.compare_snapshots import SnapshotComparator
from .claude.skills.line_movement_tracker.scripts.movement_analyzer import MovementAnalyzer
from .claude.skills.edge_alerter.scripts.edge_monitor import EdgeMonitor
from .claude.skills.edge_alerter.scripts.notification_system import NotificationSystem
from .claude.skills.dashboard_tester.scripts.test_orchestrator import TestOrchestrator
from .claude.skills.dashboard_tester.scripts.chrome_devtools_mcp import ChromeDevToolsMCP
from .claude.skills.bet_edge_analyzer.scripts.conversational_analyzer import ConversationalAnalyzer
from .claude.skills.data_validator.scripts.enhanced_validator import EnhancedDataValidator

# Import skill modules - API Integration Testing Skills (NEW)
from .claude.skills.api_contract_validator.scripts.contract_validator import APIContractValidator
from .claude.skills.frontend_integration_tester.scripts.api_integration_test_runner import IntegrationTestRunner

# FUTURE SKILLS: Planned but not yet implemented
# Uncomment and implement these skills when ready:
# from .claude.skills.pipeline_health_monitor.scripts.health_monitor import PipelineHealthMonitor
# from .claude.skills.alert_calibration_manager.scripts.calibration_manager import AlertCalibrationManager
# from .claude.skills.edge_explanation_service.scripts.explanation_service import EdgeExplanationService
# from .claude.skills.week_rollover_operator.scripts.rollover_operator import WeekRolloverOperator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BetThatSkillsOrchestrator:
    """
    Main orchestrator for all Bet-That Claude Skills.
    
    This class coordinates the execution of all skills, manages their interactions,
    and provides a unified interface for the Claude Skills system.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the skills orchestrator."""
        self.db_path = db_path if db_path else get_database_path()
        
        # Initialize core components
        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.query_tools = DatabaseQueryTools(db_path=self.db_path)
        self.edge_calculator = EdgeCalculator(db_path=self.db_path)
        
        # Initialize all skills (5 core implemented skills only)
        self.skills = {
            "line_movement_tracker": {
                "snapshot_comparator": SnapshotComparator(db_path=self.db_path),
                "movement_analyzer": MovementAnalyzer(db_path=self.db_path)
            },
            "edge_alerter": {
                "edge_monitor": EdgeMonitor(db_path=self.db_path),
                "notification_system": NotificationSystem(db_path=self.db_path)
            },
            "dashboard_tester": {
                "test_orchestrator": TestOrchestrator(db_path=self.db_path),
                "chrome_mcp": ChromeDevToolsMCP(db_path=self.db_path)
            },
            "bet_edge_analyzer": {
                "conversational_analyzer": ConversationalAnalyzer(db_path=self.db_path)
            },
            "data_validator": {
                "enhanced_validator": EnhancedDataValidator(db_path=self.db_path)
            },
            "api_contract_validator": {
                "contract_validator": APIContractValidator()
            },
            "frontend_integration_tester": {
                "test_runner": IntegrationTestRunner()
            }
            # FUTURE: Add these skills when implemented:
            # "pipeline_health_monitor": {...},
            # "alert_calibration_manager": {...},
            # "edge_explanation_service": {...},
            # "week_rollover_operator": {...}
        }
        
        # Skill execution history
        self.execution_history = []
        
        # Configuration
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration."""
        return {
            "skills": {
                "line_movement_tracker": {
                    "enabled": True,
                    "schedule": "every_6_hours",
                    "dependencies": ["data_validator"]
                },
                "edge_alerter": {
                    "enabled": True,
                    "schedule": "continuous",
                    "dependencies": ["bet_edge_analyzer", "line_movement_tracker"]
                },
                "dashboard_tester": {
                    "enabled": True,
                    "schedule": "daily",
                    "dependencies": ["data_validator"]
                },
                "bet_edge_analyzer": {
                    "enabled": True,
                    "schedule": "on_demand",
                    "dependencies": ["data_validator"]
                },
                "data_validator": {
                    "enabled": True,
                    "schedule": "every_2_hours",
                    "dependencies": []
                },
                "api_contract_validator": {
                    "enabled": True,
                    "schedule": "on_backend_change",
                    "dependencies": []
                },
                "frontend_integration_tester": {
                    "enabled": True,
                    "schedule": "pre_deploy",
                    "dependencies": ["api_contract_validator", "dashboard_tester"]
                }
                # FUTURE SKILLS (not yet implemented):
                # "pipeline_health_monitor": {
                #     "enabled": False,
                #     "schedule": "hourly",
                #     "dependencies": []
                # },
                # "alert_calibration_manager": {
                #     "enabled": False,
                #     "schedule": "weekly",
                #     "dependencies": []
                # },
                # "edge_explanation_service": {
                #     "enabled": False,
                #     "schedule": "on_demand",
                #     "dependencies": ["bet_edge_analyzer"]
                # },
                # "week_rollover_operator": {
                #     "enabled": False,
                #     "schedule": "weekly",
                #     "dependencies": []
                # }
            },
            "execution": {
                "max_concurrent_skills": 3,
                "timeout_seconds": 300,
                "retry_attempts": 3
            }
        }
    
    async def execute_skill(self, skill_name: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a specific skill operation.
        
        Args:
            skill_name: Name of the skill to execute
            operation: Specific operation to perform
            **kwargs: Additional parameters for the operation
            
        Returns:
            Dictionary with execution results
        """
        try:
            logger.info(f"Executing skill: {skill_name}, operation: {operation}")
            
            start_time = datetime.now()
            
            # Check if skill is enabled
            if not self.config["skills"].get(skill_name, {}).get("enabled", True):
                return {
                    "status": "skipped",
                    "message": f"Skill {skill_name} is disabled",
                    "timestamp": start_time.isoformat()
                }
            
            # Execute the skill operation
            result = await self._execute_skill_operation(skill_name, operation, **kwargs)
            
            # Record execution
            execution_record = {
                "skill_name": skill_name,
                "operation": operation,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "result": result
            }
            
            self.execution_history.append(execution_record)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing skill {skill_name}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_skill_operation(self, skill_name: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific skill operation."""
        try:
            skill = self.skills.get(skill_name)
            if not skill:
                return {
                    "status": "error",
                    "message": f"Skill {skill_name} not found"
                }
            
            # Route to appropriate skill operation
            if skill_name == "line_movement_tracker":
                return await self._execute_line_movement_tracker(operation, **kwargs)
            elif skill_name == "edge_alerter":
                return await self._execute_edge_alerter(operation, **kwargs)
            elif skill_name == "dashboard_tester":
                return await self._execute_dashboard_tester(operation, **kwargs)
            elif skill_name == "bet_edge_analyzer":
                return await self._execute_bet_edge_analyzer(operation, **kwargs)
            elif skill_name == "data_validator":
                return await self._execute_data_validator(operation, **kwargs)
            elif skill_name == "api_contract_validator":
                return await self._execute_api_contract_validator(operation, **kwargs)
            elif skill_name == "frontend_integration_tester":
                return await self._execute_frontend_integration_tester(operation, **kwargs)
            # FUTURE SKILLS: Uncomment when implemented
            # elif skill_name == "pipeline_health_monitor":
            #     return await self._execute_pipeline_health_monitor(operation, **kwargs)
            # elif skill_name == "alert_calibration_manager":
            #     return await self._execute_alert_calibration_manager(operation, **kwargs)
            # elif skill_name == "edge_explanation_service":
            #     return await self._execute_edge_explanation_service(operation, **kwargs)
            # elif skill_name == "week_rollover_operator":
            #     return await self._execute_week_rollover_operator(operation, **kwargs)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown skill: {skill_name}"
                }
                
        except Exception as e:
            logger.error(f"Error executing skill operation: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    # FUTURE SKILL METHODS: Implement when skills are ready
    # async def _execute_alert_calibration_manager(self, operation: str, **kwargs) -> Dict[str, Any]:
    #     """Execute alert calibration manager operations."""
    #     try:
    #         manager = AlertCalibrationManager(db_path=self.db_path)
    #         return await manager.execute_operation(operation, kwargs)
    #     except Exception as e:
    #         logger.error(f"Error executing alert_calibration_manager: {e}")
    #         return {"status": "error", "message": str(e)}

    # async def _execute_edge_explanation_service(self, operation: str, **kwargs) -> Dict[str, Any]:
    #     """Execute edge explanation service operations."""
    #     try:
    #         service = EdgeExplanationService(db_path=self.db_path)
    #         return await service.execute_operation(operation, kwargs)
    #     except Exception as e:
    #         logger.error(f"Error executing edge_explanation_service: {e}")
    #         return {"status": "error", "message": str(e)}

    # async def _execute_week_rollover_operator(self, operation: str, **kwargs) -> Dict[str, Any]:
    #     """Execute week rollover operator operations."""
    #     try:
    #         operator = WeekRolloverOperator(db_path=self.db_path)
    #         return await operator.execute_operation(operation, kwargs)
    #     except Exception as e:
    #         logger.error(f"Error executing week_rollover_operator: {e}")
    #         return {"status": "error", "message": str(e)}

    async def _execute_line_movement_tracker(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute line movement tracker operations."""
        try:
            if operation == "compare_snapshots":
                comparator = self.skills["line_movement_tracker"]["snapshot_comparator"]
                return await comparator.compare_snapshots(**kwargs)
            
            elif operation == "analyze_movements":
                analyzer = self.skills["line_movement_tracker"]["movement_analyzer"]
                return await analyzer.analyze_movements(**kwargs)
            
            elif operation == "detect_significant_movements":
                analyzer = self.skills["line_movement_tracker"]["movement_analyzer"]
                return await analyzer.detect_significant_movements(**kwargs)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for line_movement_tracker: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error executing line_movement_tracker: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_edge_alerter(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute edge alerter operations."""
        try:
            if operation == "monitor_edges":
                monitor = self.skills["edge_alerter"]["edge_monitor"]
                return await monitor.monitor_edges(**kwargs)
            
            elif operation == "send_alert":
                notification_system = self.skills["edge_alerter"]["notification_system"]
                return await notification_system.send_edge_alert(**kwargs)
            
            elif operation == "test_notifications":
                notification_system = self.skills["edge_alerter"]["notification_system"]
                return await notification_system.test_notifications(**kwargs)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for edge_alerter: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error executing edge_alerter: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_dashboard_tester(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute dashboard tester operations."""
        try:
            if operation == "run_browser_tests":
                test_orchestrator = self.skills["dashboard_tester"]["test_orchestrator"]
                return await test_orchestrator.run_browser_tests(**kwargs)
            
            elif operation == "run_api_tests":
                test_orchestrator = self.skills["dashboard_tester"]["test_orchestrator"]
                return await test_orchestrator.run_api_tests(**kwargs)
            
            elif operation == "run_full_test_suite":
                test_orchestrator = self.skills["dashboard_tester"]["test_orchestrator"]
                return await test_orchestrator.run_full_test_suite(**kwargs)
            
            elif operation == "chrome_mcp_test":
                chrome_mcp = self.skills["dashboard_tester"]["chrome_mcp"]
                return await chrome_mcp.run_full_test_suite(**kwargs)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for dashboard_tester: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error executing dashboard_tester: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_bet_edge_analyzer(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute bet edge analyzer operations."""
        try:
            if operation == "analyze_edge":
                analyzer = self.skills["bet_edge_analyzer"]["conversational_analyzer"]
                return await analyzer.analyze_edge_opportunity(**kwargs)
            
            elif operation == "analyze_week_edges":
                analyzer = self.skills["bet_edge_analyzer"]["conversational_analyzer"]
                return await analyzer.analyze_week_edges(**kwargs)
            
            elif operation == "get_edge_summary":
                analyzer = self.skills["bet_edge_analyzer"]["conversational_analyzer"]
                return await analyzer.get_edge_summary(**kwargs)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for bet_edge_analyzer: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error executing bet_edge_analyzer: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_data_validator(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute data validator operations."""
        try:
            if operation == "validate_all":
                validator = self.skills["data_validator"]["enhanced_validator"]
                return await validator.validate_all(**kwargs)
            
            elif operation == "get_validation_summary":
                validator = self.skills["data_validator"]["enhanced_validator"]
                return await validator.get_validation_summary(**kwargs)
            
            elif operation == "run_anomaly_detection":
                validator = self.skills["data_validator"]["enhanced_validator"]
                return await validator._run_anomaly_detection(**kwargs)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for data_validator: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Error executing data_validator: {e}")
            return {"status": "error", "message": str(e)}

    async def _execute_api_contract_validator(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute API contract validation operations."""
        try:
            validator = self.skills["api_contract_validator"]["contract_validator"]

            if operation == "validate_all_endpoints":
                return validator.validate_all_endpoints()
            elif operation == "validate_specific_endpoint":
                endpoint = kwargs.get('endpoint')
                params = kwargs.get('params')
                return validator.validate_specific_endpoint(endpoint, params)
            elif operation == "generate_report":
                results = kwargs.get('results')
                output_path = kwargs.get('output_path')
                return {"report": validator.generate_report(results, output_path)}
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for api_contract_validator: {operation}"
                }
        except Exception as e:
            logger.error(f"Error executing api_contract_validator: {e}")
            return {"status": "error", "message": str(e)}

    async def _execute_frontend_integration_tester(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute frontend integration testing operations."""
        try:
            test_runner = self.skills["frontend_integration_tester"]["test_runner"]

            if operation == "run_all_tests":
                return test_runner.run_all_tests()
            elif operation == "test_specific_page":
                url = kwargs.get('url')
                scenario = kwargs.get('scenario')
                return test_runner.test_page(url, scenario)
            elif operation == "list_scenarios":
                return {"scenarios": test_runner.list_scenarios()}
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation for frontend_integration_tester: {operation}"
                }
        except Exception as e:
            logger.error(f"Error executing frontend_integration_tester: {e}")
            return {"status": "error", "message": str(e)}

    # FUTURE: Implement _execute_pipeline_health_monitor when skill is ready
    # async def _execute_pipeline_health_monitor(self, operation: str, **kwargs) -> Dict[str, Any]:
    #     """Execute pipeline health monitor operations."""
    #     try:
    #         monitor = self.skills["pipeline_health_monitor"]["health_monitor"]
    #         if operation == "check_freshness":
    #             return await monitor.check_freshness(**kwargs)
    #         elif operation == "check_integrity":
    #             return await monitor.check_integrity(**kwargs)
    #         elif operation == "summarize_health":
    #             return await monitor.summarize_health(**kwargs)
    #         else:
    #             return {
    #                 "status": "error",
    #                 "message": f"Unknown operation for pipeline_health_monitor: {operation}"
    #             }
    #     except Exception as e:
    #         logger.error(f"Error executing pipeline_health_monitor: {e}")
    #         return {"status": "error", "message": str(e)}

    async def run_scheduled_tasks(self) -> Dict[str, Any]:
        """Run all scheduled tasks."""
        try:
            logger.info("Running scheduled tasks...")
            
            results = {}
            
            # Run data validation first (as it's a dependency for others)
            if self.config["skills"]["data_validator"]["enabled"]:
                logger.info("Running data validation...")
                results["data_validator"] = await self.execute_skill("data_validator", "validate_all")
            
            # Run line movement tracking
            if self.config["skills"]["line_movement_tracker"]["enabled"]:
                logger.info("Running line movement tracking...")
                results["line_movement_tracker"] = await self.execute_skill("line_movement_tracker", "compare_snapshots")
            
            # Run edge monitoring
            if self.config["skills"]["edge_alerter"]["enabled"]:
                logger.info("Running edge monitoring...")
                results["edge_alerter"] = await self.execute_skill("edge_alerter", "monitor_edges")
            
            # Run dashboard testing (daily)
            if self.config["skills"]["dashboard_tester"]["enabled"]:
                logger.info("Running dashboard testing...")
                results["dashboard_tester"] = await self.execute_skill("dashboard_tester", "run_api_tests")
            
            return {
                "status": "completed",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running scheduled tasks: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        try:
            # Get current week
            current_week = get_current_week()
            
            # Get database stats
            db_stats = self.query_tools.get_database_stats()
            
            # Get recent execution history
            recent_executions = self.execution_history[-10:] if self.execution_history else []
            
            # Get skill statuses
            skill_statuses = {}
            for skill_name, skill_config in self.config["skills"].items():
                skill_statuses[skill_name] = {
                    "enabled": skill_config.get("enabled", True),
                    "schedule": skill_config.get("schedule", "on_demand"),
                    "dependencies": skill_config.get("dependencies", [])
                }
            
            return {
                "system_status": "operational",
                "current_week": current_week,
                "database_stats": db_stats,
                "skill_statuses": skill_statuses,
                "recent_executions": recent_executions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history."""
        return self.execution_history[-limit:] if self.execution_history else []
    
    def clear_execution_history(self):
        """Clear execution history."""
        self.execution_history = []

async def main():
    """Main function for testing the skills orchestrator."""
    parser = argparse.ArgumentParser(description="Bet-That Claude Skills Orchestrator")
    parser.add_argument('--skill', type=str, help='Skill to execute')
    parser.add_argument('--operation', type=str, help='Operation to perform')
    parser.add_argument('--scheduled', action='store_true', help='Run scheduled tasks')
    parser.add_argument('--status', action='store_true', help='Get system status')
    parser.add_argument('--history', action='store_true', help='Show execution history')
    parser.add_argument('--clear-history', action='store_true', help='Clear execution history')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = BetThatSkillsOrchestrator()
    
    if args.scheduled:
        # Run scheduled tasks
        result = await orchestrator.run_scheduled_tasks()
        print("📅 Scheduled Tasks Result:")
        print(json.dumps(result, indent=2, default=str))
    
    elif args.status:
        # Get system status
        status = await orchestrator.get_system_status()
        print("📊 System Status:")
        print(json.dumps(status, indent=2, default=str))
    
    elif args.history:
        # Show execution history
        history = orchestrator.get_execution_history()
        print("📜 Execution History:")
        print(json.dumps(history, indent=2, default=str))
    
    elif args.clear_history:
        # Clear execution history
        orchestrator.clear_execution_history()
        print("🗑️ Execution history cleared")
    
    elif args.skill and args.operation:
        # Execute specific skill operation
        result = await orchestrator.execute_skill(args.skill, args.operation)
        print(f"🎯 Skill Execution Result:")
        print(json.dumps(result, indent=2, default=str))
    
    else:
        print("Use --help to see available options")

if __name__ == "__main__":
    asyncio.run(main())
