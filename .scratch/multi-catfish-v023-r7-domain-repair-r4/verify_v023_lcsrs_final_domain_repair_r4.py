#!/usr/bin/env python3
"""Integrity-only R4 adapter for the frozen R7 final verifier."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import importlib.util
import inspect
from pathlib import Path
import sys
import textwrap
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA = "multi-catfish-mcrl-v023-r7-final-verifier-domain-repair-v4"
STATUS = "PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_AND_IMPORT_CLOSURE_REPAIR_"
    "NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
R3_ADAPTER_SHA256 = (
    "7d242eb2ca31835ba2471334b7ab90f8d68f4c817a367a5f3f2c72fb518fff2d"
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
R3_ADAPTER = (
    REPO
    / ".scratch/multi-catfish-v023-r7-domain-repair-r3"
    / "verify_v023_lcsrs_final_domain_repair.py"
)


class V023R7DomainRepairR4Error(RuntimeError):
    """The exact R4 final-verifier repair failed closed."""


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V023R7DomainRepairR4Error(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_r3_adapter() -> ModuleType:
    if _sha256(R3_ADAPTER) != R3_ADAPTER_SHA256:
        raise V023R7DomainRepairR4Error("frozen R3 repair adapter digest drifted")
    name = "v023_lcsrs_frozen_r3_adapter_for_domain_repair_r4"
    specification = importlib.util.spec_from_file_location(name, R3_ADAPTER)
    if specification is None or specification.loader is None:
        raise V023R7DomainRepairR4Error("cannot load frozen R3 repair adapter")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    if _sha256(R3_ADAPTER) != R3_ADAPTER_SHA256:
        raise V023R7DomainRepairR4Error("frozen R3 repair adapter changed while loading")
    return module


R3 = _load_r3_adapter()
ORIGINAL_VERIFIER_SHA256 = R3.ORIGINAL_VERIFIER_SHA256
INVALID_VERIFICATION_SHA256 = R3.INVALID_VERIFICATION_SHA256
SOURCE_ARRAY_SCHEMA = R3.SOURCE_ARRAY_SCHEMA
SOURCE_ARRAY_DOMAIN = R3.SOURCE_ARRAY_DOMAIN
COMPOSITION_ARRAY_DOMAIN = R3.COMPOSITION_ARRAY_DOMAIN
EXPECTED_INVALID_ERROR = R3.EXPECTED_INVALID_ERROR
EXPECTED_SOURCE_LOADS = R3.EXPECTED_SOURCE_LOADS
EXPECTED_COMPOSITION_LOADS = R3.EXPECTED_COMPOSITION_LOADS
EXPECTED_PREFLIGHT_MANIFEST_SHA256 = R3.EXPECTED_PREFLIGHT_MANIFEST_SHA256
ORIGINAL_VERIFIER = R3.ORIGINAL_VERIFIER
_canonical_bytes = R3._canonical_bytes
_write_once = R3._write_once


@dataclass(frozen=True)
class PairKeyReconstruction:
    """The two independent source-only pair-key derivations."""

    json_source_keys: np.ndarray
    json_destination_keys: np.ndarray
    npz_source_keys: np.ndarray
    npz_destination_keys: np.ndarray

    @property
    def pair_source_key(self) -> np.ndarray:
        return self.json_source_keys

    @property
    def pair_destination_keys(self) -> np.ndarray:
        return self.json_destination_keys


def _require_int64(name: str, value: object) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != np.dtype(np.int64):
        raise V023R7DomainRepairR4Error(f"source {name} is not int64")
    return array


def _decode_pair_id(value: object) -> str:
    try:
        result = bytes(value).rstrip(b"\0").decode("ascii")
    except (TypeError, ValueError, UnicodeDecodeError) as error:
        raise V023R7DomainRepairR4Error("source pair_id is not fixed ASCII") from error
    if not result:
        raise V023R7DomainRepairR4Error("source pair_id is empty")
    return result


def _json_int_pair(value: object, *, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise V023R7DomainRepairR4Error(f"{label} must be two exact integers")
    maximum = int(np.iinfo(np.int64).max)
    result = int(value[0]), int(value[1])
    if any(item < 0 or item > maximum for item in result):
        raise V023R7DomainRepairR4Error(f"{label} is outside nonnegative int64")
    return result


def _json_destination_keys(
    value: object, *, label: str
) -> tuple[tuple[int, int], tuple[int, int]]:
    if not isinstance(value, list) or len(value) != 2:
        raise V023R7DomainRepairR4Error(f"{label} must contain exactly two keys")
    return (
        _json_int_pair(value[0], label=f"{label}[0]"),
        _json_int_pair(value[1], label=f"{label}[1]"),
    )


def reconstruct_pair_keys_from_source(
    *,
    topology_pairs_by_anchor: Sequence[object],
    pair_anchor_index: object,
    pair_user_ids: object,
    pair_action_ids: object,
    pair_id: object,
    physical_keys: object,
    reference_actions: object,
    action_mask: object,
) -> PairKeyReconstruction:
    """Reconstruct both pair-key arrays twice using authenticated source data."""

    pair_anchor = _require_int64("pair_anchor_index", pair_anchor_index)
    pair_users = _require_int64("pair_user_ids", pair_user_ids)
    pair_actions = _require_int64("pair_action_ids", pair_action_ids)
    keys = _require_int64("physical_keys", physical_keys)
    references = _require_int64("reference_actions", reference_actions)
    masks = np.asarray(action_mask)
    pair_ids = np.asarray(pair_id)

    pair_count = int(pair_anchor.size)
    if pair_anchor.shape != (pair_count,):
        raise V023R7DomainRepairR4Error("source pair_anchor_index shape drifted")
    if pair_users.shape != (pair_count, 2) or pair_actions.shape != (pair_count, 2):
        raise V023R7DomainRepairR4Error("source pair member/action shapes drifted")
    if pair_ids.dtype.kind != "S" or pair_ids.shape != (pair_count,):
        raise V023R7DomainRepairR4Error("source pair_id shape/dtype drifted")
    if keys.ndim != 4 or keys.shape[-1] != 2:
        raise V023R7DomainRepairR4Error("source physical_keys shape drifted")
    anchor_count, user_count, action_count, _ = keys.shape
    if references.shape != (anchor_count, user_count):
        raise V023R7DomainRepairR4Error("source reference_actions shape drifted")
    if masks.dtype != np.bool_ or masks.shape != (anchor_count, user_count, action_count):
        raise V023R7DomainRepairR4Error("source action_mask shape/dtype drifted")
    if len(topology_pairs_by_anchor) != anchor_count:
        raise V023R7DomainRepairR4Error("source topology anchor panel length drifted")

    json_sources = np.empty((pair_count, 2), dtype=np.int64, order="C")
    json_destinations = np.empty((pair_count, 2, 2), dtype=np.int64, order="C")
    npz_sources = np.empty((pair_count, 2), dtype=np.int64, order="C")
    npz_destinations = np.empty((pair_count, 2, 2), dtype=np.int64, order="C")

    for anchor in range(anchor_count):
        topology_pairs = topology_pairs_by_anchor[anchor]
        if not isinstance(topology_pairs, list):
            raise V023R7DomainRepairR4Error(
                f"source topology pairs are not a list at anchor {anchor}"
            )
        selected = np.flatnonzero(pair_anchor == anchor)
        if len(topology_pairs) != int(selected.size):
            raise V023R7DomainRepairR4Error(
                f"source topology/pair count disagrees at anchor {anchor}"
            )
        for offset, pair_raw in enumerate(selected.tolist()):
            row = int(pair_raw)
            topology_pair = topology_pairs[offset]
            if not isinstance(topology_pair, Mapping):
                raise V023R7DomainRepairR4Error(
                    f"source topology pair is malformed at anchor {anchor} offset {offset}"
                )
            identifier = _decode_pair_id(pair_ids[row])
            if topology_pair.get("pair_id") != identifier:
                raise V023R7DomainRepairR4Error(
                    f"source topology/pair_id order disagrees at row {row}"
                )
            members = _json_int_pair(
                topology_pair.get("member_users"),
                label=f"source topology member_users at row {row}",
            )
            designated = _json_int_pair(
                topology_pair.get("designated_actions"),
                label=f"source topology designated_actions at row {row}",
            )
            if members != tuple(int(value) for value in pair_users[row]):
                raise V023R7DomainRepairR4Error(
                    f"source topology/member identity disagrees at row {row}"
                )
            if designated != tuple(int(value) for value in pair_actions[row]):
                raise V023R7DomainRepairR4Error(
                    f"source topology/action identity disagrees at row {row}"
                )
            if (
                members[0] >= user_count
                or members[1] >= user_count
                or members[0] == members[1]
                or designated[0] >= action_count
                or designated[1] >= action_count
            ):
                raise V023R7DomainRepairR4Error(
                    f"source pair indices are out of range at row {row}"
                )
            reference = (
                int(references[anchor, members[0]]),
                int(references[anchor, members[1]]),
            )
            if any(value < 0 or value >= action_count for value in reference):
                raise V023R7DomainRepairR4Error(
                    f"source reference action is out of range at row {row}"
                )
            if not all(
                (
                    bool(masks[anchor, members[index], reference[index]])
                    and bool(masks[anchor, members[index], designated[index]])
                )
                for index in range(2)
            ):
                raise V023R7DomainRepairR4Error(
                    f"source pair reference/designated action is masked at row {row}"
                )

            json_source = _json_int_pair(
                topology_pair.get("source_key"),
                label=f"source topology source_key at row {row}",
            )
            json_destination = _json_destination_keys(
                topology_pair.get("destination_keys"),
                label=f"source topology destination_keys at row {row}",
            )
            source_first = np.asarray(
                keys[anchor, members[0], reference[0]], dtype=np.int64
            )
            source_second = np.asarray(
                keys[anchor, members[1], reference[1]], dtype=np.int64
            )
            destination = np.asarray(
                keys[
                    anchor,
                    np.asarray(members, dtype=np.int64),
                    np.asarray(designated, dtype=np.int64),
                ],
                dtype=np.int64,
            )
            if (
                source_first.shape != (2,)
                or source_second.shape != (2,)
                or destination.shape != (2, 2)
                or np.any(source_first < 0)
                or np.any(source_second < 0)
                or np.any(destination < 0)
            ):
                raise V023R7DomainRepairR4Error(
                    f"source physical pair keys are malformed at row {row}"
                )
            if not np.array_equal(source_first, source_second):
                raise V023R7DomainRepairR4Error(
                    f"source members do not share one physical source key at row {row}"
                )

            json_sources[row] = json_source
            json_destinations[row] = json_destination
            npz_sources[row] = source_first
            npz_destinations[row] = destination

    if pair_count and (np.any(pair_anchor < 0) or np.any(pair_anchor >= anchor_count)):
        raise V023R7DomainRepairR4Error("source pair_anchor_index is out of range")
    if not np.array_equal(json_sources, npz_sources) or not np.array_equal(
        json_destinations, npz_destinations
    ):
        raise V023R7DomainRepairR4Error(
            "source JSON/NPZ pair-key derivations disagree"
        )
    outputs = (json_sources, json_destinations, npz_sources, npz_destinations)
    if not all(value.flags.c_contiguous for value in outputs):
        raise V023R7DomainRepairR4Error("reconstructed pair keys are not C-order")
    return PairKeyReconstruction(*outputs)


def _topology_pairs_from_source(
    payload: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> list[list[object]]:
    physical_keys = np.asarray(arrays.get("physical_keys"))
    anchor_count = int(physical_keys.shape[0]) if physical_keys.ndim == 4 else -1
    anchors = payload.get("anchors")
    if anchor_count < 0 or not isinstance(anchors, list) or len(anchors) != anchor_count:
        raise V023R7DomainRepairR4Error("source anchor/topology panel is unavailable")
    topology_digests = np.asarray(arrays.get("anchor_topology_content_digest"))
    if topology_digests.shape != (anchor_count,) or topology_digests.dtype.kind != "S":
        raise V023R7DomainRepairR4Error("source topology digest array is unavailable")
    result: list[list[object]] = []
    for index, anchor_raw in enumerate(anchors):
        if not isinstance(anchor_raw, Mapping) or anchor_raw.get("phase") != index + 1:
            raise V023R7DomainRepairR4Error("source anchor JSON order drifted")
        topology = anchor_raw.get("topology")
        if not isinstance(topology, Mapping):
            raise V023R7DomainRepairR4Error("source anchor topology is not an object")
        if topology.get("content_digest") != _decode_pair_id(topology_digests[index]):
            raise V023R7DomainRepairR4Error(
                f"source topology content digest disagrees at anchor {index}"
            )
        pairs = topology.get("pairs")
        if not isinstance(pairs, list):
            raise V023R7DomainRepairR4Error(
                f"source topology pairs are unavailable at anchor {index}"
            )
        result.append(pairs)
    return result


def _reconstruct_source_pair_keys(
    payload: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> PairKeyReconstruction:
    required = (
        "pair_anchor_index",
        "pair_user_ids",
        "pair_action_ids",
        "pair_id",
        "physical_keys",
        "reference_actions",
        "action_mask",
    )
    missing = [name for name in required if name not in arrays]
    if missing:
        raise V023R7DomainRepairR4Error(
            "source pair-key reconstruction arrays are missing: " + ", ".join(missing)
        )
    return reconstruct_pair_keys_from_source(
        topology_pairs_by_anchor=_topology_pairs_from_source(payload, arrays),
        pair_anchor_index=arrays["pair_anchor_index"],
        pair_user_ids=arrays["pair_user_ids"],
        pair_action_ids=arrays["pair_action_ids"],
        pair_id=arrays["pair_id"],
        physical_keys=arrays["physical_keys"],
        reference_actions=arrays["reference_actions"],
        action_mask=arrays["action_mask"],
    )


def _install_pair_key_reconstruction(
    module: ModuleType,
) -> tuple[Any, dict[str, Any]]:
    """Inject source-only pair keys into a shallow mapping for the frozen join."""

    original = getattr(module, "_join_composition_source", None)
    if not callable(original) or getattr(original, "_v023_r4_pair_key_wrapper", False):
        raise V023R7DomainRepairR4Error(
            "frozen verifier pair-key join target is missing or already wrapped"
        )
    state: dict[str, Any] = {
        "join_applications": 0,
        "world_pair_counts": {},
        "both_derivations_agreed": True,
    }
    cache: dict[int, tuple[Mapping[str, np.ndarray], PairKeyReconstruction]] = {}

    def repaired(shard: object, source: object) -> Any:
        if not isinstance(source, tuple) or len(source) != 2:
            raise V023R7DomainRepairR4Error("frozen join source tuple is malformed")
        payload, arrays = source
        if not isinstance(payload, Mapping) or not isinstance(arrays, Mapping):
            raise V023R7DomainRepairR4Error("frozen join source evidence is malformed")
        if "pair_source_key" in arrays or "pair_destination_keys" in arrays:
            raise V023R7DomainRepairR4Error(
                "source pair-key repair target is not exactly the two missing arrays"
            )
        cached = cache.get(id(arrays))
        if cached is not None and cached[0] is arrays:
            reconstruction = cached[1]
        else:
            reconstruction = _reconstruct_source_pair_keys(payload, arrays)
            cache[id(arrays)] = (arrays, reconstruction)
        world = payload.get("world")
        if type(world) is not int:
            raise V023R7DomainRepairR4Error("source world is not an exact integer")
        pair_count = int(reconstruction.pair_source_key.shape[0])
        prior = state["world_pair_counts"].get(world)
        if prior is not None and prior != pair_count:
            raise V023R7DomainRepairR4Error("source pair count changed between joins")
        state["world_pair_counts"][world] = pair_count
        state["join_applications"] += 1
        source_arrays = dict(arrays)
        source_arrays["pair_source_key"] = reconstruction.pair_source_key
        source_arrays["pair_destination_keys"] = reconstruction.pair_destination_keys
        return original(shard, (payload, source_arrays))

    repaired._v023_r4_pair_key_wrapper = True  # type: ignore[attr-defined]
    module._join_composition_source = repaired
    return original, state


C2_DIAGNOSTIC_FIELDS = frozenset(
    {
        "diagnostic_lambda_bits_per_j_hex",
        "exposure_count",
        "kind",
        "nontrivial_count",
        "rows",
        "runtime_default_lambda_used_for_target",
        "target_filter_applied",
        "target_free_inference",
    }
)
C2_SHARED_FIELDS = (
    "kind",
    "diagnostic_lambda_bits_per_j_hex",
    "target_filter_applied",
    "target_free_inference",
    "runtime_default_lambda_used_for_target",
)
C2_COUNT_FIELDS = ("exposure_count", "nontrivial_count")


def normalize_c2_diagnostic_list(
    diagnostics: object, *, label: str
) -> tuple[dict[str, Any], dict[str, int]]:
    """Normalize writer list-of-pair objects without dropping rows/provenance."""

    if not isinstance(diagnostics, list):
        raise V023R7DomainRepairR4Error(f"{label} diagnostic list is not a list")
    if not diagnostics:
        raise V023R7DomainRepairR4Error(
            f"{label} diagnostic list is empty; required pair-level provenance is unavailable"
        )
    rows: list[object] = []
    provenance: list[dict[str, Any]] = []
    shared: dict[str, Any] | None = None
    totals = {name: 0 for name in C2_COUNT_FIELDS}
    for pair_offset, diagnostic_raw in enumerate(diagnostics):
        if not isinstance(diagnostic_raw, Mapping):
            raise V023R7DomainRepairR4Error(
                f"{label} diagnostic[{pair_offset}] is not an object"
            )
        if set(diagnostic_raw) != C2_DIAGNOSTIC_FIELDS:
            raise V023R7DomainRepairR4Error(
                f"{label} diagnostic[{pair_offset}] fields drifted"
            )
        pair_rows = diagnostic_raw.get("rows")
        if not isinstance(pair_rows, list) or any(
            not isinstance(row, Mapping) for row in pair_rows
        ):
            raise V023R7DomainRepairR4Error(
                f"{label} diagnostic[{pair_offset}] rows are malformed"
            )
        current_shared = {name: diagnostic_raw[name] for name in C2_SHARED_FIELDS}
        if shared is None:
            shared = current_shared
        elif current_shared != shared:
            raise V023R7DomainRepairR4Error(
                f"{label} per-pair diagnostic provenance disagrees"
            )
        for name in C2_COUNT_FIELDS:
            value = diagnostic_raw[name]
            if type(value) is not int or value < 0:
                raise V023R7DomainRepairR4Error(
                    f"{label} diagnostic[{pair_offset}] {name} is malformed"
                )
            totals[name] += value
        start = len(rows)
        rows.extend(pair_rows)
        provenance.append(
            {
                "pair_offset": pair_offset,
                "row_offset": start,
                "row_count": len(pair_rows),
                **{
                    name: diagnostic_raw[name]
                    for name in (*C2_SHARED_FIELDS, *C2_COUNT_FIELDS)
                },
            }
        )
    assert shared is not None
    normalized = {
        **shared,
        **totals,
        "rows": rows,
        "r4_normalization_schema": "c2-per-pair-list-to-object-v1",
        "r4_per_pair_provenance": provenance,
    }
    return normalized, {
        "pair_objects": len(diagnostics),
        "rows": len(rows),
        "exposure_count": totals["exposure_count"],
        "nontrivial_count": totals["nontrivial_count"],
    }


def _install_c2_diagnostic_normalization(
    module: ModuleType,
) -> tuple[Any, dict[str, int]]:
    """Accept only the documented writer list at the frozen diagnostic accessor."""

    original = getattr(module, "_diagnostic_rows", None)
    if not callable(original) or getattr(original, "_v023_r4_c2_wrapper", False):
        raise V023R7DomainRepairR4Error(
            "frozen verifier C2 diagnostic target is missing or already wrapped"
        )
    state = {
        "list_containers": 0,
        "mapping_passthrough": 0,
        "pair_objects": 0,
        "rows": 0,
        "exposure_count": 0,
        "nontrivial_count": 0,
    }

    def repaired(diag: object, *, label: str):
        if isinstance(diag, Mapping):
            state["mapping_passthrough"] += 1
            return original(diag, label=label)
        if isinstance(diag, list):
            normalized, counts = normalize_c2_diagnostic_list(diag, label=label)
            state["list_containers"] += 1
            for name, value in counts.items():
                state[name] += value
            return original(normalized, label=label)
        return original(diag, label=label)

    repaired._v023_r4_c2_wrapper = True  # type: ignore[attr-defined]
    module._diagnostic_rows = repaired
    return original, state


_Q2_DELTA_HELPER = "_v023_r4_writer_style_q2_delta"
_Q2_DELTA_EXPRESSION = ast.parse(
    """
