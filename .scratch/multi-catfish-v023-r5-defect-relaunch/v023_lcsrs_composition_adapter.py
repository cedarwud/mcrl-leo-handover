#!/usr/bin/env python3
"""Fail-closed V0.23 held-out LC-SRS literal-composition boundary.

This module is import-safe: it opens no simulator, TLE world, TEST split,
optimizer, or policy rollout.  Physical replay and current-slot evaluation are
explicitly injected boundaries.  The adapter owns the one-pass native
selection and immutable numeric evidence format.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType
from typing import Any, Callable

import numpy as np


V023_WORLDS = tuple(range(2026121705, 2026121713))
V023_STUDENT_SEEDS = (2026135101, 2026135102, 2026135103)
V023_FIT_ARMS = ("INFORMED", "MATCHED_PLACEBO")
V023_ACTION_COUNT = 28
V023_DRAW_COUNT = 32
V023_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
V023_ANCHOR_PHASES = tuple(range(1, 10))
V023_CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
V023_COMPOSITION_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-composition-artifact-v1"
V023_COMPOSITION_ARRAY_DOMAIN = "v023-composition-array-v1"
V023_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
V023_PHYSICAL_ROLES = (
    "ZERO_SURFACE_B",
    "INFORMED",
    "MATCHED_PLACEBO",
    "TEACHER_ORACLE",
)


class V023CompositionAdapterError(RuntimeError):
    """A composition identity, one-pass, physical, or persistence guard failed."""


def _readonly_array(
    value: object,
    *,
    dtype: np.dtype,
    name: str,
    ndim: int | None = None,
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype == object:
        raise V023CompositionAdapterError(f"{name} has forbidden object dtype")
    try:
        result = np.array(raw, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise V023CompositionAdapterError(f"{name} cannot be materialised") from error
    if ndim is not None and result.ndim != ndim:
        raise V023CompositionAdapterError(f"{name} must be {ndim}-dimensional")
    if np.issubdtype(result.dtype, np.floating) and not np.all(np.isfinite(result)):
        raise V023CompositionAdapterError(f"{name} must be finite")
    result.setflags(write=False)
    return result


def _sha256(value: object, *, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023CompositionAdapterError(f"{name} is not a lowercase SHA-256")
    return value


def array_sha256(value: object, *, domain: str) -> str:
    """Digest dtype, shape, and C-order bytes under an explicit domain."""

    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype == object:
        raise V023CompositionAdapterError("object dtype is forbidden")
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def action_vector_sha256(actions: object) -> str:
    """Use the native V0.23 complete-action digest grammar."""

    raw = np.asarray(actions)
    if raw.dtype == object:
        raise V023CompositionAdapterError("action vector has forbidden object dtype")
    values = np.ascontiguousarray(raw, dtype=np.int64)
    if values.ndim != 1 or values.size < 2:
        raise V023CompositionAdapterError("action vector must contain at least two users")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-profile-actions-v1")
    digest.update(struct.pack(">I", int(values.size)))
    digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _readonly_digest_array(value: object, *, name: str, ndim: int) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype.kind != "S":
        raise V023CompositionAdapterError(f"{name} must be fixed-width ASCII")
    result = _readonly_array(raw, dtype=raw.dtype, name=name, ndim=ndim)
    for item in result.reshape(-1).tolist():
        try:
            decoded = bytes(item).rstrip(b"\0").decode("ascii")
        except (UnicodeDecodeError, TypeError) as error:
            raise V023CompositionAdapterError(f"{name} contains non-ASCII digest") from error
        _sha256(decoded, name=name)
    return result


def _validate_selected_actions(
    *, scores: np.ndarray, mask: np.ndarray, actions: np.ndarray
) -> np.ndarray:
    if actions.dtype != np.int64 or actions.shape != (scores.shape[0],):
        raise V023CompositionAdapterError("native selector returned malformed actions")
    for user, selected_raw in enumerate(actions.tolist()):
        selected = int(selected_raw)
        if not 0 <= selected < scores.shape[1] or not bool(mask[user, selected]):
            raise V023CompositionAdapterError("native selector returned an illegal action")
        legal_actions = np.flatnonzero(mask[user])
        maximum = np.max(scores[user, legal_actions])
        tied = legal_actions[scores[user, legal_actions] == maximum]
        if selected != int(tied[0]):
            raise V023CompositionAdapterError(
                "native selector did not choose the lowest exact-tie action"
            )
    return actions


@dataclass(frozen=True)
class NativeSelectionReceipt:
    """One native masked row-wise selection and its exact-tie denominator."""

    actions: np.ndarray
    exact_tie_count: np.ndarray

    def __post_init__(self) -> None:
        actions = _readonly_array(
            self.actions, dtype=np.dtype(np.int64), name="selected actions", ndim=1
        )
        ties = _readonly_array(
            self.exact_tie_count,
            dtype=np.dtype(np.int64),
            name="exact tie counts",
            ndim=1,
        )
        if ties.shape != actions.shape or np.any(ties < 1):
            raise V023CompositionAdapterError("selection tie counts are malformed")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "exact_tie_count", ties)


def native_masked_argmax(scores: object, mask: object) -> NativeSelectionReceipt:
    """Apply one native masked argmax; NumPy resolves exact ties by lowest index."""

    values = _readonly_array(
        scores, dtype=np.dtype(np.float32), name="selection scores", ndim=2
    )
    raw_mask = np.asarray(mask)
    if raw_mask.dtype != np.bool_:
        raise V023CompositionAdapterError("native action mask must have Boolean dtype")
    legal = _readonly_array(
        raw_mask, dtype=np.dtype(np.bool_), name="native action mask", ndim=2
    )
    if legal.shape != values.shape or np.any(~np.any(legal, axis=1)):
        raise V023CompositionAdapterError(
            "native mask must match scores and expose one action per user"
        )
    masked = np.where(legal, values, -np.inf)
    actions = np.argmax(masked, axis=1).astype(np.int64, copy=False)
    maxima = masked[np.arange(masked.shape[0]), actions]
    tie_count = np.count_nonzero(legal & (values == maxima[:, None]), axis=1)
    return NativeSelectionReceipt(actions=actions, exact_tie_count=tie_count)


@dataclass(frozen=True)
class ImmutableAnchorHandle:
    """Opaque immutable token shared only by the replay and evaluator seams."""

    token: str
    content_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.token, str) or not self.token or self.token != self.token.strip():
            raise V023CompositionAdapterError("anchor handle token is malformed")
        _sha256(self.content_digest, name="anchor handle content_digest")


PAIR_CLASS_CODES = {"00": 0, "10": 1, "01": 2, "11": 3, "OTHER": 4}
PAIR_CLASS_NAMES = tuple(PAIR_CLASS_CODES)
PROFILE_ORDER = ("00", "10", "01", "11")
PHYSICAL_NONMUTATION_REQUIRED = frozenset(
    {"environment", "rng", "q1", "q2", "q3", "matched_field"}
)


def _physical_key(value: object, *, name: str) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise V023CompositionAdapterError(f"{name} must be a two-integer tuple")
    left, right = value
    if type(left) is not int or type(right) is not int or left < 0 or right < 0:
        raise V023CompositionAdapterError(f"{name} must contain nonnegative integers")
    return left, right


@dataclass(frozen=True)
class PairSourceMechanics:
    """All source-authenticated per-draw teacher and four-profile mechanics."""

    target_by_draw: np.ndarray
    profile_link_rate_bps: np.ndarray
    profile_link_power_w: np.ndarray
    profile_link_sinr: np.ndarray
    profile_g_bits: np.ndarray
    profile_system_power_w: np.ndarray
    profile_fixed_power_w: np.ndarray
    profile_active_beam_keys: np.ndarray
    profile_active_beam_counts: np.ndarray
    profile_active_satellites: np.ndarray
    profile_active_satellite_counts: np.ndarray
    profile_beam_power_w: np.ndarray
    z3_bits_by_draw: np.ndarray
    z3_normalized_by_draw: np.ndarray
    formula_identity_residual_bits: np.ndarray
    ratio_identity_value_bits: np.ndarray
    joint_ee_bits_per_j: np.ndarray
    source_nonmutation_flags: np.ndarray
    action_digest: np.ndarray
    ratio_cross_product: np.ndarray
    ratio_sign: np.ndarray
    ratio_tolerance: np.ndarray
    ratio_local_tolerance: np.ndarray
    formula_own_bits: np.ndarray
    formula_nonfocal_bits: np.ndarray
    formula_d_bits: np.ndarray
    formula_joint_delta_bits: np.ndarray
    formula_joint_delta_energy_j: np.ndarray
    formula_joint_surplus_bits: np.ndarray
    formula_interaction_bits: np.ndarray
    formula_interaction_energy_j: np.ndarray
    formula_interaction_surplus_bits: np.ndarray
    formula_equal_share_bits: np.ndarray

    def __post_init__(self) -> None:
        draw_member = {
            "target_by_draw": self.target_by_draw,
            "z3_bits_by_draw": self.z3_bits_by_draw,
            "z3_normalized_by_draw": self.z3_normalized_by_draw,
            "formula_own_bits": self.formula_own_bits,
            "formula_nonfocal_bits": self.formula_nonfocal_bits,
            "formula_d_bits": self.formula_d_bits,
        }
        draw_profile_user = {
            "profile_link_rate_bps": self.profile_link_rate_bps,
            "profile_link_power_w": self.profile_link_power_w,
            "profile_link_sinr": self.profile_link_sinr,
        }
        draw_profile = {
            "profile_g_bits": self.profile_g_bits,
            "profile_system_power_w": self.profile_system_power_w,
            "profile_fixed_power_w": self.profile_fixed_power_w,
        }
        draw_scalar = {
            "formula_identity_residual_bits": self.formula_identity_residual_bits,
            "ratio_identity_value_bits": self.ratio_identity_value_bits,
            "joint_ee_bits_per_j": self.joint_ee_bits_per_j,
            "ratio_cross_product": self.ratio_cross_product,
            "ratio_tolerance": self.ratio_tolerance,
            "ratio_local_tolerance": self.ratio_local_tolerance,
            "formula_joint_delta_bits": self.formula_joint_delta_bits,
            "formula_joint_delta_energy_j": self.formula_joint_delta_energy_j,
            "formula_joint_surplus_bits": self.formula_joint_surplus_bits,
            "formula_interaction_bits": self.formula_interaction_bits,
            "formula_interaction_energy_j": self.formula_interaction_energy_j,
            "formula_interaction_surplus_bits": self.formula_interaction_surplus_bits,
            "formula_equal_share_bits": self.formula_equal_share_bits,
        }
        converted: dict[str, np.ndarray] = {}
        for name, value in draw_member.items():
            array = _readonly_array(
                value, dtype=np.dtype(np.float64), name=name, ndim=2
            )
            if array.shape != (V023_DRAW_COUNT, 2):
                raise V023CompositionAdapterError(f"{name} must have shape (32,2)")
            converted[name] = array
        user_count: int | None = None
        for name, value in draw_profile_user.items():
            array = _readonly_array(
                value, dtype=np.dtype(np.float64), name=name, ndim=3
            )
            if array.shape[:2] != (V023_DRAW_COUNT, 4):
                raise V023CompositionAdapterError(f"{name} must begin with shape (32,4)")
            if user_count is None:
                user_count = int(array.shape[2])
            elif array.shape[2] != user_count:
                raise V023CompositionAdapterError("source profile user counts drifted")
            converted[name] = array
        for name, value in draw_profile.items():
            array = _readonly_array(
                value, dtype=np.dtype(np.float64), name=name, ndim=2
            )
            if array.shape != (V023_DRAW_COUNT, 4):
                raise V023CompositionAdapterError(f"{name} must have shape (32,4)")
            converted[name] = array
        for name, value in draw_scalar.items():
            array = _readonly_array(
                value, dtype=np.dtype(np.float64), name=name, ndim=1
            )
            if array.shape != (V023_DRAW_COUNT,):
                raise V023CompositionAdapterError(f"{name} must have shape (32,)")
            converted[name] = array

        beam_keys = _readonly_array(
            self.profile_active_beam_keys,
            dtype=np.dtype(np.int64),
            name="profile_active_beam_keys",
            ndim=4,
        )
        beam_counts = _readonly_array(
            self.profile_active_beam_counts,
            dtype=np.dtype(np.int64),
            name="profile_active_beam_counts",
            ndim=2,
        )
        beam_power = _readonly_array(
            self.profile_beam_power_w,
            dtype=np.dtype(np.float64),
            name="profile_beam_power_w",
            ndim=3,
        )
        satellites = _readonly_array(
            self.profile_active_satellites,
            dtype=np.dtype(np.int64),
            name="profile_active_satellites",
            ndim=3,
        )
        satellite_counts = _readonly_array(
            self.profile_active_satellite_counts,
            dtype=np.dtype(np.int64),
            name="profile_active_satellite_counts",
            ndim=2,
        )
        if (
            beam_keys.shape[:2] != (V023_DRAW_COUNT, 4)
            or beam_keys.shape[3:] != (2,)
            or beam_counts.shape != (V023_DRAW_COUNT, 4)
            or beam_power.shape != beam_keys.shape[:3]
            or satellites.shape[:2] != (V023_DRAW_COUNT, 4)
            or satellite_counts.shape != (V023_DRAW_COUNT, 4)
            or np.any(beam_counts < 0)
            or np.any(beam_counts > beam_keys.shape[2])
            or np.any(satellite_counts < 0)
            or np.any(satellite_counts > satellites.shape[2])
            or np.any(beam_power < 0.0)
        ):
            raise V023CompositionAdapterError("source active beam/satellite profiles are malformed")
        raw_mutation = np.asarray(self.source_nonmutation_flags)
        if raw_mutation.dtype != np.bool_:
            raise V023CompositionAdapterError("source nonmutation flags must be Boolean")
        mutation = _readonly_array(
            raw_mutation,
            dtype=np.dtype(np.bool_),
            name="source_nonmutation_flags",
            ndim=2,
        )
        if mutation.shape != (V023_DRAW_COUNT, 5) or not np.all(mutation):
            raise V023CompositionAdapterError("source five-field nonmutation receipt failed")
        actions = _readonly_digest_array(
            self.action_digest, name="source profile action digest", ndim=2
        )
        if actions.shape != (V023_DRAW_COUNT, 4):
            raise V023CompositionAdapterError("source profile action digests are malformed")
        signs = _readonly_array(
            self.ratio_sign, dtype=np.dtype(np.int8), name="ratio_sign", ndim=1
        )
        if signs.shape != (V023_DRAW_COUNT,) or np.any(~np.isin(signs, (-1, 0, 1))):
            raise V023CompositionAdapterError("source ratio signs are malformed")
        expected_cross_signs = np.where(
            converted["ratio_cross_product"]
            < -converted["ratio_tolerance"],
            -1,
            np.where(
                converted["ratio_cross_product"]
                > converted["ratio_tolerance"],
                1,
                0,
            ),
        ).astype(np.int8)
        expected_local_signs = np.where(
            converted["ratio_identity_value_bits"]
            < -converted["ratio_local_tolerance"],
            -1,
            np.where(
                converted["ratio_identity_value_bits"]
                > converted["ratio_local_tolerance"],
                1,
                0,
            ),
        ).astype(np.int8)
        if not np.array_equal(signs, expected_cross_signs) or not np.array_equal(
            signs, expected_local_signs
        ):
            raise V023CompositionAdapterError(
                "source ratio sign identity disagrees with raw operands"
            )
        if not np.array_equal(converted["target_by_draw"], converted["z3_normalized_by_draw"]):
            raise V023CompositionAdapterError("source target and normalized z3 draws disagree")
        if not np.array_equal(
            converted["z3_normalized_by_draw"],
            converted["z3_bits_by_draw"] / V023_KAPPA_BITS,
        ):
            raise V023CompositionAdapterError("source z3 normalization disagrees with kappa")
        if any(
            np.any(converted[name] < 0.0)
            for name in (
                "profile_link_rate_bps",
                "profile_link_power_w",
                "profile_link_sinr",
                "profile_system_power_w",
                "profile_fixed_power_w",
                "joint_ee_bits_per_j",
                "ratio_tolerance",
                "ratio_local_tolerance",
            )
        ):
            raise V023CompositionAdapterError("source profile mechanics violate nonnegative domains")
        for name, value in converted.items():
            object.__setattr__(self, name, value)
        for name, value in (
            ("profile_active_beam_keys", beam_keys),
            ("profile_active_beam_counts", beam_counts),
            ("profile_beam_power_w", beam_power),
            ("profile_active_satellites", satellites),
            ("profile_active_satellite_counts", satellite_counts),
            ("source_nonmutation_flags", mutation),
            ("action_digest", actions),
            ("ratio_sign", signs),
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class DeclaredPair:
    """One source-authenticated closure pair and all four 32-draw profiles."""

    pair_id: str
    member_users: tuple[int, int]
    designated_actions: tuple[int, int]
    source_key: tuple[int, int]
    destination_keys: tuple[tuple[int, int], tuple[int, int]]
    profile_actions: np.ndarray
    profile_bits: np.ndarray
    profile_energy_j: np.ndarray
    profile_served: np.ndarray
    common_field_digest: np.ndarray
    mechanics: PairSourceMechanics

    def __post_init__(self) -> None:
        if not isinstance(self.pair_id, str) or not self.pair_id:
            raise V023CompositionAdapterError("pair_id must be nonempty")
        users = self.member_users
        actions = self.designated_actions
        if (
            not isinstance(users, tuple)
            or len(users) != 2
            or any(type(value) is not int or value < 0 for value in users)
            or not users[0] < users[1]
        ):
            raise V023CompositionAdapterError("pair users must be two sorted integers")
        if (
            not isinstance(actions, tuple)
            or len(actions) != 2
            or any(type(value) is not int or not 0 <= value < V023_ACTION_COUNT for value in actions)
        ):
            raise V023CompositionAdapterError("pair designated actions are malformed")
        source = _physical_key(self.source_key, name="pair source key")
        if not isinstance(self.destination_keys, tuple) or len(self.destination_keys) != 2:
            raise V023CompositionAdapterError("pair must declare two destination keys")
        destinations = tuple(
            _physical_key(value, name="pair destination key")
            for value in self.destination_keys
        )
        if any(value == source for value in destinations):
            raise V023CompositionAdapterError("pair destination cannot equal its source")
        profile_actions = _readonly_array(
            self.profile_actions,
            dtype=np.dtype(np.int64),
            name="pair profile actions",
            ndim=3,
        )
        bits = _readonly_array(
            self.profile_bits,
            dtype=np.dtype(np.float64),
            name="pair profile bits",
            ndim=3,
        )
        energy = _readonly_array(
            self.profile_energy_j,
            dtype=np.dtype(np.float64),
            name="pair profile energy",
            ndim=2,
        )
        raw_served = np.asarray(self.profile_served)
        if raw_served.dtype != np.bool_:
            raise V023CompositionAdapterError("pair profile served flags must be Boolean")
        served = _readonly_array(
            raw_served,
            dtype=np.dtype(np.bool_),
            name="pair profile served flags",
            ndim=3,
        )
        fields = _readonly_digest_array(
            self.common_field_digest, name="pair common-field digest", ndim=1
        )
        mechanics = self.mechanics
        if not isinstance(mechanics, PairSourceMechanics):
            raise V023CompositionAdapterError(
                "pair must retain authenticated source mechanics"
            )
        if (
            profile_actions.shape[0:2] != (V023_DRAW_COUNT, 4)
            or bits.shape != profile_actions.shape
            or served.shape != profile_actions.shape
            or energy.shape != (V023_DRAW_COUNT, 4)
            or fields.shape != (V023_DRAW_COUNT,)
        ):
            raise V023CompositionAdapterError("pair profile arrays have wrong shapes")
        if mechanics.profile_link_rate_bps.shape[2] != profile_actions.shape[2]:
            raise V023CompositionAdapterError(
                "pair mechanics user count disagrees with profile actions"
            )
        if np.any(bits < 0.0) or np.any(energy <= 0.0):
            raise V023CompositionAdapterError("pair profile bits/energy domain failed")
        for draw_index in range(V023_DRAW_COUNT):
            for profile_index in range(4):
                declared_digest = bytes(
                    mechanics.action_digest[draw_index, profile_index]
                ).rstrip(b"\0").decode("ascii")
                expected_digest = action_vector_sha256(
                    profile_actions[draw_index, profile_index]
                )
                if declared_digest != expected_digest:
                    raise V023CompositionAdapterError(
                        "pair profile action digest disagrees with actions"
                    )
        object.__setattr__(self, "source_key", source)
        object.__setattr__(self, "destination_keys", destinations)
        object.__setattr__(self, "profile_actions", profile_actions)
        object.__setattr__(self, "profile_bits", bits)
        object.__setattr__(self, "profile_energy_j", energy)
        object.__setattr__(self, "profile_served", served)
        object.__setattr__(self, "common_field_digest", fields)
        object.__setattr__(self, "mechanics", mechanics)


@dataclass(frozen=True)
class DeclaredAnchor:
    """Authenticated source declaration for one held-out native anchor."""

    world: int
    phase: int
    anchor_id: str
    predecision_sha256: str
    state_schema_sha256: str
    state_sha256: str
    q12_snapshot_sha256: str
    q12_model_sha256: str
    q12_source_state_sha256: str
    q12_event_sha256: str
    view_sha256: str
    topology_sha256: str
    q1: np.ndarray
    q2: np.ndarray
    action_mask: np.ndarray
    reference_actions: np.ndarray
    physical_keys: np.ndarray
    teacher_q3: np.ndarray
    pairs: tuple[DeclaredPair, ...]
    reference_actions_sha256: str = ""

    def __post_init__(self) -> None:
        if type(self.world) is not int or self.world not in V023_WORLDS:
            raise V023CompositionAdapterError("anchor world is outside the frozen panel")
        if type(self.phase) is not int or not 1 <= self.phase <= 9:
            raise V023CompositionAdapterError("anchor phase must be in 1..9")
        if not isinstance(self.anchor_id, str) or not self.anchor_id:
            raise V023CompositionAdapterError("anchor_id must be nonempty")
        for field_name in (
            "predecision_sha256",
            "state_schema_sha256",
            "state_sha256",
            "q12_snapshot_sha256",
            "q12_model_sha256",
            "q12_source_state_sha256",
            "q12_event_sha256",
            "view_sha256",
            "topology_sha256",
        ):
            _sha256(getattr(self, field_name), name=field_name)
        q1 = _readonly_array(self.q1, dtype=np.dtype(np.float32), name="source Q1", ndim=2)
        q2 = _readonly_array(self.q2, dtype=np.dtype(np.float32), name="source Q2", ndim=2)
        if q1.shape != q2.shape or q1.shape[1] != V023_ACTION_COUNT:
            raise V023CompositionAdapterError("source Q1/Q2 shapes disagree")
        raw_mask = np.asarray(self.action_mask)
        if raw_mask.dtype != np.bool_:
            raise V023CompositionAdapterError("source action mask must be Boolean")
        mask = _readonly_array(
            raw_mask, dtype=np.dtype(np.bool_), name="source action mask", ndim=2
        )
        references = _readonly_array(
            self.reference_actions,
            dtype=np.dtype(np.int64),
            name="source reference actions",
            ndim=1,
        )
        if mask.shape != q1.shape or references.shape != (q1.shape[0],):
            raise V023CompositionAdapterError("source mask/reference shapes disagree")
        if np.any(~np.any(mask, axis=1)):
            raise V023CompositionAdapterError("every source user needs a legal action")
        q12 = np.asarray(q1 + q2, dtype=np.float32)
        _validate_selected_actions(scores=q12, mask=mask, actions=references)
        keys = _readonly_array(
            self.physical_keys,
            dtype=np.dtype(np.int64),
            name="source physical keys",
            ndim=3,
        )
        if keys.shape != (*q1.shape, 2):
            raise V023CompositionAdapterError("source physical key shape disagrees")
        teacher = _readonly_array(
            self.teacher_q3,
            dtype=np.dtype(np.float32),
            name="teacher-oracle surface",
            ndim=2,
        )
        if teacher.shape != q1.shape or np.any(teacher[~mask] != 0.0):
            raise V023CompositionAdapterError("teacher-oracle surface is malformed")
        reference_digest = array_sha256(
            references, domain="v023-reference-actions"
        )
        if self.reference_actions_sha256 not in ("", reference_digest):
            raise V023CompositionAdapterError("source reference-action digest disagrees")
        object.__setattr__(self, "q1", q1)
        object.__setattr__(self, "q2", q2)
        object.__setattr__(self, "action_mask", mask)
        object.__setattr__(self, "reference_actions", references)
        object.__setattr__(self, "physical_keys", keys)
        object.__setattr__(self, "teacher_q3", teacher)
        pairs = tuple(self.pairs)
        if any(not isinstance(pair, DeclaredPair) for pair in pairs):
            raise V023CompositionAdapterError("anchor pairs contain an invalid receipt")
        seen_pair_ids: set[str] = set()
        used_users: set[int] = set()
        for pair in pairs:
            if pair.pair_id in seen_pair_ids:
                raise V023CompositionAdapterError("anchor pair identifiers are duplicated")
            seen_pair_ids.add(pair.pair_id)
            if pair.profile_actions.shape[2] != q1.shape[0]:
                raise V023CompositionAdapterError("pair profile roster size disagrees")
            if any(user >= q1.shape[0] or user in used_users for user in pair.member_users):
                raise V023CompositionAdapterError("anchor pair users are invalid or overlap")
            used_users.update(pair.member_users)
            expected_profiles = np.repeat(references[None, :], 4, axis=0)
            expected_profiles[1, pair.member_users[0]] = pair.designated_actions[0]
            expected_profiles[2, pair.member_users[1]] = pair.designated_actions[1]
            expected_profiles[3, list(pair.member_users)] = pair.designated_actions
            if not np.array_equal(
                pair.profile_actions,
                np.repeat(expected_profiles[None, :, :], V023_DRAW_COUNT, axis=0),
            ):
                raise V023CompositionAdapterError("pair 00/10/01/11 actions drifted")
            for user, action in zip(
                pair.member_users, pair.designated_actions, strict=True
            ):
                if not bool(mask[user, action]):
                    raise V023CompositionAdapterError("pair designated action is illegal")
        if pairs:
            expected_fields = pairs[0].common_field_digest
            if any(
                not np.array_equal(pair.common_field_digest, expected_fields)
                for pair in pairs[1:]
            ):
                raise V023CompositionAdapterError(
                    "one anchor's source pairs do not share the common field"
                )
        object.__setattr__(self, "pairs", pairs)
        object.__setattr__(self, "reference_actions_sha256", reference_digest)

    @property
    def q12(self) -> np.ndarray:
        value = np.asarray(self.q1 + self.q2, dtype=np.float32)
        value.setflags(write=False)
        return value

    @property
    def q1_sha256(self) -> str:
        return array_sha256(self.q1, domain="v023-composition-source-q1-v1")

    @property
    def q2_sha256(self) -> str:
        return array_sha256(self.q2, domain="v023-composition-source-q2-v1")


@dataclass(frozen=True)
class ReplayedAnchor:
    """Fresh source-trajectory replay result, with no teacher data surface."""

    handle: ImmutableAnchorHandle
    world: int
    phase: int
    anchor_id: str
    predecision_sha256: str
    state_schema_sha256: str
    state_sha256: str
    q12_snapshot_sha256: str
    q12_model_sha256: str
    q12_source_state_sha256: str
    q12_event_sha256: str
    view_sha256: str
    topology_sha256: str
    q1: np.ndarray
    q2: np.ndarray
    action_mask: np.ndarray
    reference_actions: np.ndarray
    view: object

    def __post_init__(self) -> None:
        if not isinstance(self.handle, ImmutableAnchorHandle):
            raise V023CompositionAdapterError("replay did not return an immutable handle")
        q1 = _readonly_array(self.q1, dtype=np.dtype(np.float32), name="replayed Q1", ndim=2)
        q2 = _readonly_array(self.q2, dtype=np.dtype(np.float32), name="replayed Q2", ndim=2)
        raw_mask = np.asarray(self.action_mask)
        if raw_mask.dtype != np.bool_:
            raise V023CompositionAdapterError("replayed action mask must be Boolean")
        mask = _readonly_array(
            raw_mask, dtype=np.dtype(np.bool_), name="replayed action mask", ndim=2
        )
        references = _readonly_array(
            self.reference_actions,
            dtype=np.dtype(np.int64),
            name="replayed reference actions",
            ndim=1,
        )
        if q1.shape != q2.shape or mask.shape != q1.shape or references.shape != (q1.shape[0],):
            raise V023CompositionAdapterError("replayed Q1/Q2/mask/reference shapes disagree")
        for field_name in (
            "predecision_sha256",
            "state_schema_sha256",
            "state_sha256",
            "q12_snapshot_sha256",
            "q12_model_sha256",
            "q12_source_state_sha256",
            "q12_event_sha256",
            "view_sha256",
            "topology_sha256",
        ):
            _sha256(getattr(self, field_name), name=f"replayed {field_name}")
        verify = getattr(self.view, "verify", None)
        if not callable(verify) or verify() != self.view_sha256:
            raise V023CompositionAdapterError("replayed C3View verification failed")
        if getattr(self.view, "content_digest", None) != self.view_sha256:
            raise V023CompositionAdapterError("replayed C3View digest disagrees")
        for forbidden in (
            "teacher",
            "teacher_q3",
            "targets",
            "labels",
            "outcomes",
            "profile_bits",
            "profile_energy_j",
        ):
            if hasattr(self.view, forbidden):
                raise V023CompositionAdapterError(
                    f"replayed C3View exposes forbidden learned input: {forbidden}"
                )
        view_mask = np.asarray(getattr(self.view, "action_mask", None))
        view_references = np.asarray(getattr(self.view, "reference_actions", None))
        if not np.array_equal(view_mask, mask) or not np.array_equal(view_references, references):
            raise V023CompositionAdapterError("replayed C3View mask/reference disagrees")
        if any(value.flags.writeable for value in (view_mask, view_references)):
            raise V023CompositionAdapterError("replayed C3View arrays must be immutable")
        for field_name in (
            "action_context",
            "tokens",
            "token_mask",
            "action_mask",
            "reference_actions",
        ):
            value = getattr(self.view, field_name, None)
            if value is not None and np.asarray(value).flags.writeable:
                raise V023CompositionAdapterError(
                    f"replayed C3View {field_name} must be immutable"
                )
        object.__setattr__(self, "q1", q1)
        object.__setattr__(self, "q2", q2)
        object.__setattr__(self, "action_mask", mask)
        object.__setattr__(self, "reference_actions", references)

    @property
    def q12(self) -> np.ndarray:
        value = np.asarray(self.q1 + self.q2, dtype=np.float32)
        value.setflags(write=False)
        return value


@dataclass(frozen=True)
class AuthenticatedFitArtifact:
    """One safely reopened, fit-side-verified Q3 model."""

    held_out_world: int
    student_seed: int
    arm: str
    preflight_manifest_sha256: str
    source_manifest_sha256: str
    fit_receipt_sha256: str
    fit_receipt_content_sha256: str
    model_bytes_sha256: str
    model_sha256: str
    source_index_sha256: str
    model: object
    update_count: int = 2000

    def __post_init__(self) -> None:
        if self.held_out_world not in V023_WORLDS:
            raise V023CompositionAdapterError("fit held-out world is outside frozen panel")
        if self.student_seed not in V023_STUDENT_SEEDS:
            raise V023CompositionAdapterError("fit seed is outside frozen panel")
        if self.arm not in V023_FIT_ARMS:
            raise V023CompositionAdapterError("fit arm is outside frozen panel")
        if self.update_count != 2000:
            raise V023CompositionAdapterError("fit update count is not exactly 2000")
        for field_name in (
            "preflight_manifest_sha256",
            "source_manifest_sha256",
            "fit_receipt_sha256",
            "fit_receipt_content_sha256",
            "model_bytes_sha256",
            "model_sha256",
            "source_index_sha256",
        ):
            _sha256(getattr(self, field_name), name=field_name)


@dataclass(frozen=True)
class Q3InferenceInput:
    """The complete learned-inference API; privileged teacher data is absent."""

    model: object
    view: object
    held_out_world: int
    student_seed: int
    arm: str
    phase: int
    anchor_id: str
    model_sha256: str
    view_sha256: str


@dataclass(frozen=True)
class LearnedSelection:
    q3: np.ndarray
    scores: np.ndarray
    actions: np.ndarray
    exact_tie_count: np.ndarray
    q3_calls: int = 1
    argmax_calls: int = 1

    def __post_init__(self) -> None:
        q3 = _readonly_array(self.q3, dtype=np.dtype(np.float32), name="Q3 surface", ndim=2)
        scores = _readonly_array(
            self.scores, dtype=np.dtype(np.float32), name="Q1+Q2+Q3 scores", ndim=2
        )
        actions = _readonly_array(
            self.actions, dtype=np.dtype(np.int64), name="learned actions", ndim=1
        )
        ties = _readonly_array(
            self.exact_tie_count,
            dtype=np.dtype(np.int64),
            name="learned tie counts",
            ndim=1,
        )
        if q3.shape != scores.shape or actions.shape != ties.shape or actions.shape != (q3.shape[0],):
            raise V023CompositionAdapterError("learned selection shapes disagree")
        if self.q3_calls != 1 or self.argmax_calls != 1:
            raise V023CompositionAdapterError("learned selection was not literal one-pass")
        object.__setattr__(self, "q3", q3)
        object.__setattr__(self, "scores", scores)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "exact_tie_count", ties)


@dataclass(frozen=True)
class PairClassification:
    pair_id: str
    class_name: str
    class_code: int
    selected_member_actions: np.ndarray
    action_change: bool
    literal_11: bool
    harmful_partial_evaluated: bool
    harmful_partial: bool
    partial_ratio_cross_product: float
    partial_ratio_tolerance: float
    topology_evaluated: bool
    topology_consistent: bool
    source_empty: bool
    destinations_persist_by_nonmember: np.ndarray
    collateral_changed_count: int
    collateral_denominator: int

    def __post_init__(self) -> None:
        if self.class_name not in PAIR_CLASS_CODES or self.class_code != PAIR_CLASS_CODES[self.class_name]:
            raise V023CompositionAdapterError("pair class receipt is malformed")
        selected = _readonly_array(
            self.selected_member_actions,
            dtype=np.dtype(np.int64),
            name="selected pair actions",
            ndim=1,
        )
        destinations = _readonly_array(
            self.destinations_persist_by_nonmember,
            dtype=np.dtype(np.bool_),
            name="destination persistence flags",
            ndim=1,
        )
        if selected.shape != (2,) or destinations.shape != (2,):
            raise V023CompositionAdapterError("pair classification vectors are malformed")
        object.__setattr__(self, "selected_member_actions", selected)
        object.__setattr__(self, "destinations_persist_by_nonmember", destinations)


def _comparison_tolerance(left: float, right: float) -> float:
    return max(
        1.0e-12,
        1024.0
        * np.finfo(np.float64).eps
        * max(1.0, abs(float(left)), abs(float(right))),
    )


def classify_pair_actions(
    *,
    pair: DeclaredPair,
    baseline_actions: object,
    selected_actions: object,
    physical_keys: object,
) -> PairClassification:
    """Classify literal member adoption and rebuild topology for measurement only."""

    if not isinstance(pair, DeclaredPair):
        raise V023CompositionAdapterError("pair classification needs a declared pair")
    baseline = _readonly_array(
        baseline_actions, dtype=np.dtype(np.int64), name="pair baseline actions", ndim=1
    )
    selected = _readonly_array(
        selected_actions, dtype=np.dtype(np.int64), name="pair selected actions", ndim=1
    )
    keys = _readonly_array(
        physical_keys,
        dtype=np.dtype(np.int64),
        name="pair physical keys",
        ndim=3,
    )
    if selected.shape != baseline.shape or keys.shape != (
        baseline.size,
        V023_ACTION_COUNT,
        2,
    ):
        raise V023CompositionAdapterError("pair classification roster shapes disagree")
    if np.any(selected < 0) or np.any(selected >= V023_ACTION_COUNT):
        raise V023CompositionAdapterError("pair classification action is out of range")
    members = np.asarray(pair.member_users, dtype=np.int64)
    selected_members = selected[members]
    base_members = baseline[members]
    designated = np.asarray(pair.designated_actions, dtype=np.int64)
    first_base = bool(selected_members[0] == base_members[0])
    second_base = bool(selected_members[1] == base_members[1])
    first_designated = bool(selected_members[0] == designated[0])
    second_designated = bool(selected_members[1] == designated[1])
    if first_base and second_base:
        class_name = "00"
    elif first_designated and second_base:
        class_name = "10"
    elif first_base and second_designated:
        class_name = "01"
    elif first_designated and second_designated:
        class_name = "11"
    else:
        class_name = "OTHER"

    harmful_evaluated = class_name in {"10", "01"}
    harmful = False
    cross_product = 0.0
    tolerance = 0.0
    if harmful_evaluated:
        profile_index = PROFILE_ORDER.index(class_name)
        baseline_bits = float(np.sum(pair.profile_bits[:, 0, :], dtype=np.float64))
        selected_bits = float(
            np.sum(pair.profile_bits[:, profile_index, :], dtype=np.float64)
        )
        baseline_energy = float(
            np.sum(pair.profile_energy_j[:, 0], dtype=np.float64)
        )
        selected_energy = float(
            np.sum(pair.profile_energy_j[:, profile_index], dtype=np.float64)
        )
        left = selected_bits * baseline_energy
        right = baseline_bits * selected_energy
        cross_product = left - right
        tolerance = _comparison_tolerance(left, right)
        harmful = cross_product < -tolerance

    selected_keys = keys[np.arange(selected.size), selected]
    source = np.asarray(pair.source_key, dtype=np.int64)
    source_empty = not bool(np.any(np.all(selected_keys == source, axis=1)))
    nonmember_mask = np.ones(selected.size, dtype=np.bool_)
    nonmember_mask[members] = False
    nonmember_keys = selected_keys[nonmember_mask]
    destinations_persist = np.asarray(
        [
            bool(
                np.any(
                    np.all(
                        nonmember_keys == np.asarray(destination, dtype=np.int64),
                        axis=1,
                    )
                )
            )
            for destination in pair.destination_keys
        ],
        dtype=np.bool_,
    )
    topology_evaluated = class_name == "11"
    topology_consistent = bool(
        topology_evaluated and source_empty and np.all(destinations_persist)
    )
    collateral = int(np.count_nonzero(selected[nonmember_mask] != baseline[nonmember_mask]))
    return PairClassification(
        pair_id=pair.pair_id,
        class_name=class_name,
        class_code=PAIR_CLASS_CODES[class_name],
        selected_member_actions=selected_members,
        action_change=bool(np.any(selected_members != base_members)),
        literal_11=class_name == "11",
        harmful_partial_evaluated=harmful_evaluated,
        harmful_partial=bool(harmful),
        partial_ratio_cross_product=cross_product,
        partial_ratio_tolerance=tolerance,
        topology_evaluated=topology_evaluated,
        topology_consistent=topology_consistent,
        source_empty=source_empty,
        destinations_persist_by_nonmember=destinations_persist,
        collateral_changed_count=collateral,
        collateral_denominator=int(nonmember_mask.sum()),
    )


def _bind_replayed_anchor(declared: DeclaredAnchor, replayed: ReplayedAnchor) -> None:
    if not isinstance(declared, DeclaredAnchor) or not isinstance(replayed, ReplayedAnchor):
        raise V023CompositionAdapterError("anchor binding needs typed source and replay receipts")
    scalar_fields = (
        "world",
        "phase",
        "anchor_id",
        "predecision_sha256",
        "state_schema_sha256",
        "state_sha256",
        "q12_snapshot_sha256",
        "q12_model_sha256",
        "q12_source_state_sha256",
        "q12_event_sha256",
        "view_sha256",
        "topology_sha256",
    )
    mismatched = [
        name for name in scalar_fields if getattr(declared, name) != getattr(replayed, name)
    ]
    if mismatched:
        raise V023CompositionAdapterError(
            "replayed anchor identity/digest mismatch: " + ", ".join(mismatched)
        )
    for name, expected, actual in (
        ("Q1", declared.q1, replayed.q1),
        ("Q2", declared.q2, replayed.q2),
        ("action mask", declared.action_mask, replayed.action_mask),
        ("reference actions", declared.reference_actions, replayed.reference_actions),
    ):
        if not np.array_equal(expected, actual):
            raise V023CompositionAdapterError(f"replayed {name} disagrees with source")
    replay_reference_digest = array_sha256(
        replayed.reference_actions, domain="v023-reference-actions"
    )
    if replay_reference_digest != declared.reference_actions_sha256:
        raise V023CompositionAdapterError("replayed reference-action digest disagrees")


def select_learned_once(
    *,
    declared: DeclaredAnchor,
    replayed: ReplayedAnchor,
    fitted: AuthenticatedFitArtifact,
    q3_evaluator: Callable[[Q3InferenceInput], object],
    native_selector: Callable[[object, object], NativeSelectionReceipt] = native_masked_argmax,
    model_digestor: Callable[[object], str],
) -> LearnedSelection:
    """Bind, evaluate Q3 once, and make exactly one learned native decision."""

    _bind_replayed_anchor(declared, replayed)
    if fitted.held_out_world != declared.world:
        raise V023CompositionAdapterError("fit world disagrees with held-out anchor")
    before = _sha256(model_digestor(fitted.model), name="live fitted model digest")
    if before != fitted.model_sha256:
        raise V023CompositionAdapterError("live fitted model disagrees before Q3")
    request = Q3InferenceInput(
        model=fitted.model,
        view=replayed.view,
        held_out_world=fitted.held_out_world,
        student_seed=fitted.student_seed,
        arm=fitted.arm,
        phase=declared.phase,
        anchor_id=declared.anchor_id,
        model_sha256=fitted.model_sha256,
        view_sha256=declared.view_sha256,
    )
    q3 = _readonly_array(
        q3_evaluator(request), dtype=np.dtype(np.float32), name="evaluated Q3", ndim=2
    )
    if q3.shape != declared.q1.shape:
        raise V023CompositionAdapterError("evaluated Q3 shape disagrees with source")
    if np.any(q3[~declared.action_mask] != 0.0):
        raise V023CompositionAdapterError("illegal Q3 outputs must be exact zero")
    rows = np.arange(q3.shape[0])
    if np.any(q3[rows, declared.reference_actions] != 0.0):
        raise V023CompositionAdapterError("Q3 reference centering is not exact")
    after = _sha256(model_digestor(fitted.model), name="post-Q3 fitted model digest")
    if after != before:
        raise V023CompositionAdapterError("Q3 evaluation mutated the fitted model")
    scores = np.asarray(replayed.q12 + q3, dtype=np.float32)
    selection = native_selector(scores, declared.action_mask)
    if not isinstance(selection, NativeSelectionReceipt):
        raise V023CompositionAdapterError("native selector did not return its typed receipt")
    actions = _validate_selected_actions(
        scores=scores,
        mask=np.asarray(declared.action_mask),
        actions=np.asarray(selection.actions),
    )
    expected_ties = np.asarray(
        [
            np.count_nonzero(
                declared.action_mask[user]
                & (scores[user] == scores[user, int(actions[user])])
            )
            for user in range(scores.shape[0])
        ],
        dtype=np.int64,
    )
    if not np.array_equal(selection.exact_tie_count, expected_ties):
        raise V023CompositionAdapterError("native selector tie receipt disagrees")
    return LearnedSelection(
        q3=q3,
        scores=scores,
        actions=actions,
        exact_tie_count=selection.exact_tie_count,
    )


@dataclass(frozen=True)
class PhysicalEvaluationRequest:
    """One complete, frozen action vector on the matched 32-draw panel."""

    handle: ImmutableAnchorHandle
    world: int
    phase: int
    anchor_id: str
    role: str
    actions: np.ndarray
    draw_index: np.ndarray

    def __post_init__(self) -> None:
        if not isinstance(self.handle, ImmutableAnchorHandle):
            raise V023CompositionAdapterError("physical request lacks anchor handle")
        if self.role not in V023_PHYSICAL_ROLES:
            raise V023CompositionAdapterError("physical request role is unknown")
        actions = _readonly_array(
            self.actions, dtype=np.dtype(np.int64), name="physical request actions", ndim=1
        )
        draw = _readonly_array(
            self.draw_index,
            dtype=np.dtype(np.int64),
            name="physical request draw index",
            ndim=1,
        )
        if not np.array_equal(draw, np.arange(V023_DRAW_COUNT, dtype=np.int64)):
            raise V023CompositionAdapterError("physical request must name draws 0..31")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "draw_index", draw)


@dataclass(frozen=True)
class PhysicalEvaluation:
    """Raw, independently recomputable result for one complete action vector."""

    role: str
    actions: np.ndarray
    draw_index: np.ndarray
    total_bits: np.ndarray
    per_user_bits: np.ndarray
    energy_j: np.ndarray
    served: np.ndarray
    active_beam_counts: np.ndarray
    active_beam_keys: np.ndarray
    active_satellite_counts: np.ndarray
    active_satellites: np.ndarray
    beam_power_w: np.ndarray
    action_sha256: str
    common_field_digest: np.ndarray
    nonmutation_names: tuple[str, ...]
    nonmutation_before_sha256: np.ndarray
    nonmutation_after_sha256: np.ndarray
    nonmutation_flags: np.ndarray

    def __post_init__(self) -> None:
        if self.role not in V023_PHYSICAL_ROLES:
            raise V023CompositionAdapterError("physical evaluation role is unknown")
        actions = _readonly_array(
            self.actions, dtype=np.dtype(np.int64), name="physical actions", ndim=1
        )
        draw = _readonly_array(
            self.draw_index, dtype=np.dtype(np.int64), name="physical draw index", ndim=1
        )
        bits = _readonly_array(
            self.per_user_bits,
            dtype=np.dtype(np.float64),
            name="physical per-user bits",
            ndim=2,
        )
        totals = _readonly_array(
            self.total_bits, dtype=np.dtype(np.float64), name="physical total bits", ndim=1
        )
        energy = _readonly_array(
            self.energy_j, dtype=np.dtype(np.float64), name="physical energy", ndim=1
        )
        raw_served = np.asarray(self.served)
        if raw_served.dtype != np.bool_:
            raise V023CompositionAdapterError("physical served flags must be Boolean")
        served = _readonly_array(
            raw_served, dtype=np.dtype(np.bool_), name="physical served flags", ndim=2
        )
        beam_counts = _readonly_array(
            self.active_beam_counts,
            dtype=np.dtype(np.int64),
            name="active beam counts",
            ndim=1,
        )
        beam_keys = _readonly_array(
            self.active_beam_keys,
            dtype=np.dtype(np.int64),
            name="active beam keys",
            ndim=3,
        )
        satellite_counts = _readonly_array(
            self.active_satellite_counts,
            dtype=np.dtype(np.int64),
            name="active satellite counts",
            ndim=1,
        )
        satellites = _readonly_array(
            self.active_satellites,
            dtype=np.dtype(np.int64),
            name="active satellites",
            ndim=2,
        )
        powers = _readonly_array(
            self.beam_power_w,
            dtype=np.dtype(np.float64),
            name="beam powers",
            ndim=2,
        )
        fields = _readonly_digest_array(
            self.common_field_digest, name="common field digest", ndim=1
        )
        names = tuple(self.nonmutation_names)
        if not names or len(set(names)) != len(names) or any(
            not isinstance(name, str) or not name for name in names
        ):
            raise V023CompositionAdapterError("nonmutation names are malformed")
        if not PHYSICAL_NONMUTATION_REQUIRED.issubset(names):
            missing = sorted(PHYSICAL_NONMUTATION_REQUIRED - set(names))
            raise V023CompositionAdapterError(
                "physical nonmutation receipt omits frozen fields: "
                + ", ".join(missing)
            )
        before = _readonly_digest_array(
            self.nonmutation_before_sha256, name="nonmutation before digest", ndim=2
        )
        after = _readonly_digest_array(
            self.nonmutation_after_sha256, name="nonmutation after digest", ndim=2
        )
        raw_flags = np.asarray(self.nonmutation_flags)
        if raw_flags.dtype != np.bool_:
            raise V023CompositionAdapterError("nonmutation flags must be Boolean")
        flags = _readonly_array(
            raw_flags, dtype=np.dtype(np.bool_), name="nonmutation flags", ndim=2
        )
        expected_draw = np.arange(V023_DRAW_COUNT, dtype=np.int64)
        if not np.array_equal(draw, expected_draw):
            raise V023CompositionAdapterError("physical result must retain draws 0..31")
        users = actions.size
        if (
            bits.shape != (V023_DRAW_COUNT, users)
            or served.shape != bits.shape
            or totals.shape != (V023_DRAW_COUNT,)
            or energy.shape != (V023_DRAW_COUNT,)
            or beam_counts.shape != (V023_DRAW_COUNT,)
            or beam_keys.shape[:1] != (V023_DRAW_COUNT,)
            or beam_keys.shape[2:] != (2,)
            or powers.shape != beam_keys.shape[:2]
            or satellite_counts.shape != (V023_DRAW_COUNT,)
            or satellites.shape[:1] != (V023_DRAW_COUNT,)
            or fields.shape != (V023_DRAW_COUNT,)
            or before.shape != (V023_DRAW_COUNT, len(names))
            or after.shape != before.shape
            or flags.shape != before.shape
        ):
            raise V023CompositionAdapterError("physical result array shapes disagree")
        if np.any(bits < 0.0) or np.any(energy <= 0.0) or np.any(powers < 0.0):
            raise V023CompositionAdapterError("physical bits/energy/power domain failed")
        if not np.array_equal(totals, np.sum(bits, axis=1, dtype=np.float64)):
            raise V023CompositionAdapterError("physical total bits disagree with users")
        if np.any(beam_counts < 0) or np.any(beam_counts > beam_keys.shape[1]):
            raise V023CompositionAdapterError("active beam count exceeds padded vectors")
        if np.any(satellite_counts < 0) or np.any(
            satellite_counts > satellites.shape[1]
        ):
            raise V023CompositionAdapterError(
                "active satellite count exceeds padded vectors"
            )
        if action_vector_sha256(actions) != _sha256(
            self.action_sha256, name="physical action_sha256"
        ):
            raise V023CompositionAdapterError("physical action hash disagrees")
        expected_flags = before == after
        if not np.array_equal(flags, expected_flags):
            raise V023CompositionAdapterError("nonmutation flags disagree with raw digests")
        if not np.all(flags):
            raise V023CompositionAdapterError("physical evaluation mutated frozen state")
        for name, value in (
            ("actions", actions),
            ("draw_index", draw),
            ("total_bits", totals),
            ("per_user_bits", bits),
            ("energy_j", energy),
            ("served", served),
            ("active_beam_counts", beam_counts),
            ("active_beam_keys", beam_keys),
            ("active_satellite_counts", satellite_counts),
            ("active_satellites", satellites),
            ("beam_power_w", powers),
            ("common_field_digest", fields),
            ("nonmutation_before_sha256", before),
            ("nonmutation_after_sha256", after),
            ("nonmutation_flags", flags),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "nonmutation_names", names)


@dataclass(frozen=True)
class AnchorComposition:
    """One learned decision plus separately selected diagnostic arms."""

    declared: DeclaredAnchor
    replayed: ReplayedAnchor
    arm: str
    learned: LearnedSelection
    baseline_actions: np.ndarray
    baseline_exact_tie_count: np.ndarray
    teacher_actions: np.ndarray
    teacher_exact_tie_count: np.ndarray
    physical: tuple[PhysicalEvaluation, ...]
    teacher_argmax_calls: int = 1

    def __post_init__(self) -> None:
        if self.arm not in V023_FIT_ARMS:
            raise V023CompositionAdapterError("composition arm is outside frozen panel")
        baseline = _readonly_array(
            self.baseline_actions,
            dtype=np.dtype(np.int64),
            name="baseline actions",
            ndim=1,
        )
        baseline_ties = _readonly_array(
            self.baseline_exact_tie_count,
            dtype=np.dtype(np.int64),
            name="baseline tie counts",
            ndim=1,
        )
        teacher = _readonly_array(
            self.teacher_actions,
            dtype=np.dtype(np.int64),
            name="teacher actions",
            ndim=1,
        )
        teacher_ties = _readonly_array(
            self.teacher_exact_tie_count,
            dtype=np.dtype(np.int64),
            name="teacher tie counts",
            ndim=1,
        )
        expected_shape = self.learned.actions.shape
        if any(value.shape != expected_shape for value in (baseline, baseline_ties, teacher, teacher_ties)):
            raise V023CompositionAdapterError("composition action/tie shapes disagree")
        if self.teacher_argmax_calls != 1:
            raise V023CompositionAdapterError("teacher diagnostic was not one-pass")
        physical = tuple(self.physical)
        expected_roles = ("ZERO_SURFACE_B", self.arm, "TEACHER_ORACLE")
        if tuple(result.role for result in physical) != expected_roles:
            raise V023CompositionAdapterError("physical evaluation roles/order disagree")
        object.__setattr__(self, "baseline_actions", baseline)
        object.__setattr__(self, "baseline_exact_tie_count", baseline_ties)
        object.__setattr__(self, "teacher_actions", teacher)
        object.__setattr__(self, "teacher_exact_tie_count", teacher_ties)
        object.__setattr__(self, "physical", physical)


def _tie_counts_without_selecting(scores: np.ndarray, mask: np.ndarray, actions: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            np.count_nonzero(mask[user] & (scores[user] == scores[user, int(action)]))
            for user, action in enumerate(actions.tolist())
        ],
        dtype=np.int64,
    )


def _physical_once(
    *,
    replayed: ReplayedAnchor,
    role: str,
    actions: np.ndarray,
    physical_evaluator: Callable[[PhysicalEvaluationRequest], PhysicalEvaluation],
) -> PhysicalEvaluation:
    immutable = _readonly_array(
        actions, dtype=np.dtype(np.int64), name=f"{role} selected actions", ndim=1
    )
    before = action_vector_sha256(immutable)
    request = PhysicalEvaluationRequest(
        handle=replayed.handle,
        world=replayed.world,
        phase=replayed.phase,
        anchor_id=replayed.anchor_id,
        role=role,
        actions=immutable,
        draw_index=np.arange(V023_DRAW_COUNT, dtype=np.int64),
    )
    result = physical_evaluator(request)
    if action_vector_sha256(request.actions) != before:
        raise V023CompositionAdapterError("physical evaluator mutated selected actions")
    if not isinstance(result, PhysicalEvaluation):
        raise V023CompositionAdapterError("physical evaluator returned an untyped result")
    if result.role != role or not np.array_equal(result.actions, immutable):
        raise V023CompositionAdapterError("physical evaluator edited selected actions")
    if result.action_sha256 != before:
        raise V023CompositionAdapterError("physical evaluator action receipt drifted")
    return result


def compose_anchor_once(
    *,
    declared: DeclaredAnchor,
    replayed: ReplayedAnchor,
    fitted: AuthenticatedFitArtifact,
    q3_evaluator: Callable[[Q3InferenceInput], object],
    physical_evaluator: Callable[[PhysicalEvaluationRequest], PhysicalEvaluation],
    model_digestor: Callable[[object], str],
    native_selector: Callable[[object, object], NativeSelectionReceipt] = native_masked_argmax,
) -> AnchorComposition:
    """Perform one learned selection and measurement with no repair path."""

    learned = select_learned_once(
        declared=declared,
        replayed=replayed,
        fitted=fitted,
        q3_evaluator=q3_evaluator,
        native_selector=native_selector,
        model_digestor=model_digestor,
    )
    baseline = np.asarray(declared.reference_actions, dtype=np.int64)
    baseline_ties = _tie_counts_without_selecting(
        declared.q12, declared.action_mask, baseline
    )
    teacher_scores = np.asarray(declared.q12 + declared.teacher_q3, dtype=np.float32)
    teacher_selection = native_selector(teacher_scores, declared.action_mask)
    if not isinstance(teacher_selection, NativeSelectionReceipt):
        raise V023CompositionAdapterError("teacher selector did not return typed receipt")
    teacher_actions = _validate_selected_actions(
        scores=teacher_scores,
        mask=np.asarray(declared.action_mask),
        actions=np.asarray(teacher_selection.actions),
    )
    expected_teacher_ties = _tie_counts_without_selecting(
        teacher_scores, declared.action_mask, teacher_actions
    )
    if not np.array_equal(teacher_selection.exact_tie_count, expected_teacher_ties):
        raise V023CompositionAdapterError("teacher selector tie receipt disagrees")
    physical = (
        _physical_once(
            replayed=replayed,
            role="ZERO_SURFACE_B",
            actions=baseline,
            physical_evaluator=physical_evaluator,
        ),
        _physical_once(
            replayed=replayed,
            role=fitted.arm,
            actions=learned.actions,
            physical_evaluator=physical_evaluator,
        ),
        _physical_once(
            replayed=replayed,
            role="TEACHER_ORACLE",
            actions=teacher_actions,
            physical_evaluator=physical_evaluator,
        ),
    )
    baseline_fields = physical[0].common_field_digest
    if any(
        not np.array_equal(result.common_field_digest, baseline_fields)
        for result in physical[1:]
    ):
        raise V023CompositionAdapterError("composition arms did not reuse one common field")
    if _sha256(model_digestor(fitted.model), name="post-physical model digest") != fitted.model_sha256:
        raise V023CompositionAdapterError("physical evaluation mutated the fitted model")
    return AnchorComposition(
        declared=declared,
        replayed=replayed,
        arm=fitted.arm,
        learned=learned,
        baseline_actions=baseline,
        baseline_exact_tie_count=baseline_ties,
        teacher_actions=teacher_actions,
        teacher_exact_tie_count=teacher_selection.exact_tie_count,
        physical=physical,
    )


@dataclass(frozen=True)
class AuthenticatedSourceArtifact:
    """One exact source shard, including raw pair profiles omitted by fit records."""

    world: int
    preflight_manifest_sha256: str
    source_manifest_sha256: str
    source_index_sha256: str
    field_root_sha256: str
    anchors: tuple[DeclaredAnchor, ...]

    def __post_init__(self) -> None:
        if self.world not in V023_WORLDS:
            raise V023CompositionAdapterError("source world is outside frozen panel")
        for field_name in (
            "preflight_manifest_sha256",
            "source_manifest_sha256",
            "source_index_sha256",
            "field_root_sha256",
        ):
            _sha256(getattr(self, field_name), name=f"source {field_name}")
        anchors = tuple(self.anchors)
        if (
            len(anchors) != len(V023_ANCHOR_PHASES)
            or tuple(anchor.phase for anchor in anchors) != V023_ANCHOR_PHASES
            or any(anchor.world != self.world for anchor in anchors)
            or len({anchor.anchor_id for anchor in anchors}) != len(anchors)
        ):
            raise V023CompositionAdapterError(
                "source anchors are not the exact held-out phases 1..9"
            )
        if len({anchor.q1.shape[0] for anchor in anchors}) != 1:
            raise V023CompositionAdapterError("source anchor roster size drifted")
        object.__setattr__(self, "anchors", anchors)


@dataclass(frozen=True)
class CompositionShardSpec:
    """Exact identity for one world/seed/learned-arm composition shard."""

    held_out_world: int
    student_seed: int
    arm: str
    source_directory: Path
    source_manifest: Path
    fit_receipt: Path
    preflight_manifest_sha256: str
    source_manifest_sha256: str
    output: Path

    def __post_init__(self) -> None:
        if self.held_out_world not in V023_WORLDS:
            raise V023CompositionAdapterError("composition world is outside frozen panel")
        if self.student_seed not in V023_STUDENT_SEEDS:
            raise V023CompositionAdapterError("composition seed is outside frozen panel")
        if self.arm not in V023_FIT_ARMS:
            raise V023CompositionAdapterError("composition arm is outside frozen panel")
        _sha256(
            self.preflight_manifest_sha256,
            name="composition preflight_manifest_sha256",
        )
        _sha256(
            self.source_manifest_sha256,
            name="composition source_manifest_sha256",
        )
        for name in ("source_directory", "source_manifest", "fit_receipt", "output"):
            value = Path(getattr(self, name))
            if name == "output" and value.suffix != ".json":
                raise V023CompositionAdapterError("composition output must end in .json")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class ReplayAnchorRequest:
    """Teacher-free request to replay exactly one authenticated Q1+Q2 anchor."""

    world: int
    phase: int
    anchor_id: str
    source_directory: Path
    preflight_manifest_sha256: str
    source_manifest_sha256: str
    source_index_sha256: str
    field_root_sha256: str
    predecision_sha256: str
    state_schema_sha256: str
    state_sha256: str
    q12_snapshot_sha256: str
    q12_model_sha256: str
    q12_source_state_sha256: str
    q12_event_sha256: str
    view_sha256: str
    topology_sha256: str
    reference_actions_sha256: str

    def __post_init__(self) -> None:
        if self.world not in V023_WORLDS or self.phase not in V023_ANCHOR_PHASES:
            raise V023CompositionAdapterError("replay request identity is outside panel")
        if not isinstance(self.anchor_id, str) or not self.anchor_id:
            raise V023CompositionAdapterError("replay request anchor_id is missing")
        for field_name in (
            "preflight_manifest_sha256",
            "source_manifest_sha256",
            "source_index_sha256",
            "field_root_sha256",
            "predecision_sha256",
            "state_schema_sha256",
            "state_sha256",
            "q12_snapshot_sha256",
            "q12_model_sha256",
            "q12_source_state_sha256",
            "q12_event_sha256",
            "view_sha256",
            "topology_sha256",
            "reference_actions_sha256",
        ):
            _sha256(getattr(self, field_name), name=f"replay {field_name}")
        object.__setattr__(self, "source_directory", Path(self.source_directory))


@dataclass(frozen=True)
class CompositionArtifacts:
    index_path: Path
    arrays_path: Path
    digest_path: Path
    index: Mapping[str, object]


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023CompositionAdapterError("composition JSON is not canonicalisable") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path, *, label: str) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023CompositionAdapterError(f"{label} is missing or is a symlink")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def composition_array_metadata(
    arrays: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Return explicit dtype/shape/C-byte digest metadata for safe NPZ members."""

    if not isinstance(arrays, Mapping) or not arrays:
        raise V023CompositionAdapterError("composition arrays are empty")
    metadata: dict[str, dict[str, object]] = {}
    for name in sorted(arrays):
        if not isinstance(name, str) or not name:
            raise V023CompositionAdapterError("composition array name is malformed")
        raw = np.asarray(arrays[name])
        if raw.dtype == object:
            raise V023CompositionAdapterError(f"array {name} has forbidden object dtype")
        array = np.ascontiguousarray(raw)
        if np.issubdtype(array.dtype, np.floating) and not np.all(np.isfinite(array)):
            raise V023CompositionAdapterError(f"array {name} contains non-finite values")
        metadata[name] = {
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "c_contiguous": True,
            "sha256": array_sha256(array, domain=V023_COMPOSITION_ARRAY_DOMAIN),
        }
    return metadata


