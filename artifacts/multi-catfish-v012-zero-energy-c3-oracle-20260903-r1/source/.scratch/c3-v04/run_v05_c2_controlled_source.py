#!/usr/bin/env python3
"""Prepare, materialize, and merge the bounded V0.5 controlled C2 source.

The source is outcome-blind at prepare time and decision-step diverse.  Each
selected focal anchor retains every one of its 27 legal non-Main physical
siblings.  Shards create either one common Main tape or one initialization-
matched frozen Q1+Q3 tape, hold only the focal candidate, and replay every
nonfocal physical action identically.  This command never trains, opens TEST,
or evaluates held-out EE.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mechanics = _load_module(
    "mcrl_v05_c2_controlled_source_mechanics",
    HERE / "run_v05_c2_controlled_tape.py",
)
phase_b = mechanics.phase_b
support = phase_b.support


PREPARE_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-source-prepare-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-source-shard-v1"
ROW_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-source-row-v1"
PAIR_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-learner-pair-v1"
MERGE_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-source-merge-v1"
CLAIM_CEILING = "TRAIN_SOURCE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
Q13_SEEDS = (2026092101, 2026092102, 2026092103)
POLICY_VIEWS = ("main", "q13")
ANCHORS_PER_WORLD = 4
SIBLINGS_PER_ANCHOR = 27
EXPECTED_ANCHORS = 12
EXPECTED_ROWS_PER_VIEW = EXPECTED_ANCHORS * SIBLINGS_PER_ANCHOR
EXPECTED_TOTAL_ROWS = EXPECTED_ROWS_PER_VIEW * 4
STRATA = (
    ("e", frozenset({1, 2}), tuple(range(2026093001, 2026093011))),
    ("m", frozenset({3, 4}), tuple(range(2026093011, 2026093021))),
    ("l", frozenset({5, 6}), tuple(range(2026093021, 2026093031))),
)


class ControlledSourceError(RuntimeError):
    """A V0.5 controlled-source contract failed closed."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ControlledSourceError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ControlledSourceError(f"{field} must be a two-integer physical key")
    if any(type(item) is not int or item < 0 for item in value):
        raise ControlledSourceError(f"{field} must be a two-integer physical key")
    return int(value[0]), int(value[1])


def _physical_or_none(value: object, *, field: str) -> tuple[int, int] | None:
    if value is None:
        return None
    return _physical_key(value, field=field)


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ControlledSourceError(f"{field} must be an exact integer >= {minimum}")
    return value


