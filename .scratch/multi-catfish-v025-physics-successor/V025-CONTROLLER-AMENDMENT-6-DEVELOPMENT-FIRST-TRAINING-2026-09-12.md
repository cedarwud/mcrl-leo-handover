# Amendment 6 to Ruling 2 — development-first training, without changing any formal gate

Date: 2026-09-11 18:10 UTC (2026-09-12 02:10 Asia/Taipei). **Owner direction** (`gpt7.md`, pasted by the owner): switch to a
development-first algorithm workflow now, so that learner work is no longer serialised behind every oracle / credit /
representability decision. **This amendment does not relax, replace or reinterpret Amendment 4 or Amendment 5.** Development
runs are not formal screening runs and cannot satisfy any paper claim or formal gate. Written before any development run exists.

## 1. Development algorithm ≠ frozen formal algorithm — three levels

| level | what | may change after seeing results? | evidence status |
|---|---|---|---|
| **E0** — engineering / development runs | short learner runs; detect whether the learner, the credit and the teacher-injection code actually learn | yes, on **DEV / DEVVAL only** | no statistical claim; never Amendment 4 screening evidence |
| **E1** — development screen | longer than E0, several development seeds; chooses and fixes the kernel and its hyperparameters | yes, on DEV / DEVVAL only | still not a formal experiment |
| **S1** — frozen formal short screen | the Amendment 4 / 5 regime unchanged: frozen configuration, all declared arms and matched nulls, 1000 episodes × 3 seeds unless a later owner ruling changes it; `ρ ≥ 0.5 × R_repr`, 2/3 direction, service / rate floor, matched null, beyond seed noise | no | screening threshold, not a publication threshold |

No E0 or E1 result may move a B1 / B2 / C threshold or redefine a formal gate. Development results never substitute for exact-DR
formal arms, B2 formal arms, matched nulls, the formal seed count, service / rate-floor checks, the `ρ / R_repr` gate, or the later
confirmation with more seeds and confidence intervals. No development result is a paper success claim.

## 2. The development kernel (frozen now)

- Student: the current ratio learner (three heads `Q_B/Q_E/Q_H`, `DQNNetwork` (100, 50, 50) tanh, 113-dim input, 28-action contract,
  deployed score `Q̃_B − η̃ Q̃_E`, λ = 0). No network redesign to start this lane.
- Teacher interface: masked teacher action; 28-action score / advantage vector where available.
- **T0 = LP-prev(c = 1, m = 0)**, the first **non-privileged anchor teacher**, computed from the raw user state (raw nominal SINR,
  raw previous-step loads), exactly the rule verified in `.scratch/h4-probe/LP-PROBE-2026-09-11.md`.
- Mechanisms in the kernel: **D0** (no teacher); **D2** (on-student-state soft distillation — primary); **D2-null** (T0's score vector
  randomly permuted among the legal actions per state, seeded — matched null for "does T0's information add value"); **D3**
  (unconditional DQfD-style large margin — required hard-imitation comparator). D1 / D4 and the full nine-arm formal harness are
  completed in parallel or later.
- Not decided now: the catfish count and the multi-teacher composition; T_DR / T_SEQ / T_JOINT remain later privileged-teacher
  candidates; B1 / B2 (observation contract) and the final credit are **instantiation branches** of the shared kernel, not reasons to
  block its development.

## 3. Seed namespaces — declared before any development result exists

Searched: the pilot declaration addendum, `cf3_common.py`, `cf_ratio.py`, the pool generator, the oracle / LP / ceiling / T0 / B1
scripts, Amendments 1–5. Seed values in use: training triples (42–46, 1337–1341, 7–11) and the trainer offsets `train_seed +
70_001`, `train_seed + 80_000 + k`; evaluation env / mobility `9_111_000+i` / `9_112_000+i`; calibration `9_121_000+i` /
`9_122_000+i`; RANDOM draws `9_131_000+i`; pools env `9_141_000+1000k+i` (k ≤ 2), superseded mobility base `9_142_000`, NULL
action generators `(9_151_000, k, j, i)`, pool mobility `9_161_000+1000k+i`; ceiling random init `9_171_000+i`; the T0 clone
data use the pilot training triples 0–2 (100 episodes each; TRAIN / VAL / TEST split by episode index). New ranges, disjoint from all
of these and from each other:

