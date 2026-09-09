"""Low-cost, pre-outcome proxy for the V0.7 C2 B2 candidate.

The final B2 estimand enumerates all 28 native successor actions.  That is too
expensive for the first direction screen because every opening branch creates
another 28-way physical evaluation.  This module fixes an outcome-blind panel
of at most four legal successor actions before any rate, power, target, or EE
outcome is evaluated:

* the frozen reference-policy action;
* highest predecision candidate SINR;
* most approaching signed range rate; and
* most receding signed range rate.

Ties use the lowest native action index and duplicates are removed.  The proxy
can reject a B2 direction cheaply, but it can never authorize final B2 or
support a paper efficacy claim.  Any B2 survivor must be confirmed with the
exact native-28 target in :mod:`ee_axis_v07_c2_parallel_targets` on fresh data.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


V07_C2_B2_PROXY_PANEL_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-b2-four-action-proxy-panel-v1"
)
V07_C2_B2_PROXY_TARGET_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-b2-four-action-proxy-target-v1"
)
V07_C2_B2_PROXY_MAX_ACTIONS = 4


class B2FastProxyContractError(MCRLContractError):
    """The cheap B2 panel or its raw physical measurements are malformed."""


def _finite_vector(value: object, *, field: str, size: int | None = None) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise B2FastProxyContractError(f"{field} must be a finite vector") from error
    if (
        result.ndim != 1
        or result.size < 1
        or (size is not None and result.size != size)
        or not np.all(np.isfinite(result))
    ):
        raise B2FastProxyContractError(f"{field} must be a finite vector")
    return result


def _positive(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise B2FastProxyContractError(f"{field} must be finite and positive") from error
    if not math.isfinite(result) or result <= 0.0:
        raise B2FastProxyContractError(f"{field} must be finite and positive")
    return result


def _lowest_extreme_action(
    values: np.ndarray,
    legal_actions: np.ndarray,
    *,
    maximize: bool,
) -> int:
    legal_values = values[legal_actions]
    extreme = np.max(legal_values) if maximize else np.min(legal_values)
    tied = legal_actions[legal_values == extreme]
    return int(np.min(tied))


@dataclass(frozen=True)
class B2ProxyActionPanel:
    """Outcome-blind native successor actions selected for one branch."""

    actions: tuple[int, ...]
    reference_action: int
    max_sinr_action: int
    most_approaching_action: int
    most_receding_action: int
    claim_ceiling: str = "DIRECTION_SCREEN_ONLY__NOT_FINAL_B2"
    schema: str = V07_C2_B2_PROXY_PANEL_SCHEMA


def select_b2_proxy_action_panel(
    *,
    legal_mask: object,
    reference_action: int,
    candidate_sinr: object,
    signed_range_rate_km_s: object,
) -> B2ProxyActionPanel:
    """Select at most four legal actions without consulting target outcomes."""

    mask = np.asarray(legal_mask)
    if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,):
        raise B2FastProxyContractError(
            f"legal_mask must be Boolean shape ({NUM_ACTIONS},)"
        )
    legal = np.flatnonzero(mask)
    if legal.size < 1:
        raise B2FastProxyContractError("B2 proxy requires a nonempty native mask")
    if (
        type(reference_action) is not int
        or not 0 <= reference_action < NUM_ACTIONS
        or not bool(mask[reference_action])
    ):
        raise B2FastProxyContractError("reference_action must be native and legal")
    sinr = _finite_vector(candidate_sinr, field="candidate_sinr", size=NUM_ACTIONS)
    radial = _finite_vector(
        signed_range_rate_km_s,
        field="signed_range_rate_km_s",
        size=NUM_ACTIONS,
    )
    max_sinr = _lowest_extreme_action(sinr, legal, maximize=True)
    approaching = _lowest_extreme_action(radial, legal, maximize=False)
    receding = _lowest_extreme_action(radial, legal, maximize=True)
    ordered: list[int] = []
    for action in (reference_action, max_sinr, approaching, receding):
        if action not in ordered:
            ordered.append(action)
    return B2ProxyActionPanel(
        actions=tuple(ordered),
        reference_action=reference_action,
        max_sinr_action=max_sinr,
        most_approaching_action=approaching,
        most_receding_action=receding,
    )


def _action_indices(value: object, *, field: str) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)):
        raise B2FastProxyContractError(f"{field} must be an action sequence")
    try:
        result = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise B2FastProxyContractError(f"{field} must be an action sequence") from error
    if (
        not 1 <= len(result) <= V07_C2_B2_PROXY_MAX_ACTIONS
        or len(set(result)) != len(result)
        or any(type(action) is not int or not 0 <= action < NUM_ACTIONS for action in result)
    ):
        raise B2FastProxyContractError(
            f"{field} must contain 1..{V07_C2_B2_PROXY_MAX_ACTIONS} unique native actions"
        )
    return tuple(int(action) for action in result)


@dataclass(frozen=True)
class B2ProxyOptionSetSurplus:
    """Cheap option-panel value; never a replacement for the final native-28 B2."""

    z2_proxy_surplus_bits: float
    candidate_option_value_bits: float
    reference_option_value_bits: float
    candidate_best_action: int
    reference_best_action: int
    candidate_actions: tuple[int, ...]
    reference_actions: tuple[int, ...]
    candidate_action_surplus_bits: tuple[float, ...]
    reference_action_surplus_bits: tuple[float, ...]
    candidate_action_rates_bps: tuple[float, ...]
    reference_action_rates_bps: tuple[float, ...]
    candidate_action_full_power_w: tuple[float, ...]
    candidate_action_without_focal_power_w: tuple[float, ...]
    reference_action_full_power_w: tuple[float, ...]
    reference_action_without_focal_power_w: tuple[float, ...]
    lambda_bits_per_j: float
    interval_s: float
    claim_ceiling: str = "DIRECTION_SCREEN_ONLY__NOT_FINAL_B2"
    schema: str = V07_C2_B2_PROXY_TARGET_SCHEMA


def _panel_value(
    *,
    actions: tuple[int, ...],
    rates: np.ndarray,
    full_power: np.ndarray,
    without_power: np.ndarray,
    multiplier: float,
    interval: float,
) -> tuple[float, int, np.ndarray]:
    if not (rates.shape == full_power.shape == without_power.shape == (len(actions),)):
        raise B2FastProxyContractError("proxy raw vectors disagree with their action panel")
    marginal = full_power - without_power
    with np.errstate(over="ignore", invalid="ignore"):
        surplus = interval * (rates - multiplier * marginal)
    if not np.all(np.isfinite(surplus)):
        raise B2FastProxyContractError("proxy action-surplus arithmetic is non-finite")
    best_value = 0.0
    best_action = -1
    for action, value in sorted(zip(actions, surplus.tolist()), key=lambda item: item[0]):
        if float(value) > best_value:
            best_value = float(value)
            best_action = int(action)
    return best_value, best_action, surplus


def successor_proxy_option_set_target(
    *,
    lambda_bits_per_j: float,
    interval_s: float,
    candidate_actions: object,
    candidate_action_rates_bps: object,
    candidate_action_full_power_w: object,
    candidate_action_without_focal_power_w: object,
    reference_actions: object,
    reference_action_rates_bps: object,
    reference_action_full_power_w: object,
    reference_action_without_focal_power_w: object,
) -> B2ProxyOptionSetSurplus:
    """Compare two predeclared B2 panels in EE-surplus units."""

    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    interval = _positive(interval_s, field="interval_s")
    candidate_indices = _action_indices(candidate_actions, field="candidate_actions")
    reference_indices = _action_indices(reference_actions, field="reference_actions")
    candidate_rate = _finite_vector(
        candidate_action_rates_bps, field="candidate_action_rates_bps"
    )
    candidate_full = _finite_vector(
        candidate_action_full_power_w, field="candidate_action_full_power_w"
    )
    candidate_without = _finite_vector(
        candidate_action_without_focal_power_w,
        field="candidate_action_without_focal_power_w",
    )
    reference_rate = _finite_vector(
        reference_action_rates_bps, field="reference_action_rates_bps"
    )
    reference_full = _finite_vector(
        reference_action_full_power_w, field="reference_action_full_power_w"
    )
    reference_without = _finite_vector(
        reference_action_without_focal_power_w,
        field="reference_action_without_focal_power_w",
    )
    for name, values in (
        ("candidate_action_rates_bps", candidate_rate),
        ("candidate_action_full_power_w", candidate_full),
        ("candidate_action_without_focal_power_w", candidate_without),
        ("reference_action_rates_bps", reference_rate),
        ("reference_action_full_power_w", reference_full),
        ("reference_action_without_focal_power_w", reference_without),
    ):
        if np.any(values < 0.0):
            raise B2FastProxyContractError(f"{name} must be non-negative")
    candidate_value, candidate_best, candidate_surplus = _panel_value(
        actions=candidate_indices,
        rates=candidate_rate,
        full_power=candidate_full,
        without_power=candidate_without,
        multiplier=multiplier,
        interval=interval,
    )
    reference_value, reference_best, reference_surplus = _panel_value(
        actions=reference_indices,
        rates=reference_rate,
        full_power=reference_full,
        without_power=reference_without,
        multiplier=multiplier,
        interval=interval,
    )
    target = candidate_value - reference_value
    if not math.isfinite(target):
        raise B2FastProxyContractError("proxy target arithmetic is non-finite")
    return B2ProxyOptionSetSurplus(
        z2_proxy_surplus_bits=target,
        candidate_option_value_bits=candidate_value,
        reference_option_value_bits=reference_value,
        candidate_best_action=candidate_best,
        reference_best_action=reference_best,
        candidate_actions=candidate_indices,
        reference_actions=reference_indices,
        candidate_action_surplus_bits=tuple(float(value) for value in candidate_surplus),
        reference_action_surplus_bits=tuple(float(value) for value in reference_surplus),
        candidate_action_rates_bps=tuple(float(value) for value in candidate_rate),
        reference_action_rates_bps=tuple(float(value) for value in reference_rate),
        candidate_action_full_power_w=tuple(float(value) for value in candidate_full),
        candidate_action_without_focal_power_w=tuple(float(value) for value in candidate_without),
        reference_action_full_power_w=tuple(float(value) for value in reference_full),
        reference_action_without_focal_power_w=tuple(float(value) for value in reference_without),
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )


__all__ = [
    "B2FastProxyContractError",
    "B2ProxyActionPanel",
    "B2ProxyOptionSetSurplus",
    "V07_C2_B2_PROXY_MAX_ACTIONS",
    "V07_C2_B2_PROXY_PANEL_SCHEMA",
    "V07_C2_B2_PROXY_TARGET_SCHEMA",
    "select_b2_proxy_action_panel",
    "successor_proxy_option_set_target",
]