def _sidecar_paths(output: Path) -> tuple[Path, Path, Path]:
    index_path = Path(output)
    arrays_path = index_path.with_name(index_path.stem + ".arrays.npz")
    digest_path = arrays_path.with_name(arrays_path.name + ".sha256")
    return index_path, arrays_path, digest_path


def _assert_write_once(paths: Sequence[Path]) -> None:
    for path in paths:
        if path.exists() or path.is_symlink():
            raise V023CompositionAdapterError(
                f"refusing to overwrite composition artifact: {path}"
            )


def _write_once_bytes(path: Path, payload: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise V023CompositionAdapterError(
            f"refusing to overwrite composition artifact: {target}"
        ) from error


def _write_npz_once(path: Path, arrays: Mapping[str, np.ndarray]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_write_once((target,))
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            np.savez_compressed(
                handle,
                **{
                    name: np.ascontiguousarray(np.asarray(value))
                    for name, value in sorted(arrays.items())
                },
            )
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, target)
        except FileExistsError as error:
            raise V023CompositionAdapterError(
                f"refusing to overwrite composition artifact: {target}"
            ) from error
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass
    return _file_sha256(target, label="composition NPZ")


def _ascii_array(values: Sequence[str], *, width: int, name: str) -> np.ndarray:
    encoded: list[bytes] = []
    for value in values:
        if not isinstance(value, str):
            raise V023CompositionAdapterError(f"{name} contains a non-string")
        try:
            item = value.encode("ascii")
        except UnicodeEncodeError as error:
            raise V023CompositionAdapterError(f"{name} is not ASCII") from error
        if len(item) > width:
            raise V023CompositionAdapterError(f"{name} exceeds fixed width {width}")
        encoded.append(item)
    return np.asarray(encoded, dtype=f"S{width}")


def _comparison_receipt(
    total_bits: np.ndarray, energy_j: np.ndarray, served: np.ndarray
) -> dict[str, object]:
    base_bits = float(np.sum(total_bits[:, 0], dtype=np.float64))
    base_energy = float(np.sum(energy_j[:, 0], dtype=np.float64))
    roles: dict[str, object] = {}
    for role_index, label in ((1, "learned_vs_b"), (2, "teacher_oracle_vs_b")):
        candidate_bits = float(np.sum(total_bits[:, role_index], dtype=np.float64))
        candidate_energy = float(np.sum(energy_j[:, role_index], dtype=np.float64))
        left = candidate_bits * base_energy
        right = base_bits * candidate_energy
        tolerance = _comparison_tolerance(left, right)
        cross = left - right
        direction = -1 if cross < -tolerance else 1 if cross > tolerance else 0
        roles[label] = {
            "candidate_total_bits": candidate_bits,
            "candidate_total_energy_j": candidate_energy,
            "baseline_total_bits": base_bits,
            "baseline_total_energy_j": base_energy,
            "ratio_cross_product": cross,
            "ratio_cross_product_tolerance": tolerance,
            "direction": direction,
            "tie": direction == 0,
            "direction_denominator": 1,
            "direction_missing_count": 0,
            "direction_tie_count": int(direction == 0),
            "candidate_served_count": int(np.count_nonzero(served[:, role_index])),
            "baseline_served_count": int(np.count_nonzero(served[:, 0])),
            "service_denominator": int(served[:, role_index].size),
        }
    return roles


def _load_local_module(name: str, path: Path) -> ModuleType:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionAdapterError(f"required module is missing or symlinked: {target}")
    loaded = sys.modules.get(name)
    if loaded is not None and Path(getattr(loaded, "__file__", "")).resolve() == target.resolve():
        return loaded
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise V023CompositionAdapterError(f"cannot load required module: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(name, None)
        raise V023CompositionAdapterError(f"required module import failed: {target}") from error
    return module


def _fit_adapter_module() -> ModuleType:
    return _load_local_module(
        "mcrl_v023_lcsrs_fit_adapter_for_composition",
        Path(__file__).resolve().with_name("v023_lcsrs_fit_adapter.py"),
    )


def _read_sealed_json(path: Path, *, label: str) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023CompositionAdapterError(f"{label} is missing or is a symlink")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023CompositionAdapterError(f"{label} is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise V023CompositionAdapterError(f"{label} is not canonical JSON")
    seal = _sha256(payload.get("receipt_sha256"), name=f"{label} receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != seal:
        raise V023CompositionAdapterError(f"{label} receipt seal disagrees")
    return payload


def _decode_fixed_ascii(value: object, *, label: str) -> str:
    scalar = np.asarray(value)
    if scalar.shape != () or scalar.dtype.kind != "S":
        raise V023CompositionAdapterError(f"{label} is not fixed-width ASCII")
    try:
        result = bytes(scalar.item()).rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError as error:
        raise V023CompositionAdapterError(f"{label} is not ASCII") from error
    if not result:
        raise V023CompositionAdapterError(f"{label} is empty")
    return result


def _safe_artifact_child(root: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise V023CompositionAdapterError(f"{label} path is unsafe")
    root_resolved = Path(root).resolve()
    candidate = root_resolved / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise V023CompositionAdapterError(f"{label} is missing or is a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise V023CompositionAdapterError(f"{label} path escapes its receipt directory")
    return resolved


def authenticate_source_artifact(
    spec: CompositionShardSpec,
    *,
    fit_adapter_module: ModuleType | None = None,
) -> AuthenticatedSourceArtifact:
    """Reopen the exact source panel and recover raw held-out pair evidence safely."""

    if not isinstance(spec, CompositionShardSpec):
        raise V023CompositionAdapterError("source authentication needs a typed shard spec")
    source_root_input = Path(spec.source_directory)
    if source_root_input.is_symlink() or not source_root_input.is_dir():
        raise V023CompositionAdapterError(
            "source directory is missing or is a symlink"
        )
    source_root = source_root_input.resolve()
    module = fit_adapter_module or _fit_adapter_module()
    loader = getattr(module, "load_v023_source_panel", None)
    if not callable(loader):
        raise V023CompositionAdapterError("fit adapter lacks the typed source-panel loader")
    try:
        panel = loader(
            source_directory=spec.source_directory,
            source_manifest=spec.source_manifest,
            preflight_manifest_sha256=spec.preflight_manifest_sha256,
        )
    except Exception as error:
        raise V023CompositionAdapterError("typed source-panel authentication failed") from error
    if getattr(panel, "source_manifest_sha256", None) != spec.source_manifest_sha256:
        raise V023CompositionAdapterError("source manifest disagrees with declaration")
    if getattr(panel, "preflight_manifest_sha256", None) != spec.preflight_manifest_sha256:
        raise V023CompositionAdapterError("source preflight manifest disagrees")
    artifacts = tuple(getattr(panel, "artifacts", ()))
    matches = [item for item in artifacts if getattr(item, "world", None) == spec.held_out_world]
    if len(matches) != 1:
        raise V023CompositionAdapterError("held-out source shard is missing or duplicated")
    artifact = matches[0]
    index = getattr(artifact, "index", None)
    if not isinstance(index, Mapping):
        raise V023CompositionAdapterError("typed source shard omitted its index")
    anchors_json = index.get("anchors")
    if not isinstance(anchors_json, list) or len(anchors_json) != 9:
        raise V023CompositionAdapterError("source index omits exact anchors 1..9")
    sidecar_path = Path(getattr(artifact, "sidecar_path", ""))
    if sidecar_path.is_symlink() or not sidecar_path.is_file():
        raise V023CompositionAdapterError("source numeric sidecar is missing or symlinked")
    sidecar_path = sidecar_path.resolve()
    if not sidecar_path.is_relative_to(source_root):
        raise V023CompositionAdapterError(
            "source numeric sidecar escapes the authenticated source directory"
        )
    expected_sidecar_sha = _sha256(
        getattr(artifact, "sidecar_sha256", None), name="source sidecar sha256"
    )
    if _file_sha256(sidecar_path, label="source numeric sidecar") != expected_sidecar_sha:
        raise V023CompositionAdapterError("source numeric sidecar byte hash disagrees")
    try:
        with np.load(sidecar_path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError, KeyError) as error:
        raise V023CompositionAdapterError("source numeric sidecar cannot be safely loaded") from error
    if any(value.dtype == object for value in arrays.values()):
        raise V023CompositionAdapterError("source numeric sidecar contains object dtype")
    required = {
        "anchor_phase",
        "anchor_content_digest",
        "anchor_view_content_digest",
        "anchor_topology_content_digest",
        "action_mask",
        "reference_actions",
        "physical_keys",
        "q1_values",
        "q2_values",
        "q12_values",
        "pair_anchor_index",
        "pair_id",
        "pair_user_ids",
        "pair_action_ids",
        "pair_target_by_draw",
        "pair_target_mean",
        "draw_pair_index",
        "draw_index",
        "draw_pair_id",
        "profile_actions",
        "profile_bits",
        "profile_link_rate_bps",
        "profile_link_power_w",
        "profile_link_sinr",
        "profile_energy_j",
        "profile_g_bits",
        "profile_system_power_w",
        "profile_fixed_power_w",
        "profile_served",
        "profile_active_beam_keys",
        "profile_active_beam_counts",
        "profile_active_satellites",
        "profile_active_satellite_counts",
        "profile_beam_power_w",
        "z3_bits_by_draw",
        "z3_normalized_by_draw",
        "formula_identity_residual_bits",
        "ratio_identity_value_bits",
        "joint_ee_bits_per_j",
        "nonmutation_flags",
        "common_field_digest",
        "action_digest",
        "ratio_cross_product",
        "ratio_sign",
        "ratio_tolerance",
        "ratio_local_tolerance",
        "formula_own_bits",
        "formula_nonfocal_bits",
        "formula_d_bits",
        "formula_joint_delta_bits",
        "formula_joint_delta_energy_j",
        "formula_joint_surplus_bits",
        "formula_interaction_bits",
        "formula_interaction_energy_j",
        "formula_interaction_surplus_bits",
        "formula_equal_share_bits",
    }
    if not required.issubset(arrays):
        raise V023CompositionAdapterError(
            "source numeric sidecar omits composition arrays: "
            + ", ".join(sorted(required - set(arrays)))
        )
    exact_dtypes: dict[str, np.dtype] = {}
    for name in (
        "q1_values",
        "q2_values",
        "q12_values",
        "pair_target_by_draw",
        "pair_target_mean",
        "profile_bits",
        "profile_link_rate_bps",
        "profile_link_power_w",
        "profile_link_sinr",
        "profile_energy_j",
        "profile_g_bits",
        "profile_system_power_w",
        "profile_fixed_power_w",
        "profile_beam_power_w",
        "z3_bits_by_draw",
        "z3_normalized_by_draw",
        "formula_identity_residual_bits",
        "ratio_identity_value_bits",
        "joint_ee_bits_per_j",
        "ratio_cross_product",
        "ratio_tolerance",
        "ratio_local_tolerance",
        "formula_own_bits",
        "formula_nonfocal_bits",
        "formula_d_bits",
        "formula_joint_delta_bits",
        "formula_joint_delta_energy_j",
        "formula_joint_surplus_bits",
        "formula_interaction_bits",
        "formula_interaction_energy_j",
        "formula_interaction_surplus_bits",
        "formula_equal_share_bits",
    ):
        exact_dtypes[name] = np.dtype(np.float64)
    for name in (
        "anchor_phase",
        "reference_actions",
        "physical_keys",
        "pair_anchor_index",
        "pair_user_ids",
        "pair_action_ids",
        "draw_pair_index",
        "draw_index",
        "profile_actions",
        "profile_active_beam_keys",
        "profile_active_beam_counts",
        "profile_active_satellites",
        "profile_active_satellite_counts",
    ):
        exact_dtypes[name] = np.dtype(np.int64)
    for name in ("action_mask", "profile_served", "nonmutation_flags"):
        exact_dtypes[name] = np.dtype(np.bool_)
    exact_dtypes["ratio_sign"] = np.dtype(np.int8)
    for name in (
        "anchor_content_digest",
        "anchor_view_content_digest",
        "anchor_topology_content_digest",
        "common_field_digest",
        "action_digest",
    ):
        exact_dtypes[name] = np.dtype("S64")
    exact_dtypes["pair_id"] = np.dtype("S256")
    exact_dtypes["draw_pair_id"] = np.dtype("S256")
    wrong_dtypes = sorted(
        name
        for name, dtype in exact_dtypes.items()
        if np.asarray(arrays[name]).dtype != dtype
    )
    if wrong_dtypes:
        raise V023CompositionAdapterError(
            "source numeric sidecar dtype drift: " + ", ".join(wrong_dtypes)
        )
    phases = np.asarray(arrays["anchor_phase"])
    if phases.dtype != np.int64 or tuple(phases.tolist()) != V023_ANCHOR_PHASES:
        raise V023CompositionAdapterError("source anchor phase array drifted")
    q1_values = np.asarray(arrays["q1_values"])
    q2_values = np.asarray(arrays["q2_values"])
    q12_values = np.asarray(arrays["q12_values"])
    if (
        q1_values.ndim != 3
        or q1_values.shape != q2_values.shape
        or q1_values.shape != q12_values.shape
        or q1_values.shape[0] != 9
        or q1_values.shape[2] != V023_ACTION_COUNT
    ):
        raise V023CompositionAdapterError("source Q1/Q2/Q12 shapes drifted")
    q1_f32 = q1_values.astype(np.float32)
    q2_f32 = q2_values.astype(np.float32)
    if not np.array_equal(q12_values.astype(np.float32), (q1_f32 + q2_f32).astype(np.float32)):
        raise V023CompositionAdapterError("source Q12 is not exact float32 Q1+Q2")
    pair_anchor = np.asarray(arrays["pair_anchor_index"])
    pair_count = int(pair_anchor.size)
    pair_shape_checks = (
        pair_anchor.dtype == np.int64,
        np.asarray(arrays["pair_id"]).shape == (pair_count,),
        np.asarray(arrays["pair_user_ids"]).shape == (pair_count, 2),
        np.asarray(arrays["pair_action_ids"]).shape == (pair_count, 2),
        np.asarray(arrays["pair_target_by_draw"]).shape
        == (pair_count, V023_DRAW_COUNT, 2),
        np.asarray(arrays["pair_target_mean"]).shape == (pair_count, 2),
    )
    if not all(pair_shape_checks) or np.any(pair_anchor < 0) or np.any(pair_anchor >= 9):
        raise V023CompositionAdapterError("source pair identity arrays are malformed")
    pair_target_by_draw = np.asarray(arrays["pair_target_by_draw"])
    pair_target_mean = np.asarray(arrays["pair_target_mean"])
    if not np.array_equal(
        np.mean(pair_target_by_draw, axis=1, dtype=np.float64), pair_target_mean
    ):
        raise V023CompositionAdapterError(
            "source pair target means disagree with the 32 draws"
        )
    draw_pair = np.asarray(arrays["draw_pair_index"])
    draw_index = np.asarray(arrays["draw_index"])
    draw_pair_id = np.asarray(arrays["draw_pair_id"])
    row_count = pair_count * V023_DRAW_COUNT
    if draw_pair.shape != (row_count,) or draw_index.shape != (row_count,):
        raise V023CompositionAdapterError("source pair draw indices have wrong shapes")
    if draw_pair_id.shape != (row_count,):
        raise V023CompositionAdapterError("source pair draw identifiers are malformed")
    users = q1_values.shape[1]
    beam_keys = np.asarray(arrays["profile_active_beam_keys"])
    satellites = np.asarray(arrays["profile_active_satellites"])
    mechanics_shape_checks = (
        np.asarray(arrays["profile_actions"]).shape == (row_count, 4, users),
        np.asarray(arrays["profile_bits"]).shape == (row_count, 4, users),
        np.asarray(arrays["profile_link_rate_bps"]).shape == (row_count, 4, users),
        np.asarray(arrays["profile_link_power_w"]).shape == (row_count, 4, users),
        np.asarray(arrays["profile_link_sinr"]).shape == (row_count, 4, users),
        np.asarray(arrays["profile_energy_j"]).shape == (row_count, 4),
        np.asarray(arrays["profile_g_bits"]).shape == (row_count, 4),
        np.asarray(arrays["profile_system_power_w"]).shape == (row_count, 4),
        np.asarray(arrays["profile_fixed_power_w"]).shape == (row_count, 4),
        np.asarray(arrays["profile_served"]).shape == (row_count, 4, users),
        beam_keys.ndim == 4,
        beam_keys.shape[:2] == (row_count, 4),
        beam_keys.shape[3:] == (2,),
        np.asarray(arrays["profile_active_beam_counts"]).shape == (row_count, 4),
        np.asarray(arrays["profile_beam_power_w"]).shape == beam_keys.shape[:3],
        satellites.ndim == 3,
        satellites.shape[:2] == (row_count, 4),
        np.asarray(arrays["profile_active_satellite_counts"]).shape
        == (row_count, 4),
        np.asarray(arrays["z3_bits_by_draw"]).shape == (row_count, 2),
        np.asarray(arrays["z3_normalized_by_draw"]).shape == (row_count, 2),
        np.asarray(arrays["formula_own_bits"]).shape == (row_count, 2),
        np.asarray(arrays["formula_nonfocal_bits"]).shape == (row_count, 2),
        np.asarray(arrays["formula_d_bits"]).shape == (row_count, 2),
        np.asarray(arrays["nonmutation_flags"]).shape == (row_count, 5),
        np.asarray(arrays["common_field_digest"]).shape == (row_count,),
        np.asarray(arrays["action_digest"]).shape == (row_count, 4),
    )
    scalar_mechanics = (
        "formula_identity_residual_bits",
        "ratio_identity_value_bits",
        "joint_ee_bits_per_j",
        "ratio_cross_product",
        "ratio_sign",
        "ratio_tolerance",
        "ratio_local_tolerance",
        "formula_joint_delta_bits",
        "formula_joint_delta_energy_j",
        "formula_joint_surplus_bits",
        "formula_interaction_bits",
        "formula_interaction_energy_j",
        "formula_interaction_surplus_bits",
        "formula_equal_share_bits",
    )
    if not all(mechanics_shape_checks) or any(
        np.asarray(arrays[name]).shape != (row_count,)
        for name in scalar_mechanics
    ):
        raise V023CompositionAdapterError("source raw mechanics arrays have wrong shapes")
    declared_anchors: list[DeclaredAnchor] = []
    for anchor_index, entry in enumerate(anchors_json):
        if not isinstance(entry, Mapping) or entry.get("phase") != anchor_index + 1:
            raise V023CompositionAdapterError("source anchor JSON order drifted")
        if _decode_fixed_ascii(
            arrays["anchor_content_digest"][anchor_index], label="anchor content digest"
        ) != entry.get("predecision_sha256"):
            raise V023CompositionAdapterError("source predecision array/JSON digest disagrees")
        topology = entry.get("topology")
        topology_pairs = topology.get("pairs") if isinstance(topology, Mapping) else None
        if not isinstance(topology_pairs, list):
            raise V023CompositionAdapterError("source anchor topology pairs are missing")
        topology_content_digest = _decode_fixed_ascii(
            arrays["anchor_topology_content_digest"][anchor_index],
            label="anchor topology content digest",
        )
        if topology.get("content_digest") != topology_content_digest:
            raise V023CompositionAdapterError(
                "source topology content array/JSON digest disagrees"
            )
        selected_pairs = np.flatnonzero(pair_anchor == anchor_index)
        if len(topology_pairs) != selected_pairs.size:
            raise V023CompositionAdapterError("source topology/pair count disagrees")
        teacher = np.zeros(q1_f32.shape[1:], dtype=np.float32)
        pairs: list[DeclaredPair] = []
        for pair_offset, pair_row_raw in enumerate(selected_pairs.tolist()):
            pair_row = int(pair_row_raw)
            topology_pair = topology_pairs[pair_offset]
            if not isinstance(topology_pair, Mapping):
                raise V023CompositionAdapterError("source topology pair is malformed")
            pair_id = _decode_fixed_ascii(arrays["pair_id"][pair_row], label="pair_id")
            if topology_pair.get("pair_id") != pair_id:
                raise V023CompositionAdapterError("source topology/pair order disagrees")
            users_pair = tuple(
                int(value) for value in np.asarray(arrays["pair_user_ids"])[pair_row].tolist()
            )
            actions_pair = tuple(
                int(value) for value in np.asarray(arrays["pair_action_ids"])[pair_row].tolist()
            )
            if tuple(topology_pair.get("member_users", ())) != users_pair or tuple(
                topology_pair.get("designated_actions", ())
            ) != actions_pair:
                raise V023CompositionAdapterError("source topology/pair identity disagrees")
            rows = np.flatnonzero(draw_pair == pair_row)
            if rows.size != V023_DRAW_COUNT or not np.array_equal(
                draw_index[rows], np.arange(V023_DRAW_COUNT, dtype=np.int64)
            ):
                raise V023CompositionAdapterError("source pair does not retain draws 0..31")
            if any(
                _decode_fixed_ascii(draw_pair_id[row], label="draw pair_id") != pair_id
                for row in rows.tolist()
            ):
                raise V023CompositionAdapterError("source pair draw identity disagrees")
            mechanics = PairSourceMechanics(
                target_by_draw=pair_target_by_draw[pair_row],
                profile_link_rate_bps=np.asarray(arrays["profile_link_rate_bps"])[rows],
                profile_link_power_w=np.asarray(arrays["profile_link_power_w"])[rows],
                profile_link_sinr=np.asarray(arrays["profile_link_sinr"])[rows],
                profile_g_bits=np.asarray(arrays["profile_g_bits"])[rows],
                profile_system_power_w=np.asarray(
                    arrays["profile_system_power_w"]
                )[rows],
                profile_fixed_power_w=np.asarray(arrays["profile_fixed_power_w"])[rows],
                profile_active_beam_keys=np.asarray(
                    arrays["profile_active_beam_keys"]
                )[rows],
                profile_active_beam_counts=np.asarray(
                    arrays["profile_active_beam_counts"]
                )[rows],
                profile_active_satellites=np.asarray(
                    arrays["profile_active_satellites"]
                )[rows],
                profile_active_satellite_counts=np.asarray(
                    arrays["profile_active_satellite_counts"]
                )[rows],
                profile_beam_power_w=np.asarray(arrays["profile_beam_power_w"])[rows],
                z3_bits_by_draw=np.asarray(arrays["z3_bits_by_draw"])[rows],
                z3_normalized_by_draw=np.asarray(
                    arrays["z3_normalized_by_draw"]
                )[rows],
                formula_identity_residual_bits=np.asarray(
                    arrays["formula_identity_residual_bits"]
                )[rows],
                ratio_identity_value_bits=np.asarray(
                    arrays["ratio_identity_value_bits"]
                )[rows],
                joint_ee_bits_per_j=np.asarray(arrays["joint_ee_bits_per_j"])[rows],
                source_nonmutation_flags=np.asarray(arrays["nonmutation_flags"])[rows],
                action_digest=np.asarray(arrays["action_digest"])[rows],
                ratio_cross_product=np.asarray(arrays["ratio_cross_product"])[rows],
                ratio_sign=np.asarray(arrays["ratio_sign"])[rows],
                ratio_tolerance=np.asarray(arrays["ratio_tolerance"])[rows],
                ratio_local_tolerance=np.asarray(
                    arrays["ratio_local_tolerance"]
                )[rows],
                formula_own_bits=np.asarray(arrays["formula_own_bits"])[rows],
                formula_nonfocal_bits=np.asarray(
                    arrays["formula_nonfocal_bits"]
                )[rows],
                formula_d_bits=np.asarray(arrays["formula_d_bits"])[rows],
                formula_joint_delta_bits=np.asarray(
                    arrays["formula_joint_delta_bits"]
                )[rows],
                formula_joint_delta_energy_j=np.asarray(
                    arrays["formula_joint_delta_energy_j"]
                )[rows],
                formula_joint_surplus_bits=np.asarray(
                    arrays["formula_joint_surplus_bits"]
                )[rows],
                formula_interaction_bits=np.asarray(
                    arrays["formula_interaction_bits"]
                )[rows],
                formula_interaction_energy_j=np.asarray(
                    arrays["formula_interaction_energy_j"]
                )[rows],
                formula_interaction_surplus_bits=np.asarray(
                    arrays["formula_interaction_surplus_bits"]
                )[rows],
                formula_equal_share_bits=np.asarray(
                    arrays["formula_equal_share_bits"]
                )[rows],
            )
            means = pair_target_mean[pair_row].astype(np.float32)
            for user, action, value in zip(users_pair, actions_pair, means, strict=True):
                if teacher[user, action] != 0.0:
                    raise V023CompositionAdapterError("source teacher cells overlap")
                teacher[user, action] = value
            try:
                source_key = tuple(int(value) for value in topology_pair["source_key"])
                destination_keys = tuple(
                    tuple(int(value) for value in key)
                    for key in topology_pair["destination_keys"]
                )
            except (KeyError, TypeError, ValueError) as error:
                raise V023CompositionAdapterError("source pair topology keys are malformed") from error
            pairs.append(
                DeclaredPair(
                    pair_id=pair_id,
                    member_users=users_pair,
                    designated_actions=actions_pair,
                    source_key=source_key,
                    destination_keys=destination_keys,
                    profile_actions=np.asarray(arrays["profile_actions"])[rows],
                    profile_bits=np.asarray(arrays["profile_bits"])[rows],
                    profile_energy_j=np.asarray(arrays["profile_energy_j"])[rows],
                    profile_served=np.asarray(arrays["profile_served"])[rows],
                    common_field_digest=np.asarray(arrays["common_field_digest"])[rows],
                    mechanics=mechanics,
                )
            )
        declared_anchors.append(
            DeclaredAnchor(
                world=spec.held_out_world,
                phase=anchor_index + 1,
                anchor_id=str(entry.get("anchor_id")),
                predecision_sha256=str(entry.get("predecision_sha256")),
                state_schema_sha256=str(entry.get("state_schema_sha256")),
                state_sha256=str(entry.get("state_sha256")),
                q12_snapshot_sha256=str(entry.get("q12_snapshot_sha256")),
                q12_model_sha256=str(entry.get("q12_model_sha256")),
                q12_source_state_sha256=str(entry.get("q12_source_state_sha256")),
                q12_event_sha256=str(entry.get("q12_event_sha256")),
                view_sha256=_decode_fixed_ascii(
                    arrays["anchor_view_content_digest"][anchor_index],
                    label="anchor view digest",
                ),
                topology_sha256=topology_content_digest,
                q1=q1_f32[anchor_index],
                q2=q2_f32[anchor_index],
                action_mask=np.asarray(arrays["action_mask"])[anchor_index],
                reference_actions=np.asarray(arrays["reference_actions"])[anchor_index],
                physical_keys=np.asarray(arrays["physical_keys"])[anchor_index],
                teacher_q3=teacher,
                pairs=tuple(pairs),
                reference_actions_sha256=str(entry.get("reference_actions_sha256")),
            )
        )
    world_receipt = index.get("world_receipt")
    if not isinstance(world_receipt, Mapping):
        raise V023CompositionAdapterError("source world receipt is missing")
    return AuthenticatedSourceArtifact(
        world=spec.held_out_world,
        preflight_manifest_sha256=spec.preflight_manifest_sha256,
        source_manifest_sha256=spec.source_manifest_sha256,
        source_index_sha256=_sha256(
            getattr(artifact, "index_sha256", None), name="source index sha256"
        ),
        field_root_sha256=_sha256(
            world_receipt.get("field_root_digest"), name="source field root digest"
        ),
        anchors=tuple(declared_anchors),
    )


def authenticate_fit_artifact(
    spec: CompositionShardSpec,
    *,
    device: object = "cpu",
    fit_adapter_module: ModuleType | None = None,
) -> AuthenticatedFitArtifact:
    """Verify fit-side receipts and safely reconstruct one frozen Q3 network."""

    if not isinstance(spec, CompositionShardSpec):
        raise V023CompositionAdapterError("fit authentication needs a typed shard spec")
    module = fit_adapter_module or _fit_adapter_module()
    verifier = getattr(module, "verify_v023_fit_sidecars", None)
    if not callable(verifier):
        raise V023CompositionAdapterError("fit adapter lacks its sidecar verifier")
    try:
        verification = verifier(spec.fit_receipt)
    except Exception as error:
        raise V023CompositionAdapterError("fit-side receipt verification failed") from error
    if not isinstance(verification, Mapping) or verification.get("status") != "PASS_FIT_SIDECARS":
        raise V023CompositionAdapterError("fit-side receipt verifier did not pass")
    payload = _read_sealed_json(spec.fit_receipt, label="fit receipt")
    expected_fit_schema = getattr(module, "V023_FIT_SCHEMA", None)
    expected_claim = getattr(module, "V023_FIT_CLAIM_CEILING", V023_CLAIM_CEILING)
    if payload.get("schema") != expected_fit_schema or payload.get("claim_ceiling") != expected_claim:
        raise V023CompositionAdapterError("fit receipt schema/claim ceiling drifted")
    if payload.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise V023CompositionAdapterError("fit receipt contract digest drifted")
    expected = {
        "held_out_world": spec.held_out_world,
        "student_seed": spec.student_seed,
        "arm": spec.arm,
        "preflight_manifest_sha256": spec.preflight_manifest_sha256,
        "source_manifest_sha256": spec.source_manifest_sha256,
        "update_count": 2000,
        "split": "TRAIN_DEVELOPMENT",
    }
    for field_name, value in expected.items():
        if payload.get(field_name) != value:
            raise V023CompositionAdapterError(f"fit receipt {field_name} disagrees")
    if (
        payload.get("status") != "PASS"
        or payload.get("learner_update") is not True
        or payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("test_worlds") != []
    ):
        raise V023CompositionAdapterError("fit receipt boundary flags disagree")
    source_panel = payload.get("source_panel")
    source_indices = (
        source_panel.get("source_index_sha256s")
        if isinstance(source_panel, Mapping)
        else None
    )
    if not isinstance(source_indices, Mapping):
        raise V023CompositionAdapterError("fit receipt source-index map is missing")
    source_index_sha256 = _sha256(
        source_indices.get(str(spec.held_out_world)),
        name="fit held-out source index sha256",
    )
    model_state = payload.get("model_state")
    if not isinstance(model_state, Mapping) or model_state.get("no_pickle") is not True:
        raise V023CompositionAdapterError("fit model-state receipt is malformed")
    expected_domain = getattr(module, "V023_FIT_MODEL_ARRAY_DOMAIN", None)
    if model_state.get("array_domain") != expected_domain:
        raise V023CompositionAdapterError("fit model array domain drifted")
    model_path = _safe_artifact_child(
        Path(spec.fit_receipt).parent,
        model_state.get("path"),
        label="fit model NPZ",
    )
    model_bytes = _file_sha256(model_path, label="fit model NPZ")
    if (
        model_bytes != _sha256(payload.get("model_sha256"), name="fit model byte hash")
        or model_bytes != _sha256(model_state.get("npz_sha256"), name="fit nested model byte hash")
    ):
        raise V023CompositionAdapterError("fit model byte hash disagrees")
    metadata = model_state.get("arrays")
    if not isinstance(metadata, Mapping):
        raise V023CompositionAdapterError("fit model array metadata is missing")
    try:
        with np.load(model_path, allow_pickle=False) as archive:
            model_arrays = {
                name: np.array(archive[name], copy=True) for name in archive.files
            }
    except (OSError, ValueError, KeyError) as error:
        raise V023CompositionAdapterError("fit model NPZ cannot be safely loaded") from error
    if any(value.dtype == object for value in model_arrays.values()):
        raise V023CompositionAdapterError("fit model NPZ contains object dtype")
    expected_keys: set[str] = set()
    for parameter_name, entry in metadata.items():
        if not isinstance(parameter_name, str) or not isinstance(entry, Mapping):
            raise V023CompositionAdapterError("fit model metadata is malformed")
        key = entry.get("npz_key")
        if not isinstance(key, str) or key not in model_arrays:
            raise V023CompositionAdapterError("fit model metadata NPZ key is missing")
        expected_keys.add(key)
        array = model_arrays[key]
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023CompositionAdapterError("fit model dtype/shape metadata disagrees")
        if entry.get("sha256") != array_sha256(array, domain=str(expected_domain)):
            raise V023CompositionAdapterError("fit model array digest disagrees")
    if expected_keys != set(model_arrays):
        raise V023CompositionAdapterError("fit model NPZ keys disagree with metadata")
    network_type = getattr(module, "LCSRSC3QNetwork", None)
    digestor = getattr(module, "lcsrs_c3_network_sha256", None)
    if not callable(network_type) or not callable(digestor):
        raise V023CompositionAdapterError("fit adapter omits frozen Q3 model hooks")
    try:
        import torch

        network = network_type()
        state = network.state_dict()
        if set(state) != set(metadata):
            raise V023CompositionAdapterError("fit model parameter names disagree")
        rebuilt: dict[str, object] = {}
        for parameter_name, template in state.items():
            key = str(metadata[parameter_name]["npz_key"])
            tensor = torch.from_numpy(np.array(model_arrays[key], copy=True)).to(
                dtype=template.dtype
            )
            if tuple(tensor.shape) != tuple(template.shape):
                raise V023CompositionAdapterError("fit model parameter shape disagrees")
            rebuilt[parameter_name] = tensor
        network.load_state_dict(rebuilt, strict=True)
        network.to(device)
        network.eval()
    except V023CompositionAdapterError:
        raise
    except Exception as error:
        raise V023CompositionAdapterError("fit model reconstruction failed") from error
    logical = _sha256(digestor(network), name="reconstructed fit model digest")
    if (
        logical != _sha256(payload.get("network_sha256"), name="fit network digest")
        or logical
        != _sha256(
            model_state.get("logical_network_sha256"),
            name="fit nested network digest",
        )
    ):
        raise V023CompositionAdapterError("reconstructed fit model digest disagrees")
    return AuthenticatedFitArtifact(
        held_out_world=spec.held_out_world,
        student_seed=spec.student_seed,
        arm=spec.arm,
        preflight_manifest_sha256=spec.preflight_manifest_sha256,
        source_manifest_sha256=spec.source_manifest_sha256,
        fit_receipt_sha256=_file_sha256(spec.fit_receipt, label="fit receipt"),
        model_bytes_sha256=model_bytes,
        model_sha256=logical,
        model=network,
        update_count=2000,
        fit_receipt_content_sha256=_sha256(
            payload.get("receipt_sha256"), name="fit receipt content sha256"
        ),
        source_index_sha256=source_index_sha256,
    )


def default_model_digestor(model: object) -> str:
    """Hash the frozen native Q3 model without serialising or fitting it."""

    try:
        from mcrl.runtime.ee_axis_lcsrs_c3_learner import lcsrs_c3_network_sha256

        return _sha256(lcsrs_c3_network_sha256(model), name="Q3 model digest")
    except V023CompositionAdapterError:
        raise
    except Exception as error:
        raise V023CompositionAdapterError("Q3 model digest failed") from error


def default_q3_evaluator(request: Q3InferenceInput) -> np.ndarray:
    """Evaluate one frozen Q3 head once; teacher data is absent from this API."""

    if not isinstance(request, Q3InferenceInput):
        raise V023CompositionAdapterError("Q3 evaluator needs a typed inference request")
    forward = getattr(request.model, "forward_view", None)
    if not callable(forward) or getattr(request.model, "training", None) is not False:
        raise V023CompositionAdapterError("Q3 model is not a frozen eval-mode native head")
    try:
        import torch

        with torch.no_grad():
            result = forward(request.view)
        return np.asarray(result.detach().cpu().numpy(), dtype=np.float32)
    except Exception as error:
        raise V023CompositionAdapterError("native Q3 evaluation failed") from error


def _pack_composition_arrays(
    compositions: Sequence[AnchorComposition],
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    """Pack every raw selection, draw, profile, topology, and denominator value."""

    if len(compositions) != len(V023_ANCHOR_PHASES):
        raise V023CompositionAdapterError("composition does not retain all nine anchors")
    anchors = [item.declared for item in compositions]
    users = anchors[0].q1.shape[0]
    if any(anchor.q1.shape != (users, V023_ACTION_COUNT) for anchor in anchors):
        raise V023CompositionAdapterError("composition anchor roster/action shape drifted")
    if len({item.arm for item in compositions}) != 1:
        raise V023CompositionAdapterError("composition arm drifted between anchors")

    arrays: dict[str, np.ndarray] = {
        "anchor_phase": np.asarray([anchor.phase for anchor in anchors], dtype=np.int64),
        "anchor_id": _ascii_array(
            [anchor.anchor_id for anchor in anchors], width=256, name="anchor_id"
        ),
        "anchor_predecision_sha256": _ascii_array(
            [anchor.predecision_sha256 for anchor in anchors], width=64,
            name="anchor predecision digest",
        ),
        "anchor_state_schema_sha256": _ascii_array(
            [anchor.state_schema_sha256 for anchor in anchors], width=64,
            name="anchor state-schema digest",
        ),
        "anchor_state_sha256": _ascii_array(
            [anchor.state_sha256 for anchor in anchors], width=64,
            name="anchor state digest",
        ),
        "anchor_q12_snapshot_sha256": _ascii_array(
            [anchor.q12_snapshot_sha256 for anchor in anchors], width=64,
            name="anchor Q12 snapshot digest",
        ),
        "anchor_q12_model_sha256": _ascii_array(
            [anchor.q12_model_sha256 for anchor in anchors], width=64,
            name="anchor Q12 model digest",
        ),
        "anchor_q12_source_state_sha256": _ascii_array(
            [anchor.q12_source_state_sha256 for anchor in anchors], width=64,
            name="anchor Q12 state digest",
        ),
        "anchor_q12_event_sha256": _ascii_array(
            [anchor.q12_event_sha256 for anchor in anchors], width=64,
            name="anchor Q12 event digest",
        ),
        "anchor_view_sha256": _ascii_array(
            [anchor.view_sha256 for anchor in anchors], width=64,
            name="anchor view digest",
        ),
        "anchor_topology_sha256": _ascii_array(
            [anchor.topology_sha256 for anchor in anchors], width=64,
            name="anchor topology digest",
        ),
        "anchor_reference_actions_sha256": _ascii_array(
            [anchor.reference_actions_sha256 for anchor in anchors], width=64,
            name="anchor reference digest",
        ),
        "q1": np.stack([anchor.q1 for anchor in anchors]).astype(np.float32),
        "q2": np.stack([anchor.q2 for anchor in anchors]).astype(np.float32),
        "q12": np.stack([anchor.q12 for anchor in anchors]).astype(np.float32),
        "q3": np.stack([item.learned.q3 for item in compositions]).astype(np.float32),
        "teacher_q3": np.stack([anchor.teacher_q3 for anchor in anchors]).astype(np.float32),
        "action_mask": np.stack([anchor.action_mask for anchor in anchors]).astype(np.bool_),
        "physical_keys": np.stack([anchor.physical_keys for anchor in anchors]).astype(np.int64),
        "baseline_actions": np.stack([item.baseline_actions for item in compositions]).astype(np.int64),
        "learned_actions": np.stack([item.learned.actions for item in compositions]).astype(np.int64),
        "teacher_actions": np.stack([item.teacher_actions for item in compositions]).astype(np.int64),
        "baseline_exact_tie_count": np.stack(
            [item.baseline_exact_tie_count for item in compositions]
        ).astype(np.int64),
        "learned_exact_tie_count": np.stack(
            [item.learned.exact_tie_count for item in compositions]
        ).astype(np.int64),
        "teacher_exact_tie_count": np.stack(
            [item.teacher_exact_tie_count for item in compositions]
        ).astype(np.int64),
    }
    arrays["full_roster_learned_action_changed"] = (
        arrays["learned_actions"] != arrays["baseline_actions"]
    )
    arrays["full_roster_teacher_action_changed"] = (
        arrays["teacher_actions"] != arrays["baseline_actions"]
    )

    roles = 3
    all_physical = [result for item in compositions for result in item.physical]
    max_beams = max(result.active_beam_keys.shape[1] for result in all_physical)
    max_satellites = max(result.active_satellites.shape[1] for result in all_physical)
    nonmutation_names = all_physical[0].nonmutation_names
    if any(result.nonmutation_names != nonmutation_names for result in all_physical):
        raise V023CompositionAdapterError("physical nonmutation field names drifted")
    nonmutation_count = len(nonmutation_names)
    physical_actions = np.zeros((9, roles, users), dtype=np.int64)
    physical_draw = np.zeros((9, roles, V023_DRAW_COUNT), dtype=np.int64)
    physical_total = np.zeros((9, roles, V023_DRAW_COUNT), dtype=np.float64)
    physical_bits = np.zeros((9, roles, V023_DRAW_COUNT, users), dtype=np.float64)
    physical_energy = np.zeros((9, roles, V023_DRAW_COUNT), dtype=np.float64)
    physical_served = np.zeros((9, roles, V023_DRAW_COUNT, users), dtype=np.bool_)
    beam_counts = np.zeros((9, roles, V023_DRAW_COUNT), dtype=np.int64)
    beam_keys = np.full(
        (9, roles, V023_DRAW_COUNT, max_beams, 2), -1, dtype=np.int64
    )
    beam_power = np.zeros((9, roles, V023_DRAW_COUNT, max_beams), dtype=np.float64)
    satellite_counts = np.zeros((9, roles, V023_DRAW_COUNT), dtype=np.int64)
    satellites = np.full(
        (9, roles, V023_DRAW_COUNT, max_satellites), -1, dtype=np.int64
    )
    common_fields = np.empty((9, roles, V023_DRAW_COUNT), dtype="S64")
    action_hashes = np.empty((9, roles), dtype="S64")
    nonmutation_before = np.empty(
        (9, roles, V023_DRAW_COUNT, nonmutation_count), dtype="S64"
    )
    nonmutation_after = np.empty_like(nonmutation_before)
    nonmutation_flags = np.zeros(nonmutation_before.shape, dtype=np.bool_)
    for anchor_index, item in enumerate(compositions):
        for role_index, result in enumerate(item.physical):
            physical_actions[anchor_index, role_index] = result.actions
            physical_draw[anchor_index, role_index] = result.draw_index
            physical_total[anchor_index, role_index] = result.total_bits
            physical_bits[anchor_index, role_index] = result.per_user_bits
            physical_energy[anchor_index, role_index] = result.energy_j
            physical_served[anchor_index, role_index] = result.served
            beam_counts[anchor_index, role_index] = result.active_beam_counts
            width = result.active_beam_keys.shape[1]
            beam_keys[anchor_index, role_index, :, :width] = result.active_beam_keys
            beam_power[anchor_index, role_index, :, :width] = result.beam_power_w
            satellite_counts[anchor_index, role_index] = result.active_satellite_counts
            sat_width = result.active_satellites.shape[1]
            satellites[anchor_index, role_index, :, :sat_width] = result.active_satellites
            common_fields[anchor_index, role_index] = result.common_field_digest
            action_hashes[anchor_index, role_index] = result.action_sha256.encode("ascii")
            nonmutation_before[anchor_index, role_index] = result.nonmutation_before_sha256
            nonmutation_after[anchor_index, role_index] = result.nonmutation_after_sha256
            nonmutation_flags[anchor_index, role_index] = result.nonmutation_flags
    arrays.update({
        "physical_role": _ascii_array(
            ("ZERO_SURFACE_B", compositions[0].arm, "TEACHER_ORACLE"),
            width=32,
            name="physical role",
        ),
        "physical_actions": physical_actions,
        "physical_action_sha256": action_hashes,
        "physical_draw_index": physical_draw,
        "physical_total_bits": physical_total,
        "physical_per_user_bits": physical_bits,
        "physical_energy_j": physical_energy,
        "physical_served": physical_served,
        "physical_served_count": np.count_nonzero(physical_served, axis=(2, 3)).astype(np.int64),
        "physical_service_denominator": np.full(
            (9, roles), V023_DRAW_COUNT * users, dtype=np.int64
        ),
        "physical_active_beam_counts": beam_counts,
        "physical_active_beam_keys": beam_keys,
        "physical_beam_power_w": beam_power,
        "physical_active_satellite_counts": satellite_counts,
        "physical_active_satellites": satellites,
        "physical_common_field_digest": common_fields,
        "physical_nonmutation_name": _ascii_array(
            nonmutation_names, width=128, name="nonmutation name"
        ),
        "physical_nonmutation_before_sha256": nonmutation_before,
        "physical_nonmutation_after_sha256": nonmutation_after,
        "physical_nonmutation_flags": nonmutation_flags,
    })

    ratio_cross = np.zeros((9, roles), dtype=np.float64)
    ratio_tolerance = np.zeros((9, roles), dtype=np.float64)
    ratio_direction = np.zeros((9, roles), dtype=np.int8)
    for anchor_index in range(9):
        b_bits = float(np.sum(physical_total[anchor_index, 0], dtype=np.float64))
        b_energy = float(np.sum(physical_energy[anchor_index, 0], dtype=np.float64))
        for role_index in range(roles):
            bits = float(np.sum(physical_total[anchor_index, role_index], dtype=np.float64))
            energy = float(np.sum(physical_energy[anchor_index, role_index], dtype=np.float64))
            left = bits * b_energy
            right = b_bits * energy
            tolerance = _comparison_tolerance(left, right)
            cross = left - right
            ratio_cross[anchor_index, role_index] = cross
            ratio_tolerance[anchor_index, role_index] = tolerance
            ratio_direction[anchor_index, role_index] = (
                -1 if cross < -tolerance else 1 if cross > tolerance else 0
            )
    arrays["physical_ratio_cross_product_vs_b"] = ratio_cross
    arrays["physical_ratio_cross_product_tolerance"] = ratio_tolerance
    arrays["physical_ratio_direction_vs_b"] = ratio_direction

    pair_rows: list[tuple[int, DeclaredPair, PairClassification, PairClassification]] = []
    for anchor_index, item in enumerate(compositions):
        if item.declared.pairs and not np.array_equal(
            item.declared.pairs[0].common_field_digest,
            item.physical[0].common_field_digest,
        ):
            raise V023CompositionAdapterError(
                "physical draw panel disagrees with source pair common field"
            )
        for pair in item.declared.pairs:
            learned_class = classify_pair_actions(
                pair=pair,
                baseline_actions=item.baseline_actions,
                selected_actions=item.learned.actions,
                physical_keys=item.declared.physical_keys,
            )
            teacher_class = classify_pair_actions(
                pair=pair,
                baseline_actions=item.baseline_actions,
                selected_actions=item.teacher_actions,
                physical_keys=item.declared.physical_keys,
            )
            pair_rows.append((anchor_index, pair, learned_class, teacher_class))
    pair_count = len(pair_rows)
    profile_served = np.asarray(
        [row[1].profile_served for row in pair_rows], dtype=np.bool_
    ).reshape(pair_count, V023_DRAW_COUNT, 4, users)
    mechanics = [row[1].mechanics for row in pair_rows]

    def stack_mechanics(
        attribute: str,
        *,
        dtype: np.dtype | str,
        empty_tail: tuple[int, ...],
    ) -> np.ndarray:
        if not mechanics:
            return np.zeros((0, *empty_tail), dtype=dtype)
        try:
            return np.stack(
                [np.asarray(getattr(item, attribute)) for item in mechanics]
            ).astype(dtype, copy=False)
        except (AttributeError, TypeError, ValueError) as error:
            raise V023CompositionAdapterError(
                f"pair source mechanics cannot be stacked: {attribute}"
            ) from error

    source_mechanics_arrays = {
        "pair_target_by_draw": stack_mechanics(
            "target_by_draw", dtype=np.float64, empty_tail=(V023_DRAW_COUNT, 2)
        ),
        "pair_profile_link_rate_bps": stack_mechanics(
            "profile_link_rate_bps",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 4, users),
        ),
        "pair_profile_link_power_w": stack_mechanics(
            "profile_link_power_w",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 4, users),
        ),
        "pair_profile_link_sinr": stack_mechanics(
            "profile_link_sinr",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 4, users),
        ),
        "pair_profile_g_bits": stack_mechanics(
            "profile_g_bits", dtype=np.float64, empty_tail=(V023_DRAW_COUNT, 4)
        ),
        "pair_profile_system_power_w": stack_mechanics(
            "profile_system_power_w",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 4),
        ),
        "pair_profile_fixed_power_w": stack_mechanics(
            "profile_fixed_power_w",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 4),
        ),
        "pair_profile_active_beam_keys": stack_mechanics(
            "profile_active_beam_keys",
            dtype=np.int64,
            empty_tail=(V023_DRAW_COUNT, 4, 0, 2),
        ),
        "pair_profile_active_beam_counts": stack_mechanics(
            "profile_active_beam_counts",
            dtype=np.int64,
            empty_tail=(V023_DRAW_COUNT, 4),
        ),
        "pair_profile_active_satellites": stack_mechanics(
            "profile_active_satellites",
            dtype=np.int64,
            empty_tail=(V023_DRAW_COUNT, 4, 0),
        ),
        "pair_profile_active_satellite_counts": stack_mechanics(
            "profile_active_satellite_counts",
            dtype=np.int64,
            empty_tail=(V023_DRAW_COUNT, 4),
        ),
        "pair_profile_beam_power_w": stack_mechanics(
            "profile_beam_power_w",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 4, 0),
        ),
        "pair_z3_bits_by_draw": stack_mechanics(
            "z3_bits_by_draw", dtype=np.float64, empty_tail=(V023_DRAW_COUNT, 2)
        ),
        "pair_z3_normalized_by_draw": stack_mechanics(
            "z3_normalized_by_draw",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 2),
        ),
        "pair_formula_identity_residual_bits": stack_mechanics(
            "formula_identity_residual_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_ratio_identity_value_bits": stack_mechanics(
            "ratio_identity_value_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_joint_ee_bits_per_j": stack_mechanics(
            "joint_ee_bits_per_j",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_source_nonmutation_flags": stack_mechanics(
            "source_nonmutation_flags",
            dtype=np.bool_,
            empty_tail=(V023_DRAW_COUNT, 5),
        ),
        "pair_profile_action_sha256": stack_mechanics(
            "action_digest", dtype="S64", empty_tail=(V023_DRAW_COUNT, 4)
        ),
        "pair_ratio_cross_product": stack_mechanics(
            "ratio_cross_product", dtype=np.float64, empty_tail=(V023_DRAW_COUNT,)
        ),
        "pair_ratio_sign": stack_mechanics(
            "ratio_sign", dtype=np.int8, empty_tail=(V023_DRAW_COUNT,)
        ),
        "pair_ratio_tolerance": stack_mechanics(
            "ratio_tolerance", dtype=np.float64, empty_tail=(V023_DRAW_COUNT,)
        ),
        "pair_ratio_local_tolerance": stack_mechanics(
            "ratio_local_tolerance",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_own_bits": stack_mechanics(
            "formula_own_bits", dtype=np.float64, empty_tail=(V023_DRAW_COUNT, 2)
        ),
        "pair_formula_nonfocal_bits": stack_mechanics(
            "formula_nonfocal_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT, 2),
        ),
        "pair_formula_d_bits": stack_mechanics(
            "formula_d_bits", dtype=np.float64, empty_tail=(V023_DRAW_COUNT, 2)
        ),
        "pair_formula_joint_delta_bits": stack_mechanics(
            "formula_joint_delta_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_joint_delta_energy_j": stack_mechanics(
            "formula_joint_delta_energy_j",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_joint_surplus_bits": stack_mechanics(
            "formula_joint_surplus_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_interaction_bits": stack_mechanics(
            "formula_interaction_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_interaction_energy_j": stack_mechanics(
            "formula_interaction_energy_j",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_interaction_surplus_bits": stack_mechanics(
            "formula_interaction_surplus_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
        "pair_formula_equal_share_bits": stack_mechanics(
            "formula_equal_share_bits",
            dtype=np.float64,
            empty_tail=(V023_DRAW_COUNT,),
        ),
    }
    source_mechanics_arrays["pair_target_mean"] = np.mean(
        source_mechanics_arrays["pair_target_by_draw"], axis=1, dtype=np.float64
    )
    arrays.update({
        "pair_anchor_index": np.asarray([row[0] for row in pair_rows], dtype=np.int64),
        "pair_id": _ascii_array(
            [row[1].pair_id for row in pair_rows], width=256, name="pair_id"
        ),
        "pair_member_users": np.asarray(
            [row[1].member_users for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, 2),
        "pair_designated_actions": np.asarray(
            [row[1].designated_actions for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, 2),
        "pair_source_key": np.asarray(
            [row[1].source_key for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, 2),
        "pair_destination_keys": np.asarray(
            [row[1].destination_keys for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, 2, 2),
        "pair_profile_actions": np.asarray(
            [row[1].profile_actions for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, V023_DRAW_COUNT, 4, users),
        "pair_profile_bits": np.asarray(
            [row[1].profile_bits for row in pair_rows], dtype=np.float64
        ).reshape(pair_count, V023_DRAW_COUNT, 4, users),
        "pair_profile_energy_j": np.asarray(
            [row[1].profile_energy_j for row in pair_rows], dtype=np.float64
        ).reshape(pair_count, V023_DRAW_COUNT, 4),
        "pair_profile_served": profile_served,
        "pair_common_field_digest": np.asarray(
            [row[1].common_field_digest for row in pair_rows], dtype="S64"
        ).reshape(pair_count, V023_DRAW_COUNT),
        "learned_pair_class": np.asarray(
            [row[2].class_code for row in pair_rows], dtype=np.uint8
        ),
        "teacher_pair_class": np.asarray(
            [row[3].class_code for row in pair_rows], dtype=np.uint8
        ),
        "pair_learned_member_actions": np.asarray(
            [row[2].selected_member_actions for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, 2),
        "pair_teacher_member_actions": np.asarray(
            [row[3].selected_member_actions for row in pair_rows], dtype=np.int64
        ).reshape(pair_count, 2),
        "pair_action_change": np.asarray(
            [row[2].action_change for row in pair_rows], dtype=np.bool_
        ),
        "pair_literal_11": np.asarray(
            [row[2].literal_11 for row in pair_rows], dtype=np.bool_
        ),
        "pair_harmful_partial_evaluated": np.asarray(
            [row[2].harmful_partial_evaluated for row in pair_rows], dtype=np.bool_
        ),
        "pair_harmful_partial": np.asarray(
            [row[2].harmful_partial for row in pair_rows], dtype=np.bool_
        ),
        "pair_partial_ratio_cross_product": np.asarray(
            [row[2].partial_ratio_cross_product for row in pair_rows], dtype=np.float64
        ),
        "pair_partial_ratio_tolerance": np.asarray(
            [row[2].partial_ratio_tolerance for row in pair_rows], dtype=np.float64
        ),
        "pair_topology_evaluated": np.asarray(
            [row[2].topology_evaluated for row in pair_rows], dtype=np.bool_
        ),
        "pair_topology_consistent": np.asarray(
            [row[2].topology_consistent for row in pair_rows], dtype=np.bool_
        ),
        "pair_selected_source_empty": np.asarray(
            [row[2].source_empty for row in pair_rows], dtype=np.bool_
        ),
        "pair_destination_persist_by_nonmember": np.asarray(
            [row[2].destinations_persist_by_nonmember for row in pair_rows],
            dtype=np.bool_,
        ).reshape(pair_count, 2),
        "pair_collateral_changed_count": np.asarray(
            [row[2].collateral_changed_count for row in pair_rows], dtype=np.int64
        ),
        "pair_collateral_denominator": np.asarray(
            [row[2].collateral_denominator for row in pair_rows], dtype=np.int64
        ),
        "pair_profile_served_count": np.count_nonzero(
            profile_served, axis=(1, 3)
        ).astype(np.int64),
        "pair_profile_service_denominator": np.full(
            (pair_count, 4), V023_DRAW_COUNT * users, dtype=np.int64
        ),
    })
    partial_cross = arrays["pair_partial_ratio_cross_product"]
    partial_tolerance = arrays["pair_partial_ratio_tolerance"]
    partial_evaluated = arrays["pair_harmful_partial_evaluated"]
    arrays["pair_partial_ratio_direction"] = np.where(
        partial_evaluated & (partial_cross < -partial_tolerance),
        -1,
        np.where(
            partial_evaluated & (partial_cross > partial_tolerance), 1, 0
        ),
    ).astype(np.int8)
    arrays.update(source_mechanics_arrays)
    pair_collateral_by_user = np.zeros((pair_count, users), dtype=np.bool_)
    for row_index, (anchor_index, pair, _learned, _teacher) in enumerate(pair_rows):
        members = np.asarray(pair.member_users, dtype=np.int64)
        nonmembers = np.ones(users, dtype=np.bool_)
        nonmembers[members] = False
        pair_collateral_by_user[row_index, nonmembers] = (
            arrays["learned_actions"][anchor_index, nonmembers]
            != arrays["baseline_actions"][anchor_index, nonmembers]
        )
    arrays["pair_collateral_changed_by_user"] = pair_collateral_by_user

    selected_11 = int(np.count_nonzero(arrays["pair_literal_11"]))
    topology_numerator = int(
        np.count_nonzero(
            arrays["pair_literal_11"] & arrays["pair_topology_consistent"]
        )
    )
    if selected_11 == 0:
        topology = {
            "denominator": 0,
            "numerator": 0,
            "value": None,
            "status": "NA_ZERO_SELECTED_11",
            "predicate_ready": False,
            "predicate": False,
        }
    else:
        topology = {
            "denominator": selected_11,
            "numerator": topology_numerator,
            "value": topology_numerator / selected_11,
            "status": "OBSERVED",
            "predicate_ready": True,
            "predicate": topology_numerator == selected_11,
        }
    denominator_receipt: dict[str, object] = {
        "anchors": 9,
        "draws_per_anchor_arm": V023_DRAW_COUNT,
        "users_per_action_vector": users,
        "pair_total": pair_count,
        "action_change": pair_count,
        "literal_11": pair_count,
        "other": pair_count,
        "harmful_partial_eligible": int(
            np.count_nonzero(arrays["pair_harmful_partial_evaluated"])
        ),
        "harmful_partial_ratio_direction": {
            "denominator": int(np.count_nonzero(partial_evaluated)),
            "tie_count": int(
                np.count_nonzero(
                    partial_evaluated
                    & (arrays["pair_partial_ratio_direction"] == 0)
                )
            ),
            "missing_count": 0,
            "na_nonpartial_count": int(np.count_nonzero(~partial_evaluated)),
        },
        "full_roster_collateral": int(
            np.sum(arrays["pair_collateral_denominator"], dtype=np.int64)
        ),
        "topology_consistency": topology,
        "physical_service": int(9 * roles * V023_DRAW_COUNT * users),
        "physical_ratio_direction": {
            "denominator": int(9 * (roles - 1)),
            "tie_count": int(np.count_nonzero(ratio_direction[:, 1:] == 0)),
            "missing_count": 0,
        },
        "source_pair_draw_ratio_direction": {
            "denominator": int(pair_count * V023_DRAW_COUNT),
            "tie_count": int(np.count_nonzero(arrays["pair_ratio_sign"] == 0)),
            "missing_count": 0,
        },
        "missing_anchor_count": 0,
        "missing_draw_count": 0,
        "learned_exact_tie_users": int(
            np.count_nonzero(arrays["learned_exact_tie_count"] > 1)
        ),
        "teacher_exact_tie_users": int(
            np.count_nonzero(arrays["teacher_exact_tie_count"] > 1)
        ),
    }
    return arrays, denominator_receipt


class V023CompositionAdapter:
    """Authenticate, replay, decide once, measure once, and persist raw evidence."""

    def __init__(
        self,
        *,
        source_authenticator: Callable[[CompositionShardSpec], AuthenticatedSourceArtifact],
        fit_authenticator: Callable[[CompositionShardSpec], AuthenticatedFitArtifact],
        anchor_replayer: Callable[[ReplayAnchorRequest], ReplayedAnchor],
        q3_evaluator: Callable[[Q3InferenceInput], object],
        physical_evaluator: Callable[[PhysicalEvaluationRequest], PhysicalEvaluation],
        model_digestor: Callable[[object], str],
        native_selector: Callable[[object, object], NativeSelectionReceipt] = native_masked_argmax,
    ) -> None:
        callbacks = (
            ("source_authenticator", source_authenticator),
            ("fit_authenticator", fit_authenticator),
            ("anchor_replayer", anchor_replayer),
            ("q3_evaluator", q3_evaluator),
            ("physical_evaluator", physical_evaluator),
            ("model_digestor", model_digestor),
            ("native_selector", native_selector),
        )
        for name, callback in callbacks:
            if not callable(callback):
                raise V023CompositionAdapterError(f"{name} is not callable")
        self._source_authenticator = source_authenticator
        self._fit_authenticator = fit_authenticator
        self._anchor_replayer = anchor_replayer
        self._q3_evaluator = q3_evaluator
        self._physical_evaluator = physical_evaluator
        self._model_digestor = model_digestor
        self._native_selector = native_selector

    def compose_shard(self, spec: CompositionShardSpec) -> CompositionArtifacts:
        if not isinstance(spec, CompositionShardSpec):
            raise V023CompositionAdapterError("composition needs a typed shard spec")
        index_path, arrays_path, digest_path = _sidecar_paths(spec.output)
        _assert_write_once((index_path, arrays_path, digest_path))
        source = self._source_authenticator(spec)
        if not isinstance(source, AuthenticatedSourceArtifact):
            raise V023CompositionAdapterError("source authenticator returned wrong type")
        if source.world != spec.held_out_world:
            raise V023CompositionAdapterError("source world disagrees with shard")
        if source.preflight_manifest_sha256 != spec.preflight_manifest_sha256:
            raise V023CompositionAdapterError("source preflight manifest disagrees")
        if source.source_manifest_sha256 != spec.source_manifest_sha256:
            raise V023CompositionAdapterError("source manifest disagrees with shard")
        fitted = self._fit_authenticator(spec)
        if not isinstance(fitted, AuthenticatedFitArtifact):
            raise V023CompositionAdapterError("fit authenticator returned wrong type")
        if fitted.held_out_world != spec.held_out_world:
            raise V023CompositionAdapterError("fit world disagrees with shard")
        if fitted.student_seed != spec.student_seed:
            raise V023CompositionAdapterError("fit seed disagrees with shard")
        if fitted.arm != spec.arm:
            raise V023CompositionAdapterError("fit arm disagrees with shard")
        if fitted.preflight_manifest_sha256 != spec.preflight_manifest_sha256:
            raise V023CompositionAdapterError("fit preflight manifest disagrees")
        if fitted.source_manifest_sha256 != spec.source_manifest_sha256:
            raise V023CompositionAdapterError("fit source manifest disagrees")
        if fitted.source_index_sha256 != source.source_index_sha256:
            raise V023CompositionAdapterError("fit held-out source index disagrees")

        compositions: list[AnchorComposition] = []
        replay_handle_tokens: set[str] = set()
        for declared in source.anchors:
            request = ReplayAnchorRequest(
                world=declared.world,
                phase=declared.phase,
                anchor_id=declared.anchor_id,
                source_directory=spec.source_directory,
                preflight_manifest_sha256=spec.preflight_manifest_sha256,
                source_manifest_sha256=spec.source_manifest_sha256,
                source_index_sha256=source.source_index_sha256,
                field_root_sha256=source.field_root_sha256,
                predecision_sha256=declared.predecision_sha256,
                state_schema_sha256=declared.state_schema_sha256,
                state_sha256=declared.state_sha256,
                q12_snapshot_sha256=declared.q12_snapshot_sha256,
                q12_model_sha256=declared.q12_model_sha256,
                q12_source_state_sha256=declared.q12_source_state_sha256,
                q12_event_sha256=declared.q12_event_sha256,
                view_sha256=declared.view_sha256,
                topology_sha256=declared.topology_sha256,
                reference_actions_sha256=declared.reference_actions_sha256,
            )
            replayed = self._anchor_replayer(request)
            if not isinstance(replayed, ReplayedAnchor):
                raise V023CompositionAdapterError("replay callback returned wrong type")
            if replayed.handle.token in replay_handle_tokens:
                raise V023CompositionAdapterError(
                    "replay callback reused an anchor handle"
                )
            replay_handle_tokens.add(replayed.handle.token)
            compositions.append(
                compose_anchor_once(
                    declared=declared,
                    replayed=replayed,
                    fitted=fitted,
                    q3_evaluator=self._q3_evaluator,
                    physical_evaluator=self._physical_evaluator,
                    model_digestor=self._model_digestor,
                    native_selector=self._native_selector,
                )
            )
        arrays, denominators = _pack_composition_arrays(compositions)
        metadata = composition_array_metadata(arrays)
        npz_sha256 = _write_npz_once(arrays_path, arrays)
        _write_once_bytes(
            digest_path,
            f"{npz_sha256}  {arrays_path.name}\n".encode("ascii"),
        )
        comparisons = _comparison_receipt(
            np.asarray(arrays["physical_total_bits"]),
            np.asarray(arrays["physical_energy_j"]),
            np.asarray(arrays["physical_served"]),
        )
        unsigned: dict[str, object] = {
            "schema": V023_COMPOSITION_SCHEMA,
            "status": "PASS_COMPOSITION_EVIDENCE",
            "claim_ceiling": V023_CLAIM_CEILING,
            "contract_sha256": V023_CONTRACT_SHA256,
            "split": "TRAIN_DEVELOPMENT",
            "held_out_world": spec.held_out_world,
            "student_seed": spec.student_seed,
            "arm": spec.arm,
            "preflight_manifest_sha256": spec.preflight_manifest_sha256,
            "source_manifest_sha256": spec.source_manifest_sha256,
            "source_index_sha256": source.source_index_sha256,
            "source_field_root_sha256": source.field_root_sha256,
            "fit_receipt_sha256": fitted.fit_receipt_sha256,
            "fit_receipt_content_sha256": fitted.fit_receipt_content_sha256 or None,
            "fit_model_bytes_sha256": fitted.model_bytes_sha256,
            "fit_model_sha256": fitted.model_sha256,
            "fit_update_count": fitted.update_count,
            "fit_already_completed": True,
            "learner_update": False,
            "test_split_opened": False,
            "test_worlds": [],
            "episode_training": False,
            "scientific_decision_opened": False,
            "c3_decision": None,
            "inference": {
                "anchor_count": len(compositions),
                "q3_calls": sum(item.learned.q3_calls for item in compositions),
                "learned_argmax_calls": sum(item.learned.argmax_calls for item in compositions),
                "teacher_argmax_calls": sum(item.teacher_argmax_calls for item in compositions),
                "baseline_argmax_calls": 0,
                "physical_evaluator_calls": len(compositions) * 3,
                "q12_recomputed_from_policy": False,
                "teacher_entered_learned_input": False,
            },
            "arrays": {
                "npz_relative_path": arrays_path.name,
                "npz_sha256": npz_sha256,
                "npz_sha256_file": digest_path.name,
                "array_domain": V023_COMPOSITION_ARRAY_DOMAIN,
                "array_metadata": metadata,
                "array_count": len(arrays),
                "allow_pickle": False,
                "physical_role_order": ["ZERO_SURFACE_B", spec.arm, "TEACHER_ORACLE"],
                "pair_profile_order": list(PROFILE_ORDER),
                "pair_class_codes": dict(PAIR_CLASS_CODES),
                "padding": {
                    "physical_keys": -1,
                    "satellite_ids": -1,
                    "powers": 0.0,
                },
            },
            "denominators": denominators,
            "numeric_comparisons": comparisons,
            "no_rescue": {
                "second_learned_argmax": False,
                "retry": False,
                "fallback": False,
                "matching": False,
                "repair": False,
                "coordinator": False,
                "policy_rollout": False,
                "action_edit": False,
                "optimizer_update": False,
            },
        }
        index = dict(unsigned)
        index["receipt_sha256"] = canonical_sha256(unsigned)
        _write_once_bytes(index_path, _canonical_bytes(index) + b"\n")
        verified = verify_composition_sidecars(index_path)
        if verified["status"] != "PASS_COMPOSITION_SIDECARS":
            raise V023CompositionAdapterError("composition sidecar self-verification failed")
        return CompositionArtifacts(
            index_path=index_path,
            arrays_path=arrays_path,
            digest_path=digest_path,
            index=index,
        )


def _safe_relative_sidecar(root: Path, value: object, *, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise V023CompositionAdapterError(f"{label} path is unsafe")
    relative = Path(value)
    if relative.name != value or value in {".", ".."}:
        raise V023CompositionAdapterError(f"{label} path is unsafe")
    candidate = root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise V023CompositionAdapterError(f"{label} is missing or is a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise V023CompositionAdapterError(f"{label} escapes the artifact directory")
    return resolved


def verify_composition_sidecars(index_path: Path) -> dict[str, object]:
    """Independently reopen the sealed JSON/NPZ composition evidence."""

    source = Path(index_path)
    if source.is_symlink() or not source.is_file():
        raise V023CompositionAdapterError("composition index is missing or is a symlink")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023CompositionAdapterError("composition index is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise V023CompositionAdapterError("composition index is not canonical JSON")
    seal = _sha256(payload.get("receipt_sha256"), name="composition receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != seal:
        raise V023CompositionAdapterError("composition receipt seal disagrees")
    if (
        payload.get("schema") != V023_COMPOSITION_SCHEMA
        or payload.get("contract_sha256") != V023_CONTRACT_SHA256
        or payload.get("claim_ceiling") != V023_CLAIM_CEILING
        or payload.get("split") != "TRAIN_DEVELOPMENT"
    ):
        raise V023CompositionAdapterError("composition index authority drifted")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
        or payload.get("scientific_decision_opened") is not False
        or payload.get("c3_decision") is not None
    ):
        raise V023CompositionAdapterError("composition index crossed a closed boundary")
    receipt = payload.get("arrays")
    if not isinstance(receipt, Mapping) or receipt.get("allow_pickle") is not False:
        raise V023CompositionAdapterError("composition array receipt is malformed")
    root = source.parent.resolve()
    npz_path = _safe_relative_sidecar(
        root, receipt.get("npz_relative_path"), label="composition NPZ"
    )
    digest_path = _safe_relative_sidecar(
        root, receipt.get("npz_sha256_file"), label="composition digest sidecar"
    )
    expected_npz_sha = _sha256(
        receipt.get("npz_sha256"), name="composition NPZ sha256"
    )
    actual_npz_sha = _file_sha256(npz_path, label="composition NPZ")
    if actual_npz_sha != expected_npz_sha:
        raise V023CompositionAdapterError("composition NPZ byte hash disagrees")
    expected_digest = f"{actual_npz_sha}  {npz_path.name}\n".encode("ascii")
    if digest_path.read_bytes() != expected_digest:
        raise V023CompositionAdapterError("composition NPZ digest sidecar disagrees")
    metadata = receipt.get("array_metadata")
    if not isinstance(metadata, Mapping):
        raise V023CompositionAdapterError("composition array metadata is missing")
    try:
        with np.load(npz_path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError, KeyError) as error:
        raise V023CompositionAdapterError("composition NPZ cannot be safely loaded") from error
    if set(arrays) != set(metadata):
        raise V023CompositionAdapterError("composition NPZ members disagree with metadata")
    if composition_array_metadata(arrays) != metadata:
        raise V023CompositionAdapterError("composition array dtype/shape/digest disagrees")
    if receipt.get("array_count") != len(arrays):
        raise V023CompositionAdapterError("composition array count disagrees")
    return {
        "status": "PASS_COMPOSITION_SIDECARS",
        "scientific_claim": False,
        "held_out_world": payload.get("held_out_world"),
        "student_seed": payload.get("student_seed"),
        "arm": payload.get("arm"),
        "array_count": len(arrays),
    }


__all__ = [
    "V023CompositionAdapterError",
    "NativeSelectionReceipt",
    "native_masked_argmax",
    "array_sha256",
    "ImmutableAnchorHandle",
    "PAIR_CLASS_CODES",
    "PAIR_CLASS_NAMES",
    "PairSourceMechanics",
    "DeclaredPair",
    "DeclaredAnchor",
    "ReplayedAnchor",
    "AuthenticatedFitArtifact",
    "Q3InferenceInput",
    "LearnedSelection",
    "PairClassification",
    "classify_pair_actions",
    "select_learned_once",
    "action_vector_sha256",
    "PhysicalEvaluationRequest",
    "PhysicalEvaluation",
    "AnchorComposition",
    "compose_anchor_once",
    "AuthenticatedSourceArtifact",
    "CompositionShardSpec",
    "ReplayAnchorRequest",
    "CompositionArtifacts",
    "composition_array_metadata",
    "canonical_sha256",
    "authenticate_source_artifact",
    "authenticate_fit_artifact",
    "default_model_digestor",
    "default_q3_evaluator",
    "V023CompositionAdapter",
    "verify_composition_sidecars",
]
