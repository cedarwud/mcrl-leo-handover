# Erratum 27 — a hysteresis rule dominates the trained learner on both axes and on its own objective

Date: 2026-09-11. Source: `.scratch/feasible-frontier/FEASIBLE-FRONTIER-2026-09-11.md`
(scripts and raw output in `.scratch/feasible-frontier/scripts/`). No training, no `update()`.

## The measurement

Rule `A m`: keep the incumbent legal option unless the best challenger's nominal gain exceeds it
by `m` dB. Uses only observation block 1 (incumbent) and block 2 (gain) — **expressible and
representable from the learner's own observation.**

| arm | pooled EE (bit/J) | handover | φ1 same-sat | **φ2 sat-change** | served | active beams | trained scalar |
|---|---:|---:|---:|---:|---:|---:|---:|
| `HOLD_WHILE_LEGAL` | 77,127,064.84 | 0.1427 | 0.0000 | 0.1427 | 0.9970 | 70.72 | +0.8371 |
| **`A m=12dB`** | **101,467,361.95** | **0.2258** | 0.0010 | 0.2248 | 0.9964 | 72.48 | **+1.2232** |
| `A m=9dB` | 105,701,579.47 | 0.2753 | 0.0052 | 0.2701 | 0.9987 | 69.21 | +1.1309 |
| **TRAINED `e6b063ef…`** | **93,110,907.97** | **0.2799** | 0.0556 | 0.2243 | 0.9988 | 67.90 | **+0.9033** |
| `A m=6dB` | 111,183,610.19 | 0.3643 | 0.0145 | 0.3498 | 0.9972 | 66.13 | +0.9538 |
| `B1_NO_NEW_BEAM` | 103,474,767.67 | 0.4250 | 0.0744 | 0.3506 | 0.9978 | **37.86** | −0.3665 |
| `A m=2dB` | **112,459,003.43** | 0.5860 | 0.0362 | **0.5497** | 0.9982 | 63.51 | +0.2845 |
| `A m=1dB` | 111,161,514.48 | 0.6613 | 0.0463 | 0.6150 | 0.9982 | 63.43 | +0.0328 |
| `A m=0` = `MAX_NOMINAL_GAIN` | 111,504,571.39 | 0.7120 | 0.0573 | 0.6546 | 0.9981 | 63.72 | −0.0885 |

**`A m=12dB` dominates the trained policy**: lower handover (0.2258 vs 0.2796) **and** higher
pooled EE (+8.9%). Confirmed at n=48: handover −16.9 sem, EE +6.7 sem. (`A m=9dB` weakened to a
handover tie at n=48, so the conclusion rests on `m=12`.) Three placebos bit-identical;
handover decreases strictly with margin across the nine grid points (built-in positive control).
A fallback defect in the consolidation arms was caught in smoke and fixed before any counted cell.

## What this withdraws

### 1. The ruling that closed the demonstration line

`V025-CONTROLLER-RULING-NO-DEMONSTRATOR-ON-THE-TRAINED-OBJECTIVE-2026-09-11.md` executed:
*"If no expressible rule beats the learner on the scalarized objective, there is no
demonstrator here and the whole demonstration-RL line closes."*

**The hysteresis rules beat the learner on its own trained objective**: `m=12` +1.2232 and
`m=9` +1.1309 against +0.9033 (n=48: +1.2101 vs +0.9167; scalar sem not measured this round,
but the gap is ~0.3 against per-arm sem ~0.02 in the earlier round). That ruling's search covered
only **myopic additive** rules; a rule with one step of memory — the incumbent — was never in it.

**The demonstration line is re-opened by a measurement, not by preference.** And the
demonstrator is representable (an argmax over blocks 1-2).

### 2. "The learner is a specification success and an endpoint failure"

