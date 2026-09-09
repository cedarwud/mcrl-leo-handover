# Perfect-knowledge interaction ceiling — 2026-09-09

Status: **`DIAGNOSTIC_NOT_CLAIM`**

## Finding

**ORACLE_SET does not barely beat UNILATERAL.** Across 20 real TRAIN anchors,
the perfect-knowledge bounded set selector improves pooled energy efficiency by
**+6.359000% over the certified unilateral optimum**. This is material
set-level coordination headroom on this finite panel and catalogue. The
mechanism therefore has value that unilateral optimisation alone does not
capture; this diagnostic does **not** show that a learner can find it.

UNILATERAL itself improves pooled EE by **+664.355743% over BASELINE**. The
large first-stage gain is separate from the +6.359% coordination headroom and
must not be attributed to the interaction head.

No gain came from serving fewer users. Summed full-endpoint served counts were
826 for BASELINE, 1,939 for UNILATERAL, and 1,957 for ORACLE_SET (20 anchors ×
100 users). ORACLE_SET served at least as many users as UNILATERAL on every
anchor and far more than BASELINE on every anchor.

## Pooled energy efficiency

Pooled EE is the ratio of summed successfully decoded bits to summed modelled
partial-payload joules; it is not a mean of anchor ratios.

| Selector | Decoded bits | Joules | Pooled EE (bit/J) | Relative gain |
|---|---:|---:|---:|---:|
| BASELINE | 545,927,267,996.825 | 146,564.590466 | **3,724,823.753560** | reference |
| UNILATERAL | 1,660,779,577,104.985 | 58,332.519445 | **28,470,904.272641** | **+664.355743% vs BASELINE** |
| ORACLE_SET | 1,694,404,970,756.872 | 55,955.362098 | **30,281,369.063314** | **+6.359000% vs UNILATERAL** |

The number that answers the question is **+6.359000%**: it is the measured
headroom left for set-level coordination after exhaustive cyclic unilateral
best responses have converged.

## Per-anchor results

“Qualifies” means the selected joint candidate strictly improved exact
decision-boundary \(F=B-\eta_{ref}E\) over UNILATERAL and passed the literal
served-count guard. `Served O/U/B` reports the full 48-boundary ORACLE_SET,
UNILATERAL, and BASELINE served counts, respectively. The evaluation column is
the number of unique exact decision-boundary configurations evaluated for that
anchor.

| Anchor | Qualifies | Coalition size | Selected family | EE gain (bit/J) | EE gain vs U | Served O/U/B | Exact evals |
|---|:---:|---:|---|---:|---:|---:|---:|
| W1/A0 | yes | 3 | complete-beam-evacuation | 1,504,611.517 | 4.798098% | 99 / 98 / 43 | 10,324 |
| W1/A1 | yes | 4 | complete-beam-evacuation | 1,996,332.029 | 5.657002% | 99 / 99 / 37 | 15,461 |
| W1/A2 | yes | 4 | complete-beam-evacuation | 3,430,211.276 | 13.947100% | 98 / 97 / 40 | 14,245 |
| W1/A3 | yes | 8 | complete-beam-evacuation | 3,440,575.463 | 17.440614% | 99 / 90 / 35 | 10,324 |
| W1/A4 | yes | 6 | complete-beam-evacuation | 306,721.750 | 0.847685% | 99 / 99 / 43 | 13,362 |
| W2/A0 | yes | 3 | beam-occupant-subset | 709,637.969 | 2.248164% | 99 / 99 / 33 | 11,651 |
| W2/A1 | yes | 3 | beam-occupant-subset | 1,291,459.323 | 3.289780% | 98 / 98 / 44 | 14,699 |
| W2/A2 | yes | 6 | complete-beam-evacuation | 694,006.354 | 2.276230% | 100 / 100 / 45 | 12,286 |
| W2/A3 | yes | 3 | beam-occupant-subset | 527,398.247 | 3.201307% | 98 / 98 / 36 | 9,543 |
| W2/A4 | yes | 5 | complete-beam-evacuation | 4,082,660.072 | 15.274432% | 98 / 97 / 58 | 10,118 |
| W3/A0 | yes | 4 | complete-beam-evacuation | 1,376,292.100 | 4.874514% | 96 / 96 / 43 | 12,528 |
| W3/A1 | yes | 3 | beam-occupant-subset | 2,353,249.221 | 7.088961% | 99 / 98 / 43 | 11,473 |
| W3/A2 | yes | 3 | beam-occupant-subset | 651,798.789 | 2.511770% | 97 / 96 / 50 | 11,957 |
| W3/A3 | yes | 4 | beam-occupant-subset | 2,500,125.987 | 11.007593% | 95 / 93 / 42 | 14,603 |
| W3/A4 | yes | 4 | beam-occupant-subset | 2,467,430.908 | 7.119144% | 93 / 91 / 28 | 12,825 |
| W4/A0 | yes | 4 | complete-beam-evacuation | 643,984.504 | 1.829085% | 97 / 97 / 33 | 14,405 |
| W4/A1 | yes | 3 | beam-occupant-subset | 1,672,845.681 | 5.115104% | 97 / 97 / 47 | 17,758 |
| W4/A2 | yes | 3 | complete-beam-evacuation | 1,992,776.001 | 6.223486% | 99 / 99 / 53 | 11,289 |
| W4/A3 | yes | 5 | complete-beam-evacuation | 2,276,207.018 | 9.197952% | 100 / 100 / 39 | 18,676 |
| W4/A4 | yes | 9 | complete-beam-evacuation | 759,588.018 | 2.284418% | 97 / 97 / 34 | 12,145 |

