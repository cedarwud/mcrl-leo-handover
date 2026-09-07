"""Producer-bound admission, lifecycle, resume, and mutation tests."""

from __future__ import annotations

from argparse import Namespace
from copy import deepcopy
import importlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import sys
from typing import Any

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROVIDER_DIR = HERE.parent / "multi-catfish-v023-c1c2-provider-factory-v3"
for directory in (HERE, PROVIDER_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import ee_axis_two_route_model as MODEL
import test_v023_c1c2_provider_factory_v3 as PRODUCER_FIXTURE
import v023_c1c2_provider_factory_v3 as FACTORY
import v023_two_route_learner_orchestrator as ORCH
import v023_two_route_source_training_runner as RUNNER


MODEL_CONFIG_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
)


@pytest.fixture(scope="module", autouse=True)
def _single_torch_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


@pytest.fixture(scope="module")
def monkeypatch_module():
    patch = pytest.MonkeyPatch()
    yield patch
    patch.undo()


@pytest.fixture(scope="module")
def authenticated_boundary(tmp_path_factory, monkeypatch_module):
    base = tmp_path_factory.mktemp("two-route-producer-boundary")
    target = PRODUCER_FIXTURE._write_artifact(base / "targets")
    learner_manifest = PRODUCER_FIXTURE._write_learner_manifest(
        base / "learner-manifest.json"
    )
    provider_config = base / "provider-config.json"
    provider_config.write_bytes(
        PRODUCER_FIXTURE._canonical(
            PRODUCER_FIXTURE._config_payload(target, learner_manifest)
        )
    )
    monkeypatch_module.setenv(FACTORY.CONFIG_PATH_ENV, str(provider_config))
    monkeypatch_module.setenv(
        FACTORY.CONFIG_SHA256_ENV, PRODUCER_FIXTURE._sha_file(provider_config)
    )
    monkeypatch_module.setenv(
        FACTORY.LEARNER_MANIFEST_PATH_ENV, str(learner_manifest)
    )
    return {
        "target": target,
        "learner_manifest": learner_manifest,
        "provider_config": provider_config,
    }


def _provider(authenticated_boundary):
    return FACTORY.make_provider()


def test_real_factory_identity_is_accepted_with_its_declared_field_set(
    authenticated_boundary,
):
    provider = _provider(authenticated_boundary)
    payload = provider.provider_identity_payload
    assert set(payload) == set(FACTORY.PROVIDER_IDENTITY_FIELDS)
    assert len(payload) == 22
    assert any(
        "c3" in record[field].lower()
        for record in payload["learner_runtime"]
        for field in ("path", "module", "loaded_from")
    )
    accepted = ORCH.authenticate_factory_v3_provider_identity(
        provider,
        expected_train_seed=FACTORY.TRAIN_SEED,
        expected_model_config_sha256=FACTORY.MODEL_CONFIG_SHA256,
    )
    assert accepted == payload

    missing = deepcopy(payload)
    missing.pop("predecessor_manifest_sha256")

    class MissingIdentityField:
        provider_identity_payload = missing
        provider_identity = (
            f"{FACTORY.FACTORY_SCHEMA}:{ORCH._canonical_sha256(missing)}"
        )

    with pytest.raises(ORCH.V023TwoRouteOrchestratorError, match="authenticated"):
        ORCH.authenticate_factory_v3_provider_identity(
            MissingIdentityField(),
            expected_train_seed=FACTORY.TRAIN_SEED,
            expected_model_config_sha256=FACTORY.MODEL_CONFIG_SHA256,
        )


