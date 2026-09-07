from __future__ import annotations

from dataclasses import replace
from collections.abc import Mapping
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_real_five_arm_episode_runner.py"
SPEC = importlib.util.spec_from_file_location("v023_real_five_arm_episode_runner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)
binding = runner._binding
results = runner._results


def _common() -> dict[str, object]:
    worlds = ["source-world-a", "source-world-b"]
    seeds = [101, 202]
    return {
        "split": "TRAIN_DEVELOPMENT",
        "world_ids": worlds,
        "training_seeds": seeds,
        "world_sha256": binding.canonical_sha256({"world_ids": worlds}),
        "seed_sha256": binding.canonical_sha256({"training_seeds": seeds}),
    }


def _route(route: str, mode: str, digit: str, *, common: dict[str, object]) -> dict[str, object]:
    initializations = [f"{route.lower()}-{index}" for index in range(3)]
    return {
        "route": route,
        "mode": mode,
        "source_sha256": digit * 64,
        "source_rule": f"{route.lower()}-{mode.lower()}",
        "row_budget": 12,
        "learner_initialization_ids": initializations,
        "learner_initialization_count": len(initializations),
        "learner_initialization_sha256": binding.canonical_sha256(
            {"learner_initialization_ids": initializations}
        ),
        "learner_config_sha256": {"C1": "a", "C2": "b", "C3": "c"}[route] * 64,
        "learner_update_count": {"C1": 10, "C2": 3000, "C3": 2000}[route],
        "source_identity": f"{route}-{mode}-{digit}",
        "common": common,
    }


def _source_plan(policy_hashes: dict[str, str]) -> dict[str, object]:
    common = _common()
    c1_i = _route("C1", "INFORMED", "1", common=common)
    c1_n = _route("C1", "CLUSTER_MATCHED_NEUTRAL", "2", common=common)
    c2_i = _route("C2", "INFORMED", "3", common=common)
    c2_n = _route("C2", "EQUAL_BUDGET_NEUTRAL", "4", common=common)
    c3_i = _route("C3", "INFORMED", "5", common=common)
    c3_n = _route("C3", "MATCHED_PLACEBO_NEUTRAL", "6", common=common)
    arms: list[dict[str, object]] = [
        {"arm": "FULL", "routes": [c1_i, c2_i, c3_i], "baseline": None, "ablation_mode": binding.SOURCE_ABLATION},
        {
            "arm": "BASELINE",
            "routes": [],
            "baseline": {
                "policy_id": "pre-catfish-modqn-main",
                "policy_sha256": policy_hashes["BASELINE"],
                "authentication_sha256": "e" * 64,
                "source_kind": binding.BASELINE_SOURCE_KIND,
                "source_identity": "fixture-pre-catfish",
            },
            "ablation_mode": None,
        },
        {"arm": "DROP_C1", "routes": [c1_n, c2_i, c3_i], "baseline": None, "ablation_mode": binding.SOURCE_ABLATION},
        {"arm": "DROP_C2", "routes": [c1_i, c2_n, c3_i], "baseline": None, "ablation_mode": binding.SOURCE_ABLATION},
        {"arm": "DROP_C3", "routes": [c1_i, c2_i, c3_n], "baseline": None, "ablation_mode": binding.SOURCE_ABLATION},
    ]
    payload: dict[str, object] = {
        "schema": binding.SOURCE_PLAN_SCHEMA,
        "schema_version": 2,
        "ablation_mode": binding.SOURCE_ABLATION,
        "common": common,
        "arms": arms,
    }
    payload["plan_sha256"] = binding.canonical_sha256(payload)
    return payload


def _make_request(tmp_path: Path, *, episodes: int = 100, with_gate: bool = True) -> runner.V023RealFiveArmRequest:
    policy_paths: dict[str, Path] = {}
    policy_hashes: dict[str, str] = {}
    for index, arm in enumerate(runner.ARMS):
        path = tmp_path / f"{arm.lower()}.pt"
        path.write_bytes(f"fixture-policy-{index}".encode("ascii"))
        policy_paths[arm] = path
        policy_hashes[arm] = runner.file_sha256(path)
    plan = _source_plan(policy_hashes)
    source_plan_path = tmp_path / "source-plan.json"
    source_plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="ascii")
    worlds = tuple(
        binding.EvaluationWorldBinding(
            episode_index=index,
            world_id=f"world-{index:06d}",
            world_seed=2026091000 + index,
            field_root_digest=f"{(index % 15) + 1:x}" * 64,
        )
        for index in range(1, episodes + 1)
    )
    policies = tuple(
        binding.FrozenPolicyBinding(
            arm=arm,
            policy_id=f"policy-{arm.lower()}",
            policy_family=("AUTHENTICATED_PRE_CATFISH_MODQN" if arm == "BASELINE" else "MULTI_CATFISH_MCRL_V023"),
            checkpoint_sha256=policy_hashes[arm],
            authentication_sha256=f"{index + 8:x}" * 64,
            source_plan_sha256=plan["plan_sha256"],
            source_arm_sha256=binding.canonical_sha256(next(row for row in plan["arms"] if row["arm"] == arm)),
        )
        for index, arm in enumerate(runner.ARMS)
    )
    evaluation_binding = binding.bind_five_arm_evaluation(
        source_plan=plan,
        policies=policies,
        worlds=worlds,
        evaluation_contract_sha256="f" * 64,
    )
    tle = tmp_path / "tle.tle"
    tle.write_text("fixture TRAIN TLE archive\n", encoding="ascii")
    q12 = Path(
        ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt"
    ).resolve()
    c3 = tmp_path / "c3-target.npz"
    c3.write_bytes(b"fixture-current-v023-c3-target")
    gate: runner.ArtifactBinding | None = None
    if with_gate:
        gate_path = tmp_path / "gate-admission.json"
        gate_payload = {
            "schema": "fixture-v023-episode-admission-v1",
            "sealed": True,
            "gate_contract_sha256": runner.CURRENT_GATE_CONTRACT_SHA256,
            "episode_screen_authorized": True,
            "split": "TRAIN_DEVELOPMENT",
            "episode_count": episodes,
            "checkpoint_every": 100,
            "evaluation_binding_sha256": evaluation_binding.verify(),
            "source_plan_sha256": plan["plan_sha256"],
            "q12_checkpoint_sha256": runner.CURRENT_Q12_CHECKPOINT_SHA256,
            "c3_view_schema_sha256": runner.CURRENT_C3_VIEW_SCHEMA_SHA256,
            "c3_view_config_sha256": runner.CURRENT_C3_VIEW_CONFIG_SHA256,
            "c3_target_sha256": runner.file_sha256(c3),
            "evaluation_contract_sha256": "f" * 64,
        }
        gate_path.write_text(json.dumps(gate_payload, sort_keys=True), encoding="ascii")
        gate = runner.ArtifactBinding("sealed_gate_admission", gate_path, runner.file_sha256(gate_path))
    return runner.V023RealFiveArmRequest(
        screen_id=f"fixture-real-five-arm-{episodes}",
        binding=evaluation_binding,
        source_plan_artifact=runner.ArtifactBinding("source_plan", source_plan_path, runner.file_sha256(source_plan_path)),
        tle_archive=runner.ArtifactBinding("tle_archive", tle, runner.file_sha256(tle)),
        q12_checkpoint=runner.ArtifactBinding("q12_checkpoint", q12, runner.file_sha256(q12)),
        c3_target_artifact=runner.ArtifactBinding("c3_target_artifact", c3, runner.file_sha256(c3)),
        policy_artifacts={arm: runner.ArtifactBinding(f"policy_artifacts.{arm}", policy_paths[arm], policy_hashes[arm]) for arm in runner.ARMS},
        sealed_gate_admission=gate,
        episode_count=episodes,
    )


