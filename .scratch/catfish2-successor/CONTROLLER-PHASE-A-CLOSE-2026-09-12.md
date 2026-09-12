# Controller adjudication — Phase-A `T_H` closes; `T_DELTA` is promoted to the fallback

Date 2026-09-12. Read against Amendment 14 §6b on two seeds, then §9 and §10. Every number re-derived by me from the
raw DEVVAL JSONs in `/home/sat/mcrl-v025-cf2s-ws/runs-phaseA-k6` and `runs-phaseA-k7`.

## 1. The two seeds, verified

| seed | D0 | `D3-T_H` | vs D0 | vs null | paired vs D0 | served Δ | p10 | bits | joules |
|---|---|---|---|---|---|---|---|---|---|
| k = 6 | 97.717 M | 101.847 M | **+4.227 %** | ×1.6255 | **23/24** | +0.000 pp | ×1.928 | ×1.1724 | ×1.1249 |
| k = 7 | 101.485 M | 102.085 M | **+0.591 %** | ×1.9666 | **14/24** | +0.100 pp | ×1.505 | ×1.1818 | ×1.1749 |

Pinned TLE on all six runs. `D3-null` reproduced the E0 hard-null signature on two seeds E0 never ran (−35.88 % /
−48.85 %, served 0.92663 / 0.92342) — a genuine harness check, and it passes.

## 2. Amendment 14 §6b on two seeds

Clauses 1, 3, 4 and 5 pass on both seeds: direction positive against `D0` and the null; `served` never worse;
`p10 ≥ 0.5 × D0` by a wide margin; bits `≥ 0.95 × D0`. Clause 2 is 23/24 and then **14/24** — a coin flip.

**Clause 6 fails.** The two-seed mean effect is **+2.409 %** and the two-seed spread is **3.635 pp** — the spread is
*larger than the effect*, and E0's own ep-100 seed spread for `D3-T0` is 4.23 pp. The per-episode gap vectors of the
two seeds correlate only 0.336. At k = 7 the effect is essentially absent. **The effect does not separate from
development seed variation and therefore is not counted.**

## 3. What actually replicated, and why it is not a rescue

`D3-T_H`'s **absolute** EE is 101.847 / 102.085 M — a **0.23 %** spread — while its paired `D0` moves 3.78 %. The
tempting reading is "the variance is in `D0`, not in T_H, so the gap is only noisy because the denominator is".

That reading is real but it argues **against** T_H, not for it. What it says is that **`T_H` pins the learner near
102 M regardless of what the baseline would have done**: when `D0` is weak it looks like +4.2 %, when `D0` is strong
it looks like +0.6 %. `T_H` is a **stabiliser, not an amplifier** — and the level it stabilises at is the problem.
At the same depth, the same schedule and the same DEVVAL set, `D3-T0` delivers **112.17 / 111.77 / 112.45 M** at
ep 100 (E1 k = 3/4/5). `T_H` pins at a level the existing champion already exceeds by about **10 %**.

The behavioural signature did replicate cleanly on both seeds — `H_inter` 0.6455→0.2369 and 0.6933→0.2272, `H_intra`
0.110→0.0025 and 0.0129→0.0016, absolute p10 133.84 / 133.58 Mbit/s, service held, null margin 24/24 on both. `T_H`
is doing something real and reproducible. It is just not producing a counted EE effect, and the thing it does produce
sits below the incumbent.

The lane recorded the variance-location point as an observation and explicitly refused to use it as a substitute
clause-6 estimator. That was the correct call and I am ratifying it rather than quietly adopting the rescue.

## 4. Ruling

**`T_H` closes.** Amendment 14 §9's precondition — *"after `T_H` has independently survived k = 6 and k = 7"* — is
**not met**, so the five-arm FULL factorial is **not authorised**. Per §10, **`T_DELTA` is promoted to the one
fallback candidate.** No third seed, no hysteresis sweep, no margin sweep, no re-reading of the two seeds.

## 5. The tension I am not hiding, and my recommendation

§2's hypothesis was about **incremental** value through D3 "even if the specialist is not a better standalone
controller", and the Phase-A canary tests standalone transfer, not increment. So it is *formally* possible that
`FULL{T0, T_H}` helps while `D3-T_H` alone does not, and §9's gate forecloses that test.

I am applying the pre-declared gate rather than reinterpreting it — reinterpreting an owner gate to keep a candidate
alive is the exact failure mode these amendments exist to prevent. If the owner wants the FULL question answered
anyway, that needs explicit authorisation, and **my recommendation is against it**, for a mechanistic reason rather
than a procedural one: in the set-valued loss the learner picks whichever of `{a_T0, a_TH}` its own TD score prefers,
so `T_H`'s nominations are filtered by that score. Given that `T_H` pulls toward ~102 M while T0 already delivers
~112 M, most `T_H` nominations are options the learner should reject. The upside is bounded to the states where T_H
is right and T0 is wrong, and nothing measured so far locates such a set. Five runs is cheap, but the mechanism for
gain is thin and the pre-declared gate says no.

## 6. Disposition

`CF2S-PHASE-A` writes up and stops; no FULL or set-valued work begins. `CF2S-PHASE-B0` continues and is now the
lane that decides whether a second Catfish exists at all. Formal S1 remains **HELD**; `S1-PREP` stays parked. If
`T_DELTA` also fails, Amendment 14 §11 applies: the single-source S1 is **not** silently launched under a
"Multi-Catfish" framing — the evidence goes back to the owner to choose the framing.
