from __future__ import annotations

from dataclasses import replace
import hashlib
from types import SimpleNamespace
import sys
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_forecast_adapter as forecast  # noqa: E402
import c2_temporal_fork_selection as selection  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _authority(label: str, *, anchor_sha256: str) -> C2.ForecastAuthority:
    return C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=anchor_sha256,
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward-source"),
        live_rng_state_sha256=digest("live-rng"),
        forecast_rng_state_sha256=digest(f"forecast-rng-{label}"),
        forecast_request_sha256=digest(f"forecast-request-{label}"),
        forecast_payload_sha256=digest(f"forecast-payload-{label}"),
        forecast_namespace="c2-v03/selection-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="selection-fixture-v1",
    )


def _candidate(
    *,
    action: int,
    key: tuple[int, int],
    passed: bool = True,
    context_suffix: str = "same",
    state_suffix: str = "same",
    focal: int = 0,
    users: int = 1,
) -> SimpleNamespace:
    state = np.asarray(
        [[0.25 + 0.01 * user, 0.5, 0.75] for user in range(users)],
        dtype=np.float32,
    )
    mask = np.zeros((users, C2.ACTION_DIM), dtype=np.bool_)
    mask[:, 3] = True
    mask[:, 4] = True
    mask[:, 11] = True
    if state_suffix != "same":
        state = state.copy()
        state[focal, 0] = 0.75
    bindings_by_user = tuple(
        (
            C2.ActionBinding(3, (50001 + user, 1)),
            C2.ActionBinding(4, (50001 + user, 2)),
            C2.ActionBinding(11, (50001 + user, 11)),
        )
        for user in range(users)
    )
    bindings = bindings_by_user[focal]
    reference_key = (50001 + focal, 11)
    anchor_payload = {
        "schema": "selection-anchor-v1",
        "step_index": 17,
        "focal_user": focal,
        "evaluation_seed": 29,
        "checkpoint_sha256": digest("checkpoint"),
        "environment_source_sha256": digest("environment"),
        "reward_source_sha256": digest("reward-source"),
        "state_matrix": state.tolist(),
        "mask_matrix": mask.tolist(),
        "states_sha256": forecast.canonical_payload_sha256(state),
        "masks_sha256": forecast.canonical_payload_sha256(mask),
        "action_bindings_by_user": tuple(
            tuple((row.action, row.physical_key) for row in user_rows)
            for user_rows in bindings_by_user
        ),
        "main_actions": (11,) * users,
        "main_physical_actions": tuple(
            (50001 + user, 11) for user in range(users)
        ),
        "pre_active_physical_ids": tuple(
            (50001 + user, 11) for user in range(users)
        ),
        "live_environment_rng_state": {"state": 100},
        "live_mobility_rng_state": {"state": 200},
        "context_suffix": context_suffix,
    }
    anchor_sha256 = forecast.canonical_payload_sha256(anchor_payload)
    authority = _authority(str(action), anchor_sha256=anchor_sha256)
    evidence = C2.TemporalForkEvidence(
        authority=authority,
        focal_user=focal,
        user_count=users,
        reference_action=11,
        candidate_action=action,
        reference_key=reference_key,
        candidate_key=key,
        opening_action_bindings=bindings,
        opening_action_table_sha256=C2.action_table_sha256(bindings),
        opening_state_sha256=forecast.canonical_payload_sha256(
            tuple(float(value) for value in state[focal].tolist())
        ),
        opening_mask_sha256=forecast.canonical_payload_sha256(
            tuple(bool(value) for value in mask[focal].tolist())
        ),
        reference_branch_trace_sha256=digest(f"reference-{action}"),
        candidate_branch_trace_sha256=digest(f"candidate-{action}"),
        hold_steps=C2.HOLD_STEPS,
        release_observed=True,
        branch_structurally_valid=True,
        nonfocal_policy_aligned=True,
        focal_served_all_steps=True,
        no_new_nonfocal_outage=True,
        activation_or_energy_path=True,
        reference_useful_bits=100.0,
        candidate_useful_bits=105.0 if passed else 99.0,
        reference_energy_j=10.0,
        candidate_energy_j=9.0,
        forecast_hold_r2_margin=0.5 if passed else -0.5,
        forecast_full_r2_margin=0.5 if passed else -0.5,
    )
    certificate = C2.certify_temporal_fork(evidence)
    assert certificate.passed is passed
    build = SimpleNamespace(
        authority=authority,
        evidence=evidence,
        certificate=certificate,
        reference_trace_sha256=certificate.reference_branch_trace_sha256,
        candidate_trace_sha256=certificate.candidate_branch_trace_sha256,
        forecast_request_sha256=authority.forecast_request_sha256,
        forecast_payload_sha256=authority.forecast_payload_sha256,
    )
    observation = SimpleNamespace(state_matrix=state, masks=mask)
    anchor = SimpleNamespace(
        anchor_payload=anchor_payload,
        anchor_sha256=anchor_sha256,
        focal_user=focal,
        states=tuple(state[user] for user in range(users)),
        masks=tuple(mask[user] for user in range(users)),
        observation=observation,
        action_bindings_by_user=bindings_by_user,
        main_actions=(11,) * users,
        main_physical_actions=tuple(
            (50001 + user, 11) for user in range(users)
        ),
    )
    return SimpleNamespace(
        build=build,
        anchor=anchor,
        candidate_key=key,
        phase="forecast_complete",
    )


