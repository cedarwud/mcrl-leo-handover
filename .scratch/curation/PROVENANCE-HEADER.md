# Provenance header — mandatory at the top of every report from 2026-09-11 on

Copy the block below to the top of the report, directly under the title, and fill **every** line.
Write `UNKNOWN` rather than guess; write `n.a.` only when the field genuinely cannot apply (and say why).
If the report contains numbers produced under more than one set of conditions, give one block per
set and tag every number in the body with its block letter (`[A]`, `[B]`, ...).

Vocabulary is fixed in `.scratch/RESULTS-REGISTRY.md` §1; use its terms verbatim so reports can be
cross-checked by grep. Comparing two numbers whose blocks differ on any line marked **(C)** is a
cross-condition comparison and must be labelled as one in the same sentence.

```
PROVENANCE [A]
- physics / harness (C):   MODQN-harness | V025-a-r0-panel(<12-anchor dev | 93-anchor dev | 22-TRAIN | 20-anchor scoring | other: name>) |
                           V025-rate-target probe panel(<sealed | corrected-strict | corrected-simple> provisioning, <N> anchors) |
                           SIBLING-familyb-JULY | SIBLING-post-2026-08-05 | literature | other: <name>
                           + MDP modifiers: cap <off | k=3 per sat>, segment anchor <on | ablated>, interruption <off | on>, users <100>
- estimand (C):            pooled ratio-of-sums (Σbits/ΣJ, divided once) | mean-of-ratios (<over steps | episodes>) |
                           per-user mean (<formula + code rev>) | relative pooled-EE change (<reference arm>) |
                           trained calibrated scalar Σω·r/c | uncalibrated scalar (= 0.5·r1) | count / rate / diagnostic: <name>
                           + numerator: full-buffer Shannon, no demand cap | demand-capped at <X> | n.a.
                           + scoring horizon (V0.25 only): boundary-0 | full-48; selection horizon if different
- power accounting (C):    consumed, per-beam max over served users (MODQN default) | consumed TDM_AIRTIME |
                           consumed ADDITIVE (stress bound only) | V0.25 a-r0 TDM consumed | radiated-only | n.a.
- host + TLE archive (C):  local | sat ; archive = pinned b924c8a0 | local-unpinned (RANDOM_MASKED 53,060,175.56 check) |
                           sat-frozen pre-pin (RANDOM_MASKED 52,420,510.10 check) | V025 tape <world digest> ;
                           placebo arm + its value on this run: <arm = value>
- evaluation construction (C): fresh env per cell | shared env (_age_rng confound) ; seeds <train/env/mobility> ;
                           episodes <index range> ; greedy ε=0 | training-time log (ε=<x>) ; evaluator path (V0.25): dense evaluate_many | scalar
- tree / commit / flags:   <repo + commit> ; bootstrap = eq.16 per-head max | shared-continuation (D-1) ;
                           D-2 outage floor = off | −100 loose | per-step worst-served ; D-3 calibrated log = off | on ;
                           cap flag ; z-score = off | on ; penalty = none | <preset> ; other flags
- policy / checkpoint:     <arm name + full parameters> | frozen e6b063ef…1b09c28b | <run dir>/checkpoint-ep<N> (training ε at N = <x>) ;
                           selection rule for the checkpoint (final | other: <why>)
- n:                       evaluation episodes/anchors = <n> ; training seeds = <n> ; sem type (per-episode, unpaired | paired | bootstrap CI)
- in-sample?:              scoring anchors/episodes disjoint from training data? yes | no | n.a.
- status of this report:   SMOKE | PILOT | DEVELOPMENT | CONFIRMATORY ; supersedes: <file or none>
```

Rules that go with the header (each one is an erratum this project already paid for):

1. A number quoted from another report carries that report's block, not this one's (errata 23, 28).
2. `local` and `sat` figures are never compared unless both are on the pinned archive `b924c8a0` and the
   placebo row matches bit-for-bit (B0 ruling §4).
3. A V0.25-panel quantity (slopes, ceilings, rule scores, `eta_ref`) is never applied to the MODQN harness,
   and vice versa (erratum 28; erratum 23 §4).
4. A search winner is labelled a search winner; only a declared rule's score may be called a rule's score
   (erratum 23 §3).
5. A count (beams, slots, users) never shares a column with an EE; G-3 `active_beam_count` is relative
   slots out of 28, not physical beams (CAP-PENALTY §4 footnote).
6. Every pooled-EE figure is reported with served fraction beside it (erratum 28 correction).
7. Sibling-project figures are reference-only and carry the era tag (`SIBLING-familyb-JULY` vs
   `SIBLING-post-2026-08-05`), the estimand and the radiated-only denominator (EE-MAGNITUDE §1).
8. Nothing that was not measured goes in the report — no template numbers, no placeholders
   (penalty-arm `NOTICE-FABRICATED-PLACEHOLDER-IN-HISTORY.md`).
