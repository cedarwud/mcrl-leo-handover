"""W-101 -- clean V0.6 C2-k1 semantics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, NO_OP_ACTION
from mcrl.runtime.ee_axis_v06_c2_k1 import (
    C2K1ContractError,
    build_opening_pairs,
    c2_k1_surplus_bits,
    four_offset_metrics,
    masked_argmax,
    oracle_and_drop_scores,
    select_anchor,
    select_train_worlds,
    selected_continuation_metrics,
)


def _q(winner: int, value: float = 1.0) -> np.ndarray:
    result = np.zeros(NUM_ACTIONS)
    result[winner] = value
    return result


def _mask(*actions: int) -> np.ndarray:
    result = np.zeros(NUM_ACTIONS, dtype=bool)
    result[list(actions)] = True
    return result


def _row(action: int) -> dict[str, object]:
    return {
        "q1_k0": _q(2), "q3_k0": _q(2), "mask_k0": _mask(2, action),
        # These deliberately differ per branch.  The expected actions prove
        # that k1 is branch-local and is not overwritten by focal action.
        "reference_q1_k1": _q(3), "reference_q3_k1": _q(3), "reference_mask_k1": _mask(3, 5),
        "candidate_q1_k1": _q(5), "candidate_q3_k1": _q(5), "candidate_mask_k1": _mask(3, 5),
        "candidate_rates_k1": np.asarray([12.0, 9.0]), "reference_rates_k1": np.asarray([10.0, 10.0]),
        "candidate_power_k1": 3.0, "reference_power_k1": 2.0,
        "z2_k1_normalized_by_action": np.zeros(NUM_ACTIONS),
    }


def test_masked_argmax_is_safe_and_branch_local() -> None:
    assert masked_argmax(_q(4), _q(4), _mask(1, 4)) == 4
    assert masked_argmax(_q(4), _q(4), np.zeros(NUM_ACTIONS, dtype=bool)) == NO_OP_ACTION
    with pytest.raises(C2K1ContractError, match="Boolean"):
        masked_argmax(_q(1), _q(1), np.ones(NUM_ACTIONS, dtype=np.int8))


def test_k1_formula_keeps_negative_sign() -> None:
    # dt*sum(dR) - lambda*dt*dP = 1*(2-1) - 3*(4-2) = -5.
    assert c2_k1_surplus_bits([2.0, 1.0], [1.0, 1.0], 4.0, 2.0,
                              interval_s=1.0, lambda_bits_per_j=3.0) == -5.0


def test_opening_pairs_are_all_28_and_do_not_use_q2() -> None:
    rows = [_row(action) for action in range(NUM_ACTIONS)]
    pairs = build_opening_pairs(rows[0]["q1_k0"], rows[0]["q3_k0"], rows[0]["mask_k0"], rows,
                                reference_action=2,
                                interval_s=1.0, lambda_bits_per_j=3.0, kappa_bits=10.0)
    assert len(pairs) == NUM_ACTIONS
    assert [pair.action for pair in pairs] == list(range(NUM_ACTIONS))
    assert {(pair.reference_k1_action, pair.candidate_k1_action) for pair in pairs} == {(3, 5)}
    assert all(pair.z2_k1_normalized < 0.0 for pair in pairs)


def test_main_reference_is_explicit_not_q13_argmax() -> None:
    rows = [_row(action) for action in range(NUM_ACTIONS)]
    # Q1+Q3 prefers action 2, but the sealed Main gauge is action 0.
    pairs = build_opening_pairs(rows[0]["q1_k0"], rows[0]["q3_k0"], rows[0]["mask_k0"], rows,
                                reference_action=0, interval_s=1.0,
                                lambda_bits_per_j=3.0, kappa_bits=10.0)
    assert all(pair.reference_action == 0 for pair in pairs)


def test_direct_oracle_and_drop_scores_are_unweighted_and_masked() -> None:
    z2 = np.zeros(NUM_ACTIONS)
    z2[7] = 10.0
    oracle, drop = oracle_and_drop_scores(_q(4), _q(4), z2, _mask(4, 7))
    assert drop == 4
    assert oracle == 7
    with pytest.raises(C2K1ContractError, match="oracle mask"):
        oracle_and_drop_scores(_q(1), _q(1), z2, np.zeros(NUM_ACTIONS, dtype=bool))


def test_fixed_pools_first_four_and_first_step_lowest_user() -> None:
    pools = {
        "early": [2026101008, 2026101001, 2026101002, 2026101003, 2026101004],
        "mid": [2026101015, 2026101011, 2026101012, 2026101013, 2026101014],
        "late": [2026101025, 2026101021, 2026101022, 2026101023, 2026101024],
    }
    selected = select_train_worlds(pools)
    assert selected == tuple((pool, world) for pool, start in (("early", 2026101001), ("mid", 2026101011), ("late", 2026101021)) for world in range(start, start + 4))
    anchor = select_anchor("early", 2026101001, [2, 1], [9, 3])
    assert (anchor.step, anchor.focal_user) == (1, 3)
    with pytest.raises(C2K1ContractError, match="outside"):
        select_train_worlds({**pools, "late": [1, 2, 3, 4]})


def test_four_offset_ratio_of_sums_and_service_gate() -> None:
    rates = np.asarray([[10., 5.], [20., 5.], [30., 5.], [40., 5.]])
    power = np.asarray([2., 2., 2., 2.])
    served = np.asarray([[True, False]] * 4)
    result = four_offset_metrics(rates, power, served, interval_s=1.0)
    # The EE numerator is the canonical rate sum, not a served-mask proxy.
    assert result["total_bits"] == 120.0
    assert result["total_energy_j"] == 8.0
    assert result["ratio_of_sums_ee_bits_per_j"] == 15.0
    assert result["service_gate"]["passed"] is True


def test_selected_continuation_accepts_only_oracle_or_drop_and_keeps_gate() -> None:
    row = {
        "oracle_rates_bps": [[1.0], [2.0], [3.0], [4.0]],
        "oracle_power_w": [1.0, 1.0, 1.0, 1.0],
        "oracle_served": [[True], [True], [True], [True]],
    }
    result = selected_continuation_metrics(row, policy="oracle", interval_s=1.0)
    assert result["policy"] == "oracle"
    assert result["service_gate"]["passed"] is True
    with pytest.raises(C2K1ContractError, match="oracle or drop"):
        selected_continuation_metrics(row, policy="full", interval_s=1.0)
