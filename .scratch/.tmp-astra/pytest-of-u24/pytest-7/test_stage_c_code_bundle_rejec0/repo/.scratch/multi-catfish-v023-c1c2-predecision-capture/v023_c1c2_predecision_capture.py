#!/usr/bin/env python3
"""TRAIN-only V0.23 C1/C2 predecision capture bridge.

This module is the narrow source-stage bridge between the authenticated V0.23
Q1/Q2 environment path and the V2 C1/C2 materializer.  Its pure helpers only
read a contemporaneous reference action, previous physical association, slot
table, and candidate-SINR vector.  They never evaluate a candidate, inspect a
target/outcome, update a learner, or open TEST.

The runtime ``capture_world`` function is intentionally lazy: simulator and
source-adapter imports happen only after a caller explicitly invokes it.  A
server wrapper can therefore import this module's deterministic contract
without opening a simulator.  The runtime walks the same ten-slot TRAIN
trajectory as the authenticated source adapter, captures C1 at every current
anchor, and captures C2 only when frozen Main physically departs the previous
served association.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcrl.env.action_contract import Association, NO_OP_ACTION, NUM_ACTIONS, SlotTable  # noqa: E402
from mcrl.runtime.ee_axis_c1_selector import (  # noqa: E402
    C1_ACRM_PAIR_RULE,
    C1_DULL_ROLLOUT_KIND,
    C1_INFORMED_SOURCE_RULE,
    C1DullRolloutRecord,
    C1FrontierConfig,
)
from mcrl.runtime.ee_axis_c2_neutral_source import (  # noqa: E402
    C2_HORIZON_STEPS,
    C2_INFORMED_SOURCE_RULE,
    C2_NEUTRAL_SOURCE_RULE,
    C2_POLICY_VERSION,
)
from mcrl.runtime.ee_axis_state import (  # noqa: E402
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-capture-v2"
C2_ANCHOR_SCHEMA = "multi-catfish-mcrl-v023-c2-authenticated-anchor-v1"
TRAIN_SPLIT = "TRAIN"
CLAIM_CEILING = (
    "TRAIN_PREDECISION_SIMULATOR_SOURCE_ONLY_NO_LEARNER_NO_TEST_NO_EFFICACY"
)

# Deliberately route-local defaults.  They are source-selection RNG seeds,
# not learner seeds, and are derived solely from the declared world identity.
# Callers may provide explicit values in a frozen launch contract.
C1_NEUTRAL_SEED_OFFSET = 17
C2_NEUTRAL_SEED_OFFSET = 31
C1_FRONTIER_CONFIG = {
    "lower_anchor_fraction": 0.5,
    "lower_user_fraction": 0.5,
    "max_anchors": None,
    "max_focal_users_per_anchor": None,
}
STEPS_PER_EPISODE = 10
FROZEN_WORLDS = tuple(range(2026121705, 2026121713))
PANEL_POOL_ID = "v023-train-panel-2026121705-2026121712-predecision"


class CaptureBridgeError(ValueError):
    """A predecision capture is malformed or violates the source boundary."""


def _jsonable(value: object) -> object:
    """Convert finite NumPy/Python values to canonical JSON values."""

    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise CaptureBridgeError("canonical mappings require string keys")
            result[key] = _jsonable(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(child) for child in value]
    if isinstance(value, (bool, str, int)) or value is None:
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        converted = float(value)
        if not math.isfinite(converted):
            raise CaptureBridgeError("canonical JSON cannot contain non-finite floats")
        return converted
    raise CaptureBridgeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """Return the compact ASCII JSON representation used by V0.23 receipts."""

    try:
        return json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise CaptureBridgeError("value is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise CaptureBridgeError(f"expected a regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CaptureBridgeError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CaptureBridgeError(f"{field} must be a non-empty trimmed string")
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CaptureBridgeError(f"{field} must be an exact integer >= {minimum}")
    return value


def _finite(value: object, *, field: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise CaptureBridgeError(f"{field} must be finite")
    converted = float(value)
    if not math.isfinite(converted) or (
        minimum is not None and converted < minimum
    ):
        raise CaptureBridgeError(f"{field} must be finite and >= {minimum}")
    return converted


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CaptureBridgeError(f"{field} must be an object")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], *, field: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise CaptureBridgeError(
            f"{field} keys disagree: missing={missing}, extra={extra}"
        )


def _slot_table_payload(table: SlotTable) -> dict[str, object]:
    if not isinstance(table, SlotTable):
        raise CaptureBridgeError("slot table must be a SlotTable")
    return {
        "norad_ids": [int(value) for value in table.norad_ids.tolist()],
        "cell_ids": [int(value) for value in table.cell_ids.tolist()],
        "mask": [bool(value) for value in table.mask.tolist()],
    }


def _physical_key_from_table(
    table: SlotTable, action: int, *, field: str
) -> tuple[int, int] | None:
    if not isinstance(table, SlotTable):
        raise CaptureBridgeError(f"{field} table must be SlotTable")
    if type(action) is not int:
        raise CaptureBridgeError(f"{field} must be an exact integer action")
    if action == int(NO_OP_ACTION):
        return None
    if not 0 <= action < NUM_ACTIONS or not bool(table.mask[action]):
        raise CaptureBridgeError(f"{field} is not legal under the current slot table")
    norad = int(table.norad_ids[action])
    cell = int(table.cell_ids[action])
    if norad < 0 or cell < 0:
        raise CaptureBridgeError(f"{field} has no physical identity")
    return norad, cell


def _association_key(value: object, *, field: str) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, Association):
        return int(value.norad_id), int(value.cell_id)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        norad = _exact_int(value[0], field=f"{field}[0]")
        cell = _exact_int(value[1], field=f"{field}[1]")
        return norad, cell
    raise CaptureBridgeError(f"{field} must be None, Association, or a two-integer key")


def legal_physical_alternatives(
    table: SlotTable, *, reference_action: int
) -> tuple[dict[str, object], ...]:
    """Enumerate unique legal physical actions other than frozen Main."""

    reference_key = _physical_key_from_table(
        table, reference_action, field="reference_action"
    )
    rows: list[dict[str, object]] = []
    by_key: dict[tuple[int, int], list[int]] = {}
    for action in np.flatnonzero(table.mask).tolist():
        action = int(action)
        key = _physical_key_from_table(table, action, field=f"legal_action[{action}]")
        if key is None or action == reference_action or key == reference_key:
            continue
        by_key.setdefault(key, []).append(action)
    aliases = {key: actions for key, actions in by_key.items() if len(actions) != 1}
    if aliases:
        raise CaptureBridgeError(
            "physical alias in current slot table: "
            + ", ".join(f"{key}<-{actions}" for key, actions in sorted(aliases.items()))
        )
    for key, actions in by_key.items():
        rows.append({"action": int(actions[0]), "physical_key": [int(key[0]), int(key[1])]})
    rows.sort(key=lambda row: (tuple(row["physical_key"]), int(row["action"])))
    if not rows:
        raise CaptureBridgeError(
            "anchor/focal user has no uniquely executable non-reference alternative"
        )
    return tuple(rows)


@dataclass(frozen=True)
class C2Departure:
    """A physical departure eligible for a temporal C2 source anchor."""

    focal_user: int
    reference_action: int
    reference_physical_key: tuple[int, int]
    incumbent_physical_key: tuple[int, int]
    slot_table: SlotTable

    def verify(self) -> None:
        _exact_int(self.focal_user, field="focal_user")
        _exact_int(self.reference_action, field="reference_action")
        if not isinstance(self.slot_table, SlotTable):
            raise CaptureBridgeError("departure slot_table must be SlotTable")
        current = _physical_key_from_table(
            self.slot_table, self.reference_action, field="departure reference_action"
        )
        if current != self.reference_physical_key:
            raise CaptureBridgeError("departure reference physical key drifted")
        if self.reference_physical_key == self.incumbent_physical_key:
            raise CaptureBridgeError("departure keys must differ")
        if any(type(value) is not int or value < 0 for value in self.reference_physical_key):
            raise CaptureBridgeError("reference physical key is malformed")
        if any(type(value) is not int or value < 0 for value in self.incumbent_physical_key):
            raise CaptureBridgeError("incumbent physical key is malformed")


def detect_physical_departures(
    reference_actions: object,
    previous_associations: Sequence[object],
    slot_tables: Sequence[SlotTable],
    *,
    step_index: int,
) -> tuple[C2Departure, ...]:
    """Find served users whose frozen Main action leaves the prior physical key.

    A missing previous association is not a departure.  A frozen NO_OP is not
    a C2 anchor.  Equality is by ``(norad_id, cell_id)``, never by flat action
    index, because candidate-table ordering may change between steps.
    """

    _exact_int(step_index, field="step_index", minimum=1)
    references = np.asarray(reference_actions)
    if references.ndim != 1 or not np.issubdtype(references.dtype, np.integer):
        raise CaptureBridgeError("reference_actions must be an integer vector")
    if len(previous_associations) != references.size or len(slot_tables) != references.size:
        raise CaptureBridgeError("reference, previous-association, and table counts disagree")
    departures: list[C2Departure] = []
    for user, (raw_action, previous, table) in enumerate(
        zip(references.tolist(), previous_associations, slot_tables, strict=True)
    ):
        action = int(raw_action)
        if action == int(NO_OP_ACTION):
            continue
        reference_key = _physical_key_from_table(
            table, action, field=f"reference_actions[{user}]"
        )
        if reference_key is None:
            continue
        incumbent_key = _association_key(previous, field=f"previous_associations[{user}]")
        if incumbent_key is None or incumbent_key == reference_key:
            continue
        departure = C2Departure(
            focal_user=user,
            reference_action=action,
            reference_physical_key=reference_key,
            incumbent_physical_key=incumbent_key,
            slot_table=table,
        )
        departure.verify()
        departures.append(departure)
    return tuple(departures)


def _candidate_sinr_vector(value: object, *, field: str = "candidate_sinr") -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1 or array.shape != (NUM_ACTIONS,):
        raise CaptureBridgeError(f"{field} must have shape ({NUM_ACTIONS},)")
    if not np.issubdtype(array.dtype, np.number):
        raise CaptureBridgeError(f"{field} must be numeric")
    result = np.asarray(array, dtype=np.float64)
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise CaptureBridgeError(f"{field} must be finite and nonnegative")
    return result


def choose_c2_informed_candidate(
    *,
    incumbent_physical_key: tuple[int, int],
    alternatives: Sequence[Mapping[str, object]],
    candidate_sinr: object,
) -> tuple[int, tuple[int, int], str]:
    """Apply the frozen hold-if-legal, otherwise max-lagged-SINR rule."""

    incumbent = tuple(incumbent_physical_key)
    if len(incumbent) != 2 or any(type(value) is not int or value < 0 for value in incumbent):
        raise CaptureBridgeError("incumbent_physical_key is malformed")
    sinr = _candidate_sinr_vector(candidate_sinr)
    parsed: list[tuple[int, tuple[int, int]]] = []
    seen_actions: set[int] = set()
    seen_keys: set[tuple[int, int]] = set()
    for index, raw in enumerate(alternatives):
        payload = _mapping(raw, field=f"alternatives[{index}]")
        _exact_keys(payload, {"action", "physical_key"}, field=f"alternatives[{index}]")
        action = _exact_int(payload["action"], field=f"alternatives[{index}].action")
        if action >= NUM_ACTIONS:
            raise CaptureBridgeError("alternative action is outside the action space")
        key_raw = payload["physical_key"]
        if not isinstance(key_raw, (tuple, list)) or len(key_raw) != 2:
            raise CaptureBridgeError("alternative physical_key is malformed")
        key = (
            _exact_int(key_raw[0], field=f"alternatives[{index}].physical_key[0]"),
            _exact_int(key_raw[1], field=f"alternatives[{index}].physical_key[1]"),
        )
        if action in seen_actions or key in seen_keys:
            raise CaptureBridgeError("alternatives contain a duplicate action or physical key")
        seen_actions.add(action)
        seen_keys.add(key)
        parsed.append((action, key))
    if not parsed:
        raise CaptureBridgeError("C2 departure has no legal physical alternative")
    hold = [row for row in parsed if row[1] == incumbent]
    if hold:
        if len(hold) != 1:
            raise CaptureBridgeError("incumbent physical key is aliased")
        action, key = hold[0]
        return action, key, "incumbent-hold"
    action, key = min(
        parsed,
        key=lambda row: (-float(sinr[row[0]]), row[1][0], row[1][1], row[0]),
    )
    return action, key, "max-lagged-candidate-sinr-rival"


def _load_materializer() -> Any:
    """Load V2 materializer lazily, after the caller crossed source setup."""

    path = REPO / ".scratch" / "multi-catfish-v023-c1c2-neutral-materialization" / "materialize_v023_c1c2.py"
    if path.is_symlink() or not path.is_file():
        raise CaptureBridgeError(f"V2 materializer is missing or symlinked: {path}")
    name = "mcrl_v023_c1c2_materializer_bridge"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CaptureBridgeError("cannot load V2 materializer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def load_materializer() -> Any:
    """Public lazy seam used by compatibility tests and later runners."""

    return _load_materializer()


def c2_anchor_sha256(payload: Mapping[str, object]) -> str:
    """Expose the materializer's canonical V2 anchor digest at this seam."""

    return str(_load_materializer().c2_anchor_sha256(payload))


