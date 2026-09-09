"""Pure V0.12 current-slot C3 target formulas.

The V0.12 C3 lane is deliberately a formula-only adapter.  It receives a
branch-specific current-slot baseline and the current-slot non-focal rate
vector for each native action.  ZR uses the C3-free joint reference as its
baseline; HR uses the same reference with only the focal user removed.  It
does not call the simulator, contain an energy term, use ``lambda``, project a
future horizon, or select actions.

For action ``a`` and non-focal victim ``v`` let

``e[a, v] = interval_s * (candidate_rate[a, v] - baseline_rate[v])``.

The two preregistered candidate surfaces are:

* **ZR** (zero-energy-supported spatial redistribution):
  ``x[a] = sum_v min(e[a,v], 0) + g[a] * sum_v max(e[a,v], 0)``;
* **HR** (harm-reduction): ``L[a] = sum_v max(-e[a,v], 0)`` and
  ``r[a] = L[reference] - L[a]``.  Negative relief is always retained;
  positive relief is retained only when ``g[a]`` is true.

Both surfaces are centred on the exact reference row and zeroed outside the
native safe mask.  ``g`` is a bit-exact current-slot compatibility gate: the
served vector, ordered active-beam vector, ordered active-satellite vector,
per-beam RF vector, and canonical network power must all match the baseline.
The compatibility gate is a support condition, not a numeric energy reward.

This module owns no deployment policy and no training code.  All returned
arrays are copied and read-only so a caller cannot mutate a sealed formula
surface through an input alias.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


ZERO_MARGINAL_C3_SCHEMA = "multi-catfish-mcrl-v012-zero-marginal-c3-surface-v1"
ZERO_MARGINAL_C3_FORMULAS = ("ZR", "HR")


class ZeroMarginalC3Error(MCRLContractError):
    """A V0.12 C3 formula or compatibility input is malformed."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    """Copy an array into C order and seal it against mutation."""

    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _as_float_array(value: object, *, field: str, ndim: int | None = None) -> np.ndarray:
    """Convert a numeric input while rejecting non-finite values."""

    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise ZeroMarginalC3Error(f"{field} must be a finite numeric array") from error
    if ndim is not None and result.ndim != ndim:
        raise ZeroMarginalC3Error(f"{field} must have ndim={ndim}")
    if not np.all(np.isfinite(result)):
        raise ZeroMarginalC3Error(f"{field} must be finite")
    return np.array(result, dtype=np.float64, copy=True, order="C")


def _rates(value: object, *, field: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    result = _as_float_array(value, field=field)
    if result.ndim not in (1, 2):
        raise ZeroMarginalC3Error(f"{field} must be one- or two-dimensional")
    if shape is not None and result.shape != shape:
        raise ZeroMarginalC3Error(f"{field} must have shape {shape}, got {result.shape}")
    if np.any(result < 0.0):
        raise ZeroMarginalC3Error(f"{field} must be non-negative")
    return result


def _bool_vector(value: object, *, field: str, size: int) -> np.ndarray:
    result = np.asarray(value)
    if result.dtype != np.bool_ or result.shape != (size,):
        raise ZeroMarginalC3Error(f"{field} must be Boolean shape ({size},)")
    return np.array(result, dtype=np.bool_, copy=True, order="C")


def _native_int(value: object, *, field: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ZeroMarginalC3Error(f"{field} must be an integer")
    return int(value)


def _positive_scalar(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ZeroMarginalC3Error(f"{field} must be finite and positive") from error
    if not math.isfinite(result) or result <= 0.0:
        raise ZeroMarginalC3Error(f"{field} must be finite and positive")
    return result


def _validate_formula(value: object) -> Literal["ZR", "HR"]:
    if value not in ZERO_MARGINAL_C3_FORMULAS:
        raise ZeroMarginalC3Error(
            f"formula must be one of {ZERO_MARGINAL_C3_FORMULAS}, got {value!r}"
        )
    return value  # type: ignore[return-value]


def _validate_reference(
    reference_action: object, *, legal_mask: np.ndarray
) -> int:
    reference = _native_int(reference_action, field="reference_action")
    if bool(np.any(legal_mask)):
        if not 0 <= reference < NUM_ACTIONS or not bool(legal_mask[reference]):
            raise ZeroMarginalC3Error(
                "a nonempty safe mask requires a legal native reference_action"
            )
    elif reference != -1:
        raise ZeroMarginalC3Error(
            "an empty safe mask requires reference_action=-1"
        )
    return reference


def _validate_rate_panel(
    baseline_rate_bps: object,
    candidate_rate_bps: object,
) -> tuple[np.ndarray, np.ndarray]:
    baseline = _rates(baseline_rate_bps, field="baseline_rate_bps")
    candidate = _rates(candidate_rate_bps, field="candidate_rate_bps")
    if baseline.ndim != 1:
        raise ZeroMarginalC3Error("baseline_rate_bps must have shape (victims,)")
    if candidate.ndim != 2 or candidate.shape[0] != NUM_ACTIONS:
        raise ZeroMarginalC3Error(
            "candidate_rate_bps must have shape (28, victims)"
        )
    if candidate.shape[1] != baseline.size:
        raise ZeroMarginalC3Error(
            "candidate_rate_bps and baseline_rate_bps must share the victim axis"
        )
    return baseline, candidate


def _masked(values: np.ndarray, legal_mask: np.ndarray) -> np.ndarray:
    """Return a fresh action vector with illegal rows exactly zero."""

    return np.where(legal_mask, values, 0.0).astype(np.float64, copy=False)


@dataclass(frozen=True)
class CompatibilityResult:
    """Auditable decomposition of the bit-exact support gate ``g``."""

    g: np.ndarray
    served_equal: np.ndarray
    active_beams_equal: np.ndarray
    active_sats_equal: np.ndarray
    rf_equal: np.ndarray
    network_power_equal: np.ndarray
    schema: str = ZERO_MARGINAL_C3_SCHEMA

    def __post_init__(self) -> None:
        values: dict[str, np.ndarray] = {}
        for field in (
            "g",
            "served_equal",
            "active_beams_equal",
            "active_sats_equal",
            "rf_equal",
            "network_power_equal",
        ):
            value = np.asarray(getattr(self, field))
            if value.dtype != np.bool_ or value.ndim != 1:
                raise ZeroMarginalC3Error(
                    f"{field} must be a one-dimensional Boolean vector"
                )
            values[field] = np.array(value, dtype=np.bool_, copy=True, order="C")
        size = values["g"].size
        if any(value.size != size for name, value in values.items() if name != "g"):
            raise ZeroMarginalC3Error("compatibility components have mismatched lengths")
        conjunction = (
            values["served_equal"]
            & values["active_beams_equal"]
            & values["active_sats_equal"]
            & values["rf_equal"]
            & values["network_power_equal"]
        )
        if not np.array_equal(values["g"], conjunction):
            raise ZeroMarginalC3Error(
                "g is not the conjunction of all bit-exact compatibility components"
            )
        if self.schema != ZERO_MARGINAL_C3_SCHEMA:
            raise ZeroMarginalC3Error("compatibility schema is stale")
        for field, value in values.items():
            object.__setattr__(self, field, _readonly(value, dtype=np.bool_))

    @property
    def action_count(self) -> int:
        return int(self.g.size)


def _panel_match(
    baseline: object,
    candidate: object,
    *,
    field: str,
    finite: bool = True,
) -> np.ndarray:
    """Compare every candidate row to one baseline vector exactly.

    Shapes are intentionally strict.  No sorting or tolerance is applied to
    active identities, RF vectors, or served vectors; their order is part of
    the identity contract.
    """

    try:
        baseline_array = np.asarray(baseline)
        candidate_array = np.asarray(candidate)
    except (TypeError, ValueError) as error:
        raise ZeroMarginalC3Error(f"{field} identity arrays are malformed") from error
    if baseline_array.ndim != 1 or candidate_array.ndim != 2:
        raise ZeroMarginalC3Error(
            f"{field} must be baseline shape (n,) and candidate shape (28, n)"
        )
    if candidate_array.shape[0] != NUM_ACTIONS or candidate_array.shape[1:] != baseline_array.shape:
        raise ZeroMarginalC3Error(
            f"{field} candidate shape must be (28, {baseline_array.size})"
        )
    if baseline_array.dtype == np.dtype("O") or candidate_array.dtype == np.dtype("O"):
        raise ZeroMarginalC3Error(f"{field} must not use object dtype")
    if finite and (
        np.issubdtype(baseline_array.dtype, np.number)
        or np.issubdtype(candidate_array.dtype, np.number)
    ):
        try:
            if not np.all(np.isfinite(baseline_array)) or not np.all(np.isfinite(candidate_array)):
                raise ZeroMarginalC3Error(f"{field} must be finite")
        except TypeError as error:
            raise ZeroMarginalC3Error(f"{field} must be finite numeric data") from error
    def exact(left: np.ndarray, right: np.ndarray) -> bool:
        return bool(
            left.dtype.str == right.dtype.str
            and left.shape == right.shape
            and np.ascontiguousarray(left).tobytes(order="C")
            == np.ascontiguousarray(right).tobytes(order="C")
        )

    # Compare bytes, not merely numeric values: signed zero or dtype drift
    # cannot silently grant target support.
    return np.asarray(
        [exact(candidate_array[index], baseline_array) for index in range(NUM_ACTIONS)],
        dtype=np.bool_,
    )


def _scalar_match(
    baseline: object,
    candidate: object,
    *,
    field: str,
) -> np.ndarray:
    try:
        baseline_array = np.asarray(baseline)
        candidate_array = np.asarray(candidate)
    except (TypeError, ValueError) as error:
        raise ZeroMarginalC3Error(f"{field} values are malformed") from error
    if baseline_array.ndim != 0 or candidate_array.shape != (NUM_ACTIONS,):
        raise ZeroMarginalC3Error(
            f"{field} must be a scalar baseline and a (28,) candidate vector"
        )
    if not np.issubdtype(baseline_array.dtype, np.number) or not np.issubdtype(
        candidate_array.dtype, np.number
    ):
        raise ZeroMarginalC3Error(f"{field} must be numeric")
    if not np.isfinite(baseline_array).item() or not np.all(np.isfinite(candidate_array)):
        raise ZeroMarginalC3Error(f"{field} must be finite")
    if float(baseline_array) < 0.0 or np.any(candidate_array < 0.0):
        raise ZeroMarginalC3Error(f"{field} must be non-negative")
    return np.asarray(
        [
            candidate_array.dtype.str == baseline_array.dtype.str
            and np.ascontiguousarray(candidate_array[index]).tobytes(order="C")
            == np.ascontiguousarray(baseline_array).tobytes(order="C")
            for index in range(NUM_ACTIONS)
        ],
        dtype=np.bool_,
    )


def build_bit_exact_compatibility(
    *,
    baseline_served: object,
    candidate_served: object,
    baseline_active_beams: object,
    candidate_active_beams: object,
    baseline_active_sats: object,
    candidate_active_sats: object,
    baseline_rf_power: object,
    candidate_rf_power: object,
    baseline_network_power: object,
    candidate_network_power: object,
) -> CompatibilityResult:
    """Build the five-factor current-slot compatibility gate.

    ``active_beams`` and ``active_sats`` are compared as ordered vectors; the
    function never canonicalises them as sets.  ``baseline_network_power`` is
    the scalar ``P^N`` of the C3-free joint reference and candidate power is
    one scalar per native action.  The returned ``g`` is true exactly when all
    five row-wise equalities hold.
    """

    served_equal = _panel_match(
        baseline_served, candidate_served, field="served_vector"
    )
    active_beams_equal = _panel_match(
        baseline_active_beams, candidate_active_beams, field="active_beams"
    )
    active_sats_equal = _panel_match(
        baseline_active_sats, candidate_active_sats, field="active_sats"
    )
    rf_equal = _panel_match(
        baseline_rf_power, candidate_rf_power, field="per_beam_rf_vector"
    )
    network_power_equal = _scalar_match(
        baseline_network_power,
        candidate_network_power,
        field="network_power",
    )
    g = (
        served_equal
        & active_beams_equal
        & active_sats_equal
        & rf_equal
        & network_power_equal
    )
    return CompatibilityResult(
        g=g,
        served_equal=served_equal,
        active_beams_equal=active_beams_equal,
        active_sats_equal=active_sats_equal,
        rf_equal=rf_equal,
        network_power_equal=network_power_equal,
    )


def bit_exact_compatibility(**kwargs: object) -> np.ndarray:
    """Return only ``g`` for callers that do not need the component receipt."""

    return build_bit_exact_compatibility(**kwargs).g


compute_bit_exact_compatibility = bit_exact_compatibility


def assert_compatibility_identity(result: CompatibilityResult) -> CompatibilityResult:
    """Recheck that a compatibility receipt's ``g`` is not forged."""

    if not isinstance(result, CompatibilityResult):
        raise ZeroMarginalC3Error("result must be a CompatibilityResult")
    expected = (
        result.served_equal
        & result.active_beams_equal
        & result.active_sats_equal
        & result.rf_equal
        & result.network_power_equal
    )
    if not np.array_equal(result.g, expected):
        raise ZeroMarginalC3Error("compatibility identity falsified")
    return result