class _FixtureRealTleAdapter:
    identity = runner.TEST_FIXTURE_ADAPTER_IDENTITY
    is_test_fixture = True

    def __init__(self) -> None:
        self.states: dict[str, Mapping[str, object] | None] = {arm: None for arm in runner.ARMS}

    def resume_state_for(self, arm: str) -> Mapping[str, object] | None:
        return self.states[arm]

    def restore_resume_states(self, states: Mapping[str, object]) -> None:
        self.states = {arm: states.get(arm) for arm in runner.ARMS}

    def run_episode(self, *, arm: str, world: Any, policy: Any, resume_state: Mapping[str, object] | None) -> Any:
        previous = self.states[arm]
        if world.episode_index == 1:
            assert resume_state is None
        else:
            assert isinstance(resume_state, Mapping)
            assert resume_state["episode_index"] == world.episode_index - 1
            assert previous == resume_state
        self.states[arm] = {"arm": arm, "episode_index": world.episode_index}
        bits = float(1_000_000 + world.episode_index * 100 + len(arm))
        energy = float(10 + world.episode_index / 100)
        served = 900 + (world.episode_index % 10)
        return results.FiveArmEpisodeReceipt(
            schema=results.RECEIPT_SCHEMA,
            arm=arm,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            field_root_digest=world.field_root_digest,
            initial_world_sha256=runner.canonical_sha256({"world": world.world_id}),
            policy_checkpoint_sha256=policy.checkpoint_sha256,
            source_arm_sha256=policy.source_arm_sha256,
            evaluation_binding_sha256=self._binding_sha256,
            action_trace_sha256=runner.canonical_sha256({"arm": arm, "episode": world.episode_index}),
            total_bits=bits,
            total_energy_j=energy,
            ratio_of_sums_ee_bits_per_j=bits / energy,
            served_user_steps=served,
            service_opportunities=1000,
            service_fraction=served / 1000,
        )

    @property
    def _binding_sha256(self) -> str:
        # Set by the test after admission is built; this avoids importing a
        # scientific value or computing any result-dependent binding.
        return self.binding_sha256


