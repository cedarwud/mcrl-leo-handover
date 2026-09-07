# V0.18 relational-ZR C3 design seam

Status: DRAFT DESIGN NOTE, NOT AUTHORITY, NOT A PREREGISTRATION.

This note exists to choose one post-V0.17 design seam before implementation.
It does not authorize source generation, learner training, episode training, or
TEST access.

## One checkable completion criterion

This design step is complete only when one immutable predecision observation
interface, its allowed and forbidden inputs, an exact causal-compatibility proof
gate, a victim-relational Q3 scorer, and one executable pre-outcome decision rule
are specified without claiming that hidden realised physics is observable.

## Frozen evidence boundary

- The V0.13 exact ZR teacher has positive TRAIN oracle evidence in the integrated
  Q1+exact-Q2 context. This is not learned-head or episode-efficacy evidence.
- V0.17 rejects the B402 action-set MLP with SoftKL in all three frozen
  initialisations. Its stop rule closes loss tuning, seed/rung selection,
  threshold changes, rescaling, clipping, support masking, and further B402
  feature expansion.
- V0.17 does not reject the ZR target. It rejects the tested representation and
  learner family.
- Q1 and the learned OPS-3 Q2 stay frozen while this C3 seam is examined.
- Deployment must remain one native-safe masked argmax of Q1+Q2+Q3. A detached
  preliminary Q1+Q2 reference is a non-executed context pass, not a coordinator
  or second action decoder.

## Selected deep module

The proposed module owns the conversion from current physical predecision state
and a detached base-head reference into a permutation-safe relational C3
observation. Callers do not construct victim tensors, nominal interference
features, or compatibility headrooms themselves.

```text
encode_relational_zr_c3_state(
    environment,
    observation,
    reference_actions,
    required_power_surface,
    opening_feasibility_surface,
) -> RelationalZRC3Observation
```

The return value is immutable and contains:

```text
RelationalZRC3Observation
    action_context    [U, A, 7]
    victim_tokens     [U, A, Umax, 6]
    action_mask       [U, A]
    victim_mask       [U, A, Umax]
    positive_credit_compatible [U, A]
    reference_actions [U]
    schema_version
    content_digest
```

Here `A=28` under the current action contract. The public seam should not expose
internal peer-count maps, beam-power maps, or nominal interference-field
construction. `reference_actions` and `positive_credit_compatible` are detached
formula/context metadata; neither is an input feature to the learned victim
scorer. Physical relations are computed from `(norad_id, cell_id)`, never from
equality of flat action indices.

## Information boundary

Allowed inputs are current, predecision, and causally available:

- native safe action mask and physical action keys;
- current geometry and candidate mapping;
- detached Q1+Q2 reference actions, computed before Q3;
- opening-service feasibility and recurrence-power surfaces derived without
  realised action evaluation;
- current observation SINR as an explicitly noisy proxy;
- nominal link and interference coefficients evaluated with fading=1 and
  shadowing=0;
- peer counts, peer maximum required power, and load changes derived from the
  detached reference.

Forbidden inputs are:

- `ActionEvaluation` or any reference/candidate realised outcome;
- realised rate, SINR, interference, energy, beam-power signature, or service
  signature;
- the keyed `"physics"` fading/shadow field;
- future trace information;
- the ZR teacher action, target, or post-evaluation compatibility label;
- an RNG handle in the observation encoder.

Exact victim deltas are not predecision-observable because observation and
physics use distinct keyed random fields. The learner therefore estimates the
conditional expected victim effect, not the realised oracle delta.

## Frozen feature semantics

For legal focal candidate `a`, the seven action-context values are

```text
[service_headroom(c[u]),
 service_headroom(a),
 1{b0 == ba},
 N[-u,b0] / U,
 N[-u,ba] / U,
 (M[-u,b0] - p0) / Pmax,
 (M[-u,ba] - pa) / Pmax].
```

`service_headroom(x)` is `(Pmax-p[x])/Pmax` when the action is opening-
feasible and `-1` otherwise. Counts and maxima include only non-focal users
whose detached reference is present and opening-feasible. A null origin has
zero count/max and the explicit infeasible headroom. Illegal focal entries are
zeroed after the native action mask is stored separately.