def compatibility_falsifiers(result: CompatibilityResult) -> dict[str, np.ndarray]:
    """Return immutable per-factor falsifier masks for an audit receipt."""

    assert_compatibility_identity(result)
    return {
        "served_vector": _readonly(~result.served_equal, dtype=np.bool_),
        "active_beams": _readonly(~result.active_beams_equal, dtype=np.bool_),
        "active_sats": _readonly(~result.active_sats_equal, dtype=np.bool_),
        "per_beam_rf_vector": _readonly(~result.rf_equal, dtype=np.bool_),
        "network_power": _readonly(~result.network_power_equal, dtype=np.bool_),
        "g": _readonly(~result.g, dtype=np.bool_),
    }


@dataclass(frozen=True)
class ZeroMarginalC3Surface:
    """Immutable ZR or HR current-slot C3 surface and formula components."""

    formula: Literal["ZR", "HR"]
    baseline_rate_bps: np.ndarray
    candidate_rate_bps: np.ndarray
    delta_bits: np.ndarray
    negative_bits: np.ndarray
    positive_bits: np.ndarray
    harm_bits: np.ndarray
    raw_bits: np.ndarray
    relief_bits: np.ndarray
    z3_bits: np.ndarray
    q3_values: np.ndarray
    compatibility: np.ndarray
    legal_mask: np.ndarray
    reference_action: int
    interval_s: float
    kappa_bits: float
    schema: str = ZERO_MARGINAL_C3_SCHEMA

    def __post_init__(self) -> None:
        formula = _validate_formula(self.formula)
        baseline = _rates(self.baseline_rate_bps, field="baseline_rate_bps")
        candidate = _rates(self.candidate_rate_bps, field="candidate_rate_bps")
        if baseline.ndim != 1 or candidate.shape != (NUM_ACTIONS, baseline.size):
            raise ZeroMarginalC3Error(
                "surface rate arrays do not have the required (victims,) and (28, victims) shapes"
            )
        legal = _bool_vector(self.legal_mask, field="legal_mask", size=NUM_ACTIONS)
        compatibility = _bool_vector(
            self.compatibility, field="compatibility", size=NUM_ACTIONS
        )
        reference = _validate_reference(self.reference_action, legal_mask=legal)
        if np.any(compatibility[~legal]):
            raise ZeroMarginalC3Error(
                "compatibility must be false outside legal_mask"
            )
        interval = _positive_scalar(self.interval_s, field="interval_s")
        kappa = _positive_scalar(self.kappa_bits, field="kappa_bits")
        vector_fields = (
            "negative_bits",
            "positive_bits",
            "harm_bits",
            "raw_bits",
            "relief_bits",
            "z3_bits",
            "q3_values",
        )
        arrays: dict[str, np.ndarray] = {
            "delta_bits": _as_float_array(self.delta_bits, field="delta_bits"),
        }
        if arrays["delta_bits"].shape != candidate.shape:
            raise ZeroMarginalC3Error(
                f"delta_bits must have shape {candidate.shape}, got {arrays['delta_bits'].shape}"
            )
        for field in vector_fields:
            value = _as_float_array(getattr(self, field), field=field)
            if value.shape != (NUM_ACTIONS,) or not np.all(np.isfinite(value)):
                raise ZeroMarginalC3Error(f"{field} must be finite shape (28,)")
            arrays[field] = value
        if self.schema != ZERO_MARGINAL_C3_SCHEMA:
            raise ZeroMarginalC3Error("zero-marginal C3 schema is stale")
        for field, value in arrays.items():
            object.__setattr__(self, field, _readonly(value, dtype=np.float64))
        object.__setattr__(self, "baseline_rate_bps", _readonly(baseline, dtype=np.float64))
        object.__setattr__(self, "candidate_rate_bps", _readonly(candidate, dtype=np.float64))
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))
        object.__setattr__(self, "compatibility", _readonly(compatibility, dtype=np.bool_))
        object.__setattr__(self, "reference_action", reference)
        object.__setattr__(self, "interval_s", interval)
        object.__setattr__(self, "kappa_bits", kappa)
        object.__setattr__(self, "formula", formula)

        # The public constructor is guarded as well as the builder: a caller
        # cannot forge a surface with a nonzero illegal/reference row.
        for field in vector_fields:
            value = arrays[field]
            if np.any(value[~legal] != 0.0):
                raise ZeroMarginalC3Error(f"{field} must be zero outside legal_mask")
        if reference >= 0 and float(arrays["z3_bits"][reference]) != 0.0:
            raise ZeroMarginalC3Error("reference z3_bits entry must be exact zero")
        if reference >= 0 and float(arrays["q3_values"][reference]) != 0.0:
            raise ZeroMarginalC3Error("reference q3_values entry must be exact zero")
        expected_delta = interval * (candidate - baseline[None, :])
        expected_delta = np.where(legal[:, None], expected_delta, 0.0)
        if not np.array_equal(arrays["delta_bits"], expected_delta):
            raise ZeroMarginalC3Error("delta_bits do not match the sealed rate difference")
        expected_negative = np.where(
            legal,
            np.sum(np.minimum(expected_delta, 0.0), axis=1, dtype=np.float64),
            0.0,
        )
        expected_positive = np.where(
            legal,
            np.sum(np.maximum(expected_delta, 0.0), axis=1, dtype=np.float64),
            0.0,
        )
        expected_harm = -expected_negative
        if not np.array_equal(arrays["negative_bits"], expected_negative):
            raise ZeroMarginalC3Error("negative_bits do not match the rate deltas")
        if not np.array_equal(arrays["positive_bits"], expected_positive):
            raise ZeroMarginalC3Error("positive_bits do not match the rate deltas")
        if not np.array_equal(arrays["harm_bits"], expected_harm):
            raise ZeroMarginalC3Error("harm_bits do not match the rate deltas")
        if formula == "ZR":
            expected_raw = np.where(
                legal,
                expected_negative + compatibility.astype(np.float64) * expected_positive,
                0.0,
            )
            expected_relief = np.zeros(NUM_ACTIONS, dtype=np.float64)
            expected_centered = (
                expected_raw - expected_raw[reference]
                if reference >= 0
                else np.zeros(NUM_ACTIONS, dtype=np.float64)
            )
        else:
            expected_raw = expected_harm
            expected_relief = np.where(
                legal,
                expected_harm[reference] - expected_harm
                if reference >= 0
                else 0.0,
                0.0,
            )
            expected_centered = np.minimum(expected_relief, 0.0) + compatibility.astype(
                np.float64
            ) * np.maximum(expected_relief, 0.0)
            expected_centered = np.where(legal, expected_centered, 0.0)
        expected_centered = np.where(legal, expected_centered, 0.0)
        if reference >= 0:
            expected_centered[reference] = 0.0
        expected_q = expected_centered / kappa
        for field, expected in (
            ("raw_bits", expected_raw),
            ("relief_bits", expected_relief),
            ("z3_bits", expected_centered),
            ("q3_values", expected_q),
        ):
            if not np.array_equal(arrays[field], expected):
                raise ZeroMarginalC3Error(f"{field} does not match the {formula} formula")

    @property
    def g(self) -> np.ndarray:
        return self.compatibility

    @property
    def x3_bits(self) -> np.ndarray:
        """Alias for the uncentred candidate surface used in receipts."""

        return self.raw_bits

    @property
    def centered_bits(self) -> np.ndarray:
        return self.z3_bits

    @property
    def zr_bits(self) -> np.ndarray:
        if self.formula != "ZR":
            raise ZeroMarginalC3Error("zr_bits is unavailable on an HR surface")
        return self.z3_bits

    @property
    def hr_bits(self) -> np.ndarray:
        if self.formula != "HR":
            raise ZeroMarginalC3Error("hr_bits is unavailable on a ZR surface")
        return self.z3_bits


