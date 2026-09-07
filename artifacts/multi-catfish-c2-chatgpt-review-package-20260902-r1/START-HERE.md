# START HERE — integrated Multi-Catfish C2/C3 adjudication package

Package date: 2026-09-02  
Package status: `REVIEW_INPUT__NO_C2_SELECTED__FABLE_STAGE1B_INTEGRATED`  
Scientific claim ceiling: **development-direction evidence only**

## Purpose

This package asks a fresh reviewer to select the next scientifically valid
step for Multi-Catfish MCRL after integrating the completed Fable 5.1
clean-room challenger lane. It is not a training package and does not authorize
a Q2 learner, a held-out claim, or any 500/1500/3000/9000-episode run.

The required deployed architecture remains frozen:

- `C1 -> Q1`, `C2 -> Q2`, and `C3 -> Q3`;
- one common safe mask;
- direct unweighted `Q1 + Q2 + Q3`;
- one argmax and one executed Main action;
- final efficacy measured only by matched canonical network ratio-of-sums EE,
  with the service guard.

The final research goal remains three positive marginals:

\[
\eta(Q_1+Q_2+Q_3)>\eta(Q_1+Q_3),
\]

\[
\eta(Q_1+Q_2+Q_3)>\eta(Q_1+Q_2),
\]

\[
\eta(Q_1+Q_2+Q_3)>\eta(Q_2+Q_3).
\]

Other pair-versus-singleton contrasts are diagnostics, not additional binding
requirements.

## Use the two prompts independently

Upload this same package to two separate fresh ChatGPT contexts:

1. `CHATGPT-REVIEW-PROMPT.md` performs the package-grounded formula, receipt,
   and project-decision audit without external research.
2. `CHATGPT-DEEP-RESEARCH-PROMPT.md` uses primary external literature to
   challenge the theoretical three-head premise and design a complementary C3.

Run them independently or in parallel; do not show either answer to the other
before both are complete. The first response is the project-evidence
adjudication. The second is an external-theory challenger, not a replacement
for package receipts. Return both responses for one later integration decision.

## Evidence status

The challenger receipt manifest and both preregistration hashes verify. The
25-entry check was run against the complete original challenger artifact, not
against this package's intentionally reduced copy. An
independent package script recomputes all six Stage 1b directions from raw
episode rows and matches the stored pooled and per-initialization summaries.
See `INTEGRATION-VERIFICATION.md` and
`verification/recompute_stage1b.py`.

All new outcome evidence is limited to six fresh **TRAIN** worlds, frozen Q1/Q3
lineages, and oracle Q2 surfaces. TEST was not opened, Q2 was not learned, and
no episode training occurred. Strict source closure did not pass because the
working source had drifted from the sealed V0.4 manifest; this is recorded in
the receipts. Consequently, none of the signs below is an efficacy result.

## Current verified picture

### Fresh matched Stage 1b block

| Direction | H-A pooled; lineages/worlds | Fable OPS-3 reading pooled; lineages/worlds |
|---|---:|---:|
| C2: FULL vs DROP-C2 | `+11.700%`; 3/3, 6/6 | `+9.480%`; 3/3, 6/6 |
| C3: FULL vs DROP-C3 | `-0.485%`; 0/3, 2/6 | `-2.687%`; 0/3, 0/6 |
| C1: FULL vs DROP-C1 | `+0.644%`; 3/3, 4/6 | `+5.892%`; 3/3, 6/6 |

The C2 direction therefore passed for both formulas tested by the challenger,
while the frozen C3 failed in both new-Q2 contexts. Both routes received the
preregistered mechanical decision `C3_CONTEXT_FAIL`. The overall service guard
also failed for both routes; in H-A's C2 comparison, FULL was below DROP-C2 by
exactly one served user-step out of 18,000.

Additional fresh-world diagnostics:

- H-A FULL versus Main: `+27.396%`;
- Q1+Q3 versus Q1: `-9.716%`, independently reproducing the earlier sealed
  `-10.286%` direction;
- H-A oracle Q2 versus Q1: `+0.723%`;
- Q1+H-A oracle Q2 versus Q1: `+1.339%`;
- Fable OPS-3-reading oracle versus H-A oracle: `-4.480%`.

These are diagnostics only. The matched block shifts the immediate bottleneck
from “is a physically useful C2 direction plausible?” to “can C3 be made
complementary to Q1 plus the new C2 while retaining the fixed three-head
architecture?”

### Mechanism census for H-A

The six-world TRAIN census found a real, action-specific deterministic segment
channel:

- continued-link next-step power forecast median relative error `0.335%`, p95
  `1.45%`, maximum `3.54%`; switchers were exact to floating-point precision;
- median within-anchor target spread `1.72` kappa units versus `0.245` for
  Q1+Q3, a ratio of `6.92`, with nonzero range at every anchor;
- a legal action beat the Q1+Q3 argmax on the H-A target at `62.4%` of anchors;
- oracle action flip rate `57.0%`;
- rate/energy variance shares approximately `49%/51%`;
- the Q1+Q3 policy held the incumbent at `40.1%` of decisions with one;
- `1.96%` of legal actions were infeasible by offset one, while the incumbent
  was infeasible in `0.038%` of eligible anchors.

