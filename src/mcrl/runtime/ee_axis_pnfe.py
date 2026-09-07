"""Pure projected non-focal externality (PNFE) C3 target.

PNFE assigns C3 only the delivered-bit consequence that a focal candidate
causes for the already committed non-focal service background.  It contains
no focal rate, network-energy, handover-reward, or outage-penalty term.  The
live adapter owns the physical counterfactual; this module only aggregates
authenticated per-offset rate surfaces and applies the common Main gauge.

The frozen V0.9 aggregation is the direct-review ruling:

``X3(a) = e3,0(a) + mean_h=1..Ht e3,h(a)`` when ``Ht > 0`` and
``X3(a) = e3,0(a)`` at a terminal anchor.  Each raw externality is

``e3,h(a) = dt * sum_v!=u (R_v,h(+u,a) - R_v,h(-u))``.

The normally non-positive insertion effect is retained as measured.  Only
the action-independent Main-reference gauge is removed before division by
the shared ``kappa``.  A less harmful action can therefore have a positive
relative Q3 value without reversing the physical sign.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_ops3 import OPS3_HORIZON, OPS3_INTERVAL_S, OPS3_KAPPA_BITS


PNFE_SCHEMA = "multi-catfish-mcrl-v09-c3-pnfe-surface-v1"
PNFE_OFFSET_SCHEMA = "multi-catfish-mcrl-v09-c3-pnfe-offset-v1"


class PNFEFormulaError(MCRLContractError):
    """A PNFE input violates the frozen C3 aggregation contract."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _finite_nonnegative(value: object, *, field: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise PNFEFormulaError(f"{field} must be a finite array") from error
    if not np.all(np.isfinite(result)):
        raise PNFEFormulaError(f"{field} must be finite")
    if np.any(result < 0.0):
        raise PNFEFormulaError(f"{field} must be non-negative")
    return result


@dataclass(frozen=True)
class PNFEOffset:
    """One action-aligned non-focal rate comparison at an offset.

    ``background_rate_bps`` is the one immutable focal-removed branch.
    ``inserted_rate_bps[a]`` is the same branch plus only focal action ``a``.
    The victim columns never include the focal user.  ``focal_active`` is the
    opening/persistence gate inherited from exact OPS-3; inactive insertion
    rows contribute exact zero rather than a second outage penalty.
    """

    background_rate_bps: np.ndarray
    inserted_rate_bps: np.ndarray
    focal_active: np.ndarray
    schema: str = PNFE_OFFSET_SCHEMA

    def __post_init__(self) -> None:
        background = _finite_nonnegative(
            self.background_rate_bps, field="background_rate_bps"
        )
        inserted = _finite_nonnegative(
            self.inserted_rate_bps, field="inserted_rate_bps"
        )
        active = np.asarray(self.focal_active)
        if background.ndim != 1:
            raise PNFEFormulaError("background_rate_bps must be one-dimensional")
        if inserted.shape != (NUM_ACTIONS, background.size):
            raise PNFEFormulaError(
                "inserted_rate_bps must have native action-by-victim shape "
                f"({NUM_ACTIONS}, {background.size})"
            )
        if active.dtype != np.bool_ or active.shape != (NUM_ACTIONS,):
            raise PNFEFormulaError(
                f"focal_active must be Boolean shape ({NUM_ACTIONS},)"
            )
        if self.schema != PNFE_OFFSET_SCHEMA:
            raise PNFEFormulaError("PNFEOffset schema is stale")
        object.__setattr__(
            self,
            "background_rate_bps",
            _readonly(background, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "inserted_rate_bps",
            _readonly(inserted, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "focal_active",
            _readonly(active, dtype=np.bool_),
        )

    @property
    def victim_count(self) -> int:
        return int(self.background_rate_bps.size)


@dataclass(frozen=True)
class PNFESurface:
    """Immutable oracle C3 surface at one focal-user predecision anchor."""

    x3_bits: np.ndarray
    z3_bits: np.ndarray
    q3_values: np.ndarray
    externality_bits: np.ndarray
    focal_active: np.ndarray
    legal_mask: np.ndarray
    reference_action: int
    horizon: int
    schema: str = PNFE_SCHEMA

    def __post_init__(self) -> None:
        for field in ("x3_bits", "z3_bits", "q3_values"):
            value = np.asarray(getattr(self, field), dtype=np.float64)
            if value.shape != (NUM_ACTIONS,) or not np.all(np.isfinite(value)):
                raise PNFEFormulaError(
                    f"{field} must be finite shape ({NUM_ACTIONS},)"
                )
            object.__setattr__(self, field, _readonly(value, dtype=np.float64))
        externality = np.asarray(self.externality_bits, dtype=np.float64)
        active = np.asarray(self.focal_active)
        legal = np.asarray(self.legal_mask)
        expected = (OPS3_HORIZON + 1, NUM_ACTIONS)
        if externality.shape != expected or not np.all(np.isfinite(externality)):
            raise PNFEFormulaError(
                f"externality_bits must be finite shape {expected}"
            )
        if active.dtype != np.bool_ or active.shape != expected:
            raise PNFEFormulaError(f"focal_active must be Boolean shape {expected}")
        if legal.dtype != np.bool_ or legal.shape != (NUM_ACTIONS,):
            raise PNFEFormulaError(
                f"legal_mask must be Boolean shape ({NUM_ACTIONS},)"
            )
        if type(self.reference_action) is not int or not (
            -1 <= self.reference_action < NUM_ACTIONS
        ):
            raise PNFEFormulaError("reference_action is outside the native surface")
        if type(self.horizon) is not int or not 0 <= self.horizon <= OPS3_HORIZON:
            raise PNFEFormulaError("horizon must be in [0, 3]")
        if self.schema != PNFE_SCHEMA:
            raise PNFEFormulaError("PNFESurface schema is stale")
        object.__setattr__(
            self, "externality_bits", _readonly(externality, dtype=np.float64)
        )
        object.__setattr__(self, "focal_active", _readonly(active, dtype=np.bool_))
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))


