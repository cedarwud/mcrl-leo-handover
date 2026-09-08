"""Frozen V0.25 constants and their source/provenance manifest.

Every public constant has a one-line ``# Provenance:`` declaration at its
definition.  ``constant_manifest()`` is the machine-readable binding used by
matrix receipts.  Values marked ``VERIFY_SOURCE`` are assumptions whose cited
source does not establish flight or live-procedure applicability.
"""

from __future__ import annotations

import hashlib
import json
import math
from types import MappingProxyType

ENGINE_VERSION = "V025-ANGLE-RATE-TPC-TDM-ACM-STAGE1B"  # Provenance: sealed V025 v1.1 amendment, primary architecture.
REFERENCE_ARCHITECTURE = "b"  # Provenance: sealed V025 priority declaration, declared reference model.
PRIMARY_ARCHITECTURE = "a-r"  # Provenance: sealed V025 v1.1 amendment, primary system model.
SENSITIVITY_ARCHITECTURE = "a\u2032-r"  # Provenance: sealed V025 v1.1 amendment, architectural sensitivity.

CARRIER_FREQUENCY_HZ = 20.0e9  # Provenance: round-3 §2.6, retained source-bound benchmark carrier.
SPEED_OF_LIGHT_M_S = 299_792_458.0  # Provenance: SI exact definition of the speed of light.
TOTAL_BANDWIDTH_HZ = 500.0e6  # Provenance: round-3 §2.5 retained benchmark bandwidth.
FREQUENCY_REUSE = 3  # Provenance: round-3 §2.5 retained earth-fixed reuse-3 benchmark.
BEAM_BANDWIDTH_HZ = TOTAL_BANDWIDTH_HZ / FREQUENCY_REUSE  # Provenance: round-3 §2.5, 500/3 MHz per colour.
BOLTZMANN_J_PER_K = 1.380649e-23  # Provenance: 2019 SI exact Boltzmann constant.
ANTENNA_TEMPERATURE_K = 150.0  # Provenance: round-3 §2.6 retained TR 38.821 Ka VSAT benchmark.
REFERENCE_TEMPERATURE_K = 290.0  # Provenance: round-3 §2.6 retained reference temperature.
RECEIVER_NOISE_FIGURE_DB = 1.2  # Provenance: round-3 §2.6 retained TR 38.821 Ka VSAT benchmark.
SYSTEM_TEMPERATURE_K = ANTENNA_TEMPERATURE_K + REFERENCE_TEMPERATURE_K * (10.0**0.12 - 1.0)  # Provenance: round-3 §2.6 stated derivation.
RICIAN_K_FACTOR_DB = 20.0  # Provenance: round-3 §2.6 retained benchmark-specific interpretation.
MINIMUM_ELEVATION_DEG = 10.0  # Provenance: round-3 §2.18 live visibility contract.

BEAM_RF_CAP_W = 1.65  # Provenance: round-3 §2.2 inherited benchmark; not measured flight hardware (VERIFY_SOURCE).
PA_OUTPUT_BACKOFF_DB = 5.0  # Provenance: round-3 §2.2 inherited engineering PA assumption (VERIFY_SOURCE).
PA_SATURATION_POWER_W = BEAM_RF_CAP_W * 10.0 ** (PA_OUTPUT_BACKOFF_DB / 10.0)  # Provenance: round-3 §2.2 stated derivation.
PA_MAX_EFFICIENCY = 0.35  # Provenance: round-3 §2.2 inherited engineering PA curve assumption (VERIFY_SOURCE).
CIRCUIT_POWER_PER_CHAIN_W = 0.338  # Provenance: round-3 §2.12 retained You et al. component sum; beam-to-chain mapping is assumed (VERIFY_SOURCE).
BASEBAND_POWER_PER_ACTIVE_SATELLITE_W = 0.200  # Provenance: round-3 §2.12 retained You et al. component coefficient (VERIFY_SOURCE).
P_BUS_W = 0.0  # Provenance: round-3 §2.13 explicit exclusion of bus, terminal, gateway, and controller energy.
STANDBY_FRACTION = 1.0 / 12.0  # Provenance: round-3 §2.14 CPI 35/420 ground-HPA proxy (VERIFY_SOURCE).

