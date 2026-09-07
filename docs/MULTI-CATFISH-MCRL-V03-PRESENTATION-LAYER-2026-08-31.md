# Multi-Catfish MCRL V0.3 presentation layer

Date: 2026-08-31  
Status: **C1/C3 presentation authority only; C2 V0.7 compression superseded
after R14; replacement C2 pending**  
Scope: authoring only; this document does not delete or relax implementation,
causal-matching, reproducibility, test, or training requirements.

> **Deck hold for C2 (2026-09-02).** The focal-next `motion-one` sentences and
> equations below are retained for provenance but must not be used in a new
> deck or paper figure. The later R14 diagnostic found no held-out Q2 skill
> against the strongest null (`0/3`). Continue using the frozen C1/C3 material;
> label the C2 route `redesign pending` until a replacement passes headroom and
> observability gates.

## 1. One-sentence method

> One matched physical intervention selects one eligible focal user by the
> largest predecision signed-motion opportunity; native legal slots yield
> focal-now, non-focal-now, and focal-next EE-surplus views, and three
> route-local Q estimators feed one service-safe Main action.

This is the complete reader-facing story. C1, C2, and C3 are complementary
views of one EE objective, not three objectives whose raw values must all
increase.

## 2. Main-text scientific core

The paper main text keeps six equation blocks.

### 2.1 One final objective

\[
\eta^N=\frac{\mathcal B}{\mathcal E}.
\]

### 2.2 One matched physical comparison

\[
g_k=\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)].
\]

### 2.3 Three scoped views

\[
\begin{aligned}
\zeta_{1,u}
&=\Delta t[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)],\\
\zeta_{3,u}
&=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)],\\
\zeta_{2,u}
&=\Delta t[R_u^C(1)-R_u^M(1)]
-\lambda_0\Delta t[p_{C,u}(1)-p_{M,u}(1)].
\end{aligned}
\]

For C2, select one eligible focal user by the largest predecision
signed-motion opportunity, breaking ties by the lowest user index. Enumerate
the native 28 legal action slots under the native mask and compare each
candidate with Main at successor slot 1. The branch-indexed focal marginal
power used by C2 is

\[
p_{b,u}(1)=P_b^N(1)-P_{b,-u}^N(1),\qquad b\in\{C,M\}.
\]

Reader labels are fixed:

- C1/Q1: **focal now**;
- C3/Q3: **non-focal now**;
- C2/Q2: **motion-selected focal next slot**.

### 2.4 Scoped accounting identity

The former full-window identity is retired. The C1/C3 opening views and the
focal-next C2 view cover the opening surplus and the focal-attributable part
of the next-slot surplus; any non-focal next-slot remainder is diagnostic
only. This is accounting consistency, not learnability or EE efficacy.

### 2.5 Route-local pairwise learning

The paper may show the full registered loss:

\[
\ell_j=w_j\!\left(
[Q_j(s_u,a_u^C)-Q_j(s_u,a_u^M)-\zeta_{j,u}/\kappa]^2
+\beta Q_j(s_u,a_u^M)^2\right).
\]

The main deck uses only the semantic relation

\[
Q_j(s_u,a_u^C)-Q_j(s_u,a_u^M)\approx\zeta_{j,u}/\kappa.
\]

### 2.6 One deployed action

