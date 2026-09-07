"""Read-only canonical-runtime seams for the prospective C3 V3 gate.

This module is intentionally an adapter, not a second environment.  It
receipts the deployed scalarized-Main action surface and projects fields that
the already-executed canonical :class:`ActionEvaluation` exposes onto the
pure C3 V3 identity checks.  It does not choose a C3 candidate, fork a
trajectory, draw randomness, mutate an environment, train, or aggregate an
outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import c3_reward_aligned_v3_core as core  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
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
    """Complete, read-only receipt of one scalarized-Main inference call."""

    actions: tuple[int, ...]
    physical_actions: tuple[core.PhysicalAction, ...] | None
    objective_weights: tuple[float, float, float]
    q_values: tuple[tuple[float, ...], ...]
    masks: tuple[tuple[bool, ...], ...]

    @property
    def table_actions(self) -> tuple[int, ...]:
        """The interval-local actions before physical-ID projection."""

        return self.actions

    @property
    def physical_ids(self) -> tuple[core.PhysicalAction, ...] | None:
        """Alias that makes the physical-ID receipt explicit to callers."""

        return self.physical_actions


def _mask_matrix(masks: Any) -> np.ndarray:
    """Normalize canonical action masks without coercing truthy values."""

    raw = np.asarray(masks)
    if raw.ndim == 2 and raw.dtype == np.bool_:
        matrix = raw.astype(bool, copy=True)
    else:
        try:
            rows = [np.asarray(item.mask) for item in masks]
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("Main masks must expose one Boolean row per user") from exc
        if not rows:
            raise ValueError("Main masks must contain at least one user row")
        if any(row.ndim != 1 or row.dtype != np.bool_ for row in rows):
            raise ValueError("Main masks must contain one-dimensional Boolean rows")
        try:
            matrix = np.stack(rows).astype(bool, copy=True)
        except ValueError as exc:
            raise ValueError("Main masks must have shape (U,A)") from exc
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("Main masks must have nonempty shape (U,A)")
    return matrix


def scalarized_main_decision(
    trainer: Any,
    states: Sequence[Any],
    masks: Any,
    *,
    slot_tables: Sequence[Any] | None = None,
) -> ScalarizedMainDecision:
    """Execute the exact frozen scalarized-Main read-only inference seam.

    The configured weights are checked before state encoding or Q inference.
    This ordering is part of the gate: a Q1-only or otherwise drifted action
    surface must never produce a receipt that looks like M-REF.
    """

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
            f"Main objective weights drifted: {configured!r}, "
            f"expected {OBJECTIVE_WEIGHTS!r}"
        )

    mask_matrix = _mask_matrix(masks)
    if len(states) != mask_matrix.shape[0]:
        raise ValueError("Main states and masks disagree on user count")

    # No call above this line can invoke trainer inference.  In particular,
    # the weight assertion precedes encode_states and scalarized_q_values.
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


def _strict_numeric_array(
    value: Any, *, field: str, ndim: int | None = None
) -> np.ndarray:
    """Read a canonical numeric array without string/object coercion."""

    array = np.asarray(value)
    if ndim is not None and array.ndim != ndim:
        raise ValueError(f"canonical {field} must have dimension {ndim}")
    if array.dtype.kind not in "fiu":
        raise ValueError(f"canonical {field} must be a numeric array")
    return array


def _strict_bool_vector(value: Any, *, field: str, size: int | None = None) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1 or array.dtype != np.bool_:
        raise ValueError(f"canonical {field} must be a one-dimensional Boolean array")
    if size is not None and array.shape != (size,):
        raise ValueError(f"canonical {field} must have shape ({size},)")
    return array


def _validate_integer_vector(value: Any, *, field: str, size: int) -> np.ndarray:
    array = _strict_numeric_array(value, field=field, ndim=1)
    if array.shape != (size,) or not np.issubdtype(array.dtype, np.integer):
        raise ValueError(f"canonical {field} must have integer shape ({size},)")
    return array


def _validate_id_array(
    value: Any, *, field: str, size: int
) -> np.ndarray:
    array = _validate_integer_vector(value, field=field, size=size)
    if np.any(array < -1):
        raise ValueError(f"canonical {field} contains an invalid negative ID")
    return array


def _validate_pa_parameter(value: Any, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite positive real number")
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError(f"{field} must be a finite positive real number")
    return result


@dataclass(frozen=True)
class CanonicalPowerProjection:
    """C3 power terms plus the independent complete-identity receipt."""

    terms: core.PowerIntervalTerms
    identity: core.PowerIdentityDecision


def canonical_power_projection(
    evaluation: Any,
    *,
    pa_max_efficiency: float = PA_MAX_EFFICIENCY,
    pa_saturation_power_w: float = PA_SATURATION_POWER_W,
) -> CanonicalPowerProjection:
    """Project one canonical action evaluation without duplicating physics.

    The PA functions are imported from the canonical link-budget module.  All
    complete-system terms are then checked by ``core.validate_power_identity``;
    this adapter never derives a payload-only or per-link surrogate.  A
    mismatch between the active resolution and radiating set, or a link-power
    maximum that does not match canonical beam power, fails closed.
    """

    pa_max = _validate_pa_parameter(pa_max_efficiency, field="PA maximum efficiency")
    pa_sat = _validate_pa_parameter(pa_saturation_power_w, field="PA saturation power")

    try:
        radiating = evaluation.radiating
        resolution = evaluation.resolution
    except AttributeError as exc:
        raise ValueError("canonical action evaluation lacks radiating/resolution fields") from exc

    norads = _strict_numeric_array(
        radiating.norad_ids, field="radiating NORAD IDs", ndim=1
    )
    cells = _strict_numeric_array(radiating.cell_ids, field="radiating cell IDs", ndim=1)
    beam_power = _strict_numeric_array(
        radiating.power_w, field="radiating beam powers", ndim=1
    ).astype(np.float64, copy=False)
    if not np.issubdtype(norads.dtype, np.integer) or not np.issubdtype(
        cells.dtype, np.integer
    ):
        raise ValueError("canonical radiating-beam IDs must be integer arrays")
    if cells.shape != norads.shape or beam_power.shape != norads.shape:
        raise ValueError("canonical radiating-beam arrays must share shape (B,)")
    if np.any(~np.isfinite(beam_power)) or np.any(beam_power < 0.0):
        raise ValueError("canonical radiating-beam powers must be finite and nonnegative")

    beam_ids = tuple(
        core.validate_physical_id((int(norad), int(cell)), field="radiating beam")
        for norad, cell in zip(norads.tolist(), cells.tolist(), strict=True)
    )
    if len(set(beam_ids)) != len(beam_ids):
        raise ValueError("canonical radiating-beam IDs must be unique")
    try:
        active_beams = tuple(
            core.validate_physical_id(value, field="canonical active beam")
            for value in resolution.active_beams
        )
    except AttributeError as exc:
        raise ValueError("canonical resolution lacks active_beams") from exc
    if len(set(active_beams)) != len(active_beams):
        raise ValueError("canonical active-beam resolution contains duplicates")
    if frozenset(beam_ids) != frozenset(active_beams):
        raise ValueError("radiating beams and canonical active-beam resolution disagree")

    served = _strict_bool_vector(resolution.served, field="served flags")
    users = served.size
    serving_satellite = _validate_id_array(
        resolution.serving_satellite, field="serving satellite IDs", size=users
    )
    serving_cell = _validate_id_array(
        resolution.serving_cell, field="serving cell IDs", size=users
    )
    link_power = _strict_numeric_array(
        evaluation.link_power_w, field="link powers", ndim=1
    ).astype(np.float64, copy=False)
    if link_power.shape != (users,):
        raise ValueError(f"canonical link powers must have shape ({users},)")
    if np.any(~np.isfinite(link_power)) or np.any(link_power < 0.0):
        raise ValueError("canonical link powers must be finite and nonnegative")
    if np.any(serving_satellite[~served] != -1) or np.any(serving_cell[~served] != -1):
        raise ValueError("unserved canonical users must have serving IDs equal to -1")
    if np.any(link_power[~served] != 0.0):
        raise ValueError("unserved canonical users must have zero link power")

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
    if any(not values for values in outputs_by_beam.values()):
        raise ValueError("every canonical radiating beam must have a served link")

    efficiencies = pa_efficiency(
        beam_power,
        max_efficiency=pa_max,
        saturation_power_w=pa_sat,
    )
    supplies = supply_power_w(beam_power, efficiencies)
    counts: dict[int, int] = {}
    for beam_id in beam_ids:
        counts[beam_id[0]] = counts.get(beam_id[0], 0) + 1
    try:
        reported_fixed = evaluation.fixed_power_w
        reported_system = evaluation.system_power_w
    except AttributeError as exc:
        raise ValueError("canonical action evaluation lacks complete power totals") from exc
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
        reported_fixed_power_w=reported_fixed,
        reported_system_power_w=reported_system,
    )
    identity = core.validate_power_identity(terms)
    if not identity.passed:
        raise RuntimeError(
            "canonical power projection failed identity: "
            + ",".join(identity.reasons)
        )
    return CanonicalPowerProjection(terms, identity)


@dataclass(frozen=True)
class CanonicalLoadProjection:
    """C3 load snapshot plus the unmodified canonical ``r3`` receipt."""

    snapshot: core.LoadSnapshot
    identity: core.LoadIdentityDecision
    reward_column: tuple[float, ...]

    @property
    def canonical_r3_by_user(self) -> tuple[float, ...]:
        return self.reward_column


def _canonical_load_map(value: Any) -> dict[core.PhysicalId, int]:
    if not isinstance(value, Mapping):
        raise ValueError("canonical eligible-load map must be a mapping")
    result: dict[core.PhysicalId, int] = {}
    for raw_id, raw_count in value.items():
        physical_id = core.validate_physical_id(raw_id, field="eligible-load physical ID")
        if type(raw_count) is not int or raw_count <= 0:
            raise ValueError("canonical eligible-load counts must be positive exact integers")
        if physical_id in result:
            raise ValueError("canonical eligible-load map contains a duplicate physical ID")
        result[physical_id] = raw_count
    return result


def canonical_load_projection(evaluation: Any) -> CanonicalLoadProjection:
    """Project canonical service resolution and reward-matrix column three.

    ``eligible_load_by_beam`` is the construction authority.  The adapter
    reconstructs served physical associations from the resolution, obtains
    the *unmodified* ``reward_matrix[:, 2]`` column, and delegates the exact
    ``r_3 = -U_{b_u}``, active-beam, and squared-load identities to the pure
    C3 core.  Unserved users must carry ``(-1, -1)``, zero link association,
    and a zero canonical ``r_3`` value; no truthy or post-hoc fallback is
    accepted.
    """

    try:
        resolution = evaluation.resolution
        raw_reward_matrix = evaluation.reward_matrix
    except AttributeError as exc:
        raise ValueError("canonical action evaluation lacks resolution/reward matrix") from exc

    served = _strict_bool_vector(resolution.served, field="served flags")
    users = served.size
    serving_satellite = _validate_id_array(
        resolution.serving_satellite, field="serving satellite IDs", size=users
    )
    serving_cell = _validate_id_array(
        resolution.serving_cell, field="serving cell IDs", size=users
    )
    associations: list[core.PhysicalAction] = []
    for uid, is_served in enumerate(served.tolist()):
        if not is_served:
            if serving_satellite[uid] != -1 or serving_cell[uid] != -1:
                raise ValueError("unserved canonical users must have serving IDs equal to -1")
            associations.append(None)
            continue
        associations.append(
            core.validate_physical_id(
                (int(serving_satellite[uid]), int(serving_cell[uid])),
                field="served physical association",
            )
        )

    reward_matrix = _strict_numeric_array(
        raw_reward_matrix, field="reward matrix", ndim=2
    )
    if reward_matrix.shape != (users, 3):
        raise ValueError("canonical reward matrix must have shape (U,3)")
    if reward_matrix.dtype.kind == "b" or np.any(~np.isfinite(reward_matrix.astype(np.float64))):
        raise ValueError("canonical reward matrix must contain finite numeric values")
    reward_column = tuple(float(value) for value in reward_matrix[:, 2].tolist())
    loads = _canonical_load_map(resolution.eligible_load_by_beam)
    try:
        raw_active = resolution.active_beams
    except AttributeError as exc:
        raise ValueError("canonical resolution lacks active_beams") from exc
    if not isinstance(raw_active, (tuple, list, set, frozenset)):
        raise ValueError("canonical active beams must be a concrete collection")
    active = frozenset(
        core.validate_physical_id(value, field="canonical active beam")
        for value in raw_active
    )
    snapshot = core.LoadSnapshot(
        served_associations=tuple(associations),
        reported_eligible_loads=loads,
        reported_active_beams=active,
        canonical_r3_by_user=reward_column,
    )
    identity = core.validate_load_snapshot(snapshot)
    if not identity.passed:
        raise RuntimeError(
            "canonical load projection failed identity: "
            + ",".join(identity.reasons)
        )
    return CanonicalLoadProjection(snapshot, identity, reward_column)


# Explicit name for callers that only need the snapshot object but still want
# the same checked projection.  Returning the wrapper preserves the receipt;
# callers should use ``result.snapshot`` for the core value.
canonical_load_snapshot = canonical_load_projection


__all__ = [
    "OBJECTIVE_WEIGHTS",
    "POLICY_MODE",
    "ScalarizedMainDecision",
    "scalarized_main_decision",
    "CanonicalPowerProjection",
    "canonical_power_projection",
    "CanonicalLoadProjection",
    "canonical_load_projection",
    "canonical_load_snapshot",
]
