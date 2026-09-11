"""Family-B Earth-fixed-cell geometry and link-budget helpers.

Src port of ``analysis/env-rebuild-sdd08/family_b_geometry.py``;
parity-tested. The module is self-contained under ``src/`` and deliberately
does not import from ``analysis/``. Model conventions follow SDD 08:
spherical Earth with ``R_E = 6371.0 km``; ``km_per_deg = pi * R_E / 180``;
Walker-delta 180/9/1 by default; rotating Earth; pointy-top axial cells with
``R_cell = h * tan(theta_3dB / 2)``; area-global window ranked by area-center
slant range; sealed ``approved_transmit_gain_linear`` for every serving and
interference transmit-gain calculation; D4b' directional receive envelope;
positive-dB atmospheric loss forms; REP-04h beam power; and REP-04z
per-satellite aggregate cap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..runtime.angle_aware_ee import approved_transmit_gain_linear

R_E_KM = 6371.0
ALT_KM = 780.0
ORBIT_RADIUS_KM = R_E_KM + ALT_KM
SAT_SPEED_KM_S = 7.4
MU_KM3_S2 = 398600.4418
OMEGA_E_RAD_S = 7.2921159e-5
AREA_CENTER_LAT_DEG = 40.0
AREA_CENTER_LON_DEG = 116.0
AREA_EW_KM = 200.0
AREA_NS_KM = 90.0
KM_PER_DEG_LAT = math.pi * R_E_KM / 180.0

THETA_3DB_DEG = 3.32
G0_LINEAR = 1.0e4
RX_GAIN_SERVING_DBI = 35.0
RX_ENVELOPE_FLOOR_DBI = -10.0
CARRIER_FREQ_HZ = 20.0e9
BANDWIDTH_HZ = 500.0e6
B_ALLOC_HZ = BANDWIDTH_HZ / 3.0
NOISE_PSD_DBM_HZ = -174.0
NOISE_FIGURE_DB = 1.2
CHI_DB_PER_KM = 0.05
H_ATM_KM = 10.0
SPEED_OF_LIGHT_M_S = 299_792_458.0

P_BASE_W = 0.25
P_SCALE_W = 0.35
P_EXP = 0.5
P_MAX_W = 10.0
SAT_AGG_CAP_W = 10.0 ** (13.0 / 10.0)

L_W = 4
S1528_OFF_NADIR_LIMIT_DEG = 60.0
EARTH_LIMB_OFF_NADIR_DEG = math.degrees(math.asin(R_E_KM / ORBIT_RADIUS_KM))

AXIAL_NEIGHBOR_DIRS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
)


def noise_power_w(
    bandwidth_hz: float = B_ALLOC_HZ,
    noise_figure_db: float = NOISE_FIGURE_DB,
) -> float:
    """Return sigma^2 = N0 * bandwidth * NF."""
    n0_w_hz = 10.0 ** ((NOISE_PSD_DBM_HZ - 30.0) / 10.0)
    return n0_w_hz * bandwidth_hz * 10.0 ** (noise_figure_db / 10.0)


def default_cell_radius_km(theta_3db_deg: float = THETA_3DB_DEG) -> float:
    """REP-025 sizing convention: R_cell = h * tan(theta_3dB / 2)."""
    return ALT_KM * math.tan(math.radians(theta_3db_deg) / 2.0)


@dataclass(frozen=True)
class CellGrid:
    """Rectangular-cropped axial hex lattice with guard ring and 3-coloring."""

    cell_radius_km: float
    pitch_km: float
    axial: np.ndarray
    centers_km: np.ndarray
    colors: np.ndarray
    in_area: np.ndarray
    serves_area: np.ndarray
    neighbor_ids: np.ndarray

    @property
    def count(self) -> int:
        return int(self.axial.shape[0])

    def centers_latlon(self) -> np.ndarray:
        """Return ``(C, 2)`` latitude/longitude degrees for cell centers."""
        lat0 = AREA_CENTER_LAT_DEG
        lon0 = AREA_CENTER_LON_DEG
        km_per_deg_lon = KM_PER_DEG_LAT * math.cos(math.radians(lat0))
        lat = lat0 + self.centers_km[:, 1] / KM_PER_DEG_LAT
        lon = lon0 + self.centers_km[:, 0] / km_per_deg_lon
        return np.stack([lat, lon], axis=1)


def _axial_to_local_km(q: np.ndarray, r: np.ndarray, radius_km: float) -> np.ndarray:
    x = radius_km * math.sqrt(3.0) * (q + r / 2.0)
    y = radius_km * 1.5 * r
    return np.stack([x, y], axis=1)


def build_cell_grid(
    cell_radius_km: float | None = None,
    guard_rings: int = 1,
) -> CellGrid:
    """Build the SDD 08 Family-B candidate grid.

    ``serves_area`` is the conservative closed-form Voronoi superset: any
    nearest-center cell for an in-area point must have its center within one
    cell circumradius of the 200 x 90 km rectangle. A dense-grid nearest-center
    sample is asserted to be a subset, and every area-serving cell must have all
    six canonical neighbors present.
    """
    radius = float(cell_radius_km if cell_radius_km is not None else default_cell_radius_km())
    pitch = math.sqrt(3.0) * radius
    guard_km = guard_rings * pitch + radius

    half_ew = AREA_EW_KM / 2.0 + guard_km
    half_ns = AREA_NS_KM / 2.0 + guard_km
    q_span = (
        int(math.ceil(half_ew / (radius * math.sqrt(3.0))))
        + int(math.ceil(half_ns / (radius * 1.5)))
        + 2
    )
    r_span = int(math.ceil(half_ns / (radius * 1.5))) + 2

    qq, rr = np.meshgrid(np.arange(-q_span, q_span + 1), np.arange(-r_span, r_span + 1))
    q = qq.ravel()
    r = rr.ravel()
    xy = _axial_to_local_km(q, r, radius)
    keep = (np.abs(xy[:, 0]) <= half_ew) & (np.abs(xy[:, 1]) <= half_ns)
    q, r, xy = q[keep], r[keep], xy[keep]

    in_area = (np.abs(xy[:, 0]) <= AREA_EW_KM / 2.0) & (
        np.abs(xy[:, 1]) <= AREA_NS_KM / 2.0
    )

    dx = np.maximum(np.abs(xy[:, 0]) - AREA_EW_KM / 2.0, 0.0)
    dy = np.maximum(np.abs(xy[:, 1]) - AREA_NS_KM / 2.0, 0.0)
    serves = np.hypot(dx, dy) <= radius + 1e-9

    gx = np.linspace(-AREA_EW_KM / 2.0, AREA_EW_KM / 2.0, 201)
    gy = np.linspace(-AREA_NS_KM / 2.0, AREA_NS_KM / 2.0, 91)
    px, py = np.meshgrid(gx, gy)
    pts = np.stack([px.ravel(), py.ravel()], axis=1)
    d2 = ((pts[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2)
    sampled = np.zeros(xy.shape[0], dtype=bool)
    sampled[np.unique(d2.argmin(axis=1))] = True
    if (sampled & ~serves).any():
        raise AssertionError("dense-grid nearest-center escaped the conservative superset")

    key = {(int(qi), int(ri)): idx for idx, (qi, ri) in enumerate(zip(q, r))}
    neighbor_ids = np.full((xy.shape[0], 6), -1, dtype=np.int64)
    for idx in range(xy.shape[0]):
        for d, (dq, dr) in enumerate(AXIAL_NEIGHBOR_DIRS):
            neighbor_ids[idx, d] = key.get((int(q[idx]) + dq, int(r[idx]) + dr), -1)

    missing = serves & (neighbor_ids == -1).any(axis=1)
    if missing.any():
        raise AssertionError(
            f"{int(missing.sum())} area-serving cells lack a full 6-neighborhood; "
            f"increase guard_rings (= {guard_rings})"
        )

    return CellGrid(
        cell_radius_km=radius,
        pitch_km=pitch,
        axial=np.stack([q, r], axis=1).astype(np.int64),
        centers_km=xy,
        colors=((q - r) % 3).astype(np.int64),
        in_area=in_area,
        serves_area=serves,
        neighbor_ids=neighbor_ids,
    )


def pointable_cell_ids(grid: CellGrid) -> np.ndarray:
    """Return area-serving cells plus their canonical neighbors, sorted."""
    area_serving = np.flatnonzero(grid.serves_area)
    pointable = set(int(c) for c in area_serving)
    for c in area_serving:
        pointable.update(int(n) for n in grid.neighbor_ids[int(c)] if int(n) >= 0)
    return np.array(sorted(pointable), dtype=np.int64)


def own_cell_ids(user_xy_km: np.ndarray, grid: CellGrid) -> np.ndarray:
    """Nearest cell center per user in local-km Euclidean coordinates."""
    d2 = ((user_xy_km[:, None, :] - grid.centers_km[None, :, :]) ** 2).sum(axis=2)
    return d2.argmin(axis=1)


def neighborhood_cell_ids(own_ids: np.ndarray, grid: CellGrid) -> np.ndarray:
    """Return ``(U, 7)`` cell ids: c0 own, then the six canonical neighbors."""
    return np.concatenate([own_ids[:, None], grid.neighbor_ids[own_ids]], axis=1)


def local_km_to_ecef(xy_km: np.ndarray) -> np.ndarray:
    """Convert local east/north offsets at the area center to spherical ECEF km."""
    lat0 = math.radians(AREA_CENTER_LAT_DEG)
    lon0 = math.radians(AREA_CENTER_LON_DEG)
    km_per_deg_lon = KM_PER_DEG_LAT * math.cos(lat0)
    lat = lat0 + np.radians(xy_km[:, 1] / KM_PER_DEG_LAT)
    lon = lon0 + np.radians(xy_km[:, 0] / km_per_deg_lon)
    return np.stack(
        [
            R_E_KM * np.cos(lat) * np.cos(lon),
            R_E_KM * np.cos(lat) * np.sin(lon),
            R_E_KM * np.sin(lat),
        ],
        axis=1,
    )


def area_center_ecef() -> np.ndarray:
    return local_km_to_ecef(np.zeros((1, 2), dtype=np.float64))[0]


def walker_elements(
    total: int,
    planes: int,
    phasing: int,
    incl_deg: float,
) -> list[tuple[float, float, float]]:
    """Return ``(raan_rad, anomaly0_rad, incl_rad)`` per Walker satellite."""
    if total % planes != 0:
        raise ValueError("total satellites must be divisible by planes")
    per_plane = total // planes
    incl = math.radians(incl_deg)
    out: list[tuple[float, float, float]] = []
    for p in range(planes):
        raan = 2.0 * math.pi * p / planes
        phase0 = 2.0 * math.pi * phasing * p / total
        for k in range(per_plane):
            out.append((raan, 2.0 * math.pi * k / per_plane + phase0, incl))
    return out


def mean_motion_rad_s(mode: str = "v_derived") -> float:
    if mode == "v_derived":
        return SAT_SPEED_KM_S / ORBIT_RADIUS_KM
    if mode == "kepler":
        return math.sqrt(MU_KM3_S2 / ORBIT_RADIUS_KM**3)
    raise ValueError(f"unknown mean-motion mode {mode!r}")


def propagate_ecef(
    elements: list[tuple[float, float, float]],
    t_s: np.ndarray,
    mode: str = "v_derived",
    rotating_earth: bool = True,
    greenwich0_rad: float = 0.0,
) -> np.ndarray:
    """Return satellite ECEF positions, shape ``(S, T, 3)`` in km."""
    n = mean_motion_rad_s(mode)
    a = ORBIT_RADIUS_KM
    theta_g = (
        OMEGA_E_RAD_S * t_s + greenwich0_rad
        if rotating_earth
        else np.full_like(t_s, greenwich0_rad)
    )
    cos_g, sin_g = np.cos(theta_g), np.sin(theta_g)
    out = np.empty((len(elements), t_s.size, 3), dtype=np.float64)
    for s, (raan, anom0, incl) in enumerate(elements):
        u = anom0 + n * t_s
        x_orb, y_orb = a * np.cos(u), a * np.sin(u)
        x_i = x_orb * math.cos(raan) - y_orb * math.cos(incl) * math.sin(raan)
        y_i = x_orb * math.sin(raan) + y_orb * math.cos(incl) * math.cos(raan)
        z_i = y_orb * math.sin(incl)
        out[s, :, 0] = cos_g * x_i + sin_g * y_i
        out[s, :, 1] = -sin_g * x_i + cos_g * y_i
        out[s, :, 2] = z_i
    return out


def elevation_deg(sat_ecef: np.ndarray, ground_ecef: np.ndarray) -> np.ndarray:
    """Elevation of satellites seen from one ground point."""
    up = ground_ecef / np.linalg.norm(ground_ecef)
    d = sat_ecef - ground_ecef
    d_norm = np.linalg.norm(d, axis=-1)
    sin_el = (d @ up) / d_norm
    return np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))


def select_window(
    sats_ecef_t: np.ndarray,
    eps_min_deg: float,
    l_w: int = L_W,
) -> np.ndarray:
    """Select eligible area-global window satellite ids in canonical rank order."""
    center = area_center_ecef()
    el = elevation_deg(sats_ecef_t, center)
    slant = np.linalg.norm(sats_ecef_t - center, axis=-1)
    eligible = np.flatnonzero(el >= eps_min_deg)
    if eligible.size == 0:
        return eligible
    order = eligible[np.lexsort((eligible, slant[eligible]))]
    return order[:l_w]


def off_nadir_deg(sat_ecef: np.ndarray, target_ecef: np.ndarray) -> np.ndarray:
    """Angle between nadir and the target line of sight."""
    nadir = -sat_ecef / np.linalg.norm(sat_ecef, axis=-1, keepdims=True)
    los = target_ecef - sat_ecef
    los = los / np.linalg.norm(los, axis=-1, keepdims=True)
    cosang = np.clip((nadir * los).sum(axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(cosang))


def angle_between_deg(a_from: np.ndarray, a_to1: np.ndarray, a_to2: np.ndarray) -> np.ndarray:
    """Angle at ``a_from`` between directions to ``a_to1`` and ``a_to2``."""
    v1 = a_to1 - a_from
    v2 = a_to2 - a_from
    v1 = v1 / np.linalg.norm(v1, axis=-1, keepdims=True)
    v2 = v2 / np.linalg.norm(v2, axis=-1, keepdims=True)
    cosang = np.clip((v1 * v2).sum(axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(cosang))


def gt_linear(theta_deg: np.ndarray, theta_3db_deg: float = THETA_3DB_DEG) -> np.ndarray:
    """Sealed repo Bessel transmit gain, vectorized over degrees."""
    theta = np.atleast_1d(np.radians(theta_deg)).astype(float)
    out = approved_transmit_gain_linear(
        theta,
        g0_linear=G0_LINEAR,
        theta_3db_rad=math.radians(theta_3db_deg),
    )
    return np.asarray(out, dtype=np.float64)


def rx_gain_linear(sep_deg: np.ndarray) -> np.ndarray:
    """D4b' directional receive gain for serving/cross-satellite separation."""
    sep = np.asarray(sep_deg, dtype=np.float64)
    with np.errstate(divide="ignore"):
        env_dbi = 32.0 - 25.0 * np.log10(np.maximum(sep, 1e-9))
    env_dbi = np.clip(env_dbi, RX_ENVELOPE_FLOOR_DBI, RX_GAIN_SERVING_DBI)
    dbi = np.where(sep <= 1e-9, RX_GAIN_SERVING_DBI, env_dbi)
    return 10.0 ** (dbi / 10.0)


