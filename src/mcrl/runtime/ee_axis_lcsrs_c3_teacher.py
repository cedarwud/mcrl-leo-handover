"""Exact two-user, four-profile LC-SRS teacher boundary for V0.23."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Sequence

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_coalition_residual_c3 import (
    CoalitionResidualC3Result,
    build_coalition_residual_c3,
)
from .ee_axis_lcsrs_c3_dataset import LCSRS_DRAW_COUNT, LCSRSPairTargets
from .ee_axis_lcsrs_c3_topology import (
    LCSRSC3AnchorTopologyReceipt,
    LCSRSC3ClosurePair,
)


LCSRS_PROFILE_ORDER = ("00", "10", "01", "11")
LCSRS_C3_TEACHER_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-two-user-teacher-v1"


class LCSRSC3TeacherError(MCRLContractError):
    """A two-user profile, common field, or formula receipt is malformed."""


def _readonly(value: object, *, dtype: np.dtype) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3TeacherError("teacher array cannot be materialised") from error
    result.setflags(write=False)
    return result


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LCSRSC3TeacherError(f"{field} must be lowercase SHA-256")
    return value


def lcsrs_action_sha256(actions: object) -> str:
    """Hash one complete native action vector under the V0.23 grammar."""

    values = _readonly(actions, dtype=np.dtype(np.int64))
    if values.ndim != 1 or values.size < 2:
        raise LCSRSC3TeacherError("action vector must contain at least two users")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-profile-actions-v1")
    digest.update(struct.pack(">I", int(values.size)))
    digest.update(np.ascontiguousarray(values).tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSFourProfileDraw:
    """One complete nonlinear 00/10/01/11 evaluation on one common field."""

    draw_index: int
    profile_actions: np.ndarray
    profile_bits: np.ndarray
    profile_energy_j: np.ndarray
    common_field_sha256_by_profile: tuple[str, str, str, str]
    action_sha256_by_profile: tuple[str, str, str, str]

    def __post_init__(self) -> None:
        if (
            isinstance(self.draw_index, bool)
            or not isinstance(self.draw_index, int)
            or not 0 <= self.draw_index < LCSRS_DRAW_COUNT
        ):
            raise LCSRSC3TeacherError("draw_index must be an integer in [0,31]")
        actions = _readonly(self.profile_actions, dtype=np.dtype(np.int64))
        bits = _readonly(self.profile_bits, dtype=np.dtype(np.float64))
        energy = _readonly(self.profile_energy_j, dtype=np.dtype(np.float64))
        if actions.ndim != 2 or actions.shape[0] != 4 or actions.shape[1] < 2:
            raise LCSRSC3TeacherError("profile_actions must have shape (4,U), U>=2")
        users = int(actions.shape[1])
        if bits.shape != (4, users) or not np.all(np.isfinite(bits)) or np.any(bits < 0.0):
            raise LCSRSC3TeacherError("profile_bits must be finite nonnegative shape (4,U)")
        if energy.shape != (4,) or not np.all(np.isfinite(energy)) or np.any(energy <= 0.0):
            raise LCSRSC3TeacherError("profile_energy_j must be finite positive shape (4,)")
        fields = tuple(
            _sha256(value, field="common-field digest")
            for value in self.common_field_sha256_by_profile
        )
        action_hashes = tuple(
            _sha256(value, field="action digest") for value in self.action_sha256_by_profile
        )
        if len(fields) != 4 or len(action_hashes) != 4:
            raise LCSRSC3TeacherError("profile digest tuples must follow 00/10/01/11")
        if len(set(fields)) != 1:
            raise LCSRSC3TeacherError("00/10/01/11 did not share one common random field")
        expected_action_hashes = tuple(lcsrs_action_sha256(row) for row in actions)
        if action_hashes != expected_action_hashes:
            raise LCSRSC3TeacherError("action digest disagrees with profile action vector")
        object.__setattr__(self, "profile_actions", actions)
        object.__setattr__(self, "profile_bits", bits)
        object.__setattr__(self, "profile_energy_j", energy)
        object.__setattr__(self, "common_field_sha256_by_profile", fields)
        object.__setattr__(self, "action_sha256_by_profile", action_hashes)


def _teacher_digest(
    *,
    pair_id: str,
    member_users: np.ndarray,
    proposed_actions: np.ndarray,
    draws: tuple[LCSRSFourProfileDraw, ...],
    targets: LCSRSPairTargets,
) -> str:
    digest = hashlib.sha256()
    digest.update(LCSRS_C3_TEACHER_SCHEMA.encode("ascii"))
    encoded = pair_id.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)
    digest.update(np.ascontiguousarray(member_users).tobytes(order="C"))
    digest.update(np.ascontiguousarray(proposed_actions).tobytes(order="C"))
    for draw in draws:
        digest.update(struct.pack(">I", draw.draw_index))
        digest.update(np.ascontiguousarray(draw.profile_actions).tobytes(order="C"))
        digest.update(np.ascontiguousarray(draw.profile_bits).tobytes(order="C"))
        digest.update(np.ascontiguousarray(draw.profile_energy_j).tobytes(order="C"))
        digest.update(draw.common_field_sha256_by_profile[0].encode("ascii"))
        for value in draw.action_sha256_by_profile:
            digest.update(value.encode("ascii"))
    digest.update(np.ascontiguousarray(targets.normalized_targets_by_draw).tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSTwoUserTeacher:
    """The 32 draw-resolved formula results and one averaged pair target."""

    pair_id: str
    member_users: np.ndarray
    proposed_actions: np.ndarray
    draws: tuple[LCSRSFourProfileDraw, ...]
    formula_results: tuple[CoalitionResidualC3Result, ...]
    pair_targets: LCSRSPairTargets
    content_digest: str
    schema: str = LCSRS_C3_TEACHER_SCHEMA

    def __post_init__(self) -> None:
        if not isinstance(self.pair_id, str) or not self.pair_id:
            raise LCSRSC3TeacherError("pair_id must be a nonempty identifier")
        members = _readonly(self.member_users, dtype=np.dtype(np.int64))
        proposed = _readonly(self.proposed_actions, dtype=np.dtype(np.int64))
        draws = tuple(self.draws)
        results = tuple(self.formula_results)
        if members.shape != (2,) or np.unique(members).size != 2:
            raise LCSRSC3TeacherError("teacher receipt needs exactly two members")
        if proposed.shape != (2,):
            raise LCSRSC3TeacherError("teacher receipt needs exactly two actions")
        if len(draws) != LCSRS_DRAW_COUNT or len(results) != LCSRS_DRAW_COUNT:
            raise LCSRSC3TeacherError("teacher receipt needs exactly 32 results")
        if tuple(draw.draw_index for draw in draws) != tuple(range(LCSRS_DRAW_COUNT)):
            raise LCSRSC3TeacherError("teacher draws must be ordered 0 through 31")
        if not isinstance(self.pair_targets, LCSRSPairTargets):
            raise LCSRSC3TeacherError("teacher receipt lacks pair targets")
        if (
            self.pair_targets.pair_id != self.pair_id
            or not np.array_equal(self.pair_targets.user_ids, members)
            or not np.array_equal(self.pair_targets.action_ids, proposed)
        ):
            raise LCSRSC3TeacherError("teacher pair target identity drifted")
        for index, (draw, result) in enumerate(zip(draws, results, strict=True)):
            if not isinstance(draw, LCSRSFourProfileDraw):
                raise LCSRSC3TeacherError("teacher draw has the wrong type")
            if not isinstance(result, CoalitionResidualC3Result):
                raise LCSRSC3TeacherError("teacher formula result has the wrong type")
            result.verify()
            if (
                not np.array_equal(result.coalition_user_ids, members)
                or not np.array_equal(result.proposed_actions, proposed)
                or not np.array_equal(result.reference_bits, draw.profile_bits[0])
                or not np.array_equal(result.unilateral_bits, draw.profile_bits[1:3])
                or not np.array_equal(result.joint_bits, draw.profile_bits[3])
                or result.reference_energy_j != float(draw.profile_energy_j[0])
                or not np.array_equal(
                    result.unilateral_energy_j,
                    draw.profile_energy_j[1:3],
                )
                or result.joint_energy_j != float(draw.profile_energy_j[3])
            ):
                raise LCSRSC3TeacherError("teacher formula result drifted from draw")
            expected_target = result.z3_bits / result.kappa_bits
            if not np.array_equal(
                self.pair_targets.normalized_targets_by_draw[index],
                expected_target,
            ):
                raise LCSRSC3TeacherError("teacher normalized target was modified")
        if self.schema != LCSRS_C3_TEACHER_SCHEMA:
            raise LCSRSC3TeacherError("teacher receipt schema drifted")
        expected_digest = _teacher_digest(
            pair_id=self.pair_id,
            member_users=members,
            proposed_actions=proposed,
            draws=draws,
            targets=self.pair_targets,
        )
        if self.content_digest != expected_digest:
            raise LCSRSC3TeacherError("teacher receipt digest mismatch")
        object.__setattr__(self, "member_users", members)
        object.__setattr__(self, "proposed_actions", proposed)
        object.__setattr__(self, "draws", draws)
        object.__setattr__(self, "formula_results", results)

    def verify(self) -> str:
        expected = _teacher_digest(
            pair_id=self.pair_id,
            member_users=self.member_users,
            proposed_actions=self.proposed_actions,
            draws=self.draws,
            targets=self.pair_targets,
        )
        if self.content_digest != expected:
            raise LCSRSC3TeacherError("teacher receipt digest mismatch")
        return expected


def _profile_actions(
    reference_actions: np.ndarray,
    member_users: np.ndarray,
    proposed_actions: np.ndarray,
) -> np.ndarray:
    expected = np.repeat(reference_actions[None, :], 4, axis=0)
    expected[1, member_users[0]] = proposed_actions[0]
    expected[2, member_users[1]] = proposed_actions[1]
    expected[3, member_users] = proposed_actions
    return expected


def build_lcsrs_two_user_teacher(
    *,
    pair_id: str,
    member_users: object,
    proposed_actions: object,
    reference_actions: object,
    legal_mask: object,
    draws: Sequence[LCSRSFourProfileDraw],
    lambda_bits_per_j: float,
    kappa_bits: float,
) -> LCSRSTwoUserTeacher:
    """Apply the unchanged V0.22 identity separately to exactly 32 draws."""

    if not isinstance(pair_id, str) or not pair_id:
        raise LCSRSC3TeacherError("pair_id must be a nonempty receipt identifier")
    members = _readonly(member_users, dtype=np.dtype(np.int64))
    proposed = _readonly(proposed_actions, dtype=np.dtype(np.int64))
    references = _readonly(reference_actions, dtype=np.dtype(np.int64))
    mask_raw = np.asarray(legal_mask)
    if mask_raw.dtype != np.bool_:
        raise LCSRSC3TeacherError("legal_mask must have Boolean dtype")
    legal = _readonly(mask_raw, dtype=np.dtype(np.bool_))
    if members.shape != (2,) or np.unique(members).size != 2:
        raise LCSRSC3TeacherError("LC-SRS teacher requires exactly two unique members")
    if proposed.shape != (2,):
        raise LCSRSC3TeacherError("LC-SRS teacher requires exactly two proposed actions")
    if references.ndim != 1 or legal.shape != (references.size, 28):
        raise LCSRSC3TeacherError("reference/mask shapes disagree with native action width")
    frozen_draws = tuple(draws)
    if len(frozen_draws) != LCSRS_DRAW_COUNT:
        raise LCSRSC3TeacherError("LC-SRS teacher requires exactly 32 complete draws")
    if sorted(draw.draw_index for draw in frozen_draws) != list(range(LCSRS_DRAW_COUNT)):
        raise LCSRSC3TeacherError("draw indices must be unique and complete from 0 through 31")
    expected_actions = _profile_actions(references, members, proposed)
    results: list[CoalitionResidualC3Result] = []
    targets = np.empty((LCSRS_DRAW_COUNT, 2), dtype=np.float64)
    ordered_draws = tuple(sorted(frozen_draws, key=lambda draw: draw.draw_index))
    for draw in ordered_draws:
        if draw.profile_actions.shape != expected_actions.shape or not np.array_equal(
            draw.profile_actions, expected_actions
        ):
            raise LCSRSC3TeacherError("profile actions do not match exact 00/10/01/11")
        result = build_coalition_residual_c3(
            B0_v=draw.profile_bits[0],
            E0=draw.profile_energy_j[0],
            Bu=draw.profile_bits[1:3],
            Eu=draw.profile_energy_j[1:3],
            BC=draw.profile_bits[3],
            EC=draw.profile_energy_j[3],
            coalition_user_ids=members,
            proposed_actions=proposed,
            lambda_bits_per_j=lambda_bits_per_j,
            kappa_bits=kappa_bits,
            reference_actions=references,
            legal_mask=legal,
            action_count=28,
        )
        if result.members != 2:
            raise LCSRSC3TeacherError("formula helper widened the exact two-member seam")
        results.append(result)
        targets[draw.draw_index] = result.z3_bits / result.kappa_bits
    pair_targets = LCSRSPairTargets(
        pair_id=pair_id,
        user_ids=members,
        action_ids=proposed,
        normalized_targets_by_draw=targets,
    )
    digest = _teacher_digest(
        pair_id=pair_id,
        member_users=members,
        proposed_actions=proposed,
        draws=ordered_draws,
        targets=pair_targets,
    )
    return LCSRSTwoUserTeacher(
        pair_id=pair_id,
        member_users=members,
        proposed_actions=proposed,
        draws=ordered_draws,
        formula_results=tuple(results),
        pair_targets=pair_targets,
        content_digest=digest,
    )


def build_lcsrs_topology_teacher(
    *,
    topology: LCSRSC3AnchorTopologyReceipt,
    pair: LCSRSC3ClosurePair,
    draws: Sequence[LCSRSFourProfileDraw],
    lambda_bits_per_j: float,
    kappa_bits: float,
) -> LCSRSTwoUserTeacher:
    """Bind the formula teacher to one pre-outcome topology pair."""

    if not isinstance(topology, LCSRSC3AnchorTopologyReceipt):
        raise LCSRSC3TeacherError("topology must be an authenticated receipt")
    if not isinstance(pair, LCSRSC3ClosurePair):
        raise LCSRSC3TeacherError("pair must be an authenticated closure pair")
    topology.verify()
    matches = {
        candidate.content_digest: candidate for candidate in topology.pairs
    }
    if pair.content_digest not in matches or matches[pair.content_digest] != pair:
        raise LCSRSC3TeacherError("pair is not declared by the topology receipt")
    return build_lcsrs_two_user_teacher(
        pair_id=pair.pair_id,
        member_users=np.asarray(pair.member_users, dtype=np.int64),
        proposed_actions=np.asarray(pair.designated_actions, dtype=np.int64),
        reference_actions=topology.capture.reference_actions,
        legal_mask=topology.capture.action_mask,
        draws=draws,
        lambda_bits_per_j=lambda_bits_per_j,
        kappa_bits=kappa_bits,
    )


__all__ = [
    "LCSRS_PROFILE_ORDER",
    "LCSRS_C3_TEACHER_SCHEMA",
    "LCSRSC3TeacherError",
    "LCSRSFourProfileDraw",
    "LCSRSTwoUserTeacher",
    "lcsrs_action_sha256",
    "build_lcsrs_two_user_teacher",
    "build_lcsrs_topology_teacher",
]
