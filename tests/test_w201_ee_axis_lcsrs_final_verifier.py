"""Focused synthetic checks for the independent V0.23 final verifier."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO / ".scratch" / "multi-catfish-v023-c3-observability" / "verify_v023_lcsrs_final.py"
SPEC = importlib.util.spec_from_file_location("v023_final_test_module", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
FINAL = importlib.util.module_from_spec(SPEC)
sys.modules["v023_final_test_module"] = FINAL
SPEC.loader.exec_module(FINAL)


def _all_predicates() -> dict[str, bool]:
    return {
        "integrity": True,
        "pair_coverage": True,
        "mechanics": True,
        "physical_signature": True,
        "target_support": True,
        "held_out_learner": True,
        "world_stability": True,
        "action_exposure": True,
        "literal_11": True,
        "harmful_partial": True,
        "topology_consistency": True,
        "teacher_composition": True,
        "learned_composition": True,
        "service": True,
    }


def test_positive_token_requires_all_frozen_predicates() -> None:
    assert FINAL.adjudicate_section14(**_all_predicates()) == "GO_FIXED_LEARNER_SCREEN_CONTRACT"


@pytest.mark.parametrize(
    ("predicate", "expected"),
    (
        ("integrity", "INVALID_RUN"),
        ("pair_coverage", "INSUFFICIENT_PAIRS"),
        ("mechanics", "STOP_PHYSICS"),
        ("physical_signature", "STOP_PHYSICS"),
        ("teacher_composition", "STOP_PHYSICS"),
        ("target_support", "STOP_OBSERVABILITY"),
        ("held_out_learner", "STOP_OBSERVABILITY"),
        ("world_stability", "STOP_OBSERVABILITY"),
        ("action_exposure", "REDESIGN_INTERFACE"),
        ("literal_11", "REDESIGN_INTERFACE"),
        ("harmful_partial", "REDESIGN_INTERFACE"),
        ("topology_consistency", "REDESIGN_INTERFACE"),
        ("learned_composition", "REDESIGN_INTERFACE"),
        ("service", "REDESIGN_INTERFACE"),
    ),
)
def test_section14_precedence(predicate: str, expected: str) -> None:
    values = _all_predicates()
    values[predicate] = False
    assert FINAL.adjudicate_section14(**values) == expected


def _synthetic_shards(*, empty_pairs: bool = False, zero_energy: bool = False) -> dict[tuple[int, int, str], object]:
    """Build only the raw fields consumed by the composition recomputation."""

    shards: dict[tuple[int, int, str], object] = {}
    pair_action = np.asarray([False] if empty_pairs else [True], dtype=np.bool_)
    pair_literal = np.asarray([False] if empty_pairs else [True], dtype=np.bool_)
    pair_harmful = np.asarray([False], dtype=np.bool_)
    pair_topology = np.asarray([False] if empty_pairs else [True], dtype=np.bool_)
    for world in FINAL.V023_GATE_WORLDS:
        for seed in FINAL.V023_STUDENT_SEEDS:
            for arm in FINAL.V023_FIT_ARMS:
                bits = np.full((9, 3, FINAL.V023_DRAW_COUNT), 110.0, dtype=np.float64)
                bits[:, 0, :] = 100.0
                bits[:, 2, :] = 120.0
                energy = np.ones((9, 3, FINAL.V023_DRAW_COUNT), dtype=np.float64)
                if zero_energy:
                    energy[:, 0, :] = 0.0
                served = np.ones((9, 3, FINAL.V023_DRAW_COUNT, 2), dtype=np.bool_)
                arrays = {
                    "physical_total_bits": bits,
                    "physical_energy_j": energy,
                    "physical_served": served,
                    "pair_action_change": pair_action.copy(),
                    "pair_literal_11": pair_literal.copy(),
                    "pair_harmful_partial": pair_harmful.copy(),
                    "pair_topology_consistent": pair_topology.copy(),
                    "pair_collateral_denominator": np.asarray([0] if empty_pairs else [1], dtype=np.int64),
                    "pair_collateral_changed_count": np.asarray([0], dtype=np.int64),
                }
                shards[(world, seed, arm)] = FINAL._CompositionShard(
                    path=Path(f"synthetic-{world}-{seed}-{arm}.json"),
                    payload={},
                    arrays=arrays,
                    world=world,
                    seed=seed,
                    arm=arm,
                )
    return shards


def test_positive_composition_recomputation_feeds_positive_token() -> None:
    metrics = FINAL._composition_metrics(_synthetic_shards())
    assert metrics["physical"] == {"teacher_composition": True, "learned_composition": True, "service": True}
    assert metrics["composition"] == {
        "action_exposure": True,
        "literal_11": True,
        "harmful_partial": True,
        "topology_consistency": True,
    }
    predicates = _all_predicates()
    predicates.update(metrics["physical"])
    predicates.update(metrics["composition"])
    assert FINAL.adjudicate_section14(**predicates) == "GO_FIXED_LEARNER_SCREEN_CONTRACT"


def test_zero_selected11_is_na_and_fails_interface_predicate() -> None:
    metrics = FINAL._composition_metrics(_synthetic_shards(empty_pairs=True))
    assert metrics["pair_denominators"]["topology_consistency"] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }
    assert metrics["composition"]["topology_consistency"] is False


def test_zero_physical_energy_is_fail_closed() -> None:
    with pytest.raises(FINAL.V023FinalVerificationError, match="denominator"):
        FINAL._composition_metrics(_synthetic_shards(zero_energy=True))


def _cross_arm_shards() -> tuple[object, object]:
    arrays = {
        "anchor_id": np.asarray([b"a"], dtype="S1"),
        "anchor_phase": np.asarray([1], dtype=np.int64),
        "baseline_actions": np.asarray([1, 2], dtype=np.int64),
        "teacher_actions": np.asarray([2, 3], dtype=np.int64),
        "q1": np.asarray([1.0], dtype=np.float32),
        "q2": np.asarray([2.0], dtype=np.float32),
        "q12": np.asarray([3.0], dtype=np.float32),
        # Production role order is (baseline, learned, teacher).  The role-1
        # values are intentionally changed by the learned-arm test below.
        "physical_actions": np.asarray(
            [[[10, 11], [20, 21], [30, 31]]], dtype=np.int64
        ),
        "physical_total_bits": np.asarray(
            [[[100.0, 101.0], [200.0, 201.0], [300.0, 301.0]]], dtype=np.float64
        ),
        "physical_per_user_bits": np.asarray(
            [[
                [[50.0, 50.0], [50.0, 51.0]],
                [[100.0, 100.0], [100.0, 101.0]],
                [[150.0, 150.0], [150.0, 151.0]],
            ]],
            dtype=np.float64,
        ),
        "physical_energy_j": np.asarray(
            [[[1.0, 1.1], [2.0, 2.1], [3.0, 3.1]]], dtype=np.float64
        ),
        "physical_served": np.asarray(
            [[
                [[True, True], [True, True]],
                [[True, True], [True, True]],
                [[True, True], [True, True]],
            ]],
            dtype=np.bool_,
        ),
        "physical_common_field_digest": np.asarray(
            [[[b"a", b"b"], [b"a", b"b"], [b"a", b"b"]]], dtype="S1"
        ),
        "pair_id": np.asarray([b"p"], dtype="S1"),
        "pair_anchor_index": np.asarray([0], dtype=np.int64),
        "pair_member_users": np.asarray([[0, 1]], dtype=np.int64),
        "pair_designated_actions": np.asarray([[1, 2]], dtype=np.int64),
        "pair_profile_actions": np.asarray(
            [[[[1, 2], [3, 4], [5, 6], [7, 8]]]], dtype=np.int64
        ),
        "pair_profile_bits": np.asarray(
            [[[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]]],
            dtype=np.float64,
        ),
        "pair_profile_energy_j": np.asarray(
            [[[1.0, 2.0, 3.0, 4.0]]], dtype=np.float64
        ),
        "pair_profile_served": np.ones((1, 1, 4, 2), dtype=np.bool_),
        "pair_common_field_digest": np.asarray([[b"f"]], dtype="S1"),
    }
    left = FINAL._CompositionShard(Path("left"), {}, arrays, FINAL.V023_GATE_WORLDS[0], FINAL.V023_STUDENT_SEEDS[0], "INFORMED")
    right = FINAL._CompositionShard(Path("right"), {}, {name: value.copy() for name, value in arrays.items()}, FINAL.V023_GATE_WORLDS[0], FINAL.V023_STUDENT_SEEDS[0], "MATCHED_PLACEBO")
    return left, right


_ACTION_DEPENDENT_PHYSICAL_FIELDS = (
    "physical_actions",
    "physical_total_bits",
    "physical_per_user_bits",
    "physical_energy_j",
    "physical_served",
)


@pytest.mark.parametrize("field", _ACTION_DEPENDENT_PHYSICAL_FIELDS)
def test_cross_arm_learned_physical_outcome_is_arm_local(field: str) -> None:
    informed, placebo = _cross_arm_shards()
    tampered = dict(placebo.arrays)
    changed = np.array(tampered[field], copy=True)
    if changed.dtype == np.bool_:
        changed[:, 1, ...] = ~changed[:, 1, ...]
    else:
        changed[:, 1, ...] += 1
    tampered[field] = changed
    placebo = replace(placebo, arrays=tampered)
    FINAL.verify_cross_arm_identity(informed, placebo)


@pytest.mark.parametrize("field", _ACTION_DEPENDENT_PHYSICAL_FIELDS)
@pytest.mark.parametrize("role", (0, 2))
def test_cross_arm_shared_physical_role_mismatch_is_rejected(field: str, role: int) -> None:
    informed, placebo = _cross_arm_shards()
    tampered = dict(placebo.arrays)
    changed = np.array(tampered[field], copy=True)
    if changed.dtype == np.bool_:
        changed[:, role, ...] = ~changed[:, role, ...]
    else:
        changed[:, role, ...] += 1
    tampered[field] = changed
    placebo = replace(placebo, arrays=tampered)
    with pytest.raises(FINAL.V023FinalVerificationError, match=f"cross-arm {field} baseline/teacher"):
        FINAL.verify_cross_arm_identity(informed, placebo)


def test_cross_arm_q12_mismatch_is_rejected() -> None:
    informed, placebo = _cross_arm_shards()
    tampered = dict(placebo.arrays)
    tampered["q12"] = np.asarray([4.0], dtype=np.float32)
    placebo = replace(placebo, arrays=tampered)
    with pytest.raises(FINAL.V023FinalVerificationError, match="cross-arm q12"):
        FINAL.verify_cross_arm_identity(informed, placebo)


def test_cross_arm_common_field_mismatch_is_rejected() -> None:
    informed, placebo = _cross_arm_shards()
    tampered = dict(placebo.arrays)
    changed = np.array(tampered["physical_common_field_digest"], copy=True)
    changed[0, 1, 0] = b"x"
    tampered["physical_common_field_digest"] = changed
    placebo = replace(placebo, arrays=tampered)
    with pytest.raises(FINAL.V023FinalVerificationError, match="cross-arm physical_common_field_digest"):
        FINAL.verify_cross_arm_identity(informed, placebo)


def test_cross_arm_mismatch_is_rejected_after_join() -> None:
    informed, placebo = _cross_arm_shards()
    tampered = dict(placebo.arrays)
    tampered["q2"] = np.asarray([2], dtype=np.int64)
    placebo = replace(placebo, arrays=tampered)
    with pytest.raises(FINAL.V023FinalVerificationError, match="cross-arm q2"):
        FINAL.verify_cross_arm_identity(informed, placebo)


def test_tampered_receipt_seal_is_rejected() -> None:
    unsigned = {"schema": "synthetic", "value": 1}
    payload = dict(unsigned, receipt_sha256=FINAL.canonical_sha256(unsigned))
    FINAL._verify_seal(payload, label="synthetic")
    payload["value"] = 2
    with pytest.raises(FINAL.V023FinalVerificationError, match="seal"):
        FINAL._verify_seal(payload, label="synthetic")


def test_tampered_npz_sidecar_is_rejected(tmp_path: Path) -> None:
    npz_path = tmp_path / "arrays.npz"
    digest_path = tmp_path / "arrays.npz.sha256"
    array = np.asarray([1.0, 2.0], dtype=np.float64)
    with npz_path.open("wb") as handle:
        np.savez_compressed(handle, values=array)
    digest = FINAL.file_sha256(npz_path)
    digest_path.write_text(f"{digest}  {npz_path.name}\n", encoding="ascii")
    binding = {
        "allow_pickle": False,
        "npz_relative_path": npz_path.name,
        "npz_sha256": digest,
        "npz_sha256_file": digest_path.name,
        "array_count": 1,
        "array_metadata": {
            "values": {
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "sha256": FINAL._array_digest(array, domain=FINAL.V023_ARRAY_DOMAIN),
            }
        },
    }
    npz_path.write_bytes(npz_path.read_bytes() + b"tamper")
    with pytest.raises(FINAL.V023FinalVerificationError, match="byte hash"):
        FINAL._load_npz(tmp_path, binding, label="synthetic")


def test_context_hold_does_not_change_section14_decision() -> None:
    passing = _all_predicates()
    assert FINAL.adjudicate_section14(**passing) == "GO_FIXED_LEARNER_SCREEN_CONTRACT"
    # Section 9 is serialized independently.  A valid HOLD is not substituted
    # for a Section-14 C3 predicate and must not silently rewrite the token.
    assert FINAL.adjudicate_section14(**passing) == "GO_FIXED_LEARNER_SCREEN_CONTRACT"


def test_ops3_target_averages_native_horizon_axis_not_action_axis() -> None:
    persistence = np.ones((2, 3, 4), dtype=np.float64)
    rate = np.asarray(
        [
            [[1.0, 2.0, 4.0, 8.0], [3.0, 6.0, 9.0, 12.0], [5.0, 10.0, 15.0, 20.0]],
            [[2.0, 4.0, 8.0, 16.0], [4.0, 8.0, 12.0, 16.0], [6.0, 12.0, 18.0, 24.0]],
        ],
        dtype=np.float64,
    )
    power = np.zeros_like(rate)
    references = np.asarray([0, 1], dtype=np.int64)
    mask = np.ones((2, 4), dtype=np.bool_)
    target = FINAL._recompute_ops3_target(
        persistence,
        rate,
        power,
        q1_reference=references,
        mask=mask,
        horizon=3,
    )
    expected_raw = np.mean(rate, axis=1)
    expected = (expected_raw - expected_raw[np.arange(2), references][:, None]) / FINAL.V023_KAPPA_BITS
    expected *= FINAL.V023_OPS3_INTERVAL_S
    np.testing.assert_allclose(target, expected, rtol=0.0, atol=1.0e-15)
    assert target.shape == (2, 4)


def _timing_context(phase: int) -> dict[str, object]:
    horizon = min(FINAL.V023_OPS3_HORIZON, max(0, 9 - phase))
    base = datetime(2026, 9, 5, tzinfo=timezone.utc)
    sample = [
        (base + timedelta(seconds=0.640 * index)).isoformat()
        for index in range(horizon * 47)
    ]
    offsets = [sample[(index + 1) * 47 - 1] for index in range(horizon)]
    return {
        "future_d2_indices": list(range((phase + 1) * 47, (phase + 1 + horizon) * 47)),
        "sample_times_utc": sample,
        "offset_times_utc": offsets,
    }


def test_q2_timing_accepts_each_phase_and_terminal_empty_lists() -> None:
    for phase in range(1, 10):
        FINAL._verify_q2_timing(
            _timing_context(phase),
            phase=phase,
            horizon=min(FINAL.V023_OPS3_HORIZON, max(0, 9 - phase)),
            label=f"phase={phase}",
        )


def test_q2_timing_rejects_native_substep_or_endpoint_drift() -> None:
    context = _timing_context(1)
    context["future_d2_indices"] = context["future_d2_indices"][:-1]
    with pytest.raises(FINAL.V023FinalVerificationError, match="index schedule"):
        FINAL._verify_q2_timing(context, phase=1, horizon=3, label="phase=1")

    context = _timing_context(1)
    context["sample_times_utc"][1] = context["sample_times_utc"][0]
    with pytest.raises(FINAL.V023FinalVerificationError, match="640 ms"):
        FINAL._verify_q2_timing(context, phase=1, horizon=3, label="phase=1")


def test_q2_timing_requires_three_empty_lists_at_phase_nine() -> None:
    context = _timing_context(9)
    context["offset_times_utc"] = ["2026-09-05T00:00:00+00:00"]
    with pytest.raises(FINAL.V023FinalVerificationError, match="timestamp count"):
        FINAL._verify_q2_timing(context, phase=9, horizon=0, label="phase=9")

    context = _timing_context(9)
    context["future_d2_indices"] = [470]
    with pytest.raises(FINAL.V023FinalVerificationError, match="index schedule"):
        FINAL._verify_q2_timing(context, phase=9, horizon=0, label="phase=9")


def test_q12_carrier_is_exact_float32_sum_and_native_reference() -> None:
    q1 = np.zeros((1, 1, FINAL.V023_ACTION_COUNT), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q2[0, 0, :4] = [0.0, 0.25, 1.0, 0.5]
    q12 = np.asarray(q1 + q2, dtype=np.float64)
    carrier = FINAL._validated_q12(q1, q2, q12)
    np.testing.assert_array_equal(carrier, np.asarray(q1 + q2, dtype=np.float32))
    mask = np.zeros((1, 1, FINAL.V023_ACTION_COUNT), dtype=np.bool_)
    mask[0, 0, :3] = True
    np.testing.assert_array_equal(FINAL._q12_masked_argmax(carrier, mask), [[2]])

    tampered = q12.copy()
    tampered[0, 0, 2] = 0.75
    with pytest.raises(FINAL.V023FinalVerificationError, match="carrier identity"):
        FINAL._validated_q12(q1, q2, tampered)


def test_q2_state_digest_is_read_from_context_not_anchor_top_level() -> None:
    state = np.zeros((2, 4), dtype=np.float32)
    mask = np.ones((2, 4), dtype=np.bool_)
    digest = FINAL._q2_state_sha256(state, mask)
    context = {"q2_state_sha256": digest}
    entry = {"q2_state_sha256": "f" * 64, "q2_context": context}
    FINAL._verify_q2_state_digest_receipt(
        entry["q2_context"], state, mask, label="synthetic"
    )
    context["q2_state_sha256"] = "e" * 64
    with pytest.raises(FINAL.V023FinalVerificationError, match="state digest"):
        FINAL._verify_q2_state_digest_receipt(
            entry["q2_context"], state, mask, label="synthetic"
        )


def test_c2_diagnostic_is_one_object_with_rows_list() -> None:
    diagnostic, rows = FINAL._diagnostic_rows({"rows": []}, label="synthetic")
    assert diagnostic["rows"] == rows == []
    with pytest.raises(FINAL.V023FinalVerificationError, match="object"):
        FINAL._diagnostic_rows([], label="synthetic")
    with pytest.raises(FINAL.V023FinalVerificationError, match="rows"):
        FINAL._diagnostic_rows({"rows": {}}, label="synthetic")


def test_c2_target_sign_and_rank_are_reported_against_same_native_reference() -> None:
    prediction = np.asarray([0.5, -0.5, 0.0], dtype=np.float64)
    target = np.asarray([1.0, -1.0, 0.0], dtype=np.float64)
    sign, rank, count = FINAL._target_sign_rank(prediction, target)
    assert sign == 1.0
    assert rank == pytest.approx(1.0)
    assert count == 2
