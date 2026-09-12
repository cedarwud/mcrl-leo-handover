# MC2 — Catfish identity + intervention contract (r2, controller, 2026-09-12)

> **r2 (readings + disclosure; no formula, rule, seed or cell changed):** folds in lane B's co-sign of r1
> (`.scratch/mc2/B/CONTRACT-COSIGN.md`: R1-1…R1-4, F-1…F-3, N-items) and the fresh-context cross-model review
> (`.scratch/mc2/agy/AGY-CONTRACT-REVIEW-r1.md`), **before any ep-100 file is read**. One reading changes a decision:
> **R1-1 — each version must also beat `D3-T0`**, so a two-Catfish "success" can never score below the existing single
> Catfish.
> **r1 (scheduling + selection):** after the owner's second message of 2026-09-12 (fast iteration, freeze the algorithm
> early, "multi-catfish" narrative, maximise parallel sub-agents), `MC2-ARB-v2` runs concurrently with v1 at ep 100.

Owner ruling of 2026-09-12: a genuine two-source Multi-Catfish round (competition / selective intervention).
This is a **new version** (`MC2`), worktree `/home/u24/papers/mcrl-leo-handover-mc2`, branch `mc2/judge-override-20260912`,
base `6136c514` (Lane M k8 code `f129e340` + results). It **does not reopen or re-read Amendment 15 / k = 8**: `T_NEXT`
failed the k = 8 set-valued drop-one (`6c5ef647`) and that stays a failure. What changes is the *integration* (how a
source enters training), which is a different research variable from the source itself. Development lane only.

## 0. What failed and what this design must not repeat

k = 8 `MULTI-D3-SETVALUED-v1`: `L = max_a[S+m·1(a∉A_CF)] − max_{a∈A_CF} S`. With `|A_CF| = 2` in 60.7 % of rows the
learner discharged the margin with whichever member its own `S` already preferred, which would make the T0 constraint
escapable wherever the two disagreed (FULL 107.85 < T_NEXT-only 109.09 < T0-only 112.49; −4.12 % vs T0-only, 0/24 paired,
**one training seed, 24 evaluation episodes**). The ordering is the *measurement*; "the stronger teacher stopped binding"
is the proposed mechanism and was **never causally isolated**.
Design rule taken from it: **every margin row has exactly one target, chosen by something other than the learner's own
score.** No union set, no summed conflicting margins, no per-specialist weights.

## 1. Roles (two scripted specialists; neither is an RL agent; "specialist" in prose, "teacher" only in code names)

| | Catfish-A — anchor specialist | Catfish-B — foresight challenger |
|---|---|---|
| source policy | `T0 = LP-prev(c=1, m=0)`: `a^A = argmax_{a legal} log2(1+max(γ_a,0)) − 1[N_a=0]`, first index on ties (`cf_teacher.t0_scores`, unchanged) | `T_NEXT` `assoc-persistence-lookahead-v1` (`cf_tnext.py`, sha256 `86f0d6ee…`, unchanged): lexicographic (same physical `(norad, cell)` visible at `t+1`, nominal `t+1` gain with no fading, current T0 score, −index); users held at `t`; ephemeris-only lookahead |
| specialty | current-step rate with a lit-beam preference (`T0-only` bits ×1.105 vs `D0`, k8, one seed, ep 100) | one-step geometric foresight (T0 disagreement 0.596 on P0; `T_NEXT-only` joules ×0.856 and 53.4 vs 62.6 beams against `D0` — read from `LANE-M-K8-RESULT.json`, not from the adjudication table, k8, one seed, ep 100) |
| challenge to the main learner | v1: unconditional large margin toward `a^A` on every replay row (the frozen `D3-T0` channel, E1: +9.42 % seed-mean over paired D0, 3/3 seeds, ep 300). v2: margin toward `a^A` only where it wins the §3 comparison | a proposal that replaces the incumbent target **only if** the judge (§2) ranks it strictly higher on the same state and the same other-user actions |
| quality feedback | v1: none gating A (its quality is the E1 evidence); the judge only *records* `κ(a^A)` vs `κ(x_u)`. v2: the judge comparison with `x_u` | the judge lead is the gate and is stored per row |
| intervention product | a single-target large-margin label on the learner's own replay row | the same label type, target swapped to `a^B` |
| accounting | per row: `a^A`, challenger, target, tag ∈ {A, B, R, none}, override flag, judge lead, judge evaluations | same |
| disable semantics (retrained, never an inference flag) | remove A → no anchor; B's incumbent becomes the learner's executed action `x_u`; rows B does not win carry **no margin** (vacated dose **not refilled**) | remove B → v1: target = `a^A` on every row = the frozen `D3-T0` arm; v2: the gated `{x_u, a^A}` cell `A-only-v2` |
| final decision step | as its rule says | **B abstains** (its frozen T0 fallback is counted, never injected by B) |

