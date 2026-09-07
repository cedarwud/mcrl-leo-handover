# Prompt for a fresh ChatGPT review

## Role

Act as an independent senior algorithm and experimental-design reviewer. Review
the attached `multi-catfish-c2-chatgpt-review-package-20260902-r1` package.
This is a non-heavy, read-only adjudication task. Do not run a simulator, train
a learner, open TEST, or modify package files.

Read `START-HERE.md` first and use `EVIDENCE-MAP.md` and
`SOURCE-PATH-MAP.md` to resolve every cited file. Do not ask for clarification.

## Goal

Determine the single next scientifically valid step toward a genuine
three-Catfish MCRL method after integrating the Fable 5.1 clean-room Stage 1b
evidence. Decide whether to hold C2 and redesign C3, proceed to a bounded C2
learner gate while C3 is held, accept a two-head method, revise the acceptance
structure, or stop C2 structurally.

The fixed architecture is:

- `C1 -> Q1`, `C2 -> Q2`, `C3 -> Q3`;
- one common safe mask;
- direct unweighted `Q1 + Q2 + Q3`;
- one argmax and one executed Main action;
- final endpoint = matched canonical network ratio-of-sums EE plus the service
  guard.

The preferred final method still requires positive
`FULL > DROP-C1`, `FULL > DROP-C2`, and `FULL > DROP-C3` marginals.

## Evidence order

Use this precedence when sources disagree:

1. packaged raw result JSON and current source;
2. frozen preregistration contracts and checksums;
3. generated reports and independent verification;
4. older design prose.

Label every material statement as **verified fact**, **inference**, or
**proposal**.

The package integration independently verified:

- all 25 entries in the original Fable receipt manifest;
- H-A contract sha256
  `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545`;
- Fable OPS-3 addendum sha256
  `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046`;
- all six directions below from raw episode rows:

| Direction | H-A | Fable lane's OPS-3 reading |
|---|---:|---:|
| C2: FULL vs DROP-C2 | +11.699953%; +12.492141 / +10.670394 / +12.001460 per lineage | +9.479997%; +9.823131 / +8.478158 / +10.195031 |
| C3: FULL vs DROP-C3 | -0.484836%; -0.709544 / -0.254835 / -0.488636 | -2.687311%; -3.355799 / -2.072760 / -2.637507 |
| C1: FULL vs DROP-C1 | +0.644142%; +0.322195 / +0.946865 / +0.665748 | +5.891632%; +5.180581 / +6.284121 / +6.207623 |

These are six TRAIN worlds with oracle Q2, not learned or held-out efficacy.
Both routes mechanically received `C3_CONTEXT_FAIL`, and both overall service
guards failed.

For the Fable OPS-3 C2 contrast, P13 is taken from the H-A result block; the
challenger verified cross-block world identity for all six seeds. The copied
`docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` is an earlier immutable orientation
snapshot, not evidence that the later V0.8 receipts were applied to authority.

## Required review

### 1. Authenticate the development screen

Inspect the two packaged result JSON files, the verification script, runner,
contracts, report, census, and audits. Determine whether the screen is valid as
a six-world direction screen. Explicitly review:

- frozen interference;
- unit fading and gamma-block inversion;
- frozen non-focal context;
- the step-0 convention;
- the literal one-user-step H-A service shortfall;
- common keyed worlds and three lineages;
- source-closure failure;
- possible target, seed, action, policy, or outcome leakage.

Separate a limitation that weakens a claim from a defect that invalidates the
screen.

### 2. Keep the three C2 objects distinct

Adjudicate and re-rank:

1. H-A deterministic hold-horizon segment-timing surplus, which was run;
2. the Fable lane's preregistered OPS-3 reading, which was run;
3. the current exact OPS-3 formula/live adapter, which passed mechanics tests
   but whose declared outcome worlds remain unopened;
4. the Fable orbital option-value proposal, which remains unrun and has open
   support/background semantics.

