"""Formula-only robust development proxy for the V0.7 C2 B2 candidate.

This module is an insurance screen for an already measured, outcome-blind B2
action panel.  It does not call the physical environment, select a new panel,
run a continuation, or train Q2.  The caller supplies the panel actions and
the raw measurements already obtained for each action:

``rate_bps``, ``P_full``, and ``P_without_focal``.

For a branch ``b`` and panel action ``a`` the fixed-lambda action surplus is

``e[b, a] = interval_s * (rate[b, a] - lambda_bits_per_j *
                          (P_full[b, a] - P_without_focal[b, a]))``.

The fixed robust aggregator keeps the two best *positive opportunities* and
always makes the zero-value no-op an outside option.  Missing opportunities
are padded with a second copy of that zero outside option:

``R_b = mean(top_two((0, e[b, a]) for e[b, a] > 0))``.

Thus a harmful or empty panel cannot make a branch worse merely because its
actions were measured, while the final target remains signed:

``z2_robust_proxy = R_candidate - R_reference``.

The panel is capped at four unique native actions.  Panel order is canonicalised
by native action index before receipts are returned, so the target and the
entire receipt are deterministic and order invariant.  This is development
evidence only; it is not the native-28 B2 target and cannot support a final
efficacy claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError


V07_C2_B2_ROBUST_PROXY_PANEL_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-b2-robust-four-action-proxy-panel-v1"
)
V07_C2_B2_ROBUST_PROXY_TARGET_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-b2-robust-top-two-proxy-target-v1"
)
V07_C2_B2_ROBUST_PROXY_MAX_ACTIONS = 4
V07_C2_B2_ROBUST_PROXY_TOP_K = 2


class B2RobustProxyContractError(MCRLContractError):
    """The bounded B2 panel or its raw physical receipts are malformed."""


def _finite_vector(
    value: object,
    *,
    field: str,
    size: int | None = None,
) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise B2RobustProxyContractError(f"{field} must be a finite vector") from error
    if (
        result.ndim != 1
        or result.size < 1
        or (size is not None and result.size != size)
        or not np.all(np.isfinite(result))
    ):
        raise B2RobustProxyContractError(f"{field} must be a finite vector")
    return result


def _positive(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise B2RobustProxyContractError(
            f"{field} must be finite and positive"
        ) from error
    if not math.isfinite(result) or result <= 0.0:
        raise B2RobustProxyContractError(f"{field} must be finite and positive")
    return result


def _action_indices(value: object, *, field: str) -> tuple[int, ...]:
    """Validate and canonicalise a bounded native action panel."""

    if isinstance(value, (str, bytes)):
        raise B2RobustProxyContractError(f"{field} must be an action sequence")
    try:
        result = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise B2RobustProxyContractError(f"{field} must be an action sequence") from error
    try:
        unique_count = len(set(result))
    except TypeError as error:
        raise B2RobustProxyContractError(
            f"{field} must contain native integer actions"
        ) from error
    if (
        not 1 <= len(result) <= V07_C2_B2_ROBUST_PROXY_MAX_ACTIONS
        or unique_count != len(result)
        or any(
            type(action) is not int or not 0 <= action < NUM_ACTIONS
            for action in result
        )
    ):
        raise B2RobustProxyContractError(
            f"{field} must contain 1..{V07_C2_B2_ROBUST_PROXY_MAX_ACTIONS} "
            "unique native actions"
        )
    # The panel is a set of predeclared actions.  Sorting makes both numeric
    # results and raw receipts invariant to the caller's sequence order.
    return tuple(sorted(int(action) for action in result))


def _canonical_vector(
    values: np.ndarray,
    *,
    input_actions: tuple[int, ...],
    canonical_actions: tuple[int, ...],
    field: str,
) -> np.ndarray:
    if values.shape != (len(input_actions),):
        raise B2RobustProxyContractError(
            f"{field} must have one value for each panel action"
        )
    positions = {action: index for index, action in enumerate(input_actions)}
    return np.asarray(
        [values[positions[action]] for action in canonical_actions],
        dtype=np.float64,
    )


def _top_two_positive(
    *,
    actions: tuple[int, ...],
    action_surplus: np.ndarray,
) -> tuple[float, tuple[float, float], tuple[int, int]]:
    """Return the fixed top-two positive-opportunity mean and its receipt.

    Zero is represented by action ``-1`` in the action receipt.  A zero-valued
    measured action is not treated as a positive opportunity; it is equivalent
    to the outside option and therefore does not change the deterministic
    padding rule.
    """

    opportunities = sorted(
        (
            (float(value), int(action))
            for action, value in zip(actions, action_surplus.tolist())
            if float(value) > 0.0
        ),
        key=lambda item: (-item[0], item[1]),
    )
    selected = opportunities[:V07_C2_B2_ROBUST_PROXY_TOP_K]
    top_values = [value for value, _action in selected]
    top_actions = [action for _value, action in selected]
    while len(top_values) < V07_C2_B2_ROBUST_PROXY_TOP_K:
        top_values.append(0.0)
        top_actions.append(-1)
    top_pair = (float(top_values[0]), float(top_values[1]))
    action_pair = (int(top_actions[0]), int(top_actions[1]))
    value = float(math.fsum(top_pair) / V07_C2_B2_ROBUST_PROXY_TOP_K)
    if not math.isfinite(value):
        raise B2RobustProxyContractError("robust proxy aggregation is non-finite")
    return value, top_pair, action_pair


@dataclass(frozen=True)
class B2RobustProxyOptionSetSurplus:
    """Signed robust B2 proxy target plus independently auditable receipts."""

    z2_robust_proxy_surplus_bits: float
    candidate_robust_option_value_bits: float
    reference_robust_option_value_bits: float
    candidate_top_two_surplus_bits: tuple[float, float]
    reference_top_two_surplus_bits: tuple[float, float]
    candidate_top_two_actions: tuple[int, int]
    reference_top_two_actions: tuple[int, int]
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
    claim_ceiling: str = "DEVELOPMENT_ONLY__NOT_FINAL_B2_EVIDENCE"
    schema: str = V07_C2_B2_ROBUST_PROXY_TARGET_SCHEMA

    # Compatibility aliases keep the receipt easy to consume beside the
    # non-robust fast proxy without creating a second calculation path.
    @property
    def z2_proxy_surplus_bits(self) -> float:
        return self.z2_robust_proxy_surplus_bits

    @property
    def candidate_option_value_bits(self) -> float:
        return self.candidate_robust_option_value_bits

    @property
    def reference_option_value_bits(self) -> float:
        return self.reference_robust_option_value_bits

    @property
    def candidate_best_action(self) -> int:
        return self.candidate_top_two_actions[0]

    @property
    def reference_best_action(self) -> int:
        return self.reference_top_two_actions[0]

    @property
    def candidate_top_two_values_bits(self) -> tuple[float, float]:
        return self.candidate_top_two_surplus_bits

    @property
    def reference_top_two_values_bits(self) -> tuple[float, float]:
        return self.reference_top_two_surplus_bits


def successor_robust_proxy_option_set_target(
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
) -> B2RobustProxyOptionSetSurplus:
    """Compute the fixed top-two robust B2 target from existing measurements.

    No target-dependent panel selection occurs here.  The only ranking is the
    predeclared top-two aggregation over the supplied panel's measured action
    surpluses.  Negative action surpluses are dominated by the zero outside
    option and are retained in the raw receipt rather than clipped in place.
    """

    multiplier = _positive(lambda_bits_per_j, field="lambda_bits_per_j")
    interval = _positive(interval_s, field="interval_s")

    # Materialise once so one-shot iterables cannot make the panel and its raw
    # vectors disagree during canonicalisation.
    if isinstance(candidate_actions, (str, bytes)):
        raise B2RobustProxyContractError(
            "candidate_actions must be an action sequence"
        )
    if isinstance(reference_actions, (str, bytes)):
        raise B2RobustProxyContractError(
            "reference_actions must be an action sequence"
        )
    try:
        candidate_action_sequence = tuple(candidate_actions)  # type: ignore[arg-type]
        reference_action_sequence = tuple(reference_actions)  # type: ignore[arg-type]
    except TypeError as error:
        raise B2RobustProxyContractError(
            "candidate_actions and reference_actions must be action sequences"
        ) from error
    candidate_indices = _action_indices(
        candidate_action_sequence,
        field="candidate_actions",
    )
    reference_indices = _action_indices(
        reference_action_sequence,
        field="reference_actions",
    )

    candidate_rate_input = _finite_vector(
        candidate_action_rates_bps,
        field="candidate_action_rates_bps",
    )
    candidate_full_input = _finite_vector(
        candidate_action_full_power_w,
        field="candidate_action_full_power_w",
    )
    candidate_without_input = _finite_vector(
        candidate_action_without_focal_power_w,
        field="candidate_action_without_focal_power_w",
    )
    reference_rate_input = _finite_vector(
        reference_action_rates_bps,
        field="reference_action_rates_bps",
    )
    reference_full_input = _finite_vector(
        reference_action_full_power_w,
        field="reference_action_full_power_w",
    )
    reference_without_input = _finite_vector(
        reference_action_without_focal_power_w,
        field="reference_action_without_focal_power_w",
    )

    for name, values in (
        ("candidate_action_rates_bps", candidate_rate_input),
        ("candidate_action_full_power_w", candidate_full_input),
        ("candidate_action_without_focal_power_w", candidate_without_input),
        ("reference_action_rates_bps", reference_rate_input),
        ("reference_action_full_power_w", reference_full_input),
        ("reference_action_without_focal_power_w", reference_without_input),
    ):
        if np.any(values < 0.0):
            raise B2RobustProxyContractError(f"{name} must be non-negative")

    candidate_rate = _canonical_vector(
        candidate_rate_input,
        input_actions=candidate_action_sequence,
        canonical_actions=candidate_indices,
        field="candidate_action_rates_bps",
    )
    candidate_full = _canonical_vector(
        candidate_full_input,
        input_actions=candidate_action_sequence,
        canonical_actions=candidate_indices,
        field="candidate_action_full_power_w",
    )
    candidate_without = _canonical_vector(
        candidate_without_input,
        input_actions=candidate_action_sequence,
        canonical_actions=candidate_indices,
        field="candidate_action_without_focal_power_w",
    )
    reference_rate = _canonical_vector(
        reference_rate_input,
        input_actions=reference_action_sequence,
        canonical_actions=reference_indices,
        field="reference_action_rates_bps",
    )
    reference_full = _canonical_vector(
        reference_full_input,
        input_actions=reference_action_sequence,
        canonical_actions=reference_indices,
        field="reference_action_full_power_w",
    )
    reference_without = _canonical_vector(
        reference_without_input,
        input_actions=reference_action_sequence,
        canonical_actions=reference_indices,
        field="reference_action_without_focal_power_w",
    )

    candidate_marginal = candidate_full - candidate_without
    reference_marginal = reference_full - reference_without
    with np.errstate(over="ignore", invalid="ignore"):
        candidate_surplus = interval * (
            candidate_rate - multiplier * candidate_marginal
        )
        reference_surplus = interval * (
            reference_rate - multiplier * reference_marginal
        )
    if not np.all(np.isfinite(candidate_surplus)) or not np.all(
        np.isfinite(reference_surplus)
    ):
        raise B2RobustProxyContractError(
            "robust proxy action-surplus arithmetic is non-finite"
        )

    candidate_value, candidate_top_values, candidate_top_actions = _top_two_positive(
        actions=candidate_indices,
        action_surplus=candidate_surplus,
    )
    reference_value, reference_top_values, reference_top_actions = _top_two_positive(
        actions=reference_indices,
        action_surplus=reference_surplus,
    )
    target = float(candidate_value - reference_value)
    if not math.isfinite(target):
        raise B2RobustProxyContractError("robust proxy target arithmetic is non-finite")

    return B2RobustProxyOptionSetSurplus(
        z2_robust_proxy_surplus_bits=target,
        candidate_robust_option_value_bits=float(candidate_value),
        reference_robust_option_value_bits=float(reference_value),
        candidate_top_two_surplus_bits=candidate_top_values,
        reference_top_two_surplus_bits=reference_top_values,
        candidate_top_two_actions=candidate_top_actions,
        reference_top_two_actions=reference_top_actions,
        candidate_actions=candidate_indices,
        reference_actions=reference_indices,
        candidate_action_surplus_bits=tuple(
            float(value) for value in candidate_surplus.tolist()
        ),
        reference_action_surplus_bits=tuple(
            float(value) for value in reference_surplus.tolist()
        ),
        candidate_action_rates_bps=tuple(
            float(value) for value in candidate_rate.tolist()
        ),
        reference_action_rates_bps=tuple(
            float(value) for value in reference_rate.tolist()
        ),
        candidate_action_full_power_w=tuple(
            float(value) for value in candidate_full.tolist()
        ),
        candidate_action_without_focal_power_w=tuple(
            float(value) for value in candidate_without.tolist()
        ),
        reference_action_full_power_w=tuple(
            float(value) for value in reference_full.tolist()
        ),
        reference_action_without_focal_power_w=tuple(
            float(value) for value in reference_without.tolist()
        ),
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )


# Intuitive aliases make the formula discoverable beside the existing fast
# proxy while keeping one canonical implementation and one schema.
b2_robust_proxy_target = successor_robust_proxy_option_set_target
successor_b2_robust_proxy_target = successor_robust_proxy_option_set_target
B2RobustProxySurplus = B2RobustProxyOptionSetSurplus


__all__ = [
    "B2RobustProxyContractError",
    "B2RobustProxyOptionSetSurplus",
    "B2RobustProxySurplus",
    "V07_C2_B2_ROBUST_PROXY_MAX_ACTIONS",
    "V07_C2_B2_ROBUST_PROXY_PANEL_SCHEMA",
    "V07_C2_B2_ROBUST_PROXY_TARGET_SCHEMA",
    "V07_C2_B2_ROBUST_PROXY_TOP_K",
    "b2_robust_proxy_target",
    "successor_b2_robust_proxy_target",
    "successor_robust_proxy_option_set_target",
]
