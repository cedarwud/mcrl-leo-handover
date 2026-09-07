"""Read-only canonical-runtime seams for the prospective C2 V3 gate.

This adapter closes two deterministic integration questions only: the exact
scalarized-Main action surface and projection of an existing canonical action
evaluation onto the C2 power-identity receipt.  It does not fork a trajectory,
select a C2 candidate, run a census, mutate replay, or train a learner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import c2_activation_churn_core as core  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
    pa_efficiency,
    supply_power_w,
)
from mcrl.runtime.head_pivotality import (  # noqa: E402
    masked_greedy_actions,
    physical_action_keys,
)


OBJECTIVE_WEIGHTS = (0.5, 0.3, 0.2)
POLICY_MODE = "masked-greedy-scalarized-main"


@dataclass(frozen=True)
class ScalarizedMainDecision:
    actions: tuple[int, ...]
    physical_actions: tuple[core.PhysicalAction, ...] | None
    objective_weights: tuple[float, float, float]
    q_values: tuple[tuple[float, ...], ...]
    masks: tuple[tuple[bool, ...], ...]


def _mask_matrix(masks: Any) -> np.ndarray:
    raw = np.asarray(masks)
    if raw.ndim == 2 and raw.dtype == np.bool_:
        matrix = raw.astype(bool, copy=True)
    else:
        try:
            matrix = np.stack(
                [np.asarray(item.mask, dtype=bool) for item in masks]
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("Main masks must expose one Boolean row per user") from exc
    if matrix.ndim != 2:
        raise ValueError("Main masks must have shape (U,A)")
    return matrix


def scalarized_main_decision(
    trainer: Any,
    states: Sequence[Any],
    masks: Any,
    *,
    slot_tables: Sequence[Any] | None = None,
) -> ScalarizedMainDecision:
    """Execute the exact frozen scalarized-Main read-only inference seam."""

    raw_weights = tuple(trainer.config.objective_weights)
    if len(raw_weights) != 3 or any(
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, (int, float, np.number))
        for value in raw_weights
    ):
        raise RuntimeError("Main objective weights must be three numeric values")
    configured = tuple(float(value) for value in raw_weights)
    if configured != OBJECTIVE_WEIGHTS:
        raise RuntimeError(
            f"Main objective weights drifted: {configured!r}, expected {OBJECTIVE_WEIGHTS!r}"
        )
    mask_matrix = _mask_matrix(masks)
    if len(states) != mask_matrix.shape[0]:
        raise ValueError("Main states and masks disagree on user count")
    encoded = trainer.encode_states(states)
    q_values = np.asarray(
        trainer.scalarized_q_values(
            encoded,
            objective_weights=OBJECTIVE_WEIGHTS,
        ),
        dtype=np.float64,
    )
    if q_values.shape != mask_matrix.shape:
        raise ValueError("scalarized Main Q table and masks must share shape (U,A)")
    if np.any(~np.isfinite(q_values)):
        raise ValueError("scalarized Main Q table must be finite")
    actions = masked_greedy_actions(q_values, mask_matrix)
    physical: tuple[core.PhysicalAction, ...] | None = None
    if slot_tables is not None:
        if len(slot_tables) != mask_matrix.shape[0]:
            raise ValueError("slot tables and masks disagree on user count")
        physical = tuple(physical_action_keys(actions, slot_tables))
    return ScalarizedMainDecision(
        actions=tuple(int(value) for value in actions.tolist()),
        physical_actions=physical,
        objective_weights=OBJECTIVE_WEIGHTS,
        q_values=tuple(tuple(float(value) for value in row) for row in q_values),
        masks=tuple(tuple(bool(value) for value in row) for row in mask_matrix),
    )


@dataclass(frozen=True)
class CanonicalPowerProjection:
    terms: core.PowerIntervalTerms
    identity: core.PowerIdentityDecision


def canonical_power_projection(
    evaluation: Any,
    *,
    pa_max_efficiency: float,
    pa_saturation_power_w: float,
) -> CanonicalPowerProjection:
    """Project one canonical evaluation without duplicating its power model."""

    radiating = evaluation.radiating
    resolution = evaluation.resolution
    norads = np.asarray(radiating.norad_ids)
    cells = np.asarray(radiating.cell_ids)
    beam_power = np.asarray(radiating.power_w, dtype=np.float64)
    if norads.ndim != 1 or cells.shape != norads.shape or beam_power.shape != norads.shape:
        raise ValueError("canonical radiating-beam arrays must share shape (B,)")
    if not np.issubdtype(norads.dtype, np.integer) or not np.issubdtype(
        cells.dtype, np.integer
    ):
        raise ValueError("canonical radiating-beam IDs must be integer arrays")
    if np.any(~np.isfinite(beam_power)) or np.any(beam_power < 0.0):
        raise ValueError("canonical radiating-beam powers must be finite and nonnegative")
    beam_ids = tuple(
        core.validate_physical_id((int(norad), int(cell)), field="radiating beam")
        for norad, cell in zip(norads.tolist(), cells.tolist(), strict=True)
    )
    if len(set(beam_ids)) != len(beam_ids):
        raise ValueError("canonical radiating-beam IDs must be unique")
    active_beams = tuple(
        core.validate_physical_id(value, field="canonical active beam")
        for value in resolution.active_beams
    )
    if len(set(active_beams)) != len(active_beams):
        raise ValueError("canonical active-beam resolution contains duplicates")
    if frozenset(beam_ids) != frozenset(active_beams):
        raise ValueError("radiating beams and canonical active-beam resolution disagree")

    efficiencies = pa_efficiency(
        beam_power,
        max_efficiency=float(pa_max_efficiency),
        saturation_power_w=float(pa_saturation_power_w),
    )
    supplies = supply_power_w(beam_power, efficiencies)
    served = np.asarray(resolution.served)
    serving_satellite = np.asarray(resolution.serving_satellite)
    serving_cell = np.asarray(resolution.serving_cell)
    link_power = np.asarray(evaluation.link_power_w, dtype=np.float64)
    if not (
        served.shape
        == serving_satellite.shape
        == serving_cell.shape
        == link_power.shape
    ):
        raise ValueError("canonical per-user service and link-power arrays disagree")
    if served.dtype != np.bool_:
        raise ValueError("canonical served flags must be a Boolean array")
    if not np.issubdtype(
        serving_satellite.dtype, np.integer
    ) or not np.issubdtype(serving_cell.dtype, np.integer):
        raise ValueError("canonical serving IDs must be integer arrays")
    if np.any(~np.isfinite(link_power)) or np.any(link_power < 0.0):
        raise ValueError("canonical link powers must be finite and nonnegative")

    outputs_by_beam: dict[core.PhysicalId, list[float]] = {
        beam_id: [] for beam_id in beam_ids
    }
    for uid in np.flatnonzero(served).tolist():
        beam_id = core.validate_physical_id(
            (int(serving_satellite[uid]), int(serving_cell[uid])),
            field="served physical beam",
        )
        if beam_id not in outputs_by_beam:
            raise ValueError("served link is absent from canonical radiating beams")
        outputs_by_beam[beam_id].append(float(link_power[uid]))

    counts: dict[int, int] = {}
    for beam_id in beam_ids:
        counts[beam_id[0]] = counts.get(beam_id[0], 0) + 1
    terms = core.PowerIntervalTerms(
        beams=tuple(
            core.BeamPowerTerms(
                beam_id=beam_id,
                recurrence_outputs_w=tuple(outputs_by_beam[beam_id]),
                reported_beam_max_w=float(beam_power[index]),
                reported_pa_efficiency=float(efficiencies[index]),
                reported_pa_supply_w=float(supplies[index]),
            )
            for index, beam_id in enumerate(beam_ids)
        ),
        active_beam_counts_by_satellite=counts,
        circuit_power_per_active_beam_w=CIRCUIT_POWER_PER_BEAM_W,
        baseband_power_per_active_satellite_w=BASEBAND_POWER_PER_SATELLITE_W,
        reported_fixed_power_w=float(evaluation.fixed_power_w),
        reported_system_power_w=float(evaluation.system_power_w),
    )
    identity = core.validate_power_identity(terms)
    if not identity.passed:
        raise RuntimeError(
            "canonical power projection failed identity: "
            + ",".join(identity.reasons)
        )
    return CanonicalPowerProjection(terms, identity)
