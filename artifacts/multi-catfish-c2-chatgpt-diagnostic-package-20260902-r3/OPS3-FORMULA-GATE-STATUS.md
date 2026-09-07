# OPS-3 formula-gate status

Date: 2026-09-02  
Status: `FORMULA_CORE_GREEN__LIVE_ADAPTER_OPEN__NO_OUTCOME`

## Verified in this snapshot

- implementation: `source/runtime/ee_axis_ops3.py`;
- tests: `tests/test_w129_ee_axis_ops3.py`;
- targeted result: `17 passed`;
- Python compilation passed;
- no episode, oracle outcome, Q2 learner, or training was run.

The fixture-level tests currently pin:

- terminal, one-offset, two-offset, and three-offset horizon behavior;
- mean-over-horizon rather than a three-offset sum;
- absorbing persistence after projected service loss;
- exact `-kappa` loss without an energy-saving credit;
- recurrence power outside the feasibility ceiling;
- uncapped over-ceiling required-power ratio with service set to zero;
- canonical shared-beam maximum and new-beam/new-satellite power activation;
- exact reference zero and gauge-constant behavior;
- negative target retention, native mask safety, and null-gain handling;
- frozen constant hex values and strict positive `p0` validation.

An independent read-only review found no direct formula error in persistence,
gauge, mask, outage sign, or canonical power. It also identified missing test
coverage for horizon mean, over-ceiling recurrence, near-terminal features,
fixed constants, and `p0=0`; those gaps were added before this snapshot.

## Not yet verified

The package contains only a Protocol boundary, not a real live
`OPS3ProjectionProvider`. The following remain open:

1. future TLE propagation at all native 640 ms D2 measurements;
2. deep-copied D2 advancement with frozen user coordinates;
3. cell-centre future visibility and action-to-cell identity alignment;
4. deterministic no-fading projected receive power, same-satellite override,
   co-channel interference, beam load, SINR, and Shannon rate;
5. frozen served non-focal background extraction from the live environment;
6. end-to-end proof that live environment, tracker, RNG, candidates, and
   networks remain unchanged;
7. any OPS-3 action headroom or all three `FULL - DROP-Cj` directions.

Until these pass, the correct status is not `MECHANICS_GREEN`; it is only
`FORMULA_CORE_GREEN`. This distinction is central to the requested review.
