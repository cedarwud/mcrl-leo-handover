"""Bounded V0.21 mechanics for a conditional-expected ZR C3 surface.

The expectation is taken over complete, per-draw nonlinear ZR labels.  It is
therefore deliberately different from applying the ZR formula to an averaged
channel or averaged rate panel.  This module owns neither action selection nor
episode training.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_zero_marginal_c3_live import ZeroMarginalC3Measurements


EXPECTED_ZR_C3_SCHEMA = "multi-catfish-mcrl-v021-expected-zr-c3-surface-v1"


class ExpectedZRC3Error(MCRLContractError):
    """An expected-ZR input or identity violated the V0.21 boundary."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _positive_scalar(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ExpectedZRC3Error(f"{field} must be finite and positive") from error
    if not math.isfinite(result) or result <= 0.0:
        raise ExpectedZRC3Error(f"{field} must be finite and positive")
    return result


def apply_positive_support_after_centering(
    centred_values: object,
    *,
    compatibility: object,
    legal_mask: object,
    reference_actions: object,
) -> np.ndarray:
    """Keep unsupported centred values non-positive and restore exact gauges."""

    centred = np.asarray(centred_values, dtype=np.float64)
    compatible = np.asarray(compatibility)
    legal = np.asarray(legal_mask)
    references = np.asarray(reference_actions)
    if centred.ndim != 2 or centred.shape[1] != NUM_ACTIONS:
        raise ExpectedZRC3Error("centred_values must have shape (U,28)")
    if not np.all(np.isfinite(centred)):
        raise ExpectedZRC3Error("centred_values must be finite")
    if compatible.dtype != np.bool_ or compatible.shape != centred.shape:
        raise ExpectedZRC3Error("compatibility must be Boolean shape (U,28)")
    if legal.dtype != np.bool_ or legal.shape != centred.shape:
        raise ExpectedZRC3Error("legal_mask must be Boolean shape (U,28)")
    if np.any(compatible & ~legal):
        raise ExpectedZRC3Error("compatibility cannot widen legal_mask")
    if (
        references.ndim != 1
        or references.shape[0] != centred.shape[0]
        or not np.issubdtype(references.dtype, np.integer)
        or np.issubdtype(references.dtype, np.bool_)
    ):
        raise ExpectedZRC3Error("reference_actions must be integer shape (U,)")
    rows = np.arange(centred.shape[0])
    if (
        np.any(references < 0)
        or np.any(references >= NUM_ACTIONS)
        or not np.all(legal[rows, references.astype(np.int64)])
    ):
        raise ExpectedZRC3Error("every reference action must be legal")

    zero = np.zeros_like(centred)
    supported = np.minimum(centred, zero) + compatible.astype(
        np.float64
    ) * np.maximum(centred, zero)
    supported = np.where(legal, supported, 0.0)
    supported[rows, references.astype(np.int64)] = 0.0
    return _readonly(supported, dtype=np.float64)


def zr_q3_from_measurement(
    measurement: ZeroMarginalC3Measurements,
    *,
    kappa_bits: object,
) -> np.ndarray:
    """Build one post-centering-supported nonlinear ZR surface for one draw."""

    if not isinstance(measurement, ZeroMarginalC3Measurements):
        raise ExpectedZRC3Error(
            "measurement must be ZeroMarginalC3Measurements"
        )
    kappa = _positive_scalar(kappa_bits, field="kappa_bits")
    users = int(measurement.reference_actions.size)
    raw = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    for uid in range(users):
        delta = np.asarray(measurement.replacement_delta_bits[uid], dtype=np.float64)
        negative = np.sum(np.minimum(delta, 0.0), axis=1, dtype=np.float64)
        positive = np.sum(np.maximum(delta, 0.0), axis=1, dtype=np.float64)
        raw[uid] = negative + measurement.compatible[uid].astype(
            np.float64
        ) * positive
    rows = np.arange(users)
    centred = raw - raw[rows, measurement.reference_actions][:, None]
    supported = apply_positive_support_after_centering(
        centred,
        compatibility=measurement.compatible,
        legal_mask=measurement.legal_mask,
        reference_actions=measurement.reference_actions,
    )
    return _readonly(np.asarray(supported) / kappa, dtype=np.float64)


