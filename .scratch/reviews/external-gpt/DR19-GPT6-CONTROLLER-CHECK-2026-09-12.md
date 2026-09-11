# Controller check of two owner-pasted external documents: `dr19.md` (ChatGPT Deep Research addendum on privileged teachers) and `gpt6.md` (ChatGPT fresh-context reading of the repo and `sat`)

Date: 2026-09-12 ~01:05 Asia/Taipei (17:05 UTC 2026-09-11). Copies of both documents sit beside this file. Every number
below was re-read by the controller from the named artefact; "[V]" = re-read; "[R]" = relayed from the external
document and not re-checked.

## 1. `gpt6.md` — numbers verified against the artefacts

| claim in gpt6 | artefact | verdict |
|---|---|---|
| parity exact: max Δbits = 0, max ΔJ = 0 | `.scratch/ee-ceiling/PROGRESS.md` §"16:50 UTC interim": all searched steps, every variant, **580 steps**, identity | **[V] correct** — the ceiling agent itself recorded parity PASS, which satisfies Ruling 2 §1 in substance (its final report is still pending) |
| base service-floor search 24/24: pooled 151.257 M vs `A m=2dB` 107.001 M, +41.361 %, paired +41.943 ± 1.493 %, 24/24 | same file, "STEP 7 RESULT" | **[V] correct**; also 240/240 steps hit the 3-sweep budget → a **lower bound** |
| rate-floor variant +23.914 % (6 ep), bits ratio 0.981 | `sat:…/ceiling-ws/results/ANALYSIS.json`: `pooled_rel 0.23914`, `bits_rel −0.01925`, `joules_rel −0.20853` | **[V] correct** |
| nominal-information variant +10.958 %, bits ratio 0.483 | ANALYSIS.json: `pooled_rel 0.10958`, `bits_rel −0.51666` | **[V] correct** — throughput-degenerate by bits (the p10 flag missed it; the ceiling agent notes this) |
| compound +44.854 % (6 ep), +0.274 % over the base on the same episodes | PROGRESS §16:50 | **[V] correct** |
| LP-prev(1,0): eval +6.66 %, cal +4.75 %, bits ratio 0.954 / 0.952, served > 0.998, p10 not collapsed | `.scratch/h4-probe/LP-PROBE-2026-09-11.md` lines 95, 108: eval 114,129,570.59 (+6.662 %, paired +6.85 ± 0.65 %, 24/24), served 0.99854, bits 0.954, p10 ratio 1.016; cal 117,528,214.55 (+4.753 %, paired +4.82 ± 0.41 %, 24/24), bits 0.952, p10 ratio 0.968 | **[V] correct** |
| LP-seq(2,0) +8.92 % but served 0.988, p10 0.41 × rule | LP report first line | **[V] correct** |

Additions gpt6 did not make (all [V], same files):
- The base search's per-user rate p10 is **50.89 Mbit/s = 50.2 % of the rule's p10 (101.4)** — 0.19 Mbit/s above the
  throughput-degeneracy line. The +41 % therefore has a thin tail; the defensible headline lower bound is the
  **rate-floored +23.9 % (6 episodes)**, which keeps bits within 2 % of the rule.
- **Coordination depth**: 74.0 % of the base search's final gain is reached after sweep 1 (one sequential best-response
  pass) and 93.2 % after sweep 2 (mean of per-step ratios; per-sweep bits/joules not stored); the beam-emptying compound move
  adds +0.27 %. The joint gain is shallow coordination, not deep.
- **Information matters more than coordination**: the same search scored with nominal (observation-level) information
  collapses bits by 52 %, while realised information gains +41 % at bits −1.9 % (rate-floored). What the per-user student
  lacks is current-step interference/realised-rate information; the oracle cells (A-real/B-real vs A-nom/B-nom) will
  separate credit from information.
- The ceiling runs did **not** save committed joint actions (the search is deterministic; a re-run with an action dump
  reproduces them). The joint teacher's labels need that re-run.

## 2. Scenario status under the declared rules (Ruling 2 §2; Amendment 1 §3), as of 17:05 UTC

- **Scenario A is excluded**: constrained lower bound +41.4 % (paired, 24/24), rate-floored +23.9 % (6 ep) ≫ +3.3 %.
- **Scenario B's nominal condition is met by a deployable witness**: LP-prev(1,0), a simultaneous, observation-only per-user
  rule, clears +4.5 % with served ≥ 0.995 and bits ratio ≥ 0.95 **on both episode sets** (eval +6.66 %, cal +4.75 %; the
  calibration replication is the check against selecting the best of 24 cells on the evaluation set). The ceiling's own
  nominal search does not (bits −52 %).
