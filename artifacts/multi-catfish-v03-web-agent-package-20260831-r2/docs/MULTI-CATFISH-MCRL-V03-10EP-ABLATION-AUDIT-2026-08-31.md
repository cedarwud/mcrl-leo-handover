# Multi-Catfish MCRL V0.3 10-EP matched-ablation audit

Date: 2026-08-31
Role: fresh-context scientific audit, read-only plus audit-only probes
Status: **the 10-EP matched ablation is VOID as evidence about C1, C2 or C3**

## 0. Headline

`artifacts/multi-catfish-v03-10ep-matched-ablation-20260831/receipt.json` does
not measure the three Catfish roles. Every trained arm's deployed policy
collapsed onto 2--3 of 28 actions, and 95--99% of each head's Q variation is a
state-independent per-action bias. The reported EE ordering is a lottery over
which constant association action wins the argmax of three bias vectors.

`directional_pass.C1 = false` is therefore **not** evidence of a C1 core
failure. `directional_pass.C2 = true` and `directional_pass.C3 = true` are
**not** evidence that those roles work. All five fields should be re-labelled
`VOID_UNINTERPRETABLE_INSTRUMENT`.

## 1. What the instrument actually is

- `src/mcrl/runtime/ee_axis_evaluation.py:165` -- the deployed policy is
  `argmax_a [Q1+Q2+Q3](s,a)` under the mask. There is **no Main Q term**.
  Main is replaced wholesale by three surplus heads.
- `src/mcrl/runtime/ee_axis_pilot_runner.py` docstring -- "one pilot episode
  is exactly one diagonal C1/C2/C3 update cycle over frozen source batches".
- Checkpoint `update_count = 30` at 10 episodes: each head received exactly
  **10 full-batch Adam steps at lr = 1e-3**.

So each arm is three near-randomly-initialised 228->(100,50,50)->28 tanh
networks nudged 10 times, then asked to make 1000 held-out association
decisions.

## 2. Measured degeneracy (audit-only probe, evaluation seed 2026090201)

Deployed-action distribution over the real 1000-decision evaluation
trajectory, using the published checkpoints:

| arm | distinct actions | modal share | served |
|---|---:|---:|---:|
| untrained common init | 9 | 0.369 (a=5) | 0.939 |
| F111 | 5 | 0.484 (a=14), 0.479 (a=5) | 0.946 |
| A011 | 3 | **0.991 (a=7)** | 0.999 |
| A101 | 6 | 0.688 (a=5) | 0.936 |
| A110 | 3 | 0.611 (a=5), 0.385 (a=14) | 0.935 |
| N000 | 5 | 0.573 (a=5), 0.395 (a=7) | 0.934 |

Training *reduced* action diversity relative to the untrained network.

Variance decomposition on 216 stored real 228-D states, fraction of each
head's Q variance carried by the per-action main effect:

| arm | Q1 | Q2 | Q3 | SUM |
|---|---:|---:|---:|---:|
| untrained init | 0.870 | 0.936 | 0.874 | 0.864 |
| F111 | 0.990 | 0.920 | 0.892 | 0.951 |
| A011 | 0.995 | 0.920 | 0.892 | 0.957 |
| A101 | 0.990 | 0.993 | 0.892 | 0.979 |
| A110 | 0.990 | 0.920 | 0.972 | 0.977 |
| N000 | 0.995 | 0.993 | 0.972 | **0.992** |

`argmax_a mean_s Q_SUM(s,a)` predicts each arm's modal deployed action exactly
(F111 -> 5, A011 -> 7, A101 -> 5, A110 -> 5, N000 -> 5).

**A011's +12.5 Mbit/J advantage over F111 is entirely "constant action 7 is a
better association than constant action 5".**

Corroboration already inside the repo: the bounded pilot receipt reports
`untrained-common-init` held-out EE = 51.64 Mbit/J (seeds 2026090101/02),
against N000 53.57, A110 55.64, A101 56.77 on the ablation seeds. Three of the
five arms sit at the untrained floor.

## 3. The three "positive" contrasts are one number

On all 216 stored real states, A101, A110 and N000 emit **identical actions**
(pairwise argmax agreement 1.000). Therefore

- `c2_contribution_full_vs_A101`
- `c3_contribution_full_vs_A110`
- `full_vs_neutral`

are three measurements of the same contrast, F111 against one constant-action
policy. Reporting them as separate C2 and C3 role evidence triple-counts a
single number. F111 itself agrees with that policy on 99.1% of those states,
yet differs by 17.6 Mbit/J at the endpoint -- which bounds how much endpoint
variance is unrelated to the heads.

