# Multi-Catfish MCRL V0.4 route-interaction diagnostic

Date: 2026-09-01  
Status: `POSTOUTCOME_DIAGNOSTIC_WORK_ORDER`  
Claim ceiling: `INTERACTION_DIAGNOSIS_ONLY_NO_ROUTE_EFFICACY_CONFIRMATION`

## Question

The sealed five-arm result reports `FULL - DROP-C1 = +254.596%`, whereas an
earlier 10-update experiment reported a negative C1 direction before that
experiment was invalidated as `VOID_UNINTERPRETABLE_INSTRUMENT`.  The five-arm
contrast is a valid conditional marginal comparison, but it cannot distinguish
an intrinsically useful Q1 from Q1 counteracting the already-confirmed harmful
Q2 policy bias.

## Frozen diagnostic

Use the exact 30 TRAIN-only evaluation worlds, three initialization lineages,
selected Q3 rung 100, frozen Q1/Q2 bytes, common keyed fading fields, simulator
physics, 10-step horizon, masks, and one argmax from the sealed five-arm run.
Do not train or open TEST.

Evaluate three additional policies:

```text
C1_ONLY = Q1
C2_ONLY = Q2
C3_ONLY = Q3
```

The existing sealed `FULL`, `DROP-C1 = Q2+Q3`, `DROP-C2 = Q1+Q3`,
`DROP-C3 = Q1+Q2`, and `Main` rows remain inputs and are not regenerated.
The source five-arm result SHA-256 is
`9142da31690927fe853765b9dfc0c807d4202738784961b44be393a77c608224`.

Report absolute EE, bits, energy, service, and action-trace diversity for every
single route.  For C1 report its conditional marginal EE in the two newly
observable contexts:

```text
(Q1+Q2) - Q2
(Q1+Q3) - Q3
```

alongside the already sealed context:

```text
(Q1+Q2+Q3) - (Q2+Q3)
```

## Interpretation

This is deliberately post-outcome and therefore cannot upgrade or replace the
five-arm decision.  It may determine whether the large C1 percentage is
consistent across contexts or is primarily a cancellation interaction with
the harmful old Q2.  C1 and C3 remain frozen while C2 is redesigned.  Final
route acceptance still requires a fresh five-arm evaluation after the new C2
is selected.

## Execution note

The first frozen-C3 execution reached all 270 single-route episode evaluations
but stopped before publishing because the unchanged five-arm aggregator rejected
the diagnostic-only labels `C1_ONLY`, `C2_ONLY`, and `C3_ONLY`.  The diagnostic
runner now checks those labels itself and passes validation-only copies labelled
`FULL` to the frozen structural aggregator; no frozen evaluator/source file,
episode row metric, route map, checkpoint, or five-arm artifact is changed.
