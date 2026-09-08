# Differential physics and target-pipeline audit — 2026-09-08

## Verdict

The simulator implements the declared link budget, segment recurrence, beam
aggregation, PA/system power, interference membership, noise/load split,
fading, and pooled EE correctly in the tested domain.  The clean-room replay
found one live numerical implementation defect: the custom ascending Bessel
series perturbs interference enough to exceed the required `1e-6` threshold
in SINR, rate, and bits.  It is small (worst delivered-bits relative error
`2.93e-6`) and does not plausibly explain C3's lack of EE lift.

A second, non-live domain defect records the wrong S.465-6 `D/lambda < 50`
minimum angle (`2.4983 deg` instead of `2.0433 deg`).  The constant is not used
by the gain calculation, whose explicitly disclosed clipped near-axis
extension agrees with the thesis.  Thus it corrupts the stated standards
domain/census, not current link values.

The historical `16.4 -> 6.60 dB` SINR change is explained by interference, not
by a missing noise or gain factor.  Those medians are from different panels,
so their literal `9.8 dB` difference is not a paired causal estimate; the W27
paired ablation measured `7.34 dB`, and this audit measures `7.70–11.15 dB`.

No TEST split was opened.  No source or sealed artifact was modified.

## Scope and independent method

`reference_physics.py` was written from the requested notes, thesis equations,
constant docstrings, and the primary [ITU-R S.465-6 recommendation](https://www.itu.int/dms_pubrec/itu-r/rec/s/R-REC-S.465-6-201001-I%21%21PDF-E.pdf).
It imports no `mcrl.env` code.  It independently implements FSPL; gaseous,
scintillation, and signed shadow losses; exact Bessel `J1/J3` transmit gain;
the receive envelope and correct S.465 domain branch; `k*T*B`; unit-mean
Rician power; association-anchored power and feasibility; beam max; PA and
fixed power; physical-beam co-colour interference; Shannon/load; interval
bits; and pooled ratio-of-sums EE.

The read-only harness wraps `StepEnvironment` instance methods only to capture
otherwise hidden realized fading and intermediate physics.  It ran three
SHA-256-derived worlds (`5680416530117720853`, `1235782696574302922`,
`2768415667476064712`), 100 users, 30 steps, and all three requested policies:
270 full steps.  Reference geometry and every downstream value were rebuilt
outside the environment.  Two complete runs produced identical evidence SHA:
`c634f684e7d4831df9b15650c20296be2916e8c2e490e21b56775433b7cb71c4`.

## Ranked findings (`relative error > 1e-6`)

Classification: I = documented/standard rule differs; II = undocumented;
III = probable implementation defect.  Values are the maximum-error witness.

| Rank | Quantity | Environment | Reference | Rel. error | Class | First divergence | Source |
|---:|---|---:|---:|---:|:---:|---|---|
| 1 | inter-satellite interference (W) | 2.208629201e-20 | 2.202225294e-20 | 2.90793e-3 | III | W1/stay, step 14, u6 | `antenna.py:116`; `bessel.py:47-52,255-280` |
| 1 | intra-satellite interference (W) | 2.942637920e-15 | 2.940628704e-15 | 6.83261e-4 | III | W1/stay, step 0, u16 | same |
| 1 | total interference (W) | 3.099848654e-15 | 3.097839438e-15 | 6.48586e-4 | III | W1/stay, step 0, u16 | same |
| 1 | SINR (linear) | 0.5219514194 | 0.5219532899 | 3.58380e-6 | III | W1/random, step 12, u39 | same; `interference.py:396-399` |
| 1 | rate (bit/s) | 100987051.468 | 100987346.995 | 2.92638e-6 | III | W1/random, step 12, u39 | same; `link_budget.py:590-610` |
| 1 | interval bits | 3037690508.17 | 3037699397.62 | 2.92638e-6 | III | W1/random, step 12, u39 | same |
| 2 | S.465 minimum angle (deg) | 2.498270483 | 2.043298703 | 2.22665e-1 | I | static constant | `antenna.py:172-191` |

Finding 1 is one causal defect, not six independent defects.  The environment
uses its custom series for `|mu| <= 34`; its own comment concedes about
`5e-4` absolute error at 34.  The exact documented Bessel functions reproduce
the observed downstream sign and magnitude.  Replacing the transmit gain with
the captured environment values eliminates all other differences.

Finding 2 follows S.465-6 recommends 2: because `D/lambda ~= 40 < 50`,
`phi_min=max(2 deg,114(D/lambda)^-1.09)=2.0433 deg`.  The code applies the
`D/lambda >= 50` formula.  Actual gains still match the declared extension:
`G_R(0,0.759,1,2.043,2.498,48 deg) = (35,34.994,32,24.242,22.059,-10) dBi`
in both implementations (`antenna.py:197-217`).

All remaining maximum relative errors are below threshold: wanted power
`7.66e-13`, link power `9.24e-14`, beam RF power `2.59e-14`, PA supply
`1.27e-14`, system power `6.09e-16`, fixed power `2.17e-16`, served `0`.

## Focused physics checks and SINR root cause

- Interference membership is correct (`interference.py:384-399`): only the
  serving `(NORAD,cell)` is excluded; a same cell on another satellite remains.
  A crafted four-beam regression passes.  Fresh traces contain 208–3370 such
  cross-satellite memberships each, so this branch was exercised.
- Noise uses full `B^w=500 MHz/3`, independent of load (`step.py:214-217`).
  Only rate divides bandwidth by beam load (`link_budget.py:590-610`).
- Same-satellite interferers correctly receive the 35 dBi override
  (`antenna.py:224-235`); cross-satellite terms use angular separation.
- Rician power is unit mean at `K=20 dB`; shadow is signed zero-mean dB.
  The draw is shared per `(user,satellite)`, not per beam
  (`step.py:1327-1389`).  A 400,000-draw regression passes.
- Segment state resets on physical association change, persists through a
  dwell boundary when `(NORAD,cell)` is unchanged, and clears on outage
  (`step.py:770-862`).  Witness counts across traces: 6,782 association resets,
  3,846 dwell continuations, 253 outage clears, and 253 post-outage resets.
- Nominal versus realized recomputation changed only Rician/shadow factors:
  every other captured term had maximum absolute difference exactly zero.

W17's `16.4 dB` is at `CONTROLLER-FINDINGS-W17-2026-08-22.md:17-30`.
W27 reports with-interference `6.60 dB`, no-interference `13.84 dB`, and paired
penalty `7.34 dB` (`W27-REPLY-PROBES-2026-08-23.md:73-93`).  In fresh paired
traces, with-I medians are `0.315–1.366 dB`, no-I `9.818–12.030 dB`, and the
per-link median penalty `7.699–11.151 dB`; mean intra share is `0.858–0.975`.
Therefore co-colour interference is the approximately 10 dB term.  Different
world/policy panels explain why the absolute fresh and historical medians differ.

## C1/C2 target replay

The deterministic selection takes 12 or 13 evenly spaced rows from each of 16
mode-by-world shards for exactly 200 C1 and 200 C2 rows.

| Target | Rebuilt formula | Rows | Mismatches | Max error |
|---|---|---:|---:|---:|
| C1 focal | `dt*Delta R_u - lambda*dt*Delta P_system` | 200 | 0 | 0 |
| C1 nonfocal/identity | `dt*sum_(v!=u) Delta R_v`; additive identity | 200 | 0 | 0 |
| C2 candidate/reference/delta | mean OPS-3 persistence surplus, `-kappa` per lost offset, Q1-reference centered | 200 | 0 | 0 |

The stored rows contain rates and powers, but not ECEF geometry or fading
variates.  Consequently the target arithmetic is independently reconstructed
exactly from retained physical observables, while the underlying link budget
cannot be regenerated solely from those rows.  This is an evidence limitation,
not a replay mismatch.

## Defects confirmed

| Defect | File:line | Reproduction test | Affected artefacts | Successor fix location |
|---|---|---|---|---|
| OPS-3 lambda is not propagated | `ee_axis_ops3_live.py:879,926`; stale default `ee_axis_ops3.py:66,613` | `test_legacy_default_reproduces_nonbinding_cap_lambda_defect`: identical rates give C2 `-1.637204` through G0/default versus `-2.281140` through the nonbinding capped/repriced call | Original V0.14 NPZ Q2 targets are stale; R8 targets are repriced; R7/E1/S0/C3-S have a stale live call but do not use its target value (provenance below) | V0.25 live-surface API: require `lambda_bits_per_j` and forward it to every builder; `target_parity_suite.ops3_parity` is the isolated boundary |
| Executed oracle is not declared C3 | `oracle_marginals.py:100-118,372-389`; declaration `ee_axis_coalition_residual_c3.py:378-384` | `test_declared_c3_fixture_and_atomic_selection`: unchanged bits, energies `10,10,10,8`, lambda 1 gives executed `(0,0)` but `Psi=2`, `z3=(1,1)`, atomic `11` | The old oracle-marginal diagnostic and its reused-G0 J comparison; this does not invalidate R7's genuine coalition labels | V0.25 set decoder/oracle: score atomic profiles and re-optimize J separately after each demand transform; `target_parity_suite.declared_c3_oracle` is the isolated oracle |

## Lambda producer inventory and authenticated impact

The AST/constant scan in `lambda-provenance.json` finds 28 builder calls: 25
non-test production/archive calls can reach the stale default, one production
call is explicit, and two are the regression fixture.  The complete omitted
inventory is: live builder `src/.../ee_axis_ops3_live.py:926`; physical and
successor physical runners `physical/...:992`, `c1c2-successor-physical-evaluation/...:1037`;
candidate/contingency/E1 `c3-candidate-ca/...:1050`, `c3-contingency-f1/...:1312`,
`c3-existence-e1/...:998`; observability, R5, R6-fit, R7-balanced, R7-launch
composition/source adapters at respectively `986/880`, `986/880`, `986/880`,
`997/880`, `997/880`; R6 diagnostic `:1021`; oracle G0 `:226`; real-world
rehearsal `:358`; and both archived evidence trees (`c3-chatgpt-review-package`
and `c3-outside-opinions/.../evidence`) at copied live `:926`, F1 `:1312`, and
adapter `:880`.  The sole production explicit call is oracle capped `:256`.
The C1 APIs in `ee_surplus_targets.py:98,191`, `ee_axis_opening_runner.py:60`,
and `ee_axis_opening_source.py:445,522` all require lambda explicitly, so the
scan found no fallback-capable C1 producer.
The same scan records the two independent explicit stale authorities
`ee_axis_v06_c2_k1_state_authority.py:55` and `ee_axis_v07_c2_d2.py:70`;
they do not “fall back”, but a successor must not inherit them.

| Artefact | Value actually used for targets/selection | Receipt/config evidence |
|---|---|---|
| Original C1 opening rows and V0.14 NPZ Q2 targets | **stale** | C1 payloads and shard metadata record `0x1.443...`; seven NPZ SHA-256s begin `f5f38d`, `d9bc15`, `62fda3`, `79fc65`, `6791e4`, `0ac56c`, `08a180` |
| V0.20/R8 source targets and fitted Q1/Q2 | **repriced** | Q2 repricing result says new `0x1.c3c...`; R8 receipt SHA `e9f845...` binds `lambda_bits_per_j=0x1.c3c...`, target unit `normalized-repriced...`, checkpoint `d40a0f...`; current model-config SHA is `9eafcd...` |
| R7 | **repriced target; stale call is feature-only** | sealed result SHA `dfcc70...` binds source manifest `41e163...`; adapter emits `target_free_inference=true`, `diagnostic_lambda=0x1.c3c...`, `runtime_default_lambda_used_for_target=false` and recomputes at lines 815-823 |
| successor stage C | **no completed receipt exists** | pipeline `STATUS.md` SHA recorded in `lambda-provenance.json` says S1-S4/stage C blocked; provisional physical result SHA `f58fca...` binds repriced authority `a05ee8...`/checkpoint `d40a0f...`, with the same feature-only live path |
| E1 | **repriced objective; stale call is feature-only** | terminal SHA `0bc54f...`; panel binds `lambda=0x1.c3c...`, preflight `1d7402...`, repriced Q1/Q2 authorities |
| S0 | **eta, not OPS-3 lambda; inherits E1 feature path** | result SHA `ba496e...` binds E1 SHA `0bc54f...`, live-code SHA `684706...`, and exact `eta=0x1.d94f...` |
| C3-S | **eta, not OPS-3 lambda; inherits E1/S0 feature path** | config SHA `5427ba...` and terminal SHA `a66b48...` bind exact `eta=0x1.d94f...`, E1/S0 producer closure, and preflight `ee114c...` |

## Other 2026-08-31 defect tests

| Test | Result | Evidence |
|---|:---:|---|
| per-head bootstrap | **PASS** | `modqn.py:536-550` loops `obj_idx` and uses `target_nets[obj_idx]`; no head-0 reuse. |
| r1 aggregation | **PASS** | Per-user `R_u/P_system` contributions sum to instantaneous `sum R/P` (`energy_efficiency.py:251-262`), while the physical endpoint pools total bits and energy then divides (`v023_c1c2_successor_physical_runner.py:878-899`). `modqn.py:1300` is an episode logging scale, not the endpoint. |

## Executed versus declared C3 oracle

`declared_c3_oracle.py` implements the exact source decomposition:
`F=sum(bits)-lambda*E`, `Psi=F11-F10-F01+F00`, and
`z3_i=nonfocal_i+Psi/2`; selection is restricted atomically to 00/10/01/11.
The legacy comparator independently signs unilateral total surplus.  The
fixed fixture above proves these are different definitions.

The old-physics diagnostic reran one SHA-derived world (`5680416530117720853`),
the three fixed carriers, 30 steps each (90 anchors), with explicit repriced
lambda at every score.  “Marginal” below is pooled EE(selected)-EE(DROP_C3)
for the local two-user four-profile catalogue; it is diagnostic history, not
a successor efficacy/admission claim.

| Demand | Executed unilateral | Declared, reuse G0 J | Declared, per-regime J |
|---|---:|---:|---:|
| G0 uncapped | 49,543.515 | 93,359.619 | 93,359.619 |
| G1 200 Mb/s | 31,193.695 | 128,519.812 | 219,895.226 |
| G2 50 Mb/s | 25,891.527 | 23,637.088 | 59,511.510 |
| G3 10 Mb/s | 1,789.889 | 3,579.604 | 10,341.382 |

Units are bit/J. Re-optimizing J changes every capped regime and is always
higher on this finite catalogue. Evidence anchor SHA is `8ed717d1...` in
`declared-c3-oracle-marginals.json`; two reruns produced file SHA
`090bee75a9ded1dcd8624f22fabe2d222f2ecdcda66d90935a10e8aeba0c98f1`.

## Ambiguities and limitations

1. S.465 defines no envelope below `phi_min`; the thesis explicitly extends
   `32-25log10(phi)` to its 35 dBi clip.  The reference follows that extension.
2. Wanted power uses per-link power while interference uses beam-max radiated
   power.  The reference preserves this written asymmetry.
3. Shadow “loss” is signed zero-mean dB; negative draws act as gain and no
   linear-mean normalization is specified.
4. Rician draw ordering is unfrozen; differential replay consumes captured
   realized gains, while standalone generation uses two independent normals.
5. All-dark pooled EE is unspecified; the reference returns zero only for
   zero bits/zero energy and rejects positive bits/zero energy.
6. Target rows lack geometry/fading state, limiting replay as described above.
7. The final successor removes C3; “declared C3” could mean prior LC-SRS or
   later contingency D/F.  This audit uses last-frozen LC-SRS and names D/F.
8. Historical SINR medians are unpaired; only within-panel ablations are causal.
9. The documented project venv lacks SciPy, while system Python lacks `sgp4`.
   Reproduction uses system Python plus the project venv site-packages; SciPy
   supplies the independent Bessel reference and emits a NumPy-version warning.

## Artifacts and reproduction

- `reference_physics.py`: clean-room equations and executable anchors.
- `differential_audit.py`: read-only extractor and 270-step comparison.
- `target_replay.py`, `c3_oracle_comparison.py`: Parts 3 and 4.
- `target_parity_suite/`: importable explicit-lambda wrapper, declared-C3
  oracle, reversible physics extractor, and reward/endpoint identity check.
- Pytest summary: `12 passed, 1 warning in 0.25s` (the warning is the disclosed
  SciPy/NumPy version warning).
- `part2-results-run1.json`, `part2-results-run2.json`,
  `part3-target-replay.json`, `part4-c3-comparison.json`,
  `lambda-provenance.json`, `declared-c3-oracle-marginals.json`: evidence.
- Run: `bash .scratch/multi-catfish-v023-differential-audit/run_audit.sh`.