## 4. The C1 and C3 neutral controls were built differently

| | informed anchors | neutral anchors | neutral construction |
|---|---|---|---|
| C1 | `fa383c58`, `c92645e1` | `bfccbd0d`, `c92645e1`, `81ded3a4`, `fa383c58` | global sample over `informed.all_opportunities` |
| C3 | `b6cf2c44`, `670796e8` | same two | per-admitted-anchor sample |

`select_c1_source` populates `all_rows` for **every eligible** anchor
(`ee_axis_c1_selector.py:891`), not only selected ones, so
`sample_c1_neutral_source` draws across anchors the treatment never sees. The
C1 contrast is between-anchor confounded; the C3 contrast is within-anchor
matched. `MULTI-CATFISH-MCRL-V03-OPUS-MAX-SOURCE-CONTROL-REVIEW` requires
"neutral controls must match anchors/pairs"; the C1 control does not.

A `sample_c1_cluster_matched_neutral_source` /
`C1_CLUSTER_NEUTRAL_SOURCE_RULE` has since appeared in
`ee_axis_c1_selector.py`. That addresses this defect and not the ones in
sections 2, 3 and 5.

## 5. Group geometry makes informed and neutral different learning problems

Rows per (anchor, focal user) group:

- informed C1 and informed C3: two groups of 27 -- a complete within-state
  action ranking at two states.
- neutral C1: 45 singletons, 3 doubles, 1 triple.
- neutral C3: 38 singletons, 5 doubles, 2 triples.

A singleton row carries **no** within-state ranking information. Under the
gauge term `beta * Q(s,a^M)^2` a singleton corpus can only fit a smooth global
regression. So the neutral arm does not isolate "informed selection removed" --
it removes the head's ability to discriminate at all. "Neutral" is closer to an
"off" arm than to a control.

## 6. Structural defect that coverage cannot fix

`zeta_j(s, a^C)` is defined relative to `a^M(s)`. The 228-D state
(`ee_axis_state.py`, schema `multi-catfish-mcrl-v03-causal-state-v2`) carries
eligible served load, beam/satellite activity, max required link power,
recurrence power, gain ratio, segment age and a missing-incumbent bit -- but
**no Main reference action and no Main Q**. Since deployment is
`argmax(Q1+Q2+Q3)` with no Main term, Phi can only place the surplus zero
correctly by implicitly re-learning the entire Main policy from the pair
corpus.

This is a **G-O observability failure of the deployment rule**. Enlarging the
corpus changes only the sample cost of re-learning Main; it does not remove the
requirement.

## 7. Governance blockers

1. **No preregistration exists** for the bounded pilot or the 10-EP ablation.
   Both directories contain only `receipt.json`. Decision thresholds are the
   hardcoded `> 0.0` in `run_v03_10ep_matched_ablation.py`. Contract section 8:
   "thresholds and seed counts must be sealed before the multi-seed gate run".
2. **C2 training data violates its own claim ceiling.** The ablation's C2
   corpus is `multi-catfish-v03-c2-{matched-informed,neutral}-real-smoke-seed{1,2}`,
   whose ceiling reads "one real Main/TLE C2-to-Q2 temporal-pair plumbing
   receipt only; **no training, learnability, EE efficacy, or deployment
   claim**". Two rows total, one per seed, same anchor and focal user.
   Meanwhile the sealed reactive gate holds **41 complete traces across 5
   seeds**, unused.
3. **Opening corpus ceiling violated** the same way:
   `MULTIROW_SOURCE_CONSTRUCTION_ONLY_NOT_LEARNABILITY_OR_EE_EFFICACY`.
4. **Learning rate was selected on the endpoint.** The bounded pilot chose
   lr = 0.001 by comparing held-out EE (56.17 vs 36.45 Mbit/J), using the
   informed corpus only; the neutral arms never got their own rung. Fresh
   evaluation seeds mitigate but do not remove selection on the outcome scale.
5. **Authorization sequence skipped.** The reactive gate authorises "one
   separately preregistered bounded matched learnability pilot on
   non-overlapping seeds; never full training". What ran was an lr screen with
   `external_m0_baseline_evaluated: false`, then a 5-arm EE ablation.
6. **G-D and G-O are specified in contract section 8 but not implemented.** No
   runnable check exists for "each target must sometimes alter the final masked
   argmax". A G-D check on the deployed policy would have caught section 2
   immediately.
7. **Power.** One training seed, two evaluation seeds. Within-arm between-seed
   EE spread is 2.1--11.0 Mbit/J (M0 itself spreads 11.0). The train-seed x arm
   variance component has zero degrees of freedom.
