# V025 — pilot track declaration (controller, 2026-09-09 ≈ 02:50 UTC; sealed before the pilot runs)

The owner has asked for the fastest path to a working C3 and for training to start now, with debugging continuing in parallel. Two tracks run side by side. This declaration exists so that speed on one track cannot contaminate the other.

## Track F — pilot (starts immediately)
**Purpose:** prove the whole stages 6–8 path runs end to end on real successor physics, and obtain a first *learned* C3 signal in hours rather than days.
**Scope:** quarantined development worlds only (`V025_PROBE/world/{1,2}` for training rows, `world/{3,4}` for evaluation), the engine as it stands at the stage-4d/4f snapshot with the fixed provider, 30 anchors per world per carrier, the sealed catalogue and arms, **4 learner seeds** and the sealed learner configuration, 6 arms.
**Label on every artefact:** `PILOT_NOT_CLAIM`.
**Binding limits:** pilot numbers may never enter the paper, may never select a configuration, a regime, a margin, a seed count or any sealed rule, and may never be cited as evidence for or against C1, C2 or C3. Their only admissible uses are (i) finding integration and engineering defects, (ii) measuring cost, (iii) deciding *engineering* priorities. The pilot cannot trigger PHYSICS-GO and cannot substitute for the a-r0 matrix.
**What it may change:** engineering only — code that computes no scientific quantity differently (speed, memory, wiring, logging, schema plumbing). Any scientific change it suggests goes through the freeze rule like any other late finding.

## Track S — sealed confirmatory path (unchanged)
Stage 4g → its audit → seal package → a-r0 matrix → admission trichotomy → PHYSICS-GO → confirmatory source generation and training on the claim panel with 16 seeds. Nothing in Track F alters this sequence, its worlds, its seeds or its rules.

## Why this is safe
The pilot worlds are already quarantined from the claim panel (world 1 was opened before sealing; the formal panel uses the `V025_PROBE_R2` / `V025_CAL_R2` namespaces and reserved claim dates). The pilot uses the same code as Track S, so every integration defect it finds is a real defect of the confirmatory path, found earlier and more cheaply.

Seal: sha256 in the companion `.sha256` file.
