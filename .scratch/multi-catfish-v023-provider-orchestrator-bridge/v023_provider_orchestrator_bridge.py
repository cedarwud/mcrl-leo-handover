"""Fail-closed V0.23 provider bridge for the isolated five-arm learner.

This scratch seam is deliberately only a consumer of already-authenticated,
already-typed inputs.  C1/C2 are re-opened through the target-batch adapter and
use its authenticated full-panel batches once per source-training epoch.  C3
has no current serialized sampled-batch receipt, so callers must inject two
separately named typed inputs containing the exact precomputed batch schedule.
The bridge neither retags, samples, nor constructs target data.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import numpy as np

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import LCSRSAnchorSurface
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch


BRIDGE_SCHEMA = "multi-catfish-mcrl-v023-provider-orchestrator-bridge-v2"
ROUTE_ORDER = ("C1", "C2", "C3")
SOURCE_ORDER = ("neutral", "informed")


class V023ProviderBridgeError(MCRLContractError):
    """The authenticated provider boundary or sampler state is invalid."""


def _load_sibling_module(*, name: str, filename: str) -> ModuleType:
    """Reuse an already imported sibling to preserve its concrete class IDs."""

    path = Path(__file__).resolve().parents[1] / filename
    wanted = path.resolve()
    for module in tuple(sys.modules.values()):
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str):
            continue
        try:
            if Path(module_file).resolve() == wanted:
                return module
        except OSError:
            continue
    spec = importlib.util.spec_from_file_location(name, wanted)
    if spec is None or spec.loader is None:
        raise V023ProviderBridgeError(f"cannot load sibling seam: {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_TARGET = _load_sibling_module(
    name="v023_target_batch_adapter_for_provider_bridge",
    filename="multi-catfish-v023-target-batch-adapter/target_batch_adapter.py",
)
_ORCHESTRATOR = _load_sibling_module(
    name="v023_five_arm_orchestrator_for_provider_bridge",
    filename="multi-catfish-v023-five-arm-learner-orchestrator/v023_five_arm_learner_orchestrator.py",
)


@dataclass(frozen=True, slots=True)
class C3SourceBinding:
    """One explicitly identified typed C3 sampled-batch source.

    ``source_id`` is intentionally supplied by the C3 producer.  It must be
    the stable authenticated record/sidecar identity once that producer
    receipt exists; no C1/C2 filename is substituted for it here.
    """

    source: str
    source_id: str
    inputs: object

    def __post_init__(self) -> None:
        if self.source not in SOURCE_ORDER:
            raise ValueError(f"C3 source must be one of {SOURCE_ORDER}")
        if (
            not isinstance(self.source_id, str)
            or not self.source_id
            or self.source_id != self.source_id.strip()
        ):
            raise ValueError("C3 source_id must be a nonempty trimmed identity")


@dataclass(frozen=True, slots=True)
class _ProviderEntry:
    """A source-local immutable descriptor; it is never exposed directly."""

    file_id: str
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch | LCSRSC3SampledBatch
    c3_surfaces: tuple[LCSRSAnchorSurface, ...] = ()
    c3_targets: tuple[np.ndarray, ...] = ()


def _immutable_copy(value: np.ndarray, *, dtype: np.dtype[Any]) -> np.ndarray:
    copied = np.array(value, dtype=dtype, copy=True, order="C")
    copied.setflags(write=False)
    return copied


def _copy_pair_batch(batch: EEAxisPairBatch) -> EEAxisPairBatch:
    """Return a byte-preserving, read-only defensive copy of one typed batch."""

    return EEAxisPairBatch(
        states=_immutable_copy(np.asarray(batch.states), dtype=np.dtype(np.float32)),
        reference_actions=_immutable_copy(
            np.asarray(batch.reference_actions), dtype=np.dtype(np.int64)
        ),
        candidate_actions=_immutable_copy(
            np.asarray(batch.candidate_actions), dtype=np.dtype(np.int64)
        ),
        target_surplus_bits=_immutable_copy(
            np.asarray(batch.target_surplus_bits), dtype=np.dtype(np.float64)
        ),
        action_masks=_immutable_copy(
            np.asarray(batch.action_masks), dtype=np.dtype(np.bool_)
        ),
    )


def _copy_normalized_c2_batch(
    batch: EEAxisV014NormalizedPairBatch,
) -> EEAxisV014NormalizedPairBatch:
    return EEAxisV014NormalizedPairBatch(
        states=_immutable_copy(np.asarray(batch.states), dtype=np.dtype(np.float32)),
        reference_actions=_immutable_copy(np.asarray(batch.reference_actions), dtype=np.dtype(np.int64)),
        candidate_actions=_immutable_copy(np.asarray(batch.candidate_actions), dtype=np.dtype(np.int64)),
        normalized_target_deltas=_immutable_copy(
            np.asarray(batch.normalized_target_deltas), dtype=np.dtype(np.float64)
        ),
        action_masks=_immutable_copy(np.asarray(batch.action_masks), dtype=np.dtype(np.bool_)),
    )


def _copy_c3_batch(batch: LCSRSC3SampledBatch) -> LCSRSC3SampledBatch:
    """Return the same sampled rows in fresh read-only current typed storage."""

    return LCSRSC3SampledBatch(
        anchor_indices=np.asarray(batch.anchor_indices),
        row_classes=np.asarray(batch.row_classes),
        user_indices=np.asarray(batch.user_indices),
        action_indices=np.asarray(batch.action_indices),
        normalized_targets=np.asarray(batch.normalized_targets),
    )


def _copy_c3_targets(targets: tuple[np.ndarray, ...]) -> tuple[np.ndarray, ...]:
    """Retain selected C3 labels separately from physical feature surfaces."""

    return tuple(
        _immutable_copy(target, dtype=np.dtype(np.float32)) for target in targets
    )


def _all_read_only(batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch) -> bool:
    return all(
        not np.asarray(getattr(batch, field)).flags.writeable
        for field in (
            "states",
            "reference_actions",
            "candidate_actions",
            "target_surplus_bits" if isinstance(batch, EEAxisPairBatch) else "normalized_target_deltas",
            "action_masks",
        )
    )


class V023ProviderOrchestratorBridge:
    """A deterministic, plan-bounded provider for C1/C2/C3 five-arm updates.

    A call round is closed and ordered: ``neutral`` then ``informed`` for one
    route, followed by the next route in ``C1 -> C2 -> C3``.  Cursors are
    still stored per ``(route, source)`` so the state cannot collapse source
    identities or route-local update positions.  C1/C2 reuse the authenticated
    aggregate panel exactly once per source-training epoch, matching the frozen
    500-epoch learner convention.  C3 consumes an exact precomputed schedule.
    Every route exhausts at the declared epoch budget rather than wrapping or
    fabricating another batch.
    """

    def __init__(
        self,
        target_artifact: object,
        *,
        c3_neutral: C3SourceBinding,
        c3_informed: C3SourceBinding,
        planned_source_training_epochs: int,
    ) -> None:
        if not isinstance(target_artifact, _TARGET.V023TargetArtifact):
            raise TypeError("target_artifact must be an authenticated V023TargetArtifact")

        # Re-open the root rather than trusting a caller-created dataclass.
        # This also fails if a formerly authenticated file changed after load.
        self._target_artifact = _TARGET.load_completed_target_artifact(
            target_artifact.root
        )
        if (
            isinstance(planned_source_training_epochs, bool)
            or not isinstance(planned_source_training_epochs, int)
            or planned_source_training_epochs < 1
        ):
            raise ValueError("planned_source_training_epochs must be a positive integer")
        self._planned_source_training_epochs = planned_source_training_epochs
        self._entries: dict[tuple[str, str], tuple[_ProviderEntry, ...]] = {}
        self._source_members: dict[str, list[str]] = {}
        for source in SOURCE_ORDER:
            mode_inputs = self._target_artifact.for_mode(source)
            for route in ("C1", "C2"):
                members = self._c1c2_entries(
                    mode_inputs, route=route, source=source
                )
                aggregate = (
                    mode_inputs.c1_pair_batch
                    if route == "C1"
                    else mode_inputs.c2_pair_batch
                )
                if (
                    (route == "C1" and not isinstance(aggregate, EEAxisPairBatch))
                    or (route == "C2" and not isinstance(aggregate, EEAxisV014NormalizedPairBatch))
                    or not _all_read_only(aggregate)
                ):
                    raise V023ProviderBridgeError(
                        f"{route}/{source} authenticated aggregate panel is invalid"
                    )
                panel_id = self._panel_id(
                    route=route,
                    source=source,
                    member_ids=tuple(entry.file_id for entry in members),
                    batch=aggregate,
                )
                self._entries[(route, source)] = (
                    _ProviderEntry(file_id=panel_id, batch=aggregate),
                )
                self._source_members[f"{route}:{source}"] = [
                    entry.file_id for entry in members
                ]

        if not isinstance(c3_neutral, C3SourceBinding) or not isinstance(
            c3_informed, C3SourceBinding
        ):
            raise TypeError("C3 sources must be explicit C3SourceBinding values")
        bindings = {binding.source: binding for binding in (c3_neutral, c3_informed)}
        if set(bindings) != set(SOURCE_ORDER) or len(bindings) != 2:
            raise V023ProviderBridgeError(
                "C3 requires one explicit neutral and one explicit informed binding"
            )
        if bindings["neutral"].source_id == bindings["informed"].source_id:
            raise V023ProviderBridgeError(
                "C3 informed and neutral source identities must be distinct"
            )
        for source in SOURCE_ORDER:
            binding = bindings[source]
            entries = self._c3_entries(binding, source=source)
            if len(entries) != self._planned_source_training_epochs:
                raise V023ProviderBridgeError(
                    f"C3/{source} sampled-batch count must equal the declared "
                    "source-training epoch budget"
                )
            self._entries[("C3", source)] = entries
            self._source_members[f"C3:{source}"] = [binding.source_id]

        self._positions = {key: 0 for key in self._entries}
        self._next_update_cursor = 0
        self._next_source_index = 0
        self._source_files = {
            f"{route}:{source}": [entry.file_id for entry in self._entries[(route, source)]]
            for route in ROUTE_ORDER
            for source in SOURCE_ORDER
        }

    @staticmethod
    def _panel_id(
        *,
        route: str,
        source: str,
        member_ids: tuple[str, ...],
        batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch,
    ) -> str:
        """Bind one aggregate batch to its ordered manifest-listed members."""

        digest = hashlib.sha256()
        digest.update(b"MCRL_V023_AUTHENTICATED_C1C2_PANEL_V1\0")
        digest.update(route.encode("ascii"))
        digest.update(b"\0")
        digest.update(source.encode("ascii"))
        for member in member_ids:
            digest.update(b"\0")
            digest.update(member.encode("ascii"))
        for field in (
            "states",
            "reference_actions",
            "candidate_actions",
            "target_surplus_bits" if isinstance(batch, EEAxisPairBatch) else "normalized_target_deltas",
            "action_masks",
        ):
            value = np.ascontiguousarray(np.asarray(getattr(batch, field)))
            digest.update(b"\0")
            digest.update(field.encode("ascii"))
            digest.update(value.dtype.str.encode("ascii"))
            digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
            digest.update(value.tobytes())
        return f"{route.lower()}-{source}-panel-{digest.hexdigest()}"

    @staticmethod
    def _c1c2_entries(
        mode_inputs: object,
        *,
        route: str,
        source: str,
    ) -> tuple[_ProviderEntry, ...]:
        if not isinstance(mode_inputs, _TARGET.V023ModeInputs):
            raise TypeError("C1/C2 inputs must be actual V023ModeInputs")
        if mode_inputs.mode != source:
            raise V023ProviderBridgeError(
                "C1/C2 mode inputs cannot be retagged to another source"
            )
        datasets = (
            mode_inputs.c1_datasets if route == "C1" else mode_inputs.c2_datasets
        )
        route_batches = (
            mode_inputs.c1_route_batches
            if route == "C1"
            else mode_inputs.c2_route_batches
        )
        if not datasets or len(datasets) != len(route_batches):
            raise V023ProviderBridgeError(
                f"{route}/{source} has no one-to-one authenticated file batches"
            )
        result: list[_ProviderEntry] = []
        filenames: set[str] = set()
        for index, (entry, route_batch) in enumerate(
            zip(datasets, route_batches, strict=True)
        ):
            if (
                not isinstance(entry, _TARGET.V023DatasetEntry)
                or entry.route != route
                or entry.mode != source
                or entry.route_batch is not route_batch
                or getattr(route_batch, "route", None) != route
                or (
                    route == "C1"
                    and not isinstance(getattr(route_batch, "pair_batch", None), EEAxisPairBatch)
                )
                or (
                    route == "C2"
                    and not isinstance(
                        getattr(route_batch, "pair_batch", None),
                        EEAxisV014NormalizedPairBatch,
                    )
                )
            ):
                raise V023ProviderBridgeError(
                    f"{route}/{source} file {index} lost its typed route identity"
                )
            path = entry.path
            if (
                not isinstance(path, Path)
                or path.name != f"{route.lower()}-{source}-world-{entry.world}.json"
                or path.name in filenames
            ):
                raise V023ProviderBridgeError(
                    f"{route}/{source} does not preserve a unique manifest filename"
                )
            filenames.add(path.name)
            try:
                route_batch.verify()
            except Exception as error:
                raise V023ProviderBridgeError(
                    f"{route}/{source} manifest-listed batch failed verification"
                ) from error
            pair_batch = route_batch.pair_batch
            if not _all_read_only(pair_batch):
                raise V023ProviderBridgeError(
                    f"{route}/{source} authenticated batch is mutable"
                )
            result.append(_ProviderEntry(file_id=path.name, batch=pair_batch))
        return tuple(result)

    @staticmethod
    def _c3_entries(
        binding: C3SourceBinding,
        *,
        source: str,
    ) -> tuple[_ProviderEntry, ...]:
        if not isinstance(binding, C3SourceBinding) or binding.source != source:
            raise V023ProviderBridgeError(
                "C3 binding source disagrees with its requested source identity"
            )
        if not isinstance(binding.inputs, _TARGET.V023C3Inputs):
            raise TypeError("C3 binding inputs must be actual V023C3Inputs")
        # Validate every typed cell against the injected surface again.  This
        # does not sample or reorder; it only rejects malformed typed inputs.
        verified = _TARGET.load_lcsrs_c3_inputs(
            binding.inputs.surfaces,
            binding.inputs.sampled_batches,
            normalized_targets_by_anchor=binding.inputs.normalized_targets_by_anchor,
        )
        if not verified.surfaces or not verified.sampled_batches:
            raise V023ProviderBridgeError(
                f"C3/{source} requires explicit typed surfaces and sampled batches"
            )
        surfaces = tuple(verified.surfaces)
        selected_targets = _copy_c3_targets(verified.normalized_targets_by_anchor)
        if any(not isinstance(item, LCSRSAnchorSurface) for item in surfaces):
            raise V023ProviderBridgeError("C3 surface class drifted")
        entries: list[_ProviderEntry] = []
        for batch in verified.sampled_batches:
            if not isinstance(batch, LCSRSC3SampledBatch):
                raise V023ProviderBridgeError("C3 sampled batch class drifted")
            entries.append(
                _ProviderEntry(
                    file_id=binding.source_id,
                    batch=batch,
                    c3_surfaces=surfaces,
                    c3_targets=selected_targets,
                )
            )
        return tuple(entries)

    def _expected_positions(
        self,
        *,
        update_cursor: int,
        source_index: int,
    ) -> dict[tuple[str, str], int]:
        counts = {key: 0 for key in self._entries}
        completed_cycles, remainder = divmod(update_cursor, len(ROUTE_ORDER))
        for route_index, route in enumerate(ROUTE_ORDER):
            route_count = completed_cycles + int(route_index < remainder)
            for source in SOURCE_ORDER:
                counts[(route, source)] = route_count
        if source_index:
            counts[(ROUTE_ORDER[remainder], SOURCE_ORDER[0])] += 1
        return counts

    def _validate_next_request(
        self,
        *,
        route: str,
        source: str,
        update_cursor: int,
    ) -> None:
        if route not in ROUTE_ORDER or source not in SOURCE_ORDER:
            raise V023ProviderBridgeError("route/source is outside the closed V023 order")
        if type(update_cursor) is not int or update_cursor < 0:
            raise TypeError("update_cursor must be a nonnegative exact integer")
        expected_route = ROUTE_ORDER[self._next_update_cursor % len(ROUTE_ORDER)]
        expected_source = SOURCE_ORDER[self._next_source_index]
        if (
            update_cursor != self._next_update_cursor
            or route != expected_route
            or source != expected_source
        ):
            raise V023ProviderBridgeError(
                "provider request violates the deterministic route/source cursor order"
            )

    def next_batch(self, *, route: str, source: str, update_cursor: int) -> object:
        """Return one new typed wrapper without mutating or sharing batch storage."""

        self._validate_next_request(
            route=route, source=source, update_cursor=update_cursor
        )
        key = (route, source)
        position = self._positions[key]
        records = self._entries[key]
        if position >= self._planned_source_training_epochs:
            raise V023ProviderBridgeError(
                f"{route}/{source} declared epoch schedule exhausted at cursor {position}"
            )
        record = records[0] if route in {"C1", "C2"} else records[position]
        batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch | LCSRSC3SampledBatch
        if route == "C1":
            assert isinstance(record.batch, EEAxisPairBatch)
            batch = _copy_pair_batch(record.batch)
        elif route == "C2":
            assert isinstance(record.batch, EEAxisV014NormalizedPairBatch)
            batch = _copy_normalized_c2_batch(record.batch)
        else:
            assert isinstance(record.batch, LCSRSC3SampledBatch)
            batch = _copy_c3_batch(record.batch)
        self._positions[key] = position + 1
        if self._next_source_index + 1 == len(SOURCE_ORDER):
            self._next_source_index = 0
            self._next_update_cursor += 1
        else:
            self._next_source_index += 1
        return _ORCHESTRATOR.ProvidedRouteBatch(
            route=route,
            source=source,
            file_id=record.file_id,
            batch=batch,
            c3_surfaces=record.c3_surfaces,
        )

    def sampler_state(self) -> Mapping[str, Any]:
        """Return an independent, strict state capable of exact next-batch resume."""

        return deepcopy(
            {
                "schema": BRIDGE_SCHEMA,
                "route_order": list(ROUTE_ORDER),
                "source_order": list(SOURCE_ORDER),
                "planned_source_training_epochs": self._planned_source_training_epochs,
                "source_files": self._source_files,
                "source_members": self._source_members,
                "cursors": {
                    f"{route}:{source}": self._positions[(route, source)]
                    for route in ROUTE_ORDER
                    for source in SOURCE_ORDER
                },
                "next_update_cursor": self._next_update_cursor,
                "next_source_index": self._next_source_index,
            }
        )

    def load_sampler_state(self, state: Mapping[str, Any]) -> None:
        """Restore only an exact compatible source-local cursor state."""

        if not isinstance(state, Mapping) or set(state) != {
            "schema",
            "route_order",
            "source_order",
            "planned_source_training_epochs",
            "source_files",
            "source_members",
            "cursors",
            "next_update_cursor",
            "next_source_index",
        }:
            raise V023ProviderBridgeError("provider sampler state schema drifted")
        if (
            state["schema"] != BRIDGE_SCHEMA
            or state["route_order"] != list(ROUTE_ORDER)
            or state["source_order"] != list(SOURCE_ORDER)
            or state["planned_source_training_epochs"]
            != self._planned_source_training_epochs
            or state["source_files"] != self._source_files
            or state["source_members"] != self._source_members
        ):
            raise V023ProviderBridgeError("provider sampler state source identity drifted")
        update_cursor = state["next_update_cursor"]
        source_index = state["next_source_index"]
        if (
            type(update_cursor) is not int
            or update_cursor < 0
            or type(source_index) is not int
            or source_index not in range(len(SOURCE_ORDER))
        ):
            raise V023ProviderBridgeError("provider sampler state cursor is invalid")
        raw_cursors = state["cursors"]
        expected_keys = {
            f"{route}:{source}" for route in ROUTE_ORDER for source in SOURCE_ORDER
        }
        if not isinstance(raw_cursors, Mapping) or set(raw_cursors) != expected_keys:
            raise V023ProviderBridgeError("provider sampler state lacks source-local cursors")
        positions: dict[tuple[str, str], int] = {}
        for route in ROUTE_ORDER:
            for source in SOURCE_ORDER:
                value = raw_cursors[f"{route}:{source}"]
                if type(value) is not int or value < 0:
                    raise V023ProviderBridgeError("provider sampler position is invalid")
                if value > self._planned_source_training_epochs:
                    raise V023ProviderBridgeError("provider sampler position exceeds source")
                positions[(route, source)] = value
        if positions != self._expected_positions(
            update_cursor=update_cursor, source_index=source_index
        ):
            raise V023ProviderBridgeError("provider sampler cursors are not route/source exact")
        self._positions = positions
        self._next_update_cursor = update_cursor
        self._next_source_index = source_index


# Re-export the existing protocol surface so consumers can make a concrete
# runtime assertion without importing an unrelated sibling path themselves.
DeterministicRouteBatchProvider = _ORCHESTRATOR.DeterministicRouteBatchProvider
ProvidedRouteBatch = _ORCHESTRATOR.ProvidedRouteBatch
V023TargetArtifact = _TARGET.V023TargetArtifact
V023ModeInputs = _TARGET.V023ModeInputs
V023C3Inputs = _TARGET.V023C3Inputs
load_completed_target_artifact = _TARGET.load_completed_target_artifact
load_lcsrs_c3_inputs = _TARGET.load_lcsrs_c3_inputs


__all__ = [
    "BRIDGE_SCHEMA",
    "ROUTE_ORDER",
    "SOURCE_ORDER",
    "C3SourceBinding",
    "DeterministicRouteBatchProvider",
    "ProvidedRouteBatch",
    "V023C3Inputs",
    "V023ModeInputs",
    "V023ProviderBridgeError",
    "V023ProviderOrchestratorBridge",
    "V023TargetArtifact",
    "load_completed_target_artifact",
    "load_lcsrs_c3_inputs",
]