@pytest.mark.parametrize("semantic_field", ["routes", "arm"])
def test_factory_identity_still_rejects_semantic_c3(
    authenticated_boundary, semantic_field,
):
    provider = _provider(authenticated_boundary)
    payload = deepcopy(provider.provider_identity_payload)
    if semantic_field == "routes":
        payload["routes"] = ["C1", "C3"]
    else:
        payload["arm_independent_target_identity"]["arm"] = "C3"
        payload["arm_independent_target_identity_sha256"] = ORCH._canonical_sha256(
            payload["arm_independent_target_identity"]
        )

    class MutatedIdentity:
        provider_identity_payload = payload
        provider_identity = (
            f"{FACTORY.FACTORY_SCHEMA}:{ORCH._canonical_sha256(payload)}"
        )

    with pytest.raises(ORCH.V023TwoRouteOrchestratorError, match="C3|boundary"):
        ORCH.authenticate_factory_v3_provider_identity(
            MutatedIdentity(),
            expected_train_seed=FACTORY.TRAIN_SEED,
            expected_model_config_sha256=FACTORY.MODEL_CONFIG_SHA256,
        )


def _runner_config(provider: object, *, budget: int = 100, formal: bool = True):
    payload = provider.provider_identity_payload
    target = payload["arm_independent_target_identity"]
    model_config = RUNNER._load_model_config(MODEL_CONFIG_PATH)
    return RUNNER.FrozenSourceTrainingConfig(
        epoch_budget=budget,
        orchestrator_config=(
            ORCH.V023TwoRouteOrchestratorConfig.formal(
                model_config=model_config,
                train_seed=RUNNER.FORMAL_TRAIN_SEED,
                model_config_sha256=RUNNER.FROZEN_MODEL_CONFIG_SHA256,
            )
            if formal
            else ORCH.V023TwoRouteOrchestratorConfig(
                model_config=model_config,
                train_seed=RUNNER.FORMAL_TRAIN_SEED,
                model_config_sha256=RUNNER.FROZEN_MODEL_CONFIG_SHA256,
                lineage="runner-REHEARSAL-NONFORMAL",
                checkpoint_cadence_updates=RUNNER.NONFORMAL_CHECKPOINT_UPDATES,
                formal_use=False,
            )
        ),
        provider_factory_spec="v023_c1c2_provider_factory_v3:make_provider",
        authority_digests=RUNNER.RunAuthorityDigests(
            payload["contract_sha256"],
            payload["learner_manifest_sha256"],
            target["manifest_sha256"],
        ),
        provider_config_sha256=payload["provider_config_sha256"],
    )


def _assert_tree_identical(left: Any, right: Any) -> None:
    assert RUNNER._tree_equal(left, right)


def _run_nonformal_then_sigkill(root: str, stop_epoch: int) -> None:
    provider = FACTORY.make_provider()
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    runner.begin_new(root)
    runner.run_to_epoch(stop_epoch)
    os.kill(os.getpid(), signal.SIGKILL)


def _artifact_bytes(
    root: Path, *, exclude_resume_receipts: bool = False
) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not (
            exclude_resume_receipts
            and path.relative_to(root).parts[:1] == ("resume-receipts",)
        )
    }