For each masked victim the six tokens are

```text
[log1p(observed_candidate_sinr[v,c[v]]),
 n0[v] / U,
 (na[u,a,v] - n0[v]) / U,
 log1p(Sbar[v] / N0),
 log1p(Ibar0[v] / N0),
 asinh(delta_Ibar[u,a,v] / N0)].
```

`n0` and `na` are reference/candidate beam loads. `Sbar`, `Ibar0`, and
`delta_Ibar` come only from the deterministic nominal physical field. Tokens
are stored as finite float64 values for the diagnostic; a later learner adapter
may cast its own immutable copy to float32 under a separate contract.

## Formula-aligned relational scorer

For focal user `u`, legal candidate `a`, and non-focal victim `v`, a shared
scorer estimates

```text
d_hat[u,a,v] = f_theta(victim_tokens[u,a,v], action_context[u,a]).
```

Let `g[u,a]` be causal compatibility reconstructed before float32 feature
projection from the exact predecision opening, physical-key, and float64
required-power surfaces. It is persisted as `positive_credit_compatible`, not
supplied from an oracle evaluation, and never acts as a second action mask.

For focal user `u`, let its reference and candidate opening bits, physical beam
keys, and required powers be `(e0,b0,p0)` and `(ea,ba,pa)`. A legal action has a
physical key even when its opening bit is false; an all-empty reference
`c[u] == -1` instead uses the explicit null sentinel `b0 = bottom`, `e0 = false`,
and `p0 = 0`. For each physical beam `b`, define the non-focal reference maximum

```text
M[-u,b] = max({p[v,c[v]] : v != u, c[v] != -1,
                                e[v,c[v]], b[v,c[v]] == b}, default=0).
```

Compatibility is reconstructed by these exact branches:

```text
if e0 != ea:
    g = false
elif not e0:                       # both focal branches are unserved
    g = true
else:
    B0 = keys(M[-u,*] > 0) union {b0}
    Ba = keys(M[-u,*] > 0) union {ba}
    P0[b] = max(M[-u,b], p0 if b == b0 else 0)
    Pa[b] = max(M[-u,b], pa if b == ba else 0)
    g = (sorted(B0) == sorted(Ba)
         and float64_bytes([P0[b] for b in sorted(B0)])
             == float64_bytes([Pa[b] for b in sorted(Ba)]))
```

This explicitly covers identical physical keys and the both-unserved case.
Equal canonical beam keys and beam-power bytes imply equal active-satellite sets
and equal canonical network power under the frozen simulator equations. The
gate must nevertheless compare every reconstructed component with the live
oracle component receipts; implication is not accepted without the mechanical
proof.

Aggregate

```text
F_hat[u,a] = sum_v victim_mask[u,a,v] *
             (min(d_hat[u,a,v], 0)
              + g[u,a] * max(d_hat[u,a,v], 0)).

Q3[u,a] = (F_hat[u,a] - F_hat[u,c[u]]) / kappa.
```

This preserves the ZR semantics: all estimated victim harm counts, while
estimated victim benefit counts only under the exact causal compatibility
condition. Centering occurs after victim aggregation so `Q3[u,c[u]]` is exactly
zero. This remains one Q3 module and one optimizer, not one Q per victim.

## Required invariances

- victim-order invariance via a shared scorer and masked summation;
- user-relabel equivariance, with no user-ID feature;
- action-slot equivariance using physical action keys rather than flat indices;
- satellite/cell/color relabel invariance using equality, co-channel relations,
  and geometry rather than raw numeric identities;
- native action-mask preservation;
- zero contribution from padded victims before normalisation.

For focal `u`, candidate `a`, and victim `v`, define the exact victim predicate
before padding:

```text
victim_mask[u,a,v] =
    (v != u)
    and reference_opening[v]
    and changed_key_set[u,a] is not empty
    and (
        any(victim_beam[v] == b for b in changed_key_set[u,a])
        or any(cochannel(victim_beam[v], b)
               for b in changed_key_set[u,a])
    )
```

