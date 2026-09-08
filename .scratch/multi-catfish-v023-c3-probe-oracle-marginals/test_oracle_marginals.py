from __future__ import annotations

import numpy as np

import oracle_marginals as probe


def test_target_arithmetic_and_energy_variant() -> None:
    t1, t3, t3e = probe.target_triplet(
        [10.0, 20.0, 30.0], [13.0, 18.0, 37.0], 5.0, 7.0, 1,
        lambda_bits_per_j=4.0,
    )
    assert t1 == -10.0
    assert t3 == 10.0
    assert t3e == 2.0


def test_composition_promotes_float32_and_applies_each_scale_once() -> None:
    q1 = np.array([[0.0, 0.5]], dtype=np.float32)
    q2 = np.array([[0.0, 0.25]], dtype=np.float32)
    mask = np.array([[True, True]])
    actions = probe.compose_actions(
        q1, q2,
        np.array([[2.0, 0.0]]),
        np.array([[0.0, 1.0]]),
        np.array([[0.0, 2.0]]),
        mask, kappa_bits=2.0,
    )
    assert actions["BASE"].tolist() == [1]
    assert actions["O1"].tolist() == [0]
    assert actions["O2"].tolist() == [1]
    assert actions["O123"].tolist() == [1]


def test_tie_lowest_index_and_empty_mask_noop() -> None:
    values = np.array([[1.0, 1.0, 0.0], [8.0, 9.0, 10.0]])
    masks = np.array([[True, True, False], [False, False, False]])
    assert probe.masked_argmax(values, masks).tolist() == [0, -1]


def test_cap_application() -> None:
    got = probe.cap_bits([5.0, 20.0], 2.0, 8.0)
    assert got.tolist() == [10.0, 16.0]
    assert probe.cap_bits([5.0, 20.0], 2.0, None).tolist() == [10.0, 40.0]


def test_exact_ratio_of_sums_pooling_not_mean_of_ratios() -> None:
    rows = [
        {"bits": 10.0, "energy_j": 1.0, "served": 1, "opportunities": 1, "demand_satisfied": 1},
        {"bits": 10.0, "energy_j": 9.0, "served": 0, "opportunities": 1, "demand_satisfied": 0},
    ]
    got = probe.pooled_metrics(rows, 1.0)
    assert got["pooled_ee_bits_per_j"] == 2.0
    assert got["service_fraction"] == 0.5
    assert got["demand_satisfied_fraction"] == 0.5


def test_determinism() -> None:
    q1 = np.array([[0.1, 0.2], [0.3, 0.1]], dtype=np.float32)
    q2 = np.array([[0.2, 0.1], [0.0, 0.2]], dtype=np.float32)
    target = np.array([[1.0, -1.0], [2.0, 3.0]], dtype=np.float64)
    masks = np.ones((2, 2), dtype=np.bool_)
    first = probe.compose_actions(q1, q2, target, target / probe.KAPPA_BITS, -target, masks)
    second = probe.compose_actions(q1.copy(), q2.copy(), target.copy(), target / probe.KAPPA_BITS, -target, masks.copy())
    assert all(np.array_equal(first[key], second[key]) for key in first)
