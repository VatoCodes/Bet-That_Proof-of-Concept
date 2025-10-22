import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from utils.scheduled_validator import ScheduledValidator
from utils.data_validator import DataValidator
from utils.historical_storage import HistoricalStorage
from utils.db_manager import DatabaseManager


class PipelineHealthMonitor:
    def __init__(self, db_path: Optional[Path] = None, historical_root: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else Path('data/database/nfl_betting.db')
        self.historical_root = Path(historical_root) if historical_root else Path('data/historical')
        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.scheduled_validator = ScheduledValidator(db_path=self.db_path)
        self.data_validator = DataValidator(db_path=self.db_path)
        self.historical_storage = HistoricalStorage(base_dir=self.historical_root)

    async def check_freshness(self, max_age_minutes: int = 180) -> Dict[str, Any]:
        now = datetime.now()
        cutoff = now - timedelta(minutes=max_age_minutes)
        latest_files = list(self.historical_root.rglob('*.csv'))
        latest_json = list(self.historical_root.rglob('*.json'))
        newest_mtime = None
        for p in latest_files + latest_json:
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
                if newest_mtime is None or mtime > newest_mtime:
                    newest_mtime = mtime
            except Exception:
                continue
        status = 'ok' if newest_mtime and newest_mtime >= cutoff else 'warn'
        return {
            'check': 'freshness',
            'status': status,
            'latest_timestamp': newest_mtime.isoformat() if newest_mtime else None,
            'cutoff': cutoff.isoformat(),
        }

    async def check_integrity(self) -> Dict[str, Any]:
        try:
            basic = self.scheduled_validator.run_all_checks()
        except Exception as e:
            return {'check': 'integrity', 'status': 'error', 'error': str(e)}
        return {'check': 'integrity', 'status': 'ok' if basic.get('ok', False) else 'warn', 'details': basic}

    async def summarize_health(self) -> Dict[str, Any]:
        checks = [
            await self.check_freshness(),
            await self.check_integrity(),
        ]
        worst = 'ok'
        for c in checks:
            if c['status'] == 'error':
                worst = 'error'
                break
            if c['status'] == 'warn' and worst == 'ok':
                worst = 'warn'
        return {'status': worst, 'checks': checks, 'timestamp': datetime.now().isoformat()}


