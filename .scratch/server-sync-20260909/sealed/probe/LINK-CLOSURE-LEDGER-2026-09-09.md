# V0.25 link-closure ledger — 2026-09-09

Status: `SMOKE / VALIDITY CERTIFICATE`, TRAIN-only. This is an independent link-budget calculation, not a performance result. The executable ledger is `build_stage4h_link_ledger.py`; it deliberately imports no `mcrl` module and uses the link equation directly.

## Assumptions and boundaries

- Boresight representative: 550 km slant, 90° elevation, zero pointing loss.
- Half-power edge: 1,100 km slant, 25.801425° elevation for a 550 km circular-altitude geometry, and exactly 3 dB transmit-pattern loss at half of the declared 3.32° full HPBW.
- RF cap 1.65 W; peak transmit gain 2,000 = 33.010300 dBi; receive gain 35 dBi; 20 GHz carrier; occupied reuse-3 bandwidth 166.666667 MHz.
- `T_sys = 150 + 290(10^0.12−1) = 242.294454 K`, hence terminal `G/T = 11.156565 dB/K` and noise power `5.575393e−13 W` (−122.539 dBW).
- Nominal path loss contains free-space and elevation-scaled gaseous loss. Shadow, Rician fading and deterministic scintillation are not silently folded into nominal gain; their complete-product tenth-percentile reserve enters the wanted-link mode prediction separately.
- The n=1/2/4 fixture is one isolated co-channel beam. TDM makes one member instantaneous at a time, so intra-beam `C/I = +∞`; n changes airtime and the rate-target MODCOD, not instantaneous cochannel interference. The simulator reconciliation uses zero cross-gain for exactly that reason.

## Scalar link equation at the RF cap

`C/N = EIRP − FSPL − L_gas + G/T − k − 10log10(B)` with exact-SI `k = −228.599168 dBW/K/Hz` (−228.6 rounded).

| geometry | EIRP (dBW) | FSPL (dB) | pointing (dB) | gas (dB) | G/T (dB/K) | B (MHz) | C/I (dB) | C/N at cap (dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| boresight | 35.185139 | 173.275637 | 0.000000 | 0.250000 | 11.156565 | 166.666667 | +∞ | 19.196748 |
| half-power edge | 32.185139 | 179.296237 | 3.000000 | 0.574378 | 11.156565 | 166.666667 | +∞ | 9.851770 |

The edge penalty is 9.344978 dB: 6.020600 dB additional FSPL, 3 dB pointing loss, and 0.324378 dB additional gas loss.

## Load, mode, and headroom ledger

The common implementation allowance is included once in each threshold: `Γ_dB = Es/N0_ideal + 1.7 − 10log10(1.2)`. The lowest threshold is QPSK 1/4 at −1.441812 dB. The listed RF power is the nominal no-interference setpoint; the cap-headroom comparison is independent of the power-control implementation.

| geometry | n | required aggregate SE | rate-target mode / threshold | nominal RF setpoint (W) | cap headroom (dB) | q10 | predicted wanted-link SINR (dB) | transmitted mode / threshold | lowest-mode comparison |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| boresight | 1 | 0.300 | QPSK 1/4 / −1.441812 | 0.014244 | 20.638560 | 0.774949 | −2.549 | `NO_MODE` | below −1.441812 |
| boresight | 2 | 0.600 | QPSK 2/5 / 0.608188 | 0.022836 | 18.588560 | 0.774949 | −0.499 | QPSK 1/4 / −1.441812 | clears |
| boresight | 4 | 1.200 | QPSK 3/4 / 4.938188 | 0.061891 | 14.258560 | 0.774949 | 3.831 | QPSK 3/5 / 3.138188 | clears |
| half-power edge | 1 | 0.300 | QPSK 1/4 / −1.441812 | 0.122497 | 11.293582 | 0.520459 | −4.278 | `NO_MODE` | below −1.441812 |
| half-power edge | 2 | 0.600 | QPSK 2/5 / 0.608188 | 0.196393 | 9.243582 | 0.520459 | −2.228 | `NO_MODE` | below −1.441812 |
| half-power edge | 4 | 1.200 | QPSK 3/4 / 4.938188 | 0.532262 | 4.913582 | 0.520459 | 2.102 | QPSK 1/2 / 1.908188 | clears |

## Simulator reconciliation

An independently constructed linear gain (`G_tx × FSPL_gain × gas_gain × G_rx`) was passed to the public scalar architecture only for reconciliation. It returned the same setpoint powers to displayed precision. With realised fading fixed to unity and the sealed q10 mode rule:

| geometry | n | engine target | engine m_tx | decode flag | nominal power-feasible | 50-Mbit/s target attained |
|---|---:|---|---|---|---|---|
| boresight | 1 | QPSK 1/4 | `NO_MODE` | false | true | false |
| boresight | 2 | QPSK 2/5 | QPSK 1/4 | true | true | false |
| boresight | 4 | QPSK 3/4 | QPSK 3/5 | true | true | false |
| half-power edge | 1 | QPSK 1/4 | `NO_MODE` | false | true | false |
| half-power edge | 2 | QPSK 2/5 | `NO_MODE` | false | true | false |
| half-power edge | 4 | QPSK 3/4 | QPSK 1/2 | true | true | false |

This is internally consistent: “power-feasible” describes the nominal target setpoint, whereas decode and delivered rate describe the separately selected `m_tx` and realised outcome. A lower transmitted mode may decode yet fail the 50-Mbit/s airtime target.

## Beam capacity closure

The maximum frozen mode is 32APSK 9/10 with `4.453027 / 1.2 = 3.710855833 bit/s/Hz`. Therefore one colour beam carries at most:

`3.710855833 × 166.6666667 MHz = 618.475972 Mbit/s`.

Twelve users require 600 Mbit/s aggregate and have an eligible mode (32APSK 8/9). Thirteen require 650 Mbit/s, above 618.475972 Mbit/s, so n=13 is the first occupancy infeasible at any SINR. This reproduces the audit’s 618.476 Mbit/s and maximum n=12 exactly.
