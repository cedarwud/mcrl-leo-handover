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
# Per-link (per-UE) energy efficiency — the r1 objective's closure
# ---------------------------------------------------------------------------

EPSILON_NUM: float = 1e-12
"""Retained for provenance only.  **Never used as a denominator floor.**

The source project floors the ``eta`` denominator at this value.  This port
does not: see :func:`per_ue_energy_efficiency`.
"""


@dataclass(frozen=True)
class PerLinkEnergyEfficiency:
    """Beam-local power share and full-cost per-link EE."""

    alpha: np.ndarray
    """``κ`` — this link's share of its beam's radiated power. Shape ``(..., K)``."""

    eta: np.ndarray
    """``R_u / (κ·P_tot + P_0)`` for admitted links, 0 otherwise."""

    zero_over_zero: np.ndarray
    """Admitted links that carried no rate on no power — a legitimate 0/0."""

    @property
    def any_zero_over_zero(self) -> bool:
        return bool(np.any(self.zero_over_zero))


def per_ue_energy_efficiency(
    *,
    rates_nmk: np.ndarray,
    admitted_link_nmk: np.ndarray,
    p_req_nmk: np.ndarray,
    p_max_nm: np.ndarray,
    p_tot_nm: np.ndarray,
    p0_w: float = 0.0,
) -> PerLinkEnergyEfficiency:
    """Beam-local ``κ`` and full-cost ``η`` per link.

    **The power share is piecewise, not epsilon-regularised.**  The source
    records why (S11a M-10): the earlier ``x·q / (Σ + ε)`` shape was unsound
    because eq. (3.27)'s double sum evaluates ``κ`` on *every* beam, so an
    empty serving set produced 0/0 and the epsilon papered over it.  The
    piecewise form isolates the empty beam **by definition**::

        κ_u = q_u / Σ_{u' ∈ U_b} q_{u'}   if the link is admitted
        κ_u = 0                            otherwise,  q = min(p_req, P_max)

    so no epsilon enters the share and the admitted shares on a beam sum to
    **exactly** 1 rather than ``1 − O(ε)``.

    ★ **Declared deviation from the source: the η denominator is not floored.**

    The source computes ``η = R / max(κ·P_tot + P_0, 1e-12)``.  That floor is
    the very construction §3.7 P-7 forbids: an admitted link with zero
    denominator and positive rate comes back as ``R × 1e12`` — an astronomical
    EE produced silently, on exactly the link that consumed nothing.

    Here the zero-denominator case is fail-closed, matching
    :func:`additive_system_ee`:

    * positive rate on zero power → **raise**;
    * zero rate on zero power → ``η = 0`` with the ``zero_over_zero`` flag.

    Every *reachable* case is unchanged, because a real admitted link has
    ``κ·P_tot > 0`` and the floor never binds.  What changes is that the
    unreachable case now announces itself instead of inventing a number.
    """
    if p0_w < 0.0:
        raise ValueError("p0_w must be non-negative")

    rates = np.asarray(rates_nmk, dtype=np.float64)
    admitted = np.asarray(admitted_link_nmk, dtype=bool)
    p_req = np.asarray(p_req_nmk, dtype=np.float64)
    if rates.shape != admitted.shape or rates.shape != p_req.shape:
        raise MCRLContractError(
            "rates_nmk, admitted_link_nmk and p_req_nmk must share a shape"
        )
    if rates.ndim < 1:
        raise MCRLContractError("rates_nmk must include a UE axis")
    if not np.all(np.isfinite(rates)) or not np.all(np.isfinite(p_req)):
        raise MCRLContractError("rates and required powers must be finite")
    if np.any(rates < 0.0) or np.any(p_req < 0.0):
        raise MCRLContractError("rates and required powers must be non-negative")

    p_max = _broadcast_over_ue_axis(p_max_nm, rates.shape, "p_max_nm")
    p_tot = _broadcast_over_ue_axis(p_tot_nm, rates.shape, "p_tot_nm")
    if np.any(p_max < 0.0) or np.any(p_tot < 0.0):
        raise MCRLContractError("p_max_nm and p_tot_nm must be non-negative")

    capped_request = np.minimum(p_req, p_max)
    weighted = np.where(admitted, capped_request, 0.0)
    beam_total = np.sum(weighted, axis=-1, keepdims=True, dtype=np.float64)
    # Divide only where the beam has admitted demand; the placeholder 1.0 is
    # never observed because those entries take the κ = 0 branch.
    safe_total = np.where(beam_total > 0.0, beam_total, 1.0)
    alpha = np.where(admitted, weighted / safe_total, 0.0)

    denominator = alpha * p_tot + p0_w
    starved = admitted & (denominator <= 0.0)
    if np.any(starved & (rates > 0.0)):
        raise MCRLContractError(
            "positive link throughput with zero attributed power is invalid; "
            "P-7 forbids flooring the denominator to make it finite"
        )
    zero_over_zero = starved & (rates <= 0.0)
    eta = np.where(
        admitted & ~starved,
        rates / np.where(denominator > 0.0, denominator, 1.0),
        0.0,
    )
    return PerLinkEnergyEfficiency(
        alpha=alpha, eta=eta, zero_over_zero=zero_over_zero
    )


def _broadcast_over_ue_axis(
    value: np.ndarray, shape: tuple[int, ...], name: str
) -> np.ndarray:
    """Broadcast a per-beam quantity across the trailing UE axis."""
    array = np.asarray(value, dtype=np.float64)
    if array.shape == shape:
        return array
    if array.shape == shape[:-1]:
        return np.broadcast_to(array[..., None], shape)
    try:
        return np.broadcast_to(array, shape)
    except ValueError as error:
        raise MCRLContractError(
            f"{name} with shape {array.shape} does not broadcast to {shape}"
        ) from error