def _remove_epoch_artifacts_after_simulated_kill(
    root: Path, epoch: int, *, write_point: str
) -> str:
    """Reduce a sealed epoch/root to the prefix visible at a killed publish."""

    checkpoint = root / f"checkpoints/epoch-{epoch:04d}.runner.pt"
    receipt = root / f"checkpoint-receipts/epoch-{epoch:04d}.json"
    manifest = root / f"exports/epoch-{epoch:04d}.json"
    export_dir = root / f"exports/epoch-{epoch:04d}"
    sidecar = checkpoint.with_suffix(checkpoint.suffix + ".sha256")
    nonce = "a" * 32
    if write_point == "ledger":
        temporary = root / f".update-ledger.json.{nonce}.tmp"
        temporary.write_bytes(b"truncated-ledger")
        return temporary.relative_to(root).as_posix()
    if write_point == "canonical-receipt":
        (root / "canonical-receipt.json").unlink()
        temporary = root / f".canonical-receipt.json.{nonce}.tmp"
        temporary.write_bytes(b"truncated-receipt")
        return temporary.relative_to(root).as_posix()

    sidecar.unlink()
    if write_point in {
        "checkpoint", "checkpoint-receipt", "manifest", "export-directory"
    }:
        checkpoint.unlink()
    if write_point in {"checkpoint-receipt", "manifest", "export-directory"}:
        receipt.unlink()
    if write_point in {"manifest", "export-directory"}:
        manifest.unlink()
    if write_point == "export-directory":
        shutil.rmtree(export_dir)
        temporary = root / f"exports/.epoch-{epoch:04d}.{nonce}.tmp"
        temporary.mkdir()
        (temporary / "00-FULL2.current-ee-axis-two-route.pt").write_bytes(
            b"partial-export-directory"
        )
        return temporary.relative_to(root).as_posix()
    temporary_by_point = {
        "manifest": root / f"exports/.epoch-{epoch:04d}.json.{nonce}.tmp",
        "checkpoint-receipt": (
            root / f"checkpoint-receipts/.epoch-{epoch:04d}.json.{nonce}.tmp"
        ),
        "checkpoint": (
            root / f"checkpoints/.epoch-{epoch:04d}.runner.pt.{nonce}.tmp"
        ),
        "sidecar": (
            root
            / f"checkpoints/.epoch-{epoch:04d}.runner.pt.sha256.{nonce}.tmp"
        ),
    }
    temporary = temporary_by_point[write_point]
    temporary.write_bytes(f"truncated-{write_point}".encode("ascii"))
    assert export_dir.is_dir()
    return temporary.relative_to(root).as_posix()


def test_authenticated_real_a_to_b_boundary_and_cycle(authenticated_boundary):
    provider = _provider(authenticated_boundary)
    orchestrator = ORCH.V023TwoRouteLearnerOrchestrator(
        _runner_config(provider).orchestrator_config, provider
    )
    receipts = orchestrator.advance_many(2)
    assert tuple(receipt.route for receipt in receipts) == ("C1", "C2")
    assert orchestrator.route_update_counts == {"C1": 1, "C2": 1}
    assert tuple(orchestrator.models) == ORCH.ARMS
    for receipt in receipts:
        assert [(item.arm, item.source) for item in receipt.arm_updates] == [
            (arm, ORCH.SOURCE_ABLATION_MAP[arm][receipt.route])
            for arm in ORCH.ARMS
        ]
    sampler = provider.sampler_state()
    assert len(sampler["consumed_file_order"]) == 4
    assert all(record["members"] for record in sampler["consumed_file_order"])


def test_model_config_digest_records_seed_and_q3_are_closed(tmp_path):
    config = RUNNER._load_model_config(MODEL_CONFIG_PATH)
    model = MODEL.EEAxisTwoRouteModel(config, train_seed=RUNNER.FORMAL_TRAIN_SEED)
    state = model.checkpoint_state(
        update_count=0, route_update_counts={"C1": 0, "C2": 0}
    )
    assert state["routes"] == ["C1", "C2"]
    assert state["train_seed"] == RUNNER.FORMAL_TRAIN_SEED
    q3_mutation = deepcopy(state)
    q3_mutation["heads"]["Q3"] = deepcopy(q3_mutation["heads"]["C2"])
    with pytest.raises(MODEL.EEAxisTwoRouteError, match="Q3"):
        model.load_checkpoint_state(q3_mutation)
    adam_defaults = deepcopy(state)
    adam_defaults["optimizers"]["C1"]["state"]["param_groups"][0]["eps"] *= 2
    adam_defaults["optimizers"]["C1"]["sha256"] = MODEL._state_digest(
        adam_defaults["optimizers"]["C1"]["state"]
    )
    with pytest.raises(MODEL.EEAxisTwoRouteError, match="Adam defaults"):
        model.load_checkpoint_state(adam_defaults)

    nonfinite = deepcopy(state)
    optimizer_state = nonfinite["optimizers"]["C1"]["state"]
    parameter_id = optimizer_state["param_groups"][0]["params"][0]
    first_parameter = next(iter(nonfinite["heads"]["C1"]["state"].values()))
    optimizer_state["state"][parameter_id] = {
        "step": torch.tensor(1.0),
        "exp_avg": torch.full_like(first_parameter, float("nan")),
        "exp_avg_sq": torch.zeros_like(first_parameter),
    }
    nonfinite["optimizers"]["C1"]["sha256"] = MODEL._state_digest(
        optimizer_state
    )
    with pytest.raises(MODEL.EEAxisTwoRouteError, match="non-finite"):
        model.load_checkpoint_state(nonfinite)
    with pytest.raises(ValueError, match="train_seed"):
        MODEL.EEAxisTwoRouteModel(
            config, train_seed=RUNNER.FORMAL_TRAIN_SEED + 1
        )

    changed = tmp_path / "changed-model-config.json"
    raw = json.loads(MODEL_CONFIG_PATH.read_text(encoding="ascii"))
    raw["q1"]["beta"] = 0.2
    changed.write_text(json.dumps(raw), encoding="ascii")
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="SHA-256"):
        RUNNER._load_model_config(changed)


