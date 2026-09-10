Workspace: the current directory, `/home/sat/mcrl-v025-retrain-ws`. It holds the encoder-variant seam completed today (`ENCODER-VARIANT-SEAM-2026-09-10.md`) whose default path is proved byte-identical. Read-only access to sibling `mcrl-v025-*-ws` workspaces is fine. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

**Process limit: at most 4 concurrent worker processes.** Two jobs today spawned 14 and 30 workers and drove this shared machine to load 64 and 70 with one gigabyte of memory left, timing out SSH for other users. `nice` does not limit concurrency. Respect this limit explicitly in any pool you create.

`DIAGNOSTIC_NOT_CLAIM`. **You are building and demonstrating an instrument, not running the experiment.** No production training run and no policy run is authorised. No constant, threshold, sign, seed, horizon, price, service guard or acceptance rule may change; no sealed artefact, manifest, contract or acceptance test may be modified. Leave `PILOT_PRIMITIVE_SOURCE_FALLBACK` exactly as you find it — the exact path is selected by taking the non-fallback branch, not by flipping that flag in place.

# What is being built

The project must measure contract §C3: for each of three learned routes, that route's training source is replaced by a neutral one while **all heads are retained, updated and deployed**, and arms are compared on pooled energy efficiency. The owner additionally requires three single-informative-route arms that the sealed panel lacks.

Today's supporting work, all in sibling workspaces and all to be reused rather than rebuilt:
- `EXACT-ROW-PATH-COST-2026-09-10.md` — the exact row path is correct and costs **49.03 s per anchor**, 57.79× the surrogate. The surrogate corrupts both target labels, several Q1 and Q2 inputs, outage, rekey-sensitive Phi, and the identity of the selected coalition. **Use the exact path.**
- `MATCHED-ANCHOR-TIER-2026-09-10.md` — catalogues do **not** intersect across arms once each carries its own seed, so a shared catalogue is unsound. Each arm keeps its own seed and catalogue; a **shared physical cache** evaluates a configuration once per identical physical context; only the **union of chosen configurations** is realised. Cached realised outcomes must never leak into selection, and cache keys must bind tape, world, time, physical and run settings, evaluator identity, the nominal-versus-realised field, the boundary set and the prefix history.
- `ANYTIME-UNILATERAL-2026-09-10.md` — first-improvement local search reaches a better fixed point than best-improvement on all twenty anchors under both rules. **Every arm uses first-improvement**, and the panel declares which search it used.
- The controller's pre-declared degeneracy screen and panel spine, in `.scratch/multi-catfish-v025-physics-successor/` of any sibling workspace.

# Deliverables

**H1 — arms.** Nine learned arms plus the external control: full; three leave-one-out by neutral-source substitution; three single-informative; all-neutral; and the external geometry-only baseline. State precisely how each is constructed and assert that every arm retains, updates and deploys all heads.

**H2 — exact rows.** Build source rows through the non-fallback branch. Assert on real anchors that validity and survival pass through exactly, that both target labels come from the production target functions, and that the outputs differ from the surrogate path in the fields the cost audit listed. Report the assertion counts.

**H3 — the tier.** Implement each-arm-own-seed-and-catalogue with the shared physical cache and union realisation, exactly as specified above. Prove the cache cannot leak into selection with a test that fails if it does.

**H4 — the screen.** Implement the pre-declared degeneracy screen: below-reference decided by exact sign against the head-independent certified fixed point, and every contrast reporting both the all-anchor marginal and the marginal restricted to anchors where every arm in the contrast is at or above reference. It must be a reporting function, not a filter.

**H5 — smoke, and costs.** Demonstrate the whole path end to end on the **smallest** configuration that exercises every branch — a couple of anchors, one or two seeds, a handful of epochs — and label it a smoke test, not evidence. Then report measured costs: seconds per anchor for exact row building, per arm per epoch for training, per anchor for selection and realisation, and the total the full panel would imply at a stated anchor and seed count. **Give the arithmetic.**

**H6 — what you did not build**, and any place the instrument is still unsound.

# Rules

- Both provisioning rules must be supported, because the panel will run under both; state how the variant is selected.
- Do not choose an epoch count, an anchor count or a seed count. Report costs so the owner can choose. **Selecting a checkpoint after seeing results would bias the comparison, and this instrument must not make that easy.**
- Prefer boring reviewable code. Leave every script with exact command lines.

Write `C3-PANEL-HARNESS-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the instrument is complete and what a full panel would cost.
