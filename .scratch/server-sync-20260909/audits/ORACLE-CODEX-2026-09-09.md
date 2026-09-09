# Perfect-knowledge interaction ceiling — 2026-09-09

Status: **`DIAGNOSTIC_NOT_CLAIM`**

## Finding

**ORACLE_SET does not barely beat UNILATERAL.** Across 20 real TRAIN anchors, the perfect-knowledge bounded set selector improves pooled energy efficiency by **+6.359000% over the certified unilateral optimum**.

This is material set-level coordination headroom. The mechanism has value that unilateral optimisation alone does not capture; this diagnostic does **not** show that a learner can find it.

UNILATERAL itself improves pooled EE by **+664.355743% over BASELINE**. That first-stage gain is separate from the +6.359% coordination headroom and must not be attributed to the interaction head.

No gain came from serving fewer users. Summed full-endpoint served counts were 826 for BASELINE, 1,939 for UNILATERAL, and 1,957 for ORACLE_SET.

## Pooled energy efficiency

| Selector | Decoded bits | Joules | Pooled EE (bit/J) | Relative gain |
|---|---:|---:|---:|---:|
| BASELINE | 545,927,267,996.825 | 146,564.590466 | **3,724,823.753560** | reference |
| UNILATERAL | 1,660,779,577,104.985 | 58,332.519445 | **28,470,904.272641** | **+664.355743% vs BASELINE** |
| ORACLE_SET | 1,694,404,970,756.872 | 55,955.362098 | **30,281,369.063314** | **+6.359000% vs UNILATERAL** |

The number that answers the question is **+6.359000%**: the headroom left for set-level coordination after exhaustive cyclic unilateral best responses converged.

## Per-anchor results

`Served O/U/B` reports ORACLE_SET, UNILATERAL, and BASELINE full 48-boundary served counts.

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

Qualifying coalitions existed on **20/20 anchors**. Selected sizes ranged from 3 to 9 users. Twelve selected candidates were complete beam evacuations and eight were beam-occupant subsets. Victim-plus-top-contributor candidates were evaluated but were not selected.

## Evaluation protocol

- Four real `V025_PROBE_R2` TRAIN worlds × five anchors = **20 anchors**.
- BASELINE used the unchanged `nearest-eligible` incumbent assignment.
- UNILATERAL used deterministic cyclic best responses in ascending user order. Every legal physical assignment was evaluated; convergence required a complete pass with no improving move.
- ORACLE_SET began at that certified optimum and evaluated beam-occupant subsets, victim-plus-top-two/top-three physical interference contributors, and complete beam evacuations.
- Coalition membership came from occupancy and physical interference, not singleton-marginal ranking.
- Binary64 simulator outputs were promoted to exact rationals for \(F=B-\eta_{\rm ref}E\), with \(\eta_{\rm ref}=19,720,681.00172232\) bit/J.
- The literal served-count guard was applied against BASELINE.
- The **ten-second decision deadline was ignored entirely**. There was no timeout fallback or deadline-conditioned pruning.
- Selection used the corrected causal ACM at decision boundary 0; committed selectors were evaluated on the common full 48-boundary realised endpoint.

## Exact evaluation cost

- **259,672** unique decision-boundary configuration evaluations.
- **267,300** unilateral candidate comparisons.
- **21,540** unique mechanism-catalogue candidates.
- **21,514** new joint physical evaluations after cache reuse.
- **60** committed configurations × 48 boundaries = **2,880** committed boundary evaluations.
- **262,552 total physical boundary evaluations**.
- Complete run time: **694.562 seconds**.
- Three selection workers plus coordinator, four processes total, one numerical-library thread each, under `nice -n 10`.

The pooled totals were independently recomputed from every anchor and matched the receipt exactly. All **178 archived V0.25 physics tests** and **2 selector tests** passed.

## Provenance and limitations

The workspace tree `1728f6b0462f86d85618a4c73f4d1dd2d2c07376` exactly matches requested source commit `75c5c78c`.

Artifacts:

- [Report](/home/sat/mcrl-v025-oracle-ws/ORACLE-CEILING-2026-09-09.md)
- [Runner](/home/sat/mcrl-v025-oracle-ws/.scratch/oracle-ceiling/run_oracle_ceiling.py)
- [Raw receipt](/home/sat/mcrl-v025-oracle-ws/.scratch/oracle-ceiling/oracle-ceiling-result.json)
- Raw file SHA-256: `af5a0ae34fd511b1598ab79d004be311fb1f1ea2478ca276ecbe3e8c96c79a83`
- Embedded receipt SHA-256: `07c120297370f2b1a4826fce723950bccaf9e1a4e81007cda4ae30fae975fc29`

This does not establish unrestricted global optimality, learnability, deadline feasibility, generalisation, admission, or efficacy. It establishes the narrower requested finding:

**Set-level coordination has a measurable +6.359% pooled-EE ceiling above exhaustive unilateral optimisation here. The learner path is chasing real headroom rather than a null mechanism.**