ASK-3's framing, which the controller relayed as the paper's strongest diagnostic, **is false for
this checkpoint.** The learner loses on its own objective too. The more accurate statement:
**the frozen checkpoint is under-optimised on the objective it was trained on, and that objective
is also misaligned with the declared endpoint.** Both are true; neither alone explains the gap.
This is consistent with the three verified trainer defects (per-head bootstrap from each head's
own argmax, the outage free ride, the uncalibrated logged scalar) — a learner with those defects
is not expected to reach its objective's optimum. **Which of the two causes carries the gap is
now the stage-1 question**, and B0 is the instrument.

## Under the declared constrained endpoint (read after declaration, not fitted)

C-H, declared before these splits were read: `H_inter <= 0.6016` per user-step.

- **Best feasible non-learned rule: `A m=2dB`, 112,459,003.43 bit/J, φ2 = 0.5497.** It is also
  the highest-EE arm overall — above `MAX_NOMINAL_GAIN`, which is infeasible (φ2 0.6546).
- Sensitivity `H_total <= 0.40`: best feasible is `A m=6dB`, 111,183,610.19.
- **The EE frontier is nearly flat from m=2 to m=6** (112.46M → 111.18M, −1.1%) while total
  handover falls 0.586 → 0.364 (−38%). **Over this range there is almost no EE-vs-handover
  trade-off.** The learner is not trading EE for stability; it sits at a dominated point.

~~**This is now the bar.** A learner has a demonstrated job only if it beats **112.46M under
C-H**.~~ **Withdrawn the same day — it contradicts a standing owner decision.** The success gate
is **beating baseline MODQN only** (owner: *"能贏過當然是最好，但是沒贏過也沒關係"*; again:
*"理論上來說就是超過 baseline modqn 就算成功了吧?不需要去跟其他的 baseline 做比較"*). Non-learned
rules are **diagnostic instruments**: they locate the room, supply the catfish demonstrators, and
are reported in full — they are **not** a threshold. `A m=2dB` at 112.46M under C-H is reported as
the strongest feasible non-learned reference, nothing more. The causal comparison is
**multi-catfish MODQN vs MODQN with catfish off**, same corrected tree, objective, physics and
budget; the frozen checkpoint is an external historical reference only.

## Consequences for the C1/C2/C3 plan

| catfish | specialist | status after this measurement |
|---|---|---|
| **C1** (bits) | highest-bits rules — the `A` family at small `m` (`m=6`: 3.3787e14 bits) | exists; overlaps the `A` family |
| **C2** (handover guard) | **hysteresis `A m`** | **the strongest specialist found** — it is the frontier |
| **C3** (energy) | **`B1_NO_NEW_BEAM`**: joules **0.57x** the learner's, active beams **37.86 vs 67.90** | **exists and is structurally distinct** — half the beams, a different state region |

**C3 exists** — the open question in the plan is answered. **C1 and C2 overlap**: both are the
`A` family at different margins, so as specialists they differ in operating point, not in
information set. Whether they are two catfish or one must be decided by the coverage/overlap
test, not by the name.

## JSRL coverage gate — passed, with an unanticipated shape

Coverage `R(h)` jumps at `h=1` (1.00 → 1.60; out-of-95th-percentile 0.05 → 0.66), then oscillates
1.39-2.20 with no upward trend; out95 peaks 0.74 at `h=2` and falls to 0.28-0.42 for `h >= 4`.
Novelty sits mostly in block 4 (loads, 32-50%) and block 2 (SNR) — both set by the previous joint
action — and persists on rows with the same incumbent slot.

**Ruling:** the kill condition ("flat in h") is **not** met. The guide hands the learner states
well outside its own distribution after a single guided step. JSRL **survives the coverage gate.**
The step-then-plateau shape means a short guide prefix already delivers most of the novelty,
which is compatible with JSRL's own curriculum (it starts from a small `h` and shrinks it).
**Not measured:** whether the learner's trajectory returns to its own distribution after handoff.
Pooled EE rising monotonically with `h` is expected (the guide is better) and is not evidence
about learning, per the evaluation contract.