- **B1 vs B2 vs C is not yet decided**: that is Amendment 1 rules 1–4 on A-real / B-real (running on the H4 harness).
- **C residual is large**: per-user deployable ≈ +5–7 % against a joint lower bound of ≈ +24 % (rate-floored).
- gpt6's reading ("B has a real usable space; C has a larger residual; the current three-static-catfish implementation is
  not worth saving; the multi-catfish question is better founded than a few hours ago") matches this. Its critical path
  (ceiling fill → A-real/B-real → declared gates → B1/B2/C → first short training) matches Ruling 2.

## 3. `dr19.md` — adopted, corrected, flagged

**Adopted** (methodology; see Amendment 3 to Ruling 2):
1. The **imitation gap** (ADVISOR, Weihs et al. 2021 [R]): when the teacher's action depends on information the student
   lacks, literal imitation converges to a conditional mixture and can be worse than the restricted optimum. This maps
   exactly onto "whether my choice lights a new beam depends on others' same-step choices".
2. **Soft advantage / Q-vector distillation** (CTDS-style [R]) instead of one-hot margins: under aliasing, averaging the
   teacher's 28-action advantage vectors gives the conditional expected utility given the student's information — a
   well-defined target.
3. **DAgger-style teacher queries on student states** and **gated margins** (Q-filter / ADVISOR logic); unconditional DQfD
   margin kept as a required comparator, static teacher replay as the weakest arm.
4. The **representability metric** = the fraction of the teacher's headroom a behaviour-cloned (or soft-distilled) student
   recovers in closed loop, not action accuracy; learner performance read relative to that ceiling.
5. The **causal ladder** D0 (difference-reward RL, no teacher) → D1 static teacher replay → D2 DAgger/soft distillation →
   D3 unconditional DQfD margin → D4 gated margin; multiple teachers only after the best D arm beats D0, then T1, T1+T2,
   T1+T2+T3 plus drop-one.
6. **Teachers ordered by coordination depth** (T_DR unilateral exact-DR, T_SEQ sequential sweep, T_JOINT joint search) —
   identical to the oracle table's rows; referee demands (teacher advantage and privilege class stated; imitation gap
   measured; credit separated from demonstration; decentralised execution proven).

**Corrected**:
- "No peer-reviewed RL literature line for Catfish" is true of the **name** and of the RIS source — which the project's own
  record already classifies as grey literature (an institutional MSc thesis, no DOI; `.scratch/acrm-provenance/ACRM-PROVENANCE-2026-09-11.md:26-35`)
  — but **the mechanism family is peer-reviewed**: competitive two-learner experience/replay and regret-shaped rewards
  (Competitive Experience Replay, ICLR 2019; CuSP, ICLR 2022, exact form of ACRM; Sukhbaatar et al., ICLR 2018; Hughes et
  al., NeurIPS 2018 — erratum 26). DR searched by name only (both framings contain "catfish"), the failure mode recorded in
  memory `framing-determines-the-negative-result`. The thesis's lineage claim for the competitive element should cite
  CER/CuSP; the privileged-teacher direction cites LUPI/CTDE/RLfD/counterfactual credit.
- "Exact difference reward is only training-time cost, so less problematic": right in kind, but the magnitude decides the
  design. Measured: 7.5 ms per counterfactual evaluation (ceiling bench); a full 28-action advantage vector for 100 users
  = ~2,700 evaluations ≈ 20 s per step ≈ 200 s per episode. A DAgger query of T_DR on every student state would cost
  ~55 process-hours per 1000-episode run; T_JOINT (~20 min per episode) is infeasible as an on-student-state teacher.
  Practical: subsample queried steps/users; use the analytic lighting-price energy term (the B1 agent found joules are
  independent of interference and fading, so `E^D` is analytic and free) and counterfactual evaluation only for bits.

**Flagged for the owner**:
- **B2 changes the execution contract** (the student receives same-step information about earlier users' choices at
  deployment). DR's referee point 4 ("prove decentralised execution") applies. Ruling 2 wrote B2 as keeping the contract;
  it is a lighter change than a coordinator, but a change — it needs the owner's explicit decision like C.
- T_DR's "highest representability" in DR is an expectation: A-real's action depends on the reference joint action
  (others' current choices), which the student does not observe — it is privileged too; the representability screen
  measures it. The one teacher whose representability is certain is the **LP lighting-price rule itself** (an exact function
  of the student's observation).
