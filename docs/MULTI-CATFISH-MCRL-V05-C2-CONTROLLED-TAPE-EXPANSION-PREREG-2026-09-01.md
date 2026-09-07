# Multi-Catfish MCRL V0.5 C2 controlled-tape expansion preregistration

Date: 2026-09-01  
Status: `PREOUTCOME_EXPANSION_WORK_ORDER`  
Claim ceiling: `TRAIN_SOURCE_AND_DESIGN_SCREEN_ONLY_NO_TEST_NO_EE_EFFICACY`

## 1. Authorization and unresolved claim

The independent V0.5 mechanics receipt at
`artifacts/multi-catfish-v05-c2-controlled-tape-mechanics-20260901-r4/mechanics-verification-receipt.json`
records `PASS_MECHANICS_ONLY` for all 48 predeclared rows: 12 common-Main
rows and 12 rows for each frozen Q1+Q3 initialization.  It verifies complete
offsets, focal-only intervention, exact non-focal physical-action equality,
Q1/Q3-specific policy digests, explicit Q2 exclusion, and raw target
recomputation.  It does not train Q2 or establish EE improvement.

This work order therefore authorizes exactly one expanded TRAIN-source batch
and the three bounded learner arms in Section 6.  C2 remains mandatory and
unconfirmed until a frozen matched `FULL - DROP-C2` evaluation is positive.

## 2. Frozen C2 estimand

For focal user \(u\), candidate branch \(C\), reference branch \(M\), and
downstream offsets \(k=1,2,3\), C2 retains the all-user fixed-multiplier
surplus

\[
\zeta_{2,u}=\sum_{k=1}^{3}
\left\{
\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)]
\right\}.
\]

This formula is unchanged across all arms.  Target sign is not a gate:
positive, zero, and negative complete rows are retained.  A negative pair is
valid evidence that Q2 should suppress that candidate relative to its
reference; it is not an automatic C2 failure.

The display notation uses only single-letter branch, user, route, and time
indices.  Implementation field names may be descriptive, but each displayed
quantity maps uniquely to the active notation above.

## 3. Controlled physical intervention

One frozen reference policy first produces a four-offset physical action tape.
Both branches then execute the identical taped physical action for every
non-focal user at every offset.  Only focal user \(u\) differs:

1. branch \(M\) follows the tape;
2. branch \(C\) holds the sealed candidate physical link while it has one
   unambiguous legal mapping;
3. at the first zero-support offset, or at offset 3, branch \(C\) releases
   monotonically to the taped focal action.

Missing or duplicate physical mappings fail closed.  No branch-local
re-decision, replacement row, repaired action, or fallback is permitted.
Keyed fading, source seed, anchor, multiplier, interval, and all non-focal
actions are matched.

## 4. Outcome-blind decision-step-diverse schedule

Prepare exactly three topology strata.  Topology eligibility may inspect only
predecision masks, physical IDs, departure status, and horizon availability;
it may not execute a counterfactual or inspect a target.

| Stratum | Eligible step | Frozen ordered source-seed pool | Selection |
|---|---:|---|---|
| \(e\) | 1 or 2 | 2026093001–2026093010 | first eligible world |
| \(m\) | 3 or 4 | 2026093011–2026093020 | first eligible world |
| \(l\) | 5 or 6 | 2026093021–2026093030 | first eligible world |

Each selected world contributes the first four eligible focal users in
ascending user order.  Each focal anchor must have all 28 legal action slots;
the contemporaneous reference is shared and all 27 legal non-reference
physical siblings are retained.  The frozen cardinality is therefore

\[
3\times4\times27=324
\]

rows per reference-policy view.  Failure to find one eligible world in any
stratum is `NO_GO_CONTROLLED_SOURCE_TOPOLOGY`; the stratum or seed pool may not
be changed after observing this batch.

## 5. Four write-once target views

Materialize exactly these views over the same ordered 324 physical siblings:

