# Controller decision — closed: do not open the contract for the direct parametrisation
Recorded 2026-09-10. Decided under the owner's stated criterion that every ruling be judged by whether it serves the goal of all three learned routes individually raising pooled efficiency. Evidence: an ultra-effort design analysis that read the deployed code rather than the design documents. `DIAGNOSTIC_NOT_CLAIM`; nothing was run and nothing sealed was modified.

**Decision: no.** Not on cost, and not on the strength of the ranking result. On the ground that the replacement **removes the structure the owner's requirement is stated over**.

## Why the three routes are not interchangeable in the deployed system
Read from the live implementation, which is the three-route model and profile selector, not the older compatibility path:

- **the first route's** per-action outputs enter every candidate's score **and** the per-user argmax that builds the reference proposal and repairs an infeasible one;
- **the second route's** outputs do the same, independently;
- **the third route** supplies a single whole-set scalar to ranking only, is **hard zero on empty and singleton sets**, and never touches the proposal or repair path.

A single set-conditioned score collapses the ranking path into one head. The leave-one-out arms for the first and third routes then no longer mean what the contract says they mean.

## The construction that could preserve them, and why it is not available
A shared direct readout consuming the original heads' outputs — the first route entering through its per-user terms, the third through its interaction scalar, the second through its own sum — would keep three source interventions defined. Three things disqualify it now:

1. **It is a proposed formulation, not existing code.**
2. **The measured ranking advantage does not transfer to it.** The 32.92 % regret reduction belongs to the model that was measured; its transfer is unverified.
3. **The all-neutral control stops being all-neutral.** It would be neutral for the three original routes while still containing informative training in the shared readout, so the claim sentence becomes conditional on that predictor rather than describing a three-head system with all learned supervision neutral.

The alternative of retargeting the third route's supervision was also examined and rejected: it supplies unilateral supervision even to the neutral arm, which changes the sealed labels, the neutral training and the control background. It is not the contracted contrast.

Under the fixed requirements neither construction conforms: §B4 fixes the factor identity, §C1 fixes the per-user surrogates, §C2 fixes residual-only third-route supervision, singleton zero anchoring and the deployed sum. Retaining the exact decomposition as a reporting known-answer test would not make a different deployed score satisfy §C2.

## Erratum 16
I told the owner that both per-user feature schema digests would have to change. **They do not**, provided their raw fields and scales are unchanged; a new readout schema would be a separate object. I overstated the blast radius.

## What this does not close
The ranking result stands as a measurement: direct prediction ranks better on these pools. If the project ever pursues a selector whose contribution claim is about decision quality rather than three separable routes, that measurement is the starting point. It is simply not usable for the requirement as the owner has stated it.

## Standing
No contract opened, no sealed artefact touched, no run authorised. Existing sealed artefacts remain historical evidence and their write-once implementation would reject overwriting in any case.