| namespace | use | seeds |
|---|---|---|
| **DEV** | development training streams (continuous per-seed streams, as the trainer uses them) | triple k = 0..9: `train = 9_201_000+k`, `env = 9_202_000+k`, `mobility = 9_203_000+k` (derived trainer generators then sit at `9_271_001+k` and `9_281_000+k+…`, reserved for that) |
| **DEV-NULL** | D2-null permutations; D3/D4-null random actions | `default_rng((9_231_000, k))`, `default_rng((9_241_000, k))` |
| **DEVVAL** | development evaluation, per-episode reseeded, fresh env, greedy | episode i = 0..23: `env = 9_211_000+i`, `mobility = 9_212_000+i`; RANDOM reference draws `default_rng(9_221_000+i)` |
| **CONFIRM** (reserved; **not generated or read during E0/E1**) | the new frozen confirmation set for the eventual paper claim, after the final algorithm is frozen | episode i: `env = 9_311_000+i`, `mobility = 9_312_000+i`; confirmation training triples `9_301_000+k / 9_302_000+k / 9_303_000+k` |

From now on **no learner parameter is tuned on the existing 24 evaluation or 24 calibration episodes.** They remain in use only for
the already-declared oracle and representability gates (and S1 as declared). The existing evaluation set has informed many design
decisions, so the paper's confirmation uses CONFIRM.

## 4. Re-triage of the live lanes (from actual state at 18:02 UTC)

| lane | decision | instruction |
|---|---|---|
| **LP-ORACLE** (A-floor R1 eval 24/24; B-floor R1 eval 15/24, 4 shards alive) | **KEEP, shortened** | finish B-floor R1 evaluation to 24/24; then immediately aggregate A-floor and B-floor, apply the declared B1/B2 conditions and report the branch numbers without waiting for the full report; the only next dataset is **B-real-floor R1 calibration** (out-of-evaluation data for T_SEQ / B2 representability); once it suffices, HOLD A-floor calibration (unless the chosen branch needs it), R2, reverse order, unfloored calibration tie-ins and every other completion task |
| **T0REPR** (clones fitted; τ = 3 selected on VAL; closed-loop runs done or finishing; 400-epoch sensitivity and entropy running) | **KEEP** | let running processes finish; then the first usable `R_repr` verdict on both sets immediately; entropy, extra tables and polish after the verdict; its evaluation-set performance is never used to tune the development learner |
| **B1-CREDIT** (credit + wiring + tests uncommitted; mutant runs red on four named mutants; lighting-price greedy-rule screen in progress) | **KEEP, de-serialised** | as soon as the core tests are green and the named mutants red, make a separate **engineering-core commit** (`cf_credit.py`, the credit-mode wiring, its tests, minimal support) — an engineering checkpoint, **not scientific validation of either credit**; then continue the lighting-price no-training screen, diagnostics, cost benchmark and PASS/FAIL report; it **no longer owns the harness** |
| **CEILING2** | **STOPPED — complete** | report written (`.scratch/ee-ceiling/EE-CEILING-2026-09-11.md`, parity 720/720, +41.4 % lower bound, rate-floored +23.9 %); no compute running; no further ceiling compute |
| completed review / curation agents | not resumed | — |

## 5. DEVHARNESS — new lane, from the B1 engineering-core commit

New worktree / branch from that commit (not behind the B1 scientific report). First the **minimum E0 surface**: D0, D2-T0, D2-null,
D3-T0. Preflight before E0: unit tests for the new loss paths; teacher weight = 0 reproduces D0 exactly; T0 action / score labels
reproduce the verified T0 rule; D2-null destroys teacher-action information while preserving dimensions, masks and schedule;
deterministic seed / config manifest; launcher dry-run; stop / resume and process identity by PID + cmdline + cwd; no formal evaluation
or calibration episode used anywhere in development. A **fresh-context engineering review of the minimum E0 diff** (agy, prompt fixed
in `.scratch/dev-training/AGY-E0-REVIEW-PROMPT.md`) plus these tests suffices for the development launch. **The complete fresh-context
formal review of all nine arms remains mandatory before S1.**

