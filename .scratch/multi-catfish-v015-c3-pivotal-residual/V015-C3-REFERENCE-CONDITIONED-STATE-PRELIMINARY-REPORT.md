# V0.15 C3 reference-conditioned state: preliminary report

Status: preliminary reference pass; not a frozen authority, not a learner
gate, and not a second executed decoder.  No state encoder, source shard,
simulator, TEST split, or training code was changed for this report.

## Why the 287D learner result is not a C3 formula verdict

The ZR target/formula remains unchanged and the source-frontier construction
is mechanically well-defined.  However, the current 287D V0.14 Q3 state does
not tell a focal scorer which physical beams and satellites are occupied by
the other users' *learned Q1+Q2 base decisions*.  A decision-aligned loss
cannot reliably learn a cross-user collision residual when that conditioning
is absent from the input.

The bounded one-lineage exploratory run of the 287D pivotal learner supports
this representation diagnosis, but is not a gate result and is not an EE
claim: after 1000 updates, base/teacher agreement was `0.7877`, learned
student agreement `0.6290`, gain `-0.1587`, recovery `0.1868`, and the
support statistic was `0.2646`.  No production route should be selected from
that run.

## Reference decision and notation

At a predecision anchor, for every user `v` compute the detached background
surface

\[
b_v(a)=Q_{1,v}(a)+\widehat Q_{2,v}(a),
\qquad
c_v=\arg\max_{a\in\mathcal A_v^{safe}} b_v(a).
\]

`c_v` is a context reference only.  It is not a third deployment action and
it is not a coordinator decision.  For focal user `u`, the final action is
still exactly one masked argmax

\[
a_u^*=\arg\max_{a\in\mathcal A_u^{safe}}
       [Q_{1,u}(a)+\widehat Q_{2,u}(a)+Q_{3,u}(s_u,a)].
\]

The proposed C3 state is allowed to condition on the other users' `c_v`
because those references are computed before the final Q3 argmax.  It must
not consume a counterfactual outcome, ZR target, compatibility bit,
evaluator, future trace, or an evolving Q3 action.

For any legal focal candidate `a`, let

\[
\kappa_u(a)=(n_u(a),\ell_u(a))
\]

be its exact `(norad_id, cell_id)` physical beam identity, and let
`\sigma_u(a)=n_u(a)` be its satellite identity.  A reference action `c_v`
whose mask is empty contributes to neither block; in the ordinary source
rows every `c_v` is legal.

## Minimal first-pass state contract: R0 (343D)

Keep all 287 V0.14 ZR-Q3 state coordinates unchanged and append exactly two
28-action-aligned blocks.  The block order is frozen for this preliminary
pass:

1. `reference_same_beam_fraction`;
2. `reference_same_satellite_fraction`.

For `U` users define `d_u=max(U-1,1)`.  The blocks are

\[
\rho^{beam}_{u,a}
 = {1\over d_u}\sum_{v\ne u}
   \mathbf 1\{c_v\ne -1,\ 
   \kappa_v(c_v)=\kappa_u(a)\},
\]

\[
\rho^{sat}_{u,a}
 = {1\over d_u}\sum_{v\ne u}
   \mathbf 1\{c_v\ne -1,\ 
   \sigma_v(c_v)=\sigma_u(a)\}.
\]

Each block is action-aligned: entry `a` describes the physical resource
that focal candidate `a` would use.  Counts are over users, not duplicate
slot entries.  The exact physical key comparison is intentional; comparing
flat action indices would be invalid when per-user slot tables differ.
Both blocks lie in `[0,1]`, use current predecision candidate tables plus
the detached references only, and require no new power or rate surrogate.

The resulting state width is

\[
287+2\times28=343.
\]

This width must not be confused with the existing W160 343D draft.  W160's
two blocks describe legal candidate-table availability; R0's two blocks
describe the physical identities of other users' learned base actions.  They
have different semantics and must have a new schema/digest if implemented.

## Conditional physical burden blocks: R1 (not part of R0)

The following two blocks are useful only if the simulator exposes a canonical
predecision primitive.  They are therefore *not* included in the minimal
first pass and are not to be approximated from a post-action evaluation.

If `\hat p_v(c_v)` is a finite, predecision required-link-power estimate and
`P_*` is a separately frozen positive scale, define the action-aligned
background leader-gap block

\[
\rho^{gap}_{u,a} =
 {\hat p_u(a)-
  \max_{v\ne u:\,\kappa_v(c_v)=\kappa_u(a)}\hat p_v(c_v)
  \over P_*},
\]

using zero for an empty competing set.  The exact scale and clipping rule
would need a new pre-outcome contract; no observed outcome may choose them.

If `\hat d_v(c_v)` is a finite predecision demand/rate-burden primitive,
define

\[
\rho^{load}_{u,a} =
 {1\over d_u}\sum_{v\ne u:\,\kappa_v(c_v)=\kappa_u(a)}
 \hat d_v(c_v).
\]

The load block must use the same unit and a frozen normalization for every
world.  It cannot read a committed/post-step rate, an ActionEvaluation, or a
counterfactual branch.  If either primitive is not available at the exact
predecision boundary, the corresponding block is omitted rather than
silently proxied.  Adding both would produce a 399D state, but that is a
separate R1 proposal, not the current implementation target.

## What this report does and does not conclude

The R0 two-block state is the smallest representation that can expose the
missing cross-user physical occupancy while preserving the existing ActionSet
network and the single final `Q1+Q2+Q3` argmax.  It is a representation
hypothesis, not evidence that C3 will improve trajectory EE.  R0 has not been
implemented or decoded in this pass, so no claim is made about its learnability
or efficacy.

Before implementation, root review should freeze:

* a new state schema/digest and the exact source of `c_v`;
* whether `c_v` is recomputed per focal user or shared from one common
  learned-background surface (the latter is the proposed choice);
* the treatment of empty masks and duplicate physical slot identities;
* the R0 343D architecture/checkpoint boundary and a no-TEST source-only
  representation gate;
* whether R1 power/load blocks are deferred until their predecision data
  primitives are proven.

Until those decisions are frozen, this is only a preliminary reference pass.
It must not be presented as a second executed decoder or used to justify a
long-episode training launch.
