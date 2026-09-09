"""Pre-decision C1 Energy-Frontier source selection for MCRL V0.3.

The C1 Catfish has two deliberately separate pieces of lineage:

* EXP supplies *where to look*: a disjoint, TRAIN-only dull rollout ranks
  sealed anchors and focal users on a lower-frontier source score;
* ACRM supplies *how to compare*: after an anchor/user has been selected, the
  frozen Main action is paired with every distinct legal physical alternative.

This module implements only that source-selection seam.  It does not run the
simulator, evaluate either branch, calculate a target, or inspect a candidate
outcome.  Consequently a C1 pair's ``zeta``/reward/rate/power cannot leak into
selection through this API.  The selected opportunities are intended to be
fed to ``ee_axis_opening_source`` by a separate runner.

The old C1 EXP corpus remains lineage authority only.  Its historical replay
rows are not loaded here and are not silently reused as V0.3 opening pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
from typing import Iterable, Any

import numpy as np

from ..env.action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    SlotTable,
    assert_selected_actions_valid,
)
from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_STATE_SCHEMA, EE_AXIS_STATE_SCHEMA_SHA256


C1_SELECTOR_SCHEMA = "multi-catfish-mcrl-v03-c1-predecision-selector-v1"
"""Schema for a sealed C1 informed or neutral source plan."""

C1_DULL_ROLLOUT_SCHEMA = "multi-catfish-mcrl-v03-c1-dull-rollout-record-v1"
"""Schema for the source-only EXP ranking records."""

C1_INFORMED_SOURCE_RULE = "c1-exp-dull-rollout-lower-frontier-v1"
"""EXP source rule: lower-frontier source strata, before pair evaluation."""

C1_NEUTRAL_SOURCE_RULE = "c1-equal-budget-uniform-predecision-v1"
"""Equal-budget neutral source rule for the C1 control."""

C1_CLUSTER_NEUTRAL_SOURCE_RULE = (
    "c1-cluster-profile-matched-randomized-predecision-v2"
)
"""Seeded C1 control matched on each anchor's user/alternative profile."""

C1_ACRM_PAIR_RULE = "c1-acrm-reference-anchored-pair-v1"
"""ACRM is pair construction, not an additive reward or selector score."""

C1_TRAIN_PARTITION = "TRAIN"
C1_DULL_ROLLOUT_KIND = "dull-rollout"

PhysicalKey = tuple[int, int]
PhysicalKeyOrNone = PhysicalKey | None


class C1SelectorContractError(MCRLContractError):
    """A C1 source record or selection violates the V0.3 contract."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C1SelectorContractError(f"{field} must be lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise C1SelectorContractError(f"{field} must be a nonempty trimmed string")
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise C1SelectorContractError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _finite_float(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise C1SelectorContractError(f"{field} must be finite")
    converted = float(value)
    if not math.isfinite(converted):
        raise C1SelectorContractError(f"{field} must be finite")
    return converted


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    ndim: int,
) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise C1SelectorContractError(f"{field} has an invalid array") from error
    if array.ndim != ndim:
        raise C1SelectorContractError(f"{field} must be {ndim}-dimensional")
    try:
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise C1SelectorContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise C1SelectorContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _integer_vector(value: object, *, field: str) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1 or not np.issubdtype(array.dtype, np.integer):
        raise C1SelectorContractError(f"{field} must be a one-dimensional integer vector")
    if np.issubdtype(array.dtype, np.bool_):
        raise C1SelectorContractError(f"{field} must not be Boolean")
    return _immutable_array(
        array, field=field, dtype=np.dtype(np.int64), ndim=1
    )


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _physical_key(table: SlotTable, action: int) -> PhysicalKeyOrNone:
    """Return a sealed action's physical identity; NO_OP has no identity."""

    if action == NO_OP_ACTION:
        return None
    if not 0 <= action < NUM_ACTIONS or not bool(table.mask[action]):
        raise C1SelectorContractError(
            f"action {action} is not legal under the sealed slot table"
        )
    return int(table.norad_ids[action]), int(table.cell_ids[action])


def _copy_slot_table(value: object, *, field: str) -> SlotTable:
    if not isinstance(value, SlotTable):
        raise C1SelectorContractError(f"{field} must contain SlotTable values")
    norads = np.asarray(value.norad_ids)
    cells = np.asarray(value.cell_ids)
    mask = np.asarray(value.mask)
    if not np.issubdtype(norads.dtype, np.integer) or not np.issubdtype(
        cells.dtype, np.integer
    ):
        raise C1SelectorContractError(f"{field} identities must be integer arrays")
    if mask.dtype != np.bool_:
        raise C1SelectorContractError(f"{field} mask must be Boolean")
    try:
        copied = SlotTable(
            _immutable_array(
                norads, field=f"{field}.norad_ids", dtype=np.dtype(np.int64), ndim=1
            ),
            _immutable_array(
                cells, field=f"{field}.cell_ids", dtype=np.dtype(np.int64), ndim=1
            ),
            _immutable_array(
                mask, field=f"{field}.mask", dtype=np.dtype(np.bool_), ndim=1
            ),
        )
    except (MCRLContractError, ValueError) as error:
        raise C1SelectorContractError(f"{field} is not a valid sealed slot table") from error
    return copied


def _slot_table_payload(table: SlotTable) -> dict[str, object]:
    return {
        "norad_ids": [int(value) for value in table.norad_ids.tolist()],
        "cell_ids": [int(value) for value in table.cell_ids.tolist()],
        "mask": [bool(value) for value in table.mask.tolist()],
    }


def _physical_key_valid(value: object, *, field: str, allow_none: bool) -> None:
    if value is None:
        if allow_none:
            return
        raise C1SelectorContractError(f"{field} must name a physical key")
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(part) is not int for part in value)
    ):
        raise C1SelectorContractError(f"{field} must be a (norad_id, cell_id) tuple")


