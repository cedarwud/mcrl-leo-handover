"""Local checks for the inert DROP_C3 development-evaluation entrypoint."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[3]
HERE = REPO / ".scratch" / "multi-catfish-v023-physical"
SERVER_PATH = HERE / "run_v023_dropc3_evaluation_server.py"
SYNC_PATH = HERE / "sync_launch_v023_dropc3_evaluation_server.sh"


def _load_server():
    spec = importlib.util.spec_from_file_location("mcrl_v023_dropc3_server_test", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_server_import_is_simulator_inert() -> None:
    code = """
import importlib.util
import sys
from pathlib import Path
path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('inert_v023_server', path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
loaded = sorted(name for name in ('numpy', 'torch', 'mcrl', 'mcrl.env.tle') if name in sys.modules)
print(loaded)
"""
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-c", code, str(SERVER_PATH)],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_server_plan_is_exact_drop_c3_development_slice() -> None:
    server = _load_server()
    assert len(server.WORLD_IDS) == server.EPISODES == 100
    assert server.WORLD_IDS[0] == "world-000001"
    assert server.WORLD_IDS[-1] == "world-000100"
    assert server.WORLD_SEEDS[0] == 2026090601
    assert server.WORLD_SEEDS[-1] == 2026090700

    runner = server._load_runner()
    plan = server._build_plan(runner)
    assert plan.arms == runner.DROP_C3_ONLY_ARMS
    assert plan.evaluation_contract_sha256 == runner.DEVELOPMENT_CONTRACT_SHA256
    assert len(plan.worlds) == 100
    plan.verify(checkpoint=runner.V020CheckpointBinding())


def test_server_sync_glue_is_valid_bash() -> None:
    subprocess.run(["bash", "-n", str(SYNC_PATH)], check=True)
