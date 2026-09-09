# Generate a training corpus that contains the mechanism

`PILOT_NOT_CLAIM`. Budget 2 hours. Wait for the cross-gain repair to land first: poll for `/home/sat/mcrl-v025-pilot-ws/CROSSGAIN-REPAIR-2026-09-09.md` every 2 minutes for up to 45 minutes, then proceed regardless and say what you found.

## The defect
An audit of the existing corpus found **180 coalition rows, every one of size exactly two, one per anchor**. The generator builds the bounded catalogue, discards every configuration that does not change exactly two users, and keeps the lexicographically smallest configuration ID.

Two consequences: the learner has never seen a **three-user** coalition, which is the size the verified occupancy-activation mechanism requires; and with one coalition per anchor there is **no within-anchor variation**, so interaction coefficients are not identifiable from this design by any model.

## What to build
Replace the fixed-size-two, one-per-anchor rule with a **mechanism-aware, multi-coalition** generator. Per anchor produce a set of coalitions that includes, and labels by family:

1. **`pair-catalogue`** — the existing size-two selections, kept unchanged so the old corpus remains a subset and results stay comparable.
2. **`occupancy-activation`** — for each beam at occupancy 1 or 2, the coalition that moves in enough users to reach occupancy 3. At 10 degrees elevation the engine's quantile is `q10 = 0.42923539` against a lowest threshold of `0.7174947935`, so `q*Gamma(n)` clears only at occupancy 3. **This is the family the whole exercise exists for; make sure it is present and say how many anchors admit one.**
3. **`aggressor-relief`** — a victim plus its top two, and separately top three, interference contributors, moved to their own best legal alternatives.
4. **`beam-evacuation`** — every occupant of a beam with 2 or 3 occupants moving out, since the per-chain circuit power is saved only when the beam empties. This family needs no decode threshold at all.
5. **`nested-subsets`** — for a small number of anchors, take one block of five or six users and evaluate **every subset mask** with non-members held at the anchor. For six users that is 64 evaluations yielding 57 non-trivial residual labels and every Mobius coefficient inside the block. Report these as what they are: 64 scalar observations, **not** 57 independent measurements.

Target sizes 2 through 6 with real counts in each, and **several coalitions per anchor**, since within-anchor variation is what identifies the coefficients.

## Labels must be exact
For a coalition of size `k` the residual needs the baseline, the `k` singleton values and the coalition value, that is **`k + 2` distinct evaluations**, not four. Four suffices only for a pair. Cache the baseline and singletons per anchor so an additional coalition costs one new evaluation. State the cache key and confirm it includes the anchor, the context, the proposed actions and the evaluator configuration.

Use **exact** singleton differences. If the singletons subtracted to form a label are learned rather than exact, the head is trained on the interaction plus the singleton error, which is a different quantity. Report which convention you implement.

## Report the order audit while you are there
For the coalitions of size three and above, compute `R3(A) = Psi(A) - sum over pairs in A of Psi(pair)` and report its distribution. If it is material, a pairwise-only interaction model is misspecified no matter how good its features are, and that is a finding worth having before any retraining.

## Constraints
Workspace `/home/sat/mcrl-v025-coalgen-ws`: build it with `cp -a /home/sat/mcrl-v025-pilot-ws /home/sat/mcrl-v025-coalgen-ws` **after** the repair lands, then `rm -rf .git`, `git init`, commit. Never modify `/home/sat/mcrl-v025-pilot-ws` or any other workspace. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or `src/mcrl/env/`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. At most 4 processes, `nice -n 10`. Write large intermediates under `/home/sat/bigtmp`, never `/tmp`, which is a RAM-backed tmpfs on this host.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. Expanding which coalitions are labelled is a coverage repair, not a change to the method: the labels are exact evaluations of the sealed objective either way.

Write `COALITION-CORPUS-2026-09-09.md` in the workspace root and print it as your final message. Lead with the new size histogram and the count of anchors that admit an occupancy-activation coalition.
