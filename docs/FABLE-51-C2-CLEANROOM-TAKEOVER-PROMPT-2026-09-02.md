# Fable 5.1 clean-room takeover prompt — Multi-Catfish C2

Target model: Claude Fable 5.1  
Recommended effort: `max` for the initial scientific design decision; use a lower
effort only after the method is frozen for narrow implementation work.  
Compute class: **non-heavy** for the initial read-only audit, derivation, and
small diagnostics. Any training, sweep, matched pilot, or rollout expected to
take more than about 30 minutes is **heavy** and belongs on the Ubuntu server.

Copy everything below into a fresh Fable 5.1 session opened at
`/home/u24/papers/mcrl-leo-handover`.

---

<operating_mode>
You are operating autonomously. The user is not watching in real time and cannot answer questions mid-task, so asking "Want me to...?" or "Shall I...?" will block the work. For reversible actions that follow from the original request, proceed without asking. Stop only for destructive actions or genuine scope changes the user must decide. Offering follow-ups after the task is done is fine; asking permission before doing the work is not.

Before you start, state in one short update what you will inspect and what decision you intend to reach. Give concise progress updates during long work. Close with a self-contained recap of the verified evidence, changes made, current gate, and next executable step.

The requested scope is the deliverable. Do not stop after proposing a plan. Complete every read-only audit and bounded non-heavy diagnostic that can safely be completed now. If one part is blocked, complete all independent parts and report the exact blocker. First privately list the independent reads or checks you need; request or run them in batches while the lead keeps working.

Use direct technical prose. Use headings, tables, and bullets where they make a multifaceted scientific comparison easier to verify. Distinguish verified facts, inference, hypotheses, and recommendations. Never turn a development-screen sign into an efficacy claim.
</operating_mode>

<workspace>
Repository: `/home/u24/papers/mcrl-leo-handover`

This is a shared, dirty worktree. Before edits, inspect `git status`, relevant
processes, active writers, current authority, and artifact timestamps. Preserve
all unrelated WIP. Do not reset, stash, broadly stage, commit, push, delete, or
rewrite unrelated files. Prefer surgical edits. Do not treat an imported session
or an artifact file as proof that a process is still running.

This session is a concurrent scientific-challenger lane. Another live session
owns the provisional OPS-3 live projection adapter and its mechanics tests.
Do not edit or replace that lane's files. Keep your work read-only until the
design comparison is complete; if code is then warranted, use new isolated
Fable-prefixed files and an isolated artifact directory. Report any proposed
change to shared authority or OPS-3 files as a patch plan, not as an edit.
</workspace>

<documents>
Read these sources before deciding. Current source/code and sealed receipts
override prose that was written before later evidence.

1. Canonical EE and original three-view decomposition:
   `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`
2. Current C1/C3 formulas, notation, mechanisms, and claim boundaries:
   `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md`
3. Five-arm frozen-policy result:
   `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`
4. C3 redesign rationale and state/target alignment:
   `docs/MULTI-CATFISH-MCRL-V04-C3-VICTIM-BURDEN-DECISION-2026-09-01.md`
5. C3 confirmatory preregistration and result:
   `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-PREREG-2026-09-01.md`
   `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md`
   `docs/MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md`
   `artifacts/multi-catfish-v04-route-interaction-diagnostic-20260901-r1/result.json`
6. Current failed C2 design and its latest evidence:
   `docs/MULTI-CATFISH-MCRL-V07-C2-FOCAL-NEXT-DESIGN-DECISION-2026-09-02.md`
   `docs/MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md`
   `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-one-native28-balanced-sixanchor-sixseed-r13.json`
   `artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1/p0-motion-native28-sixanchor-loao-r14.json`
7. Runtime physics and observations:
   `src/mcrl/env/step.py`
   `src/mcrl/env/link_budget.py`
   `src/mcrl/env/scenario.py`
   `src/mcrl/env/action_contract.py`
   `src/mcrl/runtime/ee_axis_state.py`
   `src/mcrl/runtime/ee_axis_v04_c3_state.py`
   `src/mcrl/runtime/ee_axis_v07_c2_state.py`