ROLL_OFF = 0.20  # Provenance: round-3 §2.8 prospective DVB-S2 shaping choice.
IMPLEMENTATION_MARGIN_DB = 1.7  # Provenance: round-3 §2.9 prospective common receiver allowance (VERIFY_SOURCE).
POWER_CONTROL_TARGET_DB = 7.528187540  # Provenance: round-3 §2.9 8PSK 2/3 model threshold.
POWER_CONTROL_TARGET_LINEAR = 10.0 ** (POWER_CONTROL_TARGET_DB / 10.0)  # Provenance: round-3 §4 stated 5.660030272 target, derived from dB.
RATE_TARGET_BPS = 50_000_000.0  # Provenance: sealed V025 v1.1 amendment; synthetic operating point inherited from Track B L1, not calibrated demand (VERIFY_SOURCE for physical use).
SINR_MIN_DB = -1.441812460  # Provenance: round-3 §2.9 QPSK 1/4 model threshold.
SINR_MIN = 10.0 ** (SINR_MIN_DB / 10.0)  # Provenance: round-3 §2.10 PHY decodability boundary.
SHANNON_MIN_DB = -2.35 - 10.0 * math.log10(1.0 + ROLL_OFF)  # Provenance: round-3 §4 U treatment, lowest threshold with margin off.
SHANNON_MIN = 10.0 ** (SHANNON_MIN_DB / 10.0)  # Provenance: round-3 §4 U diagnostic eligibility boundary.

POWER_SOLVER_TOLERANCE_W = 1.0e-10  # Provenance: sealed V025 declaration and round-3 §4 frozen solver tolerance.
POWER_SOLVER_ITERATION_CAP = 4_096  # Provenance: sealed V025 declaration and round-3 §4 frozen solver cap.

D2_MEASUREMENT_STEP_S = 0.640  # Provenance: round-3 §2.17 native measurement clock.
D2_SUBINTERVALS = 47  # Provenance: round-3 §2.17 native subinterval count.
DECISION_INTERVAL_S = D2_SUBINTERVALS * D2_MEASUREMENT_STEP_S  # Provenance: round-3 §2.17, 47 x 0.640 = 30.08 s.
D2_THRESHOLD_KM = 1100.0  # Provenance: round-3 §2.18 retained D2-derived candidate threshold.
D2_HYSTERESIS_KM = 50.0  # Provenance: round-3 §2.18 retained D2 hysteresis.
D2_TTT_S = 1.280  # Provenance: round-3 §2.18 retained D2 time-to-trigger.
MINIMUM_ALTITUDE_KM = 300.0  # Provenance: round-3 §2.18 retained candidate altitude floor.
ASSOCIATION_ACTIONS = 28  # Provenance: round-3 §2.19 retained action inventory.
CACHED_SATELLITES = 4  # Provenance: round-3 §2.19 retained cached satellite identities.
LOCAL_CELLS = 7  # Provenance: round-3 §2.19 retained local cell actions.
IDENTITY_REFRESH_DECISIONS = 4  # Provenance: round-3 §2.19 retained identity refresh cadence.

SAME_SATELLITE_INTERRUPTION_S = 0.062  # Provenance: round-3 §2.16 conditional ADR-004 electronic handover proxy (VERIFY_SOURCE).
SATELLITE_CHANGE_INTERRUPTION_S = 0.142  # Provenance: round-3 §2.16 conditional ADR-004 electronic handover proxy (VERIFY_SOURCE).
PHI_SAME_SATELLITE = 0.5  # Provenance: round-3 §2.23 retained benchmark preference; not joules or seconds.
PHI_SATELLITE_CHANGE = 1.0  # Provenance: round-3 §2.23 retained benchmark preference; not joules or seconds.
PERSISTENCE_LOSS_UNITS = 1.0  # Provenance: round-3 §2.24 stated one-kappa design preference per lost projected offset.
FORECAST_OFFSETS = 3  # Provenance: round-3 §2.27 three physical forecast offsets.