8. **Factorial incomplete.** Five of eight cells; `(I,N,N)`, `(N,I,N)`,
   `(N,N,I)` are missing, so main effects and interactions are not separable.
9. **Sealed-manifest break in the C2 provenance chain.** The V0.3B gate sealed
   `.scratch/c2-v03/c2_temporal_fork_trainer_backend.py` at
   `1c860425...` (56107 bytes) and ran 21:14--21:22. That file -- the code that
   computes `zeta_2` -- was **modified at 22:50** to `08bd6772...`
   (56435 bytes), before the 22:53--22:58 C2 smoke rows that fed the ablation
   were generated. Those rows carry `source_manifest_sha256 = 546a6c42...`,
   not the gate's `55acddaf...`. Consequences:
   - `tests/test_w41_c2_v03b_reactive_gate_integrity.py::test_sealed_v03b_prereg_and_manifest_validate_against_current_source_set`
     is now **red**: `V0.3B source manifest SHA-256 mismatch`.
   - The sealed gate `result.json` remains valid evidence (it predates the
     edit and embeds its own digests), but the working tree can no longer
     reproduce it and a re-run would fail the seal check.
   - The ablation's C2 rows are bound to an unsealed manifest, so their
     provenance is broken independently of everything in sections 2--7.
   Before E1: diff the 22:50 edit, decide whether it changes `zeta_2`
   semantics, and either revert it or re-seal a new manifest and re-run the
   gate. Do not generate C2 training rows against an unsealed backend.

## 8. Defensible claims today

**C2 -- defensible.** Exactly the sealed reactive gate ceiling
(`artifacts/c2-v03b-reactive-keyed-physical-headroom-gate-20260831`, outcome
`GO_BOUNDED_LEARNABILITY_PILOT_ONLY`, all 16 preregistered criteria met):
41/41 complete, 0 opening and 0 post-opening censoring, service-safe positive
`zeta_2` in 4/5 seeds spanning 8 distinct sealed anchor digests, both source
rules exercised, release offsets 2 and 3 both observed, Main networks/replay/
checkpoint bitwise unchanged. State the minority rate honestly: **11 of 41**
service-safe complete traces are positive, and seed 2026090102 had 0/7.
Not defensible: learnability, Q2 pivotality, EE improvement, `directional_pass.C2`.

**C3 -- defensible.** Single-seed oracle census
(`c3-focal-nonfocal-oracle-pilot-v03-r1.json`): 20 anchors, 498 evaluated
unilateral candidates, 473 service-safe, 15/20 anchors with positive C3 action
headroom, 277/473 with `zeta_3 > 0`, Spearman(`zeta_1`,`zeta_3`) = -0.026,
affine R^2 = 2.6e-4, identity residual <= 7.6e-6 bits, identical-branch target
magnitude exactly 0. One seed, exploratory anchors, oracle not learned Q3.
Not defensible: `directional_pass.C3`, any EE-improvement statement.

**C1 -- no efficacy claim in either direction.** Retained lineage authority
only (`artifacts/smc-er-c1-authority-20260828/`). The V0.3 C1 EXP/ACRM source
seam is implemented and unit-tested; it has never been evaluated by a valid
instrument.

**Multi-Catfish overall -- no EE efficacy claim.** M0 = 85.69 Mbit/J at
served 0.9995 remains the only credible policy in the receipt, and it is the
frozen baseline.

## 9. Prioritised action

### P0 -- immediately, before anything else runs

1. Amend `artifacts/multi-catfish-v03-10ep-matched-ablation-20260831/receipt.json`
   status to `VOID_UNINTERPRETABLE_INSTRUMENT` (or add an adjacent
   `AUDIT-VOID.json`; do not silently delete -- the receipt is evidence).
   Set all five `directional_pass` fields to void.
2. Add the void to `docs/DEVIATION-REGISTER.md` and to
   `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`. Training stays **NO-GO**.
3. Do not carry any 10-EP number into Chapter 4/5, the figure deck, or the
   paper-authoring contract. Efficacy stays `TBD`.
4. Resolve the section 7.9 sealed-manifest break. Diff the 22:50 edit to
   `.scratch/c2-v03/c2_temporal_fork_trainer_backend.py`, decide whether it
   changes `zeta_2` semantics, then either revert it or seal a new manifest and
   re-run the V0.3B gate. `test_w41` must be green before any C2 row is
   generated for E1.

### P1 -- E1, instrument-validity gate (no EE endpoint)

