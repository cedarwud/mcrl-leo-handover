"""3GPP TS 38.331 event D2 satellite selection (SDD §3.2, F4, W-04).

Event D2 (NTN) has two entering conditions and two leaving conditions::

    D2-1  Ml1 − Hys > Thresh1     serving link has become too long
    D2-2  Ml2 + Hys < Thresh2     a candidate has come close enough
    D2-3  Ml1 + Hys < Thresh1     (leaving)
    D2-4  Ml2 − Hys > Thresh2     (leaving)

``Ml1``/``Ml2`` are the distances from the UE to the serving and candidate
reference locations.  **This baseline uses only the candidate side**
(D2-2 / D2-4), per SDD §3.2: the full event, serving condition included, is
reserved for the rule-based non-RL control group of decision C4.
:func:`serving_condition_entering` implements that half so C4 has it, but
nothing in the baseline path calls it.

Interpretation choices, all **S**-level and all disclosed
--------------------------------------------------------
``Ml2`` is the **slant range** UE→satellite.  TS 38.331 says "moving
reference location" without fixing it; slant range is what F4's own
thresholds were derived from, and reproducing that derivation exactly
(``slant_range_for_elevation(25, 550) = 1123.3 km``,
``(15, 550) = 1518.0 km`` against F4's 1123 and 1518) confirms the reading.

``TTT`` counts **elapsed** steps since the entering condition first held
continuously, and eligibility needs ``elapsed >= ttt_steps``.  Counting
*satisfying* steps instead would make ``TTT = 1`` a no-op, since the first
satisfying step would already qualify; 3GPP's timer only expires after the
condition has held for the full duration.

The latch is a Schmitt trigger: entry at ``Thresh2 − Hys``, release at
``Thresh2 + Hys``, so a satellite hovering at the threshold does not
chatter.  This hysteresis is F4's D2 hysteresis and is unrelated to the
slot-assignment hysteresis SDD §4A.3 removed.

Per-satellite state is keyed by **NORAD id** and survives a satellite
dropping out of the four-slot window, per the §4A.6 r7 rule: anything
per-satellite and stateful binds to identity, or it becomes hidden history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .action_contract import SatelliteCandidate
from .constants import R_E_KM, TIME_STEP_S

THRESH2_SWEEP_KM: tuple[float, ...] = (900.0, 1000.0, 1100.0, 1200.0, 1300.0)
"""**S** — F4 makes ``Thresh2`` the sweep axis of the results figures."""


def slant_range_for_elevation(elevation_deg: float, altitude_km: float) -> float:
    """Slant range to a satellite at a given elevation and altitude, km."""
    orbit_radius = R_E_KM + altitude_km
    sin_elevation = math.sin(math.radians(elevation_deg))
    return -R_E_KM * sin_elevation + math.sqrt(
        (R_E_KM * sin_elevation) ** 2 + orbit_radius**2 - R_E_KM**2
    )


def elevation_for_slant_range(slant_km: float, altitude_km: float) -> float:
    """Inverse of :func:`slant_range_for_elevation`, degrees."""
    if slant_km <= 0.0:
        raise ValueError("slant range must be positive")
    orbit_radius = R_E_KM + altitude_km
    sin_elevation = (orbit_radius**2 - R_E_KM**2 - slant_km**2) / (
        2.0 * R_E_KM * slant_km
    )
    return math.degrees(math.asin(np.clip(sin_elevation, -1.0, 1.0)))


@dataclass(frozen=True)
class D2Config:
    """Frozen D2 parameters (SDD F4).  All **S** — TS 38.331 gives no values."""

    thresh1_km: float = 1500.0
    """Serving-side threshold.  **C4 only**; unused on the baseline path."""

    thresh2_km: float = 1100.0
    """Candidate-side threshold, and the sweep axis of the results figures.

    Disclosure must quote the **measured** elevation it corresponds to:
    ≈ 21.8° at the corpus's 485 km median visible altitude, not the 25°
    that F4 computed at an assumed 550 km (author ruling, 2026-08-22).
    """

    hysteresis_km: float = 50.0
    ttt_steps: int = 1
    """3GPP's discrete TTT set has 640 ms; one 1 s slot is the nearest step."""

    min_altitude_km: float = 300.0
    """**S** — floor that excludes re-entering objects from candidacy.

    The corpus contains healthy-propagating Starlink down to 156 km, and an
    SGP4 error code does not catch them: they propagate fine near their own
    epoch.  300 km sits below every operational Starlink shell (the lowest
    is ~340 km) and above re-entry, so it excludes 0.43% of the catalogue
    and **zero** of the satellites visible above 10°.
    """

    time_step_s: float = TIME_STEP_S

    @property
    def warmup_steps(self) -> int:
        """Steps the tracker must be primed for **before** a decision step.

        A D2 latch reflects ongoing measurement; it does not come into
        existence when an episode does.  Starting an episode with cold
        latches would leave every user with an empty mask at step 0, which
        under PATCH P-03 drops the transition — 10% of a ``H = 10`` episode,
        instantly past the §4A.5a(4) outage ceiling, and for a reason that
        is an artefact of the episode boundary rather than the geometry.

        Priming is **not** a vacuum-first-step violation (P-8): it settles
        D2 latches only.  The handover ledger stays empty, so step 0 is
        still ``Ψ = 0`` with no phantom ``t−1`` action.
        """
        return max(self.ttt_steps, 1)

    def __post_init__(self) -> None:
        if self.thresh2_km <= 0.0 or self.thresh1_km <= 0.0:
            raise ValueError("thresholds must be positive")
        if self.hysteresis_km < 0.0:
            raise ValueError("hysteresis must be non-negative")
        if self.hysteresis_km >= self.thresh2_km:
            raise MCRLContractError(
                "hysteresis must be smaller than Thresh2, otherwise the entry "
                "threshold is non-positive and nothing can ever qualify"
            )
        if self.ttt_steps < 0:
            raise ValueError("ttt_steps must be >= 0")

    @property
    def entry_threshold_km(self) -> float:
        """D2-2: ``Ml2 + Hys < Thresh2``."""
        return self.thresh2_km - self.hysteresis_km

    @property
    def release_threshold_km(self) -> float:
        """D2-4: ``Ml2 − Hys > Thresh2``."""
        return self.thresh2_km + self.hysteresis_km

    def elevation_disclosure(self, altitude_km: float) -> dict[str, float]:
        """The elevation each threshold corresponds to at one altitude."""
        return {
            "altitude_km": altitude_km,
            "thresh1_elevation_deg": elevation_for_slant_range(
                self.thresh1_km, altitude_km
            ),
            "thresh2_elevation_deg": elevation_for_slant_range(
                self.thresh2_km, altitude_km
            ),
            "entry_elevation_deg": elevation_for_slant_range(
                self.entry_threshold_km, altitude_km
            ),
            "release_elevation_deg": elevation_for_slant_range(
                self.release_threshold_km, altitude_km
            ),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "event": "3GPP-TS-38.331-D2",
            "baseline_uses": "candidate-side only (D2-2 / D2-4)",
            "thresh1_km": self.thresh1_km,
            "thresh2_km": self.thresh2_km,
            "thresh2_sweep_km": list(THRESH2_SWEEP_KM),
            "hysteresis_km": self.hysteresis_km,
            "ttt_steps": self.ttt_steps,
            "ttt_seconds": self.ttt_steps * self.time_step_s,
            "min_altitude_km": self.min_altitude_km,
            "ml2_definition": "slant range UE to satellite",
        }


