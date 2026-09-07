# Multi-Catfish MCRL C1/C3 paper-authoring delta

Date: 2026-09-01  
Status: **current paper-facing delta for frozen C1 and C3 only**

This document is the handoff for a later manuscript worker. It carries the
current C1 and C3 method text and the current V0.4 claim boundary into the
paper-authoring path. It does not replace the full authority bundle, change
C2, or authorize a new experiment.

> **PENDING C2 FREEZE — DO NOT CROSS**
>
> C1 and C3 are frozen. C2 is mandatory but unresolved and remains under its
> separate controller-owned formula/mechanism freeze. This delta does not
> rewrite, finalize, remove, or validate C2. The whole Multi-Catfish method is
> therefore **not all confirmed**. Chapter 5 and all results authoring are
> untouched and pending.

## 1. Scope, authority, and manuscript status

Use this delta together with the active symbol table and the current authority
snapshot. The formal V0.3 EE-axis contract remains the source for shared
physical accounting; the V0.4 C3 victim-burden decision supersedes the C3
observation/source only. The V0.4 five-arm result is the current source for
the frozen C1 and five-arm C3 marginal claims. The separate V0.4 C3
confirmatory result is a distinct source for its distinct confirmatory claim.

No actual manuscript source exists in this repository. A read-only inspection
on 2026-09-01 found no manuscript `.tex`, `.docx`, `.odt`, or `.rtf` source;
the Markdown files present here are authority and handoff documents, not a
manuscript. No manuscript was edited, and no PPTX was edited. A later worker
may use this delta as directly insertable Chapter 4 method material, while
leaving Chapter 5 outside this scope.

## 2. Active notation and delta additions

Use the included active symbol-table snapshot at
`docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md` in the accompanying Web-agent
package. Its source snapshot in this checkout was the existing RC copy at
`artifacts/multi-catfish-v04-web-agent-package-20260901-rc/docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md`;
no live root copy was present.
The paper uses one-letter primary symbols and single-letter subscripts or
superscripts. The table below lists the symbols used by this delta; the delta
additions make the V0.4 C3 observation explicit without introducing a second
notation system.

| Symbol | Meaning | Constraint or use |
|---|---|---|
| \(\mathcal U,\mathcal S,\mathcal V\) | user, satellite, and physical-beam index sets | active notation |
| \(u,i,s,v\) | focal user, generic user, satellite, and beam indices | \(i\ne u\) denotes a non-focal user |
| \(\Delta t,H^c,k\) | decision interval, matched counterfactual horizon, and matched-horizon offset | \(k=0,\ldots,H^c-1\) |
| \(R_{u,s,v}(t)\), \(R_u(t)\) | link throughput and selected-link aggregate throughput | bit/s |
| \(P^N(t)\) | canonical network power | W |
| \(\mathcal B,\mathcal E,\eta^N\) | delivered bits, network energy, and ratio-of-sums EE | \(\eta^N=\mathcal B/\mathcal E\) |
| \(\lambda_0\), \(\Delta\mathcal B_k\), \(\Delta\mathcal E_k\), \(g_k\) | frozen TRAIN-only multiplier, matched bit/energy differences, and fixed-multiplier surplus | \(g_k=\Delta\mathcal B_k-\lambda_0\Delta\mathcal E_k\) |
| \(M,C\) | matched reference and unilateral candidate branches | schedules are sealed before outcomes |
| \(\zeta_{1,u},\zeta_{2,u},\zeta_{3,u}\) | C1, C2, and C3 route targets | bit; \(\zeta_2\) remains under the pending C2 freeze |
| \(D^o,D^t,D^a\) | opening, temporal, and held-out identity datasets | \(D^a\) never produces a gradient |
| \(s_u(t)\), \(s_{j,u}(t)\) | active deployed state and route-\(j\) causal view | \(s_{1,u},s_{2,u}\) retain the frozen common view; \(s_{3,u}\) is the V0.4 C3 view |
| \(\mathcal C\) | candidate action-slot set | \(A_u(t)\subseteq\mathcal C\) |
| \(a\), \(a_i(t)\), \(A_u(t)\) | action slot, selected previous action, and legal service-safe action set | \(a\in A_u(t)\subseteq\mathcal C\) |
| \(a_u^C(t),a_u^M(t)\) | matched unilateral candidate and reference actions used by pairwise loss | branch roles \(C/M\) |
| \(b_u(a,t)\) | physical satellite-beam pair named by action \(a\) | existing active-table mapping |
| \(\rho\) | projection from a physical satellite-beam pair to its satellite identity | one-letter function name |
| \(b^{\mathrm b}_{u,a}(t)\) **(delta)** | action-aligned lagged non-focal rate burden on the candidate beam | normalized by \(\Delta t/\kappa\) |
| \(b^{\mathrm s}_{u,a}(t)\) **(delta)** | action-aligned lagged non-focal rate burden on the candidate satellite | normalized by \(\Delta t/\kappa\) |
| \(Q_j\), \(j\in\{1,2,3\}\) | independent route-\(j\) Q surface | normalized EE-surplus output |
| \(\widetilde\zeta_{j,u}\) | normalized route target | \(\widetilde\zeta_{j,u}=\zeta_{j,u}/\kappa\) |
| \(\kappa,\nu_j,w_j,\beta,\ell_j\) | shared positive output scale, route loss-dispersion scale, route loss weight, gauge coefficient, and pairwise loss | \(w_j=1/\nu_j^2\); optimization notation |
| \(\Phi_u(t,a)\), \(a_u^\star(t)\) | summed deployment score and the one executed Main action | one common mask and one argmax |