def test_formal_admission_rejects_nonformal_seed():
    config = RUNNER._load_model_config(MODEL_CONFIG_PATH)
    with pytest.raises(ValueError, match="formal train seed"):
        ORCH.V023TwoRouteOrchestratorConfig.formal(
            model_config=config,
            train_seed=RUNNER.FORMAL_TRAIN_SEED + 17,
            model_config_sha256=RUNNER.FROZEN_MODEL_CONFIG_SHA256,
        )
    with pytest.raises(ValueError, match="train_seed"):
        MODEL.EEAxisTwoRouteModel(
            config,
            train_seed=RUNNER.FORMAL_TRAIN_SEED + 17,
            formal=True,
        )


def test_explicit_nonformal_seed_and_budget_are_accepted_and_recorded(
    authenticated_boundary,
):
    delegate = _provider(authenticated_boundary)
    payload = deepcopy(delegate.provider_identity_payload)
    for field in (
        "predecessor_manifest_sha256",
        "prereg_sha256",
        "scientific_declaration_sha256",
        "tle_file_set_sha256",
    ):
        payload.pop(field)
    rehearsal_seed = 2026090807
    rehearsal_budget = 7
    payload["train_seed"] = rehearsal_seed
    payload["epoch_budget"] = rehearsal_budget

    class ExplicitNonformalProvider:
        provider_identity_payload = payload
        provider_identity = (
            f"{FACTORY.FACTORY_SCHEMA}:{ORCH._canonical_sha256(payload)}"
        )
        planned_epoch_budget = rehearsal_budget
        next_batch = delegate.next_batch
        sampler_state = delegate.sampler_state
        load_sampler_state = delegate.load_sampler_state

    config = ORCH.V023TwoRouteOrchestratorConfig(
        model_config=RUNNER._load_model_config(MODEL_CONFIG_PATH),
        train_seed=rehearsal_seed,
        model_config_sha256=RUNNER.FROZEN_MODEL_CONFIG_SHA256,
        lineage="explicit-REHEARSAL-NONFORMAL",
        checkpoint_cadence_updates=2,
        formal_use=False,
    )
    orchestrator = ORCH.V023TwoRouteLearnerOrchestrator(
        config, ExplicitNonformalProvider()
    )
    checkpoint = orchestrator.checkpoint_state()
    assert checkpoint["config"]["formal_use"] is False
    assert checkpoint["config"]["train_seed"] == rehearsal_seed
    assert all(state["formal"] is False for state in checkpoint["arms"].values())
    assert all(
        state["train_seed"] == rehearsal_seed
        for state in checkpoint["arms"].values()
    )


