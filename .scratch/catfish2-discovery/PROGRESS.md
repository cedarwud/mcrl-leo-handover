# CATFISH2-DISCOVERY — PROGRESS

Agent: CATFISH2-DISCOVERY (opus). Lane: Stage 0 discovery, **no training, no optimizer step**.
Brief: `.scratch/catfish2-discovery/BRIEF.md` (reading rule §3 committed at `bbaf5ea0`, before any counted evaluation).
Amendment: `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-9-CATFISH2-DISCOVERY-2026-09-12.md`.
Deliverable: `.scratch/catfish2-discovery/STAGE0-2026-09-12.md`.

## Isolation receipts
- Local worktree: `/home/u24/papers/mcrl-leo-handover-cf2`, branch `catfish2/discovery-20260912`, from `05aadf1bb24a9e3a730975227fbf27ab7760deb9`. CREATED 2026-09-12.
- Server workspace: `/home/sat/mcrl-v025-catfish2-ws/` (own result root). Never touch `/home/sat/mcrl-v025-dev-e0-ws/`.
- Namespaces: DEVVAL only — env `9_211_000+i`, mobility `9_212_000+i`, i = 0..23.
- TLE: `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91`, sha256 `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9` (asserted per run).

## Step log

| # | step | status | receipt |
|---|---|---|---|
| 0 | Read brief, Amendment 9, E0 freeze | DONE | — |
| 1 | Create isolated worktree | DONE | `git worktree list` shows `-cf2` at `05aadf1b` |
| 2a | Settle the 113-dim observation contents | DONE | see "Finding 1" |
| 2b | Settle which EXISTING project constant serves as `R_min` | DONE — **NONE EXISTS; STOPPED for a controller decision** | see "Finding 2" |
| 5 | Controls + decomposition endpoints, 24 DEVVAL episodes | DONE | `sat:/home/sat/mcrl-v025-catfish2-ws/results/DEVVAL-CONTROLS.json` |
| 6 | Value-weighted complementarity diagnostic vs T0 (R_min-independent policies) | RUNNING | 3 shards, `results/DIAG-CF2-s{0,1,2}.json` |
| 7 | `r̂` instrument characterisation for the controller's `R_min` ruling | PENDING | `results/RHAT-INSTRUMENT.json` |
| 8 | Write `STAGE0-2026-09-12.md` | PENDING | — |
| 3 | Server workspace + tree + runner | DONE | tar sha256 `4d755e40936d5c2e07fb007640930d99c41db920b2fbc6b65ed4799f867ef9f9` verified both ends; `tree/COMMIT` = `05aadf1bb24a9e3a730975227fbf27ab7760deb9`; TLE assertion passes (`427e6a91…`) |
| 4 | Cost probe | DONE | DEVVAL rollout ≈ 1.4 s/episode → 34 s per 24-episode arm; `StepEnvironment.evaluate_actions` ≈ 83 ms per call |

## Finding 1 — what the deployable 113-dim observation carries

`src/mcrl/runtime/state_encoding.py::encode_state` (lines 20–128) + `state_dim_for` (131–141) build the
**112**-dim per-user state as four beam-indexed blocks of `C = 28` (satellite-major, beam-minor,
ASSUME-MODQN-REP-012), concatenated in this order:

| block | source field (`env/step_types.py::UserState`) | encoding at `encode_state` | meaning |
|---|---|---|---|
| 1 | `access_vector` (line 81) | raw 0/1 | one-hot current/incumbent beam assignment |
| 2 | `channel_quality` (line 84) | `log1p(max(snr, 0))`, line 70 | nominal (previous-step-interference) **linear SNR/SINR** γ_a per candidate slot |
| 3 | `beam_offsets` (line 87) | raw radians, line 81 | per-candidate off-axis angle θ |
| 4 | `beam_loads` (line 95) | `/ num_users`, lines 96–98 | **global, ungated, pre-admission** previous-step demand count n_a for the physical beam behind that slot — the paper's `n_{s,v}(t−1)` |

The 13-dim `contract_fields` block is an **ablation switch, off by default** (ruling C-1, `state_encoding.py`
lines 100–115, `step_types.py` lines 109–125) and is *not* part of `s_u`. The **113th** feature is added by
`src/mcrl/algorithms/cf_ratio.py::encode_with_time` (lines 204–210): `(T − t) / T`, the normalised remaining
steps. Nothing else is in the observation.