def _lower_count(total: int, fraction: float, *, field: str) -> int:
    if total <= 0:
        raise C1SelectorContractError(f"{field} cannot rank an empty population")
    value = _finite_float(fraction, field=field)
    if not 0.0 < value <= 1.0:
        raise C1SelectorContractError(f"{field} must be in (0,1]")
    return max(1, min(total, int(math.ceil(total * value))))


def _stratum(rank: int, selected_count: int) -> str:
    return "lower" if rank < selected_count else "upper"


@dataclass(frozen=True)
class C1FrontierConfig:
    """Pre-outcome rank quotas for deterministic lower-frontier selection."""

    lower_anchor_fraction: float = 0.5
    lower_user_fraction: float = 0.5
    max_anchors: int | None = None
    max_focal_users_per_anchor: int | None = None

    def verify(self) -> None:
        _lower_count(1, self.lower_anchor_fraction, field="lower_anchor_fraction")
        _lower_count(1, self.lower_user_fraction, field="lower_user_fraction")
        for field in ("max_anchors", "max_focal_users_per_anchor"):
            value = getattr(self, field)
            if value is not None and (type(value) is not int or value <= 0):
                raise C1SelectorContractError(
                    f"{field} must be a positive exact integer when supplied"
                )


@dataclass(frozen=True)
class C1DullRolloutRecord:
    """One source-only TRAIN dull-rollout anchor.

    ``frontier_score`` and ``user_frontier_scores`` are source-generation
    quantities.  They are deliberately not candidate-vs-Main outcomes and
    carry no rate, power, reward, or ``zeta`` field.  The reference action and
    slot tables are sealed Main context supplied by the runner.
    """

    record_id: str
    anchor_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    state_schema: str
    state_schema_sha256: str
    source_seed: int
    step_index: int
    partition: str
    rollout_kind: str
    policy_name: str
    frontier_score: float
    user_frontier_scores: np.ndarray
    reference_actions: np.ndarray
    slot_tables: tuple[SlotTable, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "user_frontier_scores",
            _immutable_array(
                self.user_frontier_scores,
                field="user_frontier_scores",
                dtype=np.dtype(np.float64),
                ndim=1,
            ),
        )
        object.__setattr__(
            self,
            "reference_actions",
            _integer_vector(self.reference_actions, field="reference_actions"),
        )
        object.__setattr__(
            self,
            "slot_tables",
            tuple(
                _copy_slot_table(table, field=f"slot_tables[{index}]")
                for index, table in enumerate(tuple(self.slot_tables))
            ),
        )

    @property
    def source_record_sha256(self) -> str:
        """Stable digest of this source record's predecision payload."""

        return self.verify()

    def verify(self) -> str:
        _text(self.record_id, field="record_id")
        for field in (
            "anchor_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "state_schema_sha256",
        ):
            _digest(getattr(self, field), field=field)
        _text(self.state_schema, field="state_schema")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise C1SelectorContractError(
                "C1 source record state schema is not the current V0.3 causal state"
            )
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise C1SelectorContractError(
                "C1 source record state schema digest is not current"
            )
        _text(self.policy_name, field="policy_name")
        if self.partition != C1_TRAIN_PARTITION:
            raise C1SelectorContractError(
                "C1 dull-rollout records must be from the TRAIN partition"
            )
        if self.rollout_kind != C1_DULL_ROLLOUT_KIND:
            raise C1SelectorContractError(
                "C1 source records must be explicitly marked dull-rollout"
            )
        _exact_nonnegative_int(self.source_seed, field="source_seed")
        _exact_nonnegative_int(self.step_index, field="step_index")
        _finite_float(self.frontier_score, field="frontier_score")
        scores = np.asarray(self.user_frontier_scores)
        actions = np.asarray(self.reference_actions)
        if scores.ndim != 1 or actions.ndim != 1 or scores.size != actions.size:
            raise C1SelectorContractError(
                "user frontier scores and reference actions must have one row per user"
            )
        if not np.all(np.isfinite(scores)):
            raise C1SelectorContractError("user_frontier_scores must be finite")
        if len(self.slot_tables) != scores.size or not self.slot_tables:
            raise C1SelectorContractError(
                "slot table count must equal the positive user count"
            )
        try:
            legal = assert_selected_actions_valid(actions, self.slot_tables)
        except (MCRLContractError, ValueError) as error:
            raise C1SelectorContractError(
                f"reference_actions are not legal under the sealed Main masks: {error}"
            ) from error
        if not np.array_equal(legal, actions):
            raise C1SelectorContractError("reference_actions changed during validation")
        payload = {
            "schema": C1_DULL_ROLLOUT_SCHEMA,
            "record_id": self.record_id,
            "anchor_sha256": self.anchor_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            "source_seed": self.source_seed,
            "step_index": self.step_index,
            "partition": self.partition,
            "rollout_kind": self.rollout_kind,
            "policy_name": self.policy_name,
            "frontier_score_hex": float(self.frontier_score).hex(),
            "user_frontier_scores_hex": [
                float(value).hex() for value in scores.tolist()
            ],
            "reference_actions": [int(value) for value in actions.tolist()],
            "slot_tables": [_slot_table_payload(table) for table in self.slot_tables],
        }
        return _canonical_sha256(payload)