No other display symbol is needed for the C1/C3 delta. In particular, do not
reintroduce old `r2`/`r3` objectives, the superseded C3 observation/source,
or the retired execution mask notation.

## 3. Shared physical counterfactual

The scientific endpoint is the canonical network ratio of sums:

\[
\eta^N=\frac{\mathcal B}{\mathcal E},\qquad
\mathcal B=\sum_t\sum_{u\in\mathcal U}R_u(t)\Delta t,\qquad
\mathcal E=\sum_tP^N(t)\Delta t.
\]

Before Catfish outcomes are inspected, freeze one TRAIN-only multiplier:

\[
\lambda_0=\frac{\mathcal B_0^M}{\mathcal E_0^M}.
\]

At a matched opening or temporal offset, use the same multi-user physical
world and a branch-independent matched random field:

\[
\Delta\mathcal B_k=\Delta t\sum_{i\in\mathcal U}
 [R_i^C(k)-R_i^M(k)],\qquad
\Delta\mathcal E_k=\Delta t[P_C^N(k)-P_M^N(k)],
\]
\[
g_k=\Delta\mathcal B_k-\lambda_0\Delta\mathcal E_k.
\]

At the opening anchor, candidate \(C\) and reference \(M\) initially differ
only in focal user \(u\)'s physical action. Candidate/reference schedules,
physical IDs, action slots, state schema, multiplier, and random-field
version are bound before outcomes are read. This is one unilateral
counterfactual, not two isolated worlds and not a coordinated action.

## 4. C1/Q1 — focal opening net surplus

### Role and target

C1 assigns the focal user's opening rate change and the complete opening-step
network-energy change to the only mover:

\[
\zeta_{1,u}=\Delta t\,[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t\,[P_C^N(0)-P_M^N(0)].
\]

The energy assignment is causal bookkeeping, not a private per-user power
allocation. Shared activation, interference, load, and power consequences of
the focal action are charged here once.

### RIS EXP/ACRM lineage

C1 retains the RIS lineage as a source-generation and learning mechanism:

1. **EXP** supplies informed source construction and stratification from
   disjoint TRAIN-only dull-rollout experience.
2. **ACRM** supplies the reference-anchored candidate-versus-frozen-Main
   comparison inside the C1 pairwise advantage.

EXP/ACRM does not change the canonical EE endpoint, add a shaped reward, add a
controller, or change the units of \(\zeta_{1,u}\). The lineage authority is
used only for this provenance and for its explicit warning that its
developmental material is not formal efficacy evidence. The current C1
efficacy claim comes from the V0.4 five-arm result below, not from historical
developmental material.

### Source and learning routing

C1 opening rows are generated in the shared opening source \(D^o\). Each row
stores the sealed reference/candidate pair, raw rates and network powers,
\(\zeta_{1,u}\), the common lineage fields, and the source tag. A C1 row
updates only \(Q_1\); it never updates \(Q_3\) merely because both targets
come from the same opening pair. Positive, zero, negative, and all-dark
complete rows are retained.

For V0.4 production, Q1 is the authenticated frozen common-rung-10 C1 head
carried into the three-network candidate. C1 is frozen; do not retrain it to
enlarge the observed effect or to compensate for the unresolved C2 route.

### Current C1 evidence

The current C1 efficacy statement is the exact frozen-policy comparison in
`docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`:

- `FULL` versus `DROP-C1`: **+254.596%** pooled ratio-of-sums EE;
- **3/3** initialization contrasts were positive;
- **30/30** physical-world contrasts were positive;
- the frozen decision is `CONFIRM_C1`.

This is a marginal deployment contribution under the declared five-arm block.
It does not establish that EXP/ACRM alone beats a neutral source, that the
whole three-route policy is better than Main, or that C2 is resolved.

## 5. C3/Q3 — V0.4 non-focal opening rate externality

### Role and target

C3 measures the immediate rate effect of the focal action on every other user.
Its physical target is deliberately rate-only:

\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
 [R_i^C(0)-R_i^M(0)].
\]

