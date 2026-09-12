# Amendment 15 to Ruling 2 — the sealed parallel Catfish-source portfolio

Date: 2026-09-12. **Owner decision.** Written and committed **before any outcome from `T_NEXT` or `T_TAIL` exists**,
and before the `T_DELTA` J denominators are frozen.

## 0. Scope — what this supersedes and what it does not

It supersedes **only** the Amendment 14 provisions that (a) permit exactly two candidate families, (b) prohibit a
third source family, and (c) make `T_DELTA` a sequential fallback after `T_H`. Everything else in Amendments 4, 5, 8,
10, 12, 13 and 14 that protects evidence integrity remains in force.

**Explicitly preserved:**

- **Formal S1 stays PARKED and untouched.** Verified at the time of writing: no S1 result root exists on `sat`, and no
  result file created since 2026-09-11 in the dev, `cf2s` or `cf2s-b0` workspaces contains `9111000` or `9112000`.
- The original Catfish-2 **Stage 0 result remains zero survivors**. No Stage-0 result may be retroactively relabelled
  a survivor.
- **`T_H` is CLOSED** — not reopened, not tuned, not run at k = 7 or anywhere else.
- The existing `T_DELTA` evidence and its **corrected** representability contract stand:
  `den_h = EE(J_h) − EE(rule_h)`, `R_repr_h = [EE(clone_h) − EE(rule_h)] / [EE(J_h) − EE(rule_h)]`, with
  `rule = A m=2dB` and `teacher = the T_DELTA joint rollout J`. **T0-rule headroom is context only, never the
  denominator.** The pre-registered non-identifiable outcome for `EE(J_h) ≤ EE(rule_h)` stands, and the instrument is
  not repaired after seeing J.
- The `T_DELTA` **arithmetic-identity finding stands**: because `T_DELTA ≡ argmax_a Δ(a)` and T0's action is in the
  candidate set, its candidate-better fraction (0.99958) and `CR` (6717) are near-arithmetic identities of the
  construction and are **never** independent evidence.
- The frozen ratio learner, frozen T0, frozen D3 (`m = 0.15`, `λ_E = 1.0`), the 113-dim observation, `equal_share`
  credit and `η₀` are unchanged. **"Parallel heads" means parallel source-development lanes, not neural heads and not
  any change to the frozen `Q_B / Q_E / Q_H` architecture.**
- No learner-architecture sweep, D3-margin sweep, coefficient sweep, or B2 reopening.
- The whole portfolio is **DEV-only**.

## 1. The portfolio is sealed to exactly three source families

1. **`T_DELTA`** — counterfactual system-externality specialist. Already in progress.
2. **`T_NEXT`** — one-step temporal-foresight / association-persistence specialist.
3. **`T_TAIL`** — current-state system service-tail / robustness specialist.

**No fourth source may be added after any `T_NEXT` or `T_TAIL` outcome is visible, without a new owner decision.**

The objective is to select **Catfish #2**. Multiple candidates may survive development; survival does **not** mean the
final method must contain three or four sources.

## 2A. `T_NEXT`, frozen prospectively

**Information axis:** near-future geometry / continued physical service opportunity that T0 does not receive as a
teacher signal. **It is not a handover-energy source** — v023 has no physical handover-energy or interruption
mechanism that would justify that story.

For focal user `u` and each **currently legal** action `a` at step `t`:

1. Resolve `a` to the underlying **stable physical satellite/beam association**. The current user-relative action-slot
   number is **not** a permanent physical identity and may not be used as one.
2. Inspect the **deterministic** geometry at `t+1` for the same user and the same physical association.
3. The lookahead is **side-effect-free**: do not advance the live environment; do not consume or change fading RNG; do
   not consume or change mobility RNG; do not use future stochastic fading; do not use a future learner action or any
   future policy rollout.
4. Rank legal current actions **lexicographically** by

       ( same_physical_association_is_legal_or_visible_at_t_plus_1,
         nominal_next_step_link_gain_for_that_same_association,
         current_T0_score,
         -current_action_index )

Use the existing frozen geometry and gain definitions. **No target SINR, no ACM threshold, no `R_min`, no new power
controller.** At the final decision step, where no valid `t+1` exists within the episode, fall back deterministically
to T0 and **record the fallback frequency**.

**If the code cannot map an action to a stable physical association unambiguously, STOP `T_NEXT` and report the
structural blocker. Do not approximate with raw slot persistence.**

Narrative if it survives: **temporal foresight / service-persistence Catfish** — not handover energy.

## 2B. `T_TAIL`, frozen prospectively

**Information axis:** current cross-user service-tail information that T0's local gain and previous-beam structure do
not contain.

At a current state: (1) construct T0's joint legal reference assignment `R`; (2) hold `R_{−u}` fixed for focal user
`u`; (3) for every legal alternative `a`, evaluate the resulting **current** joint allocation with the exact existing
evaluator, **without mutating the live trajectory**; (4) rank alternatives **lexicographically** by

    ( total_served_user_count,
      existing_project_p10_user_rate,
      current_T0_score,
      -current_action_index )

