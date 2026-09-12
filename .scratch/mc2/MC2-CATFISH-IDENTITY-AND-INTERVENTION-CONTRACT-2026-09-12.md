# MC2 — Catfish identity + intervention contract (draft r1, controller, 2026-09-12)

> **r1 (scheduling + selection only; no formula changed):** after the owner's second message of 2026-09-12 (fast
> iteration, finalise the algorithm as early as possible, "multi-catfish" narrative, maximise parallel sub-agents),
> `MC2-ARB-v2` is no longer held back until v1 fails: **v1 and v2 run concurrently at ep 100** on the same selection
> seeds, and the version-selection rule in §7 is declared here, before any MC2 learner result exists. Still at most two
> versions, each with its own reason; no sweep.

Owner ruling of 2026-09-12: a genuine two-source Multi-Catfish round (competition / selective intervention).
This is a **new version** (`MC2`), new worktree `/home/u24/papers/mcrl-leo-handover-mc2`, branch
`mc2/judge-override-20260912`, base `6136c514` (Lane M k8 code `f129e340` + results). It **does not reopen or re-read
Amendment 15 / k = 8**: `T_NEXT` failed the k = 8 set-valued drop-one (`6c5ef647`) and that stays a failure. What changes
is the *integration* (how a source enters training), which is a different research variable from the source itself.
Status: draft r0, to be co-signed by the method owner (lane B) before the first counted run. Development lane only.

## 0. What failed and what this design must not repeat

k = 8 `MULTI-D3-SETVALUED-v1`: `L = max_a[S+m·1(a∉A_CF)] − max_{a∈A_CF} S`. With `|A_CF| = 2` in 60.7 % of rows the
learner discharged the margin with whichever member its own `S` already preferred, so the stronger teacher stopped
binding (FULL 107.85 < T_NEXT-only 109.09 < T0-only 112.49; −4.12 % vs T0-only, 0/24 paired, **one training seed, 24
evaluation episodes**). That dilution is a *measured* outcome and a *plausible, not causally isolated* explanation.
Design rule taken from it: **every margin row has exactly one target, chosen by something other than the learner's own
score.** No union set, no summed conflicting margins, no per-teacher weights.

## 1. Roles (two scripted specialists; neither is an RL agent)

| | Catfish-A — anchor specialist | Catfish-B — foresight challenger |
|---|---|---|
| source policy | `T0 = LP-prev(c=1, m=0)`: `a^A = argmax_{a legal} log2(1+max(γ_a,0)) − 1[N_a=0]`, first index on ties (`cf_teacher.t0_scores`, unchanged) | `T_NEXT` `assoc-persistence-lookahead-v1` (`cf_tnext.py`, sha256 `86f0d6ee…`, unchanged): lexicographic (same physical `(norad, cell)` visible at `t+1`, nominal `t+1` gain with no fading, current T0 score, −index); users held at `t`; ephemeris-only lookahead |
| specialty | current-step rate with a lit-beam preference (bits at unchanged energy: T0-only bits ×1.105 vs D0 at k8) | one-step geometric foresight (T0 disagreement 0.596 on P0; T_NEXT-only joules ×0.856, beams 53 vs 63 at k8) |
| challenge to the main learner | unconditional large margin toward `a^A` on every replay row (the frozen D3-T0 channel, E1: +9.42 % over paired D0, 3/3 seeds, at ep 300) | **selective override**: on a row where `a^B ≠ a^A`, the target becomes `a^B` **only if** `a^B` beats the incumbent target on the same state and the same other-user actions, as scored by the judge (§2) |
| quality feedback | none gating A (its quality is the E1 evidence); the judge *records* `κ(a^A)` vs `κ(x_u)` as a diagnostic only | the judge lead `κ(a^B) ≻ κ(incumbent)` is the gate; the lead is stored per row |
| intervention product | a single-target D3 margin label on the learner's own replay row | the same label type, target swapped to `a^B` on override rows |
| accounting | per row: `a^A`, `a^B`, target, source tag ∈ {A, B, R, none}, override flag, judge lead, judge evaluations | same |
| disable semantics (retrained, never an inference flag) | remove A → no anchor; B's incumbent becomes the learner's executed action `x_u`; rows B does not win carry **no margin** (vacated dose is **not refilled**) | remove B → target = `a^A` on every row = the frozen `D3-T0` arm, bit-identical (§5) |
| final decision step | anchor as usual | **B abstains** (its frozen T0 fallback is counted, never injected by B), so no T0 content reaches a B-only arm through the fallback |

