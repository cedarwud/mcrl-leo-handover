"""Predeclared 18-cell V0.25 physics matrix and shared-tape hooks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal

from mcrl.errors import MCRLContractError

ArchitectureCode = Literal["b", "a", "a\u2032"]
IntegrationCode = Literal["0", "T"]
StandbyCode = Literal["0", "f"]
InterruptionCode = Literal["off", "on"]
RateCode = Literal["ACM", "U"]


@dataclass(frozen=True)
class PhysicsSetting:
    architecture: ArchitectureCode
    integration: IntegrationCode
    standby: StandbyCode
    interruption: InterruptionCode
    rate: RateCode

    def __post_init__(self) -> None:
        if self.architecture not in {"b", "a", "a\u2032"}:
            raise MCRLContractError("architecture must be b, a, or a-prime")
        if self.integration not in {"0", "T"}:
            raise MCRLContractError("integration must be 0 or T")
        if self.standby not in {"0", "f"}:
            raise MCRLContractError("standby must be 0 or f")
        if self.interruption not in {"off", "on"}:
            raise MCRLContractError("interruption must be off or on")
        if self.rate not in {"ACM", "U"}:
            raise MCRLContractError("rate must be ACM or U")

    @property
    def treatment(self) -> str:
        signature = (self.integration, self.standby, self.interruption, self.rate)
        mapping = {
            ("0", "0", "off", "ACM"): "0",
            ("T", "0", "off", "ACM"): "T",
            ("0", "f", "off", "ACM"): "S",
            ("0", "0", "on", "ACM"): "H",
            ("0", "f", "on", "ACM"): "SH",
            ("0", "0", "off", "U"): "U",
        }
        try:
            return mapping[signature]
        except KeyError:
            raise MCRLContractError("setting is outside the predeclared fractional matrix") from None

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
        "U": ("0", "0", "off", "U"),
    }
    integration, standby, interruption, rate = terms[treatment]
    return PhysicsSetting(architecture, integration, standby, interruption, rate)  # type: ignore[arg-type]


# Sealed priority order.  The seal orders the 15 primary-eligible cells and
# calls U diagnostic-only; the three U cells are appended in sealed architecture
# priority (a, b, a-prime), never interleaved into primary selection.
MATRIX_SETTINGS = tuple(
    _setting(architecture, treatment)
    for treatment in ("0", "S", "H", "SH", "T")
    for architecture in ("a", "b", "a\u2032")
) + tuple(_setting(architecture, "U") for architecture in ("a", "b", "a\u2032"))


def shared_computation_plan(*, q: float | None = None) -> dict[str, object]:
    """The simulator-inert ``--estimate`` plan consumed by Track B."""

    if q is not None and q <= 0.0:
        raise MCRLContractError("q must be positive when supplied")
    equivalents = 3 * (1 + 47)
    core_hours = equivalents * (302.0 * 4.0 / 3600.0)
    return {
        "schema": "mcrl-v025-physics-shared-computation-plan-v1",
        "architectures": ["a", "b", "a\u2032"],
        "physical_tapes_per_architecture": {"snapshot": 1, "integrated_subintervals": 47},
        "shared_physical_equivalents": equivalents,
        "reference_core_hours": core_hours,
        "q": q,
        "estimated_core_hours": None if q is None else core_hours * q,
        "rescore_from_integrated_tape": ["S", "H", "SH", "U"],
        "settings": [
            {"label": setting.label, "digest": setting.digest, **setting.payload()}
            for setting in MATRIX_SETTINGS
        ],
        "settings_count": len(MATRIX_SETTINGS),
        "test_split_opened": False,
        "training": False,
        "all_neutral_control_label": "ALL_NEUTRAL_CONTROL",
    }


__all__ = ["MATRIX_SETTINGS", "PhysicsSetting", "shared_computation_plan"]
