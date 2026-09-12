# Controller acceptance of S1-PREP, and one finding that changes how Amendment 12 must be read

Date 2026-09-12. `S1-PREP` is **accepted and PARKED**. Formal S1 stays **HELD** under Amendment 14; the fresh-context
review is **not** dispatched. Everything below I verified from the artefacts, not from the lane's report.

## 1. Verified

| item | value | check |
|---|---|---|
| S1 manifest | `artifacts/s1/S1-MANIFEST-2026-09-12.json` | sha256 **`7646bb00ab52778d60a48501933308c03ee1d6c39e8a9d0e1d809163983726fd`** — recomputed by me |
| `T0-XEP` reference | `artifacts/dev-e0/t0-xep-reference.json` | sha256 **`9bb0c01efdd403fb0e765bd133d718f7b07273a188c9f173b39fbb112ae1900c`** — recomputed by me |
| run matrix | 18 specs, **18 distinct**, 18 `arm_configs` | no collision |
| arms | 6, with the Amendment 13 §3 names and roles | correct |
| seeds / depth | `[0, 1, 2]` × **1000** episodes | correct |
| **checkpoint** | `eval_at = [1000]`, 24 evaluation episodes | **a single checkpoint — checkpoint shopping is structurally impossible, not merely forbidden** |
| `S1-TRAIN` | train `9251000`, env `9252000`, mobility `9253000` | correct |
| `S1-NULL` | `(9261000, k)` | correct |
| forbidden list | calibration, CONFIRM **and the DEV triples `9201000–9203999`** | Amendment 13 §4 enforced in code, not only in prose |
| rolled reference | `e6b063ef…1b09c28b`, `training: none` | Amendment 13 §2 |
| ε decay | **222** for 1000 episodes | = E0/E1's 67/300 scaled exactly; the frozen schedule is preserved, not re-tuned |
| TLE | `427e6a91…8fe9` | pinned |
| XEP seeds | env `9_241_500`, mobility `9_241_501` | verified unused anywhere else; no collision with the `(9_241_000, k)` RNG keys |

**Formal / calibration / CONFIRM untouched.** The S1 code *declares* the formal bases — it must, since S1 will read
them — but nothing stepped them. The preflight touched DEV `9_201/9_202/9_203`, DEVVAL `9_211/9_212` and DEV-NULL
`9_241_500/501` only, in its own scratchpad root, 20 episodes, no `runs-e1-*` opened, no `sat` compute.

## 2. The finding: the second null leaks, and the leak is measured

Preflight `D3-XEP`: **`t0xep_agreement = 0.1957`** against an exact random-legal expectation of **0.0387**. `T0-XEP`'s
advice coincides with the real T0's advice **five times more often than chance**. Amendment 12's residual-leakage
clause fires: the null is **plausible but not fully uninformative**, and the cause is structural — the score function
is identical, so systematically good slots stay systematically good even on another episode's geometry.

### 2a. Which way the bias runs, and why that matters

With `ρ_info = (EE(D3-T0) − EE(D3-XEP)) / (EE(D3-T0) − EE(D0))`, a partly informative null **raises** `EE(D3-XEP)`,
which **shrinks the numerator** and therefore **shrinks `ρ_info`**. The measured `ρ_info` is a **lower bound** on T0's
state-specific information share. The leak makes the test **harder to pass**, not easier.

### 2b. The asymmetry, declared now so it cannot be invented later

- **If `ρ_info ≥ 0.5`**: the conclusion is **strengthened**. It cleared the bar despite a null that was itself partly
  informative, so the true information share is at least that high.
- **If `ρ_info < 0.5`**: the reading is **ambiguous, not a verdict for the structural-prior interpretation.** We could
  not then distinguish "most of the gain is a generic structural prior" from "our null leaked 5× above chance". The
  Amendment 12 §3 middle band may **not** be used to restate the claim until the leakage's contribution is quantified.
- **If `ρ_info ≤ 0`**: unchanged — review, as Amendment 12 §3 already says.

This is written before S1 runs precisely so that a disappointing `ρ_info` cannot be waved away with "the null leaked"
after the fact, and a good one cannot be inflated.

### 2c. What is *not* being done about it

No redesign, no second null variant, no new lane — Amendment 14 caps the work and the leak is conservative in
direction. `T0-XEP` stays sealed and is never regenerated. If `ρ_info` lands in the middle band, quantifying the
leakage contribution becomes a controller decision **then**, on the evidence, not a pre-emptive expansion now.

## 3. Two Amendment 12 gaps, both ratified rather than improvised

1. **The reference policy was unspecified.** Resolved as **T0 itself**, and I ratify it: a T0-rolled reference has a
   realistic lit-set and beam-load structure, so the null carries the structural prior the amendment actually wants
   tested; a random-legal reference would scramble the loads and make the null *less* plausible, which is the opposite
   of what §2 asks for.
2. **DEV-NULL was declared as an RNG namespace, not an env/mobility one.** Using `9_241_500 / 9_241_501` as the
   reference episode's env and mobility seeds is a well-formed extension inside the same block; I verified it collides
   with nothing, including the `(9_241_000, k)` RNG keys. Ratified.

## 4. Three things a launcher must know, recorded because they are silent failures

1. **`run_b0_pilot.py` leaves ε-decay at 2000.** On a 1000-episode S1 that would leave the arm still exploring at the
   end and would confound the win gate. S1 uses 222 on both sides. Do not launch S1 through that script.
2. **`run_cf3_pilot.py --arm A0` reads the calibration episodes.** It must never be used for S1 — it would spend a
   protected set silently.
3. **The new `DevSettings` fields change every arm's config hash**, so **E1 roots cannot be resumed against this
   code**. Fresh roots only. This is correct behaviour of the identity scheme, not a defect, but a resume attempt
   would look like a harmless restart and would not be one.

## 5. Disposition

`S1-PREP` is parked: no review dispatch, no further S1 cycle, no `sat` compute, no protected episode set. The manifest
and the sealed reference are committed and hashed **before any formal outcome exists**, which satisfies Amendment 13
§7 condition 7 whenever the launch question returns. Amendment 13 §7's remaining conditions are met **except** the
fresh-context review, which is deliberately held until the final S1 manifest is known — that is, until the
Catfish-2 successor lane is adjudicated.
