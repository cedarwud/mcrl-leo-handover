"""Outcome-blind V0.4 C3 source schedule.

The schedule is frozen from victim-burden selector metadata before any
counterfactual branch is evaluated.  It balances focal-state contexts across
source seeds, caps sibling rows, connects all 28 TRAIN action indices, and
admits only validation action pairs already present in TRAIN.  No target,
rate outcome, reward, or EE value is accepted by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import Iterable, Mapping

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_v04_c3_selector import (
    C3_V04_INFORMED_SOURCE_RULE,
    C3_V04_MAX_SIBLINGS_PER_CONTEXT,
    C3V04SourceSelection,
)


C3_V04_SCHEDULE_SCHEMA = "multi-catfish-mcrl-v04-c3-source-schedule-v2"
C3_V04_TRAIN_CONTEXTS = 263
C3_V04_VALIDATION_CONTEXTS = 203
C3_V04_TRAIN_ROW_BUDGET = 1052
C3_V04_VALIDATION_ROW_BUDGET = 810
C3_V04_MAX_CONTEXTS_PER_ANCHOR = 8

PhysicalKey = tuple[int, int]


class C3V04ScheduleContractError(MCRLContractError):
    """A proposed C3 schedule violates the outcome-blind design contract."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3V04ScheduleContractError(f"{field} must be lowercase SHA-256")
    return value


def _strict_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise C3V04ScheduleContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _finite_tuple(values: object, *, field: str) -> tuple[float, ...]:
    if not isinstance(values, (tuple, list)) or not values:
        raise C3V04ScheduleContractError(f"{field} must be a nonempty sequence")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise C3V04ScheduleContractError(f"{field} must be finite")
    return result


def _physical_key(
    value: object, *, field: str, allow_none: bool
) -> PhysicalKey | None:
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise C3V04ScheduleContractError(f"{field} must be a physical key")
    return value


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class C3V04ContextCandidate:
    """One pre-outcome focal-state context with at most four siblings."""

    source_seed: int
    split: str
    anchor_sha256: str
    state_observation_sha256: str
    step_index: int
    focal_user: int
    source_rule: str
    reference_action: int
    reference_physical_key: PhysicalKey | None
    candidate_actions: tuple[int, ...]
    candidate_physical_keys: tuple[PhysicalKey, ...]
    burden_deltas: tuple[float, ...]
    satellite_burden_deltas: tuple[float, ...]
    victim_pressures: tuple[float, ...]
    satellite_victim_pressures: tuple[float, ...]

    @property
    def context_key(self) -> tuple[int, str, int]:
        return self.source_seed, self.anchor_sha256, self.focal_user

    @property
    def directed_pairs(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (self.reference_action, candidate) for candidate in self.candidate_actions
        )

    @property
    def rank(self) -> tuple[float, float, float, float]:
        """Beam-primary context rank with satellite-only tie-breaks."""

        return (
            max(abs(value) for value in self.burden_deltas),
            max(self.victim_pressures),
            max(abs(value) for value in self.satellite_burden_deltas),
            max(self.satellite_victim_pressures),
        )

    def verify(self) -> None:
        _strict_int(self.source_seed, field="source_seed")
        if self.split not in ("train", "validation"):
            raise C3V04ScheduleContractError("split must be train or validation")
        _digest(self.anchor_sha256, field="anchor_sha256")
        _digest(self.state_observation_sha256, field="state_observation_sha256")
        _strict_int(self.step_index, field="step_index")
        _strict_int(self.focal_user, field="focal_user")
        if self.source_rule != C3_V04_INFORMED_SOURCE_RULE:
            raise C3V04ScheduleContractError("schedule accepts only V0.4 informed rows")
        _strict_int(self.reference_action, field="reference_action")
        if not 0 <= self.reference_action < NUM_ACTIONS:
            raise C3V04ScheduleContractError("reference action is outside action space")
        reference_key = _physical_key(
            self.reference_physical_key,
            field="reference_physical_key",
            allow_none=True,
        )
        if (
            not isinstance(self.candidate_actions, tuple)
            or not 1 <= len(self.candidate_actions) <= C3_V04_MAX_SIBLINGS_PER_CONTEXT
            or any(type(action) is not int or not 0 <= action < NUM_ACTIONS for action in self.candidate_actions)
            or len(set(self.candidate_actions)) != len(self.candidate_actions)
            or self.reference_action in self.candidate_actions
        ):
            raise C3V04ScheduleContractError("candidate action tuple is malformed")
        if (
            not isinstance(self.candidate_physical_keys, tuple)
            or len(self.candidate_physical_keys) != len(self.candidate_actions)
        ):
            raise C3V04ScheduleContractError(
                "candidate physical-key tuple is malformed"
            )
        candidate_keys = tuple(
            _physical_key(value, field="candidate_physical_key", allow_none=False)
            for value in self.candidate_physical_keys
        )
        if len(set(candidate_keys)) != len(candidate_keys) or reference_key in candidate_keys:
            raise C3V04ScheduleContractError(
                "candidate physical keys repeat or match the reference"
            )
        deltas = _finite_tuple(self.burden_deltas, field="burden_deltas")
        satellite_deltas = _finite_tuple(
            self.satellite_burden_deltas,
            field="satellite_burden_deltas",
        )
        pressures = _finite_tuple(self.victim_pressures, field="victim_pressures")
        satellite_pressures = _finite_tuple(
            self.satellite_victim_pressures,
            field="satellite_victim_pressures",
        )
        if any(
            len(values) != len(self.candidate_actions)
            for values in (
                deltas,
                satellite_deltas,
                pressures,
                satellite_pressures,
            )
        ):
            raise C3V04ScheduleContractError("sibling metadata lengths disagree")
        if any(value < 0.0 for value in (*pressures, *satellite_pressures)):
            raise C3V04ScheduleContractError("victim pressures must be nonnegative")


