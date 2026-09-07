# Multi-Catfish MCRL V0.7 C2 D2 formula/source preregistration

Date: 2026-09-02  
Status: `PREOUTCOME_DRAFT__DO_NOT_LAUNCH`  
Claim ceiling: `FORMULA_SOURCE_VIABILITY_ONLY__NO_LEARNING__NO_EE_EFFICACY`

## 1. Question

D2 asks whether the V0.7 focal-attributable successor target is mechanically
valid, has useful legal-action variation, and is sufficiently stable across
the three frozen Q1/Q3 lineages to justify a bounded learnability gate.

D2 does not train Q2, open TEST, compare FULL with DROP-C2 on final EE, select a
network initialization, or authorize episode training.

The frozen numeric constants for this gate are

```text
lambda0 = 0x1.443a8f481639ap+26 bit/J
Delta t = 0x1.e147ae147ae14p+4 s
kappa   = 0x1.2cea89d260f2ap+33 bit
IQR     = NumPy linear quantile interpolation
```

Their hexadecimal values and the IQR method must appear in prepare, capture,
shard, adjudicator-input, and result receipts.  A numerically different value
is structural invalidity rather than an alternative sensitivity run.

## 2. Frozen target and policy

For branch \(b\in\{C,M\}\), focal user \(u\), and successor slot 1,

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1),
\]

