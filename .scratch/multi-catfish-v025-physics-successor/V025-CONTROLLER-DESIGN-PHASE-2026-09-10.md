# The project is in design phase, and I have been running it as if it were in confirmation

**2026-09-10 14:25 UTC. This supersedes the framing of every record I wrote today, without
retracting any measurement in them.**

The owner: *"演算法還在設計的階段，你太早就把太多參數講成是為了要結果好而不能去調整的，這樣是要
怎麼設計?"*

He is right, and this is the most systematic error I made today — larger than any individual
number.

---

## The category error

**Pre-registration discipline exists to stop a design being adjusted until a confirmatory test
passes. It does not apply to choosing the design in the first place.** I applied confirmation-
phase rules to design-phase work, so every parameter acquired language like "must not be
selected by outcome" — and under those rules **no design can be chosen at all.**

## The structure that already exists and that I failed to use

`DATE-ALLOCATION-DECISION-2026-09-10.md`, adopted at 12:00 today, allocates the 166 TRAIN
dates as **116 source/development · 48 evaluation-only claim · 2 quarantined reservations**.

**That is already a design/confirmation split.** The 48 evaluation-only dates have never been
touched.

**The protection against fooling ourselves is untouched data, not frozen parameters.** With 48
dates held aside, exploration on the other 116 costs nothing epistemically. I had that in hand
two and a half hours ago and kept freezing parameters instead.

## The two phases, stated

**Phase 1 — design. Now.**
- Sweep freely: beam width, learning rate, epochs, checkpoint cadence, catalogue construction
  and caps, head architecture, and the decomposition itself.
- On the **116 development dates** and the development anchors only.
- **Nothing produced here is a claim.** Every artefact is labelled exploration.
- Purpose: find a design in which the three routes actually do something.

**Phase 2 — confirmation. After the design is fixed.**
- Freeze the design, declare it in full, run once on the **48 untouched dates**.
- Report whatever comes, in the same detail either way.

## What I withdraw

| what I said | correct in design phase |
|---|---|
| beam width "may not be promoted by outcome" | **sweep it.** `1.66°` gives `+0.899%`; `3.32°` gives `+8.16%` — that is a design finding, not a violation |
| learning rate "is a sealed literal" | **false, and it should be swept** — already dispatched as a convergence question, which was still too narrow a framing |
| "the sealed checkpoint format rejects more than 2,000 epochs" | an implementation guard; change it if the design needs it |
| catalogue caps, layer widths, cadence, activation | design parameters |
| the training gate G1 | asked me to predict a measurement before permitting it; void |

**No measurement is retracted by this record.** What changes is what the numbers are *for*:
they are design evidence, not claim evidence.

## What still holds, and why

- **The 48 evaluation dates stay untouched.** This is the whole basis on which free exploration
  is safe. Nothing in phase 1 may read them.
- **Four-field reporting** — reference, information class, estimand, numerator — still applies.
  It prevents mislabelling, which is a hazard in every phase.
- **Genuine sealing still applies to the objective, the numerator, the fading-quantile scoring
  convention, the service guard and the decision margin.** Changing those is still a declared
  policy change, because they define what is being measured rather than how the design is
  chosen.
- **Loss values are still never evidence about EE.**

## Immediate consequences for the work in flight

- The training run started at 13:55 (v1 schema, unswept lr, 12-anchor panel) is **phase-1
  exploration**, not a confirmatory run. It does not need the heavy caveats I attached to it.
  It is the first end-to-end exercise of a chain that had never run.
- `LRSWEEP` was dispatched as a convergence-validity check. **Widen it: in design phase the
  question is which learning rate produces the best-behaved training, not merely which ones
  fail to diverge.**
- The next work is **sweeping**, not more validation: beam width, epochs, and the two candidate
  decompositions.
- `PANELCEIL` has changed what a sweep should target. On the actual 12-anchor training panel
  the coordination ceiling is `+1.944795%` and the **acceleration ceiling is `+1.045609%`** —
  not the `+100.7%` I had been quoting from a different panel. **On this panel both axes are
  about one to two per cent.** A design sweep must therefore look for a regime where either
  ceiling is materially larger, because at this operating point no learned method can be
  substantial on either axis.