Use the project's **existing** served definition and **exactly** the project's existing p10 rate convention. **No
invented `R_min`, no demand cap, no new weighted scalarisation, no arbitrary QoS/EE coefficient, and `B − ηE` must
not be placed ahead of the tail criteria.** The T0 score is only the deterministic tie-break after the tail criteria,
so if the tail criteria carry no information this source **collapses toward T0** rather than silently becoming
another `T_DELTA`.

Narrative if it survives: **system service-tail / robustness Catfish**. It is **not** required to be a superior
standalone EE controller.

## 3. Seed namespaces, audited before any counted output

**P0 state collection (both new candidates, shared where technically valid):** env **`9_202_500 + i`**, mobility
**`9_203_500 + i`**. States must be **history-carrying**, preferring `t = 1…9`, not only reset `t = 0` states. For
`T_NEXT`, only steps with a valid next step contribute the lookahead diagnostic, and the final-step T0 fallback is
reported separately.

**Portfolio learner seeds:** **k = 8** (first parallel learner screen) and **k = 9** (replication of survivors) —
DEV train `9_201_00k`, env `9_202_00k`, mobility `9_203_00k`; DEV-NULL `(9_231_000, k)` and `(9_241_000, k)`.

**k = 6 and k = 7 are retired for this portfolio.** k = 6 was observed through the closed `T_H` experiment and cannot
be called fresh for sources designed afterwards; k = 7 belongs to the old Amendment 14 `T_H` replication contract.

**Audit receipt (controller, before launch).** `9202500`, `9203500`, `9201008/9202008/9203008`,
`9201009/9202009/9203009`, `9231008/9231009`, `9241008/9241009` were grepped across the repository and every `sat`
workspace. **Zero code or documentation hits anywhere.** Local hits are coincidental digit substrings inside float
arrays in closed artefacts (`b2-representability` clone losses, `catfish-oracle-gate` candidate arrays,
`ee-ceiling` p10 values, `b1-credit` rate arrays) — none is a seed declaration. Separately,
`grep -rl '"seed_index": [89]'` across the dev, `cf2s` and `cf2s-b0` workspaces returns **nothing**: no result
anywhere carries seed index 8 or 9.

## 4. `delta_DEV`, derived and frozen before any k = 8 result

**`delta_DEV = +1.0 % relative pooled EE.`**

**Derivation.** Amendment 14 required this to come from existing E0/E1 variation rather than from the FULL outcome. On
inspection the frozen records **do not support a defensible within-seed repeatability calculation**: no arm was ever
run twice at the same seed with the same configuration, so no true replicate exists and no empirical run-to-run
variance can be estimated. Per the owner's instruction, the **fixed conservative fallback applies**.

Recorded as *context only*, not as the derivation:
- The closest thing to a same-seed replicate — `D2-T0` at DEV k = 0 with τ = 1 (112,317,765) versus τ = 0.3
  (112,325,427) — differs by **0.007 %**, two orders of magnitude below the floor.
- The known-real `D3-T0` effect at E1 ep 300 is **+7.88 / +10.46 / +9.91 %**, roughly 8–10 × the floor.
- Phase A's `T_H` at k = 7 (**+0.591 %**) would fail this floor, which is the correct outcome given its 14/24 pairing.
- Between-seed spread of the same contrast across six development seeds is s.d. ≈ 2.3 pp; that is effect
  heterogeneity, and the **two-seed replication requirement**, not the floor, is what protects against it.

**The floor may not be lowered after seeing candidate results.**

## 5. Pre-training gates

**Distinctness (both new candidates), on the frozen P0 collection:** `disagreement(T_i, T0) ≥ 0.25`. A distinctness
gate only, never a value claim. **If it fails, the candidate closes. There are no authorised constants to tune.**

**113-dim action representability probe, `A_repr` — for `T_NEXT` and `T_TAIL` only.** `T_DELTA`'s J-based closed-loop
ratio may **not** be copied and given the same semantics for these teachers. Use the frozen family already used for
the `T_DELTA` clone — `113 → 100 → 50 → 50 → 28`, tanh, Adam 1e-3, batch 256, ≤ 400 epochs — on the deployed 113-dim
observation only, with episode-disjoint TRAIN / VAL / TEST partitions fixed before fitting, and **BC / top-1
imitation only** (no candidate-specific temperature or architecture search).

    A_repr = held-out top-1 agreement with the source
    admission: A_repr >= 0.50, and the 0.25 distinctness gate already passed

Record held-out legal top-1 agreement, cross-entropy, teacher-score regret where the source score admits one,
legal-mask correctness, a per-step breakdown, and candidate disagreement conditional on clone correctness. **Call it
`A_repr`, never `R_repr`** — it must not be blurred with the inherited closed-loop ratio. A failure closes the source
before learner training.

`T_DELTA` joins the k = 8 / k = 9 portfolio **if and only if** its already-frozen B0 closed-loop contract passes.

## 6. Generic MULTI-D3, implemented before knowing which teacher survives

