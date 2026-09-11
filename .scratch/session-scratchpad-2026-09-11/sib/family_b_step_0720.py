"""Family-B sibling step environment for SDD 08 READINESS-ONLY builds.

The environment is additive and does not subclass or edit the sealed
``StepEnvironment`` path. It implements the SDD 08 Earth-fixed-cell action
space: 28 trainer slots = 4 area-window satellite ranks times each user's
reset-bound own cell plus six canonical axial neighbors. Initial assignment is
``(slot 0, own cell c0)``. Slot identity is rank; physical identity is
``(window_sat_id, cell_id)``.

Observation convention: active slot beams expose realized SINR; inactive but
unmasked slot beams expose prospective N=1 SNR using the candidate satellite as
the serving direction, with no interference terms; masked slots expose 0.0.
At retrain a sibling trainer override must resolve the G1 per-user slot read as
``slot_power_w[uid, slot]``. The sealed ``modqn.py`` hook is not edited, and the
result object deliberately omits the live raw physical-array attributes so
cross-surface misuse fails loudly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.random import Generator

from . import family_b_geometry as geo
from .step_types import (
    ActionMask,
    HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE,
    PowerSurfaceConfig,
    RewardComponents,
    UserState,
    _HOBS_ACTIVE_TX_EE_EPSILON_P_W,
)


def spawn_family_b_rng_domains(seed: int) -> tuple[np.random.SeedSequence, ...]:
    """Return train/env/mobility/phase SeedSequence domains for Family-B.

    SDD 08 retires the old ``(s, s, s)`` seed triplet on the new path:
    ``SeedSequence(s).spawn(4)`` maps to train, env, mobility, and phase domains.
    """
    return tuple(np.random.SeedSequence(int(seed)).spawn(4))


@dataclass(frozen=True)
class FamilyBEnvConfig:
    """Single-source config for the Family-B env.

    ``k_cap`` defaults to 3; prereg candidates are ``{3,4,5}``, and the final
    value is selected by acceptance-mode L3-7, not hand-picked.
    """

    constellation_total: int = 180
    constellation_planes: int = 9
    constellation_phasing: int = 1
    constellation_inclination_deg: float = 53.0
    constellation_altitude_km: float = 780.0
    constellation_speed_km_s: float = 7.4
    rotating_earth: bool = True

    l_w: int = 4
    eps_min_deg: float = 15.0

    cell_radius_km: float = field(default_factory=geo.default_cell_radius_km)
    guard_rings: int = 1

    phase_support_s: float = 86_400.0
    eval_phase_grid: int = 288
    qos_floor_bps: float = 1.0e7
    fading_enabled: bool = True
    rician_k_db: float = 20.0
    k_cap: int = 3
    cell_coloring: str = "(q-r) mod 3"
    rx_pattern_mode: str = "directional-32-25log"

    noise_psd_dbm_hz: float = -174.0
    noise_figure_db: float = 1.2
    bandwidth_hz: float = 500.0e6

    atmos_form: str = "corrected_lossy"
    theta_3db_deg: float = 3.32
    g0_linear: float = 1.0e4

    num_users: int = 100
    slot_duration_s: float = 1.0
    episode_duration_s: float = 10.0
    user_speed_kmh: float = 30.0
    area_ew_km: float = 200.0
    area_ns_km: float = 90.0
    phi1: float = 0.5
    phi2: float = 1.0
    offset_scale_km: float = 100.0

    @property
    def steps_per_episode(self) -> int:
        return int(round(self.episode_duration_s / self.slot_duration_s))

    @property
    def b_alloc_hz(self) -> float:
        return self.bandwidth_hz / 3.0

    def __post_init__(self) -> None:
        if self.constellation_total % self.constellation_planes != 0:
            raise ValueError("constellation_total must be divisible by constellation_planes")
        if self.l_w < 1:
            raise ValueError("l_w must be >= 1")
        if self.num_users < 1:
            raise ValueError("num_users must be >= 1")
        if self.slot_duration_s <= 0.0 or self.episode_duration_s <= 0.0:
            raise ValueError("slot and episode durations must be positive")
        if self.steps_per_episode != 10:
            raise ValueError("Family-B Phase A requires 10 steps per episode")
        if self.eps_min_deg <= 0.0:
            raise ValueError("eps_min_deg must be positive")
        if self.guard_rings < 1:
            raise ValueError("guard_rings must be >= 1")
        if self.k_cap < 1:
            raise ValueError("k_cap must be >= 1")
        if self.cell_coloring != "(q-r) mod 3":
            raise ValueError("only the SDD 08 cell coloring is supported")
        if self.rx_pattern_mode not in {"directional-32-25log", "isotropic"}:
            raise ValueError("rx_pattern_mode must be directional-32-25log or isotropic")
        if self.atmos_form not in {"corrected_lossy", "zenith_over_sin"}:
            raise ValueError("unsupported atmospheric form")
        if not (0.0 < self.phi1 < self.phi2):
            raise ValueError("expected 0 < phi1 < phi2")
        derived_radius = self.constellation_altitude_km * math.tan(
            math.radians(self.theta_3db_deg) / 2.0
        )
        if not math.isclose(self.cell_radius_km, derived_radius, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                "cell_radius_km must be derived as h*tan(theta_3dB/2), "
                f"got {self.cell_radius_km!r}, expected {derived_radius!r}"
            )
        if not math.isclose(self.cell_radius_km, 22.62, rel_tol=0.0, abs_tol=0.02):
            raise ValueError("default cell radius must stay near 22.62 km")
        fixed_defaults = {
            "constellation_altitude_km": (self.constellation_altitude_km, geo.ALT_KM),
            "constellation_speed_km_s": (self.constellation_speed_km_s, geo.SAT_SPEED_KM_S),
            "area_ew_km": (self.area_ew_km, geo.AREA_EW_KM),
            "area_ns_km": (self.area_ns_km, geo.AREA_NS_KM),
        }
        for name, (value, expected) in fixed_defaults.items():
            if not math.isclose(float(value), float(expected), rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"{name} must match the SDD 08 geometry port default")


@dataclass
class FamilyBStepResult:
    """Step output with distinct slot and physical surfaces.

    Physical arrays are available only through shape-asserting ``phys_*``
    accessors. The object intentionally omits the live global raw-array names.
    At retrain, a sibling trainer override resolves the per-user slot read via
    ``slot_power_w[uid, slot]``; ``modqn.py`` remains sealed.
    """

    time_s: float
    step_index: int
    done: bool
    user_states: list[UserState]
    action_masks: list[ActionMask]
    rewards: list[RewardComponents]
    slot_power_w: np.ndarray
    slot_cell_ids: np.ndarray
    window_sat_ids: np.ndarray
    cap_bump_count: int
    cap_bump_user_flags: np.ndarray
    n_phi1: int
    n_phi2: int
    n_physical_beams: int
    _phys_power_w: np.ndarray
    _phys_throughputs: np.ndarray
    _phys_loads: np.ndarray
    _phys_ids: list[tuple[int, int]]

    def _assert_phys(self, arr: np.ndarray) -> np.ndarray:
        if self.n_physical_beams == 28:
            raise AssertionError("physical beam surface must not be 28-slot shaped")
        if len(arr) != self.n_physical_beams:
            raise AssertionError(
                f"physical surface length {len(arr)} != {self.n_physical_beams}"
            )
        return arr

    def phys_beam_power_w(self) -> np.ndarray:
        return self._assert_phys(self._phys_power_w.copy())

    def phys_beam_throughputs(self) -> np.ndarray:
        return self._assert_phys(self._phys_throughputs.copy())

    def phys_beam_loads(self) -> np.ndarray:
        return self._assert_phys(self._phys_loads.copy())

    def phys_beam_ids(self) -> list[tuple[int, int]]:
        if self.n_physical_beams == 28:
            raise AssertionError("physical beam surface must not be 28-slot shaped")
        if len(self._phys_ids) != self.n_physical_beams:
            raise AssertionError(
                f"physical id length {len(self._phys_ids)} != {self.n_physical_beams}"
            )
        return list(self._phys_ids)


class _FamilyBOrbitShim:
    def __init__(self, env: "FamilyBStepEnvironment") -> None:
        self._env = env

    @property
    def num_satellites(self) -> int:
        return self._env.config.l_w

    def all_satellites(self, t_s: float) -> np.ndarray:
        return self._env._window_sats_ecef_at(float(t_s))


class _FamilyBBeamShim:
    @property
    def num_beams(self) -> int:
        return 7


@dataclass(frozen=True)
class _StepSurfaces:
    states: list[UserState]
    masks: list[ActionMask]
    user_throughputs: np.ndarray
    physical_throughputs_lc: np.ndarray
    active_loads_lc: np.ndarray
    power_lc: np.ndarray
    slot_power_w: np.ndarray
    slot_cell_ids: np.ndarray
    cap_bump_flags: np.ndarray
    mask_valid: np.ndarray


class FamilyBStepEnvironment:
    """Sibling Family-B environment with SDD 08 slot/physical semantics."""

    def __init__(self, config: FamilyBEnvConfig | None = None) -> None:
        self.config = config or FamilyBEnvConfig()
        self.grid = geo.build_cell_grid(
            cell_radius_km=self.config.cell_radius_km,
            guard_rings=self.config.guard_rings,
        )
        self.pointable_cell_ids = geo.pointable_cell_ids(self.grid)
        self.n_physical_beams = self.config.l_w * int(self.pointable_cell_ids.size)
        if self.n_physical_beams == 28:
            raise AssertionError("physical surface must not collapse to the 28-slot surface")
        if self._is_default_grid() and self.n_physical_beams != 156:
            raise AssertionError(
                f"default Family-B physical surface must be 4x39=156, got {self.n_physical_beams}"
            )

        self._elements = geo.walker_elements(
            self.config.constellation_total,
            self.config.constellation_planes,
            self.config.constellation_phasing,
            self.config.constellation_inclination_deg,
        )
        self._cell_centers_ecef = geo.local_km_to_ecef(self.grid.centers_km)
        self._pointable_index = {int(c): i for i, c in enumerate(self.pointable_cell_ids)}
        self._orbit = _FamilyBOrbitShim(self)
        self._beam = _FamilyBBeamShim()
        self._power_surface_cfg = PowerSurfaceConfig(
            hobs_power_surface_mode=HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE,
            inactive_beam_policy="zero-w",
            active_base_power_w=geo.P_BASE_W,
            load_scale_power_w=geo.P_SCALE_W,
            load_exponent=geo.P_EXP,
            max_power_w=geo.P_MAX_W,
            total_power_budget_w=geo.SAT_AGG_CAP_W,
            sinr_intra_satellite_interference=True,
            antenna_gain_in_channel=True,
            antenna_gain_g0_linear=self.config.g0_linear,
            antenna_gain_theta_3db_rad=math.radians(self.config.theta_3db_deg),
        )

        self._t_s = 0.0
        self._step_index = 0
        self._window_sat_ids = np.zeros(self.config.l_w, dtype=np.int64)
        self._user_xy_km = np.zeros((self.config.num_users, 2), dtype=np.float64)
        self._user_headings_rad = np.zeros(self.config.num_users, dtype=np.float64)
        self._own_cell_ids = np.zeros(self.config.num_users, dtype=np.int64)
        self._neighborhood_cell_ids = np.zeros((self.config.num_users, 7), dtype=np.int64)
        self._assignments_slot = np.zeros(self.config.num_users, dtype=np.int64)
        self._fading_streams: list[Generator] = []
        self._has_reset = False

    def _is_default_grid(self) -> bool:
        return (
            self.config.l_w == 4
            and math.isclose(self.config.cell_radius_km, geo.default_cell_radius_km(), abs_tol=1e-12)
            and self.config.guard_rings == 1
        )

    @property
    def window_sat_ids(self) -> np.ndarray:
        return self._window_sat_ids.copy()

    def reset(
        self,
        rng: Generator,
        mobility_rng: Generator | None = None,
        *,
        initial_time_s: float,
    ) -> tuple[list[UserState], list[ActionMask], dict[str, Any]]:
        if not math.isfinite(initial_time_s) or initial_time_s < 0.0:
            raise ValueError("initial_time_s must be finite and >= 0")
        self._t_s = float(initial_time_s)
        self._step_index = 0

        all_sats = self._all_sats_ecef_at(self._t_s)
        window = geo.select_window(all_sats, self.config.eps_min_deg, self.config.l_w)
        if window.size != self.config.l_w:
            raise RuntimeError(
                f"expected {self.config.l_w} eligible window satellites, got {window.size}"
            )
        self._window_sat_ids = window.astype(np.int64)

        mrng = mobility_rng or rng
        self._user_xy_km = np.column_stack(
            [
                mrng.uniform(
                    -self.config.area_ew_km / 2.0,
                    self.config.area_ew_km / 2.0,
                    size=self.config.num_users,
                ),
                mrng.uniform(
                    -self.config.area_ns_km / 2.0,
                    self.config.area_ns_km / 2.0,
                    size=self.config.num_users,
                ),
            ]
        ).astype(np.float64)
        stride = 2.3998277
        self._user_headings_rad = (
            np.arange(self.config.num_users, dtype=np.float64) * stride
        ) % (2.0 * math.pi)
        self._own_cell_ids = geo.own_cell_ids(self._user_xy_km, self.grid).astype(np.int64)
        self._neighborhood_cell_ids = geo.neighborhood_cell_ids(self._own_cell_ids, self.grid)
        if (self._neighborhood_cell_ids < 0).any():
            raise AssertionError("reset-bound Family-B neighborhoods must be complete")
        self._assignments_slot = np.zeros(self.config.num_users, dtype=np.int64)

        child_seeds = rng.integers(0, np.iinfo(np.uint64).max, size=self.config.num_users, dtype=np.uint64)
        self._fading_streams = [np.random.default_rng(int(seed)) for seed in child_seeds]
        self._has_reset = True

        surfaces = self._build_surfaces()
        diag = {
            "family": "FamilyB",
            "initial_time_s": self._t_s,
            "window_sat_ids": self._window_sat_ids.copy(),
            "cell_count": self.grid.count,
            "area_serving_count": int(np.sum(self.grid.serves_area)),
            "pointable_count": int(self.pointable_cell_ids.size),
            "n_physical_beams": self.n_physical_beams,
            "initial_assignment": "(slot 0, own cell c0)",
        }
        return surfaces.states, surfaces.masks, diag

    def step(self, actions: np.ndarray, rng: Generator) -> FamilyBStepResult:
        del rng
        self._require_reset()
        action_arr = np.asarray(actions, dtype=np.int64)
        if action_arr.shape != (self.config.num_users,):
            raise ValueError(
                f"Expected actions shape ({self.config.num_users},), got {action_arr.shape}"
            )
        if ((action_arr < 0) | (action_arr >= self.config.l_w * 7)).any():
            raise ValueError("Family-B actions must be integers in [0, 28)")

        prev_sat_ids, prev_cell_ids = self._assignment_physical_ids(self._assignments_slot)

        self._t_s += self.config.slot_duration_s
        self._step_index += 1
        self._move_users()
        self._assignments_slot = action_arr.copy()

        surfaces = self._build_surfaces()
        cur_sat_ids, cur_cell_ids = self._assignment_physical_ids(self._assignments_slot)
        rewards, n_phi1, n_phi2 = self._compute_rewards(
            prev_sat_ids=prev_sat_ids,
            prev_cell_ids=prev_cell_ids,
            cur_sat_ids=cur_sat_ids,
            cur_cell_ids=cur_cell_ids,
            user_throughputs=surfaces.user_throughputs,
            physical_throughputs_lc=surfaces.physical_throughputs_lc,
            active_loads_lc=surfaces.active_loads_lc,
            power_lc=surfaces.power_lc,
        )

        phys_power, phys_thr, phys_loads, phys_ids = self._physical_surface_arrays(
            surfaces.power_lc,
            surfaces.physical_throughputs_lc,
            surfaces.active_loads_lc,
        )
        done = self._step_index >= self.config.steps_per_episode
        return FamilyBStepResult(
            time_s=float(self._t_s),
            step_index=int(self._step_index),
            done=done,
            user_states=surfaces.states,
            action_masks=surfaces.masks,
            rewards=rewards,
            slot_power_w=surfaces.slot_power_w,
            slot_cell_ids=surfaces.slot_cell_ids,
            window_sat_ids=self._window_sat_ids.copy(),
            cap_bump_count=int(np.sum(surfaces.cap_bump_flags)),
            cap_bump_user_flags=surfaces.cap_bump_flags.copy(),
            n_phi1=n_phi1,
            n_phi2=n_phi2,
            n_physical_beams=self.n_physical_beams,
            _phys_power_w=phys_power,
            _phys_throughputs=phys_thr,
            _phys_loads=phys_loads,
            _phys_ids=phys_ids,
        )

    def _require_reset(self) -> None:
        if not self._has_reset:
            raise RuntimeError("FamilyBStepEnvironment.reset must be called before step")

    def _all_sats_ecef_at(self, t_s: float) -> np.ndarray:
        t = np.array([float(t_s)], dtype=np.float64)
        sats = geo.propagate_ecef(
            self._elements,
            t,
            rotating_earth=self.config.rotating_earth,
        )
        return sats[:, 0, :]

    def _window_sats_ecef_at(self, t_s: float) -> np.ndarray:
        all_sats = self._all_sats_ecef_at(float(t_s))
        return all_sats[self._window_sat_ids]

    def _move_users(self) -> None:
        distance_km = self.config.user_speed_kmh / 3600.0 * self.config.slot_duration_s
        step = np.column_stack(
            [np.cos(self._user_headings_rad), np.sin(self._user_headings_rad)]
        ) * distance_km
        self._user_xy_km = self._user_xy_km + step
        half_w = self.config.area_ew_km / 2.0
        half_h = self.config.area_ns_km / 2.0
        self._reflect_axis(axis=0, half_extent=half_w)
        self._reflect_axis(axis=1, half_extent=half_h)

    def _reflect_axis(self, *, axis: int, half_extent: float) -> None:
        high = self._user_xy_km[:, axis] > half_extent
        if high.any():
            self._user_xy_km[high, axis] = 2.0 * half_extent - self._user_xy_km[high, axis]
            if axis == 0:
                self._user_headings_rad[high] = math.pi - self._user_headings_rad[high]
            else:
                self._user_headings_rad[high] = -self._user_headings_rad[high]
        low = self._user_xy_km[:, axis] < -half_extent
        if low.any():
            self._user_xy_km[low, axis] = -2.0 * half_extent - self._user_xy_km[low, axis]
            if axis == 0:
                self._user_headings_rad[low] = math.pi - self._user_headings_rad[low]
            else:
                self._user_headings_rad[low] = -self._user_headings_rad[low]
        self._user_headings_rad %= 2.0 * math.pi

    def _assignment_physical_ids(self, actions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        slot_ids = actions // 7
        local_ids = actions % 7
        sat_ids = self._window_sat_ids[slot_ids]
        cell_ids = self._neighborhood_cell_ids[np.arange(self.config.num_users), local_ids]
        return sat_ids.astype(np.int64), cell_ids.astype(np.int64)

    def _slot_cell_ids(self) -> np.ndarray:
        return np.tile(self._neighborhood_cell_ids, (1, self.config.l_w))

    def _slot_sat_ids(self) -> np.ndarray:
        return np.repeat(self._window_sat_ids, 7)

    def _build_surfaces(self) -> _StepSurfaces:
        U = self.config.num_users
        L = self.config.l_w
        C = self.grid.count
        slot_actions = self._assignments_slot.copy()
        slot_ids = slot_actions // 7
        local_ids = slot_actions % 7
        slot_cell_ids = self._slot_cell_ids()
        action_cell_ids = slot_cell_ids[np.arange(U), slot_actions]

        user_ecef = geo.local_km_to_ecef(self._user_xy_km)
        sats_ecef = self._window_sats_ecef_at(self._t_s)
        masks_bool = self._build_masks(user_ecef, sats_ecef, slot_cell_ids)

        demand = np.zeros((L, C), dtype=np.float64)
        for uid in range(U):
            demand[int(slot_ids[uid]), int(action_cell_ids[uid])] += 1.0
        active = np.zeros((L, C), dtype=bool)
        for l in range(L):
            demanded_cells = np.flatnonzero(demand[l] > 0.0)
            if demanded_cells.size == 0:
                continue
            order = sorted(
                (int(c) for c in demanded_cells),
                key=lambda c: (-float(demand[l, c]), c),
            )
            active[l, order[: self.config.k_cap]] = True
        active_loads = np.where(active, demand, 0.0)
        power_lc = geo.apply_satellite_aggregate_cap(geo.beam_power_w(active_loads))

        cap_bump = np.zeros(U, dtype=bool)
        for uid in range(U):
            cap_bump[uid] = not active[int(slot_ids[uid]), int(action_cell_ids[uid])]

        fading = self._draw_fading()
        channel_quality, slot_power_w, slot_loads, user_thr, phys_thr = (
            self._compute_slot_channels(
                user_ecef=user_ecef,
                sats_ecef=sats_ecef,
                slot_cell_ids=slot_cell_ids,
                masks_bool=masks_bool,
                active=active,
                active_loads=active_loads,
                power_lc=power_lc,
                fading=fading,
            )
        )

        states: list[UserState] = []
        masks: list[ActionMask] = []
        for uid in range(U):
            access = np.zeros(L * 7, dtype=np.float32)
            action = int(self._assignments_slot[uid])
            if 0 <= action < L * 7:
                access[action] = 1.0
            offsets = self.grid.centers_km[slot_cell_ids[uid]] - self._user_xy_km[uid][None, :]
            states.append(
                UserState(
                    access_vector=access,
                    channel_quality=channel_quality[uid].astype(np.float32),
                    beam_offsets=offsets.astype(np.float32),
                    beam_loads=slot_loads[uid].astype(np.float32),
                )
            )
            masks.append(ActionMask(mask=masks_bool[uid].copy()))

        return _StepSurfaces(
            states=states,
            masks=masks,
            user_throughputs=user_thr,
            physical_throughputs_lc=phys_thr,
            active_loads_lc=active_loads,
            power_lc=power_lc,
            slot_power_w=slot_power_w,
            slot_cell_ids=slot_cell_ids.astype(np.int64),
            cap_bump_flags=cap_bump,
            mask_valid=masks_bool[np.arange(U), slot_actions],
        )

    def _build_masks(
        self,
        user_ecef: np.ndarray,
        sats_ecef: np.ndarray,
        slot_cell_ids: np.ndarray,
    ) -> np.ndarray:
        U = self.config.num_users
        L = self.config.l_w
        d_us = np.linalg.norm(user_ecef[:, None, :] - sats_ecef[None, :, :], axis=2)
        up = user_ecef / np.linalg.norm(user_ecef, axis=1, keepdims=True)
        sin_el = ((sats_ecef[None, :, :] - user_ecef[:, None, :]) * up[:, None, :]).sum(axis=2) / d_us
        elev = np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))
        visible = elev >= self.config.eps_min_deg

        off_nadir = geo.off_nadir_deg(sats_ecef[:, None, :], self._cell_centers_ecef[None, :, :])
        conform = off_nadir <= geo.S1528_OFF_NADIR_LIMIT_DEG

        masks = np.zeros((U, L * 7), dtype=bool)
        for l in range(L):
            base = l * 7
            cells = slot_cell_ids[:, base : base + 7]
            masks[:, base : base + 7] = visible[:, l][:, None] & conform[l, cells]
        return masks

    def _draw_fading(self) -> np.ndarray:
        U = self.config.num_users
        L = self.config.l_w
        if not self.config.fading_enabled:
            return np.ones((U, L), dtype=np.float64)
        k_lin = 10.0 ** (self.config.rician_k_db / 10.0)
        los = math.sqrt(k_lin / (k_lin + 1.0))
        scat = math.sqrt(1.0 / (2.0 * (k_lin + 1.0)))
        out = np.empty((U, L), dtype=np.float64)
        for uid, stream in enumerate(self._fading_streams):
            real_imag = stream.normal(size=(L, 2))
            h = los + scat * real_imag[:, 0] + 1j * scat * real_imag[:, 1]
            out[uid] = np.abs(h) ** 2
        return out

    def _rx_gain_for_sep(self, sep_deg: np.ndarray) -> np.ndarray:
        if self.config.rx_pattern_mode == "directional-32-25log":
            return geo.rx_gain_linear(sep_deg)
        return np.full_like(sep_deg, 10.0 ** (geo.RX_GAIN_SERVING_DBI / 10.0), dtype=np.float64)

    def _noise_power_w(self) -> float:
        n0_w_hz = 10.0 ** ((self.config.noise_psd_dbm_hz - 30.0) / 10.0)
        return n0_w_hz * self.config.b_alloc_hz * 10.0 ** (self.config.noise_figure_db / 10.0)

    def _compute_slot_channels(
        self,
        *,
        user_ecef: np.ndarray,
        sats_ecef: np.ndarray,
        slot_cell_ids: np.ndarray,
        masks_bool: np.ndarray,
        active: np.ndarray,
        active_loads: np.ndarray,
        power_lc: np.ndarray,
        fading: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        U = self.config.num_users
        L = self.config.l_w
        C = self.grid.count
        noise_w = self._noise_power_w()

        d_us = np.linalg.norm(user_ecef[:, None, :] - sats_ecef[None, :, :], axis=2)
        up = user_ecef / np.linalg.norm(user_ecef, axis=1, keepdims=True)
        sin_el = ((sats_ecef[None, :, :] - user_ecef[:, None, :]) * up[:, None, :]).sum(axis=2) / d_us
        elev = np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))
        fspl = geo.fspl_linear(d_us)
        atmo = 10.0 ** (-geo.atmos_loss_db(d_us, elev, self.config.atmos_form) / 10.0)

        sep = geo.angle_between_deg(
            user_ecef[:, None, None, :],
            sats_ecef[None, :, None, :],
            sats_ecef[None, None, :, :],
        )
        rx_by_serving = self._rx_gain_for_sep(sep)
        for l in range(L):
            rx_by_serving[:, l, l] = 10.0 ** (geo.RX_GAIN_SERVING_DBI / 10.0)

        active_pairs = np.argwhere(active)
        active_l = active_pairs[:, 0].astype(np.int64) if active_pairs.size else np.zeros(0, dtype=np.int64)
        active_c = active_pairs[:, 1].astype(np.int64) if active_pairs.size else np.zeros(0, dtype=np.int64)
        active_colors = self.grid.colors[active_c] if active_c.size else np.zeros(0, dtype=np.int64)
        pair_to_idx = {
            (int(l), int(c)): idx for idx, (l, c) in enumerate(zip(active_l, active_c))
        }

        received_by_serving = np.zeros((U, L, active_l.size), dtype=np.float64)
        if active_l.size:
            theta_active = geo.angle_between_deg(
                sats_ecef[active_l][None, :, :],
                self._cell_centers_ecef[active_c][None, :, :],
                user_ecef[:, None, :],
            )
            g_t_active = geo.gt_linear(theta_active.ravel(), self.config.theta_3db_deg).reshape(theta_active.shape)
            base_power = (
                power_lc[active_l, active_c][None, :]
                * g_t_active
                * fspl[:, active_l]
                * atmo[:, active_l]
                * fading[:, active_l]
            )
            for l_serv in range(L):
                received_by_serving[:, l_serv, :] = (
                    base_power * rx_by_serving[:, l_serv, active_l]
                )

        color_sums = np.zeros((U, L, 3), dtype=np.float64)
        for color in range(3):
            idx = np.flatnonzero(active_colors == color)
            if idx.size:
                color_sums[:, :, color] = received_by_serving[:, :, idx].sum(axis=2)

        slot_quality = np.zeros((U, L * 7), dtype=np.float64)
        slot_power_w = np.zeros((U, L * 7), dtype=np.float64)
        slot_loads = np.zeros((U, L * 7), dtype=np.float64)
        phys_thr = np.zeros((L, C), dtype=np.float64)
        user_thr = np.zeros(U, dtype=np.float64)

        p_one = geo.beam_power_w(np.array([1.0], dtype=np.float64))[0]
        serving_rx = 10.0 ** (geo.RX_GAIN_SERVING_DBI / 10.0)

        for l in range(L):
            base = l * 7
            cells = slot_cell_ids[:, base : base + 7]
            theta = geo.angle_between_deg(
                sats_ecef[l][None, None, :],
                self._cell_centers_ecef[cells],
                user_ecef[:, None, :],
            )
            g_t = geo.gt_linear(theta.ravel(), self.config.theta_3db_deg).reshape(theta.shape)
            prospective = (
                p_one
                * g_t
                * fspl[:, l][:, None]
                * atmo[:, l][:, None]
                * fading[:, l][:, None]
                * serving_rx
                / noise_w
            )
            slot_quality[:, base : base + 7] = prospective
            for local in range(7):
                slot = base + local
                c_vec = cells[:, local]
                colors = self.grid.colors[c_vec]
                co_sum = color_sums[np.arange(U), l, colors]
                signal = np.zeros(U, dtype=np.float64)
                load = np.zeros(U, dtype=np.float64)
                power = np.zeros(U, dtype=np.float64)
                is_active = np.zeros(U, dtype=bool)
                for uid, c in enumerate(c_vec):
                    idx = pair_to_idx.get((l, int(c)))
                    if idx is None:
                        continue
                    is_active[uid] = True
                    signal[uid] = received_by_serving[uid, l, idx]
                    load[uid] = active_loads[l, int(c)]
                    power[uid] = power_lc[l, int(c)]
                interference = np.maximum(co_sum - signal, 0.0)
                sinr = signal / (interference + noise_w)
                slot_quality[is_active, slot] = sinr[is_active]
                slot_loads[:, slot] = np.where(is_active, load, 0.0)
                slot_power_w[:, slot] = np.where(is_active & masks_bool[:, slot], power, 0.0)

        slot_quality = np.where(masks_bool, slot_quality, 0.0)

        action = self._assignments_slot
        action_l = action // 7
        action_c = slot_cell_ids[np.arange(U), action]
        action_valid = masks_bool[np.arange(U), action]
        for uid in range(U):
            l = int(action_l[uid])
            c = int(action_c[uid])
            if not action_valid[uid] or not active[l, c]:
                continue
            load = max(float(active_loads[l, c]), 1.0)
            sinr = float(slot_quality[uid, int(action[uid])])
            thr = self.config.b_alloc_hz / load * math.log2(1.0 + max(sinr, 0.0))
            user_thr[uid] = thr
            phys_thr[l, c] += thr

        return slot_quality, slot_power_w, slot_loads, user_thr, phys_thr

    def _compute_rewards(
        self,
        *,
        prev_sat_ids: np.ndarray,
        prev_cell_ids: np.ndarray,
        cur_sat_ids: np.ndarray,
        cur_cell_ids: np.ndarray,
        user_throughputs: np.ndarray,
        physical_throughputs_lc: np.ndarray,
        active_loads_lc: np.ndarray,
        power_lc: np.ndarray,
    ) -> tuple[list[RewardComponents], int, int]:
        U = self.config.num_users
        active_mask = active_loads_lc > 0.0
        active_thr = physical_throughputs_lc[active_mask]
        gap = 0.0 if active_thr.size < 2 else float(np.max(active_thr) - np.min(active_thr))
        total_user_thr = float(np.sum(user_throughputs, dtype=np.float64))
        total_active_power = float(np.sum(power_lc[active_mask], dtype=np.float64))
        system_ee = total_user_thr / (total_active_power + _HOBS_ACTIVE_TX_EE_EPSILON_P_W)

        rewards: list[RewardComponents] = []
        n_phi1 = 0
        n_phi2 = 0
        action = self._assignments_slot
        action_l = action // 7
        action_c = self._slot_cell_ids()[np.arange(U), action]
        for uid in range(U):
            r2 = self._handover_penalty(
                prev_sat=int(prev_sat_ids[uid]),
                prev_cell=int(prev_cell_ids[uid]),
                cur_sat=int(cur_sat_ids[uid]),
                cur_cell=int(cur_cell_ids[uid]),
            )
            if math.isclose(r2, -self.config.phi1):
                n_phi1 += 1
            elif math.isclose(r2, -self.config.phi2):
                n_phi2 += 1
            l = int(action_l[uid])
            c = int(action_c[uid])
            load = float(active_loads_lc[l, c])
            power = float(power_lc[l, c])
            allocated_power = power / load if load > 0.0 else 0.0
            r1 = float(user_throughputs[uid])
            r1_ee_credit = r1 / allocated_power if allocated_power > 0.0 else 0.0
            r1_beam_ee_credit = r1 / power if power > 0.0 else 0.0
            rewards.append(
                RewardComponents(
                    r1_throughput=r1,
                    r2_handover=r2,
                    r3_load_balance=-(gap / U) if U > 0 else 0.0,
                    r1_energy_efficiency_credit=float(r1_ee_credit),
                    r1_beam_power_efficiency_credit=float(r1_beam_ee_credit),
                    r1_hobs_active_tx_ee=float(system_ee),
                )
            )
        return rewards, n_phi1, n_phi2

    def _handover_penalty(self, *, prev_sat: int, prev_cell: int, cur_sat: int, cur_cell: int) -> float:
        if prev_sat == cur_sat and prev_cell == cur_cell:
            return 0.0
        if prev_sat == cur_sat:
            return -self.config.phi1
        return -self.config.phi2

    def _physical_surface_arrays(
        self,
        power_lc: np.ndarray,
        throughput_lc: np.ndarray,
        loads_lc: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[int, int]]]:
        powers: list[float] = []
        throughputs: list[float] = []
        loads: list[float] = []
        ids: list[tuple[int, int]] = []
        for slot_l, sat_id in enumerate(self._window_sat_ids):
            for cell_id in self.pointable_cell_ids:
                c = int(cell_id)
                powers.append(float(power_lc[slot_l, c]))
                throughputs.append(float(throughput_lc[slot_l, c]))
                loads.append(float(loads_lc[slot_l, c]))
                ids.append((int(sat_id), c))
        return (
            np.asarray(powers, dtype=np.float64),
            np.asarray(throughputs, dtype=np.float64),
            np.asarray(loads, dtype=np.float64),
            ids,
        )

    def _compute_theta_rad_for_user(
        self,
        *,
        uid: int,
        sats: np.ndarray,
        beams_per_satellite: int,
    ) -> np.ndarray:
        """Return slot-space off-axis angle for the G1 reward hook.

        The values are defined for masked slots as well and use the same
        sat->cell-center pointing seam as the channel and interference paths.
        """
        self._require_reset()
        if beams_per_satellite != 7:
            raise ValueError("Family-B exposes 7 slot beams per window satellite")
        if not (0 <= uid < self.config.num_users):
            raise IndexError(uid)
        sats_arr = np.asarray(sats, dtype=np.float64)
        if sats_arr.shape != (self.config.l_w, 3):
            sats_arr = self._window_sats_ecef_at(self._t_s)
        user_ecef = geo.local_km_to_ecef(self._user_xy_km[uid : uid + 1])[0]
        cells = self._slot_cell_ids()[uid].reshape(self.config.l_w, 7)
        theta_deg = np.zeros(self.config.l_w * 7, dtype=np.float64)
        for l in range(self.config.l_w):
            theta_deg[l * 7 : (l + 1) * 7] = geo.angle_between_deg(
                sats_arr[l][None, :],
                self._cell_centers_ecef[cells[l]],
                user_ecef[None, :],
            )
        theta_rad = np.radians(theta_deg)
        if not np.isfinite(theta_rad).all():
            raise AssertionError("Family-B theta hook must never emit NaN/inf")
        return theta_rad


__all__ = [
    "FamilyBEnvConfig",
    "FamilyBStepEnvironment",
    "FamilyBStepResult",
    "spawn_family_b_rng_domains",
]
