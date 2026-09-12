# Amendment 14 to Ruling 2 — the bounded Catfish-2 successor lane, and a HOLD on formal S1

Date: 2026-09-12. **Owner direction.** Written and committed **before any counted run of this lane exists.**

## 0. What this supersedes, and what it does not

It supersedes **only Amendment 13 §7's conditional automatic S1 launch authority**. Everything else stands unchanged:
the E1 freeze; the six-arm single-source S1 preparation; `T0-XEP` and Amendment 12; the `S1-TRAIN` / `S1-NULL`
namespaces; the baseline Option-A ruling; the fresh-context S1 review brief; and every Catfish-2 Stage-0 result
already obtained.

**Controller verification at the time of this direction (2026-09-12):** the formal evaluation set is **untouched**.
A sweep of every `sat` workspace for `9_111_000` / `9_112_000` returns hits only in pre-existing artefacts of closed
lanes (`arch-ws`, `b0-ws` TLE files, `b2-repr-ws`, `beam-ws`, `c1c2-ws`, the `catfish2-ws` tarball) and **zero hits in
`mcrl-v025-dev-e0-ws` or any new result root**. No `python` process was running on `sat`. That state is preserved.

## 1. Stage-0's verdicts are historical facts and are not rewritten

The T0 decomposition was rejected. `C-Q′-local`, `C-Q′-global` and `C-RC′` were DROP. `A m=12dB` was declared a
CONTROL: it cleared four of five Stage-0 conditions and failed the value-complementarity screen at `CR = 0.4847`. No
Stage-0 candidate advanced. T0 remains the one retained source. **None of that changes, and no threshold moves.**

## 2. The new hypothesis, which is a different question

Stage 0 taught us that a second useful source is unlikely to be another gain/load reweighting that must itself beat T0
as a standalone greedy controller. The successor lane therefore asks:

> Can a physically or behaviourally distinct specialist provide **incremental learner value when injected through the
> already-working D3 channel**, even if the specialist is *not* a better standalone EE controller than T0?

That is a different hypothesis from Stage 0's, and it is timestamped here before its counted runs.

## 3. Exactly two candidate families are authorised

1. **Phase A, primary and cheap: `T_H`.**
2. **Phase B, fallback and privileged: `T_DELTA`.**

**That is the cap.** No open-ended source search, no margin sweep, no `m` / `c` / coefficient search, no Catfish-3
search, no new observation design, no new learner architecture, no D3 hyperparameter tuning, no B2 reopening, no
exact-DR learner architecture, no α / LR / target-sync sweep. The purpose is fast convergence, not another research
tree.

## 4. Formal S1 is HELD

`S1-PREP` continues to completion — implementation, tests, mutants, manifest, DEV-only preflight — and the six-arm
harness may be implemented and reviewed. The `T0-XEP` reference stays sealed and is never regenerated. **Even if every
S1 preflight and review condition passes, nothing touches `9_111_000+i` / `9_112_000+i` until this successor lane is
adjudicated.** Q9b / curation cleanup may continue.

## 5. Isolation

`CATFISH2-SUCCESSOR` gets its own worktree, branch and server result root, and uses **DEV / DEVVAL only** — never
formal evaluation, calibration or CONFIRM. It must not work in `/home/u24/papers/mcrl-leo-handover-dev`, which
`S1-PREP` owns and which currently carries uncommitted S1 / T0-XEP changes.

**Base commit, verified rather than assumed:** `git diff --stat 05aadf1b 27f69edf` is
`scripts/dev_e0_aggregate.py | 149 ++++` — **one file, aggregation only, no scientific learner change**. The lane
therefore bases on `27f69edf` and inherits the collision-safe aggregation directly.

**Seeds:** DEV `k = 6, 7` for learner canaries. `k = 8, 9` stay reserved and may not be consumed without a further
controller authorisation.

## 6. Phase A — `T_H`

`T_H` is **exactly the existing `A m=12dB` policy, unchanged**. The hysteresis is not retuned; `m = 8, 10, 14 …` are
forbidden.

**Scientific role: continuity / stability / rate-tail specialist.** It uses the incumbent-memory axis differently from
T0, and Stage 0 already measured it as behaviourally very distinct — shared-state disagreement ≈ **0.529**,
substantially higher p10 than T0, lower standalone EE, `CR = 0.4847`.

