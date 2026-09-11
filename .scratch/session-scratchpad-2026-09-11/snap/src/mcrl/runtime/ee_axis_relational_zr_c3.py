"""V0.18 relational-ZR C3 predecision seam.

The module deliberately stops at the information boundary.  It turns the
current candidate table, a detached ``Q1+Q2`` reference, and the two exact
current surfaces into an immutable action--victim representation.  It never
asks the environment to score an action and never consumes randomness.

The learner-facing representation has one row for every focal user and
native action, and one padded victim row for every user.  A later learner may
pool the victim rows with a shared scorer; this module does not own that
learner.  The small nominal helper at the end is a diagnostic reconstruction
of the same ZR algebra with unit fading and zero shadowing.  It is not a
deployment policy.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
from typing import Iterable, Mapping, Sequence

import numpy as np

from ..env.action_contract import NUM_ACTIONS, NO_OP_ACTION, SlotTable
from ..env.antenna import RX_GAIN_MAX_DBI, receive_gain_linear, transmit_gain_linear
from ..env.geometry import angle_between_deg, look_angles
from ..env.link_budget import (
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    link_power_factor,
    noise_power_w,
    shannon_rate_bps,
)
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError


RELATIONAL_ZR_C3_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-c3-v1"
RELATIONAL_ZR_C3_SCHEMA_VERSION = 1
RELATIONAL_ZR_ACTION_CONTEXT_DIM = 7
RELATIONAL_ZR_VICTIM_TOKEN_DIM = 6
ACTION_CONTEXT_DIM = RELATIONAL_ZR_ACTION_CONTEXT_DIM
VICTIM_TOKEN_DIM = RELATIONAL_ZR_VICTIM_TOKEN_DIM


class RelationalZRC3Error(MCRLContractError):
    """A V0.18 relational C3 input or immutable observation is invalid."""


RelationalZRC3StateError = RelationalZRC3Error


def _schema_payload() -> dict[str, object]:
    return {
        "schema": RELATIONAL_ZR_C3_SCHEMA,
        "schema_version": RELATIONAL_ZR_C3_SCHEMA_VERSION,
        "action_dim": NUM_ACTIONS,
        "action_context_dim": RELATIONAL_ZR_ACTION_CONTEXT_DIM,
        "victim_token_dim": RELATIONAL_ZR_VICTIM_TOKEN_DIM,
        "layout": {
            "action_context": "(U,A,7)-float64",
            "victim_tokens": "(U,A,U,6)-float64",
            "action_mask": "(U,A)-bool-native-safe-mask",
            "victim_mask": "(U,A,U)-bool-nonfocal-reference-open-cochannel",
            "positive_credit_compatible": "(U,A)-bool-exact-predecision-support",
            "reference_actions": "(U,)-int64-detached-context",
        },
        "action_context": [
            "service_headroom_reference",
            "service_headroom_candidate",
            "same_physical_beam_as_reference",
            "nonfocal_reference_load_at_reference_beam_div_u",
            "nonfocal_reference_load_at_candidate_beam_div_u",
            "nonfocal_reference_max_power_at_reference_beam_minus_reference_power_div_pmax",
            "nonfocal_reference_max_power_at_candidate_beam_minus_candidate_power_div_pmax",
        ],
        "victim_tokens": [
            "log1p_observed_candidate_sinr_at_reference_action",
            "reference_beam_load_div_u",
            "candidate_beam_load_change_div_u",
            "log1p_nominal_reference_wanted_signal_div_noise",
            "log1p_nominal_reference_interference_div_noise",
            "asinh_nominal_interference_change_div_noise",
        ],
        "nominal_convention": "unit-rician-fading-zero-shadowing",
        "identity": "physical-(norad_id,cell_id),-never-flat-action-equality",
        "reference_semantics": "detached-nonexecuted-q1-plus-q2-context-pass",
        "forbidden": [
            "realised-branch-outcome",
            "future-state",
            "teacher-target-or-label",
            "randomness",
        ],
    }


RELATIONAL_ZR_C3_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    .encode("ascii")
).hexdigest()


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalZRC3Error("array cannot be materialised") from error
    result.setflags(write=False)
    return result


def _digest_array(digest: "hashlib._Hash", name: str, value: np.ndarray) -> None:
    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(b"\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _content_digest(
    action_context: np.ndarray,
    victim_tokens: np.ndarray,
    action_mask: np.ndarray,
    victim_mask: np.ndarray,
    compatible: np.ndarray,
    reference_actions: np.ndarray,
    schema_version: int,
) -> str:
    digest = hashlib.sha256()
    digest.update(RELATIONAL_ZR_C3_SCHEMA.encode("ascii"))
    digest.update(struct.pack(">I", int(schema_version)))
    for name, value in (
        ("action_context", action_context),
        ("victim_tokens", victim_tokens),
        ("action_mask", action_mask),
        ("victim_mask", victim_mask),
        ("positive_credit_compatible", compatible),
        ("reference_actions", reference_actions),
    ):
        _digest_array(digest, name, value)
    return digest.hexdigest()


@dataclass(frozen=True)
class RelationalZRC3Observation:
    """Immutable V0.18 relational observation and its common native mask."""

    action_context: np.ndarray
    victim_tokens: np.ndarray
    action_mask: np.ndarray
    victim_mask: np.ndarray
    positive_credit_compatible: np.ndarray
    reference_actions: np.ndarray
    schema_version: int = RELATIONAL_ZR_C3_SCHEMA_VERSION
    content_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "action_context",
            _readonly(self.action_context, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "victim_tokens",
            _readonly(self.victim_tokens, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "action_mask",
            _readonly(self.action_mask, dtype=np.bool_),
        )
        object.__setattr__(
            self,
            "victim_mask",
            _readonly(self.victim_mask, dtype=np.bool_),
        )
        object.__setattr__(
            self,
            "positive_credit_compatible",
            _readonly(self.positive_credit_compatible, dtype=np.bool_),
        )
        object.__setattr__(
            self,
            "reference_actions",
            _readonly(self.reference_actions, dtype=np.int64),
        )
        if self.content_digest == "":
            object.__setattr__(
                self,
                "content_digest",
                _content_digest(
                    self.action_context,
                    self.victim_tokens,
                    self.action_mask,
                    self.victim_mask,
                    self.positive_credit_compatible,
                    self.reference_actions,
                    int(self.schema_version),
                ),
            )
        self.verify()

    @property
    def schema(self) -> str:
        """Canonical schema name (kept as a property to avoid duplicate state)."""

        return RELATIONAL_ZR_C3_SCHEMA

    @property
    def schema_sha256(self) -> str:
        return RELATIONAL_ZR_C3_SCHEMA_SHA256

    @property
    def state_sha256(self) -> str:
        """Compatibility alias used by older state receipts."""

        return self.content_digest

    @property
    def action_masks(self) -> np.ndarray:
        """Compatibility alias for the native safe mask."""

        return self.action_mask

    def verify(self) -> str:
        if type(self.schema_version) is not int or self.schema_version != RELATIONAL_ZR_C3_SCHEMA_VERSION:
            raise RelationalZRC3Error("unsupported relational C3 schema version")
        contexts = np.asarray(self.action_context)
        tokens = np.asarray(self.victim_tokens)
        actions = np.asarray(self.action_mask)
        victims = np.asarray(self.victim_mask)
        compatible = np.asarray(self.positive_credit_compatible)
        references = np.asarray(self.reference_actions)
        if contexts.ndim != 3 or contexts.shape[1:] != (
            NUM_ACTIONS,
            RELATIONAL_ZR_ACTION_CONTEXT_DIM,
        ):
            raise RelationalZRC3Error(
                f"action_context must have shape (U,{NUM_ACTIONS},7)"
            )
        users = contexts.shape[0]
        if tokens.shape != (
            users,
            NUM_ACTIONS,
            users,
            RELATIONAL_ZR_VICTIM_TOKEN_DIM,
        ):
            raise RelationalZRC3Error(
                f"victim_tokens must have shape (U,{NUM_ACTIONS},U,6)"
            )
        if actions.dtype != np.bool_ or actions.shape != (users, NUM_ACTIONS):
            raise RelationalZRC3Error("action_mask must be Boolean shape (U,28)")
        if victims.dtype != np.bool_ or victims.shape != (users, NUM_ACTIONS, users):
            raise RelationalZRC3Error("victim_mask must be Boolean shape (U,28,U)")
        if compatible.dtype != np.bool_ or compatible.shape != (users, NUM_ACTIONS):
            raise RelationalZRC3Error(
                "positive_credit_compatible must be Boolean shape (U,28)"
            )
        if (
            references.dtype.kind not in "iu"
            or references.dtype.kind == "b"
            or references.shape != (users,)
        ):
            raise RelationalZRC3Error("reference_actions must be integer shape (U,)")
        if not np.all(np.isfinite(contexts)) or not np.all(np.isfinite(tokens)):
            raise RelationalZRC3Error("relational arrays must be finite")
        if np.any(contexts[~actions] != 0.0):
            raise RelationalZRC3Error("illegal action context rows must be zero")
        if np.any(tokens[~victims] != 0.0):
            raise RelationalZRC3Error("masked victim tokens must be zero")
        if np.any(victims[np.arange(users), :, np.arange(users)]):
            raise RelationalZRC3Error("a focal user cannot be its own victim")
        if np.any(compatible & ~actions):
            raise RelationalZRC3Error("compatibility cannot widen the native mask")
        for uid, raw in enumerate(references.tolist()):
            reference = int(raw)
            if reference == NO_OP_ACTION:
                if bool(np.any(actions[uid])):
                    raise RelationalZRC3Error(
                        "reference_actions may be -1 only for an all-empty native row"
                    )
            elif not 0 <= reference < NUM_ACTIONS or not bool(actions[uid, reference]):
                raise RelationalZRC3Error("reference action is not legal")
        if (
            actions.flags.writeable
            or victims.flags.writeable
            or compatible.flags.writeable
            or references.flags.writeable
            or contexts.flags.writeable
            or tokens.flags.writeable
        ):
            raise RelationalZRC3Error("relational observation arrays must be immutable")
        expected = _content_digest(
            contexts,
            tokens,
            actions,
            victims,
            compatible,
            references,
            self.schema_version,
        )
        if self.content_digest != expected:
            raise RelationalZRC3Error("relational observation digest disagrees with arrays")
        return expected


def _as_bool_matrix(value: object, *, shape: tuple[int, int], field: str) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise RelationalZRC3Error(f"{field} is malformed") from error
    if array.dtype != np.bool_ or array.shape != shape:
        raise RelationalZRC3Error(f"{field} must be Boolean shape {shape}")
    return np.array(array, dtype=np.bool_, copy=True, order="C")


def _as_power_matrix(value: object, *, shape: tuple[int, int]) -> np.ndarray:
    try:
        raw = np.asarray(value)
        if raw.dtype.kind == "b":
            raise ValueError("Boolean power surface")
        array = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalZRC3Error("required_power_surface is malformed") from error
    if array.shape != shape or not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise RelationalZRC3Error(
            f"required_power_surface must be finite nonnegative shape {shape}"
        )
    return np.array(array, dtype=np.float64, copy=True, order="C")


def _as_reference_vector(value: object, *, users: int) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise RelationalZRC3Error("reference_actions is malformed") from error
    if raw.shape != (users,) or raw.dtype.kind not in "iu" or raw.dtype.kind == "b":
        raise RelationalZRC3Error(f"reference_actions must be integer shape ({users},)")
    values = raw.tolist()
    # Check before narrowing unsigned values to int64.
    for value_item in values:
        number = int(value_item)
        if number < -1 or number >= NUM_ACTIONS:
            raise RelationalZRC3Error("reference action is outside the native range")
    return np.asarray(values, dtype=np.int64)


def _anchor(
    environment: StepEnvironment,
    observation: StepObservation,
) -> tuple[tuple[SlotTable, ...], np.ndarray]:
    if not isinstance(environment, StepEnvironment) or not isinstance(observation, StepObservation):
        raise RelationalZRC3Error("environment and observation must be canonical step objects")
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise RelationalZRC3Error("observation is not the current predecision anchor")
    users = int(observation.num_users)
    if users < 1 or int(getattr(environment, "num_users", -1)) != users:
        raise RelationalZRC3Error("environment and observation user counts disagree")
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    native = np.asarray(observation.masks)
    if len(tables) != users or any(not isinstance(table, SlotTable) for table in tables):
        raise RelationalZRC3Error("candidate slot tables are malformed")
    if native.dtype != np.bool_ or native.shape != (users, NUM_ACTIONS):
        raise RelationalZRC3Error("observation masks must be Boolean shape (U,28)")
    native_copy = np.array(native, dtype=np.bool_, copy=True, order="C")
    for uid, table in enumerate(tables):
        if not np.array_equal(native_copy[uid], np.asarray(table.mask, dtype=np.bool_)):
            raise RelationalZRC3Error("observation mask disagrees with slot table")
        norads = np.asarray(table.norad_ids)
        cells = np.asarray(table.cell_ids)
        if (
            norads.shape != (NUM_ACTIONS,)
            or cells.shape != (NUM_ACTIONS,)
            or norads.dtype.kind not in "iu"
            or cells.dtype.kind not in "iu"
            or np.any(native_copy[uid] & ((norads < 0) | (cells < 0)))
        ):
            raise RelationalZRC3Error("native actions need physical identities")
    return tables, native_copy


def _candidate_identity_arrays(
    tables: tuple[SlotTable, ...], native: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    users = len(tables)
    norads = np.full((users, NUM_ACTIONS), -1, dtype=np.int64)
    cells = np.full((users, NUM_ACTIONS), -1, dtype=np.int64)
    for uid, table in enumerate(tables):
        legal = native[uid]
        norads[uid, legal] = np.asarray(table.norad_ids, dtype=np.int64)[legal]
        cells[uid, legal] = np.asarray(table.cell_ids, dtype=np.int64)[legal]
    return norads, cells


def _physical_keys(
    norads: np.ndarray, cells: np.ndarray, mask: np.ndarray
) -> list[list[tuple[int, int] | None]]:
    users = norads.shape[0]
    return [
        [
            (int(norads[uid, action]), int(cells[uid, action]))
            if bool(mask[uid, action])
            else None
            for action in range(NUM_ACTIONS)
        ]
        for uid in range(users)
    ]


def _pmax_from(environment: StepEnvironment, pmax_w: float | None) -> float:
    value = pmax_w
    if value is None:
        physics = getattr(environment, "physics", None)
        value = getattr(physics, "beam_power_max_w", BEAM_POWER_MAX_W)
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalZRC3Error("pmax_w must be finite and positive") from error
    if not math.isfinite(result) or result <= 0.0:
        raise RelationalZRC3Error("pmax_w must be finite and positive")
    return result


def _validate_context_inputs(
    tables: tuple[SlotTable, ...],
    native: np.ndarray,
    references: object,
    required_power_surface: object,
    opening_feasibility_surface: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    users = len(tables)
    refs = _as_reference_vector(references, users=users)
    for uid, action_raw in enumerate(refs.tolist()):
        action = int(action_raw)
        if action == NO_OP_ACTION:
            if bool(np.any(native[uid])):
                raise RelationalZRC3Error(
                    "reference_actions may be -1 only for an all-empty native row"
                )
        elif not bool(native[uid, action]):
            raise RelationalZRC3Error("reference action is not legal")
    power = _as_power_matrix(
        required_power_surface,
        shape=(users, NUM_ACTIONS),
    )
    opening = _as_bool_matrix(
        opening_feasibility_surface,
        shape=(users, NUM_ACTIONS),
        field="opening_feasibility_surface",
    )
    if np.any(opening & ~native):
        raise RelationalZRC3Error("opening feasibility must be a subset of the native mask")
    norads, cells = _candidate_identity_arrays(tables, native)
    return refs, power, opening, np.stack((norads, cells), axis=-1)


def _float64_bytes(values: Iterable[float]) -> bytes:
    """Canonical ordered bytes for the exact compatibility comparison."""

    packed = bytearray()
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise RelationalZRC3Error("compatibility power must be finite")
        packed.extend(struct.pack(">d", number))
    return bytes(packed)


def compute_positive_credit_compatible(
    *,
    reference_actions: object,
    action_mask: object,
    opening_feasibility_surface: object,
    required_power_surface: object,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
) -> np.ndarray:
    """Reconstruct exact ZR positive-credit support from predecision surfaces.

    This is a formula/context gate, not an action mask.  Its all-unserved
    branch intentionally returns true even when the physical keys differ:
    no active beam or network-power component changes when both focal links
    are unserved.
    """

    try:
        legal = np.asarray(action_mask)
        norads = np.asarray(candidate_norad_ids)
        cells = np.asarray(candidate_cell_ids)
    except (TypeError, ValueError) as error:
        raise RelationalZRC3Error("compatibility surfaces are malformed") from error
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != NUM_ACTIONS:
        raise RelationalZRC3Error("action_mask must be Boolean shape (U,28)")
    users = legal.shape[0]
    if (
        norads.shape != legal.shape
        or cells.shape != legal.shape
        or norads.dtype.kind not in "iu"
        or cells.dtype.kind not in "iu"
    ):
        raise RelationalZRC3Error("candidate identity surfaces have the wrong shape")
    if np.any(legal & ((norads < 0) | (cells < 0))):
        raise RelationalZRC3Error("legal actions need nonnegative physical identities")
    refs = _as_reference_vector(reference_actions, users=users)
    opening = _as_bool_matrix(
        opening_feasibility_surface,
        shape=legal.shape,
        field="opening_feasibility_surface",
    )
    if np.any(opening & ~legal):
        raise RelationalZRC3Error("opening feasibility must be a subset of the native mask")
    power = _as_power_matrix(required_power_surface, shape=legal.shape)
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action == NO_OP_ACTION:
            if bool(np.any(legal[uid])):
                raise RelationalZRC3Error("-1 reference requires an all-empty native row")
        elif not bool(legal[uid, action]):
            raise RelationalZRC3Error("reference action is not legal")

    keys: list[list[tuple[int, int] | None]] = [
        [
            (int(norads[uid, action]), int(cells[uid, action]))
            if bool(legal[uid, action])
            else None
            for action in range(NUM_ACTIONS)
        ]
        for uid in range(users)
    ]
    reference_opening = np.zeros(users, dtype=np.bool_)
    reference_keys: list[tuple[int, int] | None] = [None] * users
    reference_power = np.zeros(users, dtype=np.float64)
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action >= 0:
            reference_keys[uid] = keys[uid][action]
            reference_opening[uid] = bool(opening[uid, action])
            reference_power[uid] = float(power[uid, action])

    result = np.zeros_like(legal, dtype=np.bool_)
    for uid in range(users):
        reference_action = int(refs[uid])
        e0 = reference_action >= 0 and bool(reference_opening[uid])
        b0 = reference_keys[uid]
        # M[-u,b] is a focal-user-relative surface.  In particular, the
        # focal reference must not make its own beam appear in the peer set;
        # doing so changes the beam-key set before the focal branch is added
        # explicitly below and breaks the exact compatibility gate.
        peer_max: dict[tuple[int, int], float] = {}
        for peer in range(users):
            if peer == uid or not bool(reference_opening[peer]) or reference_keys[peer] is None:
                continue
            key = reference_keys[peer]
            assert key is not None
            peer_max[key] = max(peer_max.get(key, 0.0), reference_power[peer])
        positive_keys = {key for key, value in peer_max.items() if value > 0.0}
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            ea = bool(opening[uid, action])
            ba = keys[uid][action]
            if e0 != ea:
                continue
            if not e0:
                result[uid, action] = True
                continue
            assert b0 is not None and ba is not None
            b0_set = positive_keys | {b0}
            ba_set = positive_keys | {ba}
            ordered_0 = sorted(b0_set)
            ordered_a = sorted(ba_set)
            if ordered_0 != ordered_a:
                continue
            p0 = [max(peer_max.get(key, 0.0), reference_power[uid] if key == b0 else 0.0) for key in ordered_0]
            pa = [max(peer_max.get(key, 0.0), float(power[uid, action]) if key == ba else 0.0) for key in ordered_a]
            result[uid, action] = _float64_bytes(p0) == _float64_bytes(pa)
    result &= legal
    result.setflags(write=False)
    return result


# Short public spelling used by gate runners and tests.
positive_credit_compatible = compute_positive_credit_compatible


def _cochannel(
    first: tuple[int, int],
    second: tuple[int, int],
    colors: Mapping[int, int],
) -> bool:
    satellite, cell = first
    other_satellite, other_cell = second
    if int(colors[cell]) != int(colors[other_cell]):
        return False
    return (satellite == other_satellite and cell != other_cell) or satellite != other_satellite


def compute_victim_mask(
    *,
    reference_actions: object,
    action_mask: object,
    opening_feasibility_surface: object,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
    cell_colors: object,
) -> np.ndarray:
    """Return the exact non-focal, reference-open, changed-beam victim mask."""

    legal = np.asarray(action_mask)
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != NUM_ACTIONS:
        raise RelationalZRC3Error("action_mask must be Boolean shape (U,28)")
    users = legal.shape[0]
    norads = np.asarray(candidate_norad_ids)
    cells = np.asarray(candidate_cell_ids)
    if norads.shape != legal.shape or cells.shape != legal.shape:
        raise RelationalZRC3Error("candidate identity surfaces have the wrong shape")
    if norads.dtype.kind not in "iu" or cells.dtype.kind not in "iu":
        raise RelationalZRC3Error("candidate identity surfaces must be integer")
    if np.any(legal & ((norads < 0) | (cells < 0))):
        raise RelationalZRC3Error("legal actions need nonnegative physical identities")
    refs = _as_reference_vector(reference_actions, users=users)
    opening = _as_bool_matrix(
        opening_feasibility_surface,
        shape=legal.shape,
        field="opening_feasibility_surface",
    )
    if np.any(opening & ~legal):
        raise RelationalZRC3Error("opening feasibility must be a subset of the native mask")
    colors_array = np.asarray(cell_colors)
    if colors_array.ndim != 1 or colors_array.dtype.kind not in "iu":
        raise RelationalZRC3Error("cell_colors must be a one-dimensional integer map")
    keys = _physical_keys(norads, cells, legal)
    reference_opening = np.zeros(users, dtype=np.bool_)
    reference_keys: list[tuple[int, int] | None] = [None] * users
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action == NO_OP_ACTION:
            if bool(np.any(legal[uid])):
                raise RelationalZRC3Error("-1 reference requires an all-empty native row")
            continue
        if not bool(legal[uid, action]):
            raise RelationalZRC3Error("reference action is not legal")
        reference_keys[uid] = keys[uid][action]
        reference_opening[uid] = bool(opening[uid, action])
    colors: dict[int, int] = {}
    for row in keys:
        for key in row:
            if key is None:
                continue
            _, cell = key
            if not 0 <= cell < colors_array.size:
                raise RelationalZRC3Error("a physical cell is outside cell_colors")
            colors[cell] = int(colors_array[cell])

    result = np.zeros((users, NUM_ACTIONS, users), dtype=np.bool_)
    for uid in range(users):
        reference_action = int(refs[uid])
        origin = (
            reference_keys[uid]
            if reference_action >= 0 and bool(reference_opening[uid])
            else None
        )
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            candidate_key = keys[uid][action]
            changed: set[tuple[int, int]] = set()
            if origin is not None:
                changed.add(origin)
            if bool(opening[uid, action]) and candidate_key is not None:
                changed.add(candidate_key)
            if not changed:
                continue
            for victim in range(users):
                if victim == uid or not bool(reference_opening[victim]):
                    continue
                victim_key = reference_keys[victim]
                if victim_key is None:
                    continue
                if any(
                    victim_key == changed_key
                    or _cochannel(victim_key, changed_key, colors)
                    for changed_key in changed
                ):
                    result[uid, action, victim] = True
    # Clear only the focal diagonal.  Indexing the last axis with an array
    # while leaving the first axis as ``:`` would clear every victim for each
    # focal row, silently erasing the relational signal.
    result[np.arange(users), :, np.arange(users)] = False
    result &= legal[:, :, None]
    result.setflags(write=False)
    return result


victim_mask_surface = compute_victim_mask


def _grid_data(
    environment: StepEnvironment,
    observation: StepObservation,
    norads: np.ndarray,
    cells: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray]]:
    candidates = observation.candidates
    driver = getattr(environment, "driver", None)
    grid = getattr(driver, "grid", None)
    colors_value = getattr(grid, "colors", None)
    if colors_value is None:
        colors_value = getattr(candidates, "cell_colors", None)
    if colors_value is None:
        raise RelationalZRC3Error("nominal C3 needs the canonical cell color map")
    colors = np.asarray(colors_value)
    if colors.ndim != 1 or colors.dtype.kind not in "iu":
        raise RelationalZRC3Error("cell color map is malformed")
    centres_value = getattr(grid, "centers_ecef_km", None)
    if centres_value is None:
        centres_value = getattr(candidates, "cell_centres_ecef_km", None)
    centres = np.asarray(centres_value, dtype=np.float64) if centres_value is not None else np.empty((0, 3))
    if centres.ndim != 2 or centres.shape[1] != 3 or not np.all(np.isfinite(centres)):
        raise RelationalZRC3Error("nominal C3 needs finite cell centre ECEF positions")
    used_cells = cells[cells >= 0]
    if used_cells.size and int(used_cells.max()) >= centres.shape[0]:
        raise RelationalZRC3Error("candidate cell exceeds cell centre table")
    if used_cells.size and int(used_cells.max()) >= colors.size:
        raise RelationalZRC3Error("candidate cell exceeds cell color table")

    positions: dict[int, np.ndarray] = {}
    window_ids = getattr(candidates, "window_norad_ids", None)
    window_ecef = getattr(candidates, "window_satellite_ecef_km", None)
    if window_ids is not None and window_ecef is not None:
        ids = np.asarray(window_ids)
        ecef = np.asarray(window_ecef, dtype=np.float64)
        if ids.shape != ecef.shape[:2] or ecef.ndim != 3 or ecef.shape[2] != 3:
            raise RelationalZRC3Error("candidate satellite window positions are malformed")
        for uid in range(ids.shape[0]):
            for slot in range(ids.shape[1]):
                norad = int(ids[uid, slot])
                if norad >= 0:
                    position = ecef[uid, slot]
                    if not np.all(np.isfinite(position)):
                        raise RelationalZRC3Error("satellite ECEF positions must be finite")
                    positions.setdefault(norad, np.array(position, dtype=np.float64, copy=True))
    needed = sorted({int(value) for value in norads[norads >= 0].tolist()})
    missing = [value for value in needed if value not in positions]
    if missing:
        position_method = getattr(driver, "satellite_ecef_at", None)
        if callable(position_method):
            current = position_method(0)
            if not isinstance(current, Mapping):
                raise RelationalZRC3Error("satellite_ecef_at did not return an identity map")
            for norad in missing:
                if norad in current:
                    position = np.asarray(current[norad], dtype=np.float64)
                    if position.shape != (3,) or not np.all(np.isfinite(position)):
                        raise RelationalZRC3Error("current satellite ECEF position is malformed")
                    positions[norad] = np.array(position, copy=True)
        missing = [value for value in needed if value not in positions]
    if missing:
        raise RelationalZRC3Error(f"missing current position for satellites {missing}")
    return centres, colors.astype(np.int64, copy=False), positions


def _user_positions(environment: StepEnvironment, users: int) -> np.ndarray:
    driver = getattr(environment, "driver", None)
    method = getattr(driver, "user_ecef_km", None)
    value = method() if callable(method) else getattr(environment, "user_ecef_km", None)
    if value is None:
        raise RelationalZRC3Error("nominal C3 needs current user ECEF positions")
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (users, 3) or not np.all(np.isfinite(result)):
        raise RelationalZRC3Error("current user ECEF positions are malformed")
    return np.array(result, copy=True, order="C")


def _candidate_geometry(
    environment: StepEnvironment,
    observation: StepObservation,
    norads: np.ndarray,
    cells: np.ndarray,
    centres: np.ndarray,
    positions: Mapping[int, np.ndarray],
    users_ecef: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    users = norads.shape[0]
    candidates = observation.candidates
    slots = NUM_ACTIONS // 7
    theta = np.full((users, NUM_ACTIONS), np.nan, dtype=np.float64)
    slant = np.full_like(theta, np.nan)
    elevation = np.full_like(theta, np.nan)
    supplied_theta = getattr(candidates, "off_axis_deg", None)
    supplied_slant = getattr(candidates, "slant_range_km", None)
    supplied_elevation = getattr(candidates, "elevation_deg", None)
    if supplied_theta is not None:
        value = np.asarray(supplied_theta, dtype=np.float64)
        if value.shape == (users, slots, 7):
            theta = value.reshape(users, NUM_ACTIONS).copy()
    if supplied_slant is not None:
        value = np.asarray(supplied_slant, dtype=np.float64)
        if value.shape == (users, slots):
            slant = np.repeat(value, 7, axis=1)
    if supplied_elevation is not None:
        value = np.asarray(supplied_elevation, dtype=np.float64)
        if value.shape == (users, slots):
            elevation = np.repeat(value, 7, axis=1)

    for uid in range(users):
        for action in np.flatnonzero(norads[uid] >= 0).tolist():
            norad = int(norads[uid, action])
            cell = int(cells[uid, action])
            if not np.isfinite(theta[uid, action]) or not np.isfinite(slant[uid, action]) or not np.isfinite(elevation[uid, action]):
                satellite = positions[norad]
                centre = centres[cell]
                theta[uid, action] = float(
                    angle_between_deg(satellite, centre, users_ecef[uid])
                )
                range_value, elevation_value, _ = look_angles(
                    satellite, users_ecef[uid]
                )
                slant[uid, action] = float(range_value)
                elevation[uid, action] = float(elevation_value)
            if slant[uid, action] <= 0.0 or not np.isfinite(theta[uid, action]):
                raise RelationalZRC3Error("legal candidate geometry is invalid")
    return theta, slant, elevation


def _nominal_signal_surface(
    *,
    theta: np.ndarray,
    slant: np.ndarray,
    elevation: np.ndarray,
    required_power: np.ndarray,
    legal: np.ndarray,
) -> np.ndarray:
    users = theta.shape[0]
    signal = np.zeros_like(required_power, dtype=np.float64)
    receive_max = 10.0 ** (float(RX_GAIN_MAX_DBI) / 10.0)
    for uid in range(users):
        valid = legal[uid] & np.isfinite(theta[uid]) & np.isfinite(slant[uid]) & np.isfinite(elevation[uid])
        if not np.any(valid):
            continue
        gain = transmit_gain_linear(theta[uid, valid])
        path = link_power_factor(
            slant[uid, valid],
            elevation[uid, valid],
            np.full(int(np.count_nonzero(valid)), receive_max, dtype=np.float64),
            shadow_fading_db=0.0,
        )
        signal[uid, valid] = required_power[uid, valid] * gain * path
    if not np.all(np.isfinite(signal)):
        raise RelationalZRC3Error("nominal wanted signal is non-finite")
    return signal


def _branch_actions(
    reference_actions: np.ndarray,
    *,
    focal_user: int | None = None,
    focal_action: int | None = None,
) -> np.ndarray:
    result = np.array(reference_actions, dtype=np.int64, copy=True)
    if focal_user is not None:
        assert focal_action is not None
        result[int(focal_user)] = int(focal_action)
    return result


def _branch_served(
    actions: np.ndarray,
    opening: np.ndarray,
    legal: np.ndarray,
) -> np.ndarray:
    users = actions.size
    served = np.zeros(users, dtype=np.bool_)
    for uid, raw in enumerate(actions.tolist()):
        action = int(raw)
        if action >= 0:
            if not bool(legal[uid, action]):
                raise RelationalZRC3Error("branch action is outside the native mask")
            served[uid] = bool(opening[uid, action])
    return served


def _branch_keys(
    actions: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
) -> list[tuple[int, int] | None]:
    result: list[tuple[int, int] | None] = []
    for uid, raw in enumerate(actions.tolist()):
        action = int(raw)
        result.append(
            None
            if action == NO_OP_ACTION
            else (int(norads[uid, action]), int(cells[uid, action]))
            if bool(legal[uid, action])
            else None
        )
    return result


def _nominal_interference(
    *,
    actions: np.ndarray,
    served: np.ndarray,
    required_power: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
    colours: np.ndarray,
    centres: np.ndarray,
    positions: Mapping[int, np.ndarray],
    users_ecef: np.ndarray,
) -> np.ndarray:
    users = actions.size
    keys = _branch_keys(actions, norads, cells, legal)
    beam_power: dict[tuple[int, int], float] = {}
    for uid, key in enumerate(keys):
        if bool(served[uid]) and key is not None:
            beam_power[key] = max(beam_power.get(key, 0.0), float(required_power[uid, int(actions[uid])]))
    result = np.zeros(users, dtype=np.float64)
    receive_max = 10.0 ** (float(RX_GAIN_MAX_DBI) / 10.0)
    for victim in range(users):
        if not bool(served[victim]) or keys[victim] is None:
            continue
        victim_key = keys[victim]
        assert victim_key is not None
        victim_satellite, victim_cell = victim_key
        victim_satellite_position = positions[victim_satellite]
        victim_colour = int(colours[victim_cell])
        for beam_key, beam_power_value in beam_power.items():
            beam_satellite, beam_cell = beam_key
            beam_colour = int(colours[beam_cell])
            if beam_colour != victim_colour:
                continue
            if not (
                (beam_satellite == victim_satellite and beam_cell != victim_cell)
                or beam_satellite != victim_satellite
            ):
                continue
            beam_satellite_position = positions[beam_satellite]
            transmit = float(
                transmit_gain_linear(
                    angle_between_deg(
                        beam_satellite_position,
                        centres[beam_cell],
                        users_ecef[victim],
                    )
                )
            )
            range_value, elevation_value, _ = look_angles(
                beam_satellite_position, users_ecef[victim]
            )
            path = float(
                link_power_factor(
                    np.asarray(range_value),
                    np.asarray(elevation_value),
                    np.asarray(1.0),
                    shadow_fading_db=0.0,
                )
            )
            if beam_satellite == victim_satellite:
                receive = receive_max
            else:
                separation = angle_between_deg(
                    users_ecef[victim],
                    victim_satellite_position,
                    beam_satellite_position,
                )
                receive = float(receive_gain_linear(separation))
            result[victim] += beam_power_value * transmit * path * receive
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise RelationalZRC3Error("nominal interference is non-finite")
    return result


def _noise_from(environment: StepEnvironment) -> float:
    physics = getattr(environment, "physics", None)
    value = getattr(physics, "noise_power_w", None)
    if callable(value):
        value = value()
    if value is None:
        value = noise_power_w()
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise RelationalZRC3Error("nominal noise power must be finite and positive")
    return result


def _bandwidth_from(environment: StepEnvironment) -> float:
    value = getattr(getattr(environment, "physics", None), "beam_bandwidth_hz", BEAM_BANDWIDTH_HZ)
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise RelationalZRC3Error("nominal beam bandwidth must be finite and positive")
    return result


def _nominal_rates(
    *,
    environment: StepEnvironment,
    actions: np.ndarray,
    served: np.ndarray,
    required_power: np.ndarray,
    signal_surface: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
    colours: np.ndarray,
    centres: np.ndarray,
    positions: Mapping[int, np.ndarray],
    users_ecef: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    users = actions.size
    interference = _nominal_interference(
        actions=actions,
        served=served,
        required_power=required_power,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )
    keys = _branch_keys(actions, norads, cells, legal)
    loads: dict[tuple[int, int], int] = {}
    for uid, key in enumerate(keys):
        if bool(served[uid]) and key is not None:
            loads[key] = loads.get(key, 0) + 1
    sinr = np.zeros(users, dtype=np.float64)
    for uid, key in enumerate(keys):
        if bool(served[uid]) and key is not None:
            action = int(actions[uid])
            sinr[uid] = float(signal_surface[uid, action]) / (_noise_from(environment) + interference[uid])
    load_values = np.asarray(
        [float(loads.get(key, 0)) if key is not None else 0.0 for key in keys],
        dtype=np.float64,
    )
    rates = shannon_rate_bps(
        sinr,
        beam_load=load_values,
        bandwidth_hz=_bandwidth_from(environment),
    )
    rates = np.where(served, rates, 0.0)
    return rates, interference


@dataclass(frozen=True)
class _NominalReferenceCache:
    """Anchor-constant quantities for one-user nominal branch updates.

    Only the focal user's origin and candidate beams can change between a
    reference branch and a unilateral candidate branch.  Reconstructing the
    whole beam map and every beam-to-victim geometry for all ``U*A`` branches
    is therefore unnecessary.  This cache keeps the exact reference result
    and the fixed physical coupling of every potentially active beam.
    """

    reference_served: np.ndarray
    reference_keys: tuple[tuple[int, int] | None, ...]
    reference_interference: np.ndarray
    reference_rates: np.ndarray
    reference_load_by_key: Mapping[tuple[int, int], int]
    reference_power_by_key: Mapping[tuple[int, int], float]
    peer_power_by_focal: tuple[Mapping[tuple[int, int], float], ...]
    coupling_by_key: Mapping[tuple[int, int], np.ndarray]
    reference_signal: np.ndarray
    noise_w: float
    bandwidth_hz: float


def _beam_to_reference_victim_coupling(
    *,
    beam_key: tuple[int, int],
    reference_served: np.ndarray,
    reference_keys: Sequence[tuple[int, int] | None],
    colours: np.ndarray,
    centres: np.ndarray,
    positions: Mapping[int, np.ndarray],
    users_ecef: np.ndarray,
) -> np.ndarray:
    """Return fixed received interference watts per radiated beam watt."""

    users = len(reference_keys)
    result = np.zeros(users, dtype=np.float64)
    beam_satellite, beam_cell = beam_key
    beam_colour = int(colours[beam_cell])
    beam_satellite_position = positions[beam_satellite]
    receive_max = 10.0 ** (float(RX_GAIN_MAX_DBI) / 10.0)
    for victim in range(users):
        victim_key = reference_keys[victim]
        if not bool(reference_served[victim]) or victim_key is None:
            continue
        victim_satellite, victim_cell = victim_key
        if int(colours[victim_cell]) != beam_colour:
            continue
        if not (
            (beam_satellite == victim_satellite and beam_cell != victim_cell)
            or beam_satellite != victim_satellite
        ):
            continue
        transmit = float(
            transmit_gain_linear(
                angle_between_deg(
                    beam_satellite_position,
                    centres[beam_cell],
                    users_ecef[victim],
                )
            )
        )
        range_value, elevation_value, _ = look_angles(
            beam_satellite_position, users_ecef[victim]
        )
        path = float(
            link_power_factor(
                np.asarray(range_value),
                np.asarray(elevation_value),
                np.asarray(1.0),
                shadow_fading_db=0.0,
            )
        )
        if beam_satellite == victim_satellite:
            receive = receive_max
        else:
            receive = float(
                receive_gain_linear(
                    angle_between_deg(
                        users_ecef[victim],
                        positions[victim_satellite],
                        beam_satellite_position,
                    )
                )
            )
        result[victim] = transmit * path * receive
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise RelationalZRC3Error("nominal beam coupling is non-finite")
    result.setflags(write=False)
    return result


def _build_nominal_reference_cache(
    *,
    environment: StepEnvironment,
    refs: np.ndarray,
    opening: np.ndarray,
    power: np.ndarray,
    signal: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    legal: np.ndarray,
    colours: np.ndarray,
    centres: np.ndarray,
    positions: Mapping[int, np.ndarray],
    users_ecef: np.ndarray,
) -> _NominalReferenceCache:
    reference_actions = _branch_actions(refs)
    reference_served = _branch_served(reference_actions, opening, legal)
    reference_rates, reference_interference = _nominal_rates(
        environment=environment,
        actions=reference_actions,
        served=reference_served,
        required_power=power,
        signal_surface=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )
    reference_keys = tuple(_branch_keys(reference_actions, norads, cells, legal))
    load_by_key: dict[tuple[int, int], int] = {}
    power_by_key: dict[tuple[int, int], float] = {}
    for uid, key in enumerate(reference_keys):
        if not bool(reference_served[uid]) or key is None:
            continue
        load_by_key[key] = load_by_key.get(key, 0) + 1
        power_by_key[key] = max(
            power_by_key.get(key, 0.0), float(power[uid, int(refs[uid])])
        )

    peer_power_by_focal: list[dict[tuple[int, int], float]] = []
    for focal in range(len(refs)):
        peers: dict[tuple[int, int], float] = {}
        for uid, key in enumerate(reference_keys):
            if uid == focal or not bool(reference_served[uid]) or key is None:
                continue
            peers[key] = max(peers.get(key, 0.0), float(power[uid, int(refs[uid])]))
        peer_power_by_focal.append(peers)

    possible_keys = {
        (int(norads[uid, action]), int(cells[uid, action]))
        for uid in range(legal.shape[0])
        for action in np.flatnonzero(legal[uid] & opening[uid]).tolist()
    }
    coupling_by_key = {
        key: _beam_to_reference_victim_coupling(
            beam_key=key,
            reference_served=reference_served,
            reference_keys=reference_keys,
            colours=colours,
            centres=centres,
            positions=positions,
            users_ecef=users_ecef,
        )
        for key in sorted(possible_keys)
    }
    reference_signal = np.zeros(len(refs), dtype=np.float64)
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action >= 0 and bool(reference_served[uid]):
            reference_signal[uid] = float(signal[uid, action])
    return _NominalReferenceCache(
        reference_served=np.array(reference_served, copy=True),
        reference_keys=reference_keys,
        reference_interference=np.array(reference_interference, copy=True),
        reference_rates=np.array(reference_rates, copy=True),
        reference_load_by_key=load_by_key,
        reference_power_by_key=power_by_key,
        peer_power_by_focal=tuple(peer_power_by_focal),
        coupling_by_key=coupling_by_key,
        reference_signal=reference_signal,
        noise_w=_noise_from(environment),
        bandwidth_hz=_bandwidth_from(environment),
    )


def _cached_nominal_branch_interference(
    cache: _NominalReferenceCache,
    *,
    focal_user: int,
    focal_action: int,
    opening: np.ndarray,
    power: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
) -> np.ndarray:
    """Update fixed-reference victim interference from at most two beam deltas."""

    focal = int(focal_user)
    action = int(focal_action)
    candidate_served = bool(opening[focal, action])
    candidate_key = (
        (int(norads[focal, action]), int(cells[focal, action]))
        if candidate_served
        else None
    )
    origin_key = (
        cache.reference_keys[focal]
        if bool(cache.reference_served[focal])
        else None
    )
    interference = np.array(cache.reference_interference, copy=True)
    changed_keys = {key for key in (origin_key, candidate_key) if key is not None}
    peers = cache.peer_power_by_focal[focal]
    for key in changed_keys:
        old_power = float(cache.reference_power_by_key.get(key, 0.0))
        new_power = float(peers.get(key, 0.0))
        if candidate_key == key:
            new_power = max(new_power, float(power[focal, action]))
        coupling = cache.coupling_by_key.get(key)
        if coupling is None:
            raise RelationalZRC3Error("candidate beam is absent from nominal coupling cache")
        interference += (new_power - old_power) * coupling
    tolerance = 64.0 * np.finfo(np.float64).eps * max(
        1.0, float(np.max(cache.reference_interference, initial=0.0))
    )
    if np.any(interference < -tolerance) or not np.all(np.isfinite(interference)):
        raise RelationalZRC3Error("cached nominal interference is invalid")
    return np.maximum(interference, 0.0)


def _cached_nominal_nonfocal_branch(
    cache: _NominalReferenceCache,
    *,
    focal_user: int,
    focal_action: int,
    opening: np.ndarray,
    power: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate a unilateral branch from cached interference deltas."""

    users = cache.reference_served.size
    focal = int(focal_user)
    action = int(focal_action)
    candidate_served = bool(opening[focal, action])
    candidate_key = (
        (int(norads[focal, action]), int(cells[focal, action]))
        if candidate_served
        else None
    )
    origin_key = (
        cache.reference_keys[focal]
        if bool(cache.reference_served[focal])
        else None
    )
    interference = _cached_nominal_branch_interference(
        cache,
        focal_user=focal,
        focal_action=action,
        opening=opening,
        power=power,
        norads=norads,
        cells=cells,
    )

    nonfocal_served = np.array(cache.reference_served, copy=True)
    nonfocal_served[focal] = False
    loads = np.zeros(users, dtype=np.float64)
    for victim, victim_key in enumerate(cache.reference_keys):
        if not bool(nonfocal_served[victim]) or victim_key is None:
            continue
        load = int(cache.reference_load_by_key[victim_key])
        if origin_key == victim_key:
            load -= 1
        if candidate_key == victim_key:
            load += 1
        if load < 1:
            raise RelationalZRC3Error("cached nominal served load fell below one")
        loads[victim] = float(load)
    sinr = np.divide(
        cache.reference_signal,
        cache.noise_w + interference,
        out=np.zeros(users, dtype=np.float64),
        where=nonfocal_served,
    )
    rates = shannon_rate_bps(
        sinr,
        beam_load=loads,
        bandwidth_hz=cache.bandwidth_hz,
    )
    rates = np.where(nonfocal_served, rates, 0.0)
    return rates, interference