def _build_surface(
    *,
    formula: Literal["ZR", "HR"],
    baseline_rate_bps: object,
    candidate_rate_bps: object,
    compatibility: object,
    legal_mask: object,
    reference_action: object,
    interval_s: object,
    kappa_bits: object,
) -> ZeroMarginalC3Surface:
    selected_formula = _validate_formula(formula)
    baseline, candidate = _validate_rate_panel(
        baseline_rate_bps, candidate_rate_bps
    )
    legal = _bool_vector(legal_mask, field="legal_mask", size=NUM_ACTIONS)
    gate = _bool_vector(compatibility, field="compatibility", size=NUM_ACTIONS)
    reference = _validate_reference(reference_action, legal_mask=legal)
    if np.any(gate[~legal]):
        raise ZeroMarginalC3Error(
            "compatibility must be false outside legal_mask"
        )
    interval = _positive_scalar(interval_s, field="interval_s")
    kappa = _positive_scalar(kappa_bits, field="kappa_bits")

    raw_delta = interval * (candidate - baseline[None, :])
    # Derive every action component before masking, then mask all formula
    # outputs.  This makes the native illegal-zero convention auditable.
    negative = np.sum(np.minimum(raw_delta, 0.0), axis=1, dtype=np.float64)
    positive = np.sum(np.maximum(raw_delta, 0.0), axis=1, dtype=np.float64)
    harm = -negative
    if not np.all(np.isfinite(raw_delta)) or not np.all(
        np.isfinite(np.asarray([*negative, *positive, *harm], dtype=np.float64))
    ):
        raise ZeroMarginalC3Error("C3 formula arithmetic is non-finite")

    negative = _masked(negative, legal)
    positive = _masked(positive, legal)
    harm = _masked(harm, legal)
    if selected_formula == "ZR":
        raw = negative + gate.astype(np.float64) * positive
        relief = np.zeros(NUM_ACTIONS, dtype=np.float64)
        if reference >= 0:
            centered = raw - raw[reference]
        else:
            centered = np.zeros(NUM_ACTIONS, dtype=np.float64)
    else:
        raw = harm
        relief = np.zeros(NUM_ACTIONS, dtype=np.float64)
        if reference >= 0:
            relief = _masked(harm[reference] - harm, legal)
        # A harmful change is always retained.  A positive relief is a
        # compatibility-gated credit and cannot enter from an unsupported
        # branch.
        centered = np.minimum(relief, 0.0) + gate.astype(np.float64) * np.maximum(
            relief, 0.0
        )

    raw = _masked(raw, legal)
    relief = _masked(relief, legal)
    centered = _masked(centered, legal)
    if reference >= 0:
        # Avoid a signed-zero or subtraction artefact in the exact reference
        # cell; the reference is a gauge, not a measured action effect.
        centered[reference] = 0.0
    q3 = centered / kappa
    q3 = _masked(q3, legal)
    return ZeroMarginalC3Surface(
        formula=selected_formula,
        baseline_rate_bps=baseline,
        candidate_rate_bps=candidate,
        delta_bits=np.where(legal[:, None], raw_delta, 0.0),
        negative_bits=negative,
        positive_bits=positive,
        harm_bits=harm,
        raw_bits=raw,
        relief_bits=relief,
        z3_bits=centered,
        q3_values=q3,
        compatibility=gate,
        legal_mask=legal,
        reference_action=reference,
        interval_s=interval,
        kappa_bits=kappa,
    )


