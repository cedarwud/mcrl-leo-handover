# Controller finding — C1 and C2 are target problems, not feature problems
Recorded 2026-09-10 from the admissible-repair diagnostic. `DIAGNOSTIC_NOT_CLAIM`. No learner was trained; no sealed artefact, schema, manifest or pipeline was modified, and the diagnostic stopped at the point where adoption would have required touching one.

**This corrects something I told the owner earlier today.** I said the first two heads' defects looked like repairable implementation faults rather than structural impossibility. That is now wrong for the second head and weakened for the first.

## The governing constraint
A feature is admissible only if it is computable from the pre-decision network state and the focal candidate action alone — without evaluating the candidate configuration's coupled power fixed point or its whole-network outcome, and without any label, oracle or future information. Anything else is leakage: the heads exist precisely to avoid that solve.

## First head: an admissible repair exists and buys nothing
The smallest admissible feature that breaks the published collision is the base configuration's maximum required radiated power as a fraction of the per-beam cap — a summary of the already-committed coupled state, which a controller may cache before considering candidates. It separates the two colliding states (0.4848 against 0.9091).

It also buys **exactly zero** predictive power. Held-out explained variance is unchanged to ten decimal places, because the feature is **constant at 1.0 at all thirty corpus anchors** — every current base configuration already reaches the radiated-power cap, so standardisation annihilates it. Breaking one contract witness did not supply variation this corpus can use.

That every base configuration sits at the cap is itself worth registering as a fact about the operating point.

The remaining diagnosis is structural: the first head's exact target is sensitive to coupled whole-network effects that an action-local row does not represent.

## Second head: the bug is real, large, and not the problem
The stored survival flags are wrong on **822 of 1,784** valid non-reference rows across two anchors (2,406 offset flags); counting validity errors too, **1,022 of 1,784** rows are affected. The cause is an adapter-path semantic misencoding, not a mutation in the encoder: the pilot's primitive builder defines survival as geometric legality — future visibility, D2 eligibility, cell reachability — and writes that same boolean into **both** the validity and survival fields. The exact target uses a different predicate entirely: it evaluates the whole configuration and requires **every changed user** to be in the served set. The absorbing rule is applied to the target but not to the encoded row, so a first non-surviving offset costs the target all later offsets while the row records three independent booleans.

And repairing that adapter would still not make the head learnable. In the real witness the two anchors share the same tape, the same base and incumbent mappings and the same focal candidate, yet the target's predicate ranges over **93 changed users** at one anchor and **one** at the other. The inputs available at decision time are identical; the targets are 5.4095 and 19.3467. **No admissible deterministic feature can separate them, and the admissible separating set is provably empty.**

This exposes a defect in the target itself: unrelated changed users decide the focal action's "survival". The quantity is not measuring what its name claims.

## Consequence
Neither head can presently be expected to raise pooled energy efficiency, and a training run would not repair missing information. The second head needs a **target-contract decision** before any efficacy question is meaningful — either a focal-scoped redefinition that is a function of admissible decision-time information, or reconsideration of the per-user head design. That work is already dispatched as an independent design review.

Adoption of even the one-scalar first-head repair would change the first feature schema digest, so existing sealed shard headers, merged manifests, trained checkpoints and frozen digests would no longer match. They must not be edited in place; adoption requires a newly generated, newly versioned lineage. The diagnostic correctly stopped there.

## Why this is harder than the third head, not easier
The third head's difficulty is a well-defined target over a combinatorial space with expensive labels and thin coverage above size three — costly, but the kind of problem more data and a better architecture can move, and the selection replay has just shown its target genuinely decides outcomes. The first two heads' difficulty is that their targets may not be functions of what the agent can see when it decides. No quantity of data fixes that. It is a redesign of what the head predicts.
