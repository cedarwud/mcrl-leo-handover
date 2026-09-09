#!/usr/bin/env python3
"""Validate the independent recomputation in `figure1_compute.py`.

`figure1_compute.py` derives every quantity from the sealed closed-form
equations only. This script checks that derivation against two external
oracles that were NOT used to build it:

  1. The 16 hand-computed rows of the sealed KAT table in
     `V025-ANGLE-POWER-EE-NOTE-2026-09-08.md`.
  2. `scipy.special.jv` for the Bessel pattern (the compute module uses its
     own ascending-series implementation).

It also re-checks the four structural properties the sealed KAT asserts:
monotone power up to the cap, flat power at the cap, monotone-decreasing EE,
and constant RF with falling bits for the fixed-RF reference `b0`.
"""

from __future__ import annotations

import math
import sys

import figure1_compute as f1

# Oracle rows transcribed from the sealed note, used ONLY for verification.
# Columns: (angle_deg, model, n_b) -> (G_T, p_W, mode, Mbit_beam, energy_J, Mbit_per_J)
ORACLE = {
    (0.000000, "a-r0", 1): (2000.000000, 0.317638, "QPSK 1/4", 2048.126, 126.824, 16.149),
    (0.000000, "a-r0", 2): (2000.000000, 0.509251, "QPSK 2/5", 3297.988, 156.276, 21.104),
    (0.000000, "a-r0", 4): (2000.000000, 1.380168, "QPSK 3/4", 6214.332, 246.814, 25.178),
    (0.000000, "b0", 1):   (2000.000000, 1.650000, "QPSK 4/5", 6630.952, 268.353, 24.710),
    (0.830000, "a-r0", 1): (1689.075704, 0.376108, "QPSK 1/4", 2048.126, 136.578, 14.996),
    (0.830000, "a-r0", 2): (1689.075704, 0.602994, "QPSK 2/5", 3297.988, 168.626, 19.558),
    (0.830000, "a-r0", 4): (1689.075704, 1.634228, "QPSK 3/4", 6214.332, 267.145, 23.262),
    (0.830000, "b0", 1):   (1689.075704, 1.650000, "QPSK 3/4", 6214.332, 268.353, 23.157),
    (0.853070, "a-r0", 1): (1672.930437, 0.379738, "QPSK 1/4", 2048.126, 137.158, 14.933),
    (0.853070, "a-r0", 2): (1672.930437, 0.608813, "QPSK 2/5", 3297.988, 169.360, 19.473),
    (0.853070, "a-r0", 4): (1672.930437, 1.650000, "QPSK 3/4", 6214.332, 268.353, 23.157),
    (0.853070, "b0", 1):   (1672.930437, 1.650000, "QPSK 3/4", 6214.332, 268.353, 23.157),
    (1.660000, "a-r0", 1): (1000.000817, 0.635275, "QPSK 1/4", 2048.126, 172.654, 11.863),
    (1.660000, "a-r0", 2): (1000.000817, 1.018501, "QPSK 2/5", 3297.988, 214.305, 15.389),
    (1.660000, "a-r0", 4): (1000.000817, 1.650000, "QPSK 1/2", 4131.229, 268.353, 15.395),
    (1.660000, "b0", 1):   (1000.000817, 1.650000, "QPSK 1/2", 4131.229, 268.353, 15.395),
}

SEALED_CAP_HIT_DEG = 0.853069795148802
SEALED_GAMMA_R = (0.717494793565848, 1.150320220502404, 3.117588235600445)
SEALED_ANGLE_INDEPENDENT = 6.296981727548675e-16
SEALED_FSPG = 3.557146035714657e-19
SEALED_NOISE_W = 5.575393264517296e-13
SEALED_PSAT_W = 5.217758139277826
SEALED_LOSS_DB = 2.5196926207859085

failures: list[str] = []


def check(label: str, actual: float, expected: float, tol: float) -> None:
    if expected == 0.0:
        ok = abs(actual) <= tol
        rel = abs(actual)
    else:
        rel = abs(actual / expected - 1.0)
        ok = rel <= tol
    status = "ok " if ok else "FAIL"
    print(f"  [{status}] {label:52s} got={actual!r:26.26} rel={rel:.2e} tol={tol:.0e}")
    if not ok:
        failures.append(label)


def check_eq(label: str, actual, expected) -> None:
    ok = actual == expected
    print(f"  [{'ok ' if ok else 'FAIL'}] {label:52s} got={actual!r} want={expected!r}")
    if not ok:
        failures.append(label)


print("1. Sealed scalar constants")
check("free-space path gain (2000 km)", f1.free_space_path_gain(f1.SLANT_KM), SEALED_FSPG, 1e-12)
check("atmospheric loss L(10 deg) [dB]", f1.atmospheric_loss_db(f1.ELEVATION_DEG), SEALED_LOSS_DB, 1e-14)
check("angle-independent product C", f1.angle_independent_gain(), SEALED_ANGLE_INDEPENDENT, 1e-12)
check("noise power N [W]", f1.noise_power_w(), SEALED_NOISE_W, 1e-12)
check("saturated power p_sat [W]", f1.saturated_power_w(), SEALED_PSAT_W, 1e-15)
check("decision interval Delta [s]", f1.DECISION_INTERVAL_S, 30.08, 1e-15)