def build_c2_anchor_payload(
    *,
    world_id: int,
    source_seed: int,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    state_schema: str,
    state_schema_sha256: str,
    state_sha256: str,
    observation_sha256: str,
    step_index: int,
    focal_user: int,
    reference_action: int,
    incumbent_physical_key: tuple[int, int],
    candidate_sinr: object,
    slot_table: SlotTable,
) -> dict[str, object]:
    """Build an authenticated V2 C2 anchor from current predecision values."""

    world = _exact_int(world_id, field="world_id")
    seed = _exact_int(source_seed, field="source_seed")
    source_manifest = _digest(source_manifest_sha256, field="source_manifest_sha256")
    checkpoint = _digest(checkpoint_sha256, field="checkpoint_sha256")
    schema = _text(state_schema, field="state_schema")
    schema_sha = _digest(state_schema_sha256, field="state_schema_sha256")
    state = _digest(state_sha256, field="state_sha256")
    observation = _digest(observation_sha256, field="observation_sha256")
    step = _exact_int(step_index, field="step_index", minimum=1)
    focal = _exact_int(focal_user, field="focal_user")
    action = _exact_int(reference_action, field="reference_action")
    reference_key = _physical_key_from_table(
        slot_table, action, field="reference_action"
    )
    if reference_key is None:
        raise CaptureBridgeError("C2 anchors require a served physical Main reference")
    incumbent = tuple(incumbent_physical_key)
    if len(incumbent) != 2 or any(type(value) is not int or value < 0 for value in incumbent):
        raise CaptureBridgeError("incumbent_physical_key is malformed")
    if reference_key == incumbent:
        raise CaptureBridgeError("C2 anchor is not a physical departure")
    sinr = _candidate_sinr_vector(candidate_sinr)
    alternatives = legal_physical_alternatives(slot_table, reference_action=action)
    payload: dict[str, object] = {
        "world_id": world,
        "source_seed": seed,
        "source_manifest_sha256": source_manifest,
        "checkpoint_sha256": checkpoint,
        "state_schema": schema,
        "state_schema_sha256": schema_sha,
        "state_sha256": state,
        "observation_sha256": observation,
        "step_index": step,
        "focal_user": focal,
        "reference_action": action,
        "reference_physical_key": [int(reference_key[0]), int(reference_key[1])],
        "incumbent_physical_key": [int(incumbent[0]), int(incumbent[1])],
        "candidate_sinr": [float(value) for value in sinr.tolist()],
        "slot_table": _slot_table_payload(slot_table),
        "legal_alternatives": [dict(row) for row in alternatives],
        "horizon_steps": C2_HORIZON_STEPS,
        "release_grammar": C2_POLICY_VERSION,
    }
    payload["anchor_sha256"] = c2_anchor_sha256(payload)
    return {"anchor_sha256": payload.pop("anchor_sha256"), **payload}