@dataclass(frozen=True)
class ExpectedZRC3Surface:
    """One immutable conditional expectation over complete ZR draw labels."""

    q3_values: np.ndarray
    per_draw_q3_values: np.ndarray
    compatibility: np.ndarray
    legal_mask: np.ndarray
    reference_actions: np.ndarray
    integration_draws: int
    kappa_bits: float
    schema: str = EXPECTED_ZR_C3_SCHEMA

    def __post_init__(self) -> None:
        q3 = np.asarray(self.q3_values, dtype=np.float64)
        draws = np.asarray(self.per_draw_q3_values, dtype=np.float64)
        compatibility = np.asarray(self.compatibility)
        legal = np.asarray(self.legal_mask)
        references = np.asarray(self.reference_actions)
        if q3.ndim != 2 or q3.shape[1] != NUM_ACTIONS:
            raise ExpectedZRC3Error("q3_values must have shape (U,28)")
        if draws.ndim != 3 or draws.shape[1:] != q3.shape:
            raise ExpectedZRC3Error(
                "per_draw_q3_values must have shape (K,U,28)"
            )
        if draws.shape[0] != self.integration_draws or draws.shape[0] < 1:
            raise ExpectedZRC3Error("integration_draws does not match draw data")
        if not np.all(np.isfinite(q3)) or not np.all(np.isfinite(draws)):
            raise ExpectedZRC3Error("expected-ZR values must be finite")
        if compatibility.dtype != np.bool_ or compatibility.shape != q3.shape:
            raise ExpectedZRC3Error("compatibility must be Boolean shape (U,28)")
        if legal.dtype != np.bool_ or legal.shape != q3.shape:
            raise ExpectedZRC3Error("legal_mask must be Boolean shape (U,28)")
        if references.shape != (q3.shape[0],):
            raise ExpectedZRC3Error("reference_actions must have shape (U,)")
        if not np.array_equal(q3, np.mean(draws, axis=0, dtype=np.float64)):
            raise ExpectedZRC3Error("q3_values are not the draw-wise expectation")
        rows = np.arange(q3.shape[0])
        if np.any(q3[~legal] != 0.0) or np.any(q3[rows, references] != 0.0):
            raise ExpectedZRC3Error("expected-ZR mask or reference gauge drifted")
        if np.any(q3[legal & ~compatibility] > 0.0):
            raise ExpectedZRC3Error("unsupported positive credit escaped")
        if self.schema != EXPECTED_ZR_C3_SCHEMA:
            raise ExpectedZRC3Error("expected-ZR schema is stale")
        kappa = _positive_scalar(self.kappa_bits, field="kappa_bits")
        object.__setattr__(self, "q3_values", _readonly(q3, dtype=np.float64))
        object.__setattr__(
            self,
            "per_draw_q3_values",
            _readonly(draws, dtype=np.float64),
        )
        object.__setattr__(
            self, "compatibility", _readonly(compatibility, dtype=np.bool_)
        )
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))
        object.__setattr__(
            self, "reference_actions", _readonly(references, dtype=np.int64)
        )
        object.__setattr__(self, "kappa_bits", kappa)


def expected_zr_from_measurements(
    measurements: Iterable[ZeroMarginalC3Measurements],
    *,
    kappa_bits: object,
) -> ExpectedZRC3Surface:
    """Average complete nonlinear ZR labels while holding the anchor fixed."""

    values = iter(measurements)
    try:
        first = next(values)
    except StopIteration as error:
        raise ExpectedZRC3Error("at least one integration draw is required") from error
    if not isinstance(first, ZeroMarginalC3Measurements):
        raise ExpectedZRC3Error(
            "measurements must contain ZeroMarginalC3Measurements"
        )
    kappa = _positive_scalar(kappa_bits, field="kappa_bits")
    reference_actions = np.array(first.reference_actions, dtype=np.int64, copy=True)
    legal_mask = np.array(first.legal_mask, dtype=np.bool_, copy=True)
    compatibility = np.array(first.compatible, dtype=np.bool_, copy=True)
    interval_hex = float(first.interval_s).hex()
    q_draws = [zr_q3_from_measurement(first, kappa_bits=kappa)]
    # A live measurement contains an (U,28,U) rate panel.  Keep only its small
    # Q surface and anchor identities before requesting the next draw.
    del first
    for measurement in values:
        if not isinstance(measurement, ZeroMarginalC3Measurements):
            raise ExpectedZRC3Error(
                "measurements must contain ZeroMarginalC3Measurements"
            )
        if not np.array_equal(measurement.reference_actions, reference_actions):
            raise ExpectedZRC3Error("reference actions changed across integration draws")
        if not np.array_equal(measurement.legal_mask, legal_mask):
            raise ExpectedZRC3Error("legal mask changed across integration draws")
        if not np.array_equal(measurement.compatible, compatibility):
            raise ExpectedZRC3Error("compatibility changed across integration draws")
        if float(measurement.interval_s).hex() != interval_hex:
            raise ExpectedZRC3Error("interval changed across integration draws")
        q_draws.append(zr_q3_from_measurement(measurement, kappa_bits=kappa))
    stacked = np.stack(q_draws, axis=0)
    expected = np.mean(stacked, axis=0, dtype=np.float64)
    return ExpectedZRC3Surface(
        q3_values=expected,
        per_draw_q3_values=stacked,
        compatibility=compatibility,
        legal_mask=legal_mask,
        reference_actions=reference_actions,
        integration_draws=len(q_draws),
        kappa_bits=kappa,
    )


__all__ = [
    "EXPECTED_ZR_C3_SCHEMA",
    "ExpectedZRC3Error",
    "ExpectedZRC3Surface",
    "apply_positive_support_after_centering",
    "expected_zr_from_measurements",
    "zr_q3_from_measurement",
]