With `A_CF(s) = unique({a_T0, a_Ti, …})`, the frozen margin `m = 0.15` and the learner's existing score `S`:

    L_multi = max_{a legal} [ S(s,a) + m · I(a ∉ A_CF) ] − max_{a ∈ A_CF} S(s,a)

`λ_E = 1` and the existing D3 coefficient are unchanged. **No teacher weights — no 0.5/0.5, none at all.**

Required before any learner run: singleton `{T0}` bit-identical to the current `D3-T0`; the singleton generic path
bit-identical to the existing single-teacher D3 implementation; teacher-order permutation invariance; duplicate
teacher actions collapse; only currently legal teacher actions enter `A_CF`; an illegal action can never become a
target; deterministic first-index tie behaviour; a disabled multi path reproduces the frozen control; the config hash
contains canonical teacher identities, mechanism identity and null identity; resume/stop determinism; the multi code
changes **no** inference or deployment path; and **no teacher is required at deployment**.

The **matched set-valued random-legal null** is implemented before any learner outcome exists. For a two-teacher FULL
arm it uses the Amendment 14 two-proposal legal-set semantics — draw two distinct legal actions without replacement
when at least two exist, cardinality one otherwise — unless a test demonstrates an actual matching defect. **A null is
never chosen after seeing learner results.**

## 7. The k = 8 pairwise causal matrix — a specialist need not beat T0 alone

The decisive question is **not** whether a specialist is a better greedy controller than T0. It is whether **adding
this distinct training-time source to T0 produces incremental learner value.**

For every candidate `T_i` clearing its applicable pre-training gate, run the five-arm matrix directly at **k = 8, 100
episodes**: `D0`; `T0-only` (= current `D3-T0`); `Ti-only` (= `D3-Ti`); `FULL{T0,Ti}` (set-valued MULTI-D3);
`2-null` (matched two-proposal random-legal set-valued D3). Shared arms are physically run **once** at the same exact
identity and reused across candidates. All matrices use the same k = 8 learner / environment / mobility identities and
the frozen learner and hyperparameters. Candidates may run concurrently under the shared `sat` cap.

Report per matrix: pooled bits, pooled joules, pooled EE, served, p10, handover rate, the 24 paired DEVVAL episode
outcomes, teacher agreement rates, duplicate-teacher frequency, the FULL teacher-set cardinality distribution,
runtime, and all exact run and config hashes.

**QoS floors, unchanged:** served degradation ≥ −0.5 pp vs `D0`; `p10 ≥ 0.5 × D0`; bits ≥ `0.95 × D0`.

**A candidate survives k = 8 only if** `FULL{T0,Ti} − T0-only ≥ delta_DEV` in relative pooled EE, **and**
`FULL{T0,Ti} − Ti-only ≥ delta_DEV` so T0 retains its own positive marginal value, **and** `FULL{T0,Ti} > 2-null`,
**and** the QoS floors hold. **`Ti-only` is not required to beat `T0-only`** — deliberately, because a Catfish source
may be a useful specialist without being the best standalone controller.

**The drop-one criterion may not be replaced by source disagreement, clone accuracy, standalone EE, `CR`, or narrative
plausibility.**

## 8. k = 9 replication, and selection among survivors

Only k = 8 survivors replicate at fresh **k = 9, 100 episodes**, with identical frozen definitions and mechanisms and
**no tuning between k = 8 and k = 9**. A candidate earns **provisional DEV Catfish #2** only if all four criteria hold
at **both** seeds. **Failures are reported as failures; a failed seed is never averaged away.**

If several survive, rank by `min(relative FULL−T0 effect at k8, at k9)`. If one clearly exceeds the others beyond
`delta_DEV`, freeze it as the leading Catfish #2 and keep the others as development evidence and ablations. If two or
more survivors sit within `delta_DEV` of one another, **the DEV evidence does not rank them** and only then may a
bounded fresh **k = 10** multi-source drop-one experiment be declared prospectively. **No new source family may be
invented at k = 10.** The goal is **at least two genuine sources**, not maximising the count.

## 9. Failure rule

`T_DELTA` wins → `T0 + T_DELTA → set-valued D3 → frozen ratio-DQN`. `T_NEXT` wins → structural/consolidation prior +
temporal-foresight/persistence prior. `T_TAIL` wins → structural/consolidation prior + global service-tail robustness
prior. More than one survives → the bounded selection rule above; the final count does not automatically increase.

**All three fail → the Catfish-2 successor search stops.** No further source, no relaxed gate, no swept coefficient,
no reopening of `T_H`, and **no silent launch of the old single-source S1 under a "Multi-Catfish" claim.** The evidence
returns to the owner.

## 10. Formal S1

Nothing here opens it. While the portfolio runs: do not launch `run_s1`, do not create formal result roots, do not
consume formal seed namespaces, do not inspect any formal outcome, and do not reinterpret the existing single-source
S1 manifest as final. **If a two-Catfish method freezes in DEV, the formal manifest is rewritten prospectively around
that frozen method and independently reviewed before formal evaluation begins.**
