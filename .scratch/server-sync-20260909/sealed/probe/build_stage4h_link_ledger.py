#!/usr/bin/env python3
"""Independent Stage-4h link-budget ledger (deliberately no mcrl imports)."""

from __future__ import annotations

import json
import math


C = 299_792_458.0
F = 20.0e9
K_EXACT = 1.380649e-23
K_DBW_PER_K_HZ = 10.0 * math.log10(K_EXACT)
P_CAP_W = 1.65
TX_GAIN_LINEAR = 2000.0
RX_GAIN_DBI = 35.0
T_SYS_K = 150.0 + 290.0 * (10.0**0.12 - 1.0)
B_HZ = 500.0e6 / 3.0
ROLL_OFF = 0.20
IMPLEMENTATION_MARGIN_DB = 1.7
EARTH_RADIUS_KM = 6371.0
ALTITUDE_KM = 550.0

# Name, Table-13 efficiency (bit/symbol), ideal Es/N0 (dB).
MODES = (
    ("QPSK 1/4", 0.490243, -2.35),
    ("QPSK 1/3", 0.656448, -1.24),
    ("QPSK 2/5", 0.789412, -0.30),
    ("QPSK 1/2", 0.988858, 1.00),
    ("QPSK 3/5", 1.188304, 2.23),
    ("QPSK 2/3", 1.322253, 3.10),
    ("QPSK 3/4", 1.487473, 4.03),
    ("QPSK 4/5", 1.587196, 4.68),
    ("QPSK 5/6", 1.654663, 5.18),
    ("QPSK 8/9", 1.766451, 6.20),
    ("QPSK 9/10", 1.788612, 6.42),
    ("8PSK 3/5", 1.779991, 5.50),
    ("8PSK 2/3", 1.980636, 6.62),
    ("8PSK 3/4", 2.228124, 7.91),
    ("8PSK 5/6", 2.478562, 9.35),
    ("8PSK 8/9", 2.646012, 10.69),
    ("8PSK 9/10", 2.679207, 10.98),
    ("16APSK 2/3", 2.637201, 8.97),
    ("16APSK 3/4", 2.966728, 10.21),
    ("16APSK 4/5", 3.165623, 11.03),
    ("16APSK 5/6", 3.300184, 11.61),
    ("16APSK 8/9", 3.523143, 12.89),
    ("16APSK 9/10", 3.567342, 13.13),
    ("32APSK 3/4", 3.703295, 12.73),
    ("32APSK 4/5", 3.951571, 13.64),
    ("32APSK 5/6", 4.119540, 14.28),
    ("32APSK 8/9", 4.397854, 15.69),
    ("32APSK 9/10", 4.453027, 16.05),
)


def threshold_db(row: tuple[str, float, float]) -> float:
    return row[2] + IMPLEMENTATION_MARGIN_DB - 10.0 * math.log10(1.0 + ROLL_OFF)


def spectral_efficiency(row: tuple[str, float, float]) -> float:
    return row[1] / (1.0 + ROLL_OFF)


def target_mode(users: int) -> tuple[str, float, float] | None:
    required = 50.0e6 * users / B_HZ
    eligible = [row for row in MODES if spectral_efficiency(row) >= required]
    return min(eligible, key=threshold_db) if eligible else None


def selected_mode(predicted_sinr_db: float) -> tuple[str, float, float] | None:
    eligible = [row for row in MODES if predicted_sinr_db >= threshold_db(row)]
    return max(eligible, key=lambda row: row[1]) if eligible else None


def geometry_row(
    name: str,
    *,
    slant_km: float,
    elevation_deg: float,
    pointing_loss_db: float,
    q10: float,
) -> dict[str, object]:
    tx_gain_dbi = 10.0 * math.log10(TX_GAIN_LINEAR)
    eirp_dbw = 10.0 * math.log10(P_CAP_W) + tx_gain_dbi - pointing_loss_db
    fspl_db = 20.0 * math.log10(4.0 * math.pi * slant_km * 1000.0 * F / C)
    gaseous_loss_db = 0.25 / math.sin(math.radians(elevation_deg))
    g_over_t = RX_GAIN_DBI - 10.0 * math.log10(T_SYS_K)
    cn_cap_db = (
        eirp_dbw
        - fspl_db
        - gaseous_loss_db
        + g_over_t
        - K_DBW_PER_K_HZ
        - 10.0 * math.log10(B_HZ)
    )
    loads = []
    for users in (1, 2, 4):
        target = target_mode(users)
        assert target is not None
        target_db = threshold_db(target)
        predicted_db = target_db + 10.0 * math.log10(q10)
        transmitted = selected_mode(predicted_db)
        loads.append(
            {
                "users": users,
                "c_over_i_db": "infinite (isolated co-channel beam fixture)",
                "target_mode": target[0],
                "target_threshold_db": target_db,
                "required_rf_power_w": P_CAP_W * 10.0 ** ((target_db - cn_cap_db) / 10.0),
                "cap_headroom_db": cn_cap_db - target_db,
                "q10_predicted_sinr_db": predicted_db,
                "transmitted_mode": None if transmitted is None else transmitted[0],
                "transmitted_threshold_db": None if transmitted is None else threshold_db(transmitted),
                "lowest_threshold_db": threshold_db(MODES[0]),
            }
        )
    return {
        "geometry": name,
        "slant_km": slant_km,
        "elevation_deg": elevation_deg,
        "pointing_loss_db": pointing_loss_db,
        "eirp_at_cap_dbw": eirp_dbw,
        "free_space_path_loss_db": fspl_db,
        "gaseous_path_loss_db": gaseous_loss_db,
        "receiver_g_over_t_db_per_k": g_over_t,
        "occupied_bandwidth_hz": B_HZ,
        "noise_power_w": K_EXACT * T_SYS_K * B_HZ,
        "c_over_n_at_cap_db": cn_cap_db,
        "q10": q10,
        "loads": loads,
    }


def main() -> None:
    edge_elevation = math.degrees(
        math.asin(
            ((EARTH_RADIUS_KM + ALTITUDE_KM) ** 2 - EARTH_RADIUS_KM**2 - 1100.0**2)
            / (2.0 * EARTH_RADIUS_KM * 1100.0)
        )
    )
    payload = {
        "independent_of_mcrl_runtime": True,
        "geometries": [
            geometry_row(
                "boresight",
                slant_km=550.0,
                elevation_deg=90.0,
                pointing_loss_db=0.0,
                q10=0.7749486236990524,
            ),
            geometry_row(
                "half-power-edge",
                slant_km=1100.0,
                elevation_deg=edge_elevation,
                pointing_loss_db=3.0,
                q10=0.5204588857996268,
            ),
        ],
        "maximum_spectral_efficiency_bit_per_s_hz": spectral_efficiency(MODES[-1]),
        "beam_capacity_bps": spectral_efficiency(MODES[-1]) * B_HZ,
        "maximum_users_at_50_mbps": 12,
        "first_impossible_user_count": 13,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
