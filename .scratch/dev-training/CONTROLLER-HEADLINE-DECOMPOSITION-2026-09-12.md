# The headline gain decomposes almost exactly in half, and the paper must say so

Date 2026-09-12. Surfaced by the DEVHARNESS lane's closing report on E1 and re-derived by me from the ep-300 seed
means I had already verified. **Development evidence only** — DEVVAL, three seeds, 300 episodes. It decides nothing
and it changes no gate. It changes how the result may be **worded**, which is why it is recorded now rather than
discovered during writing.

## 1. The arithmetic

ep-300 seed means (k = 3, 4, 5): `D3-T0` **113.555**, `D2-T0 τ=0.3` **113.189**, `D0` **103.783** M bit/J, against the
frozen baseline MODQN eq-(16) DEVVAL figure **94.413** M.

| comparison | value |
|---|---|
| `D3-T0` vs the published baseline | **+20.27 %** |
| `D2-T0 τ=0.3` vs the published baseline | +19.89 % |
| **`D0` vs the published baseline** | **+9.92 %** |
| `D3-T0` vs `D0` (the catfish's own contribution) | **+9.42 %** |

`1.0992 × 1.0942 = 1.2027` — the decomposition is exact and the two halves are almost equal.

## 2. What that means, stated bluntly

**Roughly half of the headline improvement over the published baseline is not the catfish.** `D0` is the same ratio
learner and the same B1 execution contract with **no teacher injection at all**, and it already beats the published
baseline by +9.92 %. The catfish mechanism contributes the other +9.42 % on top of it.

A paper that reports "+20.27 % over MODQN eq-(16)" and attributes it to catfish injection is wrong, and it is wrong in
a way a reviewer finds immediately, because `D0` is arm 1 of the S1 manifest and sits in the same table. **The
decomposition must be reported explicitly, in the abstract-level claim and not only in an ablation table.**

The honest form is two numbers: the backbone contributes about half, the catfish contributes the other half, and the
catfish half is what the drop-one and matched-null evidence is about.

## 3. Two caveats that stop this being over-read

1. **The baseline term is provisional.** 94.413 M is one of the six mutually incomparable values for checkpoint
   `e6b063ef…` that the Q9b adjudication §6 ruled **not citable as the baseline**. The authoritative decomposition
   comes from S1: Option A trains `MODQN eq.(16)` at the same 1000-episode budget in the same tree *and* rolls the
   frozen 9,000-episode checkpoint under the same protocol. Both split terms will move.
2. **This is DEVVAL at 300 episodes.** S1 runs 1000. The E1 record already notes the gap decays with depth
   (12.71 → 9.72 → 9.42 % at ep 100/200/300, decelerating), so the catfish half in particular may be smaller at S1
   depth. That was declared before S1 and still stands.

## 4. One thing that did get stronger

`D3-T0` at ep 300 is **0.965 of T0 = LP-prev(1,0)** and **1.032 of `MAX_NOMINAL_GAIN`**. Amendment 8 §4 recorded a
learner reaching the non-learned rules for the first time in this project, but on **one** seed. It now holds on
**three fresh seeds** that took no part in development. Still development evidence, still not a claim, but it is no
longer a single-seed observation.

## 5. Operational lesson from the same report

The DEVHARNESS wait loop that reported exit 255 was polling with `pgrep -f "run_dev_e0.py --arm 7"`, which **matched
its own command line** and therefore could never terminate — the runs had long finished. This is the waiting-side twin
of the unanchored-`pkill` hazard already on record: an unanchored `pgrep -f` pattern inside a poller matches the
poller. No result was lost. Recorded so the next poller excludes `$$` and anchors on the interpreter path.