TX_G0_LINEAR = 2000.0  # Provenance: round-3 §2.6 retained source-bound transmit pattern benchmark.
TX_FULL_HPBW_DEG = 3.32  # Provenance: retained HOBS full half-power beamwidth convention.
RX_GAIN_MAX_DBI = 35.0  # Provenance: round-3 §2.6 retained 0.6-m terminal peak benchmark.
RX_TERMINAL_DIAMETER_M = 0.6  # Provenance: round-3 §2.6 retained terminal aperture benchmark.
RX_ENVELOPE_A_DBI = 32.0  # Provenance: round-3 §2.7 retained S.465 engineering extrapolation coefficient.
RX_ENVELOPE_B = 25.0  # Provenance: round-3 §2.7 retained S.465 engineering extrapolation coefficient.
RX_GAIN_FLOOR_DBI = -10.0  # Provenance: retained S.465 envelope floor.
RX_S465_THETA_MIN_DEG = 2.043298703  # Provenance: round-3 §2.7 corrected S.465-6 D/lambda<50 branch.
ZENITH_GASEOUS_LOSS_DB = 0.25  # Provenance: round-3 §2.6 retained clear-sky TR 38.811/38.821 substitution.
SCINTILLATION_ELEVATION_DEG = (10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0)  # Provenance: round-3 §2.6 retained TR 38.811 20-GHz table abscissa.
SCINTILLATION_LOSS_DB = (1.08, 0.48, 0.30, 0.22, 0.17, 0.13, 0.12, 0.12, 0.12)  # Provenance: round-3 §2.6 retained TR 38.811 clear-sky scintillation table.
SHADOW_SIGMA_ELEVATION_DEG = (10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0)  # Provenance: round-3 §2.6 retained TR 38.811 Ka-LOS table abscissa.
SHADOW_SIGMA_DB = (1.9, 1.6, 1.9, 2.3, 2.7, 3.1, 3.0, 3.6, 0.4)  # Provenance: round-3 §2.6 retained TR 38.811 Ka-LOS zero-mean-dB shadow table.
REFERENCE_BEAMS_PER_SATELLITE = 39  # Provenance: round-3 assumption 26 compatibility reference, not a hardware ceiling.
REFERENCE_AGGREGATE_RF_W = REFERENCE_BEAMS_PER_SATELLITE * BEAM_RF_CAP_W  # Provenance: round-3 assumption 26 identity 39*1.65=64.35 W, not cap derivation.
HOBS_REFERENCE_MAX_RF_W = 100.0  # Provenance: round-3 assumption 26 retained 50-dBm HOBS reference, not a live clamp.