class FakeQ2F:
    objective_index = 1
    policy_version = 7
    online_network_state_hash = digest("q2f-network")

    def __init__(self, values: dict[int, float]):
        self.values = values
        self.calls: list[tuple[int, int]] = []

    def q_values(self, states: np.ndarray) -> np.ndarray:
        assert states.shape == (1, 3)
        row = np.full(C2.ACTION_DIM, -100.0, dtype=np.float64)
        for action, value in self.values.items():
            row[action] = value
        return row[None, :]


def test_k0_failed_certificates_fall_back_to_main_without_choice():
    failed = _candidate(action=3, key=(50001, 1), passed=False)
    result = selection.select_prepared_fork(
        [failed],
        behavior_rng=np.random.default_rng(1),
        preoutcome_timestamp_ns=100,
    )
    assert result.prepared is None
    assert result.behavior_probability == 1.0
    assert result.receipt.mode == selection.CHOICE_MODE_FALLBACK
    assert result.receipt.support == ()
    assert result.receipt.selected_option_id is None


def test_k1_is_forced_certificate_control_and_does_not_rank():
    candidate = _candidate(action=3, key=(50001, 1))
    result = selection.select_prepared_fork(
        [candidate],
        behavior_rng=np.random.default_rng(2),
        epsilon=1.0,
        preoutcome_timestamp_ns=101,
    )
    assert result.prepared is candidate
    assert result.receipt.mode == selection.CHOICE_MODE_FORCED
    assert result.receipt.behavior_probability == 1.0
    assert result.receipt.selected_index == 0
    assert result.receipt.selected_option_id == candidate.build.certificate.option_id
    assert result.receipt.selected_focal_user == 0
    assert result.receipt.selected_action == 3
    assert result.receipt.selected_physical_key == (50001, 1)
    assert result.receipt.scores == ()
    assert result.receipt.greedy_index is None
    assert result.receipt.q2f_policy_version is None


def test_q2f_logit_flip_changes_selected_prepared_fork():
    left = _candidate(action=3, key=(50001, 1))
    right = _candidate(action=4, key=(50001, 2))
    first = selection.select_prepared_fork(
        [left, right],
        q2f=FakeQ2F({3: 9.0, 4: 1.0}),
        behavior_rng=np.random.default_rng(3),
        epsilon=0.0,
        preoutcome_timestamp_ns=102,
    )
    second = selection.select_prepared_fork(
        [left, right],
        q2f=FakeQ2F({3: 1.0, 4: 9.0}),
        behavior_rng=np.random.default_rng(3),
        epsilon=0.0,
        preoutcome_timestamp_ns=102,
    )
    assert first.prepared is left
    assert second.prepared is right
    assert first.receipt.scores == (9.0, 1.0)
    assert second.receipt.scores == (1.0, 9.0)
    assert first.receipt.behavior_probability == 1.0


