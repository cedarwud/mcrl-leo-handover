# Amendment 13 to Ruling 2 — the frozen S1 configuration, fresh formal namespaces, and conditional launch authority

Date: 2026-09-12. **Owner ruling**, issued after reviewing the E1 result, Catfish-2 Stage 0, Amendment 12 and the S1
proposal. It opens no new development tuning. **Once S1 starts, the configuration is frozen.**

## 1. E1 is closed

`D3-T0` passed all three fresh seeds and neither Amendment 10 §4 reopen condition fired. **Do not reopen D3 or D2 and
do not open any hyperparameter search.**

## 2. Baseline: Option A adopted

- **Train MODQN eq.(16) at 1000 episodes × the 3 S1 seeds** as the **primary same-budget competitiveness comparison**.
- **Also roll the frozen `e6b063ef…` 9000-episode checkpoint once** on the same formal evaluation set, labelled
  separately as the **published / frozen reference**.
- The 9000-episode checkpoint is **not a conjunctive S1 veto**, because its training budget is different. If D3 beats
  only the 1000-episode baseline, the claim is explicitly **"same-budget superiority"**. Superiority to the fully
  trained 9000-episode reference may be claimed **only if that comparison also succeeds**.

## 3. The frozen S1 arm list — six trained arms plus one rolled reference

Amendment 6's "formal review of all nine arms remains mandatory before S1" is **superseded for S1** by the later
convergence rulings. **Do not resurrect the closed D1 / D4 / B2 / exact-DR arms merely to satisfy the old count.**

| # | arm | role |
|---|---|---|
| 1 | `D0` | control, catfish off — the paired causal comparator |
| 2 | `D3-T0` | the frozen primary |
| 3 | `D3-null` | matched hard null (Amendment 4's conjunctive gate) |
| 4 | `D3-XEP` | plausible-but-uninformative null (Amendment 12) |
| 5 | `D2-T0 τ = 0.3` | strongest soft comparator, no superiority claim |
| 6 | `MODQN eq.(16)` @ 1000 | same-budget win gate (§2) |
| — | frozen `e6b063ef…` @ 9000 | **rollout only, no training** — the published reference (§2) |

**The mandatory fresh-context review covers this entire declared S1 harness**: all six trained arms, the rolled
reference, the launcher, seed isolation, resume logic and aggregation.

## 4. Fresh formal S1 training namespaces, declared before launch

For k = 0, 1, 2:

- `S1-TRAIN train    = 9_251_000 + k`
- `S1-TRAIN env      = 9_252_000 + k`
- `S1-TRAIN mobility = 9_253_000 + k`

All six trained arms use the **same-index** S1-TRAIN triple. **DEV training streams may not be reused for S1.**

**Controller verification (2026-09-12, before any S1 run):** all four ranges were grepped across the repository in both
`9_25x_000` and `925x000` spellings. Zero seed declarations. The only textual hits are coincidental digit substrings
inside float arrays — three in the closed V0.6 stage-C artefact
`artifacts/multi-catfish-v06-c2-k1-t1-source-gate-20260902-r1/` and two inside `q_entropy` / `q_margin` floats in
`artifacts/training-2026-08-2*/episode-logs.json`. The ranges are unused. A parallel sweep of the `sat` workspaces was
run for the same tokens.

## 5. Fresh formal null RNG namespace

`D3-null` keeps **exactly the same scientific construction** — seeded uniform random **legal** action, same D3 loss,
margin, weight, masks and gradient path — but S1 draws from:

- `S1-NULL = default_rng((9_261_000, k))`, k = 0, 1, 2

The development `(9_241_000, k)` random-action streams may not be reused in the formal screen. **This is seed
isolation, not a mechanism change.**

**`T0-XEP` is different.** It keeps the **one fixed DEV-NULL reference trajectory** Amendment 12 requires; its identity
and sha256 are sealed before S1 and it is **never regenerated**.

## 6. Catfish-2 Stage 0 is closed with zero survivors

- The T0 decomposition is **rejected**; T0 remains one candidate source.
- **Do not retrospectively promote `A m=12dB`** from CONTROL to candidate despite its near-miss `CR = 0.4847`.
- **Do not move the `CR` threshold. Do not run a `D3-A12` canary.**
- A successor Catfish-2 lane, if opened, must target **information T0 does not already use** (temporal or cross-user
  structure, for example) — **not** another gain/load reweighting or coefficient sweep. It stays DEV-only and does not
  block S1.

## 7. Conditional S1 launch authority — granted now

**No further owner round-trip is required if and only if all of these pass unchanged:**

1. `T0-XEP` implementation committed; the fixed reference identity and sha256 sealed.
2. Clean tests green.
3. Every named `T0-XEP` / S1 mutant individually red.
4. DEV-only preflight ≤ 20 episodes passes.
5. `D3-null` and `MODQN @ 1000` paths verified.
6. Fresh-context review of the **complete** S1 harness returns **0 INVALIDATES and 0 BIASES**.
7. The six-arm manifest, the S1-TRAIN / S1-NULL namespaces, the 1000-episode depth, the frozen hyperparameters and the
   formal evaluation namespace are **committed and hashed before any formal outcome exists**.
8. **No formal evaluation, calibration or CONFIRM episode has been touched during preparation.**

If all hold: launch the **complete 6 × 3 = 18 trained-run S1 matrix together**, and roll the frozen 9000-episode MODQN
reference under the same formal evaluation protocol.

**Do not partially open the formal set with only a subset of arms.**

If any condition fails, or S1-PREP finds a substantive specification defect, **stop before the formal set** and return
it to the controller.
