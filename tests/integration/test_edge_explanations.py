import asyncio
import importlib.util
from pathlib import Path


def load_orchestrator():
    root = Path(__file__).resolve().parents[2]
    orchestrator_path = root / '.claude' / 'skills_orchestrator.py'
    spec = importlib.util.spec_from_file_location("skills_orchestrator", orchestrator_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.BetThatSkillsOrchestrator


async def run_explain():
    Orchestrator = load_orchestrator()
    orch = Orchestrator()
    payload = await orch.execute_skill('edge_explanation_service', 'format_for_dashboard', edge_id='TEST_EDGE', style='simple')
    return payload


def test_explanation_format():
    payload = asyncio.get_event_loop().run_until_complete(run_explain())
    assert payload.get('status') == 'success'
    data = payload.get('data', {})
    assert 'explanation' in data
    assert 'factors' in data
    assert 'confidence_breakdown' in data

