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
import build_stage_c_chunk_acceptance_bundle as acceptance_bundle_builder
import build_v023_c1c2_successor_stagec_manifest as manifest_builder
import build_v023_c1c2_successor_world_plan as plan_builder
import preflight_v023_c1c2_successor_stagec as preflight
import run_v023_c1c2_successor_stage_c as controller
import run_v023_c1c2_successor_stage_c_chunks as chunk_controller
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
        rung["pooled"]["total_bits"] += 1.0
        _write_json(rung_path, rung)
        return result

    monkeypatch.setattr(runner, "merge_arm_chunks", merge_then_mutate)
    with pytest.raises(
        common.StageCError, match=r"rungs\[100\]\.pooled\.total_bits"
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
    assert chunk_controller._parser().parse_args(
        [
            "run-chunk", "--bindings", "bindings.json",
            "--admission-supplement", "supplement.json",
            "--acceptance-bundle", "acceptance.json",
            "--runtime-admission", "runtime.json", "--arm", "BASELINE",
            "--start", "0", "--end", "100", "--chunk-root", "chunk",
        ]
    ).end == 100