def contexts_from_selection(
    *,
    source_seed: int,
    split: str,
    selection: C3V04SourceSelection,
) -> tuple[C3V04ContextCandidate, ...]:
    """Project one selector plan into scheduler-safe scalar metadata."""

    if not isinstance(selection, C3V04SourceSelection):
        raise C3V04ScheduleContractError("selection must be V0.4 C3 selection")
    selection.verify()
    by_user: dict[int, list[object]] = {}
    for row in selection.opportunities:
        by_user.setdefault(row.focal_user, []).append(row)
    contexts: list[C3V04ContextCandidate] = []
    for uid, rows in sorted(by_user.items()):
        context = C3V04ContextCandidate(
            source_seed=source_seed,
            split=split,
            anchor_sha256=selection.anchor_sha256,
            state_observation_sha256=selection.state.state_sha256,
            step_index=selection.step_index,
            focal_user=uid,
            source_rule=selection.source_rule,
            reference_action=int(rows[0].reference_action),
            reference_physical_key=rows[0].reference_physical_key,
            candidate_actions=tuple(int(row.candidate_action) for row in rows),
            candidate_physical_keys=tuple(
                row.candidate_physical_key for row in rows
            ),
            burden_deltas=tuple(float(row.burden_delta) for row in rows),
            satellite_burden_deltas=tuple(
                float(row.satellite_burden_delta) for row in rows
            ),
            victim_pressures=tuple(float(row.victim_pressure) for row in rows),
            satellite_victim_pressures=tuple(
                float(row.satellite_victim_pressure) for row in rows
            ),
        )
        context.verify()
        contexts.append(context)
    return tuple(contexts)


def _context_payload(context: C3V04ContextCandidate) -> dict[str, object]:
    return {
        "source_seed": context.source_seed,
        "split": context.split,
        "anchor_sha256": context.anchor_sha256,
        "state_observation_sha256": context.state_observation_sha256,
        "step_index": context.step_index,
        "focal_user": context.focal_user,
        "source_rule": context.source_rule,
        "reference_action": context.reference_action,
        "reference_physical_key": (
            None
            if context.reference_physical_key is None
            else list(context.reference_physical_key)
        ),
        "candidate_actions": list(context.candidate_actions),
        "candidate_physical_keys": [
            list(value) for value in context.candidate_physical_keys
        ],
        "burden_deltas": [float(value).hex() for value in context.burden_deltas],
        "satellite_burden_deltas": [
            float(value).hex() for value in context.satellite_burden_deltas
        ],
        "victim_pressures": [float(value).hex() for value in context.victim_pressures],
        "satellite_victim_pressures": [
            float(value).hex() for value in context.satellite_victim_pressures
        ],
    }


