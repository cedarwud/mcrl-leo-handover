"""W-108 -- target-free pre-reveal freeze for the C2-k1 bounded runner."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 import canonical_bytes


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/c3-v04/run_v06_c2_k1_bounded_learner.py"
)
SPEC = importlib.util.spec_from_file_location(
    "v06_c2_k1_bounded_runner_w108", RUNNER
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _prereg(tmp_path: Path) -> Path:
    path = tmp_path / "learner-prereg.md"
    path.write_text("synthetic target-free learner prereg\n", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _bind_single_freeze_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "FROZEN_FREEZE_ROOT", (tmp_path / "freeze").resolve())
    monkeypatch.setattr(
        runner,
        "_authenticate_simulator_extension",
        lambda **_kwargs: {
            "schema": "synthetic-simulator-extension-receipt-v1",
            "status": "SIMULATOR_BASELINE_AND_LEARNER_EXTENSION_VERIFIED",
            "baseline_sha256": "a" * 64,
            "baseline_file_sha256": "b" * 64,
            "baseline_seal_file_sha256": "c" * 64,
            "prepare_sha256": "d" * 64,
            "simulator_source_manifest_sha256": "e" * 64,
            "current_extended_manifest_sha256": "f" * 64,
            "baseline_files": 107,
            "learner_extension_sha256": {},
            "old_files_byte_identical": True,
            "only_declared_extensions_present": True,
            "source_outcome_opened": False,
            "training": False,
            "test_split_opened": False,
        },
    )


def _authority_paths(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "prepare_path": tmp_path / "prepare-live.json",
        "simulator_baseline": tmp_path / "simulator-baseline.json",
        "simulator_baseline_seal": tmp_path / "simulator-baseline-seal.json",
    }
    for label, path in paths.items():
        if not path.exists():
            path.write_text(label + "\n", encoding="ascii")
    return paths


def test_freeze_round_trip_binds_plan_code_prereg_and_update0(tmp_path: Path) -> None:
    prereg = _prereg(tmp_path)
    output = tmp_path / "freeze"

    authority = _authority_paths(tmp_path)
    payload = runner.freeze_update0(
        learner_prereg=prereg, output_dir=output, **authority
    )
    authenticated = runner.authenticate_freeze(output, learner_prereg=prereg)

    assert payload["status"] == "PRE_REVEAL_FROZEN"
    assert authenticated["payload"] == payload
    assert authenticated["plan"]["plan_sha256"] == payload["plan_sha256"]
    assert set(payload["update0_checkpoints"]) == {"q13-a", "q13-b", "q13-c"}
    assert payload["source_outcome_opened"] is False
    assert payload["training_started"] is False
    assert payload["test_split_opened"] is False


def test_freeze_is_write_once_and_checkpoint_tamper_fails_closed(
    tmp_path: Path,
) -> None:
    prereg = _prereg(tmp_path)
    output = tmp_path / "freeze"
    authority = _authority_paths(tmp_path)
    payload = runner.freeze_update0(
        learner_prereg=prereg, output_dir=output, **authority
    )

    with pytest.raises(FileExistsError, match="overwrite"):
        runner.freeze_update0(
            learner_prereg=prereg, output_dir=output, **authority
        )

    with pytest.raises(runner.BoundedLearnerRunnerError, match="single frozen path"):
        runner.freeze_update0(
            learner_prereg=prereg,
            output_dir=tmp_path / "replacement-freeze",
            **authority,
        )

    checkpoint = Path(
        payload["update0_checkpoints"]["q13-b"]["checkpoint_path"]
    )
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    with pytest.raises(runner.BoundedLearnerRunnerError, match="checkpoint"):
        runner.authenticate_freeze(output, learner_prereg=prereg)


def test_freeze_rejects_prereg_drift_and_duplicate_json_keys(tmp_path: Path) -> None:
    prereg = _prereg(tmp_path)
    output = tmp_path / "freeze"
    runner.freeze_update0(
        learner_prereg=prereg,
        output_dir=output,
        **_authority_paths(tmp_path),
    )

    prereg.write_text("changed after freeze\n", encoding="utf-8")
    with pytest.raises(runner.BoundedLearnerRunnerError, match="stale|malformed"):
        runner.authenticate_freeze(output, learner_prereg=prereg)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"a":1,"a":1}\n')
    with pytest.raises(runner.BoundedLearnerRunnerError, match="invalid JSON"):
        runner._read_canonical(duplicate)


def test_freeze_rejects_canonical_payload_tamper_even_with_valid_json(
    tmp_path: Path,
) -> None:
    prereg = _prereg(tmp_path)
    output = tmp_path / "freeze"
    runner.freeze_update0(
        learner_prereg=prereg,
        output_dir=output,
        **_authority_paths(tmp_path),
    )
    freeze_path = output / "pre-reveal-freeze.json"
    payload = json.loads(freeze_path.read_text(encoding="ascii"))
    payload["retry"] = True
    freeze_path.write_bytes(canonical_bytes(payload))

    with pytest.raises(runner.BoundedLearnerRunnerError, match="stale|malformed"):
        runner.authenticate_freeze(output, learner_prereg=prereg)


def test_freeze_rejects_relocated_prepare_or_baseline_authority(
    tmp_path: Path,
) -> None:
    prereg = _prereg(tmp_path)
    output = tmp_path / "freeze"
    authority = _authority_paths(tmp_path)
    runner.freeze_update0(
        learner_prereg=prereg,
        output_dir=output,
        **authority,
    )
    replacement = tmp_path / "replacement-prepare-live.json"
    replacement.write_text("prepare_path\n", encoding="ascii")
    with pytest.raises(runner.BoundedLearnerRunnerError, match="differs"):
        runner.authenticate_freeze(
            output,
            learner_prereg=prereg,
            prepare_path=replacement,
            simulator_baseline=authority["simulator_baseline"],
            simulator_baseline_seal=authority["simulator_baseline_seal"],
        )
