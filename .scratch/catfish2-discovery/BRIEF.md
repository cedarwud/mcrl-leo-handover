# CATFISH2-DISCOVERY — Stage 0 brief and the prospective reading rule (written before any counted evaluation)

Owner direction `gpt9.md` (copied to `.scratch/reviews/external-gpt/gpt9.md`). Date 2026-09-11 23:10 UTC.
**Stage 0 is discovery only: no learner training.** Everything here is development work; nothing is formal evidence.

**Status note that changes nothing but removes a constraint**: the Catfish-1 funnel has already completed. D3-null ran on
k = 0/1/2 and the provisional algorithm is frozen (`.scratch/dev-training/E0-FREEZE-PROVISIONAL-ALGORITHM-2026-09-12.md`).
T0's causal marginal under D3 is therefore closed on three development seeds (D3-T0 beats the paired D0 by +9.11 / +13.34 /
+9.23 %, 24/24 each; the matched null is −39 to −55 %). Nothing in this lane may reopen, redesign or gate that line, and no
process of this lane touches its worktree, roots or code.

## 0. Isolation

Own worktree from the frozen development code `05aadf1b` (branch `catfish2/discovery-20260912`), own result root, own server
workspace `/home/sat/mcrl-v025-catfish2-ws/`. DEV / DEVVAL namespaces only: the 24 DEVVAL episodes (env `9_211_000+i`,
mobility `9_212_000+i`) for every counted rollout; the formal evaluation (`9_111_000+i`), calibration (`9_121_000+i`) and
CONFIRM (`9_311_000+i`) sets are never touched. No formal seeds, no hyperparameter grid, no new observation feature.

## 1. Candidates

**Prospectively specified, one variant each. Definitions are fixed here and recorded before any counted run.**

- **C-Q — QoS / rate-tail specialist.** Purpose: protect the weak-user rate where T0's consolidation would overload a beam.
  Deployable form: T0's score restricted to candidates that clear a **pre-existing** rate criterion, using the user's own
  observation-level predicted share `r̂(a) = (B_w / (n_a + 1)) · log2(1 + γ_a)`, where `γ_a` is the block-2 nominal SINR and
  `n_a` the block-4 previous-step load. Choose `argmax_a T0-score(a)` over `{a : r̂(a) ≥ R_min}`; if that set is empty, fall back
  to `argmax_a r̂(a)`. **`R_min` must be an existing declared constant of this project** (the declared nominal rate target or the
  ACM/service threshold already used by `service.py` / `link_budget.py`) — find it in the code, name it in the report, and do not
  invent or tune a value. State exactly what `r̂` approximates and what it cannot see (it is the user's own share, not the beam's
  weakest user).
- **C-RC — rate-qualified consolidation.** Purpose: save activation energy only when the throughput sacrifice is acceptable.
  Deployable form: among candidates clearing `r̂(a) ≥ R_min`, prefer one whose beam was already lit (`n_a > 0`), breaking ties by
  `log2(1 + γ_a)`; if no lit candidate clears `R_min`, take `argmax_a log2(1 + γ_a)` among the clearing set; if none clears, take
  the unrestricted `argmax_a log2(1 + γ_a)`. This is deliberately not `B1_NO_NEW_BEAM`, whose restriction is unconditional.
- **Controls / references, rolled cheaply, not hypotheses**: `T0 = LP-prev(1,0)`, `MAX_NOMINAL_GAIN`, `A m=2dB`, `A m=12dB`,
  `B1_NO_NEW_BEAM`, and the frozen MODQN eq-(16) DEVVAL reference already measured (94,413,179 bit/J).
- **T0 decomposition diagnostic** (analysis only, no learner runs): the link endpoint (`c = 0` = `MAX_NOMINAL_GAIN`), the
  activation-heavy endpoint (`B1`-like high `c`), and the fused `T0` (`c = 1`): standalone frontier position, disagreement with
  T0, value-weighted complementarity, and whether either endpoint owns a state subset where it beats fused T0.

## 2. Measurements (24 DEVVAL episodes, greedy, fresh env per episode, pinned archive)