8. Current learner/deployment paths and focused tests:
   `src/mcrl/algorithms/ee_axis_pairwise.py`
   `src/mcrl/algorithms/ee_axis_v04_hybrid.py`
   `src/mcrl/algorithms/ee_axis_v07_c2_fast_q2.py`
   `src/mcrl/runtime/ee_axis_v07_c2_policy.py`
   `tests/test_w85_ee_axis_v04_c3_learnability.py`
   `tests/test_w88_ee_axis_v04_c3_confirmatory.py`
   `tests/test_w89_ee_axis_v04_five_arm_ablation.py`
9. Provisional OPS-3 challenger, formula contract, code, and tests:
   `docs/MULTI-CATFISH-C2-OPS3-FRESH-REVIEW-2026-09-02.md`
   `docs/MULTI-CATFISH-C2-PARALLEL-DESIGN-ADJUDICATION-2026-09-02.md`
   `docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md`
   `src/mcrl/runtime/ee_axis_ops3.py`
   `tests/test_w129_ee_axis_ops3.py`
</documents>

<binding_goal>
Design and validate a genuine three-Catfish Multi-Catfish MCRL method:

- C1 training mechanism updates Q1.
- C2 training mechanism updates Q2.
- C3 training mechanism updates Q3.
- Deployment uses exactly one common safe mask, the direct score
  `Q1 + Q2 + Q3`, one argmax, and one executed Main action.
- Each Catfish must have a positive marginal contribution to the final
  canonical network ratio-of-sums energy efficiency when tested as
  `FULL versus DROP-Cj` with the other two heads frozen.

The only scientific objective is final canonical EE. Old `r2` and `r3`
reward values may improve, degrade, or be replaced; they are not endpoints.
The canonical EE formula itself is frozen. Everything else may change when
the evidence requires it.

Do not weaken "positive C2 contribution" into non-harm, near-zero effect,
positive source labels, learnability alone, or fewer handovers. In particular,
verify whether the old scalar handover penalty changes delivered bits or
network power in the simulator. If it only changes a reward field, it is not a
physical EE mechanism.
</binding_goal>

<confirmed_and_failed_evidence>
Treat these as facts to authenticate, not as claims to copy blindly:

- C1: `FULL versus DROP-C1 = +254.596%`, bootstrap interval wholly positive,
  `3/3` initializations positive, `30/30` physical worlds positive.
- C3 five-arm result: `+21.970%`, `2/3` initializations positive, `30/30`
  worlds positive. Separate frozen confirmatory result: `+21.216%` with
  positive bootstrap lower bound and service guard passed.
- C1/C3 are frozen successful context. Do not retrain or redesign either merely
  to increase its reported effect.
- The post-outcome route-interaction diagnostic shows that C1 remains positive
  without Q2: `Q1+Q3` versus `Q3` is `+49.247%`. It also exposes a critical
  context limitation for C3: `Q1+Q3` versus `Q1` is `-10.286%` pooled EE, and
  all three initialization-specific directions are negative. Therefore the
  existing `CONFIRM_C3` is valid only as a marginal effect in its frozen old-Q2
  context. It does not establish that C3 will remain positive after Q2 is
  replaced. Authenticate this computation and classify C3 as
  `LIMITED_TO_OLD_Q2_CONTEXT` unless contrary matched evidence exists.
- C2 V0.7 balanced R13 is effectively zero: pooled `+0.0465%`, lineage pooled
  signs only `1/3` positive, and the six-world bootstrap interval crosses zero.
- C2 R14 leave-one-anchor-out is a valid development diagnostic: all three
  lineages have model MSE worse than the strongest of action-only and zero
  nulls; count `0/3`. This does not prove that every possible temporal C2 is
  impossible. It does block promotion of the present target/state/source
  combination.
