"""Formula-only OPS-3 projected-persistence C2 surface.

This module is deliberately a narrow boundary between the orbital projection
adapter and the C2 formula.  It does not run a scenario, advance a branch,
select a future action, draw fading, or train a learner.  A caller supplies
the offset geometry/rate/SINR values produced by an adapter which owns a
deep-copy of the live :class:`~mcrl.env.d2.D2Tracker`.  The formula layer then
applies the frozen persistence rule, the canonical network-power delta, the
``-kappa`` service-risk penalty, and the centered native action surface.

The separation is intentional.  A future-D2 adapter needs access to the
scenario's native 640-ms clock and TLE objects, while this module must remain
pure and easy to test.  The adapter contract is therefore explicit in
``OPS3ProjectionProvider`` and the value objects below.  No private live
environment object is accepted by the scoring function.

Frozen OPS-3 rules implemented here (the 2026-09-02 formula contract):

* ``H_t = min(3, T - 1 - t)`` and offsets are ``h = 1, 2, 3``;
* ``o_0`` is the current legal-action link-power/service feasibility gate;
* ``chi_h = o_0 * product(rho_1, ..., rho_h)`` is absorbing after service loss;
* ``p_hat = p0 * g_start / g_h`` has no cap or clamp; the ceiling is a
  feasibility predicate outside recurrence;
* the focal marginal power uses the canonical max-per-beam RF power, PA,
  circuit, and once-per-active-satellite baseband accounting;
* ``Z2`` is averaged over the available future offsets and Q2 is centered at
  the frozen-Main reference action;
* all legal rows and all signs are retained.  Illegal rows are zero-filled
  and never selected by this module.

The implementation uses the canonical helpers in ``env.link_budget`` rather
than introducing a second power model.  It does not use ``_previous_demand``
or any future policy output.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import Protocol

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..env.constants import DECISION_STEP_S
from ..env.link_budget import (
    BEAM_POWER_MAX_W,
    SEGMENT_START_POWER_W,
    classify_link_power_feasibility,
    pa_efficiency,
    recurrence_power_w,
    supply_power_w,
    system_power_w,
)
from ..errors import MCRLContractError


OPS3_SCHEMA = "multi-catfish-mcrl-v03-c2-ops3-formula-surface-v1.1"
OPS3_OFFSET_SCHEMA = "multi-catfish-mcrl-v03-c2-ops3-offset-v1"
OPS3_BACKGROUND_SCHEMA = "multi-catfish-mcrl-v03-c2-ops3-frozen-background-v1"
OPS3_PROJECTION_SCHEMA = "multi-catfish-mcrl-v03-c2-ops3-projection-provider-v1"

OPS3_HORIZON: int = 3
OPS3_FEATURE_DIM: int = 16
OPS3_LAMBDA_BITS_PER_J: float = float.fromhex("0x1.443a8f481639ap+26")
OPS3_KAPPA_BITS: float = float.fromhex("0x1.2cea89d260f2ap+33")
# Do not restate this as the decimal literal 30.08.  The simulator's native
# clock is constructed as 47 * 0.64 and differs from that literal by one ULP.
OPS3_INTERVAL_S: float = DECISION_STEP_S


class OPS3FormulaError(MCRLContractError):
    """An OPS-3 formula input violates the frozen mechanics contract."""


class OPS3ProjectionProvider(Protocol):
    """External boundary for a cloned, native-clock orbital projection.

    An implementation must deep-copy the live D2 tracker, hold the focal
    user/background inputs fixed as specified by the contract, and return
    canonical physical values for one offset.  It must not mutate the live
    driver, environment, tracker, RNG, or networks.  The formula module never
    calls this protocol; the protocol exists so a future runner cannot confuse
    projection with a hidden branch rollout.
    """

    def project_offset(self, offset: int, *, action_count: int) -> "OPS3Offset":
        """Return one action-aligned forecast for ``h = offset``."""


def _finite_vector(value: object, *, field: str, size: int) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise OPS3FormulaError(f"{field} must be a finite vector") from error
    if result.shape != (size,) or not np.all(np.isfinite(result)):
        raise OPS3FormulaError(f"{field} must be finite shape ({size},)")
    return np.array(result, dtype=np.float64, copy=True, order="C")


def _finite_nonnegative(value: object, *, field: str, size: int) -> np.ndarray:
    result = _finite_vector(value, field=field, size=size)
    if np.any(result < 0.0):
        raise OPS3FormulaError(f"{field} must be non-negative")
    return result


def _readonly(array: np.ndarray) -> np.ndarray:
    result = np.array(array, copy=True, order="C")
    result.setflags(write=False)
    return result


def _bool_vector(value: object, *, field: str, size: int) -> np.ndarray:
    result = np.asarray(value)
    if result.shape != (size,) or result.dtype != np.bool_:
        raise OPS3FormulaError(f"{field} must be Boolean shape ({size},)")
    return np.array(result, dtype=np.bool_, copy=True, order="C")


def _int_vector(value: object, *, field: str, size: int) -> np.ndarray:
    result = np.asarray(value)
    if (
        result.shape != (size,)
        or result.dtype == np.bool_
        or not np.issubdtype(result.dtype, np.integer)
    ):
        raise OPS3FormulaError(f"{field} must be integer shape ({size},)")
    return np.array(result, dtype=np.int64, copy=True, order="C")


@dataclass(frozen=True)
class OPS3Offset:
    """Canonical action-aligned physical values for one future offset.

    ``focal_rate_bps`` and ``focal_sinr_linear`` are supplied by the adapter
    using the canonical receive/interference/rate helpers.  The formula layer
    masks both after absorbing service loss.  ``projected_gain_linear`` is the
    transmit-side gain used by the canonical recurrence; zero represents a
    null/no-gain geometry and is not passed to ``recurrence_power_w``.
    """

    projected_gain_linear: np.ndarray
    d2_eligible: np.ndarray
    cell_visible: np.ndarray
    focal_rate_bps: np.ndarray
    focal_sinr_linear: np.ndarray
    schema: str = OPS3_OFFSET_SCHEMA

    def __post_init__(self) -> None:
        gains = np.asarray(self.projected_gain_linear)
        if gains.ndim != 1 or gains.size < 1:
            raise OPS3FormulaError("projected_gain_linear must be one-dimensional")
        size = int(gains.size)
        object.__setattr__(
            self,
            "projected_gain_linear",
            _readonly(_finite_nonnegative(gains, field="projected_gain_linear", size=size)),
        )
        object.__setattr__(
            self,
            "d2_eligible",
            _readonly(_bool_vector(self.d2_eligible, field="d2_eligible", size=size)),
        )
        object.__setattr__(
            self,
            "cell_visible",
            _readonly(_bool_vector(self.cell_visible, field="cell_visible", size=size)),
        )
        object.__setattr__(
            self,
            "focal_rate_bps",
            _readonly(_finite_nonnegative(self.focal_rate_bps, field="focal_rate_bps", size=size)),
        )
        object.__setattr__(
            self,
            "focal_sinr_linear",
            _readonly(_finite_nonnegative(self.focal_sinr_linear, field="focal_sinr_linear", size=size)),
        )
        if self.schema != OPS3_OFFSET_SCHEMA:
            raise OPS3FormulaError("OPS3Offset schema is stale")

    @property
    def action_count(self) -> int:
        return int(self.projected_gain_linear.size)

    @classmethod
    def zeros(cls, action_count: int, *, schema: str = OPS3_OFFSET_SCHEMA) -> "OPS3Offset":
        """Return a neutral offset for a horizon that is not available."""

        if type(action_count) is not int or action_count < 1:
            raise OPS3FormulaError("action_count must be a positive integer")
        return cls(
            projected_gain_linear=np.zeros(action_count, dtype=np.float64),
            d2_eligible=np.zeros(action_count, dtype=np.bool_),
            cell_visible=np.zeros(action_count, dtype=np.bool_),
            focal_rate_bps=np.zeros(action_count, dtype=np.float64),
            focal_sinr_linear=np.zeros(action_count, dtype=np.float64),
            schema=schema,
        )


@dataclass(frozen=True)
class OPS3FrozenBackground:
    """Last committed served beams excluding the focal user.

    Each row is one unique active physical beam.  ``load`` is the number of
    non-focal served users on that beam, and ``power_w`` is its canonical
    max-over-served-user RF power.  This object cannot represent ungated
    ``_previous_demand``; a caller trying to pass a duplicate or zero-power
    beam fails closed.
    """

    norad_ids: np.ndarray
    cell_ids: np.ndarray
    load: np.ndarray
    power_w: np.ndarray
    schema: str = OPS3_BACKGROUND_SCHEMA

    def __post_init__(self) -> None:
        norads = np.asarray(self.norad_ids)
        if norads.ndim != 1:
            raise OPS3FormulaError("background norad_ids must be one-dimensional")
        size = int(norads.size)
        object.__setattr__(self, "norad_ids", _readonly(_int_vector(norads, field="background.norad_ids", size=size)))
        object.__setattr__(self, "cell_ids", _readonly(_int_vector(self.cell_ids, field="background.cell_ids", size=size)))
        loads = _finite_nonnegative(self.load, field="background.load", size=size)
        powers = _finite_nonnegative(self.power_w, field="background.power_w", size=size)
        if np.any(loads < 1.0) or np.any(loads != np.floor(loads)):
            raise OPS3FormulaError("background loads must be positive integer counts")
        if np.any(powers <= 0.0):
            raise OPS3FormulaError("background served beams need positive RF power")
        pairs = list(zip(norads.tolist(), np.asarray(self.cell_ids).tolist()))
        if len(set(pairs)) != len(pairs):
            raise OPS3FormulaError("background contains a duplicate physical beam")
        object.__setattr__(self, "load", _readonly(loads.astype(np.int64)))
        object.__setattr__(self, "power_w", _readonly(powers))
        if self.schema != OPS3_BACKGROUND_SCHEMA:
            raise OPS3FormulaError("OPS3FrozenBackground schema is stale")

    @property
    def beam_count(self) -> int:
        return int(self.norad_ids.size)


@dataclass(frozen=True)
class OPS3Surface:
    """Immutable Q2 oracle surface for one focal user at one anchor."""

    z2_bits: np.ndarray
    q2_values: np.ndarray
    features: np.ndarray
    required_power_w: np.ndarray
    persistence: np.ndarray
    rate_bps: np.ndarray
    marginal_power_w: np.ndarray
    sinr_linear: np.ndarray
    legal_mask: np.ndarray
    opening_service_feasible: np.ndarray
    reference_action: int
    horizon: int
    schema: str = OPS3_SCHEMA

    def __post_init__(self) -> None:
        z = np.asarray(self.z2_bits)
        if z.ndim != 1:
            raise OPS3FormulaError("z2_bits must be one-dimensional")
        count = int(z.size)
        q = _finite_vector(self.q2_values, field="q2_values", size=count)
        f = np.asarray(self.features)
        if f.shape != (count, OPS3_FEATURE_DIM) or not np.all(np.isfinite(f)):
            raise OPS3FormulaError(
                f"features must be finite shape ({count}, {OPS3_FEATURE_DIM})"
            )
        def matrix(value: object, field: str) -> np.ndarray:
            result = np.asarray(value, dtype=np.float64)
            if result.shape != (OPS3_HORIZON, count) or not np.all(np.isfinite(result)):
                raise OPS3FormulaError(
                    f"{field} must be finite shape ({OPS3_HORIZON}, {count})"
                )
            return _readonly(result)

        object.__setattr__(self, "z2_bits", _readonly(_finite_vector(z, field="z2_bits", size=count)))
        object.__setattr__(self, "q2_values", _readonly(q))
        object.__setattr__(self, "features", _readonly(np.asarray(f, dtype=np.float64)))
        for name, value in (
            ("required_power_w", self.required_power_w),
            ("persistence", self.persistence),
            ("rate_bps", self.rate_bps),
            ("marginal_power_w", self.marginal_power_w),
            ("sinr_linear", self.sinr_linear),
        ):
            object.__setattr__(self, name, matrix(value, name))
        object.__setattr__(self, "legal_mask", _readonly(_bool_vector(self.legal_mask, field="legal_mask", size=count)))
        object.__setattr__(
            self,
            "opening_service_feasible",
            _readonly(
                _bool_vector(
                    self.opening_service_feasible,
                    field="opening_service_feasible",
                    size=count,
                )
            ),
        )
        if type(self.reference_action) is not int or self.reference_action < -1 or self.reference_action >= count:
            raise OPS3FormulaError("reference_action is outside the native action surface")
        if type(self.horizon) is not int or not 0 <= self.horizon <= OPS3_HORIZON:
            raise OPS3FormulaError("horizon must be in [0, 3]")
        if self.schema != OPS3_SCHEMA:
            raise OPS3FormulaError("OPS3Surface schema is stale")


def collect_ops3_offsets(
    provider: OPS3ProjectionProvider,
    *,
    action_count: int,
    horizon: int = OPS3_HORIZON,
) -> tuple[OPS3Offset, ...]:
    """Collect future offsets through the explicit adapter boundary.

    This helper does not clone or mutate a live environment.  That is the
    provider's responsibility and is why the contract can test formula purity
    independently of TLE/D2 plumbing.
    """

    if type(action_count) is not int or action_count < 1:
        raise OPS3FormulaError("action_count must be a positive integer")
    if type(horizon) is not int or not 0 <= horizon <= OPS3_HORIZON:
        raise OPS3FormulaError("horizon must be in [0, 3]")
    offsets: list[OPS3Offset] = []
    for offset in range(1, horizon + 1):
        value = provider.project_offset(offset, action_count=action_count)
        if not isinstance(value, OPS3Offset) or value.action_count != action_count:
            raise OPS3FormulaError("projection provider returned a malformed offset")
        offsets.append(value)
    return tuple(offsets)


def segment_start_gain_surface(
    *,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
    current_gain_linear: object,
    current_association: tuple[int, int] | None,
    committed_start_gain_linear: float | None,
    legal_mask: object,
) -> np.ndarray:
    """Apply the frozen continuing-link versus new-link start-gain rule."""

    gains = np.asarray(current_gain_linear, dtype=np.float64)
    if gains.ndim != 1:
        raise OPS3FormulaError("current_gain_linear must be one-dimensional")
    count = int(gains.size)
    gains = _finite_nonnegative(gains, field="current_gain_linear", size=count)
    legal = _bool_vector(legal_mask, field="legal_mask", size=count)
    norads = _int_vector(candidate_norad_ids, field="candidate_norad_ids", size=count)
    cells = _int_vector(candidate_cell_ids, field="candidate_cell_ids", size=count)
    result = np.array(gains, copy=True)
    if current_association is not None:
        if (
            not isinstance(current_association, tuple)
            or len(current_association) != 2
            or any(type(item) is not int for item in current_association)
        ):
            raise OPS3FormulaError("current_association must be (norad_id, cell_id) or None")
        continuing = legal & (norads == current_association[0]) & (cells == current_association[1])
        if bool(np.any(continuing)):
            if committed_start_gain_linear is None:
                raise OPS3FormulaError("a continuing link needs committed start gain")
            start = float(committed_start_gain_linear)
            if not math.isfinite(start) or start <= 0.0:
                raise OPS3FormulaError("committed start gain must be finite and positive")
            result[continuing] = start
    if np.any(result[legal] <= 0.0):
        raise OPS3FormulaError("legal actions need a positive current/start transmit gain")
    result[~legal] = 0.0
    return _readonly(result)


def opening_service_feasibility_surface(
    *,
    legal_mask: object,
    segment_start_gain_linear: object,
    current_gain_linear: object,
    p0_w: float = SEGMENT_START_POWER_W,
    pmax_w: float = BEAM_POWER_MAX_W,
) -> np.ndarray:
    """Return the execution-equivalent h=0 service gate per action.

    The live step resolves a selected legal action by applying the recurrence
    power at the current geometry and then rejecting only a null-pointing or
    over-ceiling link.  This helper computes that same admission predicate
    without advancing an environment, so the exact OPS-3 persistence formula
    can require a segment to open before crediting any future offset.
    """

    try:
        current = np.asarray(current_gain_linear, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise OPS3FormulaError("current_gain_linear must be a finite vector") from error
    if current.ndim != 1 or current.size < 1:
        raise OPS3FormulaError("current_gain_linear must be a nonempty vector")
    count = int(current.size)
    legal = _bool_vector(legal_mask, field="legal_mask", size=count)
    start = _finite_nonnegative(
        segment_start_gain_linear,
        field="segment_start_gain_linear",
        size=count,
    )
    current = _finite_nonnegative(
        current,
        field="current_gain_linear",
        size=count,
    )
    if not math.isfinite(float(p0_w)) or not 0.0 < float(p0_w) <= float(pmax_w):
        raise OPS3FormulaError("p0_w must be finite, positive, and no greater than pmax_w")
    if not math.isfinite(float(pmax_w)) or float(pmax_w) <= 0.0:
        raise OPS3FormulaError("pmax_w must be finite and positive")

    required = np.zeros(count, dtype=np.float64)
    positive = legal & (start > 0.0) & (current > 0.0)
    if bool(np.any(positive)):
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                required[positive] = recurrence_power_w(
                    start[positive], current[positive], p0_w=float(p0_w)
                )
            except FloatingPointError as error:
                raise OPS3FormulaError("h=0 recurrence power overflowed") from error
    if not np.all(np.isfinite(required)):
        raise OPS3FormulaError("h=0 recurrence power is non-finite")
    infeasible = classify_link_power_feasibility(
        required,
        max_power_w=float(pmax_w),
    )
    return _readonly(positive & ~infeasible)


def _validate_action_identity(
    *,
    legal_mask: np.ndarray,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
) -> tuple[np.ndarray, np.ndarray]:
    count = int(legal_mask.size)
    norads = _int_vector(candidate_norad_ids, field="candidate_norad_ids", size=count)
    cells = _int_vector(candidate_cell_ids, field="candidate_cell_ids", size=count)
    if np.any(legal_mask & ((norads < 0) | (cells < 0))):
        raise OPS3FormulaError("every legal action needs a physical satellite and cell")
    legal_pairs = list(zip(norads[legal_mask].tolist(), cells[legal_mask].tolist()))
    if len(set(legal_pairs)) != len(legal_pairs):
        raise OPS3FormulaError("legal actions contain duplicate physical associations")
    return norads, cells


def canonical_network_power_w(background: OPS3FrozenBackground) -> float:
    """Compute canonical network power for one frozen served-beam set."""

    if not isinstance(background, OPS3FrozenBackground):
        raise OPS3FormulaError("background must be an OPS3FrozenBackground")
    efficiency = pa_efficiency(background.power_w)
    supply = supply_power_w(background.power_w, efficiency)
    satellites, counts = np.unique(background.norad_ids, return_counts=True)
    del satellites
    return system_power_w(supply, counts.astype(np.float64))


def marginal_network_power_surface(
    *,
    background: OPS3FrozenBackground,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
    candidate_power_w: object,
    legal_mask: object,
) -> np.ndarray:
    """Return ``P^N(background + focal) - P^N(background)`` per action.

    Existing beams use ``max(background, p_hat)``.  A new beam adds one
    circuit term, and a previously inactive satellite adds one baseband term;
    both effects emerge from the canonical ``system_power_w`` helper.
    """

    legal = np.asarray(legal_mask)
    if legal.ndim != 1 or legal.dtype != np.bool_:
        raise OPS3FormulaError("legal_mask must be a Boolean vector")
    count = int(legal.size)
    norads, cells = _validate_action_identity(
        legal_mask=legal,
        candidate_norad_ids=candidate_norad_ids,
        candidate_cell_ids=candidate_cell_ids,
    )
    powers = _finite_nonnegative(candidate_power_w, field="candidate_power_w", size=count)
    baseline = canonical_network_power_w(background)
    result = np.zeros(count, dtype=np.float64)
    for action in np.flatnonzero(legal).tolist():
        # A null projected gain has no feasible service and therefore no
        # focal beam contribution.  Keep its target mechanics fail-closed but
        # do not manufacture a zero-power active beam merely to mask it later.
        if powers[action] <= 0.0:
            continue
        pair = (int(norads[action]), int(cells[action]))
        bg_pairs = list(zip(background.norad_ids.tolist(), background.cell_ids.tolist()))
        if pair in bg_pairs:
            index = bg_pairs.index(pair)
            beam_norads = np.array(background.norad_ids, copy=True)
            beam_cells = np.array(background.cell_ids, copy=True)
            beam_powers = np.array(background.power_w, copy=True)
            beam_powers[index] = max(float(beam_powers[index]), float(powers[action]))
        else:
            beam_norads = np.concatenate([background.norad_ids, np.array([norads[action]], dtype=np.int64)])
            beam_cells = np.concatenate([background.cell_ids, np.array([cells[action]], dtype=np.int64)])
            beam_powers = np.concatenate([background.power_w, np.array([powers[action]], dtype=np.float64)])
        augmented = OPS3FrozenBackground(
            norad_ids=beam_norads,
            cell_ids=beam_cells,
            load=np.concatenate([background.load, np.array([1], dtype=np.int64)])
            if pair not in bg_pairs
            else background.load,
            power_w=beam_powers,
        )
        result[action] = canonical_network_power_w(augmented) - baseline
    if not np.all(np.isfinite(result)):
        raise OPS3FormulaError("marginal network-power surface is non-finite")
    return _readonly(result)


def frozen_background_feature_surface(
    *,
    background: OPS3FrozenBackground,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
    user_count: int,
    pmax_w: float = BEAM_POWER_MAX_W,
    legal_mask: object,
) -> np.ndarray:
    """Return the four action-aligned frozen-background features."""

    if type(user_count) is not int or user_count < 1:
        raise OPS3FormulaError("user_count must be a positive integer")
    if not math.isfinite(float(pmax_w)) or pmax_w <= 0.0:
        raise OPS3FormulaError("pmax_w must be finite and positive")
    legal = np.asarray(legal_mask)
    if legal.ndim != 1 or legal.dtype != np.bool_:
        raise OPS3FormulaError("legal_mask must be a Boolean vector")
    norads, cells = _validate_action_identity(
        legal_mask=legal,
        candidate_norad_ids=candidate_norad_ids,
        candidate_cell_ids=candidate_cell_ids,
    )
    count = int(legal.size)
    load = np.zeros(count, dtype=np.float64)
    power = np.zeros(count, dtype=np.float64)
    beam_active = np.zeros(count, dtype=np.float64)
    sat_active = np.zeros(count, dtype=np.float64)
    bg_pairs = list(zip(background.norad_ids.tolist(), background.cell_ids.tolist()))
    active_sats = set(int(value) for value in background.norad_ids.tolist())
    for action in np.flatnonzero(legal).tolist():
        pair = (int(norads[action]), int(cells[action]))
        if pair in bg_pairs:
            index = bg_pairs.index(pair)
            load[action] = float(background.load[index]) / float(user_count)
            power[action] = float(background.power_w[index]) / float(pmax_w)
            beam_active[action] = 1.0
        if int(norads[action]) in active_sats:
            sat_active[action] = 1.0
    return _readonly(np.stack([load, power, beam_active, sat_active], axis=1))


def _projected_required_power(
    *,
    start_gain: np.ndarray,
    projected_gain: np.ndarray,
    legal_mask: np.ndarray,
    p0_w: float,
) -> np.ndarray:
    """Apply the canonical recurrence while treating null gains as invalid."""

    if not math.isfinite(float(p0_w)) or p0_w <= 0.0:
        raise OPS3FormulaError("p0_w must be finite and positive")
    count = int(legal_mask.size)
    result = np.zeros(count, dtype=np.float64)
    positive = legal_mask & (projected_gain > 0.0)
    if bool(np.any(positive)):
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                result[positive] = recurrence_power_w(
                    start_gain[positive], projected_gain[positive], p0_w=p0_w
                )
            except FloatingPointError as error:
                raise OPS3FormulaError("OPS3 recurrence power overflowed") from error
    if not np.all(np.isfinite(result)):
        raise OPS3FormulaError("required projected power is non-finite")
    return result


def build_ops3_surface(
    *,
    legal_mask: object,
    opening_service_feasible: object,
    reference_action: int,
    candidate_norad_ids: object,
    candidate_cell_ids: object,
    segment_start_gain_linear: object,
    offsets: Sequence[OPS3Offset],
    background: OPS3FrozenBackground,
    user_count: int,
    step_index: int,
    total_steps: int,
    p0_w: float = SEGMENT_START_POWER_W,
    pmax_w: float = BEAM_POWER_MAX_W,
    lambda_bits_per_j: float = OPS3_LAMBDA_BITS_PER_J,
    kappa_bits: float = OPS3_KAPPA_BITS,
    interval_s: float = OPS3_INTERVAL_S,
) -> OPS3Surface:
    """Build the pure OPS-3 target/features for one focal user.

    ``offsets`` are action-aligned values for ``h=1..H`` from the external
    cloned-D2/TLE adapter.  At most three offsets are consumed.  The function
    never calls an environment method, advances a tracker, draws RNG, or
    changes any input array.
    """

    legal = np.asarray(legal_mask)
    if legal.ndim != 1 or legal.dtype != np.bool_ or legal.size < 1:
        raise OPS3FormulaError("legal_mask must be a nonempty Boolean vector")
    count = int(legal.size)
    opening = _bool_vector(
        opening_service_feasible,
        field="opening_service_feasible",
        size=count,
    )
    opening = np.logical_and(legal, opening)
    if count != NUM_ACTIONS:
        raise OPS3FormulaError(
            f"OPS3 requires the native {NUM_ACTIONS}-action surface, got {count}"
        )
    norads, cells = _validate_action_identity(
        legal_mask=legal,
        candidate_norad_ids=candidate_norad_ids,
        candidate_cell_ids=candidate_cell_ids,
    )
    if type(reference_action) is not int or reference_action < -1 or reference_action >= count:
        raise OPS3FormulaError("reference_action is outside the action surface")
    if bool(np.any(legal)):
        if reference_action < 0 or not bool(legal[reference_action]):
            raise OPS3FormulaError("nonempty legal mask needs a legal reference action")
    elif reference_action != -1:
        raise OPS3FormulaError("empty legal mask requires reference_action=-1")
    if type(step_index) is not int or step_index < 0:
        raise OPS3FormulaError("step_index must be a non-negative integer")
    if type(total_steps) is not int or total_steps < 1:
        raise OPS3FormulaError("total_steps must be a positive integer")
    if step_index >= total_steps:
        raise OPS3FormulaError("step_index must be before the episode boundary")
    if not 0.0 < float(p0_w) <= float(pmax_w):
        raise OPS3FormulaError("p0_w must be positive and no greater than pmax_w")
    for name, value in (
        ("lambda_bits_per_j", lambda_bits_per_j),
        ("kappa_bits", kappa_bits),
        ("interval_s", interval_s),
        ("pmax_w", pmax_w),
    ):
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise OPS3FormulaError(f"{name} must be finite and positive")
    try:
        offset_values = tuple(offsets)
    except TypeError as error:
        raise OPS3FormulaError("offsets must be a sequence of OPS3Offset values") from error
    if len(offset_values) > OPS3_HORIZON:
        raise OPS3FormulaError("OPS3 consumes at most three future offsets")
    for value in offset_values:
        if not isinstance(value, OPS3Offset) or value.action_count != count:
            raise OPS3FormulaError("offsets must be action-aligned OPS3Offset values")

    horizon = min(OPS3_HORIZON, max(0, total_steps - 1 - step_index))
    if len(offset_values) < horizon:
        raise OPS3FormulaError("the adapter did not provide every required future offset")
    # Extra offsets are allowed at terminal/near-terminal anchors; they are
    # outside H_t and are deliberately not consumed.
    current_start = _finite_nonnegative(
        segment_start_gain_linear,
        field="segment_start_gain_linear",
        size=count,
    )
    # H_t=0 has no projected recurrence and its contract is an all-zero
    # surface.  Requiring a positive, otherwise-unused segment-start gain at
    # that boundary would make terminal scoring depend on projection plumbing.
    if horizon > 0 and np.any(current_start[legal] <= 0.0):
        raise OPS3FormulaError("legal actions need positive segment-start gain")

    static = frozen_background_feature_surface(
        background=background,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        user_count=user_count,
        pmax_w=pmax_w,
        legal_mask=legal,
    )
    zeros = np.zeros((OPS3_HORIZON, count), dtype=np.float64)
    required = np.array(zeros, copy=True)
    persistence = np.array(zeros, copy=True)
    rates = np.array(zeros, copy=True)
    marginal = np.array(zeros, copy=True)
    sinr_values = np.array(zeros, copy=True)
    terms = np.zeros((OPS3_HORIZON, count), dtype=np.float64)
    feature_blocks: list[np.ndarray] = [np.array(static, copy=True)]
    active = np.array(opening, dtype=np.bool_, copy=True)

    for offset_index in range(OPS3_HORIZON):
        offset_number = offset_index + 1
        valid_horizon = offset_number <= horizon
        if valid_horizon:
            offset = offset_values[offset_index]
            projected = np.asarray(offset.projected_gain_linear, dtype=np.float64)
            req = _projected_required_power(
                start_gain=current_start,
                projected_gain=projected,
                legal_mask=legal,
                p0_w=p0_w,
            )
            infeasible = classify_link_power_feasibility(req, max_power_w=pmax_w)
            rho = legal & active & offset.d2_eligible & offset.cell_visible
            rho &= projected > 0.0
            rho &= ~infeasible
            active &= rho
            chi = active.astype(np.float64)
            delta_power = marginal_network_power_surface(
                background=background,
                candidate_norad_ids=norads,
                candidate_cell_ids=cells,
                candidate_power_w=req,
                legal_mask=legal,
            )
            rate = np.where(active, offset.focal_rate_bps, 0.0)
            power = np.where(active, delta_power, 0.0)
            sinr = np.where(active, offset.focal_sinr_linear, 0.0)
            with np.errstate(over="raise", invalid="raise"):
                try:
                    terms[offset_index] = np.where(
                        legal,
                        chi * float(interval_s) * (rate - float(lambda_bits_per_j) * power)
                        - (1.0 - chi) * float(kappa_bits),
                        0.0,
                    )
                except FloatingPointError as error:
                    raise OPS3FormulaError("OPS3 surplus arithmetic overflowed") from error
            required[offset_index] = np.where(legal, req, 0.0)
            persistence[offset_index] = chi
            rates[offset_index] = rate
            marginal[offset_index] = power
            sinr_values[offset_index] = sinr
            required_ratio = np.where(legal & (projected > 0.0), req / float(pmax_w), 0.0)
            log_sinr = np.where(active, np.log1p(sinr), 0.0)
            feature_blocks.append(
                np.stack(
                    [
                        # First value is the contract's valid-horizon bit on
                        # a native legal row: valid_horizon is true in this
                        # branch, and illegal rows remain zero-filled.
                        legal.astype(np.float64),
                        chi,
                        required_ratio,
                        log_sinr,
                    ],
                    axis=1,
                )
            )
        else:
            feature_blocks.append(np.zeros((count, 4), dtype=np.float64))

    if horizon == 0:
        # Terminal anchors have no future action to project.  The contract
        # requires an all-zero legal surface, including features.
        features = np.zeros((count, OPS3_FEATURE_DIM), dtype=np.float64)
    else:
        features = np.concatenate(feature_blocks, axis=1)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            z = terms[:horizon].sum(axis=0) / float(horizon) if horizon else np.zeros(count, dtype=np.float64)
            q2 = (z - z[reference_action]) / float(kappa_bits) if reference_action >= 0 else np.zeros(count, dtype=np.float64)
        except FloatingPointError as error:
            raise OPS3FormulaError("OPS3 target centering overflowed") from error
    z = np.where(legal, z, 0.0)
    q2 = np.where(legal, q2, 0.0)
    if not np.all(np.isfinite(z)) or not np.all(np.isfinite(q2)):
        raise OPS3FormulaError("OPS3 target surface is non-finite")
    if reference_action >= 0 and q2[reference_action] != 0.0:
        raise OPS3FormulaError("reference Q2 row is not exact zero")
    return OPS3Surface(
        z2_bits=z,
        q2_values=q2,
        features=features,
        required_power_w=required,
        persistence=persistence,
        rate_bps=rates,
        marginal_power_w=marginal,
        sinr_linear=sinr_values,
        legal_mask=legal,
        opening_service_feasible=opening,
        reference_action=reference_action,
        horizon=horizon,
    )


__all__ = [
    "OPS3_BACKGROUND_SCHEMA",
    "OPS3_FEATURE_DIM",
    "OPS3_HORIZON",
    "OPS3_INTERVAL_S",
    "OPS3_KAPPA_BITS",
    "OPS3_LAMBDA_BITS_PER_J",
    "OPS3_OFFSET_SCHEMA",
    "OPS3_PROJECTION_SCHEMA",
    "OPS3_SCHEMA",
    "OPS3FormulaError",
    "OPS3FrozenBackground",
    "OPS3Offset",
    "OPS3ProjectionProvider",
    "OPS3Surface",
    "build_ops3_surface",
    "canonical_network_power_w",
    "collect_ops3_offsets",
    "frozen_background_feature_surface",
    "marginal_network_power_surface",
    "opening_service_feasibility_surface",
    "segment_start_gain_surface",
]