def test_unstarted_runner_consumes_nothing_and_changes_nothing(authenticated_boundary):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider), provider
    )
    before_sampler = provider.sampler_state()
    before_models = runner.orchestrator.checkpoint_state()["arms"]
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="begin_new"):
        runner.run_to_epoch(1)
    _assert_tree_identical(before_sampler, provider.sampler_state())
    _assert_tree_identical(
        before_models, runner.orchestrator.checkpoint_state()["arms"]
    )


def test_epoch_zero_export_reload_and_runner_resume_are_exact(
    authenticated_boundary, tmp_path
):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider), provider
    )
    root = tmp_path / "source-run"
    runner.begin_new(root)
    runner.run_to_epoch(1)

    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider), resumed_provider
    )
    resumed.resume_from_checkpoint(root / "checkpoints/epoch-0000.runner.pt")
    resumed.run_to_epoch(1)
    _assert_tree_identical(
        runner.orchestrator.checkpoint_state(), resumed.orchestrator.checkpoint_state()
    )


def test_checkpoint_v1_1_rejects_noncanonical_embedded_state(
    authenticated_boundary, tmp_path,
):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider), provider
    )
    root = tmp_path / "checkpoint-schema"
    runner.begin_new(root)
    checkpoint = RUNNER._read_torch(root / "checkpoints/epoch-0000.runner.pt")
    assert checkpoint["schema"] == RUNNER.CHECKPOINT_SCHEMA
    assert checkpoint["schema"].endswith("-v1.1")

    mutated = deepcopy(checkpoint)
    mutated["update_ledger_rows"] += b"\n"
    with pytest.raises(
        RUNNER.V023TwoRouteSourceTrainingRunnerError, match="non-canonical"
    ):
        runner._validate_checkpoint(mutated)


def test_epoch_100_independent_restore_exports_and_terminal_integrity(
    authenticated_boundary, tmp_path
):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider), provider
    )
    root = tmp_path / "formal-source-run"
    runner.begin_new(root)
    runner.run()
    final = json.loads((root / "canonical-receipt.json").read_text(encoding="ascii"))
    assert final["completed_updates"] == 200
    assert final["epoch_100_integrity"]["decision"] == (
        RUNNER.EPOCH_100_INTEGRITY_DECISION
    )
    assert final["epoch_100_integrity"]["restored_route_update_counts"] == {
        "C1": 100,
        "C2": 100,
    }
    checkpoint = RUNNER._read_torch(root / "checkpoints/epoch-0100.runner.pt")
    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider), resumed_provider
    )
    resumed.resume_from_checkpoint(root / "checkpoints/epoch-0100.runner.pt")
    _assert_tree_identical(
        resumed.orchestrator.checkpoint_state(),
        RUNNER.decode_checkpoint_orchestrator_state(checkpoint),
    )


def test_nonformal_resume_is_bitwise_exact_at_boundary_and_nonboundary(
    authenticated_boundary, tmp_path
):
    reference_provider = _provider(authenticated_boundary)
    reference = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(reference_provider, formal=False), reference_provider
    )
    reference.begin_new(tmp_path / "reference-REHEARSAL-NONFORMAL")
    reference.run()
    expected = reference.orchestrator.checkpoint_state()

    for stopped_epoch in (40, 43):
        root = tmp_path / f"interrupted-{stopped_epoch}-REHEARSAL-NONFORMAL"
        process = multiprocessing.get_context("fork").Process(
            target=_run_nonformal_then_sigkill,
            args=(str(root), stopped_epoch),
        )
        process.start()
        process.join(timeout=120)
        assert process.exitcode == -signal.SIGKILL

        resumed_provider = _provider(authenticated_boundary)
        resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
            _runner_config(resumed_provider, formal=False), resumed_provider
        )
        selected = resumed.resume_from_root(root)
        assert selected.name == "epoch-0040.runner.pt"
        assert resumed.completed_epochs == 40
        resumed.run()
        _assert_tree_identical(expected, resumed.orchestrator.checkpoint_state())

        checkpoint = RUNNER._read_torch(root / "checkpoints/epoch-0100.runner.pt")
        assert checkpoint["formal"] is False
        assert len(RUNNER.decode_checkpoint_ledger(checkpoint)) == 200
        assert all(
            state["formal"] is False
            for state in checkpoint["models_and_optimizers"].values()
        )


