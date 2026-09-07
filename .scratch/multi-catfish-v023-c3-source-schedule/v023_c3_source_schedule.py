"""In-memory V0.23 C3 informed/equal-budget-neutral source schedule.

This standalone seam consumes only already-authenticated ``LCSRSAnchorRecord``
values and an explicit, independently verified R7 GO binding.  It constructs
the frozen global within-world matched placebo, then precomputes paired current
``LCSRSC3SampledBatch`` values.  A pair shares every anchor/class/user/action
draw; only a SUPPORTED label can differ.

The module has no simulator, learner-update, TEST, persistence, or launcher
entry point.  In particular, it never manufactures neutral
``LCSRSAnchorSurface`` values: those surfaces contain physical pair targets.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorRecord,
    LCSRSAnchorSurface,
    LCSRSPairTargets,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRS_C3_BATCH_SIZE,
    LCSRS_C3_LEARNER_CONFIG,
    LCSRS_C3_LEARNER_CONFIG_SHA256,
    LCSRSC3ClassBalancedSampler,
    LCSRSC3SampledBatch,
)
from mcrl.runtime.ee_axis_lcsrs_c3_placebo import (
    LCSRS_C3_PLACEBO_MIN_COVERAGE,
    LCSRS_C3_PLACEBO_SCHEMA,
    LCSRSMatchedPlacebo,
    build_lcsrs_matched_placebo,
)


SOURCE_SCHEDULE_SCHEMA = (
    "multi-catfish-mcrl-v023-c3-informed-neutral-source-schedule-v1"
)
SOURCE_SCHEDULE_STATUS = "PRECOMPUTED_IN_MEMORY"
SOURCE_SCHEDULE_CLAIM_CEILING = (
    "IMPLEMENTATION_ONLY_SOURCE_SCHEDULE_NO_SIMULATOR_NO_LEARNER_UPDATE_"
    "NO_TEST_NO_ARTIFACT_WRITE"
)

R7_FINAL_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-r7-balanced-final-verification-v1"
)
R7_FINAL_STATUS = "PASS_FINAL_INTEGRITY"
R7_INTEGRITY_STATUS = "VERIFIED"
R7_GO_DECISION = "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7"
R7_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_"
    "NO_EFFICACY"
)
R7_SPLIT = "TRAIN_DEVELOPMENT"
R7_WORLDS = tuple(range(2026121801, 2026121809))
R7_CONTEXT_STATUSES = (
    "CONTEXT_DIAGNOSTICS_PASS",
    "HOLD_C1",
    "HOLD_C2",
    "HOLD_C1_C2",
)
R7_BASE_CONTRACT_SHA256 = (
    "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
)
R7_CONTRACT_SHA256 = (
    "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
)
R7_EXECUTION_ADDENDUM_SHA256 = (
    "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
)
PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
PLACEBO_KEY_SHA256 = (
    "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
)
FORMAL_SOURCE_TRAINING_EPOCH_BUDGETS = (100, 500)
SCHEDULE_RNG = "numpy-pcg64"
SCHEDULE_SEED_DOMAIN = "MCRL_V023_LCSRS_C3_PAIRED_SOURCE_SCHEDULE_PCG64_V1"

_RECORD_PANEL_DOMAIN = "MCRL_V023_LCSRS_C3_RECORD_PANEL_V1"
_TARGET_PANEL_DOMAIN = "MCRL_V023_LCSRS_C3_TARGET_PANEL_V1"
_BATCH_DOMAIN = "MCRL_V023_LCSRS_C3_SAMPLED_BATCH_V1"
_SOURCE_DOMAIN = "MCRL_V023_LCSRS_C3_SOURCE_IDENTITY_V1"


class V023C3SourceScheduleError(MCRLContractError):
    """The post-R7 C3 source schedule violated a frozen boundary."""


def canonical_bytes(value: object) -> bytes:
    """Return the compact sorted-key ASCII encoding used by schedule receipts."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V023C3SourceScheduleError(
            "schedule value is not finite canonical ASCII JSON"
        ) from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023C3SourceScheduleError(f"{field} must be a lowercase SHA-256")
    return value


def _array_payload(value: object) -> dict[str, object]:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(b"MCRL_V023_ARRAY_V1\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(b"\0")
    digest.update(canonical_bytes(list(array.shape)))
    digest.update(b"\0")
    digest.update(array.tobytes(order="C"))
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": digest.hexdigest(),
    }


