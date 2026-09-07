"""Fast synthetic checks for the non-formal fresh-model rehearsal."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest
import torch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_one_world_fresh_rehearsal_under_test",
    HERE / "rehearsal_v023_one_world_plumbing_fresh_models.py",
)
assert SPEC is not None and SPEC.loader is not None
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)


def test_export_format_round_trip_is_untrained_nonformal_and_byte_identical(tmp_path: Path):
    root = tmp_path / "MODELS-REHEARSAL-UNTRAINED"
    manifest, models, paths = R.write_fresh_untrained_exports(root)

    assert manifest["schema"] == R.EXPORT_MANIFEST_SCHEMA
    assert manifest["formal"] is False
    assert manifest["models"] == R.UNTRAINED_MODELS
    assert manifest["epoch"] == manifest["update_count"] == 0
    assert manifest["arm_order"] == list(R.ARMS)
    assert [row["arm"] for row in manifest["exports"]] == list(R.ARMS)
    assert len({row["sha256"] for row in manifest["exports"]}) == 1
    assert len({R.PLUMBING._parameter_sha256(model) for model in models.values()}) == 1

    on_disk = json.loads((root / "exports/epoch-0000.json").read_text(encoding="ascii"))
    assert on_disk["formal"] is False and on_disk["models"] == R.UNTRAINED_MODELS
    for row in on_disk["exports"]:
        checkpoint = root / row["path"]
        sidecar = checkpoint.with_suffix(checkpoint.suffix + ".sha256")
        assert checkpoint == paths[row["arm"]]
        assert sidecar.read_text(encoding="ascii") == row["sha256"] + "\n"
        assert R.file_sha256(checkpoint) == row["sha256"]
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        assert state["update_count"] == 0
        restored = type(models[row["arm"]])(R.load_model_config(), train_seed=R.TRAIN_SEED)
        assert restored.load_checkpoint_state(state) == 0
        assert R.PLUMBING._parameter_sha256(restored) == manifest["initialization_sha256"]


def test_refuses_to_overwrite_export_or_output_roots(tmp_path: Path):
    existing_export = tmp_path / "EXPORT-REHEARSAL-UNTRAINED"
    existing_export.mkdir()
    sentinel = existing_export / "sentinel"
    sentinel.write_text("keep", encoding="ascii")
    with pytest.raises(R.RehearsalError, match="already exists"):
        R.write_fresh_untrained_exports(existing_export)
    assert sentinel.read_text(encoding="ascii") == "keep"

    export_root = tmp_path / "NEW-REHEARSAL-UNTRAINED"
    existing_output = tmp_path / "OUTPUT-REHEARSAL-UNTRAINED"
    existing_output.mkdir()
    with pytest.raises(R.RehearsalError, match="output root already exists"):
        R.run_rehearsal(
            export_root=export_root,
            output_root=existing_output,
            tle_root=tmp_path,
            execute_first_decision_diagnostic=False,
        )
    assert not export_root.exists()


def test_existing_plumbing_refusal_is_reported_without_opening_a_world(tmp_path: Path):
    root = tmp_path / "PROBE-REHEARSAL-UNTRAINED"
    output = tmp_path / "RECEIPT-REHEARSAL-UNTRAINED"
    receipt = R.run_rehearsal(
        export_root=root,
        output_root=output,
        tle_root=tmp_path,
        execute_first_decision_diagnostic=False,
    )
    probe = receipt["existing_plumbing_probe"]

    assert receipt["status"] == "BLOCKED_BY_EXISTING_PLUMBING_UNTRAINED_EXPORT_CHECK"
    assert receipt["formal"] is False and receipt["test_split_opened"] is False
    assert receipt["first_decision_diagnostic"] is None
    assert probe["accepted"] is False
    assert probe["exception_type"] == "V023RealOneWorldPlumbingError"
    assert "checkpoint.update_count must be an exact integer >= 1" in probe["message"]
    assert "load_current_model_checkpoint_state" in probe["check"]
    receipt_path = output / "rehearsal-receipt.json"
    assert json.loads(receipt_path.read_text(encoding="ascii"))["status"] == receipt["status"]
    assert receipt_path.with_suffix(".json.sha256").is_file()

    # The existing package's own fixture type remains the smoke boundary for
    # environment work; the update-count refusal happens before any fixture or
    # physical TrainerEnvironment can be constructed.
    fixture_spec = importlib.util.spec_from_file_location(
        "v023_plumbing_fixture_for_rehearsal_test",
        HERE / "test_v023_real_one_world_plumbing.py",
    )
    assert fixture_spec is not None and fixture_spec.loader is not None
    fixture = importlib.util.module_from_spec(fixture_spec)
    sys.modules[fixture_spec.name] = fixture
    fixture_spec.loader.exec_module(fixture)
    assert issubclass(fixture.FakeTrainerEnvironment, R.PLUMBING._physical.TrainerEnvironment)
    world = R.PLUMBING.make_train_world(
        world_index=R.WORLD_INDEX, world_id=R.WORLD_ID, world_seed=R.WORLD_SEED
    )
    assert world.split == "TRAIN" and "TEST" not in world.world_id.upper()
