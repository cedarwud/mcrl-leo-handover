"""W-192 -- production binding of LC-SRS predecision and teacher receipts."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_lcsrs_three_route import DetachedQ12Snapshot
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.observation_provenance import (
    build_native_observation_provenance,
    numpy_rng_state_sha256,
)
from mcrl.runtime.ee_axis_lcsrs_c3_encoder import LCSRSC3PredecisionCapture
from mcrl.runtime.ee_axis_lcsrs_c3_pipeline import (
    LCSRSC3BoundAnchor,
    LCSRSC3PipelineError,
    bind_lcsrs_c3_anchor,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import (
    LCSRS_ACTION_CONTEXT_DIM,
    LCSRS_TOKEN_DIM,
    assemble_c3_view,
)
from mcrl.runtime.ee_axis_lcsrs_c3_teacher import (
    LCSRSFourProfileDraw,
    build_lcsrs_two_user_teacher,
    build_lcsrs_topology_teacher,
    lcsrs_action_sha256,
)
from mcrl.runtime.ee_axis_lcsrs_c3_topology import (
    LCSRSC3AnchorCapture,
    enumerate_lcsrs_c3_anchor,
)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _predecision(*, phase: int = 1) -> LCSRSC3PredecisionCapture:
    """Build a small but fully authenticated two-pair, four-user anchor."""

    users = 4
    action_mask = np.zeros((users, NUM_ACTIONS), dtype=np.bool_)
    action_mask[:, :3] = True
    opening = np.array(action_mask, copy=True)
    keys = np.full((users, NUM_ACTIONS, 2), -1, dtype=np.int64)
    key_rows = (
        ((10, 0), (30, 2), (100, 0)),
        ((10, 0), (30, 2), (101, 0)),
        ((30, 2), (10, 0), (102, 0)),
        ((30, 2), (10, 0), (103, 0)),
    )
    for user, row in enumerate(key_rows):
        keys[user, :3] = np.asarray(row, dtype=np.int64)

    q12 = np.full((users, NUM_ACTIONS), -100.0, dtype=np.float32)
    q12[:, :3] = np.asarray([10.0, 4.0, 3.0], dtype=np.float32)
    observation_sinr = np.ones((users, NUM_ACTIONS), dtype=np.float64)
    rng = np.random.default_rng(192)
    field = KeyedFadingField.from_components("w192", phase)
    provenance = build_native_observation_provenance(
        step_index=phase,
        candidate_sinr=observation_sinr,
        rng=rng,
        rng_pre_state_sha256=numpy_rng_state_sha256(rng),
        fading_field=field,
        sinr_provenance="w192-authenticated-fixture",
    )
    state_sha = _digest(q12.tobytes(order="C") + b"state")
    snapshot = DetachedQ12Snapshot(
        q1=q12,
        q2=np.zeros_like(q12),
        source_state_digest=state_sha,
        native_observation_event_digest=provenance.content_digest,
        model_digest=_digest(q12.tobytes(order="C") + b"model"),
    )
    capture = LCSRSC3AnchorCapture(
        world_id=192,
        phase=phase,
        anchor_id=f"w192-phase-{phase}",
        q12_snapshot=snapshot,
        action_mask=action_mask,
        opening_feasibility=opening,
        physical_keys=keys,
    )
    topology = enumerate_lcsrs_c3_anchor(capture)

    context = np.zeros(
        (users, NUM_ACTIONS, LCSRS_ACTION_CONTEXT_DIM), dtype=np.float32
    )
    margins = np.tanh(q12.astype(np.float64) - q12[:, [0]].astype(np.float64))
    context[:, :, 23] = np.where(action_mask, margins, 0.0).astype(np.float32)
    tokens = np.zeros(
        (users, NUM_ACTIONS, users + 1, LCSRS_TOKEN_DIM), dtype=np.float32
    )
    token_mask = np.zeros(
        (users, NUM_ACTIONS, users + 1), dtype=np.bool_
    )
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0
    for pair in topology.pairs:
        for user, action in zip(pair.member_users, pair.designated_actions, strict=True):
            tokens[user, action, users, 2:5] = 1.0
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    return LCSRSC3PredecisionCapture(
        topology=topology,
        view=view,
        native_observation_provenance=provenance,
        state_schema="w192-native-state-v1",
        state_schema_sha256=_digest(b"state-schema"),
        state_sha256=state_sha,
    )


def _draw(
    index: int,
    *,
    member_users: tuple[int, int],
    proposed_actions: tuple[int, int],
    reference_actions: np.ndarray | None = None,
) -> LCSRSFourProfileDraw:
    users = 4
    references = (
        np.zeros(users, dtype=np.int64)
        if reference_actions is None
        else np.asarray(reference_actions, dtype=np.int64)
    )
    actions = np.repeat(references[None, :], 4, axis=0)
    actions[1, member_users[0]] = proposed_actions[0]
    actions[2, member_users[1]] = proposed_actions[1]
    actions[3, list(member_users)] = np.asarray(proposed_actions, dtype=np.int64)
    bits = np.full((4, users), 100.0, dtype=np.float64)
    energy = np.full(4, 10.0, dtype=np.float64)
    field = _digest(f"w192-draw-{index}".encode("ascii"))
    return LCSRSFourProfileDraw(
        draw_index=index,
        profile_actions=actions,
        profile_bits=bits,
        profile_energy_j=energy,
        common_field_sha256_by_profile=(field,) * 4,
        action_sha256_by_profile=tuple(lcsrs_action_sha256(row) for row in actions),
    )


def _teachers(
    predecision: LCSRSC3PredecisionCapture,
) -> tuple:
    return tuple(
        build_lcsrs_topology_teacher(
            topology=predecision.topology,
            pair=pair,
            draws=[
                _draw(
                    index,
                    member_users=pair.member_users,
                    proposed_actions=pair.designated_actions,
                )
                for index in range(32)
            ],
            lambda_bits_per_j=1.0,
            kappa_bits=2.0,
        )
        for pair in predecision.topology.pairs
    )


def _standalone_teacher(
    *,
    pair_id: str,
    member_users: tuple[int, int],
    proposed_actions: tuple[int, int],
    reference_actions: np.ndarray | None = None,
):
    legal = np.zeros((4, NUM_ACTIONS), dtype=np.bool_)
    legal[:, :3] = True
    references = (
        np.zeros(4, dtype=np.int64)
        if reference_actions is None
        else np.asarray(reference_actions, dtype=np.int64)
    )
    return build_lcsrs_two_user_teacher(
        pair_id=pair_id,
        member_users=np.asarray(member_users, dtype=np.int64),
        proposed_actions=np.asarray(proposed_actions, dtype=np.int64),
        reference_actions=references,
        legal_mask=legal,
        draws=[
            _draw(
                index,
                member_users=member_users,
                proposed_actions=proposed_actions,
                reference_actions=references,
            )
            for index in range(32)
        ],
        lambda_bits_per_j=1.0,
        kappa_bits=2.0,
    )


def test_bind_produces_one_immutable_surface_record_and_stable_digest() -> None:
    predecision = _predecision()
    teachers = _teachers(predecision)
    bound = bind_lcsrs_c3_anchor(predecision, teachers)

    assert isinstance(bound, LCSRSC3BoundAnchor)
    assert bound.topology is predecision.topology
    assert bound.view is predecision.view
    assert bound.surface.view is predecision.view
    assert bound.record.surface is bound.surface
    assert bound.record.q12_values.tolist() == predecision.topology.capture.q12_snapshot.q12.tolist()
    assert (bound.record.world_id, bound.record.phase, bound.record.anchor_id) == (
        predecision.topology.world_id,
        predecision.topology.phase,
        predecision.topology.anchor_id,
    )
    assert isinstance(bound.teachers, tuple)
    assert [teacher.pair_id for teacher in bound.teachers] == [
        pair.pair_id for pair in predecision.topology.pairs
    ]
    assert bound.verify() == bound.content_digest
    assert not bound.surface.normalized_targets.flags.writeable
    assert not bound.record.q12_values.flags.writeable
    assert len(bound.content_digest) == 64


def test_teacher_pair_set_must_be_exact_and_membership_must_match() -> None:
    predecision = _predecision()
    teachers = _teachers(predecision)
    with pytest.raises(LCSRSC3PipelineError, match="missing"):
        bind_lcsrs_c3_anchor(predecision, teachers[:-1])

    extra = _standalone_teacher(
        pair_id="extra-pair",
        member_users=(0, 1),
        proposed_actions=(1, 1),
    )
    with pytest.raises(LCSRSC3PipelineError, match="extra"):
        bind_lcsrs_c3_anchor(predecision, (*teachers, extra))

    duplicate = (*teachers, teachers[0])
    with pytest.raises(LCSRSC3PipelineError, match="duplicated"):
        bind_lcsrs_c3_anchor(predecision, duplicate)

    first_pair = predecision.topology.pairs[0]
    wrong = _standalone_teacher(
        pair_id=first_pair.pair_id,
        member_users=predecision.topology.pairs[1].member_users,
        proposed_actions=predecision.topology.pairs[1].designated_actions,
    )
    with pytest.raises(LCSRSC3PipelineError, match="member users"):
        bind_lcsrs_c3_anchor(predecision, (wrong, teachers[1]))


def test_teacher_profile_baseline_must_match_topology_reference_vector() -> None:
    predecision = _predecision()
    teachers = _teachers(predecision)
    first_pair = predecision.topology.pairs[0]
    drifted = _standalone_teacher(
        pair_id=first_pair.pair_id,
        member_users=first_pair.member_users,
        proposed_actions=first_pair.designated_actions,
        reference_actions=np.asarray([0, 0, 2, 0], dtype=np.int64),
    )
    with pytest.raises(LCSRSC3PipelineError, match="profile actions disagree"):
        bind_lcsrs_c3_anchor(predecision, (drifted, teachers[1]))


def test_teacher_reordering_is_canonical_but_tampering_and_phase_zero_fail_closed() -> None:
    predecision = _predecision()
    teachers = _teachers(predecision)
    first = bind_lcsrs_c3_anchor(predecision, teachers)
    reordered = bind_lcsrs_c3_anchor(predecision, tuple(reversed(teachers)))
    assert reordered.content_digest == first.content_digest
    assert reordered.surface.content_digest == first.surface.content_digest
    assert reordered.record.content_digest == first.record.content_digest

    tampered = teachers[0]
    object.__setattr__(tampered, "content_digest", "0" * 64)
    with pytest.raises(LCSRSC3PipelineError, match="teacher receipt verification"):
        bind_lcsrs_c3_anchor(predecision, teachers)

    phase_zero = _predecision(phase=0)
    zero_teachers = _teachers(phase_zero)
    with pytest.raises(LCSRSC3PipelineError, match="phase"):
        bind_lcsrs_c3_anchor(phase_zero, zero_teachers)


def test_bound_object_rejects_digest_tampering() -> None:
    predecision = _predecision()
    bound = bind_lcsrs_c3_anchor(predecision, _teachers(predecision))
    with pytest.raises(LCSRSC3PipelineError, match="content digest"):
        LCSRSC3BoundAnchor(
            predecision=bound.predecision,
            teachers=bound.teachers,
            surface=bound.surface,
            record=bound.record,
            content_digest="0" * 64,
        )