def _batch_payload(batch: LCSRSC3SampledBatch) -> dict[str, object]:
    if type(batch) is not LCSRSC3SampledBatch:
        raise V023C3SourceScheduleError(
            "schedule batch must use the actual current LCSRSC3SampledBatch class"
        )
    arrays = {
        name: _array_payload(getattr(batch, name))
        for name in (
            "anchor_indices",
            "row_classes",
            "user_indices",
            "action_indices",
            "normalized_targets",
        )
    }
    body = {"domain": _BATCH_DOMAIN, "rows": batch.rows, "arrays": arrays}
    return {**body, "sha256": canonical_sha256(body)}


def _draw_payload(batch: LCSRSC3SampledBatch) -> dict[str, object]:
    arrays = {
        name: _array_payload(getattr(batch, name))
        for name in (
            "anchor_indices",
            "row_classes",
            "user_indices",
            "action_indices",
        )
    }
    body = {
        "domain": f"{_BATCH_DOMAIN}:PAIRED_DRAW",
        "rows": batch.rows,
        "arrays": arrays,
    }
    return {**body, "sha256": canonical_sha256(body)}


def _validate_and_order_records(
    records: Sequence[LCSRSAnchorRecord],
) -> tuple[LCSRSAnchorRecord, ...]:
    try:
        supplied = tuple(records)
    except TypeError as error:
        raise V023C3SourceScheduleError(
            "records must be a finite sequence of LCSRSAnchorRecord values"
        ) from error
    if not supplied:
        raise V023C3SourceScheduleError("source schedule needs authenticated records")
    if any(type(record) is not LCSRSAnchorRecord for record in supplied):
        raise V023C3SourceScheduleError(
            "records must use the actual current LCSRSAnchorRecord class"
        )

    ordered = tuple(
        sorted(supplied, key=lambda item: (item.world_id, item.phase, item.anchor_id))
    )
    identities = tuple((item.world_id, item.anchor_id) for item in ordered)
    if len(set(identities)) != len(identities):
        raise V023C3SourceScheduleError("world/anchor record identities are not unique")
    if tuple(sorted({item.world_id for item in ordered})) != R7_WORLDS:
        raise V023C3SourceScheduleError("records do not cover the exact R7 TRAIN worlds")

    surface_digests: set[str] = set()
    for index, record in enumerate(ordered):
        surface = record.surface
        if type(surface) is not LCSRSAnchorSurface:
            raise V023C3SourceScheduleError(
                f"record {index} does not carry the current LCSRSAnchorSurface class"
            )
        if any(type(pair) is not LCSRSPairTargets for pair in surface.pairs):
            raise V023C3SourceScheduleError(
                f"record {index} does not carry current LCSRSPairTargets values"
            )
        for label, array in (
            ("surface targets", surface.normalized_targets),
            ("surface classes", surface.row_class),
            ("record q12", record.q12_values),
            *(
                (f"pair {pair_index} users", pair.user_ids)
                for pair_index, pair in enumerate(surface.pairs)
            ),
            *(
                (f"pair {pair_index} actions", pair.action_ids)
                for pair_index, pair in enumerate(surface.pairs)
            ),
            *(
                (f"pair {pair_index} targets", pair.normalized_targets_by_draw)
                for pair_index, pair in enumerate(surface.pairs)
            ),
        ):
            if np.asarray(array).flags.writeable:
                raise V023C3SourceScheduleError(
                    f"record {index} {label} lost immutability"
                )

        # Re-run the current public dataclass invariants against the live array
        # values.  This catches stale content digests or post-load target/Q12
        # mutation without copying the very large C3View token tensors.
        try:
            checked_surface = LCSRSAnchorSurface(
                view=surface.view,
                normalized_targets=surface.normalized_targets,
                row_class=surface.row_class,
                pairs=surface.pairs,
                content_digest=surface.content_digest,
            )
            LCSRSAnchorRecord(
                world_id=record.world_id,
                phase=record.phase,
                anchor_id=record.anchor_id,
                surface=checked_surface,
                q12_values=record.q12_values,
                content_digest=record.content_digest,
            )
        except Exception as error:
            raise V023C3SourceScheduleError(
                f"record {index} failed current typed reauthentication"
            ) from error

        _require_digest(record.content_digest, field=f"record {index} content_digest")
        _require_digest(surface.content_digest, field=f"record {index} surface digest")
        if surface.content_digest in surface_digests:
            raise V023C3SourceScheduleError(
                "record panel contains duplicate positional anchor surfaces"
            )
        surface_digests.add(surface.content_digest)
    return ordered


