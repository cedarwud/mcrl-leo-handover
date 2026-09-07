"""W-118 -- synthetic, pure-data V0.7 C2 D2 adjudication gates."""

from __future__ import annotations

from dataclasses import replace
import hashlib

import numpy as np

from mcrl.runtime.ee_axis_v07_c2_d2 import (
    D2_INVALID_NO_INFERENCE,
    D2_PASS_AUTHORIZE_D3_IMPLEMENTATION,
    D2PhysicalAnchor,
    D2Q13SurfaceReceipt,
    D2SelectionReceipt,
    D2ActionRecord,
    D2LineageDecisionCapture,
    D2MechanicsReceipt,
    D2_DEFAULT_KAPPA_BITS,
    D2_INTERVAL_S,
    D2_LAMBDA_BITS_PER_J,
    D2_SEEDS,
    adjudicate_d2,
    average_ranks,
    spearman_rank_correlation,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import focal_next_surplus_target


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _anchor(seed: int, *, late: bool) -> D2PhysicalAnchor:
    step = 5 if late else 1
    focal_user = 1 if late else 0
    eligible = ((5, (1, 2, 3)),) if late else ((1, (0, 1, 2)),)
    mask = np.zeros(28, dtype=np.bool_)
    if seed % 2:
        mask[[1, 4, 7, 9, 12]] = True
    else:
        mask[[0, 1, 2, 3]] = True
    return D2PhysicalAnchor(
        seed=seed,
        step_index=step,
        focal_user=focal_user,
        window="late" if late else "early",
        native_action_mask=mask,
        selection=D2SelectionReceipt(
            window="late" if late else "early",
            eligible_users_by_step=eligible,
        ),
        anchor_sha256=_digest(f"anchor:{seed}:{step}:{focal_user}"),
        state_sha256=_digest(f"state:{seed}"),
        carrier_sha256=_digest(f"carrier:{seed}"),
    )


def _captures(*, constant_q: bool = False, positive: bool = True) -> tuple[D2LineageDecisionCapture, ...]:
    captures: list[D2LineageDecisionCapture] = []
    kappa = D2_DEFAULT_KAPPA_BITS
    for seed in D2_SEEDS:
        for late in (False, True):
            anchor = _anchor(seed, late=late)
            legal = anchor.legal_actions
            reference = legal[0] if constant_q else legal[-1]
            for lineage_index, lineage in enumerate(("q13-a", "q13-b", "q13-c")):
                q1 = np.zeros(28, dtype=np.float64) if constant_q else np.arange(28, dtype=np.float64)
                q3 = np.zeros(28, dtype=np.float64)
                q13 = D2Q13SurfaceReceipt(
                    q1_surface=q1,
                    q3_surface=q3,
                    q1_checkpoint_sha256=_digest(f"q1-checkpoint:{lineage}"),
                    q3_checkpoint_sha256=_digest(f"q3-checkpoint:{lineage}"),
                    policy_sha256=_digest(f"policy:{lineage}"),
                )
                rows: list[D2ActionRecord] = []
                for position, candidate in enumerate(legal):
                    if candidate == reference:
                        target_value = 0.0
                    else:
                        target_value = (1.0 if positive else -1.0) * kappa * (0.10 + 0.03 * position)
                    reference_rate = 100.0 if positive else 10.0 * kappa
                    candidate_rate = reference_rate + target_value / D2_INTERVAL_S
                    target = focal_next_surplus_target(
                        lambda_bits_per_j=D2_LAMBDA_BITS_PER_J,
                        interval_s=D2_INTERVAL_S,
                        candidate_focal_rate_bps=candidate_rate,
                        reference_focal_rate_bps=reference_rate,
                        candidate_full_power_w=10.0,
                        candidate_without_focal_power_w=9.0,
                        reference_full_power_w=10.0,
                        reference_without_focal_power_w=9.0,
                    )
                    if anchor.focal_user == 0:
                        opening_reference = np.asarray([reference, -1], dtype=np.int64)
                        opening_candidate = np.asarray([candidate, -1], dtype=np.int64)
                    else:
                        opening_reference = np.asarray([-1, reference], dtype=np.int64)
                        opening_candidate = np.asarray([-1, candidate], dtype=np.int64)
                    mechanics = D2MechanicsReceipt(
                        opening_reference_actions=opening_reference,
                        opening_candidate_actions=opening_candidate,
                        successor_reference_action_sha256=_digest(
                            f"successor-ref:{seed}:{anchor.step_index}:{lineage}"
                        ),
                        successor_candidate_action_sha256=_digest(
                            f"successor-cand:{seed}:{anchor.step_index}:{lineage}:{candidate}"
                        ),
                        crn_sha256=_digest(f"crn:{seed}:{anchor.step_index}:{anchor.focal_user}"),
                        policy_sha256=q13.policy_sha256,
                    )
                    rows.append(
                        D2ActionRecord(
                            candidate_action=candidate,
                            reference_action=reference,
                            target=target,
                            mechanics=mechanics,
                        )
                    )
                captures.append(
                    D2LineageDecisionCapture(
                        anchor=anchor,
                        lineage=lineage,
                        q13=q13,
                        rows=tuple(reversed(rows)),
                    )
                )
    # The adjudicator itself sorts these; shuffling here proves the input
    # merge order is not part of the digest.
    return tuple(reversed(captures))


def test_d2_passes_all_gates_and_digest_is_order_independent() -> None:
    captures = _captures()
    result = adjudicate_d2(captures)
    assert result.verdict == D2_PASS_AUTHORIZE_D3_IMPLEMENTATION
    assert result.metrics.g_m_pass is True
    assert result.metrics.physical_anchors == 20
    assert result.metrics.lineage_cells == 60
    assert result.metrics.g_r_median_spearman is not None
    assert result.metrics.g_r_median_spearman >= 0.60
    assert result.metrics.g_s_zero_denominator_cells == 0
    assert result.metrics.g_v_iqr_cells == 60
    assert result.metrics.g_p_positive_anchors == 20
    assert result.to_document() == adjudicate_d2(tuple(reversed(captures))).to_document()
    assert result.to_document()["formula_constants"] == {
        "lambda_bits_per_j": D2_LAMBDA_BITS_PER_J.hex(),
        "interval_s": D2_INTERVAL_S.hex(),
        "kappa_bits": D2_DEFAULT_KAPPA_BITS.hex(),
        "iqr_method": "linear",
    }


def test_kappa_is_frozen_and_cannot_change_the_verdict() -> None:
    assert (
        adjudicate_d2(_captures(), kappa_bits=100.0 * D2_DEFAULT_KAPPA_BITS).verdict
        == D2_INVALID_NO_INFERENCE
    )


def test_spearman_uses_average_ranks_for_ties() -> None:
    np.testing.assert_allclose(average_ranks([1.0, 1.0, 3.0]), [1.5, 1.5, 3.0])
    assert np.isclose(
        spearman_rank_correlation([1.0, 1.0, 3.0], [1.0, 2.0, 3.0]),
        np.sqrt(3.0) / 2.0,
    )


def test_selection_receipt_allows_one_eligible_user_with_three_actions() -> None:
    anchor = _anchor(D2_SEEDS[0], late=False)
    one_user = replace(
        anchor.selection,
        eligible_users_by_step=((1, (0,)),),
    )
    replace(anchor, selection=one_user).verify()


def test_missing_or_mask_drift_is_invalid() -> None:
    captures = _captures()
    assert adjudicate_d2(captures[:-1]).verdict == D2_INVALID_NO_INFERENCE
    changed = captures[0]
    mask = changed.anchor.native_action_mask.copy()
    legal = changed.anchor.legal_actions
    mask[legal[-1]] = False
    mask[28 - 1] = True
    changed_anchor = replace(changed.anchor, native_action_mask=mask)
    assert adjudicate_d2((replace(changed, anchor=changed_anchor),) + captures[1:]).verdict == D2_INVALID_NO_INFERENCE


def test_zero_q13_scale_denominator_is_a_scientific_fail_not_inference() -> None:
    result = adjudicate_d2(_captures(constant_q=True))
    assert result.verdict != D2_INVALID_NO_INFERENCE
    assert result.metrics.g_s_zero_denominator_cells == 60
    assert result.metrics.g_s_pass is False
    assert result.verdict.endswith("C2_FORMULA_OR_SOURCE_DESIGN")


def test_no_positive_alternative_headroom_fails_g_p() -> None:
    result = adjudicate_d2(_captures(positive=False))
    assert result.verdict.endswith("C2_FORMULA_OR_SOURCE_DESIGN")
    assert result.metrics.g_p_positive_anchors == 0
    assert result.metrics.g_p_pass is False


def test_nonfinite_surface_and_raw_formula_tampering_are_invalid() -> None:
    captures = _captures()
    bad_q1 = captures[0].q13.q1_surface.copy()
    bad_q1[0] = np.nan
    bad_q13 = replace(captures[0].q13, q1_surface=bad_q1)
    assert adjudicate_d2((replace(captures[0], q13=bad_q13),) + captures[1:]).verdict == D2_INVALID_NO_INFERENCE

    first_row = captures[0].rows[0]
    bad_target = replace(
        first_row.target,
        z2_focal_next_surplus_bits=first_row.target.z2_focal_next_surplus_bits + 1.0,
    )
    bad_row = replace(first_row, target=bad_target)
    bad_capture = replace(captures[0], rows=(bad_row,) + captures[0].rows[1:])
    assert adjudicate_d2((bad_capture,) + captures[1:]).verdict == D2_INVALID_NO_INFERENCE


def test_branch_local_noop_crn_and_retry_receipts_fail_closed() -> None:
    captures = _captures()
    first = captures[0]
    row = first.rows[0]
    bad_mechanics = replace(row.mechanics, focal_removal_only=False)
    bad_row = replace(row, mechanics=bad_mechanics)
    bad_capture = replace(first, rows=(bad_row,) + first.rows[1:])
    assert adjudicate_d2((bad_capture,) + captures[1:]).verdict == D2_INVALID_NO_INFERENCE

    bad_mechanics = replace(row.mechanics, crn_sha256=_digest("different-crn"))
    bad_row = replace(row, mechanics=bad_mechanics)
    bad_capture = replace(first, rows=(bad_row,) + first.rows[1:])
    assert adjudicate_d2((bad_capture,) + captures[1:]).verdict == D2_INVALID_NO_INFERENCE

    bad_mechanics = replace(row.mechanics, retry_count=1)
    bad_row = replace(row, mechanics=bad_mechanics)
    bad_capture = replace(first, rows=(bad_row,) + first.rows[1:])
    assert adjudicate_d2((bad_capture,) + captures[1:]).verdict == D2_INVALID_NO_INFERENCE


def test_reference_successor_must_be_invariant_within_a_cell() -> None:
    captures = _captures()
    first = captures[0]
    row = first.rows[0]
    changed_target = focal_next_surplus_target(
        lambda_bits_per_j=row.target.lambda_bits_per_j,
        interval_s=row.target.interval_s,
        candidate_focal_rate_bps=row.target.candidate_focal_rate_bps + 1000.0,
        reference_focal_rate_bps=row.target.reference_focal_rate_bps + 1000.0,
        candidate_full_power_w=row.target.candidate_full_power_w,
        candidate_without_focal_power_w=row.target.candidate_without_focal_power_w,
        reference_full_power_w=row.target.reference_full_power_w,
        reference_without_focal_power_w=row.target.reference_without_focal_power_w,
    )
    changed_row = replace(row, target=changed_target)
    changed_capture = replace(first, rows=(changed_row,) + first.rows[1:])
    assert (
        adjudicate_d2((changed_capture,) + captures[1:]).verdict
        == D2_INVALID_NO_INFERENCE
    )