What the two roles do and do not bring (disclosures, N-a1…N-a4):
- **B as the learner sees it is "judge-filtered T_NEXT", not foresight as such.** κ scores step `t` only, so a T_NEXT
  benefit that pays only at `t+1` cannot pass the gate; what reaches the learner is the subset of T_NEXT proposals that
  are also one-step κ-better than the incumbent. No "learned foresight" claim is made. A failure of both versions would
  be ambiguous between "B carries no value" and "a one-step judge cannot see B's value".
- **T_NEXT is not free of T0**: T0's score is its third tie-break key (exact ties on `(persists, nominal gain)`, rare
  outside unusable slots). "No T0 content reaches B-only" holds except through that key; the final-step fallback is
  removed by B's abstention.
- **The drop-one of A is not symmetric with the drop-one of B.** Removing B gives a clean cell. Removing A also changes
  B's comparand from `a^A` to the ε-greedy `x_u` and lowers the dose, so FULL − B-only bundles A's margin, A's role as
  B's comparand, and the dose difference. There is no content-clean alternative (gating B against `a^A` without A's
  margin would leak A into B-only); the comparison is reported with this label.
- **The judge is a third, privileged information channel** (N-a2): it uses step `t`'s physics fading draw, the current
  interference from `x_{-u}` and exact system power, none of which the learner, T0 or T_NEXT observe. Override decisions
  are therefore partly a function of noise the learner cannot see (label noise, not dilution: the hinge resolves
  conflicting targets on one observation toward the per-observation majority). Consequences: a realised override rate
  overstates learnable B content; **FULL vs A-only measures T_NEXT and the judge's information together; only FULL vs
  B-null isolates T_NEXT's proposals.**

Shared: the 113-dim observation, the replay, the network. The judge is **not** a Catfish and is never deployed.

## 2. The training-only judge (fixed-η₀ surrogate — not pooled EE)

For user `u` at decision step `t`, with `x` the behaviour joint action about to be stepped, and a candidate action `a`:

```
ev(a)  = StepEnvironment.evaluate_actions((a, x_{-u}), deepcopy(env_rng))   # pre-step, nothing committed
κ_u(a) = ( n_served(ev(a)) ,  B(ev(a)) − η₀ · E(ev(a)) )                   # lexicographic, system totals of the step
```

`B`, `E` = `cf_credit.evaluation_bits_joules(ev, dt)` (system bits and joules of the step), `n_served` = served users of the
step, `η₀ = 110 507 234.834 444 57` bit/J (frozen E0 price). `≻` = strict lexicographic; ties go to the incumbent.
Service has no beam cap (served = not no-op and link-feasible), so `Δn_served ∈ {−1, 0, +1}` reflects `u`'s own service
and the served-first key closes the outage "free ride". `B − η₀E` is a **fixed-price surrogate** of the step's
contribution; it is **not** pooled EE and a judge win is **not** an EE improvement; every claim is read only on
DEVVAL / formal pooled EE and QoS. The judge is the project's existing counterfactual evaluator (the B1 / T_DELTA path:
deep-copied generator, common random numbers — the physics fading draw covers all candidate-window satellites and does
not depend on the action vector — `frozen_driver_positions`, the segment write snapshotted and restored, handovers
classified without commit); its base evaluation of `x` is asserted equal to the committed step on every step. It is
restricted to the ≤ 3 proposals `{x_u, a^A, a^B}` — no all-action or joint-action search.

## 3. Mechanisms

**`MC2-JGO-v1` (judge-gated override).**

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