np.asarray(
    [
        q2[index, user, action] - q2[index, user, reference]
        for user, action, reference in zip(
            users_row, actions_row, expected_refs, strict=True
        )
    ],
    dtype=np.float64,
)
""",
    mode="eval",
).body


def _writer_style_q2_delta(
    q2: object,
    index: int,
    users_row: Sequence[int],
    actions_row: Sequence[int],
    expected_refs: Sequence[int],
) -> np.ndarray:
    """Reproduce the writer's float32 scalar subtraction, then widen to float64."""

    values = np.asarray(q2)
    return np.asarray(
        [
            float(
                np.float32(values[index, user, action])
                - np.float32(values[index, user, reference])
            )
            for user, action, reference in zip(
                users_row, actions_row, expected_refs, strict=True
            )
        ],
        dtype=np.float64,
    )


class _Q2DeltaPrecisionTransformer(ast.NodeTransformer):
    """Replace exactly the frozen expected-Q2-delta expression."""

    def __init__(self) -> None:
        self.replacements = 0

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        self.generic_visit(node)
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "expected_q2_delta"
            and ast.dump(node.value, include_attributes=False)
            == ast.dump(_Q2_DELTA_EXPRESSION, include_attributes=False)
        ):
            node.value = ast.copy_location(
                ast.Call(
                    func=ast.Name(id=_Q2_DELTA_HELPER, ctx=ast.Load()),
                    args=[
                        ast.Name(id="q2", ctx=ast.Load()),
                        ast.Name(id="index", ctx=ast.Load()),
                        ast.Name(id="users_row", ctx=ast.Load()),
                        ast.Name(id="actions_row", ctx=ast.Load()),
                        ast.Name(id="expected_refs", ctx=ast.Load()),
                    ],
                    keywords=[],
                ),
                node.value,
            )
            self.replacements += 1
        return node