@dataclass(frozen=True)
class C1UnilateralOpportunity:
    """One sealed ACRM candidate-vs-frozen-Main action pair.

    This is still pre-outcome data.  The canonical opening producer later
    attaches raw rates/power and computes ``zeta_1``; this record intentionally
    cannot carry any of those fields.
    """

    anchor_sha256: str
    source_record_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    state_schema: str
    state_schema_sha256: str
    step_index: int
    source_rule: str
    acrm_pair_rule: str
    anchor_rank: int
    anchor_stratum: str
    focal_user: int
    user_rank: int
    user_stratum: str
    reference_action: int
    candidate_action: int
    reference_physical_key: PhysicalKeyOrNone
    candidate_physical_key: PhysicalKey
    reference_actions: np.ndarray
    candidate_actions: np.ndarray
    action_mask: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference_actions",
            _integer_vector(self.reference_actions, field="reference_actions"),
        )
        object.__setattr__(
            self,
            "candidate_actions",
            _integer_vector(self.candidate_actions, field="candidate_actions"),
        )
        object.__setattr__(
            self,
            "action_mask",
            _immutable_array(
                self.action_mask,
                field="action_mask",
                dtype=np.dtype(np.bool_),
                ndim=1,
            ),
        )

    @property
    def opportunity_key(self) -> tuple[str, int, PhysicalKey]:
        return self.anchor_sha256, self.focal_user, self.candidate_physical_key

    def verify(self) -> None:
        for field in (
            "anchor_sha256",
            "source_record_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "state_schema_sha256",
        ):
            _digest(getattr(self, field), field=field)
        _text(self.state_schema, field="state_schema")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise C1SelectorContractError(
                "C1 opportunity state schema is not the current V0.3 causal state"
            )
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise C1SelectorContractError(
                "C1 opportunity state schema digest is not current"
            )
        if self.source_rule not in (
            C1_INFORMED_SOURCE_RULE,
            C1_NEUTRAL_SOURCE_RULE,
            C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        ):
            raise C1SelectorContractError("unsupported C1 source rule")
        if self.acrm_pair_rule != C1_ACRM_PAIR_RULE:
            raise C1SelectorContractError("unsupported C1 ACRM pair rule")
        _exact_nonnegative_int(self.step_index, field="step_index")
        _exact_nonnegative_int(self.anchor_rank, field="anchor_rank")
        _exact_nonnegative_int(self.user_rank, field="user_rank")
        _exact_nonnegative_int(self.focal_user, field="focal_user")
        if self.anchor_stratum not in ("lower", "upper"):
            raise C1SelectorContractError("anchor_stratum must be lower or upper")
        if self.user_stratum not in ("lower", "upper"):
            raise C1SelectorContractError("user_stratum must be lower or upper")
        if type(self.reference_action) is not int or type(self.candidate_action) is not int:
            raise C1SelectorContractError("opening actions must be exact integers")
        _physical_key_valid(
            self.reference_physical_key,
            field="reference_physical_key",
            allow_none=True,
        )
        _physical_key_valid(
            self.candidate_physical_key,
            field="candidate_physical_key",
            allow_none=False,
        )
        if self.reference_physical_key == self.candidate_physical_key:
            raise C1SelectorContractError(
                "candidate must change the focal physical association"
            )
        reference = np.asarray(self.reference_actions)
        candidate = np.asarray(self.candidate_actions)
        mask = np.asarray(self.action_mask)
        if reference.ndim != 1 or candidate.shape != reference.shape:
            raise C1SelectorContractError("reference/candidate action vectors disagree")
        if self.focal_user >= reference.size:
            raise C1SelectorContractError("focal_user lies outside joint action vectors")
        if mask.shape != (NUM_ACTIONS,) or mask.dtype != np.bool_:
            raise C1SelectorContractError(
                f"action_mask must have Boolean shape ({NUM_ACTIONS},)"
            )
        if reference.flags.writeable or candidate.flags.writeable or mask.flags.writeable:
            raise C1SelectorContractError("opportunity arrays must be immutable")
        if int(reference[self.focal_user]) != self.reference_action:
            raise C1SelectorContractError("reference scalar and vector disagree")
        if int(candidate[self.focal_user]) != self.candidate_action:
            raise C1SelectorContractError("candidate scalar and vector disagree")
        if not np.array_equal(
            np.delete(reference, self.focal_user),
            np.delete(candidate, self.focal_user),
        ):
            raise C1SelectorContractError(
                "C1 ACRM candidate must differ only in the focal user action"
            )
        if not 0 <= self.candidate_action < NUM_ACTIONS or not bool(
            mask[self.candidate_action]
        ):
            raise C1SelectorContractError("candidate action is not sealed legal")
        if self.reference_action == NO_OP_ACTION:
            if bool(np.any(mask)):
                raise C1SelectorContractError(
                    "reference NO_OP is illegal while a focal action is available"
                )
        elif not 0 <= self.reference_action < NUM_ACTIONS or not bool(
            mask[self.reference_action]
        ):
            raise C1SelectorContractError("reference action is not sealed legal")


