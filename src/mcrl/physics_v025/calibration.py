"""Frozen per-setting nominal-greedy calibration for V0.25."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from types import MappingProxyType
from typing import Iterable, Mapping

from mcrl.errors import MCRLContractError

from .endpoint import assert_same_energy_price, calibration, exact
from .matrix import PhysicsSetting
from .tapes import CALIBRATION_WORLD_DOMAINS, ExogenousWorldTape, digest_payload


@dataclass(frozen=True)
class NominalConfiguration:
    """Causal quantities used by the deterministic calibration policy."""

    configuration_id: str
    assignments: tuple[tuple[int, tuple[int, int] | None], ...]
    nominal_bits: float
    nominal_joules: float
    nominal_served_users: int

    def __post_init__(self) -> None:
        if not self.configuration_id or not math.isfinite(self.nominal_bits) or self.nominal_bits < 0.0:
            raise MCRLContractError("invalid nominal calibration configuration")
        if not math.isfinite(self.nominal_joules) or self.nominal_joules < 0.0:
            raise MCRLContractError("invalid nominal calibration energy")
        if type(self.nominal_served_users) is not int or self.nominal_served_users < 0:
            raise MCRLContractError("invalid nominal served-user count")


def nominal_greedy_reference(
    configurations: Iterable[NominalConfiguration],
) -> NominalConfiguration:
    """Choose served users, then bits, then lower energy, with stable ID ties.

    This policy needs no EE price, avoiding a circular calibration definition.
    It consumes nominal information only and is re-run independently per
    physics setting.
    """

    rows = tuple(configurations)
    if not rows:
        raise MCRLContractError("nominal-greedy reference needs a configuration")
    return min(
        rows,
        key=lambda row: (
            -row.nominal_served_users,
            -row.nominal_bits,
            row.nominal_joules,
            row.configuration_id,
        ),
    )


@dataclass(frozen=True)
class CalibrationObservation:
    world_domain: str
    bits: Fraction
    joules: Fraction
    users: int
    time_s: Fraction
    selected_configuration_id: str
    decision_steps: int = 1

    @classmethod
    def build(
        cls,
        *,
        world_domain: str,
        bits: int | float | str | Fraction,
        joules: int | float | str | Fraction,
        users: int,
        time_s: int | float | str | Fraction,
        selected_configuration_id: str,
        decision_steps: int = 1,
    ) -> "CalibrationObservation":
        if world_domain not in CALIBRATION_WORLD_DOMAINS:
            raise MCRLContractError("calibration observation is not from a declared V025_CAL world")
        result = cls(
            world_domain,
            exact(bits),
            exact(joules),
            users,
            exact(time_s),
            selected_configuration_id,
            decision_steps,
        )
        if (
            result.bits < 0
            or result.joules < 0
            or users <= 0
            or result.time_s <= 0
            or type(decision_steps) is not int
            or decision_steps <= 0
        ):
            raise MCRLContractError("invalid calibration observation totals")
        if not selected_configuration_id:
            raise MCRLContractError("calibration selection identity is required")
        return result


@dataclass(frozen=True)
class CalibrationValues:
    setting_label: str
    setting_digest: str
    eta_ref: Fraction
    lambda_bits_per_j: Fraction
    kappa_bits_per_user_s: Fraction
    bits_ref: Fraction
    joules_ref: Fraction
    users: int
    decision_steps_ref: int
    time_ref_s: Fraction
    world_domains: tuple[str, ...]
    selection_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        assert_calibration_prices(
            lambda_bits_per_j=self.lambda_bits_per_j,
            eta_ref=self.eta_ref,
            kappa_bits_per_user_s=self.kappa_bits_per_user_s,
        )
        if (
            self.bits_ref <= 0
            or self.joules_ref <= 0
            or self.users <= 0
            or type(self.decision_steps_ref) is not int
            or self.decision_steps_ref <= 0
            or self.time_ref_s <= 0
        ):
            raise MCRLContractError("frozen calibration totals must be positive")
        if self.eta_ref != self.bits_ref / self.joules_ref:
            raise MCRLContractError("eta_ref is not B_ref/E_ref")
        if self.kappa_bits_per_user_s != self.bits_ref / (
            self.users * self.decision_steps_ref
        ):
            raise MCRLContractError("kappa is not B_ref/(U*N_ref)")
        if set(self.world_domains) != set(CALIBRATION_WORLD_DOMAINS):
            raise MCRLContractError("calibration must use exactly the two disjoint V025_CAL worlds")

    @property
    def digest(self) -> str:
        return digest_payload(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "schema": "mcrl-v025-setting-calibration-v2-user-step",
            "setting_label": self.setting_label,
            "setting_sha256": self.setting_digest,
            "eta_ref": [self.eta_ref.numerator, self.eta_ref.denominator],
            "lambda_bits_per_j": [
                self.lambda_bits_per_j.numerator,
                self.lambda_bits_per_j.denominator,
            ],
            "kappa_bits_per_user_s": [
                self.kappa_bits_per_user_s.numerator,
                self.kappa_bits_per_user_s.denominator,
            ],
            "bits_ref": [self.bits_ref.numerator, self.bits_ref.denominator],
            "joules_ref": [self.joules_ref.numerator, self.joules_ref.denominator],
            "users": self.users,
            "decision_steps_ref": self.decision_steps_ref,
            "time_ref_s": [self.time_ref_s.numerator, self.time_ref_s.denominator],
            "world_domains": list(self.world_domains),
            "selection_ids": list(self.selection_ids),
            "frozen_once": True,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "CalibrationValues":
        """Reconstruct and revalidate an immutable calibration receipt."""

        def ratio(name: str) -> Fraction:
            value = payload.get(name)
            if not isinstance(value, list) or len(value) != 2:
                raise MCRLContractError(f"calibration field {name} is not an exact ratio")
            return Fraction(int(value[0]), int(value[1]))

        try:
            result = cls(
                str(payload["setting_label"]),
                str(payload["setting_sha256"]),
                ratio("eta_ref"),
                ratio("lambda_bits_per_j"),
                ratio("kappa_bits_per_user_s"),
                ratio("bits_ref"),
                ratio("joules_ref"),
                int(payload["users"]),
                int(payload["decision_steps_ref"]),
                ratio("time_ref_s"),
                tuple(str(value) for value in payload["world_domains"]),  # type: ignore[index]
                tuple(str(value) for value in payload["selection_ids"]),  # type: ignore[index]
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
            raise MCRLContractError("malformed calibration payload") from error
        if payload != result.payload():
            raise MCRLContractError("calibration payload is noncanonical or drifted")
        return result


def assert_calibration_prices(
    *,
    lambda_bits_per_j: int | float | str | Fraction,
    eta_ref: int | float | str | Fraction,
    kappa_bits_per_user_s: int | float | str | Fraction,
) -> tuple[Fraction, Fraction]:
    """Single mandatory gate used by every target/state producer."""

    eta = assert_same_energy_price(
        lambda_bits_per_j=lambda_bits_per_j,
        eta_ref=eta_ref,
    )
    kappa = exact(kappa_bits_per_user_s)
    if kappa <= 0:
        raise MCRLContractError("kappa must be explicitly supplied and positive")
    return eta, kappa


def freeze_setting_calibration(
    *,
    setting: PhysicsSetting,
    observations: Iterable[CalibrationObservation],
) -> CalibrationValues:
    """Pool exactly two calibration worlds and freeze eta=lambda and kappa."""

    rows = tuple(observations)
    if len(rows) != len(CALIBRATION_WORLD_DOMAINS):
        raise MCRLContractError("one observation from each calibration world is required")
    if tuple(sorted(row.world_domain for row in rows)) != tuple(sorted(CALIBRATION_WORLD_DOMAINS)):
        raise MCRLContractError("calibration world domains are missing, duplicated, or contaminated")
    users = {row.users for row in rows}
    if len(users) != 1:
        raise MCRLContractError("calibration user population changed between worlds")
    bits = sum((row.bits for row in rows), Fraction())
    joules = sum((row.joules for row in rows), Fraction())
    time_s = sum((row.time_s for row in rows), Fraction())
    user_count = next(iter(users))
    decision_steps = sum(row.decision_steps for row in rows)
    eta_ref, kappa = calibration(
        bits,
        joules,
        users=user_count,
        decision_steps=decision_steps,
        time_s=time_s,
    )
    return CalibrationValues(
        setting.label,
        setting.digest,
        eta_ref,
        eta_ref,
        kappa,
        bits,
        joules,
        user_count,
        decision_steps,
        time_s,
        tuple(row.world_domain for row in rows),
        tuple(row.selected_configuration_id for row in rows),
    )


@dataclass(frozen=True)
class CalibrationRegistry:
    """Immutable, complete, one-value-per-setting calibration mapping."""

    values: Mapping[str, CalibrationValues]

    def __post_init__(self) -> None:
        copied = dict(self.values)
        if len(copied) != len(set(copied)):
            raise MCRLContractError("duplicate calibration setting")
        if any(label != value.setting_label for label, value in copied.items()):
            raise MCRLContractError("calibration registry key/label mismatch")
        object.__setattr__(self, "values", MappingProxyType(copied))

    @property
    def digest(self) -> str:
        return digest_payload({label: value.payload() for label, value in sorted(self.values.items())})


def assert_calibration_world_separation(
    *, calibration_tapes: Sequence[ExogenousWorldTape], probe_tapes: Sequence[ExogenousWorldTape]
) -> None:
    calibration_domains = {tape.domain for tape in calibration_tapes}
    probe_domains = {tape.domain for tape in probe_tapes}
    if calibration_domains != set(CALIBRATION_WORLD_DOMAINS) or calibration_domains & probe_domains:
        raise MCRLContractError("calibration worlds are incomplete or overlap probe worlds")
    calibration_clusters = {
        (tape.tle_date, digest_payload([row.payload() for row in tape.user_layout]))
        for tape in calibration_tapes
    }
    probe_clusters = {
        (tape.tle_date, digest_payload([row.payload() for row in tape.user_layout]))
        for tape in probe_tapes
    }
    if calibration_clusters & probe_clusters:
        raise MCRLContractError("calibration and probe providers map to a colliding date/layout cluster")


__all__ = [
    "CalibrationObservation",
    "CalibrationRegistry",
    "CalibrationValues",
    "NominalConfiguration",
    "assert_calibration_prices",
    "assert_calibration_world_separation",
    "freeze_setting_calibration",
    "nominal_greedy_reference",
]
