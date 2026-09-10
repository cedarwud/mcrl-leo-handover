Workspace: the current directory, `/home/sat/mcrl-v025-c1c2suff-ws`. Read-only access to sibling `mcrl-v025-*-ws` workspaces and to `/home/sat/mcrl-v023-codex-audits/parallel-20260909/` is fine. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment, and modify nothing sealed.

`DIAGNOSTIC_NOT_CLAIM`. Design verification from code, plus a small cost measurement if one is cheap. No training run, no policy run, no learner. Change no constant, threshold, sign, seed, horizon, price, guard or acceptance rule; modify no sealed artefact, manifest, contract or acceptance test.

# What is being verified

The project must measure the sealed §C3 contrast: for each of three learned routes, that route's training source is replaced by a neutral one while **all heads are retained, updated and deployed**, and the arms are compared on pooled energy efficiency. The owner additionally wants three single-informative-route arms, which the sealed panel does not contain. The panel is expensive — six arms by twelve learner seeds by two worlds per training date over roughly 160 dates — so adding three arms is a large increase.

A design reviewer proposed a **matched-anchor tier** to make the extra arms nearly free:

> On a common set of anchors, the prefix and the catalogue are identical across arms. Evaluate each catalogue row's realised one-step outcome once, then every arm's choice is a lookup. Nine arms cost about one. It cannot answer the second route, whose value is multi-step by construction.

**I believe that proposal has a defect the reviewer did not state, and I want it checked in code rather than argued.**

The suspected defect: the reference proposal is built by a per-user argmax over the first and second routes' outputs, and the same outputs are used to repair an infeasible proposal. Neutral-source training of either of those routes therefore changes the **seed configuration**, and the bounded catalogue is generated **around that seed**. If so, the catalogue is **not** shared across arms, the "evaluate once, then look up" construction does not hold for those arms, and the tier measures only the ranking effect while silently excluding the proposal effect.

# What to determine, from the code

Read the deployed selector and learner — the three-route model and profile selector, not any older compatibility path — and establish with `file:line` citations:

**Q1. Does the seed configuration depend on the first route's outputs? On the second route's? On the third's?** Show the call path from each head's output to the configuration the catalogue is generated around, including the proposal builder and the infeasibility repair.

**Q2. Is the catalogue therefore arm-dependent?** For each of the three leave-one-out arms and the three single-informative arms, state whether its catalogue can differ from the full arm's, and through which path.

**Q3. What exactly can a matched-anchor tier measure?** If the catalogue is arm-dependent, define precisely the narrower estimand a shared-catalogue tier would measure — presumably the ranking effect at a fixed seed — and say whether that estimand answers the owner's requirement, partly answers it, or does not.

**Q4. Is there a correct cheap tier?** If a shared-catalogue tier is unsound for some arms, is there a construction that is sound and still much cheaper than the full closed-loop panel? Consider at least: fixing the seed to the full arm's and measuring ranking only, as an explicitly labelled sub-question; caching the physical evaluation of any candidate configuration by its configuration identity across arms so that overlapping catalogues share work without assuming identical catalogues; and reporting how much overlap the catalogues actually have. **Measure the overlap if it is cheap to do so** — for example on a handful of real anchors with the existing exact evaluator and two contrasting head parameterisations.

**Q5. Cost.** Give a defensible estimate of the cost of the sound cheap tier relative to one arm of the closed-loop panel, and say what drives it.

# Rules

- **If the matched-anchor tier is sound as proposed, say so in the first line.** I would rather be wrong cheaply than design around a defect that is not there.
- Distinguish what you verified by running code from what you read and from what you inferred.
- Do not propose changing the sealed contrast or the arms' definitions. This is about how to measure them, not what they are.
- Say plainly what you did not reach.

Write `MATCHED-ANCHOR-TIER-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the tier is sound as proposed, and if not, which arms it fails for.
