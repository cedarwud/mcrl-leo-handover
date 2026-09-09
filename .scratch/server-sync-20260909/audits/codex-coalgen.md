# Generate a training corpus that contains the mechanism

`PILOT_NOT_CLAIM`. Budget 2 hours. **Do not wait for anything.** The coalition labels are exact evaluations of the sealed objective and do not depend on the encoder feature path, so this runs in parallel with the feature repair.

## The defect
An audit of the existing corpus found **180 coalition rows, every one of size exactly two, one per anchor**. The generator builds the bounded catalogue, discards every configuration that does not change exactly two users, and keeps the lexicographically smallest configuration ID.

Two consequences: the learner has never seen a **three-user** coalition, which is the size the verified occupancy-activation mechanism requires; and with one coalition per anchor there is **no within-anchor variation**, so interaction coefficients are not identifiable from this design by any model.

## What to build
Replace the fixed-size-two, one-per-anchor rule with a **mechanism-aware, multi-coalition** generator. Per anchor produce a set of coalitions that includes, and labels by family:

1. **`pair-catalogue`** — the existing size-two selections, kept unchanged so the old corpus remains a subset and results stay comparable.
2. **`occupancy-activation`** — for each beam at occupancy exactly 1, the coalition that moves in enough users to reach occupancy 3. At 10 degrees elevation the engine's quantile is `q10 = 0.42923539` against a lowest threshold of `0.7174947935`, so `q*Gamma(n)` clears only at occupancy 3. **This is the family the whole exercise exists for; make sure it is present and say how many anchors admit one.**
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

## CORRECTION issued after this task started, apply it
The targeting criterion is **starting occupancy exactly 1**, not "1 or 2". A verified witness shows the sign of the interaction depends on the starting occupancy:

* start at occupancy 1, two arrivals are needed to activate the beam: `Psi = +1.962 Gb`;
* start at occupancy 2, one arrival already activates it, so the second is diminishing: `Psi = -0.778 Gb`.

Coalitions seeded from occupancy-2 beams therefore contribute **negative** interaction, the opposite of what is wanted. Build them from occupancy-1 beams. You may still include occupancy-2 cases, but label them as a separate family and report them separately so the negative population is visible rather than mixed in.

For context: in the census, occupancy 1 accounts for 5,760 of 10,848 beams, that is 53.1 %, so this is the largest bucket and not a corner case.

Compute the activation threshold from the engine tables at each beam's actual elevation rather than from the 10-degree constant, since the quantile varies with elevation.

## Corpus SIZE, not only coverage
An audit found the interaction component was trained on **180 rows** while the per-user components had **176,223** rows, a ratio of about one to a thousand, and all 180 rows were the same coalition size. Expanding the sizes is necessary but not sufficient. **Target at least several thousand coalition rows**, spread across sizes 2 to 6 and across many coalitions per anchor, and report the final count against that 180 baseline. If the evaluation budget cannot reach several thousand exact labels, say what it can reach and what the limiting cost is, so the gap is on the record rather than hidden.
