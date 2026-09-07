# Prompt 1 — Astra Pro package-only clean-room adjudication

You are the fresh-context lead scientific adjudicator for a Multi-Catfish reinforcement-learning method. Use only the uploaded package; do not rely on previous chat history or browse the web.

Use the anti-anchoring two-pass protocol in `PASS1-READ-FIRST.md`. Do not open `START-HERE.md`, `CROSS-MODEL-STATE.md`, or the excluded reviewer files until you have recorded the requested pass-1 provisional account. In pass 2, report where your independent account agrees, disagrees, or finds an issue none of them identified. Do not erase the pass-1 verdict merely because another model used confident wording.

The fixed research requirement is exactly three Q networks and three training-time Catfish mechanisms, with one Main-only masked deployment action from `argmax(Q1+Q2+Q3)`. All three routes are intended to improve the same final ratio-of-sums EE; legacy route metrics do not matter. Do not solve the problem by deleting C3, adding a coordinator, changing the final EE equation, or claiming that every marginal must be positive by theorem.

Your purpose is not to endorse the current design. Treat the package's named blind spots as already known and search for unknown unknowns: a mistaken causal abstraction, leakage, unfair comparison, invalid estimator, non-identifiability, hidden coupling, statistically invalid stop rule, learner-policy mismatch, or a simpler formulation the current team has failed to ask about.

Perform the review in this order:

1. Reconstruct the action-to-EE causal graph from source and state which physical channels genuinely remain after conditioning on the C1 and C2 background.
2. Authenticate the sealed summaries and independent receipts that are actually present. Independently recompute packaged JSON where possible, and explicitly list claims that cannot be authenticated because raw shards/checkpoints are absent. Separate source prediction, oracle policy effect, deployable estimator effect, learner effect, and episode efficacy.
3. Audit V0.21's conditional expectation: full nonlinear-label expectation, keyed-field independence, anchor conditioning, compatibility invariance, post-centering support, B/N/E/R/P fairness, fixed-action timing, and whether the P control really isolates action-specific information.
4. Decide whether the one-anchor K=8/L=8 rule is scientifically suitable as rejection-oriented triage. Identify false-reject and false-pass modes. Do not quietly upgrade it into efficacy evidence.
5. Challenge the three-head premise at the correct level: distinguish “three useful causal views can exist” from “three learned marginal ablations will all be positive simultaneously.” Determine what structural conditions would make `FULL > each DROP > BASELINE` plausible, and whether current C1/C2/C3 meet them.
6. Re-audit C1 and C2 rather than assuming they are solved. State the minimum evidence still required before any 100/500ep three-head training is worth running.
7. Expected-ZR has failed its frozen one-anchor screen. Decide whether that failure diagnoses the estimator, the ZR target family, or the anchor/estimand; then rank no more than three genuinely different R3 target families. For each, specify what C1/C2 information it must exclude, what deployable state identifies it, and one fast falsifier. Do not resurrect the rejected CSE exact-additivity claim or tune another ZR variant against this outcome.
8. Give a bounded execution plan with stop rules. No endless variant ladder.

Required output:

- `Pass-1 provisional record` — causal graph, discrepancies, and token formed before prior reviews; reproduce it without retroactive edits
- `Executive verdict`
- `Five most important new findings` (at least two must not merely repeat START-HERE)
- `Evidence authentication and discrepancies`
- `Causal identifiability verdict for C3`
- `V0.21 fast-screen verdict`
- `C1/C2 reopen-or-hold verdict`
- `Minimum path to 100/500ep training`
- `Post-V0.21 ranked R3 alternatives`
- `What the paper may and may not claim now`
- End with exactly one token:
  - `PROCEED_FULL_EXPECTED_ZR_GATE`
  - `REVISE_FAST_SCREEN_ONLY`
  - `REDESIGN_R3_NOW`
  - `REOPEN_C1_C2_BEFORE_C3`
  - `STOP_THREE_HEAD_REQUIREMENT_STRUCTURALLY`

The experiment token inside `evidence/09-*` is immutable evidence; your final token is a separate reviewer recommendation. Map it as follows: a clean experimental GO may lead to `PROCEED_FULL_EXPECTED_ZR_GATE`; a repairable screen-design defect to `REVISE_FAST_SCREEN_ONLY`; a failed or non-identifiable Expected-ZR route to `REDESIGN_R3_NOW`; a material Q1/Q2 prerequisite failure to `REOPEN_C1_C2_BEFORE_C3`; and a demonstrated structural contradiction to `STOP_THREE_HEAD_REQUIREMENT_STRUCTURALLY`. State the experiment token separately and never rewrite it.

Evidence discipline: label every important statement `VERIFIED FACT`, `DERIVATION`, `INFERENCE`, `PROPOSAL`, or `UNKNOWN`. Do not treat TRAIN signs as efficacy. Report contradictions instead of averaging them away. `SOURCE-NOTES.md` defines the package's reproduction limit. If `evidence/09-v021-fast-screen-result.json` is absent, say the package is pre-result and adjudicate the method/decision tree without inventing the outcome.
