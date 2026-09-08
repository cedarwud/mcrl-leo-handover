"""Predeclared V0.25 v1.2 physics matrix and shared-tape hooks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal

from mcrl.errors import MCRLContractError

ArchitectureCode = Literal["b", "a-\u03b3", "a\u2032-\u03b3", "a-r", "a\u2032-r"]
IntegrationCode = Literal["0", "T"]
StandbyCode = Literal["0", "f"]
InterruptionCode = Literal["off", "on"]
RateCode = Literal["ACM", "U-cap", "U-margin"]


@dataclass(frozen=True)
class PhysicsSetting:
    architecture: ArchitectureCode
    integration: IntegrationCode
    standby: StandbyCode
    interruption: InterruptionCode
    rate: RateCode

    def __post_init__(self) -> None:
        if self.architecture not in {"b", "a-\u03b3", "a\u2032-\u03b3", "a-r", "a\u2032-r"}:
            raise MCRLContractError("architecture is outside the sealed V0.25 v1.2 matrix")
        if self.integration not in {"0", "T"}:
            raise MCRLContractError("integration must be 0 or T")
        if self.standby not in {"0", "f"}:
            raise MCRLContractError("standby must be 0 or f")
        if self.interruption not in {"off", "on"}:
            raise MCRLContractError("interruption must be off or on")
        if self.rate not in {"ACM", "U-cap", "U-margin"}:
            raise MCRLContractError("rate must be ACM, U-cap, or U-margin")

    @property
    def treatment(self) -> str:
        signature = (self.integration, self.standby, self.interruption, self.rate)
        mapping = {
            ("0", "0", "off", "ACM"): "0",
            ("T", "0", "off", "ACM"): "T",
            ("0", "f", "off", "ACM"): "S",
            ("0", "0", "on", "ACM"): "H",
            ("0", "f", "on", "ACM"): "SH",
            ("0", "0", "off", "U-cap"): "U-cap",
            ("0", "0", "off", "U-margin"): "U-margin",
        }
        try:
            treatment = mapping[signature]
        except KeyError:
            raise MCRLContractError("setting is outside the predeclared fractional matrix") from None
        if treatment.startswith("U") and self.architecture in {"a-r", "a\u2032-r"}:
            raise MCRLContractError("split-U diagnostics apply only to the original architectures")
        return treatment

    @property
    def label(self) -> str:
        return f"{self.architecture}{self.treatment}"

    def payload(self) -> dict[str, str]:
        return {
            "architecture": self.architecture,
            "integration": self.integration,
            "standby": self.standby,
            "interruption": self.interruption,
            "rate": self.rate,
            "treatment": self.treatment,
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()


def _setting(architecture: ArchitectureCode, treatment: str) -> PhysicsSetting:
    terms = {
        "0": ("0", "0", "off", "ACM"),
        "T": ("T", "0", "off", "ACM"),
        "S": ("0", "f", "off", "ACM"),
        "H": ("0", "0", "on", "ACM"),
        "SH": ("0", "f", "on", "ACM"),
        "U-cap": ("0", "0", "off", "U-cap"),
        "U-margin": ("0", "0", "off", "U-margin"),
    }
    integration, standby, interruption, rate = terms[treatment]
    return PhysicsSetting(architecture, integration, standby, interruption, rate)  # type: ignore[arg-type]


# Sealed v1.2 explicit priority order. Its prose count is arithmetically
# inconsistent; the listed amendments enumerate 25 eligible settings plus
# six split-U diagnostics, hence 31 settings until the controller corrects it.
MATRIX_SETTINGS = tuple(
    _setting(architecture, treatment)
    for treatment in ("0", "S", "H", "SH", "T")
    for architecture in ("a-r", "a\u2032-r", "a-\u03b3", "b", "a\u2032-\u03b3")
) + tuple(
    _setting(architecture, treatment)
    for treatment in ("U-cap", "U-margin")
    for architecture in ("a-\u03b3", "b", "a\u2032-\u03b3")
)

# Canonical UTF-8 rendering of the v1.2 amendment's explicit order.  The
# launcher, receipts, and KAT all bind these exact Unicode labels; no ASCII
# alias is allowed to become a scientific cell identity.
SEALED_CELL_LIST_UTF8 = (
    "a-r0\na′-r0\na-γ0\nb0\na′-γ0\n"
    "a-rS\na′-rS\na-γS\nbS\na′-γS\n"
    "a-rH\na′-rH\na-γH\nbH\na′-γH\n"
    "a-rSH\na′-rSH\na-γSH\nbSH\na′-γSH\n"
    "a-rT\na′-rT\na-γT\nbT\na′-γT\n"
    "a-γU-cap\nbU-cap\na′-γU-cap\n"
    "a-γU-margin\nbU-margin\na′-γU-margin"
).encode("utf-8")


def shared_computation_plan(*, q: float | None = None) -> dict[str, object]:
    """The simulator-inert ``--estimate`` plan consumed by Track B."""

    if q is not None and q <= 0.0:
        raise MCRLContractError("q must be positive when supplied")
    architectures = ["a-r", "a\u2032-r", "a-\u03b3", "b", "a\u2032-\u03b3"]
    equivalents = len(architectures) * (1 + 47)
    core_hours = equivalents * (302.0 * 4.0 / 3600.0)
    return {
        "schema": "mcrl-v025-physics-shared-computation-plan-v1.2",
        "architectures": architectures,
        "physical_tapes_per_architecture": {"snapshot": 1, "integrated_subintervals": 47},
        "shared_physical_equivalents": equivalents,
        "reference_core_hours": core_hours,
        "q": q,
        "estimated_core_hours": None if q is None else core_hours * q,
        "rescore_from_integrated_tape": ["T", "S", "H", "SH", "U-cap", "U-margin"],
        "settings": [
            {"label": setting.label, "digest": setting.digest, **setting.payload()}
            for setting in MATRIX_SETTINGS
        ],
        "settings_count": len(MATRIX_SETTINGS),
        "cell_list_utf8_sha256": hashlib.sha256(SEALED_CELL_LIST_UTF8).hexdigest(),
        "primary_eligible_settings_count_from_explicit_list": 25,
        "diagnostic_settings_count": 6,
        "test_split_opened": False,
        "training": False,
        "all_neutral_control_label": "ALL_NEUTRAL_CONTROL",
    }


__all__ = [
    "MATRIX_SETTINGS",
    "SEALED_CELL_LIST_UTF8",
    "PhysicsSetting",
    "shared_computation_plan",
]