def _record_entries(records: tuple[LCSRSAnchorRecord, ...]) -> list[dict[str, object]]:
    return [
        {
            "anchor_index": index,
            "world_id": record.world_id,
            "phase": record.phase,
            "anchor_id": record.anchor_id,
            "record_content_sha256": record.content_digest,
            "surface_content_sha256": record.surface.content_digest,
            "view_content_sha256": record.surface.view.content_digest,
            "supported_rows": int(
                np.count_nonzero(record.surface.row_class == LCSRS_ROW_SUPPORTED)
            ),
        }
        for index, record in enumerate(records)
    ]


def _record_panel_sha256_from_ordered(
    records: tuple[LCSRSAnchorRecord, ...],
) -> str:
    return canonical_sha256(
        {"domain": _RECORD_PANEL_DOMAIN, "records": _record_entries(records)}
    )


def canonical_record_panel_sha256(
    records: Sequence[LCSRSAnchorRecord],
) -> str:
    """Reauthenticate, canonically order, and digest an exact R7 record panel."""

    return _record_panel_sha256_from_ordered(_validate_and_order_records(records))


@dataclass(frozen=True, slots=True)
class R7GoDecisionBinding:
    """Explicit fields copied from an independently authenticated R7 result.

    This is deliberately not constructible from the pre-outcome launch token.
    ``record_panel_sha256`` is computed from the records reconstructed through
    the authenticated source manifest and closes the otherwise missing link
    between the final result and these in-memory objects.
    """

    schema: str
    status: str
    integrity_status: str
    c3_decision: str
    context_status: str
    claim_ceiling: str
    split: str
    worlds: tuple[int, ...]
    source_count: int
    fit_count: int
    composition_count: int
    base_contract_sha256: str
    contract_sha256: str
    execution_addendum_sha256: str
    launch_decision_sha256: str
    code_manifest_sha256: str
    preflight_manifest_sha256: str
    launch_manifest_sha256: str
    source_manifest_sha256: str
    gate_result_sha256: str
    record_panel_sha256: str
    test_split_opened: bool
    episode_training: bool
    scientific_claim: bool
    no_rescue: bool
    no_scientific_token_before_integrity: bool

    def verify(self) -> None:
        exact = {
            "schema": (self.schema, R7_FINAL_SCHEMA),
            "status": (self.status, R7_FINAL_STATUS),
            "integrity_status": (self.integrity_status, R7_INTEGRITY_STATUS),
            "c3_decision": (self.c3_decision, R7_GO_DECISION),
            "claim_ceiling": (self.claim_ceiling, R7_CLAIM_CEILING),
            "split": (self.split, R7_SPLIT),
            "worlds": (self.worlds, R7_WORLDS),
            "source_count": (self.source_count, 8),
            "fit_count": (self.fit_count, 48),
            "composition_count": (self.composition_count, 48),
            "base_contract_sha256": (
                self.base_contract_sha256,
                R7_BASE_CONTRACT_SHA256,
            ),
            "contract_sha256": (self.contract_sha256, R7_CONTRACT_SHA256),
            "execution_addendum_sha256": (
                self.execution_addendum_sha256,
                R7_EXECUTION_ADDENDUM_SHA256,
            ),
            "test_split_opened": (self.test_split_opened, False),
            "episode_training": (self.episode_training, False),
            "scientific_claim": (self.scientific_claim, False),
            "no_rescue": (self.no_rescue, True),
            "no_scientific_token_before_integrity": (
                self.no_scientific_token_before_integrity,
                True,
            ),
        }
        for field, (actual, expected) in exact.items():
            if type(actual) is not type(expected) or actual != expected:
                raise V023C3SourceScheduleError(
                    f"R7 GO binding {field} does not equal the frozen value"
                )
        if self.context_status not in R7_CONTEXT_STATUSES:
            raise V023C3SourceScheduleError("R7 GO binding context_status is unknown")
        for field in (
            "base_contract_sha256",
            "contract_sha256",
            "execution_addendum_sha256",
            "launch_decision_sha256",
            "code_manifest_sha256",
            "preflight_manifest_sha256",
            "launch_manifest_sha256",
            "source_manifest_sha256",
            "gate_result_sha256",
            "record_panel_sha256",
        ):
            _require_digest(getattr(self, field), field=f"R7 GO binding {field}")

    def to_payload(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }

    @property
    def binding_sha256(self) -> str:
        self.verify()
        return canonical_sha256(self.to_payload())