def _schedule_payload(schedule: "C3V04SourceSchedule") -> dict[str, object]:
    return {
        "schema": C3_V04_SCHEDULE_SCHEMA,
        "seed_split": [[seed, split] for seed, split in schedule.seed_split],
        "train_context_goal": schedule.train_context_goal,
        "validation_context_goal": schedule.validation_context_goal,
        "train_row_budget": schedule.train_row_budget,
        "validation_row_budget": schedule.validation_row_budget,
        "max_contexts_per_anchor": schedule.max_contexts_per_anchor,
        "train": [_context_payload(row) for row in schedule.train],
        "validation": [_context_payload(row) for row in schedule.validation],
    }


def _components(edges: Iterable[tuple[int, int]]) -> tuple[int, set[int]]:
    parent = list(range(NUM_ACTIONS))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    seen: set[int] = set()
    for left, right in edges:
        union(left, right)
        seen.update((left, right))
    return len({find(node) for node in range(NUM_ACTIONS)}), seen


def _merge_gain(
    existing: set[tuple[int, int]], candidate: C3V04ContextCandidate
) -> int:
    before, _ = _components(existing)
    after, _ = _components((*existing, *candidate.directed_pairs))
    return before - after


def _seed_quotas(seeds: list[int], goal: int) -> dict[int, int]:
    if not seeds or goal < len(seeds):
        raise C3V04ScheduleContractError("context goal cannot cover every source seed")
    base, remainder = divmod(goal, len(seeds))
    return {
        seed: base + (1 if index < remainder else 0)
        for index, seed in enumerate(sorted(seeds))
    }


def _rank_key(context: C3V04ContextCandidate) -> tuple[object, ...]:
    return (
        -context.rank[0],
        -context.rank[1],
        -context.rank[2],
        -context.rank[3],
        context.source_seed,
        context.anchor_sha256,
        context.focal_user,
    )


def _select_train(
    candidates: list[C3V04ContextCandidate],
    *,
    quotas: Mapping[int, int],
    max_contexts_per_anchor: int,
) -> tuple[C3V04ContextCandidate, ...]:
    selected: list[C3V04ContextCandidate] = []
    selected_keys: set[tuple[int, str, int]] = set()
    counts = {seed: 0 for seed in quotas}
    anchor_counts: dict[tuple[int, str], int] = {}
    edges: set[tuple[int, int]] = set()
    while _components(edges)[0] > 1:
        available = [
            row
            for row in candidates
            if row.context_key not in selected_keys
            and counts[row.source_seed] < quotas[row.source_seed]
            and anchor_counts.get((row.source_seed, row.anchor_sha256), 0)
            < max_contexts_per_anchor
        ]
        if not available:
            break
        ranked = sorted(
            available,
            key=lambda row: (
                -_merge_gain(edges, row),
                *_rank_key(row),
            ),
        )
        chosen = ranked[0]
        gain = _merge_gain(edges, chosen)
        if gain <= 0:
            break
        selected.append(chosen)
        selected_keys.add(chosen.context_key)
        counts[chosen.source_seed] += 1
        anchor_key = (chosen.source_seed, chosen.anchor_sha256)
        anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
        edges.update(chosen.directed_pairs)
    for seed in sorted(quotas):
        needed = quotas[seed] - counts[seed]
        pool = sorted(
            (
                row
                for row in candidates
                if row.source_seed == seed and row.context_key not in selected_keys
                and anchor_counts.get((row.source_seed, row.anchor_sha256), 0)
                < max_contexts_per_anchor
            ),
            key=_rank_key,
        )
        if len(pool) < needed:
            raise C3V04ScheduleContractError(
                f"train seed {seed} lacks focal-state context coverage"
            )
        accepted = 0
        for row in pool:
            anchor_key = (row.source_seed, row.anchor_sha256)
            if anchor_counts.get(anchor_key, 0) >= max_contexts_per_anchor:
                continue
            selected.append(row)
            selected_keys.add(row.context_key)
            edges.update(row.directed_pairs)
            anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
            accepted += 1
            if accepted == needed:
                break
        if accepted != needed:
            raise C3V04ScheduleContractError(
                f"train seed {seed} lacks anchor-balanced context coverage"
            )
    components, seen = _components(edges)
    if components != 1 or seen != set(range(NUM_ACTIONS)):
        raise C3V04ScheduleContractError(
            "TRAIN schedule does not form one connected 28-action graph"
        )
    return tuple(sorted(selected, key=lambda row: row.context_key))