@pytest.mark.parametrize(
    "write_point",
    [
        "manifest",
        "export-directory",
        "checkpoint-receipt",
        "checkpoint",
        "sidecar",
        "canonical-receipt",
        "ledger",
    ],
)
def test_resume_ignores_each_unsealed_atomic_write_prefix_and_reproduces_final_bytes(
    authenticated_boundary, tmp_path, write_point,
):
    reference_provider = _provider(authenticated_boundary)
    reference = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(reference_provider, formal=False), reference_provider
    )
    reference_root = tmp_path / "reference-kill-REHEARSAL-NONFORMAL"
    reference.begin_new(reference_root)
    reference.run()

    provider = _provider(authenticated_boundary)
    interrupted = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    root = tmp_path / f"kill-{write_point}-REHEARSAL-NONFORMAL"
    interrupted.begin_new(root)
    interrupted.run_to_epoch(100 if write_point == "canonical-receipt" else 20)
    stale_path = _remove_epoch_artifacts_after_simulated_kill(
        root, 20, write_point=write_point
    )

    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider, formal=False), resumed_provider
    )
    selected = resumed.resume_from_root(root)
    expected_selected = {
        "canonical-receipt": "epoch-0100.runner.pt",
        "ledger": "epoch-0020.runner.pt",
    }.get(write_point, "epoch-0010.runner.pt")
    assert selected.name == expected_selected
    resume_receipt = json.loads(
        (root / "resume-receipts/resume-0001.json").read_text(encoding="ascii")
    )
    assert resume_receipt["schema"] == RUNNER.RESUME_RECEIPT_SCHEMA
    assert resume_receipt["removed_stale_temps"] == [stale_path]
    assert not (root / stale_path).exists()
    resumed.run()
    assert _artifact_bytes(
        root, exclude_resume_receipts=True
    ) == _artifact_bytes(reference_root, exclude_resume_receipts=True)


def test_check_root_reports_without_removing_stale_temps(
    authenticated_boundary, tmp_path, capsys,
):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    root = tmp_path / "check-root-REHEARSAL-NONFORMAL"
    runner.begin_new(root)
    runner.run_to_epoch(20)
    stale_path = _remove_epoch_artifacts_after_simulated_kill(
        root, 20, write_point="manifest"
    )

    before = _artifact_bytes(root)
    assert RUNNER.main(["--check-root", str(root)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == RUNNER.ROOT_CHECK_SCHEMA
    assert report["sealed_epochs"] == [0, 10]
    assert report["unsealed_prefixes"][0]["epoch"] == 20
    assert report["stale_temps"] == [
        {
            "artifact": "export-manifest",
            "epoch": 20,
            "kind": "file",
            "path": stale_path,
            "refusal_reason": None,
            "safe_to_remove": True,
        }
    ]
    assert _artifact_bytes(root) == before


def test_resume_refuses_to_touch_temp_belonging_to_sealed_epoch(
    authenticated_boundary, tmp_path,
):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    root = tmp_path / "sealed-temp-REHEARSAL-NONFORMAL"
    runner.begin_new(root)
    runner.run_to_epoch(10)
    stale = root / f"exports/.epoch-0010.json.{'b' * 32}.tmp"
    stale.write_bytes(b"must-not-delete")

    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider, formal=False), resumed_provider
    )
    with pytest.raises(
        RUNNER.V023TwoRouteSourceTrainingRunnerError, match="sealed epoch"
    ):
        resumed.resume_from_root(root)
    assert stale.read_bytes() == b"must-not-delete"
    assert not (root / "resume-receipts").exists()


