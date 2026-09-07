# Multi-Catfish MCRL V0.4 C3 victim-burden decision

Date: 2026-09-01  
Status: **binding redesign decision; bounded implementation fixes in progress; fresh validation pending**  
Claim ceiling: **design rationale only; no TEST or EE efficacy claim**

## Decision

The sealed V0.3 masked mean/max fallback ended with
`STOP_MASKED_MEANMAX_VALIDATION`.  V0.3 receives no further scorer, fallback,
seed, rung, or null-baseline search.

The required three-Catfish topology remains binding.  V0.4 therefore retains
C1, C2, and C3, but replaces the insufficient C3 observation/source with one
lagged victim-rate-burden mechanism.  C1 and C2 formulas, source roles, and
learners are not redesigned.

## Why V0.3 stopped

At the selected common rung, the sole fallback produced:

| Route | Mean skill over strongest state-independent null | Positive initializations |
|---|---:|---:|
| C1 | 0.1493017 | 3/3 |
| C2 | 0.0198745 | 3/3 |
| C3 | -0.0006840 | 1/3 |

The collision, action-main-effect, and C2 anchor-sensitivity gates passed.
C3 nevertheless remained negative at every evaluated rung; wider masked
mean/max context increased the Q3 input from 12 to 28 and the per-head
parameter count from 8,951 to 10,551 without fixing it.  This rejects another
capacity/context-family fallback.

The physical C3 opportunity was not rejected.  The earlier formula-first
census observed positive C3 action headroom at 15/20 anchors, and every one of
the 1,862 fresh C3 comparisons has nonzero target magnitude.  The failure is
instead an observation mismatch: each Q3 comparison stores the focal user's
state, while its target sums rate changes over all non-focal users.

A read-only census over the sealed rows found that the target correlates with
the contemporaneous non-focal reference beam-rate burden by approximately
-0.519 on TRAIN and -0.554 on validation.  Candidate/reference satellite
unions contain 95.74% of absolute non-focal rate change, while the current
previous-demand and added eligible-load blocks are identical on all 1,862
rows.  V0.3 therefore supplies redundant counts and binary activation where
Q3 needs rate-weighted victim context.

## V0.4 C3 observation

The physical target is unchanged:

\[
\zeta_{3,u}(t)=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
\left[R_i^C(t)-R_i^M(t)\right].
\]

For legal action (a), define the two causal action-aligned burdens

\[
b^{\mathrm{b}}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\ne u\\A_i(t-1)=b_u(a,t)}}R_i(t-1),
\]

\[
b^{\mathrm{s}}_{u,a}(t)=\frac{\Delta t}{\kappa}
\sum_{\substack{i\ne u\\\rho(A_i(t-1))=\rho(b_u(a,t))}}R_i(t-1).
\]

Here (b_u(a,t)) is the physical beam named by action (a),
(A_i(t-1)) and (R_i(t-1)) are committed previous-slot association and
served rate, and \(\rho(\cdot)\) returns the satellite identity.  The focal
user's own previous rate is excluded.

The two blocks replace the C3-specific `eligible_served_load` and binary
`satellite_active` blocks.  State width remains 228 and the scalar scorer
remains `12 -> 100 -> 50 -> 50 -> 1`.  The blocks are computed from committed
state only.  They may not read current joint actions, call a candidate
evaluator, inspect a target, or introduce a proposal pass.

Q3 uses this fresh local scorer.  Q1 and Q2 do not switch architecture: V0.4
carries forward their independent heads from the sealed V0.3 masked-mean/max
common-rung-10 checkpoints.  Thus the production policy contains exactly
three networks total--one frozen masked-mean/max Q1, one frozen
masked-mean/max Q2, and one trainable local Q3--rather than two three-head
trainers.  All three output the same normalized EE-surplus unit.

Deployment remains exactly

\[
\Phi_u(t,a)=Q_1(s_{1,u}(t),a)+Q_2(s_{2,u}(t),a)+Q_3(s_{3,u}(t),a),
\qquad
a_u^*(t)=\arg\max_{a\in\mathcal A_u^{\mathrm{safe}}(t)}\Phi_u(t,a).
\]

Here \(s_{1,u}=s_{2,u}=s^{\rm v03}_u\), while
\(s_{3,u}=s^{\rm v04}_u\).  Both views are computed from the same sealed
predecision anchor.  Q1/Q2 therefore retain their frozen mean/max input
semantics and parameters; only Q3 observes the new victim burdens and receives
V0.4 gradient.  The three values are summed directly without learned route
weights.

There is no auction, coordinator, joint decoder, vote, second argmax, or
post-training override.

## V0.4 C3 source

The new informed source is selected before outcomes.  Focal users are ranked
by absolute beam-burden contrast and then beam victim pressure; satellite
contrast and pressure remain auxiliary stable tie-breaks, not equal-weight
rank terms.  The source caps emitted
siblings at four per focal-state context and selected contexts at eight per
physical anchor, spans beam-burden contrast and action identity, retains every
observed target sign, and preserves a connected 28-action TRAIN graph with no
unsupported validation pair.

The fresh source has four TRAIN seeds, three validation seeds, zero TEST
seeds, and maximum row budgets of 1,052 TRAIN and 810 validation comparisons.
The sibling cap therefore requires at least 263 and 203 distinct focal-state
contexts respectively, instead of V0.3's 40 and 30.

The fresh source seeds are `2026092301`--`2026092304` for TRAIN and
`2026092305`--`2026092307` for validation.  No V0.4 TEST source is generated.
The schedule is frozen from pre-outcome burden/action metadata, requires one
connected 28-action TRAIN graph, and admits validation only on directed action
pairs already supported by TRAIN.  Materialized rows are never filtered by
the sign or magnitude of \(\zeta_3\).  Reference and candidate physical keys
are persisted and independently recomputed across schedule, materialization,
dataset, and receipt boundaries.

## Single promotion rule

V0.4 gets one fresh stronger-null learnability gate with the already frozen
three initialization seeds and rung family.  The fresh gate applies only to
Q3: its anchor-then-seed-balanced mean skill must be positive and at least 2/3
initializations must be positive.  The sealed V0.3 Q1/Q2 results remain fixed
at rung 10 and are authenticated rather than reselected.  V0.4 has no second
architecture, source, seed, or rung fallback.

- Failure: `STOP_V04_C3`; do not open TEST or EE evaluation.
- Success: authorize one bounded matched screen only.  Evaluate the sealed
  gate-selected Q3 rung first (`screen_updates_completed = 0`), then retain
  100/200/300/400/500 additional full-batch Q3 updates only as explicitly
  labelled training-trend checkpoints.  These counts are source-training
  epochs, not simulator episodes.

Even a positive learnability gate does not prove EE improvement.  C3's
independent effect requires the later matched canonical-EE/service comparison
of `Q1+Q2+Q3` against `Q1+Q2`, with all other budgets fixed.
The ablation must reuse bit-identical Q1/Q2 heads and surfaces in both arms.
This is the only experiment that can establish positive marginal C3 effect on
the final ratio-of-sums EE; positive targets or held-out Q3 skill alone cannot.
For V0.4 C3 this marginal FULL-versus-drop-C3 comparison, together with the
zero-loss service guard, is the route-survival criterion.  The older generic
informed-versus-neutral-source criterion is superseded for this route only;
V0.4 does not claim that informed C3 source curation beats a neutral source.