@dataclass(frozen=True)
class C1SourceSelection:
    """A sealed C1 informed or neutral source plan over one batch of anchors."""

    selector_schema: str
    source_rule: str
    acrm_pair_rule: str
    partition: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    state_schema: str
    state_schema_sha256: str
    eligible_anchor_sha256s: tuple[str, ...]
    selected_anchor_sha256s: tuple[str, ...]
    eligible_focal_users: tuple[tuple[str, int], ...]
    selected_focal_users: tuple[tuple[str, int], ...]
    all_opportunities: tuple[C1UnilateralOpportunity, ...]
    opportunities: tuple[C1UnilateralOpportunity, ...]

    @property
    def route(self) -> str:
        return "C1"

    @property
    def budget(self) -> int:
        """Number of route rows emitted to the C1 opening producer."""

        return len(self.opportunities)

    def verify(self) -> None:
        if self.selector_schema != C1_SELECTOR_SCHEMA:
            raise C1SelectorContractError("unsupported C1 selector schema")
        if self.source_rule not in (
            C1_INFORMED_SOURCE_RULE,
            C1_NEUTRAL_SOURCE_RULE,
            C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        ):
            raise C1SelectorContractError("unsupported C1 selection source rule")
        if self.acrm_pair_rule != C1_ACRM_PAIR_RULE:
            raise C1SelectorContractError("selection ACRM rule drifted")
        if self.partition != C1_TRAIN_PARTITION:
            raise C1SelectorContractError("C1 selections must remain TRAIN-only")
        _digest(self.source_manifest_sha256, field="source_manifest_sha256")
        _digest(self.checkpoint_sha256, field="checkpoint_sha256")
        _digest(self.state_schema_sha256, field="state_schema_sha256")
        _text(self.state_schema, field="state_schema")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise C1SelectorContractError(
                "C1 selection state schema is not the current V0.3 causal state"
            )
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise C1SelectorContractError(
                "C1 selection state schema digest is not current"
            )
        if not self.all_opportunities or not self.opportunities:
            raise C1SelectorContractError("C1 selection must have positive budget")
        eligible_anchors = tuple(self.eligible_anchor_sha256s)
        selected_anchors = tuple(self.selected_anchor_sha256s)
        for index, digest in enumerate(eligible_anchors):
            _digest(digest, field=f"eligible_anchor_sha256s[{index}]")
        for index, digest in enumerate(selected_anchors):
            _digest(digest, field=f"selected_anchor_sha256s[{index}]")
        if len(set(eligible_anchors)) != len(eligible_anchors):
            raise C1SelectorContractError("eligible anchor digests must be unique")
        if len(set(selected_anchors)) != len(selected_anchors):
            raise C1SelectorContractError("selected anchor digests must be unique")
        if not set(selected_anchors).issubset(set(eligible_anchors)):
            raise C1SelectorContractError("selected anchor is outside eligible universe")

        def _users(values: tuple[tuple[str, int], ...], *, field: str) -> set[tuple[str, int]]:
            result: set[tuple[str, int]] = set()
            for index, item in enumerate(values):
                if (
                    not isinstance(item, tuple)
                    or len(item) != 2
                    or not isinstance(item[0], str)
                    or type(item[1]) is not int
                ):
                    raise C1SelectorContractError(
                        f"{field}[{index}] must be (anchor_sha256, focal_user)"
                    )
                _digest(item[0], field=f"{field}[{index}].anchor_sha256")
                _exact_nonnegative_int(item[1], field=f"{field}[{index}].focal_user")
                result.add(item)
            if len(result) != len(values):
                raise C1SelectorContractError(f"{field} must not contain duplicates")
            return result

        eligible_users = _users(self.eligible_focal_users, field="eligible_focal_users")
        selected_users = _users(self.selected_focal_users, field="selected_focal_users")
        if not selected_users.issubset(eligible_users):
            raise C1SelectorContractError("selected focal user is outside eligible universe")

        all_keys: set[tuple[str, int, PhysicalKey]] = set()
        selected_keys: set[tuple[str, int, PhysicalKey]] = set()
        for row in self.all_opportunities:
            row.verify()
            if row.source_rule != self.source_rule:
                raise C1SelectorContractError("informed opportunity source rule drifted")
            if (
                row.source_manifest_sha256 != self.source_manifest_sha256
                or row.checkpoint_sha256 != self.checkpoint_sha256
                or row.state_schema != self.state_schema
                or row.state_schema_sha256 != self.state_schema_sha256
            ):
                raise C1SelectorContractError("opportunity lineage disagrees with selection")
            if row.anchor_sha256 not in eligible_anchors:
                raise C1SelectorContractError("opportunity anchor is not eligible")
            if row.opportunity_key in all_keys:
                raise C1SelectorContractError("duplicate physical opportunity")
            all_keys.add(row.opportunity_key)

        all_object_keys = {row.opportunity_key for row in self.all_opportunities}
        for row in self.opportunities:
            row.verify()
            if row.source_rule != self.source_rule:
                raise C1SelectorContractError("selected opportunity source rule drifted")
            if row.opportunity_key not in all_object_keys:
                raise C1SelectorContractError("selected opportunity is outside universe")
            if row.anchor_sha256 not in selected_anchors:
                raise C1SelectorContractError("selected opportunity anchor is not selected")
            if (row.anchor_sha256, row.focal_user) not in selected_users:
                raise C1SelectorContractError("selected opportunity user is not selected")
            if self.source_rule == C1_INFORMED_SOURCE_RULE and (
                row.anchor_stratum != "lower" or row.user_stratum != "lower"
            ):
                raise C1SelectorContractError(
                    "informed opportunity is outside the lower frontier strata"
                )
            if row.opportunity_key in selected_keys:
                raise C1SelectorContractError("duplicate selected physical opportunity")
            selected_keys.add(row.opportunity_key)

        observed_all_users = {(row.anchor_sha256, row.focal_user) for row in self.all_opportunities}
        observed_selected_users = {
            (row.anchor_sha256, row.focal_user) for row in self.opportunities
        }
        if observed_all_users != eligible_users:
            raise C1SelectorContractError("eligible focal-user universe disagrees with rows")
        if observed_selected_users != selected_users:
            raise C1SelectorContractError("selected focal-user universe disagrees with rows")
        if self.source_rule in (
            C1_INFORMED_SOURCE_RULE,
            C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        ):
            # EXP selection keeps the ACRM promise: once a lower-frontier
            # user is selected, every distinct legal physical alternative is
            # emitted.  The cluster-matched neutral control preserves that
            # same sampling unit.  Only the legacy row-budget neutral control
            # is exempt because it samples individual opportunities.
            all_by_user: dict[
                tuple[str, int], set[tuple[str, int, PhysicalKey]]
            ] = {}
            for row in self.all_opportunities:
                all_by_user.setdefault(
                    (row.anchor_sha256, row.focal_user), set()
                ).add(row.opportunity_key)
            selected_by_user: dict[
                tuple[str, int], set[tuple[str, int, PhysicalKey]]
            ] = {}
            for row in self.opportunities:
                selected_by_user.setdefault(
                    (row.anchor_sha256, row.focal_user), set()
                ).add(row.opportunity_key)
            for user in selected_users:
                all_for_user = all_by_user.get(user, set())
                selected_for_user = selected_by_user.get(user, set())
                if selected_for_user != all_for_user:
                    raise C1SelectorContractError(
                        "informed C1 selection omitted a legal physical alternative"
                    )