def c2_informed_payload(anchor: Mapping[str, object]) -> dict[str, object]:
    """Derive the deterministic informed row from one authenticated anchor."""

    payload = dict(anchor)
    required = {
        "anchor_sha256",
        "step_index",
        "focal_user",
        "reference_action",
        "reference_physical_key",
        "incumbent_physical_key",
        "candidate_sinr",
        "legal_alternatives",
    }
    if not required.issubset(payload):
        raise CaptureBridgeError("C2 anchor lacks fields required for informed selection")
    ref_key_raw = payload["reference_physical_key"]
    inc_key_raw = payload["incumbent_physical_key"]
    if (
        not isinstance(ref_key_raw, list)
        or len(ref_key_raw) != 2
        or any(type(value) is not int or value < 0 for value in ref_key_raw)
        or not isinstance(inc_key_raw, list)
        or len(inc_key_raw) != 2
        or any(type(value) is not int or value < 0 for value in inc_key_raw)
    ):
        raise CaptureBridgeError("C2 anchor physical keys must be arrays")
    action, candidate_key, rule = choose_c2_informed_candidate(
        incumbent_physical_key=(int(inc_key_raw[0]), int(inc_key_raw[1])),
        alternatives=payload["legal_alternatives"],  # type: ignore[arg-type]
        candidate_sinr=payload["candidate_sinr"],
    )
    return {
        "anchor_sha256": _digest(payload["anchor_sha256"], field="anchor_sha256"),
        "step_index": _exact_int(payload["step_index"], field="step_index", minimum=1),
        "focal_user": _exact_int(payload["focal_user"], field="focal_user"),
        "reference_action": _exact_int(payload["reference_action"], field="reference_action"),
        "reference_physical_key": [int(ref_key_raw[0]), int(ref_key_raw[1])],
        "candidate_action": action,
        "candidate_physical_key": [int(candidate_key[0]), int(candidate_key[1])],
        "source_rule": rule,
    }