def _canonical_bytes(payload: object) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ControlledSourceError("payload is not finite canonical JSON") from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ControlledSourceError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ControlledSourceError(f"sealed JSON artifact is missing or non-regular: {source}")
    raw = source.read_bytes()
    try:
        value = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda constant: (_ for _ in ()).throw(ValueError(constant)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ControlledSourceError(f"invalid JSON: {source}") from error
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise ControlledSourceError(f"artifact is not canonical JSON: {source}")
    return value, hashlib.sha256(raw).hexdigest()


def _write_once(path: Path, payload: Mapping[str, object]) -> str:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise ControlledSourceError(f"refusing to overwrite {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(dict(payload))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard link is an exclusive finalization step: if another writer
        # wins the race after the preflight check, the existing artifact is
        # preserved and this write fails closed.
        os.link(temporary, target)
    except FileExistsError as error:
        raise ControlledSourceError(f"refusing to overwrite {target}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(raw).hexdigest()


def _authenticate_common(args: argparse.Namespace) -> tuple[dict[str, Any], Mapping[str, Any]]:
    phase_a = phase_b._authenticate_phase_a(
        Path(args.phase_a_dir),
        prereg_path=Path(args.prereg),
    )
    return phase_a, phase_a["modules"]


def _validate_prepare_receipt(
    result: Mapping[str, object], schedule: Any
) -> None:
    """Revalidate the semantic step-strata behind a canonical prepare file.

    The schedule class authenticates the 12/324 census, but it deliberately
    knows nothing about V05's three frozen step strata.  Keep that boundary in
    this consumer so a writer cannot replace the strata metadata (and merely
    recompute ``prepare_sha256``) without also matching every selected anchor.
    """

    expected_fields = {
        "schema",
        "status",
        "claim_ceiling",
        "selection_rule",
        "strata",
        "schedule",
        "anchor_count",
        "sibling_count_per_policy_view",
        "policy_views",
        "counterfactual_outcomes_evaluated",
        "training_run",
        "test_split_opened",
        "held_out_ee_evaluated",
        "elapsed_s",
        "prepare_sha256",
    }
    if set(result) != expected_fields:
        raise ControlledSourceError("controlled prepare receipt has unexpected fields")
    if (
        result["schema"] != PREPARE_SCHEMA
        or result["status"] != "CONTROLLED_SOURCE_SCHEDULE_PREPARED"
        or result["claim_ceiling"] != CLAIM_CEILING
        or result["selection_rule"] != "first-eligible-world-in-each-frozen-step-stratum-v1"
    ):
        raise ControlledSourceError("controlled prepare receipt header drifted")
    if result["anchor_count"] != EXPECTED_ANCHORS:
        raise ControlledSourceError("controlled prepare anchor count drifted")
    if result["sibling_count_per_policy_view"] != EXPECTED_ROWS_PER_VIEW:
        raise ControlledSourceError("controlled prepare sibling count drifted")
    expected_views = ["main", *[f"q13-{seed}" for seed in Q13_SEEDS]]
    if result["policy_views"] != expected_views:
        raise ControlledSourceError("controlled prepare policy views drifted")
    for field in (
        "counterfactual_outcomes_evaluated",
        "training_run",
        "test_split_opened",
        "held_out_ee_evaluated",
    ):
        if result[field] is not False:
            raise ControlledSourceError(f"prepare.{field} must be false")
    elapsed = result["elapsed_s"]
    if type(elapsed) not in (int, float) or not math.isfinite(float(elapsed)) or float(elapsed) < 0.0:
        raise ControlledSourceError("prepare.elapsed_s must be finite and nonnegative")

    strata = result["strata"]
    if not isinstance(strata, list) or len(strata) != len(STRATA):
        raise ControlledSourceError("controlled prepare must contain three strata")
    if not hasattr(schedule, "anchors") or not hasattr(schedule, "rows"):
        raise ControlledSourceError("controlled prepare schedule is malformed")
    if len(schedule.anchors) != EXPECTED_ANCHORS or len(schedule.rows) != EXPECTED_ROWS_PER_VIEW:
        raise ControlledSourceError("controlled prepare cardinality drifted")

    selected_steps: list[int] = []
    selected_interventions: set[tuple[int, str, str, int]] = set()
    for record, (label, eligible_steps, seed_pool) in zip(strata, STRATA):
        if not isinstance(record, Mapping):
            raise ControlledSourceError("controlled prepare stratum is malformed")
        required = {
            "stratum",
            "eligible_steps",
            "seed_pool",
            "scanned_seeds",
            "selected_source_seed",
            "selected_anchor_step",
            "world_anchor_sha256",
            "focal_users",
        }
        if set(record) != required:
            raise ControlledSourceError(f"controlled prepare stratum {label} has unexpected fields")
        if (
            record["stratum"] != label
            or record["eligible_steps"] != sorted(eligible_steps)
            or record["seed_pool"] != list(seed_pool)
        ):
            raise ControlledSourceError(f"controlled prepare stratum {label} definition drifted")
        scanned = record["scanned_seeds"]
        if (
            not isinstance(scanned, list)
            or not scanned
            or any(type(seed) is not int for seed in scanned)
            or scanned != list(seed_pool[: len(scanned)])
            or scanned[-1] != record["selected_source_seed"]
        ):
            raise ControlledSourceError(f"controlled prepare stratum {label} scan order drifted")
        selected_seed = _exact_int(
            record["selected_source_seed"],
            field=f"strata[{label}].selected_source_seed",
        )
        selected_step = _exact_int(
            record["selected_anchor_step"],
            field=f"strata[{label}].selected_anchor_step",
            minimum=1,
        )
        if selected_seed not in scanned or selected_step not in eligible_steps:
            raise ControlledSourceError(f"controlled prepare stratum {label} selection drifted")
        world = _digest(record["world_anchor_sha256"], field=f"strata[{label}].world_anchor_sha256")
        focal_users = record["focal_users"]
        if (
            not isinstance(focal_users, list)
            or len(focal_users) != ANCHORS_PER_WORLD
            or any(type(user) is not int or user < 0 for user in focal_users)
            or focal_users != sorted(set(focal_users))
        ):
            raise ControlledSourceError(f"controlled prepare stratum {label} focal users drifted")
        matching = tuple(
            sorted(
                (
                    anchor
                    for anchor in schedule.anchors
                    if anchor.source_seed == selected_seed
                    and anchor.anchor_step == selected_step
                    and anchor.world_anchor_sha256 == world
                ),
                key=lambda anchor: anchor.focal_user,
            )
        )
        if len(matching) != ANCHORS_PER_WORLD or [anchor.focal_user for anchor in matching] != focal_users:
            raise ControlledSourceError(f"controlled prepare stratum {label} does not match schedule")
        if any(anchor.evaluation_seed != selected_seed for anchor in matching):
            raise ControlledSourceError(f"controlled prepare stratum {label} evaluation seed drifted")
        selected_steps.append(selected_step)
        for anchor in matching:
            intervention = anchor.intervention_key
            if intervention in selected_interventions:
                raise ControlledSourceError("controlled prepare has duplicate interventions")
            selected_interventions.add(intervention)

    if len(selected_interventions) != EXPECTED_ANCHORS or len(set(selected_steps)) != len(STRATA):
        raise ControlledSourceError("controlled prepare is not three-stratum diverse")
    if len({anchor.source_manifest_sha256 for anchor in schedule.anchors}) != 1:
        raise ControlledSourceError("controlled prepare source manifest drifted across anchors")
    if len({anchor.policy_sha256 for anchor in schedule.anchors}) != 1:
        raise ControlledSourceError("controlled prepare Main policy drifted across anchors")
    for anchor in schedule.anchors:
        if anchor.intervention_key not in selected_interventions:
            raise ControlledSourceError("controlled prepare contains an unscheduled anchor")


def _validate_policy_components(
    value: object,
    *,
    tape_policy: str,
    initialization_seed: int | None,
    reference_policy_sha256: str,
    main_policy_sha256: str | None = None,
) -> dict[str, object]:
    """Validate the Main/Q1+Q3 policy receipt without loading a learner."""

    reference_sha = _digest(
        reference_policy_sha256, field="reference_policy_sha256"
    )
    if not isinstance(value, Mapping):
        raise ControlledSourceError("reference policy components are malformed")
    try:
        components = mechanics._validate_reference_policy_components(
            value,
            tape_policy=tape_policy,
            reference_policy_sha256=reference_sha,
        )
    except Exception as error:
        raise ControlledSourceError("reference policy-component receipt failed authentication") from error
    if not isinstance(components, dict):
        raise ControlledSourceError("reference policy-component receipt is malformed")
    _digest(components["policy_components_sha256"], field="policy_components_sha256")
    if tape_policy == "main":
        _digest(components["main_policy_sha256"], field="main_policy_sha256")
        if main_policy_sha256 is not None and components["main_policy_sha256"] != main_policy_sha256:
            raise ControlledSourceError("Main policy component is not bound to the sealed policy")
    elif tape_policy == "q13":
        if initialization_seed not in Q13_SEEDS or components.get("initialization_seed") != initialization_seed:
            raise ControlledSourceError("Q1+Q3 policy-component initialization seed drifted")
        _digest(components["q1_parameters_sha256"], field="q1_parameters_sha256")
        _digest(components["q3_parameters_sha256"], field="q3_parameters_sha256")
        if components.get("q2_excluded_from_policy") is not True:
            raise ControlledSourceError("Q1+Q3 policy receipt does not exclude Q2")
    else:
        raise ControlledSourceError(f"unknown controlled tape policy: {tape_policy}")
    return components


def _hex_float(value: object, *, field: str, positive: bool = False) -> float:
    if not isinstance(value, str):
        raise ControlledSourceError(f"{field} must be a hexadecimal float")
    try:
        parsed = float.fromhex(value)
    except (TypeError, ValueError) as error:
        raise ControlledSourceError(f"{field} is not a hexadecimal float") from error
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise ControlledSourceError(f"{field} must be {'positive ' if positive else ''}finite")
    return parsed


def _validate_trace_mapping(value: object, *, field: str) -> Mapping[str, object]:
    """Check the persisted trace shape used by tape and target reconstruction."""

    if not isinstance(value, Mapping):
        raise ControlledSourceError(f"{field} is malformed")
    required = {
        "active_physical_ids",
        "detached_main_actions",
        "detached_main_physical_actions",
        "done",
        "executed_actions",
        "executed_physical_actions",
        "held_key_match_count",
        "held_physical_key",
        "link_rate_bps",
        "mask_matrix_sha256",
        "offsets",
        "release_offset",
        "release_reason",
        "served",
        "state_matrix_sha256",
        "system_power_w",
    }
    if set(value) != required:
        raise ControlledSourceError(f"{field} trace fields drifted")
    if value["offsets"] != [0, 1, 2, 3]:
        raise ControlledSourceError(f"{field}.offsets must be [0, 1, 2, 3]")
    for name in (
        "detached_main_actions",
        "detached_main_physical_actions",
        "executed_actions",
        "executed_physical_actions",
        "link_rate_bps",
        "served",
        "active_physical_ids",
        "done",
        "held_physical_key",
        "held_key_match_count",
        "release_offset",
        "release_reason",
        "state_matrix_sha256",
        "mask_matrix_sha256",
    ):
        raw = value[name]
        if not isinstance(raw, list) or len(raw) != 4:
            raise ControlledSourceError(f"{field}.{name} must cover offsets 0..3")
    rates = value["link_rate_bps"]
    powers = value["system_power_w"]
    if not isinstance(powers, list) or len(powers) != 4:
        raise ControlledSourceError(f"{field}.system_power_w must cover offsets 0..3")
    try:
        rate_array = np.asarray(rates, dtype=np.float64)
        power_array = np.asarray(powers, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ControlledSourceError(f"{field} rates/powers are not numeric") from error
    if (
        rate_array.ndim != 2
        or rate_array.shape[0] != 4
        or power_array.shape != (4,)
        or not np.all(np.isfinite(rate_array))
        or not np.all(np.isfinite(power_array))
        or np.any(rate_array < 0.0)
        or np.any(power_array <= 0.0)
    ):
        raise ControlledSourceError(f"{field} rates/powers are invalid")
    users = rate_array.shape[1]
    if users <= 0:
        raise ControlledSourceError(f"{field} has no users")
    for offset in range(4):
        for name in (
            "detached_main_actions",
            "detached_main_physical_actions",
            "executed_actions",
            "executed_physical_actions",
            "served",
        ):
            if not isinstance(value[name][offset], list) or len(value[name][offset]) != users:
                raise ControlledSourceError(f"{field}.{name}[{offset}] user width drifted")
        if not isinstance(value["done"][offset], bool):
            raise ControlledSourceError(f"{field}.done[{offset}] must be Boolean")
        for digest_name in ("state_matrix_sha256", "mask_matrix_sha256"):
            _digest(value[digest_name][offset], field=f"{field}.{digest_name}[{offset}]")
    return value


def _physical_vector(value: object, *, field: str, users: int) -> tuple[tuple[int, int] | None, ...]:
    if not isinstance(value, list) or len(value) != users:
        raise ControlledSourceError(f"{field} must contain {users} physical actions")
    return tuple(_physical_or_none(item, field=f"{field}[{index}]") for index, item in enumerate(value))


def _action_vector(value: object, *, field: str, users: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != users:
        raise ControlledSourceError(f"{field} must contain {users} actions")
    actions: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int or not -1 <= item < 28:
            raise ControlledSourceError(f"{field}[{index}] must be an action in [-1, 28)")
        actions.append(item)
    return tuple(actions)


def _validate_action_physical_binding(
    actions: tuple[int, ...],
    physical: tuple[tuple[int, int] | None, ...],
    *,
    field: str,
) -> None:
    if len(actions) != len(physical):
        raise ControlledSourceError(f"{field} action/physical widths disagree")
    for index, (action, key) in enumerate(zip(actions, physical, strict=True)):
        if (action == -1) != (key is None):
            raise ControlledSourceError(f"{field}[{index}] action/physical binding disagrees")


def _validate_controlled_receipts(
    *,
    row: Mapping[str, object],
    anchor: Any,
    tape_policy: str,
    initialization_seed: int | None,
    reference_policy_components: Mapping[str, object],
) -> None:
    """Reconstruct tape, pair plan, and all-user target from persisted traces."""

    raw = row.get("raw_trace")
    if not isinstance(raw, Mapping):
        raise ControlledSourceError("controlled row raw_trace is missing")
    if set(raw) != {
        "candidate",
        "continuation_start_offset",
        "reference",
        "reference_policy_decisions",
        "release_offset",
        "release_reason",
        "support_counts",
    }:
        raise ControlledSourceError("controlled row raw_trace fields drifted")
    reference = _validate_trace_mapping(raw["reference"], field="raw_trace.reference")
    candidate = _validate_trace_mapping(raw["candidate"], field="raw_trace.candidate")
    if reference["link_rate_bps"] and len(reference["link_rate_bps"][0]) != len(candidate["link_rate_bps"][0]):
        raise ControlledSourceError("reference/candidate user width drifted")
    if raw["continuation_start_offset"] != 1:
        raise ControlledSourceError("controlled continuation must start at offset 1")
    support_counts = raw["support_counts"]
    release_offset = _exact_int(raw["release_offset"], field="raw_trace.release_offset", minimum=1)
    if (
        not isinstance(support_counts, list)
        or len(support_counts) != 4
        or any(type(value) is not int or value < 0 for value in support_counts)
        or release_offset not in (1, 2, 3)
        or raw["release_reason"] not in ("horizon", "support_expired")
    ):
        raise ControlledSourceError("controlled release receipt is malformed")
    if raw["release_reason"] == "horizon":
        if release_offset != 3 or support_counts != [1, 1, 1, 1]:
            raise ControlledSourceError("horizon release receipt is malformed")
    elif any(value != 1 for value in support_counts[:release_offset]) or support_counts[release_offset] != 0:
        raise ControlledSourceError("support-expiry receipt is malformed")
    if any(value > 1 for value in support_counts[release_offset + 1 :]):
        raise ControlledSourceError("support-expiry receipt is ambiguous")

    try:
        decisions = raw["reference_policy_decisions"]
        if not isinstance(decisions, list) or len(decisions) != 3:
            raise ControlledSourceError("reference policy decisions must cover offsets 1..3")
        reference_users = len(reference["link_rate_bps"][0])
        for index, decision in enumerate(decisions):
            if not isinstance(decision, Mapping):
                raise ControlledSourceError("reference policy decision is malformed")
            if tape_policy == "main":
                if set(decision) != {"actions", "offset", "policy"} or decision["policy"] != "main":
                    raise ControlledSourceError("Main continuation policy receipt is malformed")
            else:
                expected_decision_fields = {
                    "actions",
                    "c3_state_sha256",
                    "decision_sha256",
                    "initialization_seed",
                    "legacy_state_sha256",
                    "mask_sha256",
                    "offset",
                    "q1_sha256",
                    "q3_sha256",
                    "schema",
                    "selected_q3_rung",
                }
                if set(decision) != expected_decision_fields or decision["schema"] != "multi-catfish-mcrl-v04-c2-q13-continuation-v1" or decision["selected_q3_rung"] != 100 or decision["initialization_seed"] != initialization_seed:
                    raise ControlledSourceError("Q1+Q3 continuation policy receipt is malformed")
                for field in ("c3_state_sha256", "decision_sha256", "legacy_state_sha256", "mask_sha256", "q1_sha256", "q3_sha256"):
                    _digest(decision[field], field=f"reference_policy_decisions[{index}].{field}")
            offset = _exact_int(decision["offset"], field=f"reference_policy_decisions[{index}].offset", minimum=1)
            if offset != index + 1:
                raise ControlledSourceError("reference policy decisions are not ordered 1..3")
            if _action_vector(decision["actions"], field=f"reference_policy_decisions[{index}].actions", users=reference_users) != _action_vector(reference["detached_main_actions"][offset], field=f"raw_trace.reference.detached_main_actions[{offset}]", users=reference_users):
                raise ControlledSourceError("reference policy decision actions disagree with trace")

        tape = mechanics.controlled.build_reference_action_tape(
            reference,
            anchor_sha256=anchor.anchor_sha256,
            reference_policy_sha256=str(row["reference_policy_sha256"]),
            common_random_field_sha256=str(row["common_random_field_sha256"]),
            focal_user=int(row["focal_user"]),
        )
        if tape.as_mapping() != dict(row["tape"]):
            raise ControlledSourceError("controlled tape mapping disagrees with reference trace")
        if tape.steps[0].physical_actions[int(row["focal_user"])] != anchor.reference_physical_key:
            raise ControlledSourceError("controlled tape opening focal key disagrees with anchor")
        plan_mapping = row["pair_plan"]
        if not isinstance(plan_mapping, Mapping):
            raise ControlledSourceError("controlled pair plan is missing")
        plan_steps = plan_mapping.get("steps")
        if not isinstance(plan_steps, list) or len(plan_steps) != 4:
            raise ControlledSourceError("controlled pair plan steps are malformed")
        step_objects = tuple(
            mechanics.controlled.ControlledTapeStepPlan(
                offset=step["offset"],
                reference_actions=tuple(step["reference_actions"]),
                candidate_actions=tuple(step["candidate_actions"]),
                reference_physical_actions=tuple(
                    None if value is None else tuple(value)
                    for value in step["reference_physical_actions"]
                ),
                candidate_physical_actions=tuple(
                    None if value is None else tuple(value)
                    for value in step["candidate_physical_actions"]
                ),
                focal_mode=step["focal_mode"],
                nonfocal_equal=step["nonfocal_equal"],
                nonfocal_equality_sha256=step["nonfocal_equality_sha256"],
            )
            for step in plan_steps
            if isinstance(step, Mapping)
        )
        if len(step_objects) != 4:
            raise ControlledSourceError("controlled pair plan step is malformed")
        plan = mechanics.controlled.ControlledTapePairPlan(
            tape_sha256=plan_mapping["tape_sha256"],
            focal_user=plan_mapping["focal_user"],
            held_physical_key=tuple(plan_mapping["held_physical_key"]),
            release_offset=plan_mapping["release_offset"],
            release_reason=plan_mapping["release_reason"],
            support_counts=tuple(plan_mapping["support_counts"]),
            steps=step_objects,
            plan_sha256=plan_mapping["plan_sha256"],
        )
        plan.verify(tape)
        if plan.as_mapping(tape) != dict(plan_mapping):
            raise ControlledSourceError("controlled pair-plan mapping is not canonical")
        if plan.release_offset != release_offset or plan.release_reason != raw["release_reason"] or list(plan.support_counts) != support_counts:
            raise ControlledSourceError("controlled pair-plan release receipt disagrees")
        users = tape.user_count
        candidate_key = _physical_key(row["candidate_physical_key"], field="row.candidate_physical_key")
        for offset in range(4):
            reference_detached_actions = _action_vector(
                reference["detached_main_actions"][offset],
                field=f"raw_trace.reference.detached_main_actions[{offset}]",
                users=users,
            )
            reference_detached_physical = _physical_vector(
                reference["detached_main_physical_actions"][offset],
                field=f"raw_trace.reference.detached_main_physical_actions[{offset}]",
                users=users,
            )
            candidate_detached_actions = _action_vector(
                candidate["detached_main_actions"][offset],
                field=f"raw_trace.candidate.detached_main_actions[{offset}]",
                users=users,
            )
            candidate_detached_physical = _physical_vector(
                candidate["detached_main_physical_actions"][offset],
                field=f"raw_trace.candidate.detached_main_physical_actions[{offset}]",
                users=users,
            )
            reference_executed_actions = _action_vector(
                reference["executed_actions"][offset],
                field=f"raw_trace.reference.executed_actions[{offset}]",
                users=users,
            )
            reference_executed_physical = _physical_vector(
                reference["executed_physical_actions"][offset],
                field=f"raw_trace.reference.executed_physical_actions[{offset}]",
                users=users,
            )
            candidate_executed_actions = _action_vector(
                candidate["executed_actions"][offset],
                field=f"raw_trace.candidate.executed_actions[{offset}]",
                users=users,
            )
            candidate_executed_physical = _physical_vector(
                candidate["executed_physical_actions"][offset],
                field=f"raw_trace.candidate.executed_physical_actions[{offset}]",
                users=users,
            )
            _validate_action_physical_binding(
                reference_detached_actions,
                reference_detached_physical,
                field=f"raw_trace.reference.detached_main[{offset}]",
            )
            _validate_action_physical_binding(
                candidate_detached_actions,
                candidate_detached_physical,
                field=f"raw_trace.candidate.detached_main[{offset}]",
            )
            _validate_action_physical_binding(
                reference_executed_actions,
                reference_executed_physical,
                field=f"raw_trace.reference.executed[{offset}]",
            )
            _validate_action_physical_binding(
                candidate_executed_actions,
                candidate_executed_physical,
                field=f"raw_trace.candidate.executed[{offset}]",
            )
            if reference_executed_actions != plan.steps[offset].reference_actions:
                raise ControlledSourceError("reference action receipt disagrees with pair plan")
            if candidate_executed_actions != plan.steps[offset].candidate_actions:
                raise ControlledSourceError("candidate action receipt disagrees with pair plan")
            if reference_executed_physical != plan.steps[offset].reference_physical_actions:
                raise ControlledSourceError("reference physical receipt disagrees with pair plan")
            if candidate_executed_physical != plan.steps[offset].candidate_physical_actions:
                raise ControlledSourceError("candidate physical receipt disagrees with pair plan")
            if (
                reference["held_physical_key"][offset] is not None
                or reference["held_key_match_count"][offset] is not None
                or reference["release_offset"][offset] is not None
                or reference["release_reason"][offset] is not None
            ):
                raise ControlledSourceError("reference trace carries candidate hold metadata")
            if candidate["held_physical_key"][offset] != list(candidate_key):
                raise ControlledSourceError("candidate held-key receipt disagrees")
            if candidate["held_key_match_count"][offset] != support_counts[offset]:
                raise ControlledSourceError("candidate support-count receipt disagrees")
            if candidate["release_offset"][offset] != release_offset or candidate["release_reason"][offset] != raw["release_reason"]:
                raise ControlledSourceError("candidate release receipt disagrees")
        target_mapping = row["target"]
        if not isinstance(target_mapping, Mapping):
            raise ControlledSourceError("controlled target is missing")
        multiplier = _hex_float(target_mapping["lambda_bits_per_j"], field="target.lambda_bits_per_j", positive=True)
        interval = _hex_float(target_mapping["interval_s"], field="target.interval_s", positive=True)
        target = mechanics.controlled.build_controlled_tape_target(
            tape_sha256=tape.tape_sha256,
            reference_rates_bps=np.asarray(reference["link_rate_bps"], dtype=np.float64),
            candidate_rates_bps=np.asarray(candidate["link_rate_bps"], dtype=np.float64),
            reference_system_power_w=np.asarray(reference["system_power_w"], dtype=np.float64),
            candidate_system_power_w=np.asarray(candidate["system_power_w"], dtype=np.float64),
            lambda_bits_per_j=multiplier,
            interval_s=interval,
        )
        if target.as_mapping() != dict(target_mapping):
            raise ControlledSourceError("controlled target disagrees with raw traces")
    except ControlledSourceError:
        raise
    except Exception as error:
        raise ControlledSourceError("controlled tape/plan/target receipt failed authentication") from error


def _validate_source_row(
    *,
    row: object,
    anchor: Any,
    candidate_key: tuple[int, int],
    tape_policy: str,
    initialization_seed: int | None,
    expected_policy_components: Mapping[str, object],
) -> None:
    """Authenticate one source row against its sealed anchor and policy view."""

    if not isinstance(row, Mapping):
        raise ControlledSourceError("controlled source row is malformed")
    expected_fields = {
        "schema",
        "source_route",
        "tape_policy",
        "anchor_sha256",
        "anchor_schedule_sha256",
        "source_manifest_sha256",
        "source_seed",
        "evaluation_seed",
        "initialization_seed",
        "focal_user",
        "candidate_physical_key",
        "reference_policy_sha256",
        "reference_policy_components",
        "common_random_field_sha256",
        "tape",
        "pair_plan",
        "target",
        "raw_trace",
        "training_run",
        "test_split_opened",
        "held_out_ee_evaluated",
        "anchor_step",
        "anchor_state",
        "learner_pair",
    }
    if set(row) != expected_fields:
        raise ControlledSourceError("controlled source row has unexpected fields")
    if row["schema"] != ROW_SCHEMA or row["source_route"] != "C2" or row["tape_policy"] != tape_policy:
        raise ControlledSourceError("controlled source row schema/route/policy drifted")
    for field in (
        "anchor_sha256",
        "anchor_schedule_sha256",
        "source_manifest_sha256",
        "common_random_field_sha256",
        "reference_policy_sha256",
    ):
        _digest(row[field], field=f"row.{field}")
    if (
        row["anchor_sha256"] != anchor.anchor_sha256
        or row["anchor_schedule_sha256"] != anchor.anchor_schedule_sha256
        or row["source_manifest_sha256"] != anchor.source_manifest_sha256
        or row["common_random_field_sha256"] != anchor.common_random_field_sha256
    ):
        raise ControlledSourceError("controlled source row anchor lineage drifted")
    if (
        row["source_seed"] != anchor.source_seed
        or row["evaluation_seed"] != anchor.evaluation_seed
        or row["anchor_step"] != anchor.anchor_step
        or row["focal_user"] != anchor.focal_user
        or row["initialization_seed"] != initialization_seed
    ):
        raise ControlledSourceError("controlled source row seed/step/focal lineage drifted")
    for field in ("source_seed", "evaluation_seed", "anchor_step", "focal_user"):
        _exact_int(row[field], field=f"row.{field}")
    if initialization_seed is not None:
        _exact_int(row["initialization_seed"], field="row.initialization_seed")
    elif row["initialization_seed"] is not None:
        raise ControlledSourceError("Main source row must not carry an initialization seed")
    if _physical_key(row["candidate_physical_key"], field="row.candidate_physical_key") != candidate_key:
        raise ControlledSourceError("controlled source row candidate key drifted")
    for field in ("training_run", "test_split_opened", "held_out_ee_evaluated"):
        if row[field] is not False:
            raise ControlledSourceError(f"controlled source row opens forbidden {field}")
    components = _validate_policy_components(
        row["reference_policy_components"],
        tape_policy=tape_policy,
        initialization_seed=initialization_seed,
        reference_policy_sha256=str(row["reference_policy_sha256"]),
        main_policy_sha256=anchor.policy_sha256 if tape_policy == "main" else None,
    )
    if components != dict(expected_policy_components):
        raise ControlledSourceError("controlled source row policy receipt disagrees with shard")
    try:
        state = phase_b._validate_anchor_state_record(
            row["anchor_state"], field="controlled source row.anchor_state"
        )
    except Exception as error:
        raise ControlledSourceError("controlled source row anchor-state receipt failed authentication") from error
    _validate_controlled_receipts(
        row=row,
        anchor=anchor,
        tape_policy=tape_policy,
        initialization_seed=initialization_seed,
        reference_policy_components=components,
    )
    pair = row["learner_pair"]
    if not isinstance(pair, Mapping):
        raise ControlledSourceError("controlled source row learner pair is missing")
    try:
        expected_pair = _learner_pair(row=row, anchor_state=state)
    except Exception as error:
        raise ControlledSourceError("controlled source row learner pair cannot be rebuilt") from error
    if dict(pair) != expected_pair:
        raise ControlledSourceError("controlled source row learner pair disagrees with anchor state")


class _ModuleView:
    """Read-only module view with a small set of local callable overrides."""

    def __init__(self, base: object, **overrides: object) -> None:
        self._base = base
        self._overrides = dict(overrides)

    def __getattr__(self, name: str) -> object:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._base, name)


def _real_seed_topology_for_steps(
    *,
    source_seed: int,
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
    eligible_steps: frozenset[int],
) -> tuple[Any, ...]:
    """Use the sealed V0.4 scanner while filtering anchors pre-outcome.

    The sealed scanner remains byte-for-byte unchanged.  This additive V0.5
    view records the current decision step at the Main-policy boundary and
    exposes departure users only inside the frozen step stratum.  Main
    actions, states, candidate topology, and every physical replay remain the
    original scanner's outputs.
    """

    if (
        type(eligible_steps) is not frozenset
        or not eligible_steps
        or any(type(value) is not int or value < 1 for value in eligible_steps)
    ):
        raise ControlledSourceError(
            "eligible_steps must be a nonempty frozenset of positive integers"
        )
    backend_smoke = modules["backend_smoke"]
    pair_smoke = modules["pair_smoke"]
    current_step: dict[str, int | None] = {"value": None}

    def _main_decision(
        trainer: Any,
        wrapped: Any,
        states: Any,
        masks: Any,
        observation: Any,
        env_rng: Any,
    ) -> Any:
        current_step["value"] = int(observation.step_index)
        return backend_smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )

    def _departure_users(wrapped: Any, main_physical: Any) -> tuple[int, ...]:
        departures = tuple(pair_smoke._departure_users(wrapped, main_physical))
        step = current_step["value"]
        if step is None:
            raise ControlledSourceError(
                "departure scan occurred before the Main decision boundary"
            )
        return departures if step in eligible_steps else ()

    filtered_modules = dict(modules)
    filtered_modules["backend_smoke"] = _ModuleView(
        backend_smoke,
        _main_decision=_main_decision,
    )
    filtered_modules["pair_smoke"] = _ModuleView(
        pair_smoke,
        _departure_users=_departure_users,
    )
    return tuple(
        support._real_seed_topology(
            source_seed=source_seed,
            modules=filtered_modules,
            context=context,
        )
    )


def _prepare(args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    _phase_a, modules = _authenticate_common(args)
    selected_anchors: list[Any] = []
    selected: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v05-c2-controlled-source-tle-") as temporary:
        context = support._production_main_context(
            modules=modules,
            prereg_path=Path(args.prereg),
            tle_root=Path(args.tle_root),
            temporary=Path(temporary),
        )
        for label, steps, seeds in STRATA:
            chosen = None
            scanned: list[int] = []
            for seed in seeds:
                scanned.append(seed)
                candidates = _real_seed_topology_for_steps(
                    source_seed=seed,
                    modules=modules,
                    context=context,
                    eligible_steps=steps,
                )
                eligible = sorted(
                    (value for value in candidates if value.eligible),
                    key=lambda value: (value.step_index, value.world_anchor_sha256),
                )
                if eligible:
                    chosen = eligible[0]
                    break
            if chosen is None:
                raise ControlledSourceError(
                    f"no eligible topology for stratum {label} and its frozen seed pool"
                )
            schedules = chosen.selected_anchor_schedules()
            if len(schedules) != ANCHORS_PER_WORLD or chosen.step_index not in steps:
                raise ControlledSourceError("selected stratum topology is malformed")
            selected_anchors.extend(schedules)
            selected.append(
                {
                    "stratum": label,
                    "eligible_steps": sorted(steps),
                    "seed_pool": list(seeds),
                    "scanned_seeds": scanned,
                    "selected_source_seed": int(chosen.source_seed),
                    "selected_anchor_step": int(chosen.step_index),
                    "world_anchor_sha256": chosen.world_anchor_sha256,
                    "focal_users": [int(value.focal_user) for value in schedules],
                }
            )
    schedule = support.build_c2_v04_support_complete_schedule(selected_anchors)
    if len(schedule.anchors) != EXPECTED_ANCHORS or len(schedule.rows) != EXPECTED_ROWS_PER_VIEW:
        raise ControlledSourceError("controlled source is not exactly 12 anchors and 324 siblings")
    steps = sorted({int(anchor.anchor_step) for anchor in schedule.anchors})
    if len(steps) != 3 or not all(
        selected[index]["selected_anchor_step"] in STRATA[index][1]
        for index in range(len(STRATA))
    ):
        raise ControlledSourceError("controlled source is not decision-step diverse")
    body: dict[str, object] = {
        "schema": PREPARE_SCHEMA,
        "status": "CONTROLLED_SOURCE_SCHEDULE_PREPARED",
        "claim_ceiling": CLAIM_CEILING,
        "selection_rule": "first-eligible-world-in-each-frozen-step-stratum-v1",
        "strata": selected,
        "schedule": schedule.to_mapping(),
        "anchor_count": len(schedule.anchors),
        "sibling_count_per_policy_view": len(schedule.rows),
        "policy_views": ["main", *[f"q13-{seed}" for seed in Q13_SEEDS]],
        "counterfactual_outcomes_evaluated": False,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "elapsed_s": float(time.monotonic() - started),
    }
    body["prepare_sha256"] = _canonical_sha256(body)
    _validate_prepare_receipt(body, schedule)
    file_sha = _write_once(Path(args.output_file), body)
    return {"status": body["status"], "output_file_sha256": file_sha}


def _read_prepare(path: Path) -> tuple[dict[str, Any], Any, str]:
    result, file_sha = _read_json(path)
    body = dict(result)
    claimed = body.pop("prepare_sha256", None)
    if (
        result.get("schema") != PREPARE_SCHEMA
        or result.get("status") != "CONTROLLED_SOURCE_SCHEDULE_PREPARED"
        or result.get("claim_ceiling") != CLAIM_CEILING
        or claimed != _canonical_sha256(body)
        or result.get("counterfactual_outcomes_evaluated") is not False
        or result.get("training_run") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
    ):
        raise ControlledSourceError("controlled prepare receipt failed authentication")
    schedule = support.C2V04SupportCompleteSchedule.from_mapping(result.get("schedule"))
    _validate_prepare_receipt(result, schedule)
    return result, schedule, file_sha


def _learner_pair(
    *,
    row: Mapping[str, object],
    anchor_state: Mapping[str, object],
) -> dict[str, object]:
    plan = row["pair_plan"]
    target = row["target"]
    if not isinstance(plan, Mapping) or not isinstance(target, Mapping):
        raise ControlledSourceError("controlled row lacks plan or target")
    steps = plan.get("steps")
    if not isinstance(steps, list) or len(steps) != 4 or not isinstance(steps[0], Mapping):
        raise ControlledSourceError("controlled plan has no opening action pair")
    focal = int(row["focal_user"])
    reference_actions = steps[0].get("reference_actions")
    candidate_actions = steps[0].get("candidate_actions")
    if not isinstance(reference_actions, list) or not isinstance(candidate_actions, list):
        raise ControlledSourceError("controlled opening actions are malformed")
    if not 0 <= focal < len(reference_actions) or len(candidate_actions) != len(reference_actions):
        raise ControlledSourceError("controlled opening actions do not contain the focal user")
    body: dict[str, object] = {
        "schema": PAIR_SCHEMA,
        "anchor_state_sha256": anchor_state["anchor_state_sha256"],
        "focal_user": focal,
        "reference_action": int(reference_actions[focal]),
        "candidate_action": int(candidate_actions[focal]),
        "candidate_physical_key": row["candidate_physical_key"],
        "target_sha256": target["target_sha256"],
        "zeta2_temporal_surplus_bits": target["zeta2_temporal_surplus_bits"],
        "tape_policy": row["tape_policy"],
        "initialization_seed": row["initialization_seed"],
    }
    body["learner_pair_sha256"] = _canonical_sha256(body)
    return body


def _materialize_source_row(
    *,
    anchor: Any,
    candidate_key: tuple[int, int],
    hybrid: Any | None,
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
    reference_policy_sha256: str,
    reference_policy_components: Mapping[str, object],
    tape_policy: str,
) -> dict[str, object]:
    replay = support._replay_main_to_step(
        source_seed=anchor.source_seed,
        target_step=anchor.anchor_step,
        modules=modules,
        context=context,
    )
    service = support._real_service_for_sealed_anchor(
        anchor=anchor,
        replay=replay,
        modules=modules,
        context=context,
    )
    prepared = service.prepare_one_candidate(
        focal_user=anchor.focal_user,
        candidate_key=candidate_key,
    )
    state, mask, state_schema, state_schema_sha, state_obs_sha = phase_b._state_and_mask(
        modules=modules,
        wrapped=prepared.anchor.wrapped,
        observation=prepared.anchor.observation,
        focal_user=anchor.focal_user,
    )
    anchor_state = phase_b._anchor_state_record(
        state=state,
        mask=mask,
        state_schema=state_schema,
        state_schema_sha256=state_schema_sha,
        state_observation_sha256=state_obs_sha,
    )
    multiplier, interval, _calibration_sha = support._production_calibration(modules)
    row = mechanics._materialize_controlled_pair(
        prepared=prepared,
        source_seed=int(anchor.source_seed),
        hybrid=hybrid,
        modules=modules,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        anchor_schedule_sha256=anchor.anchor_schedule_sha256,
        source_manifest_sha256=context["source_manifest_sha256"],
        reference_policy_sha256=reference_policy_sha256,
        reference_policy_components=reference_policy_components,
        tape_policy=tape_policy,
    )
    result = dict(row)
    result["schema"] = ROW_SCHEMA
    result["anchor_step"] = int(anchor.anchor_step)
    result["anchor_state"] = anchor_state
    result["learner_pair"] = _learner_pair(row=result, anchor_state=anchor_state)
    return result


def _shard(args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    prepare, schedule, prepare_file_sha = _read_prepare(Path(args.prepare_file))
    if type(args.anchor_index) is not int or not 0 <= args.anchor_index < EXPECTED_ANCHORS:
        raise ControlledSourceError("anchor_index lies outside 0..11")
    if args.tape_policy not in POLICY_VIEWS:
        raise ControlledSourceError("unknown controlled tape policy")
    if args.tape_policy == "main" and args.initialization_seed is not None:
        raise ControlledSourceError("Main shard forbids an initialization seed")
    if args.tape_policy == "q13" and args.initialization_seed not in Q13_SEEDS:
        raise ControlledSourceError("Q13 shard requires one frozen initialization seed")
    _phase_a, modules = _authenticate_common(args)
    q13_gate = None
    if args.tape_policy == "q13":
        q13_gate = phase_b._authenticate_q13_gate(
            Path(args.gate_dir),
            source_dir=Path(args.c3_source_dir),
            prereg_path=Path(args.prereg),
            v03_root=Path(args.v03_root),
        )
    anchor = schedule.anchors[args.anchor_index]
    with tempfile.TemporaryDirectory(prefix="mcrl-v05-c2-controlled-shard-tle-") as temporary:
        context = support._production_main_context(
            modules=modules,
            prereg_path=Path(args.prereg),
            tle_root=Path(args.tle_root),
            temporary=Path(temporary),
        )
        hybrid = None
        before = None
        if args.tape_policy == "q13":
            assert q13_gate is not None
            hybrid = phase_b._screen_module().load_gate_selected_hybrid(
                q13_gate,
                v03_root=Path(args.v03_root),
                initialization_seed=int(args.initialization_seed),
            )
            for network in hybrid.q_nets:
                network.eval()
            before = phase_b._snapshot_hybrid(hybrid)
        components = mechanics._reference_policy_components(
            tape_policy=args.tape_policy,
            main_policy_sha256=context["policy_sha256"],
            hybrid=hybrid,
            initialization_seed=args.initialization_seed,
        )
        components = _validate_policy_components(
            components,
            tape_policy=args.tape_policy,
            initialization_seed=args.initialization_seed,
            reference_policy_sha256=str(components["policy_components_sha256"]),
            main_policy_sha256=anchor.policy_sha256
            if args.tape_policy == "main"
            else None,
        )
        policy_sha = str(components["policy_components_sha256"])
        rows = [
            _materialize_source_row(
                anchor=anchor,
                candidate_key=tuple(int(value) for value in candidate_key),
                hybrid=hybrid,
                modules=modules,
                context=context,
                reference_policy_sha256=policy_sha,
                reference_policy_components=components,
                tape_policy=args.tape_policy,
            )
            for candidate_key in anchor.candidate_physical_keys
        ]
        for row, candidate_key in zip(rows, anchor.candidate_physical_keys, strict=True):
            _validate_source_row(
                row=row,
                anchor=anchor,
                candidate_key=tuple(candidate_key),
                tape_policy=args.tape_policy,
                initialization_seed=args.initialization_seed,
                expected_policy_components=components,
            )
        state_digests = {
            row["anchor_state"]["anchor_state_sha256"]
            for row in rows
            if isinstance(row, Mapping) and isinstance(row.get("anchor_state"), Mapping)
        }
        if len(state_digests) != 1:
            raise ControlledSourceError("controlled shard anchor state changed across siblings")
        if hybrid is not None:
            assert before is not None
            phase_b._assert_hybrid_unchanged(hybrid, before)
            if mechanics._reference_policy_components(
                tape_policy="q13",
                main_policy_sha256=context["policy_sha256"],
                hybrid=hybrid,
                initialization_seed=args.initialization_seed,
            ) != components:
                raise ControlledSourceError("Q1/Q3 parameters changed during shard replay")
    candidate_keys = [tuple(row["candidate_physical_key"]) for row in rows]
    if (
        len(rows) != SIBLINGS_PER_ANCHOR
        or candidate_keys != list(anchor.candidate_physical_keys)
        or len(set(candidate_keys)) != SIBLINGS_PER_ANCHOR
        or len({str(row["tape"]["tape_sha256"]) for row in rows}) != 1
    ):
        raise ControlledSourceError("controlled shard is not a complete common-tape sibling view")
    body: dict[str, object] = {
        "schema": SHARD_SCHEMA,
        "status": "CONTROLLED_SOURCE_SHARD_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "prepare_file_sha256": prepare_file_sha,
        "prepare_sha256": prepare["prepare_sha256"],
        "schedule_sha256": prepare["schedule"]["schedule_sha256"],
        "anchor_index": int(args.anchor_index),
        "anchor_sha256": anchor.anchor_sha256,
        "anchor_step": int(anchor.anchor_step),
        "tape_policy": args.tape_policy,
        "initialization_seed": args.initialization_seed,
        "reference_policy_components": components,
        "policy_parameters_unchanged": True,
        "row_count": len(rows),
        "rows": rows,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "elapsed_s": float(time.monotonic() - started),
    }
    body["shard_sha256"] = _canonical_sha256(body)
    file_sha = _write_once(Path(args.output_file), body)
    return {"status": body["status"], "row_count": len(rows), "output_file_sha256": file_sha}


def _shard_name(policy: str, seed: int | None, anchor_index: int) -> str:
    prefix = "main" if policy == "main" else f"q13-{seed}"
    return f"{prefix}-anchor-{anchor_index:02d}.json"


def _merge(args: argparse.Namespace) -> dict[str, object]:
    prepare, schedule, prepare_file_sha = _read_prepare(Path(args.prepare_file))
    shard_dir = Path(args.shard_dir)
    receipts: list[dict[str, object]] = []
    sign_counts: Counter[str] = Counter()
    view_policy_components: dict[tuple[str, int | None], dict[str, object]] = {}
    anchor_state_by_index: dict[int, str] = {}
    total_rows = 0
    for policy, seed in (("main", None), *(("q13", value) for value in Q13_SEEDS)):
        for anchor_index, anchor in enumerate(schedule.anchors):
            path = shard_dir / _shard_name(policy, seed, anchor_index)
            result, file_sha = _read_json(path)
            body = dict(result)
            claimed = body.pop("shard_sha256", None)
            expected_shard_fields = {
                "schema",
                "status",
                "claim_ceiling",
                "prepare_file_sha256",
                "prepare_sha256",
                "schedule_sha256",
                "anchor_index",
                "anchor_sha256",
                "anchor_step",
                "tape_policy",
                "initialization_seed",
                "reference_policy_components",
                "policy_parameters_unchanged",
                "row_count",
                "rows",
                "training_run",
                "test_split_opened",
                "held_out_ee_evaluated",
                "elapsed_s",
                "shard_sha256",
            }
            if (
                set(result) != expected_shard_fields
                or result.get("schema") != SHARD_SCHEMA
                or result.get("status") != "CONTROLLED_SOURCE_SHARD_COMPLETE"
                or result.get("claim_ceiling") != CLAIM_CEILING
                or claimed != _canonical_sha256(body)
                or result.get("prepare_file_sha256") != prepare_file_sha
                or result.get("prepare_sha256") != prepare["prepare_sha256"]
                or result.get("schedule_sha256") != prepare["schedule"]["schedule_sha256"]
                or result.get("anchor_index") != anchor_index
                or result.get("anchor_sha256") != anchor.anchor_sha256
                or result.get("anchor_step") != anchor.anchor_step
                or result.get("tape_policy") != policy
                or result.get("initialization_seed") != seed
                or result.get("row_count") != SIBLINGS_PER_ANCHOR
                or result.get("policy_parameters_unchanged") is not True
                or result.get("training_run") is not False
                or result.get("test_split_opened") is not False
                or result.get("held_out_ee_evaluated") is not False
            ):
                raise ControlledSourceError(f"controlled shard failed authentication: {path}")
            elapsed = result["elapsed_s"]
            if type(elapsed) not in (int, float) or not math.isfinite(float(elapsed)) or float(elapsed) < 0.0:
                raise ControlledSourceError(f"controlled shard elapsed_s is invalid: {path}")
            rows = result.get("rows")
            if not isinstance(rows, list) or len(rows) != SIBLINGS_PER_ANCHOR:
                raise ControlledSourceError(f"controlled shard rows are malformed: {path}")
            components = _validate_policy_components(
                result.get("reference_policy_components"),
                tape_policy=policy,
                initialization_seed=seed,
                reference_policy_sha256=str(
                    result["reference_policy_components"].get("policy_components_sha256")
                    if isinstance(result.get("reference_policy_components"), Mapping)
                    else ""
                ),
                main_policy_sha256=anchor.policy_sha256 if policy == "main" else None,
            )
            view_key = (policy, seed)
            previous_components = view_policy_components.get(view_key)
            if previous_components is not None and previous_components != components:
                raise ControlledSourceError(
                    f"controlled {policy} policy receipt drifted across shards"
                )
            view_policy_components[view_key] = components
            for row, candidate_key in zip(rows, anchor.candidate_physical_keys, strict=True):
                _validate_source_row(
                    row=row,
                    anchor=anchor,
                    candidate_key=tuple(candidate_key),
                    tape_policy=policy,
                    initialization_seed=seed,
                    expected_policy_components=components,
                )
            candidates = [
                _physical_key(row["candidate_physical_key"], field="row.candidate_physical_key")
                for row in rows
            ]
            if candidates != list(anchor.candidate_physical_keys):
                raise ControlledSourceError(f"controlled shard candidate census drifted: {path}")
            shard_state = next(
                row["anchor_state"]["anchor_state_sha256"]
                for row in rows
                if isinstance(row, Mapping) and isinstance(row.get("anchor_state"), Mapping)
            )
            previous_state = anchor_state_by_index.get(anchor_index)
            if previous_state is not None and previous_state != shard_state:
                raise ControlledSourceError(
                    f"controlled anchor state drifted across policy views: {anchor_index}"
                )
            anchor_state_by_index[anchor_index] = shard_state
            for row in rows:
                target = row.get("target")
                if not isinstance(target, Mapping):
                    raise ControlledSourceError("controlled row target is missing")
                value = float.fromhex(str(target["zeta2_temporal_surplus_bits"]))
                if not math.isfinite(value):
                    raise ControlledSourceError("controlled row target is nonfinite")
                sign_counts["positive" if value > 0 else "negative" if value < 0 else "zero"] += 1
            total_rows += len(rows)
            receipts.append(
                {
                    "file": path.name,
                    "file_sha256": file_sha,
                    "shard_sha256": claimed,
                    "policy": policy,
                    "initialization_seed": seed,
                    "anchor_index": anchor_index,
                    "row_count": len(rows),
                }
            )
    if len(receipts) != 48 or total_rows != EXPECTED_TOTAL_ROWS:
        raise ControlledSourceError("merged controlled source cardinality drifted")
    body: dict[str, object] = {
        "schema": MERGE_SCHEMA,
        "status": "CONTROLLED_SOURCE_MERGE_COMPLETE",
        "decision": "AUTHORIZE_THREE_BOUNDED_C2_LEARNER_ARMS",
        "claim_ceiling": CLAIM_CEILING,
        "prepare_file_sha256": prepare_file_sha,
        "prepare_sha256": prepare["prepare_sha256"],
        "schedule_sha256": prepare["schedule"]["schedule_sha256"],
        "shard_count": len(receipts),
        "row_count": total_rows,
        "rows_per_policy_view": EXPECTED_ROWS_PER_VIEW,
        "target_sign_counts": dict(sorted(sign_counts.items())),
        "shards": receipts,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    body["merge_sha256"] = _canonical_sha256(body)
    file_sha = _write_once(Path(args.output_file), body)
    return {"status": body["status"], "row_count": total_rows, "output_file_sha256": file_sha}


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "shard", "merge"))
    parser.add_argument("--phase-a-dir", default=str(mechanics.DEFAULT_PHASE_A_DIR))
    parser.add_argument("--gate-dir", default=str(mechanics.DEFAULT_GATE_DIR))
    parser.add_argument("--c3-source-dir", default=str(mechanics.DEFAULT_C3_SOURCE_DIR))
    parser.add_argument("--v03-root", default=str(mechanics.DEFAULT_V03_ROOT))
    parser.add_argument("--prereg", default=str(mechanics.DEFAULT_PREREG))
    parser.add_argument("--tle-root", default=str(mechanics.DEFAULT_TLE_ROOT))
    parser.add_argument("--prepare-file")
    parser.add_argument("--shard-dir")
    parser.add_argument("--anchor-index", type=int)
    parser.add_argument("--tape-policy", choices=POLICY_VIEWS)
    parser.add_argument("--initialization-seed", type=int, choices=Q13_SEEDS)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = _prepare(args)
    elif args.command == "shard":
        if args.prepare_file is None or args.anchor_index is None or args.tape_policy is None:
            parser.error("shard requires --prepare-file, --anchor-index, and --tape-policy")
        result = _shard(args)
    else:
        if args.prepare_file is None or args.shard_dir is None:
            parser.error("merge requires --prepare-file and --shard-dir")
        result = _merge(args)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