def serving_condition_entering(
    serving_slant_km: np.ndarray, config: D2Config
) -> np.ndarray:
    """D2-1, ``Ml1 − Hys > Thresh1``.  **For C4 only — not on the baseline path.**

    SDD §3.2 keeps the full event (serving condition included) for the
    rule-based non-RL control group.  Wiring this into baseline eligibility
    would change what the baseline is.
    """
    return np.asarray(serving_slant_km, dtype=np.float64) - config.hysteresis_km > (
        config.thresh1_km
    )


@dataclass(frozen=True)
class D2Snapshot:
    """One step's candidate state for every user and tracked satellite."""

    norad_ids: np.ndarray
    """``(S,)`` the tracked universe, fixed for the episode."""
    eligible: np.ndarray
    """``(U, S)`` bool — latched and above the altitude floor."""
    margin_km: np.ndarray
    """``(U, S)`` ``Thresh2 − Ml2``; larger is better, negative is outside."""
    ttt_elapsed: np.ndarray
    """``(U, S)`` steps the entering condition has held continuously."""
    range_rate_km_s: np.ndarray
    """``(U, S)`` signed; negative approaching."""

    def candidates_for_user(self, uid: int) -> list[SatelliteCandidate]:
        """Rows for ``mcrl.env.action_contract.assign_satellite_slots``.

        Only eligible satellites are returned: an ineligible one carries no
        slot and no state the contract needs.
        """
        indices = np.flatnonzero(self.eligible[uid])
        return [
            SatelliteCandidate(
                norad_id=int(self.norad_ids[index]),
                eligible=True,
                margin_km=float(self.margin_km[uid, index]),
                radial_rate_km_s=float(self.range_rate_km_s[uid, index]),
                ttt_counter=int(self.ttt_elapsed[uid, index]),
            )
            for index in indices.tolist()
        ]

    @property
    def eligible_counts(self) -> np.ndarray:
        return self.eligible.sum(axis=1)