\[
\Phi_u(t,a)=\sum_{j=1}^{3}Q_j(s_u(t),a),\qquad
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

Only this Main action is executed. There is no auction, coordinator, vote,
joint decoder, or post-training override.

## 3. Three Catfish descriptions for paper and slides

- **C1 — Energy-Frontier:** RIS-lineage EXP/ACRM generates informative
  candidate-versus-Main opening comparisons for the focal user's immediate
  EE surplus.
- **C2 — Focal-Next (motion-one, provisional post-R13 amendment):** select one eligible focal user by predecision
  signed-motion opportunity, enumerate its native 28 legal action slots under
  the native mask, and compare each candidate with Main to estimate focal
  next-slot attributable EE surplus. The earlier D2 preregistration predates
  motion-one and does not validate this amendment.
- **C3 — Spatial-Externality:** lagged load and activation context identifies
  spatially interactive anchors; unilateral opening comparisons estimate the
  focal action's immediate rate effect on non-focal users.

Negative route targets are retained. A negative \(\zeta_{j,u}\) can teach a Q
surface that a candidate is worse than Main; route value is judged by
held-out EE ablation, not by requiring positive target labels.

## 4. Authoring-depth boundary

| Layer | Must show | May omit from that layer |
|---|---|---|
| Paper main text | one objective; matched M/C intervention; three views and identity; one pairwise learner; one deployed action; one sentence per source mechanism | provenance fields, schema fields, key construction, physical-ID encoding, tie-break sequence, checkpoint format, exact state field list, neutral sampler internals |
| Main deck | the six-slide flow in Section 6; compact pairwise relation; summed masked action | full loss weights/gauge, dataset row schema, gate ladder, source digests, C2 source receipts, replay/checkpoint details |
| Appendix/supplement | causal matching and common-randomness protocol; full loss/calibration; source/control construction; reproducibility and claim gates | none of the facts needed to reproduce or audit the experiment |
| Implementation/tests | all canonical checks and complete provenance | nothing is removed merely because it is absent from the paper or slides |

The paper may summarize keyed common randomness as one sentence: candidate
and reference branches use identical exogenous randomness. Key composition,
match counts, and serialization belong in the reproducibility appendix or
artifact documentation.

## 5. C2 selection and scope

At each predecision anchor, select one eligible focal user by the largest
signed-motion opportunity, with the lowest user index as the tie-break. Under
the selected user's native mask, enumerate all 28 legal action slots. Compare
each candidate branch with matched Main and compute only the focal user's
attributable EE surplus at successor slot 1. These rows update Q2 only. This
motion-one rule is provisionally locked after R13; the earlier D2
preregistration predates it and does not validate this amendment.

At deployment, Q2 contributes only to the score of the motion-selected focal
user. The selected user's final action still uses the unweighted Q1+Q2+Q3
score and one native masked argmax; other users do not receive a Q2
contribution.

Presentation compression must not silently change the algorithm.

## 6. Six-slide main-deck arc

1. **One EE objective and one intervention** — \(\eta^N\), matched M/C world,
   one focal action difference.
2. **Three scoped EE views** — focal now, non-focal now, motion-selected focal
   next slot, plus the scoped accounting identity.
3. **Three Catfish source roles** — one short sentence and one visual cue per
   route; no implementation receipts.
4. **Route-local learning** — opening comparisons feed \(Q_1,Q_3\), native
   focal-next comparisons feed \(Q_2\), and each route updates only its Q.
5. **One deployed action** — \(Q_1+Q_2+Q_3\), safety mask, one Main argmax.
6. **Evidence boundary** — formula correctness is not efficacy; show only
   sealed ablation evidence and mark unresolved gates plainly.

Detailed route figures, dataset routing, control construction, and gate
ladders are appendix slides, not required stops in the main narrative.

## 7. Public notation subset

The main text and main deck introduce only the subset required by their
displayed formulas:

\[
\eta^N,\;\mathcal B,\;\mathcal E,\;M,\;C,\;b,\;\lambda_0,\;g_k,\;
\zeta_{1,u},\;\zeta_{2,u},\;\zeta_{3,u},\;p_{b,u},\;Q_j,\;\Phi_u,\;
A_u,\;R_u,\;P^N,\;\Delta t,\;k.
\]

The following are appendix-level unless needed at first use in the full loss
or dataset discussion:

\[
\kappa,\;n_0,\;\widetilde\zeta_{j,u},\;\nu_j,\;w_j,\;\beta,\;
\ell_j,\;D^o,\;D^t,\;D^a,\;s_u,\;a_u^M,\;a_u^C.
\]

Do not add aliases such as \(EE_1\), \(EE_2\), \(EE_3\), \(r_2\), \(r_3\),
\(\delta_j\), or \(\rho_j\). Primary mathematical symbols remain
single-letter with single-letter or numeric indices according to the active
symbol contract.

## 8. Claim ceiling

This compression authorizes explanation and figure/deck production. It does
not authorize a claim that any Catfish or the full method improves EE. The
balanced R13 screen is cited only as development evidence: its provisional
core lock is not formal efficacy. A formal claim still requires longer trend
and held-out matched ratio-of-sums evaluation with the service guard. See
[`MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md`](MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md).
