# Controller decision — split the interaction-existence probe across the ACM correction
Recorded 2026-09-09, server clock 06:10 UTC. **No probe outcome exists at recording time.** No regime has reported; the running probe was still in its calibration phase.

## The fact that triggered this
Stage 4h landed a confirmed correction to the ACM causality defect. Verified by file hash at 06:08 UTC, the three files carrying the defect differ between the corrected engine workspace and the two workspaces that are currently executing:

| file | `mcrl-v025-codex-ws-engine` (corrected) | `mcrl-v025-probe-ws` and `mcrl-v025-pilot-ws` (pre-fix) |
|---|---|---|
| `physics_v025/acm.py` | `aa58aeeb83c5…` | `361b0daba0e5…` |
| `physics_v025/resolution.py` | `e0b1cc50532a…` | `7fbad160d831…` |
| `physics_v025/batch.py` | `3677d530f348…` | `350f86d9b9c2…` |

The interaction-existence probe launched at 05:43 UTC and the stage-C pilot are therefore both executing the **pre-fix** physics.

## Why this matters to the probe's question
The probe asks whether, re-anchored at a certified iterated unilateral optimum `u`, any strictly improving joint move exists, that is whether `max Psi_A^u > 0`. On the stage-4h paired smoke the correction moves availability from 0.791277 to 0.453138 and pooled EE from 18,940,246 to 5,658,947 bit/J at identical joules. The corrected physics is therefore **strictly more contended**.

The inference this licenses is asymmetric, and the asymmetry is the whole reason for this decision:

* A **positive** result on the pre-fix physics is suggestive but is measured on physics we do not intend to publish.
* A **null** result on the pre-fix physics does **not** transfer to the corrected physics. Less contention means less for a coordination layer to exploit, so a null there is exactly the result the corrected physics is least bound by.

Accepting a pre-fix null as the answer to the C3 existence question would be an error of the same kind the project has already made twice: measuring the interaction term in a regime where it is structurally suppressed, then reading the suppression as an absence.

## Decision
1. The corrected-ACM probe is launched **in parallel**, in a new workspace `/home/sat/mcrl-v025-probe-ws-acmfix`, over the same six regimes (`a-r0`, `R1`, `R3`, `R4`, `R6`, `R7`), with the question, protocol, calibration reference, step count, seeds and search budget **unchanged**. Only `src/mcrl/physics_v025/` is swapped.
2. The pre-fix probe is **allowed to finish**. It is not killed and its result is not discarded. It becomes the "before" arm of a paired pre-fix / post-fix contrast, which is itself informative: if interaction exists only after the correction, the ACM defect is the mechanism that was suppressing it.
3. Neither probe's result may be used to select the other. Both were commissioned before either reported.
4. The **corrected-ACM probe is the one that answers the C3 existence question** for the paper. The pre-fix probe is reporting-only and is labelled as such.

## What this decision is not
This is not a rerun selected by outcome. The selecting fact is a source-file hash comparison, recorded above, made before any regime reported. This declaration does not change any threshold, sign, seed, horizon, acceptance rule or scientific gate, and it does not create a new gate.

## Consequence for the stage-C pilot
The pilot is also on pre-fix physics. Its energy-efficiency numbers are therefore **not comparable** to any matrix run on corrected physics, and it is reporting-only under `PILOT_NOT_CLAIM` regardless of what it produces. Its remaining value is operational: it proves the stage-C path runs end to end. That value is unaffected by the physics version.