Shared: the 113-dim observation, the replay, the network; each specialist reads the RAW state (A) or the RAW state plus
the training-only `TeacherContext` seam (B). The judge is **not** a Catfish and is never deployed.

## 2. The training-only judge (fixed-η₀ surrogate — not pooled EE)

For user `u` at decision step `t`, with `x` the behaviour joint action about to be stepped, and a candidate action `a`:

```
ev(a)  = StepEnvironment.evaluate_actions((a, x_{-u}), deepcopy(env_rng))   # pre-step, nothing committed
κ_u(a) = ( n_served(ev(a)) ,  B(ev(a)) − η₀ · E(ev(a)) )                   # lexicographic, system totals of the step
```

`B`, `E` = `cf_credit.evaluation_bits_joules(ev, dt)` (system bits and joules of the step), `n_served` = served users of the
step, `η₀ = 110 507 234.834 444 57` bit/J (frozen E0 price). `≻` = strict lexicographic; ties go to the incumbent.
The served count comes first so that no candidate can win by shedding a user. `B − η₀E` is a **fixed-price surrogate**
of the step's contribution; it is **not** pooled EE and a judge win is **not** an EE improvement; every claim is read
only on DEVVAL/formal pooled EE and QoS. The judge is the project's existing counterfactual evaluator (the B1 / T_DELTA
path: `evaluate_actions` deep-copies the generator, common random numbers, `frozen_driver_positions`); it is restricted to
the ≤ 3 proposals `{x_u, a^A, a^B}` — no all-action or joint-action search.

## 3. Mechanism `MC2-JGO-v1` (judge-gated override) — the first version

```
for each decision step t, after x = ε-greedy(S) and before env.step(x):
    a^A = T0(s_u)                                      for all u
    a^B = T_NEXT(s_u, ctx)  if t < T−1  else ABSTAIN   (B source enabled)
    a^R = Uniform(legal_u) from DEV-NULL (9_243_000,k)  if t < T−1  else ABSTAIN   (null arm only, replaces a^B)
    for each user u with a legal action:
        if A enabled:  inc = a^A ;  target = a^A ; tag = A
        else:          inc = x_u ;  target = NONE ; tag = none
        c = the challenger (a^B, or a^R in the null arm), if not ABSTAIN and c ≠ inc:
            if κ_u(c) ≻ κ_u(inc):  target = c ; tag = B (or R)
        push (s_u, x_u, r_u, s'_u, masks, done) + labels (a^A, c, target, tag, lead)
update: L = Σ_heads TD_k + λ_E · (1/|batch|) Σ_rows w_row · [ max_{a legal}(S(s,a) + m·1(a≠target)) − S(s,target) ]
        w_row = 1 if target ≠ NONE else 0;  m = 0.15, λ_E = 1.0, batch 128 (all frozen, unchanged)
```

Consequences, by construction: every margin row has one target; the learner's own score never chooses between the
specialists; with B disabled the loop is exactly `D3-T0`; B can only *move* the anchor's target to an action the judge
ranks strictly higher on the same state and background.

**Declared second version `MC2-ARB-v2` (run concurrently with v1 from r1; selection in §7)** — a different reason: v1
keeps the anchor unconditional; v2 releases it and lets both specialists compete with the learner on the same task.
Candidates `{x_u, a^A, a^B}` (B absent at `t = T−1`), winner by `κ` with ties to `x_u`, then A, then B; margin toward
the winner only if the winner ≠ `x_u`, else no margin row. Same judge, same margin, same weights. Its drop-ones:
`A-only-v2` = candidates `{x_u, a^A}` (T0 margin only where T0 beats the learner's executed action — a new cell, NOT
`D3-T0`); `B-only` = candidates `{x_u, a^B}`, which is **the same rule as v1's B-only** (without A both versions reduce
to "inject `a^B` only where it beats `x_u`"), so one shared B-only cell serves both versions, with a test proving the
two code paths coincide; `B-null-v2` = `{x_u, a^A, a^R}`. `D3-T0` stays the strong-T0 baseline for v2 as well. No other
version, no sweep of `m`, `λ_E`, threshold or tie order.