def test_sealed_epoch_export_directory_is_never_replaced(
    authenticated_boundary, tmp_path,
):
    provider = _provider(authenticated_boundary)
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    root = tmp_path / "sealed-export-REHEARSAL-NONFORMAL"
    runner.begin_new(root)
    runner.run_to_epoch(10)
    before = _artifact_bytes(root / "exports/epoch-0010")

    with pytest.raises(
        RUNNER.V023TwoRouteSourceTrainingRunnerError,
        match="sealed|export directory already exists",
    ):
        runner._write_exports(root, 10)
    assert _artifact_bytes(root / "exports/epoch-0010") == before


def test_resume_ignores_pre_fix_checkpoint_and_sidecar_without_dependencies(
    authenticated_boundary, tmp_path,
):
    provider = _provider(authenticated_boundary)
    interrupted = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    root = tmp_path / "old-order-partial-REHEARSAL-NONFORMAL"
    interrupted.begin_new(root)
    interrupted.run_to_epoch(20)
    (root / "checkpoint-receipts/epoch-0020.json").unlink()
    (root / "exports/epoch-0020.json").unlink()
    shutil.rmtree(root / "exports/epoch-0020")

    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider, formal=False), resumed_provider
    )
    selected = resumed.resume_from_root(root)
    assert selected.name == "epoch-0010.runner.pt"
    resumed.run_to_epoch(20)
    assert resumed.resume_from_root(root).name == "epoch-0020.runner.pt"


def test_resumed_nonformal_checkpoints_and_receipts_are_byte_identical(
    authenticated_boundary, tmp_path,
):
    reference_provider = _provider(authenticated_boundary)
    reference = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(reference_provider, formal=False), reference_provider
    )
    reference_root = tmp_path / "reference-bytes-REHEARSAL-NONFORMAL"
    reference.begin_new(reference_root)
    reference.run()

    provider = _provider(authenticated_boundary)
    interrupted = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider, formal=False), provider
    )
    root = tmp_path / "resumed-bytes-REHEARSAL-NONFORMAL"
    interrupted.begin_new(root)
    interrupted.run_to_epoch(40)
    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider, formal=False), resumed_provider
    )
    resumed.resume_from_root(root)
    resumed.run()

    for epoch in range(50, 101, 10):
        for relative in (
            f"checkpoints/epoch-{epoch:04d}.runner.pt",
            f"checkpoints/epoch-{epoch:04d}.runner.pt.sha256",
            f"checkpoint-receipts/epoch-{epoch:04d}.json",
        ):
            assert (root / relative).read_bytes() == (reference_root / relative).read_bytes()
    assert (root / "canonical-receipt.json").read_bytes() == (
        reference_root / "canonical-receipt.json"
    ).read_bytes()


def test_resumed_formal_epoch_100_checkpoint_and_receipts_are_byte_identical(
    authenticated_boundary, tmp_path,
):
    reference_provider = _provider(authenticated_boundary)
    reference = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(reference_provider), reference_provider
    )
    reference_root = tmp_path / "reference-formal-bytes"
    reference.begin_new(reference_root)
    reference.run()

    provider = _provider(authenticated_boundary)
    interrupted = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider), provider
    )
    root = tmp_path / "resumed-formal-bytes"
    interrupted.begin_new(root)
    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider), resumed_provider
    )
    resumed.resume_from_root(root)
    resumed.run()

    for relative in (
        "checkpoints/epoch-0100.runner.pt",
        "checkpoints/epoch-0100.runner.pt.sha256",
        "checkpoint-receipts/epoch-0100.json",
        "canonical-receipt.json",
    ):
        assert (root / relative).read_bytes() == (reference_root / relative).read_bytes()


