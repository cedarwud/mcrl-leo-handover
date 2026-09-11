Owner direction change: **switch the project to a development-first algorithm workflow now.**

The purpose is to stop serialising all learner work behind every oracle / credit / representability decision. We now have enough physics, oracle and literature evidence to freeze a reasonable **development kernel**, start short exploratory training, and continue refining the final algorithm while those runs execute.

This does **not** relax, replace or reinterpret Amendment 4 or Amendment 5. Development runs are not formal screening runs and cannot satisfy any paper claim or formal gate.

First read the current artefacts and verify the actual process state yourself. Do not rely on stale registry text. In particular read:

* `V025-CONTROLLER-AMENDMENT-4-OWNER-GATES-B2-BRANCH-AND-CATFISH-COUNT-2026-09-12.md`
* `V025-CONTROLLER-AMENDMENT-5-CRITICAL-PATH-AND-EARLY-D0-T0-PROPOSAL-2026-09-12.md`
* `.scratch/h4-probe/PROGRESS.md`
* `.scratch/t0-repr/PROGRESS.md`
* `.scratch/b1-credit/PROGRESS.md`
* `.scratch/ee-ceiling/PROGRESS.md`
* the actual worktrees and current `sat` processes by cwd + cmdline.

At the time of this instruction the independently observed state was approximately:

* A-real-floor R1 evaluation: 24/24.
* B-real-floor R1 evaluation: 5/24 and running.
* T0 placebo: PASS on both sets; collection underway, triple 0 complete and triples 1/2 running.
* B1 core implementation exists but is not yet committed in the B1 worktree.
* ceiling basin initB1/initrand: approximately 5/6 each, with the substantive ceiling work already complete.

Treat those as a checkpoint to verify, not as authority if the files have advanced.

# 1. Record Amendment 6: DEVELOPMENT-FIRST, without changing formal gates

Create and commit:

`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md`

Its governing distinction is:

**Development algorithm != frozen formal algorithm.**

Define three levels:

**E0 — engineering/development runs**

* Short learner runs.
* May be modified after inspecting DEV/DEVVAL results.
* Used to detect whether the learner, credit and teacher-injection mechanisms actually learn.
* No statistical success claim.
* Never counted as Amendment 4 screening evidence.

**E1 — development screen**

* Longer than E0, multiple development seeds.
* Used to choose/fix the algorithm kernel and hyperparameters.
* Still not a formal paper experiment.
* Only DEV/DEVVAL data may drive changes.

**S1 — frozen formal short screen**

* Existing Amendment 4 / Amendment 5 regime.
* Frozen configuration.
* Full declared arms/nulls.
* 1000 episodes × 3 seeds unless a later owner ruling changes it.
* `rho >= 0.5 * R_repr`, 2/3 direction, QoS/rate floor, matched-null and beyond-seed-noise conditions all remain unchanged.
* This remains a screening threshold, not a publication threshold.

No E0/E1 result may be used to move B1/B2/C thresholds or redefine a formal gate.

# 2. Freeze a development kernel now

The development kernel is:

* Current ratio-learner student architecture and current 28-action contract. Do not redesign the network merely to start this lane.
* A teacher interface that can provide:

  * masked teacher action;
  * 28-action score / advantage vector where available.
* T0 = `LP-prev(c=1,m=0)` as the first **non-privileged anchor teacher**.
* D2 = on-student-state / soft distillation as the primary injection mechanism.
* D3 = unconditional DQfD-style margin as the required hard-imitation comparator.
* D0 = no-teacher baseline.
* D2-null = matched null for determining whether T0 information itself adds value.

Do **not** decide the final Catfish count or multi-teacher composition now.
T_DR / T_SEQ / T_JOINT remain later privileged-teacher candidates.

B1/B2 observation contract and final credit remain **instantiation branches**, not reasons to prevent development of the shared learner/injection kernel.

# 3. Re-triage the currently running sub-agents immediately

Do this from actual current state, and send each agent a delta instruction.

## LP-ORACLE — KEEP, highest scientific priority, but shorten

Continue the currently running **B-real-floor R1 evaluation to 24/24**.

The moment it reaches 24/24:

* aggregate A-floor and B-floor immediately;
* apply the already-declared B1/B2 conditions;
* do not wait for the complete oracle report before reporting the branch-relevant numbers.