Consequence for this lane: `γ_a` = block 2, `n_a` = block 4 × `num_users`. `B_w = BEAM_BANDWIDTH_HZ = 500 MHz / 3
= 166.667 MHz` (`env/link_budget.py:21,28`) and `num_users = 100` are fixed configuration constants, not
observations, so `r̂(a) = (B_w / (n_a + 1))·log2(1 + γ_a)` is an exact function of the deployable observation.
Both candidate rules read the RAW `UserState` fields, exactly as `cf_sources.py` (its own docstring, lines
25–27) and `cf_teacher.t0_scores` already do; the log1p-encoded array is never used for the score (T0REPR
measured 2.4e-7 relative decode error, `cf_teacher.py` docstring).


## Finding 2 — `R_min`: **no such constant exists.** Lane stopped for a controller decision.

The brief (§1, C-Q) requires "`R_min` **must be an existing declared constant of this project** (the declared
nominal rate target or the ACM/service threshold already used by `service.py` / `link_budget.py`) — find it in
the code, name it in the report, and do not invent or tune a value", and instructs: "If no such constant
exists, say so in PROGRESS and stop for a controller decision rather than inventing one."

**Verified first-hand in the worktree at `05aadf1b` (not taken on report):**

1. `src/mcrl/env/service.py:289-301` — the only minimum-rate consumer this project ever had is **deleted**:
   > `# PATCH P-22 (W-26): `required_sinr()` is deleted.` … `It computed γ_req(U) = 2^(R^m·U/B^w) − 1, the
   > SINR needed to hold a minimum rate at a given load.` … `R^m = 1 Mbit/s is a **legacy-only** parameter
   > (ruling C-12), and the active contract "明文排除最低速率反推"; ruling C-2 forbids target-SINR inversion
   > outright`.
2. `docs/CONTROLLER-RULINGS-2026-08-22.md:180` (**C-12**) puts `R^m = 1 Mbit/s` in the **Legacy provenance**
   column: `| R^m = 1 Mbit/s(active 契約明文排除最低速率反推) |`.
3. `docs/CONTROLLER-RULINGS-2026-08-22.md:52-54` (**C-2**): `論文明寫不引入目標 SINR 反推、beam/satellite
   cap、PA clamp、min/max projection —— 這幾項一個都不要加回來。**唯一的上限是每波束 RF 輸出上限的可行性
   檢查,它在遞迴之外**`. The one live ceiling is `BEAM_POWER_MAX_W = 1.65 W` (`env/link_budget.py:175`) — a
   **power** feasibility test, not a rate threshold, and it is already the gate that decides `served`.
4. `env/link_budget.py` carries **no** rate threshold and **no** ACM/MODCOD table. Rate is produced only by
   `shannon_rate_bps` (line ~590), `R = (B^w / U_{s,v})·log2(1 + γ)`.
5. `grep -rnoE "[A-Z][A-Z_0-9]*_BPS" --include=*.py src/` → **zero hits**; `grep -rnE "\b(1e6|1_000_000|50e6|
   50_000_000|25e6|100e6)\b" --include=*.py src/` → **zero hits**. There is no absolute rate constant in
   `src/` at all.
6. `git ls-tree -r --name-only HEAD | grep -c physics_v025` → **0**. The v0.25 physics engine that declares
   `RATE_TARGET_BPS = 50_000_000.0` exists only on the unmerged `server/v025/*` branches, is not an ancestor
   of `05aadf1b`, is not imported by `env/step.py` even there, and its own provenance audit calls it a
   **power-control setpoint with "no delivered-rate or demand guarantee"** — so it is neither available to,
   nor semantically usable by, the MODQN DEVVAL environment these rollouts run on. The active symbol table
   likewise calls `R^⋆ = 50 Mbit/s` `功率設定點，不是需求模型`, and retires `R^m` / `R_min` from the active
   surface.

**Consequence.** C-Q and C-RC are not fully defined and **cannot be counted** at Stage 0. They are neither
`DROP` nor `CANARY-ELIGIBLE`; they are **BLOCKED — no `R_min`**, pending the controller.