# EN 302 307-1 V1.4.1 Table 13, normal FEC frames, no pilots.  Each row is
# (MODCOD, spectral efficiency bit/symbol, ideal Es/N0 dB).
ACM_TABLE = (  # Provenance: ETSI EN 302 307-1 V1.4.1 Table 13, transcribed 2026-09-08.
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


def _table_bytes() -> bytes:
    return json.dumps(ACM_TABLE, ensure_ascii=True, separators=(",", ":")).encode("ascii")


ACM_TABLE_SHA256 = "4463331e621d778f4aa97d60ed5726c1e02bcf791e2be7b134ec29eace631627"  # Provenance: frozen SHA-256 of the canonical ASCII ACM_TABLE transcription above.
if hashlib.sha256(_table_bytes()).hexdigest() != ACM_TABLE_SHA256:
    raise RuntimeError("V0.25 ACM table transcription does not match its frozen SHA-256")

VERIFY_SOURCE = MappingProxyType(  # Provenance: round-3 §2 explicit hardware/proxy applicability flags.
    {
        "beam_rf_cap_flight_hardware": True,
        "pa_curve_and_backoff_flight_hardware": True,
        "beam_to_rf_chain_mapping": True,
        "circuit_and_baseband_payload_mapping": True,
        "standby_ground_hpa_proxy_flight_applicability": True,
        "interruption_live_beam_cell_procedure_applicability": True,
        "common_1p7_db_margin_complete_distortion_budget": True,
        "rate_target_physical_calibration": True,
    }
)

# Machine-readable registry.  It is deliberately concise; source-level one-line
# provenance remains authoritative and tests ensure every exported scalar/table
# appears here.
PROVENANCE = MappingProxyType(  # Provenance: stage-1 constants-manifest contract.
    {
        "ENGINE_VERSION": "sealed V025 priority declaration identity",
        "REFERENCE_ARCHITECTURE": "sealed V025 declared reference",
        "PRIMARY_ARCHITECTURE": "sealed V025 declared primary",
        "SENSITIVITY_ARCHITECTURE": "sealed V025 architectural sensitivity",
        "CARRIER_FREQUENCY_HZ": "round-3 §2.6 retained 20-GHz benchmark",
        "SPEED_OF_LIGHT_M_S": "SI exact definition",
        "TOTAL_BANDWIDTH_HZ": "round-3 §2.5 retained 500-MHz benchmark",
        "FREQUENCY_REUSE": "round-3 §2.5 retained reuse-3 benchmark",
        "BOLTZMANN_J_PER_K": "2019 SI exact definition",
        "ANTENNA_TEMPERATURE_K": "round-3 §2.6 retained Ka-VSAT benchmark",
        "REFERENCE_TEMPERATURE_K": "round-3 §2.6 retained reference temperature",
        "RECEIVER_NOISE_FIGURE_DB": "round-3 §2.6 retained receiver noise figure",
        "D2_MEASUREMENT_STEP_S": "round-3 §2.17 native measurement clock",
        "D2_SUBINTERVALS": "round-3 §2.17 native integration count",
        "D2_THRESHOLD_KM": "round-3 §2.18 retained D2-derived threshold",
        "D2_HYSTERESIS_KM": "round-3 §2.18 retained D2 hysteresis",
        "D2_TTT_S": "round-3 §2.18 retained 1.280-s TTT",
        "MINIMUM_ALTITUDE_KM": "round-3 §2.18 retained altitude floor",
        "ASSOCIATION_ACTIONS": "round-3 §2.19 retained action count",
        "CACHED_SATELLITES": "round-3 §2.19 retained satellite cache width",
        "LOCAL_CELLS": "round-3 §2.19 retained local-cell count",
        "IDENTITY_REFRESH_DECISIONS": "round-3 §2.19 retained refresh cadence",
        "PHI_SAME_SATELLITE": "round-3 §2.23 benchmark preference, not energy/time",
        "PHI_SATELLITE_CHANGE": "round-3 §2.23 benchmark preference, not energy/time",
        "PERSISTENCE_LOSS_UNITS": "round-3 §2.24 one-kappa preference",
        "FORECAST_OFFSETS": "round-3 §2.27 three physical offsets",
        "TX_G0_LINEAR": "round-3 §2.6 retained transmit-pattern peak",
        "TX_FULL_HPBW_DEG": "retained HOBS full-HPBW convention",
        "RX_GAIN_MAX_DBI": "round-3 §2.6 retained terminal peak",
        "RX_TERMINAL_DIAMETER_M": "round-3 §2.6 retained terminal diameter",
        "RX_ENVELOPE_A_DBI": "round-3 §2.7 retained engineering extrapolation",
        "RX_ENVELOPE_B": "round-3 §2.7 retained engineering extrapolation",
        "RX_GAIN_FLOOR_DBI": "retained S.465 envelope floor",
        "ZENITH_GASEOUS_LOSS_DB": "round-3 §2.6 retained clear-sky substitution",
        "SCINTILLATION_ELEVATION_DEG": "round-3 §2.6 retained TR 38.811 abscissa",
        "SCINTILLATION_LOSS_DB": "round-3 §2.6 retained TR 38.811 20-GHz table",
        "SHADOW_SIGMA_ELEVATION_DEG": "round-3 §2.6 retained TR 38.811 abscissa",
        "SHADOW_SIGMA_DB": "round-3 §2.6 retained Ka-LOS shadow table",
        "REFERENCE_BEAMS_PER_SATELLITE": "round-3 assumption 26 compatibility reference",
        "REFERENCE_AGGREGATE_RF_W": "round-3 assumption 26 identity, not cap derivation",
        "HOBS_REFERENCE_MAX_RF_W": "round-3 assumption 26 reference, not live clamp",
        "ACM_TABLE": "ETSI EN 302 307-1 V1.4.1 Table 13, normal frames/no pilots",
        "ACM_TABLE_SHA256": "frozen SHA-256 of canonical ordered ACM transcription",
        "BEAM_RF_CAP_W": "round-3 §2.2 inherited benchmark; VERIFY_SOURCE",
        "PA_OUTPUT_BACKOFF_DB": "round-3 §2.2 inherited engineering assumption; VERIFY_SOURCE",
        "PA_SATURATION_POWER_W": "round-3 §2.2: 1.65*10^(5/10)",
        "PA_MAX_EFFICIENCY": "round-3 §2.2 engineering PA assumption; VERIFY_SOURCE",
        "CIRCUIT_POWER_PER_CHAIN_W": "round-3 §2.12 retained component sum; VERIFY_SOURCE",
        "BASEBAND_POWER_PER_ACTIVE_SATELLITE_W": "round-3 §2.12 retained component coefficient; VERIFY_SOURCE",
        "STANDBY_FRACTION": "round-3 §2.14 CPI 35/420 proxy; VERIFY_SOURCE",
        "ROLL_OFF": "round-3 §2.8 prospective shaping choice",
        "IMPLEMENTATION_MARGIN_DB": "round-3 §2.9 prospective common allowance; VERIFY_SOURCE",
        "POWER_CONTROL_TARGET_DB": "round-3 §2.9 8PSK 2/3 model threshold",
        "POWER_CONTROL_TARGET_LINEAR": "round-3 §4 target derived from dB",
        "RATE_TARGET_BPS": "sealed V025 v1.1 synthetic Track B L1 operating point; VERIFY_SOURCE for physical use",
        "SINR_MIN_DB": "round-3 §2.9 QPSK 1/4 model threshold",
        "SINR_MIN": "round-3 §2.10 PHY decodability boundary",
        "SHANNON_MIN_DB": "round-3 §4 margin-off U eligibility threshold",
        "SHANNON_MIN": "round-3 §4 margin-off U eligibility boundary",
        "RX_S465_THETA_MIN_DEG": "round-3 §2.7 corrected S.465-6 branch",
        "DECISION_INTERVAL_S": "round-3 §2.17 47*0.640 seconds",
        "BEAM_BANDWIDTH_HZ": "round-3 §2.5 500/3 MHz per colour",
        "SYSTEM_TEMPERATURE_K": "round-3 §2.6 150+290*(10^0.12-1)",
        "RICIAN_K_FACTOR_DB": "round-3 §2.6 retained benchmark interpretation",
        "MINIMUM_ELEVATION_DEG": "round-3 §2.18 live visibility floor",
        "POWER_SOLVER_TOLERANCE_W": "sealed V025 declaration",
        "POWER_SOLVER_ITERATION_CAP": "sealed V025 declaration",
        "P_BUS_W": "round-3 §2.13 explicit endpoint exclusion",
        "SAME_SATELLITE_INTERRUPTION_S": "round-3 §2.16 conditional proxy; VERIFY_SOURCE",
        "SATELLITE_CHANGE_INTERRUPTION_S": "round-3 §2.16 conditional proxy; VERIFY_SOURCE",
    }
)


def constant_manifest() -> dict[str, object]:
    """Return a canonical, serialisable binding for matrix/source receipts."""

    return {
        "engine_version": ENGINE_VERSION,
        "acm_table_sha256": ACM_TABLE_SHA256,
        "values": {name: globals()[name] for name in PROVENANCE},
        "provenance": dict(PROVENANCE),
        "verify_source": dict(VERIFY_SOURCE),
    }


__all__ = [name for name in globals() if name.isupper()] + ["constant_manifest"]
