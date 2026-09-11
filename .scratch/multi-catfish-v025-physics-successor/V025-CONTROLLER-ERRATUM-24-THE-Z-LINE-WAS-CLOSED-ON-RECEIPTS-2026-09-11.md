# Erratum 24 — the z line was closed on receipts, and "collapse is absent" was never a claim the instrument could make

> **PROVENANCE WARNING (added 2026-09-11 by the controller after CURATE):** this document contains at least one comparison between numbers produced under different conditions (physics/harness, estimand, host + TLE archive, or paired vs unpaired). Before citing any number from it, look it up in `.scratch/RESULTS-REGISTRY.md` (conditions per row, §2 lists the cross-condition comparisons) and check this document's status in `.scratch/DOCUMENT-STATUS.md`. Text below is unchanged.

Date: 2026-09-11. Withdraws two statements I made repeatedly, including to the owner.

## What I said

> collapse 和 z 兩條線在兩個物理都已經關閉

and, in the ruling `...-CATFISH-ATTACHES-TO-MODQN-...`, listed as a requirement met:
*"no collapse confound masking the measurement — **yes**, collapse and z lines closed in
both physics."*

## 1. There is no MODQNZ report

`/home/sat/mcrl-v025-mqz-ws/MODQN-Z-INTERVENTION-2026-09-10.md` **does not exist**. The
workspace holds a runner, a test and `artifacts/`; its git has **zero commits**. The
launch prompt commissioned the report (`MODQNZ.codex.log:113`) and **no conclusion was
ever written anywhere**.

**I declared a line closed on the existence of receipts rather than on a finding.** That
is the same error shape as reasoning from a cache defect I had documented that morning
(erratum 19): I treated the presence of machinery as the presence of an answer.

## 2. What the runs actually say, now that someone has read them

The runs did complete — the local 800/9000 log was stale. `MODQN_RAW` and
`MODQN_Z_INPLACE` both reached 9000/9000.

**The estimand is correct.** `run_modqn_z_intervention.py:379` computes
`pooled_bits / pooled_joules`, one division over two independently accumulated totals
(`:324-327`, `:340-341`). No mean anywhere on the EE path. **Unlike the sibling's
`argmax_EE`, this rests on EE in this project's declared estimand.**

| arm | pooled EE (bit/J) |
|---|---:|
| `MODQN_RAW` | 90,866,329.62 |
| `MODQN_Z_INPLACE` | 87,676,034.45 |

**−3.511%**, while spreading by +3.38 active physical beams. That is **row 4** of
MODQNZ's own pre-declared rule: **z lowers EE**, the sign this project's
`d(EE)/d(active) = −425,009.885 bit/J` predicts, at ~2.2x the magnitude the slope alone
gives.

**Three caveats the finding must carry, and they are not small:**
- **n = 1 training seed per arm.**
- **The frozen checkpoint was never loaded.** It is hashed only as a tamper anchor
  (`:102-106`, `:511-513`). Both arms are **from-scratch retrains**, and `MODQN_RAW` does
  not reproduce the frozen policy numerically. MODQNZ is therefore **not** a statement
  about `e6b063ef...`.
- **The width-controlled pair does not exist**: `MODQN_Z_CONCAT` died at 2300 and
  `MODQN_RAW_DUP` never started. So width is not controlled.

## 3. "Collapse is absent" was never available from this instrument

`collapse_metrics.py:46`: **"G-3 fails on a missing one, not on a bad value."**
**There is no numeric threshold for any of the four indicators.** G-3 is a **completeness
gate**. Completing the four lifts a procedural refusal; **it supplies no decision rule**.
So "collapse is absent because the indicators pass" was never a sentence this instrument
could support, with two indicators or four.

All four, computed on existing checkpoints (74.6 s, 0.89 GB, frozen sha unchanged; output
`.scratch/zclose/g3-indicators.json`). Cross-check: `active_beam_count` 7.470 reproduces
`MODQN-COLLAPSE`'s `argmax_distinct` 0.07470 exactly.

| | active_beam | argmax_agree | q_margin | q_entropy |
|---|---:|---:|---:|---:|
| FROZEN_MODQN | 7.470 | 0.4871 | 0.144691 | 0.996027 |
| **UNTRAINED (0 steps)** | 2.580 | **0.9225** | 0.114468 | **0.999150** |
| MODQNZ RAW | 9.110 | 0.3875 | 0.157988 | 0.996287 |
| MODQNZ Z_INPLACE | 6.510 | 0.4435 | 0.167438 | 0.995020 |

**The two indicators the gate exists to add discriminate nothing here.** A randomly
initialised network — 92.25% argmax agreement over 2.58 of 28 slots — scores `q_margin`
at **79.1%** of the trained policy's and `q_entropy` **higher**. `q_entropy` spans
6.06e-03 across all 400 profiles and correlates **−0.952 with `q_range`**: it is
normalised only by `log(n)` and never by the Q range, so it **saturates** — exactly the
defect the module's own docstring warns about for `q_margin` and fixes only there.

The current learner sits at **2 of 4** (`active_beam_count` 7.7344,
`argmax_agreement` 0.4185); `q_margin` and `q_entropy` are **not computable** from
existing artefacts, because only selected indices were cached, never the per-action score
rows. No proxy was substituted.

## Verdict

**Collapse here is UNDETERMINED — not absent, and not present.** Indicators 1-2 are
nowhere near degenerate, so nothing suggests a collapsed policy; but the instrument
licenses no verdict either way, and the two indicators added to settle it turn out not to
separate a trained policy from a random one.

## What changes

- The ruling `...-CATFISH-ATTACHES-TO-MODQN-NOT-STAGEC-...` lists "no collapse confound"
  as a **met** requirement. **It is not met; it is undetermined.** The rest of that
  ruling does not depend on it — the demonstration line closed for an unrelated reason
  (no expressible demonstrator) — but the row is wrong and is corrected here.
- **z-score defaults to OFF** in anything that runs next. Not a new gate: the only
  measurement in this project's declared estimand has it lowering EE by 3.511%, and the
  physics gives the same sign. n=1, so this is a default, not a finding.
- **`q_entropy` is a defective indicator as implemented** (log(n) normalisation without
  Q-range normalisation, −0.952 correlation with `q_range`). Recorded; not fixed here,
  because fixing an instrument in the middle of an open question is how instruments come
  to agree with expectations.
