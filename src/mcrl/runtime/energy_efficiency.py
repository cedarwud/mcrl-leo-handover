"""Additive system energy efficiency with fail-closed zero-power semantics.

Guardrails P-6 and P-7 (SDD §3.7), gates G-8 and G-12.

**P-7 — never pad the denominator.**  ``angle_aware_ee.py:537-546`` is
explicit: zero power with positive throughput is *impossible*, so it raises;
zero over zero is a legitimate all-dark step, so it returns 0.0 and flags
``zero_over_zero``.  What it never does is add an epsilon.  A floor of 1e-9 W
under a step that radiated nothing turns 0/0 into 0/1e-9 and reports an
energy efficiency of whatever the numerator noise happens to be —
**silently inflating EE exactly on the steps where the system did least**.

**P-6 — one load semantics.**  ``beam_load_b`` must equal the counts implied
by ``serving_beam_u``, and a beam is active if and only if its load is
positive.  B13's counting-form ``r3 = −U_{b_u}`` is *defined* on that count,
and ``γ_req(U)`` divides by it; two load definitions drifting apart would
make ``r3`` and the rate refer to different systems while both look fine.

**G-8 — an EE number without a service rate is not comparable.**  The old
3.9× headline turned out to be a coverage difference (33.7% served), not an
efficiency one.  :class:`SystemEnergyEfficiency` therefore carries ``served``
and ``eff_beams`` alongside the ratio, and :func:`format_ee_comparison`
refuses to render a comparison that omits them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError


@dataclass(frozen=True)
class SystemEnergyEfficiency:
    """One step's system EE, with the two figures G-8 requires beside it."""

    system_throughput_bps: float
    system_consumed_power_w: float
    system_ee_bits_per_j: float
    per_user_contributions_bits_per_j: tuple[float, ...]
    served: int
    """Users actually receiving service this step."""
    eff_beams: int
    """Beams radiating this step (active ⟺ positive load, P-6)."""
    zero_over_zero: bool = False
    """True only for a genuine all-dark step: 0 bits over 0 watts."""

    @property
    def service_rate(self) -> float:
        raise NotImplementedError  # replaced below to keep users explicit

    def as_dict(self) -> dict[str, object]:
        return {
            "system_throughput_bps": self.system_throughput_bps,
            "system_consumed_power_w": self.system_consumed_power_w,
            "system_ee_bits_per_j": self.system_ee_bits_per_j,
            "served": self.served,
            "eff_beams": self.eff_beams,
            "zero_over_zero": self.zero_over_zero,
        }


# ``service_rate`` needs the population size, which the dataclass does not
# carry; drop the placeholder rather than inviting a wrong denominator.
del SystemEnergyEfficiency.service_rate


def assert_single_load_semantics(
    serving_beam_u: np.ndarray,
    beam_load_b: np.ndarray,
    beam_active_b: np.ndarray,
) -> np.ndarray:
    """P-6 / G-12 — the load identity, checked rather than assumed.

    Returns the realised loads.  ``serving_beam_u[u] == -1`` means unserved.
    """
    serving = np.asarray(serving_beam_u, dtype=np.int64)
    loads = np.asarray(beam_load_b, dtype=np.float64)
    active = np.asarray(beam_active_b, dtype=bool)
    if serving.ndim != 1 or loads.ndim != 1 or active.shape != loads.shape:
        raise MCRLContractError(
            "serving_beam_u must be (U,), beam_load_b and beam_active_b (B,)"
        )
    beam_count = loads.size
    if np.any((serving < -1) | (serving >= beam_count)):
        raise MCRLContractError(
            "serving_beam_u entries must be -1 or a valid beam index"
        )
    if np.any(loads < 0.0):
        raise MCRLContractError("beam loads must be non-negative")

    served = serving >= 0
    realised = np.bincount(serving[served], minlength=beam_count).astype(
        np.float64
    )
    if not np.array_equal(loads, realised):
        raise MCRLContractError(
            "beam_load_b must equal the counts implied by serving_beam_u; "
            "r3 = -U_{b_u} and gamma_req(U) cannot use a separate load semantics"
        )
    if np.any(active & (loads <= 0.0)) or np.any((~active) & (loads != 0.0)):
        raise MCRLContractError(
            "activation and positive load must coincide: active beams need "
            "positive load, inactive beams exactly zero"
        )
    if np.any(served) and np.any(~active[serving[served]]):
        raise MCRLContractError("a served user cannot point at an inactive beam")
    return realised