After that, the only next high-priority oracle dataset is:

**B-real-floor R1 calibration**

because it supplies out-of-evaluation teacher data for T_SEQ / B2 representability.

Once B-floor calibration is sufficient for the representability screen:

* HOLD A-floor calibration unless it is actually required by the chosen branch;
* HOLD R2;
* HOLD reverse-order sensitivity;
* HOLD unfloored calibration tie-ins;
* HOLD every other oracle completion task that is not needed for the immediate B1/B2 decision.

Do not waste counterfactual CPU merely to finish the old matrix.

## T0REPR — KEEP

It has already passed the placebo and its current collections have sunk cost.

Let the currently running collection processes finish.

Then prioritise:

1. clone fitting;
2. selection of the best one-hot/soft clone according to the predeclared VAL rule;
3. closed-loop `R_repr` on both required sets;
4. immediate admission verdict.

Do not let conditional-entropy presentation, extra tables or report polishing delay the first usable `R_repr` verdict. Those can be completed after the verdict is recorded.

The representability result remains formal evidence; however **do not use its evaluation-set performance to tune the development learner**.

## B1-CREDIT — KEEP, but break the artificial serialization

The B1 worktree currently has useful uncommitted engineering code.

As soon as the existing core tests are green and named mutants are red, make a **separate engineering-core commit** containing:

* `cf_credit.py`;
* the credit-mode wiring;
* the corresponding tests;
* only the minimal supporting code needed for that implementation.

Do not wait for the new lighting-price rollout, the final B1 report or all diagnostics before making this intermediate engineering commit.

Record clearly that this is an engineering checkpoint, **not scientific validation of either credit**.

After that commit, B1-CREDIT continues independently with:

* the lighting-price credit's own no-training greedy rollout requested by Amendment 5;
* exact-DR / lighting-price diagnostics;
* cost benchmark;
* PASS/FAIL report.

The B1 agent no longer owns the D0–D4 harness after this point.

## CEILING2 — finish sunk work, then STOP compute

The substantive ceiling result, rate-floor result, lever split, nominal variant, compound test and T_JOINT dump already exist.

If initB1/initrand cells are still currently running and only their final already-started cells remain, let those **existing cells** finish.

Do not launch or relaunch any additional basin, search-depth, new-init or other ceiling compute just to complete the old plan.

After the current processes exit:

* aggregate what exists;
* write the ceiling report;
* stop the agent's compute activity.

The ceiling report remains useful for the paper and final interpretation, but it is **not a blocker of development training**.

Completed/stale review/curation agents are not to be resumed merely because this workflow changed.

# 4. Split out a new DEVHARNESS lane as soon as the B1 engineering-core commit exists

Create a new isolated worktree/branch from that engineering-core commit.

Do not serialize this behind the B1 scientific report.

DEVHARNESS first implements only the minimum training surface needed for E0:

* D0
* D2-T0
* D2-null
* D3-T0

The full D1/D4/formal nine-arm harness can be completed in parallel/later.

Minimum preflight before E0:

* unit tests for the new loss paths;
* teacher weight = 0 reproduces D0 exactly;
* T0 action/score labels reproduce the verified T0 rule;
* D2-null destroys teacher-action information while preserving dimensions/masks/schedule;
* deterministic seed/config manifest;
* launcher dry-run;
* stop/resume/process identity test using PID + cmdline + cwd;
* no use of the formal evaluation/calibration episodes for development selection.

Do not require the complete formal agy review of all nine arms before E0.
A fresh-context engineering review of the **minimum E0 diff** plus the tests above is sufficient for development launch.
The complete fresh-context formal review remains mandatory before S1.

# 5. Create separate DEV / DEVVAL episode namespaces before training

Search all existing declarations and seed namespaces first.

Allocate new, non-overlapping:

* DEV
* DEVVAL

seed ranges.

Write and commit those ranges **before the first E0 result exists**.

They must not overlap:

* current evaluation episodes;
* calibration episodes;
* T0 clone training/VAL/TEST episodes;
* source pools;
* existing oracle/search episodes.

From this point forward, do not tune any learner parameter using the project's existing 24 evaluation episodes or calibration episodes.

The current evaluation/calibration sets may still be used for the already-declared oracle / representability gates, but not for iterative learner development.

