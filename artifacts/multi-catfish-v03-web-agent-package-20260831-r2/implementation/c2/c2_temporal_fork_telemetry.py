"""Fail-closed telemetry for the bounded C2 V0.3 carrier.

The primary performance surface is always the Main trajectory.  Its energy
efficiency is a ratio of accumulated useful bits to accumulated joules, never
an average of per-step ratios and never a reward proxy.  C2 opportunity,
forecast cost, option execution, and optimizer dose are recorded separately so
mechanism activity cannot be mistaken for Main-only EE efficacy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

import numpy as np

from mcrl.env.constants import DECISION_STEP_S


SCHEMA = "multi-catfish-c2-v03-run-telemetry-v1"
CLAIM_CEILING = (
    "training-carrier telemetry only; Main ratio-of-sums EE and C2 dose are "
    "descriptive, not an efficacy or Chapter-5 result"
)


class TelemetryContractError(RuntimeError):
    """A required canonical telemetry field is absent or malformed."""


def _finite_nonnegative(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise TelemetryContractError(f"{field_name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TelemetryContractError(f"{field_name} must be finite and nonnegative")
    return result


@dataclass
class MainOutcomeAccumulator:
    """Accumulate canonical Main outcomes without affecting the trajectory."""

    steps: int = 0
    useful_bits: float = 0.0
    energy_j: float = 0.0
    served_user_intervals: int = 0
    user_intervals: int = 0
    reward_sum: np.ndarray = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )

    def observe(self, outcome: Any) -> None:
        energy = getattr(outcome, "energy", None)
        resolution = getattr(outcome, "resolution", None)
        rewards = np.asarray(getattr(outcome, "reward_matrix", None))
        served = np.asarray(getattr(resolution, "served", None))
        if rewards.ndim != 2 or rewards.shape[1] != 3:
            raise TelemetryContractError("Main outcome reward_matrix must be U-by-3")
        if not np.issubdtype(rewards.dtype, np.number) or not np.isfinite(rewards).all():
            raise TelemetryContractError("Main outcome reward_matrix must be finite numeric")
        if served.dtype != np.bool_ or served.ndim != 1 or served.size != rewards.shape[0]:
            raise TelemetryContractError(
                "Main outcome served vector must be Boolean and match reward users"
            )
        throughput_bps = _finite_nonnegative(
            getattr(energy, "system_throughput_bps", None),
            field_name="system_throughput_bps",
        )
        consumed_power_w = _finite_nonnegative(
            getattr(energy, "system_consumed_power_w", None),
            field_name="system_consumed_power_w",
        )
        reported_served = getattr(resolution, "served_count", None)
        if (
            isinstance(reported_served, bool)
            or not isinstance(reported_served, (int, np.integer))
            or int(reported_served) != int(served.sum())
        ):
            raise TelemetryContractError(
                "Main outcome served_count must equal the served vector"
            )
        self.steps += 1
        self.useful_bits += throughput_bps * float(DECISION_STEP_S)
        self.energy_j += consumed_power_w * float(DECISION_STEP_S)
        self.served_user_intervals += int(reported_served)
        self.user_intervals += int(served.size)
        self.reward_sum += rewards.sum(axis=0, dtype=np.float64)

    def snapshot(self) -> dict[str, Any]:
        return {
            "steps": int(self.steps),
            "useful_bits": float(self.useful_bits),
            "energy_j": float(self.energy_j),
            "ratio_of_sums_ee_bits_per_j": (
                float(self.useful_bits / self.energy_j)
                if self.energy_j > 0.0
                else None
            ),
            "served_user_intervals": int(self.served_user_intervals),
            "user_intervals": int(self.user_intervals),
            "served_fraction": (
                float(self.served_user_intervals / self.user_intervals)
                if self.user_intervals > 0
                else None
            ),
            "canonical_reward_sum": self.reward_sum.tolist(),
        }


@dataclass
class C2RunTelemetry:
    """Keep Main performance and C2 mechanism activity on separate ledgers."""

    main: MainOutcomeAccumulator = field(default_factory=MainOutcomeAccumulator)
    schedules: int = 0
    empty_anchor_attempts: int = 0
    scheduled_candidates: int = 0
    certificate_pass: int = 0
    certificate_fail: int = 0
    support_rejection: int = 0
    contract_error: int = 0
    forecast_wall_time_s: float = 0.0
    k0: int = 0
    k1: int = 0
    k_ge_2: int = 0
    options_executed: int = 0
    option_primitive_steps: int = 0
    admitted_options: int = 0
    q2f_updates: int = 0
    joint_commits: int = 0

    def observe_main(self, outcome: Any) -> None:
        self.main.observe(outcome)

    def observe_schedule(
        self,
        diagnostics: Sequence[Mapping[str, Any]],
        *,
        support_count: int,
    ) -> None:
        if isinstance(support_count, bool) or not isinstance(
            support_count, (int, np.integer)
        ):
            raise TelemetryContractError("support_count must be an integer")
        support = int(support_count)
        if support < 0:
            raise TelemetryContractError("support_count must be nonnegative")
        rows = list(diagnostics)
        if not rows:
            if support != 0:
                raise TelemetryContractError(
                    "empty candidate schedule cannot have learned support"
                )
            self.empty_anchor_attempts += 1
            return
        local_counts = {
            "certificate_pass": 0,
            "certificate_fail": 0,
            "support_rejection": 0,
            "contract_error": 0,
        }
        local_wall_time = 0.0
        for row in rows:
            if not isinstance(row, Mapping):
                raise TelemetryContractError("candidate diagnostic must be a mapping")
            elapsed = row.get("elapsed_s", 0.0)
            local_wall_time += _finite_nonnegative(
                elapsed, field_name="candidate elapsed_s"
            )
            if "contract_error" in row:
                local_counts["contract_error"] += 1
            elif "support_rejection" in row:
                local_counts["support_rejection"] += 1
            elif row.get("passed") is True:
                local_counts["certificate_pass"] += 1
            elif row.get("passed") is False:
                local_counts["certificate_fail"] += 1
            else:
                raise TelemetryContractError(
                    "candidate diagnostic has no classifiable outcome"
                )
        if support != local_counts["certificate_pass"]:
            raise TelemetryContractError(
                "selection support_count disagrees with passed certificates"
            )
        self.schedules += 1
        self.scheduled_candidates += len(rows)
        if support == 0:
            self.k0 += 1
        elif support == 1:
            self.k1 += 1
        else:
            self.k_ge_2 += 1
        self.certificate_pass += local_counts["certificate_pass"]
        self.certificate_fail += local_counts["certificate_fail"]
        self.support_rejection += local_counts["support_rejection"]
        self.contract_error += local_counts["contract_error"]
        self.forecast_wall_time_s += local_wall_time

    @staticmethod
    def certificate_pass_for_last_schedule(
        rows: Sequence[Mapping[str, Any]],
    ) -> int:
        return sum(
            1
            for row in rows
            if "contract_error" not in row
            and "support_rejection" not in row
            and row.get("passed") is True
        )

    def observe_execution(self, receipt: Any, unit: Any | None) -> None:
        if unit is None:
            if any(
                bool(getattr(receipt, field_name, False))
                for field_name in ("admitted", "updated", "joint_committed")
            ):
                raise TelemetryContractError(
                    "nonexecuted C2 option cannot carry admission or update dose"
                )
            return
        payloads = tuple(getattr(unit, "committed_payloads", ()))
        if not payloads:
            raise TelemetryContractError("executed C2 option has no primitive payload")
        admitted = bool(getattr(receipt, "admitted", False))
        updated = bool(getattr(receipt, "updated", False))
        committed = bool(getattr(receipt, "joint_committed", False))
        if updated and not admitted:
            raise TelemetryContractError("Q2F update cannot occur without admission")
        if committed and not updated:
            raise TelemetryContractError("joint commit cannot occur without an update")
        self.options_executed += 1
        self.option_primitive_steps += len(payloads)
        self.admitted_options += int(admitted)
        self.q2f_updates += int(updated)
        self.joint_commits += int(committed)

    def snapshot(self) -> dict[str, Any]:
        main = self.main.snapshot()
        return {
            "schema": SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "main": main,
            "c2": {
                "schedules": int(self.schedules),
                "empty_anchor_attempts": int(self.empty_anchor_attempts),
                "scheduled_candidates": int(self.scheduled_candidates),
                "candidate_outcomes": {
                    "certificate_pass": int(self.certificate_pass),
                    "certificate_fail": int(self.certificate_fail),
                    "support_rejection": int(self.support_rejection),
                    "contract_error": int(self.contract_error),
                },
                "choice_counts": {
                    "K0": int(self.k0),
                    "K1": int(self.k1),
                    "K>=2": int(self.k_ge_2),
                },
                "forecast_wall_time_s": float(self.forecast_wall_time_s),
                "options_executed": int(self.options_executed),
                "option_primitive_steps": int(self.option_primitive_steps),
                "admitted_options": int(self.admitted_options),
                "q2f_updates": int(self.q2f_updates),
                "joint_commits": int(self.joint_commits),
                "joint_commit_per_main_step": (
                    float(self.joint_commits / main["steps"])
                    if main["steps"] > 0
                    else None
                ),
            },
        }


class OutcomeTelemetryEnvironment:
    """Transparent environment observer for the unchanged baseline trainer."""

    def __init__(self, environment: Any, telemetry: C2RunTelemetry) -> None:
        self._telemetry_environment = environment
        self._telemetry = telemetry

    def __getattr__(self, name: str) -> Any:
        return getattr(self._telemetry_environment, name)

    def step(self, actions: Any, rng: Any) -> Any:
        result = self._telemetry_environment.step(actions, rng)
        self._telemetry.observe_main(self._telemetry_environment.last_outcome)
        return result


__all__ = [
    "CLAIM_CEILING",
    "C2RunTelemetry",
    "MainOutcomeAccumulator",
    "OutcomeTelemetryEnvironment",
    "SCHEMA",
    "TelemetryContractError",
]