**`MC2-ARB-v2` (competitive arbitration)** — a different reason: v1 keeps the anchor unconditional; v2 lets both
specialists compete with the learner on the same task. Winner by strict comparisons in the declared order:
`w = x_u; if κ(a^A) ≻ κ(w): w = a^A; if B present and κ(a^B) ≻ κ(w): w = a^B` (= max κ, ties `x_u` → A → B; B absent at
`t = T−1`); margin toward `w` only if `w ≠ x_u`, else no margin row. Same judge, margin, weights and normaliser.
Drop-ones: `A-only-v2` = `{x_u, a^A}` — a judge-gated T0 (a Q-filter on T0 with the simulator as critic) that drops the
T0 margin wherever the learner already plays `a^A`; it is **not** `D3-T0`. `B-only` = `{x_u, a^B}` = **exactly v1's
B-only** (without A both rules inject `a^B` only where κ(a^B) ≻ κ(x_u)); one shared cell with a rule-independent
identity serves both, proven by a parameter-sha256 equality test. `B-null-v2` = `{x_u, a^A, a^R}`.

Consequences, by construction: every margin row has one target; the learner's own score never chooses between the
specialists; with B disabled v1 is exactly `D3-T0`. **Cap disclosure**: the large-margin term is zero iff the target is
the argmax (any `m ≥ 0`), so it pulls the greedy policy toward the per-row target and never past it; anything beyond the
specialists can come only from TD. No other version, no sweep of `m`, `λ_E`, threshold or tie order.

## 4. Relation to the original CDRL / RIS catfish method (claims must stay inside this table)

| CDRL element (thesis via `07-true-catfish-formulas.md`) | retained in MC2 | changed / absent in MC2 |
|---|---|---|
| external high-EE specialist (Phase-1 solver) + learning catfish agent | two external specialists outside the main learner | both are **scripted rules**; no solver search; no catfish learner |
| competition on the same task (ACRM, `r^S = r^CF − r^M`, a reward term for a learning catfish) | a same-state, same-background comparison decides whether a specialist's proposal is used | the lead is a **gate**, never a reward term; in v1 FULL the comparand is the **anchor A**, not the main learner (only B-only and v2 compare with the learner's executed ε-greedy action, which is not its greedy action) |
| high-value stimulus (M1, `EE ≥ EE_high` routes **experiences** into a catfish memory) | a value filter decides which specialist output enters training | what passes is a **label on the learner's own transition**; the specialist's action is never executed or stored; relative threshold (beat the incumbent), not an absolute EE level |
| intervention mode (M3, catfish-collected experiences mixed 70/30 into main batches at randomized periods; the catfish agent also trains) | the intervention acts on the main learner's update | no catfish-collected experiences, no 70/30 mix, no random period; a label on every sampled row (dose 1.0 in v1 FULL, < 1 in B-only and every v2 cell) |
| asymmetric discounts (M2) | — | absent (one learner, γ = 1, finite horizon) |
| Phase-1 solver-seeded catfish replay | — | absent |
| dual-agent rollout; two replay memories | — | absent (one learner, one replay) |
| deployment = the trained CDRL policy alone | deployment = the main learner's masked argmax only | — |

Borrowed, to be cited, not claimed as new (lane B, `.scratch/mc2/B/LITERATURE-DELTA.md`): the large-margin **loss form**
of DQfD (Hester et al., AAAI 2018, arXiv:1704.03732) — applied, as in `D3-T0`, to the learner's own replay rows rather
than to demonstration transitions only; on-learner-state expert querying from DAgger (Ross, Gordon & Bagnell, AISTATS
2011); the per-sample **gate** from the Q-filter (Nair et al., ICRA 2018, arXiv:1709.10089), with the learner's critic
replaced by the simulator's one-step counterfactual; and only the concept "per state, defer to the better of several
oracles" from MAMBA (Cheng, Kolobov & Agarwal, NeurIPS 2020, arXiv:2007.00795) and MAPS (Liu, Yoneda, Wang, Walter &
Chen, ICML 2023, arXiv:2306.10259) — neither selects a supervised target by comparing oracle actions; both learn oracle
values from roll-outs. The narrow MC2-specific element: among these papers, none compares **two specialists'** actions
under an evaluator to pick one supervised target. No theoretical guarantee is claimed and none transfers; keeping the T0
margin does **not** guarantee EE cannot fall.

