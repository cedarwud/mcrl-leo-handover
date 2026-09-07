# Multi-Catfish V0.4 C3 implementation seam

Date: 2026-09-01  
Status: implementation work order; no training or efficacy claim

## Fixed decision

V0.3 is closed by the sealed
`STOP_MASKED_MEANMAX_VALIDATION` result.  V0.4 keeps the physical target

\[
\zeta_{3,u}=\Delta t\sum_{i\ne u}(R_i^C-R_i^M)
\]

and changes only the information supplied to the spatial-externality route
and the breadth of its informed source.  There is no second V0.3 fallback.

For a legal focal action `a`, define causal lagged victim burdens

\[
b^{\rm beam}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\ne u\\A_i(t-1)=b_u(a,t)}}R_i(t-1),
\]

\[
b^{\rm sat}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\ne u\\\rho(A_i(t-1))=\rho(b_u(a,t))}}R_i(t-1).
\]

Only committed previous-slot associations and served rates may enter these
blocks.  Current joint actions, `evaluate_actions`, candidate outcomes,
targets, future offsets, a proposal pass, and a second argmax are forbidden.

The V0.4 state remains 228-dimensional.  In the C3 causal view, replace the
redundant `eligible_served_load` block with `previous_beam_rate_burden` and
replace binary `satellite_active` with `previous_satellite_rate_burden`.
Retain `beam_active`, `maximum_required_link_power`, the four legacy physical
blocks, and the four temporal global features.  The new Q3 per-action scorer
remains `12 -> 100 -> 50 -> 50 -> 1`; learning rate, beta, kappa,
route-local loss, Q1/Q2 targets and sources, and deployment weights remain
unchanged.

The views are route-local at both learning and deployment:

\[
s_{1,u}=s_{2,u}=s^{\rm v03}_u,\qquad
s_{3,u}=s^{\rm v04}_u.
\]

The production container contains exactly three networks, not two three-head
trainers:

1. the sealed rung-10 masked-mean/max Q1 head on the V0.3 view and mask;
2. the sealed rung-10 masked-mean/max Q2 head on the V0.3 view and mask;
3. one fresh local action-shared Q3 head on the V0.4 view.

The Q1/Q2 heads are loaded by initialization seed from their authenticated
V0.3 checkpoints and remain frozen.  Only Q3 receives gradient in V0.4.  All
three heads predict the same normalized EE-surplus unit, are summed directly
without weights, and are passed through one common safe mask and one argmax.
Supplying Q3's new burden blocks to Q1/Q2, instantiating unused companion
heads, or reopening Q1/Q2 validation is forbidden.

The C3 informed source must use beam burden as its primary pre-outcome ranking
signal.  Satellite burden is an auxiliary tie-break and retained Q3 feature;
it is not an equal-weight rank term.  The source caps emitted siblings at four
per focal-state context and caps selected contexts sharing one physical anchor
at eight.  It stratifies across beam-burden contrast and action identity,
retains all observed target signs, and preserves a connected 28-action TRAIN
graph with no unsupported validation action pair.  The fixed maximum budgets
are 1052 TRAIN and 810 validation rows under four TRAIN, three validation,
and zero test seeds.  This gives at least 263 TRAIN and 203 validation
focal-state contexts.

Fresh source seeds are frozen before V0.4 outcome generation:

- TRAIN: `2026092301`, `2026092302`, `2026092303`, `2026092304`;
- validation: `2026092305`, `2026092306`, `2026092307`;
- TEST: none;
- learner initializations remain `2026092101`, `2026092102`, `2026092103`.

The scheduler balances the 263 TRAIN contexts as 66/66/66/65 and the 203
validation contexts as 68/68/67 over the sorted seeds.  It freezes a connected
28-action TRAIN graph, filters validation only by TRAIN action-pair support,
and accepts no target or outcome field.  Reference and candidate physical keys
are persisted in the schedule, comparison, dataset, and receipt and are
recomputed during materialization.  After materialization every scheduled row
is retained regardless of target sign.

## Deep module and seam

