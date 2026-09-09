# PSI witness audit — 2026-09-09

DIAGNOSTIC_NOT_CLAIM.

1. Decode-threshold cliff via interference: **WITNESS FOUND**.
2. Airtime cliff via occupancy: **WITNESS FOUND**.
3. Exchange / swap: **WITNESS FOUND**.
4. Cap release: **WITNESS FOUND**.

The decisive answer is yes: the corrected engine produces Psi_A > 0 under the unchanged service guard. The positive terms are delivered-bit and/or physical-energy interactions, not a change to the user roster or a reimplementation of the score.

`NO_MODE` is not counted as served: **no**. The guard’s served count is based on positive decoded time (`served_PHY`), and a transmission with `m_tx = NO_MODE` contributes zero credited bits and zero served time.

## Frozen run

The workspace was populated from corrected commit `75c5c78c`. The run used the supplied calibration manifest, without recomputing or tuning eta_ref, lambda, kappa, thresholds, signs, seed, or the guard:

- eta_ref = lambda = 491164408115206640000000/24906057152504541 = 19,720,681.00172232 bit/J.
- kappa = 6139555101440083/7500000 = 818,607,346.8586777 bit/user-step.
- bandwidth = 500/3 MHz, RF cap = 1.65 W, r* = 50,000,000 bit/s, alpha = 0.10, interval = 30.08 s.
- fixed synthetic seed = 4448249745144365367, with the engine’s 48-boundary keyed fading stream.

The engine stores the handover term as a negative preference phi. I report the question’s convention as `Phi_cost = -kappa*phi`, so `F = B - eta_ref*E - Phi_cost`. The preference is additive and therefore cancels from Psi, although it remains in each reported d_i and F.

The table numbers below are decimal renderings in 10^9 bit-equivalent units; the linked JSON receipts retain exact rational `F_exact`, `d_exact`, and `psi_exact` values. `guard vs a0` is shown for every row, although production selection applies the guard to the joint candidate; singleton counterfactuals are intentionally evaluated even when they fail it.

## 1. Decode-threshold cliff via interference

Configuration: users u0,...,u4 are all at `g(0,0)`, where `g(y,z)=(sqrt(6371^2-y^2-z^2),y,z)` km. Satellites are ID 1 at `S(30°,0°)`, ID 2 at `S(10°,0°)`, and ID 3 at `S(90°,0°)`, all 550 km altitude. Beams are:

- X=(1,0), colour 0, target g(0,0);
- Y=(1,1), colour 0, target g(0,45);
- W=(1,2), colour 0, target g(0,0);
- Aaway=(2,0), colour 2, target g(0,150);
- G=(3,0), colour 2, target g(0,0).

Anchor `a0=[X,Y,G,G,G]`. A is u0: X→Aaway. B is u1: Y→W. The three G users are served sentinels. The real engine’s `b0` fixed-RF/ACM path scored all four assignments:

| field | evaluation | F (10^9 bit-equiv.) | B (10^9 bit) | E (J) | served | guard vs a0 |
|---|---|---:|---:|---:|---:|:---:|
| margin | a0 | 7.810542049 | 23.568227289 | 799.043665820 | 4 | yes |
| margin | a_A | 6.040054018 | 22.734986222 | 805.059665820 | 4 | yes |
| margin | a_B | 2.436768331 | 18.603757244 | 799.043665820 | 3 | no |
| margin | a_AB | 12.517161100 | 29.621396978 | 805.059665820 | 4 | yes |
| realised | a0 | 7.810542049 | 23.568227289 | 799.043665820 | 4 | yes |
| realised | a_A | 5.864257041 | 22.559189244 | 805.059665820 | 4 | yes |
| realised | a_B | 2.436768331 | 18.603757244 | 799.043665820 | 3 | no |
| realised | a_AB | 12.048325367 | 29.152561244 | 805.059665820 | 4 | yes |

