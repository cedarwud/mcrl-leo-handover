# Controller finding — the unilateral comparator now exists and is not degenerate
Recorded 2026-09-10 from the offline certified-unilateral diagnostic. `DIAGNOSTIC_NOT_CLAIM`.

## The defect this closes
Every previous run reported the unilateral comparator as identical to the neutral control, in both adjudications and again in the retraining pilot, where all five calls missed their five-second deadline after one iteration and executed the documented fallback. The cause was never the search: it was the discard-on-abort rule, which the sealed contract mandates as "atomic commit of the final profile only". Contract amendment v1.2 item 6 already requires a two-arm split — an offline arm for diagnosis, a deadline-bounded arm for operation. This is the offline arm, built and measured.

## It moves
On 90 anchors of world 1, the offline arm selected a profile **different from its anchor at 73 (81.1 %)**. The other 17 were certified local optima at the anchor. So the arm is informative: the earlier degeneracy was an artefact of the budget, not evidence that the anchor is already unilaterally optimal.

Every one of the 90 rows terminates with a complete-neighbourhood certificate. At each final iterate the neighbourhood contains exactly 2,700 legal alternatives, all were evaluated, none improved the guarded objective, and 45,819 alternatives across the panel were rejected by the unchanged service guard.

Cost is affordable offline: mean 65.1 s per anchor, median 55.5 s, max 253.3 s; 1,012,016 physical boundary evaluations in total; a mean of 78.2 committed user moves over 4.6 sequential passes, on two workers.

Receipt SHA-256 `7c20620826dde48f70102383cd56eeec3407de3bc0d506c24d20db39f85ee1fe`, on tape `V025_PROBE_R2/world/1` (`a7d222ea…`) with frozen a-r0 calibration `20a8574e…`. The operational runner's blob equals its HEAD blob: its deadline, guard, fallback and discard behaviour are untouched.

## What it does and does not license
The fixed point is the arbitrary endpoint of one deterministic greedy path — ascending user ID, exact best response, stable tie-break, repeat to a zero-move pass. **It is not a ceiling on unilateral reasoning.** Beating it licenses exactly one sentence: *not reproducible by this greedy path*.

Order-invariance is only weakly checked. Three real anchors agree with a deadline-free global-argmax transcription, but all three are zero-move anchors. A moving real anchor was attempted and abandoned after about fifteen minutes with no receipt, so **agreement on a moving anchor is not established** and no claim that the orders always agree is made. A controlled non-anchor test does force two moves and shows both algorithms reach the same fixed point.

## A vacuous test also closed
The T2 acceptance test previously passed on a case where the interaction was zero and both arms selected the base profile — it could not fail. It now requires three conditions together: the placebo interaction within its existing tolerance, the unilateral arm selecting a non-anchor profile, and the deployed selector selecting that same profile. The current degenerate case now fails with "T2 is vacuous: the unilateral arm must select a non-anchor profile". No tolerance or threshold was changed; only the conjunction was strengthened.

## Standing
This removes the strongest objection to every comparison the project has run since the comparator went degenerate, and it does so without touching the operational arm. It does not by itself change any efficacy result: those must be re-measured against this arm before anything is claimed.