- The current motion-one selector reduced exposure and removed much of the
  damage. It did not establish learned positive C2 efficacy. Retire the present
  V0.7 learner candidate rather than polishing it toward zero.
- OPS-3 is only a provisional deterministic projected-persistence formula. Its
  pure formula core currently passes 17 focused tests, but no live TLE/D2
  projection adapter, oracle outcome screen, learner, or positive C2 evidence
  has yet been completed. Treat it as one hypothesis to challenge, not as the
  answer. Authenticate the code and contract independently.
</confirmed_and_failed_evidence>

<scientific_reset>
Start from

`eta = total delivered bits / total network energy`

and the fixed TRAIN-only Dinkelbach-style multiplier

`lambda0 = B0_Main / E0_Main`.

Derive exactly which consequences of a current action can change future
delivered bits or future network energy in this simulator. Inspect, rather
than assume, at least:

- deterministic TLE/SGP4 geometry, slant range, elevation, off-axis angle,
  signed range rate, and remaining legal/visible time;
- angle-recurrence link power and the per-beam max aggregation;
- PA supply power, beam circuit power, and per-satellite baseband activation;
- future service feasibility and actual lost delivered bits;
- lagged load/interference state and treatment-induced policy cascades;
- whether handover class or `phi1/phi2` has any physical path into B or E.

The new C2 must describe a temporal quantity that is both caused by the action
and observable or predictably estimable at decision time. Do not train Q2 on a
realized stochastic successor residual that the input state cannot predict.
Prefer an expected or deterministic matched temporal EE quantity when the
orbital physics supports it. Do not duplicate C1's focal opening-step surplus
or C3's non-focal opening-step rate externality.
</scientific_reset>

<workstreams>
Run the following as parallel workstreams where their reads and calculations
are independent.

## A. C1/C3 early health audit

Do not wait for long training. Verify now:

1. paper formula versus implementation formula and units;
2. state fields are causal, action-aligned, and available at deployment;
3. source selection is outcome-blind and retains all target signs;
4. learner output normalization/gauge and direct `Q1+Q2+Q3` scale;
5. the five-arm and C3 confirmatory evaluators truly hold the other heads,
   environment, seeds, and fading fixed;
6. no old reward semantics, six-Q interpretation, coordinator, selector-only
   deployment, or stale public document has leaked back in;
7. displayed paper/slides notation follows the active symbol table and uses
   single-letter base symbols with indices where required.

Classify every finding as one of: `CONFIRMED`, `LIMITED_TO_OLD_Q2_CONTEXT`,
`IMPLEMENTATION_DEFECT`, `DOCUMENTATION_DRIFT`, or `NEEDS_NEW_C2_INTEGRATION`.

Because the deployed argmax is nonlinear, explicitly test the key limitation:
C1 and C3 were confirmed with a particular frozen Q2 context. Their marginal
effects are not automatically guaranteed after Q2 is replaced. Define a small
fresh matched factorial integration screen that will recheck C1, C2, and C3
simultaneously before any long episode training. Do not alter C1/C3 merely
because this future recheck is necessary.

Keep the evidence stages distinct:

- Stage 1 is route-local fail-fast design evidence. Establish that each route
  has a real EE causal channel, action-specific headroom, decision-time
  observability, and learnable ranking. A new C2 candidate may advance from
  Stage 1 without first proving that every two-Catfish combination improves EE.
- Stage 1b is an inexpensive formula/oracle interaction screen as soon as the
  top C2 has an evaluable action score, before spending time on a neural learner.
  With C1 and C3 frozen, compare `Q1+Q2*+Q3` against `Q1+Q3`, `Q1+Q2*`, and
  `Q2*+Q3` under matched worlds/common randomness. These are the three exact
  final marginal directions for C2, C3, and C1. Require all three directions
  and the service guard to pass in every reported initialization for this
  fail-fast screen. If an exact oracle score cannot legitimately share the
  deployed Q scale, explain that limitation and construct the closest
  predeclared no-training counterfactual test; do not fake comparability.
