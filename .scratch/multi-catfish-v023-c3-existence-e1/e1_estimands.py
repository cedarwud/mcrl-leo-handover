#!/usr/bin/env python3
"""Exact finite-panel estimands for the C3 existence screen E1.

The solver uses Dinkelbach iterations.  Each inner, service-constrained
multiple-choice problem is solved exactly by dynamic programming over the
integer served-count dimension.  Inputs are finite IEEE-754 values; proof
arithmetic converts each one with ``Fraction.from_float``.  At termination,
the certificate records that the exact maximum of ``B - q E`` over every
service-feasible selection is zero.  Since all energies are positive, this is
both a primal witness and a proof that no feasible selection has ratio above
``q``.

The float summaries are deliberately separate from the proof: they use
``math.fsum`` in canonical anchor order and are emitted in hexadecimal form.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from typing import Any, Mapping, Sequence


SERVICE_MARGIN_NUMERATOR = 1
SERVICE_MARGIN_DENOMINATOR = 1000
SERVICE_MARGIN = SERVICE_MARGIN_NUMERATOR / SERVICE_MARGIN_DENOMINATOR
MAX_DINKELBACH_ITERATIONS = 10_000
BASE_PROFILE_ID = "BASE"
U1_ESTIMAND = "U1"
J1_ESTIMAND = "J1"
CERTIFICATE_METHOD = "EXACT_RATIONAL_DINKELBACH_INTEGER_SERVICE_DP"


class E1EstimandError(RuntimeError):
    """An E1 panel or exact optimization certificate is invalid."""


@dataclass(frozen=True)
class ProfileOption:
    """One complete physical profile available at an anchor."""

    profile_id: str
    total_bits: float
    total_energy_j: float
    served: int
    opportunities: int

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise E1EstimandError("profile_id must be a nonempty string")
        if isinstance(self.total_bits, bool) or not math.isfinite(self.total_bits):
            raise E1EstimandError("total_bits must be finite")
        if self.total_bits < 0.0:
            raise E1EstimandError("total_bits must be nonnegative")
        if (
            isinstance(self.total_energy_j, bool)
            or not math.isfinite(self.total_energy_j)
            or self.total_energy_j <= 0.0
        ):
            raise E1EstimandError("total_energy_j must be finite and positive")
        if type(self.served) is not int or type(self.opportunities) is not int:
            raise E1EstimandError("service counts must be exact integers")
        if not 0 <= self.served <= self.opportunities or self.opportunities <= 0:
            raise E1EstimandError("service counts are outside their domain")

    @property
    def bits_exact(self) -> Fraction:
        return Fraction.from_float(self.total_bits)

    @property
    def energy_exact(self) -> Fraction:
        return Fraction.from_float(self.total_energy_j)


@dataclass(frozen=True)
class AnchorOptions:
    """Canonical BASE plus candidate profiles for one matched anchor."""

    anchor_id: str
    base: ProfileOption
    candidates: tuple[ProfileOption, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.anchor_id, str) or not self.anchor_id:
            raise E1EstimandError("anchor_id must be a nonempty string")
        if self.base.profile_id != BASE_PROFILE_ID:
            raise E1EstimandError("the anchor base profile_id must be BASE")
        ids = [self.base.profile_id, *(row.profile_id for row in self.candidates)]
        if len(ids) != len(set(ids)):
            raise E1EstimandError("profile IDs must be unique within an anchor")
        if any(row.opportunities != self.base.opportunities for row in self.candidates):
            raise E1EstimandError("all profiles at an anchor need equal opportunities")

    @property
    def profiles(self) -> tuple[ProfileOption, ...]:
        return (self.base, *self.candidates)


def _int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise E1EstimandError(f"{field} must be an exact integer")
    return value


def _float(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise E1EstimandError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise E1EstimandError(f"{field} must be numeric") from error
    if not math.isfinite(result):
        raise E1EstimandError(f"{field} must be finite")
    return result


def _profile_from_mapping(value: Mapping[str, object], *, default_id: str) -> ProfileOption:
    profile_id = value.get("profile_id", default_id)
    if not isinstance(profile_id, str):
        raise E1EstimandError("profile_id must be a string")
    served_value = value.get("served", value.get("served_user_steps"))
    opportunity_value = value.get("opportunities", value.get("service_opportunities"))
    return ProfileOption(
        profile_id=profile_id,
        total_bits=_float(value.get("total_bits"), field="total_bits"),
        total_energy_j=_float(value.get("total_energy_j"), field="total_energy_j"),
        served=_int(served_value, field="served"),
        opportunities=_int(opportunity_value, field="opportunities"),
    )


def _profile(value: object, *, default_id: str) -> ProfileOption:
    if isinstance(value, ProfileOption):
        return value
    if isinstance(value, Mapping):
        return _profile_from_mapping(value, default_id=default_id)
    try:
        rates = tuple(float(item) for item in value.link_rate_bps)  # type: ignore[attr-defined]
        interval = float(value.interval_s)  # type: ignore[attr-defined]
        energy = float(value.network_energy_j)  # type: ignore[attr-defined]
        served = sum(bool(item) for item in value.served)  # type: ignore[attr-defined]
        opportunities = int(value.users)  # type: ignore[attr-defined]
    except (AttributeError, TypeError, ValueError, OverflowError) as error:
        raise E1EstimandError("profile is not an E1 metric mapping or physical profile") from error
    return ProfileOption(
        profile_id=default_id,
        total_bits=interval * math.fsum(rates),
        total_energy_j=energy,
        served=served,
        opportunities=opportunities,
    )


def _anchor(value: object, *, candidate_field: str) -> AnchorOptions:
    if isinstance(value, AnchorOptions):
        return value
    if not isinstance(value, Mapping):
        raise E1EstimandError("each anchor must be AnchorOptions or a mapping")
    anchor_id = value.get("anchor_id")
    if not isinstance(anchor_id, str):
        raise E1EstimandError("anchor_id must be a string")
    base = _profile(value.get("base"), default_id=BASE_PROFILE_ID)
    raw_candidates = value.get(candidate_field, value.get("candidates"))
    if not isinstance(raw_candidates, Sequence) or isinstance(raw_candidates, (str, bytes)):
        raise E1EstimandError(f"{candidate_field} must be a sequence")
    candidates = tuple(
        _profile(row, default_id=f"{candidate_field}:{index:06d}")
        for index, row in enumerate(raw_candidates)
    )
    return AnchorOptions(anchor_id=anchor_id, base=base, candidates=candidates)


def _canonical_anchors(values: Sequence[object], *, candidate_field: str) -> tuple[AnchorOptions, ...]:
    anchors = tuple(_anchor(value, candidate_field=candidate_field) for value in values)
    if not anchors:
        raise E1EstimandError("the panel must contain at least one anchor")
    ordered = tuple(sorted(anchors, key=lambda row: row.anchor_id))
    if len({row.anchor_id for row in ordered}) != len(ordered):
        raise E1EstimandError("anchor IDs must be unique")
    normalized = []
    for anchor in ordered:
        candidates = tuple(sorted(anchor.candidates, key=lambda row: row.profile_id))
        normalized.append(AnchorOptions(anchor.anchor_id, anchor.base, candidates))
    return tuple(normalized)


def _ceil_fraction(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _required_served(anchors: Sequence[AnchorOptions]) -> tuple[int, int, int]:
    base_served = sum(anchor.base.served for anchor in anchors)
    opportunities = sum(anchor.base.opportunities for anchor in anchors)
    threshold = Fraction(base_served, 1) - Fraction(
        SERVICE_MARGIN_NUMERATOR * opportunities, SERVICE_MARGIN_DENOMINATOR
    )
    return _ceil_fraction(threshold), base_served, opportunities


@dataclass(frozen=True)
class _DPState:
    score: Fraction
    choices: tuple[int, ...]


def _better(left: _DPState, right: _DPState | None) -> bool:
    return right is None or left.score > right.score or (
        left.score == right.score and left.choices < right.choices
    )


def _inner_exact(
    anchors: Sequence[AnchorOptions], *, q: Fraction, required_served: int,
    trace: list[dict[str, object]] | None = None,
) -> _DPState:
    """Maximize exact ``sum(B-qE)`` subject to the pooled service threshold."""

    dp: dict[int, _DPState] = {0: _DPState(Fraction(0), ())}
    for anchor in anchors:
        # For a fixed served count only the best linear-score profile matters.
        by_served: dict[int, tuple[int, Fraction]] = {}
        for index, profile in enumerate(anchor.profiles):
            score = profile.bits_exact - q * profile.energy_exact
            current = by_served.get(profile.served)
            if current is None or score > current[1] or (
                score == current[1] and index < current[0]
            ):
                by_served[profile.served] = (index, score)
        next_dp: dict[int, _DPState] = {}
        for prior_served in sorted(dp):
            prior = dp[prior_served]
            for served in sorted(by_served):
                index, score = by_served[served]
                capped = min(required_served, prior_served + served)
                candidate = _DPState(prior.score + score, prior.choices + (index,))
                if _better(candidate, next_dp.get(capped)):
                    next_dp[capped] = candidate
        dp = next_dp
        if trace is not None:
            rows = [
                [
                    served,
                    str(state.score.numerator),
                    str(state.score.denominator),
                    list(state.choices),
                ]
                for served, state in sorted(dp.items())
            ]
            encoded = json.dumps(
                rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            trace.append(
                {
                    "anchor_index": len(trace),
                    "state_count": len(rows),
                    "states_sha256": hashlib.sha256(encoded).hexdigest(),
                }
            )
    result = dp.get(required_served)
    if result is None:
        raise E1EstimandError("the pooled service constraint is infeasible")
    return result


def _totals_exact(
    anchors: Sequence[AnchorOptions], choices: Sequence[int]
) -> tuple[Fraction, Fraction, int]:
    bits = Fraction(0)
    energy = Fraction(0)
    served = 0
    for anchor, choice in zip(anchors, choices, strict=True):
        profile = anchor.profiles[choice]
        bits += profile.bits_exact
        energy += profile.energy_exact
        served += profile.served
    return bits, energy, served


def _fraction_payload(value: Fraction) -> dict[str, object]:
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
        "float_hex": float(value).hex(),
    }


def _coefficient_payload(anchors: Sequence[AnchorOptions]) -> list[dict[str, object]]:
    return [
        {
            "anchor_id": anchor.anchor_id,
            "profiles": [
                {
                    "profile_id": profile.profile_id,
                    "bits": _fraction_payload(profile.bits_exact),
                    "energy_j": _fraction_payload(profile.energy_exact),
                    "served": profile.served,
                    "opportunities": profile.opportunities,
                }
                for profile in anchor.profiles
            ],
        }
        for anchor in anchors
    ]


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _choice_set_census(
    anchors: Sequence[AnchorOptions], *, q: Fraction
) -> dict[str, object]:
    rows = []
    for anchor in anchors:
        by_served: dict[int, tuple[int, Fraction]] = {}
        for index, profile in enumerate(anchor.profiles):
            score = profile.bits_exact - q * profile.energy_exact
            current = by_served.get(profile.served)
            if current is None or score > current[1] or (
                score == current[1] and index < current[0]
            ):
                by_served[profile.served] = (index, score)
        rows.append(
            {
                "anchor_id": anchor.anchor_id,
                "profiles_before_reduction": len(anchor.profiles),
                "profiles_after_final_q_reduction": len(by_served),
                "profile_ids": [profile.profile_id for profile in anchor.profiles],
                "final_q_survivors_by_served": {
                    str(served): anchor.profiles[index].profile_id
                    for served, (index, _score) in sorted(by_served.items())
                },
            }
        )
    return {
        "anchor_count": len(anchors),
        "profile_count": sum(len(anchor.profiles) for anchor in anchors),
        "profiles_after_final_q_reduction": sum(
            int(row["profiles_after_final_q_reduction"]) for row in rows
        ),
        "anchors": rows,
    }


def verify_certificate(
    anchors: Sequence[object], result: Mapping[str, object], *, candidate_field: str
) -> bool:
    """Re-run the exact terminal inner problem and verify the proof payload."""

    panel = _canonical_anchors(anchors, candidate_field=candidate_field)
    certificate = result.get("certificate")
    if not isinstance(certificate, Mapping):
        raise E1EstimandError("result lacks an optimization certificate")
    ratio = certificate.get("optimal_ratio_exact")
    if not isinstance(ratio, Mapping):
        raise E1EstimandError("certificate lacks optimal_ratio_exact")
    try:
        q = Fraction(int(ratio["numerator"]), int(ratio["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise E1EstimandError("certificate ratio is malformed") from error
    required, _base_served, _opportunities = _required_served(panel)
    trace: list[dict[str, object]] = []
    inner = _inner_exact(panel, q=q, required_served=required, trace=trace)
    bits, energy, served = _totals_exact(panel, inner.choices)
    if inner.score != 0 or bits - q * energy != 0 or served < required:
        raise E1EstimandError("certificate does not prove global optimality")
    estimand = U1_ESTIMAND if candidate_field == "unilateral_profiles" else J1_ESTIMAND
    base_ratio = (
        sum((anchor.base.bits_exact for anchor in panel), Fraction(0))
        / sum((anchor.base.energy_exact for anchor in panel), Fraction(0))
    )
    base_float_bits = math.fsum(anchor.base.total_bits for anchor in panel)
    base_float_energy = math.fsum(anchor.base.total_energy_j for anchor in panel)
    chosen = result.get("chosen_profiles")
    expected = {
        anchor.anchor_id: anchor.profiles[index].profile_id
        for anchor, index in zip(panel, inner.choices, strict=True)
    }
    if (
        result.get("value_hex") != float(q).hex()
        or result.get(estimand) != float(q)
        or result.get("eta_BASE_hex") != (base_float_bits / base_float_energy).hex()
        or result.get("eta_BASE_exact") != _fraction_payload(base_ratio)
        or certificate.get("coefficients_sha256")
        != _canonical_sha256(_coefficient_payload(panel))
        or certificate.get("choice_set_census") != _choice_set_census(panel, q=q)
        or certificate.get("dp_trace") != trace
        or certificate.get("terminal_backpointer_profile_ids") != expected
        or certificate.get("selected_totals_exact")
        != {
            "bits": _fraction_payload(bits),
            "energy_j": _fraction_payload(energy),
            "served": served,
            "ratio": _fraction_payload(bits / energy),
        }
    ):
        raise E1EstimandError("certificate numeric summary disagrees with exact proof")
    if chosen != expected:
        raise E1EstimandError("certificate witness disagrees with chosen profiles")
    return True


def _solve(values: Sequence[object], *, candidate_field: str, estimand: str) -> dict[str, object]:
    anchors = _canonical_anchors(values, candidate_field=candidate_field)
    required, base_served, opportunities = _required_served(anchors)
    base_bits = sum((anchor.base.bits_exact for anchor in anchors), Fraction(0))
    base_energy = sum((anchor.base.energy_exact for anchor in anchors), Fraction(0))
    q = base_bits / base_energy
    iterations = 0
    while True:
        iterations += 1
        if iterations > MAX_DINKELBACH_ITERATIONS:
            raise E1EstimandError("exact Dinkelbach iteration limit exceeded")
        inner = _inner_exact(anchors, q=q, required_served=required)
        bits, energy, served = _totals_exact(anchors, inner.choices)
        residual = bits - q * energy
        if residual == 0:
            break
        if residual < 0:
            raise E1EstimandError("Dinkelbach residual became negative")
        next_q = bits / energy
        if next_q <= q:
            raise E1EstimandError("Dinkelbach ratio failed to increase")
        q = next_q

    chosen_options = [
        anchor.profiles[index]
        for anchor, index in zip(anchors, inner.choices, strict=True)
    ]
    float_bits = math.fsum(row.total_bits for row in chosen_options)
    float_energy = math.fsum(row.total_energy_j for row in chosen_options)
    base_float_bits = math.fsum(anchor.base.total_bits for anchor in anchors)
    base_float_energy = math.fsum(anchor.base.total_energy_j for anchor in anchors)
    chosen = {
        anchor.anchor_id: option.profile_id
        for anchor, option in zip(anchors, chosen_options, strict=True)
    }
    final_trace: list[dict[str, object]] = []
    certified_inner = _inner_exact(
        anchors, q=q, required_served=required, trace=final_trace
    )
    if certified_inner != inner:
        raise E1EstimandError("terminal DP replay changed the optimal witness")
    coefficients = _coefficient_payload(anchors)
    choice_set_census = _choice_set_census(anchors, q=q)
    result: dict[str, object] = {
        estimand: float(q),
        "value_hex": float(q).hex(),
        "eta_BASE": base_float_bits / base_float_energy,
        "eta_BASE_hex": (base_float_bits / base_float_energy).hex(),
        "eta_BASE_exact": _fraction_payload(base_bits / base_energy),
        "chosen_profiles": chosen,
        "pooled": {
            "total_bits_hex": float_bits.hex(),
            "total_energy_j_hex": float_energy.hex(),
            "served": served,
            "opportunities": opportunities,
            "service_fraction_hex": (served / opportunities).hex(),
            "minimum_served": required,
            "base_served": base_served,
        },
        "certificate": {
            "method": CERTIFICATE_METHOD,
            "iterations": iterations,
            "choice_set_census": choice_set_census,
            "coefficients": coefficients,
            "coefficients_sha256": _canonical_sha256(coefficients),
            "optimal_ratio_exact": _fraction_payload(q),
            "terminal_inner_max_exact": _fraction_payload(inner.score),
            "chosen_residual_exact": _fraction_payload(bits - q * energy),
            "selected_totals_exact": {
                "bits": _fraction_payload(bits),
                "energy_j": _fraction_payload(energy),
                "served": served,
                "ratio": _fraction_payload(bits / energy),
            },
            "service_dimension": "INTEGER_SERVED_COUNT_CAPPED_AT_REQUIRED_THRESHOLD",
            "minimum_served": required,
            "witness_served": served,
            "feasible": served >= required,
            "global_upper_bound_proved": inner.score == 0,
            "dp_recurrence": "D_i[min(required,c+s)]=max_x(D_i-1[c]+B_ix-qE_ix)",
            "dp_trace": final_trace,
            "terminal_backpointer_profile_ids": chosen,
        },
    }
    verify_certificate(values, result, candidate_field=candidate_field)
    return result


def solve_u1(anchors: Sequence[object]) -> dict[str, object]:
    """Solve the exact BASE-or-legal-unilateral pooled fractional problem."""

    return _solve(anchors, candidate_field="unilateral_profiles", estimand=U1_ESTIMAND)


def solve_j1(catalog: Sequence[object]) -> dict[str, object]:
    """Solve the exact BASE-or-complete-joint-witness pooled problem."""

    return _solve(catalog, candidate_field="joint_profiles", estimand=J1_ESTIMAND)


__all__ = [
    "AnchorOptions",
    "BASE_PROFILE_ID",
    "CERTIFICATE_METHOD",
    "E1EstimandError",
    "J1_ESTIMAND",
    "ProfileOption",
    "SERVICE_MARGIN",
    "SERVICE_MARGIN_DENOMINATOR",
    "SERVICE_MARGIN_NUMERATOR",
    "U1_ESTIMAND",
    "solve_j1",
    "solve_u1",
    "verify_certificate",
]