def _validate_records(
    records: Iterable[C1DullRolloutRecord],
) -> tuple[C1DullRolloutRecord, ...]:
    materialized = tuple(records)
    if not materialized:
        raise C1SelectorContractError("C1 source record set is empty")
    for index, record in enumerate(materialized):
        if not isinstance(record, C1DullRolloutRecord):
            raise C1SelectorContractError(
                f"records[{index}] must be C1DullRolloutRecord"
            )
        record.verify()
    if len({record.record_id for record in materialized}) != len(materialized):
        raise C1SelectorContractError("dull-rollout record IDs must be unique")
    if len({record.anchor_sha256 for record in materialized}) != len(materialized):
        raise C1SelectorContractError("dull-rollout anchors must be disjoint")
    lineage = {
        (
            record.source_manifest_sha256,
            record.checkpoint_sha256,
            record.state_schema,
            record.state_schema_sha256,
            record.partition,
        )
        for record in materialized
    }
    if len(lineage) != 1:
        raise C1SelectorContractError(
            "C1 source records mix source manifest, Main checkpoint, or state schema"
        )
    return materialized


def _opportunities_for_record(
    record: C1DullRolloutRecord,
    *,
    anchor_rank: int,
    anchor_stratum: str,
    user_selected_count: int,
) -> tuple[
    tuple[int, ...],
    tuple[C1UnilateralOpportunity, ...],
    tuple[C1UnilateralOpportunity, ...],
]:
    """Build every distinct legal physical alternative without physics calls."""

    users: list[tuple[int, float, tuple[tuple[int, int], ...]]] = []
    rows: list[tuple[int, int, float, int, C1UnilateralOpportunity]] = []
    for focal_user, table in enumerate(record.slot_tables):
        reference_action = int(record.reference_actions[focal_user])
        reference_key = _physical_key(table, reference_action)
        # The canonical environment rejects NO_OP whenever a valid action
        # exists; record.verify() already enforces this for the Main vector.
        by_physical: dict[PhysicalKey, int] = {}
        for candidate_action in np.flatnonzero(table.mask).tolist():
            action = int(candidate_action)
            key = _physical_key(table, action)
            if key is None or key == reference_key:
                continue
            # An action-slot alias is not a second physical alternative.  The
            # lowest action slot is the deterministic representative.
            by_physical.setdefault(key, action)
        if not by_physical:
            continue
        ordered_candidates = tuple(
            sorted(by_physical.items(), key=lambda item: (item[0][0], item[0][1], item[1]))
        )
        users.append(
            (
                focal_user,
                float(record.user_frontier_scores[focal_user]),
                ordered_candidates,
            )
        )

    users.sort(key=lambda item: (item[1], item[0]))
    if not users:
        return (), ()
    selected_users = tuple(
        user[0]
        for user in users[:user_selected_count]
    )
    selected_set = set(selected_users)
    for user_rank, (focal_user, _score, alternatives) in enumerate(users):
        user_stratum = _stratum(user_rank, user_selected_count)
        for candidate_key, candidate_action in alternatives:
            candidate_actions = np.array(
                record.reference_actions, dtype=np.int64, copy=True
            )
            candidate_actions[focal_user] = int(candidate_action)
            candidate_actions.setflags(write=False)
            row = C1UnilateralOpportunity(
                anchor_sha256=record.anchor_sha256,
                source_record_sha256=record.source_record_sha256,
                source_manifest_sha256=record.source_manifest_sha256,
                checkpoint_sha256=record.checkpoint_sha256,
                state_schema=record.state_schema,
                state_schema_sha256=record.state_schema_sha256,
                step_index=record.step_index,
                source_rule=C1_INFORMED_SOURCE_RULE,
                acrm_pair_rule=C1_ACRM_PAIR_RULE,
                anchor_rank=anchor_rank,
                anchor_stratum=anchor_stratum,
                focal_user=focal_user,
                user_rank=user_rank,
                user_stratum=user_stratum,
                reference_action=int(record.reference_actions[focal_user]),
                candidate_action=int(candidate_action),
                reference_physical_key=_physical_key(
                    record.slot_tables[focal_user],
                    int(record.reference_actions[focal_user]),
                ),
                candidate_physical_key=candidate_key,
                reference_actions=record.reference_actions,
                candidate_actions=candidate_actions,
                action_mask=record.slot_tables[focal_user].mask,
            )
            row.verify()
            rows.append((focal_user, user_rank, float(_score), int(candidate_action), row))
    rows.sort(key=lambda item: (item[0], item[3]))
    return (
        selected_users,
        tuple(item[-1] for item in rows if item[0] in selected_set),
        tuple(item[-1] for item in rows),
    )