print("\n2. Rate-target thresholds Gamma_r(n_b)")
for nb, sealed in zip(f1.OCCUPANCIES, SEALED_GAMMA_R):
    check(f"Gamma_r(n_b={nb})", f1.gamma_required(nb), sealed, 1e-15)
check_eq("m_r(1)", f1.rate_target_mode(1).name, "QPSK 1/4")
check_eq("m_r(2)", f1.rate_target_mode(2).name, "QPSK 2/5")
check_eq("m_r(4)", f1.rate_target_mode(4).name, "QPSK 3/4")

print("\n3. Radiation pattern: series implementation vs scipy, and normalisation")
check("G_T(0)", f1.transmit_gain_linear(0.0), 2000.0, 1e-15)
try:
    from scipy.special import jv

    worst = 0.0
    for i in range(0, 401):
        theta = f1.PATTERN_EDGE_DEG * i / 400.0
        if theta == 0.0:
            continue
        mu = f1.BESSEL_SCALE * math.sin(math.radians(theta)) / math.sin(
            math.radians(f1.TX_FULL_HPBW_DEG / 2.0)
        )
        ref = 2000.0 * (jv(1, mu) / (2 * mu) + 36 * jv(3, mu) / mu**3) ** 2
        worst = max(worst, abs(f1.transmit_gain_linear(theta) / ref - 1.0))
    print(f"  [{'ok ' if worst < 1e-12 else 'FAIL'}] "
          f"{'G_T series vs scipy.jv, worst rel over 400 angles':52s} rel={worst:.2e} tol=1e-12")
    if worst >= 1e-12:
        failures.append("G_T vs scipy")
except ImportError:
    print("  [skip] scipy unavailable")

print("\n4. Cap-hit angle (independent bisection on the Bessel pattern)")
check("cap-hit angle, n_b=4 [deg]", f1.cap_hit_angle_deg(4), SEALED_CAP_HIT_DEG, 1e-11)
check_eq("cap-hit, n_b=1 is None", f1.cap_hit_angle_deg(1), None)
check_eq("cap-hit, n_b=2 is None", f1.cap_hit_angle_deg(2), None)

print("\n5. The 16 sealed KAT rows")
for (angle, model, nb), (gain, power, mode, mbit, energy, mbit_per_j) in ORACLE.items():
    # The note prints the cap-hit row rounded to 0.853070, but evaluates it at
    # the exact cap-hit angle. Just past that angle the n_b=4 link is capped and
    # drops a MODCOD, so the row only reproduces at full precision.
    eval_angle = SEALED_CAP_HIT_DEG if angle == 0.853070 else angle
    p = f1.evaluate(eval_angle, nb, fixed_rf=(model == "b0"))
    tag = f"{angle:.6f} {model} n_b={nb}"
    check(f"{tag}: G_T", p.transmit_gain, gain, 5e-10)
    check(f"{tag}: p [W]", p.rf_power_w, power, 5e-6)
    check_eq(f"{tag}: mode", p.mode, mode)
    check(f"{tag}: Mbit/beam-step", p.bits_beam / 1e6, mbit, 5e-7)
    check(f"{tag}: energy [J]", p.energy_j, energy, 5e-6)
    check(f"{tag}: EE [Mbit/J]", p.ee_bit_per_j / 1e6, mbit_per_j, 5e-5)

print("\n6. Structural properties asserted by the sealed KAT")
angles = [f1.PATTERN_EDGE_DEG * i / 100.0 for i in range(101)]
for nb in f1.OCCUPANCIES:
    pts = [f1.evaluate(a, nb, fixed_rf=False) for a in angles]
    powers = [p.rf_power_w for p in pts]
    ees = [p.ee_bit_per_j for p in pts]
    mono_p = all(b - a >= -1e-13 for a, b in zip(powers, powers[1:]))
    strict_below = all(
        b - a > 0.0
        for a, b in zip(powers, powers[1:])
        if a < f1.BEAM_RF_CAP_W - 1e-9
    )
    mono_ee = all(b - a <= 1e-6 for a, b in zip(ees, ees[1:])) and ees[-1] < ees[0]
    check_eq(f"n_b={nb}: p non-decreasing in theta", mono_p, True)
    check_eq(f"n_b={nb}: p strictly increasing below cap", strict_below, True)
    check_eq(f"n_b={nb}: EE non-increasing and strictly lower at edge", mono_ee, True)

b0 = [f1.evaluate(a, 1, fixed_rf=True) for a in angles]
check_eq("b0: RF constant at the cap", {round(p.rf_power_w, 12) for p in b0}, {f1.BEAM_RF_CAP_W})
check_eq("b0: energy constant", len({round(p.energy_j, 9) for p in b0}), 1)
check_eq("b0: bits non-increasing",
         all(b.bits_beam - a.bits_beam <= 0.0 for a, b in zip(b0, b0[1:])), True)
check_eq("b0: mode at boresight", b0[0].mode, "QPSK 4/5")
check_eq("b0: mode at pattern edge", b0[-1].mode, "QPSK 1/2")

print("\n" + "=" * 72)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("ALL CHECKS PASSED — independent recomputation agrees with the sealed KAT.")