Per candidate and control: pooled EE (bits and joules separately), served fraction, per-served-user rate mean / p10 / minimum,
active beams, `H_inter` / `H_intra`, action agreement and disagreement with T0, and disagreement with `MAX_NOMINAL_GAIN` (and
with the frozen MODQN reference if cheap).

**Value-weighted complementarity against T0.** On every decision where the candidate and T0 choose different legal actions, hold
**all other users at T0's joint action for that step** and use the environment's counterfactual evaluator with common random
numbers to record the candidate-minus-T0 unilateral `Δbits`, `Δjoules`, and `Δ(bits − η₀·joules)` with `η₀ = 110,507,234.83444457`
bit/J; also whether the candidate raises the step's own predicted share for the moving user, the candidate-better fraction, the
T0-better fraction, the median / p10 / p90 of the value difference, and the fraction of moves that would be QoS-invalid. This
diagnostic may use privileged physics **for measurement only**; the source policies themselves stay deployable.

## 3. Prospective reading rule — fixed here, before any counted Stage-0 evaluation

A candidate advances to a Stage-1 canary only if **all five** hold. The numbers reuse existing project conventions; none is
invented after seeing a result.

1. **Deployability**: the policy is an exact function of the current deployable observation (algebraic check). If a candidate is
   not exactly observation-computable, it is classified privileged and must pass the existing clone test at `R_repr ≥ 0.5`
   (evaluation and calibration) before any canary.
2. **Position in (EE, served, p10)**: either **non-dominated** against T0 and the other retained candidates (no other is at least
   equal on all three with one strict advantage), **or clearly complementary**, defined as `p10 ≥ 1.10 × T0's p10` on the same
   set with `served ≥ 0.995` and `EE ≥ 0.95 × T0's EE`.
3. **Behavioural distinctness from T0**: action disagreement on shared states **≥ 25 %** (the Ruling 2 §4 pre-screen number, kept
   as a diagnostic, not as the definition of a catfish).
4. **Positive value-weighted complementarity**: on the disagreement states, the candidate-better fraction **≥ 0.30** and the
   complementarity ratio `CR = Σ max(Δ, 0) / Σ |min(Δ, 0)| ≥ 0.5`, with `Δ` the unilateral `Δ(bits − η₀·joules)` defined above.
   A candidate that merely differs, while losing wherever it differs, fails.
5. **No QoS collapse**: `served ≥ 0.995`, `p10 ≥ 0.5 ×` the `A m=2dB` p10 on the same set, and a strictly positive minimum
   served-user rate.

**Ranking and cap**: survivors are ranked by `CR`; if two are within 10 % relative on `CR`, the higher p10 ranks first. **At most
the best two advance.** If zero qualify, the report says zero — no count is manufactured.

**T0 decomposition**: the decomposition is *supported* only if each endpoint separately satisfies conditions 1–5 against the
fused T0. Otherwise the report states that T0 remains one candidate source and the decomposition is rejected as a multi-catfish
interpretation.

## 4. Stage 1 (not authorised yet — the controller confirms after reading the Stage-0 table)

Per survivor: the already-working D3 large-margin injection, DEV k = 0, 100 episodes, the same student, credit and optimisation
configuration as the frozen D3-T0 line, a matched random-legal null with its own declared DEV-NULL generator identity, compared
against D0 at the same depth. A candidate closes immediately if it does not beat its matched null and D0 directionally without
QoS degradation. Only a k = 0 survivor gets k = 1. Nothing runs to 300. No exact-DR training, no B2 reopening, no long oracle
search, no change to the frozen Catfish-1 learner.

## 5. First report

`.scratch/catfish2-discovery/STAGE0-2026-09-12.md`, one compact table with: candidate name, the exact deployable score or rule,
the information it uses, standalone EE / served / p10, Pareto status, T0 action disagreement, value-weighted complementarity,
representability result, and the classification `DROP` / `CONTROL ONLY` / `CANARY-ELIGIBLE`. Then state whether the T0
decomposition is supported or rejected, which zero to two candidates advance, and the prospective reading rule that was applied
(quote §3). Keep `.scratch/catfish2-discovery/PROGRESS.md` current; ≤ 3 server processes, `nice -n 16`, one BLAS thread, detached
for anything long, exact-PID kills, sha256-verified copies.
