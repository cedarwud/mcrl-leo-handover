from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_arlp_shadow_gate as gate  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402


def _candidate(
    action: int,
    key: tuple[int, int],
    *,
    load: float,
    sinr: float,
) -> gate.ARLPCandidate:
    return gate.ARLPCandidate(
        action=action,
        key=key,
        prior_demand=load,
        candidate_sinr=sinr,
    )


def test_activation_power_anchor_matches_frozen_physics() -> None:
    anchor = gate.activation_power_anchor()

    assert anchor["segment_start_output_power_w"] == pytest.approx(0.825)
    assert anchor["pa_efficiency"] == pytest.approx(0.13917237753423384)
    assert anchor["pa_supply_power_w"] == pytest.approx(5.927900454219554)
    assert anchor["minimum_active_beam_consumed_power_w"] == pytest.approx(
        gate.EXPECTED_ACTIVATION_POWER_ANCHOR_W
    )


@pytest.mark.parametrize(
    ("loads", "focal_key"),
    [
        ({(10, 1): 1}, (10, 1)),
        ({(10, 1): 4}, (10, 1)),
        ({(10, 1): 4, (20, 2): 2}, (20, 2)),
    ],
)
def test_difference_reward_is_exact_potential_difference(
    loads: dict[tuple[int, int], int], focal_key: tuple[int, int]
) -> None:
    load = loads[focal_key]
    without = dict(loads)
    if load == 1:
        del without[focal_key]
    else:
        without[focal_key] = load - 1

    marginal = gate.arlp_potential(loads) - gate.arlp_potential(without)

    assert -gate.arlp_difference_reward(load) == pytest.approx(marginal)


def test_proposal_api_has_no_q1_reference_or_outcome_input() -> None:
    assert set(inspect.signature(gate.arlp_proposal).parameters) == {
        "candidates",
        "visible_incumbent_key",
    }


def test_proposal_prefers_active_lower_marginal_cost_over_empty_activation() -> None:
    proposal = gate.arlp_proposal(
        candidates=[
            _candidate(0, (10, 1), load=2.0, sinr=2.0),
            _candidate(1, (20, 1), load=0.0, sinr=99.0),
        ],
        visible_incumbent_key=None,
    )

    assert proposal.choice.action == 0
    assert [row.marginal_cost for row in proposal.candidates] == pytest.approx(
        [5.0 / 6.0, 7.0 / 6.0]
    )


def test_proposal_excludes_focal_from_visible_incumbent_demand() -> None:
    proposal = gate.arlp_proposal(
        candidates=[
            _candidate(0, (10, 1), load=1.0, sinr=100.0),
            _candidate(1, (20, 1), load=1.0, sinr=1.0),
        ],
        visible_incumbent_key=(10, 1),
    )

    assert proposal.candidates[0].other_demand == 0.0
    assert proposal.candidates[0].activation_indicator == 1
    assert proposal.choice.action == 1


def test_proposal_tie_breaks_by_sinr_then_action() -> None:
    higher_sinr = gate.arlp_proposal(
        candidates=[
            _candidate(4, (10, 1), load=1.0, sinr=5.0),
            _candidate(7, (20, 1), load=1.0, sinr=8.0),
        ],
        visible_incumbent_key=None,
    )
    action_tie = gate.arlp_proposal(
        candidates=[
            _candidate(4, (10, 1), load=1.0, sinr=8.0),
            _candidate(7, (20, 1), load=1.0, sinr=8.0),
        ],
        visible_incumbent_key=None,
    )

    assert higher_sinr.choice.action == 7
    assert action_tie.choice.action == 4


def test_duplicate_physical_candidates_fail_closed() -> None:
    with pytest.raises(ValueError, match="de-duplicated"):
        gate.arlp_proposal(
            candidates=[
                _candidate(0, (10, 1), load=1.0, sinr=2.0),
                _candidate(1, (10, 1), load=1.0, sinr=2.0),
            ],
            visible_incumbent_key=None,
        )


def test_raw_duplicate_physical_actions_are_forbidden() -> None:
    class FakeTable:
        mask = np.array([True, True])

        @staticmethod
        def association(action: int) -> Association:
            del action
            return Association(norad_id=10, cell_id=1)

    with pytest.raises(RuntimeError, match="duplicate physical keys"):
        gate.physical_candidates(
            FakeTable(),
            prior_demand=np.array([1.0, 1.0]),
            candidate_sinr=np.array([2.0, 2.0]),
        )


def test_random_control_is_deterministic_uniform_pool_and_not_reference() -> None:
    candidates = [
        _candidate(0, (10, 1), load=1.0, sinr=1.0),
        _candidate(1, (20, 1), load=1.0, sinr=1.0),
        _candidate(2, (30, 1), load=1.0, sinr=1.0),
    ]
    first = gate.draw_random_control(
        candidates,
        reference_key=(10, 1),
        rng=np.random.default_rng(1234),
    )
    second = gate.draw_random_control(
        candidates,
        reference_key=(10, 1),
        rng=np.random.default_rng(1234),
    )

    assert first == second
    assert first is not None
    assert [item.key for item in first.pool] == [(20, 1), (30, 1)]
    assert first.choice == first.pool[first.draw_index]
    assert first.choice.key != (10, 1)


def test_rollout_freezes_proposal_then_control_before_physics() -> None:
    source = inspect.getsource(gate.run_rollout)

    proposal_position = source.index("proposal = arlp_proposal")
    q1_position = source.index("q1 = trainer.scalarized_q_values")
    control_position = source.index("control = draw_random_control")
    physics_position = source.index(
        "baseline = step_environment.evaluate_actions"
    )

    assert proposal_position < q1_position < control_position < physics_position


def _passing_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for seed in gate.V4_EVALUATION_SEEDS:
        for _ in range(100):
            rows.append(
                {
                    "status": "evaluated",
                    "evaluation_seed": seed,
                    "reference": {"c3": 2.0},
                    "arlp": {"c3": 1.0},
                    "arlp_vs_reference": {
                        "alternative_minus_reference": {
                            "system_ee_bits_per_j": 2.0
                        },
                        "service_unsafe": False,
                    },
                    "random_vs_reference": {"service_unsafe": False},
                    "arlp_minus_random": {
                        "alternative_minus_reference": {
                            "system_ee_bits_per_j": 1.0
                        }
                    },
                }
            )
    return rows


def test_frozen_summary_requires_every_condition() -> None:
    rows = _passing_rows()

    passed = gate.summarize_gate(
        rows,
        seeds=gate.V4_EVALUATION_SEEDS,
        confirmation=True,
    )
    rows[0]["arlp_minus_random"]["alternative_minus_reference"][  # type: ignore[index]
        "system_ee_bits_per_j"
    ] = -2000.0
    failed = gate.summarize_gate(
        rows,
        seeds=gate.V4_EVALUATION_SEEDS,
        confirmation=True,
    )

    assert passed["all_conditions_pass"] is True
    assert passed["decision"] == "PASS_ADVANCE_TO_R3_IMPLEMENTATION_AUDIT_ONLY"
    assert failed["frozen_conditions"]["arlp_vs_random_ee"] is False
    assert failed["decision"] == "FAIL_DROP_ARLP_R3_DIRECTION"


def test_pilot_cannot_emit_a_scientific_decision() -> None:
    result = gate.summarize_gate(
        _passing_rows()[:20], seeds=gate.PILOT_SEEDS, confirmation=False
    )

    assert result["all_conditions_pass"] is False
    assert result["decision"] == "PILOT_ONLY_NO_SCIENTIFIC_DECISION"
