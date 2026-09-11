"""Target-free preparation boundary for the V0.6 C2-k1 learner screen.

The T1 source gate is intentionally frozen in its own runner.  This module is
only the seam between a target-free PREPARE anchor and a future, bounded Q2
learner: it serialises the focal user's 228-dimensional pre-decision state,
binds the native action mask and the frozen authorities, and verifies that the
sidecar contains no source outcomes.

It does not read T1 source rows, choose learner hyperparameters, train a
network, open a held-out evaluation, or launch 9000 episodes.  The learner
plan checker below accepts a plan only after the formal T1 verdict is exactly
``AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN``; even then it returns a
preparation receipt and does not start training.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from typing import Any

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from .ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from .ee_axis_v06_c2_k1 import (
    ACTION_COUNT,
    POLICY_RULE,
    POOL_NAMES,
    SCHEMA as V06_ALGORITHM_SCHEMA,
    SOURCE_RULE as V06_SOURCE_RULE,
    TRAIN_STEP_WINDOWS,
    TRAIN_WORLD_POOLS,
)


STATE_SIDECAR_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-state-sidecar-v1"
STATE_SIDECAR_SOURCE_RULE = "target-free-focal-anchor-state-mask-v1"
PREPARE_LIVE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-v2"
FORMAL_LEARNER_VERDICT = "AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN"
LEARNER_PLAN_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-bounded-learner-plan-v1"
LEARNER_SCOPE = "one-bounded-c2-k1-q2-only"
WORLD_COUNT = 12
ROWS_PER_ANCHOR = ACTION_COUNT
ROW_COUNT = WORLD_COUNT * ROWS_PER_ANCHOR


class C2K1LearnerPreparationError(ValueError):
    """A target-free sidecar or post-gate plan is not admissible."""


_AUTHORITY_FIELDS = (
    "prepare_sha256",
    "simulator_source_manifest_sha256",
    "q13_gate_source_manifest_sha256",
    "simulator_prereg_file_sha256",
    "t1_prereg_file_sha256",
    "code_authority_sha256",
    "source_authority_sha256",
)
_ANCHOR_FIELDS = (
    "pool",
    "world_id",
    "step",
    "focal_user",
    "reference_action",
    "world_anchor_sha256",
    "anchor_sha256",
    "checkpoint_sha256",
    "simulator_source_manifest_sha256",
    "policy_sha256",
    "evaluation_seed",
    "legal_action_mask",
)
_ROW_FIELDS = frozenset(
    {
        "row_key",
        "anchor_key",
        "pool",
        "world_id",
        "step",
        "focal_user",
        "action",
        "reference_action",
        "state_schema",
        "state_schema_sha256",
        "state",
        "action_mask",
        "state_sha256",
        "mask_sha256",
        "provenance_sha256",
        "anchor_sha256",
        "world_anchor_sha256",
        "checkpoint_sha256",
        "policy_sha256",
        *_AUTHORITY_FIELDS,
    }
)
_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "algorithm_schema",
        "source_rule",
        "prepare_schema",
        "state_schema",
        "state_schema_sha256",
        *_AUTHORITY_FIELDS,
        "counts",
        "rows",
        "target_free",
        "training",
        "test_split_opened",
        "outcome_selection",
        "q2_consulted",
        "sidecar_sha256",
    }
)
_FORBIDDEN_FIELDS = frozenset(
    {
        "target",
        "target_surplus_bits",
        "z2",
        "z2_k1_bits",
        "z2_k1_normalized",
        "outcome",
        "outcomes",
        "metrics",
        "ee",
        "oracle",
        "drop",
        "rates",
        "power",
        "served",
        "loss",
        "q2",
    }
)


def _canonical_sha256(payload: object) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C2K1LearnerPreparationError(
            "payload is not canonical finite JSON"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2K1LearnerPreparationError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise C2K1LearnerPreparationError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _reject_forbidden_keys(value: Mapping[str, Any], *, field: str) -> None:
    forbidden = sorted(set(value) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise C2K1LearnerPreparationError(
            f"{field} contains forbidden target/outcome fields: {forbidden}"
        )


def _anchor_key(anchor: Mapping[str, Any]) -> str:
    return (
        f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:{anchor['focal_user']}"
    )


def _state_array(value: object, *, field: str) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise C2K1LearnerPreparationError(f"{field} is not an array") from error
    if raw.shape != (EE_AXIS_STATE_DIM,):
        raise C2K1LearnerPreparationError(
            f"{field} must have shape ({EE_AXIS_STATE_DIM},), got {raw.shape}"
        )
    if raw.dtype.kind not in "fiu":
        raise C2K1LearnerPreparationError(f"{field} must be numeric")
    if not np.all(np.isfinite(raw)):
        raise C2K1LearnerPreparationError(f"{field} must be finite")
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            result = np.array(raw, dtype=np.float32, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise C2K1LearnerPreparationError(f"{field} is not float32-compatible") from error
    if not np.all(np.isfinite(result)):
        raise C2K1LearnerPreparationError(f"{field} is not finite after float32 encoding")
    result.setflags(write=False)
    return result


def _mask_array(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (NUM_ACTIONS,) or raw.dtype != np.bool_:
        raise C2K1LearnerPreparationError(
            f"{field} must be Boolean shape ({NUM_ACTIONS},)"
        )
    if not bool(np.any(raw)):
        raise C2K1LearnerPreparationError(f"{field} must contain a legal action")
    result = np.array(raw, dtype=np.bool_, copy=True, order="C")
    result.setflags(write=False)
    return result


def _state_hash(state: np.ndarray, mask: np.ndarray) -> str:
    payload = {
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "state_float32_hex": [float(value).hex() for value in state.tolist()],
        "action_mask": [bool(value) for value in mask.tolist()],
    }
    return _canonical_sha256(payload)


def _mask_hash(mask: np.ndarray) -> str:
    return _canonical_sha256(
        {
            "action_dim": NUM_ACTIONS,
            "action_mask": [bool(value) for value in mask.tolist()],
        }
    )


def _row_provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": STATE_SIDECAR_SCHEMA,
        "row_key": row["row_key"],
        "anchor_key": row["anchor_key"],
        "action": row["action"],
        "reference_action": row["reference_action"],
        "state_sha256": row["state_sha256"],
        "mask_sha256": row["mask_sha256"],
        "anchor_sha256": row["anchor_sha256"],
        "world_anchor_sha256": row["world_anchor_sha256"],
        "checkpoint_sha256": row["checkpoint_sha256"],
        "policy_sha256": row["policy_sha256"],
        **{field: row[field] for field in _AUTHORITY_FIELDS},
    }


def _authority_context(prepare: Mapping[str, Any]) -> dict[str, str]:
    """Validate only target-free PREPARE authority and return its digests."""

    if not isinstance(prepare, Mapping):
        raise C2K1LearnerPreparationError("prepare must be a mapping")
    _reject_forbidden_keys(prepare, field="prepare")
    if prepare.get("schema") != PREPARE_LIVE_SCHEMA:
        raise C2K1LearnerPreparationError(
            "sidecar requires the current PREPARE_LIVE_SCHEMA"
        )
    if prepare.get("algorithm_schema") != V06_ALGORITHM_SCHEMA:
        raise C2K1LearnerPreparationError("prepare algorithm schema is stale")
    if prepare.get("source_rule") != V06_SOURCE_RULE:
        raise C2K1LearnerPreparationError("prepare source rule is stale")
    if prepare.get("policy_rule") != POLICY_RULE:
        raise C2K1LearnerPreparationError("prepare policy rule is stale")
    for field in (
        "simulator_source_manifest_sha256",
        "q13_gate_source_manifest_sha256",
        "simulator_prereg_file_sha256",
        "t1_prereg_file_sha256",
    ):
        _digest(prepare.get(field), field=f"prepare.{field}")
    prepare_digest = _digest(prepare.get("prepare_sha256"), field="prepare.prepare_sha256")
    unsigned = dict(prepare)
    unsigned.pop("prepare_sha256", None)
    if _canonical_sha256(unsigned) != prepare_digest:
        raise C2K1LearnerPreparationError("prepare_sha256 disagrees with PREPARE payload")

    if (
        prepare.get("training") is not False
        or prepare.get("test_split_opened") is not False
        or prepare.get("outcome_selection") is not False
        or prepare.get("q2_consulted") is not False
        or prepare.get("prepared_before_generation") is not True
    ):
        raise C2K1LearnerPreparationError("PREPARE is not target-free")

    code_authority = prepare.get("code_authority")
    if not isinstance(code_authority, Mapping):
        raise C2K1LearnerPreparationError("prepare.code_authority is missing")
    _reject_forbidden_keys(code_authority, field="prepare.code_authority")
    code_digest = _digest(code_authority.get("sha256"), field="prepare.code_authority.sha256")
    code_files = code_authority.get("files")
    if not isinstance(code_files, Mapping) or not code_files:
        raise C2K1LearnerPreparationError("prepare.code_authority.files is empty")
    for name, digest in code_files.items():
        if not isinstance(name, str) or not name.strip():
            raise C2K1LearnerPreparationError("code authority file name is malformed")
        _digest(digest, field=f"prepare.code_authority.files.{name}")
    # The frozen T1 runner defines ``code_authority.sha256`` as the digest of
    # the file-name-to-digest mapping itself (not of a wrapper object).
    if _canonical_sha256(dict(code_files)) != code_digest:
        raise C2K1LearnerPreparationError("code authority digest disagrees with files")

    source_authority = prepare.get("source_authority")
    if not isinstance(source_authority, Mapping) or not source_authority:
        raise C2K1LearnerPreparationError("prepare.source_authority is missing")
    _reject_forbidden_keys(source_authority, field="prepare.source_authority")
    source_authority_digest = _canonical_sha256(dict(source_authority))

    anchors = prepare.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != WORLD_COUNT:
        raise C2K1LearnerPreparationError(
            f"prepare must contain exactly {WORLD_COUNT} anchors"
        )
    anchor_map: dict[str, Mapping[str, Any]] = {}
    pool_counts = {pool: 0 for pool in POOL_NAMES}
    previous_sort_key: tuple[int, int] | None = None
    pool_order = {pool: index for index, pool in enumerate(POOL_NAMES)}
    for raw in anchors:
        if not isinstance(raw, Mapping):
            raise C2K1LearnerPreparationError("prepare anchor is malformed")
        _reject_forbidden_keys(raw, field="prepare.anchor")
        missing = set(_ANCHOR_FIELDS) - set(raw)
        if missing:
            raise C2K1LearnerPreparationError(
                f"prepare anchor is missing fields: {sorted(missing)}"
            )
        pool = raw.get("pool")
        world = raw.get("world_id")
        if pool not in POOL_NAMES or type(world) is not int or world not in TRAIN_WORLD_POOLS[pool]:
            raise C2K1LearnerPreparationError("prepare anchor is outside fixed world pools")
        sort_key = (pool_order[pool], world)
        if previous_sort_key is not None and sort_key <= previous_sort_key:
            raise C2K1LearnerPreparationError("prepare anchors are not canonically sorted")
        previous_sort_key = sort_key
        step = _exact_int(raw.get("step"), field="prepare.anchor.step")
        lo, hi = TRAIN_STEP_WINDOWS[pool]
        if not lo <= step <= hi:
            raise C2K1LearnerPreparationError("prepare anchor step is outside its pool window")
        focal = _exact_int(raw.get("focal_user"), field="prepare.anchor.focal_user")
        reference = _exact_int(
            raw.get("reference_action"),
            field="prepare.anchor.reference_action",
        )
        if reference >= NUM_ACTIONS:
            raise C2K1LearnerPreparationError("prepare reference action is outside action space")
        for field in (
            "world_anchor_sha256",
            "anchor_sha256",
            "checkpoint_sha256",
            "simulator_source_manifest_sha256",
            "policy_sha256",
        ):
            _digest(raw.get(field), field=f"prepare.anchor.{field}")
        if raw["simulator_source_manifest_sha256"] != prepare["simulator_source_manifest_sha256"]:
            raise C2K1LearnerPreparationError("prepare anchor source authority drifted")
        if raw.get("evaluation_seed") != world:
            raise C2K1LearnerPreparationError("prepare anchor evaluation seed is not its world")
        mask = raw.get("legal_action_mask")
        if (
            not isinstance(mask, list)
            or len(mask) != NUM_ACTIONS
            or any(type(value) is not bool for value in mask)
            or not all(mask)
        ):
            raise C2K1LearnerPreparationError(
                "prepare anchor legal_action_mask is not the complete native mask"
            )
        key = _anchor_key(raw)
        if key in anchor_map or (pool, world) in {(item["pool"], item["world_id"]) for item in anchor_map.values()}:
            raise C2K1LearnerPreparationError("prepare contains a duplicate anchor/world")
        anchor_map[key] = raw
        pool_counts[pool] += 1
    if pool_counts != {pool: 4 for pool in POOL_NAMES}:
        raise C2K1LearnerPreparationError("prepare must contain four worlds per pool")

    return {
        "prepare_sha256": prepare_digest,
        "simulator_source_manifest_sha256": prepare["simulator_source_manifest_sha256"],
        "q13_gate_source_manifest_sha256": prepare["q13_gate_source_manifest_sha256"],
        "simulator_prereg_file_sha256": prepare["simulator_prereg_file_sha256"],
        "t1_prereg_file_sha256": prepare["t1_prereg_file_sha256"],
        "code_authority_sha256": code_digest,
        "source_authority_sha256": source_authority_digest,
        "_anchor_map": anchor_map,
    }


def build_state_sidecar(
    prepare: Mapping[str, Any],
    focal_states: Mapping[str, Mapping[str, object]],
) -> dict[str, Any]:
    """Build a deterministic, target-free state/mask sidecar.

    ``focal_states`` is keyed by the canonical PREPARE anchor key
    ``pool:world_id:step:focal_user``.  Each value contains exactly ``state``
    (the focal user's 228-D state) and ``action_mask`` (the native 28-action
    Boolean mask).  No target, trace, metric, or Q2 value is accepted.
    """

    authorities = _authority_context(prepare)
    if not isinstance(focal_states, Mapping):
        raise C2K1LearnerPreparationError("focal_states must be keyed by PREPARE anchors")
    anchor_map = authorities.pop("_anchor_map")
    if set(focal_states) != set(anchor_map):
        raise C2K1LearnerPreparationError(
            "focal_states must cover exactly the 12 PREPARE anchors"
        )

    rows: list[dict[str, Any]] = []
    for key, anchor in anchor_map.items():
        raw_state = focal_states[key]
        if not isinstance(raw_state, Mapping):
            raise C2K1LearnerPreparationError(f"{key} state record is malformed")
        _reject_forbidden_keys(raw_state, field=f"focal_states[{key}]")
        if set(raw_state) != {"state", "action_mask"}:
            raise C2K1LearnerPreparationError(
                f"focal_states[{key}] must contain only state and action_mask"
            )
        state = _state_array(raw_state["state"], field=f"{key}.state")
        mask = _mask_array(raw_state["action_mask"], field=f"{key}.action_mask")
        expected_mask = np.asarray(anchor["legal_action_mask"], dtype=np.bool_)
        if not np.array_equal(mask, expected_mask):
            raise C2K1LearnerPreparationError(
                f"{key}.action_mask disagrees with PREPARE anchor"
            )
        state_digest = _state_hash(state, mask)
        mask_digest = _mask_hash(mask)
        for action in range(NUM_ACTIONS):
            row = {
                "row_key": f"{key}:{action}",
                "anchor_key": key,
                "pool": anchor["pool"],
                "world_id": anchor["world_id"],
                "step": anchor["step"],
                "focal_user": anchor["focal_user"],
                "action": action,
                "reference_action": anchor["reference_action"],
                "state_schema": EE_AXIS_STATE_SCHEMA,
                "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
                "state": [float(value) for value in state.tolist()],
                "action_mask": [bool(value) for value in mask.tolist()],
                "state_sha256": state_digest,
                "mask_sha256": mask_digest,
                "anchor_sha256": anchor["anchor_sha256"],
                "world_anchor_sha256": anchor["world_anchor_sha256"],
                "checkpoint_sha256": anchor["checkpoint_sha256"],
                "policy_sha256": anchor["policy_sha256"],
                **authorities,
            }
            row["provenance_sha256"] = _canonical_sha256(_row_provenance(row))
            rows.append(row)

    body: dict[str, Any] = {
        "schema": STATE_SIDECAR_SCHEMA,
        "algorithm_schema": V06_ALGORITHM_SCHEMA,
        "source_rule": STATE_SIDECAR_SOURCE_RULE,
        "prepare_schema": PREPARE_LIVE_SCHEMA,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        **authorities,
        "counts": {
            "worlds": WORLD_COUNT,
            "anchors": WORLD_COUNT,
            "actions_per_anchor": NUM_ACTIONS,
            "rows": ROW_COUNT,
        },
        "rows": rows,
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    result = body | {"sidecar_sha256": _canonical_sha256(body)}
    verify_state_sidecar(result, prepare=prepare)
    return result


def verify_state_sidecar(
    payload: Mapping[str, Any],
    *,
    prepare: Mapping[str, Any],
) -> str:
    """Independently verify sidecar shape, coverage, hashes, and provenance."""

    if not isinstance(payload, Mapping):
        raise C2K1LearnerPreparationError("sidecar must be a mapping")
    _reject_forbidden_keys(payload, field="sidecar")
    unknown = set(payload) - _TOP_LEVEL_FIELDS
    if unknown:
        if unknown & _FORBIDDEN_FIELDS:
            raise C2K1LearnerPreparationError(
                f"sidecar contains forbidden target/outcome fields: {sorted(unknown & _FORBIDDEN_FIELDS)}"
            )
        raise C2K1LearnerPreparationError(f"sidecar has unknown fields: {sorted(unknown)}")
    sidecar_digest = _digest(payload.get("sidecar_sha256"), field="sidecar_sha256")
    unsigned = dict(payload)
    unsigned.pop("sidecar_sha256", None)
    if _canonical_sha256(unsigned) != sidecar_digest:
        raise C2K1LearnerPreparationError("sidecar_sha256 disagrees with payload")

    authorities = _authority_context(prepare)
    anchor_map = authorities.pop("_anchor_map")
    if payload.get("schema") != STATE_SIDECAR_SCHEMA:
        raise C2K1LearnerPreparationError("unsupported V0.6 state sidecar schema")
    expected_scalars = {
        "algorithm_schema": V06_ALGORITHM_SCHEMA,
        "source_rule": STATE_SIDECAR_SOURCE_RULE,
        "prepare_schema": PREPARE_LIVE_SCHEMA,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "target_free": True,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    for field, expected in expected_scalars.items():
        if payload.get(field) != expected:
            raise C2K1LearnerPreparationError(f"sidecar {field} is not target-free/current")
    for field in _AUTHORITY_FIELDS:
        _digest(payload.get(field), field=f"sidecar.{field}")
        if payload[field] != authorities[field]:
            raise C2K1LearnerPreparationError(f"sidecar {field} disagrees with PREPARE")

    counts = payload.get("counts")
    if counts != {
        "worlds": WORLD_COUNT,
        "anchors": WORLD_COUNT,
        "actions_per_anchor": NUM_ACTIONS,
        "rows": ROW_COUNT,
    }:
        raise C2K1LearnerPreparationError("sidecar counts are not the fixed 12x28 coverage")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != ROW_COUNT:
        raise C2K1LearnerPreparationError(f"sidecar must contain exactly {ROW_COUNT} rows")

    expected_order = [
        f"{key}:{action}"
        for key in anchor_map
        for action in range(NUM_ACTIONS)
    ]
    observed_keys: list[str] = []
    anchor_states: dict[str, tuple[np.ndarray, np.ndarray, str, str]] = {}
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise C2K1LearnerPreparationError(f"sidecar row {index} is malformed")
        _reject_forbidden_keys(raw, field=f"sidecar row {index}")
        unknown_row = set(raw) - _ROW_FIELDS
        if unknown_row:
            if unknown_row & _FORBIDDEN_FIELDS:
                raise C2K1LearnerPreparationError(
                    f"sidecar row {index} contains forbidden target/outcome fields"
                )
            raise C2K1LearnerPreparationError(
                f"sidecar row {index} has unknown fields: {sorted(unknown_row)}"
            )
        missing = _ROW_FIELDS - set(raw)
        if missing:
            raise C2K1LearnerPreparationError(
                f"sidecar row {index} is missing fields: {sorted(missing)}"
            )
        key = raw.get("anchor_key")
        if not isinstance(key, str) or key not in anchor_map:
            raise C2K1LearnerPreparationError(f"sidecar row {index} has an unknown anchor")
        anchor = anchor_map[key]
        action = _exact_int(raw.get("action"), field=f"sidecar row {index}.action")
        if action >= NUM_ACTIONS:
            raise C2K1LearnerPreparationError(f"sidecar row {index}.action is outside action space")
        row_key = raw.get("row_key")
        if row_key != f"{key}:{action}":
            raise C2K1LearnerPreparationError(f"sidecar row {index} row_key is not anchor/action keyed")
        observed_keys.append(row_key)
        for field in ("pool", "world_id", "step", "focal_user", "reference_action"):
            if raw.get(field) != anchor[field]:
                raise C2K1LearnerPreparationError(
                    f"sidecar row {index} {field} disagrees with PREPARE anchor"
                )
        if raw.get("state_schema") != EE_AXIS_STATE_SCHEMA or raw.get("state_schema_sha256") != EE_AXIS_STATE_SCHEMA_SHA256:
            raise C2K1LearnerPreparationError(f"sidecar row {index} state schema drifted")
        state = _state_array(raw.get("state"), field=f"sidecar row {index}.state")
        mask = _mask_array(raw.get("action_mask"), field=f"sidecar row {index}.action_mask")
        expected_mask = np.asarray(anchor["legal_action_mask"], dtype=np.bool_)
        if not np.array_equal(mask, expected_mask):
            raise C2K1LearnerPreparationError(f"sidecar row {index} action_mask disagrees with PREPARE")
        if raw.get("anchor_sha256") != anchor["anchor_sha256"] or raw.get("world_anchor_sha256") != anchor["world_anchor_sha256"]:
            raise C2K1LearnerPreparationError(f"sidecar row {index} anchor digest drifted")
        if raw.get("checkpoint_sha256") != anchor["checkpoint_sha256"] or raw.get("policy_sha256") != anchor["policy_sha256"]:
            raise C2K1LearnerPreparationError(f"sidecar row {index} frozen policy authority drifted")
        for field in _AUTHORITY_FIELDS:
            if raw.get(field) != authorities[field]:
                raise C2K1LearnerPreparationError(f"sidecar row {index} {field} drifted")
        state_digest = _digest(raw.get("state_sha256"), field=f"sidecar row {index}.state_sha256")
        mask_digest = _digest(raw.get("mask_sha256"), field=f"sidecar row {index}.mask_sha256")
        if state_digest != _state_hash(state, mask):
            raise C2K1LearnerPreparationError(f"sidecar row {index} state_sha256 disagrees with arrays")
        if mask_digest != _mask_hash(mask):
            raise C2K1LearnerPreparationError(f"sidecar row {index} mask_sha256 disagrees with array")
        provenance = _digest(raw.get("provenance_sha256"), field=f"sidecar row {index}.provenance_sha256")
        if provenance != _canonical_sha256(_row_provenance(raw)):
            raise C2K1LearnerPreparationError(f"sidecar row {index} provenance digest disagrees")
        previous = anchor_states.get(key)
        current = (state, mask, state_digest, mask_digest)
        if previous is None:
            anchor_states[key] = current
        elif (
            not np.array_equal(previous[0], state)
            or not np.array_equal(previous[1], mask)
            or previous[2:] != current[2:]
        ):
            raise C2K1LearnerPreparationError(
                f"sidecar anchor {key} is not deterministic across actions"
            )

    if observed_keys != expected_order:
        raise C2K1LearnerPreparationError("sidecar rows are not canonical 12-world/action coverage")
    if set(anchor_states) != set(anchor_map):
        raise C2K1LearnerPreparationError("sidecar does not cover exactly 12 PREPARE worlds")
    return sidecar_digest


def check_postgate_learner_plan(
    plan: Mapping[str, Any],
    *,
    formal_verdict: object,
) -> dict[str, Any]:
    """Fail closed unless the exact T1 verdict authorises one bounded screen.

    This checker intentionally accepts no learner hyperparameters, update
    ladder, model choice, seed, or result.  Those choices remain a separate
    post-gate contract and cannot be outcome-selected here.
    """

    if formal_verdict != FORMAL_LEARNER_VERDICT:
        raise C2K1LearnerPreparationError(
            "post-gate learner screen is refused until the exact formal verdict is present"
        )
    if not isinstance(plan, Mapping):
        raise C2K1LearnerPreparationError("learner plan must be a mapping")
    _reject_forbidden_keys(plan, field="learner plan")
    allowed = {
        "schema",
        "formal_verdict",
        "scope",
        "q1_q3_frozen",
        "q2_only_updates",
        "source_sidecar_schema",
        "fresh_heldout_evaluation_required",
        "test_split_opened",
        "training_started",
        "hyperparameters_bound",
        "no_9000ep",
    }
    unknown = set(plan) - allowed
    if unknown:
        raise C2K1LearnerPreparationError(
            f"learner plan contains uncontracted choices or fields: {sorted(unknown)}"
        )
    required = allowed - set(plan)
    if required:
        raise C2K1LearnerPreparationError(
            f"learner plan is missing fields: {sorted(required)}"
        )
    expected = {
        "schema": LEARNER_PLAN_SCHEMA,
        "formal_verdict": FORMAL_LEARNER_VERDICT,
        "scope": LEARNER_SCOPE,
        "q1_q3_frozen": True,
        "q2_only_updates": True,
        "source_sidecar_schema": STATE_SIDECAR_SCHEMA,
        "fresh_heldout_evaluation_required": True,
        "test_split_opened": False,
        "training_started": False,
        "hyperparameters_bound": False,
        "no_9000ep": True,
    }
    if dict(plan) != expected:
        raise C2K1LearnerPreparationError(
            "learner plan does not match the bounded, not-yet-launched contract"
        )
    return {
        "schema": LEARNER_PLAN_SCHEMA,
        "formal_verdict": FORMAL_LEARNER_VERDICT,
        "scope": LEARNER_SCOPE,
        "accepted": True,
        "training_started": False,
        "hyperparameters_bound": False,
        "test_split_opened": False,
    }


__all__ = [
    "C2K1LearnerPreparationError",
    "FORMAL_LEARNER_VERDICT",
    "LEARNER_PLAN_SCHEMA",
    "LEARNER_SCOPE",
    "PREPARE_LIVE_SCHEMA",
    "ROW_COUNT",
    "STATE_SIDECAR_SCHEMA",
    "STATE_SIDECAR_SOURCE_RULE",
    "WORLD_COUNT",
    "build_state_sidecar",
    "check_postgate_learner_plan",
    "verify_state_sidecar",
]