def _supported_context(
    context: C3V04ContextCandidate,
    *,
    supported: set[tuple[int, int]],
) -> C3V04ContextCandidate | None:
    keep = [
        index
        for index, pair in enumerate(context.directed_pairs)
        if pair in supported
    ]
    if not keep:
        return None
    result = replace(
        context,
        candidate_actions=tuple(context.candidate_actions[index] for index in keep),
        candidate_physical_keys=tuple(
            context.candidate_physical_keys[index] for index in keep
        ),
        burden_deltas=tuple(context.burden_deltas[index] for index in keep),
        satellite_burden_deltas=tuple(
            context.satellite_burden_deltas[index] for index in keep
        ),
        victim_pressures=tuple(context.victim_pressures[index] for index in keep),
        satellite_victim_pressures=tuple(
            context.satellite_victim_pressures[index] for index in keep
        ),
    )
    result.verify()
    return result


def _select_validation(
    candidates: list[C3V04ContextCandidate],
    *,
    quotas: Mapping[int, int],
    supported: set[tuple[int, int]],
    row_budget: int,
    max_contexts_per_anchor: int,
) -> tuple[C3V04ContextCandidate, ...]:
    filtered = [
        result
        for row in candidates
        if (result := _supported_context(row, supported=supported)) is not None
    ]
    selected: list[C3V04ContextCandidate] = []
    anchor_counts: dict[tuple[int, str], int] = {}
    for seed in sorted(quotas):
        pool = sorted(
            (row for row in filtered if row.source_seed == seed), key=_rank_key
        )
        accepted = 0
        for row in pool:
            anchor_key = (row.source_seed, row.anchor_sha256)
            if anchor_counts.get(anchor_key, 0) >= max_contexts_per_anchor:
                continue
            selected.append(row)
            anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
            accepted += 1
            if accepted == quotas[seed]:
                break
        if accepted != quotas[seed]:
            raise C3V04ScheduleContractError(
                f"validation seed {seed} lacks anchor-balanced TRAIN-supported contexts"
            )
    excess = sum(len(row.candidate_actions) for row in selected) - row_budget
    while excess > 0:
        removable = [row for row in selected if len(row.candidate_actions) > 1]
        if not removable:
            raise C3V04ScheduleContractError(
                "validation row budget cannot preserve every selected context"
            )
        row = sorted(removable, key=_rank_key, reverse=True)[0]
        index = selected.index(row)
        selected[index] = replace(
            row,
            candidate_actions=row.candidate_actions[:-1],
            candidate_physical_keys=row.candidate_physical_keys[:-1],
            burden_deltas=row.burden_deltas[:-1],
            satellite_burden_deltas=row.satellite_burden_deltas[:-1],
            victim_pressures=row.victim_pressures[:-1],
            satellite_victim_pressures=row.satellite_victim_pressures[:-1],
        )
        selected[index].verify()
        excess -= 1
    return tuple(sorted(selected, key=lambda row: row.context_key))


