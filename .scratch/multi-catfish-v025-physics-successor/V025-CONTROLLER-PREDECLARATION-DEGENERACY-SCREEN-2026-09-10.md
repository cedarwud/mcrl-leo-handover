# Pre-declaration — the degeneracy screen for the §C3 panel, fixed before any §C3 number exists
Recorded 2026-09-10, **before** the panel is built and before any source-training contrast has been measured. `DIAGNOSTIC_NOT_CLAIM`. Nothing here changes an arm definition, a source, a catalogue rule, a price, a guard or an acceptance criterion; it fixes how the resulting numbers may be read.

## The problem this prevents
A leave-one-out arm ranks candidates with predicted scores, and its catalogue retains a fallback. A poorly informed head can therefore select something **worse** than the fallback. If it does, the gap between the full arm and that arm is large — and that largeness is evidence of the reference arm collapsing, not of the missing route contributing.

One reviewer put the arithmetic plainly: a ranker can add at most the coordination span above the certified fixed point, so **any gap materially larger than that span means one arm fell below it**. On today's measurements that span is roughly one per cent, while a pilot produced a full-minus-drop gap of +15.6 %. I reported that gap to the owner as encouraging. It was not.

## The reference, and why it is well defined
The certified unilateral fixed point is produced by an exact best-response search over single-user deviations. **It consumes no head output**, so at a given anchor and provisioning rule there is exactly one such endpoint, shared by every arm. It is therefore a legitimate common reference and needs no per-arm construction.

Which local search produces it must be stated: today's anytime work showed that accepting the first strict improvement reaches a **different and better** endpoint than completing a best-improvement sweep, on all twenty anchors under both rules. **The screen uses whichever search the panel's own arms are built on, and the panel must use one search for every arm.**

## The screen, declared
For every arm and every anchor, compute the committed forty-eight-boundary pooled efficiency of the arm's chosen configuration and of the certified unilateral fixed point at that same anchor.

An arm is **below reference** at an anchor when its committed efficiency is strictly less than the fixed point's. No tolerance is applied: the comparison is by exact sign, so no threshold is chosen and none can later be argued about.

Then report, for every contrast, **both** of the following:

1. the marginal over **all** anchors;
2. the marginal over the subset where **every arm in the contrast** is at or above reference.

**If the two agree, nothing is at issue. If they diverge, the divergence is the finding**, and the all-anchor figure may not be presented as component evidence without the restricted figure beside it.

Also report, per arm, the count and fraction of anchors below reference, and the distribution of the shortfall. An arm that is frequently below reference has a defect of its own, whatever its ordering says.

## Why it is written this way
No threshold is picked, so none can be tuned. The restricted subset is a standard sensitivity analysis rather than a filter chosen to produce an outcome. And both figures are published, so a reader can see exactly what the screen did.

## What it does not do
It does not decide whether a route contributes. It prevents one specific misreading. A route whose arm stays above reference and still shows a positive marginal is supported by this panel; a route whose apparent margin comes from its reference arm collapsing is not.

## Standing
Fixed on 2026-09-10, before the panel exists. If it is ever changed, the change and its reason must be recorded with a date, and any result produced under the earlier version must be reported under both.
