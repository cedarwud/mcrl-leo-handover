"""Pure, outcome-blind LC-SRS C3 topology enumeration for V0.23.

The module is the pre-teacher seam described by Contract section 4.  It
accepts one frozen native anchor surface (masks, opening predicates, physical
keys, and detached Q1+Q2 values), and returns immutable topology and coverage
receipts.  It never accepts an environment, a random generator, a label, or a
profile result.  Consequently a caller can serialize the returned topology
before any physical profile is evaluated.

The public interface deliberately keeps raw physical identifiers in receipt
metadata only.  They are used for equality and deterministic ordering, never
as learner features.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import struct
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


LCSRS_C3_TOPOLOGY_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-c3-topology-v1"
LCSRS_DECISION_PHASES = tuple(range(0, 10))
LCSRS_NATIVE_PHASES = tuple(range(1, 10))
LCSRS_MIN_CLOSURE_PAIRS = 24
LCSRS_TOPOLOGY_OK = "OK"
LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS = "INSUFFICIENT_PAIRS"
LCSRS_RETENTION_RETAINED = "RETAINED_FOR_FITTING"
LCSRS_RETENTION_NO_PAIRS = "ENUMERATED_NO_CLOSURE_PAIR"
LCSRS_RETENTION_EMPTY_CLASS = "ENUMERATED_EMPTY_S_R_C_CLASS"

PhysicalKey = tuple[int, int]


class LCSRSC3TopologyError(MCRLContractError):
    """A frozen LC-SRS topology input or receipt violates section 4."""


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise LCSRSC3TopologyError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise LCSRSC3TopologyError(f"{field} must be a nonempty trimmed string")
    return value


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LCSRSC3TopologyError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    ndim: int,
    exact_dtype: bool = False,
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != ndim:
        raise LCSRSC3TopologyError(f"{field} must be {ndim}-dimensional")
    if exact_dtype and raw.dtype != dtype:
        raise LCSRSC3TopologyError(f"{field} must have dtype {dtype}")
    try:
        result = np.array(raw, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3TopologyError(f"{field} cannot be materialised") from error
    if np.issubdtype(result.dtype, np.floating) and not np.all(np.isfinite(result)):
        raise LCSRSC3TopologyError(f"{field} must be finite")
    result.setflags(write=False)
    return result


def _readonly(value: object, *, dtype: np.dtype[Any]) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3TopologyError("receipt array cannot be materialised") from error
    result.setflags(write=False)
    return result


def _digest_array(digest: "hashlib._Hash", name: str, value: np.ndarray) -> None:
    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(b"\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _digest_text(digest: "hashlib._Hash", value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)


def _key(value: object, *, field: str) -> PhysicalKey:
    if not isinstance(value, tuple) or len(value) != 2:
        raise LCSRSC3TopologyError(f"{field} must be a two-integer physical key")
    first, second = value
    if type(first) is not int or type(second) is not int or first < 0 or second < 0:
        raise LCSRSC3TopologyError(
            f"{field} must contain two nonnegative exact integers"
        )
    return (first, second)


def _key_digest(digest: "hashlib._Hash", value: PhysicalKey) -> None:
    digest.update(struct.pack(">2q", *value))


def _pair_id(
    *,
    world_id: int,
    phase: int,
    anchor_id: str,
    source_key: PhysicalKey,
    users: tuple[int, int],
) -> str:
    # This is receipt metadata, not a learner feature.  Including the users
    # prevents an accidental collision if a future topology rule changes.
    return (
        f"w{world_id}:t{phase}:a{anchor_id}:"
        f"s{source_key[0]}-{source_key[1]}:u{users[0]}-{users[1]}"
    )


def _select_destination(
    capture: "LCSRSC3AnchorCapture",
    *,
    user: int,
    source_key: PhysicalKey,
    member_users: tuple[int, int],
) -> tuple[tuple[int, ...], int | None, PhysicalKey | None]:
    """Return all fixed destination actions and the native-index tie winner."""

    references = np.asarray(capture.reference_actions)
    keys = np.asarray(capture.physical_keys)
    mask = np.asarray(capture.action_mask)
    opening = np.asarray(capture.opening_feasibility)
    q12 = np.asarray(capture.detached_q12)
    nonmember_keys = {
        (int(keys[other, int(references[other]), 0]), int(keys[other, int(references[other]), 1]))
        for other in range(keys.shape[0])
        if other not in member_users
    }
    eligible: list[int] = []
    for action in np.flatnonzero(mask[user] & opening[user]).tolist():
        candidate = (int(keys[user, action, 0]), int(keys[user, action, 1]))
        if candidate != source_key and candidate in nonmember_keys:
            eligible.append(int(action))
    eligible_tuple = tuple(sorted(eligible))
    if not eligible_tuple:
        return eligible_tuple, None, None
    selected = max(eligible_tuple, key=lambda action: (float(q12[user, action]), -action))
    selected_key = (int(keys[user, selected, 0]), int(keys[user, selected, 1]))
    return eligible_tuple, int(selected), selected_key


@dataclass(frozen=True)
class LCSRSC3AnchorCapture:
    """Immutable native anchor inputs to the pure topology implementation."""

    world_id: int
    phase: int
    anchor_id: str
    q12_snapshot: object
    action_mask: np.ndarray
    opening_feasibility: np.ndarray
    physical_keys: np.ndarray
    reference_actions: object | None = None
    content_digest: str = ""

    def __post_init__(self) -> None:
        world = _exact_int(self.world_id, field="world_id")
        phase = _exact_int(self.phase, field="phase")
        if phase not in LCSRS_DECISION_PHASES:
            raise LCSRSC3TopologyError("phase must be a native decision in 0..9")
        anchor = _text(self.anchor_id, field="anchor_id")

        raw_mask = np.asarray(self.action_mask)
        raw_opening = np.asarray(self.opening_feasibility)
        if raw_mask.dtype != np.bool_ or raw_opening.dtype != np.bool_:
            raise LCSRSC3TopologyError(
                "action_mask and opening_feasibility must have Boolean dtype"
            )
        mask = _array(
            raw_mask,
            field="action_mask",
            dtype=np.dtype(np.bool_),
            ndim=2,
            exact_dtype=True,
        )
        opening = _array(
            raw_opening,
            field="opening_feasibility",
            dtype=np.dtype(np.bool_),
            ndim=2,
            exact_dtype=True,
        )
        if mask.shape[1:] != (NUM_ACTIONS,) or opening.shape != mask.shape:
            raise LCSRSC3TopologyError(
                f"native masks must have shape (U,{NUM_ACTIONS})"
            )
        if mask.shape[0] < 1:
            raise LCSRSC3TopologyError("anchor capture needs at least one user")
        if np.any(opening & ~mask):
            raise LCSRSC3TopologyError(
                "opening_feasibility must be a subset of action_mask"
            )
        if np.any(~np.any(mask, axis=1)):
            raise LCSRSC3TopologyError("each user needs at least one legal action")

        from ..algorithms.ee_axis_lcsrs_three_route import DetachedQ12Snapshot

        if not isinstance(self.q12_snapshot, DetachedQ12Snapshot):
            raise LCSRSC3TopologyError(
                "q12_snapshot must be an authenticated DetachedQ12Snapshot"
            )
        q12_raw = np.asarray(self.q12_snapshot.q12)
        if not np.issubdtype(q12_raw.dtype, np.floating):
            raise LCSRSC3TopologyError("detached_q12 must have floating dtype")
        q12 = _array(
            q12_raw,
            field="detached_q12",
            dtype=np.dtype(np.float64),
            ndim=2,
        )
        if q12.shape != mask.shape:
            raise LCSRSC3TopologyError(
                f"detached_q12 must have shape (U,{NUM_ACTIONS})"
            )
        q12_mutable = np.array(q12, copy=True, order="C")
        q12_mutable[~mask] = 0.0
        q12_mutable.setflags(write=False)
        q12 = q12_mutable

        raw_keys = np.asarray(self.physical_keys)
        if (
            not np.issubdtype(raw_keys.dtype, np.integer)
            or np.issubdtype(raw_keys.dtype, np.bool_)
        ):
            raise LCSRSC3TopologyError("physical_keys must have integer dtype")
        keys = _array(
            raw_keys,
            field="physical_keys",
            dtype=np.dtype(np.int64),
            ndim=3,
        )
        if keys.shape != (mask.shape[0], NUM_ACTIONS, 2):
            raise LCSRSC3TopologyError(
                f"physical_keys must have shape (U,{NUM_ACTIONS},2)"
            )
        keys_mutable = np.array(keys, copy=True, order="C")
        keys_mutable[~mask] = -1
        for user in range(mask.shape[0]):
            seen: set[PhysicalKey] = set()
            for action in np.flatnonzero(mask[user]).tolist():
                physical = (int(keys_mutable[user, action, 0]), int(keys_mutable[user, action, 1]))
                if physical[0] < 0 or physical[1] < 0:
                    raise LCSRSC3TopologyError(
                        "legal physical keys must be nonnegative"
                    )
                if physical in seen:
                    raise LCSRSC3TopologyError(
                        "one user cannot expose duplicate legal physical keys"
                    )
                seen.add(physical)
        keys_mutable.setflags(write=False)

        references = np.argmax(np.where(mask, q12, -np.inf), axis=1).astype(
            np.int64, copy=False
        )
        if self.reference_actions is not None:
            raw_references = np.asarray(self.reference_actions)
            if (
                raw_references.dtype != np.dtype(np.int64)
                or raw_references.shape != (mask.shape[0],)
            ):
                raise LCSRSC3TopologyError(
                    "reference_actions must be int64 shape (U,)"
                )
            if not np.array_equal(raw_references, references):
                raise LCSRSC3TopologyError(
                    "reference_actions disagree with masked detached Q1+Q2 argmax"
                )
        references = _readonly(references, dtype=np.dtype(np.int64))

        object.__setattr__(self, "world_id", world)
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "anchor_id", anchor)
        object.__setattr__(self, "action_mask", mask)
        object.__setattr__(self, "opening_feasibility", opening)
        object.__setattr__(self, "physical_keys", keys_mutable)
        object.__setattr__(self, "reference_actions", references)
        expected = _capture_digest(self)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3TopologyError("anchor capture digest disagrees with inputs")
        object.__setattr__(self, "content_digest", expected)

    @property
    def users(self) -> int:
        return int(self.action_mask.shape[0])

    @property
    def q12_values(self) -> np.ndarray:
        """Compatibility name for the already detached Q1+Q2 surface."""

        return self.detached_q12

    @property
    def detached_q12(self) -> np.ndarray:
        """Exact immutable Q1+Q2 surface owned by the authenticated snapshot."""

        return self.q12_snapshot.q12

    def verify(self) -> str:
        expected = _capture_digest(self)
        if self.content_digest != expected:
            raise LCSRSC3TopologyError("anchor capture digest disagrees with inputs")
        return expected


def _capture_digest(capture: LCSRSC3AnchorCapture) -> str:
    digest = hashlib.sha256()
    digest.update(LCSRS_C3_TOPOLOGY_SCHEMA.encode("ascii"))
    digest.update(struct.pack(">QI", capture.world_id, capture.phase))
    _digest_text(digest, capture.anchor_id)
    for name, value in (
        ("detached_q12", capture.detached_q12),
        ("action_mask", capture.action_mask),
        ("opening_feasibility", capture.opening_feasibility),
        ("physical_keys", capture.physical_keys),
        ("reference_actions", np.asarray(capture.reference_actions)),
    ):
        _digest_array(digest, name, value)
    digest.update(capture.q12_snapshot.content_digest.encode("ascii"))
    digest.update(capture.q12_snapshot.source_state_digest.encode("ascii"))
    digest.update(capture.q12_snapshot.model_digest.encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSC3ClosurePair:
    """One supported exact-two source and its frozen designated moves."""

    world_id: int
    phase: int
    anchor_id: str
    source_key: PhysicalKey
    member_users: tuple[int, int]
    designated_actions: tuple[int, int]
    destination_keys: tuple[PhysicalKey, PhysicalKey]
    eligible_actions_by_member: tuple[tuple[int, ...], tuple[int, ...]]
    detached_q12_digest: str
    content_digest: str = ""

    def __post_init__(self) -> None:
        _exact_int(self.world_id, field="world_id")
        phase = _exact_int(self.phase, field="phase")
        if phase not in LCSRS_DECISION_PHASES:
            raise LCSRSC3TopologyError("pair phase must be in 0..9")
        _text(self.anchor_id, field="anchor_id")
        source = _key(self.source_key, field="source_key")
        users = self.member_users
        actions = self.designated_actions
        destinations = self.destination_keys
        candidates = self.eligible_actions_by_member
        if (
            not isinstance(users, tuple)
            or len(users) != 2
            or any(type(user) is not int or user < 0 for user in users)
            or not users[0] < users[1]
        ):
            raise LCSRSC3TopologyError("closure pair members must be two sorted users")
        if (
            not isinstance(actions, tuple)
            or len(actions) != 2
            or any(type(action) is not int or not 0 <= action < NUM_ACTIONS for action in actions)
        ):
            raise LCSRSC3TopologyError("closure pair actions must be two native actions")
        if not isinstance(destinations, tuple) or len(destinations) != 2:
            raise LCSRSC3TopologyError("closure pair needs two destination keys")
        parsed_destinations = tuple(
            _key(value, field="destination_key") for value in destinations
        )
        if any(value == source for value in parsed_destinations):
            raise LCSRSC3TopologyError("designated destination must differ from source")
        if (
            not isinstance(candidates, tuple)
            or len(candidates) != 2
            or any(
                not isinstance(row, tuple)
                or tuple(sorted(row)) != row
                or any(type(action) is not int or not 0 <= action < NUM_ACTIONS for action in row)
                for row in candidates
            )
            or any(action not in row for action, row in zip(actions, candidates, strict=True))
        ):
            raise LCSRSC3TopologyError("eligible destination actions are malformed")
        digest = _sha256(self.detached_q12_digest, field="detached_q12_digest")
        object.__setattr__(self, "source_key", source)
        object.__setattr__(self, "destination_keys", parsed_destinations)
        object.__setattr__(self, "detached_q12_digest", digest)
        expected = _pair_digest(self)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3TopologyError("closure pair digest disagrees with fields")
        object.__setattr__(self, "content_digest", expected)

    @property
    def pair_id(self) -> str:
        return _pair_id(
            world_id=self.world_id,
            phase=self.phase,
            anchor_id=self.anchor_id,
            source_key=self.source_key,
            users=self.member_users,
        )

    @property
    def user_ids(self) -> tuple[int, int]:
        return self.member_users

    @property
    def proposed_actions(self) -> tuple[int, int]:
        return self.designated_actions


def _pair_digest(pair: LCSRSC3ClosurePair) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-c3-closure-pair-v1")
    digest.update(struct.pack(">QI", pair.world_id, pair.phase))
    _digest_text(digest, pair.anchor_id)
    _key_digest(digest, pair.source_key)
    digest.update(struct.pack(">2q", *pair.member_users))
    digest.update(struct.pack(">2q", *pair.designated_actions))
    for key in pair.destination_keys:
        _key_digest(digest, key)
    for row in pair.eligible_actions_by_member:
        digest.update(struct.pack(">I", len(row)))
        if row:
            digest.update(struct.pack(f">{len(row)}q", *row))
    digest.update(pair.detached_q12_digest.encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSC3NoCloseControl:
    """An occupancy-three control using the first two users by user id."""

    world_id: int
    phase: int
    anchor_id: str
    source_key: PhysicalKey
    member_users: tuple[int, int]
    third_user: int
    designated_actions: tuple[int | None, int | None]
    destination_keys: tuple[PhysicalKey | None, PhysicalKey | None]
    eligible_actions_by_member: tuple[tuple[int, ...], tuple[int, ...]]
    detached_q12_digest: str
    content_digest: str = ""

    def __post_init__(self) -> None:
        _exact_int(self.world_id, field="world_id")
        phase = _exact_int(self.phase, field="phase")
        if phase not in LCSRS_DECISION_PHASES:
            raise LCSRSC3TopologyError("no-close phase must be in 0..9")
        _text(self.anchor_id, field="anchor_id")
        source = _key(self.source_key, field="source_key")
        users = self.member_users
        _exact_int(self.third_user, field="third_user")
        if (
            not isinstance(users, tuple)
            or len(users) != 2
            or any(type(user) is not int or user < 0 for user in users)
            or not users[0] < users[1] < self.third_user
        ):
            raise LCSRSC3TopologyError(
                "no-close members must be the first two users before third_user"
            )
        actions = self.designated_actions
        destinations = self.destination_keys
        candidates = self.eligible_actions_by_member
        if not isinstance(actions, tuple) or len(actions) != 2:
            raise LCSRSC3TopologyError("no-close needs two optional designated actions")
        if not isinstance(destinations, tuple) or len(destinations) != 2:
            raise LCSRSC3TopologyError("no-close needs two optional destinations")
        if (
            not isinstance(candidates, tuple)
            or len(candidates) != 2
            or any(
                not isinstance(row, tuple)
                or tuple(sorted(row)) != row
                or any(type(action) is not int or not 0 <= action < NUM_ACTIONS for action in row)
                for row in candidates
            )
        ):
            raise LCSRSC3TopologyError("no-close eligible destination actions are malformed")
        for action, destination, row in zip(actions, destinations, candidates, strict=True):
            if action is None:
                if destination is not None:
                    raise LCSRSC3TopologyError(
                        "missing no-close action must have a missing destination"
                    )
            else:
                if type(action) is not int or not 0 <= action < NUM_ACTIONS:
                    raise LCSRSC3TopologyError("no-close designated action is not native")
                if action not in row or destination is None:
                    raise LCSRSC3TopologyError(
                        "no-close designated action is outside its candidate set"
                    )
                parsed = _key(destination, field="no-close destination_key")
                if parsed == source:
                    raise LCSRSC3TopologyError(
                        "no-close designated destination must differ from source"
                    )
        digest = _sha256(self.detached_q12_digest, field="detached_q12_digest")
        object.__setattr__(self, "source_key", source)
        object.__setattr__(self, "detached_q12_digest", digest)
        expected = _no_close_digest(self)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3TopologyError("no-close digest disagrees with fields")
        object.__setattr__(self, "content_digest", expected)

    @property
    def control_id(self) -> str:
        return (
            f"w{self.world_id}:t{self.phase}:a{self.anchor_id}:"
            f"no-close-s{self.source_key[0]}-{self.source_key[1]}"
        )

    @property
    def eligible(self) -> bool:
        return all(action is not None for action in self.designated_actions)


def _no_close_digest(control: LCSRSC3NoCloseControl) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-c3-no-close-v1")
    digest.update(struct.pack(">QI", control.world_id, control.phase))
    _digest_text(digest, control.anchor_id)
    _key_digest(digest, control.source_key)
    digest.update(struct.pack(">3q", *control.member_users, control.third_user))
    for action, destination, candidates in zip(
        control.designated_actions,
        control.destination_keys,
        control.eligible_actions_by_member,
        strict=True,
    ):
        digest.update(struct.pack(">q", -1 if action is None else action))
        digest.update(b"\0" if destination is None else b"\1")
        if destination is not None:
            _key_digest(digest, destination)
        digest.update(struct.pack(">I", len(candidates)))
        if candidates:
            digest.update(struct.pack(f">{len(candidates)}q", *candidates))
    digest.update(control.detached_q12_digest.encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSC3AnchorTopologyReceipt:
    """All exact-two pairs, occupancy-three controls, and class receipt data."""

    capture: LCSRSC3AnchorCapture
    pairs: tuple[LCSRSC3ClosurePair, ...]
    no_close_controls: tuple[LCSRSC3NoCloseControl, ...]
    reference_source_occupancies: tuple[tuple[PhysicalKey, int], ...]
    content_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.capture, LCSRSC3AnchorCapture):
            raise LCSRSC3TopologyError("topology receipt needs an anchor capture")
        self.capture.verify()
        pairs = tuple(self.pairs)
        controls = tuple(self.no_close_controls)
        if any(not isinstance(pair, LCSRSC3ClosurePair) for pair in pairs):
            raise LCSRSC3TopologyError("topology pairs contain an invalid record")
        if any(not isinstance(control, LCSRSC3NoCloseControl) for control in controls):
            raise LCSRSC3TopologyError("topology controls contain an invalid record")
        occupancies = tuple(self.reference_source_occupancies)
        parsed_occupancies: list[tuple[PhysicalKey, int]] = []
        for item in occupancies:
            if not isinstance(item, tuple) or len(item) != 2:
                raise LCSRSC3TopologyError("reference source occupancy receipt is malformed")
            key = _key(item[0], field="reference_source_key")
            count = _exact_int(item[1], field="reference_source_occupancy")
            if count < 1:
                raise LCSRSC3TopologyError("reference source occupancy must be positive")
            parsed_occupancies.append((key, count))
        if tuple(sorted(parsed_occupancies)) != tuple(parsed_occupancies):
            raise LCSRSC3TopologyError("reference source occupancies are not sorted")
        if len({key for key, _ in parsed_occupancies}) != len(parsed_occupancies):
            raise LCSRSC3TopologyError("reference source occupancy keys are duplicated")
        expected_sources = {key for key, _ in parsed_occupancies}
        pair_sources = [pair.source_key for pair in pairs]
        control_sources = [control.source_key for control in controls]
        if pair_sources != sorted(pair_sources) or control_sources != sorted(control_sources):
            raise LCSRSC3TopologyError("topology records are not source-key ordered")
        if len(pair_sources) != len(set(pair_sources)) or len(control_sources) != len(set(control_sources)):
            raise LCSRSC3TopologyError("topology source keys are duplicated")
        if not set(pair_sources).issubset(expected_sources) or not set(control_sources).issubset(expected_sources):
            raise LCSRSC3TopologyError("topology record source is absent from occupancy receipt")
        if any(count != 2 for key, count in parsed_occupancies if key in pair_sources):
            raise LCSRSC3TopologyError("closure pair source is not exact-two occupancy")
        if any(count != 3 for key, count in parsed_occupancies if key in control_sources):
            raise LCSRSC3TopologyError("no-close source is not exact-three occupancy")
        _validate_records_against_capture(
            self.capture,
            pairs,
            controls,
            tuple(parsed_occupancies),
        )
        users: set[int] = set()
        for pair in pairs:
            if pair.world_id != self.capture.world_id or pair.phase != self.capture.phase or pair.anchor_id != self.capture.anchor_id:
                raise LCSRSC3TopologyError("closure pair provenance disagrees with capture")
            if any(user in users for user in pair.member_users):
                raise LCSRSC3TopologyError("closure pairs must be user-disjoint")
            users.update(pair.member_users)
        for control in controls:
            if control.world_id != self.capture.world_id or control.phase != self.capture.phase or control.anchor_id != self.capture.anchor_id:
                raise LCSRSC3TopologyError("no-close provenance disagrees with capture")
            if any(user in users for user in (*control.member_users, control.third_user)):
                raise LCSRSC3TopologyError(
                    "exact-two and occupancy-three controls must be user-disjoint"
                )
            users.update((*control.member_users, control.third_user))

        object.__setattr__(self, "pairs", pairs)
        object.__setattr__(self, "no_close_controls", controls)
        object.__setattr__(self, "reference_source_occupancies", tuple(parsed_occupancies))
        expected = _anchor_topology_digest(self)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3TopologyError("anchor topology digest disagrees with fields")
        object.__setattr__(self, "content_digest", expected)

    @property
    def world_id(self) -> int:
        return self.capture.world_id

    @property
    def phase(self) -> int:
        return self.capture.phase

    @property
    def anchor_id(self) -> str:
        return self.capture.anchor_id

    @property
    def pair_count(self) -> int:
        return len(self.pairs)

    @property
    def no_close_count(self) -> int:
        return len(self.no_close_controls)

    @property
    def class_counts(self) -> dict[str, int]:
        """Return a fresh receipt mapping for S/R/C/MASKED counts."""

        legal = int(np.count_nonzero(self.capture.action_mask))
        references = self.capture.users
        supported = 2 * self.pair_count
        control = legal - references - supported
        masked = self.capture.users * NUM_ACTIONS - legal
        return {"S": supported, "R": references, "C": control, "MASKED": masked}

    @property
    def retained_for_fitting(self) -> bool:
        counts = self.class_counts
        return self.pair_count > 0 and all(counts[name] > 0 for name in ("S", "R", "C"))

    @property
    def retention_status(self) -> str:
        if self.pair_count == 0:
            return LCSRS_RETENTION_NO_PAIRS
        if not self.retained_for_fitting:
            return LCSRS_RETENTION_EMPTY_CLASS
        return LCSRS_RETENTION_RETAINED

    def verify(self) -> str:
        expected = _anchor_topology_digest(self)
        if self.content_digest != expected:
            raise LCSRSC3TopologyError("anchor topology digest disagrees with fields")
        return expected

    def to_receipt(self) -> dict[str, object]:
        """Return only topology/coverage metadata, safe to serialize pre-teacher."""

        counts = self.class_counts
        return {
            "schema": LCSRS_C3_TOPOLOGY_SCHEMA,
            "world_id": self.world_id,
            "phase": self.phase,
            "anchor_id": self.anchor_id,
            "capture_sha256": self.capture.content_digest,
            "q12_source_state_sha256": (
                self.capture.q12_snapshot.source_state_digest
            ),
            "native_observation_event_sha256": (
                self.capture.q12_snapshot.native_observation_event_digest
            ),
            "q12_model_sha256": self.capture.q12_snapshot.model_digest,
            "detached_reference_actions": [
                int(value) for value in self.capture.reference_actions.tolist()
            ],
            "reference_source_occupancies": [
                {"key": [key[0], key[1]], "count": count}
                for key, count in self.reference_source_occupancies
            ],
            "pairs": [
                {
                    "pair_id": pair.pair_id,
                    "source_key": [pair.source_key[0], pair.source_key[1]],
                    "member_users": list(pair.member_users),
                    "designated_actions": list(pair.designated_actions),
                    "destination_keys": [
                        [key[0], key[1]] for key in pair.destination_keys
                    ],
                    "eligible_actions_by_member": [
                        list(actions) for actions in pair.eligible_actions_by_member
                    ],
                    "detached_q12_sha256": pair.detached_q12_digest,
                    "content_digest": pair.content_digest,
                }
                for pair in self.pairs
            ],
            "pair_ids": [pair.pair_id for pair in self.pairs],
            "no_close_controls": [
                {
                    "control_id": control.control_id,
                    "source_key": [control.source_key[0], control.source_key[1]],
                    "member_users": list(control.member_users),
                    "third_user": control.third_user,
                    "designated_actions": list(control.designated_actions),
                    "destination_keys": [
                        None if key is None else [key[0], key[1]]
                        for key in control.destination_keys
                    ],
                    "eligible_actions_by_member": [
                        list(actions)
                        for actions in control.eligible_actions_by_member
                    ],
                    "detached_q12_sha256": control.detached_q12_digest,
                    "content_digest": control.content_digest,
                }
                for control in self.no_close_controls
            ],
            "no_close_control_ids": [
                control.control_id for control in self.no_close_controls
            ],
            "pair_count": self.pair_count,
            "no_close_count": self.no_close_count,
            "class_counts": counts,
            "retained_for_fitting": self.retained_for_fitting,
            "retention_status": self.retention_status,
            "content_digest": self.content_digest,
        }


def _anchor_topology_digest(receipt: LCSRSC3AnchorTopologyReceipt) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-c3-anchor-topology-v1")
    digest.update(receipt.capture.content_digest.encode("ascii"))
    for key, count in receipt.reference_source_occupancies:
        _key_digest(digest, key)
        digest.update(struct.pack(">Q", count))
    for pair in receipt.pairs:
        digest.update(pair.content_digest.encode("ascii"))
    for control in receipt.no_close_controls:
        digest.update(control.content_digest.encode("ascii"))
    for name, count in receipt.class_counts.items():
        _digest_text(digest, name)
        digest.update(struct.pack(">q", count))
    _digest_text(digest, receipt.retention_status)
    return digest.hexdigest()


def _source_users(capture: LCSRSC3AnchorCapture) -> dict[PhysicalKey, tuple[int, ...]]:
    keys = np.asarray(capture.physical_keys)
    references = np.asarray(capture.reference_actions)
    by_source: dict[PhysicalKey, list[int]] = {}
    for user, action in enumerate(references.tolist()):
        source = (int(keys[user, action, 0]), int(keys[user, action, 1]))
        by_source.setdefault(source, []).append(user)
    return {
        source: tuple(sorted(users))
        for source, users in sorted(by_source.items(), key=lambda item: item[0])
    }


def _validate_records_against_capture(
    capture: LCSRSC3AnchorCapture,
    pairs: tuple[LCSRSC3ClosurePair, ...],
    controls: tuple[LCSRSC3NoCloseControl, ...],
    occupancies: tuple[tuple[PhysicalKey, int], ...],
) -> None:
    """Reject a hand-built receipt that is not the canonical enumeration."""

    source_users = _source_users(capture)
    expected_occupancies = tuple(
        (source, len(users)) for source, users in source_users.items()
    )
    if occupancies != expected_occupancies:
        raise LCSRSC3TopologyError(
            "reference source occupancy receipt disagrees with detached references"
        )
    q12_digest = _q12_digest(capture)
    expected_pairs: dict[PhysicalKey, tuple[tuple[int, int], tuple[int, int], tuple[PhysicalKey, PhysicalKey], tuple[tuple[int, ...], tuple[int, ...]]]] = {}
    expected_controls: dict[PhysicalKey, tuple[tuple[int, int], int, tuple[int | None, int | None], tuple[PhysicalKey | None, PhysicalKey | None], tuple[tuple[int, ...], tuple[int, ...]]]] = {}
    opening = np.asarray(capture.opening_feasibility)
    references = np.asarray(capture.reference_actions)
    for source, users in source_users.items():
        if len(users) == 2:
            if not all(bool(opening[user, references[user]]) for user in users):
                continue
            selected: list[tuple[int, ...]] = []
            actions: list[int | None] = []
            destinations: list[PhysicalKey | None] = []
            for user in users:
                eligible, action, destination = _select_destination(
                    capture,
                    user=user,
                    source_key=source,
                    member_users=users,
                )
                selected.append(eligible)
                actions.append(action)
                destinations.append(destination)
            if all(action is not None for action in actions):
                expected_pairs[source] = (
                    users,
                    (int(actions[0]), int(actions[1])),
                    (destinations[0], destinations[1]),  # type: ignore[arg-type]
                    (selected[0], selected[1]),
                )
        elif len(users) == 3:
            members = (users[0], users[1])
            selected = []
            actions = []
            destinations = []
            for user in members:
                eligible, action, destination = _select_destination(
                    capture,
                    user=user,
                    source_key=source,
                    member_users=members,
                )
                selected.append(eligible)
                actions.append(action)
                destinations.append(destination)
            expected_controls[source] = (
                members,
                users[2],
                (actions[0], actions[1]),
                (destinations[0], destinations[1]),
                (selected[0], selected[1]),
            )
    if set(pair.source_key for pair in pairs) != set(expected_pairs):
        raise LCSRSC3TopologyError("closure pair set is not the canonical exact-two set")
    if set(control.source_key for control in controls) != set(expected_controls):
        raise LCSRSC3TopologyError(
            "no-close control set is not the canonical occupancy-three set"
        )
    for pair in pairs:
        expected = expected_pairs[pair.source_key]
        if (
            pair.member_users != expected[0]
            or pair.designated_actions != expected[1]
            or pair.destination_keys != expected[2]
            or pair.eligible_actions_by_member != expected[3]
            or pair.detached_q12_digest != q12_digest
        ):
            raise LCSRSC3TopologyError("closure pair disagrees with canonical destination selection")
    for control in controls:
        expected = expected_controls[control.source_key]
        if (
            control.member_users != expected[0]
            or control.third_user != expected[1]
            or control.designated_actions != expected[2]
            or control.destination_keys != expected[3]
            or control.eligible_actions_by_member != expected[4]
            or control.detached_q12_digest != q12_digest
        ):
            raise LCSRSC3TopologyError(
                "no-close control disagrees with canonical destination selection"
            )


def enumerate_lcsrs_c3_anchor(
    capture: LCSRSC3AnchorCapture,
) -> LCSRSC3AnchorTopologyReceipt:
    """Enumerate every exact-two pair and every occupancy-three control."""

    if not isinstance(capture, LCSRSC3AnchorCapture):
        raise LCSRSC3TopologyError("capture must be LCSRSC3AnchorCapture")
    capture.verify()
    keys = np.asarray(capture.physical_keys)
    references = np.asarray(capture.reference_actions)
    by_source: dict[PhysicalKey, list[int]] = {}
    for user, action in enumerate(references.tolist()):
        source = (int(keys[user, action, 0]), int(keys[user, action, 1]))
        by_source.setdefault(source, []).append(user)

    source_items = tuple(
        (source, tuple(sorted(users)))
        for source, users in sorted(by_source.items(), key=lambda item: item[0])
    )
    source_receipt = tuple(
        (source, len(users)) for source, users in source_items
    )
    pairs: list[LCSRSC3ClosurePair] = []
    controls: list[LCSRSC3NoCloseControl] = []
    for source, source_users in source_items:
        if len(source_users) == 2:
            member_users = (source_users[0], source_users[1])
            if not all(
                bool(capture.opening_feasibility[user, references[user]])
                for user in member_users
            ):
                continue
            selected: list[tuple[int, ...]] = []
            actions: list[int | None] = []
            destinations: list[PhysicalKey | None] = []
            for user in member_users:
                eligible, action, destination = _select_destination(
                    capture,
                    user=user,
                    source_key=source,
                    member_users=member_users,
                )
                selected.append(eligible)
                actions.append(action)
                destinations.append(destination)
            if all(action is not None for action in actions):
                pair = LCSRSC3ClosurePair(
                    world_id=capture.world_id,
                    phase=capture.phase,
                    anchor_id=capture.anchor_id,
                    source_key=source,
                    member_users=member_users,
                    designated_actions=(int(actions[0]), int(actions[1])),
                    destination_keys=(destinations[0], destinations[1]),  # type: ignore[arg-type]
                    eligible_actions_by_member=(selected[0], selected[1]),
                    detached_q12_digest=_q12_digest(capture),
                )
                pairs.append(pair)
        elif len(source_users) == 3:
            member_users = (source_users[0], source_users[1])
            selected = []
            actions = []
            destinations = []
            for user in member_users:
                eligible, action, destination = _select_destination(
                    capture,
                    user=user,
                    source_key=source,
                    member_users=member_users,
                )
                selected.append(eligible)
                actions.append(action)
                destinations.append(destination)
            controls.append(
                LCSRSC3NoCloseControl(
                    world_id=capture.world_id,
                    phase=capture.phase,
                    anchor_id=capture.anchor_id,
                    source_key=source,
                    member_users=member_users,
                    third_user=source_users[2],
                    designated_actions=(actions[0], actions[1]),
                    destination_keys=(destinations[0], destinations[1]),
                    eligible_actions_by_member=(selected[0], selected[1]),
                    detached_q12_digest=_q12_digest(capture),
                )
            )

    pairs.sort(key=lambda pair: (pair.source_key, pair.member_users))
    controls.sort(key=lambda control: (control.source_key, control.member_users))
    return LCSRSC3AnchorTopologyReceipt(
        capture=capture,
        pairs=tuple(pairs),
        no_close_controls=tuple(controls),
        reference_source_occupancies=source_receipt,
    )


def _q12_digest(capture: LCSRSC3AnchorCapture) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-detached-q12-v1")
    _digest_array(digest, "detached_q12", capture.detached_q12)
    _digest_array(digest, "reference_actions", np.asarray(capture.reference_actions))
    _digest_array(digest, "action_mask", capture.action_mask)
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSC3WorldTopologyReceipt:
    """Complete phase-1..9 topology receipt for one fresh world."""

    world_id: int
    anchors: tuple[LCSRSC3AnchorTopologyReceipt, ...]
    content_digest: str = ""

    def __post_init__(self) -> None:
        world = _exact_int(self.world_id, field="world_id")
        anchors = tuple(self.anchors)
        if tuple(anchor.phase for anchor in anchors) != LCSRS_NATIVE_PHASES:
            raise LCSRSC3TopologyError(
                "a world must enumerate exactly native phases t=1..9 in order"
            )
        if any(anchor.world_id != world for anchor in anchors):
            raise LCSRSC3TopologyError("world anchors disagree on world_id")
        if len({anchor.anchor_id for anchor in anchors}) != len(anchors):
            raise LCSRSC3TopologyError("world anchor identifiers must be unique")
        expected = _world_digest(world, anchors)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3TopologyError("world topology digest disagrees with anchors")
        object.__setattr__(self, "world_id", world)
        object.__setattr__(self, "anchors", anchors)
        object.__setattr__(self, "content_digest", expected)

    @property
    def pair_count(self) -> int:
        return sum(anchor.pair_count for anchor in self.anchors)

    @property
    def has_zero_closure_pairs(self) -> bool:
        return self.pair_count == 0

    def verify(self) -> str:
        expected = _world_digest(self.world_id, self.anchors)
        if self.content_digest != expected:
            raise LCSRSC3TopologyError("world topology digest disagrees with anchors")
        return expected


def _world_digest(
    world_id: int, anchors: tuple[LCSRSC3AnchorTopologyReceipt, ...]
) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-c3-world-topology-v1")
    digest.update(struct.pack(">Q", world_id))
    for anchor in anchors:
        digest.update(anchor.content_digest.encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSC3ScheduleTopologyReceipt:
    """Deterministically ordered world receipts and the pair-count gate."""

    worlds: tuple[LCSRSC3WorldTopologyReceipt, ...]
    minimum_pairs: int = LCSRS_MIN_CLOSURE_PAIRS
    status: str = LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS
    content_digest: str = ""

    def __post_init__(self) -> None:
        worlds = tuple(self.worlds)
        if not worlds:
            raise LCSRSC3TopologyError("schedule needs at least one world")
        minimum = _exact_int(self.minimum_pairs, field="minimum_pairs")
        if minimum != LCSRS_MIN_CLOSURE_PAIRS:
            raise LCSRSC3TopologyError(
                "minimum_pairs is frozen at 24 for the V0.23 gate"
            )
        if tuple(world.world_id for world in worlds) != tuple(sorted(world.world_id for world in worlds)):
            raise LCSRSC3TopologyError("world receipts are not deterministically ordered")
        if len({world.world_id for world in worlds}) != len(worlds):
            raise LCSRSC3TopologyError("world identifiers must be unique")
        expected_status = (
            LCSRS_TOPOLOGY_OK
            if self.pair_count >= minimum and all(not world.has_zero_closure_pairs for world in worlds)
            else LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS
        )
        if self.status != expected_status:
            raise LCSRSC3TopologyError("schedule status disagrees with topology coverage")
        expected = _schedule_digest(worlds, minimum, expected_status)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3TopologyError("schedule topology digest disagrees with worlds")
        object.__setattr__(self, "worlds", worlds)
        object.__setattr__(self, "minimum_pairs", minimum)
        object.__setattr__(self, "status", expected_status)
        object.__setattr__(self, "content_digest", expected)

    @property
    def pair_count(self) -> int:
        return sum(world.pair_count for world in self.worlds)

    @property
    def retained_anchors(self) -> tuple[LCSRSC3AnchorTopologyReceipt, ...]:
        return tuple(
            anchor
            for world in self.worlds
            for anchor in world.anchors
            if anchor.retained_for_fitting
        )

    @property
    def coverage_anchors(self) -> tuple[LCSRSC3AnchorTopologyReceipt, ...]:
        return tuple(anchor for world in self.worlds for anchor in world.anchors)

    @property
    def meets_pair_gate(self) -> bool:
        return self.status == LCSRS_TOPOLOGY_OK

    def verify(self) -> str:
        expected = _schedule_digest(self.worlds, self.minimum_pairs, self.status)
        if self.content_digest != expected:
            raise LCSRSC3TopologyError("schedule topology digest disagrees with worlds")
        return expected

    def to_receipt(self) -> dict[str, object]:
        return {
            "schema": LCSRS_C3_TOPOLOGY_SCHEMA,
            "world_ids": [world.world_id for world in self.worlds],
            "minimum_pairs": self.minimum_pairs,
            "pair_count": self.pair_count,
            "zero_pair_world_ids": [
                world.world_id for world in self.worlds if world.has_zero_closure_pairs
            ],
            "retained_anchor_ids": [
                [anchor.world_id, anchor.phase, anchor.anchor_id]
                for anchor in self.retained_anchors
            ],
            "status": self.status,
            "content_digest": self.content_digest,
        }


def _schedule_digest(
    worlds: tuple[LCSRSC3WorldTopologyReceipt, ...],
    minimum_pairs: int,
    status: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-c3-schedule-topology-v1")
    digest.update(struct.pack(">Q", minimum_pairs))
    _digest_text(digest, status)
    for world in worlds:
        digest.update(world.content_digest.encode("ascii"))
    return digest.hexdigest()


def enumerate_lcsrs_c3_world(
    captures: Sequence[LCSRSC3AnchorCapture],
) -> LCSRSC3WorldTopologyReceipt:
    """Enumerate all nine noninitial anchors for one world, in phase order."""

    try:
        rows = tuple(captures)
    except TypeError as error:
        raise LCSRSC3TopologyError("captures must be a sequence") from error
    if not rows:
        raise LCSRSC3TopologyError("a world needs native phases 1..9")
    if any(not isinstance(row, LCSRSC3AnchorCapture) for row in rows):
        raise LCSRSC3TopologyError("world captures contain an invalid anchor")
    ordered = tuple(sorted(rows, key=lambda row: row.phase))
    if tuple(row.phase for row in ordered) != LCSRS_NATIVE_PHASES:
        raise LCSRSC3TopologyError(
            "a world must provide exactly one capture for each phase 1..9"
        )
    world_ids = {row.world_id for row in ordered}
    if len(world_ids) != 1:
        raise LCSRSC3TopologyError("world captures must share one world_id")
    anchors = tuple(enumerate_lcsrs_c3_anchor(row) for row in ordered)
    return LCSRSC3WorldTopologyReceipt(world_id=ordered[0].world_id, anchors=anchors)


def enumerate_lcsrs_c3_schedule(
    worlds: Sequence[Sequence[LCSRSC3AnchorCapture]] | Sequence[LCSRSC3AnchorCapture],
) -> LCSRSC3ScheduleTopologyReceipt:
    """Enumerate ordered worlds and emit the pre-profile pair-count status.

    Both a flat sequence of captures and a sequence of per-world sequences are
    accepted.  Flat captures are grouped by ``world_id`` before the strict
    nine-phase world check.  Grouping and every returned record are sorted by
    world id, phase, source key, and user id.
    """

    try:
        rows = tuple(worlds)
    except TypeError as error:
        raise LCSRSC3TopologyError("worlds must be a sequence") from error
    if not rows:
        raise LCSRSC3TopologyError("schedule needs at least one world")
    if all(isinstance(row, LCSRSC3AnchorCapture) for row in rows):
        grouped: dict[int, list[LCSRSC3AnchorCapture]] = {}
        for row in rows:  # type: ignore[union-attr]
            grouped.setdefault(row.world_id, []).append(row)
        world_rows = tuple(grouped[world_id] for world_id in sorted(grouped))
    else:
        if any(isinstance(row, LCSRSC3AnchorCapture) for row in rows):
            raise LCSRSC3TopologyError("schedule cannot mix flat and grouped captures")
        world_rows = tuple(rows)  # type: ignore[assignment]
    receipts = tuple(
        sorted(
            (enumerate_lcsrs_c3_world(group) for group in world_rows),
            key=lambda receipt: receipt.world_id,
        )
    )
    minimum = LCSRS_MIN_CLOSURE_PAIRS
    pair_count = sum(receipt.pair_count for receipt in receipts)
    status = (
        LCSRS_TOPOLOGY_OK
        if pair_count >= minimum and all(not receipt.has_zero_closure_pairs for receipt in receipts)
        else LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS
    )
    return LCSRSC3ScheduleTopologyReceipt(
        worlds=receipts,
        minimum_pairs=minimum,
        status=status,
    )


# Explicit aliases make the seam discoverable beside the existing encoder and
# dataset names without creating a second implementation.
LCSRSAnchorCapture = LCSRSC3AnchorCapture
LCSRSClosurePair = LCSRSC3ClosurePair
LCSRSNoCloseControl = LCSRSC3NoCloseControl
LCSRSAnchorTopologyReceipt = LCSRSC3AnchorTopologyReceipt
LCSRSWorldTopologyReceipt = LCSRSC3WorldTopologyReceipt
LCSRSScheduleTopologyReceipt = LCSRSC3ScheduleTopologyReceipt


__all__ = [
    "LCSRS_C3_TOPOLOGY_SCHEMA",
    "LCSRS_DECISION_PHASES",
    "LCSRS_NATIVE_PHASES",
    "LCSRS_MIN_CLOSURE_PAIRS",
    "LCSRS_TOPOLOGY_OK",
    "LCSRS_TOPOLOGY_INSUFFICIENT_PAIRS",
    "LCSRS_RETENTION_RETAINED",
    "LCSRS_RETENTION_NO_PAIRS",
    "LCSRS_RETENTION_EMPTY_CLASS",
    "PhysicalKey",
    "LCSRSC3TopologyError",
    "LCSRSC3AnchorCapture",
    "LCSRSC3ClosurePair",
    "LCSRSC3NoCloseControl",
    "LCSRSC3AnchorTopologyReceipt",
    "LCSRSC3WorldTopologyReceipt",
    "LCSRSC3ScheduleTopologyReceipt",
    "LCSRSAnchorCapture",
    "LCSRSClosurePair",
    "LCSRSNoCloseControl",
    "LCSRSAnchorTopologyReceipt",
    "LCSRSWorldTopologyReceipt",
    "LCSRSScheduleTopologyReceipt",
    "enumerate_lcsrs_c3_anchor",
    "enumerate_lcsrs_c3_world",
    "enumerate_lcsrs_c3_schedule",
]
