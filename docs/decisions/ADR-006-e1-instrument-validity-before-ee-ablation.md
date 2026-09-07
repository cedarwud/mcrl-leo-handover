# ADR-006: Require E1 instrument validity before another EE ablation

## Status

Accepted

## Date

2026-08-31

## Context

The first 10-episode V0.3 ablation used only ten optimizer steps per head and a
54/2/54 route corpus. Its deployed scores were dominated by relative-action
slot effects, so its EE ordering could not identify C1, C2, or C3. The run did
show that the software path executes, but an EE endpoint cannot distinguish a
state-conditioned learned policy from a constant slot preference.

An earlier audit proposed treating a missing explicit frozen-Main action as a
structural defect. Fresh review found that conclusion too strong: frozen Main
is deterministic from its input, mask, checkpoint, and weights, while pair
training explicitly receives the reference action. Structural failure must be
demonstrated by conflicting targets under an identical model input.

## Decision

Run a no-EE E1 gate before any further EE ablation. E1 uses fresh, sealed,
non-overlapping source seeds and cluster-level train/validation/test splits. It
tests provenance, exact input collisions, validation-to-test action-slot
effects, pairwise skill over an action-only baseline, and route removal
pivotality at deployment.

Keep exactly three trainable route-local Q functions. Do not add a Main Q to
the deployment sum. Select any repair only after the E1 failure mode is known.

## Alternatives considered

### Continue directly to 500 or 9000 episodes

Rejected. More optimizer steps do not make a confounded or non-resolving
instrument interpretable, and EE must not select the instrument that measures
EE.

### Declare the absent Main action a structural failure immediately

Rejected. Architecture inspection alone does not establish an observation
collision. It may indicate sample burden, which E1 measures separately.

### Add a fourth Main Q at deployment

Rejected. It violates the requested three-Q topology and mixes a legacy value
surface with route-local pairwise surplus units.

### Use modal action share as the primary gate

Rejected. A scientifically valid policy can prefer a small action subset.
State-conditioned generalization and route pivotality are the relevant tests.

## Consequences

- The 10-episode EE numbers remain archived but void as route evidence.
- Existing 54/2/54 and 41-trace physical-headroom artifacts cannot become
  claim-bearing E1 training rows.
- One fresh source-generation run is required before claim-bearing E1.
- If E1 passes, the next run is a matched EE ablation; if it fails, the repair
  is bounded by the observed failure mode.
- Paper and figure authoring may continue with efficacy labelled `TBD`.

See `docs/MULTI-CATFISH-MCRL-V03-E1-INSTRUMENT-VALIDITY-CONTRACT-2026-08-31.md`.