@dataclass(frozen=True)
class C3V04SourceSchedule:
    """Authenticated outcome-blind TRAIN/validation source schedule."""

    seed_split: tuple[tuple[int, str], ...]
    train_context_goal: int
    validation_context_goal: int
    train_row_budget: int
    validation_row_budget: int
    max_contexts_per_anchor: int
    train: tuple[C3V04ContextCandidate, ...]
    validation: tuple[C3V04ContextCandidate, ...]
    schedule_sha256: str
    schema: str = C3_V04_SCHEDULE_SCHEMA

    def verify(self) -> str:
        if self.schema != C3_V04_SCHEDULE_SCHEMA:
            raise C3V04ScheduleContractError("schedule schema is stale")
        split = dict(self.seed_split)
        if len(split) != len(self.seed_split) or set(split.values()) != {
            "train",
            "validation",
        }:
            raise C3V04ScheduleContractError("seed split is malformed")
        for field in (
            "train_context_goal",
            "validation_context_goal",
            "train_row_budget",
            "validation_row_budget",
            "max_contexts_per_anchor",
        ):
            _strict_int(getattr(self, field), field=field, minimum=1)
        if len(self.train) != self.train_context_goal or len(
            self.validation
        ) != self.validation_context_goal:
            raise C3V04ScheduleContractError("schedule context count drifted")
        if self.train != tuple(sorted(self.train, key=lambda row: row.context_key)):
            raise C3V04ScheduleContractError("TRAIN contexts are not canonically sorted")
        if self.validation != tuple(
            sorted(self.validation, key=lambda row: row.context_key)
        ):
            raise C3V04ScheduleContractError(
                "validation contexts are not canonically sorted"
            )
        all_rows = (*self.train, *self.validation)
        keys: set[tuple[int, str, int]] = set()
        anchor_owner: dict[str, str] = {}
        for row in all_rows:
            row.verify()
            if split.get(row.source_seed) != row.split:
                raise C3V04ScheduleContractError("row disagrees with seed split")
            if row.context_key in keys:
                raise C3V04ScheduleContractError("duplicate focal-state context")
            keys.add(row.context_key)
            if anchor_owner.setdefault(row.anchor_sha256, row.split) != row.split:
                raise C3V04ScheduleContractError("physical anchor crosses design splits")
        anchor_counts: dict[tuple[int, str], int] = {}
        anchor_metadata: dict[tuple[int, str], tuple[int, str]] = {}
        for row in all_rows:
            anchor_key = (row.source_seed, row.anchor_sha256)
            anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
            metadata = (row.step_index, row.state_observation_sha256)
            if anchor_metadata.setdefault(anchor_key, metadata) != metadata:
                raise C3V04ScheduleContractError(
                    "physical anchor has inconsistent step/state metadata"
                )
        if any(
            count > self.max_contexts_per_anchor
            for count in anchor_counts.values()
        ):
            raise C3V04ScheduleContractError(
                "physical anchor exceeds the frozen context cap"
            )
        train_seeds = sorted(seed for seed, name in split.items() if name == "train")
        validation_seeds = sorted(
            seed for seed, name in split.items() if name == "validation"
        )
        for selected, quotas, name in (
            (self.train, _seed_quotas(train_seeds, self.train_context_goal), "TRAIN"),
            (
                self.validation,
                _seed_quotas(validation_seeds, self.validation_context_goal),
                "validation",
            ),
        ):
            counts = {
                seed: sum(row.source_seed == seed for row in selected)
                for seed in quotas
            }
            if counts != quotas:
                raise C3V04ScheduleContractError(
                    f"{name} contexts are not balanced across source seeds"
                )
        if sum(len(row.candidate_actions) for row in self.train) > self.train_row_budget:
            raise C3V04ScheduleContractError("TRAIN row budget exceeded")
        if sum(len(row.candidate_actions) for row in self.validation) > self.validation_row_budget:
            raise C3V04ScheduleContractError("validation row budget exceeded")
        train_pairs = {
            pair for row in self.train for pair in row.directed_pairs
        }
        components, seen = _components(train_pairs)
        if components != 1 or seen != set(range(NUM_ACTIONS)):
            raise C3V04ScheduleContractError("TRAIN action graph is not connected")
        validation_pairs = {
            pair for row in self.validation for pair in row.directed_pairs
        }
        if not validation_pairs.issubset(train_pairs):
            raise C3V04ScheduleContractError("validation has unsupported action pairs")
        supplied = _digest(self.schedule_sha256, field="schedule_sha256")
        actual = _canonical_sha256(_schedule_payload(self))
        if supplied != actual:
            raise C3V04ScheduleContractError("schedule digest disagrees with payload")
        return actual


