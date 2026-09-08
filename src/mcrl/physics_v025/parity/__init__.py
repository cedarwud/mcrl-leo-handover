"""Independent declared-target and decoder parity checks for V0.25."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Mapping, Sequence

from mcrl.errors import MCRLContractError

from ..calibration import assert_calibration_prices
from ..endpoint import StepEndpoint, exact, pool, reward_core
from ..targets import NetworkOutcome, c3_lcsrs_interaction


LABELS = ("00", "10", "01", "11")


@dataclass(frozen=True)
class DecisionProfile:
    label: str
    bits: tuple[Fraction, ...]
    energy_j: Fraction
    served: tuple[bool, ...]

    @classmethod
    def build(
        cls,
        label: str,
        *,
        bits: Sequence[int | float | str | Fraction],
        energy_j: int | float | str | Fraction,
        served: Sequence[bool],
    ) -> "DecisionProfile":
        result = cls(label, tuple(exact(value) for value in bits), exact(energy_j), tuple(served))
        if label not in LABELS or len(result.bits) != 2 or len(result.served) != 2:
            raise MCRLContractError("parity profiles require labelled two-user 00/10/01/11 states")
        if result.energy_j < 0 or any(value < 0 for value in result.bits):
            raise MCRLContractError("parity endpoint bits and energy must be nonnegative")
        if sum(result.bits, Fraction()) > 0 and result.energy_j == 0:
            raise MCRLContractError("positive parity bits require positive energy")
        return result

    @property
    def total_bits(self) -> Fraction:
        return sum(self.bits, Fraction())


@dataclass(frozen=True)
class C3ParityResult:
    f_values: tuple[Fraction, ...]
    unilateral_c3: tuple[Fraction, Fraction]
    psi: Fraction
    lcsrs_shares: tuple[Fraction, Fraction]


@dataclass(frozen=True)
class ExecutedEndpoint:
    action: str
    bits: tuple[Fraction, ...]
    energy_j: Fraction
    served: tuple[bool, ...]


@dataclass(frozen=True)
class DecoderParityTrace:
    raw_state_endpoints: Mapping[str, ExecutedEndpoint]
    production_formula_matches_declared: bool
    additive_execution: ExecutedEndpoint
    atomic_execution: ExecutedEndpoint


@dataclass(frozen=True)
class BootstrapChoice:
    action_index: int
    selected_heads: tuple[Fraction, ...]
    scalarized_value: Fraction


def _prices(
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> tuple[Fraction, Fraction]:
    return assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )


def _validate_profiles(profiles: Sequence[DecisionProfile]) -> tuple[DecisionProfile, ...]:
    rows = tuple(profiles)
    if len(rows) != 4 or tuple(row.label for row in rows) != LABELS:
        raise MCRLContractError("profiles must be ordered 00,10,01,11")
    return rows


def _outcome(profile: DecisionProfile) -> NetworkOutcome:
    return NetworkOutcome.build(
        bits=profile.total_bits,
        joules=profile.energy_j,
        phi=0,
        decoding_availability=sum(profile.served) / 2,
        useful_availability=sum(profile.served) / 2,
        per_user_bits={index: value for index, value in enumerate(profile.bits)},
    )


def declared_c3_oracle(
    p00: DecisionProfile,
    p10: DecisionProfile,
    p01: DecisionProfile,
    p11: DecisionProfile,
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> C3ParityResult:
    """Independent LC-SRS Ψ oracle, adapted from the V0.23 parity suite."""

    rows = _validate_profiles((p00, p10, p01, p11))
    price, _ = _prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    f_values = tuple(row.total_bits - price * row.energy_j for row in rows)
    # The successor whole-network C1 already carries every unilateral bit and
    # energy change.  The historical own-bits C1 externality term is therefore
    # zero here; only the equal interaction share belongs in C3.
    unilateral = (Fraction(), Fraction())
    psi = f_values[3] - f_values[1] - f_values[2] + f_values[0]
    return C3ParityResult(f_values, unilateral, psi, (unilateral[0] + psi / 2, unilateral[1] + psi / 2))


def production_c3(
    p00: DecisionProfile,
    p10: DecisionProfile,
    p01: DecisionProfile,
    p11: DecisionProfile,
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> C3ParityResult:
    """Evaluate the same raw profiles through the production target formula."""

    _validate_profiles((p00, p10, p01, p11))
    result = c3_lcsrs_interaction(
        coalition_users=(0, 1),
        f00=_outcome(p00),
        f10=_outcome(p10),
        f01=_outcome(p01),
        f11=_outcome(p11),
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    return C3ParityResult(
        (result.f00, result.f10, result.f01, result.f11),
        (Fraction(), Fraction()),
        result.psi,
        (dict(result.z3_by_user)[0], dict(result.z3_by_user)[1]),
    )


def _execute(profile: DecisionProfile) -> ExecutedEndpoint:
    return ExecutedEndpoint(profile.label, profile.bits, profile.energy_j, profile.served)


def trace_declared_target_decoder_parity(
    p00: DecisionProfile,
    p10: DecisionProfile,
    p01: DecisionProfile,
    p11: DecisionProfile,
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> DecoderParityTrace:
    """Cross both formulas and both decoders through actions to endpoints."""

    rows = _validate_profiles((p00, p10, p01, p11))
    declared = declared_c3_oracle(
        *rows,
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    production = production_c3(
        *rows,
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    by_label = {row.label: row for row in rows}
    additive_label = f"{int(declared.lcsrs_shares[0] > 0)}{int(declared.lcsrs_shares[1] > 0)}"
    # The atomic decoder scores only attainable joint actions.  It must not
    # splice independent head maxima into a state absent from the catalogue.
    atomic_scores = tuple(
        sum(
            (
                declared.lcsrs_shares[user]
                for user, enabled in enumerate(label)
                if enabled == "1"
            ),
            Fraction(),
        )
        for label in LABELS
    )
    atomic_index = min(range(4), key=lambda index: (-atomic_scores[index], index))
    endpoints = MappingProxyType({label: _execute(by_label[label]) for label in LABELS})
    return DecoderParityTrace(
        endpoints,
        production == declared,
        _execute(by_label[additive_label]),
        _execute(rows[atomic_index]),
    )


def demand_cap_profiles(
    profiles: Sequence[DecisionProfile],
    *,
    demand_cap_bits: int | float | str | Fraction,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> tuple[DecisionProfile, ...]:
    """Apply a demand cap after binding prices; a non-binding cap is invariant."""

    _prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    cap = exact(demand_cap_bits)
    if cap < 0:
        raise MCRLContractError("demand cap must be nonnegative")
    return tuple(
        DecisionProfile.build(
            row.label,
            bits=tuple(min(value, cap) for value in row.bits),
            energy_j=row.energy_j,
            served=row.served,
        )
        for row in profiles
    )


def reoptimize_joint_by_regime(
    profiles_by_regime: Mapping[str, Sequence[DecisionProfile]],
    *,
    lambda_by_regime: Mapping[str, int | float | str | Fraction],
    eta_ref_by_regime: Mapping[str, int | float | str | Fraction],
    kappa_bits_per_user_s_by_regime: Mapping[str, int | float | str | Fraction],
) -> dict[str, str]:
    """Re-evaluate every atomic J candidate separately in each physics regime."""

    if not (
        set(profiles_by_regime)
        == set(lambda_by_regime)
        == set(eta_ref_by_regime)
        == set(kappa_bits_per_user_s_by_regime)
    ):
        raise MCRLContractError("every regime needs explicit lambda, eta, and kappa")
    choices = {}
    for regime, profiles in profiles_by_regime.items():
        rows = _validate_profiles(profiles)
        price, _ = _prices(
            lambda_bits_per_j=lambda_by_regime[regime],
            eta_ref=eta_ref_by_regime[regime],
            kappa_bits_per_user_s=kappa_bits_per_user_s_by_regime[regime],
        )
        index = min(range(4), key=lambda item: (-(rows[item].total_bits - price * rows[item].energy_j), item))
        choices[regime] = rows[index].label
    return choices


def common_action_bootstrap(
    heads_by_action: Sequence[Sequence[int | float | str | Fraction]],
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> BootstrapChoice:
    """Choose one scalarised next action; never mix maxima across heads."""

    _prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    rows = tuple(tuple(exact(value) for value in heads) for heads in heads_by_action)
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise MCRLContractError("bootstrap heads must be a nonempty rectangular action table")
    index = min(range(len(rows)), key=lambda item: (-sum(rows[item], Fraction()), item))
    return BootstrapChoice(index, rows[index], sum(rows[index], Fraction()))


def reward_endpoint_identity(
    *,
    step_bits: Sequence[int | float | str | Fraction],
    step_energy_j: Sequence[int | float | str | Fraction],
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> Fraction:
    """Imported parity assertion: step rewards equal the pooled endpoint core."""

    eta, _ = _prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    if len(step_bits) != len(step_energy_j) or not step_bits:
        raise MCRLContractError("reward parity arrays must be nonempty and equally sized")
    steps = tuple(
        StepEndpoint.build(
            bits=bits,
            joules=energy,
            decoding_user_seconds=0,
            useful_user_seconds=0,
            opportunity_user_seconds=0,
            complete_service_user_steps=0,
            user_steps=0,
        )
        for bits, energy in zip(step_bits, step_energy_j, strict=True)
    )
    summed = sum((reward_core(step, eta_ref=eta) for step in steps), Fraction())
    endpoint = reward_core(pool(steps), eta_ref=eta)
    if summed != endpoint:
        raise MCRLContractError("reward and endpoint cores disagree")
    return endpoint


__all__ = [
    "BootstrapChoice",
    "C3ParityResult",
    "DecisionProfile",
    "DecoderParityTrace",
    "ExecutedEndpoint",
    "common_action_bootstrap",
    "declared_c3_oracle",
    "demand_cap_profiles",
    "production_c3",
    "reoptimize_joint_by_regime",
    "reward_endpoint_identity",
    "trace_declared_target_decoder_parity",
]