def additive_system_ee(
    user_throughputs_bps: np.ndarray,
    system_consumed_power_w: float,
    *,
    serving_beam_u: np.ndarray,
    beam_load_b: np.ndarray,
    beam_active_b: np.ndarray,
) -> SystemEnergyEfficiency:
    """System EE as ``Σ_u R_u / P_system``, decomposed additively per user.

    The decomposition is exact by construction (a shared denominator), and
    the sum identity is re-checked so a future change cannot quietly break
    the property ADR-003 relies on.
    """
    rates = np.asarray(user_throughputs_bps, dtype=np.float64)
    if rates.ndim != 1:
        raise MCRLContractError("user_throughputs_bps must be one-dimensional")
    if not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
        raise MCRLContractError(
            "user throughputs must be finite and non-negative"
        )
    power_w = float(system_consumed_power_w)
    if not math.isfinite(power_w) or power_w < 0.0:
        raise MCRLContractError(
            "system consumed power must be finite and non-negative"
        )

    assert_single_load_semantics(serving_beam_u, beam_load_b, beam_active_b)
    served = int(np.count_nonzero(np.asarray(serving_beam_u) >= 0))
    eff_beams = int(np.count_nonzero(np.asarray(beam_active_b)))
    throughput = float(rates.sum())

    if power_w == 0.0:
        # P-7: zero power cannot carry bits.  This is a contract violation
        # upstream, not something to smooth over.
        if throughput > 0.0:
            raise MCRLContractError(
                "positive system throughput with zero consumed power is invalid"
            )
        if eff_beams:
            raise MCRLContractError(
                "zero consumed power with active beams is invalid"
            )
        return SystemEnergyEfficiency(
            system_throughput_bps=0.0,
            system_consumed_power_w=0.0,
            system_ee_bits_per_j=0.0,
            per_user_contributions_bits_per_j=tuple(0.0 for _ in rates),
            served=served,
            eff_beams=0,
            zero_over_zero=True,
        )

    contributions = tuple(float(rate / power_w) for rate in rates)
    system_ee = throughput / power_w
    tolerance = max(8.0, 4.0 * rates.size) * math.ulp(1.0)
    if not math.isclose(
        sum(contributions), system_ee, rel_tol=tolerance, abs_tol=0.0
    ):
        raise MCRLContractError(
            "additive system-EE decomposition lost its sum identity"
        )
    return SystemEnergyEfficiency(
        system_throughput_bps=throughput,
        system_consumed_power_w=power_w,
        system_ee_bits_per_j=system_ee,
        per_user_contributions_bits_per_j=contributions,
        served=served,
        eff_beams=eff_beams,
        zero_over_zero=False,
    )


def format_ee_comparison(
    arms: dict[str, SystemEnergyEfficiency], *, num_users: int
) -> str:
    """G-8 — render an EE comparison that cannot omit the service rate.

    Any arm-to-arm EE comparison must show ``served`` and ``eff_beams``
    alongside the ratio.  The old 3.9× headline was a coverage gap (one arm
    served 33.7% of users), and an EE column alone cannot tell the two
    apart.
    """
    if not arms:
        raise MCRLContractError("nothing to compare")
    if num_users <= 0:
        raise ValueError("num_users must be positive")
    lines = [
        f"{'arm':<24}{'EE [bits/J]':>16}{'served':>10}{'served %':>10}"
        f"{'eff_beams':>11}"
    ]
    for name, result in arms.items():
        lines.append(
            f"{name:<24}{result.system_ee_bits_per_j:>16.4e}"
            f"{result.served:>10d}{100.0 * result.served / num_users:>9.1f}%"
            f"{result.eff_beams:>11d}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-link EE display quantity (3.17) and r1 (3.25)
# ---------------------------------------------------------------------------
#
# RULING C-7 (2026-08-22): the per-link ``kappa`` power-share closure is
# WITHDRAWN.  Eq. (3.17) divides by the **common system power** ``P^N``, and
# the paper says plainly that the result "不宣稱為 private-power 的 true
# per-user EE" — it is one link's additive contribution to the system figure,
# which is exactly what :func:`additive_system_ee` computes.  Attributing a
# private share of the power to each link was a different quantity.


def link_energy_efficiency(
    link_rate_bps: np.ndarray, system_power_w: float
) -> np.ndarray:
    """Paper eq. (3.17): ``η_{u,s,v} = R_{u,s,v} / P^N``.

    Same fail-closed policy as :func:`additive_system_ee` — positive rate on
    zero system power raises, zero over zero is 0.  P-7 forbids the
    epsilon floor that would otherwise turn the second case into an
    astronomical efficiency.
    """
    rates = np.asarray(link_rate_bps, dtype=np.float64)
    if np.any(rates < 0.0) or not np.all(np.isfinite(rates)):
        raise MCRLContractError("rates must be finite and non-negative")
    power = float(system_power_w)
    if not math.isfinite(power) or power < 0.0:
        raise MCRLContractError("system power must be finite and non-negative")
    if power == 0.0:
        if np.any(rates > 0.0):
            raise MCRLContractError(
                "positive throughput with zero system power is invalid"
            )
        return np.zeros_like(rates)
    return rates / power


def r1_energy_efficiency(
    served_rate_bps: np.ndarray, system_power_w: float
) -> np.ndarray:
    """Paper eq. (3.25): ``r1_u = Σ_{s,v} x·η = (Σ x·R) / P^N``, bit/J.

    Unselected links are excluded by ``x = 0``, so the caller passes each
    user's already-selected rate (zero when unserved).  The result is
    additive across users by construction — summing it recovers the system
    EE exactly — which is the property that makes ``r1`` a decomposition of
    a global objective rather than a per-user proxy for one.
    """
    return link_energy_efficiency(served_rate_bps, system_power_w)