def _target_panel_payload(
    records: tuple[LCSRSAnchorRecord, ...],
    targets: tuple[np.ndarray, ...],
    *,
    source: str,
) -> dict[str, object]:
    if len(targets) != len(records):
        raise V023C3SourceScheduleError("target surface count differs from records")
    anchors: list[dict[str, object]] = []
    for index, (record, target) in enumerate(zip(records, targets, strict=True)):
        array = np.asarray(target)
        surface = record.surface
        if (
            array.dtype != np.float32
            or array.shape != surface.normalized_targets.shape
            or array.flags.writeable
            or not np.all(np.isfinite(array))
        ):
            raise V023C3SourceScheduleError(
                f"{source} target surface {index} is not immutable finite float32"
            )
        if np.any(array[surface.row_class != LCSRS_ROW_SUPPORTED] != 0.0):
            raise V023C3SourceScheduleError(
                f"{source} target surface {index} changes an R/C/MASKED zero"
            )
        anchors.append(
            {
                "anchor_index": index,
                "record_content_sha256": record.content_digest,
                "target": _array_payload(array),
            }
        )
    body = {"domain": _TARGET_PANEL_DOMAIN, "source": source, "anchors": anchors}
    return {**body, "sha256": canonical_sha256(body)}


def _mapping_payload(placebo: LCSRSMatchedPlacebo) -> list[dict[str, object]]:
    return [
        {
            "stratum": list(mapping.stratum.key()),
            "source_anchor_index": mapping.source_anchor,
            "source_user": mapping.source_user,
            "source_action": mapping.source_action,
            "destination_anchor_index": mapping.destination_anchor,
            "destination_user": mapping.destination_user,
            "destination_action": mapping.destination_action,
            "shift": mapping.shift,
        }
        for mapping in placebo.mappings
    ]


def _derive_pcg64_seed(explicit_seed: int) -> tuple[str, int]:
    if (
        isinstance(explicit_seed, bool)
        or not isinstance(explicit_seed, int)
        or not 0 <= explicit_seed < 2**64
    ):
        raise V023C3SourceScheduleError(
            "schedule_seed must be an exact unsigned 64-bit integer"
        )
    payload = {
        "domain": SCHEDULE_SEED_DOMAIN,
        "explicit_seed": explicit_seed,
        "rng": SCHEDULE_RNG,
    }
    digest = canonical_sha256(payload)
    return digest, int.from_bytes(bytes.fromhex(digest)[:16], "big")


def _source_identity(
    *,
    source: str,
    gate_binding_sha256: str,
    record_panel_sha256: str,
    target_panel_sha256: str,
    batch_schedule_sha256: str,
    placebo_sha256: str | None,
    epoch_budget: int,
    seed_derivation_sha256: str,
) -> tuple[str, str]:
    body = {
        "domain": _SOURCE_DOMAIN,
        "source": source,
        "gate_binding_sha256": gate_binding_sha256,
        "record_panel_sha256": record_panel_sha256,
        "target_panel_sha256": target_panel_sha256,
        "batch_schedule_sha256": batch_schedule_sha256,
        "placebo_sha256": placebo_sha256,
        "epoch_budget": epoch_budget,
        "seed_derivation_sha256": seed_derivation_sha256,
    }
    digest = canonical_sha256(body)
    return f"v023-c3-{source}-{digest}", digest


