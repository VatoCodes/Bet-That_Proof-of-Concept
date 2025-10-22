import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from utils.db_manager import DatabaseManager
from utils.model_calibration import ModelCalibrator


class AlertCalibrationManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path('data/database/nfl_betting.db')
        self.db = DatabaseManager(db_path=self.db_path)
        self.calibrator = ModelCalibrator(db_path=self.db_path)

    async def execute_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if operation == 'analyze_precision':
                return await self._analyze_precision(params)
            if operation == 'recommend_thresholds':
                return await self._recommend_thresholds(params)
            if operation == 'apply_calibration':
                return await self._apply_calibration(params)
            if operation == 'backtest_thresholds':
                return await self._backtest_thresholds(params)
            return {"status": "error", "message": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _analyze_precision(self, params: Dict[str, Any]) -> Dict[str, Any]:
        weeks_back = int(params.get('weeks_back', 4))
        analysis = self.calibrator.analyze_model_performance(weeks_back=weeks_back)
        return {"status": "success", "data": analysis}

    async def _recommend_thresholds(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder: derive suggested thresholds from calibration metrics
        weeks_back = int(params.get('weeks_back', 6))
        precision_target = float(params.get('precision_target', 0.7))
        analysis = self.calibrator.analyze_model_performance(weeks_back=weeks_back)

        # Simple heuristic: increase edge_threshold if calibration error is high
        calibration_error = analysis.get('overall_metrics', {}).get('calibration_error', 0.1)
        suggested_edge_threshold = min(0.2, 0.08 + calibration_error * 0.5)
        suggested_confidence_threshold = 0.6 if precision_target >= 0.7 else 0.5
        min_hold_days = 0

        recommendations = {
            'edge_threshold': round(suggested_edge_threshold, 3),
            'confidence_threshold': suggested_confidence_threshold,
            'min_hold_days': min_hold_days,
            'weeks_back': weeks_back,
            'precision_target': precision_target
        }

        self._log_calibration_run(params, recommendations, applied=False, notes='recommend_only')
        return {"status": "success", "data": {"recommendations": recommendations}}

    async def _apply_calibration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        dry_run = bool(params.get('dry_run', True))
        thresholds = params.get('thresholds') or {}
        if not thresholds:
            # If none provided, compute first
            rec = await self._recommend_thresholds(params)
            thresholds = rec.get('data', {}).get('recommendations', {})

        # Here we would persist thresholds (e.g., to a settings/config table)
        # For now, just log to calibration_history respecting dry_run.
        self._log_calibration_run(params, thresholds, applied=not dry_run, notes='apply_calibration')

        return {
            "status": "success",
            "data": {
                "thresholds": thresholds,
                "applied": not dry_run
            }
        }

    async def _backtest_thresholds(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder backtest using performance analysis as proxy
        weeks_back = int(params.get('weeks_back', 4))
        analysis = self.calibrator.analyze_model_performance(weeks_back=weeks_back)
        roi = analysis.get('overall_metrics', {}).get('roi', 0)
        brier = analysis.get('overall_metrics', {}).get('brier_score', 0)
        return {
            "status": "success",
            "data": {
                "weeks_back": weeks_back,
                "roi_proxy": roi,
                "brier_score": brier
            }
        }

    def _log_calibration_run(self, params: Dict[str, Any], recommendations: Dict[str, Any], applied: bool, notes: str):
        try:
            self.db.connect()
            self.db.cursor.execute(
                """
                INSERT INTO calibration_history (params_json, recommendations_json, applied, notes)
                VALUES (?, ?, ?, ?)
                """,
                (
                    json.dumps(params),
                    json.dumps(recommendations),
                    1 if applied else 0,
                    notes
                )
            )
            self.db.conn.commit()
        finally:
            self.db.close()