def _build_q2_delta_context(
    module: ModuleType, state: dict[str, int]
) -> Any:
    original = getattr(module, "_context_status", None)
    if not callable(original) or getattr(
        original, "_v023_r4_q2_delta_precision", False
    ):
        raise V023R7DomainRepairR4Error(
            "frozen verifier Q2 delta target is missing or already transformed"
        )
    try:
        source = textwrap.dedent(inspect.getsource(original))
        tree = ast.parse(source, filename=str(ORIGINAL_VERIFIER))
    except (OSError, TypeError, SyntaxError) as error:
        raise V023R7DomainRepairR4Error(
            "cannot inspect frozen C2 context verifier"
        ) from error
    transformer = _Q2DeltaPrecisionTransformer()
    transformed = transformer.visit(tree)
    if transformer.replacements != 1:
        raise V023R7DomainRepairR4Error(
            "frozen expected Q2 delta expression is not unique"
        )
    ast.fix_missing_locations(transformed)
    namespace = dict(module.__dict__)

    def writer_style_q2_delta(
        q2: object,
        index: int,
        users_row: Sequence[int],
        actions_row: Sequence[int],
        expected_refs: Sequence[int],
    ) -> np.ndarray:
        result = _writer_style_q2_delta(
            q2, index, users_row, actions_row, expected_refs
        )
        state["rows_checked"] += 1
        state["member_deltas_checked"] += int(result.size)
        return result

    namespace[_Q2_DELTA_HELPER] = writer_style_q2_delta
    try:
        exec(
            compile(transformed, str(ORIGINAL_VERIFIER), "exec"),
            namespace,
            namespace,
        )
    except (TypeError, ValueError, SyntaxError) as error:
        raise V023R7DomainRepairR4Error(
            "cannot compile scoped Q2 delta precision repair"
        ) from error
    repaired = namespace.get(original.__name__)
    if not callable(repaired) or repaired is original:
        raise V023R7DomainRepairR4Error(
            "scoped Q2 delta precision repair did not produce a new context verifier"
        )
    repaired._v023_r4_q2_delta_precision = True  # type: ignore[attr-defined]
    return repaired