C3 is unilateral. It captures non-focal effects induced through shared beam
load, bandwidth sharing, co-channel interference, and shared activation state,
but it does not create or execute a paired or coordinated user action.

### Frozen V0.4 causal observation

For legal action \(a\), the physical beam named by the action is
\(b_u(a,t)\). The V0.4 decision record writes the committed previous-slot
association as \(A_i(t-1)\); using the active symbol-table notation, the
same association is \(b_i(a_i(t-1),t-1)\), where \(a_i(t-1)\) is the previous
committed action. The two action-aligned victim burdens are:

\[
b^{\mathrm b}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\in\mathcal U\setminus\{u\}\\
 b_i(a_i(t-1),t-1)=b_u(a,t)}}R_i(t-1),
\]

\[
b^{\mathrm s}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\in\mathcal U\setminus\{u\}\\
 \rho(b_i(a_i(t-1),t-1))=\rho(b_u(a,t))}}R_i(t-1).
\]

The focal user's own previous rate is excluded. Here \(\rho\) is the
unindexed physical-pair-to-satellite projection used by the V0.4 decision;
it is distinct from any indexed service-satellite notation elsewhere in the
active table. Both blocks are computed only from committed previous-slot
associations and served rates. They do not read
current joint actions, call a candidate evaluator, inspect a target, or run a
proposal pass. The blocks replace the superseded C3-specific eligible-load
and binary satellite-active observation blocks.

The frozen V0.4 decision retains state width 228 and the local C3 scorer
shape `12 -> 100 -> 50 -> 50 -> 1`. These are method/configuration facts, not
an additional efficacy claim. Q1 and Q2 retain their frozen common view; Q3
receives the V0.4 victim-burden view.

### V0.4 source-generation semantics

The informed C3 source is selected from pre-outcome, lagged metadata. Focal
users are ranked first by absolute beam-burden contrast and then by beam victim
pressure; satellite contrast and satellite pressure are stable auxiliary
tie-breaks, not equal-weight causal terms. The source enumerates unilateral
legal opening actions at sealed anchors and retains the observed target sign;
it does not filter rows by \(\zeta_{3,u}\) magnitude or sign.

The sealed production source uses four TRAIN seeds, three validation seeds,
and zero TEST seeds. It caps emitted siblings at four per focal-state context
and selected contexts at eight per physical anchor, requires a connected
28-action TRAIN graph, and admits validation only on directed action pairs
already supported by TRAIN. Reference and candidate physical keys are
persisted across the source boundaries. These rules describe source lineage;
they do not open a TEST split or constitute Chapter 5 results.

Each C3 row is stored once in \(D^o\) with \(\zeta_{3,u}\) and its common
opening lineage. A C3 row updates only \(Q_3\). The current V0.4 Q3 is the
fresh local victim-burden head selected by the sealed validation decision; C3 is frozen for
paper purposes.

### Why C3 has no energy term

There is no energy term in \(\zeta_{3,u}\) by design. At \(k=0\), the focal
action is the sole intervention, so the complete shared opening energy change
already belongs to C1. Adding
\(-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)]\) again to C3 would count the same
physical energy twice. The C3 target is therefore invariant to the choice of
\(\lambda_0\), while C1 carries the opening energy exactly once. This is
non-overlap bookkeeping, not an assertion that C3 has no physical effect on
energy in the world.

### Current C3 evidence

Keep the following two current claims separate and cite each to its exact
source:

1. The V0.4 five-arm frozen-policy result at
   `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`
   reports `FULL` versus `DROP-C3` of **+21.970%**, with **2/3** positive
   initialization contrasts and **30/30** positive physical-world contrasts.
2. The separate V0.4 confirmatory result at
   `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md`
   reports `FULL` versus `DROP-C3` of **+21.216%**, with all 30 physical-world
   contrasts positive, two of three initialization contrasts positive, and
   the frozen decision `CONFIRM_C3`.

These are different frozen-policy blocks and must not be averaged, added, or
described as one number. The confirmatory block did not open TEST and did not
authorize additional Q3 updates or long training.

## 6. Non-overlap bookkeeping and data boundaries

For one matched horizon, the three route views obey the accounting identity

\[
\zeta_{1,u}+\zeta_{3,u}+\zeta_{2,u}
=\sum_{k=0}^{H^c-1}g_k.
\]

The opening offset is partitioned as follows:

- C1 receives the focal opening rate difference and all opening network-energy
  difference.
- C3 receives only the non-focal opening rate difference.
- Every later-offset remainder belongs to the separate \(\zeta_{2,u}\) route,
  whose formula/mechanism remains under the pending C2 freeze.

