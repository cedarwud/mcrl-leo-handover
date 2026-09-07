# Multi-Catfish V0.20 C3 parallel candidate screen

Date: 2026-09-04  
Status: **NON-AUTHORITY DESIGN DRAFT / NO LEARNER RUN / NO NEW OUTCOME**

This draft converts the V0.19 failure into one bounded, parallel TRAIN-only
development screen.  It does not change R3/ZR, authorize a fresh source panel,
or authorize episode training.  The external Fable clean-room review may still
reject or amend this draft before implementation is frozen.

## 1. Fixed scientific boundary

For row \(n\) and legal action \(a\), define the detached background, exact
normalized ZR residual, and learned residual as

\[
b_{na}=Q_{1,n}(a)+Q_{2,n}(a),\qquad
y_{na}=z_{3,n}(a)/\kappa,\qquad
q_{na}=Q_3(s_n,a).
\]

The reference is \(r_n=\arg\max_a b_{na}\), and both \(y_{nr_n}\) and
\(q_{nr_n}\) are structurally zero.  Define exact and student decision
margins relative to the background reference:

\[
m^T_{na}=b_{na}+y_{na}-b_{nr_n},\qquad
m^S_{na}=b_{na}+q_{na}-b_{nr_n}.
\]

The deployed action remains exactly

\[
\arg\max_{a\in\mathcal A_n^{\rm safe}}(b_{na}+q_{na}).
\]

The frozen \(b\) surface is allowed only as a detached training label/loss
context.  It is not a Q3 state input and receives no gradient.  Each candidate
still produces one normalized `(N,28)` Q3 surface; there is no threshold,
support classifier, second decoder, gate, coordinator, or fallback at
deployment.

All candidates reuse the V0.19 relational action/victim state, native mask,
predecision compatibility bit, exact centred ZR label, one shared \(\kappa\),
network architecture, Adam `lr=0.001`, and structural reference centring.

## 2. Why another uniform surface loss is not sufficient

The opened-TRAIN census covers twelve shards and no VALIDATION/TEST rows:

- 1,882/12,000 rows (15.683%) are teacher-pivotal;
- the teacher action is positive and compatible on all 1,882 pivotal rows;
- only 3.646% of 306,486 legal non-reference cells are positive;
- the highest-background compatible candidate identifies the teacher on
  75.292% of pivotal rows;
- choosing that candidate unconditionally has only 44.400% positive support;
- its true decision margin has median `-0.35975` and p95 `+0.50041`.

Thus the main task is to learn whether the ZR gain crosses the frozen
background gap.  A low average surface MSE can miss precisely this boundary.

## 3. Candidate A: class-balanced exact decision margins (primary)

Partition legal non-reference cells using the exact decision margin:

\[
W=\{(n,a):m^T_{na}>0\},
\]

\[
H=\{(n,a):m^T_{na}\le0,\ a\text{ is among the three largest legal }b_{na}\},
\]

and let \(R\) be the remaining legal non-reference cells.  Ties use native
action order.  Let \(\sigma_{na}=+1\) when the exact margin is positive and
\(-1\) otherwise.  With Smooth-L1 \(h_{0.25}\), define an exact calibration
term and a zero-margin ordering violation:

\[
e_{na}=h_{0.25}(m^S_{na}-m^T_{na})
+\left[\max(0,-\sigma_{na}m^S_{na})\right]^2.
\]

The ordering term is zero at the exact target; it does not introduce a tuned
margin or change output units.  The loss is

\[
L_A={1\over3}\left[
\operatorname{mean}_{W}e+
\operatorname{mean}_{H}e+
\operatorname{mean}_{R}e
\right].
\]

Each update samples 192 cells from \(W\), 192 from \(H\), and 128 from
\(R\), with deterministic within-stratum replacement when required.  This is
still calibrated regression in the common EE-surplus unit; only the sampling
measure is changed to match the deployed decision boundary.  Unlike pure
surface regression, the second term directly evaluates the actual detached
background plus Q3 decision margin.

This differs from V0.15/V0.16 because it trains all winning cells plus explicit
background hard negatives, rather than one pivotal `(base, teacher)` pair and
an uncalibrated zero-margin stability hinge.  It also uses the relational
state rather than B402.

## 4. Candidate B: balanced full-action hard-negative margins

Let

\[
t_n=\arg\max_a(b_{na}+y_{na}),
\qquad p_n=\mathbf1\{t_n\ne r_n\}.
\]

For student scores \(s_{na}=b_{na}+q_{na}\), define exact and learned margins
from the teacher winner to every rival:

