#!/usr/bin/env python3
"""Independent fail-closed verifier for the V0.5 C2 mechanics screen.

The V0.5 producer intentionally has a small interface, but a producer-side
``verify()`` call is not enough evidence for a batch receipt: it can only tell
us that one in-memory object is self-consistent.  This verifier reads the
persisted JSON and reconstructs the lineage, tape, pair-plan, and target
digests independently.  It therefore catches a self-consistent but tampered
receipt, a mixed anchor batch, and a target that was not regenerated from the
raw trace.

The verifier is deliberately outcome-blind.  A passing result means exactly
that the 48 physical rows satisfy the controlled-tape mechanics contract.  It
does not inspect target signs, train a Q network, open TEST, or make an EE
efficacy claim.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


# These are frozen V0.5/V0.4 wire constants, repeated here on purpose.  The
# verifier must not call producer-side ``verify`` methods as its authority.
NUM_ACTIONS = 28
USER_COUNT = 100
OFFSETS = (0, 1, 2, 3)
DOWNSTREAM_OFFSETS = (1, 2, 3)
Q13_SEEDS = (2026092101, 2026092102, 2026092103)
EXPECTED_LAMBDA_HEX = "0x1.443a8f481639ap+26"
EXPECTED_INTERVAL_HEX = "0x1.e147ae147ae15p+4"
EXPECTED_SOURCE_RULE = "c2-support-complete-legal-nonmain-v1"
EXPECTED_CLAIM_CEILING = (
    "V05_CONTROLLED_TAPE_MECHANICS_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
)
SCHEDULE_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-sibling-schedule-v1"
ANCHOR_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-anchor-schedule-v1"
SIBLING_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-sibling-row-v1"
TAPE_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-tape-v1"
PLAN_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-tape-plan-v1"
TARGET_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-tape-target-v1"
FADING_MODE = "keyed-branch-independent-v1"
OUTPUT_SCHEMA_V1 = "multi-catfish-mcrl-v05-c2-controlled-tape-lockstep-12-v1"
OUTPUT_SCHEMA_V2 = "multi-catfish-mcrl-v05-c2-controlled-tape-lockstep-12-v2"
OUTPUT_STATUS = "V05_CONTROLLED_TAPE_LOCKSTEP_12_COMPLETE"
ROW_SCHEMA_V1 = "multi-catfish-mcrl-v05-c2-controlled-tape-physical-row-v1"
ROW_SCHEMA_V2 = "multi-catfish-mcrl-v05-c2-controlled-tape-physical-row-v2"
Q13_POLICY_COMPONENT_SCHEMA = "multi-catfish-mcrl-v05-q13-policy-components-v1"
MAIN_POLICY_COMPONENT_SCHEMA = "multi-catfish-mcrl-v05-main-policy-components-v1"
RELEASE_REASONS = {"horizon", "support_expired"}
FOCAL_MODES = {"hold", "released"}


class MechanicsVerificationError(ValueError):
    """A persisted V0.5 mechanics receipt failed a hard gate."""


def _fail(message: str) -> None:
    raise MechanicsVerificationError(message)


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise MechanicsVerificationError("payload is not finite canonical JSON") from error


def _canonical_sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    _fail(f"JSON constant {value!r} is not finite")
    return None


def _read_json(path: Path, *, canonical: bool = True) -> tuple[dict[str, object], str]:
    if path.is_symlink() or not path.is_file():
        _fail(f"JSON input is missing or non-regular: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except MechanicsVerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise MechanicsVerificationError(f"invalid JSON input: {path}") from error
    if not isinstance(payload, dict):
        _fail(f"JSON root must be an object: {path}")
    if canonical and raw != _canonical_bytes(payload) + b"\n":
        _fail(f"JSON input is not the canonical write-once encoding: {path}")
    return payload, hashlib.sha256(raw).hexdigest()


def _keys(value: object, expected: set[str], *, field: str, optional: set[str] | None = None) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(f"{field} must be a JSON object")
    actual = set(value)
    allowed = expected | (optional or set())
    missing = sorted(expected - actual)
    extra = sorted(actual - allowed)
    if missing:
        _fail(f"{field} missing required field(s): {', '.join(missing)}")
    if extra:
        _fail(f"{field} contains unsupported field(s): {', '.join(extra)}")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{field} must be a lowercase SHA-256 digest")
    return value


def _network_parameter_sha256_from_state(value: object, *, field: str) -> str:
    """Recompute the runner's parameter-only digest from a safe state map.

    V0.5 Q13 policy identity intentionally excludes Q2.  The checkpoint is
    loaded with ``weights_only=True`` by the caller; this helper only consumes
    tensor state and repeats the byte-level digest recipe independently.
    """

    if not isinstance(value, Mapping) or not value:
        _fail(f"{field} must be a non-empty parameter mapping")
    digest = hashlib.sha256()
    for name in sorted(value):
        tensor = value[name]
        detach = getattr(tensor, "detach", None)
        if not callable(detach):
            _fail(f"{field}.{name} is not a tensor")
        try:
            array = tensor.detach().cpu().contiguous().numpy()
            metadata = json.dumps(
                {
                    "name": str(name),
                    "dtype": array.dtype.str,
                    "shape": list(array.shape),
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("ascii")
            raw = array.tobytes(order="C")
        except (AttributeError, TypeError, ValueError, UnicodeEncodeError) as error:
            raise MechanicsVerificationError(f"{field}.{name} tensor payload is invalid") from error
        digest.update(len(metadata).to_bytes(8, "big"))
        digest.update(metadata)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def _hybrid_parameter_digests(path: Path, *, seed: int) -> tuple[str, str]:
    """Read only the Q-network state maps from one selected hybrid."""

    if path.is_symlink() or not path.is_file():
        _fail(f"Q13 hybrid {seed} file is missing or non-regular")
    try:
        import torch

        payload = torch.load(path, map_location="cpu", weights_only=True)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as error:
        raise MechanicsVerificationError(f"Q13 hybrid {seed} cannot be safely loaded") from error
    if not isinstance(payload, Mapping) or not isinstance(payload.get("hybrid"), Mapping):
        _fail(f"Q13 hybrid {seed} has no sealed hybrid mapping")
    hybrid = payload["hybrid"]
    q_networks = hybrid.get("q_networks")
    if not isinstance(q_networks, list) or len(q_networks) != 3:
        _fail(f"Q13 hybrid {seed} does not contain exactly three Q-network states")
    if payload.get("initialization_seed") != seed or hybrid.get("initialization_seed") != seed:
        _fail(f"Q13 hybrid {seed} initialization seed lineage drifted")
    if payload.get("selected_q3_rung") != 100 or hybrid.get("selected_q3_rung") != 100:
        _fail(f"Q13 hybrid {seed} selected rung is not 100")
    return (
        _network_parameter_sha256_from_state(q_networks[0], field=f"Q13 hybrid {seed}.q1"),
        _network_parameter_sha256_from_state(q_networks[2], field=f"Q13 hybrid {seed}.q3"),
    )


def _verify_reference_policy_components(
    value: object,
    *,
    policy: str,
    init_seed: int | None,
    reference_policy_sha: str,
    main_policy_sha: str,
    hybrid_path: Path | None,
    field: str,
) -> dict[str, object]:
    """Validate and independently recompute the V0.5 policy-component digest."""

    if policy == "main":
        expected = {"schema", "policy_kind", "main_policy_sha256", "policy_components_sha256"}
    elif policy == "q13":
        expected = {
            "schema", "policy_kind", "initialization_seed", "q1_parameters_sha256",
            "q3_parameters_sha256", "q2_excluded_from_policy", "policy_components_sha256",
        }
    else:
        _fail(f"{field} has an unknown policy")
    components = _keys(value, expected, field=field)
    claimed = _digest(components["policy_components_sha256"], field=f"{field}.policy_components_sha256")
    payload = {key: components[key] for key in expected if key != "policy_components_sha256"}
    if _canonical_sha(payload) != claimed or claimed != reference_policy_sha:
        _fail(f"{field} digest disagrees with its canonical payload or row policy digest")
    if policy == "main":
        if components["schema"] != MAIN_POLICY_COMPONENT_SCHEMA or components["policy_kind"] != "main":
            _fail(f"{field} Main policy-component schema/kind is stale")
        if components["main_policy_sha256"] != main_policy_sha:
            _fail(f"{field} Main policy component is not bound to the sealed policy")
    else:
        if components["schema"] != Q13_POLICY_COMPONENT_SCHEMA or components["policy_kind"] != "q1-plus-q3":
            _fail(f"{field} Q1+Q3 policy-component schema/kind is stale")
        if components["initialization_seed"] != init_seed:
            _fail(f"{field} Q1+Q3 initialization seed drifted")
        if components["q2_excluded_from_policy"] is not True:
            _fail(f"{field} does not explicitly exclude Q2 from the policy")
        q1_claim = _digest(components["q1_parameters_sha256"], field=f"{field}.q1_parameters_sha256")
        q3_claim = _digest(components["q3_parameters_sha256"], field=f"{field}.q3_parameters_sha256")
        if hybrid_path is not None:
            q1_actual, q3_actual = _hybrid_parameter_digests(hybrid_path, seed=int(init_seed))
            if (q1_claim, q3_claim) != (q1_actual, q3_actual):
                _fail(f"{field} Q1/Q3 parameter digest disagrees with selected hybrid")
    return dict(components)


def _int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{field} must be an exact integer >= {minimum}")
    return value


def _number(value: object, *, field: str, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        _fail(f"{field} must be {'positive ' if positive else ''}finite")
    return result


def _physical(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        _fail(f"{field} must be a two-integer physical key")
    return (_int(value[0], field=f"{field}[0]"), _int(value[1], field=f"{field}[1]"))


def _physical_or_none(value: object, *, field: str) -> tuple[int, int] | None:
    return None if value is None else _physical(value, field=field)


def _action(value: object, *, field: str, allow_noop: bool = True) -> int:
    if type(value) is not int or value < (-1 if allow_noop else 0) or value >= NUM_ACTIONS:
        low = -1 if allow_noop else 0
        _fail(f"{field} must be an action in [{low},{NUM_ACTIONS})")
    return value


def _actions(value: object, *, field: str, width: int = USER_COUNT) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != width:
        _fail(f"{field} must contain exactly {width} actions")
    return tuple(_action(item, field=f"{field}[{index}]") for index, item in enumerate(value))


def _physical_vector(value: object, *, field: str, width: int = USER_COUNT) -> tuple[tuple[int, int] | None, ...]:
    if not isinstance(value, list) or len(value) != width:
        _fail(f"{field} must contain exactly {width} physical actions")
    return tuple(_physical_or_none(item, field=f"{field}[{index}]") for index, item in enumerate(value))


def _bool_vector(value: object, *, field: str, width: int = USER_COUNT) -> tuple[bool, ...]:
    if not isinstance(value, list) or len(value) != width or any(type(item) is not bool for item in value):
        _fail(f"{field} must contain exactly {width} Boolean values")
    return tuple(value)


def _vec4(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list) or len(value) != len(OFFSETS):
        _fail(f"{field} must contain four offsets")
    return value


def _scan_forbidden(value: object, *, field: str = "root") -> None:
    """Reject any explicit fallback/drop/replacement/repair claim or marker."""

    forbidden = ("fallback", "drop", "replacement", "repair")
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = str(key).casefold()
            if any(term in token for term in forbidden):
                _fail(f"{field} contains forbidden mechanics field {key!r}")
            _scan_forbidden(child, field=f"{field}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden(child, field=f"{field}[{index}]")
    elif isinstance(value, str):
        token = value.casefold()
        if any(term in token for term in forbidden):
            _fail(f"{field} contains forbidden mechanics marker {value!r}")


def _anchor_payload(anchor: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": ANCHOR_SCHEMA,
        "source_rule": anchor["source_rule"],
        "source_seed": anchor["source_seed"],
        "anchor_step": anchor["anchor_step"],
        "world_anchor_sha256": anchor["world_anchor_sha256"],
        "anchor_sha256": anchor["anchor_sha256"],
        "focal_user": anchor["focal_user"],
        "reference_action": anchor["reference_action"],
        "reference_physical_key": anchor["reference_physical_key"],
        "incumbent_physical_key": anchor["incumbent_physical_key"],
        "common_random_field_sha256": anchor["common_random_field_sha256"],
        "predecision_heuristic_scores": anchor["predecision_heuristic_scores"],
        "legal_action_mask": anchor["legal_action_mask"],
        "candidate_actions": anchor["candidate_actions"],
        "candidate_physical_keys": anchor["candidate_physical_keys"],
        "checkpoint_sha256": anchor["checkpoint_sha256"],
        "source_manifest_sha256": anchor["source_manifest_sha256"],
        "policy_sha256": anchor["policy_sha256"],
        "evaluation_seed": anchor["evaluation_seed"],
    }


def _verify_anchor(anchor: object, *, index: int) -> Mapping[str, object]:
    expected = {
        "schema", "source_rule", "source_seed", "anchor_step", "world_anchor_sha256",
        "anchor_sha256", "focal_user", "reference_action", "reference_physical_key",
        "incumbent_physical_key", "common_random_field_sha256", "predecision_heuristic_scores",
        "legal_action_mask", "candidate_actions", "candidate_physical_keys", "checkpoint_sha256",
        "source_manifest_sha256", "policy_sha256", "evaluation_seed", "anchor_schedule_sha256",
    }
    value = _keys(anchor, expected, field=f"schedule.anchors[{index}]")
    if value["schema"] != ANCHOR_SCHEMA or value["source_rule"] != EXPECTED_SOURCE_RULE:
        _fail(f"schedule.anchors[{index}] has stale schema/source rule")
    source_seed = _int(value["source_seed"], field=f"anchor[{index}].source_seed")
    anchor_step = _int(value["anchor_step"], field=f"anchor[{index}].anchor_step", minimum=1)
    focal = _int(value["focal_user"], field=f"anchor[{index}].focal_user")
    if focal >= USER_COUNT:
        _fail(f"anchor[{index}].focal_user lies outside the 100-user trace")
    for name in ("world_anchor_sha256", "anchor_sha256", "common_random_field_sha256", "checkpoint_sha256", "source_manifest_sha256", "policy_sha256", "anchor_schedule_sha256"):
        _digest(value[name], field=f"anchor[{index}].{name}")
    reference_action = _action(value["reference_action"], field=f"anchor[{index}].reference_action", allow_noop=False)
    reference_key = _physical(value["reference_physical_key"], field=f"anchor[{index}].reference_physical_key")
    _physical(value["incumbent_physical_key"], field=f"anchor[{index}].incumbent_physical_key")
    evaluation_seed = _int(value["evaluation_seed"], field=f"anchor[{index}].evaluation_seed")
    if evaluation_seed != source_seed:
        _fail(f"anchor[{index}] source/evaluation seed lineage differs")
    scores = value["predecision_heuristic_scores"]
    if not isinstance(scores, list) or len(scores) != NUM_ACTIONS - 1:
        _fail(f"anchor[{index}] heuristic vector is not a 27-action vector")
    for j, item in enumerate(scores):
        _number(item, field=f"anchor[{index}].predecision_heuristic_scores[{j}]")
    mask = value["legal_action_mask"]
    if not isinstance(mask, list) or len(mask) != NUM_ACTIONS or any(type(item) is not bool for item in mask):
        _fail(f"anchor[{index}] legal action mask is not a 28-action Boolean vector")
    if not mask[reference_action]:
        _fail(f"anchor[{index}] Main reference action is not legal")
    actions_raw = value["candidate_actions"]
    keys_raw = value["candidate_physical_keys"]
    if not isinstance(actions_raw, list) or not isinstance(keys_raw, list) or len(actions_raw) != NUM_ACTIONS - 1 or len(keys_raw) != NUM_ACTIONS - 1:
        _fail(f"anchor[{index}] does not contain 27 legal non-Main siblings")
    actions = tuple(_action(item, field=f"anchor[{index}].candidate_actions[{j}]", allow_noop=False) for j, item in enumerate(actions_raw))
    keys = tuple(_physical(item, field=f"anchor[{index}].candidate_physical_keys[{j}]") for j, item in enumerate(keys_raw))
    if len(set(actions)) != len(actions) or len(set(keys)) != len(keys):
        _fail(f"anchor[{index}] candidate actions/keys are not unique")
    if reference_action in actions or reference_key in keys:
        _fail(f"anchor[{index}] candidate census contains the Main reference")
    expected_actions = {j for j, legal in enumerate(mask) if legal and j != reference_action}
    if set(actions) != expected_actions:
        _fail(f"anchor[{index}] candidate actions do not equal the legal non-Main set")
    if tuple(zip(keys, actions)) != tuple(sorted(zip(keys, actions))):
        _fail(f"anchor[{index}] candidate census is not canonically sorted")
    if _canonical_sha(_anchor_payload(value)) != value["anchor_schedule_sha256"]:
        _fail(f"anchor[{index}] anchor_schedule_sha256 is invalid")
    # The schedule's anchor_sha256 is an upstream physical identity.  It is
    # not recomputed here because the upstream producer deliberately includes
    # simulator-originated fields not present in this V0.5 output.
    return value


def _anchor_intervention_key(anchor: Mapping[str, object]) -> tuple[int, str, str, int]:
    return (int(anchor["source_seed"]), str(anchor["world_anchor_sha256"]), str(anchor["anchor_sha256"]), int(anchor["focal_user"]))


def _verify_schedule(path: Path) -> tuple[dict[str, Mapping[str, object]], str]:
    schedule, _file_sha = _read_json(path)
    _keys(schedule, {"anchors", "rows", "schedule_sha256", "schema", "version"}, field="schedule")
    if schedule["schema"] != SCHEDULE_SCHEMA or schedule["version"] != 1:
        _fail("schedule schema/version is stale")
    schedule_sha = _digest(schedule["schedule_sha256"], field="schedule.schedule_sha256")
    anchors_raw = schedule["anchors"]
    rows_raw = schedule["rows"]
    if not isinstance(anchors_raw, list) or len(anchors_raw) != 12:
        _fail("schedule must contain exactly 12 anchors")
    if not isinstance(rows_raw, list) or len(rows_raw) != 324:
        _fail("schedule must contain exactly 324 sibling rows")
    anchors = [_verify_anchor(anchor, index=index) for index, anchor in enumerate(anchors_raw)]
    anchor_keys = [_anchor_intervention_key(anchor) for anchor in anchors]
    if len(set(anchor_keys)) != len(anchor_keys):
        _fail("schedule contains duplicate intervention anchors")
    if anchor_keys != sorted(anchor_keys):
        _fail("schedule anchors are not in canonical intervention order")
    by_anchor = {str(anchor["anchor_sha256"]): anchor for anchor in anchors}
    if len(by_anchor) != len(anchors):
        _fail("schedule anchor_sha256 identities are not unique")
    grouped: dict[tuple[int, str, str, int], set[tuple[int, tuple[int, int]]]] = {key: set() for key in anchor_keys}
    seen_rows: set[tuple[int, str, str, int, tuple[int, int]]] = set()
    row_expected = {
        "schema", "source_rule", "source_seed", "anchor_step", "world_anchor_sha256", "anchor_sha256",
        "focal_user", "anchor_schedule_sha256", "reference_action", "reference_physical_key",
        "incumbent_physical_key", "common_random_field_sha256", "predecision_heuristic_scores",
        "legal_action_mask", "candidate_actions", "candidate_physical_keys", "candidate_action",
        "candidate_physical_key", "checkpoint_sha256", "source_manifest_sha256", "policy_sha256",
        "evaluation_seed", "row_status", "failure_code",
    }
    for index, raw_row in enumerate(rows_raw):
        row = _keys(raw_row, row_expected, field=f"schedule.rows[{index}]")
        if row["schema"] != SIBLING_SCHEMA or row["source_rule"] != EXPECTED_SOURCE_RULE:
            _fail(f"schedule.rows[{index}] has stale schema/source rule")
        anchor = by_anchor.get(str(row["anchor_sha256"]))
        if anchor is None:
            _fail(f"schedule.rows[{index}] has an unscheduled anchor")
        shared_names = (
            "source_seed", "anchor_step", "world_anchor_sha256", "anchor_sha256", "focal_user",
            "anchor_schedule_sha256", "reference_action", "reference_physical_key", "incumbent_physical_key",
            "common_random_field_sha256", "predecision_heuristic_scores", "legal_action_mask", "candidate_actions",
            "candidate_physical_keys", "checkpoint_sha256", "source_manifest_sha256", "policy_sha256", "evaluation_seed",
        )
        for name in shared_names:
            if row[name] != anchor[name]:
                _fail(f"schedule.rows[{index}] shared field {name} disagrees with anchor")
        candidate_action = _action(row["candidate_action"], field=f"schedule.rows[{index}].candidate_action", allow_noop=False)
        candidate_key = _physical(row["candidate_physical_key"], field=f"schedule.rows[{index}].candidate_physical_key")
        pairs = {(int(a), _physical(k, field=f"schedule.rows[{index}].candidate_physical_keys")) for a, k in zip(anchor["candidate_actions"], anchor["candidate_physical_keys"], strict=True)}
        if (candidate_action, candidate_key) not in pairs:
            _fail(f"schedule.rows[{index}] is not a member of the complete sibling census")
        status = row["row_status"]
        if status not in {"ready", "row-failure", "support-expired"}:
            _fail(f"schedule.rows[{index}] has an invalid row_status")
        if status == "ready" and row["failure_code"] is not None:
            _fail(f"schedule.rows[{index}] ready row carries failure_code")
        if status != "ready" and (not isinstance(row["failure_code"], str) or not row["failure_code"].strip()):
            _fail(f"schedule.rows[{index}] non-ready row lacks failure_code")
        intervention = _anchor_intervention_key(anchor)
        identity = intervention + (candidate_key,)
        if identity in seen_rows:
            _fail(f"schedule.rows[{index}] duplicates a sibling identity")
        seen_rows.add(identity)
        grouped[intervention].add((candidate_action, candidate_key))
    for anchor in anchors:
        intervention = _anchor_intervention_key(anchor)
        expected_pairs = {(int(action), _physical(key, field="anchor.candidate_physical_keys")) for action, key in zip(anchor["candidate_actions"], anchor["candidate_physical_keys"], strict=True)}
        if grouped[intervention] != expected_pairs:
            _fail(f"schedule census is incomplete for anchor {anchor['anchor_sha256']}")
    body = {"schema": schedule["schema"], "version": schedule["version"], "anchors": schedule["anchors"], "rows": schedule["rows"]}
    if _canonical_sha(body) != schedule_sha:
        _fail("schedule_sha256 disagrees with canonical schedule contents")
    return by_anchor, schedule_sha


def _verify_prepare(path: Path, *, anchors: Mapping[str, Mapping[str, object]], schedule_sha: str) -> tuple[str, str]:
    prepare, _file_sha = _read_json(path)
    required = {"claim_ceiling", "policy_sha256", "schedule_sha256", "source_manifest_sha256", "source_rule", "status", "training_run", "test_opened", "held_out_ee_evaluated"}
    # The production receipt carries authenticated provenance fields in
    # addition to the small lineage subset consumed below.  Keep the allowlist
    # explicit so an accidental/new field still fails closed while accepting
    # the current V0.4 receipt shape.
    optional = {
        "checkpoint_sha256", "common_random_field_roots",
        "counterfactual_outcomes_evaluated", "environment_source_sha256",
        "prepare_file_sha256", "prepare_sha256", "prereg_file_sha256",
        "prereg_path", "prereg_sha256", "reward_source_sha256",
        "scanned_source_seeds", "schedule_file_sha256", "schema",
        "selected_source_seeds", "source_manifest_file_sha256", "tle_root",
    }
    _keys(prepare, required, field="prepare-receipt", optional=optional)
    if prepare.get("schema") != "multi-catfish-mcrl-v04-c2-support-complete-prepare-receipt-v1":
        _fail("prepare receipt schema is stale")
    if prepare["status"] != "PREPARED" or prepare["source_rule"] != EXPECTED_SOURCE_RULE:
        _fail("prepare receipt is not the sealed C2 source receipt")
    if prepare["claim_ceiling"] != "FRESH_TRAIN_DESIGN_PROBE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY":
        _fail("prepare receipt claim ceiling is too weak or stale")
    if prepare["schedule_sha256"] != schedule_sha:
        _fail("prepare receipt schedule lineage differs")
    for key in ("source_manifest_sha256", "policy_sha256"):
        _digest(prepare[key], field=f"prepare-receipt.{key}")
    for key in (
        "checkpoint_sha256", "environment_source_sha256", "reward_source_sha256",
        "prepare_file_sha256", "prepare_sha256", "prereg_file_sha256",
        "prereg_sha256", "schedule_file_sha256", "source_manifest_file_sha256",
    ):
        if key in prepare:
            _digest(prepare[key], field=f"prepare-receipt.{key}")
    if prepare.get("counterfactual_outcomes_evaluated") is not False:
        _fail("prepare receipt evaluated counterfactual outcomes")
    if prepare.get("scanned_source_seeds") != [2026092801, 2026092802, 2026092803] or prepare.get("selected_source_seeds") != [2026092801, 2026092802, 2026092803]:
        _fail("prepare receipt source-seed census is not the frozen three-world set")
    if prepare["training_run"] is not False or prepare["test_opened"] is not False or prepare["held_out_ee_evaluated"] is not False:
        _fail("prepare receipt opens training, TEST, or held-out EE")
    for anchor in anchors.values():
        if anchor["source_manifest_sha256"] != prepare["source_manifest_sha256"]:
            _fail("anchor source manifest differs from prepare receipt")
        if anchor["policy_sha256"] != prepare["policy_sha256"]:
            _fail("anchor Main policy differs from prepare receipt")
    return str(prepare["source_manifest_sha256"]), str(prepare["policy_sha256"])


def _verify_q13_gate(path: Path) -> tuple[dict[int, str], dict[int, Path]]:
    gate, _file_sha = _read_json(path)
    required = {"selected_hybrids", "selected_q3_rung", "claim_ceiling", "status"}
    optional = {
        "authority_file_sha256", "authority_seal_file_sha256", "authority_sha256",
        "collision_censuses", "decision", "elapsed_s", "episode_training",
        "held_out_ee_evaluated", "mean_model_to_strongest_null_ratio_by_rung",
        "metrics", "q3_pairwise_training_completed", "rung_checkpoints",
        "schema", "source_manifest_sha256", "source_verify", "test_split_opened",
        "train_surface_sha256", "training", "training_scope",
        "validation_dataset_bytes_opened", "validation_metrics_computed",
        "validation_surface_sha256", "schedule_sha256",
    }
    _keys(gate, required, field="Q13 gate result", optional=optional)
    if gate.get("schema") != "multi-catfish-mcrl-v04-c3-learnability-result-v1":
        _fail("Q13 gate result schema is stale")
    if gate["status"] != "GO_500EP_SCREEN_ONLY" or gate["selected_q3_rung"] != 100:
        _fail("Q13 gate is not the selected rung-100 authority")
    if gate["claim_ceiling"] != "V04_C3_LEARNABILITY_ONLY_AUTHORIZE_ONE_500EP_SCREEN_NO_TEST_NO_EE_CLAIM":
        _fail("Q13 gate claim ceiling is too weak or stale")
    selected = gate["selected_hybrids"]
    if not isinstance(selected, Mapping) or set(selected) != {str(seed) for seed in Q13_SEEDS}:
        _fail("Q13 gate does not contain exactly the three frozen initialization hybrids")
    result: dict[int, str] = {}
    hybrid_paths: dict[int, Path] = {}
    for seed in Q13_SEEDS:
        descriptor = selected[str(seed)]
        required_descriptor = {"exact_three_networks", "file_sha256", "frozen_q1_q2_bit_identical", "path", "q1_head_index", "q2_head_index", "q3_trainable_only", "strict_reload"}
        d = _keys(descriptor, required_descriptor, field=f"Q13 gate hybrid {seed}")
        if any(d[name] is not True for name in ("exact_three_networks", "frozen_q1_q2_bit_identical", "q3_trainable_only", "strict_reload")):
            _fail(f"Q13 hybrid {seed} does not carry the exact-three-network lineage")
        if d["q1_head_index"] != 0 or d["q2_head_index"] != 1:
            _fail(f"Q13 hybrid {seed} has a stale head mapping")
        expected = _digest(d["file_sha256"], field=f"Q13 gate hybrid {seed}.file_sha256")
        hybrid_path = Path(str(d["path"]))
        if not hybrid_path.is_absolute():
            hybrid_path = path.parent.parent.parent / hybrid_path
        if hybrid_path.is_symlink() or not hybrid_path.is_file():
            _fail(f"Q13 hybrid {seed} file is missing or non-regular")
        actual = hashlib.sha256(hybrid_path.read_bytes()).hexdigest()
        if actual != expected:
            _fail(f"Q13 hybrid {seed} file digest drifted")
        result[seed] = expected
        hybrid_paths[seed] = hybrid_path
    return result, hybrid_paths


def _trace_digest(trace: Mapping[str, object]) -> str:
    steps = []
    for index in range(len(OFFSETS)):
        steps.append({
            "offset": int(trace["offsets"][index]),
            "executed_actions": list(trace["executed_actions"][index]),
            "executed_physical_actions": [None if item is None else list(item) for item in trace["executed_physical_actions"][index]],
        })
    return _canonical_sha({"schema": "controlled-tape-reference-trace-v1", "steps": steps})


def _nonfocal_receipt(*, offset: int, focal: int, reference: Sequence[tuple[int, int] | None], candidate: Sequence[tuple[int, int] | None]) -> str:
    return _canonical_sha({
        "schema": "controlled-tape-nonfocal-equality-v1",
        "offset": offset,
        "focal_user": focal,
        "reference": [None if item is None else list(item) for index, item in enumerate(reference) if index != focal],
        "candidate": [None if item is None else list(item) for index, item in enumerate(candidate) if index != focal],
    })


def _tape_payload(tape: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": TAPE_SCHEMA,
        "anchor_sha256": tape["anchor_sha256"],
        "reference_trace_sha256": tape["reference_trace_sha256"],
        "reference_policy_sha256": tape["reference_policy_sha256"],
        "common_random_field_sha256": tape["common_random_field_sha256"],
        "fading_mode": tape["fading_mode"],
        "focal_user": tape["focal_user"],
        "steps": tape["steps"],
    }


def _plan_payload(plan: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": PLAN_SCHEMA,
        "tape_sha256": plan["tape_sha256"],
        "focal_user": plan["focal_user"],
        "held_physical_key": plan["held_physical_key"],
        "release_offset": plan["release_offset"],
        "release_reason": plan["release_reason"],
        "support_counts": plan["support_counts"],
        "steps": plan["steps"],
    }


def _float_hex(value: float) -> str:
    if not math.isfinite(float(value)):
        _fail("target contains a non-finite float")
    return float(value).hex()


def _hex_vector(value: object, *, field: str, length: int) -> list[float]:
    if not isinstance(value, list) or len(value) != length or any(not isinstance(item, str) for item in value):
        _fail(f"{field} must contain exactly {length} hexadecimal floats")
    parsed: list[float] = []
    for index, item in enumerate(value):
        try:
            result = float.fromhex(item)
        except (TypeError, ValueError) as error:
            raise MechanicsVerificationError(f"{field}[{index}] is not a hexadecimal float") from error
        if not math.isfinite(result):
            _fail(f"{field}[{index}] is not finite")
        parsed.append(result)
    return parsed


def _target_payload(target: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": TARGET_SCHEMA,
        "tape_sha256": target["tape_sha256"],
        "lambda_bits_per_j": target["lambda_bits_per_j"],
        "interval_s": target["interval_s"],
        "reference_rates_bps": target["reference_rates_bps"],
        "candidate_rates_bps": target["candidate_rates_bps"],
        "reference_system_power_w": target["reference_system_power_w"],
        "candidate_system_power_w": target["candidate_system_power_w"],
        "offset_rate_delta_bps": target["offset_rate_delta_bps"],
        "offset_system_energy_delta_j": target["offset_system_energy_delta_j"],
        "offset_surplus_bits": target["offset_surplus_bits"],
        "zeta2_temporal_surplus_bits": target["zeta2_temporal_surplus_bits"],
        "mean_offset_surplus_bits": target["mean_offset_surplus_bits"],
    }


def _verify_trace_branch(trace: object, *, field: str) -> dict[str, Any]:
    expected = {
        "active_physical_ids", "detached_main_actions", "detached_main_physical_actions", "done",
        "executed_actions", "executed_physical_actions", "held_key_match_count", "held_physical_key",
        "link_rate_bps", "mask_matrix_sha256", "offsets", "release_offset", "release_reason", "served",
        "state_matrix_sha256", "system_power_w",
    }
    value = _keys(trace, expected, field=field)
    offsets = value["offsets"]
    if offsets != list(OFFSETS):
        _fail(f"{field}.offsets must be exactly [0,1,2,3]")
    active_by_offset = _vec4(value["active_physical_ids"], field=f"{field}.active_physical_ids")
    detached_actions = _vec4(value["detached_main_actions"], field=f"{field}.detached_main_actions")
    detached_physical = _vec4(value["detached_main_physical_actions"], field=f"{field}.detached_main_physical_actions")
    executed_actions = _vec4(value["executed_actions"], field=f"{field}.executed_actions")
    executed_physical = _vec4(value["executed_physical_actions"], field=f"{field}.executed_physical_actions")
    served = _vec4(value["served"], field=f"{field}.served")
    rates = _vec4(value["link_rate_bps"], field=f"{field}.link_rate_bps")
    powers = value["system_power_w"]
    done = value["done"]
    state_digests = _vec4(value["state_matrix_sha256"], field=f"{field}.state_matrix_sha256")
    mask_digests = _vec4(value["mask_matrix_sha256"], field=f"{field}.mask_matrix_sha256")
    held = _vec4(value["held_physical_key"], field=f"{field}.held_physical_key")
    match_counts = _vec4(value["held_key_match_count"], field=f"{field}.held_key_match_count")
    releases = _vec4(value["release_offset"], field=f"{field}.release_offset")
    reasons = _vec4(value["release_reason"], field=f"{field}.release_reason")
    if not isinstance(powers, list) or len(powers) != 4 or not isinstance(done, list) or len(done) != 4 or any(type(item) is not bool for item in done):
        _fail(f"{field} power/done vectors are malformed")
    for index in range(4):
        active = [_physical(item, field=f"{field}.active_physical_ids[{index}]") for item in active_by_offset[index]]
        if len(set(active)) != len(active):
            _fail(f"{field}.active_physical_ids[{index}] contains duplicate physical keys")
        da = _actions(detached_actions[index], field=f"{field}.detached_main_actions[{index}]")
        dp = _physical_vector(detached_physical[index], field=f"{field}.detached_main_physical_actions[{index}]")
        ea = _actions(executed_actions[index], field=f"{field}.executed_actions[{index}]")
        ep = _physical_vector(executed_physical[index], field=f"{field}.executed_physical_actions[{index}]")
        _bool_vector(served[index], field=f"{field}.served[{index}]")
        rate_row = rates[index]
        if not isinstance(rate_row, list) or len(rate_row) != USER_COUNT:
            _fail(f"{field}.link_rate_bps[{index}] must contain 100 users")
        rate_values = tuple(_number(item, field=f"{field}.link_rate_bps[{index}][{j}]") for j, item in enumerate(rate_row))
        if any(item < 0.0 for item in rate_values):
            _fail(f"{field}.link_rate_bps[{index}] contains a negative rate")
        for label, actions, physical in (("detached", da, dp), ("executed", ea, ep)):
            for user, (action, key) in enumerate(zip(actions, physical, strict=True)):
                if (action == -1) != (key is None):
                    _fail(f"{field}.{label} action/physical binding disagrees at offset {index}, user {user}")
        _number(powers[index], field=f"{field}.system_power_w[{index}]", positive=True)
        for label, digests in (("state", state_digests), ("mask", mask_digests)):
            if not isinstance(digests[index], str):
                _fail(f"{field}.{label}_matrix_sha256[{index}] is not a digest")
            _digest(digests[index], field=f"{field}.{label}_matrix_sha256[{index}]")
        if held[index] is not None:
            _physical(held[index], field=f"{field}.held_physical_key[{index}]")
        if match_counts[index] is not None:
            _int(match_counts[index], field=f"{field}.held_key_match_count[{index}]")
        if releases[index] is not None:
            _int(releases[index], field=f"{field}.release_offset[{index}]")
            if releases[index] not in DOWNSTREAM_OFFSETS:
                _fail(f"{field}.release_offset[{index}] lies outside downstream offsets")
        if reasons[index] is not None and reasons[index] not in RELEASE_REASONS:
            _fail(f"{field}.release_reason[{index}] is invalid")
    return {
        "offsets": tuple(offsets),
        "active": tuple(tuple(_physical(item, field=f"{field}.active_physical_ids[{i}]") for item in active_by_offset[i]) for i in range(4)),
        "detached_actions": tuple(_actions(detached_actions[i], field=f"{field}.detached_main_actions[{i}]") for i in range(4)),
        "detached_physical": tuple(_physical_vector(detached_physical[i], field=f"{field}.detached_main_physical_actions[{i}]") for i in range(4)),
        "executed_actions": tuple(_actions(executed_actions[i], field=f"{field}.executed_actions[{i}]") for i in range(4)),
        "executed_physical": tuple(_physical_vector(executed_physical[i], field=f"{field}.executed_physical_actions[{i}]") for i in range(4)),
        "rates": np.asarray(rates, dtype=np.float64),
        "powers": np.asarray(powers, dtype=np.float64),
        "held": tuple(_physical_or_none(item, field=f"{field}.held_physical_key[{i}]") for i, item in enumerate(held)),
        "match_counts": tuple(None if item is None else _int(item, field=f"{field}.held_key_match_count[{i}]") for i, item in enumerate(match_counts)),
        "releases": tuple(None if item is None else _int(item, field=f"{field}.release_offset[{i}]") for i, item in enumerate(releases)),
        "reasons": tuple(reasons),
    }


def _verify_decisions(raw: Mapping[str, object], *, policy: str, init_seed: int | None, reference: Mapping[str, Any]) -> None:
    decisions = raw["reference_policy_decisions"]
    if not isinstance(decisions, list) or len(decisions) != 3:
        _fail("reference_policy_decisions must contain offsets 1,2,3 exactly once")
    seen: list[int] = []
    for index, decision in enumerate(decisions):
        if policy == "main":
            d = _keys(decision, {"actions", "offset", "policy"}, field=f"reference_policy_decisions[{index}]")
            if d["policy"] != "main":
                _fail("Main tape contains a non-Main continuation decision")
        else:
            d = _keys(decision, {"actions", "c3_state_sha256", "decision_sha256", "initialization_seed", "legacy_state_sha256", "mask_sha256", "offset", "q1_sha256", "q3_sha256", "schema", "selected_q3_rung"}, field=f"reference_policy_decisions[{index}]")
            if d["schema"] != "multi-catfish-mcrl-v04-c2-q13-continuation-v1" or d["selected_q3_rung"] != 100 or d["initialization_seed"] != init_seed:
                _fail("Q13 continuation decision lineage drifted")
            for name in ("c3_state_sha256", "decision_sha256", "legacy_state_sha256", "mask_sha256", "q1_sha256", "q3_sha256"):
                _digest(d[name], field=f"reference_policy_decisions[{index}].{name}")
        offset = _int(d["offset"], field=f"reference_policy_decisions[{index}].offset")
        if offset not in DOWNSTREAM_OFFSETS or offset in seen:
            _fail("reference continuation offsets are not exactly 1,2,3")
        seen.append(offset)
        actions = _actions(d["actions"], field=f"reference_policy_decisions[{index}].actions")
        if actions != reference["detached_actions"][offset]:
            _fail(f"reference policy decision actions disagree at offset {offset}")
    if seen != list(DOWNSTREAM_OFFSETS):
        _fail("reference continuation decisions are out of order")


def _verify_target(target: object, *, tape_sha: str, reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    value = _keys(target, {"candidate_rates_bps", "candidate_system_power_w", "interval_s", "lambda_bits_per_j", "mean_offset_surplus_bits", "offset_rate_delta_bps", "offset_surplus_bits", "offset_system_energy_delta_j", "reference_rates_bps", "reference_system_power_w", "schema", "tape_sha256", "target_sha256", "zeta2_temporal_surplus_bits"}, field="target")
    if value["schema"] != TARGET_SCHEMA or value["tape_sha256"] != tape_sha:
        _fail("target schema or tape binding drifted")
    _digest(value["target_sha256"], field="target.target_sha256")
    if value["lambda_bits_per_j"] != EXPECTED_LAMBDA_HEX or value["interval_s"] != EXPECTED_INTERVAL_HEX:
        _fail("target uses a non-canonical lambda or interval")
    multiplier = float.fromhex(EXPECTED_LAMBDA_HEX)
    interval = float.fromhex(EXPECTED_INTERVAL_HEX)
    ref_rates = np.asarray(reference["rates"], dtype=np.float64)
    cand_rates = np.asarray(candidate["rates"], dtype=np.float64)
    ref_power = np.asarray(reference["powers"], dtype=np.float64)
    cand_power = np.asarray(candidate["powers"], dtype=np.float64)
    expected_hex: dict[str, object] = {
        "reference_rates_bps": [_float_hex(x) for x in ref_rates.ravel()],
        "candidate_rates_bps": [_float_hex(x) for x in cand_rates.ravel()],
        "reference_system_power_w": [_float_hex(x) for x in ref_power.ravel()],
        "candidate_system_power_w": [_float_hex(x) for x in cand_power.ravel()],
    }
    for name, length in (("reference_rates_bps", 4 * USER_COUNT), ("candidate_rates_bps", 4 * USER_COUNT), ("reference_system_power_w", 4), ("candidate_system_power_w", 4)):
        _hex_vector(value[name], field=f"target.{name}", length=length)
        if value[name] != expected_hex[name]:
            _fail(f"target.{name} disagrees with raw trace")
    delta_rate = np.asarray([cand_rates[offset] - ref_rates[offset] for offset in DOWNSTREAM_OFFSETS], dtype=np.float64)
    delta_energy = np.asarray([interval * (cand_power[offset] - ref_power[offset]) for offset in DOWNSTREAM_OFFSETS], dtype=np.float64)
    surplus = np.asarray([interval * float(np.sum(delta_rate[index])) - multiplier * delta_energy[index] for index in range(3)], dtype=np.float64)
    expected_target_fields = {
        "offset_rate_delta_bps": [_float_hex(x) for x in delta_rate.ravel()],
        "offset_system_energy_delta_j": [_float_hex(x) for x in delta_energy],
        "offset_surplus_bits": [_float_hex(x) for x in surplus],
        "zeta2_temporal_surplus_bits": _float_hex(math.fsum(float(x) for x in surplus)),
        "mean_offset_surplus_bits": _float_hex(math.fsum(float(x) for x in surplus) / 3.0),
    }
    for name, length in (("offset_rate_delta_bps", 3 * USER_COUNT), ("offset_system_energy_delta_j", 3), ("offset_surplus_bits", 3)):
        _hex_vector(value[name], field=f"target.{name}", length=length)
        if value[name] != expected_target_fields[name]:
            _fail(f"target.{name} disagrees with raw rate/energy recomputation")
    for name in ("zeta2_temporal_surplus_bits", "mean_offset_surplus_bits"):
        if not isinstance(value[name], str) or value[name] != expected_target_fields[name]:
            _fail(f"target.{name} disagrees with raw surplus recomputation")
        _hex_vector([value[name]], field=f"target.{name}", length=1)
    expected_payload = {
        "schema": TARGET_SCHEMA,
        "tape_sha256": tape_sha,
        "lambda_bits_per_j": EXPECTED_LAMBDA_HEX,
        "interval_s": EXPECTED_INTERVAL_HEX,
        "reference_rates_bps": expected_hex["reference_rates_bps"],
        "candidate_rates_bps": expected_hex["candidate_rates_bps"],
        "reference_system_power_w": expected_hex["reference_system_power_w"],
        "candidate_system_power_w": expected_hex["candidate_system_power_w"],
        **expected_target_fields,
    }
    if _canonical_sha(expected_payload) != value["target_sha256"]:
        _fail("target_sha256 disagrees with the canonical target payload")


def _verify_row(
    row: object,
    *,
    index: int,
    anchor: Mapping[str, object],
    policy: str,
    init_seed: int | None,
    source_manifest_sha: str,
    main_policy_sha: str,
    q13_policy_shas: Mapping[int, str],
    require_policy_components: bool,
    top_policy_components: Mapping[str, object] | None,
    q13_hybrid_path: Path | None,
) -> tuple[tuple[int, str, str, int], tuple[int, int]]:
    expected = {"anchor_schedule_sha256", "anchor_sha256", "candidate_physical_key", "common_random_field_sha256", "evaluation_seed", "focal_user", "held_out_ee_evaluated", "initialization_seed", "pair_plan", "raw_trace", "reference_policy_sha256", "schema", "source_manifest_sha256", "source_route", "source_seed", "tape", "tape_policy", "target", "test_split_opened", "training_run"}
    if require_policy_components:
        expected.add("reference_policy_components")
    value = _keys(row, expected, field=f"rows[{index}]")
    expected_schema = ROW_SCHEMA_V2 if require_policy_components else ROW_SCHEMA_V1
    if value["schema"] != expected_schema or value["source_route"] != "C2" or value["tape_policy"] != policy:
        _fail(f"rows[{index}] schema/route/policy is stale")
    if value["initialization_seed"] != init_seed:
        _fail(f"rows[{index}] initialization seed drifted")
    for name in ("training_run", "test_split_opened", "held_out_ee_evaluated"):
        if value[name] is not False:
            _fail(f"rows[{index}] opens forbidden {name}")
    for name in ("anchor_sha256", "anchor_schedule_sha256", "common_random_field_sha256", "source_manifest_sha256", "reference_policy_sha256"):
        _digest(value[name], field=f"rows[{index}].{name}")
    for name in ("anchor_sha256", "anchor_schedule_sha256", "common_random_field_sha256", "source_manifest_sha256"):
        if value[name] != anchor[name] and name != "source_manifest_sha256":
            _fail(f"rows[{index}].{name} disagrees with schedule anchor")
    if value["source_manifest_sha256"] != source_manifest_sha:
        _fail(f"rows[{index}] source manifest is not the authenticated Phase-A source")
    if value["source_seed"] != anchor["source_seed"] or value["evaluation_seed"] != anchor["evaluation_seed"] or value["focal_user"] != anchor["focal_user"]:
        _fail(f"rows[{index}] seed/focal lineage disagrees with schedule anchor")
    candidate_key = _physical(value["candidate_physical_key"], field=f"rows[{index}].candidate_physical_key")
    if candidate_key != _physical(anchor["candidate_physical_keys"][0], field=f"anchor[{index}].candidate_physical_keys[0]"):
        _fail(f"rows[{index}] candidate selection is not the first sealed legal non-Main key")
    if require_policy_components:
        if top_policy_components is None:
            _fail(f"rows[{index}] has no top-level policy-component receipt")
        components = _verify_reference_policy_components(
            value["reference_policy_components"],
            policy=policy,
            init_seed=init_seed,
            reference_policy_sha=str(value["reference_policy_sha256"]),
            main_policy_sha=main_policy_sha,
            hybrid_path=q13_hybrid_path,
            field=f"rows[{index}].reference_policy_components",
        )
        if components != dict(top_policy_components):
            _fail(f"rows[{index}] policy components disagree with top-level receipt")
    else:
        expected_policy = main_policy_sha if policy == "main" else q13_policy_shas[int(init_seed)]
        if value["reference_policy_sha256"] != expected_policy:
            _fail(f"rows[{index}] reference policy digest is not the expected lineage")
    raw = _keys(value["raw_trace"], {"candidate", "continuation_start_offset", "reference", "reference_policy_decisions", "release_offset", "release_reason", "support_counts"}, field=f"rows[{index}].raw_trace")
    if raw["continuation_start_offset"] != 1:
        _fail(f"rows[{index}] continuation does not start at offset 1")
    counts_raw = raw["support_counts"]
    if not isinstance(counts_raw, list) or len(counts_raw) != 4:
        _fail(f"rows[{index}] support_counts does not cover offsets 0..3")
    counts = tuple(_int(item, field=f"rows[{index}].support_counts[{j}]") for j, item in enumerate(counts_raw))
    release_offset = _int(raw["release_offset"], field=f"rows[{index}].release_offset")
    if release_offset not in DOWNSTREAM_OFFSETS or raw["release_reason"] not in RELEASE_REASONS:
        _fail(f"rows[{index}] release receipt is invalid")
    if raw["release_reason"] == "horizon":
        if release_offset != 3 or counts != (1, 1, 1, 1):
            _fail(f"rows[{index}] horizon release must have unique support at offsets 0..3")
    else:
        if any(item != 1 for item in counts[:release_offset]) or counts[release_offset] != 0 or any(item > 1 for item in counts[release_offset + 1:]):
            _fail(f"rows[{index}] support-expiry receipt is not monotone and unambiguous")
    reference = _verify_trace_branch(raw["reference"], field=f"rows[{index}].raw_trace.reference")
    candidate = _verify_trace_branch(raw["candidate"], field=f"rows[{index}].raw_trace.candidate")
    if reference["held"] != (None, None, None, None) or reference["match_counts"] != (None, None, None, None) or reference["releases"] != (None, None, None, None) or reference["reasons"] != (None, None, None, None):
        _fail(f"rows[{index}] reference branch carries candidate hold/release metadata")
    tape = _keys(value["tape"], {"anchor_sha256", "common_random_field_sha256", "fading_mode", "focal_user", "reference_policy_sha256", "reference_trace_sha256", "schema", "steps", "tape_sha256"}, field=f"rows[{index}].tape")
    if tape["schema"] != TAPE_SCHEMA or tape["fading_mode"] != FADING_MODE or tape["focal_user"] != value["focal_user"]:
        _fail(f"rows[{index}] tape schema/fading/focal binding drifted")
    for name in ("anchor_sha256", "common_random_field_sha256", "reference_policy_sha256", "tape_sha256", "reference_trace_sha256"):
        _digest(tape[name], field=f"rows[{index}].tape.{name}")
    if tape["anchor_sha256"] != value["anchor_sha256"] or tape["common_random_field_sha256"] != value["common_random_field_sha256"] or tape["reference_policy_sha256"] != value["reference_policy_sha256"]:
        _fail(f"rows[{index}] tape lineage disagrees with row")
    tape_steps = tape["steps"]
    if not isinstance(tape_steps, list) or len(tape_steps) != 4:
        _fail(f"rows[{index}] tape does not contain offsets 0..3")
    normalized_tape_steps: list[dict[str, object]] = []
    for offset, step in enumerate(tape_steps):
        st = _keys(step, {"offset", "physical_actions", "source_action_indices"}, field=f"rows[{index}].tape.steps[{offset}]")
        if st["offset"] != offset:
            _fail(f"rows[{index}] tape step offsets are not ordered")
        physical = _physical_vector(st["physical_actions"], field=f"rows[{index}].tape.steps[{offset}].physical_actions")
        actions = _actions(st["source_action_indices"], field=f"rows[{index}].tape.steps[{offset}].source_action_indices")
        if physical != reference["executed_physical"][offset] or actions != reference["executed_actions"][offset]:
            _fail(f"rows[{index}] tape step disagrees with reference raw trace at offset {offset}")
        normalized_tape_steps.append({"offset": offset, "physical_actions": [None if item is None else list(item) for item in physical], "source_action_indices": list(actions)})
    if tape["reference_trace_sha256"] != _trace_digest(raw["reference"]):
        _fail(f"rows[{index}] reference trace digest is invalid")
    tape_payload = {"schema": TAPE_SCHEMA, "anchor_sha256": tape["anchor_sha256"], "reference_trace_sha256": tape["reference_trace_sha256"], "reference_policy_sha256": tape["reference_policy_sha256"], "common_random_field_sha256": tape["common_random_field_sha256"], "fading_mode": tape["fading_mode"], "focal_user": tape["focal_user"], "steps": normalized_tape_steps}
    if _canonical_sha(tape_payload) != tape["tape_sha256"]:
        _fail(f"rows[{index}] tape_sha256 is invalid")
    if tape_steps[0]["physical_actions"][int(value["focal_user"])] != anchor["reference_physical_key"]:
        _fail(f"rows[{index}] tape opening focal key differs from sealed Main")
    plan = _keys(value["pair_plan"], {"focal_user", "held_physical_key", "plan_sha256", "release_offset", "release_reason", "schema", "steps", "support_counts", "tape_sha256"}, field=f"rows[{index}].pair_plan")
    if plan["schema"] != PLAN_SCHEMA or plan["tape_sha256"] != tape["tape_sha256"] or plan["focal_user"] != value["focal_user"] or plan["release_offset"] != release_offset or plan["release_reason"] != raw["release_reason"] or plan["support_counts"] != list(counts):
        _fail(f"rows[{index}] pair plan top-level binding drifted")
    held_key = _physical(plan["held_physical_key"], field=f"rows[{index}].pair_plan.held_physical_key")
    if held_key != candidate_key or held_key == _physical(anchor["reference_physical_key"], field=f"anchor[{index}].reference_physical_key"):
        _fail(f"rows[{index}] held focal key is not the selected non-Main key")
    plan_steps = plan["steps"]
    if not isinstance(plan_steps, list) or len(plan_steps) != 4:
        _fail(f"rows[{index}] pair plan does not contain offsets 0..3")
    normalized_plan_steps: list[dict[str, object]] = []
    for offset, step in enumerate(plan_steps):
        st = _keys(step, {"candidate_actions", "candidate_physical_actions", "focal_mode", "nonfocal_equal", "nonfocal_equality_sha256", "offset", "reference_actions", "reference_physical_actions"}, field=f"rows[{index}].pair_plan.steps[{offset}]")
        if st["offset"] != offset:
            _fail(f"rows[{index}] pair plan step offsets are not ordered")
        ref_actions = _actions(st["reference_actions"], field=f"rows[{index}].pair_plan.steps[{offset}].reference_actions")
        cand_actions = _actions(st["candidate_actions"], field=f"rows[{index}].pair_plan.steps[{offset}].candidate_actions")
        ref_physical = _physical_vector(st["reference_physical_actions"], field=f"rows[{index}].pair_plan.steps[{offset}].reference_physical_actions")
        cand_physical = _physical_vector(st["candidate_physical_actions"], field=f"rows[{index}].pair_plan.steps[{offset}].candidate_physical_actions")
        tape_physical = _physical_vector(
            tape_steps[offset]["physical_actions"],
            field=f"rows[{index}].tape.steps[{offset}].physical_actions",
        )
        if ref_actions != reference["executed_actions"][offset] or ref_physical != tape_physical:
            _fail(f"rows[{index}] pair reference actions disagree at offset {offset}")
        # Compare against normalized tuples to avoid list/tuple ambiguity.
        candidate_raw_physical = candidate["executed_physical"][offset]
        if cand_actions != candidate["executed_actions"][offset] or cand_physical != candidate_raw_physical:
            _fail(f"rows[{index}] pair candidate actions disagree at offset {offset}")
        focal = int(value["focal_user"])
        if any(ref_physical[user] != cand_physical[user] for user in range(USER_COUNT) if user != focal):
            _fail(f"rows[{index}] nonfocal physical action mismatch at offset {offset}")
        if st["nonfocal_equal"] is not True:
            _fail(f"rows[{index}] nonfocal_equal is not true")
        receipt = _nonfocal_receipt(offset=offset, focal=focal, reference=ref_physical, candidate=cand_physical)
        if st["nonfocal_equality_sha256"] != receipt:
            _fail(f"rows[{index}] nonfocal equality receipt is invalid at offset {offset}")
        _digest(st["nonfocal_equality_sha256"], field=f"rows[{index}].pair_plan.steps[{offset}].nonfocal_equality_sha256")
        expected_mode = "hold" if offset < release_offset else "released"
        if st["focal_mode"] != expected_mode or st["focal_mode"] not in FOCAL_MODES:
            _fail(f"rows[{index}] focal hold/release mode drifted at offset {offset}")
        if offset < release_offset:
            if cand_physical[focal] != held_key:
                _fail(f"rows[{index}] focal hold key drifted at offset {offset}")
        elif cand_physical[focal] != _physical(tape_steps[offset]["physical_actions"][focal], field="tape focal physical"):
            _fail(f"rows[{index}] focal released action does not follow tape at offset {offset}")
        normalized_plan_steps.append({
            "offset": offset,
            "reference_actions": list(ref_actions),
            "candidate_actions": list(cand_actions),
            "reference_physical_actions": [None if item is None else list(item) for item in ref_physical],
            "candidate_physical_actions": [None if item is None else list(item) for item in cand_physical],
            "focal_mode": st["focal_mode"],
            "nonfocal_equal": True,
            "nonfocal_equality_sha256": receipt,
        })
    normalized_plan = {"schema": PLAN_SCHEMA, "tape_sha256": plan["tape_sha256"], "focal_user": plan["focal_user"], "held_physical_key": list(held_key), "release_offset": release_offset, "release_reason": plan["release_reason"], "support_counts": list(counts), "steps": normalized_plan_steps}
    if _canonical_sha(normalized_plan) != plan["plan_sha256"]:
        _fail(f"rows[{index}] plan_sha256 is invalid")
    for offset in range(4):
        if candidate["held"][offset] != held_key or candidate["match_counts"][offset] != counts[offset] or candidate["releases"][offset] != release_offset or candidate["reasons"][offset] != raw["release_reason"]:
            _fail(f"rows[{index}] candidate hold/release receipt disagrees at offset {offset}")
        # ``support_counts`` is measured from the pre-action observation.  At
        # the release offset the candidate has already executed the released
        # tape action, so the post-step active set is not expected to retain
        # the held key (and the key may legitimately remain active for a
        # different user).  During the actual hold interval, however, the
        # executed focal action must be represented by an active held key.
        if offset < release_offset and held_key not in candidate["active"][offset]:
            _fail(f"rows[{index}] held focal key is absent from active physical IDs during hold at offset {offset}")
    _verify_decisions(raw, policy=policy, init_seed=init_seed, reference=reference)
    _verify_target(value["target"], tape_sha=str(tape["tape_sha256"]), reference=reference, candidate=candidate)
    intervention = (int(anchor["source_seed"]), str(anchor["world_anchor_sha256"]), str(anchor["anchor_sha256"]), int(anchor["focal_user"]))
    return intervention, candidate_key


def _verify_output(
    path: Path,
    *,
    anchors: Mapping[str, Mapping[str, object]],
    policy: str,
    init_seed: int | None,
    source_manifest_sha: str,
    main_policy_sha: str,
    q13_policy_shas: Mapping[int, str],
    q13_hybrid_paths: Mapping[int, Path],
) -> dict[str, object]:
    output, file_sha = _read_json(path)
    schema = output.get("schema")
    if schema not in {OUTPUT_SCHEMA_V1, OUTPUT_SCHEMA_V2}:
        _fail(f"{path} output schema is stale or unsupported")
    require_policy_components = schema == OUTPUT_SCHEMA_V2
    top_expected = {"anchor_count", "candidate_selection", "held_out_ee_evaluated", "initialization_seed", "rows", "schema", "status", "tape_policy", "test_split_opened", "training_run"}
    if require_policy_components:
        top_expected.add("reference_policy_components")
    top = _keys(output, top_expected, field=str(path), optional={"claim_ceiling"})
    if output.get("claim_ceiling", EXPECTED_CLAIM_CEILING) != EXPECTED_CLAIM_CEILING:
        _fail(f"{path} claim ceiling is too weak or stale")
    if top["status"] != OUTPUT_STATUS or top["tape_policy"] != policy or top["anchor_count"] != 12 or top["candidate_selection"] != "first-sealed-legal-nonmain-key" or top["initialization_seed"] != init_seed:
        _fail(f"{path} top-level schema, policy, or cardinality is invalid")
    if top["training_run"] is not False or top["test_split_opened"] is not False or top["held_out_ee_evaluated"] is not False:
        _fail(f"{path} opens training, TEST, or held-out EE")
    rows = top["rows"]
    if not isinstance(rows, list) or len(rows) != 12:
        _fail(f"{path} must contain exactly 12 rows")
    top_policy_components: Mapping[str, object] | None = None
    q13_hybrid_path = None
    if require_policy_components:
        if policy == "q13":
            if init_seed is None or int(init_seed) not in q13_hybrid_paths:
                _fail(f"{path} has no selected Q13 hybrid for policy-component recomputation")
            q13_hybrid_path = q13_hybrid_paths[int(init_seed)]
        top_policy_components = _verify_reference_policy_components(
            top["reference_policy_components"],
            policy=policy,
            init_seed=init_seed,
            reference_policy_sha=str(top["reference_policy_components"].get("policy_components_sha256")) if isinstance(top["reference_policy_components"], Mapping) else "",
            main_policy_sha=main_policy_sha,
            hybrid_path=q13_hybrid_path,
            field=f"{path}.reference_policy_components",
        )
    expected_anchors = sorted(anchors.values(), key=lambda anchor: (int(anchor["source_seed"]), int(anchor["anchor_step"]), int(anchor["focal_user"]), str(anchor["anchor_sha256"])))
    if any(not isinstance(row, Mapping) for row in rows):
        _fail(f"{path} rows must all be JSON objects")
    if [str(row["anchor_sha256"]) for row in rows] != [str(anchor["anchor_sha256"]) for anchor in expected_anchors]:
        _fail(f"{path} rows are not the deterministic 12-anchor prefix")
    identities: list[tuple[tuple[int, str, str, int], tuple[int, int]]] = []
    for index, (row, anchor) in enumerate(zip(rows, expected_anchors, strict=True)):
        identities.append(_verify_row(row, index=index, anchor=anchor, policy=policy, init_seed=init_seed, source_manifest_sha=source_manifest_sha, main_policy_sha=main_policy_sha, q13_policy_shas=q13_policy_shas, require_policy_components=require_policy_components, top_policy_components=top_policy_components, q13_hybrid_path=None))
    if len(set(identity[0] for identity in identities)) != 12:
        _fail(f"{path} contains duplicate anchor identities")
    return {"path": str(path.resolve()), "file_sha256": file_sha, "policy": policy, "initialization_seed": init_seed, "row_count": 12, "schema": str(schema), "status": "PASS_MECHANICS_ONLY"}


def verify_lockstep_batch(*, main_path: Path, q13_paths: Sequence[Path], schedule_path: Path, prepare_receipt_path: Path, q13_gate_path: Path) -> dict[str, object]:
    """Verify Main 12 + three Q13 12-row outputs and return a receipt."""

    if len(q13_paths) != 3:
        _fail("exactly three Q13 output paths are required")
    anchors, schedule_sha = _verify_schedule(schedule_path)
    source_manifest_sha, main_policy_sha = _verify_prepare(prepare_receipt_path, anchors=anchors, schedule_sha=schedule_sha)
    q13_policy_shas, q13_hybrid_paths = _verify_q13_gate(q13_gate_path)
    # This scan runs after parsing but before any target interpretation.  It
    # prevents a future producer from adding a silent repair/drop channel.
    main_raw, _ = _read_json(main_path)
    _scan_forbidden(main_raw)
    q13_raw: list[dict[str, object]] = []
    for path in q13_paths:
        raw, _ = _read_json(path)
        _scan_forbidden(raw)
        q13_raw.append(raw)
    main_summary = _verify_output(main_path, anchors=anchors, policy="main", init_seed=None, source_manifest_sha=source_manifest_sha, main_policy_sha=main_policy_sha, q13_policy_shas=q13_policy_shas, q13_hybrid_paths=q13_hybrid_paths)
    q13_summaries: list[dict[str, object]] = []
    seen_seeds: set[int] = set()
    for path, raw in zip(q13_paths, q13_raw, strict=True):
        seed = raw.get("initialization_seed")
        if type(seed) is not int or seed not in Q13_SEEDS or seed in seen_seeds:
            _fail(f"Q13 output {path} has a duplicate or unsupported initialization seed")
        seen_seeds.add(seed)
        q13_summaries.append(_verify_output(path, anchors=anchors, policy="q13", init_seed=seed, source_manifest_sha=source_manifest_sha, main_policy_sha=main_policy_sha, q13_policy_shas=q13_policy_shas, q13_hybrid_paths=q13_hybrid_paths))
    if seen_seeds != set(Q13_SEEDS):
        _fail("the Q13 batch does not cover exactly seeds 2026092101/02/03")
    # Cross-policy rows must share the same schedule identity, source seed,
    # focal user, candidate key, and keyed fading root.  The tape/policy
    # digests are allowed to differ because the reference policy differs.
    shared: dict[str, tuple[object, ...]] = {}
    for seed_path in [main_path, *q13_paths]:
        payload, _ = _read_json(seed_path)
        key = str(payload["initialization_seed"])
        shared[key] = tuple((
            row["anchor_sha256"], row["anchor_schedule_sha256"], row["source_seed"], row["evaluation_seed"], row["focal_user"], tuple(row["candidate_physical_key"]), row["common_random_field_sha256"],
        ) for row in payload["rows"])
    if len(set(shared.values())) != 1:
        _fail("Main and Q13 outputs do not share the same physical 12-anchor batch")
    return {
        "schema": "multi-catfish-mcrl-v05-c2-controlled-tape-mechanics-verification-v1",
        "status": "PASS_MECHANICS_ONLY",
        "claim_ceiling": EXPECTED_CLAIM_CEILING,
        "schedule_sha256": schedule_sha,
        "source_manifest_sha256": source_manifest_sha,
        "row_count": 48,
        "main": main_summary,
        "q13": sorted(q13_summaries, key=lambda item: int(item["initialization_seed"])),
        "target_signs_inspected": False,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--q13", type=Path, action="append", required=True, help="repeat exactly three times")
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--prepare-receipt", type=Path, required=True)
    parser.add_argument("--q13-gate", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify_lockstep_batch(main_path=args.main, q13_paths=args.q13, schedule_path=args.schedule, prepare_receipt_path=args.prepare_receipt, q13_gate_path=args.q13_gate)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(_cli())
    except MechanicsVerificationError as error:
        print(f"FAIL_CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2)


__all__ = ["EXPECTED_CLAIM_CEILING", "MechanicsVerificationError", "verify_lockstep_batch"]