@dataclass(frozen=True, slots=True)
class V023C3PairedSourceSchedule:
    """Immutable paired schedule and its sealed in-memory canonical receipt."""

    records: tuple[LCSRSAnchorRecord, ...]
    surfaces: tuple[LCSRSAnchorSurface, ...]
    informed_targets_by_anchor: tuple[np.ndarray, ...]
    neutral_targets_by_anchor: tuple[np.ndarray, ...]
    informed_batches: tuple[LCSRSC3SampledBatch, ...]
    neutral_batches: tuple[LCSRSC3SampledBatch, ...]
    matched_placebo: LCSRSMatchedPlacebo
    gate_decision: R7GoDecisionBinding
    epoch_budget: int
    schedule_seed: int
    derived_pcg64_seed: int
    informed_source_id: str
    neutral_source_id: str
    record_panel_sha256: str
    paired_draw_schedule_sha256: str
    informed_batch_schedule_sha256: str
    neutral_batch_schedule_sha256: str
    canonical_receipt_bytes: bytes
    receipt_sha256: str

    @property
    def receipt(self) -> dict[str, Any]:
        """Return a fresh JSON object so callers cannot mutate the sealed bytes."""

        value = json.loads(self.canonical_receipt_bytes.decode("ascii"))
        if not isinstance(value, dict):  # pragma: no cover - construction invariant
            raise V023C3SourceScheduleError("sealed receipt root is not an object")
        return value

    def source_id(self, source: str) -> str:
        if source == "informed":
            return self.informed_source_id
        if source == "neutral":
            return self.neutral_source_id
        raise V023C3SourceScheduleError("C3 source must be informed or neutral")

    def batches_for(self, source: str) -> tuple[LCSRSC3SampledBatch, ...]:
        if source == "informed":
            return self.informed_batches
        if source == "neutral":
            return self.neutral_batches
        raise V023C3SourceScheduleError("C3 source must be informed or neutral")

    def batch_for(self, source: str, epoch_index: int) -> LCSRSC3SampledBatch:
        if (
            isinstance(epoch_index, bool)
            or not isinstance(epoch_index, int)
            or epoch_index < 0
        ):
            raise V023C3SourceScheduleError(
                "epoch_index must be a nonnegative exact integer"
            )
        if epoch_index >= self.epoch_budget:
            raise V023C3SourceScheduleError(
                f"C3 {source} schedule exhausted at epoch {epoch_index}"
            )
        return self.batches_for(source)[epoch_index]


