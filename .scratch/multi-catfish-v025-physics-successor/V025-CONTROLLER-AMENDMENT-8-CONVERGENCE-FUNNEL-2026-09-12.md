# Amendment 8 to Ruling 2 — from exploration to a convergence funnel: D3-T0 is the development champion

Date: 2026-09-11 22:15 UTC (2026-09-12 06:15 Asia/Taipei). **Owner direction.** It changes what the development line does next;
it changes no Amendment 4 or 5 gate, and nothing here is formal evidence.

## 1. The numbers, re-derived by the controller from the DEVVAL JSONs (root-aware)

DEVVAL, 24 episodes, greedy, fresh env per episode; references on the same set: T0 = LP-prev(1,0) 117.66 M, `A m=2dB` 111.58 M,
`MAX_NOMINAL_GAIN` 110.03 M, RANDOM 52.00 M bit/J. A caution for anyone aggregating these files: the τ-sweep runs share
`arm_name`, `seed_index` and depth with the τ = 3 arm, so keys must include the run root.

| arm (k = 0) | ep 100 | ep 200 | ep 300 | agreement with T0 @300 |
|---|---:|---:|---:|---:|
| D0 | 103.059 | 104.697 | 105.492 | 0.391 |
| D2-T0 (τ = 3) | 107.432 | 109.864 | 109.493 | 0.577 |
| D2-null | 100.956 | 100.773 | 102.727 | 0.418 |
| **D3-T0** | **112.444** | **112.939** | **113.131** | **0.716** |

Paired per-episode, k = 0: D3 vs D2-T0 +4.67 % (23/24), +2.80 % (23/24), +3.32 % (24/24) at 100/200/300; **D3 vs D0 +9.11 /
+7.87 / +7.24 %, 24/24 at every depth**; D2-T0 vs D0 +3.79 % (22/24) at 300; D2-T0 vs D2-null +6.59 % (24/24) at 300.
k = 1 @100: D0 99.301, D2-T0 107.575, D2-null 97.647 M; D2-T0 vs D0 +8.33 % (24/24), vs null +10.17 % (24/24) — the D2 mechanism
replicates on a second development seed.

**The τ sweep landed and settles the D2 question**: τ = 1 gives 112.318 M and τ = 0.3 gives 112.325 M at ep 100, both **+4.55 %
over τ = 3 (24/24)** and both **−0.11 % against D3-T0 at the same depth** (paired −0.13 / −0.14 ± 0.37 %, 9/24 and 10/24). So
**D2 hyperparameter tuning is closed**; D2 stays as the soft comparator, and from now on its comparator configuration is
**τ = 1**, not the τ = 3 default (τ = 3 was selected for a clone with free logits; at τ = 3 only ~0.11 nats of the target is
learnable). Presenting τ = 3 as D2's representative result would understate the comparator.

## 2. What the funnel does next

1. No α sweep; no learning-rate, clipping or target-cadence sweep without a new measured reason.
2. **D3-T0 at DEV k = 1**, same MCRL-Dev-v0.1 configuration, stop at 100, paired to the existing k = 1 readout.
3. **D3-null**, the minimum control: same D3 loss, margin, `λ_E`, schedule, masks and gradient path, the T0 action replaced by a
   seeded random legal action from the declared DEV-NULL namespace, the T0 action entering no loss input. Focused tests only
   (target legal, independent of T0, DEV-NULL generator only, teacher weight zero still reduces to D0, the version hash covers
   the null identity), a short fresh-context review of that minimal diff, then k = 0 and k = 1 to 100.
4. **Promotion rule (development, not a formal gate)**: if D3-T0 again beats the paired D0 at k = 1 and beats D3-null in the same
   direction without QoS collapse, D3-T0 becomes the **provisional primary injection mechanism**; then k = 2 for D3-T0, D0 and
   D3-null as a third development seed. **Successive halving** — only survivors continue to 300.
5. Roll the frozen **baseline MODQN eq-(16) checkpoint** once on DEVVAL as a development reference, so the champion is read
   against the actual paper baseline and not only against simple rules. Development only; the formal evaluation, calibration and
   CONFIRM sets stay untouched.
6. **B2 stays closed** (T_SEQ `R_repr` ≈ 0.13–0.15 plus the full-context diagnostic); no oracle compute to rescue it unless the
   owner reopens it. **No exact-DR learner training** — ≈ 6.2 h per 1000-episode run and its oracle-first behaviour has not
   cleared the rate-tail concern; the credit interface stays pluggable and blocks nothing.

## 3. The freeze this funnel is aiming at

If D3-T0 survives k = 1, D3-null and the third seed, the provisional candidate freezes as **B1 execution contract + the current
ratio learner + T0 + D3 large-margin injection**, with D2-T0 (τ = 1) as the soft comparator, and the line moves to **E1** instead
of opening new hyperparameter families. The objective is a funnel, not expansion: one primary mechanism, verified across
development seeds and against a matched null, then frozen and taken toward S1 under the unchanged Amendment 4 and 5 regime.

## 4. Reading note for the paper, recorded now

On DEVVAL the champion at 300 episodes (113.13 M) is above `MAX_NOMINAL_GAIN` (110.03 M) and above `A m=2dB` (111.58 M), and at
0.96 of T0 (117.66 M). That is the first time a learner in this project has reached the non-learned rules on any set. It is a
development set with one seed at 300 episodes; it is not evidence for any claim, and the S1 regime still decides.