def select_c1_source(
    records: Iterable[C1DullRolloutRecord],
    *,
    config: C1FrontierConfig | None = None,
) -> C1SourceSelection | None:
    """Select lower-frontier C1 anchors/users and enumerate their alternatives.

    Selection is deterministic.  Anchors are sorted by source-only
    ``frontier_score``; users within each anchor are sorted by source-only
    ``user_frontier_scores``.  Ties use source seed, step, anchor digest, and
    user/action identifiers.  No candidate branch, target, reward, rate, or
    power is accepted by this function.
    """

    current = config or C1FrontierConfig()
    if not isinstance(current, C1FrontierConfig):
        raise C1SelectorContractError("config must be C1FrontierConfig")
    current.verify()
    materialized = _validate_records(records)

    # First determine physical opportunity support.  Eligibility is itself a
    # predecision mask/identity fact, so ineligible anchors do not consume a
    # lower-frontier quota.
    eligible: list[tuple[C1DullRolloutRecord, tuple[int, ...]]] = []
    for record in materialized:
        potential_users: list[int] = []
        for focal_user, table in enumerate(record.slot_tables):
            reference_key = _physical_key(
                table, int(record.reference_actions[focal_user])
            )
            physical = {
                _physical_key(table, int(action))
                for action in np.flatnonzero(table.mask).tolist()
            }
            physical.discard(None)
            if any(key != reference_key for key in physical):
                potential_users.append(focal_user)
        if potential_users:
            eligible.append((record, tuple(potential_users)))
    if not eligible:
        return None

    eligible.sort(
        key=lambda item: (
            float(item[0].frontier_score),
            int(item[0].source_seed),
            int(item[0].step_index),
            item[0].anchor_sha256,
            item[0].record_id,
        )
    )
    anchor_count = _lower_count(
        len(eligible), current.lower_anchor_fraction, field="lower_anchor_fraction"
    )
    if current.max_anchors is not None:
        anchor_count = min(anchor_count, current.max_anchors)
    selected_anchor_records = tuple(item[0] for item in eligible[:anchor_count])
    selected_anchor_set = {record.anchor_sha256 for record in selected_anchor_records}

    all_rows: list[C1UnilateralOpportunity] = []
    selected_rows: list[C1UnilateralOpportunity] = []
    eligible_users: list[tuple[str, int]] = []
    selected_users: list[tuple[str, int]] = []
    for anchor_rank, (record, _potential_users) in enumerate(eligible):
        # Rank all eligible users inside this anchor before selecting the
        # lower user stratum.  This keeps the informed source independent of
        # which alternative later receives a physical evaluation.
        user_count = len(_potential_users)
        user_selected_count = _lower_count(
            user_count,
            current.lower_user_fraction,
            field="lower_user_fraction",
        )
        if current.max_focal_users_per_anchor is not None:
            user_selected_count = min(
                user_selected_count, current.max_focal_users_per_anchor
            )
        selected_for_anchor, selected, all_for_anchor = _opportunities_for_record(
            record,
            anchor_rank=anchor_rank,
            anchor_stratum=_stratum(anchor_rank, anchor_count),
            user_selected_count=user_selected_count,
        )
        if not all_for_anchor:
            continue
        all_rows.extend(all_for_anchor)
        anchor_users = tuple(
            sorted({(row.anchor_sha256, row.focal_user) for row in all_for_anchor})
        )
        selected_for_anchor_set = set(selected_for_anchor)
        eligible_users.extend(anchor_users)
        if record.anchor_sha256 in selected_anchor_set:
            selected_users.extend(
                (record.anchor_sha256, focal_user)
                for focal_user in selected_for_anchor_set
            )
            selected_rows.extend(selected)

    if not selected_rows:
        return None
    # A selected anchor is retained only if its source record emitted rows;
    # all rows are immutable and every selected informed user gets all aliases
    # collapsed to distinct physical alternatives.
    emitted_anchors = tuple(
        record.anchor_sha256
        for record in selected_anchor_records
        if any(row.anchor_sha256 == record.anchor_sha256 for row in selected_rows)
    )
    source = C1SourceSelection(
        selector_schema=C1_SELECTOR_SCHEMA,
        source_rule=C1_INFORMED_SOURCE_RULE,
        acrm_pair_rule=C1_ACRM_PAIR_RULE,
        partition=C1_TRAIN_PARTITION,
        source_manifest_sha256=materialized[0].source_manifest_sha256,
        checkpoint_sha256=materialized[0].checkpoint_sha256,
        state_schema=materialized[0].state_schema,
        state_schema_sha256=materialized[0].state_schema_sha256,
        eligible_anchor_sha256s=tuple(record.anchor_sha256 for record, _ in eligible),
        selected_anchor_sha256s=emitted_anchors,
        eligible_focal_users=tuple(sorted(set(eligible_users))),
        selected_focal_users=tuple(sorted(set(selected_users))),
        all_opportunities=tuple(all_rows),
        opportunities=tuple(selected_rows),
    )
    source.verify()
    return source


def select_c1_sources(
    records: Iterable[C1DullRolloutRecord],
    *,
    config: C1FrontierConfig | None = None,
) -> C1SourceSelection | None:
    """Plural alias for :func:`select_c1_source` used by source schedulers."""

    return select_c1_source(records, config=config)


def _neutral_row(row: C1UnilateralOpportunity) -> C1UnilateralOpportunity:
    return replace(row, source_rule=C1_NEUTRAL_SOURCE_RULE)


def _cluster_neutral_row(
    row: C1UnilateralOpportunity,
) -> C1UnilateralOpportunity:
    return replace(row, source_rule=C1_CLUSTER_NEUTRAL_SOURCE_RULE)


def _randomized_profile_anchor_matching(
    candidate_anchors_by_profile: Sequence[Sequence[str]],
    *,
    rng: np.random.Generator,
) -> tuple[str, ...]:
    """Return one seeded complete bipartite matching or fail closed.

    Candidate identities are canonicalized before any random draw.  The
    augmenting paths make this a feasibility-complete matcher rather than a
    greedy assignment; the seed randomizes traversal but is not claimed to be
    uniform over all possible perfect matchings.
    """

    if not isinstance(rng, np.random.Generator):
        raise C1SelectorContractError("rng must be numpy.random.Generator")
    canonical = tuple(
        tuple(sorted(set(candidates))) for candidates in candidate_anchors_by_profile
    )
    if not canonical or any(not candidates for candidates in canonical):
        raise C1SelectorContractError(
            "every informed cluster profile needs a feasible neutral anchor"
        )
    candidate_order: dict[int, tuple[str, ...]] = {}
    for index, candidates in enumerate(canonical):
        permutation = np.asarray(rng.permutation(len(candidates))).tolist()
        candidate_order[index] = tuple(
            candidates[int(candidate)] for candidate in permutation
        )

    owner_by_anchor: dict[str, int] = {}
    assigned_by_profile: dict[int, str] = {}

    def augment(profile_index: int, seen: set[str]) -> bool:
        for anchor in candidate_order[profile_index]:
            if anchor in seen:
                continue
            seen.add(anchor)
            owner = owner_by_anchor.get(anchor)
            if owner is None or augment(owner, seen):
                owner_by_anchor[anchor] = profile_index
                assigned_by_profile[profile_index] = anchor
                return True
        return False

    matching_order = np.asarray(rng.permutation(len(canonical))).tolist()
    for raw_index in matching_order:
        index = int(raw_index)
        if not augment(index, set()):
            raise C1SelectorContractError(
                "insufficient unique neutral anchors for informed cluster profiles"
            )
    result = tuple(assigned_by_profile[index] for index in range(len(canonical)))
    if len(set(result)) != len(result):
        raise C1SelectorContractError(
            "cluster-profile matching did not assign unique neutral anchors"
        )
    return result


