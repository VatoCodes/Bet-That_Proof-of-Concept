import time
from typing import Dict, Any, Optional
from pathlib import Path

from utils.db_manager import DatabaseManager


class EdgeExplanationService:
    _cache: Dict[str, Dict[str, Any]] = {}
    _ttl_seconds: int = 900  # 15 minutes

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path('data/database/nfl_betting.db')
        self.db = DatabaseManager(db_path=self.db_path)

    async def execute_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if operation == 'explain_edge':
                return await self._explain_edge(params)
            if operation == 'list_edge_factors':
                return await self._list_edge_factors(params)
            if operation == 'generate_confidence_breakdown':
                return await self._generate_confidence_breakdown(params)
            if operation == 'format_for_dashboard':
                return await self._format_for_dashboard(params)
            return {"status": "error", "message": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._cache.get(key)
        if not item:
            return None
        if time.time() - item['ts'] > self._ttl_seconds:
            self._cache.pop(key, None)
            return None
        return item['value']

    def _set_cache(self, key: str, value: Dict[str, Any]):
        self._cache[key] = {'ts': time.time(), 'value': value}

    async def _explain_edge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        edge_id = params.get('edge_id')
        style = params.get('style', 'simple')
        if not edge_id:
            return {"status": "error", "message": "edge_id is required"}

        cache_key = f"explain:{edge_id}:{style}"
        cached = self._get_cache(cache_key)
        if cached:
            return {"status": "success", "data": cached, "cached": True}

        # Placeholder: minimal deterministic explanation template
        explanation = {
            'explanation': f"Edge {edge_id} shows favorable odds versus model projection.",
            'style': style
        }

        self._set_cache(cache_key, explanation)
        return {"status": "success", "data": explanation}

    async def _list_edge_factors(self, params: Dict[str, Any]) -> Dict[str, Any]:
        edge_id = params.get('edge_id')
        if not edge_id:
            return {"status": "error", "message": "edge_id is required"}

        factors = [
            {"name": "Line movement", "weight": 0.4},
            {"name": "Book discrepancy", "weight": 0.35},
            {"name": "Defense matchup", "weight": 0.25},
        ]
        return {"status": "success", "data": {"factors": factors}}

    async def _generate_confidence_breakdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        edge_id = params.get('edge_id')
        if not edge_id:
            return {"status": "error", "message": "edge_id is required"}

        breakdown = {
            "model_agreement": 0.5,
            "market_efficiency": 0.3,
            "data_freshness": 0.2
        }
        return {"status": "success", "data": {"confidence_breakdown": breakdown}}

    async def _format_for_dashboard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        edge_id = params.get('edge_id')
        style = params.get('style', 'simple')
        if not edge_id:
            return {"status": "error", "message": "edge_id is required"}

        exp = await self._explain_edge({"edge_id": edge_id, "style": style})
        fac = await self._list_edge_factors({"edge_id": edge_id})
        conf = await self._generate_confidence_breakdown({"edge_id": edge_id})

        if exp.get('status') != 'success':
            return exp

        payload = {
            "explanation": exp['data']['explanation'],
            "factors": fac.get('data', {}).get('factors', []),
            "confidence_breakdown": conf.get('data', {}).get('confidence_breakdown', {}),
            "recommendations": [
                "Consider staking at reduced Kelly if odds tighten",
                "Monitor line movement before kickoff"
            ]
        }
        return {"status": "success", "data": payload}


