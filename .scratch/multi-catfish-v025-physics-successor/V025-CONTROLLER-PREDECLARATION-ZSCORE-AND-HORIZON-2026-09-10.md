# Pre-declaration — how the z-score result will be read, and what a big gain would cost

Date: 2026-09-10 ~15:25Z · Controller
**Written before any z-score number exists.** ZSCORE launched 15:00:04Z and has produced
no result. This document exists so the reading rule is not chosen after seeing the outcome.

## A. The horizon finding that changes how today's trainings may be read

`LR-CONVERGENCE-SWEEP-2026-09-10.md` (`/home/sat/mcrl-v025-c1c2-ws`), landed 15:13Z:

- **21 of 21 route x learning-rate cells fail a convergence rule fixed before the sweep**;
- **none of the three current literals** (`1e-2` C1, `1e-3` C2, `1e-3` C3) is admissible;
- the runner takes **one deterministic full-batch Adam update per epoch**, so "500 epochs" is
  **500 gradient steps**, and C3 loss still moves **6.89-8.96%** between step 400 and 500.

This sweep computed **no EE quantity**, and its rule was fixed in `spec.md` before running.
It is an optimisation-validity finding, not an outcome-selected one.

**Consequence, declared now.** Both live trainings (v1 13:55Z, v2 14:25Z) finish ~16:45Z at
500 gradient steps. Whatever route contrast they produce is a contrast **between unconverged
models at equal budget**. That is a valid paired comparison. It is **not** evidence that a
route is dead. A negative contrast at 500 steps and a negative contrast at convergence are
different findings and will be reported as different findings.

**No learning rate may be selected from that sweep.** It ranked nothing; it disqualified
everything. Selecting the best-at-500 rate would be choosing against an observed result.

## B. The z-score reading rule, fixed in advance

The intervention widens Q1 `15 -> 30` and Q2 `22 -> 44`, which **doubles first-layer
parameters**. Amendment 1 to ZSCORE (issued 15:24Z, before any result) adds two FULL-only
controls: **`raw_dup`** `[raw||raw]` — same width, zero new information — and **`z_perm`** —
same normalisation, statistics taken over a permuted grouping so that a user is no longer
normalised against the users it actually competes with.

Four `FULL` runs on one axis at equal budget: **non-z**, `raw_dup`, `z_perm`, `[raw||z]`.

| observed | reading, fixed now |
|---|---|
| `[raw\|\|z]` > both controls | the **cross-user normalisation** carries the gain |
| `[raw\|\|z]` ~= `raw_dup` | the gain is **capacity**. Say so. |
| `[raw\|\|z]` ~= `z_perm` > non-z | the gain is **having a normalised block**, not cross-user coupling — a materially different and weaker claim |
| all four ~= | the sibling project's intervention **does not transfer** |
| any arm gains while **service falls** | **not admissible** under the service guard, whatever the EE |

## C. The outcome that is most dangerous to the stated goal, named before it can happen

The owner's requirement is **three Catfish, each raising EE**.

**If z-score raises EE substantially AND the route contrasts stay degenerate, then the gain
belongs to the normalisation and not to C1/C2/C3.** The honest paper would then say: the
headline improvement is an input transform; the three-route decomposition rides on top of it
and must find its own headroom **above the corrected base**, or be restated.

I am naming this now because it is the outcome I would be most tempted to reframe later.

**There is a specific reason to take it seriously.** I already observed the signature of a
degenerate reference and blamed it on something else: eight route contrasts taking only four
distinct values, with `FULL - ALL_NEUTRAL_CONTROL` **bit-identical** to `FULL - ONLY_C1`. I
attributed that to a smoke-test artefact (`anchor_count: 1`). A degenerate `a0` produces the
same signature. **Those two explanations have never been separated.** Separating them is what
COLLAPSE plus the corrected trainings will do.

## D. If the gain is real, what must be rebuilt — scoped now, not after

**Everything derived from the operating point changes. The sealed protocol mostly survives.**

| item | fate if the base moves | why |
|---|---|---|
| **`eta_ref`** | **must be recomputed — highest risk** | it is a frozen offline TRAIN calibration equal to pooled base EE, and it is the **exchange rate between bits and joules** in `F = B - eta_ref*E`. If base EE moves by a large factor, the selector is optimising the wrong trade-off **silently** — nothing errors. |
| source corpus (176,223 rows) | **regenerate** | rows were rolled out under the current policy; the visited state distribution is the collapsed one. This is distribution shift, not a label defect — separate from the known surrogate-label defect. |
| C3 coalition shards (4,552 rows / 22 anchors) | **regenerate** | same reason |
| bounded catalogue (~991 rows deployed) | **rebuild** | constructed from `a0` |
| panel ceilings (+1.944795% / +1.045609% / +0.905261%) | **recompute** | local to `a0`'s neighbourhood — see erratum 17 discussion and KILLTRIAGE |
| 16 seeds, 10 s coordinator budget, three forecast offsets | **survive** | none is a function of the operating point |
| **+0.5% decision margin** | **survives** | expressed as a percentage, so a level change does not move it |
| C1/C2/C3 **definitions** | **survive** | difference surplus / persistence forecast / interaction are structural; their **values** change |
| §3.2 `F = B - eta_ref*E - Phi` | **survives as written**; becomes a formulation change **only** if `eta_ref` is made adaptive | Calvo-Fullana Prop. 1 targets exactly the fixed-scalarisation form, so this is a live design question, not a bug fix |

**The cost is dominated by corpus regeneration, not by retraining.** Training is ~10 min per
seed. The exact source build has been running **2.3 hours** and is not finished. Any statement
of the form "we can just rerun it" is about the cheap half.

## E. Held, with a stated trigger — not dispatched

- **`ZCONTROL`** (`raw_dup` + `z_perm`, FULL only): Amendment 1 was appended to the prompt file
  after ZSCORE had already read it, so **it will not reach the running job.** The controls run
  as a follow-up reusing ZSCORE's view builder. Trigger: ZSCORE completes.
- **`DUALETA`** (adaptive vs frozen `eta_ref`, the second remedy in the same literature):
  **held on CROWDCOST.** If crowding is cheap in this physics, both z-score and dual-eta are
  remedies for a problem that does not exist here, and dispatching it now would be dispatching
  on a hunch.
- **Longer horizon rerun:** held until the 500-step contrasts exist, so that the horizon change
  is justified by LRSWEEP's pre-declared rule and not by a disliked outcome.