def sample_c1_neutral_source(
    informed: C1SourceSelection,
    *,
    rng: np.random.Generator,
) -> C1SourceSelection:
    """Uniformly sample an equal-budget neutral C1 opportunity plan.

    The sampling unit is one sealed ``(anchor, focal user, physical
    alternative)`` opportunity.  Thus every eligible physical opportunity is
    equally likely, no frontier score is consulted, and the neutral plan has
    exactly the informed number of rows.  Both plans still use the same
    reference-anchored ACRM pair construction and lineage.
    """

    if not isinstance(informed, C1SourceSelection):
        raise C1SelectorContractError("informed must be C1SourceSelection")
    informed.verify()
    if informed.source_rule != C1_INFORMED_SOURCE_RULE:
        raise C1SelectorContractError("neutral sampling requires an informed C1 plan")
    if not isinstance(rng, np.random.Generator):
        raise C1SelectorContractError("rng must be numpy.random.Generator")
    budget = informed.budget
    universe = tuple(_neutral_row(row) for row in informed.all_opportunities)
    if budget <= 0 or budget > len(universe):
        raise C1SelectorContractError("neutral budget is outside the sealed universe")
    indices = np.asarray(rng.choice(len(universe), size=budget, replace=False)).tolist()
    selected = tuple(
        sorted(
            (universe[int(index)] for index in indices),
            key=lambda row: (
                row.anchor_sha256,
                row.focal_user,
                row.candidate_physical_key,
                row.candidate_action,
            ),
        )
    )
    neutral = C1SourceSelection(
        selector_schema=informed.selector_schema,
        source_rule=C1_NEUTRAL_SOURCE_RULE,
        acrm_pair_rule=informed.acrm_pair_rule,
        partition=informed.partition,
        source_manifest_sha256=informed.source_manifest_sha256,
        checkpoint_sha256=informed.checkpoint_sha256,
        state_schema=informed.state_schema,
        state_schema_sha256=informed.state_schema_sha256,
        eligible_anchor_sha256s=informed.eligible_anchor_sha256s,
        selected_anchor_sha256s=tuple(
            sorted({row.anchor_sha256 for row in selected})
        ),
        eligible_focal_users=informed.eligible_focal_users,
        selected_focal_users=tuple(
            sorted({(row.anchor_sha256, row.focal_user) for row in selected})
        ),
        all_opportunities=universe,
        opportunities=selected,
    )
    neutral.verify()
    return neutral


