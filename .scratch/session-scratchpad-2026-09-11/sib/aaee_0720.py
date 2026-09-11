"""Pure angle-aware energy-efficiency objective math.

This module implements the Phase 01 v2.2 objective surface as standalone
NumPy functions.  Inputs are linear units: gains are linear, powers are watts,
energies are joules, frame time is seconds, and rates use the caller's rate
unit per second.

``assigned_nmk`` is expected to come from the actual serving assignment after
the simulator has resolved the baseline action/mask for the step.  Pure
hypothetical candidate-link evaluations must pass ``assigned_nmk = 0`` so they
cannot leak into admission, outage, beam power, or per-UE cost attribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]

DEFAULT_EPSILON_NUM = 1e-12
DEFAULT_EWMA_ALPHA = 0.7
DEFAULT_BACKOFF_DB = 5.0
DEFAULT_ETA_MAX = 0.45
DEFAULT_ETA_MIN = 0.08


@dataclass(frozen=True)
class EffectiveGainResult:
    """Effective channel gain plus service-feasibility metadata."""

    g_bar: FloatArray
    g_bar_for_division: FloatArray
    feasible_g: BoolArray
    epsilon_num: FloatArray


@dataclass(frozen=True)
class AdmissionClassification:
    """Link-level admission masks and per-UE service summary."""

    requested_k: BoolArray
    infeasible_nmk: BoolArray
    attempted_link_nmk: BoolArray
    admitted_link_nmk: BoolArray
    attempted_infeasible_nmk: BoolArray
    served_k: BoolArray
    outage_infeasible_k: BoolArray
    service_miss_k: BoolArray


@dataclass(frozen=True)
class PerUeEnergyEfficiencyResult:
    """Beam-local full-cost attribution and per-link UE EE."""

    alpha_nmk: FloatArray
    eta_nmk: FloatArray


@dataclass(frozen=True)
class RewardSurfaceTerms:
    """Raw reward terms for later PopArt-style standardization."""

    throughput_raw: float
    r4_eta_raw: float
    r5_outage_raw: float
    r_service_miss_raw: float
    outage_count: int
    service_miss_count: int
    eta_k: FloatArray


def _as_float_array(value: ArrayLike, name: str) -> FloatArray:
    arr = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _as_bool_array(value: ArrayLike, name: str) -> BoolArray:
    return np.asarray(value, dtype=np.bool_)


def _broadcast_with_ue_axis(
    value: ArrayLike,
    link_shape: tuple[int, ...],
    name: str,
) -> FloatArray:
    """Broadcast a per-link or link-plus-UE value to ``link_shape``."""
    arr = _as_float_array(value, name)
    prefix_shape = link_shape[:-1]
    if arr.shape == link_shape:
        return arr
    if arr.shape == prefix_shape:
        arr = arr[..., np.newaxis]
    elif arr.shape == ():
        pass
    try:
        return np.broadcast_to(arr, link_shape).astype(np.float64, copy=False)
    except ValueError as exc:
        raise ValueError(
            f"{name} with shape {arr.shape} cannot broadcast to link shape "
            f"{link_shape}"
        ) from exc


def _as_ue_mask(value: ArrayLike, ue_count: int, name: str) -> BoolArray:
    arr = _as_bool_array(value, name)
    if arr.shape == ():
        return np.full((ue_count,), bool(arr), dtype=np.bool_)
    if arr.shape == (ue_count,):
        return arr
    raise ValueError(
        f"{name} must be a scalar or shape ({ue_count},), got {arr.shape}"
    )


def _broadcast_ue_mask(mask_k: BoolArray, link_shape: tuple[int, ...]) -> BoolArray:
    reshape = (1,) * (len(link_shape) - 1) + (link_shape[-1],)
    return np.broadcast_to(mask_k.reshape(reshape), link_shape)


def _any_over_link_axes(link_mask: BoolArray) -> BoolArray:
    if link_mask.ndim == 1:
        return link_mask
    return np.any(link_mask, axis=tuple(range(link_mask.ndim - 1)))


def _sum_over_link_axes(values: FloatArray) -> FloatArray:
    if values.ndim == 1:
        return values
    return np.sum(values, axis=tuple(range(values.ndim - 1)), dtype=np.float64)


def effective_gain(
    h_nmk: ArrayLike,
    tx_gain_theta_nmk: ArrayLike,
    rx_gain_nmk: ArrayLike,
    *,
    g_service_min: ArrayLike,
    epsilon_num: ArrayLike | None = None,
) -> EffectiveGainResult:
    """Compute ``g_bar = H * G_T(theta) * G_R``.

    ``h_nmk`` is the HOBS channel factor and is used directly.  Do not pass an
    additional shadowed-fading multiplier here when ``H`` already includes
    shadow fading.
    """
    h = _as_float_array(h_nmk, "h_nmk")
    tx_gain = _as_float_array(tx_gain_theta_nmk, "tx_gain_theta_nmk")
    rx_gain = _as_float_array(rx_gain_nmk, "rx_gain_nmk")
    g_min = _as_float_array(g_service_min, "g_service_min")
    h, tx_gain, rx_gain, g_min = np.broadcast_arrays(h, tx_gain, rx_gain, g_min)

    if np.any(g_min < 0.0):
        raise ValueError("g_service_min must be non-negative")

    g_bar = (h * tx_gain * rx_gain).astype(np.float64, copy=False)
    eps = (
        np.maximum(g_min * 1e-6, DEFAULT_EPSILON_NUM)
        if epsilon_num is None
        else _as_float_array(epsilon_num, "epsilon_num")
    )
    eps = np.broadcast_to(eps, g_bar.shape).astype(np.float64, copy=False)
    if np.any(eps <= 0.0):
        raise ValueError("epsilon_num must be positive")

    return EffectiveGainResult(
        g_bar=g_bar,
        g_bar_for_division=np.maximum(g_bar, eps),
        feasible_g=g_bar >= g_min,
        epsilon_num=eps,
    )


def lagged_interference(
    interference_a_prev: ArrayLike,
    interference_b_prev: ArrayLike,
    *,
    previous_i_hat: ArrayLike | None = None,
    interference_estimate: ArrayLike | None = None,
    alpha: float | None = None,
) -> FloatArray:
    """Compute open-loop lagged interference, optionally with EWMA smoothing."""
    ia_prev = _as_float_array(interference_a_prev, "interference_a_prev")
    ib_prev = _as_float_array(interference_b_prev, "interference_b_prev")
    open_loop = ia_prev + ib_prev

    if previous_i_hat is None and interference_estimate is None:
        return open_loop.astype(np.float64, copy=False)

    ewma_alpha = DEFAULT_EWMA_ALPHA if alpha is None else float(alpha)
    if ewma_alpha < 0.0 or ewma_alpha > 1.0:
        raise ValueError("alpha must be in [0, 1]")
    prev = (
        open_loop
        if previous_i_hat is None
        else _as_float_array(previous_i_hat, "previous_i_hat")
    )
    estimate = (
        open_loop
        if interference_estimate is None
        else _as_float_array(interference_estimate, "interference_estimate")
    )
    prev, estimate = np.broadcast_arrays(prev, estimate)
    return ewma_alpha * prev + (1.0 - ewma_alpha) * estimate


def per_ue_required_tx_power(
    gamma_req_k: ArrayLike,
    interference_hat_nmk: ArrayLike,
    sigma2_w: ArrayLike,
    g_bar_nmk: ArrayLike,
    *,
    epsilon_num: ArrayLike = DEFAULT_EPSILON_NUM,
) -> FloatArray:
    """Compute ``p_req = gamma_req * (I_hat + sigma2) / g_bar`` in watts."""
    gamma_req = _as_float_array(gamma_req_k, "gamma_req_k")
    i_hat = _as_float_array(interference_hat_nmk, "interference_hat_nmk")
    sigma2 = _as_float_array(sigma2_w, "sigma2_w")
    g_bar = _as_float_array(g_bar_nmk, "g_bar_nmk")
    eps = _as_float_array(epsilon_num, "epsilon_num")
    if np.any(gamma_req < 0.0) or np.any(i_hat < 0.0) or np.any(sigma2 < 0.0):
        raise ValueError("gamma_req, interference_hat, and sigma2 must be non-negative")
    if np.any(eps <= 0.0):
        raise ValueError("epsilon_num must be positive")
    gamma_req, i_hat, sigma2, g_bar, eps = np.broadcast_arrays(
        gamma_req, i_hat, sigma2, g_bar, eps
    )
    return gamma_req * (i_hat + sigma2) / np.maximum(g_bar, eps)


def classify_request_admission(
    *,
    within_coverage_k: ArrayLike,
    qos_active_k: ArrayLike,
    assigned_nmk: ArrayLike,
    feasible_g_nmk: ArrayLike,
    p_req_nmk: ArrayLike,
    p_max_nm: ArrayLike,
) -> AdmissionClassification:
    """Classify requested service, link admission, outage, and service miss.

    ``assigned_nmk`` is the actual post-action serving assignment mask for this
    step.  Candidate diagnostics for links that were not selected must pass
    ``assigned_nmk = 0``; otherwise they would be treated as attempted service.
    """
    assigned = _as_bool_array(assigned_nmk, "assigned_nmk")
    feasible_g = _as_bool_array(feasible_g_nmk, "feasible_g_nmk")
    p_req = _as_float_array(p_req_nmk, "p_req_nmk")
    if assigned.shape != feasible_g.shape or assigned.shape != p_req.shape:
        raise ValueError(
            "assigned_nmk, feasible_g_nmk, and p_req_nmk must have the same shape"
        )
    if assigned.ndim < 1:
        raise ValueError("assigned_nmk must include a UE axis")
    if np.any(p_req < 0.0):
        raise ValueError("p_req_nmk must be non-negative")

    ue_count = assigned.shape[-1]
    within_coverage = _as_ue_mask(within_coverage_k, ue_count, "within_coverage_k")
    qos_active = _as_ue_mask(qos_active_k, ue_count, "qos_active_k")
    requested_k = within_coverage & qos_active
    requested_nmk = _broadcast_ue_mask(requested_k, assigned.shape)

    p_max = _broadcast_with_ue_axis(p_max_nm, assigned.shape, "p_max_nm")
    if np.any(p_max < 0.0):
        raise ValueError("p_max_nm must be non-negative")

    infeasible = (~feasible_g) | (p_req > p_max)
    attempted = assigned & requested_nmk
    admitted = attempted & (~infeasible)
    attempted_infeasible = attempted & infeasible

    served_k = requested_k & _any_over_link_axes(admitted)
    outage_infeasible_k = (
        requested_k & (~served_k) & _any_over_link_axes(attempted_infeasible)
    )
    service_miss_k = requested_k & (~served_k) & (~outage_infeasible_k)

    return AdmissionClassification(
        requested_k=requested_k,
        infeasible_nmk=infeasible,
        attempted_link_nmk=attempted,
        admitted_link_nmk=admitted,
        attempted_infeasible_nmk=attempted_infeasible,
        served_k=served_k,
        outage_infeasible_k=outage_infeasible_k,
        service_miss_k=service_miss_k,
    )


def beam_served_set(
    admitted_link_nmk: ArrayLike,
    infeasible_nmk: ArrayLike,
) -> BoolArray:
    """Return ``S_nm`` as a boolean link-plus-UE mask."""
    admitted = _as_bool_array(admitted_link_nmk, "admitted_link_nmk")
    infeasible = _as_bool_array(infeasible_nmk, "infeasible_nmk")
    if admitted.shape != infeasible.shape:
        raise ValueError("admitted_link_nmk and infeasible_nmk must have the same shape")
    return admitted & (~infeasible)


def beam_required_power(
    p_req_nmk: ArrayLike,
    served_set_nmk: ArrayLike,
) -> FloatArray:
    """Compute ``P_req_nm = max_{k in S_nm} p_req_nmk`` with an empty-set guard."""
    p_req = _as_float_array(p_req_nmk, "p_req_nmk")
    served_set = _as_bool_array(served_set_nmk, "served_set_nmk")
    if p_req.shape != served_set.shape:
        raise ValueError("p_req_nmk and served_set_nmk must have the same shape")
    if p_req.ndim < 1:
        raise ValueError("p_req_nmk must include a UE axis")
    if np.any(p_req < 0.0):
        raise ValueError("p_req_nmk must be non-negative")

    any_served = np.any(served_set, axis=-1)
    max_req = np.max(np.where(served_set, p_req, 0.0), axis=-1)
    return np.where(any_served, max_req, 0.0).astype(np.float64, copy=False)


def downlink_power(
    z_nm: ArrayLike,
    p_max_nm: ArrayLike,
    p_req_nm: ArrayLike,
) -> FloatArray:
    """Compute ``P_DL_nm = z_nm * min(P_max_nm, P_req_nm)``."""
    z = _as_float_array(z_nm, "z_nm")
    p_max = _as_float_array(p_max_nm, "p_max_nm")
    p_req = _as_float_array(p_req_nm, "p_req_nm")
    if np.any(z < 0.0) or np.any(p_max < 0.0) or np.any(p_req < 0.0):
        raise ValueError("z_nm, p_max_nm, and p_req_nm must be non-negative")
    z, p_max, p_req = np.broadcast_arrays(z, p_max, p_req)
    return z * np.minimum(p_max, p_req)


def pa_efficiency(
    p_dl_nm: ArrayLike,
    p_max_nm: ArrayLike,
    *,
    backoff_db: float = DEFAULT_BACKOFF_DB,
    eta_max: float = DEFAULT_ETA_MAX,
    eta_min: float = DEFAULT_ETA_MIN,
    constant_eta: float | None = None,
    epsilon_num: float = DEFAULT_EPSILON_NUM,
) -> FloatArray:
    """Compute load-dependent Doherty PA efficiency.

    ``constant_eta`` is an explicit ablation hook.  The default path uses the
    v2.2 load-dependent model.
    """
    p_dl = _as_float_array(p_dl_nm, "p_dl_nm")
    p_max = _as_float_array(p_max_nm, "p_max_nm")
    if np.any(p_dl < 0.0) or np.any(p_max < 0.0):
        raise ValueError("p_dl_nm and p_max_nm must be non-negative")
    if eta_min <= 0.0 or eta_max <= 0.0 or eta_min > eta_max:
        raise ValueError("eta_min and eta_max must be positive with eta_min <= eta_max")
    if epsilon_num <= 0.0:
        raise ValueError("epsilon_num must be positive")

    p_dl, p_max = np.broadcast_arrays(p_dl, p_max)
    if constant_eta is not None:
        constant = float(constant_eta)
        if constant <= 0.0:
            raise ValueError("constant_eta must be positive")
        return np.full(p_dl.shape, constant, dtype=np.float64)

    p_sat = p_max * (10.0 ** (float(backoff_db) / 10.0))
    ratio = p_dl / np.maximum(p_sat, epsilon_num)
    eta = eta_max * np.sqrt(np.maximum(ratio, 0.0))
    return np.clip(eta, eta_min, eta_max).astype(np.float64, copy=False)


def beam_total_power(
    *,
    z_nm: ArrayLike,
    p_circuit_w: ArrayLike,
    p_bb_w: ArrayLike,
    p_dl_nm: ArrayLike,
    eta_pa_nm: ArrayLike,
    e_train_j_nm: ArrayLike = 0.0,
    train_indicator_nm: ArrayLike = 0.0,
    t_f_s: float = 1.0,
    e_switch_j: ArrayLike = 0.0,
    switch_indicator_nm: ArrayLike = 0.0,
) -> FloatArray:
    """Compute consumed power per beam from circuit, PA, train, and switch terms."""
    if t_f_s <= 0.0:
        raise ValueError("t_f_s must be positive")
    z = _as_float_array(z_nm, "z_nm")
    p_circuit = _as_float_array(p_circuit_w, "p_circuit_w")
    p_bb = _as_float_array(p_bb_w, "p_bb_w")
    p_dl = _as_float_array(p_dl_nm, "p_dl_nm")
    eta = _as_float_array(eta_pa_nm, "eta_pa_nm")
    e_train = _as_float_array(e_train_j_nm, "e_train_j_nm")
    train = _as_float_array(train_indicator_nm, "train_indicator_nm")
    e_switch = _as_float_array(e_switch_j, "e_switch_j")
    switch = _as_float_array(switch_indicator_nm, "switch_indicator_nm")

    z, p_circuit, p_bb, p_dl, eta, e_train, train, e_switch, switch = (
        np.broadcast_arrays(
            z, p_circuit, p_bb, p_dl, eta, e_train, train, e_switch, switch
        )
    )
    if (
        np.any(z < 0.0)
        or np.any(p_circuit < 0.0)
        or np.any(p_bb < 0.0)
        or np.any(p_dl < 0.0)
        or np.any(eta <= 0.0)
        or np.any(e_train < 0.0)
        or np.any(train < 0.0)
        or np.any(e_switch < 0.0)
        or np.any(switch < 0.0)
    ):
        raise ValueError("power, energy, indicator, and efficiency values are invalid")

    active_fixed = z * (p_circuit + p_bb)
    pa_power = p_dl / eta
    train_power = e_train * train / t_f_s
    switch_power = e_switch * switch / t_f_s
    return active_fixed + pa_power + train_power + switch_power


def system_energy_efficiency(
    total_rate: float,
    p_tot_nm: ArrayLike,
    *,
    epsilon_num: float = DEFAULT_EPSILON_NUM,
) -> float:
    """Compute system EE as total rate divided by summed ``P_tot``."""
    if total_rate < 0.0:
        raise ValueError("total_rate must be non-negative")
    if epsilon_num <= 0.0:
        raise ValueError("epsilon_num must be positive")
    p_tot = _as_float_array(p_tot_nm, "p_tot_nm")
    if np.any(p_tot < 0.0):
        raise ValueError("p_tot_nm must be non-negative")
    denominator = float(np.sum(p_tot, dtype=np.float64))
    return float(total_rate) / max(denominator, epsilon_num)


def per_ue_energy_efficiency(
    *,
    rates_nmk: ArrayLike,
    admitted_link_nmk: ArrayLike,
    p_req_nmk: ArrayLike,
    p_max_nm: ArrayLike,
    p_tot_nm: ArrayLike,
    p0_w: float = 0.0,
    epsilon_num: float = DEFAULT_EPSILON_NUM,
) -> PerUeEnergyEfficiencyResult:
    """Compute beam-local ``alpha_nmk`` and full-cost ``eta_nmk``."""
    if p0_w < 0.0:
        raise ValueError("p0_w must be non-negative")
    if epsilon_num <= 0.0:
        raise ValueError("epsilon_num must be positive")

    rates = _as_float_array(rates_nmk, "rates_nmk")
    admitted = _as_bool_array(admitted_link_nmk, "admitted_link_nmk")
    p_req = _as_float_array(p_req_nmk, "p_req_nmk")
    if rates.shape != admitted.shape or rates.shape != p_req.shape:
        raise ValueError(
            "rates_nmk, admitted_link_nmk, and p_req_nmk must have the same shape"
        )
    if rates.ndim < 1:
        raise ValueError("rates_nmk must include a UE axis")
    if np.any(rates < 0.0) or np.any(p_req < 0.0):
        raise ValueError("rates_nmk and p_req_nmk must be non-negative")

    p_max = _broadcast_with_ue_axis(p_max_nm, rates.shape, "p_max_nm")
    p_tot = _broadcast_with_ue_axis(p_tot_nm, rates.shape, "p_tot_nm")
    if np.any(p_max < 0.0) or np.any(p_tot < 0.0):
        raise ValueError("p_max_nm and p_tot_nm must be non-negative")

    capped_req = np.minimum(p_req, p_max)
    weighted_req = np.where(admitted, capped_req, 0.0)
    beam_denominator = np.sum(weighted_req, axis=-1, keepdims=True, dtype=np.float64)
    alpha = weighted_req / (beam_denominator + epsilon_num)

    eta_denominator = np.maximum(alpha * p_tot + p0_w, epsilon_num)
    eta = np.where(admitted, rates / eta_denominator, 0.0)
    return PerUeEnergyEfficiencyResult(alpha_nmk=alpha, eta_nmk=eta)


def reward_surface_terms(
    *,
    throughput_raw: float,
    outage_infeasible_k: ArrayLike,
    eta_k: ArrayLike | None = None,
    eta_nmk: ArrayLike | None = None,
    admitted_link_nmk: ArrayLike | None = None,
    service_miss_k: ArrayLike | None = None,
    beta_out: float = 1.0,
    beta_miss: float = 0.0,
) -> RewardSurfaceTerms:
    """Expose raw terms for later PopArt-style running z-score composition.

    When ``eta_nmk`` is collapsed to ``eta_k``, each requested UE may have at
    most one admitted serving link.  Multi-link admission needs an explicit
    caller-provided ``eta_k`` aggregation policy.
    """
    if throughput_raw < 0.0:
        raise ValueError("throughput_raw must be non-negative")
    if beta_out < 0.0 or beta_miss < 0.0:
        raise ValueError("beta_out and beta_miss must be non-negative")

    outage = _as_bool_array(outage_infeasible_k, "outage_infeasible_k")
    service_miss = (
        np.zeros(outage.shape, dtype=np.bool_)
        if service_miss_k is None
        else _as_bool_array(service_miss_k, "service_miss_k")
    )
    if service_miss.shape != outage.shape:
        raise ValueError("service_miss_k must have the same shape as outage_infeasible_k")

    if eta_k is None:
        if eta_nmk is None or admitted_link_nmk is None:
            raise ValueError(
                "Provide eta_k directly or provide eta_nmk with admitted_link_nmk"
            )
        eta_links = _as_float_array(eta_nmk, "eta_nmk")
        admitted = _as_bool_array(admitted_link_nmk, "admitted_link_nmk")
        if eta_links.shape != admitted.shape:
            raise ValueError("eta_nmk and admitted_link_nmk must have the same shape")
        admitted_count_k = _sum_over_link_axes(admitted.astype(np.float64))
        if np.any(admitted_count_k > 1.0):
            raise ValueError(
                "eta_nmk collapse requires at most one admitted link per UE; "
                "provide eta_k for an explicit multi-link aggregation policy"
            )
        eta_values_k = _sum_over_link_axes(np.where(admitted, eta_links, 0.0))
    else:
        eta_values_k = _as_float_array(eta_k, "eta_k")
    if eta_values_k.shape != outage.shape:
        raise ValueError("eta values must resolve to the same UE shape as outage")

    outage_count = int(np.count_nonzero(outage))
    service_miss_count = int(np.count_nonzero(service_miss))
    return RewardSurfaceTerms(
        throughput_raw=float(throughput_raw),
        r4_eta_raw=float(np.sum(eta_values_k, dtype=np.float64)),
        r5_outage_raw=-float(beta_out) * outage_count,
        r_service_miss_raw=-float(beta_miss) * service_miss_count,
        outage_count=outage_count,
        service_miss_count=service_miss_count,
        eta_k=eta_values_k,
    )


DEFAULT_G0_LINEAR: float = 10_000.0
DEFAULT_THETA_3DB_RAD: float = math.radians(2.0)


# The ascending power series in ``_bessel_j_integer`` is exact for small |x|
# but suffers catastrophic float64 cancellation once the largest intermediate
# term (~e^|x| / sqrt(2*pi*|x|)) exceeds ~1e16, i.e. |x| >~ 40 (e.g.
# ``_bessel_j_integer(3, 70)`` returns -5.8e11 vs the true ~-0.0154). The SDD-04
# 7-beam env never drives the Bessel argument past its ANALYTIC geometric ceiling
# mu = 32.38 (horizon nadir angle arcsin(R_E/(R_E+h)) = 62.99 deg at h=780 km, +
# the 2.0 deg ring-beam tilt -> 64.99 deg off-axis -> mu = 2.07123*sin(64.99)/
# sin(0.058) = 32.38; confirmed by a 240-phase x 5-seed full-orbit sweep, max
# 32.3805, zero calls > 34). So this 34.0 threshold (margin 1.62) leaves EVERY
# 7-beam (baseline) gain evaluation on the UNCHANGED series path -- preserving
# baseline bit-identity -- while routing the narrow-beam fidelity env's
# far-satellite mu > 34 evaluations to the numerically stable downward recurrence
# below. NOTE: the 1.62 margin is a property of the scenario constants (780 km
# altitude, 2.0 deg ring tilt); a future scenario change that lowers altitude or
# widens the ring tilt must re-verify mu_ceiling < _BESSEL_SERIES_MAX_ABS_X
# (asserted in tests/test_fidelity_env_landscape_probe.py).
_BESSEL_SERIES_MAX_ABS_X: float = 34.0


def _bessel_j_miller(n: int, x: float) -> float:
    """``J_n(x)`` via Miller's downward recurrence -- numerically stable for all |x|.

    Used only when ``abs(x) > _BESSEL_SERIES_MAX_ABS_X``, where the ascending
    power series in :func:`_bessel_j_integer` loses all precision to cancellation.
    Validated against the series over ``[0, 32]`` (max abs diff ~1e-4) and against
    the first Bessel zeros to ~1e-14. (The series path itself serves ``[0, 34]``;
    its error grows to ~5e-4 at x=34, but the gain bracket divides J by mu and
    mu^3 and squares, so a 5e-4 J error there maps to a ~1e-8 gain effect -- and
    it never touches the bit-identical 7-beam region, mu_ceiling 32.38 < 34.)
    """
    if x < 0.0:
        return (-1.0 if n % 2 else 1.0) * _bessel_j_miller(n, -x)
    ax = x
    start = int(n + ax + 20.0 + 10.0 * math.sqrt(ax))
    if start % 2 == 1:
        start += 1  # keep the highest retained order even for the J0+2*sum normaliser
    j_hi = 0.0  # J_{start+1}
    j_cur = 1.0e-30  # J_{start} seed (arbitrary scale; divided out by the normaliser)
    target = 0.0
    norm = 0.0  # accumulates 2*(J_2 + J_4 + ...)
    for k in range(start, 0, -1):
        j_low = (2.0 * k / ax) * j_cur - j_hi  # J_{k-1}
        if k - 1 == n:
            target = j_low
        if (k - 1) >= 2 and (k - 1) % 2 == 0:
            norm += 2.0 * j_low
        j_hi = j_cur
        j_cur = j_low
        if abs(j_cur) > 1.0e250:  # rescale to avoid overflow far from the turning point
            scale = 1.0e-250
            j_cur *= scale
            j_hi *= scale
            target *= scale
            norm *= scale
    norm += j_cur  # + J_0
    return target / norm


def _bessel_j_integer(n: int, x: float) -> float:
    if n < 0:
        raise ValueError("n must be non-negative")
    if not math.isfinite(x):
        raise ValueError("x must be finite")
    if x == 0.0:
        return 1.0 if n == 0 else 0.0
    if abs(x) > _BESSEL_SERIES_MAX_ABS_X:
        return _bessel_j_miller(n, x)

    term = (0.5 * x) ** n / math.factorial(n)
    total = term
    x2_over_4 = (x * x) / 4.0
    for m in range(200):
        term *= -x2_over_4 / ((m + 1) * (m + n + 1))
        total += term
        if abs(term) <= 1e-15 * max(1.0, abs(total)):
            break
    return float(total)


def approved_transmit_gain_linear(
    theta_rad: ArrayLike,
    *,
    g0_linear: float = DEFAULT_G0_LINEAR,
    theta_3db_rad: float = DEFAULT_THETA_3DB_RAD,
) -> FloatArray:
    """Bessel beam pattern G_T(θ) = G₀·[J₁(μ)/(2μ) + 36·J₃(μ)/μ³]² in linear units."""
    theta = _as_float_array(theta_rad, "theta_rad")
    if g0_linear <= 0.0:
        raise ValueError("g0_linear must be positive")
    if theta_3db_rad <= 0.0:
        raise ValueError("theta_3db_rad must be positive")

    mu = 2.07123 * np.sin(theta) / math.sin(theta_3db_rad)
    gains = np.empty(theta.shape, dtype=np.float64)
    for index in np.ndindex(theta.shape):
        mu_value = float(mu[index])
        if abs(mu_value) < 1e-10:
            gains[index] = float(g0_linear)
            continue
        j1 = _bessel_j_integer(1, mu_value)
        j3 = _bessel_j_integer(3, mu_value)
        bracket = j1 / (2.0 * mu_value) + 36.0 * j3 / (mu_value**3)
        gains[index] = float(g0_linear) * (bracket**2)
    return gains


__all__ = [
    "AdmissionClassification",
    "DEFAULT_BACKOFF_DB",
    "DEFAULT_EPSILON_NUM",
    "DEFAULT_ETA_MAX",
    "DEFAULT_ETA_MIN",
    "DEFAULT_EWMA_ALPHA",
    "DEFAULT_G0_LINEAR",
    "DEFAULT_THETA_3DB_RAD",
    "EffectiveGainResult",
    "PerUeEnergyEfficiencyResult",
    "RewardSurfaceTerms",
    "approved_transmit_gain_linear",
    "beam_required_power",
    "beam_served_set",
    "beam_total_power",
    "classify_request_admission",
    "downlink_power",
    "effective_gain",
    "lagged_interference",
    "pa_efficiency",
    "per_ue_energy_efficiency",
    "per_ue_required_tx_power",
    "reward_surface_terms",
    "system_energy_efficiency",
]