def fspl_linear(slant_km: np.ndarray) -> np.ndarray:
    d_m = np.asarray(slant_km, dtype=np.float64) * 1000.0
    lam = SPEED_OF_LIGHT_M_S / CARRIER_FREQ_HZ
    return (lam / (4.0 * math.pi * d_m)) ** 2


def atmos_loss_db(
    slant_km: np.ndarray,
    elev_deg: np.ndarray,
    form: str = "corrected_lossy",
) -> np.ndarray:
    """Return positive atmospheric loss in dB for the SDD 08 forms."""
    if form == "corrected_lossy":
        return 3.0 * np.asarray(slant_km, dtype=np.float64) * CHI_DB_PER_KM / (10.0 * ALT_KM)
    if form == "zenith_over_sin":
        a_z = CHI_DB_PER_KM * H_ATM_KM
        return a_z / np.maximum(np.sin(np.radians(elev_deg)), 1e-3)
    raise ValueError(f"unknown atmospheric form {form!r}")


def beam_power_w(loads: np.ndarray) -> np.ndarray:
    """REP-04h active-load-concave per-beam power; inactive beams are 0 W."""
    loads = np.asarray(loads, dtype=np.float64)
    p = np.minimum(P_BASE_W + P_SCALE_W * np.power(np.maximum(loads, 0.0), P_EXP), P_MAX_W)
    return np.where(loads > 0, p, 0.0)