def build_v04_c3_schedule(
    candidates: Iterable[C3V04ContextCandidate],
    *,
    seed_split: Mapping[int, str],
    train_context_goal: int = C3_V04_TRAIN_CONTEXTS,
    validation_context_goal: int = C3_V04_VALIDATION_CONTEXTS,
    train_row_budget: int = C3_V04_TRAIN_ROW_BUDGET,
    validation_row_budget: int = C3_V04_VALIDATION_ROW_BUDGET,
    max_contexts_per_anchor: int = C3_V04_MAX_CONTEXTS_PER_ANCHOR,
) -> C3V04SourceSchedule:
    """Build the one fixed schedule without observing a branch outcome."""

    normalized_split = dict(seed_split)
    if (
        not normalized_split
        or any(type(seed) is not int or seed < 0 for seed in normalized_split)
        or set(normalized_split.values()) != {"train", "validation"}
    ):
        raise C3V04ScheduleContractError("seed_split must contain train and validation")
    rows = list(candidates)
    if not rows:
        raise C3V04ScheduleContractError("candidate context universe is empty")
    seen_keys: set[tuple[int, str, int]] = set()
    for row in rows:
        if not isinstance(row, C3V04ContextCandidate):
            raise C3V04ScheduleContractError("candidate universe contains a non-context")
        row.verify()
        if normalized_split.get(row.source_seed) != row.split:
            raise C3V04ScheduleContractError("candidate disagrees with seed split")
        if row.context_key in seen_keys:
            raise C3V04ScheduleContractError("candidate context repeats")
        seen_keys.add(row.context_key)
    train_seeds = sorted(seed for seed, split in normalized_split.items() if split == "train")
    validation_seeds = sorted(
        seed for seed, split in normalized_split.items() if split == "validation"
    )
    train = _select_train(
        [row for row in rows if row.split == "train"],
        quotas=_seed_quotas(train_seeds, train_context_goal),
        max_contexts_per_anchor=max_contexts_per_anchor,
    )
    train_pairs = {pair for row in train for pair in row.directed_pairs}
    validation = _select_validation(
        [row for row in rows if row.split == "validation"],
        quotas=_seed_quotas(validation_seeds, validation_context_goal),
        supported=train_pairs,
        row_budget=validation_row_budget,
        max_contexts_per_anchor=max_contexts_per_anchor,
    )
    if sum(len(row.candidate_actions) for row in train) > train_row_budget:
        raise C3V04ScheduleContractError("TRAIN row budget is too small")
    draft = C3V04SourceSchedule(
        seed_split=tuple(sorted(normalized_split.items())),
        train_context_goal=train_context_goal,
        validation_context_goal=validation_context_goal,
        train_row_budget=train_row_budget,
        validation_row_budget=validation_row_budget,
        max_contexts_per_anchor=max_contexts_per_anchor,
        train=train,
        validation=validation,
        schedule_sha256="0" * 64,
    )
    result = replace(draft, schedule_sha256=_canonical_sha256(_schedule_payload(draft)))
    result.verify()
    return result


