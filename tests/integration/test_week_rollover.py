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


async def run_rollover():
    Orchestrator = load_orchestrator()
    orch = Orchestrator()
    prep = await orch.execute_skill('week_rollover_operator', 'prepare_rollover')
    exe = await orch.execute_skill('week_rollover_operator', 'execute_rollover', dry_run=True)
    return prep, exe


def test_week_rollover_dry_run():
    prep, exe = asyncio.get_event_loop().run_until_complete(run_rollover())
    assert prep.get('status') == 'success'
    assert exe.get('status') == 'success'
    assert exe.get('data', {}).get('dry_run') is True