**It must not be called a handover-energy specialist.** In v023 physics handover has no physical energy cost. Its role
is continuity, resistance to opportunistic reassociation, and rate-tail stability.

The claim under test is **not** "`T_H` is a better greedy controller than T0". It is "`T_H` supplies a distinct
inductive bias the learner can exploit selectively through D3".

### 6a. The Phase-A canary

The frozen learner is reused exactly: 113-dim observation, `equal_share` credit, `η₀` fixed, `λ = 0`, the same ratio
learner, the same network / Adam / replay / target sync, D3 with `m = 0.15` and `λ_E = 1.0`. **No hyperparameter
change.** Only the teacher identity `T_H` is added, whose action is exactly `A m=12dB`.

First run only, **DEV k = 6, 100 episodes**: `D0`, `D3-T_H`, matched `D3-null`. The matched null stays a seeded uniform
random **legal** action through the development null stream — no new null mechanism is invented.

### 6b. The Phase-A reading rule, fixed before launch

Using the existing Amendment 4 / E1 development conventions:

- EE direction **positive against both `D0` and the matched null**;
- paired DEVVAL direction positive;
- `served` degradation no worse than **−0.5 pp**;
- `p10 ≥ 0.5 × D0`;
- bits ratio `≥ 0.95 × D0`;
- the effect must **not** be counted if it sits inside the already-observed development seed noise.

**`D3-T_H` is not required to beat `D3-T0`.** That is not the question.

If k = 6 carries no usable positive transfer, `T_H` closes immediately — **no hysteresis sweep**. If it does,
replicate only `D0` / `D3-T_H` / `D3-null` at **k = 7, 100 episodes**, reusing an existing `D0` or null result only if
every frozen identity truly matches.

## 7. Phase B0 — `T_DELTA` discovery, no training, concurrent with Phase A

It does **not** wait for `T_H`.

`T_DELTA` is the **counterfactual externality specialist** built on the already validated difference-reward /
system-contrast machinery. The B1-CREDIT evidence is **motivation only, not the new result**, and it used its own
declared background, so it may not be assumed to transfer to T0 states: `B^D − η E^D` moved the argmax in 43.3 % of
decisions versus B-only; it agreed with the unilateral system best response in 1982/2000 = 99.1 %; within-decision
score / system-contrast correlation was 1.0; the old reference policy's action was not the unilateral best response in
most decisions.

### 7a. Definition, declared prospectively

For a current state: (1) construct T0's joint legal action `R`; (2) for focal user `u`, hold all other users at
`R_{−u}`; (3) score every legal action `a` for `u` by the exact counterfactual system externality already defined by
the B1 difference semantics,

    D_u(a) = B_u^D(a | R_{−u}) − η₀ · E_u^D(a | R_{−u})

including the already validated outage charge; (4) `T_DELTA` selects the legal masked argmax, first index on ties.

`T_DELTA` is a **training-only privileged specialist around T0's joint reference**, not a deployable runtime
coordinator. Its extra information is precisely what T0 does not observe directly: bandwidth-share externality,
co-channel interference externality, per-beam maximum-power externality, and beam / satellite activation externality.
**Deployment must never need this evaluator.**

### 7b. The cheap exact path is verified before anything is counted

The ≈ 6.2 h / 1000-episode full-evaluator path is avoided if possible. B1-CREDIT contains `without_user_rates`, which
reportedly reproduces full-evaluator without-`u` rates to ~1e-9 relative, making the bits externality `O(U²)`
arithmetic while the energy externality is analytic. **Before any counted `T_DELTA` diagnostic**: independently verify
the cheap path against the full evaluator on a small DEV sample, and require action identity plus score agreement
tight enough that it cannot change an argmax. **If it fails, stop and report — do not approximate.**

### 7c. What is measured, on a fixed DEV / DEVVAL state collection, `T_DELTA` vs T0

Action disagreement; candidate-better fraction; value-weighted Δ under the exact system contrast;
`CR` / Σ positive / Σ negative; QoS-invalid fraction; and a standalone joint rollout **only** as a diagnostic where it
is well defined — a simultaneous joint rollout failure must **not** be confused with absence of useful per-user
specialist information.

