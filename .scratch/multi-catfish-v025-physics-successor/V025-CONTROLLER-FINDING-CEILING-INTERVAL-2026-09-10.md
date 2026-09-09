# Controller finding — the headroom now has an interval, and it is stable across dates
Recorded 2026-09-10 from the thirty-date coordination-headroom diagnostic. `DIAGNOSTIC_NOT_CLAIM`. No learner; no sealed value changed.

## The number the strategic review asked for
Both strategic reviews named the same weakest point: the coordination headroom was a single figure with no interval. It now has one.

Across **30 TRAIN dates**, treating the date as the independent unit — each date pools bits and joules across its anchors, computes each arm's pooled efficiency, then forms the ratio — the mean gain of the bounded joint selector over the certified unilateral fixed point is **+5.888 %**, date-level sample SD **1.747 %**, two-sided 95 % interval **[+5.235 %, +6.540 %]**.

**All thirty dates are positive.** Minimum +3.205 % on 2026-07-17, maximum +9.652 % on 2025-09-30. The twenty dates spanning the full archive give +5.978 % and a single-month panel of ten January dates gives +5.706 %, so the effect is not an artefact of the date spread.

Pooling all 196 anchors regardless of date gives +5.926 %, reported as a separate weighting and deliberately not used for the interval, because it weights dates by their energies and by unequal anchor counts.

## Two facts that close off easy objections
The panel runs from 2025-07-31 to 2026-08-20, over which the constellation grows from **8,044 to 10,746 satellites**. The correlation between a date's gain and its satellite count is **−0.122** over all thirty dates and −0.166 within the full-span twenty. So the variation across dates is **not constellation growth**; it is time-varying geometry. Every selected daily ephemeris file has zero quarantined records.

## What it does and does not establish
It establishes that the effect the project measured on a narrow panel is **stable across dates** under the physics as it was then implemented. It is a descriptive interval over the selected dates, not a population-randomisation interval.

**Every one of these numbers was computed under the provisioning rule since shown defective** — the one that credits nothing on about three quarters of transmission instances and attains the per-user rate target for none of 2,000 users. So the interval is an interval on an artefact.

## Why it still matters, and what was dispatched
Two things survive the defect. The **method** — thirty dates, the date as the independent unit, per-date receipts, a refuse-to-overwrite guard — is exactly what the corrected measurement needs. And the **spread** is the warning: this quantity varies by a factor of three across dates, with a date-level SD of 1.747 %.

That matters because every judgement made today about whether the project has a future rests on a single corrected-physics figure of about +0.51 %, measured on **one** twenty-anchor panel drawn from four worlds. If the corrected quantity has comparable relative variation, its true value could be materially smaller or larger than that one measurement, and those two cases imply different decisions.

The same thirty-date panel under the corrected rule is therefore running, with a bit-identity assertion required on at least three dates before any of its output is admissible.

## Cost, for planning
About eight minutes of wall clock and 0.3 core-hours per date at eight to ten anchors; roughly ten core-hours for the panel.
