from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "checkpoint_trend_evaluation", HERE / "checkpoint_trend_evaluation.py"
)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_checkpoint_schedule_is_exact_and_fail_closed():
    assert M.checkpoint_schedule(1500) == tuple(range(100, 1501, 100))
    assert M.checkpoint_schedule(3000) == tuple(range(100, 3001, 100))
    with pytest.raises(M.CheckpointTrendError, match="end on"):
        M.checkpoint_schedule(1550)


def test_aggregate_trajectory_uses_ratio_of_sums_not_mean_of_ratios():
    rows = []
    for arm in M.ALLOWED_ARMS:
        for seed, bits, energy in zip(
            M.TREND_EVALUATION_SEEDS,
            (10.0, 90.0, 10.0, 10.0, 10.0),
            (1.0, 90.0, 1.0, 1.0, 1.0),
        ):
            rows.append(
                {
                    "arm": arm,
                    "episodes_completed": 100,
                    "evaluation_seed": seed,
                    "useful_bits": bits,
                    "system_energy_j": energy,
                    "served_user_intervals": 1,
                    "total_user_intervals": 1,
                    "zero_power_intervals": 0,
                    "zero_service_intervals": 0,
                }
            )
    summary = M.aggregate_trajectory(rows)
    assert len(summary) == 5
    assert summary[0]["system_ee_bits_per_j"] == pytest.approx(130.0 / 94.0)


def test_inventory_requires_every_arm_and_every_100ep_checkpoint(
    tmp_path, monkeypatch
):
    matrix = {
        "status": "complete",
        "arms": list(M.ALLOWED_ARMS),
        "episodes": 200,
        "training": {
            "training_seed": 123,
            "checkpoint_every_episodes": 100,
        },
    }
    (tmp_path / "matrix-receipt.json").write_text(
        json.dumps(matrix), encoding="utf-8"
    )
    for arm in M.ALLOWED_ARMS:
        checkpoints = []
        for completed in (100, 200):
            path = tmp_path / arm / "checkpoints" / f"ep-{completed:06d}-main.pt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{arm}-{completed}".encode())
            checkpoints.append(
                {
                    "episodes_completed": completed,
                    "path": str(path),
                    "sha256": M.sha256_file(path),
                }
            )
        status = {
            "status": "complete",
            "arm": arm,
            "result": {"periodic_checkpoints": checkpoints},
        }
        (tmp_path / arm / "status.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

    def fake_read(path, *, map_location):
        completed = int(Path(path).stem.split("-")[1])
        return SimpleNamespace(episode=completed - 1, train_seed=123)

    monkeypatch.setattr(M, "read_checkpoint", fake_read)
    episodes, seed, inventory = M.load_checkpoint_inventory(tmp_path)
    assert episodes == 200
    assert seed == 123
    assert len(inventory) == 10

    status_path = tmp_path / "A110" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["result"]["periodic_checkpoints"].pop()
    status_path.write_text(json.dumps(status), encoding="utf-8")
    with pytest.raises(M.CheckpointTrendError, match="sequence is incomplete"):
        M.load_checkpoint_inventory(tmp_path)