def build_v023_c3_source_schedule(
    records: Sequence[LCSRSAnchorRecord],
    *,
    r7_go: R7GoDecisionBinding,
    epoch_budget: int,
    schedule_seed: int,
) -> V023C3PairedSourceSchedule:
    """Build exactly N paired informed/neutral batches without any update."""

    if type(r7_go) is not R7GoDecisionBinding:
        raise V023C3SourceScheduleError(
            "r7_go must be an explicit current R7GoDecisionBinding"
        )
    r7_go.verify()
    if (
        isinstance(epoch_budget, bool)
        or not isinstance(epoch_budget, int)
        or epoch_budget not in FORMAL_SOURCE_TRAINING_EPOCH_BUDGETS
    ):
        raise V023C3SourceScheduleError(
            "epoch_budget must be exactly 100 or 500 source-training epochs"
        )
    if (
        LCSRS_C3_BATCH_SIZE != 256
        or LCSRS_C3_LEARNER_CONFIG.batch_size != 256
        or LCSRS_C3_LEARNER_CONFIG.rng != SCHEDULE_RNG
        or LCSRS_C3_PLACEBO_SCHEMA
        != "multi-catfish-mcrl-v023-matched-placebo-v1"
        or LCSRS_C3_PLACEBO_MIN_COVERAGE != 0.80
        or hashlib.sha256(PLACEBO_KEY.encode("utf-8")).hexdigest()
        != PLACEBO_KEY_SHA256
    ):
        raise V023C3SourceScheduleError("current frozen learner/placebo constants drifted")

    ordered = _validate_and_order_records(records)
    record_panel_sha256 = _record_panel_sha256_from_ordered(ordered)
    if r7_go.record_panel_sha256 != record_panel_sha256:
        raise V023C3SourceScheduleError(
            "R7 GO binding record panel does not match the supplied records"
        )
    surfaces = tuple(record.surface for record in ordered)

    try:
        placebo = build_lcsrs_matched_placebo(ordered, placebo_key=PLACEBO_KEY)
    except Exception as error:
        raise V023C3SourceScheduleError(
            "frozen global within-world matched-placebo construction failed"
        ) from error
    if placebo.placebo_key_sha256 != PLACEBO_KEY_SHA256:
        raise V023C3SourceScheduleError("matched-placebo key digest drifted")
    if not placebo.meets_coverage_gate:
        raise V023C3SourceScheduleError(
            "global matched-placebo coverage is below the frozen 0.80 threshold"
        )
    if any(
        ordered[mapping.source_anchor].world_id
        != ordered[mapping.destination_anchor].world_id
        for mapping in placebo.mappings
    ):
        raise V023C3SourceScheduleError("matched-placebo mapping crosses worlds")

    informed_targets = tuple(
        np.array(surface.normalized_targets, dtype=np.float32, copy=True, order="C")
        for surface in surfaces
    )
    for target in informed_targets:
        target.setflags(write=False)
    neutral_targets = tuple(placebo.normalized_targets_by_anchor)
    for index, (surface, informed, neutral) in enumerate(
        zip(surfaces, informed_targets, neutral_targets, strict=True)
    ):
        non_supported = surface.row_class != LCSRS_ROW_SUPPORTED
        changed = informed != neutral
        if np.any(changed & non_supported):
            raise V023C3SourceScheduleError(
                f"neutral target surface {index} changes a non-SUPPORTED cell"
            )
        if np.any(informed[non_supported] != 0.0) or np.any(
            neutral[non_supported] != 0.0
        ):
            raise V023C3SourceScheduleError(
                f"target surface {index} changed an exact R/C/MASKED zero"
            )

    informed_target_payload = _target_panel_payload(
        ordered, informed_targets, source="informed"
    )
    neutral_target_payload = _target_panel_payload(
        ordered, neutral_targets, source="neutral"
    )
    seed_derivation_sha256, derived_seed = _derive_pcg64_seed(schedule_seed)
    sampler = LCSRSC3ClassBalancedSampler(surfaces, student_seed=derived_seed)
    if type(sampler.rng.bit_generator) is not np.random.PCG64:
        raise V023C3SourceScheduleError("source schedule did not instantiate PCG64")

    informed_batches: list[LCSRSC3SampledBatch] = []
    neutral_batches: list[LCSRSC3SampledBatch] = []
    schedule_entries: list[dict[str, object]] = []
    for epoch_index in range(epoch_budget):
        informed = sampler.draw(LCSRS_C3_BATCH_SIZE)
        neutral_values = np.asarray(
            [
                neutral_targets[int(anchor)][int(user), int(action)]
                for anchor, user, action in zip(
                    informed.anchor_indices.tolist(),
                    informed.user_indices.tolist(),
                    informed.action_indices.tolist(),
                    strict=True,
                )
            ],
            dtype=np.float32,
        )
        neutral = LCSRSC3SampledBatch(
            anchor_indices=informed.anchor_indices,
            row_classes=informed.row_classes,
            user_indices=informed.user_indices,
            action_indices=informed.action_indices,
            normalized_targets=neutral_values,
        )
        for field in (
            "anchor_indices",
            "row_classes",
            "user_indices",
            "action_indices",
        ):
            if not np.array_equal(getattr(informed, field), getattr(neutral, field)):
                raise V023C3SourceScheduleError(
                    f"epoch {epoch_index} informed/neutral draw identity diverged"
                )
        for row, (anchor, row_class, user, action) in enumerate(
            zip(
                informed.anchor_indices.tolist(),
                informed.row_classes.tolist(),
                informed.user_indices.tolist(),
                informed.action_indices.tolist(),
                strict=True,
            )
        ):
            expected_informed = informed_targets[int(anchor)][int(user), int(action)]
            expected_neutral = neutral_targets[int(anchor)][int(user), int(action)]
            if informed.normalized_targets[row] != expected_informed:
                raise V023C3SourceScheduleError(
                    f"epoch {epoch_index} informed sampled label drifted"
                )
            if neutral.normalized_targets[row] != expected_neutral:
                raise V023C3SourceScheduleError(
                    f"epoch {epoch_index} neutral sampled label drifted"
                )
            if row_class != int(LCSRS_ROW_SUPPORTED) and (
                informed.normalized_targets[row] != 0.0
                or neutral.normalized_targets[row] != 0.0
            ):
                raise V023C3SourceScheduleError(
                    f"epoch {epoch_index} sampled R/C zero changed"
                )
        informed_batch = _batch_payload(informed)
        neutral_batch = _batch_payload(neutral)
        draw = _draw_payload(informed)
        schedule_entries.append(
            {
                "epoch_index": epoch_index,
                "paired_draw_sha256": draw["sha256"],
                "informed_batch_sha256": informed_batch["sha256"],
                "neutral_batch_sha256": neutral_batch["sha256"],
            }
        )
        informed_batches.append(informed)
        neutral_batches.append(neutral)

    paired_draw_schedule_sha256 = canonical_sha256(
        {
            "domain": f"{_BATCH_DOMAIN}:PAIRED_DRAW_SCHEDULE",
            "entries": [entry["paired_draw_sha256"] for entry in schedule_entries],
        }
    )
    informed_batch_schedule_sha256 = canonical_sha256(
        {
            "domain": f"{_BATCH_DOMAIN}:INFORMED_SCHEDULE",
            "entries": [entry["informed_batch_sha256"] for entry in schedule_entries],
        }
    )
    neutral_batch_schedule_sha256 = canonical_sha256(
        {
            "domain": f"{_BATCH_DOMAIN}:NEUTRAL_SCHEDULE",
            "entries": [entry["neutral_batch_sha256"] for entry in schedule_entries],
        }
    )

    gate_binding_sha256 = r7_go.binding_sha256
    informed_source_id, informed_source_sha256 = _source_identity(
        source="informed",
        gate_binding_sha256=gate_binding_sha256,
        record_panel_sha256=record_panel_sha256,
        target_panel_sha256=str(informed_target_payload["sha256"]),
        batch_schedule_sha256=informed_batch_schedule_sha256,
        placebo_sha256=None,
        epoch_budget=epoch_budget,
        seed_derivation_sha256=seed_derivation_sha256,
    )
    neutral_source_id, neutral_source_sha256 = _source_identity(
        source="neutral",
        gate_binding_sha256=gate_binding_sha256,
        record_panel_sha256=record_panel_sha256,
        target_panel_sha256=str(neutral_target_payload["sha256"]),
        batch_schedule_sha256=neutral_batch_schedule_sha256,
        placebo_sha256=placebo.content_digest,
        epoch_budget=epoch_budget,
        seed_derivation_sha256=seed_derivation_sha256,
    )
    if informed_source_id == neutral_source_id:
        raise V023C3SourceScheduleError("informed and neutral source identities alias")

    mappings = _mapping_payload(placebo)
    world_coverage: list[dict[str, object]] = []
    eligible_by_world = {world: 0 for world in R7_WORLDS}
    total_by_world = {world: 0 for world in R7_WORLDS}
    for record in ordered:
        total_by_world[record.world_id] += int(
            np.count_nonzero(record.surface.row_class == LCSRS_ROW_SUPPORTED)
        )
    for mapping in placebo.mappings:
        eligible_by_world[ordered[mapping.destination_anchor].world_id] += 1
    for world in R7_WORLDS:
        total = total_by_world[world]
        eligible = eligible_by_world[world]
        world_coverage.append(
            {
                "world": world,
                "eligible_supported_rows": eligible,
                "total_supported_rows": total,
                "coverage": eligible / total,
                "coverage_hex": float(eligible / total).hex(),
            }
        )

    body: dict[str, object] = {
        "schema": SOURCE_SCHEDULE_SCHEMA,
        "status": SOURCE_SCHEDULE_STATUS,
        "claim_ceiling": SOURCE_SCHEDULE_CLAIM_CEILING,
        "gate_decision": {
            **r7_go.to_payload(),
            "binding_sha256": gate_binding_sha256,
        },
        "worlds": list(R7_WORLDS),
        "records": _record_entries(ordered),
        "record_panel_sha256": record_panel_sha256,
        "target_surfaces": {
            "informed": informed_target_payload,
            "neutral": neutral_target_payload,
            "original_typed_surface_count": len(surfaces),
            "neutral_lcsrs_anchor_surfaces_constructed": False,
            "differences_limited_to_supported": True,
            "reference_control_masked_targets_exact_zero": True,
        },
        "matched_placebo": {
            "schema": LCSRS_C3_PLACEBO_SCHEMA,
            "key": PLACEBO_KEY,
            "key_sha256": PLACEBO_KEY_SHA256,
            "content_sha256": placebo.content_digest,
            "mapping_count": len(mappings),
            "mappings_sha256": canonical_sha256(mappings),
            "eligible_supported_rows": placebo.eligible_supported_rows,
            "total_supported_rows": placebo.total_supported_rows,
            "coverage": placebo.coverage,
            "coverage_hex": float(placebo.coverage).hex(),
            "minimum_coverage": LCSRS_C3_PLACEBO_MIN_COVERAGE,
            "minimum_coverage_hex": float(LCSRS_C3_PLACEBO_MIN_COVERAGE).hex(),
            "meets_coverage_gate": True,
            "per_world": world_coverage,
            "world_crossing_count": 0,
        },
        "sampling": {
            "rng": SCHEDULE_RNG,
            "bit_generator": "PCG64",
            "seed_domain": SCHEDULE_SEED_DOMAIN,
            "explicit_seed": schedule_seed,
            "seed_derivation_sha256": seed_derivation_sha256,
            "derived_pcg64_seed_uint128": str(derived_seed),
            "learner_config_sha256": LCSRS_C3_LEARNER_CONFIG_SHA256,
            "batch_size": LCSRS_C3_BATCH_SIZE,
            "paired_draw_identity": "anchor-class-user-action",
        },
        "source_training_epoch_budget": epoch_budget,
        "batch_schedule": {
            "batch_count_by_source": {
                "informed": len(informed_batches),
                "neutral": len(neutral_batches),
            },
            "entries": schedule_entries,
            "paired_draw_schedule_sha256": paired_draw_schedule_sha256,
            "informed_batch_schedule_sha256": informed_batch_schedule_sha256,
            "neutral_batch_schedule_sha256": neutral_batch_schedule_sha256,
        },
        "sources": {
            "informed": {
                "source_id": informed_source_id,
                "source_sha256": informed_source_sha256,
            },
            "neutral": {
                "source_id": neutral_source_id,
                "source_sha256": neutral_source_sha256,
            },
        },
        "boundaries": {
            "simulator_run": False,
            "learner_update": False,
            "model_fit": False,
            "test_split_opened": False,
            "episode_training": False,
            "artifact_write": False,
        },
    }
    receipt_sha256 = canonical_sha256(body)
    sealed_receipt = {**body, "receipt_sha256": receipt_sha256}
    receipt_bytes = canonical_bytes(sealed_receipt)

    return V023C3PairedSourceSchedule(
        records=ordered,
        surfaces=surfaces,
        informed_targets_by_anchor=informed_targets,
        neutral_targets_by_anchor=neutral_targets,
        informed_batches=tuple(informed_batches),
        neutral_batches=tuple(neutral_batches),
        matched_placebo=placebo,
        gate_decision=r7_go,
        epoch_budget=epoch_budget,
        schedule_seed=schedule_seed,
        derived_pcg64_seed=derived_seed,
        informed_source_id=informed_source_id,
        neutral_source_id=neutral_source_id,
        record_panel_sha256=record_panel_sha256,
        paired_draw_schedule_sha256=paired_draw_schedule_sha256,
        informed_batch_schedule_sha256=informed_batch_schedule_sha256,
        neutral_batch_schedule_sha256=neutral_batch_schedule_sha256,
        canonical_receipt_bytes=receipt_bytes,
        receipt_sha256=receipt_sha256,
    )


__all__ = [
    "FORMAL_SOURCE_TRAINING_EPOCH_BUDGETS",
    "PLACEBO_KEY",
    "PLACEBO_KEY_SHA256",
    "R7GoDecisionBinding",
    "R7_BASE_CONTRACT_SHA256",
    "R7_CLAIM_CEILING",
    "R7_CONTRACT_SHA256",
    "R7_EXECUTION_ADDENDUM_SHA256",
    "R7_FINAL_SCHEMA",
    "R7_FINAL_STATUS",
    "R7_GO_DECISION",
    "R7_INTEGRITY_STATUS",
    "R7_SPLIT",
    "R7_WORLDS",
    "SCHEDULE_SEED_DOMAIN",
    "SOURCE_SCHEDULE_CLAIM_CEILING",
    "SOURCE_SCHEDULE_SCHEMA",
    "SOURCE_SCHEDULE_STATUS",
    "V023C3PairedSourceSchedule",
    "V023C3SourceScheduleError",
    "build_v023_c3_source_schedule",
    "canonical_bytes",
    "canonical_record_panel_sha256",
    "canonical_sha256",
]
