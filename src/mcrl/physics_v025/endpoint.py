"""Exact pooled-EE, reward-core, and service endpoint accounting."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Iterable

from mcrl.errors import MCRLContractError


Number = int | float | str | Fraction


def exact(value: Number) -> Fraction:
    """Convert declared decimal inputs to rational values without float summing."""

    if isinstance(value, bool):
        raise MCRLContractError("Boolean is not an endpoint quantity")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MCRLContractError("endpoint quantities must be finite")
        return Fraction(str(value))
    return Fraction(value)


@dataclass(frozen=True)
class StepEndpoint:
    bits: Fraction
    joules: Fraction
    decoding_user_seconds: Fraction
    useful_user_seconds: Fraction
    opportunity_user_seconds: Fraction
    complete_service_user_steps: int
    user_steps: int

    @classmethod
    def build(
        cls,
        *,
        bits: Number,
        joules: Number,
        decoding_user_seconds: Number,
        useful_user_seconds: Number,
        opportunity_user_seconds: Number,
        complete_service_user_steps: int,
        user_steps: int,
    ) -> "StepEndpoint":
        result = cls(
            exact(bits),
            exact(joules),
            exact(decoding_user_seconds),
            exact(useful_user_seconds),
            exact(opportunity_user_seconds),
            int(complete_service_user_steps),
            int(user_steps),
        )
        result.verify()
        return result

    def verify(self) -> None:
        if self.bits < 0 or self.joules < 0:
            raise MCRLContractError("bits and joules must be nonnegative")
        if self.joules == 0 and self.bits > 0:
            raise MCRLContractError("positive bits at zero energy is invalid")
        if not 0 <= self.decoding_user_seconds <= self.opportunity_user_seconds:
            raise MCRLContractError("decoding availability is outside its opportunity time")
        if not 0 <= self.useful_user_seconds <= self.decoding_user_seconds:
            raise MCRLContractError("useful time is outside decoding time")
        if not 0 <= self.complete_service_user_steps <= self.user_steps:
            raise MCRLContractError("complete-service count is outside user steps")


@dataclass(frozen=True)
class EndpointTotals:
    bits: Fraction
    joules: Fraction
    pooled_ee: Fraction | None
    decoding_availability: Fraction
    useful_availability: Fraction
    complete_service_user_steps: int
    user_steps: int


def pool(steps: Iterable[StepEndpoint]) -> EndpointTotals:
    """Ratio of sums; all-dark is explicitly undefined rather than dropped."""

    rows = tuple(steps)
    for row in rows:
        row.verify()
    bits = sum((row.bits for row in rows), Fraction())
    joules = sum((row.joules for row in rows), Fraction())
    opportunity = sum((row.opportunity_user_seconds for row in rows), Fraction())
    decoding = sum((row.decoding_user_seconds for row in rows), Fraction())
    useful = sum((row.useful_user_seconds for row in rows), Fraction())
    return EndpointTotals(
        bits,
        joules,
        None if joules == 0 else bits / joules,
        Fraction() if opportunity == 0 else decoding / opportunity,
        Fraction() if opportunity == 0 else useful / opportunity,
        sum(row.complete_service_user_steps for row in rows),
        sum(row.user_steps for row in rows),
    )


def reward_core(
    endpoint: StepEndpoint | EndpointTotals,
    *,
    eta_ref: Number,
) -> Fraction:
    """Return ``B - eta_ref*E`` for either one step or its pooled endpoint."""

    if isinstance(endpoint, StepEndpoint):
        endpoint.verify()
    b, e, eta = endpoint.bits, endpoint.joules, exact(eta_ref)
    if b < 0 or e < 0 or eta <= 0:
        raise MCRLContractError("reward inputs require B,E>=0 and eta_ref>0")
    return b - eta * e


def assert_same_energy_price(
    *,
    lambda_bits_per_j: Number,
    eta_ref: Number,
) -> Fraction:
    """Fail closed unless explicit target lambda and endpoint eta are identical."""

    target_price = exact(lambda_bits_per_j)
    endpoint_price = exact(eta_ref)
    if target_price <= 0 or endpoint_price <= 0:
        raise MCRLContractError("lambda and eta_ref must both be positive")
    if target_price != endpoint_price:
        raise MCRLContractError("target lambda and endpoint eta_ref do not match")
    return endpoint_price


def calibration(bits: Number, joules: Number, *, users: int, time_s: Number) -> tuple[Fraction, Fraction]:
    """Return ``(eta_ref, kappa)`` from positive nominal-greedy totals."""

    b, e, duration = exact(bits), exact(joules), exact(time_s)
    if b <= 0 or e <= 0 or users <= 0 or duration <= 0:
        raise MCRLContractError("calibration totals, users, and time must be positive")
    return b / e, b / (users * duration)


__all__ = [
    "EndpointTotals",
    "StepEndpoint",
    "assert_same_energy_price",
    "calibration",
    "exact",
    "pool",
    "reward_core",
]
