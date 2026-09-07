from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

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
import build_v023_c1c2_successor_stagec_manifest as manifest_builder
import build_v023_c1c2_successor_world_plan as plan_builder
import preflight_v023_c1c2_successor_stagec as preflight
import run_v023_c1c2_successor_stage_c as controller
import stagec_common as common
import verify_v023_c1c2_successor_stagec as verifier
import v023_c1c2_successor_physical_runner as runner


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(common.canonical_bytes(value))


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
    runner.FixedPolicyEvaluationRunner(adapter=_ProducerFixtureAdapter(), plan=plan).run(output_dir=root, pause_at=100)
    return root, payload


def test_independent_verifier_accepts_runner_written_synthetic_rung(runner_written_rung) -> None:
    root, plan = runner_written_rung
    checkpoint = verifier._read_checkpoint(root / "checkpoints/checkpoint-000100.json")
    pooled = verifier.verify_episode_rows(checkpoint["receipts"], plan, 100)
    assert pooled["FULL2"]["ratio_of_sums_ee_bits_per_j"] > pooled["BASELINE"]["ratio_of_sums_ee_bits_per_j"]


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
    with pytest.raises(common.StageCError, match="owner-notification"):
        controller._continuation(
            runner=runner, evaluation=object(), output=output,
            checkpoint=tmp_path / "checkpoint.json", authority=authority,
            owner_marker=tmp_path / "missing-owner.json", bindings_sha="a" * 64,
        )


def test_9000_authority_authenticates_literal_owner_reply_and_result(tmp_path: Path) -> None:
    result = tmp_path / "result.json"
    _write_json(result, {"overall_token": runner.HELD, "completed_episode": 3000})
    bindings_sha = "a" * 64
    acknowledgement = "I acknowledge and authorize the 9000-world continuation."
    marker = tmp_path / "owner-notification.json"
    _write_json(
        marker,
        {
            "formal": True,
            "status": "OWNER_NOTIFIED_FOR_9000_CONTINUATION",
            "owner_acknowledgement": acknowledgement,
            "result_3000_sha256": common.file_sha256(result),
            "bindings_sha256": bindings_sha,
            "plan_sha256": common.PLAN_SHA256,
        },
    )
    authority = tmp_path / "authority.json"
    _write_json(
        authority,
        {
            "formal": True,
            "owner_notification_sha256": common.file_sha256(marker),
            "owner_acknowledgement_sha256": hashlib.sha256(acknowledgement.encode("utf-8")).hexdigest(),
            "bindings_sha256": bindings_sha,
            "plan_sha256": common.PLAN_SHA256,
        },
    )
    common.write_digest_sidecar(authority)
    authenticated = controller._authenticate_continuation_authority(
        result_path=result, authority=authority, owner_marker=marker, bindings_sha=bindings_sha,
    )
    assert authenticated[1] == common.file_sha256(marker)
    assert authenticated[2] == hashlib.sha256(acknowledgement.encode("utf-8")).hexdigest()
    _write_json(marker.with_name("wrong-marker.json"), {"formal": True})
    with pytest.raises(common.StageCError, match="owner-notification"):
        controller._authenticate_continuation_authority(
            result_path=result, authority=authority,
            owner_marker=marker.with_name("wrong-marker.json"), bindings_sha=bindings_sha,
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


def test_baseline_dependency_fails_closed_until_postfix_assertion_exists() -> None:
    module = importlib.import_module("baseline_adapter")
    if getattr(module, "CONTRACT_FIELDS_EXCLUDED", None) is True:
        pytest.skip("workspace already contains the required post-fix adapter")
    with pytest.raises(common.StageCError, match="contract_fields_excluded"):
        binder.bind_baseline(common.BASELINE_CHECKPOINT, common.BASELINE_STATUS)


def test_dry_run_prints_commands_without_remote_execution() -> None:
    launcher = HERE / "sync_launch_v023_c1c2_successor_stagec_server.sh"
    syntax = subprocess.run(["bash", "-n", str(launcher)], capture_output=True, text=True, check=False)
    assert syntax.returncode == 0, syntax.stderr
    environment = dict(os.environ)
    environment.pop("V023_STAGEC_PYTHON", None)
    completed = subprocess.run(
        [str(launcher), "--dry-run"], cwd=REPO, env=environment,
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ssh sat test -d" in completed.stdout
    assert "rsync -aR --files-from=" in completed.stdout
    assert "tmux new-session" in completed.stdout
    assert "wait-up-to-120s" in completed.stdout
    assert "LOG_PATH=" in completed.stdout
