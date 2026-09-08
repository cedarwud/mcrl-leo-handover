from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import build_c3s_confirm_preflight as preflight
import build_c3s_confirm_world_plan as plan_builder
import c3s_full2_policy_adapter as adapter
import run_v023_c3s_confirmatory as runner


SHA = "1" * 64


class FakeFrozen:
    arm = "FULL2"

    def verify(self) -> None:
        return None

    def binding(self) -> dict[str, object]:
        return {
            "checkpoint_path": "/sealed/FULL2.pt", "checkpoint_sha256": "2" * 64,
            "q1_parameter_sha256": "3" * 64, "q2_parameter_sha256": "4" * 64,
            "update_count": 200, "routes": ["C1", "C2"],
        }


class FakeSnapshot:
    def __init__(self) -> None:
        self.base_actions = np.array([0, 1], dtype=np.int64)
        self.q_inference_seconds = 0.25

    def verify(self) -> str:
        return "stable-snapshot"


def test_adapter_disabled_is_full2_argmax_and_enabled_coordinates_every_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshots: list[object] = []

    def snapshot_inputs(_delegate: object, step_environment: object, observation: object):
        assert getattr(step_environment, "private_live_marker") == "must-not-reach-decision"
        assert observation == "observation"
        return FakeSnapshot(), SimpleNamespace(snapshot_only=True)

    def coordinated(snapshot: object, evaluator: object):
        assert isinstance(snapshot, FakeSnapshot)
        assert vars(evaluator) == {"snapshot_only": True}
        snapshots.append(snapshot)
        return adapter.c3s_policy.DecisionResult(
            actions=np.array([1, 0], dtype=np.int64),
            base_actions=np.array([0, 1], dtype=np.int64),
            profile_id="U:0:1", catalog_size=2,
            counts={"base": 1, "unilateral": 1, "joint": 0},
            nominal={}, phase_wall_seconds={}, unique_nominal_evaluations=2,
        )

    monkeypatch.setattr(adapter.c3s_policy, "_snapshot_inputs", snapshot_inputs)
    monkeypatch.setattr(adapter.c3s_policy, "_real_decision", coordinated)
    disabled = adapter.C3SFull2PolicyAdapter(
        frozen_full2=FakeFrozen(), coordinator_enabled=False, catalog="lite",
    )
    enabled = adapter.C3SFull2PolicyAdapter(
        frozen_full2=FakeFrozen(), coordinator_enabled=True, catalog="lite",
    )
    step = SimpleNamespace(private_live_marker="must-not-reach-decision")
    rng = np.random.default_rng(5)
    assert disabled.select_actions(step, "observation", rng).tolist() == [0, 1]
    assert enabled.select_actions(step, "observation", rng).tolist() == [1, 0]
    assert enabled.select_actions(step, "observation", rng).tolist() == [1, 0]
    assert len(snapshots) == 2
    assert disabled.binding()["proposal_rule"].startswith("FLOAT32_UNWEIGHTED_MASKED")


def episode(arm: str, index: int, *, bits: float = 100.0, energy: float = 10.0, served: int = 1000) -> dict[str, object]:
    domain = f"C3S_CONFIRM/world/{index}"
    return {
        "schema": f"{runner.SCHEMA}-episode-receipt", "status": "COMPLETE",
        "arm": arm, "episode_index": index,
        "world_id": f"c3s-confirm-world-{index:06d}",
        "world_domain": domain, "world_seed": plan_builder.derive_seed(domain),
        "field_root_digest": SHA, "initial_state_sha256": SHA,
        "policy_binding_sha256": ("2" if arm == "FULL2" else "3") * 64,
        "total_bits": bits, "total_energy_j": energy,
        "served_user_steps": served, "service_opportunities": 1000,
        "action_trace_sha256": SHA, "plan_sha256": "4" * 64,
    }


