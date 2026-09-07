"""Runtime ordering gate for a C2 V0.3 pre-outcome forecast.

The mathematical certificate can bind exact payloads, but hashes alone do not
show that the forecast was completed before the live environment outcome.  A
``PreoutcomeForecastGate`` owns that small temporal boundary: it snapshots the
live RNG, executes the detached forecast callback, proves that the live RNG did
not advance, and only then permits exactly one live-step callback.

The gate is deliberately ignorant of the satellite environment.  The runtime
adapter supplies a read-only RNG-state snapshot and callbacks; this module
supplies the fail-closed order and an immutable receipt.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, TypeVar

import c2_temporal_fork_core as core
import c2_temporal_fork_forecast_adapter as forecast


T = TypeVar("T")


class C2ChronologyError(core.C2LeakageError):
    """The runtime crossed or could not prove the pre-outcome boundary."""


@dataclass(frozen=True)
class PreoutcomeForecastReceipt:
    schema: str
    option_id: str
    anchor_sha256: str
    live_rng_before_sha256: str
    live_rng_after_forecast_sha256: str
    forecast_rng_sha256: str
    forecast_request_sha256: str
    forecast_payload_sha256: str
    forecast_started_ns: int
    forecast_completed_ns: int
    live_step_started_ns: int
    live_step_completed_ns: int
    forecast_sequence: tuple[str, ...]
    live_rng_unchanged_during_forecast: bool
    claim_ceiling: str = "ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY"


class PreoutcomeForecastGate:
    """Single-use state machine: anchor -> forecast -> one live outcome."""

    # V2 binds the V0.3B hold-while-legal release-policy lineage.  Keeping the
    # receipt schema distinct prevents a fixed-hold chronology from being
    # replayed as a support-expiry chronology.
    SCHEMA = "c2-v03-preoutcome-chronology-receipt-v2"

    def __init__(
        self,
        *,
        anchor_payload: Mapping[str, Any],
        live_rng_state: Callable[[], Mapping[str, Any]],
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if not isinstance(anchor_payload, Mapping):
            raise C2ChronologyError("anchor_payload must be a mapping")
        if not callable(live_rng_state):
            raise C2ChronologyError("live_rng_state must be callable")
        if not callable(clock_ns):
            raise C2ChronologyError("clock_ns must be callable")
        self._anchor_payload = copy.deepcopy(dict(anchor_payload))
        self._anchor_sha256 = forecast.canonical_payload_sha256(
            self._anchor_payload
        )
        self._live_rng_state = live_rng_state
        self._clock_ns = clock_ns
        self._phase = "anchor"
        self._build: forecast.AuthoritativeForecastBuild | None = None
        self._live_before_sha256: str | None = None
        self._live_after_forecast_sha256: str | None = None
        self._forecast_started_ns: int | None = None
        self._forecast_completed_ns: int | None = None

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def anchor_payload(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._anchor_payload)

    def _snapshot_live_rng(self) -> tuple[Mapping[str, Any], str]:
        value = self._live_rng_state()
        if not isinstance(value, Mapping):
            raise C2ChronologyError("live RNG snapshot must be a mapping")
        copied = copy.deepcopy(dict(value))
        return copied, forecast.canonical_payload_sha256(copied)

    def run_forecast(
        self,
        producer: Callable[
            [Mapping[str, Any], Mapping[str, Any]],
            forecast.AuthoritativeForecastBuild,
        ],
    ) -> forecast.AuthoritativeForecastBuild:
        """Complete one detached forecast without advancing the live RNG.

        The producer receives defensive copies of the anchor payload and the
        captured live RNG *state*, never the live ``Generator`` object.
        """

        if self._phase != "anchor":
            raise C2ChronologyError("forecast may run exactly once at the anchor")
        if not callable(producer):
            raise C2ChronologyError("forecast producer must be callable")
        live_state, before = self._snapshot_live_rng()
        self._forecast_started_ns = int(self._clock_ns())
        try:
            built = producer(
                copy.deepcopy(self._anchor_payload), copy.deepcopy(live_state)
            )
        except Exception:
            self._phase = "failed"
            raise
        self._forecast_completed_ns = int(self._clock_ns())
        if not isinstance(built, forecast.AuthoritativeForecastBuild):
            self._phase = "failed"
            raise C2ChronologyError(
                "producer did not return AuthoritativeForecastBuild"
            )
        _after_state, after = self._snapshot_live_rng()
        authority = built.authority
        if after != before:
            self._phase = "failed"
            raise C2ChronologyError("forecast advanced the live RNG")
        if authority.live_rng_state_sha256 != before:
            self._phase = "failed"
            raise C2ChronologyError(
                "forecast authority is not bound to the captured live RNG"
            )
        if authority.anchor_sha256 != self._anchor_sha256:
            self._phase = "failed"
            raise C2ChronologyError(
                "forecast authority is not bound to the captured anchor"
            )
        if authority.generated_preoutcome is not True:
            self._phase = "failed"
            raise C2ChronologyError("forecast is not marked pre-outcome")
        if self._forecast_completed_ns < self._forecast_started_ns:
            self._phase = "failed"
            raise C2ChronologyError("monotonic clock moved backwards")
        self._build = built
        self._live_before_sha256 = before
        self._live_after_forecast_sha256 = after
        self._phase = "forecast_complete"
        return built

    def run_live_step(
        self, executor: Callable[[], T]
    ) -> tuple[T, PreoutcomeForecastReceipt]:
        """Execute the live outcome only after a valid pre-outcome forecast."""

        if self._phase != "forecast_complete" or self._build is None:
            raise C2ChronologyError(
                "live step requires one completed pre-outcome forecast"
            )
        if not callable(executor):
            raise C2ChronologyError("live-step executor must be callable")
        live_started = int(self._clock_ns())
        if live_started < int(self._forecast_completed_ns):
            self._phase = "failed"
            raise C2ChronologyError("live step began before forecast completion")
        self._phase = "live_running"
        try:
            result = executor()
        except Exception:
            self._phase = "failed"
            raise
        live_completed = int(self._clock_ns())
        if live_completed < live_started:
            self._phase = "failed"
            raise C2ChronologyError("monotonic clock moved backwards")
        authority = self._build.authority
        receipt = PreoutcomeForecastReceipt(
            schema=self.SCHEMA,
            option_id=self._build.certificate.option_id,
            anchor_sha256=self._anchor_sha256,
            live_rng_before_sha256=str(self._live_before_sha256),
            live_rng_after_forecast_sha256=str(
                self._live_after_forecast_sha256
            ),
            forecast_rng_sha256=authority.forecast_rng_state_sha256,
            forecast_request_sha256=authority.forecast_request_sha256,
            forecast_payload_sha256=authority.forecast_payload_sha256,
            forecast_started_ns=int(self._forecast_started_ns),
            forecast_completed_ns=int(self._forecast_completed_ns),
            live_step_started_ns=live_started,
            live_step_completed_ns=live_completed,
            forecast_sequence=(
                "anchor_captured",
                "detached_forecast_started",
                "detached_forecast_completed",
                "live_rng_nonadvancement_verified",
                "live_step_started",
                "live_step_completed",
            ),
            live_rng_unchanged_during_forecast=True,
        )
        self._phase = "closed"
        return result, receipt


__all__ = [
    "C2ChronologyError",
    "PreoutcomeForecastGate",
    "PreoutcomeForecastReceipt",
]
