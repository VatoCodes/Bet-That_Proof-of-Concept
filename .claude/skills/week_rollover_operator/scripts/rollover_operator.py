import json
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from utils.db_manager import DatabaseManager
from utils.historical_storage import HistoricalStorage
from config import get_current_week


class WeekRolloverOperator:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path('data/database/nfl_betting.db')
        self.db = DatabaseManager(db_path=self.db_path)
        self.storage = HistoricalStorage()

    async def execute_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if operation == 'prepare_rollover':
                return await self._prepare_rollover(params)
            if operation == 'execute_rollover':
                return await self._execute_rollover(params)
            if operation == 'rollback_rollover':
                return await self._rollback_rollover(params)
            if operation == 'schedule_rollover':
                return {"status": "success", "data": {"scheduled": True}}
            return {"status": "error", "message": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _prepare_rollover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        current_week = int(params.get('current_week', get_current_week()))
        self.db.connect()
        try:
            # Basic completeness checks (row counts per table for current week)
            checks = {}
            for table in ['matchups', 'odds_spreads', 'odds_totals', 'qb_props']:
                self.db.cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE week = ?", (current_week,))
                count = self.db.cursor.fetchone()[0]
                checks[table] = count
            return {"status": "success", "data": {"week": current_week, "counts": checks}}
        finally:
            self.db.close()

    async def _execute_rollover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        dry_run = bool(params.get('dry_run', True))
        current_week = int(params.get('current_week', get_current_week()))
        target_week = int(params.get('target_week', current_week + 1))

        backup_dir = Path('data/database/backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"nfl_betting_backup_{timestamp}.db"

        # Create DB file backup
        if not dry_run:
            shutil.copy2(self.db_path, backup_path)

        # Archive historical CSVs for the week
        archive = self.storage.archive_week(current_week)

        # Log to rollover_history
        self._log_rollover_history(from_week=current_week, to_week=target_week, backup_path=str(backup_path), status='preview' if dry_run else 'executed', details={"archive": str(archive) if archive else None})

        return {"status": "success", "data": {"from_week": current_week, "to_week": target_week, "backup_path": str(backup_path), "dry_run": dry_run}}

    async def _rollback_rollover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        backup_path = params.get('backup_path')
        if not backup_path:
            return {"status": "error", "message": "backup_path is required"}
        shutil.copy2(backup_path, self.db_path)
        self._log_rollover_history(from_week=None, to_week=None, backup_path=backup_path, status='rolled_back', details={})
        return {"status": "success", "data": {"restored_from": backup_path}}

    def _log_rollover_history(self, from_week: Optional[int], to_week: Optional[int], backup_path: str, status: str, details: Dict[str, Any]):
        try:
            self.db.connect()
            self.db.cursor.execute(
                """
                INSERT INTO rollover_history (from_week, to_week, backup_path, status, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (from_week, to_week, backup_path, status, json.dumps(details))
            )
            self.db.conn.commit()
        finally:
            self.db.close()