## 4. Relation to the original CDRL / RIS catfish method (claims must stay inside this table)

| CDRL element (thesis via `07-true-catfish-formulas.md`) | kept in MC2 | changed in MC2 |
|---|---|---|
| external high-EE specialist (Phase-1 solver) + catfish agent | two external specialists outside the main learner | both are **scripted rules**, not an RL agent, not a solver search; no second learner |
| competition on the same task (ACRM, `r^S = r^CF − r^M`) | B intervenes only by beating the incumbent on the **same state and same other-user actions** | the lead is a judge comparison used as a **gate**; nothing is added to any reward |
| high-value stimulus (M1, `EE ≥ EE_high` → catfish memory) | only judge-approved B proposals become intervention samples | relative threshold (beat the incumbent), not an absolute EE level; no second memory |
| intervention mode (M3, 70 % main / 30 % catfish batches) | the main learner is the only thing updated; intervention enters its training | a DQfD large-margin **label** on the learner's own replay rows (Hester et al.), per-state selective, not a randomized periodic batch mix |
| asymmetric discounts (M2) | — | absent (one learner, γ = 1, finite horizon) |
| deployment = the trained CDRL policy alone | deployment = the main learner's masked argmax only | — |

Borrowed, to be cited, not claimed as new: DQfD large margin (Hester et al., arXiv:1704.03732); per-state selection among
several oracles by comparing their value / advantage (Cheng et al., arXiv:2007.00795; Liu et al., arXiv:2306.10259). What
MC2 adds is narrow: the oracle comparison is done by a training-only counterfactual judge rather than by learned oracle
value functions or the learner's own critic, and the second source can only override, never dilute, the anchor's
target. No theoretical guarantee is claimed; keeping the T0 margin does **not** guarantee EE cannot fall.

## 5. Invariants and minimum new tests

Unchanged: ratio learner, 113-dim observation, 28 actions, 100-50-50 tanh, B1 execution contract, physics, pinned TLE
`427e6a91…`, pooled bits/joules evaluation, `T_NEXT` source and seam (`cf_tnext.py` sha `86f0d6ee…`, trace digest
`0568b222…9bee` reproduced by code identity, no re-run), `--episodes 300 --stop-after 100`, ε 1.0→0.01 over 67 episodes.
New tests only for the new seam: (1) arms 1–9 config hashes identical to base; (2) FULL with the gate forced shut ≡
`D3-T0` parameter sha256 (judge is side-effect-free on env, env RNG, driver); (3) the judge's base evaluation of `x`
equals the committed step's bits, joules and served flags exactly; (4) gate semantics (strict lexicographic, ties →
incumbent, B abstains at `T−1`, no call when `c = inc`); (5) the null reads no T_NEXT and draws exactly one uniform legal
action per user with a legal action at `t < T−1`, from `(9_243_000, k)` only; (6) seed-namespace collision checks;
(7) config hash carries mechanism id, source set, judge id + η₀, null id + key; (8) a checkpoint runs with every source
and the judge unregistered; (9) stop/resume determinism for the new arms; (10) B-only rows without an override carry
zero margin.

## 6. Cells, seeds and budget

Arms: `D0` (arm 1), `A-only` = `D3-T0` (arm 4, same identity), and a new parameterised arm over (rule, source set):
v1 `FULL` (`{A,B}`), v1 `B-null` (`{A,R}`); v2 `A-only-v2` (`{A}`), v2 `FULL` (`{A,B}`), v2 `B-null` (`{A,R}`); and the
shared `B-only` (`{B}`, rule-independent identity). `A-null` is not run (A's content is not in question: E0/E1 D3-null
evidence).

