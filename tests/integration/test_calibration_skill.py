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


async def run_ops():
    Orchestrator = load_orchestrator()
    orch = Orchestrator()
    a = await orch.execute_skill('alert_calibration_manager', 'analyze_precision', weeks_back=1)
    r = await orch.execute_skill('alert_calibration_manager', 'recommend_thresholds', weeks_back=1)
    ap = await orch.execute_skill('alert_calibration_manager', 'apply_calibration', dry_run=True)
    b = await orch.execute_skill('alert_calibration_manager', 'backtest_thresholds', weeks_back=1)
    return a, r, ap, b


def test_calibration_skill_basic_flow():
    a, r, ap, b = asyncio.get_event_loop().run_until_complete(run_ops())
    assert a.get('status') in ('success', 'no_data', 'success')
    assert r.get('status') == 'success'
    assert ap.get('status') == 'success'
    assert b.get('status') == 'success'

