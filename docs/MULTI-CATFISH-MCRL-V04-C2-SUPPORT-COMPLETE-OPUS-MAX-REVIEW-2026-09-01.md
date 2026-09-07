# Multi-Catfish MCRL V0.4 support-complete C2 review

Date: 2026-09-01  
Status: `ADVISORY_REVIEW_COMPLETE`  
Decision: `DESIGN_GO_PROBE_REVISE`

## Review identity

One bounded fresh-context review was run with the user-required CLI surface:

```text
claude -p "<sealed documents-first prompt>" --model opus --effort max \
  --output-format json --dangerously-skip-permissions
```

The returned session identifier was
`68aa9025-02a9-4392-9a2e-90d22e0d62cb`; the provider reported canonical model
`claude-opus-5`, terminal status `completed`, and no Web requests.  The exact
prompt is retained at
`.scratch/c3-v04/OPUS-MAX-C2-SUPPORT-COMPLETE-REVIEW-PROMPT.md`.

This memo records an advisory review, not experimental evidence.  Reviewer
recomputations that are not independently sealed by the repository remain
reviewer-reported observations.

## Verdict

The reviewer agreed that full legal-action temporal sibling enumeration is the
best single bounded repair.  The design is `GO`; the proposed three-cluster
probe was `REVISE` because it was too small and did not test continuation
sensitivity or delivered-rate collapse.

The central design mismatch is:

> Old C2 trains a one-sibling candidate/reference comparison at each state,
> but deployment asks Q2 to participate in a legal 28-way ranking.

The reviewer also identified a separate surviving risk: the downstream target
uses a branch-local Main continuation whereas deployment re-decides every
step.  Full sibling coverage cannot, by itself, prove that the temporal ranking
is stable under the deployed non-C2 continuation.

## Adopted recommendation

The one support-complete formulation keeps all of the following frozen:

- canonical ratio-of-sums EE and fixed \(\lambda_0\);
- shared \(\kappa\) and \(H^c=4\);
- the downstream \(\zeta_2\) arithmetic;
- hold-while-legal and monotone release;
- Q1, Q3, learner architecture, pairwise loss, and direct unweighted
  `Q1 + Q2 + Q3` deployment under one common mask and one argmax.

It changes only the C2 source coverage: every legal non-Main action at the same
sealed anchor/focal state becomes a matched temporal sibling against the same
Main reference.

The fresh no-training probe is enlarged to three worlds, one pre-outcome
anchor per world, and four focal departure clusters per anchor.  It measures:

1. whether non-incumbent siblings survive the horizon and have non-degenerate
   temporal effects;
2. whether the old Q2 selections have material physical regret;
3. whether high-\(\zeta_2\) siblings preserve delivered bits rather than merely
   a served/not-served indicator; and
4. whether sibling rankings remain stable under frozen DROP-C2 (`Q1 + Q3`)
   continuation.

Exact gates and seeds are fixed separately in the pre-outcome census
preregistration.  Pairwise MAE skill is not an efficacy gate because the sealed
five-arm evidence showed that a weak-positive C2 prediction gate coexisted with
negative marginal EE.

## Binding interpretation of a negative result

A negative probe or second negative marginal gate retires only this exact
support-complete-temporal formulation.  It does not retire C2, reduce the
method to two Catfish, or relax the final acceptance test.  C2 must then return
to a new formula/physics design cycle until all three frozen marginal tests are
positive:

```text
FULL > DROP-C1
FULL > DROP-C2
FULL > DROP-C3
FULL > Main
```

No 1500/3000/9000-episode run is authorized by this review.