def build_zero_marginal_c3_surface(
    *,
    formula: Literal["ZR", "HR"],
    baseline_rate_bps: object,
    candidate_rate_bps: object,
    compatibility: object,
    legal_mask: object,
    reference_action: object,
    interval_s: object = 1.0,
    kappa_bits: object = 1.0,
) -> ZeroMarginalC3Surface:
    """Build one frozen ZR or HR surface from current-slot rate panels."""

    return _build_surface(
        formula=formula,
        baseline_rate_bps=baseline_rate_bps,
        candidate_rate_bps=candidate_rate_bps,
        compatibility=compatibility,
        legal_mask=legal_mask,
        reference_action=reference_action,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )


def build_zr_surface(
    *,
    baseline_rate_bps: object,
    candidate_rate_bps: object,
    compatibility: object,
    legal_mask: object,
    reference_action: object,
    interval_s: object = 1.0,
    kappa_bits: object = 1.0,
) -> ZeroMarginalC3Surface:
    """Build the ZR zero-energy-supported redistribution surface."""

    return build_zero_marginal_c3_surface(
        formula="ZR",
        baseline_rate_bps=baseline_rate_bps,
        candidate_rate_bps=candidate_rate_bps,
        compatibility=compatibility,
        legal_mask=legal_mask,
        reference_action=reference_action,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )


