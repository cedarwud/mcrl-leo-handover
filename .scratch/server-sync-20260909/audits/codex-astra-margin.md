# Adversarial review: argue AGAINST me. Should the sealed margin rule stay as it is?

You are reviewing a controller decision I am about to take, and I want you to try to stop me. I have already been told I am right by one outside model, after I told it my position first, so the agreement is worth very little. Your job is to find what is wrong with my reasoning, not to confirm it.

Read these files first, in this order. They are on this machine.
* `/home/sat/mcrl-records/decisions/V025-CONTROLLER-ADJUDICATION-R11B-MARGIN-RULE-2026-09-09.md` — my adjudication, the thing you are attacking.
* `/home/sat/mcrl-records/decisions/V025-CONTROLLER-FINDING-ACTIVATION-WINDOW-2026-09-09.md` — a verified calculation that complicates it.
* `/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.9-AMENDMENT-2026-09-09.md` — the sealed rule, item 1 is the one in question.
* The engine itself: `/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/{acm.py,channel.py,batch.py,resolution.py}`.

## The situation
The sealed rule says transmit power is computed from nominal gains and the fade margin must **not** be re-solved into power; instead the transmitted mode is demoted using a tenth-percentile fading quantile. Its stated reason is that setting `p = p_nominal / q` would make the link target the threshold again, so "the margin bought no reserve, only more power and more interference".

I now claim that reason is mathematically wrong, because with `p = p0/q` the realised SINR is `Γ·G/q`, so decoding succeeds exactly when `G >= q`, which is 0.90 by construction.

## What I need you to attack, in order of how much it would cost me to be wrong

**1. Is the stated rationale actually wrong, or did I misread it?** Read v1.9 item 1 in full and in context with items 2 and 3. Is there a reading under which the original reason is correct, for instance one about interference coupling, about the coupled fixed point re-solving all powers simultaneously, or about what happens at the cap? The original text mentions "more power and more interference". I may have dismissed a real coupled-system argument as a naive one. **This is the question I most want answered.**

**2. Does the amendment survive the coupled fixed point?** Our power solve is a coupled capped fixed point across beams. Scaling one link's power by `1/q` changes every other link's interference, which changes their powers, and so on. Show whether the fixed point still converges, whether it converges to something with the claimed 90 % property, and whether it can diverge or hit the cap far more often. A per-link statement that ignores the coupling may simply be false at system level.

**3. Is the 90 % claim even the right target?** The quantile is of the wanted link's fading product with interference frozen at nominal. If interference is also random, a wanted-link quantile is not a 90 % guarantee. Quantify how wrong it is in our system rather than just noting it.

**4. The uncomfortable part.** A verified calculation shows our actual quantile sits inside a window where a beam with one or two users selects no mode and three users activate one. That is a genuine super-additive mechanism, and it exists **because** of the current rule. Amending the rule probably destroys it. I have said this must not influence the decision. Tell me whether I am being naive: is there a defensible reading in which the current rule is a legitimate model of a power-limited payload, so that the mechanism is real physics rather than an artefact? Multi-beam payloads do share a power pool and cannot boost one beam without taking from another. Does that make the no-boost rule a reasonable model rather than a defect?

**5. Cost and freeze discipline.** We have a sealed design-freeze and closure rule. Amending the physics now means an engine change, recalibration, a re-derived figure, and restarting two probes, at a cost of most of a day, with the paper deadline pressing. Weigh that honestly. Is "the rationale is wrong but the policy is defensible, so document it and move on" the better call?

## What I want back
A recommendation of exactly one of: **AMEND**, **KEEP_AND_DOCUMENT**, or **RUN_BOTH_WITH_DECLARED_PRIMARY**, with the reasoning that decides it. Then, separately, a list of every place where my adjudication overstates its evidence, quoting the sentence. I would rather be embarrassed now than in review.

Do not be agreeable. If you think I am right, say so in one line and spend the rest of your effort on the parts I have got wrong anyway. Do not modify any file. Budget 1 hour.
