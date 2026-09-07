"""Focused source-only tests for the V0.18 relational-Q3 report seam.

The fixture writes authenticated source and raw prediction artifacts directly;
it never invokes the learner, simulator, source harvester, or TEST split.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve()
R2_ROOT = HERE.parents[1]
REPO = R2_ROOT.parents[2]
sys.path.insert(0, str(R2_ROOT))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(R2_ROOT.parent / "next-learner-draft"))

from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    RelationalZRC3Observation,
)
import relational_learner_runner as runner  # noqa: E402
import relational_source_harvester as harvester  # noqa: E402
from relational_learner_runner import (  # noqa: E402
    _write_result,
    _write_validation_predictions,
    load_verified_source_panel,
)
import relational_validation_report as report  # noqa: E402
import verify_relational_validation_report as verifier  # noqa: E402
from relational_source_bridge import (  # noqa: E402
    capture_anchor_source,
    write_source_closure,
)


KAPPA = 1.0
LINEAGE = 41
INIT_SEED = 31
CONTRACT = "a" * 64
CODE = "b" * 64
Q1 = "c" * 64
Q2 = "d" * 64


def _observation(world: int) -> tuple[RelationalZRC3Observation, np.ndarray]:
    rng = np.random.default_rng(world)
    rows, actions, victims = 2, 28, 2
    action_context = rng.normal(size=(rows, actions, 7))
    victim_tokens = rng.normal(size=(rows, actions, victims, 6))
    action_mask = np.ones((rows, actions), dtype=np.bool_)
    victim_mask = np.ones((rows, actions, victims), dtype=np.bool_)
    victim_mask[np.arange(rows), :, np.arange(rows)] = False
    compatible = np.zeros((rows, actions), dtype=np.bool_)
    compatible[:, 1] = True
    references = np.array([0, 2], dtype=np.int64)
    action_context[~action_mask] = 0.0
    victim_tokens[~victim_mask] = 0.0
    target = np.full((rows, actions), -1.0, dtype=np.float64)
    target[:, 3 if world < 200 else 1] = 2.0
    target[np.arange(rows), references] = 0.0
    target[~action_mask] = 0.0
    return RelationalZRC3Observation(
        action_context=action_context,
        victim_tokens=victim_tokens,
        action_mask=action_mask,
        victim_mask=victim_mask,
        positive_credit_compatible=compatible,
        reference_actions=references,
    ), target


def _write_source(root: Path, *, world: int, split: str) -> Path:
    observation, target = _observation(world)
    captured = capture_anchor_source(
        predecision_encoder=lambda observation=observation: observation,
        exact_target_provider=lambda _capture, target=target: target,
        world_seed=world,
        lineage=LINEAGE,
        split=split,
        field_root_digest="e" * 64,
        kappa_bits=KAPPA,
    )
    write_source_closure(root, captured)
    return root


def _write_init(root: Path, panel) -> Path:
    root.mkdir(parents=True)
    checkpoint = root / "checkpoint.pt"
    checkpoint.write_bytes(b"synthetic-checkpoint")
    checkpoint_sha256 = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    parameter_sha256 = "e" * 64
    predictions = []
    for closure in panel.validation:
        values = np.zeros((closure.source.rows, 28), dtype=np.float64)
        values[:, 1] = 1.0
        values[np.arange(closure.source.rows), closure.source.reference_actions] = 0.0
        predictions.append((closure, values))
    receipt = _write_validation_predictions(
        root,
        predictions,
        initialization_seed=INIT_SEED,
        lineage=LINEAGE,
        source_sha256=panel.source_sha256,
        parameter_sha256=parameter_sha256,
    )
    body = {
        "schema": runner.RUNNER_SCHEMA,
        "version": 1,
        "status": "MECHANICAL_ARTIFACT_WRITTEN",
        "initialization_seed": INIT_SEED,
        "lineage": LINEAGE,
        "config": {},
        "schedule_sha256": "f" * 64,
        "source_panel_sha256": panel.source_sha256,
        "q1_q2_digest_binding": {
            "q1_checkpoint_sha256": Q1,
            "q2_checkpoint_sha256": Q2,
            "loaded": False,
            "modified": False,
        },
        "updates": [],
        "update_count": 100,
        "checkpoint": {"path": str(checkpoint), "checkpoint_sha256": checkpoint_sha256},
        "parameter_sha256": parameter_sha256,
        "validation_prediction_digest": receipt["arrays_sha256"],
        "reloaded_parameter_sha256": parameter_sha256,
        "reloaded_validation_prediction_digest": receipt["arrays_sha256"],
        "reload_bitwise_equal": True,
        "restored_update_count": 100,
        "validation_predictions": receipt,
        "test_split_opened": False,
        "episode_training": False,
        "scientific_gate_evaluated": False,
    }
    _write_result(root, body)
    return root


def _config(source_sha256: str, *, kappa: float = KAPPA) -> report.RelationalValidationConfig:
    return report.RelationalValidationConfig(
        contract_sha256=CONTRACT,
        code_manifest_sha256=CODE,
        source_panel_sha256=source_sha256,
        train_worlds=(101, 102),
        validation_worlds=(201, 202),
        initialization_lineages=((INIT_SEED, LINEAGE),),
        q1_checkpoint_sha256_by_lineage=((LINEAGE, Q1),),
        q2_checkpoint_sha256_by_lineage=((LINEAGE, Q2),),
        kappa_bits=kappa,
        null_kinds=("zero", "action_only"),
        gate_config=None,
    )


def _frozen_gate_config() -> report.RelationalValidationConfig:
    lineages = (41, 42, 43)
    return report.RelationalValidationConfig(
        contract_sha256=CONTRACT,
        code_manifest_sha256=CODE,
        source_panel_sha256="f" * 64,
        train_worlds=(101, 102, 103, 104),
        validation_worlds=(201, 202, 203),
        initialization_lineages=((31, 41), (32, 42), (33, 43)),
        q1_checkpoint_sha256_by_lineage=tuple((lineage, Q1) for lineage in lineages),
        q2_checkpoint_sha256_by_lineage=tuple((lineage, Q2) for lineage in lineages),
        kappa_bits=KAPPA,
        null_kinds=("zero", "action_only"),
        gate_config={
            "contract_sha256": CONTRACT,
            "contract_status": report.FROZEN_STATUS,
            "min_mean_skill": 0.0,
            "min_positive_initializations": 2,
            "min_supported_change_rate": 0.5,
            "min_supported_initializations": 2,
            "required_updates": 100,
        },
    )


@pytest.fixture
def artifact(tmp_path: Path) -> dict[str, object]:
    train = [_write_source(tmp_path / f"train-{world}", world=world, split="TRAIN") for world in (101, 102)]
    validation = [_write_source(tmp_path / f"validation-{world}", world=world, split="VALIDATION") for world in (201, 202)]
    panel = load_verified_source_panel(
        train,
        validation,
        train_worlds=(101, 102),
        validation_worlds=(201, 202),
        lineages=(LINEAGE,),
    )
    init = _write_init(tmp_path / "init", panel)
    background = report.write_background_surface_package(
        tmp_path / "background",
        initialization_seed=INIT_SEED,
        lineage=LINEAGE,
        source_sha256=panel.source_sha256,
        q1_checkpoint_sha256=Q1,
        q2_checkpoint_sha256=Q2,
        arrays={
            ("VALIDATION", world, LINEAGE): (
                np.zeros((2, 28), dtype=np.float64),
                np.zeros((2, 28), dtype=np.float64),
            )
            for world in (201, 202)
        },
    )
    config = _config(panel.source_sha256)
    report_payload = report.generate_validation_report(
        panel=panel,
        config=config,
        initialization_outputs={INIT_SEED: init},
        output_dir=tmp_path / "report",
        background_outputs={INIT_SEED: background["output_dir"]},
    )
    return {
        "root": tmp_path,
        "train": train,
        "validation": validation,
        "panel": panel,
        "init": init,
        "background": Path(background["output_dir"]),
        "config": config,
        "report": tmp_path / "report",
        "payload": report_payload,
    }


def _rewrite_json(path: Path, body: dict[str, object], *, digest_field: str | None = None) -> None:
    payload = dict(body)
    if digest_field is not None:
        payload.pop(digest_field, None)
        payload[digest_field] = report.canonical_sha256(payload)
    path.write_bytes(report._canonical_bytes(payload))


def test_decision_level_metrics_and_clean_room_bitwise_replay(artifact: dict[str, object]) -> None:
    payload = artifact["payload"]
    metrics = payload["initializations"][0]["validation"]
    assert metrics["teacher_action_agreement"] == 1.0
    assert metrics["pivotal_agreement"] == 1.0
    assert metrics["validation_skill"] == (
        metrics["pivotal_agreement"] - metrics["strongest_null_pivotal_agreement"]
    )
    assert metrics["positive_support_rate"] == 1.0
    assert metrics["background_action_changes"]["supported_positive_change_count"] > 0
    verified = verifier.verify(artifact["report"], config=artifact["config"])
    assert verified["status"] == "VERIFIED"
    with np.load(artifact["report"] / report.SURFACE_NPZ_FILENAME, allow_pickle=False) as surfaces:
        raw, _metadata = runner.read_validation_predictions(artifact["init"])
        for key, value in surfaces.items():
            np.testing.assert_array_equal(value, raw[f"q_values_{int(key.split('_')[-1]):04d}"])


def test_verifier_rejects_report_tamper_and_unknown_prediction_array(artifact: dict[str, object]) -> None:
    report_path = artifact["report"] / report.REPORT_FILENAME
    body = json.loads(report_path.read_text(encoding="ascii"))
    body["claim_ceiling"] = "tampered"
    report_path.write_bytes(report._canonical_bytes(body))
    with pytest.raises(verifier.RelationalValidationVerificationError):
        verifier.verify(artifact["report"], config=artifact["config"])

    # The report is already intentionally invalid; restore it from the fixture
    # payload before exercising the raw prediction boundary.
    report_path.write_bytes(report._canonical_bytes(artifact["payload"]))
    prediction_path = Path(artifact["init"]) / runner.PREDICTION_NPZ_FILENAME
    with np.load(prediction_path, allow_pickle=False) as loaded:
        arrays = {key: np.array(value, copy=True) for key, value in loaded.items()}
    arrays["target_surface_bits"] = np.zeros((2, 28), dtype=np.float64)
    np.savez_compressed(prediction_path, **arrays)
    with pytest.raises(verifier.RelationalValidationVerificationError):
        verifier.verify(artifact["report"], config=artifact["config"])


def test_generator_fails_closed_on_wrong_split_missing_world_and_kappa(artifact: dict[str, object]) -> None:
    root = artifact["root"]
    config = artifact["config"]
    with pytest.raises(report.RelationalValidationReportError):
        report.generate_validation_report_from_paths(
            train_source_paths=artifact["validation"],
            validation_source_paths=artifact["train"],
            config=config,
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "wrong-split",
        )
    with pytest.raises(report.RelationalValidationReportError):
        report.generate_validation_report_from_paths(
            train_source_paths=artifact["train"],
            validation_source_paths=artifact["validation"][:1],
            config=config,
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "missing-world",
        )
    with pytest.raises(report.RelationalValidationReportError, match="kappa"):
        report.generate_validation_report(
            panel=artifact["panel"],
            config=replace(config, kappa_bits=2.0),
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "wrong-kappa",
        )


def test_generator_fails_closed_on_nonfinite_prediction_and_wrong_update_count(artifact: dict[str, object]) -> None:
    root = artifact["root"]
    prediction_path = Path(artifact["init"]) / runner.PREDICTION_NPZ_FILENAME
    with np.load(prediction_path, allow_pickle=False) as loaded:
        arrays = {key: np.array(value, copy=True) for key, value in loaded.items()}
    arrays["q_values_0000"][0, 1] = np.inf
    np.savez_compressed(prediction_path, **arrays)
    with pytest.raises(report.RelationalValidationReportError):
        report.generate_validation_report(
            panel=artifact["panel"],
            config=artifact["config"],
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "nonfinite",
        )

    # Rebuild the fixture's init is unnecessary: a fresh result mutation is
    # checked before the prediction bytes are read.
    result_path = Path(artifact["init"]) / "result.json"
    result = json.loads(result_path.read_text(encoding="ascii"))
    result["update_count"] = 99
    _rewrite_json(result_path, result, digest_field="result_sha256")
    with pytest.raises(report.RelationalValidationReportError, match="100 updates"):
        report.generate_validation_report(
            panel=artifact["panel"],
            config=artifact["config"],
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "wrong-updates",
        )


def test_background_package_rejects_nonfinite_missing_world_and_q1_q2_digest_mismatch(artifact: dict[str, object]) -> None:
    config = artifact["config"]
    root = artifact["root"]
    missing = report.write_background_surface_package(
        root / "background-missing",
        initialization_seed=INIT_SEED,
        lineage=LINEAGE,
        source_sha256=artifact["panel"].source_sha256,
        q1_checkpoint_sha256=Q1,
        q2_checkpoint_sha256=Q2,
        arrays={("VALIDATION", 201, LINEAGE): (np.zeros((2, 28)), np.zeros((2, 28)))},
    )
    with pytest.raises(report.RelationalValidationReportError, match="missing"):
        report.generate_validation_report(
            panel=artifact["panel"],
            config=config,
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "background-missing-report",
            background_outputs={INIT_SEED: missing["output_dir"]},
        )

    nonfinite = root / "background-nonfinite"
    background = artifact["background"]
    nonfinite.mkdir()
    for name in (report.BACKGROUND_METADATA_FILENAME, report.BACKGROUND_RECEIPT_FILENAME):
        (nonfinite / name).write_bytes((background / name).read_bytes())
    with np.load(background / report.BACKGROUND_NPZ_FILENAME, allow_pickle=False) as loaded:
        arrays = {key: np.array(value, copy=True) for key, value in loaded.items()}
    arrays["q1_0000"][0, 1] = np.nan
    np.savez_compressed(nonfinite / report.BACKGROUND_NPZ_FILENAME, **arrays)
    with pytest.raises(report.RelationalValidationReportError):
        report.generate_validation_report(
            panel=artifact["panel"],
            config=config,
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "background-nonfinite-report",
            background_outputs={INIT_SEED: nonfinite},
        )

    with pytest.raises(report.RelationalValidationReportError, match="Q1"):
        report.generate_validation_report(
            panel=artifact["panel"],
            config=replace(config, q1_checkpoint_sha256_by_lineage=((LINEAGE, "f" * 64),)),
            initialization_outputs={INIT_SEED: artifact["init"]},
            output_dir=root / "q1-mismatch",
            background_outputs={INIT_SEED: artifact["background"]},
        )


def test_harvested_q12_sidecars_round_trip_as_explicit_sum_zero_background(
    artifact: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = artifact["panel"]
    config = artifact["config"]
    harvested: dict[Path, SimpleNamespace] = {}
    expected_by_identity: dict[tuple[str, int, int], np.ndarray] = {}
    for closure in panel.validation:
        identity = closure.identity
        q12 = np.full(
            (closure.source.rows, report.ACTION_DIM),
            float(identity[1]),
            dtype=np.float64,
        )
        expected_by_identity[identity] = q12
        harvested[closure.path] = SimpleNamespace(
            source=closure.source,
            metadata={
                "contract_sha256": config.contract_sha256,
                "code_manifest_sha256": config.code_manifest_sha256,
                "q1_checkpoint_sha256": Q1,
                "q2_checkpoint_sha256": Q2,
            },
            sidecar={"background_q12": q12},
        )

    monkeypatch.setattr(
        harvester,
        "read_harvest_closure",
        lambda path: harvested[Path(path)],
    )
    outputs, manifest = report.write_background_surface_packages_from_harvests(
        panel=panel,
        config=config,
        output_root=artifact["root"] / "harvested-backgrounds",
    )
    assert manifest["representation"] == report.BACKGROUND_REPRESENTATION_SUM_ZERO
    package = report.read_background_surface_package(
        outputs[INIT_SEED],
        expected_source_sha256=panel.source_sha256,
        expected_lineage=LINEAGE,
        expected_q1_checkpoint_sha256=Q1,
        expected_q2_checkpoint_sha256=Q2,
    )
    assert package.representation == report.BACKGROUND_REPRESENTATION_SUM_ZERO
    for identity, (left, right) in package.arrays.items():
        np.testing.assert_array_equal(left, expected_by_identity[identity])
        np.testing.assert_array_equal(right, np.zeros_like(left))
        np.testing.assert_array_equal(left + right, expected_by_identity[identity])

    report.generate_validation_report(
        panel=panel,
        config=config,
        initialization_outputs={INIT_SEED: artifact["init"]},
        output_dir=artifact["root"] / "harvested-background-report",
        background_outputs=outputs,
    )
    verified = verifier.verify(
        artifact["root"] / "harvested-background-report", config=config
    )
    assert verified["status"] == "VERIFIED"


def test_sum_zero_background_rejects_nonzero_right_surface(tmp_path: Path) -> None:
    left = np.zeros((2, report.ACTION_DIM), dtype=np.float64)
    right = np.zeros_like(left)
    right[0, 0] = 1.0
    with pytest.raises(report.RelationalValidationReportError, match="exact zero"):
        report.write_background_surface_package(
            tmp_path / "bad-sum-zero",
            initialization_seed=INIT_SEED,
            lineage=LINEAGE,
            source_sha256="a" * 64,
            q1_checkpoint_sha256=Q1,
            q2_checkpoint_sha256=Q2,
            arrays={("VALIDATION", 201, LINEAGE): (left, right)},
            representation=report.BACKGROUND_REPRESENTATION_SUM_ZERO,
        )


def _gate_report(skill: float, exposure: int, supported: int) -> dict[str, object]:
    return {
        "validation_skill": skill,
        "background_changed_action_count": exposure,
        "supported_positive_change_count": supported,
        "positive_support_rate": float(supported / exposure) if exposure else 0.0,
    }


def test_frozen_gate_uses_strict_thresholds_and_additive_pooled_support() -> None:
    config = _frozen_gate_config()

    passing = [
        _gate_report(0.1, 10, 6),
        _gate_report(0.1, 10, 6),
        _gate_report(-0.1, 10, 4),
    ]
    generated = report._gate_result(config=config, reports=passing)
    independently_verified = verifier._gate(verifier._config_body(config), passing)
    assert generated == independently_verified
    assert generated["decision"] == "PASS_LEARNER_GATE"
    assert generated["pooled_supported_change_rate"] == 16 / 30

    # An unweighted mean of the per-initialization rates would pass, but the
    # binding additive-count pool must fail.
    pooled_failure = [
        _gate_report(0.1, 10, 9),
        _gate_report(0.1, 10, 9),
        _gate_report(-0.1, 100, 10),
    ]
    assert sum(item["positive_support_rate"] for item in pooled_failure) / 3 > 0.5
    assert report._gate_result(config=config, reports=pooled_failure)["decision"] == "STOP_LEARNER_GATE"

    strict_skill_failure = [
        _gate_report(0.0, 10, 6),
        _gate_report(0.0, 10, 6),
        _gate_report(0.1, 10, 6),
    ]
    assert report._gate_result(config=config, reports=strict_skill_failure)["decision"] == "STOP_LEARNER_GATE"

    strict_support_failure = [
        _gate_report(0.1, 10, 5),
        _gate_report(0.1, 10, 5),
        _gate_report(-0.1, 10, 6),
    ]
    assert report._gate_result(config=config, reports=strict_support_failure)["decision"] == "STOP_LEARNER_GATE"


def test_frozen_gate_rejects_relaxed_panel_or_threshold_contract() -> None:
    config = _frozen_gate_config()
    with pytest.raises(report.RelationalValidationReportError, match="exactly 3 VALIDATION"):
        replace(config, validation_worlds=(201, 202))
    with pytest.raises(report.RelationalValidationReportError, match="exactly 3 initializations"):
        replace(
            config,
            initialization_lineages=((31, 41), (32, 42)),
            q1_checkpoint_sha256_by_lineage=((41, Q1), (42, Q1)),
            q2_checkpoint_sha256_by_lineage=((41, Q2), (42, Q2)),
        )
    relaxed = dict(config.gate_config)
    relaxed["min_supported_change_rate"] = 0.49
    with pytest.raises(report.RelationalValidationReportError, match="frozen V0.18"):
        replace(config, gate_config=relaxed)
