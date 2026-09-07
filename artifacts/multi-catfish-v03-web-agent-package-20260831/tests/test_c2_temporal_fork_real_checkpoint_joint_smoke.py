from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_c2_v03_real_checkpoint_joint_smoke as smoke  # noqa: E402


def test_entrypoint_without_execute_is_plan_only(tmp_path, monkeypatch, capsys):
    """The bounded real-checkpoint path must remain explicit opt-in."""

    def forbidden(*_args, **_kwargs):
        raise AssertionError("plan-only entrypoint must not execute the smoke")

    monkeypatch.setattr(smoke, "run_real_checkpoint_joint_smoke", forbidden)
    output = tmp_path / "receipt.json"
    assert smoke.main(["--output", str(output)]) == 0
    assert not output.exists()
    plan = __import__("json").loads(capsys.readouterr().out)
    assert plan["status"] == "NOT_RUN"
    assert plan["heavy_training"] is False
    assert plan["would_require"] == "K>=2 complete candidate support"


def test_replay_lineage_digest_is_deterministic_and_binds_action():
    row = {
        "state": np.asarray([1.0, 2.0], dtype=np.float32),
        "action": 7,
        "reward": np.asarray([0.1, 0.2, 0.3], dtype=np.float32),
        "next_state": np.asarray([3.0, 4.0], dtype=np.float32),
        "mask": np.asarray([True, False, True]),
        "next_mask": np.asarray([False, True, True]),
        "done": False,
    }

    def digest_for(action: int) -> str:
        digest = hashlib.sha256()
        smoke._hash_replay_row(digest, **{**row, "action": action})
        return digest.hexdigest()

    assert digest_for(row["action"]) == digest_for(row["action"])
    assert digest_for(row["action"]) != digest_for(row["action"] + 1)


def test_prefill_fails_closed_if_checkpoint_replay_is_not_empty():
    class Replay:
        def __len__(self):
            return 1

    trainer = type("Trainer", (), {"replay": Replay()})()
    try:
        smoke._prefill_main_replay(
            trainer,
            environment=None,
            seed=1,
            target_rows=128,
            checkpoint_episode=8999,
        )
    except smoke.SmokeGateError as error:
        assert "unexpectedly contains Main replay rows" in str(error)
    else:  # pragma: no cover - assertion documents the gate
        raise AssertionError("non-empty checkpoint replay must be rejected")
