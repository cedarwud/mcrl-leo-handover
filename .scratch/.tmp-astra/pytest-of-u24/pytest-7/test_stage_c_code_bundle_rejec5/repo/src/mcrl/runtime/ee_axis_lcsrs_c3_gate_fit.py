"""Fold-safe fit and held-out row evaluation for the V0.23 LC-SRS gate.

The physical source adapter owns simulator reconstruction and composition.
This module owns the narrower learner boundary: exact leave-one-world-out
partitioning, matched-placebo construction, the fixed 2,000-update fit, and
prediction metrics against unchanged held-out targets.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import struct
from typing import Mapping, Sequence

import numpy as np
import torch

from ..algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_dataset import (
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorRecord,
)
from .ee_axis_lcsrs_c3_gate_metrics import (
    SignAccuracy,
    sign_accuracy,
    tie_aware_spearman,
)
from .ee_axis_lcsrs_c3_learner import (
    LCSRSC3FitReceipt,
    fit_lcsrs_c3_source,
)
from .ee_axis_lcsrs_c3_placebo import (
    LCSRSMatchedPlacebo,
    build_lcsrs_matched_placebo,
)


V023_GATE_WORLDS = tuple(range(2026121705, 2026121713))
V023_STUDENT_SEEDS = (2026135101, 2026135102, 2026135103)
V023_PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
V023_PLACEBO_KEY_SHA256 = (
    "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
)


class LCSRSC3GateFitError(MCRLContractError):
    """A fold, source, prediction, or fit violates the frozen V0.23 gate."""


def _digest_text(digest: "hashlib._Hash", value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)


def _prediction_digest(
    identities: tuple[tuple[int, str, int, int], ...],
    predictions: np.ndarray,
    targets: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-heldout-predictions-v1")
    for world, anchor, user, action in identities:
        digest.update(struct.pack(">QII", world, user, action))
        _digest_text(digest, anchor)
    for name, array in (("prediction", predictions), ("target", targets)):
        value = np.ascontiguousarray(array, dtype=np.float64)
        _digest_text(digest, name)
        digest.update(value.dtype.str.encode("ascii"))
        digest.update(struct.pack(">I", value.size))
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _verified_records(
    records_by_world: Mapping[int, Sequence[LCSRSAnchorRecord]],
) -> dict[int, tuple[LCSRSAnchorRecord, ...]]:
    if set(records_by_world) != set(V023_GATE_WORLDS):
        raise LCSRSC3GateFitError("source panel is not the exact frozen eight worlds")
    result: dict[int, tuple[LCSRSAnchorRecord, ...]] = {}
    identities: set[tuple[int, str]] = set()
    for world in V023_GATE_WORLDS:
        records = tuple(
            sorted(
                records_by_world[world],
                key=lambda record: (record.phase, record.anchor_id),
            )
        )
        if not records:
            raise LCSRSC3GateFitError(f"world {world} has no retained fitting anchor")
        for record in records:
            if not isinstance(record, LCSRSAnchorRecord):
                raise LCSRSC3GateFitError("source panel contains a non-anchor record")
            if record.world_id != world:
                raise LCSRSC3GateFitError("anchor world disagrees with source partition")
            identity = (world, record.anchor_id)
            if identity in identities:
                raise LCSRSC3GateFitError("source panel repeats a world/anchor identity")
            identities.add(identity)
            try:
                record.surface.view.verify()
                LCSRSAnchorRecord(
                    world_id=record.world_id,
                    phase=record.phase,
                    anchor_id=record.anchor_id,
                    surface=record.surface,
                    q12_values=record.q12_values,
                    content_digest=record.content_digest,
                )
            except (MCRLContractError, TypeError, ValueError) as error:
                raise LCSRSC3GateFitError(
                    f"source anchor failed reconstruction: {error}"
                ) from error
        result[world] = records
    return result


@dataclass(frozen=True)
class LCSRSC3FoldSource:
    """One exact seven-world fitting source and untouched held-out world."""

    held_out_world: int
    training_records: tuple[LCSRSAnchorRecord, ...]
    held_out_records: tuple[LCSRSAnchorRecord, ...]
    matched_placebo: LCSRSMatchedPlacebo

    @property
    def placebo_coverage(self) -> float:
        return self.matched_placebo.coverage


def prepare_lcsrs_loo_fold(
    records_by_world: Mapping[int, Sequence[LCSRSAnchorRecord]],
    *,
    held_out_world: int,
) -> LCSRSC3FoldSource:
    """Freeze one LOO partition and build placebo from fitting worlds only."""

    if held_out_world not in V023_GATE_WORLDS:
        raise LCSRSC3GateFitError("held-out world is outside the frozen panel")
    panel = _verified_records(records_by_world)
    training = tuple(
        record
        for world in V023_GATE_WORLDS
        if world != held_out_world
        for record in panel[world]
    )
    held_out = panel[held_out_world]
    placebo = build_lcsrs_matched_placebo(
        training,
        placebo_key=V023_PLACEBO_KEY,
    )
    if placebo.placebo_key_sha256 != V023_PLACEBO_KEY_SHA256:
        raise LCSRSC3GateFitError("matched-placebo key digest drifted")
    return LCSRSC3FoldSource(
        held_out_world=held_out_world,
        training_records=training,
        held_out_records=held_out,
        matched_placebo=placebo,
    )


@dataclass(frozen=True)
class LCSRSC3HeldoutMetrics:
    """All unchanged held-out SUPPORTED rows for one model."""

    identities: tuple[tuple[int, str, int, int], ...]
    predictions: np.ndarray
    targets: np.ndarray
    spearman: float | None
    sign: SignAccuracy
    content_digest: str

    def __post_init__(self) -> None:
        predictions = np.array(self.predictions, dtype=np.float64, copy=True, order="C")
        targets = np.array(self.targets, dtype=np.float64, copy=True, order="C")
        if predictions.ndim != 1 or targets.shape != predictions.shape:
            raise LCSRSC3GateFitError("held-out prediction vectors are not aligned")
        if len(self.identities) != predictions.size:
            raise LCSRSC3GateFitError("held-out identities do not match prediction rows")
        if not np.all(np.isfinite(predictions)) or not np.all(np.isfinite(targets)):
            raise LCSRSC3GateFitError("held-out predictions and targets must be finite")
        expected = _prediction_digest(self.identities, predictions, targets)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3GateFitError("held-out prediction digest mismatch")
        predictions.setflags(write=False)
        targets.setflags(write=False)
        object.__setattr__(self, "predictions", predictions)
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "content_digest", expected)


def evaluate_lcsrs_heldout_rows(
    network: LCSRSC3QNetwork,
    records: Sequence[LCSRSAnchorRecord],
    *,
    device: torch.device | str = "cpu",
) -> LCSRSC3HeldoutMetrics:
    """Evaluate one fitted network against every true held-out SUPPORTED row."""

    if not isinstance(network, LCSRSC3QNetwork):
        raise TypeError("network must be the frozen LC-SRS C3 head")
    frozen = tuple(records)
    if not frozen:
        raise LCSRSC3GateFitError("held-out evaluation needs a retained anchor")
    identities: list[tuple[int, str, int, int]] = []
    predictions: list[float] = []
    targets: list[float] = []
    network.eval()
    with torch.no_grad():
        for record in frozen:
            if not isinstance(record, LCSRSAnchorRecord):
                raise LCSRSC3GateFitError("held-out source contains a non-anchor record")
            surface = record.surface
            surface.view.verify()
            values = network.forward_view(surface.view, device=device).detach().cpu().numpy()
            for user, action in surface.cells_for_class(LCSRS_ROW_SUPPORTED).tolist():
                user_id = int(user)
                action_id = int(action)
                reference = int(surface.view.reference_actions[user_id])
                prediction = float(values[user_id, action_id] - values[user_id, reference])
                target = float(surface.normalized_targets[user_id, action_id])
                identities.append(
                    (record.world_id, record.anchor_id, user_id, action_id)
                )
                predictions.append(prediction)
                targets.append(target)
    if not identities:
        raise LCSRSC3GateFitError("held-out world has no SUPPORTED row")
    predicted = np.asarray(predictions, dtype=np.float64)
    truth = np.asarray(targets, dtype=np.float64)
    return LCSRSC3HeldoutMetrics(
        identities=tuple(identities),
        predictions=predicted,
        targets=truth,
        spearman=tie_aware_spearman(predicted, truth),
        sign=sign_accuracy(predicted, truth),
        content_digest="",
    )


@dataclass(frozen=True)
class LCSRSC3FoldFit:
    """One fitted arm and its unchanged held-out row metrics."""

    arm: str
    student_seed: int
    source: LCSRSC3FoldSource
    network: LCSRSC3QNetwork
    fit_receipt: LCSRSC3FitReceipt
    heldout: LCSRSC3HeldoutMetrics


def fit_lcsrs_loo_arm(
    source: LCSRSC3FoldSource,
    *,
    arm: str,
    student_seed: int,
    device: torch.device | str = "cpu",
) -> LCSRSC3FoldFit:
    """Run the exact 2,000-update arm and score its held-out true rows."""

    if arm not in {"INFORMED", "MATCHED_PLACEBO"}:
        raise LCSRSC3GateFitError("unknown V0.23 fit arm")
    if student_seed not in V023_STUDENT_SEEDS:
        raise LCSRSC3GateFitError("student seed is outside the frozen panel")
    if not source.matched_placebo.meets_coverage_gate:
        raise LCSRSC3GateFitError(
            "matched-placebo coverage is below the frozen 0.80 gate"
        )
    surfaces = tuple(record.surface for record in source.training_records)
    target_override = (
        None
        if arm == "INFORMED"
        else source.matched_placebo.normalized_targets_by_anchor
    )
    network, fit_receipt = fit_lcsrs_c3_source(
        surfaces,
        arm=arm,
        student_seed=student_seed,
        normalized_targets_by_anchor=target_override,
        device=device,
    )
    fit_receipt = replace(
        fit_receipt,
        source_anchor_sha256s=tuple(
            record.content_digest for record in source.training_records
        ),
    )
    heldout = evaluate_lcsrs_heldout_rows(
        network,
        source.held_out_records,
        device=device,
    )
    return LCSRSC3FoldFit(
        arm=arm,
        student_seed=student_seed,
        source=source,
        network=network,
        fit_receipt=fit_receipt,
        heldout=heldout,
    )


__all__ = [
    "V023_GATE_WORLDS",
    "V023_STUDENT_SEEDS",
    "V023_PLACEBO_KEY",
    "V023_PLACEBO_KEY_SHA256",
    "LCSRSC3GateFitError",
    "LCSRSC3FoldSource",
    "LCSRSC3HeldoutMetrics",
    "LCSRSC3FoldFit",
    "prepare_lcsrs_loo_fold",
    "evaluate_lcsrs_heldout_rows",
    "fit_lcsrs_loo_arm",
]