with

```text
changed_key_set[u,a] = ({b0} if e0 else empty)
                       union ({ba} if ea else empty).
```

where

```text
cochannel((s,c),(s2,c2)) =
    color(c) == color(c2)
    and ((s == s2 and c != c2) or (s != s2)).
```

The same-beam terms capture load changes. The two co-channel terms capture all
possible interference changes because only the focal origin/candidate beam can
change activation or RF power under a unilateral replacement. A non-focal user
that is unserved under the detached reference remains unserved because its
action and link-feasibility predicate do not depend on interference. Therefore
every excluded real victim has exact zero rate delta under the frozen physics.
The encoder must assert `victim_mask[u,a,u] == false`, set every padded or
invalid victim mask false, and mechanically zero all tokens under
`~victim_mask` before any pooling or normalisation.

The observed SINR proxy and nominal physical coefficients are separate
features. Nominal wanted, interference, and interference-change values must be
built independently from current geometry with fading exactly one and shadowing
exactly zero. The nominal builder may not substitute observed SINR for any
nominal coefficient.

## First gate: parameter-free analytic diagnostic

Before fitting a relational neural learner, run one preregistered matched
diagnostic:

- four newly frozen TRAIN worlds whose outcomes have never been opened;
- all three frozen Q1/Q2 lineages;
- contexts h=12, h=1, and h=2;
- no optimiser, no learned C3, no episode training, and no TEST split.

At each anchor the runner must persist causal tokens before invoking the oracle.
It then:

1. reconstructs causal compatibility from raw exact predecision surfaces and
   requires exact agreement with the live oracle compatibility for every legal
   action;
2. computes a parameter-free nominal victim delta from the six victim-token
   fields;
3. aggregates and centres it with the unchanged ZR rule;
4. compares argmax(Q1+Q2+nominal-Q3) with the exact ZR teacher;
5. in the full context, runs matched ten-step `BASE`, `EXACT_ZR`, and
   `NOMINAL_ZR` arms under one keyed field per world and reports canonical
   ratio-of-sums EE and served user-steps.

The exact-ZR upper bound and nominal-ZR diagnostic must each have positive
pooled EE versus BASE, positive direction for at least two of three lineages and
three of four worlds, and pooled served fraction noninferior to BASE within the
fixed absolute margin `0.001`. For every lineage, also require:

- full agreement strictly above the frozen Q1+Q2 background;
- pivotal agreement at least 0.50;
- stable-decision preservation at least 0.95;
- at least one changed decision and positive-compatible support at least 0.80;
- h=1 and h=2 noninferior to their backgrounds;
- exact permutation-test agreement and finite tokens.

Compatibility proof is a step-0 prerequisite before any matched arm executes.
Any causal-compatibility mismatch stops as mechanics failure. A negative exact-
ZR upper bound stops the unchanged target in the learned-Q2 context; an exact-ZR
pass followed by nominal diagnostic failure stops the relational-observability
route. None permits redrawing worlds or replacing lineages. Passing authorizes
exactly one separately frozen relational source-only learner gate whose inputs
are limited to the nominal decoder's predecision variables; it does not
authorize episode training.

## Retired alternatives

Do not reopen B402/SoftKL, add more flat B402 features, tune the V0.17 loss, select
a favourable seed or checkpoint, or rerun PNFE. A different C3 target is a new
method proposal and requires a separate design decision rather than an informal
fallback inside this route.

## External adjudication

The independent fresh-context review selected a victim-relational ZR learner.
Fable 5.1 first returned `GO_ANALYTIC_C3_GATE`, then clarified this as
`ANALYTIC_DIAGNOSTIC_THEN_RELATIONAL`: a permanent analytic Q3 would violate the
three-learned-head invariant, while a parameter-free analytic diagnostic may
precede exactly one relational learner attempt. Fable's suggestion to reuse the
already opened V0.13 worlds is rejected; the executable diagnostic must use new
TRAIN worlds and be frozen before any outcome is opened.
