# Amendment 1 to the probe-neighbourhood declaration — a fifth candidate family, aimed by the headroom diagnostic
Recorded 2026-09-09, server clock about 08:40 UTC. **No probe has reported a verdict.** The evidence below is a physics diagnostic, not a C3 result: it measures where infeasibility comes from, and says nothing about whether any coordination scheme succeeds.

The parent record is `V025-CONTROLLER-DECISIONS-PROBE-NEIGHBOURHOOD-2026-09-09.md`, which declared four added families. This adds a fifth. It removes none.

## What the diagnostic found
`HEADROOM-CEILING-2026-09-09.md`, verified against the sealed stage-4h receipt to the unit across all 140 arm-anchors, on `V025_SMOKE/world/1`, 14,000 user-steps:

| finding | value |
|---|---:|
| infeasible user-steps that are interference-limited | 91.110 % |
| infeasible user-steps that are noise-limited | 8.680 % |
| user-steps that are mode-infeasible at their occupancy | 0.000 % |
| interference arriving from the same satellite, adjacent beam | 98.879 % |
| share of a victim's interference carried by its single strongest aggressor | 74.251 % |
| interference-limited population restored by removing the **top-1** aggressor alone | 76.444 % |

## The inference that aims the new family
Removing the single strongest aggressor restores feasibility for 76.444 % of the interference-limited population. **The complement is the point.** For the remaining 23.556 %, removing the strongest aggressor alone is **not** enough. Those victims need two or more aggressors relieved before they cross their decode threshold.

That is the exact signature of a super-additive interaction. Moving aggressor A alone changes nothing for the victim, moving aggressor B alone changes nothing, and moving both together crosses the threshold. The individual marginals are zero or negative while the joint move is positive, so the difference lands entirely in the interaction term.

Note carefully what this does **not** say. Where removing one aggressor suffices, the benefit is already captured in that aggressor's own marginal `d_i`, because the score is evaluated on the whole network. Single-aggressor relief is C1's, not C3's. C3's candidate territory is specifically the multi-aggressor tail.

## The fifth family
`aggressor-coalition`. For each victim transmission that is interference-limited and **not** restored by removing its top-1 aggressor alone:

* form the coalition of the victim and its top-2 aggressors, and separately the victim and its top-3;
* move each aggressor to its own best legal alternative beam, and the victim to its own best legal alternative, in every combination of the coalition's members;
* also include the aggressors-only coalitions, without the victim moving, since the victim may need no move of its own.

Report this family's census separately, as the parent declaration requires of every family, and never pooled with the others.

## Why this is admissible and is not tuning
The same argument as the parent record. The probe asks an **existence** question. A positive answer is a constructive proof exhibiting a specific configuration, so enlarging the search cannot manufacture one. A null answer is always "none found within the searched neighbourhood and budget", so enlarging the neighbourhood makes a null stronger, never weaker.

The selecting evidence is a diagnostic of where infeasibility originates in the physics. It is not a probe outcome, it is not an arm comparison, and no probe has reported. No threshold, sign, seed, horizon, λ, κ, η_ref, service guard or acceptance rule changes, and this creates no gate.

## Correction to two numbers I had been quoting
The diagnostic corrects the controller's own framing, and the corrections are recorded here rather than quietly adopted:
* the evaluation holds **14,000** user-steps, not 28,000; the infeasible share is unchanged at 40.814 %;
* the `NO_MODE` share over the full 14-arm census is **76.5551 %**, not 62 %. The 62 % figure was one arm at one anchor.

## One engine observation carried forward, not adjudicated here
The diagnostic reports that two different feasibility conventions appear inside a single receipt: configurations scored through the dense batch path use a chunk-wide refined slot grid and take feasibility as an OR across slots within a boundary, 50 of 140 arm-anchors, while the scalar object path uses its own slot partition, takes an AND across slots, and applies a `Γ·(1 − 1e-10)` tolerance, 90 of 140. That is recorded as an observation. It is not adjudicated by this amendment and it does not block the probe.