def write_v04_c3_schedule(path: Path, schedule: C3V04SourceSchedule) -> str:
    """Atomically write a canonical schedule that refuses overwrite."""

    schedule.verify()
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite C3 schedule: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**_schedule_payload(schedule), "schedule_sha256": schedule.schedule_sha256}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="ascii", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
    try:
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _decode_context(payload: object) -> C3V04ContextCandidate:
    if not isinstance(payload, dict) or set(payload) != {
        "source_seed",
        "split",
        "anchor_sha256",
        "state_observation_sha256",
        "step_index",
        "focal_user",
        "source_rule",
        "reference_action",
        "reference_physical_key",
        "candidate_actions",
        "candidate_physical_keys",
        "burden_deltas",
        "satellite_burden_deltas",
        "victim_pressures",
        "satellite_victim_pressures",
    }:
        raise C3V04ScheduleContractError("serialized context schema is unexpected")
    try:
        deltas = tuple(float.fromhex(value) for value in payload["burden_deltas"])
        satellite_deltas = tuple(
            float.fromhex(value) for value in payload["satellite_burden_deltas"]
        )
        pressures = tuple(float.fromhex(value) for value in payload["victim_pressures"])
        satellite_pressures = tuple(
            float.fromhex(value)
            for value in payload["satellite_victim_pressures"]
        )
        reference_physical_key = (
            None
            if payload["reference_physical_key"] is None
            else tuple(payload["reference_physical_key"])
        )
        candidate_physical_keys = tuple(
            tuple(value) for value in payload["candidate_physical_keys"]
        )
    except (TypeError, ValueError) as error:
        raise C3V04ScheduleContractError("serialized burden values are malformed") from error
    row = C3V04ContextCandidate(
        source_seed=payload["source_seed"],
        split=payload["split"],
        anchor_sha256=payload["anchor_sha256"],
        state_observation_sha256=payload["state_observation_sha256"],
        step_index=payload["step_index"],
        focal_user=payload["focal_user"],
        source_rule=payload["source_rule"],
        reference_action=payload["reference_action"],
        reference_physical_key=reference_physical_key,
        candidate_actions=tuple(payload["candidate_actions"]),
        candidate_physical_keys=candidate_physical_keys,
        burden_deltas=deltas,
        satellite_burden_deltas=satellite_deltas,
        victim_pressures=pressures,
        satellite_victim_pressures=satellite_pressures,
    )
    row.verify()
    return row


def read_v04_c3_schedule(path: Path) -> C3V04SourceSchedule:
    """Read and fully authenticate one canonical schedule."""

    try:
        payload = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise C3V04ScheduleContractError("cannot read C3 schedule") from error
    if not isinstance(payload, dict) or set(payload) != {
        "schema",
        "seed_split",
        "train_context_goal",
        "validation_context_goal",
        "train_row_budget",
        "validation_row_budget",
        "max_contexts_per_anchor",
        "train",
        "validation",
        "schedule_sha256",
    }:
        raise C3V04ScheduleContractError("serialized schedule schema is unexpected")
    try:
        seed_split = tuple((row[0], row[1]) for row in payload["seed_split"])
        train = tuple(_decode_context(row) for row in payload["train"])
        validation = tuple(_decode_context(row) for row in payload["validation"])
    except (TypeError, IndexError) as error:
        raise C3V04ScheduleContractError("serialized schedule vectors are malformed") from error
    schedule = C3V04SourceSchedule(
        seed_split=seed_split,
        train_context_goal=payload["train_context_goal"],
        validation_context_goal=payload["validation_context_goal"],
        train_row_budget=payload["train_row_budget"],
        validation_row_budget=payload["validation_row_budget"],
        max_contexts_per_anchor=payload["max_contexts_per_anchor"],
        train=train,
        validation=validation,
        schedule_sha256=payload["schedule_sha256"],
        schema=payload["schema"],
    )
    schedule.verify()
    return schedule


__all__ = [
    "C3_V04_SCHEDULE_SCHEMA",
    "C3_V04_TRAIN_CONTEXTS",
    "C3_V04_TRAIN_ROW_BUDGET",
    "C3_V04_MAX_CONTEXTS_PER_ANCHOR",
    "C3_V04_VALIDATION_CONTEXTS",
    "C3_V04_VALIDATION_ROW_BUDGET",
    "C3V04ContextCandidate",
    "C3V04ScheduleContractError",
    "C3V04SourceSchedule",
    "build_v04_c3_schedule",
    "contexts_from_selection",
    "read_v04_c3_schedule",
    "write_v04_c3_schedule",
]