## 6. The first E0 batch (frozen here)

| # | arm | credit | status |
|---|---|---|---|
| 1 | D0 | equal_share | development |
| 2 | D2-T0 | equal_share | development |
| 3 | D2-null | equal_share | development |
| 4 | D3-T0 | equal_share | development |
| 5 | D0 | lighting_price | development diagnostic, only if B1's lighting-price code path has green unit tests |
| 6 | D2-T0 | lighting_price | same |

- equal_share is not endorsed as the final credit; it is the known implemented reference that isolates whether the teacher-injection
  kernel works. The lighting-price pair stays a development diagnostic even if the no-training screen later FAILS, and can never enter
  S1 evidence. **No exact-DR learner arm trains before its oracle-first formal gate** (Amendment 1 rule 1 on the rate-floored A-real).
- **Seed**: DEV triple k = 0 for every arm (paired). **Budget: 300 episodes per run** (frozen for this batch).
- ε: linear 1.0 → 0.01 over round(2000 · 300 / 9000) = 67 episodes, then flat (the CF3 compression rule). **η fixed at η_0 =
  110,507,234.83 bit/J, λ = 0, no η updates in E0** (an η update would need an episode set; development may not use calibration
  episodes). Units `s_B`, `s_E` from `calibration.json` (constants). Everything else as CF3 A1 (Adam 1e-3, batch 128, replay 50,000,
  hard target sync every 50 episodes, one update per decision step, P-03 filtering, gamma 1 with the remaining-steps feature).
- D2: loss `α · CE(softmax(T0 scores / τ), softmax(S / τ_s))` over legal actions on student-visited states, `S` = the deployed scalar
  score; initial `α = 1.0`, `τ = 3` (T0REPR's VAL selection on training-triple episodes, not on evaluation), `τ_s = 1`. D2-null: same with
  permuted scores. D3: `λ_E · (max_a [S(s, a) + m·1(a ≠ a_T)] − S(s, a_T))`, initial `m = 0.15` (CFSCREEN margin scale 0.14–0.16 in the
  heads' units), `λ_E = 1.0` (DQfD default). Teacher labels are computed from the raw user state at collection time and stored with the
  transition.
- Evaluation: DEVVAL (24 episodes) at episodes 100, 200 and 300, greedy; pooled EE with bits and joules, served, per-user rate
  mean / p10 / min, lit beams, H_inter / H_intra; the rule references `A m=2dB`, LP-prev(1,0), `MAX_NOMINAL_GAIN` and RANDOM rolled once
  on DEVVAL. Never on the evaluation, calibration or CONFIRM sets.
- Compute: sat, own workspace, ≤ 6 training processes while the oracle and T0 lanes run, `nice -n 10`, 1 thread, MemoryMax 5G,
  detached.

## 7. What E0 may and may not change

May (on DEV / DEVVAL evidence only): learning rate; teacher-loss weight / schedule; soft-distillation temperature; replay / query
frequency; gradient scaling / clipping; DQfD margin; target-update cadence; engineering-level stability fixes. Every change is logged in
`.scratch/dev-training/PROGRESS.md` with the configuration hash, the reason, the DEV / DEVVAL evidence that caused it, and whether it
is engineering-only or changes the algorithmic story. No config is overwritten silently. May not: redefine B1 / B2 thresholds or
Amendment 4; choose the catfish count; claim statistical superiority; select on the formal evaluation set.

## 8. E1, and joining the branches

After E0 shows the kernel is functional, at most the strongest one or two development configurations (chosen on DEVVAL) go to a modest
multi-seed E1 whose purpose is to freeze the shared kernel, the injection mechanism and the development hyperparameters. When B1 / B2
and privileged-teacher results arrive during E0 / E1, useful development runs are kept, the chosen credit / observation branch is
instantiated on the same kernel, mismatching earlier runs are classified as development diagnostics, and then the formal S1 config is
prepared.
