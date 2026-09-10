# Note — C1 and C2 compete for the same signal; the Q1 schema decides which gets credit

Date: 2026-09-11 ~00:05Z · Controller
Source: `Z-VIEW-SCORING-2026-09-10.md` (`/home/sat/mcrl-v025-zscoring-ws`, SHA-256 `152a2607...`).
16 seeds x 20 development anchors, epoch 500, each run scored on its own panel, matched by
schema digest. *Information class: 500 unconverged constant-rate updates on surrogate labels —
paired comparison only; no route may be called dead or alive from this.* Marginal denominator:
the dropped arm's pooled EE.

| marginal | z view | Q1 v2 | Q1 v1 |
|---|---|---|---|
| `FULL - DROP_C1` | +1.353181 (+3.4513%, 14/16 +) | **+12.691200 (+42.9183%, 16/16 +)** | — |
| `FULL - DROP_C2` | +0.762113 (+1.9149%, 13/16 +) | -1.148719 (-2.6462%, 15/16 -) | **+6.13 (16/16 +)** |
| `FULL - DROP_C3` | -2.251681 (-5.2593%, 15/16 -) | -1.200528 (-2.7622%, 14/16 -) | **-10.04 (16/16 -)** |

## Readings

1. **z view: closed at this budget.** It reduces the C1 marginal at 16/16 paired seeds (mean
   -11.34 Mbit/J) and does not detectably change C2 or C3. Normalisation-vs-capacity attribution
   of the C1 reduction awaits `RAWDUP`.
2. **C1 and C2 compete.** Changing Q1 v1 -> v2 flipped C2 from +6.13 (16/16) to -1.15 (15/16
   negative) while C1 became +12.69 (16/16). Under additive decomposition, credit goes to
   whichever route has the better features. **This is a structural threat to "three routes each
   raising EE"**, independent of label quality, and it must be re-checked on exact labels at
   convergence (EXACT93, Q1V3TRAIN).
3. **C3 negative under every schema**, on labels 81.82% wrong. Not yet evidence.
4. **`ALL_NEUTRAL_CONTROL` is not a no-information control**: at 48/48 checkpoints its selection
   differs at 20/20 anchors from the zero-score knockout (11.495 Mbit/J). `FULL - ALL_NEUTRAL`
   measures a switch to neutral-trained heads, not an information knockout. Any claim worded as
   "informative vs no information" is wrong; the sealed wording "informative vs neutral source
   training" is the correct one and must be kept.

## Consequence for the C2 decision

The competition finding makes the C2TARGET question sharper: if a perfect oracle C2 adds little
once C1 can see gain, C2's positive marginals under weaker Q1 schemas were C1's work done by C2.