def build_hr_surface(
    *,
    baseline_rate_bps: object,
    candidate_rate_bps: object,
    compatibility: object,
    legal_mask: object,
    reference_action: object,
    interval_s: object = 1.0,
    kappa_bits: object = 1.0,
) -> ZeroMarginalC3Surface:
    """Build the HR harm-reduction surface."""

    return build_zero_marginal_c3_surface(
        formula="HR",
        baseline_rate_bps=baseline_rate_bps,
        candidate_rate_bps=candidate_rate_bps,
        compatibility=compatibility,
        legal_mask=legal_mask,
        reference_action=reference_action,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )


@dataclass(frozen=True)
class C3IdentityReport:
    """Small, serialisable result for formula identity/falsifier checks."""

    formula: Literal["ZR", "HR"]
    reference_zero: bool
    illegal_zero: bool
    finite: bool
    compatibility_identity: bool
    positive_gate_identity: bool
    passed: bool


def validate_surface_identity(surface: ZeroMarginalC3Surface) -> C3IdentityReport:
    """Check reference, mask, finiteness, and formula identities."""

    if not isinstance(surface, ZeroMarginalC3Surface):
        raise ZeroMarginalC3Error("surface must be a ZeroMarginalC3Surface")
    ref = surface.reference_action
    reference_zero = ref < 0 or (
        surface.z3_bits[ref] == 0.0 and surface.q3_values[ref] == 0.0
    )
    illegal_zero = bool(
        np.all(surface.z3_bits[~surface.legal_mask] == 0.0)
        and np.all(surface.q3_values[~surface.legal_mask] == 0.0)
    )
    finite = bool(
        np.all(np.isfinite(surface.delta_bits))
        and np.all(np.isfinite(surface.z3_bits))
        and np.all(np.isfinite(surface.q3_values))
    )
    compatibility_identity = bool(np.array_equal(surface.g, surface.compatibility))
    if surface.formula == "ZR":
        expected_raw = surface.negative_bits + surface.g.astype(np.float64) * surface.positive_bits
        expected_raw = np.where(surface.legal_mask, expected_raw, 0.0)
        expected_centered = (
            expected_raw - expected_raw[surface.reference_action]
            if surface.reference_action >= 0
            else np.zeros(NUM_ACTIONS, dtype=np.float64)
        )
        expected_centered = np.where(surface.legal_mask, expected_centered, 0.0)
        if surface.reference_action >= 0:
            expected_centered[surface.reference_action] = 0.0
        positive_gate_identity = bool(
            np.array_equal(surface.raw_bits, expected_raw)
            and np.array_equal(surface.z3_bits, expected_centered)
            and np.array_equal(surface.q3_values, expected_centered / surface.kappa_bits)
        )
    else:
        expected = np.minimum(surface.relief_bits, 0.0) + surface.g.astype(np.float64) * np.maximum(
            surface.relief_bits, 0.0
        )
        expected = np.where(surface.legal_mask, expected, 0.0)
        positive_gate_identity = bool(
            np.array_equal(surface.z3_bits, expected)
            and np.array_equal(surface.q3_values, expected / surface.kappa_bits)
        )
    passed = all(
        (
            reference_zero,
            illegal_zero,
            finite,
            compatibility_identity,
            positive_gate_identity,
        )
    )
    return C3IdentityReport(
        formula=surface.formula,
        reference_zero=reference_zero,
        illegal_zero=illegal_zero,
        finite=finite,
        compatibility_identity=compatibility_identity,
        positive_gate_identity=positive_gate_identity,
        passed=passed,
    )