def test_formal_resume_before_epoch_100_selects_only_epoch_zero(
    authenticated_boundary, tmp_path
):
    provider = _provider(authenticated_boundary)
    interrupted = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(provider), provider
    )
    root = tmp_path / "formal-interrupted"
    interrupted.begin_new(root)
    interrupted.run_to_epoch(43)
    assert sorted(path.name for path in (root / "checkpoints").glob("*.runner.pt")) == [
        "epoch-0000.runner.pt"
    ]

    resumed_provider = _provider(authenticated_boundary)
    resumed = RUNNER.V023TwoRouteSourceTrainingRunner(
        _runner_config(resumed_provider), resumed_provider
    )
    selected = resumed.resume_from_root(root)
    assert selected.name == "epoch-0000.runner.pt"
    assert resumed.completed_epochs == 0


def test_runner_cli_resume_entry_delegates_to_validated_root_resume(
    monkeypatch, tmp_path
):
    root = tmp_path / "cli-REHEARSAL-NONFORMAL"
    root.mkdir()
    observed: dict[str, object] = {}

    class StubRunner:
        def resume_from_root(self, value):
            observed["resume"] = value

        def run(self):
            observed["run"] = True

    def fake_preflight(arguments):
        observed["nonformal"] = arguments.nonformal
        return StubRunner()

    monkeypatch.setattr(RUNNER, "preflight_from_args", fake_preflight)
    assert RUNNER.main(
        [
            "--resume", str(root), "--epochs", "100",
            "--provider-factory", "provider:factory",
            "--model-config-json", "model.json",
            "--train-seed", str(RUNNER.FORMAL_TRAIN_SEED),
            "--authority-sha256", "0" * 64,
            "--code-sha256", "1" * 64,
            "--input-sha256", "2" * 64,
            "--nonformal", "--execute",
        ]
    ) == 0
    assert observed == {
        "nonformal": True,
        "resume": str(root),
        "run": True,
    }


def test_mutations_reject_fallback_identity_digests_and_budget(
    authenticated_boundary, tmp_path
):
    provider = _provider(authenticated_boundary)
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="budget 500"):
        _runner_config(provider, budget=500)

    class Fallback:
        provider_identity = provider.provider_identity
        provider_identity_payload = provider.provider_identity_payload
        planned_epoch_budget = 100
        next_batch = provider.next_batch
        sampler_state = provider.sampler_state
        load_sampler_state = provider.load_sampler_state

    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="fallback"):
        RUNNER.V023TwoRouteSourceTrainingRunner(_runner_config(provider), Fallback())

    bad = deepcopy(_runner_config(provider))
    object.__setattr__(
        bad,
        "authority_digests",
        RUNNER.RunAuthorityDigests("0" * 64, "1" * 64, "2" * 64),
    )
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="cross-bound"):
        RUNNER.V023TwoRouteSourceTrainingRunner(bad, _provider(authenticated_boundary))

    arguments = Namespace(
        execute=True,
        output_root=str(tmp_path / "cli-output"),
        epochs=100,
        provider_factory="v023_c1c2_provider_factory_v3:make_provider",
        model_config_json=str(MODEL_CONFIG_PATH),
        train_seed=RUNNER.FORMAL_TRAIN_SEED,
        authority_sha256="0" * 64,
        code_sha256="1" * 64,
        input_sha256="2" * 64,
    )
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="cross-bound"):
        RUNNER.preflight_from_args(arguments)


def test_deploy_function_matches_existing_physical_carrier_on_random_inputs():
    physical_directory = HERE.parent / "multi-catfish-v023-physical"
    sys.path.insert(0, str(physical_directory))
    try:
        physical = importlib.import_module("v023_physical_episode_runner")
    finally:
        sys.path.remove(str(physical_directory))
    rng = np.random.default_rng(20260907)
    for _ in range(25):
        q1 = rng.normal(size=(7, 28)).astype(np.float32)
        q2 = rng.normal(size=(7, 28)).astype(np.float32)
        masks = rng.random((7, 28)) > 0.3
        masks[:, 0] = True
        expected = physical._masked_argmax(
            np.asarray(q1, dtype=np.float64) + np.asarray(q2, dtype=np.float64), masks
        )
        actual = MODEL.deploy_q12_action(q1, q2, masks)
        assert np.array_equal(actual, expected)
