"""Pure adjudication seam for a future V0.18 learned-Q3 gate.

This module intentionally performs no learning and opens no data.  It accepts
only already-produced validation summaries and a contract hash whose status
was frozen before outcomes were opened.  Thresholds are required constructor
arguments: no result-dependent defaults are hidden in the gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any


GATE_ALGORITHM = "multi-catfish-mcrl-v018-relational-zr-c3-100-update-gate"
GATE_VERSION = 1
REQUIRED_UPDATES = 100
FROZEN_STATUS = "FROZEN_BEFORE_OUTCOME"


class RelationalGateError(ValueError):
    """A learner-gate contract or summary is malformed."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalGateError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _finite(value: object, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalGateError(f"{field} must be finite") from error
    if not math.isfinite(number):
        raise RelationalGateError(f"{field} must be finite")
    return number


def canonical_sha256(payload: object) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalGateError("payload is not finite canonical JSON") from error
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class RelationalZRC3GateConfig:
    """All acceptance choices fixed before any validation outcome is opened."""

    contract_sha256: str
    contract_status: str
    min_mean_skill: float
    min_positive_initializations: int
    min_supported_change_rate: float
    min_supported_initializations: int
    required_updates: int = REQUIRED_UPDATES

    def __post_init__(self) -> None:
        _digest(self.contract_sha256, field="contract_sha256")
        if self.contract_status != FROZEN_STATUS:
            raise RelationalGateError(
                f"contract_status must be {FROZEN_STATUS!r} before the gate runs"
            )
        if self.required_updates != REQUIRED_UPDATES:
            raise RelationalGateError("the draft gate is fixed at exactly 100 updates")
        _finite(self.min_mean_skill, field="min_mean_skill")
        _finite(self.min_supported_change_rate, field="min_supported_change_rate")
        if not 0.0 <= float(self.min_supported_change_rate) <= 1.0:
            raise RelationalGateError("min_supported_change_rate must lie in [0, 1]")
        for field in ("min_positive_initializations", "min_supported_initializations"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise RelationalGateError(f"{field} must be a positive integer")


@dataclass(frozen=True)
class RelationalZRC3GateResult:
    """Stable, JSON-friendly result of a fixed-summary adjudication."""

    algorithm: str
    version: int
    decision: str
    passed: bool
    contract_sha256: str
    required_updates: int
    initialization_count: int
    mean_validation_skill: float
    positive_initializations: int
    mean_supported_change_rate: float
    supported_initializations: int
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _summary(report: object, *, label: str, required_updates: int) -> tuple[float, float]:
    if not isinstance(report, Mapping):
        raise RelationalGateError(f"validation summary {label!r} must be a mapping")
    update_count = report.get("update_count")
    if isinstance(update_count, bool) or not isinstance(update_count, int):
        raise RelationalGateError(f"validation summary {label!r} has invalid update_count")
    if update_count != required_updates:
        raise RelationalGateError(
            f"validation summary {label!r} must be exactly {required_updates} updates"
        )
    skill = _finite(report.get("validation_skill"), field=f"{label}.validation_skill")
    supported = _finite(
        report.get("supported_change_rate"),
        field=f"{label}.supported_change_rate",
    )
    if not 0.0 <= supported <= 1.0:
        raise RelationalGateError(
            f"validation summary {label!r} supported_change_rate must lie in [0, 1]"
        )
    return skill, supported


def adjudicate_100_update_gate(
    reports: Mapping[str, Mapping[str, Any]],
    config: RelationalZRC3GateConfig,
) -> RelationalZRC3GateResult:
    """Adjudicate fixed validation summaries without changing any source choice.

    A report is *positive* when its validation skill is at least the explicit
    ``min_mean_skill`` threshold, and *supported* when its supported-change
    rate is at least the explicit rate threshold.  The gate passes only when
    the pooled mean skill and both minimum initialization counts pass.  This
    is a pure arithmetic decision; it cannot select worlds, seeds, thresholds,
    or a target after seeing outcomes.
    """

    if not isinstance(config, RelationalZRC3GateConfig):
        raise RelationalGateError("config must be RelationalZRC3GateConfig")
    if not isinstance(reports, Mapping) or not reports:
        raise RelationalGateError("reports must be a nonempty mapping")
    values = tuple(
        _summary(report, label=str(label), required_updates=config.required_updates)
        for label, report in reports.items()
    )
    skills = tuple(skill for skill, _supported in values)
    supported_rates = tuple(rate for _skill, rate in values)
    positive = sum(skill >= float(config.min_mean_skill) for skill in skills)
    supported = sum(
        rate >= float(config.min_supported_change_rate) for rate in supported_rates
    )
    mean_skill = float(sum(skills) / len(skills))
    mean_supported = float(sum(supported_rates) / len(supported_rates))
    passed = (
        mean_skill >= float(config.min_mean_skill)
        and positive >= config.min_positive_initializations
        and supported >= config.min_supported_initializations
    )
    if passed:
        reason = "all frozen 100-update gate predicates passed"
        decision = "PASS_LEARNER_GATE"
    else:
        reason = "one or more frozen 100-update gate predicates failed"
        decision = "STOP_LEARNER_GATE"
    return RelationalZRC3GateResult(
        algorithm=GATE_ALGORITHM,
        version=GATE_VERSION,
        decision=decision,
        passed=passed,
        contract_sha256=config.contract_sha256,
        required_updates=config.required_updates,
        initialization_count=len(values),
        mean_validation_skill=mean_skill,
        positive_initializations=positive,
        mean_supported_change_rate=mean_supported,
        supported_initializations=supported,
        reason=reason,
    )


__all__ = [
    "FROZEN_STATUS",
    "GATE_ALGORITHM",
    "GATE_VERSION",
    "REQUIRED_UPDATES",
    "RelationalGateError",
    "RelationalZRC3GateConfig",
    "RelationalZRC3GateResult",
    "adjudicate_100_update_gate",
    "canonical_sha256",
]
