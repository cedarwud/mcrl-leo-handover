"""Outcome-blind, support-complete V0.4 C2 sibling schedules.

This module is the data-only boundary for the one authorised C2 repair probe.
For one sealed ``(world, anchor, focal-user)`` intervention, Main is the
common reference and *every* legal non-Main action is represented by exactly
one temporal sibling row.  The module deliberately does not import the
simulator, the temporal fork backend, a trainer, or any outcome calculator.

The old V0.3 E1 schedule is intentionally not adapted here.  Its identity is
one selected candidate per focal state, so extending it in place would make a
complete sibling census look like duplicate interventions.  V0.4 has a new
schema and a new identity contract instead.

Rows with a source failure or support expiry remain in the sealed schedule;
they are never silently filtered into a positive-only source set.  A later
capture layer may attach a temporal outcome to a row, but that is outside this
pre-outcome contract.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


# ---------------------------------------------------------------------------
# Versioned public contract
# ---------------------------------------------------------------------------

C2_V04_SUPPORT_COMPLETE_SOURCE_RULE = "c2-support-complete-legal-nonmain-v1"
"""The only source rule admitted by this V0.4 sibling census."""

# Short aliases make the rule easy to import from source runners while keeping
# the fully descriptive name available for authority documents.
C2_V04_SOURCE_RULE = C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
C2_SUPPORT_COMPLETE_SOURCE_RULE = C2_V04_SUPPORT_COMPLETE_SOURCE_RULE

C2_V04_ANCHOR_SCHEDULE_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-anchor-schedule-v1"
)
C2_V04_SIBLING_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-sibling-row-v1"
)
C2_V04_SCHEDULE_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-sibling-schedule-v1"
)
C2_V04_SCHEDULE_VERSION = 1

C2_V04_ROW_READY = "ready"
C2_V04_ROW_FAILURE = "row-failure"
C2_V04_ROW_SUPPORT_EXPIRED = "support-expired"
C2_V04_ROW_STATUSES = frozenset(
    {C2_V04_ROW_READY, C2_V04_ROW_FAILURE, C2_V04_ROW_SUPPORT_EXPIRED}
)

PhysicalKey = tuple[int, int]
InterventionKey = tuple[int, str, str, int]
SiblingKey = tuple[int, str, str, int, PhysicalKey]


class C2V04SiblingScheduleContractError(MCRLContractError):
    """A proposed V0.4 C2 sibling schedule violates its sealed contract."""


# A few callers use the shorter historical spelling.  Keep this as an alias,
# not a second exception hierarchy.
C2V04ScheduleContractError = C2V04SiblingScheduleContractError


def _canonical_json_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C2V04SiblingScheduleContractError(
            "schedule payload is not canonical JSON or contains a non-finite value"
        ) from error


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _action(value: object, *, field: str) -> int:
    action = _exact_nonnegative_int(value, field=field)
    if action >= NUM_ACTIONS:
        raise C2V04SiblingScheduleContractError(
            f"{field} must lie in the current action space [0, {NUM_ACTIONS})"
        )
    return action


def _physical_key(value: object, *, field: str) -> PhysicalKey:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a two-integer physical key"
        )
    return (
        _exact_nonnegative_int(value[0], field=f"{field}[0]"),
        _exact_nonnegative_int(value[1], field=f"{field}[1]"),
    )


def _bool_tuple(value: object, *, field: str) -> tuple[bool, ...]:
    if not isinstance(value, (tuple, list)):
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a Boolean sequence"
        )
    result = tuple(value)
    if any(type(item) is not bool for item in result):
        raise C2V04SiblingScheduleContractError(
            f"{field} must contain only exact Boolean values"
        )
    if len(result) != NUM_ACTIONS:
        raise C2V04SiblingScheduleContractError(
            f"{field} must have exactly {NUM_ACTIONS} actions"
        )
    return result


def _physical_keys(value: object, *, field: str) -> tuple[PhysicalKey, ...]:
    if not isinstance(value, (tuple, list)):
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a physical-key sequence"
        )
    return tuple(
        _physical_key(item, field=f"{field}[{index}]")
        for index, item in enumerate(value)
    )


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a nonempty trimmed string"
        )
    return value


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise C2V04SiblingScheduleContractError(
            f"{field} must be a finite numeric value"
        )
    result = float(value)
    if not math.isfinite(result):
        raise C2V04SiblingScheduleContractError(f"{field} must be finite")
    return result


def _row_status(value: object) -> str:
    """Validate and canonicalise pre-outcome row status.

    The hyphenated spellings are the V0.4 wire values.  The underscore forms
    are accepted only as a compatibility convenience at the Python boundary
    and are normalised before they can enter a digest or a serialized file.
    """

    if not isinstance(value, str):
        raise C2V04SiblingScheduleContractError(
            "row_status must be a nonempty status string"
        )
    aliases = {
        "row_failure": C2_V04_ROW_FAILURE,
        "support_expired": C2_V04_ROW_SUPPORT_EXPIRED,
    }
    result = aliases.get(value, value)
    if result not in C2_V04_ROW_STATUSES:
        raise C2V04SiblingScheduleContractError(
            "row_status must be ready, row-failure, or support-expired"
        )
    return result


def _failure_code(value: object, *, status: str) -> str | None:
    if value is None:
        return None
    result = _text(value, field="failure_code")
    if status == C2_V04_ROW_READY:
        raise C2V04SiblingScheduleContractError(
            "ready rows cannot carry a failure_code"
        )
    return result


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise C2V04SiblingScheduleContractError(f"{field} must be a JSON object")
    return value


def _reject_unknown_fields(
    payload: Mapping[str, object], *, allowed: frozenset[str], field: str
) -> None:
    unknown = sorted(set(payload) - set(allowed))
    if unknown:
        raise C2V04SiblingScheduleContractError(
            f"{field} contains unsupported field(s): {', '.join(unknown)}"
        )


def _anchor_payload(anchor: "C2V04AnchorSchedule") -> dict[str, object]:
    """Canonical payload for the per-intervention anchor digest."""

    return {
        "schema": C2_V04_ANCHOR_SCHEDULE_SCHEMA,
        "source_rule": anchor.source_rule,
        "source_seed": anchor.source_seed,
        "anchor_step": anchor.anchor_step,
        "world_anchor_sha256": anchor.world_anchor_sha256,
        "anchor_sha256": anchor.anchor_sha256,
        "focal_user": anchor.focal_user,
        "reference_action": anchor.reference_action,
        "reference_physical_key": list(anchor.reference_physical_key),
        "incumbent_physical_key": list(anchor.incumbent_physical_key),
        "common_random_field_sha256": anchor.common_random_field_sha256,
        "predecision_heuristic_scores": list(anchor.predecision_heuristic_scores),
        "legal_action_mask": list(anchor.legal_action_mask),
        "candidate_actions": list(anchor.candidate_actions),
        "candidate_physical_keys": [
            list(value) for value in anchor.candidate_physical_keys
        ],
        "checkpoint_sha256": anchor.checkpoint_sha256,
        "source_manifest_sha256": anchor.source_manifest_sha256,
        "policy_sha256": anchor.policy_sha256,
        "evaluation_seed": anchor.evaluation_seed,
    }


def canonical_anchor_schedule_sha256(anchor: "C2V04AnchorSchedule") -> str:
    """Return the digest of the complete, outcome-free anchor census."""

    return _sha256_bytes(_canonical_json_bytes(_anchor_payload(anchor)))


def _anchor_shared_payload(anchor: "C2V04AnchorSchedule") -> dict[str, object]:
    """Fields duplicated onto rows and checked for exact agreement."""

    return _anchor_payload(anchor) | {
        "anchor_schedule_sha256": anchor.anchor_schedule_sha256,
    }


@dataclass(frozen=True)
class C2V04AnchorSchedule:
    """One sealed focal intervention and its complete legal action census.

    ``candidate_actions`` and ``candidate_physical_keys`` are paired and
    sorted by ``(physical_key, action)``.  They are exactly the legal actions
    other than Main, as described by ``legal_action_mask``.  No temporal
    branch is executed while this object is being constructed.
    """

    source_seed: int
    anchor_step: int
    world_anchor_sha256: str
    anchor_sha256: str
    focal_user: int
    reference_action: int
    reference_physical_key: PhysicalKey
    incumbent_physical_key: PhysicalKey
    common_random_field_sha256: str
    predecision_heuristic_scores: tuple[float, ...]
    legal_action_mask: tuple[bool, ...]
    candidate_actions: tuple[int, ...]
    candidate_physical_keys: tuple[PhysicalKey, ...]
    checkpoint_sha256: str
    source_manifest_sha256: str
    policy_sha256: str
    evaluation_seed: int
    source_rule: str = C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
    anchor_schedule_sha256: str | None = None

    def __post_init__(self) -> None:
        source_seed = _exact_nonnegative_int(self.source_seed, field="source_seed")
        object.__setattr__(self, "source_seed", source_seed)
        anchor_step = _exact_nonnegative_int(self.anchor_step, field="anchor_step")
        if anchor_step < 1:
            raise C2V04SiblingScheduleContractError(
                "anchor_step must be at least one for a temporal departure anchor"
            )
        object.__setattr__(self, "anchor_step", anchor_step)
        for field in ("world_anchor_sha256", "anchor_sha256"):
            object.__setattr__(self, field, _digest(getattr(self, field), field=field))
        object.__setattr__(
            self,
            "focal_user",
            _exact_nonnegative_int(self.focal_user, field="focal_user"),
        )
        reference_action = _action(self.reference_action, field="reference_action")
        object.__setattr__(self, "reference_action", reference_action)
        reference_key = _physical_key(
            self.reference_physical_key, field="reference_physical_key"
        )
        object.__setattr__(self, "reference_physical_key", reference_key)
        incumbent_key = _physical_key(
            self.incumbent_physical_key, field="incumbent_physical_key"
        )
        object.__setattr__(self, "incumbent_physical_key", incumbent_key)
        object.__setattr__(
            self,
            "common_random_field_sha256",
            _digest(
                self.common_random_field_sha256,
                field="common_random_field_sha256",
            ),
        )
        scores = tuple(
            _finite(value, field=f"predecision_heuristic_scores[{index}]")
            for index, value in enumerate(self.predecision_heuristic_scores)
        )
        object.__setattr__(self, "predecision_heuristic_scores", scores)
        mask = _bool_tuple(self.legal_action_mask, field="legal_action_mask")
        object.__setattr__(self, "legal_action_mask", mask)
        if not mask[reference_action]:
            raise C2V04SiblingScheduleContractError(
                "Main reference action is not legal under legal_action_mask"
            )
        actions = tuple(
            _action(value, field=f"candidate_actions[{index}]")
            for index, value in enumerate(self.candidate_actions)
        )
        keys = _physical_keys(
            self.candidate_physical_keys, field="candidate_physical_keys"
        )
        if len(actions) != len(keys):
            raise C2V04SiblingScheduleContractError(
                "candidate actions and physical keys must have equal length"
            )
        if len(scores) != len(actions):
            raise C2V04SiblingScheduleContractError(
                "predecision heuristic scores must align with candidate census"
            )
        if len(set(actions)) != len(actions):
            raise C2V04SiblingScheduleContractError(
                "candidate actions contain duplicates"
            )
        if len(set(keys)) != len(keys):
            raise C2V04SiblingScheduleContractError(
                "candidate physical keys contain duplicates"
            )
        if reference_action in actions:
            raise C2V04SiblingScheduleContractError(
                "Main reference action cannot be a non-Main candidate"
            )
        if reference_key in keys:
            raise C2V04SiblingScheduleContractError(
                "Main reference physical key cannot be a candidate"
            )
        pairs = tuple(zip(keys, actions))
        if pairs != tuple(sorted(pairs)):
            raise C2V04SiblingScheduleContractError(
                "candidate physical keys/actions must be canonically sorted"
            )
        expected_actions = tuple(
            action
            for action, legal in enumerate(mask)
            if legal and action != reference_action
        )
        if set(actions) != set(expected_actions):
            missing = sorted(set(expected_actions) - set(actions))
            extra = sorted(set(actions) - set(expected_actions))
            raise C2V04SiblingScheduleContractError(
                "candidate census disagrees with legal_action_mask "
                f"(missing={missing}, extra={extra})"
            )
        object.__setattr__(self, "candidate_actions", actions)
        object.__setattr__(self, "candidate_physical_keys", keys)
        for field in (
            "checkpoint_sha256",
            "source_manifest_sha256",
            "policy_sha256",
        ):
            object.__setattr__(self, field, _digest(getattr(self, field), field=field))
        object.__setattr__(
            self,
            "evaluation_seed",
            _exact_nonnegative_int(self.evaluation_seed, field="evaluation_seed"),
        )
        if self.source_rule != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE:
            raise C2V04SiblingScheduleContractError(
                "source_rule is stale or unsupported for V0.4 C2"
            )
        actual = canonical_anchor_schedule_sha256(self)
        if self.anchor_schedule_sha256 is not None:
            supplied = _digest(
                self.anchor_schedule_sha256, field="anchor_schedule_sha256"
            )
            if supplied != actual:
                raise C2V04SiblingScheduleContractError(
                    "anchor_schedule_sha256 disagrees with sealed anchor census"
                )
        object.__setattr__(self, "anchor_schedule_sha256", actual)

    @property
    def intervention_key(self) -> InterventionKey:
        """The versioned identity of one sealed focal intervention."""

        return (
            self.source_seed,
            self.world_anchor_sha256,
            self.anchor_sha256,
            self.focal_user,
        )

    @property
    def candidate_pairs(self) -> tuple[tuple[PhysicalKey, int], ...]:
        return tuple(zip(self.candidate_physical_keys, self.candidate_actions))

    def verify(self) -> str:
        """Re-run structural checks and return the anchor digest."""

        rebuilt = type(self)(
            source_seed=self.source_seed,
            anchor_step=self.anchor_step,
            world_anchor_sha256=self.world_anchor_sha256,
            anchor_sha256=self.anchor_sha256,
            focal_user=self.focal_user,
            reference_action=self.reference_action,
            reference_physical_key=self.reference_physical_key,
            incumbent_physical_key=self.incumbent_physical_key,
            common_random_field_sha256=self.common_random_field_sha256,
            predecision_heuristic_scores=self.predecision_heuristic_scores,
            legal_action_mask=self.legal_action_mask,
            candidate_actions=self.candidate_actions,
            candidate_physical_keys=self.candidate_physical_keys,
            checkpoint_sha256=self.checkpoint_sha256,
            source_manifest_sha256=self.source_manifest_sha256,
            policy_sha256=self.policy_sha256,
            evaluation_seed=self.evaluation_seed,
            source_rule=self.source_rule,
            anchor_schedule_sha256=self.anchor_schedule_sha256,
        )
        return rebuilt.anchor_schedule_sha256

    def to_mapping(self) -> dict[str, object]:
        return _anchor_payload(self) | {
            "anchor_schedule_sha256": self.anchor_schedule_sha256
        }

    @classmethod
    def from_mapping(cls, value: object) -> "C2V04AnchorSchedule":
        payload = _mapping(value, field="anchor")
        allowed = frozenset(
            {
                "schema",
                "source_rule",
                "source_seed",
                "anchor_step",
                "world_anchor_sha256",
                "anchor_sha256",
                "focal_user",
                "reference_action",
                "reference_physical_key",
                "incumbent_physical_key",
                "common_random_field_sha256",
                "predecision_heuristic_scores",
                "legal_action_mask",
                "candidate_actions",
                "candidate_physical_keys",
                "checkpoint_sha256",
                "source_manifest_sha256",
                "policy_sha256",
                "evaluation_seed",
                "anchor_schedule_sha256",
            }
        )
        _reject_unknown_fields(payload, allowed=allowed, field="anchor")
        required = allowed
        missing = sorted(required - set(payload))
        if missing:
            raise C2V04SiblingScheduleContractError(
                f"anchor is missing required field(s): {', '.join(missing)}"
            )
        if payload["schema"] != C2_V04_ANCHOR_SCHEDULE_SCHEMA:
            raise C2V04SiblingScheduleContractError(
                "anchor schema is stale or unsupported"
            )
        return cls(
            source_seed=payload["source_seed"],  # type: ignore[arg-type]
            anchor_step=payload["anchor_step"],  # type: ignore[arg-type]
            world_anchor_sha256=payload["world_anchor_sha256"],  # type: ignore[arg-type]
            anchor_sha256=payload["anchor_sha256"],  # type: ignore[arg-type]
            focal_user=payload["focal_user"],  # type: ignore[arg-type]
            reference_action=payload["reference_action"],  # type: ignore[arg-type]
            reference_physical_key=payload["reference_physical_key"],  # type: ignore[arg-type]
            incumbent_physical_key=payload["incumbent_physical_key"],  # type: ignore[arg-type]
            common_random_field_sha256=payload["common_random_field_sha256"],  # type: ignore[arg-type]
            predecision_heuristic_scores=tuple(payload["predecision_heuristic_scores"]),  # type: ignore[arg-type]
            legal_action_mask=tuple(payload["legal_action_mask"]),  # type: ignore[arg-type]
            candidate_actions=tuple(payload["candidate_actions"]),  # type: ignore[arg-type]
            candidate_physical_keys=tuple(
                tuple(item) for item in payload["candidate_physical_keys"]  # type: ignore[union-attr]
            ),
            checkpoint_sha256=payload["checkpoint_sha256"],  # type: ignore[arg-type]
            source_manifest_sha256=payload["source_manifest_sha256"],  # type: ignore[arg-type]
            policy_sha256=payload["policy_sha256"],  # type: ignore[arg-type]
            evaluation_seed=payload["evaluation_seed"],  # type: ignore[arg-type]
            source_rule=payload["source_rule"],  # type: ignore[arg-type]
            anchor_schedule_sha256=payload["anchor_schedule_sha256"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class C2V04SiblingRow:
    """One candidate sibling, retaining pre-outcome source status."""

    source_seed: int
    anchor_step: int
    world_anchor_sha256: str
    anchor_sha256: str
    focal_user: int
    anchor_schedule_sha256: str
    reference_action: int
    reference_physical_key: PhysicalKey
    incumbent_physical_key: PhysicalKey
    common_random_field_sha256: str
    predecision_heuristic_scores: tuple[float, ...]
    legal_action_mask: tuple[bool, ...]
    candidate_actions: tuple[int, ...]
    candidate_physical_keys: tuple[PhysicalKey, ...]
    candidate_action: int
    candidate_physical_key: PhysicalKey
    checkpoint_sha256: str
    source_manifest_sha256: str
    policy_sha256: str
    evaluation_seed: int
    row_status: str = C2_V04_ROW_READY
    failure_code: str | None = None
    source_rule: str = C2_V04_SUPPORT_COMPLETE_SOURCE_RULE

    @classmethod
    def from_anchor(
        cls,
        anchor: C2V04AnchorSchedule,
        *,
        candidate_action: int,
        candidate_physical_key: PhysicalKey,
        row_status: str = C2_V04_ROW_READY,
        failure_code: str | None = None,
    ) -> "C2V04SiblingRow":
        anchor.verify()
        return cls(
            source_seed=anchor.source_seed,
            anchor_step=anchor.anchor_step,
            world_anchor_sha256=anchor.world_anchor_sha256,
            anchor_sha256=anchor.anchor_sha256,
            focal_user=anchor.focal_user,
            anchor_schedule_sha256=anchor.anchor_schedule_sha256,
            reference_action=anchor.reference_action,
            reference_physical_key=anchor.reference_physical_key,
            incumbent_physical_key=anchor.incumbent_physical_key,
            common_random_field_sha256=anchor.common_random_field_sha256,
            predecision_heuristic_scores=anchor.predecision_heuristic_scores,
            legal_action_mask=anchor.legal_action_mask,
            candidate_actions=anchor.candidate_actions,
            candidate_physical_keys=anchor.candidate_physical_keys,
            candidate_action=candidate_action,
            candidate_physical_key=candidate_physical_key,
            checkpoint_sha256=anchor.checkpoint_sha256,
            source_manifest_sha256=anchor.source_manifest_sha256,
            policy_sha256=anchor.policy_sha256,
            evaluation_seed=anchor.evaluation_seed,
            row_status=row_status,
            failure_code=failure_code,
            source_rule=anchor.source_rule,
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_seed", _exact_nonnegative_int(self.source_seed, field="source_seed"))
        anchor_step = _exact_nonnegative_int(self.anchor_step, field="anchor_step")
        if anchor_step < 1:
            raise C2V04SiblingScheduleContractError(
                "anchor_step must be at least one for a temporal departure anchor"
            )
        object.__setattr__(self, "anchor_step", anchor_step)
        for field in ("world_anchor_sha256", "anchor_sha256", "anchor_schedule_sha256"):
            object.__setattr__(self, field, _digest(getattr(self, field), field=field))
        object.__setattr__(self, "focal_user", _exact_nonnegative_int(self.focal_user, field="focal_user"))
        object.__setattr__(self, "reference_action", _action(self.reference_action, field="reference_action"))
        object.__setattr__(self, "candidate_action", _action(self.candidate_action, field="candidate_action"))
        object.__setattr__(self, "reference_physical_key", _physical_key(self.reference_physical_key, field="reference_physical_key"))
        object.__setattr__(self, "candidate_physical_key", _physical_key(self.candidate_physical_key, field="candidate_physical_key"))
        object.__setattr__(self, "incumbent_physical_key", _physical_key(self.incumbent_physical_key, field="incumbent_physical_key"))
        object.__setattr__(
            self,
            "common_random_field_sha256",
            _digest(self.common_random_field_sha256, field="common_random_field_sha256"),
        )
        scores = tuple(
            _finite(value, field=f"predecision_heuristic_scores[{index}]")
            for index, value in enumerate(self.predecision_heuristic_scores)
        )
        object.__setattr__(self, "predecision_heuristic_scores", scores)
        object.__setattr__(self, "legal_action_mask", _bool_tuple(self.legal_action_mask, field="legal_action_mask"))
        actions = tuple(
            _action(value, field=f"candidate_actions[{index}]")
            for index, value in enumerate(self.candidate_actions)
        )
        keys = _physical_keys(
            self.candidate_physical_keys, field="candidate_physical_keys"
        )
        if len(actions) != len(keys):
            raise C2V04SiblingScheduleContractError(
                "candidate actions and physical keys must have equal length"
            )
        if len(scores) != len(actions):
            raise C2V04SiblingScheduleContractError(
                "predecision heuristic scores must align with candidate census"
            )
        if len(set(actions)) != len(actions):
            raise C2V04SiblingScheduleContractError(
                "candidate actions contain duplicates"
            )
        if len(set(keys)) != len(keys):
            raise C2V04SiblingScheduleContractError(
                "candidate physical keys contain duplicates"
            )
        if tuple(zip(keys, actions)) != tuple(sorted(zip(keys, actions))):
            raise C2V04SiblingScheduleContractError(
                "candidate physical keys/actions must be canonically sorted"
            )
        expected_actions = tuple(
            action
            for action, legal in enumerate(self.legal_action_mask)
            if legal and action != self.reference_action
        )
        if set(actions) != set(expected_actions):
            raise C2V04SiblingScheduleContractError(
                "candidate census disagrees with legal_action_mask"
            )
        if self.candidate_action not in actions:
            raise C2V04SiblingScheduleContractError(
                "candidate action is missing from complete sibling census"
            )
        if self.candidate_physical_key not in keys:
            raise C2V04SiblingScheduleContractError(
                "candidate physical key is missing from complete sibling census"
            )
        object.__setattr__(self, "candidate_actions", actions)
        object.__setattr__(self, "candidate_physical_keys", keys)
        for field in ("checkpoint_sha256", "source_manifest_sha256", "policy_sha256"):
            object.__setattr__(self, field, _digest(getattr(self, field), field=field))
        object.__setattr__(self, "evaluation_seed", _exact_nonnegative_int(self.evaluation_seed, field="evaluation_seed"))
        if self.source_rule != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE:
            raise C2V04SiblingScheduleContractError("source_rule is stale or unsupported for V0.4 C2")
        if not self.legal_action_mask[self.reference_action]:
            raise C2V04SiblingScheduleContractError("reference action is illegal under legal_action_mask")
        if not self.legal_action_mask[self.candidate_action]:
            raise C2V04SiblingScheduleContractError("candidate action is illegal under legal_action_mask")
        if self.candidate_action == self.reference_action:
            raise C2V04SiblingScheduleContractError("Main reference action cannot be a sibling candidate")
        if self.candidate_physical_key == self.reference_physical_key:
            raise C2V04SiblingScheduleContractError("Main reference physical key cannot be a sibling candidate")
        status = _row_status(self.row_status)
        object.__setattr__(self, "row_status", status)
        object.__setattr__(self, "failure_code", _failure_code(self.failure_code, status=status))

    @property
    def intervention_key(self) -> InterventionKey:
        return (
            self.source_seed,
            self.world_anchor_sha256,
            self.anchor_sha256,
            self.focal_user,
        )

    @property
    def sibling_key(self) -> SiblingKey:
        return self.intervention_key + (self.candidate_physical_key,)

    def verify_against(self, anchor: C2V04AnchorSchedule) -> None:
        """Reject any row whose duplicated shared fields drifted."""

        anchor.verify()
        expected = _anchor_shared_payload(anchor)
        actual = {
            "schema": C2_V04_ANCHOR_SCHEDULE_SCHEMA,
            "source_rule": self.source_rule,
            "source_seed": self.source_seed,
            "anchor_step": self.anchor_step,
            "world_anchor_sha256": self.world_anchor_sha256,
            "anchor_sha256": self.anchor_sha256,
            "focal_user": self.focal_user,
            "reference_action": self.reference_action,
            "reference_physical_key": list(self.reference_physical_key),
            "incumbent_physical_key": list(self.incumbent_physical_key),
            "common_random_field_sha256": self.common_random_field_sha256,
            "predecision_heuristic_scores": list(self.predecision_heuristic_scores),
            "legal_action_mask": list(self.legal_action_mask),
            "candidate_actions": list(self.candidate_actions),
            "candidate_physical_keys": [
                list(value) for value in self.candidate_physical_keys
            ],
            "checkpoint_sha256": self.checkpoint_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "policy_sha256": self.policy_sha256,
            "evaluation_seed": self.evaluation_seed,
            "anchor_schedule_sha256": self.anchor_schedule_sha256,
        }
        if actual != expected:
            raise C2V04SiblingScheduleContractError(
                "sibling row shared anchor fields disagree with sealed anchor"
            )
        if (self.candidate_action, self.candidate_physical_key) not in {
            (action, key) for key, action in anchor.candidate_pairs
        }:
            raise C2V04SiblingScheduleContractError(
                "sibling candidate is missing from or extra to the complete legal census"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema": C2_V04_SIBLING_SCHEMA,
            "source_rule": self.source_rule,
            "source_seed": self.source_seed,
            "anchor_step": self.anchor_step,
            "world_anchor_sha256": self.world_anchor_sha256,
            "anchor_sha256": self.anchor_sha256,
            "focal_user": self.focal_user,
            "anchor_schedule_sha256": self.anchor_schedule_sha256,
            "reference_action": self.reference_action,
            "reference_physical_key": list(self.reference_physical_key),
            "incumbent_physical_key": list(self.incumbent_physical_key),
            "common_random_field_sha256": self.common_random_field_sha256,
            "predecision_heuristic_scores": list(self.predecision_heuristic_scores),
            "legal_action_mask": list(self.legal_action_mask),
            "candidate_actions": list(self.candidate_actions),
            "candidate_physical_keys": [
                list(value) for value in self.candidate_physical_keys
            ],
            "candidate_action": self.candidate_action,
            "candidate_physical_key": list(self.candidate_physical_key),
            "checkpoint_sha256": self.checkpoint_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "policy_sha256": self.policy_sha256,
            "evaluation_seed": self.evaluation_seed,
            "row_status": self.row_status,
            "failure_code": self.failure_code,
        }

    @classmethod
    def from_mapping(cls, value: object) -> "C2V04SiblingRow":
        payload = _mapping(value, field="sibling row")
        allowed = frozenset(
            {
                "schema",
                "source_rule",
                "source_seed",
                "anchor_step",
                "world_anchor_sha256",
                "anchor_sha256",
                "focal_user",
                "anchor_schedule_sha256",
                "reference_action",
                "reference_physical_key",
                "incumbent_physical_key",
                "common_random_field_sha256",
                "predecision_heuristic_scores",
                "legal_action_mask",
                "candidate_actions",
                "candidate_physical_keys",
                "candidate_action",
                "candidate_physical_key",
                "checkpoint_sha256",
                "source_manifest_sha256",
                "policy_sha256",
                "evaluation_seed",
                "row_status",
                "failure_code",
            }
        )
        _reject_unknown_fields(payload, allowed=allowed, field="sibling row")
        missing = sorted(allowed - set(payload))
        if missing:
            raise C2V04SiblingScheduleContractError(
                f"sibling row is missing required field(s): {', '.join(missing)}"
            )
        if payload["schema"] != C2_V04_SIBLING_SCHEMA:
            raise C2V04SiblingScheduleContractError(
                "sibling row schema is stale or unsupported"
            )
        return cls(
            source_seed=payload["source_seed"],  # type: ignore[arg-type]
            anchor_step=payload["anchor_step"],  # type: ignore[arg-type]
            world_anchor_sha256=payload["world_anchor_sha256"],  # type: ignore[arg-type]
            anchor_sha256=payload["anchor_sha256"],  # type: ignore[arg-type]
            focal_user=payload["focal_user"],  # type: ignore[arg-type]
            anchor_schedule_sha256=payload["anchor_schedule_sha256"],  # type: ignore[arg-type]
            reference_action=payload["reference_action"],  # type: ignore[arg-type]
            reference_physical_key=payload["reference_physical_key"],  # type: ignore[arg-type]
            incumbent_physical_key=payload["incumbent_physical_key"],  # type: ignore[arg-type]
            common_random_field_sha256=payload["common_random_field_sha256"],  # type: ignore[arg-type]
            predecision_heuristic_scores=tuple(payload["predecision_heuristic_scores"]),  # type: ignore[arg-type]
            legal_action_mask=tuple(payload["legal_action_mask"]),  # type: ignore[arg-type]
            candidate_actions=tuple(payload["candidate_actions"]),  # type: ignore[arg-type]
            candidate_physical_keys=tuple(
                tuple(item) for item in payload["candidate_physical_keys"]  # type: ignore[union-attr]
            ),
            candidate_action=payload["candidate_action"],  # type: ignore[arg-type]
            candidate_physical_key=payload["candidate_physical_key"],  # type: ignore[arg-type]
            checkpoint_sha256=payload["checkpoint_sha256"],  # type: ignore[arg-type]
            source_manifest_sha256=payload["source_manifest_sha256"],  # type: ignore[arg-type]
            policy_sha256=payload["policy_sha256"],  # type: ignore[arg-type]
            evaluation_seed=payload["evaluation_seed"],  # type: ignore[arg-type]
            row_status=payload["row_status"],  # type: ignore[arg-type]
            failure_code=payload["failure_code"],  # type: ignore[arg-type]
            source_rule=payload["source_rule"],  # type: ignore[arg-type]
        )


def _schedule_payload(schedule: "C2V04SupportCompleteSchedule") -> dict[str, object]:
    return {
        "schema": C2_V04_SCHEDULE_SCHEMA,
        "version": C2_V04_SCHEDULE_VERSION,
        "anchors": [anchor.to_mapping() for anchor in schedule.anchors],
        "rows": [row.to_mapping() for row in schedule.rows],
    }


@dataclass(frozen=True)
class C2V04SupportCompleteSchedule:
    """A sealed collection of complete C2 sibling censuses."""

    anchors: tuple[C2V04AnchorSchedule, ...]
    rows: tuple[C2V04SiblingRow, ...]
    schedule_sha256: str
    schema: str = C2_V04_SCHEDULE_SCHEMA
    version: int = C2_V04_SCHEDULE_VERSION

    def __post_init__(self) -> None:
        if self.schema != C2_V04_SCHEDULE_SCHEMA or self.version != C2_V04_SCHEDULE_VERSION:
            raise C2V04SiblingScheduleContractError("schedule schema or version is stale")
        if not isinstance(self.anchors, tuple) or not self.anchors:
            raise C2V04SiblingScheduleContractError("anchors must be a nonempty tuple")
        if not isinstance(self.rows, tuple):
            raise C2V04SiblingScheduleContractError("rows must be an immutable tuple")
        anchors = tuple(self.anchors)
        rows = tuple(self.rows)
        if anchors != tuple(sorted(anchors, key=lambda value: value.intervention_key)):
            raise C2V04SiblingScheduleContractError("anchors are not canonically sorted")
        if rows != tuple(sorted(rows, key=lambda value: value.sibling_key)):
            raise C2V04SiblingScheduleContractError("sibling rows are not canonically sorted")
        by_intervention: dict[InterventionKey, C2V04AnchorSchedule] = {}
        for anchor in anchors:
            if not isinstance(anchor, C2V04AnchorSchedule):
                raise C2V04SiblingScheduleContractError("anchors contain a non-anchor record")
            anchor.verify()
            if anchor.intervention_key in by_intervention:
                raise C2V04SiblingScheduleContractError("duplicate intervention_key")
            by_intervention[anchor.intervention_key] = anchor
        seen_siblings: set[SiblingKey] = set()
        grouped: dict[InterventionKey, set[tuple[int, PhysicalKey]]] = {
            key: set() for key in by_intervention
        }
        for row in rows:
            if not isinstance(row, C2V04SiblingRow):
                raise C2V04SiblingScheduleContractError("rows contain a non-sibling record")
            anchor = by_intervention.get(row.intervention_key)
            if anchor is None:
                raise C2V04SiblingScheduleContractError("sibling row has no matching anchor")
            row.verify_against(anchor)
            if row.sibling_key in seen_siblings:
                raise C2V04SiblingScheduleContractError("duplicate sibling_key")
            seen_siblings.add(row.sibling_key)
            grouped[row.intervention_key].add((row.candidate_action, row.candidate_physical_key))
        for key, anchor in by_intervention.items():
            expected = {(action, physical) for physical, action in anchor.candidate_pairs}
            if grouped[key] != expected:
                missing = sorted(expected - grouped[key], key=lambda item: (item[1], item[0]))
                extra = sorted(grouped[key] - expected, key=lambda item: (item[1], item[0]))
                raise C2V04SiblingScheduleContractError(
                    "sibling rows are not a complete legal census "
                    f"(missing={missing}, extra={extra})"
                )
        supplied = _digest(self.schedule_sha256, field="schedule_sha256")
        actual = _sha256_bytes(_canonical_json_bytes(_schedule_payload(self)))
        if supplied != actual:
            raise C2V04SiblingScheduleContractError(
                "schedule_sha256 disagrees with canonical schedule contents"
            )

    @property
    def file_sha256(self) -> str:
        return _sha256_bytes(_canonical_json_bytes(self.to_mapping()))

    def verify(self) -> str:
        """Revalidate all rows and return the schedule body digest."""

        type(self)(
            anchors=self.anchors,
            rows=self.rows,
            schedule_sha256=self.schedule_sha256,
            schema=self.schema,
            version=self.version,
        )
        return self.schedule_sha256

    def to_mapping(self) -> dict[str, object]:
        return _schedule_payload(self) | {"schedule_sha256": self.schedule_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "C2V04SupportCompleteSchedule":
        payload = _mapping(value, field="schedule")
        allowed = frozenset(
            {"schema", "version", "anchors", "rows", "schedule_sha256"}
        )
        _reject_unknown_fields(payload, allowed=allowed, field="schedule")
        missing = sorted(allowed - set(payload))
        if missing:
            raise C2V04SiblingScheduleContractError(
                f"schedule is missing required field(s): {', '.join(missing)}"
            )
        if not isinstance(payload["anchors"], list) or not isinstance(payload["rows"], list):
            raise C2V04SiblingScheduleContractError("schedule anchors and rows must be JSON lists")
        anchors = tuple(C2V04AnchorSchedule.from_mapping(item) for item in payload["anchors"])
        rows = tuple(C2V04SiblingRow.from_mapping(item) for item in payload["rows"])
        return cls(
            anchors=anchors,
            rows=rows,
            schedule_sha256=payload["schedule_sha256"],  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
            version=payload["version"],  # type: ignore[arg-type]
        )


def build_c2_v04_support_complete_schedule(
    anchors: Iterable[C2V04AnchorSchedule],
    rows: Iterable[C2V04SiblingRow] | None = None,
) -> C2V04SupportCompleteSchedule:
    """Seal a deterministic schedule without evaluating any branch outcome.

    When ``rows`` is omitted, one ``ready`` row is materialised for every
    candidate in every anchor.  When it is supplied, every row—including
    ``row-failure`` and ``support-expired`` statuses—is retained and checked
    against the complete census.
    """

    anchor_values = tuple(anchors)
    if not anchor_values:
        raise C2V04SiblingScheduleContractError("anchor universe is empty")
    canonical_anchors = tuple(sorted(anchor_values, key=lambda value: value.intervention_key))
    if rows is None:
        row_values = tuple(
            C2V04SiblingRow.from_anchor(
                anchor,
                candidate_action=action,
                candidate_physical_key=physical,
            )
            for anchor in canonical_anchors
            for physical, action in anchor.candidate_pairs
        )
    else:
        row_values = tuple(rows)
    canonical_rows = tuple(sorted(row_values, key=lambda value: value.sibling_key))
    draft = {
        "schema": C2_V04_SCHEDULE_SCHEMA,
        "version": C2_V04_SCHEDULE_VERSION,
        "anchors": [anchor.to_mapping() for anchor in canonical_anchors],
        "rows": [row.to_mapping() for row in canonical_rows],
    }
    schedule_sha256 = _sha256_bytes(_canonical_json_bytes(draft))
    schedule = C2V04SupportCompleteSchedule(
        anchors=canonical_anchors,
        rows=canonical_rows,
        schedule_sha256=schedule_sha256,
    )
    schedule.verify()
    return schedule


def write_c2_v04_support_complete_schedule(
    path: str | Path, schedule: C2V04SupportCompleteSchedule
) -> str:
    """Atomically write one canonical schedule and refuse overwrite."""

    schedule.verify()
    destination = Path(path)
    if os.path.lexists(destination):
        raise FileExistsError(f"refusing to overwrite C2 V0.4 schedule: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json_bytes(schedule.to_mapping()) + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
        try:
            directory_fd = os.open(destination.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite C2 V0.4 schedule: {destination}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return _sha256_bytes(encoded)


def read_c2_v04_support_complete_schedule(
    path: str | Path, *, expected_file_sha256: str | None = None
) -> C2V04SupportCompleteSchedule:
    """Read and fail-closed validate one canonical schedule."""

    destination = Path(path)
    if destination.is_symlink() or not destination.is_file():
        raise C2V04SiblingScheduleContractError(
            "C2 V0.4 schedule must be a regular non-symlink file"
        )
    encoded = destination.read_bytes()
    actual_file_sha256 = _sha256_bytes(encoded)
    if expected_file_sha256 is not None and actual_file_sha256 != _digest(
        expected_file_sha256, field="expected_file_sha256"
    ):
        raise C2V04SiblingScheduleContractError(
            "schedule file SHA-256 disagrees with expected seal"
        )
    try:
        payload = json.loads(encoded.decode("ascii"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise C2V04SiblingScheduleContractError("cannot read canonical C2 V0.4 schedule") from error
    if encoded != _canonical_json_bytes(payload) + b"\n":
        raise C2V04SiblingScheduleContractError(
            "C2 V0.4 schedule is not canonical JSON"
        )
    return C2V04SupportCompleteSchedule.from_mapping(payload)


# Compatibility aliases for concise source-runner imports.  They point to the
# exact same versioned objects; no old schema is mutated or re-exported.
C2V04Anchor = C2V04AnchorSchedule
C2V04Sibling = C2V04SiblingRow
C2V04Schedule = C2V04SupportCompleteSchedule
build_v04_c2_sibling_schedule = build_c2_v04_support_complete_schedule
read_v04_c2_sibling_schedule = read_c2_v04_support_complete_schedule
write_v04_c2_sibling_schedule = write_c2_v04_support_complete_schedule


__all__ = [
    "C2_SUPPORT_COMPLETE_SOURCE_RULE",
    "C2_V04_ANCHOR_SCHEDULE_SCHEMA",
    "C2_V04_ROW_FAILURE",
    "C2_V04_ROW_READY",
    "C2_V04_ROW_STATUSES",
    "C2_V04_ROW_SUPPORT_EXPIRED",
    "C2_V04_SCHEDULE_SCHEMA",
    "C2_V04_SCHEDULE_VERSION",
    "C2_V04_SIBLING_SCHEMA",
    "C2_V04_SOURCE_RULE",
    "C2_V04_SUPPORT_COMPLETE_SOURCE_RULE",
    "C2V04Anchor",
    "C2V04AnchorSchedule",
    "C2V04Schedule",
    "C2V04ScheduleContractError",
    "C2V04Sibling",
    "C2V04SiblingRow",
    "C2V04SiblingScheduleContractError",
    "C2V04SupportCompleteSchedule",
    "build_c2_v04_support_complete_schedule",
    "build_v04_c2_sibling_schedule",
    "canonical_anchor_schedule_sha256",
    "read_c2_v04_support_complete_schedule",
    "read_v04_c2_sibling_schedule",
    "write_c2_v04_support_complete_schedule",
    "write_v04_c2_sibling_schedule",
]