def make_chunk(root: Path, arm: str, start: int, *, bits: float) -> Path:
    rows = [episode(arm, index, bits=bits) for index in range(start + 1, start + 101)]
    boundaries = []
    for boundary in (start, start + 100):
        value = {
            "schema": f"{runner.SCHEMA}-boundary-state", "arm": arm,
            "episode_index": boundary, "synthetic_state": boundary,
        }
        value["boundary_state_sha256"] = runner.canonical_sha256(value)
        boundaries.append(value)
    runner.write_once(root / "boundary-start.json", boundaries[0])
    runner.write_once(root / "boundary-end.json", boundaries[1])
    for row in rows:
        runner.write_once(root / "episodes" / f"episode-{row['episode_index']:06d}.json", row)
    runner.write_once(root / "chunk-receipt.json", {
        "schema": f"{runner.SCHEMA}-chunk-receipt", "status": "COMPLETE",
        "arm": arm, "chunk_id": f"{arm}-{start:06d}-{start + 100:06d}",
        "start_boundary": start, "end_boundary": start + 100,
        "start_boundary_state_sha256": boundaries[0]["boundary_state_sha256"],
        "end_boundary_state_sha256": boundaries[1]["boundary_state_sha256"],
        "ordered_episode_digest": runner.canonical_sha256(rows),
        "authority_sha256": "6" * 64,
    })
    return root


def test_chunk_arm_merge_and_two_arm_rung_have_no_early_token(tmp_path: Path) -> None:
    arm_roots: dict[str, Path] = {}
    for arm, bits in (("FULL2", 100.0), ("FULL2+C3-S", 101.0)):
        chunk = make_chunk(tmp_path / "chunks" / arm, arm, 0, bits=bits)
        merged = tmp_path / "arm-merges" / arm
        result = runner.merge_arm_chunks(arm, [chunk], merged)
        assert result["completed_episode"] == 100
        assert (merged / "checkpoints/checkpoint-000100.json").is_file()
        assert (merged / "rungs/rung-000100.json").is_file()
        assert not (merged / "rungs/rung-000200.json").exists()
        arm_roots[arm] = merged
    combined = runner.merge_two_arms(arm_roots, tmp_path / "combined")
    assert combined["overall_token"] is None
    assert combined["scientific_disposition_emitted"] is False
    assert not (tmp_path / "combined/result.json").exists()


@pytest.mark.parametrize(
    ("c3s_ee", "c3s_served", "token", "reasons"),
    [
        (10.0001, 2_997_000, runner.HELD, []),
        (10.0, 2_997_000, runner.FALSIFIED, ["EE_NOT_STRICTLY_ABOVE_FULL2"]),
        (10.0001, 2_996_999, runner.FALSIFIED, ["SERVICE_MARGIN_FAILED"]),
        (9.9, 2_996_999, runner.FALSIFIED, ["EE_NOT_STRICTLY_ABOVE_FULL2", "SERVICE_MARGIN_FAILED"]),
    ],
)
def test_terminal_token_is_strict_ratio_and_exact_service_margin(
    c3s_ee: float, c3s_served: int, token: str, reasons: list[str],
) -> None:
    pooled = {
        "FULL2": {
            "episodes": 3000, "ee_bits_per_j": 10.0,
            "served_user_steps": 3_000_000, "service_opportunities": 3_000_000,
        },
        "FULL2+C3-S": {
            "episodes": 3000, "ee_bits_per_j": c3s_ee,
            "served_user_steps": c3s_served, "service_opportunities": 3_000_000,
        },
    }
    result = runner.adjudicate(pooled, completed_episodes=3000)
    assert result == {
        "scientific_disposition_emitted": True,
        "overall_token": token,
        "reasons": reasons,
    }


def test_unsealed_contract_and_other_worlds_are_refused(tmp_path: Path) -> None:
    unsealed = tmp_path / "PLAN.md"
    unsealed.write_text("draft", encoding="ascii")
    with pytest.raises(runner.ConfirmatoryError, match="sealed file"):
        runner.validate_sealed_file(unsealed)
    wrong = episode("FULL2", 1)
    wrong["world_id"] = "world-000001"
    with pytest.raises(runner.ConfirmatoryError, match="identity"):
        runner.validate_episode(wrong)


def test_world_builder_refuses_allocated_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    original = plan_builder.derive_seed

    def collide(domain: str) -> int:
        if domain == "C3S_CONFIRM/world/1":
            return 2026090601
        return original(domain)

    monkeypatch.setattr(plan_builder, "derive_seed", collide)
    with pytest.raises(plan_builder.WorldPlanError, match="allocated seed collision"):
        plan_builder.build_world_plan(3000)


def test_write_once_is_immutable_and_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    digest = runner.write_once(target, {"value": 1})
    assert runner.file_sha256(target) == digest
    assert target.stat().st_mode & 0o777 == 0o444
    assert Path(f"{target}.sha256").stat().st_mode & 0o777 == 0o444
    with pytest.raises(runner.ConfirmatoryError, match="overwrite"):
        runner.write_once(target, {"value": 2})


