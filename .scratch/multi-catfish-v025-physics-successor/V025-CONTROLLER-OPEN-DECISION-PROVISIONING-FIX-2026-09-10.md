# Open owner decision — correct the provisioning reference frame, or declare the current one
Recorded 2026-09-10. This is the largest decision on the table and it is not mine to take: it changes the declared physics, so it is a versioned successor. No constant has been changed and no run is authorised. Related: [de-rating slip finding], [occupancy convexity], [literature check].

## What is on the table
Power is provisioned so the **nominal** signal-to-noise ratio equals the rate-target threshold exactly; the mode is then chosen from that same ratio **after** multiplying by the tenth-percentile fade quantile. The de-rating is never compensated at provisioning. Two independent adjudications, from different starting points and with the second given no knowledge of the first, agree this is a reference-frame slip rather than declared physics.

Its effect on the sealed model: **207,607 of 275,616 transmission instances (75.32 %) are credited nothing**, including **all 91,584** single-user instances.

## The proposed correction
One expression, at two sites and their dense twins: provision against the same quantile the selection is later judged at — the threshold divided by the quantile instead of the threshold.

Under it the selection ratio becomes the target threshold exactly, so the transmitted mode equals the target mode and the beam is provisioned to actually deliver the per-user rate. Decoding then succeeds whenever the realised fade is at least the tenth percentile — which is the stated design intent, a ninety per cent link availability. The quantile recovers its meaning as a fade margin instead of being a pure penalty.

The cheaper alternative — deleting the de-rating at selection — was measured and is **not** defensible: it declares a mode the link cannot hold, so its decode failures are real rather than bookkeeping.

## What it costs, measured
Radiated power rises by exactly the reciprocal of the quantile at every occupancy: **+1.107 dB in the best elevation bin to +4.830 dB in the worst**, a factor 2.26 at 45°.

On the isolated sweep the target mode is achieved at every occupancy from one through ten without the cap binding; the cap starts to bind at eleven, where the delivered fraction of the rate target falls to 0.998 and then 0.915. At thirteen and above no target mode exists and the rule changes nothing.

On the real panel it is **not free**, and the analysis says so plainly. Credited instances at occupancy one go from **0 to 45,215**, and at occupancy two from **85 to 40,273**. But cap-bound instances at occupancy one nearly double, from 22,721 to 43,517, and there is a genuine loss at middling occupancy, because every user drawing 3.5 dB more power also **emits** 3.5 dB more interference into the coupled fixed point.

One consequence to keep visible: at occupancy one the corrected rule delivers 1.362 times the rate target, because the bottom rung's spectral efficiency exceeds what was required. Over-delivery is credited by the current numerator. Whether that is the right numerator is a separate open question, currently under adversarial review.

## The three options
**A — correct it, as a versioned successor.** The model then serves users the way its own design intent describes, and the geometry dependence the owner requires survives the change on the analysis so far. Cost: every efficiency figure, served count, prevalence census and coordination headroom the project holds must be recomputed. Nothing already sealed may be edited; a new lineage is generated.

**B — declare the current rule as the design.** Defensible only if the project is prepared to state in writing that its model deliberately provisions with zero fade margin and consequently credits nothing on three quarters of its transmissions, that a beam must be over-subscribed to be served, and that the reported service figures mean positive decoding time rather than rate-target attainment. I do not recommend this; the non-monotone service curve is the part a reviewer will not accept.

**C — correct it and re-price the cap together.** The correction shifts the whole power demand curve up by one to five decibels, so the set of geometries served without the cap binding shrinks by that much. Whether the cap is then still the right value is a separate design question that the owner has already ruled is theirs, as with the beam half-power angle. Bundling avoids two rounds of recomputation.

## What must be settled before any of this is acted on
The pooled-efficiency comparison across the twenty-anchor panel under both formulations is being written up now. Until it lands we do not know whether the coordination headroom — the quantity every result rests on — survives the correction. **No decision should be taken before that number exists.** The adversarial review of the replacement mechanism is also outstanding.

## Standing
Recorded as an open decision, not a recommendation to act. The obligation this creates is to recompute, not to re-argue.