def _wired_adapter(request: runner.V023RealFiveArmRequest) -> _FixtureRealTleAdapter:
    adapter = _FixtureRealTleAdapter()
    adapter.binding_sha256 = request.binding.verify()  # type: ignore[attr-defined]
    return adapter


def test_preflight_reports_all_missing_current_artifacts(tmp_path: Path) -> None:
    request = _make_request(tmp_path, with_gate=False)
    with pytest.raises(runner.V023RealFiveArmAdmissionError) as error:
        request.admit()
    message = str(error.value)
    assert "sealed_gate_admission" in message
    assert "execution-NO-GO" in message


def test_real_runner_rejects_legacy_or_synthetic_adapter(tmp_path: Path) -> None:
    request = _make_request(tmp_path)
    adapter = _wired_adapter(request)
    adapter.identity = "synthetic-deterministic-adapter-v1"  # type: ignore[misc]
    with pytest.raises(runner.V023RealFiveArmError, match="synthetic/legacy"):
        runner.V023RealFiveArmEpisodeRunner(request=request, adapter=adapter, allow_test_fixture=True)


def test_real_fixture_executes_exact_five_arms_and_writes_checkpoint(tmp_path: Path) -> None:
    request = _make_request(tmp_path, episodes=100)
    adapter = _wired_adapter(request)
    output = tmp_path / "run"
    result = runner.V023RealFiveArmEpisodeRunner(
        request=request,
        adapter=adapter,
        allow_test_fixture=True,
    ).run(output_dir=output)
    assert result["status"] == "COMPLETE_UNADJUDICATED"
    assert result["completed_episode"] == 100
    assert (output / "checkpoints/checkpoint-000100.json").is_file()
    assert (output / "receipts.json").is_file()
    assert (output / "result.json").is_file()
    assert result["scientific_decision"] is None
    evaluation = result["evaluation"]
    assert evaluation["pooled_by_arm"]["FULL"]["episodes"] == 100


def test_real_fixture_resume_from_100_checkpoint_to_500_is_admitted(tmp_path: Path) -> None:
    request = _make_request(tmp_path, episodes=500)
    first_adapter = _wired_adapter(request)
    output = tmp_path / "resumed-run"
    paused = runner.V023RealFiveArmEpisodeRunner(
        request=request,
        adapter=first_adapter,
        allow_test_fixture=True,
    ).run(output_dir=output, stop_after=100)
    checkpoint = output / "checkpoints/checkpoint-000100.json"
    assert paused["completed_episode"] == 100
    second_adapter = _wired_adapter(request)
    result = runner.V023RealFiveArmEpisodeRunner(
        request=request,
        adapter=second_adapter,
        allow_test_fixture=True,
    ).run(output_dir=output, resume_checkpoint=checkpoint)
    assert result["completed_episode"] == 500
    assert (output / "checkpoints/checkpoint-000500.json").is_file()


def test_only_100_or_500_episode_budgets_are_admitted(tmp_path: Path) -> None:
    request = _make_request(tmp_path, episodes=100)
    bad = replace(request, episode_count=1500)
    with pytest.raises(runner.V023RealFiveArmAdmissionError, match="100 or 500"):
        bad.admit()


def test_manifest_loader_preserves_explicit_binding_and_artifact_paths(tmp_path: Path) -> None:
    request = _make_request(tmp_path, episodes=100)
    manifest = {
        "schema": runner.MANIFEST_SCHEMA,
        "screen_id": request.screen_id,
        "episode_count": request.episode_count,
        "split": request.split,
        "checkpoint_every": request.checkpoint_every,
        "evaluation_binding": {
            "schema": request.binding.schema,
            "split": request.binding.split,
            "source_plan": request.binding.source_plan,
            "evaluation_contract_sha256": request.binding.evaluation_contract_sha256,
            "checkpoint_every": request.binding.checkpoint_every,
            "policies": [policy.to_dict() for policy in request.binding.policies],
            "worlds": [world.to_dict() for world in request.binding.worlds],
        },
        "artifacts": {
            "source_plan": request.source_plan_artifact.to_dict(base=tmp_path),
            "tle_archive": request.tle_archive.to_dict(base=tmp_path),
            "q12_checkpoint": request.q12_checkpoint.to_dict(base=tmp_path),
            "c3_target_artifact": request.c3_target_artifact.to_dict(base=tmp_path),
            "policies": {
                arm: request.policy_artifacts[arm].to_dict(base=tmp_path)
                for arm in runner.ARMS
            },
            "sealed_gate_admission": request.sealed_gate_admission.to_dict(base=tmp_path),
        },
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="ascii")
    loaded = runner.load_request_manifest(path)
    assert loaded.admit().run_fingerprint == request.admit().run_fingerprint