\[
\zeta_{2,u}(s,a)=
\Delta t\,[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t\,[p_{C,u}(1)-p_{M,u}(1)].
\]

The without-focal evaluation holds every non-focal successor action fixed and
replaces only \(u\)'s action with the physics-only no-op.  Both evaluations are
non-committing.  Signed targets are retained without clipping or sign filtering.

D2 uses one common, frozen Main carrier trajectory before each anchor so the
three lineages see the same physical predecision state.  The carrier's anchor
action is not executed.  At the anchor it is replaced by each lineage's own
bootstrap behavior policy:

\[
a^M=\arg\max_{a\in\mathcal A(s)}[Q_1(s,a)+0+Q_3(s,a)].
\]

There is one common native mask and one argmax.  The resident legacy Q2 must
not be evaluated.  Each candidate branch changes only focal opening action
\(a_u\); both branches then recompute their successor action vectors from
their own successor states using the same frozen bootstrap policy.

This common-carrier construction is limited to D2 formula/rank diagnosis.  It
is not evidence that Q2 learns on its deployment distribution.  D3 must use
the separately frozen on-policy bootstrap-plus-one-refresh schedule.

Q2 alone consumes the 228-dimensional signed-motion observation
`multi-catfish-mcrl-v07-c2-q2-signed-range-rate-state-v1`, whose schema
SHA-256 is
`70cef9bd525ded7df76138364afd31b2e804446b9d199d01ccef845e5a09d2c0`.
Q1 retains the frozen V0.3 state and Q3 retains the V0.4 C3 state.  The Q2
schema name and digest must appear in prepare, capture, shard, and
adjudication receipts; matching dimension alone is insufficient.

## 3. Outcome-blind schedule

Use only physical seeds `2026104001` through `2026104010`.  These seeds are
fresh relative to the opened V0.4, V0.5, and V0.6 source/evaluation blocks.
They become unavailable for D3, D4, confirmation, and TEST after D2 is frozen,
whether selected or not.

For each seed, create exactly two physical anchors:

| Window | Eligible steps | Selection |
|---|---|---|
| early | 1--2 | first chronological step with a user having at least 3 legal actions; choose the lowest such user ID |
| late | 5--6 | first chronological step with a user having at least 3 legal actions; choose the lowest such user ID |

The frozen Main carrier supplies the pre-anchor history for selection.
Eligibility inspects only the predecision step, native mask, and user ID.  It
must not execute a counterfactual or inspect a target, rate, power, service, or
EE result.  The scan receipt contains only the chronological prefix through
the first eligible step.  The chosen anchor action is never executed merely to
inspect a later step in the same window.  A missing window makes D2
structurally invalid; no later step, replacement seed, or replacement user may
be introduced.

The same 20 physical `(seed, step, user)` anchors are evaluated under all three
frozen Q1/Q3 lineages, yielding exactly 60 lineage-decision cells.  Each cell
enumerates every action in its native legal mask exactly once.  No illegal
action or synthetic full mask is added.

## 4. Matched mechanics

For every lineage-decision cell:

1. replay the sealed Main carrier prefix to the anchor under one keyed random
   field;
2. replace the carrier's unexecuted anchor action with the lineage-specific
   direct Q1+0+Q3 reference vector;
3. retain the candidate-equals-reference row as an exact-zero control;
4. replay each other legal focal opening from the same history and CRN root;
5. recompute successor actions separately on candidate and reference branches;
6. evaluate full successor physics without commit;
7. evaluate the same successor vector with only the focal user removed; and
8. persist the two focal rates, four network-power terms, successor action
   digests, native masks, policy digest, CRN digest, and reconstructed target.

Opening action vectors must differ in at most the focal coordinate and in
exactly one coordinate for every non-reference candidate.  The frozen Q1/Q3
bytes must remain unchanged.

## 5. Fixed D2 diagnostics

All quantities below use all 60 cells.  A normalized target means
\(\zeta_{2,u}/\kappa\), so its scale is comparable with Q1+Q3.

### G-M: mechanics and provenance

All conditions must hold:

- 20 physical anchors and 60 lineage-decision cells are present;
- every native legal action appears exactly once per cell;
- all equal-action rows reconstruct bitwise/exact zero;
- all non-reference openings differ only at focal user;
- candidate/reference branches share the declared keyed-field root;
- successor decisions are branch-local;
- all formula raw terms reconstruct their stored target;
- no resident legacy Q2, TEST record, retry, replacement, or outcome-based row
  selection is used.

### G-R: cross-lineage rank stability

For each physical anchor, compute Spearman rank correlation of the complete
legal-action target vectors for each of the three lineage pairs.  Ties use
average ranks.  D2 requires the median of all 60 pairwise correlations to be
at least `0.60`.

### G-S: scale compatibility

For each cell compute

\[
\rho_s=
\frac{\operatorname{sd}_{a\in\mathcal A(s)}[\zeta_{2,u}(s,a)/\kappa]}
{\operatorname{sd}_{a\in\mathcal A(s)}[Q_1(s,a)+Q_3(s,a)]}.
\]

A zero denominator is a failed cell.  The median finite \(\rho_s\) must be at
most `3.0`.

### G-V: target variation

At least 30 of 60 cells must have target IQR at least `0.05 kappa`.

### G-P: positive alternative headroom

For a cell, positive headroom means at least one non-reference legal action
has \(\zeta_{2,u}>0\).  At least 6 of 20 physical anchors must have positive
headroom in at least two of the three lineages.  This gate is necessary
because an all-nonpositive target whose maximum is always the reference action
cannot give C2 an independent deployment role.

## 6. Decision

- `D2_PASS_AUTHORIZE_D3_IMPLEMENTATION` only if G-M, G-R, G-S, G-V, and G-P all
  pass.
- `D2_FAIL_RETURN_TO_C2_FORMULA_OR_SOURCE_DESIGN` if the run is structurally
  valid but any scientific gate fails.
- `D2_INVALID_NO_INFERENCE` for missing cells, provenance failure, runtime
  error, nonfinite data, schedule drift, or any retry/replacement.

No threshold may be weakened after opening a target-bearing row.  Partial
results cannot select a subset, lineage, seed, action, target scale, network,
or new threshold.

## 7. Compute and launch boundary

This is heavy non-GUI matched simulation.  It must run on the Ubuntu server,
not the browser/WSL environment.  Before D2, run exactly one separate
development anchor for wall-time calibration and plumbing only; that anchor
must use a seed outside every evidence block and its target values may not
change this preregistration.

The one completed development calibration is fixed at
`artifacts/multi-catfish-v07-c2-development-calibration-20260902-r1/calibration.json`
with file SHA-256
`a061429c4326934cd33596ae6c89dfc54f8cd043ebe56544340c5a3fa3aa62b5`
and payload SHA-256
`6fc168578c97bd6e6f09013fd7b4167e2b2b34189bb549f23b48ae8025706693`.
It used seed `2026104099` and lineage `q13-a`; it may not be retried or
replaced.

The first formal attempt ID is
`multi-catfish-v07-c2-d2-formal-20260902-r1`.  Its only admissible outputs are
`prepare.json`, `shard-q13-a.json`, `shard-q13-b.json`,
`shard-q13-c.json`, and `adjudication.json` under the identically named
artifact directory.  Each stage atomically writes a `.started.json` marker
before reading target-bearing inputs or executing counterfactuals.  An
existing marker or output forbids a retry, replacement, alternate output
path, or partial rerun under this attempt ID.

Estimated D2 wall time is 1--2 hours after calibration.  D2 is not a 1500-,
3000-, or 9000-episode training run.  No episode training is authorized by
this document, and the user must be notified before any future 9000-episode
launch.
