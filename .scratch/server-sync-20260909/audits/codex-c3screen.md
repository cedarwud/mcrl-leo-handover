Workspace: the current directory, `/home/sat/mcrl-v025-retrain-ws`. It holds the nine-arm panel harness built immediately before this task (`C3-PANEL-HARNESS-2026-09-10.md`). **Read that report first and use the harness exactly as built.** Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

**Process limit: at most 4 concurrent worker processes.** This is a shared machine; two jobs today spawned 14 and 30 workers and drove it to load 64 and 70 with one gigabyte of memory left, timing out SSH for other users. `nice` does not limit concurrency.

`DIAGNOSTIC_NOT_CLAIM` and, explicitly, **`SCREEN_NOT_CONFIRMATORY`.** This run exists so the owner can see the machinery work and the arms separate, quickly. **It is not evidence for or against any component's efficacy**, and no result from it may be reported as the answer to the owner's requirement. Every table it produces carries that label.

# What this is

Contract §C3 is the source-training contrast: for each of three learned routes, that route's training source is replaced by a neutral one while **all heads are retained, updated and deployed**. The owner's requirement is that each route individually raise pooled energy efficiency, with the ordering full above any two above the control. **That contrast has never been run.** This is its first execution, at screening scale.

# Configuration, fixed before the run

- **All nine learned arms plus the external control**, as the harness defines them.
- **Both provisioning rules.** A conclusion that holds only under the rule now known to credit nothing on three quarters of transmissions is worthless, and one that holds only under the corrected rule prejudges a decision the owner has not taken.
- **Existing sealed learning rates and architectures, unchanged**: the first route at 1.0e-2 with one hidden layer of 8 and ReLU; the second at 1.0e-3 with 100-50-50 and tanh; the third at 1.0e-3 with 64-64 and ReLU; Adam with the sealed betas and epsilon; one deterministic full-batch update per route per source epoch. **Do not tune any of these.** If a route fails to train, report that as the finding.
- **Two learner seeds**, the smallest number that exposes seed sensitivity at all.
- **The smallest anchor set that exercises every branch**, chosen by the harness's own smoke configuration. State it.
- **Nine thousand source epochs, checkpointed every 100; full panel evaluation at a declared subset only.** This budget was fixed by the controller before dispatch and before any result existed, and it is not yours to change.
  - **Save** a checkpoint every 100 source epochs. Serialising weights is nearly free, so save often.
  - **Evaluate** the full panel at exactly these points and no others: **500, 1000, 2000, 4000, 9000**. Panel evaluation over arms, anchors and 48 boundaries is the expensive operation, so its count is what the budget controls — not the number of training epochs.
  - **Report the contrast at 9000.** The four earlier evaluations are trajectory, not candidate results. Do not report any of them as the outcome, and do not recommend one.
  - If cost forces an early stop, stop at whichever declared evaluation point you reached, state that the reason was **cost** and give the measured figures that made it so. A cost-driven stop is legitimate; a stop chosen because a particular point looked favourable is not, and the distinction must be visible in the report.

# What to report

1. **Training curves per route per arm**, from the checkpoints: the training and validation objective against source epoch. **This is the primary deliverable.** The owner needs to see whether the routes converge, oscillate or are still climbing, because that determines whether the learning rates and epoch budget need attention before any confirmatory run.
2. **The contrast at the declared epoch**, for every pairing the requirement needs: full against each leave-one-out, each single-informative against the all-neutral control, and each arm against the external baseline.
3. **The pre-declared degeneracy screen applied**: below-reference by exact sign against the head-independent certified fixed point, with every contrast reported both over all anchors and over the subset where every arm in that contrast is at or above reference.
4. **Served counts and rate-target attainment, separately**, never merged.
5. **Whether any arm failed to differ from the full arm at all**, which would indicate the intervention did not take effect in that route.
6. **Wall time and cost**, so the owner can size the confirmatory run.

7. **A convergence verdict per route**, against this rule, declared here before the run and not to be reinterpreted afterwards:
   - validation objective still decreasing at epoch 2000 → **under-trained**; the remedy is more epochs, **not** a different learning rate;
   - validation objective oscillating without settling → **learning rate too high for that route**;
   - validation objective flat early and high → learning rate too low, or capacity or features are the limit, which needs further diagnosis rather than a rate change.
   State which case each route falls into, or that none applies.

# Rules

- **Report the contrast at the declared epoch, and show the checkpoint trajectory beside it.** Do not select a checkpoint. A previous pilot moved from −2.4 % through −1.6 % to +15.6 % across checkpoints; choosing among those after the fact would bias everything downstream.
- If the curves show a route has not converged, **say so in the first line** — that is more useful to the owner right now than any contrast value.
- Two seeds cannot support an interval. Report the seedwise values separately and make no distributional claim.
- Every number reproducible from a script left here with exact commands.

Write `C3-SCREEN-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the routes converged, and whether the arms separated at all.