def test_q2f_can_choose_across_focal_local_anchors_at_one_global_context():
    left = _candidate(
        action=3,
        key=(50001, 1),
        focal=0,
        users=2,
    )
    right = _candidate(
        action=4,
        key=(50002, 2),
        focal=1,
        users=2,
    )

    result = selection.select_prepared_fork(
        [left, right],
        q2f=FakeQ2F({3: 1.0, 4: 9.0}),
        behavior_rng=np.random.default_rng(30),
        epsilon=0.0,
        preoutcome_timestamp_ns=102,
    )

    assert result.prepared is right
    assert tuple(item.focal_user for item in result.receipt.support) == (0, 1)
    assert len({item.anchor_sha256 for item in result.receipt.support}) == 2
    assert result.receipt.anchor_sha256 is None
    assert len({item.anchor_context_sha256 for item in result.receipt.support}) == 1


def test_epsilon_greedy_receipt_reports_exact_probability():
    left = _candidate(action=3, key=(50001, 1))
    right = _candidate(action=4, key=(50001, 2))
    q2f = FakeQ2F({3: 9.0, 4: 1.0})
    result = selection.select_prepared_fork(
        [left, right],
        q2f=q2f,
        behavior_rng=np.random.default_rng(0),
        epsilon=0.2,
        preoutcome_timestamp_ns=103,
    )
    assert result.receipt.mode == selection.CHOICE_MODE_Q2F
    assert result.receipt.greedy_index == 0
    if result.receipt.selected_index == 0:
        assert result.behavior_probability == pytest.approx(0.9)
    else:
        assert result.behavior_probability == pytest.approx(0.1)
    assert result.receipt.q2f_policy_version == 7
    assert result.receipt.q2f_online_network_state_sha256 == digest("q2f-network")


def test_matched_random_is_uniform_and_reproducible_on_identical_support():
    left = _candidate(action=3, key=(50001, 1))
    right = _candidate(action=4, key=(50001, 2))
    first = selection.select_prepared_fork(
        [right, left],
        behavior_rng=np.random.default_rng(44),
        mode=selection.CHOICE_MODE_RANDOM,
        epsilon=0.9,
        preoutcome_timestamp_ns=104,
    )
    second = selection.select_prepared_fork(
        [right, left],
        behavior_rng=np.random.default_rng(44),
        mode=selection.CHOICE_MODE_RANDOM,
        epsilon=0.9,
        preoutcome_timestamp_ns=104,
    )
    assert first.prepared is second.prepared
    assert first.receipt.receipt_sha256 == second.receipt.receipt_sha256
    assert first.receipt.behavior_probability == 0.5
    assert first.receipt.scores == ()


def test_tie_break_is_deterministic_by_sorted_physical_id():
    low = _candidate(action=3, key=(50001, 1))
    high = _candidate(action=4, key=(50001, 2))
    result = selection.select_prepared_fork(
        [high, low],
        q2f=FakeQ2F({3: 2.0, 4: 2.0}),
        behavior_rng=np.random.default_rng(5),
        epsilon=0.0,
        preoutcome_timestamp_ns=105,
    )
    assert result.prepared is low
    assert result.receipt.support[0].physical_key == (50001, 1)


@pytest.mark.parametrize("kind", ["mixed_anchor", "duplicate", "tampered_state"])
def test_mixed_anchor_duplicate_or_tampered_state_is_rejected(kind):
    left = _candidate(action=3, key=(50001, 1))
    right = _candidate(action=4, key=(50001, 2))
    if kind == "mixed_anchor":
        changed_anchor = SimpleNamespace(
            **{
                **vars(right.anchor),
                "anchor_payload": {
                    **right.anchor.anchor_payload,
                    "step_index": 18,
                },
            }
        )
        changed = SimpleNamespace(**{**vars(right), "anchor": changed_anchor})
    elif kind == "tampered_state":
        changed_anchor = SimpleNamespace(
            **{
                **vars(right.anchor),
                "observation": SimpleNamespace(
                    state_matrix=np.asarray([[0.99, 0.5, 0.75]], dtype=np.float32),
                    masks=right.anchor.observation.masks,
                ),
            }
        )
        changed = SimpleNamespace(**{**vars(right), "anchor": changed_anchor})
    else:
        changed = (left, left)
    rows = changed if isinstance(changed, tuple) else (left, changed)
    with pytest.raises(selection.C2SelectionError):
        selection.select_prepared_fork(
            rows,
            q2f=FakeQ2F({3: 1.0, 4: 2.0}),
            behavior_rng=np.random.default_rng(6),
            preoutcome_timestamp_ns=106,
        )


