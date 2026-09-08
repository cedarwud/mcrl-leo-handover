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


@dataclass(frozen=True)
class SealedRunSetting:
    """A sealed executable setting, including prospective regime overrides."""

    run_id: str
    base_cell: str
    claim_classification: Literal["PRIMARY", "EXPLORATORY_SENSITIVITY"]
    regime: str
    rate_target_bps: float = 50_000_000.0
    user_count: int = 100
    circuit_power_per_active_chain_w: float = 0.338
    c2_horizon_offsets: int = 3

    def __post_init__(self) -> None:
        if self.base_cell not in {row.label for row in MATRIX_SETTINGS}:
            raise MCRLContractError("sealed run setting names an unknown base cell")
        if self.claim_classification == "PRIMARY" and self.run_id != "a-r0":
            raise MCRLContractError("a-r0 is the only primary run setting")
        if self.claim_classification != "PRIMARY" and self.run_id == "a-r0":
            raise MCRLContractError("a-r0 cannot be exploratory")
        if self.rate_target_bps <= 0 or self.user_count <= 0:
            raise MCRLContractError("regime rate target and user count must be positive")
        if self.circuit_power_per_active_chain_w < 0:
            raise MCRLContractError("regime circuit power must be nonnegative")
        if self.c2_horizon_offsets not in {1, 2, 3}:
            raise MCRLContractError("C2 horizon must contain the first 1, 2, or 3 offsets")

    def payload(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "base_cell": self.base_cell,
            "claim_classification": self.claim_classification,
            "regime": self.regime,
            "rate_target_bps": self.rate_target_bps,
            "user_count": self.user_count,
            "circuit_power_per_active_chain_w": self.circuit_power_per_active_chain_w,
            "c2_horizon_offsets": self.c2_horizon_offsets,
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()


PRIMARY_RUN_SETTING = SealedRunSetting("a-r0", "a-r0", "PRIMARY", "R0")
REGIME_RUN_SETTINGS = (
    SealedRunSetting("R1", "a-r0", "EXPLORATORY_SENSITIVITY", "R1", rate_target_bps=100_000_000.0),
    SealedRunSetting("R2", "a-r0", "EXPLORATORY_SENSITIVITY", "R2", user_count=150),
    SealedRunSetting("R3", "a-r0", "EXPLORATORY_SENSITIVITY", "R3", circuit_power_per_active_chain_w=1.0),
    SealedRunSetting("R4", "a-r0", "EXPLORATORY_SENSITIVITY", "R4", circuit_power_per_active_chain_w=0.1),
    SealedRunSetting("R7", "a-r0", "EXPLORATORY_SENSITIVITY", "R7", rate_target_bps=25_000_000.0),
)
C2_HORIZON_RUN_SETTINGS = (
    SealedRunSetting("C2-H1", "a-r0", "EXPLORATORY_SENSITIVITY", "C2-H1", c2_horizon_offsets=1),
    SealedRunSetting("C2-H2", "a-r0", "EXPLORATORY_SENSITIVITY", "C2-H2", c2_horizon_offsets=2),
)


def run_setting_for(run_id: str) -> SealedRunSetting:
    """Resolve the CLI setting identity without aliasing scientific labels."""

    if run_id == "a-r0":
        return PRIMARY_RUN_SETTING
    for row in REGIME_RUN_SETTINGS + C2_HORIZON_RUN_SETTINGS:
        if row.run_id == run_id:
            return row
    for setting in MATRIX_SETTINGS:
        if setting.label == run_id:
            regime = "R5" if run_id == "a′-r0" else "R6" if run_id == "a-γ0" else "MATRIX"
            return SealedRunSetting(
                run_id,
                run_id,
                "EXPLORATORY_SENSITIVITY",
                regime,
            )
    raise MCRLContractError(f"unknown sealed run setting: {run_id}")


# Enumeration preserves the sealed 31-cell list, then appends only genuinely
# new settings.  R5/R6 are aliases of existing matrix cells and are not run twice.
ALL_SEALED_RUN_SETTINGS = tuple(run_setting_for(row.label) for row in MATRIX_SETTINGS) + (
    *REGIME_RUN_SETTINGS,
    *C2_HORIZON_RUN_SETTINGS,
)
LAUNCH_RUN_ORDER = (
    PRIMARY_RUN_SETTING,
    *REGIME_RUN_SETTINGS[:4],
    run_setting_for("a′-r0"),
    run_setting_for("a-γ0"),
    run_setting_for("R7"),
    *C2_HORIZON_RUN_SETTINGS,
    *tuple(
        run_setting_for(row.label)
        for row in MATRIX_SETTINGS
        if row.label not in {"a-r0", "a′-r0", "a-γ0"}
    ),
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
        "sealed_run_settings": [row.payload() | {"digest": row.digest} for row in ALL_SEALED_RUN_SETTINGS],
        "sealed_run_settings_count": len(ALL_SEALED_RUN_SETTINGS),
        "launch_run_order": [row.run_id for row in LAUNCH_RUN_ORDER],
        "only_primary_run_id": "a-r0",
        "cell_list_utf8_sha256": hashlib.sha256(SEALED_CELL_LIST_UTF8).hexdigest(),
        "primary_eligible_settings_count_from_explicit_list": 25,
        "diagnostic_settings_count": 6,
        "test_split_opened": False,
        "training": False,
        "all_neutral_control_label": "ALL_NEUTRAL_CONTROL",
    }


__all__ = [
    "MATRIX_SETTINGS",
    "ALL_SEALED_RUN_SETTINGS",
    "C2_HORIZON_RUN_SETTINGS",
    "LAUNCH_RUN_ORDER",
    "PRIMARY_RUN_SETTING",
    "REGIME_RUN_SETTINGS",
    "SEALED_CELL_LIST_UTF8",
    "PhysicsSetting",
    "SealedRunSetting",
    "run_setting_for",
    "shared_computation_plan",
]