\[
\Delta^T_{na}=(b_{nt_n}+y_{nt_n})-(b_{na}+y_{na}),
\qquad
\Delta^S_{na}=s_{nt_n}-s_{na}.
\]

Choose the current hardest rival by detached student margin,

\[
h_n=\arg\min_{a\ne t_n}\operatorname{stopgrad}(\Delta^S_{na}),
\]

and use the exact calibrated, zero-margin-safe error

\[
e_{na}=h_{0.25}(\Delta^S_{na}-\Delta^T_{na})
+[\max(0,-\Delta^S_{na})]^2.
\]

For one row,

\[
c_n={1\over2}e_{nh_n}
+{1\over2(|\mathcal A_n^{\rm safe}|-1)}
\sum_{a\ne t_n}e_{na}.
\]

The loss balances pivotal and stable rows rather than their natural
15.7/84.3 mixture:

\[
L_B={1\over2}\left[
\operatorname{mean}_{p=1}c+
\operatorname{mean}_{p=0}c
\right].
\]

Each update contains 256 pivotal and 256 stable rows, deterministically sampled
with replacement.  The exact margin calibration prevents an arbitrary
classifier-logit scale from entering the unweighted Q sum.

This is not the V0.17 soft-KL learner: it uses the relational state, no teacher
probability distribution or temperature, explicit pivotal/stable macro
balancing, an online hard rival, and exact full-score margin calibration.

## 5. Candidate C: sign-stratified surface calibration (control)

Partition legal non-reference cells into positive \(P\), negative \(N\), and
zero \(Z\) exact ZR targets.  Use

\[
L_C={1\over3}\left[
\operatorname{mean}_{P}h_{0.25}(q-y)+
\operatorname{mean}_{N}h_{0.25}(q-y)+
\operatorname{mean}_{Z}h_{0.25}(q-y)
\right],
\]

with 256/128/128 deterministic samples per update.  Candidate C contains no
background-aware ranking term.  It is retained as a control to distinguish
plain target-imbalance failure from a genuinely decision-context-dependent
failure.  It is not the V0.14 hurdle model: there is one scalar Q3 output, no
classifier, posterior correction, mixture, or inference threshold.

## 6. TRAIN-only leave-one-world-out screen

No V0.19 VALIDATION row may enter model selection.  For each of the three
frozen lineages, rotate each of the four already-opened TRAIN worlds as the
complete holdout world; train on the other three.  Each candidate/fold runs
exactly 100 updates and writes immutable checkpoints at updates `10`, `30`,
and `100`.  Candidate, fold, and initialization jobs may run in parallel and
share no optimizer.

The same mechanical checks apply to every candidate:

- TRAIN split only; no environment/simulator import or source write;
- exact source/context row identity;
- finite loss, gradients, parameters, and predictions;
- one division by \(\kappa\);
- reference Q3 bitwise zero and illegal Q3 exactly zero;
- frozen Q1/Q2 bytes unchanged;
- deterministic batch schedule and rerun digest;
- one Q3 state dict and one optimizer only.

For held-out TRAIN worlds, record:

- teacher-pivotal agreement;
- stable background preservation;
- action-change exposure;
- fraction of student changes with `pcc=true` and `y>0`;
- positive decision-margin recall;
- exact-margin MAE on \(W/H/R\);
- output/target dispersion and strongest fixed null.

An arm remains eligible for a later fresh gate only if:

1. all three lineages have nonzero action-change exposure;
2. pooled pivotal agreement is at least `0.50`, and at least two lineages have
   mean pivotal agreement at least `0.45` across folds;
3. pooled stable preservation is at least `0.98`, with no lineage below
   `0.95`;
4. pooled positive-compatible precision among student changes is at least
   `0.80`, with no lineage at or below `0.50`;
5. pooled positive decision-margin recall is at least `0.25`;
6. its teacher-agreement skill is strictly above the strongest frozen null.

These are development selection rules, not efficacy claims.  If multiple arms
are eligible, rank by minimum-lineage pivotal agreement, then pooled stable
preservation, then lower loss complexity in the order `A`, `C`, `B`.  Freeze
exactly one primary before any fresh source outcome.  If no arm is eligible,
stop the fixed relational-ZR learner family; do not open another serial fresh
panel.

## 7. Next gate, conditional only

One eligible primary would justify a separately preregistered shared fresh
TRAIN source gate with three initializations.  Only that fresh learned-Q3 gate
can authorize the already prepared 100-episode five-arm trajectory screen.
Neither this draft nor its opened-TRAIN screen authorizes 100, 500, 1500,
3000, or 9000 episode policy training.