The identity proves non-overlapping accounting only. It does not prove
learnability, route-level efficacy, or full-method efficacy. \(D^o\) stores
the opening C1 and C3 targets once; \(D^t\) remains reserved for the pending
C2 route; held-out \(D^a\) is evaluation/identity-only and never sends a
gradient. No outcome-triggered refresh or sign-based row deletion is allowed.

## 7. Pairwise training and one deployed Main action

There are exactly three independent Q networks, one per required route. A
route-\(j\) pair uses one shared output scale:

\[
\widetilde\zeta_{j,u}=\frac{\zeta_{j,u}}{\kappa},\qquad
\ell_j=w_j\left(
 [Q_j(s_{j,u}(t),a_u^C(t))-Q_j(s_{j,u}(t),a_u^M(t))
 -\widetilde\zeta_{j,u}]^2
 +\beta Q_j(s_{j,u}(t),a_u^M(t))^2\right).
\]

The C1 opening row routes only to \(Q_1\), and the C3 opening row routes only
to \(Q_3\). The pairwise learner is zero-bootstrap: no Bellman target, target
network, cross-route gradient, redundant sum loss, or legacy checkpoint is
introduced by this delta. Loss weights affect optimization only; deployment
weights remain one.

Deployment remains exactly three Q outputs summed under one common legal and
service-safe mask:

\[
\Phi_u(t,a)=Q_1(s_{1,u}(t),a)+Q_2(s_{2,u}(t),a)+Q_3(s_{3,u}(t),a),
\]
\[
a_u^\star(t)=\arg\max_{a\in A_u(t)}\Phi_u(t,a).
\]

Only this one Main action executes. There is no auction, coordinator, vote,
learned gate, second argmax, joint decoder, or post-training override. C1 and
C3 are summands in the one deployed score, not two extra actors; Q2 remains a
required but unresolved route and cannot be silently removed or replaced in
this paper delta.

## 8. Allowed and forbidden paper language

### Allowed now

- “C1/Q1 is the focal opening net-surplus route and retains RIS EXP/ACRM
  lineage as an experience-generation mechanism.”
- “C3/Q3 is the V0.4 non-focal opening rate-externality route, using lagged
  action-aligned beam and satellite victim-rate burdens.”
- “The C1 and C3 targets are non-overlapping views of one matched physical
  intervention; opening energy is assigned to C1 and is not duplicated in C3.”
- “The V0.4 five-arm frozen-policy result confirms the C1 marginal comparison
  at +254.596% (3/3 initializations, 30/30 worlds), as reported in its exact
  result authority.”
- “The V0.4 five-arm frozen-policy result reports the C3 marginal comparison
  at +21.970% (2/3 initializations, 30/30 worlds), as reported in its exact
  result authority.”
- “The separate V0.4 C3 confirmatory block reports +21.216%; this is a distinct
  result and is not merged with the five-arm value.”
- “Deployment sums exactly three independent Q networks, applies one common
  service-safe mask, performs one argmax, and executes one Main action.”

### Forbidden

- Saying that the whole three-Catfish method is finalized, all routes are
  confirmed, or `FULL` improves the frozen Main baseline.
- Calling C2 confirmed, finalized, optional, removable, or replaced by this
  C1/C3 delta. C2 is mandatory and unresolved.
- Presenting the five-arm C3 value and the separate confirmatory C3 value as a
  pooled, averaged, or single headline number.
- Treating the superseded V0.3 C3 observation/source as current, or adding an
  energy term to the frozen V0.4 C3 target.
- Treating EXP/ACRM lineage, source rows, positive target values, or the
  accounting identity as proof of learned EE efficacy beyond the named
  frozen-policy comparisons.
- Claiming a TEST result, a 1500/3000/9000 run, a long-training result, or a
  completed Chapter 5 narrative.
- Adding an auction, coordinator, vote, learned gate, joint action decoder,
  or post-training override to deployment.

## 9. Chapter 5 and handoff boundary

Chapter 5 is **untouched**. This delta does not supply a Chapter 5 result
narrative, curves, confidence intervals beyond the exact cited result
authorities, or any new training claim. The later manuscript worker should
insert the C1/C3 method paragraphs and exact, separately cited current result
sentences, then leave all C2, whole-method, long-training, and Chapter 5
fields pending until their own authority exists.

The paper-facing source chain for this delta is:

- `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`;
- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`;
- `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md`;
- `docs/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md`;
- `docs/MULTI-CATFISH-MCRL-V04-C3-VICTIM-BURDEN-DECISION-2026-09-01.md`;
- `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md`; and
- `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md`.

The C1 lineage README is provenance-only. It does not supersede the current
V0.4 C1 result, and no historical C1 efficacy artifact is part of the new
reader package.