class D2Tracker:
    """Per-user, per-NORAD D2 latches over a fixed satellite universe.

    The universe is the screened satellite set for the episode, which is far
    larger than the four slots.  That is deliberate: §4A.6 requires the
    per-satellite state to persist while a satellite is temporarily outside
    the window, because it may re-enter and its latch is history.
    """

    def __init__(
        self,
        norad_ids: np.ndarray,
        num_users: int,
        config: D2Config | None = None,
    ) -> None:
        self.config = config or D2Config()
        self.norad_ids = np.asarray(norad_ids, dtype=np.int64)
        if self.norad_ids.ndim != 1 or self.norad_ids.size == 0:
            raise MCRLContractError("norad_ids must be a non-empty 1-D array")
        if len(set(self.norad_ids.tolist())) != self.norad_ids.size:
            raise MCRLContractError("norad_ids must be unique")
        if num_users < 1:
            raise ValueError("num_users must be >= 1")
        self.num_users = int(num_users)
        self._index = {
            int(norad): column for column, norad in enumerate(self.norad_ids.tolist())
        }
        self.reset()

    def reset(self) -> None:
        shape = (self.num_users, self.norad_ids.size)
        self._latched = np.zeros(shape, dtype=bool)
        # An explicit flag, not a negative sentinel: warm-up runs at negative
        # step indices, which a "-1 means unset" encoding would swallow.
        self._condition_active = np.zeros(shape, dtype=bool)
        self._condition_started = np.zeros(shape, dtype=np.int64)
        self._ttt_elapsed = np.zeros(shape, dtype=np.int64)
        self._steps_seen = 0
        self._primed = False

    @property
    def primed(self) -> bool:
        return self._primed

    def prime(
        self,
        *,
        slant_range_km: np.ndarray,
        altitude_km: np.ndarray,
        range_rate_km_s: np.ndarray,
    ) -> None:
        """Settle the latches over the warm-up window before step 0.

        Arrays are ``(U, S, W)`` / ``(S, W)`` / ``(U, S, W)`` covering the
        ``W = config.warmup_steps`` steps immediately **before** the
        episode's first decision step; warm-up steps use negative step
        indices so the TTT arithmetic is continuous across the boundary.
        """
        window = self.config.warmup_steps
        slant = np.asarray(slant_range_km, dtype=np.float64)
        if slant.ndim != 3 or slant.shape[2] < window:
            raise MCRLContractError(
                f"prime() needs at least {window} warm-up steps, got "
                f"{slant.shape[2] if slant.ndim == 3 else slant.ndim}"
            )
        altitude = np.asarray(altitude_km, dtype=np.float64)
        rate = np.asarray(range_rate_km_s, dtype=np.float64)
        for offset in range(window, 0, -1):
            column = slant.shape[2] - offset
            self.update(
                -offset,
                slant_range_km=slant[:, :, column],
                altitude_km=altitude[:, column],
                range_rate_km_s=rate[:, :, column],
            )
        self._primed = True

    def column_for(self, norad_id: int) -> int:
        try:
            return self._index[int(norad_id)]
        except KeyError:
            raise MCRLContractError(
                f"NORAD {norad_id} is not in this tracker's universe"
            ) from None

    @property
    def latched(self) -> np.ndarray:
        return self._latched.copy()

    def update(
        self,
        step_index: int,
        *,
        slant_range_km: np.ndarray,
        altitude_km: np.ndarray,
        range_rate_km_s: np.ndarray,
    ) -> D2Snapshot:
        """Advance every latch one step and return this step's candidates.

        ``slant_range_km`` and ``range_rate_km_s`` are ``(U, S)``;
        ``altitude_km`` is ``(S,)`` — altitude is a property of the
        satellite, not of the observer.
        """
        shape = (self.num_users, self.norad_ids.size)
        slant = np.asarray(slant_range_km, dtype=np.float64)
        rate = np.asarray(range_rate_km_s, dtype=np.float64)
        altitude = np.asarray(altitude_km, dtype=np.float64)
        if slant.shape != shape or rate.shape != shape:
            raise MCRLContractError(
                f"slant_range_km and range_rate_km_s must be {shape}"
            )
        if altitude.shape != (self.norad_ids.size,):
            raise MCRLContractError(
                f"altitude_km must be ({self.norad_ids.size},)"
            )
        if not np.all(np.isfinite(slant)) or not np.all(np.isfinite(rate)):
            raise MCRLContractError("D2 measurements must be finite")

        config = self.config
        above_floor = altitude >= config.min_altitude_km  # (S,)

        entering = (slant + config.hysteresis_km < config.thresh2_km) & above_floor
        releasing = slant - config.hysteresis_km > config.thresh2_km

        # TTT: elapsed steps since the entering condition first held.
        started = np.where(
            entering & ~self._condition_active, step_index, self._condition_started
        )
        elapsed = np.where(entering, step_index - started, 0)
        self._condition_active = entering
        self._condition_started = np.where(entering, started, 0)
        self._ttt_elapsed = elapsed

        timer_expired = entering & (elapsed >= config.ttt_steps)
        latched = (self._latched | timer_expired) & ~releasing
        # An object that drops below the altitude floor is never a candidate,
        # latched or not: SGP4 will keep propagating a re-entering satellite.
        latched &= above_floor
        self._latched = latched
        self._steps_seen += 1

        return D2Snapshot(
            norad_ids=self.norad_ids.copy(),
            eligible=latched.copy(),
            margin_km=config.thresh2_km - slant,
            ttt_elapsed=elapsed.copy(),
            range_rate_km_s=rate.copy(),
        )
