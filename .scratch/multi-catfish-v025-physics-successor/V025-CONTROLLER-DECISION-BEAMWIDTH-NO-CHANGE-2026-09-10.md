# Controller decision — closed: the beam width does not change, because the current design point works
Recorded 2026-09-10 from the final beam-width curve, which applies **both** corrections at once: strict numerical clearance and correct pairing of the joint arm against the same local search its unilateral arm uses. All five widths reached 8/8 anchors under both provisioning rules. `DIAGNOSTIC_NOT_CLAIM`; the sealed one-sided half-power angle remains 1.66° and no sealed value was changed.

## The correction I owe
Tonight I told the owner that at the width we model, coordination under corrected physics is **negative** at −0.303 %, and that the design point was therefore dead. **That was wrong**, and both defects contributed:

| at the sealed 1.66° width, corrected rule | gap | negative anchors |
|---|---:|---:|
| simple division, mispaired | −0.302750 % | 5/8 |
| strict clearance, mispaired | −0.176800 % | 3/8 |
| **strict clearance, correctly paired** | **+0.899421 %** | **1/8** |

## The curve
| one-sided width | sealed rule | **corrected rule** | negative anchors, corrected |
|---:|---:|---:|---:|
| **1.66°, sealed design point** | +3.618798 % | **+0.899421 %** | **1/8** |
| 2.40° | +10.834491 % | +0.820174 % | 2/8 |
| 3.32°, the source's own value | +12.549948 % | +1.154601 % | **4/8** |
| 4.50° | +19.960312 % | +2.156154 % | 2/8 |
| 6.65° | +26.186258 % | +4.022219 % | 2/8 |

Under the corrected rule the curve is **not monotone** — it dips at 2.40°. Under the sealed rule it is strictly increasing. The monotone rise I reported earlier belongs to the defective physics.

## Why the width does not change
The current design point is **positive and the most stable point sampled**: one negative anchor out of eight, against four of eight at the source's own value. The source width has a higher mean, +1.155 % against +0.899 %, and markedly worse per-anchor consistency.

So there is no case for moving. That outcome is the cleanest available:

- the exposure to *"you chose an antenna that flatters your method"* **disappears entirely**;
- the adjudication's requirement to **freeze the sealed width for the provisioning comparison** is satisfied by doing nothing;
- the provenance erratum stands and is already repaired — the comment asserting a retained full-beamwidth convention was false, proved by substituting the source's own value into its own equation and obtaining exactly one half — but that only makes the comment true. **It moves no value.**

The report kept the boundary I set for it: no wider width is offered as a remedy for the 1.66° result, and any antenna change is stated as a separate design decision outside the diagnostic.

## Where this leaves the coordination side
Corrected-physics coordination span, three panels: **+0.899 %** on eight anchors, **+1.291 %** on twenty, **+0.717 %** on thirty dates with the old pairing. Small, positive, and stably present. Four exploratory routes were measured and none enlarges it; the fifth shows the design point needs no change.

**The coordination side is closed. Effort moves to the source-training contrast, which is the owner's actual requirement and has still never been run.**
