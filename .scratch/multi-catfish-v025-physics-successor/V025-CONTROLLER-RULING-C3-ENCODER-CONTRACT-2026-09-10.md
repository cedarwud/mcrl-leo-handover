# Ruling — the C3 encoder width contract

Date: 2026-09-10 ~16:22Z · Controller
Proposal from: `PANELFIX`, in its stop-for-authorisation output
Ruling: **ADOPT THE DERIVATION NOW, DEFER THE FORMAT CHANGE**

## The defect

Four mutually incompatible C3 context widths exist simultaneously, and **no file declares one
authoritatively**:

| producer | C1 | C2 | C3 |
|---|---:|---:|---:|
| v1 run = production encoder (Q1 v1) | 16 | 22 | **240** |
| v2 run (Q1 v2) | 15 | 22 | **236** |
| z-view run (Q1 v2 + cross-user z) | 30 | 44 | **296** |
| the panel PANELBUILD shipped | 16 | 22 | **237** |

**237 is a builder defect**, not a schema: `build_stagec_scoring_panel.py:147` truncated the
six-field ordered global suffix to three fields and did not fail. The other three are correct
consequences of their Q1 schemas.

**Both sides derive the width from checkpoint weights and compare against whatever the panel
happens to contain.** Neither consults a declared constant. That is why the drift was silent
and why it surfaced only at scoring time.

## What is already established, and is stronger than the proposal assumed

The width is **not** an arbitrary per-producer choice. It is a function:

```
member_width = 2 * Q1_width + 6
C3_width     = 1 + 2 * member_width + 4*7 + (32*4 + 1) + 6
```

Verified against **three independent real checkpoints**: `Q1=16 -> 240`, `Q1=15 -> 236`,
`Q1=30 -> 296`. The z case was **predicted before it was measured** and matched exactly.

**A contract does not need to be stored to be checkable — it needs to be derivable and
enforced.** That changes the ruling.

## Ruling

**1. ADOPT, effective immediately, as validation rather than format.**

Every producer and every consumer of a C3 state vector must, before use, derive the expected
width from the Q1 schema in hand and **fail closed** on mismatch. No checkpoint field, no panel
field, no format version is required for this. It can be added today, to code that is already
running, without touching the three live runs.

**2. ADOPT the fail-closed builder fix.** Already authorised to `PANELFIX2`: silent truncation
is the defect that produced 237. A build that now fails was always wrong.

**3. DEFER the stored-digest half of the proposal to the next training generation.**

Storing an authenticated encoder-contract digest in both checkpoint and panel, and comparing
digests before scoring, is the right end state. **It is a checkpoint format change, and three
16-seed runs are writing checkpoints in the current format right now** (landing ~17:05Z,
~17:20Z, ~18:20Z). Changing the format today would strand them.

It is declared here as the **next generation's** format, to be applied when a training run is
next launched from a clean start — not retrofitted.

**4. REJECT one-panel-per-schema as the permanent answer.** `PANELZ` is asked whether one panel
carrying a per-schema state block can serve all widths. If it can, that is the target: the
20-anchor **physical** content is schema-independent — the catalogue, the full-buffer outcomes,
the fixed point, the anytime incumbent — and only the state encoding varies. Rebuilding
identical physics per schema is waste and is itself a drift surface.

## Why this is engineering, not science

**No number changes.** No estimand, reference, numerator or arm definition is affected. This
governs whether two artefacts may be compared at all, not what the comparison says. It touches
no sealed declaration and requires no versioned model amendment.

## The general rule this instance is an example of

**A quantity that three producers compute independently and no file declares will drift, and it
will surface at the most expensive step.** Here it surfaced at scoring, an hour before three
trainings landed, and only because the scorer was run against a real checkpoint instead of
being trusted.

Where a quantity is **derivable**, enforce the derivation at every boundary and fail closed.
Where it is **chosen**, one file declares it and everyone reads that file. What must not happen
is what happened here: everyone infers it from whatever they were handed.