def _externality_bits(
    offset: PNFEOffset,
    *,
    legal: np.ndarray,
    interval_s: float,
) -> np.ndarray:
    if not isinstance(offset, PNFEOffset):
        raise PNFEFormulaError("each offset must be a PNFEOffset")
    difference = offset.inserted_rate_bps - offset.background_rate_bps[None, :]
    value = float(interval_s) * np.sum(difference, axis=1, dtype=np.float64)
    value = np.where(legal & offset.focal_active, value, 0.0)
    if not np.all(np.isfinite(value)):
        raise PNFEFormulaError("non-focal externality arithmetic is non-finite")
    return value


def build_pnfe_surface(
    *,
    legal_mask: object,
    reference_action: int,
    opening: PNFEOffset,
    future: Sequence[PNFEOffset],
    step_index: int,
    total_steps: int,
    interval_s: float = OPS3_INTERVAL_S,
    kappa_bits: float = OPS3_KAPPA_BITS,
) -> PNFESurface:
    """Aggregate opening and projected non-focal rate differences into Q3."""

    legal = np.asarray(legal_mask)
    if legal.dtype != np.bool_ or legal.shape != (NUM_ACTIONS,):
        raise PNFEFormulaError(
            f"legal_mask must be Boolean shape ({NUM_ACTIONS},)"
        )
    if bool(np.any(legal)):
        if (
            type(reference_action) is not int
            or not 0 <= reference_action < NUM_ACTIONS
            or not bool(legal[reference_action])
        ):
            raise PNFEFormulaError("a nonempty mask needs a legal reference action")
    elif reference_action != -1:
        raise PNFEFormulaError("an empty mask requires reference_action=-1")
    if type(step_index) is not int or step_index < 0:
        raise PNFEFormulaError("step_index must be a non-negative integer")
    if type(total_steps) is not int or total_steps < 1 or step_index >= total_steps:
        raise PNFEFormulaError("step_index must be inside a positive episode")
    for field, value in (("interval_s", interval_s), ("kappa_bits", kappa_bits)):
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise PNFEFormulaError(f"{field} must be finite and positive")
    if not isinstance(opening, PNFEOffset):
        raise PNFEFormulaError("opening must be a PNFEOffset")
    values = tuple(future)
    horizon = min(OPS3_HORIZON, total_steps - 1 - step_index)
    if len(values) < horizon:
        raise PNFEFormulaError("the adapter did not provide every required future offset")
    if len(values) > OPS3_HORIZON:
        raise PNFEFormulaError("PNFE consumes at most three future offsets")
    if any(not isinstance(value, PNFEOffset) for value in values):
        raise PNFEFormulaError("future offsets must be PNFEOffset values")
    victims = opening.victim_count
    if any(value.victim_count != victims for value in values[:horizon]):
        raise PNFEFormulaError("all PNFE offsets must use one victim universe")

    externality = np.zeros(
        (OPS3_HORIZON + 1, NUM_ACTIONS), dtype=np.float64
    )
    active = np.zeros_like(externality, dtype=np.bool_)
    externality[0] = _externality_bits(
        opening, legal=legal, interval_s=float(interval_s)
    )
    active[0] = legal & opening.focal_active
    for index in range(horizon):
        externality[index + 1] = _externality_bits(
            values[index], legal=legal, interval_s=float(interval_s)
        )
        active[index + 1] = legal & values[index].focal_active

    x3 = np.array(externality[0], copy=True)
    if horizon:
        x3 += np.mean(externality[1 : horizon + 1], axis=0)
    if reference_action >= 0:
        z3 = x3 - x3[reference_action]
        q3 = z3 / float(kappa_bits)
    else:
        z3 = np.zeros(NUM_ACTIONS, dtype=np.float64)
        q3 = np.zeros(NUM_ACTIONS, dtype=np.float64)
    x3 = np.where(legal, x3, 0.0)
    z3 = np.where(legal, z3, 0.0)
    q3 = np.where(legal, q3, 0.0)
    if reference_action >= 0 and q3[reference_action] != 0.0:
        raise PNFEFormulaError("reference Q3 row is not exact zero")
    return PNFESurface(
        x3_bits=x3,
        z3_bits=z3,
        q3_values=q3,
        externality_bits=externality,
        focal_active=active,
        legal_mask=legal,
        reference_action=reference_action,
        horizon=horizon,
    )


__all__ = [
    "PNFE_OFFSET_SCHEMA",
    "PNFE_SCHEMA",
    "PNFEFormulaError",
    "PNFEOffset",
    "PNFESurface",
    "build_pnfe_surface",
]
