# Fable 5.1 clean-room audit — EE formula, R3/C3 target, and learner route

Work class: **non-heavy** (read-only scientific/source audit plus lightweight
recomputation). Stay in the current environment. Do not launch simulator jobs,
source generation, learner runs, episode training, sweeps, or server work.

<operating_mode>
The user will not be watching and cannot answer questions during this run.
Proceed autonomously within the scope below, make reasonable read-only choices,
and deliver the complete requested report. Batch independent reads and checks
when practical.
</operating_mode>

<role>
Act as an independent scientific-method and source-code reviewer. You are a
clean-room challenger, not an implementer and not a vote for the existing
design. The research objective is a genuine three-head Multi-Catfish MCRL:
exactly Q1, Q2, and Q3; one unweighted safe argmax of Q1+Q2+Q3 at deployment;
no coordinator, auction, vote, threshold, fallback policy, or post-training
override. The sole final metric is canonical ratio-of-sums energy efficiency.
</role>

<goal>
Determine, from the EE equation and executable physics, whether the current
R3/C3 route is causally valid and learnable, whether the V0.19 failure is best
explained by the R3 target/state or by the learner objective/sampling, and
whether the proposed V0.20 bounded learner screen is the correct next step.
Also identify any concrete C1/C2 premise that must be rechecked before a
three-head short-episode screen, without reopening their entire historical
design.
</goal>

<fresh_context_protocol>
Use this order so the existing proposal cannot anchor your derivation.

Phase A — independent derivation. Before reading
`.scratch/multi-catfish-v020-c3-candidate-screen/CANDIDATE-DESIGN-DRAFT.md`,
derive and record for yourself:

1. The exact condition under which a candidate physical action improves
   eta = total delivered bits / total network energy relative to its matched
   reference.
2. A causal map from a focal action through focal bits, non-focal bits,
   activation/link/network energy, future availability, handover/interruption,
   and the final ratio-of-sums EE.
3. What a non-overlapping C1/C2/C3 decomposition can prove, and what it cannot
   prove about learned heads, simultaneous composition, or positive ablation
   marginals.
4. The most defensible role for R3/C3 if all three heads must ultimately help
   the same EE objective.

For this phase, read only the EE-axis formula contract and executable physics
listed under `Phase A inputs` below. Do not read the current-authority summary,
the root derivation, the V0.20 draft, or old cross-model verdicts yet.

Phase B — evidence and challenger audit. Only after Phase A, inspect V0.18,
V0.19, the TRAIN-only census, and the V0.20 candidate draft. Compare their
claims with your independent derivation and report disagreements explicitly.
</fresh_context_protocol>

<primary_inputs>
Read the smallest relevant portions of these files, following imports when
needed:

Phase A inputs — formula and executable physics only:

- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`
- `src/mcrl/runtime/ee_axis_zero_marginal_c3.py`
- `src/mcrl/runtime/ee_axis_relational_zr_c3.py`
- the simulator/runtime functions actually used to compute delivered bits,
  link power, activation/network energy, handover/interruption, and canonical
  ratio-of-sums EE; locate them with `rg` rather than relying on prose.

Phase B inputs — current boundary, implementation, evidence, and proposals:

- `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`
- `.scratch/multi-catfish-v020-c3-source-audit/ROOT-SOURCE-DERIVATION.md`
- `src/mcrl/algorithms/ee_axis_relational_zr_c3_head_v019.py`
- `.scratch/multi-catfish-v019-relational-zr-normalized/learner/relational_q3_learner_v019.py`

Development evidence:

- `artifacts/multi-catfish-v018-relational-zr-20260904-r2/contracts/result.json`
- `artifacts/multi-catfish-v018-relational-zr-20260904-r2/contracts/independent-validation.json`
- `artifacts/multi-catfish-v019-relational-q3-learner-20260904-r1/server-run/gate-output/report/result.json`
- `artifacts/multi-catfish-v019-relational-q3-learner-20260904-r1/server-run/gate-output/independent-verification.json`
- the three V0.19 learner `result.json` files under
  `server-run/learner-output/init-*`
- `.scratch/multi-catfish-v020-c3-source-audit/v019-train-decision-geometry.json`
- `.scratch/multi-catfish-v020-c3-source-audit/analyze_v019_train_decision_geometry.py`

Existing proposal, read only in Phase B:

- `.scratch/multi-catfish-v020-c3-candidate-screen/CANDIDATE-DESIGN-DRAFT.md`
</primary_inputs>

<required_questions>
Answer every question with source/receipt references and distinguish verified
fact, inference, and proposal.

1. Starting from eta = B/E, derive the exact matched-reference sign condition.
   State precisely when a frozen lambda surplus has the same sign and when it
   is only a surrogate.
2. Audit whether current C1, C2, and C3 assignments are non-overlapping in
   physical bookkeeping. In particular, compare the original exact non-focal
   opening effect with the current zero-marginal/positive-credit-compatible ZR
   target. Identify any residual created by the conservative target and where
   it belongs.
3. Is `positive_credit_compatible` fully predecision-computable, or does any
   component leak outcome/counterfactual information into state or deployment?
   Audit both code and stored metadata, not names alone.
4. Independently recompute the headline V0.18 oracle effect and V0.19 learned
   gate direction from raw JSON. Then explain which conclusions those results
   do and do not support. Treat all of them as development evidence, not
   efficacy.
5. Diagnose V0.19 among at least these hypotheses: wrong output scale; uniform
   loss dominated by non-pivotal action cells; missing decision context;
   insufficient state information; structurally unsuitable R3 target; code or
   pairing defect. Rank them and state the falsifier for the leading diagnosis.
6. Determine whether the available state contains enough predecision signal to
   identify when a C3-compatible action crosses the detached Q1+Q2 action gap.
   Do not infer learnability solely from an oracle. Use conditional statistics
   or another lightweight TRAIN-only falsifier if needed.
7. Audit V0.20 Candidates A, B, and C line by line. For each, check unit
   compatibility, zero-at-teacher behavior, sign/tie handling, reference
   centering, gradient flow, sampling bias, stability pressure, relation to
   deployed argmax, and whether it silently recreates a classifier/gate or
   deployment mechanism. Point out any mathematical bug or unnecessary
   complexity.
8. If none is acceptable as written, propose at most two concrete replacements
   with complete equations, fixed sampling, and a bounded TRAIN-only selection
   rule. Prefer the simplest option that preserves one normalized Q3 surface
   and unweighted Q1+Q2+Q3 deployment.
9. Assess whether a positive C3 marginal in the Q1+Q2 context is theoretically
   possible, empirically supported in the sampled physics, or contradicted.
   Separate existence, oracle decision quality, supervised learnability, and
   episode-training efficacy.
10. Give the minimum pre-training recheck for C1/C2. Do not demand that all
    pairwise coalitions be positive unless that is mathematically necessary for
    the user's requested final ordering. Explain the exact acceptance relation
    needed for FULL > DROP-C1, DROP-C2, DROP-C3 > BASELINE.
</required_questions>

<evidence_rules>
- Do not open or use any TEST split.
- Do not launch any simulator, source harvest, learner, episode training, or
  sweep. Small scripts that only recompute statistics from already-opened TRAIN
  or existing published-development JSON/NPZ are allowed; save them under the
  output directory.
- Do not modify `src/`, `docs/`, existing `.scratch/` designs, contracts,
  authority files, or existing artifacts.
- Do not tune thresholds, seeds, horizons, lambda, targets, or candidate
  definitions against a newly opened outcome.
- Existing model reports are hypotheses, not authority. Verify equations and
  numbers yourself.
- A decomposition identity is not evidence that each learned head helps EE.
- An oracle gain is not learner success; a learner gate is not episode-level
  efficacy; TRAIN development signs are not held-out claims.
- Do not preserve R3, ZR, or V0.20 merely to minimize changes. Reject or amend
  them if the source-level derivation requires it.
</evidence_rules>

<deliverables>
Create only this directory and its files:

`artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/`

Required files:

1. `FABLE-C3-SOURCE-AUDIT.md` containing:
   - executive verdict;
   - independent EE derivation and causal map;
   - C1/C2/C3 bookkeeping audit;
   - independently authenticated evidence table;
   - ranked root-cause diagnosis for V0.19;
   - V0.20 A/B/C adjudication;
   - any replacement equations;
   - minimum C1/C2 recheck;
   - one bounded next-step contract;
   - claim ceiling and remaining risks.
2. `verdict.json` with machine-readable fields:
   `decision`, `r3_target`, `v019_root_cause`, `selected_candidate`,
   `required_amendments`, `c1_c2_recheck`, `next_compute_class`, and
   `prohibited_claims`.
3. `MANIFEST.sha256` covering every file in the directory except itself.

End the Markdown report with exactly one of these decision tokens on its own
line:

- `FREEZE_V020_TRAIN_ONLY_SCREEN`
- `AMEND_V020_THEN_FREEZE_SCREEN`
- `REDESIGN_R3_TARGET_FIRST`
- `STOP_R3_ROUTE_AS_STRUCTURALLY_UNSUPPORTED`

If the next step would exceed roughly 30 minutes, classify it as heavy and
write a server handoff plan with estimated wall time; do not launch it.
</deliverables>

<final_response>
Return a concise summary containing the decision token, the leading diagnosis,
the selected/amended candidate if any, discrepancies found, the exact report
path, and the manifest hash. Avoid mannered prose. Then stop.
</final_response>