def _install_q2_delta_precision(
    module: ModuleType,
) -> tuple[Any, dict[str, int]]:
    """Install the unique expected-Q2-delta transform and return the original."""

    state = {"rows_checked": 0, "member_deltas_checked": 0}
    original = getattr(module, "_context_status", None)
    repaired = _build_q2_delta_context(module, state)
    module._context_status = repaired
    return original, state


def _load_original() -> ModuleType:
    if _sha256(R3_ADAPTER) != R3_ADAPTER_SHA256:
        raise V023R7DomainRepairR4Error("frozen R3 repair adapter digest drifted")
    return R3._load_original()


def _pair_reconstruction_receipt(state: Mapping[str, Any]) -> dict[str, Any]:
    counts = state.get("world_pair_counts")
    if not isinstance(counts, Mapping):
        raise V023R7DomainRepairR4Error("pair-key reconstruction counts are unavailable")
    return {
        "arrays_reconstructed": ["pair_source_key", "pair_destination_keys"],
        "source_only": True,
        "json_topology_derivation": True,
        "source_npz_physical_derivation": True,
        "both_derivations_agreed": state.get("both_derivations_agreed") is True,
        "all_enumerated_pairs": True,
        "pair_retained_filter_applied": False,
        "pair_order_preserved": True,
        "dtype": "int64",
        "c_order": True,
        "shapes": {"pair_source_key": "(P,2)", "pair_destination_keys": "(P,2,2)"},
        "source_worlds": len(counts),
        "source_pair_rows": sum(int(value) for value in counts.values()),
        "join_applications": int(state.get("join_applications", -1)),
    }