def apply_satellite_aggregate_cap(power_w: np.ndarray) -> np.ndarray:
    """Apply REP-04z proportional per-satellite aggregate cap."""
    power = np.asarray(power_w, dtype=np.float64).copy()
    total = power.sum(axis=1, keepdims=True)
    scale = np.where(total > SAT_AGG_CAP_W, SAT_AGG_CAP_W / np.maximum(total, 1e-12), 1.0)
    return power * scale


def family_b_sinr(
    user_ecef: np.ndarray,
    window_sats_ecef: np.ndarray,
    cell_centers_ecef: np.ndarray,
    serving_slot: np.ndarray,
    serving_cell: np.ndarray,
    loads: np.ndarray,
    colors: np.ndarray,
    atmos_form: str = "corrected_lossy",
    apply_agg_cap: bool = True,
) -> dict[str, np.ndarray]:
    """Per-user serving-link SINR/SNR under the frozen SDD 08 probe model."""
    U = user_ecef.shape[0]
    L = window_sats_ecef.shape[0]
    noise_w = noise_power_w()

    power = beam_power_w(loads)
    if apply_agg_cap:
        power = apply_satellite_aggregate_cap(power)

    d_us = np.linalg.norm(user_ecef[:, None, :] - window_sats_ecef[None, :, :], axis=2)
    up = user_ecef / np.linalg.norm(user_ecef, axis=1, keepdims=True)
    sin_el = ((window_sats_ecef[None, :, :] - user_ecef[:, None, :]) * up[:, None, :]).sum(axis=2) / d_us
    elev = np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))
    fspl = fspl_linear(d_us)
    atmo = 10.0 ** (-atmos_loss_db(d_us, elev, atmos_form) / 10.0)

    serv_sat = window_sats_ecef[serving_slot]
    sep = angle_between_deg(user_ecef[:, None, :], serv_sat[:, None, :], window_sats_ecef[None, :, :])
    rx = rx_gain_linear(sep)
    rx[np.arange(U), serving_slot] = 10.0 ** (RX_GAIN_SERVING_DBI / 10.0)

    sig = np.zeros(U, dtype=np.float64)
    intra = np.zeros(U, dtype=np.float64)
    inter = np.zeros(U, dtype=np.float64)

    active = power > 0
    for l in range(L):
        act_cells = np.flatnonzero(active[l])
        if act_cells.size == 0:
            continue
        theta = angle_between_deg(
            window_sats_ecef[l][None, None, :],
            cell_centers_ecef[act_cells][None, :, :],
            user_ecef[:, None, :],
        )
        g_t = gt_linear(theta.ravel()).reshape(theta.shape)
        rcv = (
            power[l, act_cells][None, :]
            * g_t
            * (fspl[:, l] * atmo[:, l] * rx[:, l])[:, None]
        )

        serving_here = serving_slot == l
        if serving_here.any():
            pos = {int(c): i for i, c in enumerate(act_cells)}
            for u in np.flatnonzero(serving_here):
                i = pos.get(int(serving_cell[u]))
                if i is not None:
                    sig[u] = rcv[u, i]

        co = colors[act_cells][None, :] == colors[serving_cell][:, None]
        contrib = np.where(co, rcv, 0.0).sum(axis=1)
        own_term = np.zeros(U, dtype=np.float64)
        own_mask = serving_here & np.isin(serving_cell, act_cells)
        if own_mask.any():
            pos_arr = np.full(cell_centers_ecef.shape[0], -1, dtype=np.int64)
            pos_arr[act_cells] = np.arange(act_cells.size)
            uu = np.flatnonzero(own_mask)
            own_term[uu] = rcv[uu, pos_arr[serving_cell[uu]]]
        intra[serving_slot == l] += (contrib - own_term)[serving_slot == l]
        inter[serving_slot != l] += contrib[serving_slot != l]

    snr = sig / noise_w
    sinr = sig / (intra + inter + noise_w)
    return {
        "snr_linear": snr,
        "sinr_linear": sinr,
        "signal_w": sig,
        "intra_w": intra,
        "inter_w": inter,
        "noise_w": np.full(U, noise_w, dtype=np.float64),
        "elev_deg_serving": elev[np.arange(U), serving_slot],
    }


