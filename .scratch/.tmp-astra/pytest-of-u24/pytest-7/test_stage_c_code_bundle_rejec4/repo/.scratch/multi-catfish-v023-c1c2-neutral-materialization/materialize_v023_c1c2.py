#!/usr/bin/env python3
"""Materialize V0.23 C1/C2 source pairs from a sealed predecision capture.

This is a source-only seam.  It consumes a canonical, TRAIN-only JSON capture
whose two route views came from one predecision candidate pool, invokes the
existing pure C1 selector and C1/C2 neutral samplers, and writes four typed
source selections plus a receipt.  It deliberately does not import the
simulator, open an episode, evaluate a branch, fit a learner, or inspect an
outcome.

The current checkout does not contain the required V0.23 C1/C2 predecision
capture.  Consequently this module is plumbing for the next source-stage
capture, not a conversion of the old V0.20/E1 target-bearing artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS, SlotTable  # noqa: E402
from mcrl.runtime.ee_axis_c1_selector import (  # noqa: E402
    C1_ACRM_PAIR_RULE,
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_DULL_ROLLOUT_KIND,
    C1_INFORMED_SOURCE_RULE,
    C1DullRolloutRecord,
    C1FrontierConfig,
    C1SourceSelection,
    C1UnilateralOpportunity,
    sample_c1_cluster_matched_neutral_source,
    select_c1_source,
)
from mcrl.runtime.ee_axis_c2_neutral_source import (  # noqa: E402
    C2_HORIZON_STEPS,
    C2_INFORMED_SOURCE_RULE,
    C2_NEUTRAL_SOURCE_RULE,
    C2_POLICY_VERSION,
    C2PhysicalAlternative,
    C2PredecisionAnchor,
    C2PredecisionOpportunity,
    build_c2_predecision_universe,
    sample_c2_neutral_source,
)
from mcrl.runtime.ee_axis_state import (  # noqa: E402
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-capture-v2"
OUTPUT_SCHEMA = "multi-catfish-mcrl-v023-c1-c2-materialization-v2"
SELECTION_SCHEMA = "multi-catfish-mcrl-v023-c1-c2-selection-v2"
C2_ANCHOR_SCHEMA = "multi-catfish-mcrl-v023-c2-authenticated-anchor-v1"
C2_ANCHOR_FIELDS = (
    "world_id",
    "source_seed",
    "source_manifest_sha256",
    "checkpoint_sha256",
    "state_schema",
    "state_schema_sha256",
    "state_sha256",
    "observation_sha256",
    "step_index",
    "focal_user",
    "reference_action",
    "reference_physical_key",
    "incumbent_physical_key",
    "candidate_sinr",
    "slot_table",
    "legal_alternatives",
    "horizon_steps",
    "release_grammar",
)
CLAIM_CEILING = (
    "TRAIN_PREDECISION_SOURCE_ONLY_NO_SIMULATOR_NO_LEARNER_NO_EPISODE_EE"
)
TRAIN_SPLIT = "TRAIN"

# The source rule may be emitted by the live C2 backend as one of these two
# concrete predecision rules, or as the current aggregate rule used by the
# typed C2 source contract.  None of them is an outcome or a target.
C2_INFORMED_ROW_RULES = frozenset(
    {
        C2_INFORMED_SOURCE_RULE,
        "incumbent-hold",
        "max-lagged-candidate-sinr-rival",
    }
)

_MISSING = object()
_HEX = frozenset("0123456789abcdef")
_FORBIDDEN_KEYS = frozenset(
    {
        "test",
        "test_id",
        "test_ids",
        "test_split",
        "test_split_opened",
        "test_world",
        "test_worlds",
        "episode",
        "episodes",
        "episode_id",
        "episode_count",
        "episode_training",
        "physical_episode",
        "outcome",
        "outcomes",
        "target",
        "targets",
        "reward",
        "rewards",
        "rate",
        "rates",
        "power",
        "energy",
        "bits",
        "ee",
        "metric",
        "metrics",
        "head_drop",
        "alias",
        "aliases",
        "source_alias",
        "source_aliases",
    }
)


class MaterializationError(ValueError):
    """A predecision capture cannot be admitted or materialized."""


def _jsonable(value: object) -> object:
    """Convert only finite, JSON-safe values for canonical receipts."""

    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise MaterializationError("canonical mappings require string keys")
            result[key] = _jsonable(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(child) for child in value]
    if isinstance(value, (bool, str, int)) or value is None:
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        converted = float(value)
        if not math.isfinite(converted):
            raise MaterializationError("canonical JSON cannot contain non-finite floats")
        return converted
    raise MaterializationError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise MaterializationError("value is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise MaterializationError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _duplicate_rejector(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise MaterializationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_canonical_json(path: Path) -> dict[str, object]:
    """Read one canonical ASCII JSON object and reject duplicate keys."""

    if path.is_symlink() or not path.is_file():
        raise MaterializationError(f"capture must be a regular file: {path}")
    try:
        raw = path.read_bytes()
        text = raw.decode("ascii")
        value = json.loads(text, object_pairs_hook=_duplicate_rejector)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MaterializationError(f"capture is not valid ASCII JSON: {path}") from error
    if not isinstance(value, dict):
        raise MaterializationError("capture root must be a JSON object")
    # Source receipts are immutable canonical bytes.  Accept exactly one final
    # newline, which is what the repository's write-once receipt writers emit.
    expected = canonical_bytes(value) + b"\n"
    if raw != expected:
        raise MaterializationError(
            "capture must use canonical compact ASCII JSON with one final newline"
        )
    return value


def _reject_forbidden_tree(value: object, *, field: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise MaterializationError(f"{field} contains a non-string key")
            if key.strip().lower() in _FORBIDDEN_KEYS:
                raise MaterializationError(f"{field} contains forbidden field {key}")
            _reject_forbidden_tree(child, field=f"{field}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            _reject_forbidden_tree(child, field=f"{field}[{index}]")


def _mapping(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise MaterializationError(f"{field} must be an object")
    return dict(value)


def _exact_keys(value: Mapping[str, object], expected: set[str], *, field: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise MaterializationError(
            f"{field} keys disagree: missing={missing}, extra={extra}"
        )


def c2_anchor_body(payload: Mapping[str, object]) -> dict[str, object]:
    """Return the one canonical body shared by the capture bridge and verifier."""

    value = _mapping(payload, field="c2 authenticated anchor digest input")
    actual = set(value)
    expected = set(C2_ANCHOR_FIELDS)
    if "anchor_sha256" in actual:
        expected.add("anchor_sha256")
    _exact_keys(value, expected, field="c2 authenticated anchor digest input")
    return {
        "schema": C2_ANCHOR_SCHEMA,
        **{name: value[name] for name in C2_ANCHOR_FIELDS},
    }


def c2_anchor_sha256(payload: Mapping[str, object]) -> str:
    """Digest one canonical authenticated C2 anchor without trusting its label."""

    return canonical_sha256(c2_anchor_body(payload))


def c1_anchor_sha256(payload: Mapping[str, object]) -> str:
    """Recompute the C1 dull-source anchor identity from retained inputs."""

    value = _mapping(payload, field="c1 authenticated anchor digest input")
    required = {
        "source_seed",
        "step_index",
        "state_sha256",
        "reference_actions",
        "slot_tables",
    }
    missing = sorted(required - set(value))
    if missing:
        raise MaterializationError(f"c1 anchor digest input is missing {missing}")
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v03-c1-anchor-v1",
            "source_seed": value["source_seed"],
            "step_index": value["step_index"],
            "state_observation_sha256": value["state_sha256"],
            "reference_actions": value["reference_actions"],
            "slot_tables": value["slot_tables"],
        }
    )


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise MaterializationError(f"{field} must be a non-empty trimmed string")
    return value


def _digest(value: object, *, field: str) -> str:
    result = _text(value, field=field)
    if len(result) != 64 or result != result.lower() or any(c not in _HEX for c in result):
        raise MaterializationError(f"{field} must be a lowercase SHA-256 digest")
    return result


def _int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise MaterializationError(f"{field} must be an exact integer >= {minimum}")
    return value


def _float(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MaterializationError(f"{field} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise MaterializationError(f"{field} must be finite")
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise MaterializationError(f"{field} must be a non-empty JSON array")
    return list(value)


def _int_list(
    value: object,
    *,
    field: str,
    length: int | None = None,
    minimum: int = 0,
) -> list[int]:
    values = _list(value, field=field)
    result = [
        _int(item, field=f"{field}[{index}]", minimum=minimum)
        for index, item in enumerate(values)
    ]
    if length is not None and len(result) != length:
        raise MaterializationError(f"{field} must contain exactly {length} entries")
    return result


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise MaterializationError(f"{field} must be a two-integer array")
    return (
        _int(value[0], field=f"{field}[0]"),
        _int(value[1], field=f"{field}[1]"),
    )


def _float_list(
    value: object,
    *,
    field: str,
    length: int | None = None,
    minimum: float | None = None,
) -> list[float]:
    values = _list(value, field=field)
    result = [
        _float(item, field=f"{field}[{index}]")
        for index, item in enumerate(values)
    ]
    if length is not None and len(result) != length:
        raise MaterializationError(f"{field} must contain exactly {length} entries")
    if minimum is not None and any(item < minimum for item in result):
        raise MaterializationError(f"{field} entries must be >= {minimum}")
    return result


def _slot_table(value: object, *, field: str) -> SlotTable:
    payload = _mapping(value, field=field)
    _exact_keys(payload, {"norad_ids", "cell_ids", "mask"}, field=field)
    norads = _int_list(
        payload["norad_ids"],
        field=f"{field}.norad_ids",
        length=28,
        minimum=-1,
    )
    cells = _int_list(
        payload["cell_ids"],
        field=f"{field}.cell_ids",
        length=28,
        minimum=-1,
    )
    raw_mask = _list(payload["mask"], field=f"{field}.mask")
    if len(raw_mask) != len(norads) or any(type(item) is not bool for item in raw_mask):
        raise MaterializationError(f"{field}.mask must be Boolean and match identities")
    try:
        return SlotTable(
            np.asarray(norads, dtype=np.int64),
            np.asarray(cells, dtype=np.int64),
            np.asarray(raw_mask, dtype=np.bool_),
        )
    except Exception as error:  # pragma: no cover - defensive runtime contract
        raise MaterializationError(f"{field} is not a valid slot table") from error


def _provenance(value: object) -> dict[str, str]:
    payload = _mapping(value, field="provenance")
    _exact_keys(
        payload,
        {"source_manifest_sha256", "checkpoint_sha256", "state_schema", "state_schema_sha256"},
        field="provenance",
    )
    result = {
        "source_manifest_sha256": _digest(
            payload["source_manifest_sha256"], field="provenance.source_manifest_sha256"
        ),
        "checkpoint_sha256": _digest(
            payload["checkpoint_sha256"], field="provenance.checkpoint_sha256"
        ),
        "state_schema": _text(payload["state_schema"], field="provenance.state_schema"),
        "state_schema_sha256": _digest(
            payload["state_schema_sha256"], field="provenance.state_schema_sha256"
        ),
    }
    if result["state_schema"] != EE_AXIS_STATE_SCHEMA:
        raise MaterializationError("provenance.state_schema is not current V0.3")
    if result["state_schema_sha256"] != EE_AXIS_STATE_SCHEMA_SHA256:
        raise MaterializationError("provenance.state_schema_sha256 is not current")
    return result


def _c1_record(
    value: object,
    *,
    provenance: Mapping[str, str],
) -> C1DullRolloutRecord:
    payload = _mapping(value, field="c1.records[]")
    expected = {
        "record_id",
        "anchor_sha256",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "state_schema",
        "state_schema_sha256",
        "state_sha256",
        "source_seed",
        "step_index",
        "partition",
        "rollout_kind",
        "policy_name",
        "frontier_score",
        "user_frontier_scores",
        "reference_actions",
        "slot_tables",
    }
    _exact_keys(payload, expected, field="c1.records[]")
    source_manifest = _digest(payload["source_manifest_sha256"], field="c1 record source manifest")
    checkpoint = _digest(payload["checkpoint_sha256"], field="c1 record checkpoint")
    state_schema = _text(payload["state_schema"], field="c1 record state schema")
    state_schema_sha256 = _digest(
        payload["state_schema_sha256"], field="c1 record state schema digest"
    )
    state_sha256 = _digest(payload["state_sha256"], field="c1 record state digest")
    for name, actual in (
        ("source_manifest_sha256", source_manifest),
        ("checkpoint_sha256", checkpoint),
        ("state_schema", state_schema),
        ("state_schema_sha256", state_schema_sha256),
    ):
        if actual != provenance[name]:
            raise MaterializationError(f"c1 record {name} disagrees with capture provenance")
    if payload["partition"] != TRAIN_SPLIT:
        raise MaterializationError("C1 predecision records must be TRAIN-only")
    if payload["rollout_kind"] != C1_DULL_ROLLOUT_KIND:
        raise MaterializationError("C1 records must be dull-rollout records")
    user_scores = np.asarray(
        [_float(item, field="c1 record user_frontier_scores[]") for item in _list(payload["user_frontier_scores"], field="c1 record user_frontier_scores")],
        dtype=np.float64,
    )
    reference_actions = np.asarray(
        _int_list(
            payload["reference_actions"],
            field="c1 record reference_actions",
            minimum=int(NO_OP_ACTION),
        ),
        dtype=np.int64,
    )
    tables_raw = _list(payload["slot_tables"], field="c1 record slot_tables")
    tables = tuple(
        _slot_table(item, field=f"c1 record slot_tables[{index}]")
        for index, item in enumerate(tables_raw)
    )
    if len(tables) != user_scores.size or reference_actions.size != user_scores.size:
        raise MaterializationError(
            "C1 user scores, reference actions, and slot tables must have equal user count"
        )
    if c1_anchor_sha256(payload) != payload["anchor_sha256"]:
        raise MaterializationError("C1 authenticated anchor digest mismatch")
    try:
        record = C1DullRolloutRecord(
            record_id=_text(payload["record_id"], field="c1 record record_id"),
            anchor_sha256=_digest(payload["anchor_sha256"], field="c1 record anchor"),
            source_manifest_sha256=source_manifest,
            checkpoint_sha256=checkpoint,
            state_schema=state_schema,
            state_schema_sha256=state_schema_sha256,
            source_seed=_int(payload["source_seed"], field="c1 record source_seed"),
            step_index=_int(payload["step_index"], field="c1 record step_index"),
            partition=TRAIN_SPLIT,
            rollout_kind=C1_DULL_ROLLOUT_KIND,
            policy_name=_text(payload["policy_name"], field="c1 record policy_name"),
            frontier_score=_float(payload["frontier_score"], field="c1 record frontier_score"),
            user_frontier_scores=user_scores,
            reference_actions=reference_actions,
            slot_tables=tables,
        )
        record.verify()
    except Exception as error:
        if isinstance(error, MaterializationError):
            raise
        raise MaterializationError("C1 dull-rollout record failed typed verification") from error
    return record


@dataclass(frozen=True)
class AuthenticatedC2Anchor:
    """One live C2 anchor with enough predecision evidence to verify its rule."""

    anchor: C2PredecisionAnchor
    world_id: int
    source_seed: int
    source_manifest_sha256: str
    checkpoint_sha256: str
    state_schema: str
    state_schema_sha256: str
    state_sha256: str
    observation_sha256: str
    incumbent_physical_key: tuple[int, int]
    candidate_sinr: np.ndarray
    slot_table: SlotTable

    def __post_init__(self) -> None:
        values = np.array(self.candidate_sinr, dtype=np.float64, copy=True)
        if values.shape != (NUM_ACTIONS,) or not np.all(np.isfinite(values)):
            raise MaterializationError("C2 candidate_sinr must be finite shape (28,)")
        if np.any(values < 0.0):
            raise MaterializationError("C2 candidate_sinr must be nonnegative")
        values.setflags(write=False)
        object.__setattr__(self, "candidate_sinr", values)

    def verify(self, *, provenance: Mapping[str, str]) -> None:
        self.anchor.verify()
        for name in (
            "source_manifest_sha256",
            "checkpoint_sha256",
            "state_schema_sha256",
            "state_sha256",
            "observation_sha256",
        ):
            _digest(getattr(self, name), field=f"C2 authenticated anchor {name}")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise MaterializationError("C2 authenticated anchor state schema drifted")
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise MaterializationError("C2 authenticated anchor state schema digest drifted")
        for name in (
            "source_manifest_sha256",
            "checkpoint_sha256",
            "state_schema",
            "state_schema_sha256",
        ):
            if getattr(self, name) != provenance[name]:
                raise MaterializationError(f"C2 authenticated anchor {name} drifted")
        _int(self.world_id, field="C2 authenticated anchor world_id")
        _int(self.source_seed, field="C2 authenticated anchor source_seed")
        if _slot_physical_key(
            self.slot_table,
            self.anchor.reference_action,
            field="C2 authenticated anchor reference_action",
        ) != self.anchor.reference_physical_key:
            raise MaterializationError("C2 authenticated anchor slot binding drifted")
        self.expected_informed()

    def expected_informed(self) -> tuple[C2PhysicalAlternative, str]:
        """Recompute hold-or-best-rival from only sealed predecision values."""

        alternatives = tuple(self.anchor.legal_alternatives)
        incumbent = [
            row for row in alternatives
            if row.physical_key == self.incumbent_physical_key
        ]
        if incumbent:
            if len(incumbent) != 1:
                raise MaterializationError("C2 incumbent physical key is aliased")
            return incumbent[0], "incumbent-hold"
        ordered = sorted(
            alternatives,
            key=lambda row: (
                -float(self.candidate_sinr[row.action]),
                row.physical_key[0],
                row.physical_key[1],
                row.action,
            ),
        )
        if not ordered:
            raise MaterializationError("C2 anchor has no finite legal rival")
        return ordered[0], "max-lagged-candidate-sinr-rival"


def _slot_physical_key(table: SlotTable, action: int, *, field: str) -> tuple[int, int]:
    if action < 0 or action >= NUM_ACTIONS or not bool(table.mask[action]):
        raise MaterializationError(f"{field} is not legal under the sealed slot table")
    key = (int(table.norad_ids[action]), int(table.cell_ids[action]))
    if key[0] < 0 or key[1] < 0:
        raise MaterializationError(f"{field} has no physical identity")
    return key


def _c2_anchor(
    value: object,
    *,
    provenance: Mapping[str, str],
) -> AuthenticatedC2Anchor:
    payload = _mapping(value, field="c2.anchors[]")
    expected = {
        "anchor_sha256",
        "world_id",
        "source_seed",
        "source_manifest_sha256",
        "checkpoint_sha256",
        "state_schema",
        "state_schema_sha256",
        "state_sha256",
        "observation_sha256",
        "step_index",
        "focal_user",
        "reference_action",
        "reference_physical_key",
        "incumbent_physical_key",
        "candidate_sinr",
        "slot_table",
        "legal_alternatives",
        "horizon_steps",
        "release_grammar",
    }
    _exact_keys(payload, expected, field="c2.anchors[]")
    source_manifest = _digest(
        payload["source_manifest_sha256"], field="c2 anchor source manifest"
    )
    checkpoint = _digest(payload["checkpoint_sha256"], field="c2 anchor checkpoint")
    state_schema = _text(payload["state_schema"], field="c2 anchor state schema")
    state_schema_sha256 = _digest(
        payload["state_schema_sha256"], field="c2 anchor state schema digest"
    )
    for name, actual in (
        ("source_manifest_sha256", source_manifest),
        ("checkpoint_sha256", checkpoint),
        ("state_schema", state_schema),
        ("state_schema_sha256", state_schema_sha256),
    ):
        if actual != provenance[name]:
            raise MaterializationError(f"c2 anchor {name} disagrees with capture provenance")
    state_sha256 = _digest(payload["state_sha256"], field="c2 anchor state digest")
    observation_sha256 = _digest(
        payload["observation_sha256"], field="c2 anchor observation digest"
    )
    world_id = _int(payload["world_id"], field="c2 anchor world_id")
    source_seed = _int(payload["source_seed"], field="c2 anchor source_seed")
    step_index = _int(payload["step_index"], field="c2 anchor step_index")
    focal_user = _int(payload["focal_user"], field="c2 anchor focal_user")
    reference_action = _int(payload["reference_action"], field="c2 anchor reference_action")
    reference_physical_key = _physical_key(
        payload["reference_physical_key"], field="c2 anchor reference_physical_key"
    )
    incumbent_physical_key = _physical_key(
        payload["incumbent_physical_key"], field="c2 anchor incumbent_physical_key"
    )
    if incumbent_physical_key == reference_physical_key:
        raise MaterializationError("C2 source anchor is not a physical departure")
    slot_payload = _mapping(payload["slot_table"], field="c2 anchor slot_table")
    slot_table = _slot_table(slot_payload, field="c2 anchor slot_table")
    if _slot_physical_key(
        slot_table, reference_action, field="c2 anchor reference_action"
    ) != reference_physical_key:
        raise MaterializationError("C2 reference physical key disagrees with slot table")
    candidate_sinr = np.asarray(
        _float_list(
            payload["candidate_sinr"],
            field="c2 anchor candidate_sinr",
            length=NUM_ACTIONS,
            minimum=0.0,
        ),
        dtype=np.float64,
    )
    alternatives_raw = _list(payload["legal_alternatives"], field="c2 anchor legal_alternatives")
    horizon_steps = _int(payload["horizon_steps"], field="c2 anchor horizon_steps", minimum=1)
    release_grammar = _text(payload["release_grammar"], field="c2 anchor release_grammar")
    if horizon_steps != C2_HORIZON_STEPS or release_grammar != C2_POLICY_VERSION:
        raise MaterializationError("C2 anchor horizon or release grammar drifted")
    alternatives: list[C2PhysicalAlternative] = []
    for index, raw in enumerate(alternatives_raw):
        child = _mapping(raw, field=f"c2 anchor legal_alternatives[{index}]")
        _exact_keys(child, {"action", "physical_key"}, field=f"c2 anchor legal_alternatives[{index}]")
        try:
            row = C2PhysicalAlternative(
                action=_int(child["action"], field=f"c2 alternative[{index}].action"),
                physical_key=_physical_key(child["physical_key"], field=f"c2 alternative[{index}].physical_key"),
            )
            row.verify()
        except Exception as error:
            if isinstance(error, MaterializationError):
                raise
            raise MaterializationError("C2 physical alternative failed verification") from error
        alternatives.append(row)
    try:
        supplied_anchor_sha256 = _digest(
            payload["anchor_sha256"], field="c2 anchor digest"
        )
        expected_by_key: dict[tuple[int, int], list[C2PhysicalAlternative]] = {}
        for action in np.flatnonzero(np.asarray(slot_table.mask, dtype=np.bool_)).tolist():
            action = int(action)
            key = _slot_physical_key(slot_table, action, field=f"c2 anchor legal_action[{action}]")
            if action == reference_action or key == reference_physical_key:
                continue
            expected_by_key.setdefault(key, []).append(
                C2PhysicalAlternative(action=action, physical_key=key)
            )
        aliases = {
            key: rows for key, rows in expected_by_key.items() if len(rows) != 1
        }
        if aliases:
            raise MaterializationError("C2 contemporaneous slot table contains a physical alias")
        expected_alternatives = tuple(
            sorted(
                (rows[0] for rows in expected_by_key.values()),
                key=lambda row: (row.physical_key, row.action),
            )
        )
        if tuple(alternatives) != expected_alternatives:
            raise MaterializationError(
                "C2 legal alternatives disagree with contemporaneous slot table"
            )
        normalized_anchor_payload = {
            "world_id": world_id,
            "source_seed": source_seed,
            "source_manifest_sha256": source_manifest,
            "checkpoint_sha256": checkpoint,
            "state_schema": state_schema,
            "state_schema_sha256": state_schema_sha256,
            "state_sha256": state_sha256,
            "observation_sha256": observation_sha256,
            "step_index": step_index,
            "focal_user": focal_user,
            "reference_action": reference_action,
            "reference_physical_key": list(reference_physical_key),
            "incumbent_physical_key": list(incumbent_physical_key),
            "candidate_sinr": [float(item) for item in candidate_sinr.tolist()],
            "slot_table": {
                "norad_ids": [int(item) for item in slot_table.norad_ids.tolist()],
                "cell_ids": [int(item) for item in slot_table.cell_ids.tolist()],
                "mask": [bool(item) for item in slot_table.mask.tolist()],
            },
            "legal_alternatives": [
                {"action": row.action, "physical_key": list(row.physical_key)}
                for row in alternatives
            ],
            "horizon_steps": horizon_steps,
            "release_grammar": release_grammar,
        }
        if c2_anchor_sha256(normalized_anchor_payload) != supplied_anchor_sha256:
            raise MaterializationError("C2 authenticated anchor digest mismatch")
        anchor = C2PredecisionAnchor(
            anchor_sha256=supplied_anchor_sha256,
            step_index=step_index,
            focal_user=focal_user,
            reference_action=reference_action,
            reference_physical_key=reference_physical_key,
            legal_alternatives=tuple(alternatives),
            horizon_steps=horizon_steps,
            release_grammar=release_grammar,
        )
        anchor.verify()
    except Exception as error:
        if isinstance(error, MaterializationError):
            raise
        raise MaterializationError("C2 predecision anchor failed typed verification") from error
    return AuthenticatedC2Anchor(
        anchor=anchor,
        world_id=world_id,
        source_seed=source_seed,
        source_manifest_sha256=source_manifest,
        checkpoint_sha256=checkpoint,
        state_schema=state_schema,
        state_schema_sha256=state_schema_sha256,
        state_sha256=state_sha256,
        observation_sha256=observation_sha256,
        incumbent_physical_key=incumbent_physical_key,
        candidate_sinr=candidate_sinr,
        slot_table=slot_table,
    )


def _c2_informed_row(
    value: object,
    *,
    anchors_by_key: Mapping[tuple[str, int], AuthenticatedC2Anchor],
) -> C2PredecisionOpportunity:
    payload = _mapping(value, field="c2.informed[]")
    expected = {
        "anchor_sha256",
        "step_index",
        "focal_user",
        "reference_action",
        "reference_physical_key",
        "candidate_action",
        "candidate_physical_key",
        "source_rule",
    }
    _exact_keys(payload, expected, field="c2.informed[]")
    source_rule = _text(payload["source_rule"], field="c2 informed source_rule")
    if source_rule not in C2_INFORMED_ROW_RULES:
        raise MaterializationError(f"unsupported C2 informed source rule: {source_rule}")
    anchor_digest = _digest(payload["anchor_sha256"], field="c2 informed anchor")
    focal_user = _int(payload["focal_user"], field="c2 informed focal_user")
    authenticated = anchors_by_key.get((anchor_digest, focal_user))
    if authenticated is None:
        raise MaterializationError("C2 informed row is outside the sealed anchor pool")
    anchor = authenticated.anchor
    reference_key = _physical_key(
        payload["reference_physical_key"], field="c2 informed reference_physical_key"
    )
    candidate_key = _physical_key(
        payload["candidate_physical_key"], field="c2 informed candidate_physical_key"
    )
    candidate_action = _int(payload["candidate_action"], field="c2 informed candidate_action")
    reference_action = _int(payload["reference_action"], field="c2 informed reference_action")
    if (
        reference_action != anchor.reference_action
        or reference_key != anchor.reference_physical_key
        or _int(payload["step_index"], field="c2 informed step_index") != anchor.step_index
    ):
        raise MaterializationError("C2 informed row disagrees with its anchor")
    allowed = {
        (alternative.action, alternative.physical_key)
        for alternative in anchor.legal_alternatives
    }
    if (candidate_action, candidate_key) not in allowed:
        raise MaterializationError("C2 informed candidate is not a legal anchor alternative")
    expected_candidate, expected_rule = authenticated.expected_informed()
    if source_rule != expected_rule:
        raise MaterializationError(
            f"C2 informed source rule is not authenticated: expected {expected_rule}"
        )
    if (
        candidate_action != expected_candidate.action
        or candidate_key != expected_candidate.physical_key
    ):
        raise MaterializationError(
            "C2 informed candidate is not the deterministic hold-or-best-rival choice"
        )
    row = C2PredecisionOpportunity(
        anchor_sha256=anchor.anchor_sha256,
        step_index=anchor.step_index,
        focal_user=anchor.focal_user,
        reference_action=anchor.reference_action,
        reference_physical_key=anchor.reference_physical_key,
        candidate_action=candidate_action,
        candidate_physical_key=candidate_key,
        horizon_steps=anchor.horizon_steps,
        release_grammar=anchor.release_grammar,
        source_rule=source_rule,
    )
    try:
        row.verify()
    except Exception as error:
        raise MaterializationError("C2 informed opportunity failed verification") from error
    return row


def _frontier_config(value: object) -> C1FrontierConfig:
    payload = _mapping(value, field="c1.frontier_config")
    allowed = {
        "lower_anchor_fraction",
        "lower_user_fraction",
        "max_anchors",
        "max_focal_users_per_anchor",
    }
    if set(payload) - allowed:
        raise MaterializationError(
            f"c1.frontier_config has unsupported keys: {sorted(set(payload) - allowed)}"
        )
    kwargs: dict[str, object] = {}
    for field in allowed:
        if field in payload:
            raw = payload[field]
            if field.startswith("lower_"):
                kwargs[field] = _float(raw, field=f"c1.frontier_config.{field}")
            elif raw is not None:
                kwargs[field] = _int(raw, field=f"c1.frontier_config.{field}", minimum=1)
            else:
                kwargs[field] = None
    try:
        config = C1FrontierConfig(**kwargs)  # type: ignore[arg-type]
        config.verify()
    except Exception as error:
        raise MaterializationError("C1 frontier configuration failed verification") from error
    return config


def _pool_payload(payload: Mapping[str, object]) -> dict[str, object]:
    c1 = _mapping(payload.get("c1", _MISSING), field="c1")
    c2 = _mapping(payload.get("c2", _MISSING), field="c2")
    return {
        "pool_id": payload.get("pool_id", _MISSING),
        "provenance": payload.get("provenance", _MISSING),
        "c1_frontier_config": c1.get("frontier_config", _MISSING),
        "c1_neutral_seed": c1.get("neutral_seed", _MISSING),
        "c1_records": c1.get("records", _MISSING),
        "c2_neutral_seed": c2.get("neutral_seed", _MISSING),
        "c2_anchors": c2.get("anchors", _MISSING),
        "c2_informed": c2.get("informed", _MISSING),
    }


def _check_pool(payload: Mapping[str, object]) -> tuple[str, str]:
    pool_id = _text(payload.get("pool_id", _MISSING), field="pool_id")
    supplied = _digest(payload.get("pool_sha256", _MISSING), field="pool_sha256")
    raw_pool = _pool_payload(payload)
    if _MISSING in raw_pool.values():
        raise MaterializationError("capture pool fields are incomplete")
    actual = canonical_sha256(raw_pool)
    if supplied != actual:
        raise MaterializationError(
            f"pool_sha256 mismatch: expected capture {supplied}, recomputed {actual}"
        )
    return pool_id, supplied


@dataclass(frozen=True)
class C2InformedMaterialization:
    """Outcome-blind C2 informed rows accepted from the live source rule."""

    pool_id: str
    pool_sha256: str
    provenance: Mapping[str, str]
    anchors: tuple[AuthenticatedC2Anchor, ...]
    all_opportunities: tuple[C2PredecisionOpportunity, ...]
    opportunities: tuple[C2PredecisionOpportunity, ...]

    @property
    def route(self) -> str:
        return "C2"

    @property
    def source_rule(self) -> str:
        return C2_INFORMED_SOURCE_RULE

    @property
    def budget(self) -> int:
        return len(self.opportunities)

    def verify(self) -> None:
        _digest(self.pool_sha256, field="C2 materialization pool_sha256")
        if not self.pool_id:
            raise MaterializationError("C2 materialization pool_id is empty")
        checked_provenance = _provenance(self.provenance)
        if not self.anchors:
            raise MaterializationError("C2 informed materialization has no anchors")
        anchor_keys: set[tuple[str, int]] = set()
        for authenticated in self.anchors:
            if not isinstance(authenticated, AuthenticatedC2Anchor):
                raise MaterializationError("C2 anchors are not authenticated")
            authenticated.verify(provenance=checked_provenance)
            key = (authenticated.anchor.anchor_sha256, authenticated.anchor.focal_user)
            if key in anchor_keys:
                raise MaterializationError("C2 authenticated anchors contain duplicates")
            anchor_keys.add(key)
        if not self.all_opportunities or not self.opportunities:
            raise MaterializationError("C2 informed materialization must have positive budget")
        all_keys = {row.opportunity_key for row in self.all_opportunities}
        if len(all_keys) != len(self.all_opportunities):
            raise MaterializationError("C2 materialization universe contains duplicates")
        selected_keys: set[tuple[str, int, tuple[int, int]]] = set()
        for row in self.all_opportunities:
            row.verify()
            if row.source_rule != C2_NEUTRAL_SOURCE_RULE:
                raise MaterializationError("C2 materialization universe must be neutral-tagged")
            if (row.anchor_sha256, row.focal_user) not in anchor_keys:
                raise MaterializationError("C2 universe row has no authenticated anchor")
        for row in self.opportunities:
            row.verify()
            if row.source_rule not in C2_INFORMED_ROW_RULES:
                raise MaterializationError("C2 informed row has unsupported source rule")
            if row.opportunity_key not in all_keys:
                raise MaterializationError("C2 informed row is outside universe")
            if row.opportunity_key in selected_keys:
                raise MaterializationError("C2 informed materialization has duplicate rows")
            selected_keys.add(row.opportunity_key)


@dataclass(frozen=True)
class ValidatedCapture:
    """Typed predecision rows admitted before any panel-level selection.

    A per-world capture may be authenticated independently, but C1 frontier
    selection and both neutral draws are defined over the merged frozen panel.
    Keeping this value separate from :class:`MaterializedBundle` prevents a
    world writer from accidentally sampling a panel-level control arm.
    """

    pool_id: str
    pool_sha256: str
    provenance: Mapping[str, str]
    c1_records: tuple[C1DullRolloutRecord, ...]
    c1_config: C1FrontierConfig
    c1_neutral_seed: int
    c2_anchors: tuple[AuthenticatedC2Anchor, ...]
    c2_universe: tuple[C2PredecisionOpportunity, ...]
    c2_informed_rows: tuple[C2PredecisionOpportunity, ...]
    c2_neutral_seed: int


@dataclass(frozen=True)
class MaterializedBundle:
    """Four source selections from one immutable predecision capture."""

    pool_id: str
    pool_sha256: str
    provenance: Mapping[str, str]
    c1_informed: C1SourceSelection
    c1_neutral: C1SourceSelection
    c2_informed: C2InformedMaterialization
    c2_neutral: Any  # C2SourceSelection; kept Any to avoid a second protocol type.

    def verify(self) -> None:
        self.c1_informed.verify()
        self.c1_neutral.verify()
        self.c2_informed.verify()
        self.c2_neutral.verify()
        if self.c1_informed.source_rule != C1_INFORMED_SOURCE_RULE:
            raise MaterializationError("C1 informed source rule drifted")
        if self.c1_neutral.source_rule != C1_CLUSTER_NEUTRAL_SOURCE_RULE:
            raise MaterializationError("C1 neutral source rule drifted")
        if self.c2_neutral.source_rule != C2_NEUTRAL_SOURCE_RULE:
            raise MaterializationError("C2 neutral source rule drifted")
        if self.c1_informed.budget != self.c1_neutral.budget:
            raise MaterializationError("C1 informed/neutral row budgets disagree")
        if self.c2_informed.budget != self.c2_neutral.budget:
            raise MaterializationError("C2 informed/neutral row budgets disagree")


def _c1_opportunity_payload(row: C1UnilateralOpportunity) -> dict[str, object]:
    return {
        "anchor_sha256": row.anchor_sha256,
        "source_record_sha256": row.source_record_sha256,
        "source_manifest_sha256": row.source_manifest_sha256,
        "checkpoint_sha256": row.checkpoint_sha256,
        "state_schema": row.state_schema,
        "state_schema_sha256": row.state_schema_sha256,
        "step_index": row.step_index,
        "source_rule": row.source_rule,
        "acrm_pair_rule": row.acrm_pair_rule,
        "anchor_rank": row.anchor_rank,
        "anchor_stratum": row.anchor_stratum,
        "focal_user": row.focal_user,
        "user_rank": row.user_rank,
        "user_stratum": row.user_stratum,
        "reference_action": row.reference_action,
        "candidate_action": row.candidate_action,
        "reference_physical_key": None
        if row.reference_physical_key is None
        else [row.reference_physical_key[0], row.reference_physical_key[1]],
        "candidate_physical_key": [row.candidate_physical_key[0], row.candidate_physical_key[1]],
        "reference_actions": [int(value) for value in row.reference_actions.tolist()],
        "candidate_actions": [int(value) for value in row.candidate_actions.tolist()],
        "action_mask": [bool(value) for value in row.action_mask.tolist()],
    }


def _c1_selection_payload(
    selection: C1SourceSelection,
    *,
    pool_id: str,
    pool_sha256: str,
) -> dict[str, object]:
    selection.verify()
    return {
        "schema": SELECTION_SCHEMA,
        "route": "C1",
        "pool_id": pool_id,
        "pool_sha256": pool_sha256,
        "selector_schema": selection.selector_schema,
        "source_rule": selection.source_rule,
        "acrm_pair_rule": selection.acrm_pair_rule,
        "partition": selection.partition,
        "source_manifest_sha256": selection.source_manifest_sha256,
        "checkpoint_sha256": selection.checkpoint_sha256,
        "state_schema": selection.state_schema,
        "state_schema_sha256": selection.state_schema_sha256,
        "eligible_anchor_sha256s": list(selection.eligible_anchor_sha256s),
        "selected_anchor_sha256s": list(selection.selected_anchor_sha256s),
        "eligible_focal_users": [list(value) for value in selection.eligible_focal_users],
        "selected_focal_users": [list(value) for value in selection.selected_focal_users],
        "all_opportunities": [_c1_opportunity_payload(row) for row in selection.all_opportunities],
        "opportunities": [_c1_opportunity_payload(row) for row in selection.opportunities],
        "row_budget": selection.budget,
        "selection_digest": canonical_sha256(
            {
                "pool_sha256": pool_sha256,
                "route": "C1",
                "source_rule": selection.source_rule,
                "opportunity_keys": [row.opportunity_key for row in selection.opportunities],
            }
        ),
    }


def _c2_opportunity_payload(row: C2PredecisionOpportunity) -> dict[str, object]:
    return {
        "anchor_sha256": row.anchor_sha256,
        "step_index": row.step_index,
        "focal_user": row.focal_user,
        "reference_action": row.reference_action,
        "reference_physical_key": [row.reference_physical_key[0], row.reference_physical_key[1]],
        "candidate_action": row.candidate_action,
        "candidate_physical_key": [row.candidate_physical_key[0], row.candidate_physical_key[1]],
        "horizon_steps": row.horizon_steps,
        "release_grammar": row.release_grammar,
        "source_rule": row.source_rule,
    }


def _c2_anchor_payload(value: AuthenticatedC2Anchor) -> dict[str, object]:
    value.verify(
        provenance={
            "source_manifest_sha256": value.source_manifest_sha256,
            "checkpoint_sha256": value.checkpoint_sha256,
            "state_schema": value.state_schema,
            "state_schema_sha256": value.state_schema_sha256,
        }
    )
    table = value.slot_table
    return {
        "anchor_sha256": value.anchor.anchor_sha256,
        "world_id": value.world_id,
        "source_seed": value.source_seed,
        "source_manifest_sha256": value.source_manifest_sha256,
        "checkpoint_sha256": value.checkpoint_sha256,
        "state_schema": value.state_schema,
        "state_schema_sha256": value.state_schema_sha256,
        "state_sha256": value.state_sha256,
        "observation_sha256": value.observation_sha256,
        "step_index": value.anchor.step_index,
        "focal_user": value.anchor.focal_user,
        "reference_action": value.anchor.reference_action,
        "reference_physical_key": list(value.anchor.reference_physical_key),
        "incumbent_physical_key": list(value.incumbent_physical_key),
        "candidate_sinr": [float(item) for item in value.candidate_sinr.tolist()],
        "slot_table": {
            "norad_ids": [int(item) for item in table.norad_ids.tolist()],
            "cell_ids": [int(item) for item in table.cell_ids.tolist()],
            "mask": [bool(item) for item in table.mask.tolist()],
        },
        "legal_alternatives": [
            {"action": row.action, "physical_key": list(row.physical_key)}
            for row in value.anchor.legal_alternatives
        ],
        "horizon_steps": value.anchor.horizon_steps,
        "release_grammar": value.anchor.release_grammar,
    }


def _c2_selection_payload(
    selection: Any,
    *,
    pool_id: str,
    pool_sha256: str,
    provenance: Mapping[str, str],
    anchors: Sequence[AuthenticatedC2Anchor],
    informed: bool,
) -> dict[str, object]:
    selection.verify()
    opportunities = tuple(selection.opportunities)
    universe = tuple(selection.all_opportunities)
    return {
        "schema": SELECTION_SCHEMA,
        "route": "C2",
        "pool_id": pool_id,
        "pool_sha256": pool_sha256,
        "provenance": dict(provenance),
        "anchors": [_c2_anchor_payload(row) for row in anchors],
        "selector_schema": selection.selector_schema,
        "source_rule": C2_INFORMED_SOURCE_RULE if informed else selection.source_rule,
        "release_grammar": C2_POLICY_VERSION,
        "horizon_steps": C2_HORIZON_STEPS,
        "informed_budget": len(opportunities) if informed else selection.informed_budget,
        "all_opportunities": [_c2_opportunity_payload(row) for row in universe],
        "opportunities": [_c2_opportunity_payload(row) for row in opportunities],
        "row_budget": len(opportunities),
        "selection_digest": canonical_sha256(
            {
                "pool_sha256": pool_sha256,
                "route": "C2",
                "source_rule": C2_INFORMED_SOURCE_RULE if informed else selection.source_rule,
                "opportunity_keys": [row.opportunity_key for row in opportunities],
            }
        ),
    }


def _c2_informed_payload(
    selection: C2InformedMaterialization,
) -> dict[str, object]:
    selection.verify()
    return {
        "schema": SELECTION_SCHEMA,
        "route": "C2",
        "pool_id": selection.pool_id,
        "pool_sha256": selection.pool_sha256,
        "provenance": dict(selection.provenance),
        "anchors": [_c2_anchor_payload(row) for row in selection.anchors],
        "selector_schema": "multi-catfish-mcrl-v03-c2-predecision-selector-v1",
        "source_rule": C2_INFORMED_SOURCE_RULE,
        "release_grammar": C2_POLICY_VERSION,
        "horizon_steps": C2_HORIZON_STEPS,
        "informed_budget": selection.budget,
        "all_opportunities": [_c2_opportunity_payload(row) for row in selection.all_opportunities],
        "opportunities": [_c2_opportunity_payload(row) for row in selection.opportunities],
        "row_budget": selection.budget,
        "selection_digest": canonical_sha256(
            {
                "pool_sha256": selection.pool_sha256,
                "route": "C2",
                "source_rule": C2_INFORMED_SOURCE_RULE,
                "opportunity_keys": [row.opportunity_key for row in selection.opportunities],
            }
        ),
    }


def _c1_cluster_match_audit(
    informed: C1SourceSelection,
    neutral: C1SourceSelection,
) -> dict[str, object]:
    """Summarize the sealed C1 cluster match without outcome information.

    Multiple informed anchors can have the same profile, so the concrete
    augmenting-path ownership is not scientifically identifiable from the two
    emitted selections.  The receipt therefore records a canonical
    profile-equivalent pairing (sorted within an exact profile), not a claim
    about the matcher's internal traversal.  Every reported quantity is
    derived only from the predecision opportunity universe.
    """

    informed.verify()
    neutral.verify()
    if informed.source_rule != C1_INFORMED_SOURCE_RULE:
        raise MaterializationError("C1 cluster audit requires the informed source")
    if neutral.source_rule != C1_CLUSTER_NEUTRAL_SOURCE_RULE:
        raise MaterializationError("C1 cluster audit requires the matched neutral source")

    counts_by_user: dict[tuple[str, int], int] = {}
    for row in informed.all_opportunities:
        key = (row.anchor_sha256, row.focal_user)
        counts_by_user[key] = counts_by_user.get(key, 0) + 1

    def selected_profiles(
        selection: C1SourceSelection,
    ) -> dict[str, tuple[int, ...]]:
        users_by_anchor: dict[str, list[int]] = {}
        for anchor, user in selection.selected_focal_users:
            try:
                count = counts_by_user[(anchor, user)]
            except KeyError as error:
                raise MaterializationError(
                    "C1 selected user is absent from the common opportunity universe"
                ) from error
            users_by_anchor.setdefault(anchor, []).append(count)
        profiles = {
            anchor: tuple(sorted(counts))
            for anchor, counts in users_by_anchor.items()
        }
        if set(profiles) != set(selection.selected_anchor_sha256s):
            raise MaterializationError(
                "C1 selected anchors and profile-bearing users disagree"
            )
        return profiles

    informed_profiles = selected_profiles(informed)
    neutral_profiles = selected_profiles(neutral)
    informed_multiset = sorted(informed_profiles.values())
    neutral_multiset = sorted(neutral_profiles.values())
    if informed_multiset != neutral_multiset:
        raise MaterializationError(
            "C1 neutral profile multiset does not exactly match informed"
        )

    available_by_anchor: dict[str, dict[int, int]] = {}
    for (anchor, _user), alternative_count in counts_by_user.items():
        histogram = available_by_anchor.setdefault(anchor, {})
        histogram[alternative_count] = histogram.get(alternative_count, 0) + 1

    def histogram(profile: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
        result: dict[int, int] = {}
        for alternative_count in profile:
            result[alternative_count] = result.get(alternative_count, 0) + 1
        return tuple(sorted(result.items()))

    def feasible_count(profile: tuple[int, ...]) -> int:
        required = histogram(profile)
        return sum(
            all(available.get(size, 0) >= count for size, count in required)
            for available in available_by_anchor.values()
        )

    informed_by_profile: dict[tuple[int, ...], list[str]] = {}
    neutral_by_profile: dict[tuple[int, ...], list[str]] = {}
    for anchor, profile in informed_profiles.items():
        informed_by_profile.setdefault(profile, []).append(anchor)
    for anchor, profile in neutral_profiles.items():
        neutral_by_profile.setdefault(profile, []).append(anchor)

    pairings: list[dict[str, object]] = []
    for profile in sorted(informed_by_profile):
        informed_anchors = sorted(informed_by_profile[profile])
        neutral_anchors = sorted(neutral_by_profile.get(profile, ()))
        if len(informed_anchors) != len(neutral_anchors):
            raise MaterializationError("C1 profile group cardinality drifted")
        profile_histogram = [
            {
                "alternative_count": size,
                "focal_user_count": count,
            }
            for size, count in histogram(profile)
        ]
        degree = feasible_count(profile)
        for informed_anchor, neutral_anchor in zip(
            informed_anchors, neutral_anchors, strict=True
        ):
            pairings.append(
                {
                    "informed_anchor_sha256": informed_anchor,
                    "neutral_anchor_sha256": neutral_anchor,
                    "alternative_count_histogram": profile_histogram,
                    "feasible_neutral_anchor_count": degree,
                }
            )

    overlap = tuple(
        sorted(set(informed.selected_anchor_sha256s) & set(neutral.selected_anchor_sha256s))
    )
    return {
        "schema": "multi-catfish-mcrl-v023-c1-cluster-match-audit-v1",
        "matching_rule": C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        "pairing_semantics": "canonical-profile-equivalent-not-internal-traversal",
        "predecision_only": True,
        "uniform_over_all_feasible_matchings_claimed": False,
        "informed_anchor_count": len(informed.selected_anchor_sha256s),
        "neutral_anchor_count": len(neutral.selected_anchor_sha256s),
        "informed_focal_user_count": len(informed.selected_focal_users),
        "neutral_focal_user_count": len(neutral.selected_focal_users),
        "informed_row_count": informed.budget,
        "neutral_row_count": neutral.budget,
        "exact_profile_multiset": True,
        "anchor_overlap_count": len(overlap),
        "anchor_overlap_sha256s": list(overlap),
        "canonical_profile_pairing": pairings,
    }


def validate_capture(payload: Mapping[str, object]) -> ValidatedCapture:
    """Authenticate capture rows without selecting or sampling source arms."""

    if not isinstance(payload, Mapping):
        raise MaterializationError("capture must be a mapping")
    _reject_forbidden_tree(payload, field="capture")
    _exact_keys(
        payload,
        {"schema", "split", "pool_id", "pool_sha256", "provenance", "c1", "c2"},
        field="capture",
    )
    if payload.get("schema") != SCHEMA:
        raise MaterializationError("capture schema is not V0.23 predecision capture")
    if payload.get("split") != TRAIN_SPLIT:
        raise MaterializationError("capture split must be exactly TRAIN")
    pool_id, pool_sha256 = _check_pool(payload)
    provenance = _provenance(payload.get("provenance", _MISSING))

    c1_payload = _mapping(payload.get("c1", _MISSING), field="c1")
    _exact_keys(
        c1_payload,
        {"frontier_config", "neutral_seed", "records"},
        field="c1",
    )
    c1_records_raw = _list(c1_payload.get("records", _MISSING), field="c1.records")
    c1_records = tuple(_c1_record(item, provenance=provenance) for item in c1_records_raw)
    if not c1_records:
        raise MaterializationError("C1 predecision capture must contain records")
    config = _frontier_config(c1_payload.get("frontier_config"))
    c1_neutral_seed = _int(c1_payload.get("neutral_seed", _MISSING), field="c1.neutral_seed")

    c2_payload = _mapping(payload.get("c2", _MISSING), field="c2")
    _exact_keys(c2_payload, {"neutral_seed", "anchors", "informed"}, field="c2")
    anchors_raw = _list(c2_payload.get("anchors", _MISSING), field="c2.anchors")
    authenticated_anchors = tuple(
        _c2_anchor(item, provenance=provenance) for item in anchors_raw
    )
    if not authenticated_anchors:
        raise MaterializationError("C2 predecision capture must contain anchors")
    for authenticated in authenticated_anchors:
        authenticated.verify(provenance=provenance)
    anchors = tuple(item.anchor for item in authenticated_anchors)
    if len({(anchor.anchor_sha256, anchor.focal_user) for anchor in anchors}) != len(anchors):
        raise MaterializationError("C2 anchor/focal-user identities must be unique")
    universe = build_c2_predecision_universe(anchors)
    anchors_by_key = {
        (item.anchor.anchor_sha256, item.anchor.focal_user): item
        for item in authenticated_anchors
    }
    informed_c2_rows_raw = _list(c2_payload.get("informed", _MISSING), field="c2.informed")
    informed_c2_rows = tuple(
        _c2_informed_row(item, anchors_by_key=anchors_by_key)
        for item in informed_c2_rows_raw
    )
    if not informed_c2_rows:
        raise MaterializationError("C2 predecision capture must contain informed rows")
    informed_keys = [row.opportunity_key for row in informed_c2_rows]
    if len(set(informed_keys)) != len(informed_keys):
        raise MaterializationError("C2 informed rows must not repeat a physical opportunity")
    all_keys = {row.opportunity_key for row in universe}
    if not set(informed_keys).issubset(all_keys):
        raise MaterializationError("C2 informed rows are outside the common candidate pool")
    c2_neutral_seed = _int(c2_payload.get("neutral_seed", _MISSING), field="c2.neutral_seed")

    return ValidatedCapture(
        pool_id=pool_id,
        pool_sha256=pool_sha256,
        provenance=dict(provenance),
        c1_records=c1_records,
        c1_config=config,
        c1_neutral_seed=c1_neutral_seed,
        c2_anchors=authenticated_anchors,
        c2_universe=tuple(universe),
        c2_informed_rows=informed_c2_rows,
        c2_neutral_seed=c2_neutral_seed,
    )


def materialize_capture(payload: Mapping[str, object]) -> MaterializedBundle:
    """Materialize source arms once the complete frozen panel is assembled.

    The C2 informed rows are supplied by the source-stage C2 grammar.  This
    function authenticates them against the anchor pool; it does not invent a
    C2 candidate from a target, an outcome, or a downstream trace.
    """

    capture = validate_capture(payload)
    informed_c1 = select_c1_source(capture.c1_records, config=capture.c1_config)
    if informed_c1 is None:
        raise MaterializationError("C1 source selector found no eligible predecision rows")
    neutral_c1 = sample_c1_cluster_matched_neutral_source(
        informed_c1,
        rng=np.random.default_rng(capture.c1_neutral_seed),
    )
    neutral_c2 = sample_c2_neutral_source(
        capture.c2_universe,
        informed_budget=len(capture.c2_informed_rows),
        rng=np.random.default_rng(capture.c2_neutral_seed),
        random_seed=capture.c2_neutral_seed,
    )
    informed_c2 = C2InformedMaterialization(
        pool_id=capture.pool_id,
        pool_sha256=capture.pool_sha256,
        provenance=dict(capture.provenance),
        anchors=capture.c2_anchors,
        all_opportunities=capture.c2_universe,
        opportunities=capture.c2_informed_rows,
    )
    bundle = MaterializedBundle(
        pool_id=capture.pool_id,
        pool_sha256=capture.pool_sha256,
        provenance=dict(capture.provenance),
        c1_informed=informed_c1,
        c1_neutral=neutral_c1,
        c2_informed=informed_c2,
        c2_neutral=neutral_c2,
    )
    bundle.verify()
    return bundle


def _write_once(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise MaterializationError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with path.open("xb") as handle:
        handle.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def write_materialization(bundle: MaterializedBundle, output_dir: Path) -> dict[str, object]:
    """Write immutable route selections and a manifest; refuse overwrites."""

    bundle.verify()
    if output_dir.exists() or output_dir.is_symlink():
        raise MaterializationError(f"refusing to overwrite output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    files: dict[str, str] = {}
    route_payloads = {
        "c1-informed.json": _c1_selection_payload(
            bundle.c1_informed, pool_id=bundle.pool_id, pool_sha256=bundle.pool_sha256
        ),
        "c1-neutral.json": _c1_selection_payload(
            bundle.c1_neutral, pool_id=bundle.pool_id, pool_sha256=bundle.pool_sha256
        ),
        "c2-informed.json": _c2_informed_payload(bundle.c2_informed),
        "c2-neutral.json": _c2_selection_payload(
            bundle.c2_neutral,
            pool_id=bundle.pool_id,
            pool_sha256=bundle.pool_sha256,
            provenance=bundle.provenance,
            anchors=bundle.c2_informed.anchors,
            informed=False,
        ),
    }
    for name in sorted(route_payloads):
        files[name] = _write_once(output_dir / name, route_payloads[name])
    receipt = {
        "schema": OUTPUT_SCHEMA,
        "status": "MATERIALIZED_TRAIN_PREDECISION_ONLY",
        "claim_ceiling": CLAIM_CEILING,
        "split": TRAIN_SPLIT,
        "pool_id": bundle.pool_id,
        "pool_sha256": bundle.pool_sha256,
        "provenance": dict(bundle.provenance),
        "route_budgets": {
            "C1_informed": bundle.c1_informed.budget,
            "C1_neutral": bundle.c1_neutral.budget,
            "C2_informed": bundle.c2_informed.budget,
            "C2_neutral": bundle.c2_neutral.budget,
        },
        "route_rules": {
            "C1_informed": C1_INFORMED_SOURCE_RULE,
            "C1_neutral": C1_CLUSTER_NEUTRAL_SOURCE_RULE,
            "C2_informed": C2_INFORMED_SOURCE_RULE,
            "C2_neutral": C2_NEUTRAL_SOURCE_RULE,
        },
        "c1_cluster_match_audit": _c1_cluster_match_audit(
            bundle.c1_informed,
            bundle.c1_neutral,
        ),
        "files": files,
        "controls": {
            "simulator_run": False,
            "learner_update": False,
            "episode_training": False,
            "test_split_opened": False,
            "outcome_tuning": False,
            "head_drop": False,
            "source_alias": False,
            "shared_route_learner_budget_assumed": False,
        },
    }
    receipt_hash = _write_once(output_dir / "receipt.json", receipt)
    files["receipt.json"] = receipt_hash
    manifest_lines = [f"{files[name]}  {name}" for name in sorted(files)]
    manifest_path = output_dir / "MANIFEST.sha256"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise MaterializationError(f"refusing to overwrite manifest: {manifest_path}")
    with manifest_path.open("xb") as handle:
        handle.write(("\n".join(manifest_lines) + "\n").encode("ascii"))
    return {
        "schema": OUTPUT_SCHEMA,
        "receipt": str((output_dir / "receipt.json").resolve()),
        "receipt_sha256": receipt_hash,
        "manifest": str(manifest_path.resolve()),
        "manifest_entries": len(files),
        "route_budgets": receipt["route_budgets"],
        "claim_ceiling": CLAIM_CEILING,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "materialized-source",
        help="new output directory; existing directories are never overwritten",
    )
    args = parser.parse_args(argv)
    try:
        payload = read_canonical_json(args.capture)
        bundle = materialize_capture(payload)
        report = write_materialization(bundle, args.output)
    except (MaterializationError, OSError) as error:
        print(f"MATERIALIZATION_BLOCKED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


__all__ = [
    "CLAIM_CEILING",
    "C2InformedMaterialization",
    "MaterializationError",
    "MaterializedBundle",
    "OUTPUT_SCHEMA",
    "SCHEMA",
    "canonical_bytes",
    "canonical_sha256",
    "_c1_cluster_match_audit",
    "file_sha256",
    "main",
    "materialize_capture",
    "read_canonical_json",
    "validate_capture",
    "ValidatedCapture",
    "write_materialization",
]


if __name__ == "__main__":
    raise SystemExit(main())