This supports physical plausibility and decision-time discrimination, not
learned efficacy.

### Earlier C1/C3 context evidence

The clean-room audit found no arithmetic, pairing, leakage, matching, or
sign-filter defect in the old C1/C3 receipts. It did find that their positive
claims were context-bound:

- C1 was strongly positive beside the old harmful Q2 and remains positive in
  both fresh oracle-Q2 contexts, although its H-A marginal is small;
- C3's previous `+21.970%` and `+21.216%` confirmations both included the old
  harmful Q2; without it, Q1+Q3 versus Q1 was `-10.286%` in the sealed block
  and `-9.716%` on the fresh worlds;
- the frozen lambda0 came from an r1-greedy Main calibration rollout with
  objective weights `(1,0,0)`, not the `(0.5,0.3,0.2)` Main policy described in
  prose. C3 is lambda-invariant and C1 is uniformly shifted. The challenger
  proposes correcting the documentation, not recomputing lambda0.

The audit's five shared-authority edits remain proposals only. No shared
authority file was changed by this package.

The copied `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` is an immutable
orientation snapshot and still describes the earlier V0.7 state. For this
review, the later root integration files and V0.8 receipts describe the
post-snapshot evidence; they do not themselves enact an authority change.

## Candidate state after integration

### 1. H-A deterministic hold-horizon segment-timing surplus

H-A sums offsets 1..3, censors the hold after first infeasibility, and uses a
frozen non-focal context. It passed its mechanism census and C2-local Stage 1b
direction, but failed the full method gate because C3 was negative and the
service guard failed. Status: **run development candidate; not selected; no
learner authorized**.

### 2. Fable lane's OPS-3 reading

The challenger preregistered and ran an averaged, outage-penalized variant on
the same worlds. Its C2 direction was positive but its C3 marginal was more
negative. Status: **run development variant; not selected**.

Crucially, this is not the outcome of the current exact OPS-3 implementation.
The Fable runner differs materially in D2 projection, visibility, persistence,
interference, clock construction, background validation, and Q-surface gauge.
The gauge difference is argmax-invariant; the other differences can change
actions and outcomes. The `+9.480%` value must therefore be labelled only as
the **Fable lane's OPS-3 reading**.

### 3. Current exact OPS-3 Projected-Persistence Catfish

The exact formula and live adapter use a cloned native D2 tracker, 47 native
640-ms updates per future decision, projected D2 eligibility, physical
cell-centre visibility, absorbing persistence, projected frozen-background
interference, the exact native clock, and Main-reference centering. Its 29
targeted and 92 nearby physics tests passed. Its predeclared oracle worlds have
not been opened. Status: **mechanically verified provisional candidate; exact
outcome unrun**.

### 4. Fable orbital option value

The separate Fable option-value proposal remains unrun. Its branch-local
future option set, no-op/background convention, and causal interpretation are
not closed. Status: **unrun reserve hypothesis**.

H-C energy/cliff-only and H-B dwell-boundary control are fallback hypotheses,
not selected live formulas.

## Questions the fresh reviewer must decide

1. Is the six-world oracle screen valid as a direction screen, given its
   frozen-interference, unit-fading, gamma-inversion, frozen-context, step-0,
   source-closure, and service-guard limitations?
2. Does the evidence justify holding C2 fixed while redesigning C3 to measure a
   physical externality complementary to Q1 plus projected persistence?
3. Alternatively, is a two-head method scientifically acceptable, or should
   the acceptance structure change? The fixed user objective still prefers a
   genuine three-Catfish method, so any departure needs an explicit argument.
4. Should exact OPS-3 receive its already-frozen no-training oracle screen, or
   would that be redundant until the C3 decision is resolved?
5. What is the single next step, with a pre-outcome contract, compute class,
   and hard stop rule?

Do not rescue a route by rescaling Q3 or changing signs, seeds, thresholds,
horizons, outage terms, or lambda0 against observed outcomes.

## Reading order

1. Choose one prompt: `CHATGPT-REVIEW-PROMPT.md` for package adjudication or
   `CHATGPT-DEEP-RESEARCH-PROMPT.md` for the independent literature lane;
   each starts by reading this file.
2. `INTEGRATION-VERIFICATION.md`.
3. `fable-cleanroom-lane/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md`.
4. The Fable Stage 1b report, both frozen contracts, and H-A census report.
5. The exact OPS-3 formula contract, mechanics checkpoint, merge checkpoint,
   source, and tests.
6. The parallel-design adjudication and the unrun Fable option-value review.
7. The C1/C3 audit and old interaction/failure evidence as needed.
8. Use `EVIDENCE-MAP.md` and `SOURCE-PATH-MAP.md` for exact locations.

## Stop boundary

The reviewer must return one adjudication only. It must not modify files, run
the simulator, train a learner, open TEST, or invent a post-outcome rescue.
After the reply is returned, this package lane pauses for explicit integration.
