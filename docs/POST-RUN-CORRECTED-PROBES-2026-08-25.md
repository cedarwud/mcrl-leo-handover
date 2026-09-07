# Corrected P2/P3/P7 post-run record (2026-08-25)

**Status: COMPLETE. P6 remained BLOCKED at the result gate; corrective R2 was
subsequently sealed and must pass server validation before training.**

This is the formal rerun required by the runtime-correction ruling. It used the
result-before execution addendum, the byte-preserved 2026-08-25 prereg seal,
the frozen 373-file TLE view, and a fresh Ubuntu-server checkout. The runner
completed every arm and then returned status 2 because corrected P3 changed
the Q-F input. That exit is the intended scientific stop, not a crash.

## 1. Execution receipt

Output root:
`artifacts/probes-2026-08-25-rerun01/`

| Probe | Arms | Episodes per arm | Decision rows per arm |
|---|---:|---:|---:|
| P2 | `N = 2, 3, 4` | 200 | 200,000 |
| P3 | nearest / random / stay | 200 | 200,000 |
| P7 | main / sensitivity | 100 | 100,000 |

The execution-manifest self-digest is
`e78371f1725697d6c12f521af49d9f365bd6156eb62871ceb78e477e4f3049af`.
The byte SHA-256 values used by the R2 evidence gate are:

| Artifact | SHA-256 |
|---|---|
| `summary.json` | `8fb0ac591b3d2297747699e54520c090e2aa0e7cb5830b120ab634ee41fa4028` |
| `execution-manifest.json` | `5390ac254b79ebb0d17175e5adc588afc3c5564adb4823a6205dff58d45013e7` |
| `p3-stay-if-possible.json` | `1f49d8cb81854fac882f6203365808e7b94bc11195fa65d6a25fe9996b1a37c9` |

## 2. P3 calibration result

The selection mapping consumes only `stay-if-possible`, as frozen. It produced
200,000 decision rows and 198,910 served rows.

| Quantity | Corrected observation | Prior resolved value | Verdict |
|---|---:|---:|---|
| `c1`: served-step p95 of `r1` | `2029238.4328742754` bit/J | `2471140.576` bit/J | mismatch |
| `c3`: rounded served-step p95 of `abs(r3)` | `6` users | `6` users | match |

The `c1` comparison was presealed at three decimal places solely because the
prior literal had three decimals: `2029238.433 != 2471140.576`. The Q-F rule
itself says a continuous bit/J value is not rounded. Therefore the deterministic
R2 resolution is the full raw p95, `2029238.4328742754`, not the comparison
string `2029238.433`.

Additional mechanism diagnostics are descriptive, not trained-policy claims:

- strict first-index `r1`/`r3` argmax agreement: `0.111385`;
- setwise agreement under the large `r3` tie set: `0.999845`;
- per-step `r1`/`r3` correlation: `0.2364674563`.

This supports the earlier concern: `r3` is active, but its current load-count
objective has a very broad best-action tie set. It can affect `r1` through
selection, yet it supplies weak fine-grained action discrimination. This is
evidence for later Catfish design work, not authority to change the baseline
before corrected training finishes.

## 3. P7 warm-start effect

| Arm | Outage | Served | Power gate | Mask gate |
|---|---:|---:|---|---|
| main: uniform episode length | `0.06312` | `0.93688` | binding | binding |
| sensitivity: fixed segment age 6 | `0.05207` | `0.94793` | binding | binding |

The main arm is 1.105 percentage points above the sensitivity arm. Both are far
above the defective-run estimate near one percent. The age-overwrite bug was
therefore scientifically material; the old P6/main completion cannot be
rehabilitated as the intended baseline.

## 4. P2 sensitivity result

| N | System power p50 (W) | Power swing (W) | Link EE p50 (bit/J) | Link EE p95 (bit/J) | Rekey rate |
|---:|---:|---:|---:|---:|---:|
| 2 | 262.654 | 140.563 | 419,708 | 2,220,494 | 0.01981 |
| 3 | 264.765 | 139.594 | 381,953 | 2,108,500 | 0.02716 |
| 4 | 258.901 | 140.563 | 337,779 | 2,029,238 | 0.03182 |

P2 does not reopen Q-E: the predeclared re-key mapping still resolves `N = 4`.
It does show that the affected runtime changes moved the descriptive power,
outage and EE distributions enough that the old post-run report must remain
historical only.

## 5. Training gate

The permitted transition is:

1. preserve the first 2026-08-25 seal and every corrected-probe byte;
2. create `PREREG-FROZEN-2026-08-25-R2.json` by applying only Q-F's already
   declared mapping to the full raw served-step p95;
3. mechanically verify the old seal digest, protocol digest, manifest digest,
   evidence hashes, row counts, policy identity, raw p95, unchanged `c3`, and
   the exact R2 resolved value;
4. only then run the frozen three-arm P6 sweep and independent main training in
   a fresh output directory on the Ubuntu server.

R2 now exists with self-digest
`3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4`
and byte SHA-256
`8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543`.
The local evidence gate passes. P6 remains blocked until the same gate and live
environment validation pass on the Ubuntu server. Passing them authorizes
execution, not scientific acceptance. Catfish integration and thesis result
promotion remain blocked until corrected P6/main completes and receives a
separate post-run interpretation.