## 5. Invariants and minimum new tests

Unchanged: ratio learner, 113-dim observation, 28 actions, 100-50-50 tanh, B1 execution contract, physics, pinned TLE
`427e6a91…`, pooled bits/joules evaluation, `T_NEXT` source and seam (`cf_tnext.py` sha `86f0d6ee…`, trace digest
`0568b222…9bee` reproduced by code identity, no re-run), `--episodes 300 --stop-after 100`, ε 1.0→0.01 over 67 episodes.
New tests only for the new seam: (1) arms 1–9 config hashes identical to base; (2) FULL with the gate forced shut —
running the judge and the T_NEXT context — ≡ `D3-T0` parameter sha256; (3) the judge's base evaluation of `x` equals the
committed step's bits, joules and served flags exactly; (4) gate semantics (strict lexicographic, ties → incumbent, B
abstains at `T−1`, no call when `c = inc`); (5) the null reads no T_NEXT, builds no context, and draws exactly one
uniform legal action per user with a legal action at `t < T−1`, from a fresh `(9_243_000, k)` generator saved and
restored on resume; (6) seed-namespace collision checks; (7) config hash carries mechanism id, source set, judge id +
η₀ + key order, null id + key; (8) a checkpoint runs with every source and the judge unregistered; (9) stop/resume
determinism for the new arm; (10) B-only zero-margin rows; (11) shared B-only: v1 and v2 paths give identical labels
and identical parameter sha256.

## 6. Cells, seeds and budget