def c1_record_payload(
    record: C1DullRolloutRecord, *, state_sha256: str
) -> dict[str, object]:
    """Serialize only the source-only fields accepted by materializer V2."""

    if not isinstance(record, C1DullRolloutRecord):
        raise CaptureBridgeError("record must be C1DullRolloutRecord")
    record.verify()
    payload = {
        "record_id": record.record_id,
        "anchor_sha256": record.anchor_sha256,
        "source_manifest_sha256": record.source_manifest_sha256,
        "checkpoint_sha256": record.checkpoint_sha256,
        "state_schema": record.state_schema,
        "state_schema_sha256": record.state_schema_sha256,
        "state_sha256": _digest(state_sha256, field="state_sha256"),
        "source_seed": int(record.source_seed),
        "step_index": int(record.step_index),
        "partition": record.partition,
        "rollout_kind": record.rollout_kind,
        "policy_name": record.policy_name,
        "frontier_score": float(record.frontier_score),
        "user_frontier_scores": [
            float(value) for value in np.asarray(record.user_frontier_scores).tolist()
        ],
        "reference_actions": [
            int(value) for value in np.asarray(record.reference_actions).tolist()
        ],
        "slot_tables": [_slot_table_payload(table) for table in record.slot_tables],
    }
    if _load_materializer().c1_anchor_sha256(payload) != record.anchor_sha256:
        raise CaptureBridgeError("C1 record anchor digest does not match retained state")
    return payload


def _provenance_payload(value: Mapping[str, object]) -> dict[str, str]:
    expected = {
        "source_manifest_sha256",
        "checkpoint_sha256",
        "state_schema",
        "state_schema_sha256",
    }
    _exact_keys(value, expected, field="provenance")
    result = {
        "source_manifest_sha256": _digest(
            value["source_manifest_sha256"], field="provenance.source_manifest_sha256"
        ),
        "checkpoint_sha256": _digest(
            value["checkpoint_sha256"], field="provenance.checkpoint_sha256"
        ),
        "state_schema": _text(value["state_schema"], field="provenance.state_schema"),
        "state_schema_sha256": _digest(
            value["state_schema_sha256"], field="provenance.state_schema_sha256"
        ),
    }
    if result["state_schema"] != EE_AXIS_STATE_SCHEMA:
        raise CaptureBridgeError("provenance state schema is not current V0.3")
    if result["state_schema_sha256"] != EE_AXIS_STATE_SCHEMA_SHA256:
        raise CaptureBridgeError("provenance state schema digest is not current")
    return result