margin: d_A=-1.770488030 Gb, d_B=-5.373773718 Gb; Psi=11.850880800 Gb; Delta F=4.706619052 Gb. Psi ledger: bits=11.850880800 Gb, energy=0.000000000 Gb.

realised: d_A=-1.946285008 Gb, d_B=-5.373773718 Gb; Psi=11.557842044 Gb; Delta F=4.237783318 Gb. Psi ledger: bits=11.557842044 Gb, energy=0.000000000 Gb.

At the first realised boundary, a0 has A decoded with `m_tx=QPSK 3/5`, while B is `NO_MODE` under the same-colour X/Y interference. In a_A, A’s away link is `NO_MODE` and B on Y decodes with `m_tx=QPSK 1/2`; A’s own credited bits fall from 4.964470044 Gb to zero and d_A is negative. In a_B, A on X and B on W remain co-channel and both are `NO_MODE`, so B-alone gains zero bits and d_B is negative. In a_AB, A is off the interfering satellite and B on W decodes with `m_tx=16APSK 2/3`, producing 10.548803999999996 Gb for B in the realised field. Thus the physical effect is removal of A’s same-satellite co-channel interference at a discrete ACM mode cliff. The joint Delta F is positive as well as Psi.

Exact coordinate payload and all 48-boundary traces: [mechanism1_fixedrf.json](/home/sat/mcrl-v025-witness-ws/analysis/mechanism1_fixedrf.json). Construction: [mechanism1_fixedrf.py](/home/sat/mcrl-v025-witness-ws/analysis/mechanism1_fixedrf.py).

## 2. Airtime cliff via occupancy

Configuration: users u0,...,u4 are all at g(0,0); satellite 1 is `S(60°,0°)` and satellite 2 is `S(90°,0°)`. X=(1,0), colour 0, targets g(0,0); Y=(1,1), colour 1, targets g(0,5); Z=(1,2), colour 2, targets g(0,-5); G=(2,0), colour 2, target g(0,0). Anchor `a0=[X,Y,Z,G,G]`. Movers are u1 and u2, both to X; u3/u4 stay on G. This gives a nonzero anchor service floor of two. The real engine’s `a-r0` rate-target path scored:

| field | evaluation | F (10^9 bit-equiv.) | B (10^9 bit) | E (J) | served | guard vs a0 |
|---|---|---:|---:|---:|---:|:---:|
| margin | a0 | -1.190510063 | 2.048126311 | 164.225382155 | 2 | yes |
| margin | a_1 | -0.997492068 | 2.048126311 | 133.682741758 | 2 | yes |
| margin | a_2 | -0.997438994 | 2.048126311 | 133.680050466 | 2 | yes |
| margin | a_{1,2} | 1.158034833 | 4.096252622 | 107.481604853 | 5 | yes |
| realised | a0 | -1.234087218 | 2.004549156 | 164.225382155 | 2 | yes |
| realised | a_1 | -1.041069224 | 2.004549156 | 133.682741758 | 2 | yes |
| realised | a_2 | -1.041016149 | 2.004549156 | 133.680050466 | 2 | yes |
| realised | a_{1,2} | 0.998251929 | 3.936469719 | 107.481604853 | 5 | yes |

margin: d_1=0.193017995 Gb, d_2=0.193071069 Gb; Psi=1.962455832 Gb; Delta F=2.348544895 Gb. Psi ledger: bits=2.048126311 Gb, energy=-0.085670480 Gb.

realised: d_1=0.193017995 Gb, d_2=0.193071069 Gb; Psi=1.846250083 Gb; Delta F=2.232339147 Gb. Psi ledger: bits=1.931920563 Gb, energy=-0.085670480 Gb.