For the eventual paper confirmation, plan a new frozen confirmation set after the final algorithm is frozen, because the existing evaluation set has already informed many design decisions. Do not generate/read that final confirmation result during E0/E1.

# 6. Launch E0 as soon as the minimum harness preflight passes

Do not wait for:

* full ceiling report;
* Q9;
* R2 oracle;
* reverse order;
* T_JOINT completion beyond what already exists;
* final Catfish count;
* final B1/B2 adjudication;
* full nine-arm harness.

First E0 batch:

1. `D0 / equal_share`
2. `D2-T0 / equal_share`
3. `D2-null / equal_share`
4. `D3-T0 / equal_share`

One development seed each.
Use a short development budget in the **100–300 episode class**; choose one exact value before launch and freeze it for this E0 batch.

Why equal_share is included:
it is not being endorsed as the final credit; it is a known implemented reference that lets us isolate whether the teacher-injection kernel itself works.

If the B1 engineering implementation of `lighting_price` is stable enough to execute, also permit a separate clearly labelled exploratory pair:

5. `D0 / lighting_price`
6. `D2-T0 / lighting_price`

These are **development diagnostics even if the lighting-price oracle-first screen has not passed**.
If the no-training screen later FAILS, these runs remain diagnostics only and can never enter formal S1 evidence.

Do not train exact-DR learner arms before its existing oracle-first formal gate. Development-first does not override that explicit restriction.

# 7. What E0 is allowed to change

Inspect only DEV / DEVVAL.

E0 may be used to debug or adjust:

* learning rate;
* teacher-loss weight / schedule;
* soft-distillation temperature;
* replay/query frequency;
* gradient scaling/clipping;
* DQfD margin;
* target-update cadence;
* clearly engineering-level stability issues.

Track every change in:

`.scratch/dev-training/PROGRESS.md`

with:

* configuration hash;
* reason for change;
* which DEV/DEVVAL evidence caused it;
* whether the change affects only engineering or changes the algorithmic story.

Do not silently overwrite configs.

Do not use E0 to:

* redefine B1/B2 thresholds;
* redefine Amendment 4;
* choose Catfish count;
* claim statistical superiority;
* select based on the formal evaluation set.

# 8. E1 only after the kernel behaves sensibly

After E0 establishes that the learner/injection code is functional, select at most the strongest one or two development configurations using DEVVAL and run a modest multi-seed E1.

E1's purpose is to freeze:

* the shared student kernel;
* the injection mechanism;
* development hyperparameters.

B1/B2 and privileged-teacher results may arrive during E0/E1.

When they do:

* do not discard useful development runs;
* instantiate the chosen credit / observation branch on top of the same shared kernel;
* classify mismatching earlier runs as development diagnostics;
* then prepare the formal S1 config.

# 9. Formal science remains unchanged

S1 still requires the complete frozen comparison required by Amendments 4–5, including matched nulls.

Development results cannot substitute for:

* exact-DR formal arms;
* B2 formal arms;
* matched nulls;
* formal seed count;
* QoS / rate-floor checks;
* `rho` / `R_repr` gate;
* later confirmation with more seeds / CI.

No early development result is a paper success claim.

# 10. Controller outputs required now

Do not ask me for another approval unless an irreversible choice outside these rules is encountered.

Execute the following now:

1. write and commit Amendment 6;
2. inspect and re-triage every live agent from actual artefacts/processes;
3. send the KEEP / SHORTEN / STOP instructions above;
4. get the B1 engineering-core commit made as soon as tests permit;
5. dispatch DEVHARNESS from that commit;
6. declare new DEV/DEVVAL seed namespaces;
7. get the minimal E0 harness through preflight;
8. launch the first development batch;
9. keep the formal oracle / representability lanes running only to the shortened stopping points above.

In your next owner-facing response, report only:

* which agents were kept / shortened / stopped and why;
* actual branch-relevant oracle progress;
* whether B1 engineering core has been committed;
* whether DEVHARNESS is ready;
* exact frozen E0 arms/budget/seeds;
* whether E0 training has actually launched;
* any blocker that truly prevents optimizer training.

The objective is now **parallel convergence**:
learn whether the algorithm kernel trains while the remaining measurements decide the final credit, observation contract and teacher set.