Arms: `D0` (arm 1), `D3-T0` (arm 4, = v1 A-only and the strong single-Catfish baseline for both versions), and a new
parameterised arm over (rule, source set): v1 `FULL` (`{A,B}`), v1 `B-null` (`{A,R}`); v2 `A-only-v2` (`{A}`), v2 `FULL`
(`{A,B}`), v2 `B-null` (`{A,R}`); shared `B-only` (`{B}`). `A-null` is not run (A's content is not in question).

Seeds (DEV namespace; formal / calibration / CONFIRM / S1-TRAIN / S1-NULL untouched): selection **k = 10, 11** (ep 100);
confirmation of the primary **k = 12, 13, 14** (ep 300); **k = 15, 16, 17** = fixed-order fallback confirmation of the
non-primary (§7), used only when both versions qualified; **k = 9 stays unused** (Amendment-15 index). DEV-NULL base
`9_243_000`. `MAX_DEV_SEED_INDEX` 9 → 19. **Hygiene**: nobody — controller, lanes, tooling — reads a k = 15–17 file
before the primary's ep-300 verdict is written.

Budget: learner updates (1 per decision step), batch 128, replay 50 000, ε schedule and env interaction identical in
every arm. Margin dose = fraction of sampled rows with a target (1.0 in `D3-T0`, v1 FULL, v1 B-null; learner-dependent
and < 1 in B-only and every v2 cell; B-only's is front-loaded because at ε ≈ 1 its comparand is random). Judge
evaluations and wall are counted per episode and reported; they are privileged training compute (B-null calls the judge
on ≈ 27/28 of rows, FULL on ≈ 60 %); **no sample-efficiency claim is made**.

## 7. Readings (declared before any MC2 learner result exists)

**Quantities.** Estimand: seed-wise relative pooled EE `EE_X,k / EE_Y,k − 1` on the 24 DEVVAL episodes
(`9_211_000+i / 9_212_000+i`, i < 24), greedy, fresh env per episode. *Seed-mean* = arithmetic mean over k of the
per-seed ratios; *seed-mean of min(…)* = mean over k of the per-seed min (R1-2). *Positive* = strictly > 0. QoS floors
(F-3), each per seed, FULL vs same-seed `D0`: served drop `D0.served − FULL.served ≤ 0.005`;
`per_served_user_rate_p10_bps` (as stored, pooled over the 24 episodes) ≥ 0.5×; pooled `bits` ≥ 0.95×.
*B activity* (F-1, R1-3), per seed, pooled over training episodes 1…100, denominator = user-steps with at least one
legal action over all `t` (including `T−1`): v1 numerator = FULL user-steps tagged B; v2 numerator = FULL user-steps
whose winner is `a^B` with `a^B ≠ a^A`. Required ≥ 1 % on each seed.

**ep 100 selection (k = 10, 11; v1 and v2 concurrently; 8 cells × 2 seeds = 16 runs).** A version *qualifies* iff all:
(i) seed-mean FULL vs its own A-only ≥ +0.5 %; (ii) seed-mean FULL vs `D3-T0` ≥ +0.5 % (R1-1; identical to (i) for v1);
(iii) seed-mean FULL vs B-only > 0; (iv) seed-mean FULL vs its own B-null > 0; (v) the QoS floors on each seed;
(vi) B activity ≥ 1 % on each seed. *Primary*: if both qualify, the larger seed-mean of
`min(FULL/own-A-only − 1, FULL/D3-T0 − 1, FULL/B-only − 1)`; within 0.10 pp → v1. If one qualifies it is the primary.
If neither qualifies, the data go to the owner (both declared versions failed at selection; no third version, no
relaxation). If the P0 pre-training diagnostic showed a near-zero override rate, a failed (vi) is reported as structural,
not as "B has no content".

**DEV survival at ep 300 (primary on k = 12, 13, 14, fresh)** — the owner's gate, unrelaxed, plus R1-1: FULL vs own
A-only, FULL vs B-only and FULL vs `D3-T0` each seed-mean ≥ +1.0 % with ≥ 2/3 seeds positive; FULL vs own B-null
seed-mean > 0 with ≥ 2/3 seeds positive; the QoS floors on each seed. **If the primary fails** (F-2): when the other
version also qualified, its concurrent fallback confirmation on k = 15, 16, 17 is read under the identical gate; when it
did not, the data go to the owner. **Multiplicity disclosure**: at most two confirmation attempts on disjoint fresh
seeds — the owner's "at most two versions" — and any survival report states which attempt passed. This is a
prospective DEV screen, not a formal significance claim. If both versions fail: no relaxation, no single-Catfish
downgrade — the data, the smallest blocking reason and the specific hypothesis that would have to change go to the owner.

**Reported beside every reading, never hidden**: FULL vs `D3-T0` bits, joules, served, p10; override / win rates for
FULL and for B-null (measured on the P0 probe at T0's background: `a^B` is approved on 28.6 % of decision rows, a
uniform `a^R` on 14.1 %, so FULL vs B-null is **not dose-matched**: it
identifies whether T_NEXT's specific proposals, filtered by this judge on top of the same anchor, beat content-free
proposals filtered the same way; it does not identify that foresight is the active ingredient, the value of the judge
itself, a dose-matched effect, or whether the judge's privileged information is necessary); per-episode doses for B-only
and every v2 cell; per-source margin-loss share and sampled rows per tag; judge evaluations; DEVVAL greedy agreement with
`a^A` and with `a^B` where they differ (`B/b_output_change.py`). Readings are computed independently by lane B
(`B/b_readout.py`) from the raw DEVVAL files.

**Pre-training diagnostic (not a gate; controller probe, run before any ep-100 file existed)**: on the P0 collection
(env `9_202_500+i` / mobility `9_203_500+i`, 24 episodes) — A/B disagreement, judge override rates of `a^B` and of a
uniform `a^R` over `a^A` at four backgrounds (T0, composite, D3-T0 learner, random), and the pooled EE of the T0, T_NEXT,
composite and composite-R rule rollouts. Result, recorded in
`.scratch/mc2/CONTROLLER-PROBE-READOUT-2026-09-12.md` (`/home/sat/mcrl-v025-mc2-ws/controller-probe/probe-*.json`):
T0 116.963 M bit/J, T_NEXT 103.111 (−11.84 %), composite **124.130 (+6.13 %, 24/24 paired)**, composite-R 119.691
(+2.33 %, 24/24), composite over composite-R +3.71 % (23/24); override rates 0.286 (`a^B`) and 0.141 (`a^R`) at T0's
background, 0.308 and 0.155 at the frozen learner's; judge–step parity exact and zero RNG contamination. B is therefore
not structurally inert, and the judge alone does not account for the rule-level effect.