X’s occupancy is 1 in a0, 2 after either singleton, and 3 jointly. The engine target modes are QPSK 1/4, QPSK 2/5, and QPSK 3/5; the first two cases select `NO_MODE`, while occupancy 3 creates enough back-off room for QPSK 1/4 to transmit. The joint serves u0,u1,u2 plus the two G sentinels. This is real credited delivery: the two singleton moves have zero mover/occupant bits, whereas the joint gives all three X users positive bits. The positive bit interaction dominates the negative energy interaction in the realised ledger.

The requested single-mover test was also executed: each singleton has Psi=0 exactly and served count 2. The conventional unloading direction was separately run with 13 users, anchor `[X×7,Y×3,Z×3]`, moves u0:X→Y and u1:X→Z; it also gave positive interaction, Psi=+0.561429578 Gb (margin) and +0.188897224 Gb (realised), with served count 13 in every evaluation. The guarded arrival receipt is [mechanism2_guarded.json](/home/sat/mcrl-v025-witness-ws/analysis/mechanism2_guarded.json); the unloading receipt is in [selected-witnesses.json](/home/sat/mcrl-v025-witness-ws/witness/selected-witnesses.json).

## 3. Exchange / swap

Configuration: satellite 1 is `S(60°,0°)`. Let L=g(0,-15), R=g(0,15); X=(1,0), colour 0, target L; Y=(1,1), colour 1, target R. User positions in ID order are `[R,L,L,L,R,R]`. Anchor is `[X,X,X,Y,Y,Y]`; A=u0 moves X→Y and B=u3 moves Y→X. Cross-interference is zero because the two beams have different colours. The real `a-r0` path scored:

| field | evaluation | F (10^9 bit-equiv.) | B (10^9 bit) | E (J) | served | guard vs a0 |
|---|---|---:|---:|---:|---:|:---:|
| margin | a0 | 0.737347727 | 4.096252622 | 170.323980950 | 6 | yes |
| margin | a_A | 0.113370810 | 3.297987911 | 140.731115108 | 4 | no |
| margin | a_B | 0.113370810 | 3.297987911 | 140.731115108 | 4 | no |
| margin | a_AB | 0.964853348 | 4.096252622 | 117.277487907 | 6 | yes |
| realised | a0 | 0.381467623 | 3.740372519 | 170.323980950 | 6 | yes |
| realised | a_A | -0.281335190 | 2.903281911 | 140.731115108 | 4 | no |
| realised | a_B | -0.140995279 | 3.043621822 | 140.731115108 | 4 | no |
| realised | a_AB | 0.608973244 | 3.740372519 | 117.277487907 | 6 | yes |

margin: d_A=-0.623976917 Gb, d_B=-0.623976917 Gb; Psi=1.475459455 Gb; Delta F=0.227505621 Gb. Psi ledger: bits=1.596529422 Gb, energy=-0.121069967 Gb.

realised: d_A=-0.662802814 Gb, d_B=-0.522462903 Gb; Psi=1.412771337 Gb; Delta F=0.227505621 Gb. Psi ledger: bits=1.533841304 Gb, energy=-0.121069967 Gb.

Each singleton changes occupancy from 3/3 to 2/4, leaves users on the source side in `NO_MODE`, loses F, and fails the six-user guard. The joint restores 3/3, keeps the occupancy target modes balanced, places each mover on its better-aligned beam, saves energy, serves all six, passes the guard, and improves F. The interaction is therefore a TDM occupancy/link-alignment coupling, not RF interference.

## 4. Cap release

Configuration: five users are at g(0,0), satellite 1 is `S(60°,0°)`, X=(1,0), colour 0, target g(0,45), and Y=(1,1), colour 1, target g(0,0). Anchor is `[X,X,Y,Y,Y]`; A=u0 and B=u1 both move X→Y. The real `a-r0` path scored:

| field | evaluation | F (10^9 bit-equiv.) | B (10^9 bit) | E (J) | served | guard vs a0 |
|---|---|---:|---:|---:|---:|:---:|
| margin | a0 | -4.340769421 | 2.048126311 | 323.969325969 | 3 | yes |
| margin | a_A | -3.706598283 | 3.297987911 | 334.434826078 | 4 | yes |
| margin | a_B | -3.706598283 | 3.297987911 | 334.434826078 | 4 | yes |
| margin | a_AB | 2.340968320 | 4.964470044 | 91.522923422 | 5 | yes |
| realised | a0 | -4.478763747 | 1.910131985 | 323.969325969 | 3 | yes |
| realised | a_A | -3.960964372 | 3.043621822 | 334.434826078 | 4 | yes |
| realised | a_B | -3.943421883 | 3.061164311 | 334.434826078 | 4 | yes |
| realised | a_AB | 2.013524552 | 4.637026276 | 91.522923422 | 5 | yes |

margin: d_A=0.634171137 Gb, d_B=0.634171137 Gb; Psi=5.413395466 Gb; Delta F=6.681737741 Gb. Psi ledger: bits=0.416620533 Gb, energy=4.996774933 Gb.

realised: d_A=0.517799374 Gb, d_B=0.535341863 Gb; Psi=5.439147060 Gb; Delta F=6.492288298 Gb. Psi ledger: bits=0.442372127 Gb, energy=4.996774933 Gb.

In a0 and either singleton, X’s attempted user is pinned at 1.65 W with `m_tx=NO_MODE` and zero credited bits. With both moves, X is removed from the active schedule and both movers become served on Y; the roster remains five users. Y occupancy 3→4→5 changes its target mode, and the joint 253.377402764-J energy saving supplies most of Psi. This is cap release through both real delivery and removal of wasted capped power; it is not denominator reclassification.

## Structural conclusion and execution receipts

Psi_A <= 0 does not hold identically. The engine can represent coupling: target mode and airtime depend on beam occupancy, transmit power is solved with cross-beam terms, decoding is thresholded, and energy includes active-beam/shared hardware and nonlinear PA effects. These executed four-point identities disprove additive separability. The cause in mechanisms 1–4 is respectively interference/ACM, occupancy/airtime/ACM, occupancy plus alignment, and capped-power/occupancy; it is not a score-decomposition defect. The separate additive Phi term cancels from Psi exactly.

Executed validations:

- `analysis/verify_new_witnesses.py`: PASS for the new physical interference and non-vacuous occupancy receipts.
- `witness/verify_evidence.py`: PASS for the existing swap/cap/occupancy receipts, exact identities, service guard, cap persistence, and mode-threshold decoding.
- `tests/physics_v025`: PASS (all tests).

The real scoring route was `resolve_configuration`/`AngleRateTPC_TDM` or `FixedRF` → `SharedArchitectureTape`/`score_setting` → `NetworkOutcome`/`network_objective` → `set_score_decomposition`. Scenario code only constructs ECEF positions and calls the archived channel helpers. It never reimplements B, E, ACM, decoding, or Psi.

Reproduction commands from the workspace root:

```bash
nice -n 10 env PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/sat/mcrl-leo-handover/.venv/bin/python -B analysis/mechanism1_fixedrf.py
nice -n 10 env PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/sat/mcrl-leo-handover/.venv/bin/python -B analysis/mechanism2_guarded.py
nice -n 10 /home/sat/mcrl-leo-handover/.venv/bin/python -B witness/run_witnesses.py
nice -n 10 /home/sat/mcrl-leo-handover/.venv/bin/python -B witness/verify_evidence.py
```

Evidence: [mechanism1_fixedrf.json](/home/sat/mcrl-v025-witness-ws/analysis/mechanism1_fixedrf.json), [mechanism2_guarded.json](/home/sat/mcrl-v025-witness-ws/analysis/mechanism2_guarded.json), [selected-witnesses.json](/home/sat/mcrl-v025-witness-ws/witness/selected-witnesses.json), and [verify_evidence.py](/home/sat/mcrl-v025-witness-ws/witness/verify_evidence.py).
