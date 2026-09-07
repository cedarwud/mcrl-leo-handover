# Prompt 2 — Astra Pro Deep Research on the missing third EE head

Use Deep Research and the uploaded package. Treat package files as project-specific evidence and external sources as literature evidence; never blur the two.

Use the anti-anchoring two-pass protocol in `PASS1-READ-FIRST.md`. Conduct the literature search and record a provisional answer before opening `START-HERE.md`, `CROSS-MODEL-STATE.md`, or the excluded reviewer files. Use them only in pass 2 to expose disagreements and missing questions, not as authority. Preserve any independently derived conflict instead of silently conforming to a prior reviewer.

Research question:

Can a three-head, one-action policy for LEO multi-beam handover be designed so that three distinct training-time counterfactual views each have positive marginal value for the same final ratio-of-sums EE, especially when the third view captures spatial load sharing / beam consolidation under stochastic fading? The project's frozen conditional Expected-ZR fast screen failed: determine whether that result rejects the estimator, the ZR target family, or the chosen initial-anchor estimand, and identify the strongest principled replacement.

Search primary sources first: peer-reviewed papers, original conference/journal articles, authoritative technical standards, and foundational method papers. Prefer recent satellite/LEO resource-allocation work where available, but include foundational work needed for causal credit assignment. Do not rely on generic blogs or secondary summaries for substantive claims.

Cover these literature lanes:

1. Difference rewards, counterfactual baselines, wonderful-life utilities, COMA-style credit assignment, value decomposition, monotonic mixing, and conditions for local utilities to align with a global scalar objective.
2. Multi-objective versus single-objective multi-head RL: when auxiliary heads improve a common endpoint and when destructive interference makes all-positive ablations structurally unlikely.
3. Ratio-of-sums EE optimization, Dinkelbach/surplus formulations, fixed-multiplier limitations, and stochastic-policy evaluation.
4. Conditional expectation under fading, Jensen effects through Shannon/log/min/max/gating, distributional or risk-aware value prediction, and privileged-teacher-to-deployable-student transfer.
5. Beam activation, load-aware association, bandwidth sharing, max-power beam accounting, sleep modes, and energy savings from user/beam consolidation in satellite or wireless systems.
6. Public-good/shared-cost attribution: Shapley value, cost sharing, submodularity, potential games, joint-action effects, and fast approximations that do not falsely claim unilateral additivity.

Do more than summarize papers. Map each relevant result to this project's constraints:

- exactly Q1/Q2/Q3 and one masked sum/argmax;
- no deployment coordinator or joint decoder;
- C1 is focal-now EE surplus;
- C2 is temporal/future EE surplus;
- C3 must add a non-overlapping deployable spatial view;
- final objective is ratio-of-sums EE only;
- desired but unproved ordering is FULL > each one-head ablation > baseline.

Explicitly answer:

1. Is the desired ablation lattice theoretically reasonable, merely empirically possible, or structurally inconsistent under these constraints?
2. Does taking `E[complete nonlinear ZR label | deployable state]` preserve the right decision signal, or can joint beam-extinction/public-good effects remain unidentifiable regardless of sample count?
3. What is the strongest control to distinguish action-specific C3 knowledge from a generic “do not light new beams” support bias?
4. Given the observed Expected-ZR failure, which one genuinely different R3 family has the best combination of causal validity, learnability, low formula complexity, and compatibility with one-action deployment?
5. What minimum experimental design is publication-defensible before 100/500ep and before 9000ep? Include world/seed clustering, ablation arms, service/noninferiority, and multiple-comparison considerations.
6. Which current paper story is scientifically defensible without overstating novelty or efficacy?

Required deliverable:

- a `Pass-1 provisional record` formed before prior reviews and reproduced without retroactive edits;
- concise executive answer;
- evidence table with direct links/DOIs and primary-source quotations kept brief;
- a project-to-literature causal map;
- theorem/assumption/empirical-claim separation;
- ranked assessment of Expected-ZR and at most three alternatives;
- a minimal pre-outcome experimental protocol;
- a “blind spots the project team did not ask about” section;
- paper claim ceiling and novelty wording;
- final decision token exactly one of:
  - `EXPECTED_ZR_IS_PRINCIPLED__TEST_IT`
  - `EXPECTED_ZR_CANNOT_IDENTIFY_JOINT_GAIN__REDESIGN`
  - `THREE_HEAD_LATTICE_IS_PLAUSIBLE_BUT_EMPIRICAL`
  - `THREE_HEAD_LATTICE_NEEDS_STRUCTURAL_RELAXATION`

The experiment token in `evidence/09-*`, if present, is immutable project evidence and is distinct from your literature-level final token. Cite every external factual claim near the claim. Clearly mark when a recommendation is an inference from multiple sources. Do not use external literature to overwrite contradictory simulator evidence; explain the mismatch. Respect the static-inspection boundary in `SOURCE-NOTES.md`.