Seeds (DEV namespace, formal / calibration / CONFIRM / S1-TRAIN / S1-NULL untouched):
selection **k = 10, 11** (ep 100); confirmation **k = 12, 13, 14** (ep 300, never used for selection);
reserve **k = 15, 16, 17** only if v1's confirmation seeds were consumed and v2 needs its own. **k = 9 stays unused**
(Amendment-15 index). New DEV-NULL base `9_243_000` for the proposal-replacement null. `MAX_DEV_SEED_INDEX` 9 → 19.

Budget: learner updates (1 per decision step), batch 128, replay 50 000, ε schedule and env interaction identical in
every arm. Margin dose = fraction of sampled rows with a target (1.0 in A-only / FULL / B-null; < 1 in B-only, not
refilled). Judge evaluations and wall are counted per episode and reported; they are privileged training compute,
matched in kind between FULL and B-null; **no sample-efficiency claim is made**.

## 7. Readings (declared before any MC2 learner result exists)

Estimand everywhere: seed-wise relative pooled EE `EE_X,k / EE_Y,k − 1` on the 24 DEVVAL episodes (`9_211_000+i /
9_212_000+i`), greedy, fresh env per episode.

**ep 100 selection (k = 10, 11; v1 and v2 concurrently).** Cells: `D0`, `D3-T0` (= v1 A-only), shared `B-only`,
`FULL-v1`, `B-null-v1`, `A-only-v2`, `FULL-v2`, `B-null-v2` — 8 cells × 2 seeds = 16 runs. A version *qualifies* iff,
with its own drop-ones (v1: A-only = `D3-T0`; v2: A-only = `A-only-v2`): seed-mean FULL vs A-only ≥ +0.5 %; seed-mean
FULL vs B-only > 0; seed-mean FULL vs its B-null > 0; per seed FULL vs D0 served drop ≤ 0.5 pp, p10 ≥ 0.5×,
bits ≥ 0.95×; B is not inert (v1: override rate ≥ 1 % of decision rows; v2: B wins ≥ 1 % of decision rows).
*Selection*: if both qualify, the **primary** is the one with the larger seed-mean of `min(FULL/A-only − 1,
FULL/B-only − 1)`; within 0.10 pp → v1 (fewer moving parts). If one qualifies it is the primary. If neither qualifies,
the data go to the owner (both declared versions failed at selection; no third version, no relaxation).
*Fixed-order fallback*: when both qualify, the non-primary may be confirmed **concurrently** on the reserve seeds
k = 15, 16, 17 under the same unrelaxed gate; it is read **only if the primary fails** its own confirmation, never
compared with it to pick a winner. The selection is on k = 10, 11 only; k = 12–17 never enter selection.

**DEV survival at ep 300 (k = 12, 13, 14, fresh)** — owner's gate, unrelaxed: FULL vs A-only and FULL vs B-only each
seed-mean ≥ +1.0 % with ≥ 2/3 seeds positive; FULL vs B-null seed-mean > 0 with ≥ 2/3 seeds positive; per seed FULL vs
same-seed D0 served drop ≤ 0.5 pp, p10 ≥ 0.5×, bits ≥ 0.95×. Reported beside it, never hidden: FULL vs A-only bits,
joules, served, p10; override rate, doses, per-source margin-loss share, sampled rows per tag, judge evaluations; DEVVAL
greedy agreement with `a^A` and with `a^B` where they differ. This is a prospective DEV screen, not a formal
significance claim. If both versions fail: no relaxation, no single-Catfish downgrade — the data, the smallest blocking
reason and the specific hypothesis that would have to change go back to the owner.

**Pre-training diagnostic (not a gate)**: on the P0 collection (T0-rolled, env `9_202_500+i` / mobility `9_203_500+i`,
24 episodes), the A/B disagreement rate, the judge override rate at T0's joint background, and the pooled EE of the
non-learned composite rule (per user `a^B` if it beats `a^A` under κ, else `a^A`) against T0 and T_NEXT rollouts.