The module is the V0.4 victim-burden state encoder.  Its interface accepts a
current predecision anchor plus the frozen `interval_s` and `kappa_bits`, and
returns one immutable, action-aligned 228-dimensional observation.  It hides
previous-rate persistence, focal-user exclusion, physical-key aggregation,
normalization, masking, and digest construction.  Callers must not reproduce
those rules.

The environment commit seam persists the previous served rate vector beside
the existing previous association, demand, radiating, and link-power state.
Counterfactual evaluation must not mutate it.

## Checkable completion criterion

The first implementation slice is complete only when targeted tests prove all
of the following through the module interface:

1. episode-start burdens are exactly zero;
2. after one committed step, beam and satellite burdens equal the two formulas
   and exclude the focal user's own previous rate;
3. illegal slots remain zero and output arrays are immutable/deterministic;
4. `evaluate_actions` leaves previous served rates and burden output unchanged;
5. V0.4 output remains 228-dimensional, while existing V0.3 state and
   counterfactual-neutrality tests remain green.

Passing this criterion authorizes source-scheduler implementation only.  It
does not authorize 500EP, TEST opening, or an EE claim.

## Source-selector slice

The informed selector ranks focal users by the largest absolute beam-burden
contrast and beam victim pressure, using satellite burden only to break ties.
Within one focal-state context it emits, in order, the minimum signed
beam-burden change, the maximum signed beam-burden change, and then the
remaining largest absolute beam contrasts, with satellite contrast and stable
action index as tie-breaks.  Duplicate physical keys are removed and the
total is capped at four siblings.  Equal-budget neutral data are sampled from
the same pre-outcome universe while preserving that cap.

This selector slice is complete only when tests prove that it never calls the
physics evaluator, includes both burden-relief and burden-pressure examples
when both exist, rejects episode-start zero-pressure anchors, rejects stale or
V0.3 state, and makes the neutral budget deterministic for a fixed seed.

Local receipt (2026-09-01): the state/counterfactual regression set passed
13 tests; the state plus V0.4 selector set passed 10 tests.  The real-TLE
integration rerun in the isolated Ubuntu snapshot
`/home/sat/mcrl-leo-handover-v04-c3-20260901` passed all 17 targeted tests,
including the committed-step/evaluate-only case.  These are implementation
receipts, not learnability evidence.

After adding the V0.4-only matched opening producer and binding its provenance
to the informed/neutral victim-burden rules, the combined local and Ubuntu
regression set passed 37 tests.  The producer rejects V0.3 state/rules,
unbound keyed fading, stale anchors, and non-unilateral branches, and verifies
the unchanged non-focal delta-rate target.  Dataset/schedule publication is
still pending.

The outcome-blind 263/203 context scheduler and write-once C3-only dataset
persistence boundary are now implemented.  The combined V0.4 plus V0.3
regression set passed 54/54 tests both locally and in the isolated Ubuntu
snapshot.  This closes the state, selector, matched producer, schedule, and
dataset plumbing slices; the real fresh-source runner and learnability result
remain pending.

The route-state prototype established view isolation, but it is not the
production container because it creates three local heads.  The binding
production seam is the exactly-three-network hybrid above.  It must prove
that a Q3 update leaves the sealed Q1/Q2 tensors bit-identical, that changing
only the C3 view cannot change Q1/Q2 surfaces, and that full and drop-C3 arms
reuse the same Q1/Q2 values before one common masked argmax.

Local receipt (2026-09-01): the focused W68, W74, W76--W83, W85, and W86
regression suite passed 71/71 tests after the frozen-source-lineage,
receipt-only-smoke, and subtraction-before-summation review fixes.  A
separate read-only load of all three real sealed
rung-10 checkpoints produced exactly three networks per initialization, zero
trainable Q1/Q2 parameters, and head indices `(0, 1)`.  This closes the local
hybrid implementation seam; it is not C3 learnability or EE evidence.

Real-TLE smoke receipt (2026-09-01):
`artifacts/multi-catfish-v04-c3-real-tle-smoke-20260901-r3` sealed
`PASS_SMOKE_ONLY` on disjoint seed `2026092299`, with one non-opening anchor,
2/2 materialized physical comparisons, receipt SHA-256
`26b56cb8326f84736d36c5c0f338d237332c29bc190a2177c4459685d1743196`,
and no published learning dataset.  This is engineering evidence only.