1. one common-Main tape view: 324 rows;
2. one frozen Q1+Q3 tape view for initialization 2026092101: 324 rows;
3. one frozen Q1+Q3 tape view for initialization 2026092102: 324 rows;
4. one frozen Q1+Q3 tape view for initialization 2026092103: 324 rows.

Total: 1,296 controlled rows.  Every Q1+Q3 receipt must hash Q1 and Q3
parameters separately and state that Q2 is excluded from tape selection.
Q1, Q2, and Q3 bytes must remain unchanged during source generation.

Each row retains the 228-value focal learner state, complete 28-action mask,
reference and candidate action slots, physical keys, raw per-user rates, raw
system powers, raw per-offset surplus, release receipt, tape digest, and
normalized-learning target lineage.  Source generation performs no optimizer
step and opens neither DESIGN-EVAL nor TEST.

Source expansion is authorized only if all 48 shards and all 1,296 rows pass
the same fail-closed mechanics and arithmetic verifier used for the r4 gate,
with zero deletion, replacement, or fallback.  Target sign and magnitude do
not select rows or policies.

## 6. Exactly three bounded learner arms

After the expanded source is sealed, run these arms concurrently:

| Arm | Target view | Pair residual |
|---|---|---|
| `CT-MAIN-VALUE` | common Main | squared |
| `CT-Q13-VALUE` | initialization-matched Q1+Q3 | squared |
| `CT-Q13-HUBER` | same Q1+Q3 rows and labels | Huber, \(\delta=1\) |

Only Q2 receives gradients.  Q1 and Q3 stay frozen.  All arms share the same
network family, initialization seeds, optimizer, minibatch order, target scale
\(\kappa\), multiplier \(\lambda_0\), update budget, and DESIGN-EVAL worlds.
The update ladder is 100, 500, and 1,500 offline Q2 pairwise updates, with a
write-once checkpoint every 100 updates.  These are not simulator episodes.

No fourth arm, alternative horizon, target multiplier, target clipping,
positive-only filter, Main-Huber arm, iterative tape refresh, or post-result
hyperparameter sweep is authorized by this work order.

## 7. Frozen selection rule

At each declared rung, evaluate the direct deployed score

\[
\Phi_u(t,a)=Q_1(s_{1,u}(t),a)+Q_2(s_{2,u}(t),a)+Q_3(s_{3,u}(t),a)
\]

using one common safe-action mask and one argmax.  There is no auction,
coordinator, learned gate, vote, or second decision.

An arm is design-positive at one fixed rung only when all conditions hold:

1. pooled paired ratio-of-sums EE for `FULL - DROP-C2` is strictly positive;
2. at least two of three initialization contrasts are positive;
3. delivered bits do not decrease in at least two of three initializations;
4. every action and trace is valid, finite, and source-authenticated; and
5. TEST remains unopened.

At most one arm advances.  Select the design-positive arm with the largest
pooled paired `FULL - DROP-C2` EE; exact ties use the simplicity order shown in
Section 6.  A design-positive arm is still not Chapter 5 efficacy.  Final
confirmation must use a separately frozen fresh block.

If all three arms fail, the disposition is
`NEXT_C2_FORMULA_PHYSICS_BATCH_REQUIRED`.  It is not permission to remove C2,
keep a harmful head, or call a two-route method Multi-Catfish.

## 8. Execution and evidence boundary

Heavy source generation and learner runs execute on the Ubuntu server.  The
local workspace owns preregistration, code review, receipts, and independent
verification.  No 9,000-episode run is authorized here.  Before any future
9,000-episode run, the user must be notified explicitly.

The immediate implementation authority is:

- `src/mcrl/runtime/ee_axis_v05_c2_controlled_tape.py`;
- `.scratch/c3-v04/run_v05_c2_controlled_tape.py`;
- `.scratch/c3-v04/verify_v05_c2_controlled_tape_mechanics.py`;
- `.scratch/c3-v04/run_v05_c2_controlled_source.py`; and
- the sealed r4 mechanics receipt named in Section 1.
