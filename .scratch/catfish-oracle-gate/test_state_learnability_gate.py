from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_state_learnability_dataset as dataset  # noqa: E402
import run_state_learnability_gate as gate  # noqa: E402
import verify_state_learnability_result as result_verify  # noqa: E402


def test_state_fields_preserve_exact_q_head_input_and_mask() -> None:
    encoded = np.linspace(0.0, 1.0, dataset.STATE_DIM, dtype=np.float32)
    mask = np.zeros(28, dtype=bool)
    mask[[1, 7, 20]] = True

    fields = dataset._state_fields(encoded, mask)

    assert fields["state_input_scope"] == "exact_live_q_head_input_only"
    assert np.array_equal(
        np.asarray(fields["focal_encoded_state"], dtype=np.float32), encoded
    )
    assert fields["focal_action_mask"] == mask.tolist()


@pytest.mark.parametrize(
    ("state", "mask"),
    [
        (np.zeros(111, dtype=np.float32), np.zeros(28, dtype=bool)),
        (np.full(112, np.nan, dtype=np.float32), np.zeros(28, dtype=bool)),
        (np.zeros(112, dtype=np.float32), np.zeros(27, dtype=bool)),
    ],
)
def test_state_fields_fail_closed_on_invalid_model_input(
    state: np.ndarray, mask: np.ndarray
) -> None:
    with pytest.raises(RuntimeError):
        dataset._state_fields(state, mask)


def test_strip_state_fields_changes_no_physics_field() -> None:
    row = {
        "evaluation_seed": 1,
        "jointly_positive": True,
        "focal_encoded_state": [0.0] * 112,
        "focal_action_mask": [True] * 28,
        "state_input_scope": "exact_live_q_head_input_only",
        "topology_contract": "strict_net_plus_one_added_1_removed_0",
    }

    assert dataset._strip_state_fields(row) == {
        "evaluation_seed": 1,
        "jointly_positive": True,
    }


def test_strict_split_label_requires_no_removed_beam() -> None:
    base = {
        "realised_active_beams_added": [[20, 1]],
        "realised_active_beams_removed": [],
        "realised_proposed_beam_opening": True,
        "reference_effective_beams": 10,
        "alternative_effective_beams": 11,
        "delta_load_relief": 2.0,
        "ee_positive": True,
        "service_safe": True,
    }
    strict = dict(base)
    dataset._apply_strict_split_labels(strict)

    assert strict["role_positive"] is True
    assert strict["jointly_positive"] is True

    removed = base | {"realised_active_beams_removed": [[10, 1]]}
    dataset._apply_strict_split_labels(removed)
    assert removed["topology_endpoint_positive"] is False
    assert removed["jointly_positive"] is False


def test_label_summary_keeps_seed_as_cluster() -> None:
    rows = [
        {
            "evaluation_seed": 10,
            "status": "evaluated",
            "role_positive": True,
            "ee_positive": True,
            "jointly_positive": True,
            "service_safe": True,
        },
        {
            "evaluation_seed": 10,
            "status": "evaluated",
            "role_positive": False,
            "ee_positive": True,
            "jointly_positive": False,
            "service_safe": False,
        },
        {
            "evaluation_seed": 11,
            "status": "ineligible",
        },
    ]

    summary = dataset._label_summary(rows)

    assert summary["sampled"] == 3
    assert summary["eligible"] == 2
    assert summary["jointly_positive"] == 1
    assert summary["service_unsafe"] == 1
    assert summary["by_seed"]["10"]["eligible"] == 2
    assert summary["by_seed"]["11"]["eligible"] == 0


def _model_row(
    *, action: int, label: bool, state_offset: float = 0.0
) -> dict[str, object]:
    return {
        "focal_encoded_state": (
            np.linspace(0.0, 1.0, dataset.STATE_DIM, dtype=np.float32)
            + state_offset
        ).tolist(),
        "proposal_action": action,
        "jointly_positive": label,
        # These forbidden outcome/Q1 fields must never enter model tensors.
        "reference_q1": 1.0e30,
        "delta_ee_bits_per_j": -1.0e30,
    }


def test_model_tensors_use_only_focal_state_action_and_label() -> None:
    rows = [
        _model_row(action=3, label=False),
        _model_row(action=7, label=True, state_offset=0.5),
    ]

    states, actions, labels = gate._model_tensors(rows)

    assert states.shape == (2, dataset.STATE_DIM)
    assert actions.tolist() == [3, 7]
    assert labels.tolist() == [0.0, 1.0]
    assert states[1, 0].item() == pytest.approx(0.5)


def test_rank_metrics_are_tie_aware_and_deterministic() -> None:
    tied_labels = np.asarray([0.0, 1.0])
    tied_scores = np.asarray([0.25, 0.25])
    assert gate._auroc(tied_labels, tied_scores) == pytest.approx(0.5)

    labels = np.asarray([1.0, 0.0, 1.0])
    scores = np.asarray([0.9, 0.8, 0.7])
    assert gate._average_precision(labels, scores) == pytest.approx(5.0 / 6.0)


