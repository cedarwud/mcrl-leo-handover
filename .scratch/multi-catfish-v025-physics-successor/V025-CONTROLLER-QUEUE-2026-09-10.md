# Work queue — explicit, because a queued item was lost today

**2026-09-10 12:22 UTC.** `C3REAL` was queued at 10:03 with "SCHEMA2 lands and I add it".
`SCHEMA2` landed at 10:26. It was not added. Two hours passed. **This file exists so a queued
item is a written entry rather than something I remember.**

## Running

| job | since | question | blocks the first training run? |
|---|---|---|---|
| `TRAINRUNNER` | 11:56 | build a parameterised runner + wire the arm-difference fixture as a start gate; report measured s/epoch/arm | **YES — this is the critical path** |
| `EXACTGEN2` | 09:54 | exact-path corpus, physics serialised separately from the rebuildable view layer | **YES** |
| `NEUTRALCHECK` | 12:18 | is neutral-source training distinguishable from knockout, in principle and in practice | **YES — if not, the run's primary contrast is void** |
| `PANELCEIL` | 12:19 | both oracle ceilings on the training panel, plus the traversal-order gap on that panel | no, but the result is uninterpretable without it |
| `C2REAL` | 10:03 | is the declared C2 target learnable, v1 schema | no |
| `C1REALV2` | 10:33 | C1 on the repaired schema — **landed**, see below | no |
| `OBJMISMATCH` | 04:22 | are the certified endpoints locally optimal under the reported objective | no |

## Queued, with the trigger written down

| job | trigger | why it matters |
|---|---|---|
| **`C3REAL`** | when `C2REAL` or `C1REALV2` frees a slot | **C3's target has never been tested for learnability at all.** C1 and C2 have. |
| **`C2REALV2`** | after `C2REAL` reports | C1's verdict reversed entirely on the repaired schema (`0.1711 -> 0.3381`); C2's v1 result must not be read as final for the same reason |
| **`SCORER`** | after `TRAINRUNNER` | dual-axis scoring: coordination contrast and acceleration recovered-fraction, from the same checkpoints |
| **`SIGNFORK` rerun** | when load allows, one cell at a time with peak-RSS measured first | the `RESIDTOGGLE` `+5.62%` vs `C3REACH` `-60%` sign contradiction is still open; the first attempt drove the machine to load 157 |

## Landed today, and what each did to the core quantity

Reporting in three separate categories, never merged.

**(a) Obstruction removed** — does not create value:
`C3REACH` (C3 is reachable: exact Ψ flips 14/20 anchors, learned 20/20, 0/80 tie-break flips) ·
`DATEALLOC` (116/48/2; item closed, world generation unblocked) ·
`PROVFIX` (outcome B, sealed rule stands, closed) ·
wall 2 (the "+1% undetectable" statement was **withdrawn** by the v1.1 amendment, and its
assumed 5% date SD is contradicted by a measured `0.751%`) ·
wall 1 (below).

**(b) New number measured** — not EE:
`C1REALV2`: on the repaired schema, LOAO top-1 `0.1711 -> 0.3381` against an unchanged floor of
`0.1716`; level `R^2` `-0.2724 -> +0.0379`; ordering `0.5889 -> 0.7310`, on the same 37
exact-path anchors. **This falsified a reviewer's own pre-stated test** ("if top-1 is materially
above `0.25`, this paragraph is wrong and should be withdrawn"), so wall 1 was a defective-schema
artefact, not an information ceiling.

**(c) Core quantity changed:** **nothing, all day.**
The coordination-axis oracle ceiling remains `~1%` (`+0.899%` at 8 anchors, `+0.717%` mean over
30 dates with SD `0.751%` and 4/30 non-positive). The acceleration-axis oracle ceiling remains
`+100.7%` at the contract's 10 s budget, **with no learned measurement of any kind**.

**Seven items were called good news today; four were retracted within hours; none of the three
that stand is an EE result.**