def test_receipt_hash_binds_rng_and_is_deterministic_for_fixed_timestamp():
    left = _candidate(action=3, key=(50001, 1))
    right = _candidate(action=4, key=(50001, 2))
    first = selection.select_prepared_fork(
        [left, right],
        q2f=FakeQ2F({3: 1.0, 4: 2.0}),
        behavior_rng=np.random.default_rng(7),
        epsilon=0.1,
        preoutcome_timestamp_ns=107,
    )
    second = selection.select_prepared_fork(
        [left, right],
        q2f=FakeQ2F({3: 1.0, 4: 2.0}),
        behavior_rng=np.random.default_rng(7),
        epsilon=0.1,
        preoutcome_timestamp_ns=107,
    )
    assert first.receipt.receipt_sha256 == second.receipt.receipt_sha256
    assert first.receipt.behavior_rng_before_sha256 != first.receipt.behavior_rng_after_sha256
    assert first.receipt.claim_ceiling == selection.CLAIM_CEILING
    assert first.receipt.schema == selection.SELECTION_SCHEMA


def test_receipt_hash_binds_failed_support_rows_outside_selectable_support():
    candidate = _candidate(action=3, key=(50001, 1))
    completed = selection.candidate_schedule_row_from_prepared(
        candidate,
        schedule_index=0,
    )
    rejected = selection.rejected_candidate_schedule_row(
        schedule_index=1,
        focal_user=7,
        candidate_key=(50007, 3),
        outcome=selection.CANDIDATE_OUTCOME_SUPPORT_REJECTION,
        rejection_reason="focal_hold_expired",
    )
    first = selection.select_prepared_fork(
        [candidate],
        candidate_schedule=(completed, rejected),
        behavior_rng=np.random.default_rng(71),
        preoutcome_timestamp_ns=171,
    )
    changed = replace(rejected, rejection_reason="nonfocal_reference_unavailable")
    second = selection.select_prepared_fork(
        [candidate],
        candidate_schedule=(completed, changed),
        behavior_rng=np.random.default_rng(71),
        preoutcome_timestamp_ns=171,
    )

    assert first.receipt.candidate_schedule_size == 2
    assert first.receipt.candidate_schedule_sha256 != second.receipt.candidate_schedule_sha256
    assert first.receipt.receipt_sha256 != second.receipt.receipt_sha256
    with pytest.raises(selection.C2SelectionError, match="schedule differs"):
        selection.assert_prepared_selection_bound(
            replace(first, candidate_schedule=(completed, changed))
        )


def test_consumer_seal_revalidates_complete_support_and_selected_identity():
    left = _candidate(action=3, key=(50001, 1))
    right = _candidate(action=4, key=(50001, 2))
    result = selection.select_prepared_fork(
        [left, right],
        q2f=FakeQ2F({3: 1.0, 4: 9.0}),
        behavior_rng=np.random.default_rng(8),
        epsilon=0.2,
        preoutcome_timestamp_ns=108,
    )

    assert selection.assert_prepared_selection_bound(result) == result.receipt

    with pytest.raises(selection.C2SelectionError, match="self-consistent"):
        selection.assert_prepared_selection_bound(
            replace(
                result,
                receipt=replace(
                    result.receipt,
                    behavior_probability=result.receipt.behavior_probability / 2.0,
                ),
            )
        )
    with pytest.raises(selection.C2SelectionError, match="complete candidate set"):
        selection.assert_prepared_selection_bound(
            replace(result, candidate_set=(left,))
        )


def test_consumer_seal_accepts_k0_and_k1_controls():
    failed = _candidate(action=3, key=(50001, 1), passed=False)
    fallback = selection.select_prepared_fork(
        [failed],
        behavior_rng=np.random.default_rng(9),
        preoutcome_timestamp_ns=109,
    )
    forced_candidate = _candidate(action=4, key=(50001, 2))
    forced = selection.select_prepared_fork(
        [forced_candidate],
        behavior_rng=np.random.default_rng(10),
        preoutcome_timestamp_ns=110,
    )

    assert selection.assert_prepared_selection_bound(fallback) == fallback.receipt
    assert selection.assert_prepared_selection_bound(forced) == forced.receipt