def rate_bps(sinr_linear: np.ndarray, loads_of_serving: np.ndarray) -> np.ndarray:
    """Per-user rate = (B/3 / N_b) * log2(1 + SINR)."""
    share = B_ALLOC_HZ / np.maximum(loads_of_serving, 1.0)
    return share * np.log2(1.0 + np.maximum(sinr_linear, 0.0))


__all__ = [
    "AREA_CENTER_LAT_DEG",
    "AREA_CENTER_LON_DEG",
    "AREA_EW_KM",
    "AREA_NS_KM",
    "ALT_KM",
    "R_E_KM",
    "ORBIT_RADIUS_KM",
    "OMEGA_E_RAD_S",
    "SAT_SPEED_KM_S",
    "THETA_3DB_DEG",
    "G0_LINEAR",
    "B_ALLOC_HZ",
    "BANDWIDTH_HZ",
    "L_W",
    "S1528_OFF_NADIR_LIMIT_DEG",
    "EARTH_LIMB_OFF_NADIR_DEG",
    "AXIAL_NEIGHBOR_DIRS",
    "CellGrid",
    "build_cell_grid",
    "pointable_cell_ids",
    "own_cell_ids",
    "neighborhood_cell_ids",
    "default_cell_radius_km",
    "local_km_to_ecef",
    "area_center_ecef",
    "walker_elements",
    "mean_motion_rad_s",
    "propagate_ecef",
    "elevation_deg",
    "select_window",
    "off_nadir_deg",
    "angle_between_deg",
    "gt_linear",
    "rx_gain_linear",
    "fspl_linear",
    "atmos_loss_db",
    "beam_power_w",
    "apply_satellite_aggregate_cap",
    "noise_power_w",
    "family_b_sinr",
    "rate_bps",
    "P_BASE_W",
    "P_SCALE_W",
    "P_EXP",
    "P_MAX_W",
    "SAT_AGG_CAP_W",
    "NOISE_FIGURE_DB",
    "RX_GAIN_SERVING_DBI",
]