Qualifying coalitions existed on **20/20 anchors**. Selected sizes ranged from
3 to 9 users. Twelve selected candidates were complete beam evacuations and
eight were beam-occupant subsets. Victim-plus-top-contributor candidates were
evaluated but were not selected on this panel. The exactly reconstructed
\(\Psi_A\) was positive for every selected coalition; no sign filter was used.

## What was evaluated

- **Anchors:** four real `V025_PROBE_R2` TRAIN worlds × the first five decision
  anchors = **20 anchors**. Each world used one detached immutable tape shared
  by every selector. No TEST or claim-panel world was opened.
- **BASELINE:** the unchanged `nearest-eligible` incumbent assignment from the
  corrected V0.25 engine.
- **UNILATERAL:** deterministic cyclic best response in ascending user order.
  At each user visit, every legal physical assignment was evaluated and the
  best strict, service-guarded \(F\) improvement was committed. Convergence
  required a complete pass with no improving move. Across the panel this took
  99 passes, accepted 1,960 single-user moves, and made 267,300 candidate
  comparisons. This is a certified coordinate-wise optimum, not a global joint
  optimum.
- **ORACLE_SET:** began from that certified optimum and evaluated a fixed
  mechanism-derived bounded catalogue: within-beam occupant subsets of sizes
  2–4 (fixed total cap 1,024), each victim with its top two and top three
  positive physical interference contributors, and complete beam evacuations
  to every common legal destination. Coalition membership was determined by
  occupancy and nominal received interference per RF watt/TDM share—not by
  ranking users on singleton marginal size. Every complete candidate profile
  was physically evaluated; no unilateral effects were summed to choose it.
- **Exact interaction:** binary64 simulator outputs were promoted to exact
  rationals for \(F=B-\eta_{ref}E\), with frozen
  \(\eta_{ref}=19,720,681.00172232\) bit/J. For the selected set, the exact
  joint value and all matching singleton values reconstructed
  \(\Psi_A=F(A)-F(\varnothing)-\sum_i[F(i)-F(\varnothing)]\).
- **Causal/realised boundary convention:** the selector used the corrected
  causal ACM at realised decision boundary 0, held for the engine’s 30.08-s
  selection snapshot. The three committed profiles were then evaluated on the
  complete common 48-boundary realised endpoint. This is a privileged oracle
  ceiling, not a deployable information contract.
- **Service guard:** selection-time served count could not be below BASELINE’s
  at the same anchor. BASELINE remained in both searches.
- **Deadline:** the **ten-second decision deadline was ignored entirely**, as
  requested. There was no timeout fallback, pruning, or deadline-conditioned
  choice. This measures a ceiling, not a deployable policy.

## Exact evaluation cost and integrity

The full panel performed:

- **259,672** unique exact selection-configuration evaluations, each at the
  decision boundary;
- **267,300** unilateral candidate comparisons (cache hits explain why this is
  larger than unique selection evaluations);
- **21,540** unique mechanism-catalogue candidates enumerated, of which
  **21,514** required new physical evaluations after reuse of terminal
  singleton sweeps;
- **60** unique committed configurations evaluated at 48 boundaries each =
  **2,880** committed physical boundary evaluations;
- **262,552 total physical boundary evaluations** (selection plus committed);
- 694.562 s (11 min 34.562 s) for the complete 20-anchor run, using three
  selection workers plus the coordinator (four processes total), one thread per
  BLAS/OpenMP library, under `nice -n 10`.

The pooled totals above were independently recomputed from all per-anchor
bits/joules and matched the stored summary exactly. The embedded receipt hash
recomputed successfully.

## Provenance and limitations

The workspace was already clean and committed when opened. Its tree
`1728f6b0462f86d85618a4c73f4d1dd2d2c07376` exactly matches requested source
commit `75c5c78c`; local baseline commit was `3d48108`. The corrected causal ACM
is therefore the pinned authority.

Reproducible artifacts:

- runner: [`.scratch/oracle-ceiling/run_oracle_ceiling.py`](.scratch/oracle-ceiling/run_oracle_ceiling.py)
- raw per-anchor receipt: [`.scratch/oracle-ceiling/oracle-ceiling-result.json`](.scratch/oracle-ceiling/oracle-ceiling-result.json)
- raw file SHA-256: `af5a0ae34fd511b1598ab79d004be311fb1f1ea2478ca276ecbe3e8c96c79a83`
- embedded receipt SHA-256: `07c120297370f2b1a4826fce723950bccaf9e1a4e81007cda4ae30fae975fc29`

This is finite-panel oracle evidence for the declared bounded candidate family.
It establishes neither unrestricted global joint optimality, learner
approximation quality, deadline feasibility, generalisation, admission, nor
efficacy. The appropriate conclusion is narrower but decisive for the stated
diagnostic: **set-level coordination has a measurable +6.359% pooled-EE ceiling
above exhaustive unilateral optimisation here, so the learner path is chasing
real headroom rather than a null mechanism.**
