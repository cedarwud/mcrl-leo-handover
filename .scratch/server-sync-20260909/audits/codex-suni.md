# Is the coordination comparator valid when it falls back 88 per cent of the time?

Adjudicate. A parallel review by a different model is running; give your own judgement independently.

## The measurement, taken today
Profiling the certified iterated unilateral best response, `S_UNI`, on 90 real anchors under the unchanged production cutoff:

| quantity | value |
|---|---:|
| decisions that fell back to BASE | **79 of 90, 87.8 %** |
| decisions that actually reached the 10 s budget | **0 of 90, 0.0 %** |
| decision wall, median / p95 / max | 9.223 / 9.412 / 9.975 s |
| best-response iterations, median | **0** |
| anchors with zero iterations | **53 of 90** |

The guard is 0.5 s, so anything finishing after 9.5 s is declared a miss although nothing exceeded 10 s. Removing the cutoff entirely, the same anchors need **up to 876.4 s and 86 best-response iterations** to converge, against a median of 8.9 s for the easy ones. Those are two populations, not one distribution with a tail.

## Why this matters
Sealed contract C4 makes coordination attribution conditional on `FULL > the S_UNI-equipped comparator` on held-out pooled energy efficiency. If `S_UNI` falls back to BASE on 88 per cent of anchors, that comparison is close to free, and **the error is in the direction that flatters the coordination claim**. The figure specification calls `S_UNI` "the honest comparator".

Contract C2 defines it as "iterated exact unilateral improvement to a local optimum, every legal unilateral alternative evaluated with the same nominal joint physics at each iterate, deterministic improving move, atomic commit of the final profile only, termination certificate reported". That reads like an offline reference quantity, not a deployable policy, but it is nonetheless run under the deployment deadline.

An outside methodological review has already given the general principle: keep deadline-constrained all-anchor performance as the deployment primary, and add a separate offline shadow evaluation, because "the key diagnostic outcome is the separation between the mechanism having value and the deadline-constrained implementation delivering it".

## The controller's proposal, which you should attack rather than confirm
Split it into two arms: `S_UNI` computed **without** the deadline as the quality comparator, and a separate deadline-limited unilateral arm as the deployability comparator. Report both. The controller believes the present single arm conflates two different questions and that the 88 per cent fallback is the symptom.

## What I need
1. **Is the proposal right?** If a quality comparator is given unlimited compute while the treatment is not, does `FULL > S_UNI` still mean anything, or has the comparison become unfair in the other direction? Say which asymmetry is worse.
2. **Is the present arrangement already fatal to the C4 attribution**, or is a fallback-heavy comparator defensible as the honest deployment comparison, since a policy that cannot finish is a policy that does not act?
3. **The 0.5 s guard against a 10 s budget.** Nothing exceeded 10 s and 88 per cent were declared misses. Is that guard doing legitimate work, or is it manufacturing the fallback rate? Note that changing it to fix a result would be tuning against an observation, so answer on principle.
4. **Zero best-response iterations at 53 of 90 anchors.** The comparator spent nine seconds and evaluated no improving move at all. Does that make the arm meaningless rather than merely weak?
5. **Under this project's freeze discipline**, is amending contract C4's comparator definition admissible now, given that no panel outcome exists and the amendment is prompted by a timing measurement rather than by a result? The project has amended sealed documents repeatedly, always outcome-blind.
6. Every place the controller's framing above is wrong or overstated, quoting the sentence.

Read `/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md` and the CH5 figure specification for the comparator definitions, and verify the profile data in `/home/sat/mcrl-v025-certprofile-ws/.scratch/cert-profile/s-uni-profile.json`.

Read-only; change nothing. Write `SUNI-ADJUDICATION-2026-09-09.md` in the workspace root and print it as your final message, leading with your answer to question 2 in one line.