**Second, design-level objection, recorded for that decision** (not a measurement): an absolute `R_min` used
to *gate actions* against a predicted share `r̂(a) = (B_w/(n_a+1))·log2(1+γ_a)` is one algebraic step from the
inversion `γ_req = 2^(R^m·U/B^w) − 1` that PATCH P-22 deleted and ruling C-2 forbids — declaring one re-opens
a closed ruling, not merely a parameter.

**What this lane did instead**: everything that does not depend on `R_min` — the controls, the T0
decomposition endpoints, and the value-weighted complementarity diagnostic — was completed, and the `r̂`
distribution was characterised as decision support (`RHAT-INSTRUMENT.json`), with **no candidate outcome
computed at any threshold**, so that choosing `R_min` from a result remains impossible from this lane's output.

## Declared before running: the QoS-invalid definition used by the diagnostic

Ported verbatim from the existing convention in
`.scratch/h4-probe/scripts/oracle_cells.py::best_response_step` (lines 190-215), with the reference
`R` = **T0's joint action at that same step** (the counterfactual holds every other user at it):
a unilateral move is QoS-invalid iff some user served under `R` becomes unserved, **or** some user served
under both has realised rate below `0.5 ×` its rate under `R` at the same step. The `0.5` is the project's
existing factor (Ruling 2 §2 rate-floor variant), not a new one.

---

## Amendment 11 (controller, `98dd3f48`) — received 23:20 UTC, blocker resolved

The controller upheld Finding 2, **refused an absolute `R_min`** (no such threshold may be declared without an
owner decision reopening C-2), adopted this lane's design-level objection as a standing project constraint, and
re-specified the candidates on the project's existing 10th-percentile tail convention. **Provenance: when this
lane received the amendment, no candidate outcome at any threshold had been computed** — see
`STAGE0-2026-09-12.md` "Provenance guard".

| # | step | status | receipt |
|---|---|---|---|
| 9 | Implement C-Q′-local, C-Q′-global, C-RC′ per Amendment 11 §2 | DONE | `scripts/cf2_common.py` (`TAIL_PCT = 10.0`, `q10_local`, `q10_global`, `cq_local_rule`, `crc_local_rule`, `cq_global_actions`) |
| 10 | Mirror `cf_dev.dev_rollout` for the privileged arm, and VERIFY the mirror | DONE | `A11-MIRRORCHECK-T0.json`: T0 through `cf2_priv.py::priv_rollout` reproduces `DEVVAL-REFERENCES.json`'s `LP_prev_c1_m0` row to zero absolute difference on all ten statistics |
| 11 | Standalone DEVVAL rollouts of the three candidates | DONE | `A11-DEVVAL-LOCAL.json`, `A11-DEVVAL-C_Q_global.json` |
| 12 | Complementarity diagnostic re-run with all three added | DONE | `A11-DIAG-s{0,1,2}.json`, 60,143 counterfactual evaluations |
| 13 | Aggregate and adjudicate against brief §3 | DONE | `STAGE0-AGGREGATE-A11.json` |
| 8 | Write `STAGE0-2026-09-12.md` | DONE | report written; all sha256 receipts inside it |

**Verdicts (brief §3, unchanged by Amendment 11 §3).** All three DROP.
`C-Q′-local` — c3 fails, 0.0024 shared-state disagreement (57 of 24,000 decisions); it is the only arm in the
lane clearing c4 (`CR = 0.5037`), which is the same fact seen from the other side.
`C-Q′-global` — c3 (0.0760) and c4 (`CR = 0.4798`) both fail; its `R_repr` clone screen was **deliberately not
run** because condition 1's clone test gates advancement and an arm failing c3 and c4 cannot advance at any
`R_repr`. The one-survivor-slot rule is moot.
`C-RC′` — c4 fails (`CR = 0.4229`); c3 also fails on the shared-state reading (0.2311; 0.3337 own-trajectory),
and the verdict does not depend on which reading is taken.
**T0 decomposition REJECTED**: link endpoint fails c3 + c4; activation endpoint fails c2 + c4 + c5.
**Amendment 11 §4's escape hatch was not needed** — every candidate was evaluable with no number that is not
already in the project.

**Server state at close**: no `catfish2` process alive (verified by cwd + cmdline). The dev lane's nine E1
runs were never touched.
