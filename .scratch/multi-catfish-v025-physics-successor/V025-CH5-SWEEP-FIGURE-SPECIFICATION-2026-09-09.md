# V025 — CH5 sweep-figure specification and the reporting arms it needs (controller, 2026-09-09 ≈ 03:30 UTC; sealed before any formal outcome)

The owner requires the chapter-5 result figures to be **pooled energy efficiency on the y-axis against several x-axis sweeps, with one curve per arm**. This file fixes exactly what is plotted, so no panel can be chosen after seeing results. It adds two **reporting-only** arms; it changes no certificate, margin, admission rule or claim.

## 1. Curves (the same five in every panel, in this fixed order and style)
| curve | definition | role |
|---|---|---|
| `BASELINE` | the external baseline policy (carrier proposal executed) | reference |
| `C1` | oracle selection scored by C1 alone | cumulative build-up, reporting only |
| `C1+C2` | oracle selection scored by C1 + C2 (C2 as the sealed tie-break) | cumulative build-up, reporting only |
| `FULL` | oracle selection scored by C1 + C2 + C3 | the sealed arm |
| `S_UNI` | certified iterated exact unilateral best response | the honest comparator (thin dashed) |
The sealed leave-one-out arms (`DROP_C1`, `DROP_C2`, `DROP_C3`) remain the load-bearing evidence and are plotted in the companion contrast figure; the cumulative curves exist because a reader cannot see a component's contribution from leave-one-out bars alone. Both views must be shown, and the text states that they answer different questions.

## 2. Panels (x-axes), each with y = pooled ΣB/ΣE over the panel's units
| panel | x-axis | values | data source |
|---|---|---|---|
| A | rate target r* (Mbit/s) | 25, 50 (primary), 100 | regimes R7, a-r0, R1 |
| B | activation cost — circuit power per active chain (W) | 0.1, 0.338 (primary), 1.0 | regimes R4, a-r0, R3 |
| C | occupancy — mean users per active beam | the synthetic grid's LOW / MID / HIGH | synthetic mechanism map (labelled synthetic) |
| D | co-channel coupling — cross-gain relative to direct (dB) | −25 (weak), −12 (strong) | synthetic mechanism map (labelled synthetic) |
| E | architecture | a-r0 (TDM), a′-r0 (FDM), a-γ0 (fixed SINR), b0 (fixed RF) | matrix settings |
| F | off-axis angle (°) | the sealed sweep of figure 1, but per arm at fixed occupancy | matrix, quarantined world |
Panels A, B, E, F carry real-physics data; panels C and D are synthetic and are drawn with a visible `SYNTHETIC` banner and never mixed into the same axes as real-physics panels.

## 3. Presentation rules
Every point carries its interval by the sealed method with the sidedness and nominal level named in the caption, and the measured coverage stated once per figure (v1.7 erratum item 6). Absolute EE in bit/J on the left axis; a right axis shows the relative gain against `BASELINE` for readability. Points that come from a development or pilot panel carry the label banner on the figure. Panels whose regime was declared but not executed are drawn empty with the word `未執行` (skipped), never omitted silently. A csv sidecar accompanies every panel.

## 4. Arms to add (reporting only, pre-outcome)
`ONLY_C1` and `ONLY_C1C2` are added to the oracle arm set with the same catalogue, guards, deadline and evaluation as every other arm, scored by their own key (per v1.9 §4: an arm never ranks or prunes with a score it does not own). They are reporting arms: they enter no certificate and no admission branch. `S_UNI` and `BASELINE` already exist.

Seal: sha256 in the companion `.sha256` file.
