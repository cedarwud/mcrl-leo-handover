"""W-96 -- bounded C2 parallel-screen contract.

These tests exercise only the fail-closed protocol helpers.  They do not open
the Phase-B server artifact, load a simulator/TLE archive, train Q2, or run a
DESIGN-EVAL episode.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v04_c2_parallel_screen_runner",
    REPO / ".scratch/c3-v04/run_v04_c2_parallel_screen.py",
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _sha(label: str) -> str:
    return runner.canonical_sha256({"label": label})


def _field() -> SimpleNamespace:
    return SimpleNamespace(root_digest="b" * 64)


def _row(
    *,
    candidate_id: str,
    update: int,
    world: int,
    policy: str,
    initialization_seed: int | None,
    bits: float,
    energy: float = 1.0,
    actions_value: int = 0,
) -> dict[str, object]:
    actions = [[actions_value for _ in range(runner.USERS)] for _ in range(runner.STEPS_PER_EPISODE)]
    phase_b_sha = "a" * 64
    return runner._episode_row(
        candidate_id=candidate_id,
        checkpoint_update=update,
        policy_label=policy,
        initialization_seed=initialization_seed,
        evaluation_seed=world,
        phase_b_sha256=phase_b_sha,
        field=_field(),
        start_epoch="2026-09-01T00:00:00+00:00",
        initial_world_sha256=_sha(f"world-{world}"),
        initial_state_sha256=_sha(f"state-{world}"),
        initial_mask_sha256=_sha(f"mask-{world}"),
        actions=actions,
        total_bits=bits,
        total_energy_j=energy,
        served_user_steps=runner.USERS * runner.STEPS_PER_EPISODE,
        q2_magnitude_samples=(1.0,) if policy != "MAIN" else (),
        q13_magnitude_samples=(2.0,) if policy == "FULL" else (),
    )


def test_frozen_screen_budget_and_field_namespace() -> None:
    assert runner.DESIGN_EVAL_SEEDS == tuple(range(2026092901, 2026092911))
    assert runner.FIELD_COMPONENT == "V04_C2_PARALLEL_SCREEN_V1"
    assert runner.UPDATE_LADDER == (100, 500, 1500)
    assert runner.CHECKPOINT_UPDATES == tuple(range(100, 1501, 100))
    assert runner.expected_design_eval_episodes(3) == 310
    assert runner.expected_design_eval_episodes(1) == 130
    assert runner.expected_design_eval_episodes(1, target_update=100) == 70
    assert runner.expected_design_eval_episodes(1, target_update=500) == 100
    assert runner._rung_updates(100) == (100,)
    assert runner._rung_updates(500) == (100, 500)
    assert runner._checkpoint_updates_for(500) == (100, 200, 300, 400, 500)


def test_staged_rung_receipts_and_cli_are_explicit() -> None:
    result_path, seal_path = runner._arm_receipt_paths(Path("/tmp/c2-arm"), 500)
    assert result_path.name == "arm-000500-result.json"
    assert seal_path.name == "arm-000500-seal.json"
    arm_args = runner._arguments(
        [
            "arm",
            "--candidate-id",
            runner.C2_Q13_VALUE,
            "--initialization-seed",
            str(runner.INITIALIZATION_SEEDS[0]),
            "--target-update",
            "500",
            "--output-dir",
            "/tmp/c2-arm",
        ]
    )
    assert arm_args.target_update == 500
    merge_args = runner._arguments(["merge", "--target-update", "100"])
    assert merge_args.target_update == 100
    with pytest.raises(runner.C2ParallelScreenError):
        runner._target_update(200)


def test_q13_targets_allow_expired_phase_a_support_but_p0_rejects() -> None:
    expired_phase_a = {
        "row_status": "support-expired",
        "zeta2_temporal_surplus_bits": 999.0,
    }
    phase_b_pair = {"zeta2_temporal_surplus_bits": 1.25}
    assert runner._select_pair_target(
        runner.C2_Q13_VALUE, expired_phase_a, phase_b_pair, index=0
    ) == pytest.approx(1.25)
    assert runner._select_pair_target(
        runner.C2_Q13_HUBER, expired_phase_a, phase_b_pair, index=0
    ) == pytest.approx(1.25)
    with pytest.raises(runner.C2ParallelScreenError):
        runner._select_pair_target(
            runner.C2_MAIN_VALUE, expired_phase_a, phase_b_pair, index=0
        )
    assert runner._select_pair_target(
        runner.C2_MAIN_VALUE,
        {"row_status": "ready", "zeta2_temporal_surplus_bits": 2.5},
        phase_b_pair,
        index=0,
    ) == pytest.approx(2.5)


@pytest.mark.parametrize(
    ("gc", "physical", "expected"),
    (
        (True, 0, (runner.C2_MAIN_VALUE,)),
        (True, 2, runner.C2_CANDIDATE_IDS),
        (False, 2, (runner.C2_Q13_VALUE, runner.C2_Q13_HUBER)),
        (False, 1, ()),
    ),
)
def test_eligible_arms_are_arm_specific(gc: bool, physical: int, expected: tuple[str, ...]) -> None:
    assert runner.eligible_arms_from_gates(
        gc_passed=gc, q13_physical_pass_count=physical
    ) == expected


def test_eligible_arm_gate_rejects_non_boolean_or_out_of_range() -> None:
    with pytest.raises(runner.C2ParallelScreenError):
        runner.eligible_arms_from_gates(gc_passed=1, q13_physical_pass_count=2)  # type: ignore[arg-type]
    with pytest.raises(runner.C2ParallelScreenError):
        runner.eligible_arms_from_gates(gc_passed=False, q13_physical_pass_count=4)


def test_spearman_is_tie_aware_and_fail_closed_on_constant_surface() -> None:
    assert runner.spearman((1.0, 2.0, 2.0), (1.0, 2.0, 3.0)) == pytest.approx(0.8660254)
    assert runner.spearman((1.0, 1.0), (1.0, 2.0)) is None


def test_episode_row_binds_common_field_and_action_receipt() -> None:
    row = _row(
        candidate_id=runner.C2_MAIN_VALUE,
        update=100,
        world=runner.DESIGN_EVAL_SEEDS[0],
        policy="FULL",
        initialization_seed=runner.INITIALIZATION_SEEDS[0],
        bits=2.0,
    )
    runner._validate_design_row(
        row,
        candidate_id=runner.C2_MAIN_VALUE,
        update_count=100,
        phase_b_sha256="a" * 64,
    )
    tampered = dict(row)
    tampered["fading_field_components"] = [
        runner.FIELD_COMPONENT,
        "a" * 64,
        "arm-specific",
    ]
    with pytest.raises(runner.C2ParallelScreenError):
        runner._validate_design_row(
            tampered,
            candidate_id=runner.C2_MAIN_VALUE,
            update_count=100,
            phase_b_sha256="a" * 64,
        )


def test_aggregate_requires_two_lineages_before_design_positive() -> None:
    candidate = runner.C2_Q13_VALUE
    rows: list[dict[str, object]] = []
    for seed_index, initialization_seed in enumerate(runner.INITIALIZATION_SEEDS):
        for world in runner.DESIGN_EVAL_SEEDS:
            rows.append(
                _row(
                    candidate_id=candidate,
                    update=100,
                    world=world,
                    policy="FULL",
                    initialization_seed=initialization_seed,
                    bits=20.0 + seed_index,
                    actions_value=0,
                )
            )
            rows.append(
                _row(
                    candidate_id=candidate,
                    update=100,
                    world=world,
                    policy="DROP_C2",
                    initialization_seed=initialization_seed,
                    bits=10.0,
                    actions_value=0,
                )
            )
    rows.extend(
        _row(
            candidate_id=candidate,
            update=100,
            world=world,
            policy="MAIN",
            initialization_seed=None,
            bits=15.0,
        )
        for world in runner.DESIGN_EVAL_SEEDS
    )
    summary = runner.aggregate_design_rows(
        rows,
        candidate_id=candidate,
        update_count=100,
        phase_b_sha256="a" * 64,
    )
    assert summary["design_positive"] is True
    assert summary["checks"]["pooled_full_minus_drop_c2_positive"] is True
    assert summary["checks"]["at_least_two_initializations_full_minus_drop_c2_positive"] is True
    assert summary["full"]["pooled_ratio_of_sums_ee_bits_per_j"] > summary["drop_c2"]["pooled_ratio_of_sums_ee_bits_per_j"]


def test_write_once_receipt_never_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    first = runner._write_once_json(target, {"b": 1, "a": 2})
    assert len(first) == 64
    with pytest.raises(FileExistsError):
        runner._write_once_json(target, {"changed": True})


def test_prepare_authentication_rejects_split_or_budget_drift(tmp_path: Path) -> None:
    phase_b = {
        "phase_b_sha256": "a" * 64,
        "eligible_arms": [runner.C2_MAIN_VALUE],
        "result": {
            "q13_gate_authority_sha256": "a" * 64,
            "q13_gate_result_file_sha256": "c" * 64,
            "q13_gate_source_manifest_sha256": "d" * 64,
            "q13_gate_schedule_sha256": "e" * 64,
        },
    }
    payload = {
        "schema": runner.PREPARE_SCHEMA,
        "status": "PREPARED",
        "claim_ceiling": runner.CLAIM_CEILING,
        "phase_b_sha256": "a" * 64,
        "eligible_arms": [runner.C2_MAIN_VALUE],
        "initialization_seeds": list(runner.INITIALIZATION_SEEDS),
        "update_ladder": list(runner.UPDATE_LADDER),
        "checkpoint_every": runner.CHECKPOINT_EVERY,
        "evaluation_split": runner.EVALUATION_SPLIT,
        "design_eval_seeds": list(runner.DESIGN_EVAL_SEEDS),
        "users": runner.USERS,
        "steps_per_episode": runner.STEPS_PER_EPISODE,
        "episode_budget": runner.expected_design_eval_episodes(1),
        "field_components": [runner.FIELD_COMPONENT, "a" * 64, "evaluation_seed"],
        "gate_binding": {
            "authority_sha256": "a" * 64,
            "authority_file_sha256": "b" * 64,
            "result_file_sha256": "c" * 64,
            "source_manifest_sha256": "d" * 64,
            "schedule_sha256": "e" * 64,
            "selected_q3_rung": 100,
        },
        "prereg_file_sha256": "f" * 64,
        "counterfactual_outcomes_evaluated": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    seal = {
        "schema": runner.PREPARE_SEAL_SCHEMA,
        "status": "PREPARED",
        "prepare_file_sha256": runner.canonical_sha256(payload),
        "phase_b_sha256": "a" * 64,
        "eligible_arms": [runner.C2_MAIN_VALUE],
        "episode_budget": runner.expected_design_eval_episodes(1),
        "counterfactual_outcomes_evaluated": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    # _write_once_json returns the file-byte digest, which is what the seal
    # authenticates; create the payload first, then bind that exact digest.
    prepare_dir = tmp_path / "prepare"
    prepare_dir.mkdir()
    payload_sha = runner._write_once_json(prepare_dir / "prepare.json", payload)
    seal["prepare_file_sha256"] = payload_sha
    runner._write_once_json(prepare_dir / "prepare-seal.json", seal)
    auth = runner.authenticate_prepare(prepare_dir, phase_b=phase_b)
    assert auth["payload_file_sha256"] == payload_sha
    payload["episode_budget"] = 999
    (tmp_path / "tampered").mkdir()
    tampered = tmp_path / "tampered"
    runner._write_once_json(tampered / "prepare.json", payload)
    runner._write_once_json(tampered / "prepare-seal.json", seal)
    with pytest.raises(runner.C2ParallelScreenError):
        runner.authenticate_prepare(tampered, phase_b=phase_b)


def test_gate_uses_frozen_manifest_receipt_without_reopening_current_source_closure(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "c3-source"
    source_dir.mkdir()
    frozen_body = {
        "schema": "multi-catfish-mcrl-v04-c3-source-manifest-v1",
        "sealed_closure": "old-gated-closure",
    }
    frozen_manifest = dict(frozen_body)
    frozen_manifest["source_manifest_sha256"] = runner.canonical_sha256(frozen_body)
    runner._write_once_json(source_dir / "source-manifest.json", frozen_manifest)
    # A later checkout/source closure is intentionally different.  The gate
    # seam must not reopen it during this C2 consumer authentication.
    runner._write_once_json(
        source_dir / "current-source-closure.json",
        {"closure": "new-checkout-closure"},
    )

    class ReceiptOnlyGate:
        def __init__(self, source_manifest_sha256: str) -> None:
            self.source_manifest_sha256 = source_manifest_sha256
            self.seen_source_dir: Path | None = Path("sentinel")

        def authenticate_gate(self, gate_dir: Path, *, source_dir: Path | None, prereg_path: Path) -> dict[str, object]:
            del gate_dir, prereg_path
            self.seen_source_dir = source_dir
            return {"source_manifest_sha256": self.source_manifest_sha256}

    expected = frozen_manifest["source_manifest_sha256"]
    gate = ReceiptOnlyGate(expected)
    receipt = runner._authenticate_frozen_source_gate(
        screen_module=gate,  # type: ignore[arg-type]
        gate_dir=tmp_path / "gate",
        c3_source_dir=source_dir,
        prereg_path=tmp_path / "prereg.json",
    )
    assert gate.seen_source_dir is None
    assert receipt["frozen_source_manifest_sha256"] == expected

    mismatched = ReceiptOnlyGate("c" * 64)
    with pytest.raises(runner.C2ParallelScreenError):
        runner._authenticate_frozen_source_gate(
            screen_module=mismatched,  # type: ignore[arg-type]
            gate_dir=tmp_path / "gate",
            c3_source_dir=source_dir,
            prereg_path=tmp_path / "prereg.json",
        )
