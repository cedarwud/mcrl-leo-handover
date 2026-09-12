# Controller probe readout — the judge, the two specialists and the composite rule, before any MC2 learner run

Date 2026-09-12. **Development lane, non-learning.** No learner was trained; the only learner involved is the frozen
`D3-T0` k = 8 ep-100 checkpoint, used read-only as one of the four backgrounds. This is the §7 pre-training diagnostic of
contract r2 and it is **not a gate**: it decides nothing, and every number here is a rule-level or background-level
measurement on the P0 collection (env `9_202_500+i` / mobility `9_203_500+i`, i = 0…23, 24 episodes, 100 users, 10 steps),
pinned TLE `427e6a91…`, judge `κ = (n_served, B − η₀E)` at the frozen `η₀ = 110 507 234.834 444 57` bit/J.
Script `/home/sat/mcrl-v025-mc2-ws/controller-probe/mc2_judge_probe.py` (sha256 `a11ebeec…`), outputs `probe-*.json`
beside it. Probe-only uniform draws: `default_rng((9_243_000, 900 + 2i + j))`, index ≥ 900, disjoint from every run's
seed index.

## 1. Rule rollouts (pooled Σbits/Σjoules over the 24 episodes, one estimand, divided once)

| rule | pooled EE (M bit/J) | vs T0 | bits | joules | served | beams | p10 (M bit/s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `T0 = LP-prev(1,0)` | 116.963 | — | 3.0949e14 | 2.6460e6 | 0.99896 | 57.45 | 109.52 |
| `T_NEXT` | 103.111 | −11.84 % | 2.2376e14 | 2.1701e6 | 0.99538 | 46.77 | 69.61 |
| **composite = T0 with judge-approved T_NEXT overrides** | **124.130** | **+6.13 %** | 3.1312e14 | 2.5225e6 | 0.99900 | 54.60 | 116.68 |
| composite-R = T0 with judge-approved **uniform random** overrides | 119.691 | +2.33 % | 3.2634e14 | 2.7265e6 | 0.99946 | 59.25 | 115.76 |
| frozen `D3-T0` learner (k8 ep-100, greedy) | 111.525 | −4.65 % | 3.2286e14 | 2.8950e6 | 0.99854 | 63.03 | 117.51 |
| uniform random actions | 52.139 | −55.42 % | — | — | 0.93867 | 76.67 | 26.29 |

**The composite rule is better than either specialist alone, and not by trading throughput for energy**: against T0 it
gains bits (+1.2 %) *and* spends fewer joules (−4.7 %) with the same service (+0.004 pp) and a higher p10 (+6.5 %).
`T_NEXT` alone is 11.8 % *worse* than T0 — it saves 18 % of the joules but sheds 28 % of the bits. So the rule-level
evidence says the two sources are complementary **only when something arbitrates between them per decision**, which is
exactly the mechanism under test. This is a rule-level statement about the *target* the margin points at, not a claim
about what a learner will reach.

**How much of that is the judge and how much is `T_NEXT`'s content — the rule-level analogue of FULL vs B-null.** The
same judge fed content-free uniform proposals (composite-R) also beats T0, by **+2.33 %** (24/24 paired episodes
positive, median +2.39 %, min +0.04 %). The composite with `T_NEXT` beats composite-R by **+3.71 %** (23/24 paired
positive), and beats T0 by +6.13 % (24/24, median +5.96 %, min +2.35 %). So, at rule level:

- the judge's filtering alone is worth about a third of the effect, and `B-null` is therefore a real comparator, not a
  straw man — but it does not account for the effect;
- the two halves work by **different physics**: composite-R buys bits (×1.055) by lighting *more* beams (59.25) and
  spending more joules (×1.030), while `T_NEXT`'s overrides cut joules (×0.953) with *fewer* beams (54.60). The
  energy-side direction is specific to `T_NEXT`'s content, which is what the k8 single-arm readings already suggested
  (`T_NEXT-only` joules ×0.856).

None of this is a learner result, and none of it is a gate; it is the declared §7 diagnostic, read before any ep-100
file existed.

## 2. How often the judge lets the challenger through (per decision row, t < T−1, users with a legal action; 21,600 rows)

| background `x` | `a^B ≠ a^A` | **`a^B` overrides** | `a^R ≠ a^A` | `a^R` overrides | `a^A` beats `x` | v2 winner x / A / B |
|---|---:|---:|---:|---:|---:|---|
| T0 joint | 0.676 | **0.286** | 0.961 | 0.141 | — | 0.714 / — / 0.286 |
| composite-rolled | 0.648 | 0.270 | 0.961 | 0.138 | — | 0.730 / — / 0.270 |
| frozen `D3-T0` learner | 0.671 | **0.308** | 0.962 | 0.155 | 0.156 | 0.622 / 0.130 / 0.248 |
| uniform random (the ε ≈ 1 regime) | 0.689 | 0.391 | 0.962 | 0.258 | 0.707 | 0.178 / 0.489 / 0.333 |

- **B is not inert.** At the learner background the override rate is 30.8 % of all decision rows — 31 × the contract's
  1 % activity floor. v2's B-win share there is 24.8 %, and its total margin dose is ≈ 38 % (A 13 % + B 25 %).
- Overrides are decided by the `B − η₀E` term, essentially never by the served count (served-decisive ≈ 0.03 %), so the
  service floor in the key is doing its job without driving the decisions.
- The per-step override rate is stable (0.17–0.43) with no structural collapse at any step; `t = T−1` is absent by B's
  declared abstention.
- **A random proposal is approved 14 % of the time** (26 % in the ε ≈ 1 regime), with a κ-lead distribution of the same
  order as T_NEXT's. So `B-null` is a real competitor, not a straw man: the judge plus content-free proposals is itself a
  stochastic one-step best response. Whether that converts into pooled EE is the composite-R row in §1.

## 3. Measurement hygiene

- **Parity**: the judge's pre-step evaluation of the executed joint action equals the committed step's bits and joules to
  `0.0` absolute and its served vector exactly, on all 216 checked steps per background.
- **No RNG contamination**: the env generator's bit-generator state is bit-identical before and after every judge batch
  (0 violations in all modes); the judge only ever sees a deep copy.
- Cost, measured: ≈ 1,600 judge evaluations per episode at ~8–9 ms each; the FULL-style background costs ≈ 310 s per 24
  episodes single-threaded. The learner background adds one forward pass per step.

## 4. What this changes and what it does not

- It changes **nothing** in the contract: no gate, no threshold, no cell, no seed.
- It is the declared answer to "is the second specialist structurally inert under a one-step judge": **no**, at 28–31 %
  of decisions, so a failed activity check later cannot be blamed on structure.
- It does **not** show that the learner can carry the composite target (the judge reads step-`t` fading and the
  concurrent actions, which the 113-dim observation does not contain — contract §1, N-a2), and it does **not** separate
  T_NEXT's content from the judge's filtering. The ep-100 matrix and the `B-null` cell are what address those.