Preregister and seal before running. Purpose: decide with data whether the
three-head Phi argmax has any state-conditional resolving power, before any
further EE contrast. Estimated 1--2 h wall; **heavy, no GUI -- run on the
Ubuntu server.**

Corpus:
- C1/C3: >= 20 anchors x >= 3 focal users x full 27-alternative enumeration,
  both routes. RIS lineage preserved: informed remains EXP dull-rollout
  lower-frontier ranking plus ACRM reference-anchored full enumeration.
- Neutral control: `sample_c1_cluster_matched_neutral_source`, matched on
  anchor count, users per anchor, and alternatives per user, so the neutral
  corpus has the same 27-sibling group geometry. Build the C3 neutral the same
  way. This removes the section 4 and section 5 defects together.
- C2: use the **41 sealed reactive-gate traces**, with a cluster-matched
  neutral drawn from the same anchors. The 2-row smoke is retired from any
  training role.
- Retention: positive, zero, negative and all-dark rows all retained; no
  post-outcome filtering.

Training: fixed lr, gradient-budget ladder `{10, 100, 1000, 10000}` updates.
Every rung is reported; no rung may be chosen after seeing any result.

Primary criteria, all on a held-out anchor set, **none on EE**:
- **G-D-deploy** -- modal-action share of the deployed argmax over >= 1000
  held-out decisions < 0.50, and >= 8 distinct actions used.
  (Today: F111 0.484 / 5 actions; A011 0.991 / 3 actions.)
- **G-S** -- per-action main effect carries < 0.60 of Phi variance.
  (Today: 0.95--0.99; untrained 0.86.)
- **G-Gen** -- held-out pair MAE beats a state-independent per-action-mean
  baseline by a preregistered margin.
- **G-O** -- a probe trained on the same states predicts `a^M(s)` at held-out
  states above a preregistered top-1 floor.

Forbidden decision inputs, written into the prereg: held-out EE, arm selection
after seeing EE, lr or budget selection on any outcome, seed dropping,
threshold relaxation after outcomes, reuse of a smoke receipt as training data.

Stop/go:
- **All four pass at some rung** -> GO to E2.
- **G-O passes, G-D/G-S/G-Gen fail at every rung** -> coverage-bound. Expand
  the corpus once, re-run E1. Bounded to two iterations, then redesign.
- **G-O fails** -> **redesign now**. The Main-free Phi deployment rule is the
  defect. The minimal repair inside the EE formula and the three-role
  decomposition is to restore an explicit reference term at deployment
  (`Phi = Q_M + Q1 + Q2 + Q3`, or feed `a^M(s)` into the state as an
  observation). Neither changes the EE endpoint, the `zeta` definitions, the
  `(1,1,1)` weights, or the three roles.

### P2 -- E2, matched EE ablation (only after E1 GO)

Preregistered, sealed thresholds. **Heavy -- Ubuntu server.**
- Full 2^3 factorial, all eight cells, so main effects and interactions
  separate.
- >= 5 training seeds x >= 5 fresh evaluation seeds, paired on evaluation seed.
- Primary endpoint: paired difference in pooled ratio-of-sums EE, with a
  preregistered non-inferiority margin on `served_fraction`. Service stays a
  guard, never a reward.
- Always report M0 and the untrained-common-init floor as reference arms.

### P3 -- permanent instrumentation

Implement contract section 8 G-D and G-O as runnable gates in
`src/mcrl/runtime/`, covered by tests, and make every future pilot/ablation
runner refuse to publish a receipt whose deployed policy fails G-D-deploy.

## 10. Note on the test suite

Two suites are red at audit time, neither caused by this audit:

- `tests/test_g6_forbidden_list.py::test_no_new_module_mentions_a_forbidden_term`
  -- stale vocabulary guard; "catfish" is now the project's own name. Cosmetic;
  retire or exempt the term.
- `tests/test_w41_c2_v03b_reactive_gate_integrity.py::test_sealed_v03b_prereg_and_manifest_validate_against_current_source_set`
  -- the section 7.9 sealed-manifest break. **Not cosmetic.**

Every other targeted V0.3 suite passes, and passed while all of sections 2--6
was true. Unit-test coverage of the source seam does not constrain the validity
of a deployed-policy measurement -- section 2 is precisely that gap, and P3
exists to close it.

Concurrent work is in flight in this tree: `ee_axis_c1_selector.py` gained
`sample_c1_cluster_matched_neutral_source` during this audit, and the C2 fork
backend was edited at 22:50. Both are uncommitted. Sequence P0 against whoever
holds those edits before starting E1.
