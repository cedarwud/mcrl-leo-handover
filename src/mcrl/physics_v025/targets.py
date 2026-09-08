"""V0.25 C1/C2/C3 targets with one explicit calibrated energy price."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Callable, Iterable, Literal, Mapping, Sequence

from mcrl.errors import MCRLContractError

from .calibration import assert_calibration_prices
from .constants_v025 import (
    BEAM_RF_CAP_W,
    DECISION_INTERVAL_S,
    FORECAST_OFFSETS,
    PHI_SAME_SATELLITE,
    PHI_SATELLITE_CHANGE,
)
from .endpoint import EndpointTotals, StepEndpoint, exact, pool, reward_core


PhysicalIdentity = tuple[int, int]
TransitionKind = Literal[
    "unchanged",
    "beam_change",
    "satellite_change",
    "cell_rekey",
    "initial_entry",
    "reentry",
    "exit",
]


@dataclass(frozen=True)
class HandoverEvent:
    user_id: int
    kind: TransitionKind
    before: PhysicalIdentity | None
    after: PhysicalIdentity | None
    cell_rekey: bool = False


def classify_physical_transition(
    *,
    user_id: int,
    before: PhysicalIdentity | None,
    after: PhysicalIdentity | None,
    cell_rekey: bool,
    was_previously_served: bool,
) -> HandoverEvent:
    """Classify by physical NORAD/beam-chain, never action slot/cell ID."""

    if before is None and after is None:
        kind: TransitionKind = "unchanged"
    elif before is None:
        kind = "reentry" if was_previously_served else "initial_entry"
    elif after is None:
        kind = "exit"
    elif before[0] != after[0]:
        kind = "satellite_change"
    elif before[1] != after[1]:
        kind = "beam_change"
    elif cell_rekey:
        kind = "cell_rekey"
    else:
        kind = "unchanged"
    return HandoverEvent(user_id, kind, before, after, cell_rekey)


def phi_qos(events: Iterable[HandoverEvent]) -> Fraction:
    """Return the explicit dimensionless Phi preference (higher is better)."""

    score = 0.0
    for event in events:
        if event.kind == "satellite_change":
            score -= PHI_SATELLITE_CHANGE
        elif event.kind == "beam_change":
            score -= PHI_SAME_SATELLITE
    return exact(score)


@dataclass(frozen=True)
class NetworkOutcome:
    """One whole-network physical profile used by every teacher."""

    bits: Fraction
    joules: Fraction
    phi: Fraction
    decoding_availability: Fraction
    useful_availability: Fraction
    per_user_bits: tuple[tuple[int, Fraction], ...] = ()

    @classmethod
    def build(
        cls,
        *,
        bits: int | float | str | Fraction,
        joules: int | float | str | Fraction,
        phi: int | float | str | Fraction,
        decoding_availability: int | float | str | Fraction,
        useful_availability: int | float | str | Fraction,
        per_user_bits: Mapping[int, int | float | str | Fraction] | None = None,
    ) -> "NetworkOutcome":
        result = cls(
            exact(bits),
            exact(joules),
            exact(phi),
            exact(decoding_availability),
            exact(useful_availability),
            tuple(
                sorted(
                    (int(user), exact(value))
                    for user, value in ({} if per_user_bits is None else per_user_bits).items()
                )
            ),
        )
        if result.bits < 0 or result.joules < 0:
            raise MCRLContractError("network bits/joules must be nonnegative")
        if result.bits > 0 and result.joules == 0:
            raise MCRLContractError("positive network bits at zero energy is invalid")
        if not 0 <= result.useful_availability <= result.decoding_availability <= 1:
            raise MCRLContractError("network availability is outside [0,1]")
        if result.per_user_bits and sum((value for _, value in result.per_user_bits), Fraction()) != result.bits:
            raise MCRLContractError("per-user bits do not sum to whole-network bits")
        return result


def network_objective(
    outcome: NetworkOutcome,
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> Fraction:
    """F = B - eta_ref E for the whole network; Phi stays separate."""

    eta, _kappa = assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    return outcome.bits - eta * outcome.joules


@dataclass(frozen=True)
class C1Label:
    difference_surplus_bits: Fraction
    phi_difference: Fraction
    normalized_total: Fraction


def c1_difference_surplus(
    candidate: NetworkOutcome,
    default: NetworkOutcome,
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> C1Label:
    """Whole-network C1 difference versus the declared default action."""

    eta, kappa = assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    core = (candidate.bits - default.bits) - eta * (candidate.joules - default.joules)
    phi = candidate.phi - default.phi
    return C1Label(core, phi, core / kappa + phi)


@dataclass(frozen=True)
class OffsetProjection:
    offset_index: int
    valid: bool
    survives: bool
    outcome: NetworkOutcome
    background_power_recomputed: bool
    required_power_w: float | None
    power_cap_w: float | None
    min_decoding_margin_db: float
    mean_acm_se_bit_s_hz: float

    def __post_init__(self) -> None:
        if self.offset_index not in range(1, FORECAST_OFFSETS + 1):
            raise MCRLContractError("forecast offset is outside the frozen three offsets")
        if not self.background_power_recomputed:
            raise MCRLContractError("projection reused stale background powers")
        if not math.isfinite(self.min_decoding_margin_db) or not math.isfinite(self.mean_acm_se_bit_s_hz):
            raise MCRLContractError("projection margin/SE must be finite")
        if (self.required_power_w is None) != (self.power_cap_w is None):
            raise MCRLContractError("required power and cap must be supplied together")
        if self.required_power_w is not None and (
            not math.isfinite(self.required_power_w)
            or not math.isfinite(self.power_cap_w)
            or self.required_power_w < 0.0
            or self.power_cap_w <= 0.0
        ):
            raise MCRLContractError("invalid projected required-power/cap values")

    @property
    def required_power_cap_margin_w(self) -> float | None:
        if self.required_power_w is None or self.power_cap_w is None:
            return None
        return self.power_cap_w - self.required_power_w


ProjectionEvaluator = Callable[[int, float, Mapping[int, PhysicalIdentity | None], bool], OffsetProjection]


def project_three_offsets(
    *,
    assignments: Mapping[int, PhysicalIdentity | None],
    evaluator: ProjectionEvaluator,
    architecture: str,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> tuple[OffsetProjection, ...]:
    """Project three physical offsets and force background re-optimisation."""

    assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    rows = tuple(
        evaluator(index, index * DECISION_INTERVAL_S, assignments, True)
        for index in range(1, FORECAST_OFFSETS + 1)
    )
    if architecture in {"a-r", "a′-r"} and any(
        row.required_power_w is None or row.power_cap_w is None for row in rows
    ):
        raise MCRLContractError("rate-target forecast lacks required-power/cap fields")
    return rows


@dataclass(frozen=True)
class C2Label:
    forecast_surplus_bits: Fraction
    lost_offsets: int
    persistence_penalty_bits: Fraction
    normalized_total: Fraction
    projections: tuple[OffsetProjection, ...]


def c2_persistence_forecast(
    candidate: Sequence[OffsetProjection],
    default: Sequence[OffsetProjection],
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> C2Label:
    """OPS-3-style absorbing persistence with one -kappa per lost offset.

    The failed offset's attempted transmission is already present in its
    ``NetworkOutcome``.  Only later offsets are made absorbing losses; live
    recovery outside this forecast remains possible.
    """

    eta, kappa = assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    candidate_rows, default_rows = tuple(candidate), tuple(default)
    if len(candidate_rows) != FORECAST_OFFSETS or len(default_rows) != FORECAST_OFFSETS:
        raise MCRLContractError("C2 requires exactly three candidate and default projections")
    if tuple(row.offset_index for row in candidate_rows) != (1, 2, 3):
        raise MCRLContractError("candidate forecast offsets are not ordered 1,2,3")
    if tuple(row.offset_index for row in default_rows) != (1, 2, 3):
        raise MCRLContractError("default forecast offsets are not ordered 1,2,3")
    alive = True
    core = Fraction()
    lost = 0
    retained: list[OffsetProjection] = []
    for selected, baseline in zip(candidate_rows, default_rows, strict=True):
        if not selected.background_power_recomputed or not baseline.background_power_recomputed:
            raise MCRLContractError("C2 projection did not recompute background powers")
        if alive:
            core += (selected.outcome.bits - baseline.outcome.bits) - eta * (
                selected.outcome.joules - baseline.outcome.joules
            )
            retained.append(selected)
            if not selected.valid or not selected.survives:
                alive = False
                lost += 1
        else:
            lost += 1
            retained.append(selected)
    penalty = kappa * lost
    return C2Label(core, lost, penalty, (core - penalty) / kappa, tuple(retained))


@dataclass(frozen=True)
class C3Interaction:
    f00: Fraction
    f10: Fraction
    f01: Fraction
    f11: Fraction
    psi: Fraction
    z3_by_user: tuple[tuple[int, Fraction], ...]


def c3_lcsrs_interaction(
    *,
    coalition_users: Sequence[int],
    f00: NetworkOutcome,
    f10: NetworkOutcome,
    f01: NetworkOutcome,
    f11: NetworkOutcome,
    externality_e_by_user: Mapping[int, int | float | str | Fraction],
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> C3Interaction:
    """Declared LC-SRS two-user interaction Psi on one network objective F."""

    users = tuple(int(user) for user in coalition_users)
    if len(users) != 2 or len(set(users)) != 2 or set(users) != set(externality_e_by_user):
        raise MCRLContractError("LC-SRS interaction requires exactly two coalition users/e_i values")
    values = tuple(
        network_objective(
            outcome,
            lambda_bits_per_j=lambda_bits_per_j,
            eta_ref=eta_ref,
            kappa_bits_per_user_s=kappa_bits_per_user_s,
        )
        for outcome in (f00, f10, f01, f11)
    )
    psi = values[3] - values[1] - values[2] + values[0]
    z3 = tuple((user, exact(externality_e_by_user[user]) + psi / 2) for user in users)
    return C3Interaction(*values, psi, z3)


def assert_reward_core_identity(
    steps: Iterable[StepEndpoint],
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> Fraction:
    """Prove sum_t(B_t-eta E_t) == B-eta E for the supplied trajectory."""

    eta, _kappa = assert_calibration_prices(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
        kappa_bits_per_user_s=kappa_bits_per_user_s,
    )
    rows = tuple(steps)
    lhs = sum((reward_core(row, eta_ref=eta) for row in rows), Fraction())
    rhs = reward_core(pool(rows), eta_ref=eta)
    if lhs != rhs:
        raise MCRLContractError("reward core does not telescope to the endpoint")
    return rhs


__all__ = [
    "C1Label",
    "C2Label",
    "C3Interaction",
    "HandoverEvent",
    "NetworkOutcome",
    "OffsetProjection",
    "assert_reward_core_identity",
    "c1_difference_surplus",
    "c2_persistence_forecast",
    "c3_lcsrs_interaction",
    "classify_physical_transition",
    "network_objective",
    "phi_qos",
    "project_three_offsets",
]