- Stage 2 is a small fresh matched integration screen after a provisional
  learned Q2 exists. Evaluate the full `2^3` route-mask factorial when
  affordable: none, each singleton, each pair, and all three. The binding
  directional checks are `FULL versus DROP-C1`, `FULL versus DROP-C2`, and
  `FULL versus DROP-C3`. Singleton and pair contrasts are interaction
  diagnostics, not extra efficacy claims and not hard requirements that every
  pair beat every singleton.
- Stage 3 is confirmatory evidence with the preregistered sample size and
  uncertainty/service guards. Statistical confidence belongs here, not in the
  tiny Stage-1 screen.

## B. Clean-room C2 design

Generate at most three materially different C2 hypotheses. For each provide:

- the causal path from action to future B and/or E;
- an exact target in native bits using the fixed `lambda0`;
- the non-overlap boundary with C1/C3;
- the minimal decision-time state;
- an outcome-blind anchor/source selector;
- why its target should be predictable across physical anchors;
- the fastest observation-only or no-learner falsification test;
- the main failure mode and a hard stop rule;
- expected implementation and compute cost.

Rank the hypotheses before running outcome-bearing diagnostics. Select one top
candidate only if its rationale is distinct, physically represented in this
simulator, and capable in principle of a strictly positive marginal EE effect.
OPS-3 may rank first, be revised, or be rejected. At least one comparison must
start directly from the EE numerator/denominator rather than modifying OPS-3.

## C. Fail-fast evidence ladder

For the top C2 hypothesis, use this order:

1. **Mechanism census:** prove nonzero action-specific temporal headroom and
   positive alternatives on small fresh TRAIN-design anchors, without a
   learner. Report effect scale relative to Q1+Q3 and service consequences.
2. **Formula/oracle interaction screen:** before fitting Q2, freeze C1 and C3
   and test the new C2 candidate under matched worlds/common randomness. Use
   `P1=Q1`, `P13=Q1+Q3`, `P12=Q1+Q2*`, `P23=Q2*+Q3`, and
   `P123=Q1+Q2*+Q3`. Require `eta(P123)>eta(P13)` for C2,
   `eta(P123)>eta(P12)` for C3 in the new context, and
   `eta(P123)>eta(P23)` for C1, with the service guard. Report every
   initialization. This is a fail-fast interaction test, not confirmatory
   efficacy and not a demand that every pair beat every singleton.
3. **Observability census:** using world/anchor-disjoint folds, show that a
   simple causal model beats both zero and action-only nulls. The state must
   include the physical quantities used to generate the target. If this fails,
   stop this hypothesis before neural training.
4. **Small learner gate:** only after 1 through 3 pass, fit Q2 with complete legal
   action support and evaluate held-out ranking/calibration.
5. **Small matched integration screen:** freeze Q1/Q2/Q3 and, when affordable,
   evaluate the complete `2^3` route-mask factorial on fresh matched development
   worlds. At minimum include Main, FULL, DROP-C1, DROP-C2, and DROP-C3. For this
   small screen require the three `FULL versus DROP-Cj` pooled directions and
   medians to be positive, majority initialization support, and pooled service
   non-inferiority. Report every singleton and pair contrast as an interaction
   diagnostic; do not require every pair to dominate every singleton. Do not
   demand a positive confidence-interval lower bound from a deliberately tiny
   development screen.
6. **Confirmatory matched gate:** only for a candidate surviving step 5,
   preregister enough fresh held-out worlds to assess uncertainty. Require each
   `FULL versus DROP-Cj` pooled EE contrast to be positive, a positive median,
   a positive paired-world bootstrap lower bound, majority initialization
   support, and pooled service non-inferiority.
7. Only then consider 500/1500/3000 episode trends. Checkpoint every 100
   episodes or updates, as appropriate. Tell the user before any 9000-episode
   launch; never launch 9000 episodes silently.