Do not report the Fable O-arm `+9.479997%` as an outcome of current exact
`source/runtime/ee_axis_ops3_live.py`. Cross-check Addendum A and the Fable
runner against the exact OPS-3 contract/source. Address at least:

- decision-step positions versus cloned 47 x 0.640-s D2 projection;
- absence versus presence of projected D2 eligibility;
- focal-user elevation versus physical cell-centre visibility;
- instantaneous versus absorbing persistence;
- gamma-inverted constant interference versus projected frozen-background
  interference;
- decimal `30.08` versus the canonical clock;
- omitted versus exact Main-reference centering;
- permissive `_last_outcome` reconstruction versus fail-closed committed-state
  validation.

State which differences are only gauge changes and which can change actions or
outcomes. Apply the parallel-design selection order: three-marginal direction
and stability, held-out ranking versus nulls, native coverage, simplicity, then
compute. Do not form a post-hoc hybrid.

Before authorizing any exact OPS-3 outcome opening, resolve the formula-level
question preserved in the mechanics checkpoint: whether future persistence
must also be conditioned on successful opening service at h=0. Treat this as a
pre-outcome formula decision, not an adapter repair or a tunable response to
the Fable results.

### 3. Decide the C3 issue explicitly

The frozen C3 is negative in 0/3 lineages with both tested new-Q2 variants and
Q1+Q3 versus Q1 is -9.716% on fresh worlds, reproducing the sealed -10.286%
direction. Its old positive result existed only with the harmful old Q2.

Compare these options:

- hold C3 and temporarily evaluate a two-head C1+C2 method;
- redesign C3 so its target measures a physical non-focal externality
  complementary to what Q1 plus projected-persistence Q2 already capture;
- reformulate the acceptance structure while preserving scientific honesty.

If recommending C3 redesign, specify the physical estimand, non-overlap with C1
and C2, action-aligned state, Catfish source, common units, and the smallest
**no-training** oracle test. Explain how it can improve final EE. Do not rescue
C3 by rescaling it, reselecting a rung, or changing signs after these outcomes.

Also state whether C1 needs any design change now, rather than merely a
documentation correction for lambda0 provenance.

### 4. Select one next step

Give exactly one next executable step. Define:

- candidate/formula held fixed;
- arms and comparators;
- unopened TRAIN-design worlds and lineage pairing;
- raw ratio-of-sums and service decision rules;
- hard stop rule;
- what must be preregistered before outcomes;
- compute class and estimated wall time.

Classify a simulator/training/rollout job projected above about 30 minutes as
**heavy** and recommend the Ubuntu server; otherwise label it **non-heavy**.
Do not prescribe a 500/1500/3000/9000-episode run at this gate.

## Boundaries

- Final EE, three-head mapping, direct unweighted sum, mask, argmax, and one
  Main action are frozen unless the final decision explicitly accepts a
  scientifically different two-head or acceptance structure.
- Do not tune signs, seeds, thresholds, horizons, outage terms, lambda0, or Q3
  scale against opened outcomes.
- Do not treat oracle headroom, positive target values, action flips, TRAIN
  signs, checksums, or passing mechanics tests as learned efficacy.
- Do not require every pair of heads to beat every singleton. The binding
  three-marginal checks are FULL versus each DROP-Cj.
- List the Fable lane's shared-authority patch plan only as proposals; do not
  assume it was applied.

## Response format

1. Executive verdict
2. Evidence and method audit
3. C2 candidate adjudication and ranking
4. C1/C3 diagnosis
5. Recommended method-level direction
6. Single preregistered next step
7. Remaining risks and claim ceiling
8. Final decision

The final line must contain exactly one token from this set, with no text after
it:

`GO_C2_LEARNER_GATE__C3_HELD`

`REDESIGN_C3_FIRST`

`ACCEPT_TWO_HEAD_METHOD`

`REVISE_ACCEPTANCE_STRUCTURE`

`STOP_C2_STRUCTURALLY`
