# Opus Max active co-design record: Multi-Catfish MCRL V0.3

Date: 2026-08-31  
Role: active redesign participant, not final acceptance reviewer

Current-status note: keyed branch-independent fading and the fixed-hold C2
gate were subsequently implemented. The sealed gate is `INDETERMINATE`; the
post-gate hold-while-legal release amendment supersedes this record's old
implementation-status paragraph, while the decomposition below remains
binding.

## Decision

Opus Max selected the fixed-global-multiplier structure but replaced the V0.2
isolated-world split with a same-system focal/non-focal/horizon split:

\[
\zeta_{1,u}=\Delta t[R_u^C(0)-R_u^M(0)]
-\lambda_0\Delta t[P_C^N(0)-P_M^N(0)],
\]
\[
\zeta_{3,u}=\Delta t\sum_{i\in\mathcal U\setminus\{u\}}
[R_i^C(0)-R_i^M(0)],
\]
\[
\zeta_{2,u}=\sum_{k=1}^{H^c-1}
\left\{\Delta t\sum_{i\in\mathcal U}[R_i^C(k)-R_i^M(k)]
-\lambda_0\Delta t[P_C^N(k)-P_M^N(k)]\right\}.
\]

The principal reason was causal and numerical: the isolated evaluator changed
bandwidth, load, interference, beam activation, and marginal power. Its legacy
schema fields `z1` and residual `z3` therefore mixed physical-world differences and encouraged
two large, anticorrelated values to cancel at deployment.

## Adopted design changes

- one TRAIN-only frozen
  \(\lambda_0=\mathcal B_0^M/\mathcal E_0^M\) across every arm and window;
- remove isolated evaluation from the target path;
- assign all opening-step energy delta to the focal intervention;
- define C3 as non-focal immediate rate externality, hence invariant to
  \(\lambda_0\);
- define C2 as every full-system offset after zero, including release offset;
- use one shared output scale \(\kappa\), not per-head output rescaling;
- use pairwise zero-bootstrap advantage regression first;
- add a reference-action gauge penalty and remove redundant sum loss;
- replace the old per-head Bellman maxima rather than mixing estimators;
- require explicit Q2 segment history and lagged Q3 load/activation/max-power
  observations;
- keep potential/value-tail shaping only as an optional second-stage truncation
  correction for C2, not as the C2 definition.

## Evidence and limits

Opus inspected the environment energy/load implementation, state encoder,
MODQN targets, and C2 fork adapters. Its local read-only sample reported that
shared load and marginal beam-power effects occur often enough to justify a C3
census, but those measurements were exploratory and are not accepted efficacy
evidence.

The review also identified a decisive C2 limitation: current twins disable
fading. Removing that flag alone is insufficient because sequential RNG draws
may desynchronize after branch divergence. A canonical-fading,
branch-independent keyed common-random field is required before C2 target
distributions can support a scientific viability claim.

The governing design is the V0.3 contract. This record explains why V0.2 was
superseded; it does not independently authorize training.
