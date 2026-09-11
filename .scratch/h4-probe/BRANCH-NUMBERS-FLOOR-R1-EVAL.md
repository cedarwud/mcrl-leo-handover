# Branch numbers — rate-floored oracle cells, R1, 24 evaluation episodes (controller-computed, PROVISIONAL)

Date: 2026-09-11 18:22 UTC. **Computed by the controller**, not by the oracle agent: the agent's four v4 shards finished
B-real-floor R1 evaluation at 18:10:37 UTC and the agent was then killed by an API session limit before it could aggregate.
The 48 per-episode JSONs were mirrored from `sat:/home/sat/mcrl-v025-h4-probe-ws/results-oracle/` into
`.scratch/h4-probe/results-oracle/` and aggregated locally. **Provisional until the oracle agent re-derives them**; the agent
must cross-check on resume.

Conditions (identical for both cells and the reference): MODQN harness, 100 users; pooled Σbits/ΣJ divided once, full-buffer;
consumed per-beam `max` power; host sat, pinned archive `427e6a91…`; 24 **evaluation** episodes (env `9_111_000+i`, mobility
`9_112_000+i`), fresh env per episode; one-step myopic oracles with realised counterfactuals; reference joint action R1 =
`A m=2dB`'s action at each step; fixed user order 0..99; the declared rate floor (a move is disallowed if it drops any served
user below 50 % of its rate under the reference action at that step). Reference `A m=2dB` on the same set: **107,000,983.53
bit/J**, p10 101.40 Mbit/s, bits 3.108076e14.

| cell | pooled EE (bit/J) | vs rule | paired per-episode | served | lit beams | bits ratio | p10 (Mbit/s) | p10 / rule | parity max \|Δ\| |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A-real-floor** (simultaneous best response) | 113,531,833.46 | **+6.104 %** | +5.72 ± 0.95 % (23/24) | 0.99925 | 59.13 | 0.992 | 28.60 | **0.282** | 0.0 |
| **B-real-floor** (one sequential sweep) | 134,129,417.19 | **+25.353 %** | +25.71 ± 0.95 % (24/24) | 0.99887 | 66.93 | 1.321 | 165.46 | **1.632** | 0.0 |

**B-real-floor − A-real-floor = +19.25 percentage points of the rule's EE.**

(The unfloored cells, for comparison on the same set: A-real +5.93 %, p10 0.271 ×; B-real +29.52 %, p10 1.141 ×. Both floored
cells report `n_disallowed_floor_only` as absent, so the floor-only rejection count is not available from these files; the total
disallowed counts are 316,073 for A-floor and 415,758 for B-floor.)

## Reading against the declared rules (Amendment 1 §3; Amendment 4 §1 item 3 and §2)

1. **Rule 1** (A-real ≤ rule + 3.3 % → the exact difference-reward credit is dropped untrained): **does not fire** — A-real-floor
   is +6.10 %. **But** the cell is **throughput-degenerate** by the declared flag (p10 0.282 × the rule's, far below the 0.5 ×
   line; bits ratio 0.992 passes). Per Ruling 2 §2 a gain the rate floor does not protect does not count toward A/B/C, so
   A-real-floor's +6.10 % **cannot be carried into any claim**, and it authorises nothing on its own (Amendment 4 §2 already
   said this of the unfloored cell). The per-move floor cannot stop the collapse because the moves are **simultaneous**: each
   user's move passes the test against the reference action, yet the joint move herds (the agent measured 66–99 of 100 users
   moving per step with a ~4-step oscillation).
2. **Rule 2** (A-real wins and B-real ≤ A-real + 3.3 pp → the credit change alone is the fix, B1): **does not hold** (+19.25 pp).
3. **Rule 3** (B-real ≥ A-real + 3.3 pp → the learner needs current-step lighting information; the B2 path): **holds, by a wide
   margin**, and B-real-floor is **not** throughput-degenerate: served 0.99887, bits ratio 1.321, p10 1.632 × the rule's. The
   sequential oracle delivers 32 % more bits than the rule at 3.6 more lit beams — its gain is bits, not fewer beams.
4. **Rule 4** (only the joint corner is high): does not apply; the sequential cell is high.
5. **Rule 5** (the nominal-information cell of the chosen path must itself clear rule + 4.5 % with served ≥ 0.995 and the rate
   floor preserved): **currently FAILS for the B2 path.** The deployable sequential rules are throughput-degenerate on this set —
   LP-seq(1,0) +6.65 % but bits ratio 0.712 and served 0.99571; LP-seq(2,0) +8.92 % but served 0.98796 and p10 0.41 ×; the
   ceiling's nominal-information search +11.0 % with bits −51.7 %. By rule 5 this is the case "the realised cell wins but the
   nominal cell does not: the credit is right and the **information** is wrong", whose declared next step is an **observation
   redesign screen** (what to add to the per-user observation so a nominal sequential rule approaches the realised sequential
   oracle) — still before any training.

## Amendment 4 §2 (owner) — the three B2 entry conditions

| condition | status |
|---|---|
| 1. B-real − A-real ≥ +3.3 pp after the rate floor | **met** (+19.25 pp) |
| 2. service and the rate floor preserved in both cells | **partly**: B-floor yes (served 0.99887, p10 1.63 ×); **A-floor no** (p10 0.282 ×) |
| 3. the extra value representable from the B2 student's observation (T_SEQ `R_repr` ≥ 0.5 on the augmented observation) | **not yet measured** — needs the floored B-real **calibration** cells (5/24 at 18:18 UTC, running) and a clone trained on the augmented observation |

**Therefore: B2 is indicated but not entered.** Entering B2 is the owner's decision and requires condition 3; B1 stays as the
comparator. Nothing here changes any threshold, and no learner training is authorised by these numbers. The development lane
(Amendment 6, T0 anchor teacher) is unaffected: T0 is non-privileged and its E0 arms do not depend on this adjudication.