def assert_surface_identity(surface: ZeroMarginalC3Surface) -> C3IdentityReport:
    """Fail closed if a surface's formula or zero conventions are falsified."""

    report = validate_surface_identity(surface)
    if not report.passed:
        raise ZeroMarginalC3Error(f"C3 surface identity falsified: {report}")
    return report


def surface_falsifiers(surface: ZeroMarginalC3Surface) -> dict[str, bool]:
    """Expose named failed checks for a diagnostic receipt."""

    report = validate_surface_identity(surface)
    return {
        "reference_nonzero": not report.reference_zero,
        "illegal_nonzero": not report.illegal_zero,
        "nonfinite": not report.finite,
        "compatibility_identity": not report.compatibility_identity,
        "positive_gate_identity": not report.positive_gate_identity,
    }


__all__ = [
    "C3IdentityReport",
    "CompatibilityResult",
    "ZERO_MARGINAL_C3_FORMULAS",
    "ZERO_MARGINAL_C3_SCHEMA",
    "ZeroMarginalC3Error",
    "ZeroMarginalC3Surface",
    "assert_compatibility_identity",
    "assert_surface_identity",
    "bit_exact_compatibility",
    "build_bit_exact_compatibility",
    "build_hr_surface",
    "build_zero_marginal_c3_surface",
    "build_zr_surface",
    "compatibility_falsifiers",
    "compute_bit_exact_compatibility",
    "surface_falsifiers",
    "validate_surface_identity",
]
