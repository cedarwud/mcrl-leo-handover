"""Pre-outcome manifest for the three V0.7 C2 candidate arms.

The manifest is a pure-data boundary.  It registers P0, B1, and B2 together
before any target-bearing outcome is opened and derives one immutable,
standalone dispatch specification per arm.  It does not run an environment,
train Q2, select a winner, or write files.

All nested values are frozen dataclasses and tuples.  Canonical JSON digests
bind the common physical block, stage budgets, target implementations,
keyed-field/tape grammars, and selection rules.  Serialized job specifications
are derived from the manifest and checked on load, so an arm cannot be omitted
or cancelled by deleting a job entry and recomputing unrelated metadata.

The manifest also carries a separately labelled B2 fast-proxy specification.
Its predeclared panel is capped at four native action IDs and is diagnostic
only; full B2 confirmation remains bound to all 28 native actions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_v07_c2_d2 import (
    D2_DEFAULT_KAPPA_BITS,
    D2_EARLY_STEPS,
    D2_EXPECTED_ANCHORS,
    D2_EXPECTED_CELLS,
    D2_INTERVAL_S,
    D2_IQR_METHOD,
    D2_LAMBDA_BITS_PER_J,
    D2_LATE_STEPS,
    D2_LINEAGES,
    D2_SEEDS,
)
from .ee_axis_v07_c2_focal_next import V07_C2_TARGET_SCHEMA
from .ee_axis_v07_c2_parallel_targets import (
    V07_C2_B1_TARGET_SCHEMA,
    V07_C2_B2_TARGET_SCHEMA,
)
from .ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)


V07_C2_PARALLEL_MANIFEST_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-parallel-manifest-v1"
)
V07_C2_PARALLEL_JOB_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-parallel-job-v1"
)
V07_C2_PARALLEL_ANCHOR_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-physical-anchor-v1"
)
V07_C2_PARALLEL_LINEAGE_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-lineage-authority-v1"
)
V07_C2_PARALLEL_SEEDS_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-seed-schedule-v1"
)
V07_C2_PARALLEL_BUDGET_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-shared-budget-v1"
)
V07_C2_PARALLEL_TARGET_AUTHORITY_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-target-authority-v1"
)
V07_C2_PARALLEL_PROTOCOL_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-protocol-binding-v1"
)
V07_C2_PARALLEL_SELECTION_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-selection-rules-v1"
)
V07_C2_PARALLEL_FIREWALL_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-outcome-firewall-v1"
)
V07_C2_FAST_PROXY_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-preoutcome-b2-fast-proxy-v1"
)

V07_C2_PARALLEL_MANIFEST_VERSION = 1
V07_C2_PARALLEL_ARMS = ("P0", "B1", "B2")
V07_C2_PARALLEL_STAGES = ("A", "B", "C")
V07_C2_FAST_PROXY_STAGE = "FAST_PROXY"
V07_C2_FAST_PROXY_LABEL = "B2-fast-proxy"
V07_C2_FAST_PROXY_STAGE_LABEL = V07_C2_FAST_PROXY_LABEL
V07_C2_FAST_PROXY_EVIDENCE_STATUS = "diagnostic-only-not-final-evidence"
V07_C2_FAST_PROXY_MAX_ACTIONS = 4
V07_C2_FAST_PROXY_ACTION_PANEL_MAX = V07_C2_FAST_PROXY_MAX_ACTIONS
V07_C2_FAST_PROXY_ACTION_PANEL = (0, 1, 2, 3)
V07_C2_NATIVE_ACTION_COUNT = NUM_ACTIONS
V07_C2_B2_NATIVE_ACTION_COUNT = V07_C2_NATIVE_ACTION_COUNT
V07_C2_FULL_B2_CONFIRMATION_STAGE = "B2-full-native-28-confirmation"
V07_C2_FULL_B2_CONFIRMATION_LABEL = "B2-full-native-28-confirmation"
V07_C2_FULL_B2_NATIVE_ACTION_COUNT = V07_C2_NATIVE_ACTION_COUNT
V07_C2_STAGE_PLAN = (
    "A:always-run-registered-source-screen",
    "B:run-only-if-own-stage-a-pass-otherwise-report-not-run",
    "C:run-only-if-own-stage-b-pass-otherwise-report-not-run",
)
V07_C2_ANCHOR_SELECTOR = (
    "per-seed:first-chronological-eligible-step-in-early-1-2-and-late-5-6;"
    "eligibility=native-mask-at-least-3;focal=lowest-eligible-user-id;"
    "no-target-inspection;no-retry;no-replacement"
)
V07_C2_KEYED_FIELD_GRAMMAR = (
    "keyed-field-v1|root=(physical-seed,anchor-receipt-sha256)|"
    "draw=(successor-offset,physical-entity,draw-purpose)|"
    "excluded=(arm,lineage,branch,action-enumeration-order)"
)
V07_C2_NONFOCAL_TAPE_GRAMMAR = (
    "nonfocal-physical-tape-v1|"
    "key=(physical-seed,anchor-receipt-sha256,lineage,successor-offset,user-id)|"
    "value=(norad-id,cell-id)|offsets=(1,2,3)|"
    "shared=(B1,B2,candidate,reference)|branch-local-index=forbidden|"
    "unreplayable=structural-unsupported|fallback=forbidden"
)
V07_C2_SELECTION_STATISTIC = (
    "greatest-registered-median-heldout-ratio-of-sums-ee-improvement-"
    "subject-to-frozen-service-guard"
)
V07_C2_NO_PASS_DISPOSITION = "seal-p0-b1-b2-generation-negative"

_TARGET_DEFINITIONS = {
    "P0": (
        V07_C2_TARGET_SCHEMA,
        "ee_axis_v07_c2_focal_next.py",
        "mcrl.runtime.ee_axis_v07_c2_focal_next",
        "focal_next_surplus_target",
        False,
    ),
    "B1": (
        V07_C2_B1_TARGET_SCHEMA,
        "ee_axis_v07_c2_parallel_targets.py",
        "mcrl.runtime.ee_axis_v07_c2_parallel_targets",
        "focal_segment_continuation_target",
        True,
    ),
    "B2": (
        V07_C2_B2_TARGET_SCHEMA,
        "ee_axis_v07_c2_parallel_targets.py",
        "mcrl.runtime.ee_axis_v07_c2_parallel_targets",
        "successor_option_set_target",
        True,
    ),
}


class V07C2ParallelManifestError(MCRLContractError):
    """A purported pre-outcome three-arm manifest violates its contract."""


def canonical_json_bytes(payload: object) -> bytes:
    """Return the sole finite, ASCII canonical JSON representation."""

    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V07C2ParallelManifestError(
            "parallel manifest payload is not canonical finite JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    """Return a lower-case SHA-256 over canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _schema_identifier_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _mapping(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise V07C2ParallelManifestError(f"{field} must be a JSON object")
    if not all(isinstance(key, str) for key in value):
        raise V07C2ParallelManifestError(f"{field} keys must be strings")
    return dict(value)


def _exact_fields(
    payload: Mapping[str, object], *, fields: frozenset[str], label: str
) -> None:
    missing = sorted(fields - set(payload))
    unknown = sorted(set(payload) - fields)
    if missing:
        raise V07C2ParallelManifestError(
            f"{label} is missing required field(s): {', '.join(missing)}"
        )
    if unknown:
        raise V07C2ParallelManifestError(
            f"{label} contains forbidden/unknown field(s): {', '.join(unknown)}"
        )


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise V07C2ParallelManifestError(
            f"{field} must be a nonempty trimmed string"
        )
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V07C2ParallelManifestError(
            f"{field} must be a lower-case SHA-256 digest"
        )
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise V07C2ParallelManifestError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _exact_bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise V07C2ParallelManifestError(f"{field} must be a Boolean")
    return value


def _int_tuple(
    value: object, *, field: str, nonempty: bool = True
) -> tuple[int, ...]:
    if not isinstance(value, tuple):
        raise V07C2ParallelManifestError(f"{field} must be an immutable tuple")
    parsed = tuple(
        _exact_int(item, field=f"{field}[{index}]")
        for index, item in enumerate(value)
    )
    if nonempty and not parsed:
        raise V07C2ParallelManifestError(f"{field} must not be empty")
    if tuple(sorted(set(parsed))) != parsed:
        raise V07C2ParallelManifestError(
            f"{field} must be strictly increasing and duplicate-free"
        )
    return parsed


def _action_panel(value: object, *, field: str) -> tuple[int, ...]:
    """Validate an immutable, predeclared subset of native action IDs."""

    panel = _int_tuple(value, field=field)
    if len(panel) > V07_C2_FAST_PROXY_MAX_ACTIONS:
        raise V07C2ParallelManifestError(
            f"{field} must contain at most "
            f"{V07_C2_FAST_PROXY_MAX_ACTIONS} native actions"
        )
    if any(action >= V07_C2_NATIVE_ACTION_COUNT for action in panel):
        raise V07C2ParallelManifestError(
            f"{field} action IDs must be in [0,{V07_C2_NATIVE_ACTION_COUNT})"
        )
    return panel


def _hex_nonnegative(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    try:
        parsed = float.fromhex(text)
    except (ValueError, OverflowError) as error:
        raise V07C2ParallelManifestError(
            f"{field} must be a canonical finite hexadecimal float"
        ) from error
    if not math.isfinite(parsed) or parsed < 0.0 or parsed.hex() != text:
        raise V07C2ParallelManifestError(
            f"{field} must be a canonical finite non-negative hexadecimal float"
        )
    return text


def _source_sha256(filename: str) -> str:
    path = Path(__file__).resolve().with_name(filename)
    try:
        source = path.read_bytes()
    except OSError as error:
        raise V07C2ParallelManifestError(
            f"target authority source is unavailable: {filename}"
        ) from error
    return hashlib.sha256(source).hexdigest()


@dataclass(frozen=True, slots=True)
class PhysicalAnchorSpec:
    """One outcome-blind physical anchor shared by every candidate arm."""

    seed: int
    window: str
    step_index: int
    focal_user: int
    anchor_receipt_sha256: str
    schema: str = V07_C2_PARALLEL_ANCHOR_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_ANCHOR_SCHEMA:
            raise V07C2ParallelManifestError("physical anchor schema is stale")
        seed = _exact_int(self.seed, field="anchor.seed")
        if seed not in D2_SEEDS:
            raise V07C2ParallelManifestError(
                "physical anchor seed is outside the frozen Stage-A seeds"
            )
        window = _text(self.window, field="anchor.window")
        if window not in {"early", "late"}:
            raise V07C2ParallelManifestError(
                "physical anchor window must be early or late"
            )
        step = _exact_int(self.step_index, field="anchor.step_index")
        allowed = D2_EARLY_STEPS if window == "early" else D2_LATE_STEPS
        if step not in allowed:
            raise V07C2ParallelManifestError(
                "physical anchor step is outside its frozen selection window"
            )
        object.__setattr__(
            self,
            "focal_user",
            _exact_int(self.focal_user, field="anchor.focal_user"),
        )
        object.__setattr__(
            self,
            "anchor_receipt_sha256",
            _digest(
                self.anchor_receipt_sha256,
                field="anchor.anchor_receipt_sha256",
            ),
        )

    @property
    def anchor_id_sha256(self) -> str:
        return canonical_sha256(self._body())

    @property
    def sort_key(self) -> tuple[int, int]:
        return (self.seed, 0 if self.window == "early" else 1)

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "seed": self.seed,
            "window": self.window,
            "step_index": self.step_index,
            "focal_user": self.focal_user,
            "anchor_receipt_sha256": self.anchor_receipt_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"anchor_id_sha256": self.anchor_id_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "PhysicalAnchorSpec":
        payload = _mapping(value, field="physical anchor")
        fields = frozenset(
            {
                "schema",
                "seed",
                "window",
                "step_index",
                "focal_user",
                "anchor_receipt_sha256",
                "anchor_id_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="physical anchor")
        anchor = cls(
            seed=payload["seed"],  # type: ignore[arg-type]
            window=payload["window"],  # type: ignore[arg-type]
            step_index=payload["step_index"],  # type: ignore[arg-type]
            focal_user=payload["focal_user"],  # type: ignore[arg-type]
            anchor_receipt_sha256=payload["anchor_receipt_sha256"],  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["anchor_id_sha256"], field="anchor.anchor_id_sha256"
        ) != anchor.anchor_id_sha256:
            raise V07C2ParallelManifestError(
                "anchor_id_sha256 disagrees with the physical anchor"
            )
        return anchor


@dataclass(frozen=True, slots=True)
class LineageAuthority:
    """Pinned Q1/Q3 bytes and direct-policy bytes for one lineage."""

    lineage: str
    q1_checkpoint_sha256: str
    q3_checkpoint_sha256: str
    direct_policy_sha256: str
    schema: str = V07_C2_PARALLEL_LINEAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_LINEAGE_SCHEMA:
            raise V07C2ParallelManifestError("lineage authority schema is stale")
        lineage = _text(self.lineage, field="lineage.lineage")
        if lineage not in D2_LINEAGES:
            raise V07C2ParallelManifestError(
                "lineage is not one of the three frozen Q1/Q3 lineages"
            )
        for field in (
            "q1_checkpoint_sha256",
            "q3_checkpoint_sha256",
            "direct_policy_sha256",
        ):
            object.__setattr__(
                self,
                field,
                _digest(getattr(self, field), field=f"lineage.{field}"),
            )

    @property
    def authority_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "lineage": self.lineage,
            "q1_checkpoint_sha256": self.q1_checkpoint_sha256,
            "q3_checkpoint_sha256": self.q3_checkpoint_sha256,
            "direct_policy_sha256": self.direct_policy_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"authority_sha256": self.authority_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "LineageAuthority":
        payload = _mapping(value, field="lineage authority")
        fields = frozenset(
            {
                "schema",
                "lineage",
                "q1_checkpoint_sha256",
                "q3_checkpoint_sha256",
                "direct_policy_sha256",
                "authority_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="lineage authority")
        authority = cls(
            lineage=payload["lineage"],  # type: ignore[arg-type]
            q1_checkpoint_sha256=payload["q1_checkpoint_sha256"],  # type: ignore[arg-type]
            q3_checkpoint_sha256=payload["q3_checkpoint_sha256"],  # type: ignore[arg-type]
            direct_policy_sha256=payload["direct_policy_sha256"],  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["authority_sha256"], field="lineage.authority_sha256"
        ) != authority.authority_sha256:
            raise V07C2ParallelManifestError(
                "lineage authority digest disagrees with its contents"
            )
        return authority


@dataclass(frozen=True, slots=True)
class CommonSeedSchedule:
    """One shared, disjoint seed allocation used by all three arms."""

    stage_a_physical_seeds: tuple[int, ...]
    stage_b_train_world_seeds: tuple[int, ...]
    stage_b_validation_world_seeds: tuple[int, ...]
    stage_b_initialization_seeds: tuple[int, ...]
    stage_c_evaluation_world_seeds: tuple[int, ...]
    schema: str = V07_C2_PARALLEL_SEEDS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_SEEDS_SCHEMA:
            raise V07C2ParallelManifestError("common seed schedule schema is stale")
        for field in (
            "stage_a_physical_seeds",
            "stage_b_train_world_seeds",
            "stage_b_validation_world_seeds",
            "stage_b_initialization_seeds",
            "stage_c_evaluation_world_seeds",
        ):
            object.__setattr__(
                self,
                field,
                _int_tuple(getattr(self, field), field=f"seeds.{field}"),
            )
        if self.stage_a_physical_seeds != D2_SEEDS:
            raise V07C2ParallelManifestError(
                "Stage-A physical seeds must equal the frozen ten-seed D2 block"
            )
        named_sets = {
            "stage_a": set(self.stage_a_physical_seeds),
            "stage_b_train": set(self.stage_b_train_world_seeds),
            "stage_b_validation": set(self.stage_b_validation_world_seeds),
            "stage_b_initialization": set(self.stage_b_initialization_seeds),
            "stage_c_evaluation": set(self.stage_c_evaluation_world_seeds),
        }
        names = tuple(named_sets)
        for first_index, first in enumerate(names):
            for second in names[first_index + 1 :]:
                if named_sets[first] & named_sets[second]:
                    raise V07C2ParallelManifestError(
                        f"common seed roles overlap: {first} and {second}"
                    )

    @property
    def schedule_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "stage_a_physical_seeds": list(self.stage_a_physical_seeds),
            "stage_b_train_world_seeds": list(self.stage_b_train_world_seeds),
            "stage_b_validation_world_seeds": list(
                self.stage_b_validation_world_seeds
            ),
            "stage_b_initialization_seeds": list(
                self.stage_b_initialization_seeds
            ),
            "stage_c_evaluation_world_seeds": list(
                self.stage_c_evaluation_world_seeds
            ),
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"schedule_sha256": self.schedule_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "CommonSeedSchedule":
        payload = _mapping(value, field="common seed schedule")
        fields = frozenset(
            {
                "schema",
                "stage_a_physical_seeds",
                "stage_b_train_world_seeds",
                "stage_b_validation_world_seeds",
                "stage_b_initialization_seeds",
                "stage_c_evaluation_world_seeds",
                "schedule_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="common seed schedule")

        def ints(name: str) -> tuple[int, ...]:
            raw = payload[name]
            if not isinstance(raw, list):
                raise V07C2ParallelManifestError(
                    f"seeds.{name} must be a JSON list"
                )
            return tuple(raw)  # type: ignore[arg-type]

        schedule = cls(
            stage_a_physical_seeds=ints("stage_a_physical_seeds"),
            stage_b_train_world_seeds=ints("stage_b_train_world_seeds"),
            stage_b_validation_world_seeds=ints(
                "stage_b_validation_world_seeds"
            ),
            stage_b_initialization_seeds=ints("stage_b_initialization_seeds"),
            stage_c_evaluation_world_seeds=ints(
                "stage_c_evaluation_world_seeds"
            ),
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["schedule_sha256"], field="seeds.schedule_sha256"
        ) != schedule.schedule_sha256:
            raise V07C2ParallelManifestError(
                "common seed schedule digest disagrees with its contents"
            )
        return schedule


@dataclass(frozen=True, slots=True)
class SharedStageBudgets:
    """One budget object referenced identically by P0, B1, and B2."""

    stage_a_physical_anchors: int
    stage_a_lineages: int
    stage_a_lineage_cells: int
    stage_b_updates: int
    stage_b_train_worlds: int
    stage_b_validation_worlds: int
    stage_b_initializations: int
    stage_c_evaluation_worlds: int
    stage_c_lineages: int
    stage_c_paired_variants: tuple[str, ...] = ("FULL", "DROP_C2")
    schema: str = V07_C2_PARALLEL_BUDGET_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_BUDGET_SCHEMA:
            raise V07C2ParallelManifestError("shared budget schema is stale")
        for field in (
            "stage_a_physical_anchors",
            "stage_a_lineages",
            "stage_a_lineage_cells",
            "stage_b_updates",
            "stage_b_train_worlds",
            "stage_b_validation_worlds",
            "stage_b_initializations",
            "stage_c_evaluation_worlds",
            "stage_c_lineages",
        ):
            object.__setattr__(
                self,
                field,
                _exact_int(getattr(self, field), field=f"budgets.{field}", minimum=1),
            )
        if (
            self.stage_a_physical_anchors != D2_EXPECTED_ANCHORS
            or self.stage_a_lineages != len(D2_LINEAGES)
            or self.stage_a_lineage_cells != D2_EXPECTED_CELLS
        ):
            raise V07C2ParallelManifestError(
                "Stage-A budget must be exactly 20 anchors x 3 lineages = 60 cells"
            )
        if self.stage_b_updates != 100:
            raise V07C2ParallelManifestError(
                "Stage-B budget must be exactly 100 updates per passing arm"
            )
        if self.stage_c_lineages != len(D2_LINEAGES):
            raise V07C2ParallelManifestError(
                "Stage-C budget must retain all three frozen lineages"
            )
        if not isinstance(self.stage_c_paired_variants, tuple):
            raise V07C2ParallelManifestError(
                "Stage-C paired variants must be an immutable tuple"
            )
        if self.stage_c_paired_variants != ("FULL", "DROP_C2"):
            raise V07C2ParallelManifestError(
                "Stage-C variants must be exactly FULL and DROP_C2"
            )

    @property
    def budget_sha256(self) -> str:
        return canonical_sha256(self._body())

    def verify_against(self, seeds: CommonSeedSchedule) -> None:
        expected = (
            len(seeds.stage_b_train_world_seeds),
            len(seeds.stage_b_validation_world_seeds),
            len(seeds.stage_b_initialization_seeds),
            len(seeds.stage_c_evaluation_world_seeds),
        )
        actual = (
            self.stage_b_train_worlds,
            self.stage_b_validation_worlds,
            self.stage_b_initializations,
            self.stage_c_evaluation_worlds,
        )
        if actual != expected:
            raise V07C2ParallelManifestError(
                "shared Stage-B/C budgets disagree with the common seed schedule"
            )

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "stage_a_physical_anchors": self.stage_a_physical_anchors,
            "stage_a_lineages": self.stage_a_lineages,
            "stage_a_lineage_cells": self.stage_a_lineage_cells,
            "stage_b_updates": self.stage_b_updates,
            "stage_b_train_worlds": self.stage_b_train_worlds,
            "stage_b_validation_worlds": self.stage_b_validation_worlds,
            "stage_b_initializations": self.stage_b_initializations,
            "stage_c_evaluation_worlds": self.stage_c_evaluation_worlds,
            "stage_c_lineages": self.stage_c_lineages,
            "stage_c_paired_variants": list(self.stage_c_paired_variants),
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"budget_sha256": self.budget_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "SharedStageBudgets":
        payload = _mapping(value, field="shared budgets")
        fields = frozenset(
            {
                "schema",
                "stage_a_physical_anchors",
                "stage_a_lineages",
                "stage_a_lineage_cells",
                "stage_b_updates",
                "stage_b_train_worlds",
                "stage_b_validation_worlds",
                "stage_b_initializations",
                "stage_c_evaluation_worlds",
                "stage_c_lineages",
                "stage_c_paired_variants",
                "budget_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="shared budgets")
        variants = payload["stage_c_paired_variants"]
        if not isinstance(variants, list):
            raise V07C2ParallelManifestError(
                "budgets.stage_c_paired_variants must be a JSON list"
            )
        budgets = cls(
            stage_a_physical_anchors=payload["stage_a_physical_anchors"],  # type: ignore[arg-type]
            stage_a_lineages=payload["stage_a_lineages"],  # type: ignore[arg-type]
            stage_a_lineage_cells=payload["stage_a_lineage_cells"],  # type: ignore[arg-type]
            stage_b_updates=payload["stage_b_updates"],  # type: ignore[arg-type]
            stage_b_train_worlds=payload["stage_b_train_worlds"],  # type: ignore[arg-type]
            stage_b_validation_worlds=payload[
                "stage_b_validation_worlds"
            ],  # type: ignore[arg-type]
            stage_b_initializations=payload["stage_b_initializations"],  # type: ignore[arg-type]
            stage_c_evaluation_worlds=payload[
                "stage_c_evaluation_worlds"
            ],  # type: ignore[arg-type]
            stage_c_lineages=payload["stage_c_lineages"],  # type: ignore[arg-type]
            stage_c_paired_variants=tuple(variants),  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["budget_sha256"], field="budgets.budget_sha256"
        ) != budgets.budget_sha256:
            raise V07C2ParallelManifestError(
                "shared budget digest disagrees with its contents"
            )
        return budgets


@dataclass(frozen=True, slots=True)
class TargetAuthority:
    """One arm's exact target schema, callable, and current source bytes."""

    arm: str
    target_schema: str
    target_module: str
    target_callable: str
    target_code_sha256: str
    uses_common_nonfocal_tape: bool
    schema: str = V07_C2_PARALLEL_TARGET_AUTHORITY_SCHEMA
    native_action_count: int = V07_C2_NATIVE_ACTION_COUNT

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_TARGET_AUTHORITY_SCHEMA:
            raise V07C2ParallelManifestError("target authority schema is stale")
        arm = _text(self.arm, field="target.arm")
        if arm not in V07_C2_PARALLEL_ARMS:
            raise V07C2ParallelManifestError("target arm is not P0, B1, or B2")
        expected = _TARGET_DEFINITIONS[arm]
        uses_tape = _exact_bool(
            self.uses_common_nonfocal_tape,
            field=f"target[{arm}].uses_common_nonfocal_tape",
        )
        object.__setattr__(self, "uses_common_nonfocal_tape", uses_tape)
        supplied = (
            self.target_schema,
            self.target_module,
            self.target_callable,
            uses_tape,
        )
        expected_semantics = (expected[0], expected[2], expected[3], expected[4])
        if supplied != expected_semantics:
            raise V07C2ParallelManifestError(
                f"{arm} target schema/callable/tape semantics drifted"
            )
        object.__setattr__(
            self,
            "target_code_sha256",
            _digest(self.target_code_sha256, field=f"target[{arm}].code_sha256"),
        )
        if self.target_code_sha256 != _source_sha256(expected[1]):
            raise V07C2ParallelManifestError(
                f"{arm} target code hash disagrees with current source bytes"
            )
        if (
            _exact_int(
                self.native_action_count,
                field=f"target[{arm}].native_action_count",
                minimum=1,
            )
            != V07_C2_NATIVE_ACTION_COUNT
        ):
            raise V07C2ParallelManifestError(
                f"{arm} target must retain native 28-action surface"
            )

    @property
    def target_schema_sha256(self) -> str:
        return _schema_identifier_sha256(self.target_schema)

    @property
    def target_action_count(self) -> int:
        return self.native_action_count

    @property
    def authority_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "arm": self.arm,
            "target_schema": self.target_schema,
            "target_schema_sha256": self.target_schema_sha256,
            "target_module": self.target_module,
            "target_callable": self.target_callable,
            "target_code_sha256": self.target_code_sha256,
            "native_action_count": self.native_action_count,
            "uses_common_nonfocal_tape": self.uses_common_nonfocal_tape,
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"authority_sha256": self.authority_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "TargetAuthority":
        payload = _mapping(value, field="target authority")
        fields = frozenset(
            {
                "schema",
                "arm",
                "target_schema",
                "target_schema_sha256",
                "target_module",
                "target_callable",
                "target_code_sha256",
                "native_action_count",
                "uses_common_nonfocal_tape",
                "authority_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="target authority")
        authority = cls(
            arm=payload["arm"],  # type: ignore[arg-type]
            target_schema=payload["target_schema"],  # type: ignore[arg-type]
            target_module=payload["target_module"],  # type: ignore[arg-type]
            target_callable=payload["target_callable"],  # type: ignore[arg-type]
            target_code_sha256=payload["target_code_sha256"],  # type: ignore[arg-type]
            native_action_count=payload["native_action_count"],  # type: ignore[arg-type]
            uses_common_nonfocal_tape=_exact_bool(
                payload["uses_common_nonfocal_tape"],
                field="target.uses_common_nonfocal_tape",
            ),
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["target_schema_sha256"],
            field="target.target_schema_sha256",
        ) != authority.target_schema_sha256:
            raise V07C2ParallelManifestError("target schema digest drifted")
        if _digest(
            payload["authority_sha256"], field="target.authority_sha256"
        ) != authority.authority_sha256:
            raise V07C2ParallelManifestError(
                "target authority digest disagrees with its contents"
            )
        return authority


def current_target_authorities() -> tuple[TargetAuthority, ...]:
    """Return the exact three target bindings for the current checkout."""

    authorities: list[TargetAuthority] = []
    for arm in V07_C2_PARALLEL_ARMS:
        target_schema, filename, module, callable_name, uses_tape = (
            _TARGET_DEFINITIONS[arm]
        )
        authorities.append(
            TargetAuthority(
                arm=arm,
                target_schema=target_schema,
                target_module=module,
                target_callable=callable_name,
                target_code_sha256=_source_sha256(filename),
                uses_common_nonfocal_tape=uses_tape,
            )
        )
    return tuple(authorities)


@dataclass(frozen=True, slots=True)
class ProtocolBindings:
    """Hashes and grammars needed to reconstruct each common capture."""

    keyed_field_implementation_sha256: str
    nonfocal_tape_implementation_sha256: str
    stage_a_rules_sha256: str
    stage_b_rules_sha256: str
    stage_c_rules_sha256: str
    anchor_selector: str = V07_C2_ANCHOR_SELECTOR
    keyed_field_grammar: str = V07_C2_KEYED_FIELD_GRAMMAR
    nonfocal_tape_grammar: str = V07_C2_NONFOCAL_TAPE_GRAMMAR
    lambda_bits_per_j_hex: str = D2_LAMBDA_BITS_PER_J.hex()
    interval_s_hex: str = D2_INTERVAL_S.hex()
    kappa_bits_hex: str = D2_DEFAULT_KAPPA_BITS.hex()
    iqr_method: str = D2_IQR_METHOD
    schema: str = V07_C2_PARALLEL_PROTOCOL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_PROTOCOL_SCHEMA:
            raise V07C2ParallelManifestError("protocol binding schema is stale")
        expected = (
            V07_C2_ANCHOR_SELECTOR,
            V07_C2_KEYED_FIELD_GRAMMAR,
            V07_C2_NONFOCAL_TAPE_GRAMMAR,
            D2_LAMBDA_BITS_PER_J.hex(),
            D2_INTERVAL_S.hex(),
            D2_DEFAULT_KAPPA_BITS.hex(),
            D2_IQR_METHOD,
        )
        actual = (
            self.anchor_selector,
            self.keyed_field_grammar,
            self.nonfocal_tape_grammar,
            self.lambda_bits_per_j_hex,
            self.interval_s_hex,
            self.kappa_bits_hex,
            self.iqr_method,
        )
        if actual != expected:
            raise V07C2ParallelManifestError(
                "protocol selector, grammar, numeric, or IQR rule drifted"
            )
        for field in (
            "keyed_field_implementation_sha256",
            "nonfocal_tape_implementation_sha256",
            "stage_a_rules_sha256",
            "stage_b_rules_sha256",
            "stage_c_rules_sha256",
        ):
            object.__setattr__(
                self,
                field,
                _digest(getattr(self, field), field=f"protocol.{field}"),
            )

    @property
    def protocol_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "anchor_selector": self.anchor_selector,
            "keyed_field_grammar": self.keyed_field_grammar,
            "keyed_field_implementation_sha256": (
                self.keyed_field_implementation_sha256
            ),
            "nonfocal_tape_grammar": self.nonfocal_tape_grammar,
            "nonfocal_tape_implementation_sha256": (
                self.nonfocal_tape_implementation_sha256
            ),
            "lambda_bits_per_j_hex": self.lambda_bits_per_j_hex,
            "interval_s_hex": self.interval_s_hex,
            "kappa_bits_hex": self.kappa_bits_hex,
            "iqr_method": self.iqr_method,
            "stage_a_rules_sha256": self.stage_a_rules_sha256,
            "stage_b_rules_sha256": self.stage_b_rules_sha256,
            "stage_c_rules_sha256": self.stage_c_rules_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"protocol_sha256": self.protocol_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "ProtocolBindings":
        payload = _mapping(value, field="protocol bindings")
        fields = frozenset(
            {
                "schema",
                "anchor_selector",
                "keyed_field_grammar",
                "keyed_field_implementation_sha256",
                "nonfocal_tape_grammar",
                "nonfocal_tape_implementation_sha256",
                "lambda_bits_per_j_hex",
                "interval_s_hex",
                "kappa_bits_hex",
                "iqr_method",
                "stage_a_rules_sha256",
                "stage_b_rules_sha256",
                "stage_c_rules_sha256",
                "protocol_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="protocol bindings")
        protocol = cls(
            keyed_field_implementation_sha256=payload[
                "keyed_field_implementation_sha256"
            ],  # type: ignore[arg-type]
            nonfocal_tape_implementation_sha256=payload[
                "nonfocal_tape_implementation_sha256"
            ],  # type: ignore[arg-type]
            stage_a_rules_sha256=payload["stage_a_rules_sha256"],  # type: ignore[arg-type]
            stage_b_rules_sha256=payload["stage_b_rules_sha256"],  # type: ignore[arg-type]
            stage_c_rules_sha256=payload["stage_c_rules_sha256"],  # type: ignore[arg-type]
            anchor_selector=payload["anchor_selector"],  # type: ignore[arg-type]
            keyed_field_grammar=payload["keyed_field_grammar"],  # type: ignore[arg-type]
            nonfocal_tape_grammar=payload["nonfocal_tape_grammar"],  # type: ignore[arg-type]
            lambda_bits_per_j_hex=payload["lambda_bits_per_j_hex"],  # type: ignore[arg-type]
            interval_s_hex=payload["interval_s_hex"],  # type: ignore[arg-type]
            kappa_bits_hex=payload["kappa_bits_hex"],  # type: ignore[arg-type]
            iqr_method=payload["iqr_method"],  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["protocol_sha256"], field="protocol.protocol_sha256"
        ) != protocol.protocol_sha256:
            raise V07C2ParallelManifestError(
                "protocol binding digest disagrees with its contents"
            )
        return protocol


@dataclass(frozen=True, slots=True)
class SelectionRules:
    """Frozen cross-arm selection, tie, and report-all semantics."""

    practical_tie_band_fraction_hex: str
    service_guard_sha256: str
    primary_statistic: str = V07_C2_SELECTION_STATISTIC
    simplicity_order: tuple[str, ...] = V07_C2_PARALLEL_ARMS
    report_all_arms: bool = True
    no_pass_disposition: str = V07_C2_NO_PASS_DISPOSITION
    fresh_confirmation_required: bool = True
    schema: str = V07_C2_PARALLEL_SELECTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_SELECTION_SCHEMA:
            raise V07C2ParallelManifestError("selection-rule schema is stale")
        if self.primary_statistic != V07_C2_SELECTION_STATISTIC:
            raise V07C2ParallelManifestError("primary selection statistic drifted")
        if not isinstance(self.simplicity_order, tuple):
            raise V07C2ParallelManifestError(
                "selection simplicity_order must be an immutable tuple"
            )
        if self.simplicity_order != V07_C2_PARALLEL_ARMS:
            raise V07C2ParallelManifestError(
                "selection tie order must be exactly P0, B1, B2"
            )
        if _exact_bool(self.report_all_arms, field="selection.report_all_arms") is not True:
            raise V07C2ParallelManifestError("all three arm results must be reported")
        if self.no_pass_disposition != V07_C2_NO_PASS_DISPOSITION:
            raise V07C2ParallelManifestError("no-pass disposition drifted")
        if _exact_bool(
            self.fresh_confirmation_required,
            field="selection.fresh_confirmation_required",
        ) is not True:
            raise V07C2ParallelManifestError(
                "the selected arm must retain the fresh-confirmation gate"
            )
        object.__setattr__(
            self,
            "practical_tie_band_fraction_hex",
            _hex_nonnegative(
                self.practical_tie_band_fraction_hex,
                field="selection.practical_tie_band_fraction_hex",
            ),
        )
        object.__setattr__(
            self,
            "service_guard_sha256",
            _digest(
                self.service_guard_sha256,
                field="selection.service_guard_sha256",
            ),
        )

    @property
    def selection_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "primary_statistic": self.primary_statistic,
            "practical_tie_band_fraction_hex": (
                self.practical_tie_band_fraction_hex
            ),
            "simplicity_order": list(self.simplicity_order),
            "service_guard_sha256": self.service_guard_sha256,
            "report_all_arms": self.report_all_arms,
            "no_pass_disposition": self.no_pass_disposition,
            "fresh_confirmation_required": self.fresh_confirmation_required,
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"selection_sha256": self.selection_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "SelectionRules":
        payload = _mapping(value, field="selection rules")
        fields = frozenset(
            {
                "schema",
                "primary_statistic",
                "practical_tie_band_fraction_hex",
                "simplicity_order",
                "service_guard_sha256",
                "report_all_arms",
                "no_pass_disposition",
                "fresh_confirmation_required",
                "selection_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="selection rules")
        order = payload["simplicity_order"]
        if not isinstance(order, list):
            raise V07C2ParallelManifestError(
                "selection.simplicity_order must be a JSON list"
            )
        selection = cls(
            practical_tie_band_fraction_hex=payload[
                "practical_tie_band_fraction_hex"
            ],  # type: ignore[arg-type]
            service_guard_sha256=payload["service_guard_sha256"],  # type: ignore[arg-type]
            primary_statistic=payload["primary_statistic"],  # type: ignore[arg-type]
            simplicity_order=tuple(order),  # type: ignore[arg-type]
            report_all_arms=_exact_bool(
                payload["report_all_arms"], field="selection.report_all_arms"
            ),
            no_pass_disposition=payload["no_pass_disposition"],  # type: ignore[arg-type]
            fresh_confirmation_required=_exact_bool(
                payload["fresh_confirmation_required"],
                field="selection.fresh_confirmation_required",
            ),
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["selection_sha256"], field="selection.selection_sha256"
        ) != selection.selection_sha256:
            raise V07C2ParallelManifestError(
                "selection-rule digest disagrees with its contents"
            )
        return selection


@dataclass(frozen=True, slots=True)
class OutcomeFirewall:
    """Explicit pre-outcome attestations that must never be relaxed."""

    created_before_target_outcomes: bool = True
    target_outcomes_opened: bool = False
    test_split_opened: bool = False
    arm_omission_allowed: bool = False
    cross_arm_cancellation_allowed: bool = False
    retry_count: int = 0
    replacement_count: int = 0
    partial_results_may_mutate_manifest: bool = False
    ineligible_jobs_retained_for_report: bool = True
    schema: str = V07_C2_PARALLEL_FIREWALL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_FIREWALL_SCHEMA:
            raise V07C2ParallelManifestError("outcome-firewall schema is stale")
        expected = (
            True,
            False,
            False,
            False,
            False,
            0,
            0,
            False,
            True,
        )
        actual = (
            _exact_bool(
                self.created_before_target_outcomes,
                field="firewall.created_before_target_outcomes",
            ),
            _exact_bool(
                self.target_outcomes_opened,
                field="firewall.target_outcomes_opened",
            ),
            _exact_bool(
                self.test_split_opened, field="firewall.test_split_opened"
            ),
            _exact_bool(
                self.arm_omission_allowed,
                field="firewall.arm_omission_allowed",
            ),
            _exact_bool(
                self.cross_arm_cancellation_allowed,
                field="firewall.cross_arm_cancellation_allowed",
            ),
            _exact_int(self.retry_count, field="firewall.retry_count"),
            _exact_int(
                self.replacement_count, field="firewall.replacement_count"
            ),
            _exact_bool(
                self.partial_results_may_mutate_manifest,
                field="firewall.partial_results_may_mutate_manifest",
            ),
            _exact_bool(
                self.ineligible_jobs_retained_for_report,
                field="firewall.ineligible_jobs_retained_for_report",
            ),
        )
        if actual != expected:
            raise V07C2ParallelManifestError(
                "outcome-driven omission, cancellation, retry, replacement, "
                "or mutation is forbidden"
            )

    @property
    def firewall_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "created_before_target_outcomes": self.created_before_target_outcomes,
            "target_outcomes_opened": self.target_outcomes_opened,
            "test_split_opened": self.test_split_opened,
            "arm_omission_allowed": self.arm_omission_allowed,
            "cross_arm_cancellation_allowed": (
                self.cross_arm_cancellation_allowed
            ),
            "retry_count": self.retry_count,
            "replacement_count": self.replacement_count,
            "partial_results_may_mutate_manifest": (
                self.partial_results_may_mutate_manifest
            ),
            "ineligible_jobs_retained_for_report": (
                self.ineligible_jobs_retained_for_report
            ),
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"firewall_sha256": self.firewall_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "OutcomeFirewall":
        payload = _mapping(value, field="outcome firewall")
        fields = frozenset(
            {
                "schema",
                "created_before_target_outcomes",
                "target_outcomes_opened",
                "test_split_opened",
                "arm_omission_allowed",
                "cross_arm_cancellation_allowed",
                "retry_count",
                "replacement_count",
                "partial_results_may_mutate_manifest",
                "ineligible_jobs_retained_for_report",
                "firewall_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="outcome firewall")
        firewall = cls(
            created_before_target_outcomes=_exact_bool(
                payload["created_before_target_outcomes"],
                field="firewall.created_before_target_outcomes",
            ),
            target_outcomes_opened=_exact_bool(
                payload["target_outcomes_opened"],
                field="firewall.target_outcomes_opened",
            ),
            test_split_opened=_exact_bool(
                payload["test_split_opened"], field="firewall.test_split_opened"
            ),
            arm_omission_allowed=_exact_bool(
                payload["arm_omission_allowed"],
                field="firewall.arm_omission_allowed",
            ),
            cross_arm_cancellation_allowed=_exact_bool(
                payload["cross_arm_cancellation_allowed"],
                field="firewall.cross_arm_cancellation_allowed",
            ),
            retry_count=payload["retry_count"],  # type: ignore[arg-type]
            replacement_count=payload["replacement_count"],  # type: ignore[arg-type]
            partial_results_may_mutate_manifest=_exact_bool(
                payload["partial_results_may_mutate_manifest"],
                field="firewall.partial_results_may_mutate_manifest",
            ),
            ineligible_jobs_retained_for_report=_exact_bool(
                payload["ineligible_jobs_retained_for_report"],
                field="firewall.ineligible_jobs_retained_for_report",
            ),
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(
            payload["firewall_sha256"], field="firewall.firewall_sha256"
        ) != firewall.firewall_sha256:
            raise V07C2ParallelManifestError(
                "outcome-firewall digest disagrees with its contents"
            )
        return firewall


@dataclass(frozen=True, slots=True)
class FastProxyStageSpec:
    """A diagnostic-only, predeclared B2 action-panel stage.

    The proxy is deliberately a separate stage from the registered B2 target.
    It may use a small action panel to answer a cheap implementation question,
    but it can never be reported as B2 efficacy evidence.  The full B2 target
    remains bound to the native 28-action surface for confirmation.
    """

    action_panel: tuple[int, ...] = V07_C2_FAST_PROXY_ACTION_PANEL
    stage: str = V07_C2_FAST_PROXY_STAGE
    label: str = V07_C2_FAST_PROXY_LABEL
    arm: str = "B2"
    evidence_status: str = V07_C2_FAST_PROXY_EVIDENCE_STATUS
    final_evidence: bool = False
    max_action_count: int = V07_C2_FAST_PROXY_MAX_ACTIONS
    full_confirmation_stage: str = V07_C2_FULL_B2_CONFIRMATION_STAGE
    full_confirmation_action_count: int = V07_C2_NATIVE_ACTION_COUNT
    schema: str = V07_C2_FAST_PROXY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != V07_C2_FAST_PROXY_SCHEMA:
            raise V07C2ParallelManifestError("fast-proxy schema is stale")
        if self.stage != V07_C2_FAST_PROXY_STAGE:
            raise V07C2ParallelManifestError("fast-proxy stage kind is stale")
        if self.label != V07_C2_FAST_PROXY_LABEL:
            raise V07C2ParallelManifestError("fast-proxy label is stale")
        if self.arm != "B2":
            raise V07C2ParallelManifestError(
                "fast-proxy stage is reserved for B2"
            )
        if self.evidence_status != V07_C2_FAST_PROXY_EVIDENCE_STATUS:
            raise V07C2ParallelManifestError(
                "fast-proxy evidence status must remain diagnostic-only"
            )
        if _exact_bool(self.final_evidence, field="fast_proxy.final_evidence"):
            raise V07C2ParallelManifestError(
                "fast-proxy cannot be called final evidence"
            )
        if (
            _exact_int(
                self.max_action_count,
                field="fast_proxy.max_action_count",
                minimum=1,
            )
            != V07_C2_FAST_PROXY_MAX_ACTIONS
        ):
            raise V07C2ParallelManifestError(
                "fast-proxy maximum action count must remain 4"
            )
        if self.full_confirmation_stage != V07_C2_FULL_B2_CONFIRMATION_STAGE:
            raise V07C2ParallelManifestError(
                "fast-proxy must promote only to full B2 confirmation"
            )
        if (
            _exact_int(
                self.full_confirmation_action_count,
                field="fast_proxy.full_confirmation_action_count",
                minimum=1,
            )
            != V07_C2_NATIVE_ACTION_COUNT
        ):
            raise V07C2ParallelManifestError(
                "full B2 confirmation must retain native 28 actions"
            )
        object.__setattr__(
            self,
            "action_panel",
            _action_panel(self.action_panel, field="fast_proxy.action_panel"),
        )

    @property
    def stage_label(self) -> str:
        """Stable human-readable label for the separate proxy stage."""

        return self.label

    @property
    def action_ids(self) -> tuple[int, ...]:
        """Alias exposing the predeclared native action IDs."""

        return self.action_panel

    @property
    def panel(self) -> tuple[int, ...]:
        """Short alias for consumers that call the IDs a panel."""

        return self.action_panel

    @property
    def action_panel_size(self) -> int:
        return len(self.action_panel)

    @property
    def action_count(self) -> int:
        return len(self.action_panel)

    @property
    def max_actions(self) -> int:
        return self.max_action_count

    @property
    def is_final_evidence(self) -> bool:
        return self.final_evidence

    @property
    def full_b2_action_count(self) -> int:
        return self.full_confirmation_action_count

    @property
    def confirmation_action_count(self) -> int:
        return self.full_confirmation_action_count

    @property
    def uses_native_28_confirmation(self) -> bool:
        return self.full_b2_is_native_28

    @property
    def proxy_sha256(self) -> str:
        return canonical_sha256(self._body())

    @property
    def full_b2_is_native_28(self) -> bool:
        return self.full_confirmation_action_count == V07_C2_NATIVE_ACTION_COUNT

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "stage": self.stage,
            "label": self.label,
            "arm": self.arm,
            "action_panel": list(self.action_panel),
            "action_panel_size": len(self.action_panel),
            "max_action_count": self.max_action_count,
            "evidence_status": self.evidence_status,
            "final_evidence": self.final_evidence,
            "full_confirmation_stage": self.full_confirmation_stage,
            "full_confirmation_action_count": self.full_confirmation_action_count,
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"proxy_sha256": self.proxy_sha256}

    def verify(self) -> str:
        """Revalidate the proxy and return its content digest."""

        type(self)(
            action_panel=self.action_panel,
            stage=self.stage,
            label=self.label,
            arm=self.arm,
            evidence_status=self.evidence_status,
            final_evidence=self.final_evidence,
            max_action_count=self.max_action_count,
            full_confirmation_stage=self.full_confirmation_stage,
            full_confirmation_action_count=self.full_confirmation_action_count,
            schema=self.schema,
        )
        return self.proxy_sha256

    @classmethod
    def from_mapping(cls, value: object) -> "FastProxyStageSpec":
        payload = _mapping(value, field="fast-proxy stage")
        fields = frozenset(
            {
                "schema",
                "stage",
                "label",
                "arm",
                "action_panel",
                "action_panel_size",
                "max_action_count",
                "evidence_status",
                "final_evidence",
                "full_confirmation_stage",
                "full_confirmation_action_count",
                "proxy_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="fast-proxy stage")
        panel = payload["action_panel"]
        if not isinstance(panel, list):
            raise V07C2ParallelManifestError(
                "fast_proxy.action_panel must be a JSON list"
            )
        panel_size = _exact_int(
            payload["action_panel_size"],
            field="fast_proxy.action_panel_size",
            minimum=1,
        )
        if panel_size != len(panel):
            raise V07C2ParallelManifestError(
                "fast-proxy action panel size disagrees with its contents"
            )
        max_action_count = _exact_int(
            payload["max_action_count"],
            field="fast_proxy.max_action_count",
            minimum=1,
        )
        if max_action_count != V07_C2_FAST_PROXY_MAX_ACTIONS:
            raise V07C2ParallelManifestError(
                "fast-proxy maximum action count drifted"
            )
        spec = cls(
            action_panel=tuple(panel),  # type: ignore[arg-type]
            stage=payload["stage"],  # type: ignore[arg-type]
            label=payload["label"],  # type: ignore[arg-type]
            arm=payload["arm"],  # type: ignore[arg-type]
            evidence_status=payload["evidence_status"],  # type: ignore[arg-type]
            final_evidence=_exact_bool(
                payload["final_evidence"], field="fast_proxy.final_evidence"
            ),
            max_action_count=payload["max_action_count"],  # type: ignore[arg-type]
            full_confirmation_stage=payload[
                "full_confirmation_stage"
            ],  # type: ignore[arg-type]
            full_confirmation_action_count=payload[
                "full_confirmation_action_count"
            ],  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if _digest(payload["proxy_sha256"], field="fast_proxy.proxy_sha256") != spec.proxy_sha256:
            raise V07C2ParallelManifestError(
                "fast-proxy digest disagrees with its contents"
            )
        return spec


# Names used by callers that prefer to spell out that this is the B2 proxy.
FastProxyB2Spec = FastProxyStageSpec
B2FastProxySpec = FastProxyStageSpec
FastProxySpec = FastProxyStageSpec
B2FastProxyStage = FastProxyStageSpec


def _verify_common_block(
    *,
    anchors: tuple[PhysicalAnchorSpec, ...],
    lineages: tuple[LineageAuthority, ...],
    seeds: CommonSeedSchedule,
    budgets: SharedStageBudgets,
) -> tuple[PhysicalAnchorSpec, ...]:
    if not isinstance(anchors, tuple) or any(
        not isinstance(anchor, PhysicalAnchorSpec) for anchor in anchors
    ):
        raise V07C2ParallelManifestError(
            "anchors must be an immutable tuple of PhysicalAnchorSpec"
        )
    ordered = tuple(sorted(anchors, key=lambda anchor: anchor.sort_key))
    if len(ordered) != D2_EXPECTED_ANCHORS:
        raise V07C2ParallelManifestError(
            "parallel manifest requires exactly 20 physical anchors"
        )
    expected_keys = {
        (seed, window)
        for seed in D2_SEEDS
        for window in ("early", "late")
    }
    actual_keys = {(anchor.seed, anchor.window) for anchor in ordered}
    if actual_keys != expected_keys or len(actual_keys) != len(ordered):
        raise V07C2ParallelManifestError(
            "anchors must contain exactly one early and one late anchor per seed"
        )
    anchor_receipts = {anchor.anchor_receipt_sha256 for anchor in ordered}
    anchor_ids = {anchor.anchor_id_sha256 for anchor in ordered}
    if len(anchor_receipts) != len(ordered) or len(anchor_ids) != len(ordered):
        raise V07C2ParallelManifestError(
            "physical anchor receipts and identities must be unique"
        )
    if not isinstance(lineages, tuple) or any(
        not isinstance(lineage, LineageAuthority) for lineage in lineages
    ):
        raise V07C2ParallelManifestError(
            "lineages must be an immutable tuple of LineageAuthority"
        )
    if tuple(lineage.lineage for lineage in lineages) != D2_LINEAGES:
        raise V07C2ParallelManifestError(
            "parallel manifest requires exactly q13-a, q13-b, q13-c in order"
        )
    if len({lineage.authority_sha256 for lineage in lineages}) != len(lineages):
        raise V07C2ParallelManifestError(
            "three lineage authority receipts must be distinct"
        )
    if not isinstance(seeds, CommonSeedSchedule):
        raise V07C2ParallelManifestError("seeds must be CommonSeedSchedule")
    if not isinstance(budgets, SharedStageBudgets):
        raise V07C2ParallelManifestError("budgets must be SharedStageBudgets")
    if tuple(sorted({anchor.seed for anchor in ordered})) != seeds.stage_a_physical_seeds:
        raise V07C2ParallelManifestError(
            "physical anchors disagree with the common Stage-A seed block"
        )
    budgets.verify_against(seeds)
    return ordered


@dataclass(frozen=True, slots=True)
class ParallelArmJobSpec:
    """Standalone immutable dispatch input for one registered candidate arm."""

    manifest_sha256: str
    arm: str
    anchors: tuple[PhysicalAnchorSpec, ...]
    lineages: tuple[LineageAuthority, ...]
    seeds: CommonSeedSchedule
    budgets: SharedStageBudgets
    q2_state_schema: str
    q2_state_schema_sha256: str
    target: TargetAuthority
    protocol: ProtocolBindings
    selection: SelectionRules
    outcome_firewall: OutcomeFirewall
    stage_plan: tuple[str, ...] = V07_C2_STAGE_PLAN
    schema: str = V07_C2_PARALLEL_JOB_SCHEMA
    fast_proxy: FastProxyStageSpec | None = None

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_JOB_SCHEMA:
            raise V07C2ParallelManifestError("parallel job schema is stale")
        object.__setattr__(
            self,
            "manifest_sha256",
            _digest(self.manifest_sha256, field="job.manifest_sha256"),
        )
        if self.arm not in V07_C2_PARALLEL_ARMS:
            raise V07C2ParallelManifestError("job arm is not P0, B1, or B2")
        if not isinstance(self.target, TargetAuthority) or self.target.arm != self.arm:
            raise V07C2ParallelManifestError(
                "job target authority does not match its registered arm"
            )
        ordered = _verify_common_block(
            anchors=self.anchors,
            lineages=self.lineages,
            seeds=self.seeds,
            budgets=self.budgets,
        )
        object.__setattr__(self, "anchors", ordered)
        if (
            self.q2_state_schema != V07_C2_Q2_STATE_SCHEMA
            or self.q2_state_schema_sha256 != V07_C2_Q2_STATE_SCHEMA_SHA256
        ):
            raise V07C2ParallelManifestError("job Q2 state schema/digest drifted")
        if not isinstance(self.protocol, ProtocolBindings):
            raise V07C2ParallelManifestError(
                "job protocol must be ProtocolBindings"
            )
        if not isinstance(self.selection, SelectionRules):
            raise V07C2ParallelManifestError(
                "job selection must be SelectionRules"
            )
        if not isinstance(self.outcome_firewall, OutcomeFirewall):
            raise V07C2ParallelManifestError(
                "job outcome_firewall must be OutcomeFirewall"
            )
        if not isinstance(self.stage_plan, tuple) or self.stage_plan != V07_C2_STAGE_PLAN:
            raise V07C2ParallelManifestError(
                "job must retain the frozen A/B/C gate and report plan"
            )
        if self.arm == "B2":
            if not isinstance(self.fast_proxy, FastProxyStageSpec):
                raise V07C2ParallelManifestError(
                    "B2 job must carry the separately labelled fast-proxy stage"
                )
        elif self.fast_proxy is not None:
            raise V07C2ParallelManifestError(
                "only the B2 job may carry the fast-proxy stage"
            )

    @property
    def job_id(self) -> str:
        return f"v07-c2-{self.arm.lower()}-{self.manifest_sha256[:16]}"

    @property
    def fast_proxy_spec(self) -> FastProxyStageSpec | None:
        return self.fast_proxy

    @property
    def fast_proxy_action_panel(self) -> tuple[int, ...] | None:
        return None if self.fast_proxy is None else self.fast_proxy.action_panel

    @property
    def full_b2_confirmation_action_count(self) -> int | None:
        return None if self.fast_proxy is None else self.fast_proxy.full_b2_action_count

    @property
    def job_sha256(self) -> str:
        return canonical_sha256(self._body())

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "manifest_sha256": self.manifest_sha256,
            "job_id": self.job_id,
            "arm": self.arm,
            "stage_plan": list(self.stage_plan),
            "anchors": [anchor.to_mapping() for anchor in self.anchors],
            "lineages": [lineage.to_mapping() for lineage in self.lineages],
            "seeds": self.seeds.to_mapping(),
            "budgets": self.budgets.to_mapping(),
            "q2_state_schema": self.q2_state_schema,
            "q2_state_schema_sha256": self.q2_state_schema_sha256,
            "target": self.target.to_mapping(),
            "protocol": self.protocol.to_mapping(),
            "selection": self.selection.to_mapping(),
            "outcome_firewall": self.outcome_firewall.to_mapping(),
            "fast_proxy": (
                None if self.fast_proxy is None else self.fast_proxy.to_mapping()
            ),
        }

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {"job_sha256": self.job_sha256}

    def verify(self) -> str:
        type(self)(
            manifest_sha256=self.manifest_sha256,
            arm=self.arm,
            anchors=self.anchors,
            lineages=self.lineages,
            seeds=self.seeds,
            budgets=self.budgets,
            q2_state_schema=self.q2_state_schema,
            q2_state_schema_sha256=self.q2_state_schema_sha256,
            target=self.target,
            protocol=self.protocol,
            selection=self.selection,
            outcome_firewall=self.outcome_firewall,
            stage_plan=self.stage_plan,
            fast_proxy=self.fast_proxy,
            schema=self.schema,
        )
        return self.job_sha256

    @classmethod
    def from_mapping(cls, value: object) -> "ParallelArmJobSpec":
        payload = _mapping(value, field="parallel job")
        fields = frozenset(
            {
                "schema",
                "manifest_sha256",
                "job_id",
                "arm",
                "stage_plan",
                "anchors",
                "lineages",
                "seeds",
                "budgets",
                "q2_state_schema",
                "q2_state_schema_sha256",
                "target",
                "protocol",
                "selection",
                "outcome_firewall",
                "fast_proxy",
                "job_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="parallel job")
        anchors = payload["anchors"]
        lineages = payload["lineages"]
        stage_plan = payload["stage_plan"]
        if not isinstance(anchors, list) or not isinstance(lineages, list):
            raise V07C2ParallelManifestError(
                "parallel job anchors and lineages must be JSON lists"
            )
        if not isinstance(stage_plan, list):
            raise V07C2ParallelManifestError(
                "parallel job stage_plan must be a JSON list"
            )
        fast_proxy_payload = payload["fast_proxy"]
        fast_proxy = (
            None
            if fast_proxy_payload is None
            else FastProxyStageSpec.from_mapping(fast_proxy_payload)
        )
        job = cls(
            manifest_sha256=payload["manifest_sha256"],  # type: ignore[arg-type]
            arm=payload["arm"],  # type: ignore[arg-type]
            anchors=tuple(PhysicalAnchorSpec.from_mapping(item) for item in anchors),
            lineages=tuple(
                LineageAuthority.from_mapping(item) for item in lineages
            ),
            seeds=CommonSeedSchedule.from_mapping(payload["seeds"]),
            budgets=SharedStageBudgets.from_mapping(payload["budgets"]),
            q2_state_schema=payload["q2_state_schema"],  # type: ignore[arg-type]
            q2_state_schema_sha256=payload["q2_state_schema_sha256"],  # type: ignore[arg-type]
            target=TargetAuthority.from_mapping(payload["target"]),
            protocol=ProtocolBindings.from_mapping(payload["protocol"]),
            selection=SelectionRules.from_mapping(payload["selection"]),
            outcome_firewall=OutcomeFirewall.from_mapping(
                payload["outcome_firewall"]
            ),
            stage_plan=tuple(stage_plan),  # type: ignore[arg-type]
            fast_proxy=fast_proxy,
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        if payload["job_id"] != job.job_id:
            raise V07C2ParallelManifestError("parallel job_id drifted")
        if _digest(payload["job_sha256"], field="job.job_sha256") != job.job_sha256:
            raise V07C2ParallelManifestError(
                "parallel job digest disagrees with its contents"
            )
        return job


@dataclass(frozen=True, slots=True)
class V07C2PreOutcomeParallelManifest:
    """Complete pre-outcome authority for P0/B1/B2 and their shared ladder."""

    anchors: tuple[PhysicalAnchorSpec, ...]
    lineages: tuple[LineageAuthority, ...]
    seeds: CommonSeedSchedule
    budgets: SharedStageBudgets
    targets: tuple[TargetAuthority, ...]
    protocol: ProtocolBindings
    selection: SelectionRules
    outcome_firewall: OutcomeFirewall
    q2_state_schema: str = V07_C2_Q2_STATE_SCHEMA
    q2_state_schema_sha256: str = V07_C2_Q2_STATE_SCHEMA_SHA256
    version: int = V07_C2_PARALLEL_MANIFEST_VERSION
    schema: str = V07_C2_PARALLEL_MANIFEST_SCHEMA
    fast_proxy: FastProxyStageSpec = FastProxyStageSpec()

    def __post_init__(self) -> None:
        if self.schema != V07_C2_PARALLEL_MANIFEST_SCHEMA:
            raise V07C2ParallelManifestError("parallel manifest schema is stale")
        version = _exact_int(self.version, field="manifest.version", minimum=1)
        if version != V07_C2_PARALLEL_MANIFEST_VERSION:
            raise V07C2ParallelManifestError("parallel manifest version is stale")
        ordered = _verify_common_block(
            anchors=self.anchors,
            lineages=self.lineages,
            seeds=self.seeds,
            budgets=self.budgets,
        )
        object.__setattr__(self, "anchors", ordered)
        if (
            self.q2_state_schema != V07_C2_Q2_STATE_SCHEMA
            or self.q2_state_schema_sha256 != V07_C2_Q2_STATE_SCHEMA_SHA256
        ):
            raise V07C2ParallelManifestError(
                "parallel manifest Q2 state schema/digest drifted"
            )
        if not isinstance(self.targets, tuple) or any(
            not isinstance(target, TargetAuthority) for target in self.targets
        ):
            raise V07C2ParallelManifestError(
                "targets must be an immutable tuple of TargetAuthority"
            )
        if tuple(target.arm for target in self.targets) != V07_C2_PARALLEL_ARMS:
            raise V07C2ParallelManifestError(
                "parallel manifest must register exactly P0, B1, and B2"
            )
        if self.targets != current_target_authorities():
            raise V07C2ParallelManifestError(
                "target authorities disagree with current target schemas/code"
            )
        if not isinstance(self.protocol, ProtocolBindings):
            raise V07C2ParallelManifestError(
                "protocol must be ProtocolBindings"
            )
        if not isinstance(self.selection, SelectionRules):
            raise V07C2ParallelManifestError(
                "selection must be SelectionRules"
            )
        if not isinstance(self.outcome_firewall, OutcomeFirewall):
            raise V07C2ParallelManifestError(
                "outcome_firewall must be OutcomeFirewall"
            )
        if not isinstance(self.fast_proxy, FastProxyStageSpec):
            raise V07C2ParallelManifestError(
                "manifest must bind a separately labelled B2 fast-proxy stage"
            )

    @property
    def arms(self) -> tuple[str, ...]:
        return tuple(target.arm for target in self.targets)

    @property
    def fast_proxy_stage(self) -> FastProxyStageSpec:
        """Stable alias for the separately labelled B2 proxy stage."""

        return self.fast_proxy

    @property
    def fast_proxy_spec(self) -> FastProxyStageSpec:
        return self.fast_proxy

    @property
    def b2_fast_proxy(self) -> FastProxyStageSpec:
        return self.fast_proxy

    @property
    def fast_proxy_action_panel(self) -> tuple[int, ...]:
        """The predeclared panel used only by the diagnostic proxy."""

        return self.fast_proxy.action_panel

    @property
    def full_b2_confirmation_action_count(self) -> int:
        """Native action width retained by full B2 confirmation."""

        return self.fast_proxy.full_confirmation_action_count

    @property
    def fast_proxy_is_final_evidence(self) -> bool:
        return self.fast_proxy.final_evidence

    @property
    def full_b2_uses_native_28(self) -> bool:
        return self.fast_proxy.full_b2_is_native_28

    def _body(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "version": self.version,
            "arms": list(self.arms),
            "anchors": [anchor.to_mapping() for anchor in self.anchors],
            "lineages": [lineage.to_mapping() for lineage in self.lineages],
            "seeds": self.seeds.to_mapping(),
            "budgets": self.budgets.to_mapping(),
            "q2_state_schema": self.q2_state_schema,
            "q2_state_schema_sha256": self.q2_state_schema_sha256,
            "targets": [target.to_mapping() for target in self.targets],
            "protocol": self.protocol.to_mapping(),
            "selection": self.selection.to_mapping(),
            "outcome_firewall": self.outcome_firewall.to_mapping(),
            "fast_proxy": self.fast_proxy.to_mapping(),
        }

    @property
    def manifest_sha256(self) -> str:
        return canonical_sha256(self._body())

    @property
    def parallel_job_specs(self) -> tuple[ParallelArmJobSpec, ...]:
        """Return all three jobs; callers cannot request an arm subset here."""

        return tuple(
            ParallelArmJobSpec(
                manifest_sha256=self.manifest_sha256,
                arm=target.arm,
                anchors=self.anchors,
                lineages=self.lineages,
                seeds=self.seeds,
                budgets=self.budgets,
                q2_state_schema=self.q2_state_schema,
                q2_state_schema_sha256=self.q2_state_schema_sha256,
                target=target,
                protocol=self.protocol,
                selection=self.selection,
                outcome_firewall=self.outcome_firewall,
                fast_proxy=self.fast_proxy if target.arm == "B2" else None,
            )
            for target in self.targets
        )

    @property
    def file_sha256(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.to_mapping())).hexdigest()

    def to_mapping(self) -> dict[str, object]:
        return self._body() | {
            "jobs": [job.to_mapping() for job in self.parallel_job_specs],
            "manifest_sha256": self.manifest_sha256,
        }

    def verify(self, *, expected_manifest_sha256: str | None = None) -> str:
        reconstructed = type(self)(
            anchors=self.anchors,
            lineages=self.lineages,
            seeds=self.seeds,
            budgets=self.budgets,
            targets=self.targets,
            protocol=self.protocol,
            selection=self.selection,
            outcome_firewall=self.outcome_firewall,
            q2_state_schema=self.q2_state_schema,
            q2_state_schema_sha256=self.q2_state_schema_sha256,
            fast_proxy=self.fast_proxy,
            version=self.version,
            schema=self.schema,
        )
        digest = reconstructed.manifest_sha256
        if expected_manifest_sha256 is not None and digest != _digest(
            expected_manifest_sha256, field="expected_manifest_sha256"
        ):
            raise V07C2ParallelManifestError(
                "parallel manifest digest does not match expected authority"
            )
        if tuple(job.arm for job in reconstructed.parallel_job_specs) != (
            V07_C2_PARALLEL_ARMS
        ):
            raise V07C2ParallelManifestError(
                "parallel manifest failed to derive all three jobs"
            )
        return digest

    @classmethod
    def from_mapping(cls, value: object) -> "V07C2PreOutcomeParallelManifest":
        payload = _mapping(value, field="parallel manifest")
        fields = frozenset(
            {
                "schema",
                "version",
                "arms",
                "anchors",
                "lineages",
                "seeds",
                "budgets",
                "q2_state_schema",
                "q2_state_schema_sha256",
                "targets",
                "protocol",
                "selection",
                "outcome_firewall",
                "fast_proxy",
                "jobs",
                "manifest_sha256",
            }
        )
        _exact_fields(payload, fields=fields, label="parallel manifest")
        for field in ("arms", "anchors", "lineages", "targets", "jobs"):
            if not isinstance(payload[field], list):
                raise V07C2ParallelManifestError(
                    f"parallel manifest {field} must be a JSON list"
                )
        if tuple(payload["arms"]) != V07_C2_PARALLEL_ARMS:  # type: ignore[arg-type]
            raise V07C2ParallelManifestError(
                "serialized manifest must name exactly P0, B1, and B2"
            )
        manifest = cls(
            anchors=tuple(
                PhysicalAnchorSpec.from_mapping(item)
                for item in payload["anchors"]  # type: ignore[union-attr]
            ),
            lineages=tuple(
                LineageAuthority.from_mapping(item)
                for item in payload["lineages"]  # type: ignore[union-attr]
            ),
            seeds=CommonSeedSchedule.from_mapping(payload["seeds"]),
            budgets=SharedStageBudgets.from_mapping(payload["budgets"]),
            targets=tuple(
                TargetAuthority.from_mapping(item)
                for item in payload["targets"]  # type: ignore[union-attr]
            ),
            protocol=ProtocolBindings.from_mapping(payload["protocol"]),
            selection=SelectionRules.from_mapping(payload["selection"]),
            outcome_firewall=OutcomeFirewall.from_mapping(
                payload["outcome_firewall"]
            ),
            q2_state_schema=payload["q2_state_schema"],  # type: ignore[arg-type]
            q2_state_schema_sha256=payload["q2_state_schema_sha256"],  # type: ignore[arg-type]
            fast_proxy=FastProxyStageSpec.from_mapping(payload["fast_proxy"]),
            version=payload["version"],  # type: ignore[arg-type]
            schema=payload["schema"],  # type: ignore[arg-type]
        )
        supplied_manifest_sha = _digest(
            payload["manifest_sha256"], field="manifest.manifest_sha256"
        )
        if supplied_manifest_sha != manifest.manifest_sha256:
            raise V07C2ParallelManifestError(
                "parallel manifest digest disagrees with its contents"
            )
        supplied_jobs = tuple(
            ParallelArmJobSpec.from_mapping(item)
            for item in payload["jobs"]  # type: ignore[union-attr]
        )
        expected_jobs = manifest.parallel_job_specs
        if tuple(job.to_mapping() for job in supplied_jobs) != tuple(
            job.to_mapping() for job in expected_jobs
        ):
            raise V07C2ParallelManifestError(
                "serialized jobs omit, cancel, replace, or redefine a registered arm"
            )
        return manifest


def build_v07_c2_parallel_manifest(
    *,
    anchors: Sequence[PhysicalAnchorSpec],
    lineages: Sequence[LineageAuthority],
    seeds: CommonSeedSchedule,
    budgets: SharedStageBudgets,
    keyed_field_implementation_sha256: str,
    nonfocal_tape_implementation_sha256: str,
    stage_a_rules_sha256: str,
    stage_b_rules_sha256: str,
    stage_c_rules_sha256: str,
    practical_tie_band_fraction_hex: str,
    service_guard_sha256: str,
    fast_proxy_action_panel: Sequence[int] | None = None,
    fast_proxy: FastProxyStageSpec | None = None,
) -> V07C2PreOutcomeParallelManifest:
    """Build the only admitted complete three-arm pre-outcome manifest."""

    if fast_proxy is None:
        fast_proxy = FastProxyStageSpec(
            action_panel=(
                V07_C2_FAST_PROXY_ACTION_PANEL
                if fast_proxy_action_panel is None
                else tuple(fast_proxy_action_panel)
            )
        )
    elif (
        fast_proxy_action_panel is not None
        and tuple(fast_proxy_action_panel) != fast_proxy.action_panel
    ):
        raise V07C2ParallelManifestError(
            "fast-proxy action panel was redefined by the builder"
        )

    return V07C2PreOutcomeParallelManifest(
        anchors=tuple(anchors),
        lineages=tuple(lineages),
        seeds=seeds,
        budgets=budgets,
        targets=current_target_authorities(),
        protocol=ProtocolBindings(
            keyed_field_implementation_sha256=keyed_field_implementation_sha256,
            nonfocal_tape_implementation_sha256=(
                nonfocal_tape_implementation_sha256
            ),
            stage_a_rules_sha256=stage_a_rules_sha256,
            stage_b_rules_sha256=stage_b_rules_sha256,
            stage_c_rules_sha256=stage_c_rules_sha256,
        ),
        selection=SelectionRules(
            practical_tie_band_fraction_hex=practical_tie_band_fraction_hex,
            service_guard_sha256=service_guard_sha256,
        ),
        outcome_firewall=OutcomeFirewall(),
        fast_proxy=fast_proxy,
    )


def load_v07_c2_parallel_manifest(
    payload: object, *, expected_manifest_sha256: str | None = None
) -> V07C2PreOutcomeParallelManifest:
    """Strictly parse and validate a canonical manifest mapping."""

    manifest = V07C2PreOutcomeParallelManifest.from_mapping(payload)
    manifest.verify(expected_manifest_sha256=expected_manifest_sha256)
    return manifest


__all__ = [
    "CommonSeedSchedule",
    "B2FastProxySpec",
    "B2FastProxyStage",
    "FastProxyB2Spec",
    "FastProxySpec",
    "FastProxyStageSpec",
    "LineageAuthority",
    "OutcomeFirewall",
    "ParallelArmJobSpec",
    "PhysicalAnchorSpec",
    "ProtocolBindings",
    "SelectionRules",
    "SharedStageBudgets",
    "TargetAuthority",
    "V07C2ParallelManifestError",
    "V07C2PreOutcomeParallelManifest",
    "V07_C2_ANCHOR_SELECTOR",
    "V07_C2_FAST_PROXY_ACTION_PANEL_MAX",
    "V07_C2_FAST_PROXY_ACTION_PANEL",
    "V07_C2_FAST_PROXY_EVIDENCE_STATUS",
    "V07_C2_FAST_PROXY_LABEL",
    "V07_C2_FAST_PROXY_MAX_ACTIONS",
    "V07_C2_FAST_PROXY_SCHEMA",
    "V07_C2_FAST_PROXY_STAGE",
    "V07_C2_FAST_PROXY_STAGE_LABEL",
    "V07_C2_FULL_B2_CONFIRMATION_LABEL",
    "V07_C2_FULL_B2_CONFIRMATION_STAGE",
    "V07_C2_FULL_B2_NATIVE_ACTION_COUNT",
    "V07_C2_B2_NATIVE_ACTION_COUNT",
    "V07_C2_KEYED_FIELD_GRAMMAR",
    "V07_C2_NONFOCAL_TAPE_GRAMMAR",
    "V07_C2_PARALLEL_ARMS",
    "V07_C2_PARALLEL_JOB_SCHEMA",
    "V07_C2_PARALLEL_MANIFEST_SCHEMA",
    "V07_C2_PARALLEL_STAGES",
    "V07_C2_NATIVE_ACTION_COUNT",
    "V07_C2_SELECTION_STATISTIC",
    "build_v07_c2_parallel_manifest",
    "canonical_json_bytes",
    "canonical_sha256",
    "current_target_authorities",
    "load_v07_c2_parallel_manifest",
]