Use small development diagnostics to choose whether a hypothesis is worth a
formal gate, but never relabel them as confirmatory evidence. A failed candidate
must narrow the hypothesis space; do not change seeds, thresholds, signs, or
scales post hoc to rescue it.
</workstreams>

<compute_routing>
Classify each command or worker before launching it.

- Read-only inspection, implementation, focused tests, documentation, and
  short diagnostics remain in the current environment.
- Training, sweeps, matched pilots, or long rollouts expected to exceed about
  30 minutes are heavy. Run them on the Ubuntu server, not WSL2. Before issuing
  a heavy worker prompt, state the estimated wall time and include these setup
  steps: SSH to the server; synchronize the repository and required artifacts;
  confirm the Python environment and dependency versions; open a Codex/Claude
  worker session in the synchronized checkout; paste the scoped worker prompt.
- Do not launch a heavy run until its pre-outcome contract, input hashes,
  output path, checkpoint cadence, and stop rule are frozen.
</compute_routing>

<editing_boundary>
Begin with read-only work. You may create a new versioned clean-room C2 design
decision and bounded diagnostic code/tests after the formula-first ranking is
settled, but only in new Fable-prefixed files that do not overlap the live
OPS-3 adapter lane. Keep the current V0.7 artifacts as negative evidence; do not delete
them. Mark superseded public claims surgically only after authenticating the
later evidence.

Do not update the web-agent package, thesis method chapter, figure handoff, or
presentation as though the new C2 were final until it passes the mechanism and
observability gates. You may produce a clearly labelled delta/handoff that says
what is frozen, retired, provisional, and still blocked.
</editing_boundary>

<deliverables>
Return and, where appropriate, save:

1. a one-page takeover/status verdict;
2. an EE-formula causal map for C1/C2/C3;
3. the C1/C3 early health-audit table;
4. at most three ranked C2 candidates;
5. the exact top-candidate formula, state, source, and fail-fast gate;
6. results of every bounded non-heavy diagnostic actually run;
7. an explicit `GO`, `REVISE`, or `STOP` decision for the top C2 candidate;
8. a heavy Ubuntu worker prompt only if the next authorized step exceeds
   roughly 30 minutes;
9. a list of files changed and files deliberately left untouched.

The final answer must state separately:

- whether current V0.7 C2 is retired;
- whether a new positive C2 is physically plausible, merely unproven, or
  structurally impossible in this simulator;
- whether C1 and C3 remain trustworthy under their old frozen context;
- what exact evidence is still required to trust all three together;
- whether any 500/1500/3000/9000 episode run is authorized now.
</deliverables>

<task>
Take over Multi-Catfish C2 from clean context. Determine whether this simulator
contains a decision-time-observable temporal mechanism that can train Q2 to
make a strictly positive marginal contribution to final EE. Retire the failed
V0.7 candidate, independently compare the provisional OPS-3 hypothesis against
up to two genuinely different EE-derived replacements, fail-fast-test the best
non-heavy option, and audit C1/C3 now so integration defects are found before
long training. Continue through all safe, reversible, in-scope work without
waiting for another instruction. Do not block on or overwrite the concurrent
OPS-3 adapter session; your deliverable is an independent challenger and a
same-protocol adjudication recommendation.
</task>

First privately list what you need next; then request or run every item that
does not depend on another result in one batch.

---

Suggested CLI invocation:

```bash
claude -p "$(<docs/FABLE-51-C2-CLEANROOM-TAKEOVER-PROMPT-2026-09-02.md)" \
  --model fable \
  --effort max \
  --output-format json \
  --dangerously-skip-permissions
```

If the shell substitution would include the introductory metadata and fenced
command rather than only the prompt body, copy the text between the horizontal
rules into a fresh Fable session instead. The fresh interactive-session option
is preferred because it preserves an append-only conversation history and
lets the user see progress updates.