def nominal_relational_zr_surface(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    reference_actions: object,
    required_power_surface: object,
    opening_feasibility_surface: object,
    interval_s: float | None = None,
    kappa_bits: float = 1.0,
    pmax_w: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Reconstruct the parameter-free nominal ``(z_3, q_3)`` surfaces.

    The returned pair is ``(delta_bits, q3_values)`` with shapes ``(U,A,U)``
    and ``(U,A)``.  Only deterministic geometry, unit fading, zero shadowing,
    current required power, and opening feasibility are used.  The focal rate
    is removed from every victim panel, then the fixed ZR positive/negative
    aggregation is applied and centred on the detached reference.
    """

    del pmax_w  # retained for a uniform call surface; nominal rates do not need it
    tables, legal = _anchor(environment, observation)
    refs, power, opening, identity = _validate_context_inputs(
        tables,
        legal,
        reference_actions,
        required_power_surface,
        opening_feasibility_surface,
    )
    norads = identity[:, :, 0]
    cells = identity[:, :, 1]
    centres, colours, positions = _grid_data(environment, observation, norads, cells)
    users_ecef = _user_positions(environment, len(tables))
    theta, slant, elevation = _candidate_geometry(
        environment,
        observation,
        norads,
        cells,
        centres,
        positions,
        users_ecef,
    )
    signal = _nominal_signal_surface(
        theta=theta,
        slant=slant,
        elevation=elevation,
        required_power=power,
        legal=legal,
    )
    cache = _build_nominal_reference_cache(
        environment=environment,
        refs=refs,
        opening=opening,
        power=power,
        signal=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )
    users = len(tables)
    candidate_rates = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    for uid in range(users):
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            rates, _interference = _cached_nominal_nonfocal_branch(
                cache,
                focal_user=uid,
                focal_action=action,
                opening=opening,
                power=power,
                norads=norads,
                cells=cells,
            )
            candidate_rates[uid, action] = rates
            candidate_rates[uid, action, uid] = 0.0
    interval = interval_s
    if interval is None:
        config = getattr(getattr(environment, "driver", None), "config", None)
        ephemeris = getattr(config, "ephemeris", None)
        interval = getattr(ephemeris, "time_step_s", 1.0)
    try:
        interval_value = float(interval)
        kappa = float(kappa_bits)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalZRC3Error("interval_s and kappa_bits must be finite positive values") from error
    if not math.isfinite(interval_value) or interval_value <= 0.0 or not math.isfinite(kappa) or kappa <= 0.0:
        raise RelationalZRC3Error("interval_s and kappa_bits must be finite positive values")
    delta = interval_value * (
        candidate_rates - cache.reference_rates[None, None, :]
    )
    delta = np.where(legal[:, :, None], delta, 0.0)
    # The victim axis is the last axis; zero the focal diagonal, not all
    # victim columns.
    delta[np.arange(users), :, np.arange(users)] = 0.0
    victim_mask = compute_victim_mask(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        cell_colors=colours,
    )
    compatible = compute_positive_credit_compatible(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening,
        required_power_surface=power,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    aggregated = np.sum(
        victim_mask
        * (
            np.minimum(delta, 0.0)
            + compatible[:, :, None] * np.maximum(delta, 0.0)
        ),
        axis=2,
    )
    reference_aggregate = aggregated[np.arange(users), np.maximum(refs, 0)]
    q3 = aggregated - reference_aggregate[:, None]
    q3 = np.where(legal, q3 / kappa, 0.0)
    q3[refs == NO_OP_ACTION] = 0.0
    if not np.all(np.isfinite(delta)) or not np.all(np.isfinite(q3)):
        raise RelationalZRC3Error("nominal ZR surface is non-finite")
    delta.setflags(write=False)
    q3.setflags(write=False)
    return delta, q3


nominal_zr_surface = nominal_relational_zr_surface
nominal_relational_zr_q3 = nominal_relational_zr_surface


def encode_relational_zr_c3_state(
    environment: StepEnvironment,
    observation: StepObservation,
    reference_actions: object,
    required_power_surface: object | None = None,
    opening_feasibility_surface: object | None = None,
    *,
    current_required_power_w: object | None = None,
    opening_service_feasible: object | None = None,
    pmax_w: float | None = None,
) -> RelationalZRC3Observation:
    """Encode the frozen V0.18 relational C3 predecision observation."""

    if required_power_surface is None:
        required_power_surface = current_required_power_w
    elif current_required_power_w is not None:
        raise RelationalZRC3Error("provide one required-power surface spelling")
    if opening_feasibility_surface is None:
        opening_feasibility_surface = opening_service_feasible
    elif opening_service_feasible is not None:
        raise RelationalZRC3Error("provide one opening-surface spelling")
    if required_power_surface is None or opening_feasibility_surface is None:
        raise RelationalZRC3Error("required and opening surfaces are both required")

    tables, legal = _anchor(environment, observation)
    refs, power, opening, identity = _validate_context_inputs(
        tables,
        legal,
        reference_actions,
        required_power_surface,
        opening_feasibility_surface,
    )
    norads = identity[:, :, 0]
    cells = identity[:, :, 1]
    users = len(tables)
    pmax = _pmax_from(environment, pmax_w)
    centres, colours, positions = _grid_data(environment, observation, norads, cells)
    users_ecef = _user_positions(environment, users)
    theta, slant, elevation = _candidate_geometry(
        environment,
        observation,
        norads,
        cells,
        centres,
        positions,
        users_ecef,
    )
    signal = _nominal_signal_surface(
        theta=theta,
        slant=slant,
        elevation=elevation,
        required_power=power,
        legal=legal,
    )
    cache = _build_nominal_reference_cache(
        environment=environment,
        refs=refs,
        opening=opening,
        power=power,
        signal=signal,
        norads=norads,
        cells=cells,
        legal=legal,
        colours=colours,
        centres=centres,
        positions=positions,
        users_ecef=users_ecef,
    )

    contexts = np.zeros((users, NUM_ACTIONS, RELATIONAL_ZR_ACTION_CONTEXT_DIM), dtype=np.float64)
    victims = compute_victim_mask(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        cell_colors=colours,
    )
    compatible = compute_positive_credit_compatible(
        reference_actions=refs,
        action_mask=legal,
        opening_feasibility_surface=opening,
        required_power_surface=power,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    keys = _physical_keys(norads, cells, legal)
    ref_opening = np.zeros(users, dtype=np.bool_)
    ref_keys: list[tuple[int, int] | None] = [None] * users
    ref_power = np.zeros(users, dtype=np.float64)
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action >= 0:
            ref_keys[uid] = keys[uid][action]
            ref_opening[uid] = bool(opening[uid, action])
            ref_power[uid] = float(power[uid, action])
    peer_count: dict[tuple[int, int], int] = {}
    peer_max: dict[tuple[int, int], float] = {}
    for peer in range(users):
        key = ref_keys[peer]
        if bool(ref_opening[peer]) and key is not None:
            peer_count[key] = peer_count.get(key, 0) + 1
            peer_max[key] = max(peer_max.get(key, 0.0), ref_power[peer])
    # The context is explicitly relative to the focal user.  Keep the
    # all-user maps above for the reference load tokens, then derive the
    # non-focal maps used by the seven action-context entries.
    peer_count_by_focal: list[dict[tuple[int, int], int]] = []
    peer_max_by_focal: list[dict[tuple[int, int], float]] = []
    for uid in range(users):
        count_map: dict[tuple[int, int], int] = {}
        max_map: dict[tuple[int, int], float] = {}
        for peer in range(users):
            if peer == uid or not bool(ref_opening[peer]) or ref_keys[peer] is None:
                continue
            key = ref_keys[peer]
            assert key is not None
            count_map[key] = count_map.get(key, 0) + 1
            max_map[key] = max(max_map.get(key, 0.0), ref_power[peer])
        peer_count_by_focal.append(count_map)
        peer_max_by_focal.append(max_map)

    observed_sinr = np.asarray(getattr(observation, "candidate_sinr", np.zeros((users, NUM_ACTIONS))), dtype=np.float64)
    if observed_sinr.shape != (users, NUM_ACTIONS) or not np.all(np.isfinite(observed_sinr)) or np.any(observed_sinr < 0.0):
        raise RelationalZRC3Error("candidate_sinr proxy must be finite nonnegative shape (U,28)")
    n0 = np.zeros(users, dtype=np.float64)
    sbar = np.zeros(users, dtype=np.float64)
    ibar0 = np.zeros(users, dtype=np.float64)
    reference_interference = cache.reference_interference
    for uid, raw in enumerate(refs.tolist()):
        action = int(raw)
        if action < 0 or not bool(ref_opening[uid]) or ref_keys[uid] is None:
            continue
        n0[uid] = float(peer_count.get(ref_keys[uid], 0))
        sbar[uid] = float(cache.reference_signal[uid])
        ibar0[uid] = float(reference_interference[uid])
    noise = _noise_from(environment)
    denominator_users = float(users)
    for uid in range(users):
        reference_action = int(refs[uid])
        reference_key = ref_keys[uid]
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            candidate_key = keys[uid][action]
            candidate_open = bool(opening[uid, action])
            reference_headroom = (
                (pmax - ref_power[uid]) / pmax
                if reference_action >= 0 and bool(ref_opening[uid])
                else -1.0
            )
            candidate_headroom = (pmax - float(power[uid, action])) / pmax if candidate_open else -1.0
            same_beam = float(reference_key is not None and candidate_key == reference_key)
            focal_peer_count = peer_count_by_focal[uid]
            focal_peer_max = peer_max_by_focal[uid]
            candidate_count = focal_peer_count.get(candidate_key, 0) if candidate_key is not None else 0
            candidate_max = focal_peer_max.get(candidate_key, 0.0) if candidate_key is not None else 0.0
            reference_count = focal_peer_count.get(reference_key, 0) if reference_key is not None else 0
            reference_max = focal_peer_max.get(reference_key, 0.0) if reference_key is not None else 0.0
            contexts[uid, action] = np.asarray(
                [
                    reference_headroom,
                    candidate_headroom,
                    same_beam,
                    reference_count / denominator_users,
                    candidate_count / denominator_users,
                    (reference_max - ref_power[uid]) / pmax,
                    (candidate_max - float(power[uid, action])) / pmax,
                ],
                dtype=np.float64,
            )

    tokens = np.zeros((users, NUM_ACTIONS, users, RELATIONAL_ZR_VICTIM_TOKEN_DIM), dtype=np.float64)
    for uid in range(users):
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            candidate_interference = _cached_nominal_branch_interference(
                cache,
                focal_user=uid,
                focal_action=action,
                opening=opening,
                power=power,
                norads=norads,
                cells=cells,
            )
            for victim in np.flatnonzero(victims[uid, action]).tolist():
                victim_ref = int(refs[victim])
                if victim_ref < 0:
                    continue
                victim_key = ref_keys[victim]
                if victim_key is None:
                    continue
                candidate_load = 0
                for peer, peer_key in enumerate(ref_keys):
                    if peer != uid and bool(ref_opening[peer]) and peer_key == victim_key:
                        candidate_load += 1
                if bool(opening[uid, action]) and candidate_key_equals(keys[uid][action], victim_key):
                    candidate_load += 1
                observed = float(observed_sinr[victim, victim_ref])
                tokens[uid, action, victim] = np.asarray(
                    [
                        math.log1p(observed),
                        n0[victim] / denominator_users,
                        (float(candidate_load) - n0[victim]) / denominator_users,
                        math.log1p(sbar[victim] / noise),
                        math.log1p(ibar0[victim] / noise),
                        math.asinh((float(candidate_interference[victim]) - ibar0[victim]) / noise),
                    ],
                    dtype=np.float64,
                )

    contexts[~legal] = 0.0
    tokens[~victims] = 0.0
    result = RelationalZRC3Observation(
        action_context=contexts,
        victim_tokens=tokens,
        action_mask=legal,
        victim_mask=victims,
        positive_credit_compatible=compatible,
        reference_actions=refs,
    )
    result.verify()
    return result


def candidate_key_equals(
    first: tuple[int, int] | None,
    second: tuple[int, int] | None,
) -> bool:
    return first is not None and second is not None and first == second


encode_v018_relational_zr_c3_state = encode_relational_zr_c3_state


__all__ = [
    "ACTION_CONTEXT_DIM",
    "RELATIONAL_ZR_ACTION_CONTEXT_DIM",
    "RELATIONAL_ZR_C3_SCHEMA",
    "RELATIONAL_ZR_C3_SCHEMA_SHA256",
    "RELATIONAL_ZR_C3_SCHEMA_VERSION",
    "RELATIONAL_ZR_VICTIM_TOKEN_DIM",
    "VICTIM_TOKEN_DIM",
    "RelationalZRC3Error",
    "RelationalZRC3StateError",
    "RelationalZRC3Observation",
    "compute_positive_credit_compatible",
    "compute_victim_mask",
    "encode_relational_zr_c3_state",
    "encode_v018_relational_zr_c3_state",
    "nominal_relational_zr_q3",
    "nominal_relational_zr_surface",
    "nominal_zr_surface",
    "positive_credit_compatible",
    "victim_mask_surface",
]