def test_accepted_metrics_report_precision_lift_and_physics() -> None:
    rows = [
        {
            "jointly_positive": True,
            "delta_ee_bits_per_j": 2.0e6,
            "delta_throughput_bps": 3.0e9,
            "delta_power_w": 4.0,
            "service_safe": True,
        },
        {
            "jointly_positive": False,
            "delta_ee_bits_per_j": -1.0e6,
            "delta_throughput_bps": -2.0e9,
            "delta_power_w": 1.0,
            "service_safe": False,
        },
        {
            "jointly_positive": False,
            "delta_ee_bits_per_j": 0.0,
            "delta_throughput_bps": 0.0,
            "delta_power_w": 0.0,
            "service_safe": True,
        },
        {
            "jointly_positive": False,
            "delta_ee_bits_per_j": 0.0,
            "delta_throughput_bps": 0.0,
            "delta_power_w": 0.0,
            "service_safe": True,
        },
    ]

    metrics = gate._accepted_metrics(
        rows, np.asarray([True, True, False, False], dtype=bool)
    )

    assert metrics["coverage"] == pytest.approx(0.5)
    assert metrics["joint_prevalence"] == pytest.approx(0.25)
    assert metrics["joint_precision"] == pytest.approx(0.5)
    assert metrics["joint_precision_lift_over_prevalence"] == pytest.approx(2.0)
    assert metrics["mean_delta_ee_mbit_per_j"] == pytest.approx(0.5)
    assert metrics["service_unsafe_rate"] == pytest.approx(0.5)


def test_short_fit_is_reproducible_for_fixed_seed() -> None:
    rows = [
        _model_row(
            action=index % 28,
            label=bool(index % 3 == 0),
            state_offset=float(index) / 100.0,
        )
        for index in range(24)
    ]

    first, _first_receipt = gate._fit_member(rows, seed=1234, epochs=2)
    second, _second_receipt = gate._fit_member(rows, seed=1234, epochs=2)

    for first_parameter, second_parameter in zip(
        first.parameters(), second.parameters(), strict=True
    ):
        assert torch.equal(first_parameter, second_parameter)


def test_result_verifier_numeric_comparison_is_strict_but_tolerant() -> None:
    result_verify._assert_same(
        {"metric": [0.3, True]},
        {"metric": [0.3000000000001, True]},
        path="fixture",
    )
    with pytest.raises(RuntimeError):
        result_verify._assert_same(
            {"metric": 0.31}, {"metric": 0.30}, path="fixture"
        )


def test_recomputed_gate_requires_every_frozen_condition() -> None:
    verification = {"status": "verified"}
    per_seed = {
        str(seed): {
            "mean_delta_ee_mbit_per_j": 0.1,
            "jointly_positive": 4,
            "joint_precision": 0.4,
            "joint_recall": 0.3,
            "coverage": 0.2,
        }
        for seed in dataset.HELDOUT_SEEDS
    }
    conditions = result_verify._recompute_conditions(
        development_verification=verification,
        heldout_verification=verification,
        classification={"prevalence": 0.2, "auroc": 0.7, "average_precision": 0.35},
        always={"service_unsafe_rate": 0.002},
        accepted={
            "accepted_rows": 200,
            "coverage": 0.2,
            "joint_precision": 0.4,
            "mean_delta_ee_mbit_per_j": 0.1,
            "service_unsafe_rate": 0.005,
        },
        per_seed=per_seed,
        seed_interval={
            "available": True,
            "descriptive_t95_low_mbit_per_j": 0.05,
        },
    )

    assert all(condition["passed"] for condition in conditions.values())
    per_seed[str(dataset.HELDOUT_SEEDS[-1])]["coverage"] = 0.0
    per_seed[str(dataset.HELDOUT_SEEDS[-2])]["coverage"] = 0.0
    per_seed[str(dataset.HELDOUT_SEEDS[-3])]["coverage"] = 0.0
    failed = result_verify._recompute_conditions(
        development_verification=verification,
        heldout_verification=verification,
        classification={"prevalence": 0.2, "auroc": 0.7, "average_precision": 0.35},
        always={"service_unsafe_rate": 0.002},
        accepted={
            "accepted_rows": 200,
            "coverage": 0.2,
            "joint_precision": 0.4,
            "mean_delta_ee_mbit_per_j": 0.1,
            "service_unsafe_rate": 0.005,
        },
        per_seed=per_seed,
        seed_interval={
            "available": True,
            "descriptive_t95_low_mbit_per_j": 0.05,
        },
    )
    assert failed["per_seed_selection"]["passed"] is False