def test_boundary_replay_imports_stage_c_body() -> None:
    worlds = [
        {
            "episode_index": index, "world_id": f"c3s-confirm-world-{index:06d}",
            "world_seed": index + 99, "field_root_digest": SHA,
        }
        for index in range(1, 101)
    ]
    plan = {"worlds": worlds, "plan_sha256": "4" * 64}
    table = runner.boundary_table(
        plan=plan, arm="FULL2", policy_binding={"arm": "FULL2"},
        boundaries=(0, 100),
        rng_factory=lambda seed: tuple(
            np.random.default_rng(child) for child in np.random.SeedSequence(seed).spawn(2)
        ),
    )
    assert table[100]["source_builder"]["path"] == str(runner.BOUNDARY_DONOR.resolve())
    assert table[100]["source_stage_c_boundary"]["draw_replay"]["draws_replayed"] == 100


def test_stage_c_equivalence_exclusions_are_imported() -> None:
    left = {"value": 1.0, "started_utc": "a"}
    right = {"value": 1.0, "started_utc": "b"}
    runner.acceptance_comparison(left, right, artifact="receipt")
    assert "started_utc" in runner._equivalence_exclusions()
    with pytest.raises(Exception, match="bitwise chunk equivalence"):
        runner.acceptance_comparison({"value": 1.0}, {"value": np.nextafter(1.0, 2.0)}, artifact="receipt")


def test_acceptance_receipt_requires_200_vs_two_100(tmp_path: Path) -> None:
    direct = [episode("FULL2", index) for index in range(1, 201)]
    for index, row in enumerate(direct, 1):
        domain = f"C3S_CONFIRM_ACCEPT/world/{index}"
        row["world_domain"] = domain
        row["world_id"] = f"c3s-confirm-accept-world-{index:06d}"
        row["world_seed"] = plan_builder.derive_seed(domain)
    boundaries = {0: {"state": 0}, 100: {"state": 100}, 200: {"state": 200}}
    receipt = runner.build_acceptance_receipt(
        arm="FULL2", direct_rows=direct,
        first_chunk_rows=direct[:100], second_chunk_rows=direct[100:],
        direct_boundary_states=boundaries, chunk_boundary_states=boundaries,
        preflight_sha256="5" * 64, output=tmp_path / "ACCEPTANCE.json",
    )
    assert receipt["status"] == "PASS_BITWISE_CHUNK_EQUIVALENCE"
    assert receipt["chunks"] == [[1, 100], [101, 200]]
    with pytest.raises(runner.ConfirmatoryError, match="exactly 2x100"):
        runner.build_acceptance_receipt(
            arm="FULL2", direct_rows=direct[:-1],
            first_chunk_rows=direct[:100], second_chunk_rows=direct[100:],
            direct_boundary_states=boundaries, chunk_boundary_states=boundaries,
            preflight_sha256="5" * 64, output=tmp_path / "NO.json",
        )


def test_progression_rule_selects_lite_then_only_supported_full() -> None:
    common = {
        "status": "COMPLETE", "outcome": "C3S_THREE_ARM_SCREEN_COMPLETE", "integrity": True,
    }
    assert preflight.selected_catalog({
        **common, "decisions": {
            "FULL": {"outcome": "C3S_FULL_SCREEN_SUPPORT"},
            "LITE": {"outcome": "C3S_LITE_SCREEN_SUPPORT"},
        },
    }) == "lite"
    assert preflight.selected_catalog({
        **common, "decisions": {
            "FULL": {"outcome": "C3S_FULL_SCREEN_SUPPORT"},
            "LITE": {"outcome": "C3S_LITE_SCREEN_NO_SUPPORT"},
        },
    }) == "full"
    with pytest.raises(runner.ConfirmatoryError, match="progression is closed"):
        preflight.selected_catalog({
            **common, "decisions": {
                "FULL": {"outcome": "C3S_FULL_SCREEN_NO_SUPPORT"},
                "LITE": {"outcome": "C3S_LITE_SCREEN_NO_SUPPORT"},
            },
        })


def test_ladder_constants_and_dry_run() -> None:
    assert runner.RUNG_BOUNDARIES == (100, 500, 1500, 3000)
    assert "execution=NOT_STARTED" in runner.dry_run("lite")
