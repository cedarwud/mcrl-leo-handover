from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (
    HERE,
    REPO / "src",
    REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation",
    REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import bind_v023_c1c2_successor_stagec_freeze as binder
import accept_stage_c_chunk_equivalence as chunk_acceptance
import build_stage_c_admission_mapping as admission_mapping_builder
import build_stage_c_chunk_acceptance_bundle as acceptance_bundle_builder
import build_v023_c1c2_successor_stagec_manifest as manifest_builder
import build_v023_c1c2_successor_world_plan as plan_builder
import preflight_v023_c1c2_successor_stagec as preflight
import run_v023_c1c2_successor_stage_c as controller
import run_v023_c1c2_successor_stage_c_chunks as chunk_controller
import seal_stage_c_declined_continuation as closure_sealer
import stagec_common as common
import verify_v023_c1c2_successor_stagec as verifier
import v023_c1c2_successor_physical_runner as runner
from mcrl.runtime.trainer_env import TrainerEnvironment


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(common.canonical_bytes(value))


def _fixture_rngs(seed: int):
    sequence = np.random.SeedSequence(seed)
    children = sequence.spawn(2)
    return np.random.default_rng(children[0]), np.random.default_rng(children[1])


class _AcceptanceProducerAdapter:
    """Synthetic producer using the real receipt and chunk persistence writers."""

    def __init__(self, arm: str) -> None:
        self.arm = arm
        self.rng_factory = _fixture_rngs
        self.archive = object()
        self.environment_factory = self._environment_factory
        self._state = None
        self._binding = {
            "arm": arm,
            "routes": [] if arm == "BASELINE" else ["C1", "C2"],
            "checkpoint_sha256": runner.canonical_sha256(
                {"arm": arm, "fixture": "acceptance-producer"}
            ),
            "fixed_policy": True,
        }

    @staticmethod
    def _environment_factory(_archive, _users):
        environment = object.__new__(TrainerEnvironment)
        environment.environment = SimpleNamespace(
            physics=SimpleNamespace(segment_warm_start="uniform-episode-length")
        )
        return environment

    @property
    def policy_bindings(self):
        return {self.arm: self._binding}

    def resume_state_for(self, arm):
        assert arm == self.arm
        return self._state

    def run_episode(self, *, arm, world, plan_sha256, resume_state=None):
        assert arm == self.arm
        if resume_state is None:
            age_rng = _fixture_rngs(world.world_seed)[0].spawn(1)[0]
        else:
            age_rng = np.random.default_rng()
            age_rng.bit_generator.state = resume_state["environment_training_state"]["age_rng_state"]
        ages = age_rng.integers(0, runner.STEPS, size=runner.USERS)
        bits = float(math.fsum(float(value + 1) for value in ages))
        energy = float(runner.USERS + world.episode_index / 10_000)
        receipt = runner.EpisodeReceipt(
            schema=runner.RECEIPT_SCHEMA,
            status=runner.STATUS,
            split=runner.SPLIT,
            arm=arm,
            routes=() if arm == "BASELINE" else runner.ROUTES,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=runner.USERS,
            steps=runner.STEPS,
            decision_interval_s=1.0,
            total_bits=bits,
            total_energy_j=energy,
            ratio_of_sums_ee_bits_per_j=bits / energy,
            served_user_steps=runner.USERS * runner.STEPS,
            service_opportunities=runner.USERS * runner.STEPS,
            service_fraction=1.0,
            initial_world_sha256=runner.canonical_sha256({"ages": ages}),
            field_component=runner.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=runner.canonical_sha256({"ages": ages, "arm": arm}),
            plan_sha256=plan_sha256,
            policy_binding=self._binding,
        )
        receipt.verify()
        self._state = {
            "schema": f"{runner.SCHEMA}-resume-state",
            "arm": arm,
            "episode_index": world.episode_index,
            "world_id": world.world_id,
            "world_seed": world.world_seed,
            "field_root_digest": world.field_root_digest,
            "plan_sha256": plan_sha256,
            "policy_binding": self._binding,
            "environment_training_state": {
                "format_version": 1,
                "age_rng_state": age_rng.bit_generator.state,
            },
        }
        return receipt


@pytest.fixture(scope="module")
def producer_exports(tmp_path_factory: pytest.TempPathFactory):
    from ee_axis_two_route_model import EEAxisTwoRouteConfig, EEAxisTwoRouteModel
    from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
    from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig

    raw = json.loads((REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json").read_text())
    q1, q2 = dict(raw["q1"]), dict(raw["q2"])
    q1["hidden_layers"] = tuple(q1["hidden_layers"])
    q1["loss_weights"] = tuple(q1["loss_weights"])
    q2["hidden_layers"] = tuple(q2["hidden_layers"])
    model = EEAxisTwoRouteModel(
        EEAxisTwoRouteConfig(q1=EEAxisActionSharedConfig(**q1), q2=EEAxisV014HeadConfig(**q2)),
        train_seed=2927175120652069826,
    )
    root = tmp_path_factory.mktemp("sealed-stage-a")
    export_dir = root / "exports/epoch-0100"
    export_dir.mkdir(parents=True)
    entries = []
    for index, arm in enumerate(common.LEARNED_ARMS):
        state = model.checkpoint_state(update_count=200, route_update_counts={"C1": 100, "C2": 100})
        path = export_dir / f"{index:02d}-{arm}.current-ee-axis-two-route.pt"
        torch.save(state, path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        path.with_name(path.name + ".sha256").write_text(f"{sha}\n", encoding="ascii")
        entries.append({"arm": arm, "path": path.relative_to(root).as_posix(), "sha256": sha, "update_count": 200})
    export_manifest = {"epoch": 100, "update_count": 200, "arm_order": list(common.LEARNED_ARMS), "exports": entries}
    _write_json(root / "exports/epoch-0100.json", export_manifest)
    receipt = {"arm_order": list(common.LEARNED_ARMS), "epoch_100_integrity": {"decision": "PASS_SOURCE_TRAINING_INTEGRITY"}}
    _write_json(root / "canonical-receipt.json", receipt)
    files = [path for path in root.rglob("*") if path.is_file()]
    manifest = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
        for path in sorted(files)
    )
    (root / "MANIFEST.sha256").write_text(manifest, encoding="ascii")
    manifest_sha = hashlib.sha256((root / "MANIFEST.sha256").read_bytes()).hexdigest()
    (root / "COMPLETE").write_text(f"{manifest_sha}  MANIFEST.sha256\n", encoding="ascii")
    return root, entries


def test_stage_a_binding_uses_model_written_exports(producer_exports) -> None:
    root, entries = producer_exports
    bound = binder.bind_stage_a(root)
    assert [entry["arm"] for entry in bound["exports"]] == list(common.LEARNED_ARMS)
    assert [entry["sha256"] for entry in bound["exports"]] == [entry["sha256"] for entry in entries]


def test_finished_verifier_requires_and_materializes_authenticated_stage_ab_supplement(
    tmp_path: Path,
    producer_exports,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage_a_root, _entries = producer_exports
    stage_a = binder.bind_stage_a(stage_a_root)
    bindings_path = tmp_path / "prospective-bindings.json"
    _write_json(bindings_path, {"fixture": "prospective-empty-stage-a"})
    stage_b_path = tmp_path / "stage-b-gate.json"
    _write_json(
        stage_b_path,
        {"status": "PASS_PLUMBING_INTEGRITY", "formal": True},
    )
    common.write_digest_sidecar(stage_b_path)
    supplement_path = tmp_path / "stage-ab-supplement.json"
    _write_json(
        supplement_path,
        {
            "schema": common.SCHEMA_STAGE_AB_SUPPLEMENT,
            "status": "PASS_STAGE_AB_IMPORTED_FOR_STAGE_C",
            "formal": True,
            "bindings_sha256": common.file_sha256(bindings_path),
            "stage_a": stage_a,
            "stage_b_pass_receipt": {
                "path": str(stage_b_path.resolve()),
                "sha256": common.file_sha256(stage_b_path),
            },
        },
    )
    common.write_digest_sidecar(supplement_path)
    root = tmp_path / "finished-root"
    root.mkdir()
    prospective = {
        "stage_a": {"root": "", "exports": [], "manifest_sha256": "0" * 64},
        "stage_c_output_root": str(root.resolve()),
        "code": {"external_manifest_sha256": "c" * 64},
        "git": {"commit": "d" * 40, "tree": "e" * 40},
    }
    monkeypatch.setattr(common, "verify_bindings", lambda _path: copy.deepcopy(prospective))
    monkeypatch.setattr(common, "verify_runtime_identity", lambda _bindings: None)
    monkeypatch.setattr(common, "verify_code_manifest", lambda: ("c" * 64, {}))

    def observe_materialized(bindings):
        assert bindings["stage_a"] == stage_a
        raise common.StageCError("observed materialized Stage-A supplement")

    monkeypatch.setattr(verifier, "_expected_policy_bindings", observe_materialized)
    with pytest.raises(common.StageCError, match="observed materialized"):
        verifier.verify_finished(root, bindings_path, supplement_path)
    with pytest.raises(common.StageCError, match="missing"):
        verifier.verify_finished(root, bindings_path, tmp_path / "missing-supplement.json")
    _write_json(bindings_path, {"fixture": "prospective-bindings-drifted-after-supplement"})
    with pytest.raises(common.StageCError, match="supplement identity drifted"):
        verifier.verify_finished(root, bindings_path, supplement_path)


def test_acceptance_end_to_end_formal_mutation_rehearsal_and_launch_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in common.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    plan_path = tmp_path / "world-plan.json"
    _write_json(plan_path, plan_builder.build_world_plan())
    bindings_path = tmp_path / "bindings.json"
    _write_json(bindings_path, {"fixture": "producer-written-acceptance"})
    runtime_path = tmp_path / "runtime-admission.json"
    _write_json(runtime_path, {"fixture": "runtime-admission"})
    common.write_digest_sidecar(runtime_path)
    supplement_path = tmp_path / "stage-ab-supplement.json"
    acceptance_sha = common.file_sha256(common.ACCEPTANCE_PROCEDURE)
    sampler = {"part": "train", "fixture": "acceptance-producer"}
    bindings = {
        "physical_inputs": {
            "tle_root": str(tmp_path / "tle"),
            "tle_manifest_sha256": "a" * 64,
            "prereg_sha256": "b" * 64,
        },
        "world_plan": {"path": str(plan_path)},
        "scheduling_addendum": {"sha256": "c" * 64},
        "code": {"external_manifest_sha256": "d" * 64},
        "execution": {name: "1" for name in common.NUMERICAL_THREAD_ENV},
        "acceptance_procedure": {"sha256": acceptance_sha},
    }
    supplement = {"supplement_sha256": "e" * 64}
    admission = {
        "admission_sha256": "f" * 64,
        "sampler": {"as_dict_sha256": common.canonical_sha256(sampler)},
    }
    monkeypatch.setattr(common, "verify_bindings", lambda _path: dict(bindings))
    monkeypatch.setattr(
        common, "verify_stage_ab_supplement",
        lambda _supplement, _bindings_path, _bindings=None: dict(supplement),
    )
    monkeypatch.setattr(common, "materialize_stage_ab", lambda value, _supplement: value)
    monkeypatch.setattr(common, "verify_runtime_identity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chunk_controller, "_runner", lambda: runner)
    monkeypatch.setattr(
        chunk_controller, "_policy", lambda _bindings, _runner, arm: SimpleNamespace(arm=arm)
    )
    monkeypatch.setattr(
        runner, "authenticate_runtime_admission", lambda *_args, **_kwargs: dict(admission)
    )
    monkeypatch.setattr(runner, "authenticate_tle_archive", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        runner,
        "FixedPolicyEpisodeAdapter",
        lambda *, policies, **_kwargs: _AcceptanceProducerAdapter(policies[0].arm),
    )
    monkeypatch.setattr(
        controller, "_make_environment",
        lambda _archive, _users: SimpleNamespace(sampler=SimpleNamespace(as_dict=lambda: sampler)),
    )
    import mcrl.env.tle as tle_module
    monkeypatch.setattr(tle_module, "TleArchive", lambda _path: object())

    def acceptance_args(arm: str, output: Path, *, non_formal: bool) -> argparse.Namespace:
        return argparse.Namespace(
            bindings=bindings_path,
            arm=arm,
            output=output,
            runtime_admission=runtime_path,
            admission_supplement=supplement_path,
            episodes=100 if non_formal else 200,
            chunks=2,
            non_formal=non_formal,
        )

    formal_receipts = []
    for arm in common.ARMS:
        output = tmp_path / "formal" / arm
        result = chunk_acceptance.accept(acceptance_args(arm, output, non_formal=False))
        assert result["formal"] is True
        assert result["rehearsal_chunk"] is None
        formal_receipts.append(output / "ACCEPTANCE.json")

    original_merge = runner.merge_arm_chunks

    def merge_then_mutate(*args, **kwargs):
        result = original_merge(*args, **kwargs)
        merged_root = Path(args[2])
        rung_path = merged_root / "rungs/rung-000100.json"
        rung = common.read_json(rung_path, field="mutation fixture rung")
        rung["scientific_disposition_emitted"] = True
        _write_json(rung_path, rung)
        return result

    monkeypatch.setattr(runner, "merge_arm_chunks", merge_then_mutate)
    with pytest.raises(
        common.StageCError,
        match=r"rungs\[100\]\.scientific_disposition_emitted",
    ):
        chunk_acceptance.accept(
            acceptance_args("FULL2", tmp_path / "mutated", non_formal=False)
        )
    monkeypatch.setattr(runner, "merge_arm_chunks", original_merge)

    rehearsal_receipts = []
    for arm in common.ARMS:
        output = tmp_path / "rehearsal" / arm
        result = chunk_acceptance.accept(acceptance_args(arm, output, non_formal=True))
        assert result["formal"] is False
        assert result["rehearsal_chunk"] == 50
        rehearsal_receipts.append(output / "ACCEPTANCE.json")

    formal_bundle = tmp_path / "formal-bundle.json"
    assert acceptance_bundle_builder.main([
        "--bindings", str(bindings_path), "--receipts",
        *(str(path) for path in formal_receipts), "--output", str(formal_bundle),
    ]) == 0
    gate_bindings = {
        **bindings,
        "bindings_sha256": common.file_sha256(bindings_path),
    }
    assert common.verify_acceptance_bundle(formal_bundle, gate_bindings)["formal"] is True
    launch_args = argparse.Namespace(
        bindings=bindings_path,
        admission_supplement=supplement_path,
        acceptance_bundle=formal_bundle,
        runtime_admission=runtime_path,
        arm="FULL2",
    )
    assert chunk_controller.authenticate_launch(launch_args)["status"] == "AUTHENTICATED_STAGEC_CHUNK_LAUNCH"

    rehearsal_bundle = tmp_path / "rehearsal-bundle.json"
    assert acceptance_bundle_builder.main([
        "--bindings", str(bindings_path), "--receipts",
        *(str(path) for path in rehearsal_receipts), "--output", str(rehearsal_bundle),
    ]) == 0
    with pytest.raises(common.StageCError, match="acceptance bundle identity drifted"):
        chunk_controller.authenticate_launch(
            argparse.Namespace(**{**vars(launch_args), "acceptance_bundle": rehearsal_bundle})
        )


def _configure_admission_mapping_builder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[list[str], dict[str, object], SimpleNamespace, Path, Path]:
    bindings_path = tmp_path / "bindings.json"
    _write_json(bindings_path, {"fixture": "admission-mapping-builder"})

    stage_a_root = tmp_path / "stage-a"
    stage_a_root.mkdir()
    exports = []
    policy_bindings = {}
    for arm in common.LEARNED_ARMS:
        checkpoint = stage_a_root / f"{arm}.pt"
        checkpoint.write_bytes(arm.encode("ascii"))
        checkpoint_sha = common.file_sha256(checkpoint)
        exports.append({"arm": arm, "path": checkpoint.name, "sha256": checkpoint_sha})
        policy_bindings[arm] = {
            "arm": arm,
            "routes": ["C1", "C2"],
            "checkpoint_sha256": checkpoint_sha,
            "fixed_policy": True,
        }

    baseline_checkpoint = tmp_path / "baseline.pt"
    baseline_status = tmp_path / "baseline-status.json"
    baseline_checkpoint.write_bytes(b"baseline")
    _write_json(baseline_status, {"status": "complete"})
    baseline_checkpoint_sha = common.file_sha256(baseline_checkpoint)
    baseline_status_sha = common.file_sha256(baseline_status)
    policy_bindings["BASELINE"] = {
        "arm": "BASELINE",
        "routes": [],
        "checkpoint_sha256": baseline_checkpoint_sha,
        "authentication_sha256": baseline_status_sha,
        "fixed_policy": True,
    }
    prospective = {
        "baseline": {
            "checkpoint_path": str(baseline_checkpoint),
            "checkpoint_sha256": baseline_checkpoint_sha,
            "status_path": str(baseline_status),
            "status_sha256": baseline_status_sha,
            "adapter_closure_sha256": "a" * 64,
        },
        "code": {"external_manifest_sha256": "b" * 64},
        "git": {"commit": "1" * 40, "tree": "2" * 40},
        "acceptance_procedure": {"sha256": common.file_sha256(common.ACCEPTANCE_PROCEDURE)},
    }
    stage_a = {
        "root": str(stage_a_root),
        "exports": exports,
        "manifest_sha256": "c" * 64,
    }
    supplement = {
        "stage_a": stage_a,
        "supplement_path": str(tmp_path / "supplement.json"),
        "supplement_sha256": "d" * 64,
    }
    materialized = {**prospective, "stage_a": stage_a}

    procedure_sha = common.file_sha256(common.ACCEPTANCE_PROCEDURE)
    receipt_records = []
    for arm in common.ARMS:
        receipt_path = tmp_path / f"acceptance-{arm}.json"
        _write_json(
            receipt_path,
            {
                "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
                "formal": True,
                "arm": arm,
                "episodes": 200,
                "chunks": [[1, 100], [101, 200]],
                "rehearsal_chunk": None,
                "bindings_sha256": common.file_sha256(bindings_path),
                "code_manifest_sha256": "b" * 64,
                "acceptance_procedure_sha256": procedure_sha,
                "receipt_comparison_excluded_provenance_fields": list(
                    common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS
                ),
                "merged_artifacts_compared": list(common.CHUNK_EQUIVALENCE_ARTIFACTS),
            },
        )
        common.write_digest_sidecar(receipt_path)
        receipt_records.append(
            {
                "arm": arm,
                "path": str(receipt_path),
                "sha256": common.file_sha256(receipt_path),
                "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
            }
        )
    acceptance_path = tmp_path / "acceptance-bundle.json"
    _write_json(
        acceptance_path,
        {
            "schema": common.SCHEMA_ACCEPTANCE_BUNDLE,
            "status": "PASS_ALL_FOUR_ARM_CHUNK_EQUIVALENCE",
            "formal": True,
            "arms": list(common.ARMS),
            "bindings_sha256": common.file_sha256(bindings_path),
            "code_manifest_sha256": "b" * 64,
            "acceptance_procedure_sha256": procedure_sha,
            "receipts": receipt_records,
        },
    )
    common.write_digest_sidecar(acceptance_path)

    runtime_path = tmp_path / "runtime-admission.json"
    _write_json(runtime_path, {"fixture": "authenticated-runtime-admission"})
    common.write_digest_sidecar(runtime_path)
    adapter = SimpleNamespace(policy_bindings=policy_bindings)
    evidence_records = {}
    for name in ("prereg", "tle", "execution", "stage-a", "stage-b"):
        evidence = (
            stage_a_root / "stage-a-pass.json"
            if name == "stage-a"
            else tmp_path / f"{name}.json"
        )
        _write_json(evidence, {"evidence": name})
        evidence_records[name] = {
            "path": str(evidence.resolve()), "sha256": common.file_sha256(evidence),
        }
        if name in {"tle", "execution", "stage-b"}:
            common.write_digest_sidecar(evidence)
    runtime_admission = {
        "admission_path": str(runtime_path.resolve()),
        "admission_sha256": common.file_sha256(runtime_path),
        "prereg": evidence_records["prereg"],
        "tle_manifest": evidence_records["tle"],
        "execution_configuration": evidence_records["execution"],
        "predecessor_pass_receipts": [
            evidence_records["stage-a"], evidence_records["stage-b"],
        ],
    }
    fake_runner = SimpleNamespace(
        authenticate_runtime_admission=lambda *_args, **_kwargs: copy.deepcopy(runtime_admission)
    )
    monkeypatch.setattr(common, "verify_bindings", lambda _path: copy.deepcopy(prospective))
    monkeypatch.setattr(
        common,
        "verify_stage_ab_supplement",
        lambda *_args, **_kwargs: copy.deepcopy(supplement),
    )
    monkeypatch.setattr(
        common,
        "verify_runtime_identity",
        lambda _bindings, *, chunk_mode=False: None
        if chunk_mode
        else pytest.fail("admission mapping builder did not use chunk runtime identity"),
    )
    monkeypatch.setattr(controller, "_authenticate_stage_b", lambda *_args: None)
    monkeypatch.setattr(controller, "_module", lambda _path: fake_runner)
    monkeypatch.setattr(controller, "_policies", lambda *_args: tuple(policy_bindings))
    monkeypatch.setattr(
        controller, "_adapter_and_plan", lambda *_args, **_kwargs: (adapter, object())
    )
    output = tmp_path / "admission-mapping.json"
    argv = [
        "--bindings", str(bindings_path),
        "--admission-supplement", str(tmp_path / "supplement.json"),
        "--acceptance-bundle", str(acceptance_path),
        "--runtime-admission", str(runtime_path),
        "--stage-b-root", str(tmp_path / "stage-b"),
        "--output", str(output),
    ]
    return argv, materialized, adapter, acceptance_path, output


def test_admission_mapping_builder_is_byte_identical_to_sequential_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv, bindings, adapter, _acceptance, output = _configure_admission_mapping_builder(
        tmp_path, monkeypatch
    )
    expected = admission_mapping_builder.build(
        admission_mapping_builder._parser().parse_args(argv)
    )
    assert admission_mapping_builder.main(argv) == 0
    assert output.read_bytes() == common.canonical_bytes(expected) + b"\n"
    assert common.verify_named_sidecar(output) == common.file_sha256(output)
    assert capsys.readouterr().out == (
        f"STAGEC_ADMISSION_MAPPING_WRITTEN path={output} "
        f"sha256={common.file_sha256(output)}\n"
    )


def test_builder_output_published_by_merge_satisfies_formal_admission_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    argv, bindings, adapter, _acceptance, output = _configure_admission_mapping_builder(
        tmp_path, monkeypatch
    )
    assert admission_mapping_builder.main(argv) == 0
    built = common.read_json(output, field="builder formal admission")
    merged_root = tmp_path / "synthetic-merge-four"
    merged_root.mkdir()
    common.publish_sealed_json(
        merged_root / common.FORMAL_ADMISSION_NAME,
        built,
        field="synthetic merge-four formal admission",
    )
    inputs = built["authenticated_inputs"]
    stage_a_path = Path(str(inputs["stage_a_pass_receipt"]["path"]))
    supplement = {
        "supplement_sha256": "d" * 64,
        "stage_a": {
            "root": str(stage_a_path.parent),
            "pass_receipt": {
                "path": stage_a_path.name,
                "sha256": inputs["stage_a_pass_receipt"]["sha256"],
            },
        },
        "stage_b_pass_receipt": inputs["stage_b_pass_receipt"],
    }
    monkeypatch.setattr(
        verifier,
        "_physical_runner",
        lambda: SimpleNamespace(
            SCHEMA="multi-catfish-mcrl-v023-c1c2-successor-physical-evaluation-v1"
        ),
    )
    accepted = verifier._verify_formal_admission(
        merged_root,
        bindings,
        adapter.policy_bindings,
        common.file_sha256(Path(argv[1])),
        supplement,
    )
    assert accepted == built
    assert set(accepted["authenticated_inputs"]) == {
        "prereg", "tle_manifest", "execution_configuration",
        "stage_a_pass_receipt", "stage_b_pass_receipt", "runtime_admission",
    }


def test_admission_mapping_builder_refuses_drifted_acceptance_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv, _bindings, _adapter, acceptance, output = _configure_admission_mapping_builder(
        tmp_path, monkeypatch
    )
    acceptance.write_bytes(acceptance.read_bytes() + b"\n")
    assert admission_mapping_builder.main(argv) == 2
    assert not output.exists()
    assert capsys.readouterr().err.startswith("STAGEC_ADMISSION_MAPPING_ERROR: ")


class _ProducerFixtureAdapter:
    def __init__(self) -> None:
        self._bindings = {
            arm: {"arm": arm, "routes": [] if arm == "BASELINE" else ["C1", "C2"], "checkpoint_sha256": hashlib.sha256(arm.encode()).hexdigest(), "fixed_policy": True}
            for arm in common.ARMS
        }
        self._states = {arm: None for arm in common.ARMS}

    @property
    def policy_bindings(self):
        return self._bindings

    def resume_state_for(self, arm):
        return self._states[arm]

    def restore_resume_states(self, states):
        self._states = dict(states)

    def run_episode(self, *, arm, world, plan_sha256, resume_state=None):
        offset = common.ARMS.index(arm)
        bits = float(13000 - 1000 * offset + world.episode_index)
        row = runner.EpisodeReceipt(
            schema=runner.RECEIPT_SCHEMA, status=runner.STATUS, split=runner.SPLIT,
            arm=arm, routes=() if arm == "BASELINE" else runner.ROUTES,
            episode_index=world.episode_index, world_id=world.world_id, world_seed=world.world_seed,
            users=100, steps=10, decision_interval_s=1.0, total_bits=bits,
            total_energy_j=10.0, ratio_of_sums_ee_bits_per_j=bits / 10.0,
            served_user_steps=1000, service_opportunities=1000, service_fraction=1.0,
            initial_world_sha256=runner.canonical_sha256({"world": world.world_id}),
            field_component=runner.FIELD_COMPONENT, field_root_digest=world.field_root_digest,
            action_trace_sha256=runner.canonical_sha256({"arm": arm, "world": world.world_id}),
            plan_sha256=plan_sha256, policy_binding=self._bindings[arm],
        )
        self._states[arm] = {"arm": arm, "episode_index": world.episode_index, "plan_sha256": plan_sha256}
        return row


@pytest.fixture
def runner_written_rung(tmp_path: Path):
    payload = plan_builder.build_world_plan()
    plan = runner.EvaluationPlan(
        worlds=tuple(runner.WorldBinding(**row) for row in payload["worlds"]),
        plan_sha256=payload["plan_sha256"],
    )
    root = tmp_path / "formal-root"
    adapter = _ProducerFixtureAdapter()
    admission_mapping = {
        arm: {"policy_binding": adapter.policy_bindings[arm]}
        for arm in common.ARMS
    }
    runner.FixedPolicyEvaluationRunner(
        adapter=adapter, plan=plan, admission_mapping=admission_mapping
    ).run(output_dir=root, pause_at=100)
    return root, payload


def test_independent_verifier_accepts_runner_written_synthetic_rung(runner_written_rung) -> None:
    root, plan = runner_written_rung
    checkpoint = verifier._read_checkpoint(root / "checkpoints/checkpoint-000100.json")
    pooled = verifier.verify_episode_rows(checkpoint["receipts"], plan, 100)
    assert pooled["FULL2"]["ratio_of_sums_ee_bits_per_j"] > pooled["BASELINE"]["ratio_of_sums_ee_bits_per_j"]


def test_verifier_rejects_policy_digest_not_equal_to_frozen_binding(runner_written_rung) -> None:
    root, plan = runner_written_rung
    checkpoint = verifier._read_checkpoint(root / "checkpoints/checkpoint-000100.json")
    expected = copy.deepcopy(checkpoint["policy_bindings"])
    expected["FULL2"]["checkpoint_sha256"] = "f" * 64
    with pytest.raises(common.StageCError, match="frozen policy"):
        verifier.verify_episode_rows(
            checkpoint["receipts"],
            plan,
            100,
            expected_policy_bindings=expected,
        )


def test_verifier_rejects_rewritten_cumulative_prefix(runner_written_rung) -> None:
    root, _plan = runner_written_rung
    checkpoint = verifier._read_checkpoint(root / "checkpoints/checkpoint-000100.json")
    previous = checkpoint["receipts"]
    pooled = {arm: verifier._pool(previous, arm) for arm in common.ARMS}
    rewritten = copy.deepcopy(previous)
    rewritten[0]["total_bits"] += 1.0
    with pytest.raises(common.StageCError, match="prefix was rewritten"):
        verifier._verify_cumulative_prefix(
            previous, pooled, rewritten, pooled, boundary=200
        )


@pytest.fixture
def runner_written_arm_barrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    for name in common.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    payload = plan_builder.build_world_plan()
    plan = runner.EvaluationPlan(
        worlds=tuple(runner.WorldBinding(**row) for row in payload["worlds"]),
        plan_sha256=payload["plan_sha256"],
    )
    adapter = _AcceptanceProducerAdapter("BASELINE")
    provenance = {
        name: common.canonical_sha256({"barrier-fixture": name})
        for name in (
            "authority_sha256",
            "code_manifest_sha256",
            "configuration_sha256",
            "tle_sha256",
            "prereg_sha256",
            "admission_sha256",
            "stage_ab_supplement_sha256",
            "acceptance_evidence_sha256",
            "acceptance_procedure_sha256",
        )
    }
    context = {
        "arm": "BASELINE",
        "adapter": adapter,
        "schedule_sha256": "a" * 64,
        "execution_mode": "arm_decoupled",
        "formal": True,
        "continuation_limit": 3000,
        "provenance": provenance,
    }
    table = runner.build_chunk_boundary_states(plan, context, (0, 100, 200))
    roots = []
    for start, end in ((0, 100), (100, 200)):
        root = tmp_path / f"BASELINE-{start:06d}-{end:06d}"
        runner.run_arm_chunk("BASELINE", start, end, table[start], root)
        roots.append(root)
    merged = tmp_path / "BASELINE-merged"
    runner.merge_arm_chunks("BASELINE", roots, merged)
    return merged


def _barrier_args(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        arm_merge_root=root,
        arm="BASELINE",
        completed=200,
        bindings=Path("bindings.json"),
        admission_supplement=Path("supplement.json"),
        acceptance_bundle=Path("acceptance.json"),
        runtime_admission=Path("runtime.json"),
    )


def _stub_chunk_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunk_controller, "_runner", lambda: runner)
    monkeypatch.setattr(
        controller,
        "_module",
        lambda _path: SimpleNamespace(verify_arm_chunk=lambda *_args, **_kwargs: {}),
    )


def test_barrier_authenticates_exact_runner_written_cumulative_contents(
    runner_written_arm_barrier: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_chunk_verifier(monkeypatch)
    result = chunk_controller.check_barrier(_barrier_args(runner_written_arm_barrier))
    assert result["status"] == "AUTHENTICATED_CUMULATIVE_BARRIER"


@pytest.mark.parametrize("mutation", ["empty", "missing", "wrong-count", "tampered-rung"])
def test_barrier_rejects_incomplete_or_tampered_cumulative_contents(
    runner_written_arm_barrier: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _stub_chunk_verifier(monkeypatch)
    merge_path = runner_written_arm_barrier / "arm-merge.json"
    merge = common.read_json(merge_path, field="barrier mutation merge")
    if mutation == "empty":
        merge["chunk_receipts"] = []
    elif mutation == "missing":
        merge["chunk_receipts"].pop()
    elif mutation == "wrong-count":
        checkpoint_path = runner_written_arm_barrier / "checkpoints/checkpoint-000200.json"
        checkpoint = common.read_json(checkpoint_path, field="barrier mutation checkpoint")
        checkpoint["receipts"].pop()
        _write_json(checkpoint_path, checkpoint)
        merge["barrier_artifacts"]["200"]["checkpoint"]["sha256"] = common.file_sha256(
            checkpoint_path
        )
    else:
        rung_path = runner_written_arm_barrier / "rungs/rung-000200.json"
        rung = common.read_json(rung_path, field="barrier mutation rung")
        rung["pooled"]["total_bits"] += 1.0
        _write_json(rung_path, rung)
        merge["barrier_artifacts"]["200"]["rung"]["sha256"] = common.file_sha256(
            rung_path
        )
    _write_json(merge_path, merge)
    with pytest.raises(common.StageCError):
        chunk_controller.check_barrier(_barrier_args(runner_written_arm_barrier))


def test_arm_merge_provenance_uses_explicit_order_after_canonical_serialisation(
    tmp_path: Path,
) -> None:
    provenance = {}
    for arm in common.ARMS:
        merge_path = tmp_path / f"{arm}-arm-merge.json"
        _write_json(merge_path, {"chunk_receipts": []})
        provenance[arm] = {
            "path": str(merge_path.resolve()),
            "sha256": common.file_sha256(merge_path),
            "chunk_receipts": [],
        }
    receipt_path = tmp_path / "canonical-receipt.json"
    _write_json(
        receipt_path,
        {
            "arm_order": list(common.ARMS),
            "arm_merge_provenance": provenance,
        },
    )
    receipt = common.read_json(receipt_path, field="canonical arm-order receipt")
    assert list(receipt["arm_merge_provenance"]) != list(common.ARMS)
    verifier._verify_arm_merge_provenance(
        receipt["arm_merge_provenance"], receipt["arm_order"]
    )
    with pytest.raises(common.StageCError, match="arm-merge provenance"):
        verifier._verify_arm_merge_provenance(
            receipt["arm_merge_provenance"], list(reversed(common.ARMS))
        )


def test_verifier_rejects_any_stop_token_in_scientific_root(tmp_path: Path) -> None:
    root = tmp_path / "stopped"
    root.mkdir()
    _write_json(root / "receipt.json", {"nested": {"token": "STOP_PHYSICAL_EVALUATION_INTEGRITY"}})
    with pytest.raises(common.StageCError, match="STOP token"):
        verifier._reject_nonformal(root)


def test_stage_b_gate_authenticates_admitted_stage_a_exports_and_receipt(tmp_path: Path) -> None:
    root = tmp_path / "stage-b"
    root.mkdir()
    admission = tmp_path / "stage-b-runtime-admission.json"
    _write_json(admission, {"schema": "runtime-admission"})
    common.write_digest_sidecar(admission)
    stage_a_receipt = tmp_path / "stage-a-receipt.json"
    _write_json(stage_a_receipt, {"status": "PASS_SOURCE_TRAINING_INTEGRITY"})
    exports = []
    for arm in common.LEARNED_ARMS:
        path = tmp_path / f"{arm}.pt"
        path.write_bytes(arm.encode("ascii"))
        exports.append({"arm": arm, "path": str(path.resolve()), "sha256": common.file_sha256(path)})
    admission_record = {"path": str(admission.resolve()), "sha256": common.file_sha256(admission)}
    stage_a_record = {
        "path": str(stage_a_receipt.resolve()),
        "sha256": common.file_sha256(stage_a_receipt),
        "status": "PASS_SOURCE_TRAINING_INTEGRITY",
    }
    plumbing = {
        "runtime_admission": admission_record,
        "admitted_stage_a": stage_a_record,
        "admitted_exports": exports,
    }
    _write_json(root / "plumbing-receipt.json", plumbing)
    bindings_sha = "a" * 64
    gate = {
        "status": "PASS_PLUMBING_INTEGRITY",
        "formal": True,
        "bindings_sha256": bindings_sha,
        "plumbing_receipt_sha256": common.file_sha256(root / "plumbing-receipt.json"),
        "arms": list(common.ARMS),
        **plumbing,
    }
    _write_json(root / "stage-b-gate.json", gate)
    common.write_digest_sidecar(root / "stage-b-gate.json")
    controller._authenticate_stage_b(root, bindings_sha)
    (tmp_path / "FULL2.pt").write_bytes(b"forged")
    with pytest.raises(common.StageCError, match="export bytes drifted"):
        controller._authenticate_stage_b(root, bindings_sha)


def test_fifth_arm_mutation_is_rejected(runner_written_rung) -> None:
    root, plan = runner_written_rung
    checkpoint = verifier._read_checkpoint(root / "checkpoints/checkpoint-000100.json")
    mutated = copy.deepcopy(checkpoint["receipts"])
    mutated[0]["arm"] = "FIFTH_ARM"
    with pytest.raises(common.StageCError, match="arm order"):
        verifier.verify_episode_rows(mutated, plan, 100)


def test_nonformal_root_and_receipt_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "FORMAL"
    root.mkdir()
    _write_json(root / "receipt.json", {"formal": False})
    with pytest.raises(common.StageCError, match="non-formal"):
        verifier._reject_nonformal(root)
    rehearsal = tmp_path / "x-REHEARSAL-NONFORMAL-y"
    rehearsal.mkdir()
    with pytest.raises(common.StageCError, match="REHEARSAL-NONFORMAL"):
        verifier._reject_nonformal(rehearsal)


def test_plan_drift_is_rejected() -> None:
    payload = plan_builder.build_world_plan()
    payload["worlds"][0]["world_seed"] += 1
    body = dict(payload)
    body.pop("plan_sha256")
    payload["plan_sha256"] = plan_builder.canonical_sha256(body)
    with pytest.raises(plan_builder.WorldPlanError, match="declared 9000-world plan"):
        plan_builder.verify_world_plan(payload)


def test_9000_refuses_missing_owner_notification_marker(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    _write_json(output / "result.json", {"overall_token": runner.HELD, "completed_episode": 3000})
    authority = tmp_path / "authority.json"
    _write_json(authority, {"authority": "continue"})
    args = argparse.Namespace(
        output=output,
        bindings=tmp_path / "bindings.json",
        continuation_authority=authority,
        owner_notification_marker=tmp_path / "missing-owner.json",
        controller_session_id="controller-test",
    )
    with pytest.raises(common.StageCError, match="owner-notification|missing"):
        controller._continuation_banner(args)


def test_9000_banner_authenticates_procedural_owner_reply_and_result(tmp_path: Path) -> None:
    output = tmp_path / "run"
    output.mkdir()
    result = output / "result.json"
    _write_json(result, {"overall_token": runner.HELD, "completed_episode": 3000})
    acknowledgement = "I acknowledge and authorize the unchanged 9000-world continuation."
    bindings = tmp_path / "bindings.json"
    _write_json(bindings, {"binding": "test"})
    marker = tmp_path / "owner-notification.json"
    _write_json(
        marker,
        {
            "formal": True,
            "status": "OWNER_NOTIFIED_FOR_9000_CONTINUATION",
            "owner_reply_verbatim": acknowledgement,
            "notification_sent_utc": "2026-09-08T01:00:00Z",
            "owner_reply_received_utc": "2026-09-08T01:01:00Z",
            "notification_channel": "controller-chat",
            "recorded_by": "controller-test",
            "result_3000_sha256": common.file_sha256(result),
            "bindings_sha256": common.file_sha256(bindings),
            "plan_sha256": common.PLAN_SHA256,
        },
    )
    common.write_digest_sidecar(marker)
    authority = tmp_path / "authority.json"
    _write_json(
        authority,
        {
            "schema": runner.CONTINUATION_AUTHORITY_SCHEMA,
            "status": "AUTHORIZED_CONTINUATION_TO_9000",
            "continuation_from_episode": 3000,
            "continuation_to_episode": 9000,
            "owner_notification": {
                "status": "OWNER_NOTIFIED",
                "path": str(marker.resolve()),
                "sha256": common.file_sha256(marker),
            },
            "owner_reply_sha256": hashlib.sha256(acknowledgement.encode("utf-8")).hexdigest(),
            "recorded_by": "controller-test",
            "bindings_sha256": common.file_sha256(bindings),
            "plan_sha256": common.PLAN_SHA256,
            "policy_bindings_sha256": "b" * 64,
            "held_terminal_token_sha256": runner.HELD_TOKEN_SHA256,
            "result_3000_sha256": common.file_sha256(result),
            "checkpoint_3000_sha256": "c" * 64,
        },
    )
    common.write_digest_sidecar(authority)
    args = argparse.Namespace(
        output=output,
        bindings=bindings,
        continuation_authority=authority,
        owner_notification_marker=marker,
        controller_session_id="controller-test",
    )
    assert controller._continuation_banner(args) == acknowledgement
    _write_json(marker.with_name("wrong-marker.json"), {"formal": True})
    common.write_digest_sidecar(marker.with_name("wrong-marker.json"))
    args.owner_notification_marker = marker.with_name("wrong-marker.json")
    with pytest.raises(common.StageCError, match="owner.notification"):
        controller._continuation_banner(args)


@pytest.mark.parametrize(
    "missing",
    [
        "owner_reply_verbatim",
        "notification_sent_utc",
        "owner_reply_received_utc",
        "notification_channel",
        "recorded_by",
        "result_3000_sha256",
    ],
)
def test_9000_banner_refuses_each_required_owner_marker_field(
    tmp_path: Path, missing: str
) -> None:
    output = tmp_path / "run"
    output.mkdir()
    _write_json(output / "result.json", {"overall_token": runner.HELD, "completed_episode": 3000})
    bindings = tmp_path / "bindings.json"
    _write_json(bindings, {"binding": "test"})
    marker_payload = {
        "formal": True,
        "status": "OWNER_NOTIFIED_FOR_9000_CONTINUATION",
        "owner_reply_verbatim": "Owner authorizes the unchanged 9000-world continuation.",
        "notification_sent_utc": "2026-09-08T01:00:00Z",
        "owner_reply_received_utc": "2026-09-08T01:01:00Z",
        "notification_channel": "controller-chat",
        "recorded_by": "controller-test",
        "result_3000_sha256": common.file_sha256(output / "result.json"),
        "bindings_sha256": common.file_sha256(bindings),
        "plan_sha256": common.PLAN_SHA256,
    }
    marker_payload.pop(missing)
    marker = tmp_path / "owner-marker.json"
    _write_json(marker, marker_payload)
    common.write_digest_sidecar(marker)
    authority = tmp_path / "authority.json"
    _write_json(
        authority,
        {
            "owner_notification": {
                "status": "OWNER_NOTIFIED",
                "path": str(marker.resolve()),
                "sha256": common.file_sha256(marker),
            },
            "recorded_by": "controller-test",
            "bindings_sha256": common.file_sha256(bindings),
        },
    )
    common.write_digest_sidecar(authority)
    with pytest.raises(common.StageCError, match="owner notification marker"):
        controller._continuation_banner(
            argparse.Namespace(
                output=output,
                bindings=bindings,
                continuation_authority=authority,
                owner_notification_marker=marker,
                controller_session_id="controller-test",
            )
        )


@pytest.mark.parametrize(
    "decision", ["DECLINE_CONTINUATION", "DEFER_AND_CLOSE_REPORTING_ROOT"]
)
def test_administrative_decision_marker_authenticates_explicit_closure(
    tmp_path: Path, decision: str
) -> None:
    digests = {
        name: common.canonical_sha256({"closure-fixture": name})
        for name in ("bindings", "policy", "mapping", "result", "checkpoint")
    }
    marker = tmp_path / "owner-decision.json"
    _write_json(marker, {
        "schema": common.SCHEMA_OWNER_CLOSURE_DECISION,
        "formal": True,
        "decision": decision,
        "owner_reply_verbatim": "I explicitly request closure of this reporting root.",
        "notification_sent_utc": "2026-09-08T01:00:00Z",
        "owner_reply_received_utc": "2026-09-08T01:01:00Z",
        "notification_channel": "controller-chat",
        "recorded_by": "controller-test",
        "bindings_sha256": digests["bindings"],
        "plan_sha256": common.PLAN_SHA256,
        "policy_bindings_sha256": digests["policy"],
        "admission_mapping_sha256": digests["mapping"],
        "result_3000_sha256": digests["result"],
        "held_terminal_token_sha256": closure_sealer.HELD_TOKEN_SHA256,
        "checkpoint_3000_sha256": digests["checkpoint"],
    })
    common.write_digest_sidecar(marker)
    payload, observed = closure_sealer._authenticate_decision_marker(
        marker,
        bindings_sha256=digests["bindings"],
        plan_sha256=common.PLAN_SHA256,
        policy_bindings_sha256=digests["policy"],
        admission_mapping_sha256=digests["mapping"],
        result_sha256=digests["result"],
        checkpoint_sha256=digests["checkpoint"],
    )
    assert payload["decision"] == decision
    assert observed == common.file_sha256(marker)


def test_administrative_decision_marker_refuses_silence_or_plain_deferral(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "silent-decision.json"
    digest = "a" * 64
    _write_json(marker, {
        "schema": common.SCHEMA_OWNER_CLOSURE_DECISION,
        "formal": True,
        "decision": "DEFER_CONTINUATION",
        "owner_reply_verbatim": "I will decide whether to continue at a later time.",
        "notification_sent_utc": "2026-09-08T01:00:00Z",
        "owner_reply_received_utc": "2026-09-08T01:01:00Z",
        "notification_channel": "controller-chat",
        "recorded_by": "controller-test",
        "bindings_sha256": digest,
        "plan_sha256": common.PLAN_SHA256,
        "policy_bindings_sha256": digest,
        "result_3000_sha256": digest,
        "held_terminal_token_sha256": closure_sealer.HELD_TOKEN_SHA256,
        "checkpoint_3000_sha256": digest,
    })
    common.write_digest_sidecar(marker)
    with pytest.raises(common.StageCError, match="silent|unanswered"):
        closure_sealer._authenticate_decision_marker(
            marker,
            bindings_sha256=digest,
            plan_sha256=common.PLAN_SHA256,
            policy_bindings_sha256=digest,
            admission_mapping_sha256=digest,
            result_sha256=digest,
            checkpoint_sha256=digest,
        )


def test_manifest_requires_closure_list_and_syncs_every_closure_path(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="required closure list missing"):
        manifest_builder.closure(tmp_path)
    closure_list = REPO / ".scratch/multi-catfish-v023-controller-handoff-20260907/SHADOW-CLOSURE-LIST-2026-09-07.txt"
    closure_paths = {
        line.strip() for line in closure_list.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    }
    sync_paths = set((HERE / manifest_builder.SYNC_LIST_NAME).read_text(encoding="ascii").splitlines())
    assert len(closure_paths) == 246
    assert closure_paths <= sync_paths
    stage_c_members = set(manifest_builder.closure(REPO))
    predecessor = (
        ".scratch/multi-catfish-v023-c1c2-successor/"
        "V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md"
    )
    addendum = (
        ".scratch/multi-catfish-v023-c1c2-successor/"
        "V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-08-R2.md"
    )
    assert {
        predecessor, f"{predecessor}.sha256", addendum, f"{addendum}.sha256",
        ".scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py",
        ".scratch/multi-catfish-v023-ch5-figure-pipeline/test_render_v023_development_curves.py",
        ".scratch/multi-catfish-v023-ch5-figure-pipeline/README.md",
    } <= stage_c_members


def test_runtime_and_closure_bind_only_r2_while_recording_predecessor(
    tmp_path: Path,
) -> None:
    r2_sha = common.verify_named_sidecar(common.SCHEDULING_ADDENDUM)
    predecessor_sha = common.verify_named_sidecar(
        common.PREDECESSOR_SCHEDULING_ADDENDUM
    )
    bindings = {
        "scheduling_addendum": {
            "path": str(common.SCHEDULING_ADDENDUM.resolve()), "sha256": r2_sha,
        },
        "predecessor_addendum": {
            "path": str(common.PREDECESSOR_SCHEDULING_ADDENDUM.resolve()),
            "sha256": predecessor_sha,
        },
    }
    assert closure_sealer._verify_bound_r2_addendum(
        common.SCHEDULING_ADDENDUM, bindings
    ) == r2_sha
    supplied = tmp_path / "supplied-addendum.md"
    supplied.write_bytes(common.SCHEDULING_ADDENDUM.read_bytes())
    common.write_digest_sidecar(supplied)
    with pytest.raises(common.StageCError, match="R2 path bound"):
        closure_sealer._verify_bound_r2_addendum(supplied, bindings)


def test_circular_execution_binding_digest_is_rejected() -> None:
    with pytest.raises(common.StageCError, match="circular"):
        preflight._reject_circular_digest({"self_sha256": "a" * 64}, "b" * 64)
    with pytest.raises(common.StageCError, match="own digest"):
        preflight._reject_circular_digest({"nested": ["b" * 64]}, "b" * 64)


def test_runtime_identity_rejects_git_or_execution_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    frozen_git = {"commit": "a" * 40, "tree": "b" * 40}
    frozen_execution = {"OMP_NUM_THREADS": "2"}
    monkeypatch.setattr(common, "git_identity", lambda _repo=common.REPO: dict(frozen_git))
    monkeypatch.setattr(common, "process_environment", lambda: dict(frozen_execution))
    common.verify_runtime_identity({"git": frozen_git, "execution": frozen_execution})
    with pytest.raises(common.StageCError, match="commit/tree"):
        common.verify_runtime_identity(
            {"git": {"commit": "c" * 40, "tree": "b" * 40}, "execution": frozen_execution}
        )
    with pytest.raises(common.StageCError, match="process/resource"):
        common.verify_runtime_identity({"git": frozen_git, "execution": {"OMP_NUM_THREADS": "8"}})


def test_baseline_dependency_fails_closed_until_postfix_assertion_exists() -> None:
    module = importlib.import_module("baseline_adapter")
    if getattr(module, "CONTRACT_FIELDS_EXCLUDED", None) is True:
        pytest.skip("workspace already contains the required post-fix adapter")
    with pytest.raises(common.StageCError, match="contract_fields_excluded"):
        binder.bind_baseline(common.BASELINE_CHECKPOINT, common.BASELINE_STATUS)


def test_dry_run_prints_commands_without_remote_execution(tmp_path: Path) -> None:
    launcher = HERE / "sync_launch_v023_c1c2_successor_stagec_server.sh"
    syntax = subprocess.run(["bash", "-n", str(launcher)], capture_output=True, text=True, check=False)
    assert syntax.returncode == 0, syntax.stderr
    environment = dict(os.environ)
    environment.pop("V023_STAGEC_PYTHON", None)
    caller_tmpdir = tmp_path / "caller-tmp"
    environment["TMPDIR"] = str(caller_tmpdir)
    completed = subprocess.run(
        [str(launcher), "--dry-run"], cwd=REPO, env=environment,
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ssh sat test -d" in completed.stdout
    assert f"DRY_RUN TMPDIR={caller_tmpdir}" in completed.stdout
    assert "/proc/self/oom_score_adj" not in completed.stderr
    assert "rsync -aR --files-from=" in completed.stdout
    assert "rev-parse HEAD" in completed.stdout
    assert "rev-parse 'HEAD^{tree}'" in completed.stdout
    assert "mode=prepare-and-bind-only-no-stage-b-no-stage-c-launch" in completed.stdout
    assert "tmux new-session" not in completed.stdout
    assert "NO_STAGE_B_OR_STAGE_C_PROCESS_LAUNCHED" not in completed.stdout
    early = subprocess.run(
        [str(launcher), "--dry-run", "--early-baseline-only"], cwd=REPO,
        env=environment, capture_output=True, text=True, check=False,
    )
    assert early.returncode == 2
    assert "usage" in early.stderr


def test_withdrawn_early_baseline_mode_is_absent() -> None:
    assert not hasattr(runner, "authenticate_early_baseline_admission")
    assert "early-baseline" not in (HERE / "launch_stage_c_chunks.sh").read_text(encoding="utf-8")
    assert "early-baseline" not in (HERE / "sync_launch_v023_c1c2_successor_stagec_server.sh").read_text(encoding="utf-8")


def test_chunk_launcher_enforces_worker_cap_and_has_merge_step() -> None:
    launcher = HERE / "launch_stage_c_chunks.sh"
    syntax = subprocess.run(["bash", "-n", str(launcher)], capture_output=True, text=True, check=False)
    assert syntax.returncode == 0, syntax.stderr
    source = launcher.read_text(encoding="utf-8")
    assert "reserve_capacity=$((cores - 2))" in source
    assert "occupied=$(pgrep" in source
    assert "flock -x 9" in source
    assert "OMP_NUM_THREADS=1" in source
    assert "OPENBLAS_NUM_THREADS=1" in source
    assert "--barrier" in source
    assert "chunk-receipt.json" in source
    assert "merge-arm" in source
    assert "6000) previous=3000" in source
    assert "9000) previous=6000" in source
    assert "--continuation-authority" in source
    assert "--owner-notification-marker" in source
    assert "register-continuation" in source
    assert "--continuation-activity" in source
    assert "--resume-continuation" in source
    assert "final_args=(merge-four" in source
    assert "OMP_NUM_THREADS=2" in source
    help_result = subprocess.run(
        [
            sys.executable,
            str(HERE / "run_v023_c1c2_successor_stage_c_chunks.py"),
            "merge-four",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "build_stage_c_admission_mapping.py" in help_result.stdout
    assert chunk_controller._parser().parse_args(
        [
            "run-chunk", "--bindings", "bindings.json",
            "--admission-supplement", "supplement.json",
            "--acceptance-bundle", "acceptance.json",
            "--runtime-admission", "runtime.json", "--arm", "BASELINE",
            "--start", "0", "--end", "100", "--chunk-root", "chunk",
        ]
    ).end == 100


def test_chunk_continuation_refuses_missing_authority_before_boundary_work() -> None:
    called = False

    class NoSchedulingRunner:
        class C1C2PhysicalError(RuntimeError):
            pass

        @staticmethod
        def authenticate_continuation_chain(*_args, **_kwargs):
            nonlocal called
            called = True

    with pytest.raises(common.StageCError, match="continuation authority"):
        chunk_controller._authenticate_continuation(
            argparse.Namespace(
                continuation_authority=None,
                owner_notification_marker=None,
                bindings=Path("bindings.json"),
            ),
            {"stage_c_output_root": "/must-not-be-read"},
            NoSchedulingRunner,
        )
    assert called is False


def test_continuation_policy_membership_accepts_producer_sorted_json_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "reporting"
    checkpoint = root / "checkpoints/checkpoint-003000.json"
    _write_json(
        checkpoint,
        {"policy_bindings": {arm: {"arm": arm} for arm in sorted(common.ARMS)}},
    )
    bindings_path = tmp_path / "bindings.json"
    _write_json(bindings_path, {"fixture": "sorted-policy-membership"})
    monkeypatch.setattr(
        chunk_controller, "_verify_continuation_activity", lambda *_args: {
            "continuation_authority_sha256": "a" * 64,
            "owner_notification_sha256": "b" * 64,
        },
    )

    class SortedOrderRunner:
        class C1C2PhysicalError(RuntimeError):
            pass

        @staticmethod
        def authenticate_continuation_chain(*_args, **kwargs):
            assert set(kwargs["policy_bindings"]) == set(common.ARMS)
            return {
                "authority_sha256": "a" * 64,
                "owner_notification_sha256": "b" * 64,
            }

    result = chunk_controller._authenticate_continuation(
        argparse.Namespace(
            continuation_authority=tmp_path / "authority.json",
            owner_notification_marker=tmp_path / "owner.json",
            continuation_activity=tmp_path / "activity.json",
            bindings=bindings_path,
            resume_continuation=False,
        ),
        {"stage_c_output_root": str(root)},
        SortedOrderRunner,
    )
    assert result["authority_sha256"] == "a" * 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", None),
        ("notification_sent_utc", "2026-09-08garbageZ"),
        ("recorded_by", None),
    ],
)
def test_complete_q1_marker_contract_refuses_schema_time_and_controller(
    tmp_path: Path, field: str, value: object,
) -> None:
    digest = "a" * 64
    marker_payload = {
        "schema": common.SCHEMA_OWNER_CLOSURE_DECISION,
        "formal": True,
        "decision": "DECLINE_CONTINUATION",
        "owner_reply_verbatim": "I explicitly decline continuation and request closure.",
        "notification_sent_utc": "2026-09-08T01:00:00Z",
        "owner_reply_received_utc": "2026-09-08T01:01:00Z",
        "notification_channel": "controller-chat",
        "recorded_by": "controller-test",
        "bindings_sha256": digest,
        "plan_sha256": common.PLAN_SHA256,
        "policy_bindings_sha256": digest,
        "admission_mapping_sha256": digest,
        "result_3000_sha256": digest,
        "held_terminal_token_sha256": closure_sealer.HELD_TOKEN_SHA256,
        "checkpoint_3000_sha256": digest,
    }
    if value is None:
        marker_payload.pop(field)
    else:
        marker_payload[field] = value
    marker = tmp_path / "owner-decision.json"
    _write_json(marker, marker_payload)
    common.write_digest_sidecar(marker)
    with pytest.raises(common.StageCError, match="marker|RFC-3339"):
        closure_sealer._authenticate_decision_marker(
            marker,
            bindings_sha256=digest,
            plan_sha256=common.PLAN_SHA256,
            policy_bindings_sha256=digest,
            admission_mapping_sha256=digest,
            result_sha256=digest,
            checkpoint_sha256=digest,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("overall_token", verifier.HELD),
        ("reasons", []),
        ("terminal_boundary", 8999),
        ("q3_evaluated", True),
        ("test_split_opened", True),
        ("episode_training", True),
        ("learner_update", True),
        ("claim_ceiling", "C3_EFFICACY"),
    ],
)
def test_9000_continuation_semantic_mutations_are_refused(
    field: str, value: object,
) -> None:
    continuation = {
        "schema": verifier.CONTINUATION_RESULT_SCHEMA,
        "completed_episode": 9000,
        "terminal_boundary": 9000,
        "scientific_disposition_emitted": False,
        "q3_evaluated": False,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "claim_ceiling": common.FORMAL_CLAIM,
    }
    continuation[field] = value
    with pytest.raises(common.StageCError, match="forbidden semantics"):
        verifier._verify_continuation_result_semantics(continuation)


def test_finished_continuation_in_external_chunk_root_blocks_closure(
    tmp_path: Path,
) -> None:
    reporting = tmp_path / "reporting"
    activity = reporting / "continuation/ACTIVITY-BASELINE-006000.json"
    external_chunk = tmp_path / "chunks/BASELINE-003000-003100"
    _write_json(external_chunk / "chunk-receipt.json", {"status": "COMPLETE_CHUNK"})
    _write_json(
        activity,
        {
            "schema": common.SCHEMA_CONTINUATION_ACTIVITY,
            "formal": True,
            "registered_chunk_roots": [str(external_chunk.resolve())],
        },
    )
    common.write_digest_sidecar(activity)
    with pytest.raises(common.StageCError, match="continuation activity marker|registry"):
        closure_sealer._refuse_continuation_evidence(
            reporting, tmp_path / "bindings.json"
        )


def test_stop_bearing_prefix_is_refused_before_continuation_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporting = tmp_path / "reporting"
    reporting.mkdir()
    bindings_path = tmp_path / "bindings.json"
    _write_json(bindings_path, {"fixture": "stop-prefix"})
    bindings = {"stage_c_output_root": str(reporting.resolve())}
    monkeypatch.setattr(common, "verify_bindings", lambda _path: dict(bindings))
    monkeypatch.setattr(
        common, "verify_stage_ab_supplement", lambda *_args: {"supplement_sha256": "a" * 64}
    )
    monkeypatch.setattr(common, "verify_acceptance_bundle", lambda *_args: {})
    monkeypatch.setattr(common, "materialize_stage_ab", lambda value, _supplement: value)
    monkeypatch.setattr(common, "verify_runtime_identity", lambda _bindings: None)

    class StopVerifier:
        HELD = verifier.HELD

        @staticmethod
        def verify_finished(*_args, **_kwargs):
            raise common.StageCError("root carrying a STOP token is not a scientific result")

    monkeypatch.setattr(controller, "_module", lambda _path: StopVerifier)
    with pytest.raises(common.StageCError, match="STOP token"):
        chunk_controller.register_continuation_activity(
            argparse.Namespace(
                bindings=bindings_path,
                admission_supplement=tmp_path / "supplement.json",
                acceptance_bundle=tmp_path / "acceptance.json",
                arm="BASELINE",
                barrier=6000,
                chunk_roots=[tmp_path / "chunks/BASELINE-003000-003100"],
                continuation_authority=tmp_path / "authority.json",
                owner_notification_marker=tmp_path / "owner.json",
            )
        )
    assert not (reporting / "continuation").exists()


def test_continuation_registration_binds_verified_prefix_and_external_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporting = tmp_path / "reporting"
    _write_json(reporting / "result.json", {"overall_token": verifier.HELD})
    _write_json(
        reporting / "checkpoints/checkpoint-003000.json", {"completed_episode": 3000}
    )
    bindings_path = tmp_path / "bindings.json"
    _write_json(bindings_path, {"fixture": "activity"})
    bindings = {"stage_c_output_root": str(reporting.resolve())}
    monkeypatch.setattr(common, "verify_bindings", lambda _path: dict(bindings))
    monkeypatch.setattr(
        common, "verify_stage_ab_supplement", lambda *_args: {"supplement_sha256": "a" * 64}
    )
    monkeypatch.setattr(common, "verify_acceptance_bundle", lambda *_args: {})
    monkeypatch.setattr(common, "materialize_stage_ab", lambda value, _supplement: value)
    monkeypatch.setattr(common, "verify_runtime_identity", lambda _bindings: None)

    class HeldVerifier:
        HELD = verifier.HELD

        @staticmethod
        def verify_finished(*_args, **_kwargs):
            return {"completed_episode": 3000, "overall_token": verifier.HELD}

    monkeypatch.setattr(controller, "_module", lambda _path: HeldVerifier)
    monkeypatch.setattr(
        chunk_controller,
        "_authenticate_continuation_without_activity",
        lambda *_args: {
            "authority_sha256": "b" * 64,
            "owner_notification_sha256": "c" * 64,
        },
    )
    chunk_roots = [
        tmp_path / "chunks/BASELINE-003000-003100",
        tmp_path / "chunks/BASELINE-003100-003200",
    ]
    registered = chunk_controller.register_continuation_activity(
        argparse.Namespace(
            bindings=bindings_path,
            admission_supplement=tmp_path / "supplement.json",
            acceptance_bundle=tmp_path / "acceptance.json",
            arm="BASELINE",
            barrier=6000,
            chunk_roots=chunk_roots,
            continuation_authority=tmp_path / "authority.json",
            owner_notification_marker=tmp_path / "owner.json",
        )
    )
    activity_path = Path(str(registered["activity_path"]))
    assert common.verify_named_sidecar(activity_path) == registered["activity_sha256"]
    prefix = registered["prefix_verification"]
    assert common.verify_named_sidecar(prefix["path"]) == prefix["sha256"]
    assert registered["registered_chunk_roots"] == [
        str(path.resolve()) for path in chunk_roots
    ]


def test_tree_seal_finalises_interruption_after_manifest_publication(
    tmp_path: Path,
) -> None:
    root = tmp_path / "partial-finalisation"
    _write_json(root / "continuation-result.json", {"completed_episode": 9000})
    relative = "continuation-result.json"
    manifest_raw = (
        f"{common.file_sha256(root / relative)}  {relative}\n".encode("ascii")
    )
    (root / common.TREE_MANIFEST_NAME).write_bytes(manifest_raw)
    manifest_before = (root / common.TREE_MANIFEST_NAME).read_bytes()
    manifest_sha = common.write_tree_seal(root)
    assert (root / common.TREE_MANIFEST_NAME).read_bytes() == manifest_before
    assert (root / common.COMPLETE_NAME).read_text(encoding="ascii") == (
        f"{manifest_sha}  {common.TREE_MANIFEST_NAME}\n"
    )
    assert common.verify_tree_seal(root) == manifest_sha


@pytest.mark.parametrize("interruption", ["after-checkpoint", "after-continuation-result"])
def test_merge_four_resume_continuation_recovers_both_publication_interruptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interruption: str,
) -> None:
    output = tmp_path / "reporting"
    policy_bindings = {arm: {"arm": arm} for arm in sorted(common.ARMS)}
    _write_json(
        output / "checkpoints/checkpoint-003000.json",
        {"policy_bindings": policy_bindings},
    )
    _write_json(output / "result.json", {"overall_token": verifier.HELD})
    interrupted_path = (
        output / "checkpoints/checkpoint-003100.json"
        if interruption == "after-checkpoint"
        else output / "continuation-result.json"
    )
    _write_json(interrupted_path, {"interruption": interruption})
    interrupted_bytes = interrupted_path.read_bytes()
    bindings_path = tmp_path / "bindings.json"
    _write_json(bindings_path, {"fixture": "resume-continuation"})
    bindings = {"stage_c_output_root": str(output.resolve())}
    mapping = {arm: {"policy_binding": {"arm": arm}} for arm in common.ARMS}
    mapping_path = tmp_path / "formal-admission.json"
    _write_json(mapping_path, {"admission_mapping": mapping})
    acceptance_path = tmp_path / "acceptance.json"
    _write_json(acceptance_path, {"fixture": "acceptance"})
    arm_roots = []
    for arm in common.ARMS:
        root = tmp_path / f"merged-{arm}"
        _write_json(root / "arm-merge.json", {"completed_episode": 9000})
        arm_roots.append(root)
    monkeypatch.setattr(common, "verify_bindings", lambda _path: dict(bindings))
    monkeypatch.setattr(
        common, "verify_stage_ab_supplement", lambda *_args: {"supplement_sha256": "a" * 64}
    )
    monkeypatch.setattr(common, "verify_acceptance_bundle", lambda *_args: {})
    monkeypatch.setattr(common, "materialize_stage_ab", lambda value, _supplement: value)
    monkeypatch.setattr(common, "verify_runtime_identity", lambda _bindings: None)
    monkeypatch.setattr(
        common, "verify_stage_c_admission_mapping", lambda value: dict(value)
    )
    monkeypatch.setattr(
        chunk_controller, "_verify_continuation_activity", lambda *_args: {
            "continuation_authority_sha256": "b" * 64,
            "owner_notification_sha256": "c" * 64,
        },
    )

    class RecoveryRunner:
        HELD = verifier.HELD

        class C1C2PhysicalError(RuntimeError):
            pass

        @staticmethod
        def authenticate_continuation_chain(*_args, **kwargs):
            assert kwargs["allow_published_continuation"] is True
            return {
                "authority_sha256": "b" * 64,
                "owner_notification_sha256": "c" * 64,
            }

        @staticmethod
        def merge_four_arm(*_args, **kwargs):
            assert kwargs["resume_continuation"] is True
            assert interrupted_path.read_bytes() == interrupted_bytes
            if interruption == "after-checkpoint":
                _write_json(output / "continuation-result.json", {"completed_episode": 9000})
            return {"completed_episode": 9000}

    class RecoveryVerifier:
        @staticmethod
        def verify_finished(*_args, **_kwargs):
            assert (output / "continuation-result.json").is_file()
            return {"completed_episode": 9000, "overall_token": verifier.HELD}

    monkeypatch.setattr(chunk_controller, "_runner", lambda: RecoveryRunner)
    monkeypatch.setattr(controller, "_module", lambda _path: RecoveryVerifier)
    result = chunk_controller.merge_four(
        argparse.Namespace(
            bindings=bindings_path,
            admission_supplement=tmp_path / "supplement.json",
            acceptance_bundle=acceptance_path,
            arm_roots=arm_roots,
            admission_mapping=mapping_path,
            output=output,
            continuation_authority=tmp_path / "authority.json",
            owner_notification_marker=tmp_path / "owner.json",
            continuation_activity=tmp_path / "activity.json",
            resume_continuation=True,
        )
    )
    assert result["completed_episode"] == 9000
    assert interrupted_path.read_bytes() == interrupted_bytes
    assert (output / common.COMPLETE_NAME).is_file()
