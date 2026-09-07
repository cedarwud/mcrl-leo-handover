"""W-64 -- train/validation ladder driver keeps the E1 test split closed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "ee-axis-redesign" / "run_v03_e1_validation_ladder.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_v03_e1_validation_ladder_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checkpoint(runner) -> str:
    return json.loads(
        runner.sources.CALIBRATION_RECEIPT.read_text(encoding="utf-8")
    )["checkpoint_sha256"]


def test_config_is_reconstructed_only_from_sealed_learner_contract() -> None:
    runner = _module()
    checkpoint = _checkpoint(runner)
    prereg = {
        "checkpoint_sha256": checkpoint,
        "learner": runner.sources._learner_contract(
            checkpoint_sha256=checkpoint
        ),
    }
    config = runner._config_from_prereg(prereg)
    assert config.state_dim == 228
    assert config.action_dim == 28
    assert config.hidden_layers == (100, 50, 50)
    assert config.learning_rate == pytest.approx(0.001)


def test_training_code_manifest_binds_driver_and_ladder() -> None:
    runner = _module()
    manifest = runner._training_code_manifest()
    paths = {row["path"] for row in manifest["files"]}
    assert ".scratch/ee-axis-redesign/run_v03_e1_validation_ladder.py" in paths
    assert "src/mcrl/runtime/ee_axis_e1_ladder.py" in paths
    assert len(manifest["manifest_sha256"]) == 64


def test_ladder_index_with_any_test_seed_is_rejected_before_dataset_read(
    tmp_path: Path, monkeypatch
) -> None:
    runner = _module()
    source_root = tmp_path / "source"
    data_root = source_root / "source-data"
    data_root.mkdir(parents=True)
    checkpoint = _checkpoint(runner)
    prereg = {
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": checkpoint,
        "learner": runner.sources._learner_contract(
            checkpoint_sha256=checkpoint
        ),
    }
    runner.sources._write_once_json(
        data_root / "ladder-index.json",
        {
            "schema": "multi-catfish-mcrl-v03-e1-ladder-source-index-v1",
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": checkpoint,
            "seed_split": {"2026091005": "test"},
            "datasets": {},
            "test_split_opened": False,
        },
    )
    opened: list[Path] = []
    monkeypatch.setattr(runner, "read_opening_dataset", lambda path: opened.append(Path(path)))
    monkeypatch.setattr(runner, "read_temporal_dataset", lambda path: opened.append(Path(path)))
    with pytest.raises(runner.E1ValidationLadderDriverError, match="test or wrong seeds"):
        runner._load_ladder_batches(
            source_root=source_root,
            prereg=prereg,
            config=runner._config_from_prereg(prereg),
            expected_source_receipt_sha256="a" * 64,
        )
    assert opened == []


def test_run_refuses_existing_authority_before_loading_sources(tmp_path: Path) -> None:
    runner = _module()
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError, match="overwrite"):
        runner.run(
            source_root=tmp_path / "unused",
            output_dir=output,
            device="cpu",
            expected_source_receipt_sha256="a" * 64,
        )


@pytest.mark.parametrize(
    "malicious",
    (
        "/tmp/opening-2026091001.json",
        "../../opening-2026091001.json",
    ),
)
def test_dataset_path_rejects_absolute_and_traversal(
    tmp_path: Path, malicious: str
) -> None:
    runner = _module()
    data_root = tmp_path / "source-data"
    data_root.mkdir()
    with pytest.raises(runner.E1ValidationLadderDriverError, match="path changed"):
        runner._canonical_dataset_path(
            data_root=data_root,
            raw=malicious,
            expected="opening-2026091001.json",
        )


def test_dataset_path_rejects_symlink_even_with_canonical_basename(
    tmp_path: Path,
) -> None:
    runner = _module()
    data_root = tmp_path / "source-data"
    data_root.mkdir()
    external = tmp_path / "external.json"
    external.write_text("{}\n", encoding="ascii")
    (data_root / "opening-2026091001.json").symlink_to(external)
    with pytest.raises(runner.E1ValidationLadderDriverError, match="symlink"):
        runner._canonical_dataset_path(
            data_root=data_root,
            raw="opening-2026091001.json",
            expected="opening-2026091001.json",
        )


def test_ladder_index_must_match_digest_bound_in_source_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    runner = _module()
    source_root = tmp_path / "source"
    data_root = source_root / "source-data"
    data_root.mkdir(parents=True)
    checkpoint = _checkpoint(runner)
    prereg = {
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": checkpoint,
        "learner": runner.sources._learner_contract(
            checkpoint_sha256=checkpoint
        ),
    }
    opening = {str(seed): "b" * 64 for seed in runner.sources.SOURCE_SEED_SPLIT}
    temporal = {str(seed): "c" * 64 for seed in runner.sources.SOURCE_SEED_SPLIT}
    ladder_index, _test_index = runner.sources._source_index_payloads(
        source_manifest_sha256="a" * 64,
        checkpoint_sha256=checkpoint,
        opening_sha256s=opening,
        temporal_sha256s=temporal,
    )
    runner.sources._write_once_json(data_root / "ladder-index.json", ladder_index)
    receipt_file_sha256 = runner.sources._write_once_json(
        data_root / "receipt.json",
        {
            "schema": runner.sources.SOURCE_RECEIPT_SCHEMA,
            "status": "PASS",
            "claim_ceiling": runner.sources.CLAIM_CEILING,
            "training": False,
            "held_out_ee_evaluated": False,
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": checkpoint,
            "opening_dataset_sha256s": opening,
            "temporal_dataset_sha256s": temporal,
            "opening_dataset_file_sha256s": opening,
            "temporal_dataset_file_sha256s": temporal,
            "ladder_index_file_sha256": "d" * 64,
            "test_index_file_sha256": "e" * 64,
            "ladder_generation_details_file_sha256": "f" * 64,
            "test_generation_details_file_sha256": "1" * 64,
            "coverage_by_seed": [
                {
                    "source_seed": seed,
                    "split": split,
                    "c1_rows": 1,
                    "c3_rows": 1,
                    "c2_scheduled_clusters": 15,
                    "c2_scheduled_anchors": 3,
                    "c2_complete_clusters": 10,
                    "c2_complete_anchors": 3,
                    "c2_censored_clusters": 5,
                }
                for seed, split in sorted(runner.sources.SOURCE_SEED_SPLIT.items())
            ],
            "split_receipt": {},
            "elapsed_s": 0.0,
        },
    )
    opened: list[Path] = []
    monkeypatch.setattr(runner, "read_opening_dataset", lambda path: opened.append(Path(path)))
    monkeypatch.setattr(runner, "read_temporal_dataset", lambda path: opened.append(Path(path)))
    with pytest.raises(
        runner.E1ValidationLadderDriverError, match="not authenticated"
    ):
        runner._load_ladder_batches(
            source_root=source_root,
            prereg=prereg,
            config=runner._config_from_prereg(prereg),
            expected_source_receipt_sha256=receipt_file_sha256,
        )
    assert opened == []


def test_ladder_rejects_symlinked_source_data_parent(tmp_path: Path) -> None:
    runner = _module()
    source_root = tmp_path / "source"
    external = tmp_path / "external-source-data"
    source_root.mkdir()
    external.mkdir()
    (source_root / "source-data").symlink_to(external, target_is_directory=True)
    checkpoint = _checkpoint(runner)
    prereg = {
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": checkpoint,
        "learner": runner.sources._learner_contract(
            checkpoint_sha256=checkpoint
        ),
    }
    with pytest.raises(runner.E1ValidationLadderDriverError, match="source-data"):
        runner._load_ladder_batches(
            source_root=source_root,
            prereg=prereg,
            config=runner._config_from_prereg(prereg),
            expected_source_receipt_sha256="a" * 64,
        )


def test_claim_bearing_ladder_rejects_non_cpu_device(tmp_path: Path) -> None:
    runner = _module()
    with pytest.raises(runner.E1ValidationLadderDriverError, match="CPU"):
        runner.run(
            source_root=tmp_path / "unused",
            output_dir=tmp_path / "new-output",
            device="cuda",
            expected_source_receipt_sha256="a" * 64,
        )


def test_checkpoint_receipt_binds_all_rungs_and_selected_files(
    tmp_path: Path,
) -> None:
    runner = _module()
    run_root = tmp_path / "run"
    checkpoint_root = run_root / "checkpoints"
    checkpoint_root.mkdir(parents=True)
    spec = SimpleNamespace(
        initialization_seeds=(11, 12, 13),
        update_rungs=(10, 100, 1_000, 10_000),
    )
    for seed in spec.initialization_seeds:
        for rung in spec.update_rungs:
            (checkpoint_root / f"init-{seed}-rung-{rung:06d}.pt").write_bytes(
                f"{seed}:{rung}".encode("ascii")
            )
    digests, selected = runner._checkpoint_file_receipt(
        run_root=run_root,
        spec=spec,
        selected_rung=100,
    )
    assert len(digests) == 12
    assert set(selected) == {"11", "12", "13"}
    assert all(row["path"].endswith("rung-000100.pt") for row in selected.values())


@pytest.mark.parametrize("fault", ("missing", "extra", "symlink"))
def test_checkpoint_receipt_rejects_missing_extra_or_symlink(
    tmp_path: Path, fault: str
) -> None:
    runner = _module()
    run_root = tmp_path / "run"
    checkpoint_root = run_root / "checkpoints"
    checkpoint_root.mkdir(parents=True)
    spec = SimpleNamespace(initialization_seeds=(11,), update_rungs=(10,))
    expected = checkpoint_root / "init-11-rung-000010.pt"
    if fault == "missing":
        pass
    elif fault == "extra":
        expected.write_bytes(b"checkpoint")
        (checkpoint_root / "unexpected.pt").write_bytes(b"extra")
    else:
        external = tmp_path / "external.pt"
        external.write_bytes(b"checkpoint")
        expected.symlink_to(external)
    with pytest.raises(runner.E1ValidationLadderDriverError, match="checkpoint"):
        runner._checkpoint_file_receipt(
            run_root=run_root,
            spec=spec,
            selected_rung=10,
        )