def _c2_normalization_receipt(state: Mapping[str, int]) -> dict[str, Any]:
    return {
        "applied": True,
        "input_container": "list-of-per-pair-objects",
        "output_container": "single-object",
        "pair_order_preserved": True,
        "all_rows_preserved": True,
        "per_pair_scalar_provenance_preserved": True,
        "shared_fields_asserted_equal": list(C2_SHARED_FIELDS),
        "count_fields_summed": list(C2_COUNT_FIELDS),
        **{name: int(value) for name, value in state.items()},
    }


def _q2_delta_precision_receipt(state: Mapping[str, int]) -> dict[str, Any]:
    return {
        "expected_computed_in": "float32-as-writer",
        "rows_checked": int(state.get("rows_checked", -1)),
        "member_deltas_checked": int(state.get("member_deltas_checked", -1)),
        "scoped_target": "_context_status expected_q2_delta",
    }


def run(
    *,
    source_paths: Sequence[Path],
    fit_paths: Sequence[Path],
    composition_paths: Sequence[Path],
    source_manifest: Path,
    launch_manifest: Path,
    launch_manifest_digest: Path,
    invalid_verification: Path,
    contract: Path,
    output: Path,
    receipt: Path,
) -> dict[str, Any]:
    if len(source_paths) != 8 or len(fit_paths) != 48 or len(composition_paths) != 48:
        raise V023R7DomainRepairR4Error("repair requires the exact 8/48/48 panel")
    for target in (output, receipt):
        if target.exists() or target.is_symlink():
            raise V023R7DomainRepairR4Error(f"refusing to overwrite: {target}")
    r3 = _load_r3_adapter()
    contract_sha = r3._sha256(contract)
    invalid_sha = r3._verify_invalid_attempt(invalid_verification)
    original = _load_original()
    original_loader, dispatch_counts = r3._install_domain_dispatch(original)
    original_pair_validator: Any | None = None
    original_join: Any | None = None
    original_diagnostic: Any | None = None
    original_context: Any | None = None
    pair_state: dict[str, Any] = {}
    diagnostic_state: dict[str, int] = {}
    q2_delta_state: dict[str, int] = {}
    try:
        original_pair_validator = r3._install_pair_profile_broadcast(original)
        original_join, pair_state = _install_pair_key_reconstruction(original)
        original_diagnostic, diagnostic_state = _install_c2_diagnostic_normalization(
            original
        )
        original_context, q2_delta_state = _install_q2_delta_precision(original)
        with r3._temporary_import_path(ORIGINAL_VERIFIER.parent):
            result = original.verify_v023_final_gate(
                source_paths=tuple(source_paths),
                fit_paths=tuple(fit_paths),
                composition_paths=tuple(composition_paths),
                source_manifest_path=source_manifest,
                expected_preflight_manifest_sha256=EXPECTED_PREFLIGHT_MANIFEST_SHA256,
                launch_manifest_path=launch_manifest,
                launch_manifest_digest_path=launch_manifest_digest,
            )
    finally:
        if original_context is not None:
            original._context_status = original_context
        if original_diagnostic is not None:
            original._diagnostic_rows = original_diagnostic
        if original_join is not None:
            original._join_composition_source = original_join
        if original_pair_validator is not None:
            original._validate_pair_arrays = original_pair_validator
        original._load_npz = original_loader
    if not isinstance(result, Mapping):
        raise V023R7DomainRepairR4Error(
            "corrected final verifier did not return a mapping"
        )
    if result.get("status") == "INVALID_RUN":
        errors = result.get("errors")
        if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)):
            detail = "; ".join(str(error) for error in errors)
        else:
            detail = repr(errors)
        raise V023R7DomainRepairR4Error(
            "corrected final verification returned INVALID_RUN before "
            f"repair postconditions: {detail}"
        )
    if dispatch_counts != {
        "source": EXPECTED_SOURCE_LOADS,
        "composition": EXPECTED_COMPOSITION_LOADS,
    }:
        raise V023R7DomainRepairR4Error(
            f"NPZ domain dispatch count drifted: {dispatch_counts}"
        )
    pair_receipt = _pair_reconstruction_receipt(pair_state)
    diagnostic_receipt = _c2_normalization_receipt(diagnostic_state)
    q2_delta_receipt = _q2_delta_precision_receipt(q2_delta_state)
    if (
        pair_receipt["source_worlds"] != 8
        or pair_receipt["join_applications"] != 48
        or not pair_receipt["both_derivations_agreed"]
        or diagnostic_receipt["list_containers"] != 72
        or diagnostic_receipt["mapping_passthrough"] != 0
        or diagnostic_receipt["pair_objects"] != diagnostic_receipt["rows"]
        or pair_receipt["source_pair_rows"] != diagnostic_receipt["rows"]
        or q2_delta_receipt["rows_checked"] != diagnostic_receipt["rows"]
        or q2_delta_receipt["member_deltas_checked"]
        != 2 * diagnostic_receipt["rows"]
    ):
        raise V023R7DomainRepairR4Error(
            "R4 pair-key/C2 normalization postconditions drifted"
        )
    output_sha = r3._write_once(output, r3._canonical_bytes(result))
    passed = (
        result.get("status") == "PASS_FINAL_INTEGRITY"
        and result.get("integrity_status") == "VERIFIED"
        and result.get("source_count") == 8
        and result.get("fit_count") == 48
        and result.get("composition_count") == 48
        and result.get("scientific_claim") is False
        and result.get("test_split_opened") is False
        and result.get("episode_training") is False
    )
    receipt_payload = {
        "schema": SCHEMA,
        "status": STATUS if passed else "FAILED_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4",
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": contract_sha,
        "repair_adapter_sha256": r3._sha256(Path(__file__).resolve()),
        "r3_adapter_sha256": R3_ADAPTER_SHA256,
        "original_verifier_sha256": ORIGINAL_VERIFIER_SHA256,
        "preflight_manifest_sha256": EXPECTED_PREFLIGHT_MANIFEST_SHA256,
        "invalid_verification_sha256": invalid_sha,
        "corrected_verification_sha256": output_sha,
        "domain_dispatch": {
            "source": SOURCE_ARRAY_DOMAIN,
            "composition": COMPOSITION_ARRAY_DOMAIN,
            "source_loads": dispatch_counts["source"],
            "composition_loads": dispatch_counts["composition"],
        },
        "pair_profile_broadcast": {
            "operation": "np.broadcast_to(expected_profiles[None, :, :], profile_actions[p].shape)",
            "draw_count": 32,
            "scoped_target": "composition pair profile actions",
        },
        "sibling_import_path_scoped": True,
        "pair_key_reconstruction": pair_receipt,
        "c2_diagnostic_normalization": diagnostic_receipt,
        "q2_delta_precision": q2_delta_receipt,
        "corrected_integrity_status": result.get("integrity_status"),
        "corrected_status": result.get("status"),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "scientific_claim": False,
    }
    r3._write_once(receipt, r3._canonical_bytes(receipt_payload))
    if not passed:
        raise V023R7DomainRepairR4Error(
            "corrected final verification remains invalid"
        )
    return receipt_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs=8, type=Path, required=True)
    parser.add_argument("--fit", nargs=48, type=Path, required=True)
    parser.add_argument("--composition", nargs=48, type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--launch-manifest", type=Path, required=True)
    parser.add_argument("--launch-manifest-digest", type=Path, required=True)
    parser.add_argument("--invalid-verification", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repair_receipt = run(
            source_paths=args.source,
            fit_paths=args.fit,
            composition_paths=args.composition,
            source_manifest=args.source_manifest,
            launch_manifest=args.launch_manifest,
            launch_manifest_digest=args.launch_manifest_digest,
            invalid_verification=args.invalid_verification,
            contract=args.contract,
            output=args.output,
            receipt=args.receipt,
        )
    except Exception as error:
        print(f"V023_R7_DOMAIN_REPAIR_R4_FAILED: {error}", file=sys.stderr)
        return 2
    print(
        "V023_R7_DOMAIN_REPAIR_R4_PASS "
        f"source_loads={repair_receipt['domain_dispatch']['source_loads']} "
        f"composition_loads={repair_receipt['domain_dispatch']['composition_loads']} "
        f"pairs={repair_receipt['pair_key_reconstruction']['source_pair_rows']} "
        f"c2_rows={repair_receipt['c2_diagnostic_normalization']['rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPOSITION_ARRAY_DOMAIN",
    "C2_COUNT_FIELDS",
    "C2_DIAGNOSTIC_FIELDS",
    "C2_SHARED_FIELDS",
    "PairKeyReconstruction",
    "SOURCE_ARRAY_DOMAIN",
    "SOURCE_ARRAY_SCHEMA",
    "V023R7DomainRepairR4Error",
    "_install_c2_diagnostic_normalization",
    "_install_pair_key_reconstruction",
    "_install_q2_delta_precision",
    "_writer_style_q2_delta",
    "build_parser",
    "main",
    "normalize_c2_diagnostic_list",
    "reconstruct_pair_keys_from_source",
    "run",
]
