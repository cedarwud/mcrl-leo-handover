"""W-92 -- V0.4 C2 support-complete prepare and Phase-A contract."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v04_c2_support_complete_census",
    REPO / ".scratch/c3-v04/run_v04_c2_support_complete_census.py",
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _focal(*, seed: int, step: int, focal_user: int) -> object:
    reference = 0
    candidates = tuple(action for action in range(28) if action != reference)
    keys = tuple((90000 + seed % 100 + action, action) for action in candidates)
    return runner.C2V04TopologyFocal(
        focal_user=focal_user,
        anchor_sha256=_sha(f"anchor-{seed}-{step}-{focal_user}"),
        reference_action=reference,
        reference_physical_key=(90000 + seed % 100 + reference, reference),
        incumbent_physical_key=(91000 + seed % 100 + focal_user, focal_user),
        common_random_field_sha256=_sha(f"field-{seed}-{step}-{focal_user}"),
        predecision_heuristic_scores=tuple(float(action + 1) for action in candidates),
        legal_action_mask=tuple(True for _ in range(28)),
        candidate_actions=candidates,
        candidate_physical_keys=keys,
    )


def _topology(
    seed: int,
    *,
    step: int = 2,
    focal_users: tuple[int, ...] = (1, 2, 4, 7, 9),
    horizon: bool = True,
) -> object:
    return runner.C2V04TopologyAnchor(
        source_seed=seed,
        step_index=step,
        world_anchor_sha256=_sha(f"world-{seed}-{step}"),
        focal_candidates=tuple(
            _focal(seed=seed, step=step, focal_user=user)
            for user in sorted(focal_users)
        ),
        physical_main_departures=tuple(sorted(focal_users)),
        checkpoint_sha256=_sha("checkpoint"),
        source_manifest_sha256=_sha("manifest"),
        policy_sha256=_sha("policy"),
        evaluation_seed=seed + 100,
        common_random_field_root_sha256=_sha(f"field-root-{seed}"),
        complete_forecast_horizon=horizon,
    )


def test_prepare_scans_ordered_prefix_and_selects_earliest_step_lowest_four() -> None:
    calls: list[int] = []

    def scan(seed: int):
        calls.append(seed)
        if seed == 2026092801:
            # Step 1 is not eligible; step 2 is the first eligible anchor.
            return (
                _topology(seed, step=1, focal_users=(1, 2, 4)),
                _topology(seed, step=2, focal_users=(9, 2, 7, 4, 1)),
            )
        if seed in (2026092802, 2026092803):
            return (_topology(seed, step=3),)
        return ()

    prepared = runner.prepare_c2_v04_census(scan)

    assert calls == [2026092801, 2026092802, 2026092803]
    assert prepared.scanned_source_seeds == tuple(calls)
    assert prepared.selected_source_seeds == (2026092801, 2026092802, 2026092803)
    assert len(prepared.schedule.anchors) == runner.EXPECTED_CLUSTERS == 12
    assert len(prepared.schedule.rows) == runner.EXPECTED_SIBLINGS == 324
    seed_one_users = [
        anchor.focal_user
        for anchor in prepared.schedule.anchors
        if anchor.source_seed == 2026092801
    ]
    assert sorted(seed_one_users) == [1, 2, 4, 7]
    assert all(row.row_status == runner.C2_V04_ROW_READY for row in prepared.schedule.rows)


def test_prepare_never_needs_forecast_or_outcome_and_rejects_short_pool() -> None:
    calls: list[int] = []

    def topology_only(seed: int):
        calls.append(seed)
        return (_topology(seed),) if seed <= 2026092803 else ()

    prepared = runner.prepare_c2_v04_census(topology_only)
    assert prepared.counterfactual_outcomes_evaluated is False
    assert prepared.training_run is False
    assert prepared.test_opened is False
    assert prepared.held_out_ee_evaluated is False

    with pytest.raises(runner.C2V04CensusRunnerError, match="three eligible worlds"):
        runner.prepare_c2_v04_census(lambda seed: (_topology(seed),) if seed == 2026092801 else ())


def test_production_anchor_uses_228d_causal_encoder_not_legacy_payload() -> None:
    state_matrix = np.arange(2 * 228, dtype=np.float32).reshape(2, 228)
    action_masks = np.ones((2, 28), dtype=np.bool_)
    calls: list[tuple[object, object]] = []

    class Encoder:
        @staticmethod
        def encode_ee_axis_state(environment, observation):
            calls.append((environment, observation))
            return SimpleNamespace(
                state_matrix=state_matrix,
                action_masks=action_masks,
            )

    environment = object()
    observation = SimpleNamespace(state_matrix=np.zeros((2, 112), dtype=np.float32))
    state, mask = runner._production_ee_axis_anchor(
        modules={"ee_axis_state": Encoder},
        wrapped=SimpleNamespace(environment=environment),
        observation=observation,
        focal_user=1,
    )

    assert calls == [(environment, observation)]
    assert state.shape == (228,)
    assert mask.shape == (28,)
    assert np.array_equal(state, state_matrix[1])
    assert np.array_equal(mask, action_masks[1])


def test_production_anchor_fails_closed_on_legacy_encoder_shape() -> None:
    class LegacyEncoder:
        @staticmethod
        def encode_ee_axis_state(_environment, _observation):
            return SimpleNamespace(
                state_matrix=np.zeros((1, 112), dtype=np.float32),
                action_masks=np.ones((1, 28), dtype=np.bool_),
            )

    with pytest.raises(runner.C2V04CensusRunnerError, match="228 state"):
        runner._production_ee_axis_anchor(
            modules={"ee_axis_state": LegacyEncoder},
            wrapped=SimpleNamespace(environment=object()),
            observation=object(),
            focal_user=0,
        )


def test_prepare_artifact_round_trip_is_write_once_and_fail_closed(tmp_path: Path) -> None:
    prepared = runner.prepare_c2_v04_census(
        lambda seed: (_topology(seed),) if seed in (2026092801, 2026092802, 2026092803) else ()
    )
    path = tmp_path / "prepare.json"
    file_sha = runner.write_c2_v04_prepare_artifact(path, prepared)
    restored = runner.read_c2_v04_prepare_artifact(path, expected_file_sha256=file_sha)
    assert restored == prepared
    with pytest.raises(FileExistsError):
        runner.write_c2_v04_prepare_artifact(path, prepared)
    payload = json.loads(path.read_text(encoding="ascii"))
    payload["schedule"]["rows"][0]["candidate_action"] = 27
    path.write_text(json.dumps(payload), encoding="ascii")
    with pytest.raises(runner.C2V04CensusRunnerError):
        runner.read_c2_v04_prepare_artifact(path)


def _prepared_fixture() -> object:
    return runner.prepare_c2_v04_census(
        lambda seed: (_topology(seed),) if seed in (2026092801, 2026092802, 2026092803) else ()
    )


def _outcomes_and_rankings(prepared):
    outcomes: dict[object, dict[str, object]] = {}
    rankings: dict[object, tuple[object, ...]] = {}
    for anchor in prepared.schedule.anchors:
        # Main is action 0 in this fixture; action 2 is the frozen old pair.
        rankings[anchor.intervention_key] = tuple(
            runner.C2V04OldQ2Ranking(
                initialization_seed=seed,
                ranked_actions=(anchor.reference_action, 1, 2, *tuple(
                    action
                    for action in range(28)
                    if action not in (anchor.reference_action, 1, 2)
                )),
                supervised_candidate_action=2,
            )
            for seed in runner.Q2_INITIALIZATION_SEEDS
        )
        for row in prepared.schedule.rows:
            if row.intervention_key != anchor.intervention_key:
                continue
            action = row.candidate_action
            target = 2.0 if action == 1 else (1.0 if action == 2 else ((action % 5) - 2.0) / 2.0)
            outcomes[row.sibling_key] = {
                "row_status": runner.C2_V04_ROW_READY,
                "non_incumbent": True,
                "release_offset": 2,
                "zeta2_temporal_surplus_bits": target * runner.KAPPA_BITS,
                "delivered_bit_delta": 0.0 if action == 1 else -1.0,
                "common_random_field_sha256": row.common_random_field_sha256,
            }
    return outcomes, rankings


def test_phase_a_materializes_all_324_rows_and_computes_gates_and_rankings() -> None:
    prepared = _prepared_fixture()
    outcomes, rankings = _outcomes_and_rankings(prepared)
    result = runner.phase_a_census(prepared, outcomes, rankings)

    assert result["row_count"] == 324
    assert result["expected_row_count"] == 324
    assert result["source_rule"] == runner.C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
    assert result["counterfactual_outcomes_evaluated"] is True
    assert result["training_run"] is False
    assert result["test_opened"] is False
    assert result["held_out_ee_evaluated"] is False
    assert result["decision"] == "AUTHORIZE_PHASE_B_CONTINUATION_PROBE"
    assert result["gates"]["G-S"]["passed"] is True
    assert result["gates"]["G-R"]["passed"] is True
    assert result["gates"]["G-V"]["passed"] is True
    assert len(result["gates"]["G-R"]["old_q2_rankings"]) == 36


def test_phase_a_retains_missing_and_support_expired_rows_and_fails_gate() -> None:
    prepared = _prepared_fixture()
    outcomes, rankings = _outcomes_and_rankings(prepared)
    support_expired_key = prepared.schedule.rows[1].sibling_key
    outcomes[support_expired_key] = {
        "row_status": "support_expired",
        "failure_code": "support_lost_at_offset_1",
        "non_incumbent": True,
        "release_offset": 1,
        "zeta2_temporal_surplus_bits": 0.25 * runner.KAPPA_BITS,
        "delivered_bit_delta": -1.0,
        "common_random_field_sha256": prepared.schedule.rows[1].common_random_field_sha256,
    }
    missing_key = prepared.schedule.rows[2].sibling_key
    outcomes.pop(missing_key)
    result = runner.phase_a_census(prepared, outcomes, rankings)
    statuses = {row["row_status"] for row in result["rows"]}
    assert "support-expired" in statuses
    assert "row-failure" in statuses
    assert result["row_count"] == 324
    assert result["gates"]["G-S"]["missing_outcome_count"] >= 1
    assert result["decision"] == "FORMULATION_REDESIGN_REQUIRED"


def test_phase_a_rejects_missing_q2_head_or_bad_ranking_shape() -> None:
    prepared = _prepared_fixture()
    outcomes, rankings = _outcomes_and_rankings(prepared)
    key = next(iter(rankings))
    rankings[key] = rankings[key][:2]
    with pytest.raises(runner.C2V04CensusRunnerError, match="three ordered"):
        runner.phase_a_census(prepared, outcomes, rankings)


def _zero_raw_trace() -> dict[str, object]:
    rates = [[0.0 for _ in range(100)] for _ in range(4)]
    served = [[False for _ in range(100)] for _ in range(4)]
    return {
        "reference_rates_bps": rates,
        "candidate_rates_bps": [list(row) for row in rates],
        "reference_system_power_w": [1.0, 1.0, 1.0, 1.0],
        "candidate_system_power_w": [1.0, 1.0, 1.0, 1.0],
        "reference_served": served,
        "candidate_served": [list(row) for row in served],
        "lambda_bits_per_j": 1.0,
        "interval_s": 1.0,
        "offset_surplus_bits": [0.0, 0.0, 0.0],
    }


def test_phase_a_recomputes_raw_trace_and_delivered_delta() -> None:
    prepared = _prepared_fixture()
    outcomes, rankings = _outcomes_and_rankings(prepared)
    key = prepared.schedule.rows[0].sibling_key
    outcomes[key] = {
        "row_status": runner.C2_V04_ROW_READY,
        "non_incumbent": True,
        "release_offset": 3,
        "zeta2_temporal_surplus_bits": 0.0,
        "delivered_bit_delta": 0.0,
        "common_random_field_sha256": prepared.schedule.rows[0].common_random_field_sha256,
        "raw_trace": _zero_raw_trace(),
    }
    result = runner.phase_a_census(prepared, outcomes, rankings)
    row = next(item for item in result["rows"] if item["sibling_key"] == list(key[:4]) + [list(key[4])])
    assert row["raw_trace"]["offset_surplus_bits"] == [0.0, 0.0, 0.0]

    outcomes[key]["delivered_bit_delta"] = 1.0
    with pytest.raises(runner.C2V04CensusRunnerError, match="delivered_bit_delta"):
        runner.phase_a_census(prepared, outcomes, rankings)


def test_phase_a_rejects_extra_outcome_and_ranking_cluster() -> None:
    prepared = _prepared_fixture()
    outcomes, rankings = _outcomes_and_rankings(prepared)
    extra_key = (2026092809, _sha("extra-world"), _sha("extra-anchor"), 9, (1, 2))
    outcomes[extra_key] = outcomes[next(iter(outcomes))]
    with pytest.raises(runner.C2V04CensusRunnerError, match="unscheduled extra sibling"):
        runner.phase_a_census(prepared, outcomes, rankings)

    outcomes, rankings = _outcomes_and_rankings(prepared)
    first = next(iter(rankings.values()))
    rankings[(2026092809, _sha("extra-world"), _sha("extra-anchor"), 9)] = first
    with pytest.raises(runner.C2V04CensusRunnerError, match="unscheduled extra cluster"):
        runner.phase_a_census(prepared, outcomes, rankings)