def _forbidden_tree(value: object, *, field: str) -> None:
    forbidden = {
        "test", "test_id", "test_split", "test_world", "test_worlds",
        "episode", "episodes", "episode_training", "physical_episode",
        "outcome", "outcomes", "target", "targets", "reward", "rewards",
        "rate", "rates", "power", "energy", "bits", "ee", "metric", "metrics",
        "head_drop", "alias", "aliases", "source_alias", "source_aliases",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CaptureBridgeError(f"{field} contains a non-string key")
            if key.strip().lower() in forbidden:
                raise CaptureBridgeError(f"{field} contains forbidden field {key}")
            _forbidden_tree(child, field=f"{field}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _forbidden_tree(child, field=f"{field}[{index}]")


def _pool_payload(payload: Mapping[str, object]) -> dict[str, object]:
    c1 = _mapping(payload.get("c1"), field="c1")
    c2 = _mapping(payload.get("c2"), field="c2")
    required = {
        "pool_id", "provenance", "c1_frontier_config", "c1_neutral_seed",
        "c1_records", "c2_neutral_seed", "c2_anchors", "c2_informed",
    }
    result = {
        "pool_id": payload.get("pool_id"),
        "provenance": payload.get("provenance"),
        "c1_frontier_config": c1.get("frontier_config"),
        "c1_neutral_seed": c1.get("neutral_seed"),
        "c1_records": c1.get("records"),
        "c2_neutral_seed": c2.get("neutral_seed"),
        "c2_anchors": c2.get("anchors"),
        "c2_informed": c2.get("informed"),
    }
    if any(result[key] is None for key in required):
        raise CaptureBridgeError("capture pool fields are incomplete")
    return result


def recompute_pool_sha256(payload: Mapping[str, object]) -> str:
    """Recompute the exact V2 pool digest used by the materializer."""

    return canonical_sha256(_pool_payload(payload))


def _normalize_records(records: Iterable[object]) -> tuple[dict[str, object], ...]:
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(records):
        if isinstance(item, C1DullRolloutRecord):
            raise CaptureBridgeError(
                "typed C1 records require an explicit state digest before normalization"
            )
        elif isinstance(item, Mapping):
            payload = dict(item)
            # Validate through the materializer at the final boundary.  Keep
            # this bridge's public payload exact and do not inject fields.
            normalized.append(payload)
        else:
            raise CaptureBridgeError(f"c1_records[{index}] is not a C1 record or mapping")
    if not normalized:
        raise CaptureBridgeError("c1_records must be non-empty")
    return tuple(normalized)


def build_capture_payload(
    *,
    pool_id: str,
    provenance: Mapping[str, object],
    frontier_config: Mapping[str, object],
    c1_neutral_seed: int,
    c1_records: Iterable[object],
    c2_neutral_seed: int,
    c2_anchors: Iterable[Mapping[str, object]],
    c2_informed: Iterable[Mapping[str, object]] | None = None,
    extra_c2_fields: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Assemble one canonical V2 capture and fail closed on forbidden fields."""

    _text(pool_id, field="pool_id")
    checked_provenance = _provenance_payload(provenance)
    frontier = dict(frontier_config)
    allowed_frontier = {
        "lower_anchor_fraction", "lower_user_fraction", "max_anchors",
        "max_focal_users_per_anchor",
    }
    if set(frontier) - allowed_frontier:
        raise CaptureBridgeError("frontier_config contains unsupported fields")
    C1FrontierConfig(
        lower_anchor_fraction=float(frontier.get("lower_anchor_fraction", 0.5)),
        lower_user_fraction=float(frontier.get("lower_user_fraction", 0.5)),
        max_anchors=frontier.get("max_anchors"),  # type: ignore[arg-type]
        max_focal_users_per_anchor=frontier.get("max_focal_users_per_anchor"),  # type: ignore[arg-type]
    ).verify()
    c1_seed = _exact_int(c1_neutral_seed, field="c1_neutral_seed")
    c2_seed = _exact_int(c2_neutral_seed, field="c2_neutral_seed")
    records = _normalize_records(c1_records)
    anchors = tuple(dict(item) for item in c2_anchors)
    if not anchors:
        raise CaptureBridgeError("c2_anchors must be non-empty")
    informed = (
        tuple(dict(item) for item in c2_informed)
        if c2_informed is not None
        else tuple(c2_informed_payload(anchor) for anchor in anchors)
    )
    if not informed:
        raise CaptureBridgeError("c2_informed must be non-empty")
    c2: dict[str, object] = {
        "neutral_seed": c2_seed,
        "anchors": list(anchors),
        "informed": list(informed),
    }
    if extra_c2_fields:
        _forbidden_tree(extra_c2_fields, field="c2")
        c2.update(dict(extra_c2_fields))
    if set(c2) != {"neutral_seed", "anchors", "informed"}:
        raise CaptureBridgeError("c2 contains unsupported or missing fields")
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "split": TRAIN_SPLIT,
        "pool_id": pool_id,
        "pool_sha256": "0" * 64,
        "provenance": checked_provenance,
        "c1": {
            "frontier_config": frontier,
            "neutral_seed": c1_seed,
            "records": list(records),
        },
        "c2": c2,
    }
    _forbidden_tree(payload, field="capture")
    # C2 anchors are authenticated by the shared V2 helper; reject a stale
    # supplied digest before returning the payload.
    materializer = _load_materializer()
    anchor_by_key: dict[tuple[str, int], Mapping[str, object]] = {}
    for index, anchor in enumerate(anchors):
        if materializer.c2_anchor_sha256(anchor) != anchor.get("anchor_sha256"):
            raise CaptureBridgeError(f"c2_anchors[{index}] digest does not authenticate")
        anchor_digest = anchor.get("anchor_sha256")
        focal = anchor.get("focal_user")
        if not isinstance(anchor_digest, str) or type(focal) is not int:
            raise CaptureBridgeError(f"c2_anchors[{index}] identity is malformed")
        key = (anchor_digest, focal)
        if key in anchor_by_key:
            raise CaptureBridgeError("c2 anchors contain duplicate anchor/focal identities")
        anchor_by_key[key] = anchor
    for index, row in enumerate(informed):
        if set(row) != {
            "anchor_sha256", "step_index", "focal_user", "reference_action",
            "reference_physical_key", "candidate_action", "candidate_physical_key",
            "source_rule",
        }:
            raise CaptureBridgeError(f"c2_informed[{index}] has unsupported or missing fields")
        if not isinstance(row["anchor_sha256"], str) or type(row["focal_user"]) is not int:
            raise CaptureBridgeError(f"c2_informed[{index}] identity is malformed")
        anchor_key = (row["anchor_sha256"], row["focal_user"])
        anchor = anchor_by_key.get(anchor_key)  # type: ignore[arg-type]
        if anchor is None or dict(row) != c2_informed_payload(anchor):
            raise CaptureBridgeError(
                f"c2_informed[{index}] is not the deterministic choice for its anchor"
            )
    payload["pool_sha256"] = recompute_pool_sha256(payload)
    return payload


def merge_world_captures(
    captures: Iterable[Mapping[str, object]],
    *,
    c1_neutral_seed: int,
    c2_neutral_seed: int,
) -> dict[str, object]:
    """Merge exactly the eight frozen world captures before source selection.

    C1 lower-frontier selection and both neutral samplers must see the complete
    source panel.  Materializing each world separately would silently change
    that population, so this seam authenticates every write-once world capture
    and then rebuilds one panel-level pool with explicitly predeclared neutral
    seeds.
    """

    materializer = _load_materializer()
    by_world: dict[int, Mapping[str, object]] = {}
    common_provenance: dict[str, str] | None = None
    common_frontier: dict[str, object] | None = None
    for index, raw in enumerate(captures):
        if not isinstance(raw, Mapping):
            raise CaptureBridgeError(f"captures[{index}] must be an object")
        payload = dict(raw)
        if payload.get("schema") != SCHEMA or payload.get("split") != TRAIN_SPLIT:
            raise CaptureBridgeError(f"captures[{index}] is not a TRAIN V2 capture")
        if payload.get("pool_sha256") != recompute_pool_sha256(payload):
            raise CaptureBridgeError(f"captures[{index}] pool digest drifted")
        try:
            materializer.validate_capture(payload)
        except Exception as error:
            raise CaptureBridgeError(
                f"captures[{index}] failed V2 capture validation"
            ) from error
        provenance = _provenance_payload(
            _mapping(payload.get("provenance"), field=f"captures[{index}].provenance")
        )
        c1 = _mapping(payload.get("c1"), field=f"captures[{index}].c1")
        c2 = _mapping(payload.get("c2"), field=f"captures[{index}].c2")
        records = tuple(c1.get("records", ()))
        anchors = tuple(c2.get("anchors", ()))
        informed = tuple(c2.get("informed", ()))
        if not records or not anchors or not informed:
            raise CaptureBridgeError(f"captures[{index}] has an empty source route")
        c1_worlds = {
            _exact_int(
                _mapping(row, field=f"captures[{index}].c1.records[]").get("source_seed"),
                field=f"captures[{index}].c1.records[].source_seed",
            )
            for row in records
        }
        c2_worlds = {
            _exact_int(
                _mapping(row, field=f"captures[{index}].c2.anchors[]").get("world_id"),
                field=f"captures[{index}].c2.anchors[].world_id",
            )
            for row in anchors
        }
        c2_seeds = {
            _exact_int(
                _mapping(row, field=f"captures[{index}].c2.anchors[]").get("source_seed"),
                field=f"captures[{index}].c2.anchors[].source_seed",
            )
            for row in anchors
        }
        if len(c1_worlds) != 1 or c1_worlds != c2_worlds or c2_seeds != c2_worlds:
            raise CaptureBridgeError(
                f"captures[{index}] does not bind one common world/source seed"
            )
        world = next(iter(c2_worlds))
        if world not in FROZEN_WORLDS or world in by_world:
            raise CaptureBridgeError(
                f"captures[{index}] has an unexpected or duplicate frozen world"
            )
        if payload.get("pool_id") != f"v023-train-world-{world}-predecision":
            raise CaptureBridgeError(f"captures[{index}] world pool identity drifted")
        frontier = dict(
            _mapping(c1.get("frontier_config"), field=f"captures[{index}].frontier_config")
        )
        if common_provenance is None:
            common_provenance = provenance
            common_frontier = frontier
        elif provenance != common_provenance or frontier != common_frontier:
            raise CaptureBridgeError(
                "world captures do not share provenance and frontier configuration"
            )
        by_world[world] = payload

    if tuple(sorted(by_world)) != FROZEN_WORLDS:
        missing = sorted(set(FROZEN_WORLDS) - set(by_world))
        extra = sorted(set(by_world) - set(FROZEN_WORLDS))
        raise CaptureBridgeError(
            f"panel must contain exactly the frozen worlds: missing={missing}, extra={extra}"
        )
    if common_provenance is None or common_frontier is None:
        raise CaptureBridgeError("panel capture list is empty")

    records: list[object] = []
    anchors: list[Mapping[str, object]] = []
    informed: list[Mapping[str, object]] = []
    for world in FROZEN_WORLDS:
        payload = by_world[world]
        c1 = _mapping(payload["c1"], field=f"world[{world}].c1")
        c2 = _mapping(payload["c2"], field=f"world[{world}].c2")
        records.extend(tuple(c1["records"]))  # type: ignore[arg-type]
        anchors.extend(tuple(c2["anchors"]))  # type: ignore[arg-type]
        informed.extend(tuple(c2["informed"]))  # type: ignore[arg-type]
    return build_capture_payload(
        pool_id=PANEL_POOL_ID,
        provenance=common_provenance,
        frontier_config=common_frontier,
        c1_neutral_seed=_exact_int(c1_neutral_seed, field="c1_neutral_seed"),
        c1_records=records,
        c2_neutral_seed=_exact_int(c2_neutral_seed, field="c2_neutral_seed"),
        c2_anchors=anchors,
        c2_informed=informed,
    )


def write_capture(payload: Mapping[str, object], output: Path) -> str:
    """Write one canonical capture exactly once and return its file digest."""

    _forbidden_tree(payload, field="capture")
    if payload.get("schema") != SCHEMA or payload.get("split") != TRAIN_SPLIT:
        raise CaptureBridgeError("capture must be V2 and TRAIN-only")
    if payload.get("pool_sha256") != recompute_pool_sha256(payload):
        raise CaptureBridgeError("capture pool_sha256 does not authenticate")
    # Authenticate the one-world predecision rows before creating the
    # write-once file.  Frontier selection and both neutral draws are panel-
    # level operations and therefore must not run until all worlds are merged.
    try:
        _load_materializer().validate_capture(payload)
    except Exception as error:
        raise CaptureBridgeError("capture failed V2 capture validation") from error
    target = Path(output)
    if target.exists() or target.is_symlink():
        raise CaptureBridgeError(f"refusing to overwrite capture: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    try:
        with target.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise CaptureBridgeError(f"refusing to overwrite capture: {target}") from error
    return hashlib.sha256(encoded).hexdigest()


def _default_neutral_seeds(world: int) -> tuple[int, int]:
    value = _exact_int(world, field="world")
    return value + C1_NEUTRAL_SEED_OFFSET, value + C2_NEUTRAL_SEED_OFFSET


def _load_source_adapter() -> Any:
    path = REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "v023_lcsrs_source_adapter.py"
    if path.is_symlink() or not path.is_file():
        raise CaptureBridgeError(f"authenticated source adapter is missing: {path}")
    name = "mcrl_v023_c1c2_capture_source_adapter"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CaptureBridgeError("cannot load authenticated V0.23 source adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def capture_world(
    config: Any,
    *,
    world: int,
    expected_manifest_sha256: str,
    c1_neutral_seed: int | None = None,
    c2_neutral_seed: int | None = None,
    frontier_config: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Capture one current V0.23 TRAIN world without learner or TEST work.

    ``config`` must be the authenticated adapter's
    ``V023SourceAdapterConfig``.  The routine intentionally reuses its
    private ``_authenticate`` and ``_native_q12_anchor`` seams so the C1/C2
    capture cannot silently switch to an old Q1/Q2 or environment path.
    """

    world = _exact_int(world, field="world")
    if world not in FROZEN_WORLDS:
        raise CaptureBridgeError("world is outside the frozen V0.23 TRAIN panel")
    expected_manifest = _digest(expected_manifest_sha256, field="expected_manifest_sha256")
    adapter = _load_source_adapter()
    # The server may load the adapter under a different module name than this
    # bridge's lazy loader.  Require the frozen config's public fields rather
    # than relying on cross-loader ``isinstance`` identity.
    for field in ("tle_root", "prereg", "manifest", "manifest_digest", "execution_addendum", "source_family"):
        if not hasattr(config, field):
            raise CaptureBridgeError(f"config lacks V0.23 field {field}")
    v020, v018, q1, q2, auth, manifest_sha = adapter.V023RuntimeSourceAdapter(config)._authenticate(
        expected_manifest_sha256=expected_manifest
    )
    if manifest_sha != expected_manifest:
        raise CaptureBridgeError("authenticated source manifest drifted")
    q1_receipt = auth["q1_receipt"]
    checkpoint_sha = _digest(q1_receipt["checkpoint_sha256"], field="checkpoint_sha256")
    record = v018._V015._V013.read_prereg(config.prereg)
    archive_root = config.tle_root
    c1_seed, c2_seed = _default_neutral_seeds(world)
    if c1_neutral_seed is not None:
        c1_seed = _exact_int(c1_neutral_seed, field="c1_neutral_seed")
    if c2_neutral_seed is not None:
        c2_seed = _exact_int(c2_neutral_seed, field="c2_neutral_seed")
    frontier = dict(frontier_config or C1_FRONTIER_CONFIG)

    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.ee_axis_c1_dull_source import capture_c1_dull_rollout_sample

    c1_records: list[dict[str, object]] = []
    c2_anchors: list[dict[str, object]] = []
    c2_informed: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v023-c1c2-capture-tle-") as temporary:
        archive = v018._V015._V013.screen._frozen_archive(
            record, archive_root, Path(temporary) / "frozen-tle"
        )
        validation = v018._V015._V013.screen.assert_ephemeris_matches_record(
            record, archive=archive
        )
        if not isinstance(validation, Mapping):
            raise CaptureBridgeError("ephemeris validator returned no receipt")
        environment = v018._V015._V013.screen._make_environment(
            archive, users=v018.USERS
        )
        step_env = environment.environment
        step_env._fading_field = KeyedFadingField.from_components(
            config.source_family, world
        )
        env_rng, mobility_rng, _action_rng, _control_rng = (
            v018._V015._V013.screen._evaluation_rngs(world)
        )
        _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        q1_before = str(v018._V015._q_parameter_sha256(q1))
        q2_before = str(v018._V015._q_parameter_sha256(q2))
        for step_index in range(STEPS_PER_EPISODE):
            if int(observation.step_index) != step_index:
                raise CaptureBridgeError("native episode step index drifted")
            anchor_data = adapter._native_q12_anchor(
                v018=v018,
                q1=q1,
                q2=q2,
                step_env=step_env,
                observation=observation,
                model_digest=adapter._model_digest(
                    q1, q2, auth["q1_receipt"], auth["q2_receipt"]
                ),
            )
            background = np.asarray(anchor_data["background"], dtype=np.int64)
            live_before_c1 = adapter._live_digest(v018, environment, env_rng)
            c1_sample = capture_c1_dull_rollout_sample(
                step_env,
                observation=observation,
                reference_actions=background,
                source_manifest_sha256=manifest_sha,
                checkpoint_sha256=checkpoint_sha,
                source_seed=world,
                rng=env_rng,
            )
            live_after_c1 = adapter._live_digest(v018, environment, env_rng)
            if live_after_c1 != live_before_c1:
                raise CaptureBridgeError(
                    "C1 dull-source evaluation mutated live state or RNG"
                )
            c1_records.append(
                c1_record_payload(
                    c1_sample.record,
                    state_sha256=c1_sample.state_observation.state_sha256,
                )
            )
            if step_index > 0:
                departures = detect_physical_departures(
                    background,
                    tuple(getattr(step_env, "_previous_association", ())),
                    tuple(observation.candidates.slot_tables),
                    step_index=step_index,
                )
                observation_provenance = getattr(observation, "observation_provenance", None)
                if observation_provenance is None:
                    raise CaptureBridgeError("native observation provenance is missing")
                native = anchor_data["native"]
                for departure in departures:
                    anchor = build_c2_anchor_payload(
                        world_id=world,
                        source_seed=world,
                        source_manifest_sha256=manifest_sha,
                        checkpoint_sha256=checkpoint_sha,
                        state_schema=native.schema,
                        state_schema_sha256=native.schema_sha256,
                        state_sha256=native.state_sha256,
                        observation_sha256=observation_provenance.content_digest,
                        step_index=step_index,
                        focal_user=departure.focal_user,
                        reference_action=departure.reference_action,
                        incumbent_physical_key=departure.incumbent_physical_key,
                        candidate_sinr=observation.candidate_sinr[departure.focal_user],
                        slot_table=departure.slot_table,
                    )
                    c2_anchors.append(anchor)
                    c2_informed.append(c2_informed_payload(anchor))
            outcome = environment.step(background, env_rng)
            if outcome.done and step_index != STEPS_PER_EPISODE - 1:
                raise CaptureBridgeError("episode terminated before ten source anchors")
            if not outcome.done and step_index == STEPS_PER_EPISODE - 1:
                raise CaptureBridgeError("episode did not terminate at ten source anchors")
            if not outcome.done:
                # TrainerEnvironment.step returns the compact StepResult;
                # the complete successor observation is exposed by the
                # authenticated adapter's last_outcome bridge.
                observation = adapter._step_result_observation(environment, outcome)
        q1_after = str(v018._V015._q_parameter_sha256(q1))
        q2_after = str(v018._V015._q_parameter_sha256(q2))
    if q1_after != q1_before or q2_after != q2_before:
        raise CaptureBridgeError("Q1/Q2 parameters changed during predecision capture")
    if not c2_anchors:
        raise CaptureBridgeError("TRAIN world produced no physical Main departures for C2")
    pool_id = f"v023-train-world-{world}-predecision"
    provenance = {
        "source_manifest_sha256": manifest_sha,
        "checkpoint_sha256": checkpoint_sha,
        "state_schema": EE_AXIS_STATE_SCHEMA,
        "state_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
    }
    return build_capture_payload(
        pool_id=pool_id,
        provenance=provenance,
        frontier_config=frontier,
        c1_neutral_seed=c1_seed,
        c1_records=c1_records,
        c2_neutral_seed=c2_seed,
        c2_anchors=c2_anchors,
        c2_informed=c2_informed,
    )


capture_v023_train_world = capture_world


__all__ = [
    "C1_ACRM_PAIR_RULE",
    "C1_DULL_ROLLOUT_KIND",
    "C1_INFORMED_SOURCE_RULE",
    "C2_HORIZON_STEPS",
    "C2_INFORMED_SOURCE_RULE",
    "C2_NEUTRAL_SOURCE_RULE",
    "C2_POLICY_VERSION",
    "C2_ANCHOR_SCHEMA",
    "C2Departure",
    "CLAIM_CEILING",
    "CaptureBridgeError",
    "FROZEN_WORLDS",
    "PANEL_POOL_ID",
    "SCHEMA",
    "TRAIN_SPLIT",
    "build_c2_anchor_payload",
    "build_capture_payload",
    "canonical_bytes",
    "canonical_sha256",
    "c2_anchor_sha256",
    "capture_v023_train_world",
    "capture_world",
    "c1_record_payload",
    "c2_informed_payload",
    "choose_c2_informed_candidate",
    "detect_physical_departures",
    "file_sha256",
    "legal_physical_alternatives",
    "load_materializer",
    "merge_world_captures",
    "recompute_pool_sha256",
    "write_capture",
]
