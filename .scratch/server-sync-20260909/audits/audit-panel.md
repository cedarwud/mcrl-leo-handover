You are auditing an instrument **before** the most consequential run this project will make. Read the code, not the prose. Workspace: `/home/sat/mcrl-v025-retrain-ws`, read-only for your purposes; read-only access to sibling `mcrl-v025-*-ws` is fine. Never modify anything.

`DIAGNOSTIC_NOT_CLAIM`. Audit only. Change no constant, threshold, sign, seed, horizon, price, guard or acceptance rule; modify no sealed artefact, manifest, contract, acceptance test or the harness itself. **At most 2 concurrent processes** if you run anything; this is a shared machine.

# What is about to run

Contract §C3, the source-training contrast, for the first time. For each of three learned routes, that route's training source is replaced by a neutral one while **all heads are retained, updated and deployed**. Eight learned arms — the complete factorial over informative/neutral for three routes: full, three leave-one-out, three single-informative, and all-neutral — plus an external geometry-only baseline with no learner.

The harness is `C3-PANEL-HARNESS-2026-09-10.md` and its code in that workspace. The declared protocol: both provisioning rules; sealed learning rates and architectures untouched; two learner seeds; nine thousand source epochs; checkpoints every 100; **full panel evaluation only at 500, 1000, 2000, 4000 and 9000**; the contrast reported at 9000 with the earlier four as trajectory. Supporting decisions are in `.scratch/multi-catfish-v025-physics-successor/` of any sibling workspace: the pre-declared degeneracy screen, the panel spine, the arm-set decision and the matched-anchor-tier verification.

# The question I actually want answered

**What would make this run wasted?** Not "is the design elegant" — what would force us to run it again, or leave the result uninterpretable after the compute is spent.

Check at minimum, in code:

1. **Do all eight learned arms retain, update and deploy all three heads?** Neutral-source substitution must change the training data for one route, never remove a head. Show where, with `file:line`. If any arm silently drops a head or leaves it at initialisation, that is a blocking defect.
2. **Can the shared physical cache leak into selection?** The tier evaluates a configuration once per identical physical context and lets each arm look up its own candidates. Verify the cache key binds tape, world, time, physical and run settings, evaluator identity, the nominal-versus-realised field, the boundary set and prefix history — and that a realised outcome cannot reach a selection decision. Try to construct a leak.
3. **Is the degeneracy screen a reporting function, not a filter?** It must compute both the all-anchor marginal and the marginal restricted to anchors where every arm in that contrast is at or above the head-independent certified fixed point, and report both. If it silently drops anchors, that is a defect.
4. **Is the local search identical across arms, and is it first-improvement?** A different traversal order reaches a different local optimum; this cost the project a full day of mispaired figures.
5. **Are the arms actually distinguishable?** Is there any path by which two arms would produce identical committed configurations at every anchor, making the contrast vacuous?
6. **Does anything about the protocol make the result uninterpretable?** Two seeds, the checkpoint schedule, the evaluation subset, the reporting point, both provisioning rules.
7. **Anything else you find.** Especially: silent proxies, fields filled with constants, and any place a label or an input is not what its name says. A row-path audit today found the surrogate builder writing geometric legality into both the validity and survival fields, and both row paths hard-coding the off-axis angle to zero.

# Output

Write your note to the audits directory as `PANEL-AUDIT-<yourname>-2026-09-10.md` and print it in full as your final message.

**Lead with one line: whether this run should proceed as configured, and if not, the single blocking defect.**

Then list every finding as `BLOCKING`, `DEGRADES_THE_RESULT`, or `COSMETIC`, with `file:line`. Be specific. If you find nothing blocking, say so plainly rather than manufacturing concerns — the project needs to spend this compute, and a false alarm costs it as surely as a missed defect.
