# V0.20 C3 screen root pre-freeze audit

Date: 2026-09-04  
Status: **NON-AUTHORITY / NO RUN / NO OUTCOME OPENED**

This note records the finite closure items that must be resolved after the
Fable clean-room review and before any V0.20 candidate implementation is
frozen. It does not select a candidate or authorize learner/episode training.

## Already coherent

- All three candidates retain one normalized `(N, 28)` Q3 surface and the
  deployed decision `argmax(Q1 + Q2 + Q3)` over the native safe mask.
- Q1+Q2 is detached loss context only; it is neither Q3 state nor a deployment
  gate and receives no gradient.
- Exact target calibration remains in the common normalized EE-surplus unit.
- Structural reference centring makes the reference Q3 value exactly zero, so
  an extra gauge penalty would be redundant.
- Candidate A uses the background only in its ordering-violation term;
  Candidate B uses it in the student decision margins. The calibration
  differences themselves algebraically reduce to Q3-minus-target differences,
  which is expected rather than a defect.
- Candidate C is a useful causal control for class imbalance versus genuine
  decision-context dependence.

## Items that must be frozen, not decided after outcomes

1. **Training decision context authority.** Convert the V0.19
   `evaluation_only=true`, `learner_loadable=false` sidecar into a new explicit
   TRAIN-only, digest-bound, loss-only context. Never silently reinterpret the
   old sidecar.
2. **Tie rules.** Apply the native lowest-action-index tie rule to the teacher
   winner, background reference, top-background strata, student decision, and
   Candidate B's online hardest rival.
3. **Sampling seeds.** Declare the exact seed derivation and immutable batch
   schedule for candidate, lineage, fold, and update. Replacement is allowed
   only within the preregistered stratum.
4. **Missing classes.** A fold lacking any required class/stratum is a
   mechanical failure, not permission to change proportions.
5. **Positive decision-margin recall.** Define it explicitly. Recommended
   action-cell definition:

   \[
   R_+=\frac{|\{(n,a)\in W:m^S_{na}>0\}|}{|W|}.
   \]

   Keep this distinct from pivotal-row teacher-winner agreement.
6. **Changed-action precision.** Use exact deployed student argmax. A run with
   no changed action is ineligible under the exposure rule; do not assign it a
   favorable vacuous precision.
7. **Frozen nulls.** Name and implement every null before the run. At minimum:
   zero-Q3/background-only and the unchanged V0.19 learned Q3 surface. Decide
   before freezing whether a deterministic highest-background-compatible
   heuristic is a diagnostic or a null; it cannot become a deployment method.
8. **Teacher regret.** Record exact held-out regret even if it is not the
   primary selector:

   \[
   R=\operatorname{mean}_n[T_{nt_n}-T_{n\hat a_n}],\qquad
   R^0=\operatorname{mean}_n[T_{nt_n}-T_{nr_n}].
   \]

   The contract must state whether `R/R0 < 1` is an eligibility requirement or
   diagnostic only.
9. **Initialization parity.** Declare the exact shared initialization seeds and
   guarantee byte-identical initial Q3 parameters across candidates within a
   lineage/fold comparison. State whether the screen has one initialization per
   lineage or a separate initialization panel.
10. **Selection rule.** The ranking must be total and deterministic. Every
    metric used for selection, including `teacher-agreement skill`, must have a
    formula, aggregation order, and zero-denominator rule.
11. **Data boundary.** Fit-stratum construction uses only the three fit TRAIN
    worlds in each fold. The fourth TRAIN world is evaluation-only for that
    fold. No VALIDATION/TEST or simulator import is allowed.
12. **Claim boundary.** Passing this screen establishes only source-level
    decision learnability on rotated opened TRAIN worlds. It does not establish
    C3 EE efficacy, positive ablation marginal, or the requested five-arm
    ordering.

## Candidate-specific questions for adjudication

### Candidate A

- Confirm whether macro weighting `W/H/R = 1/3 each` and sampling
  `192/192/128` are both intended; if class means are computed after fixed-size
  sampling, the two descriptions agree only through the final explicit macro
  average.
- Freeze whether the negative class at exact zero follows the native reference
  tie rule. The present sign convention does so.
- Decide whether top-three background hard negatives are the simplest adequate
  set or an unnecessary post-census hyperparameter.

### Candidate B

- Freeze lowest-index tie handling for the detached online hard rival.
- Confirm the exact per-row normalization when only one legal action exists;
  such a row should be mechanically excluded or rejected before division.
- Its calibrated residual cancels the background algebraically, while the
  ordering hinge retains it. This is coherent but should be stated explicitly.

### Candidate C

- Define zero as exact generated zero, not a tunable tolerance opened after the
  result.
- Because it omits the detached background, it should remain a diagnostic
  control unless it independently passes the same deployment-aligned gate.

## Finite decision after clean-room review

After reading the Fable report, perform one adjudication only:

1. retain or redesign the R3/ZR target;
2. accept/amend/reject A, B, and C;
3. close the twelve items above in one frozen TRAIN-only contract;
4. implement and run the parallel candidate screen once;
5. select exactly one candidate or stop this fixed R3 learner family.

Do not respond to a failed screen by opening another serial candidate on the
same outcome.