def sample_c1_cluster_matched_neutral_source(
    informed: C1SourceSelection,
    *,
    rng: np.random.Generator,
) -> C1SourceSelection:
    """Sample a neutral C1 plan at the ACRM anchor/user sampling unit.

    The informed and neutral arms have the same number of anchors, the same
    number of focal users per anchor, the same per-user legal-physical-
    alternative count strata, and therefore the same number of physical
    evaluations and Q1 updates.  Every selected neutral focal user emits all
    of its legal physical alternatives.  Anchor and user choices use only the
    sealed predecision opportunity universe; candidate outcomes are absent.

    Homogeneous informed profiles retain the original uniform anchor draw.
    Heterogeneous profiles use a seeded randomized bipartite matching: every
    informed anchor profile is assigned to one unique feasible neutral anchor,
    then users are sampled uniformly without replacement inside each required
    alternative-count stratum.  The matcher consults only the sealed
    predecision opportunity structure; it never uses a frontier rank, target,
    outcome, reward, or EE value.
    """

    if not isinstance(informed, C1SourceSelection):
        raise C1SelectorContractError("informed must be C1SourceSelection")
    informed.verify()
    if informed.source_rule != C1_INFORMED_SOURCE_RULE:
        raise C1SelectorContractError(
            "cluster-matched neutral sampling requires an informed C1 plan"
        )
    if not isinstance(rng, np.random.Generator):
        raise C1SelectorContractError("rng must be numpy.random.Generator")

    grouped_rows: dict[
        tuple[str, int], list[C1UnilateralOpportunity]
    ] = {}
    for row in informed.all_opportunities:
        grouped_rows.setdefault((row.anchor_sha256, row.focal_user), []).append(row)
    original_by_user: dict[
        tuple[str, int], tuple[C1UnilateralOpportunity, ...]
    ] = {}
    for key in informed.eligible_focal_users:
        rows = tuple(grouped_rows.get(key, ()))
        if not rows:
            raise C1SelectorContractError(
                "eligible C1 cluster has no physical alternatives"
            )
        original_by_user[key] = rows

    selected_by_anchor: dict[str, list[tuple[str, int]]] = {}
    for key in informed.selected_focal_users:
        selected_by_anchor.setdefault(key[0], []).append(key)
    if not selected_by_anchor:
        raise C1SelectorContractError("informed C1 plan selected no clusters")

    profiles_by_anchor = {
        anchor: tuple(sorted(len(original_by_user[key]) for key in keys))
        for anchor, keys in selected_by_anchor.items()
    }

    users_by_anchor_and_size: dict[str, dict[int, list[tuple[str, int]]]] = {}
    for key, rows in original_by_user.items():
        users_by_anchor_and_size.setdefault(key[0], {}).setdefault(
            len(rows), []
        ).append(key)

    ordered_informed = tuple(sorted(profiles_by_anchor.items()))

    def requirements(profile: tuple[int, ...]) -> dict[int, int]:
        result: dict[int, int] = {}
        for size in profile:
            result[size] = result.get(size, 0) + 1
        return result

    unique_profiles = set(profiles_by_anchor.values())
    assigned_by_profile_index: dict[int, str] = {}
    if len(unique_profiles) == 1:
        # Preserve the original exactly-uniform anchor-subset draw whenever
        # all informed anchors share one profile.
        required_by_size = requirements(next(iter(unique_profiles)))
        feasible_anchors = tuple(
            sorted(
                anchor
                for anchor, by_size in users_by_anchor_and_size.items()
                if all(
                    len(by_size.get(size, ())) >= count
                    for size, count in required_by_size.items()
                )
            )
        )
        anchor_budget = len(ordered_informed)
        if len(feasible_anchors) < anchor_budget:
            raise C1SelectorContractError(
                "insufficient neutral anchors for the informed cluster profile"
            )
        anchor_indices = np.asarray(
            rng.choice(len(feasible_anchors), size=anchor_budget, replace=False)
        ).tolist()
        chosen_anchors = tuple(
            sorted(feasible_anchors[int(anchor_index)] for anchor_index in anchor_indices)
        )
        for index, anchor in enumerate(chosen_anchors):
            assigned_by_profile_index[index] = anchor
    else:
        # Candidate order and augmenting-path order are seeded.  This is a
        # randomized feasible matching, not a claim of uniform sampling over
        # the set of all perfect matchings.
        candidates_by_profile: list[tuple[str, ...]] = []
        for index, (_, profile) in enumerate(ordered_informed):
            required_by_size = requirements(profile)
            feasible = tuple(
                sorted(
                    anchor
                    for anchor, by_size in users_by_anchor_and_size.items()
                    if all(
                        len(by_size.get(size, ())) >= count
                        for size, count in required_by_size.items()
                    )
                )
            )
            if not feasible:
                raise C1SelectorContractError(
                    "no neutral anchor supports an informed cluster profile"
                )
            candidates_by_profile.append(feasible)
        matched = _randomized_profile_anchor_matching(
            candidates_by_profile,
            rng=rng,
        )
        assigned_by_profile_index.update(enumerate(matched))

    selected_anchors = tuple(sorted(assigned_by_profile_index.values()))
    if len(selected_anchors) != len(ordered_informed):
        raise C1SelectorContractError(
            "cluster-profile matching did not assign unique neutral anchors"
        )

    selected_users: list[tuple[str, int]] = []
    for index, (_, profile) in enumerate(ordered_informed):
        anchor = assigned_by_profile_index[index]
        required_by_size = requirements(profile)
        for size in sorted(required_by_size):
            candidates = tuple(sorted(users_by_anchor_and_size[anchor][size]))
            count = required_by_size[size]
            indices = np.asarray(
                rng.choice(len(candidates), size=count, replace=False)
            ).tolist()
            selected_users.extend(candidates[int(index)] for index in indices)

    universe = tuple(
        _cluster_neutral_row(row) for row in informed.all_opportunities
    )
    selected_user_set = set(selected_users)
    selected = tuple(
        row
        for row in universe
        if (row.anchor_sha256, row.focal_user) in selected_user_set
    )
    neutral = C1SourceSelection(
        selector_schema=informed.selector_schema,
        source_rule=C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        acrm_pair_rule=informed.acrm_pair_rule,
        partition=informed.partition,
        source_manifest_sha256=informed.source_manifest_sha256,
        checkpoint_sha256=informed.checkpoint_sha256,
        state_schema=informed.state_schema,
        state_schema_sha256=informed.state_schema_sha256,
        eligible_anchor_sha256s=informed.eligible_anchor_sha256s,
        selected_anchor_sha256s=selected_anchors,
        eligible_focal_users=informed.eligible_focal_users,
        selected_focal_users=tuple(sorted(selected_user_set)),
        all_opportunities=universe,
        opportunities=selected,
    )
    neutral.verify()
    if neutral.budget != informed.budget:
        raise C1SelectorContractError(
            "cluster-matched neutral and informed row budgets disagree"
        )
    return neutral


class C1SourceSelector:
    """Reusable deterministic C1 source selector with a fixed quota config."""

    def __init__(self, *, config: C1FrontierConfig | None = None) -> None:
        self.config = config or C1FrontierConfig()
        if not isinstance(self.config, C1FrontierConfig):
            raise C1SelectorContractError("config must be C1FrontierConfig")
        self.config.verify()

    def select(
        self, records: Iterable[C1DullRolloutRecord]
    ) -> C1SourceSelection | None:
        return select_c1_source(records, config=self.config)

    @staticmethod
    def neutral(
        informed: C1SourceSelection, *, rng: np.random.Generator
    ) -> C1SourceSelection:
        return sample_c1_neutral_source(informed, rng=rng)


__all__ = [
    "C1_ACRM_PAIR_RULE",
    "C1_DULL_ROLLOUT_KIND",
    "C1_DULL_ROLLOUT_SCHEMA",
    "C1_INFORMED_SOURCE_RULE",
    "C1_NEUTRAL_SOURCE_RULE",
    "C1_SELECTOR_SCHEMA",
    "C1_TRAIN_PARTITION",
    "C1DullRolloutRecord",
    "C1FrontierConfig",
    "C1SelectorContractError",
    "C1SourceSelection",
    "C1SourceSelector",
    "C1UnilateralOpportunity",
    "PhysicalKey",
    "PhysicalKeyOrNone",
    "sample_c1_neutral_source",
    "select_c1_source",
    "select_c1_sources",
]
