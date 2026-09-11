# Controller independent aggregate — oracle cells A-real(R1) and B-real(R1), evaluation set (PROVISIONAL)

Date: 2026-09-11 17:40 UTC. **Provisional until the oracle agent's report is written.** Computed by the controller from the raw
per-episode JSONs (`.scratch/h4-probe/results-oracle/{A,B}-real-R1-evaluation-fwd-ep00..23.json`, mirrored from sat), not from
the agent's aggregator. Reference = `A m=2dB` on the same 24 evaluation episodes, per-episode values from
`.scratch/h4-probe/results-lp/LP-prev-evaluation-c0-m2.json` (pooled 107,000,983.53 bit/J, bit-identical to the ceiling's
reference). Pooled = Σbits / Σjoules; paired = mean ± sem of per-episode relative EE differences; p10 over served user-steps
(rate > 0). Conditions: MODQN harness, 100 users, consumed `max` power, sat, pinned archive 427e6a91, per-episode reseeded,
one-step myopic oracles with realised counterfactuals, reference R1 = `A m=2dB`'s joint action, fixed user order 0..99.

| cell | pooled EE (bit/J) | vs rule | paired | served | lit beams | bits ratio | p10 (Mbit/s) | p10 / rule | parity max |Δ| |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A-real(R1) | 113,342,542.25 | +5.927 % | +5.67 ± 0.88 % (23/24) | 0.99925 | 58.05 | 0.972 | 27.47 | 0.271 | 0.0 |
| B-real(R1) | 138,591,214.31 | +29.523 % | +29.95 ± 1.03 % (24/24) | 0.99913 | 64.91 | 1.323 | 115.65 | 1.141 | 0.0 |

- **Agreement**: every value equals the oracle agent's own figures (`PROGRESS.md` §T2-11, §T2-14) to the printed digit.
- **Reading (unfloored, provisional)**: B-real exceeds A-real by **+23.60 percentage points** of the rule's EE; B-real shows no
  rate collapse (p10 1.14 × the rule's) and delivers 32 % more bits than the rule at 1.6 more lit beams — its gain is bits,
  not fewer beams. A-real is throughput-degenerate (p10 0.27 ×; the simultaneous best response herds).
- **Not a gate decision.** Amendment 4 §2 requires the **rate-floored** A-real and B-real (running, v4) and B2 condition 3
  (the extra value representable from the B2 student's observation). B2 is therefore a conditional branch to be **prepared
  in parallel now**, not declared passed.
