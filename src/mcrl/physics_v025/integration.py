"""Clock-correct trapezoidal integration and conditional interruption."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Literal, Mapping

from mcrl.errors import MCRLContractError

from .constants_v025 import (
    D2_MEASUREMENT_STEP_S,
    D2_SUBINTERVALS,
    DECISION_INTERVAL_S,
    SAME_SATELLITE_INTERRUPTION_S,
    SATELLITE_CHANGE_INTERRUPTION_S,
)

EventKind = Literal[
    "same_satellite_beam_change",
    "satellite_change",
    "initial_entry",
    "reentry",
]


@dataclass(frozen=True)
class BoundarySample:
    """One D2-boundary value; duplicate times encode a discontinuity."""

    time_s: float
    rate_bps: Mapping[int, float]
    power_w: float
    decoding: Mapping[int, bool]


@dataclass(frozen=True)
class InterruptionEvent:
    user_id: int
    time_s: float
    kind: EventKind


@dataclass(frozen=True)
class IntegrationReceipt:
    bits: dict[int, float]
    joules: float
    decoding_time_s: dict[int, float]
    useful_time_s: dict[int, float]
    event_log: tuple[InterruptionEvent, ...]


def _validate_samples(samples: tuple[BoundarySample, ...]) -> None:
    if len(samples) < 2:
        raise MCRLContractError("trapezoidal integration needs at least two samples")
    previous = -math.inf
    users = set(samples[0].rate_bps)
    for sample in samples:
        if not math.isfinite(sample.time_s) or sample.time_s < previous:
            raise MCRLContractError("sample times must be finite and nondecreasing")
        if set(sample.rate_bps) != users or set(sample.decoding) != users:
            raise MCRLContractError("every boundary must cover the same user identities")
        if not math.isfinite(sample.power_w) or sample.power_w < 0.0:
            raise MCRLContractError("boundary power must be finite and nonnegative")
        if any(not math.isfinite(rate) or rate < 0.0 for rate in sample.rate_bps.values()):
            raise MCRLContractError("boundary rates must be finite and nonnegative")
        previous = sample.time_s


def _blackouts(
    events: Iterable[InterruptionEvent],
    *,
    start_s: float,
    end_s: float,
) -> tuple[dict[int, tuple[tuple[float, float], ...]], tuple[InterruptionEvent, ...]]:
    logged = tuple(sorted(events, key=lambda event: (event.time_s, event.user_id, event.kind)))
    intervals: dict[int, list[tuple[float, float]]] = {}
    for event in logged:
        if event.kind in {"initial_entry", "reentry"}:
            continue
        duration = (
            SAME_SATELLITE_INTERRUPTION_S
            if event.kind == "same_satellite_beam_change"
            else SATELLITE_CHANGE_INTERRUPTION_S
        )
        low = max(start_s, event.time_s)
        high = min(end_s, event.time_s + duration)
        if high > low:
            intervals.setdefault(event.user_id, []).append((low, high))
    merged: dict[int, tuple[tuple[float, float], ...]] = {}
    for user, rows in intervals.items():
        result: list[list[float]] = []
        for low, high in sorted(rows):
            if result and low <= result[-1][1]:
                result[-1][1] = max(result[-1][1], high)
            else:
                result.append([low, high])
        merged[user] = tuple((low, high) for low, high in result)
    return merged, logged


def _linear_integral(y0: float, y1: float, t0: float, t1: float, low: float, high: float) -> float:
    if high <= low or t1 <= t0:
        return 0.0
    slope = (y1 - y0) / (t1 - t0)
    a = low - t0
    b = high - t0
    return y0 * (b - a) + 0.5 * slope * (b * b - a * a)


def integrate_trapezoidal(
    samples: Iterable[BoundarySample],
    *,
    interruptions: Iterable[InterruptionEvent] = (),
    interruption_enabled: bool = False,
) -> IntegrationReceipt:
    """Integrate boundary values, never interpolating across duplicate-time jumps."""

    points = tuple(samples)
    _validate_samples(points)
    start = points[0].time_s
    end = points[-1].time_s
    blackouts, log = _blackouts(interruptions, start_s=start, end_s=end)
    users = tuple(points[0].rate_bps)
    bits = {user: 0.0 for user in users}
    decoding = {user: 0.0 for user in users}
    useful = {user: 0.0 for user in users}
    joules = 0.0
    for left, right in zip(points, points[1:]):
        t0, t1 = left.time_s, right.time_s
        if t1 == t0:
            continue
        duration = t1 - t0
        joules += 0.5 * (left.power_w + right.power_w) * duration
        for user in users:
            decoded_integral = 0.5 * (float(left.decoding[user]) + float(right.decoding[user])) * duration
            decoding[user] += decoded_integral
            excluded: list[tuple[float, float]] = []
            if interruption_enabled:
                for low, high in blackouts.get(user, ()):
                    cut_low, cut_high = max(t0, low), min(t1, high)
                    if cut_high > cut_low:
                        excluded.append((cut_low, cut_high))
            full_bits = 0.5 * (left.rate_bps[user] + right.rate_bps[user]) * duration
            removed_bits = math.fsum(
                _linear_integral(left.rate_bps[user], right.rate_bps[user], t0, t1, low, high)
                for low, high in excluded
            )
            removed_time = math.fsum(
                _linear_integral(
                    float(left.decoding[user]),
                    float(right.decoding[user]),
                    t0,
                    t1,
                    low,
                    high,
                )
                for low, high in excluded
            )
            bits[user] += full_bits - removed_bits
            useful[user] += decoded_integral - removed_time
    return IntegrationReceipt(bits, joules, decoding, useful, log)


def integrate_47_subintervals(
    samples: Iterable[BoundarySample],
    *,
    discontinuities: Iterable[BoundarySample] = (),
    interruptions: Iterable[InterruptionEvent] = (),
    interruption_enabled: bool = False,
) -> IntegrationReceipt:
    """Require exactly t plus the next 47 0.640-s D2 boundary samples."""

    points = tuple(samples)
    if len(points) != D2_SUBINTERVALS + 1:
        raise MCRLContractError("treatment 0 needs exactly 48 boundary samples")
    for index, point in enumerate(points):
        expected = points[0].time_s + index * D2_MEASUREMENT_STEP_S
        if not math.isclose(point.time_s, expected, rel_tol=0.0, abs_tol=1.0e-12):
            raise MCRLContractError("D2 boundary tape is not on the frozen 0.640-s clock")
    if not math.isclose(points[-1].time_s - points[0].time_s, DECISION_INTERVAL_S, rel_tol=0.0, abs_tol=1.0e-12):
        raise MCRLContractError("integration tape does not span 30.08 seconds")
    extra = tuple(discontinuities)
    if any(point.time_s <= points[0].time_s or point.time_s >= points[-1].time_s for point in extra):
        raise MCRLContractError("event discontinuities must lie strictly inside the step")
    # Callers encode left/right event limits as two samples at the same time.
    counts: dict[float, int] = {}
    for point in extra:
        counts[point.time_s] = counts.get(point.time_s, 0) + 1
    if any(count != 2 for count in counts.values()):
        raise MCRLContractError("each event discontinuity needs exactly left/right samples")
    # When an event lands on a scheduled D2 sample, its explicit left/right
    # limits replace that single regular point.  Keeping all three would still
    # interpolate the preceding interval to the regular (right-limit) value.
    merged = tuple(
        sorted(
            tuple(point for point in points if point.time_s not in counts) + extra,
            key=lambda point: point.time_s,
        )
    )
    return integrate_trapezoidal(
        merged,
        interruptions=interruptions,
        interruption_enabled=interruption_enabled,
    )


def snapshot_left(sample: BoundarySample, *, end_s: float) -> IntegrationReceipt:
    """Treatment T: decision-time (left) snapshot held to the supplied end."""

    duration = end_s - sample.time_s
    if not math.isfinite(duration) or duration <= 0.0:
        raise MCRLContractError("left snapshot end must follow the decision instant")
    bits = {user: rate * duration for user, rate in sample.rate_bps.items()}
    decoding = {user: float(value) * duration for user, value in sample.decoding.items()}
    return IntegrationReceipt(bits, sample.power_w * duration, decoding, dict(decoding), ())


def snapshot_terminal(sample: BoundarySample, *, start_s: float) -> IntegrationReceipt:
    """Compatibility helper for the superseded terminal-snapshot interpretation.

    V0.25 matrix treatment T does not call this helper after the controller's
    stage-1 decision record; it remains named so older stage-1 imports fail no
    more broadly than necessary.
    """

    duration = sample.time_s - start_s
    if not math.isclose(duration, DECISION_INTERVAL_S, rel_tol=0.0, abs_tol=1.0e-12):
        raise MCRLContractError("terminal snapshot must be at t+30.08")
    bits = {user: rate * duration for user, rate in sample.rate_bps.items()}
    decoding = {user: float(value) * duration for user, value in sample.decoding.items()}
    return IntegrationReceipt(bits, sample.power_w * duration, decoding, dict(decoding), ())


__all__ = [
    "BoundarySample",
    "IntegrationReceipt",
    "InterruptionEvent",
    "integrate_47_subintervals",
    "integrate_trapezoidal",
    "snapshot_left",
    "snapshot_terminal",
]
