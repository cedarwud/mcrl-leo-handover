# Controller record — both audits say do not proceed, and the two reviewers split on whether the requirement is achievable at all
Recorded 2026-09-10. Two independent pre-run audits of the panel harness and two independent strategic notes, all commissioned in parallel while the screening run was starting. The screening run was stopped ten minutes after launch on the strength of the first audit. `DIAGNOSTIC_NOT_CLAIM`; nothing sealed was modified.

## The audits agree: do not proceed
**Both** auditors independently found the two-provisioning-rule design broken, from different angles.

One found that all arm plans are built **before** the provisioning-rule loop, so proposal repair, catalogue construction, learned scores and eligibility guards are identical between rules — the design measures *the same inherited-rule decisions under two outcome evaluators*.

The other found something stronger and proved it: **the corrected rule is never engaged at all.** The bridge calls the scalar evaluator, which never touches the variant seam; the seam is consulted only inside the batched path. **The receipt shows all eight contrast marginals identical across the two rules to sixteen significant digits.** "Both rules" was one rule run twice under two labels, and the harness's own contract tests cannot catch it because they never call the bridge.

Two further blocking findings:

**The source tape and the evaluator tape have different authenticated digests**, with no equivalence check. The run cannot authenticate which physical problem its decisions were trained and selected against.

**The declared protocol has no implementation.** The only entry point hard-codes one seed, two epochs, one anchor and one step; the trainer has no checkpoint write or load; and the sealed checkpoint loader rejects completed epochs above two thousand and any arm inventory other than the five production arms. **My declared nine-thousand-epoch, eight-arm, hundred-epoch-cadence protocol cannot be expressed in the sealed format.** I did not know that when I declared it.

## The finding that matters most for the owner's requirement
One auditor found a **structural blind spot** for the set-level route: a jointly legal per-user argmax becomes the search seed, that route is **exactly zero on singleton coalitions**, and the panel then permits only single-user moves requiring strict improvement. So **when the seed is already an additive optimum, that route cannot cause the first move**, however decisively its prediction favours a two-user configuration. Arms differing only in that route can therefore commit identical configurations at every such anchor.

This explains the earlier probe result that dropping that route changed **zero** proposed assignments. I recorded that as mechanistic asymmetry. **It is closer to the route being locked out.**

## The strategic split
**One reviewer: the requirement cannot be met in this system under any arrangement.** The set-level residual is small at both measured decision objects — about +0.7 % to +1.3 % on association under the corrected rule, and about +2.1 % on power and mode, where an independent per-beam probe reaches 97.9 % of the coupled search. Three structural reasons: the coordination span collapsed four- to eight-fold once the provisioning defect was repaired, so most of the room ever observed was that defect; the one mechanism that fires at real anchors is a step function of summed beam occupancy, **expressible as a per-user feature and needing no residual at all**; and at the power object the coupling that would make a set-level term necessary is weak against local amplifier and threshold effects. It also disposes of the +15.6 % pilot: with about one per cent above the fixed point, any leave-one-out contrast clearing five per cent is the reference arm falling below it, which the pre-declared screen strips.

Its per-route verdict is sharper than anything I had: the first route has large room at power and mode; **the second has none anywhere measured, because that object's gain is per-slot with no temporal component**; the third gets about two per cent anywhere.

**The other reviewer: not established.** The set-level route is **not restricted to cross-beam interference** — a per-beam rule already sees a whole beam's users, and a sum of per-user terms need not capture shared activation costs, occupancy thresholds or simultaneous moves, so the 2.1 % does not bound the residual. It also refuses to fund the panel yet.

## They agree on the decisive measurement
Both point to the same thing: measure, under the **reported** forty-eight-boundary objective rather than the fixed-price single-boundary proxy, how much enabling the **exact** set residual adds. That is the ceiling for any learned head on that route. Both pre-declared a screen — ten per cent for one, five per cent for the other — and both said a result below it stops this candidate design without establishing universal impossibility.

Two jobs are running that measure it.

## Standing
The harness is **not** being rebuilt yet. Repairing a panel that the pending measurement may show should never exist would be the most expensive mistake available today.