### 7d. Representability pre-screen — do not repeat T_SEQ's mistake

Run the representability / transferability pre-screen appropriate to a privileged teacher. If a 113-dim clone cannot
reach the existing `R_repr ≥ 0.5` admission convention, **close `T_DELTA` before any learner training.**

## 8. The minimum real multi-Catfish mechanism, if `T_H` survives two seeds

**Two D3 teacher losses may not be summed with an arbitrary 50/50 coefficient.** Use a **set-valued D3 large-margin
loss**. With `A_CF(s) = unique({a_T0, a_TH})`,

    L_multi = max_{a legal} [ S(s,a) + m · I(a ∉ A_CF) ] − max_{a ∈ A_CF} S(s,a)

at the same frozen `m = 0.15`. Either specialist may nominate an acceptable high-value action; the learner's own TD
score decides which it prefers in that state.

**Required identities and tests before training:** with one teacher `L_multi` is **bit-identical** to the current
single-teacher D3; teacher order is permutation-invariant; duplicate teacher actions collapse to one action; only
currently legal teacher actions enter the set; illegal actions can never become targets; zero teacher weight or a
disabled multi path reproduces the appropriate frozen control; the config hash covers teacher identities, the multi
mechanism identity and the null identity; resume / stop determinism is intact.

**The multi matched null** for a two-teacher FULL arm is a **two-proposal random-legal set** under its own declared
DEV-NULL stream and the same set-valued margin loss: when at least two legal actions exist, draw two distinct legal
actions without replacement; when only one exists, the set has cardinality one. **Comparing a two-teacher set-valued
loss only against the old one-action `D3-null` is not a matched comparison.**

## 9. The minimal two-Catfish factorial

After `T_H` independently survives k = 6 and k = 7, run only the minimum causal matrix at **100 episodes on those same
two seeds**: `D0`; `T0-only` (= current `D3-T0`); `TH-only` (= `D3-T_H`); `FULL{T0,TH}` (set-valued D3); `2-null` (the
matched two-random-legal set). An already completed arm is reused **only** when code, config, seed, depth and result
identity match exactly.

**Before these counted FULL runs, declare the experiment's practical resolution from the existing E0 / E1 development
variation. It may not be chosen from the FULL outcome.**

**The second Catfish is earned only if** `FULL − T0-only` is positive on **both** k = 6 and k = 7 in the same
direction and **beyond the pre-declared resolution**; the QoS floors hold; `FULL` beats the matched `2-null`; and the
effect is not an artefact of a single DEVVAL episode. `FULL − TH-only` is also reported, because T0 must still have
its own marginal role.

**If `FULL − T0-only` does not survive, `T_H` is not Catfish #2** — even if its own D3 arm is useful. No semantic
relabelling substitutes for the drop-one result.

## 10. If `T_H` fails, or its FULL drop-one fails

`T_DELTA` becomes the one fallback candidate; its no-training and representability screens should already be complete
because Phase B0 ran in parallel. If it passes distinctness, positive system value and `R_repr`, run `D0` /
`D3-T_DELTA` / matched one-action `D3-null` at DEV k = 6, 100 episodes; replicate k = 7 if it transfers positively with
QoS intact; then integrate `{T0, T_DELTA}` with the **same set-valued D3 machinery** and the **same five-arm drop-one
structure**. **No other integration mechanism may be invented after seeing `T_DELTA`'s result.** If it fails
representability, transfer or the drop-one marginal, it closes.

## 11. Formal S1 disposition after this lane

- **If a genuine two-Catfish FULL freezes**: the current single-source S1 manifest becomes a **prepared fallback, not
  the final algorithm**, and the successor S1 manifest — including FULL and the necessary drop-one controls — is
  declared prospectively before the still-untouched formal set is used.
- **If both bounded attempts fail**: the single-source formal S1 is **not** silently launched under a "Multi-Catfish"
  framing. Return to the owner with the evidence that only one source survived, so the owner chooses between
  (1) proceeding with a single-Catfish / teacher-injected algorithm and changing the paper framing, or
  (2) explicitly authorising a new research direction.

**The final Catfish count is still earned by drop-one marginal value, and by nothing else.**
