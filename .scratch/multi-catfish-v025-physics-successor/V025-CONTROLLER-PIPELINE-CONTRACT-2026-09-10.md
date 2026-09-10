# Pipeline contract — the interfaces, written down once

**2026-09-10 13:15 UTC.** Today's four real blockers were **not** failed tests. They were
interface mismatches between stages built in isolation against assumed contracts:

| blocker | found | how |
|---|---|---|
| the only code that trains arms is hard-coded to 2 epochs (`run_c3_panel_smoke.py:612`, `:721`), `--output` its only argument | 12:10 | reading the CLI |
| the runner fails closed without `mcrl-v025-stagec-c3-coalition-shard-v2`; the corpus has none | 12:33 | reading the reader, then `find -iname '*coalition*'` |
| the stored physics has no joint evaluation with changed set ≥ 2, so `Psi_A` is unrecoverable | 12:45 | `COALSHARD` Part 1 |
| the health monitor's `run_resumable\.sh` regex never matched `run_resumable2.sh`, so every job launched after 09:50 looked orphaned | 12:52 | checking a flagged "orphan" before killing it |

**Every one would have been visible at design time if this document had existed.** It exists
now. A stage may only be built against what is written here; if a stage needs something not
listed, the contract is amended **first**.

---

## Stage 1 — corpus

**Produces** `artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM/`, generated in a
pre-declared anchor order, physics separated from a rebuildable view layer.

| layer | schemas | consumer |
|---|---|---|
| physics | `-physics-shard-v1`, `-configuration-physics-v1`, `-row-physics-v1`, `-anchor-context-v1` | rebuilds any view or target without re-running physics |
| view | `mcrl-v025-exact-source-view-shard-v1` | Stage 2, C1/C2 |
| view | `mcrl-v025-stagec-c3-coalition-shard-v2` | Stage 2, C3 — **`COALBUILD` is adding this** |

**Requirements, all load-bearing:** canonical JSON with a valid `.sha256` sidecar per shard;
C1, C2 and C3 shards share **one physics digest**; targets are the declared
`c1_difference_surplus` and `c2_persistence_forecast` and the exact `Psi_A`, never the
`kappa*tanh(log ratio)` surrogate; `Psi` is **exactly zero on every singleton**; the coalition
support and its **size distribution** are reported, because a support dominated by `|A| = 1`
bounds what any C3 fit can mean.

**Known constraint:** `Delta F(A)` for `|A| >= 2` requires a **real joint evaluation** and is
not reconstructible from singleton outcomes.

## Stage 2 — training runner

`/home/sat/mcrl-v025-retrain-ws/scripts/run_stagec_training.py`, sha256
`4885570b8552dc95a2143764cc10bd7b78f06504d63c4fa07866817bfc797d66`.

**Consumes** the view layer only — any admitted path containing a `physics` component is
rejected. **Mandatory:** `--corpus --output --epochs --seeds`. `--checkpoint-cadence` defaults
to 100 and is checked against the sealed value. `--seeds N` means `V025_LEARNER/seed/{1..N}`;
a value other than the v1.1-required 16 emits a loud notice and is recorded as nonconforming.
**No silent 12-seed default.**

**Sealed bounds, verified:** at most **2,000** completed epochs; only the production five-arm
inventory (`learner.py:1170-1171`, `:1186`). Head literals unchanged: C1 `(8,)` relu lr `1.0e-2`
gauge_beta `0.2`; C2 `(100,50,50)` tanh lr `1.0e-3` gauge_beta `0.1`; C3 `(64,64)` relu
lr `1.0e-3`; Adam `(0.9, 0.999)`.

**Start gate:** the arm-difference fixture must PASS for all four pairs. Any identical raw
score, identical selection, or identical pooled fixture EE is a **hard failure**. Currently
PASS 4/4.

**Emits** checkpoints at cadence, each verified readable by the sealed loader in-run, plus a
launch receipt.

**Must also record, for Stage 3 axis B:** **physics evaluations consumed per arm** and
**wall-clock to decision**. These were added on 2026-09-10 after the figure plan showed F8
could not otherwise be drawn. **If the runner does not record them, that is a Stage 2 defect,
not a Stage 3 workaround.**

## Stage 3 — scorer

`SCORER`, in `/home/sat/mcrl-v025-selector-ws`. **Consumes** Stage 2 checkpoints. One run,
scored twice.

**Axis A, coordination:** pooled EE on the **declared full-buffer numerator** — no demand cap,
per declaration v1.8 item 5. Reference `ALL_NEUTRAL_CONTROL`; **`BASE` is never a reference and
never relabelled as one.** Contrasts `FULL - ALL_NEUTRAL_CONTROL` and `FULL - DROP_Ci`, at
**every** checkpoint.

**Axis B, acceleration:** pooled EE as a fraction of the certified fixed point's, at the
contract's **10 s** budget (v1 §F2), with **the anytime incumbent at the same budget** reported
beside every arm.

**Knockout check, required before the primary number may be reported:** from the `FULL`
checkpoint, evaluate the all-terms-removed selection and report anchors differing from
`ALL_NEUTRAL_CONTROL` and their pooled EE difference. If they coincide everywhere, the primary
contrast is reported as a **knockout** contrast and labelled as such.

**Every figure names:** reference and its construction, information class, estimand, numerator,
panel identity, and **fixed-point traversal order** — traversal order alone moves the fixed
point by `8.13%` (SEALED) / `1.62%` (MARGIN_Q), about nine times the coordination band.

## Stage 4 — figures

Eight, per `V025-CONTROLLER-FIGURE-PLAN-2026-09-10.md`. F1-F5 need no training and are
buildable from receipts already on disk. F6-F8 consume Stage 3 tables.

---

## The rule this document imposes

**Before any stage is built, its consumer's contract is read — not assumed.** Where a consumer
does not exist yet, its contract is written here first. Today two blockers were found by
reading a CLI and a reader; both would otherwise have surfaced at launch, after the preparation
was already spent.

**And: run the reader, do not reason about it.** Reasoning about whether stages connect is
free and was wrong twice today.
