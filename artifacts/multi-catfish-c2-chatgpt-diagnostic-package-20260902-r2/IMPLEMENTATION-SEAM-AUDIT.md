# OPS-3 implementation-seam audit

Date: 2026-09-02  
Status: read-only feasibility evidence; no formula implementation or outcome

## Reusable simulator authority

| Need | Packaged source | Required use |
|---|---|---|
| current legal action to physical satellite/cell | `source/env/action_contract.py` | use the native slot/action mapping and current mask |
| future TLE geometry | `source/env/scenario.py`, `source/env/ephemeris.py` | project the current physical satellite identity at offsets |
| cloned eligibility | `source/env/d2.py` | deep-copy and advance D2 at the native 640 ms cadence with frozen user position |
| recurrence power and service feasibility | `source/env/link_budget.py` | reuse canonical recurrence and ceiling rules |
| Shannon rate and network power | `source/env/link_budget.py` | reuse load, PA, beam-circuit, and satellite-baseband semantics |
| receive/interference field | `source/env/interference.py` | use canonical beam field, receive gain, same-satellite override, and co-channel interference |
| cell visibility and off-axis gain | `source/env/candidates.py`, `source/env/geometry.py`, `source/env/pointing.py` | evaluate visibility at cell center and gain toward the frozen user |
| frozen served background | `source/runtime/ee_axis_state.py`, `source/env/step.py` | derive load/power from previous served associations; ungated demand is not load |

## Old seams that cannot implement OPS-3

- the current-slot no-commit action evaluator has no future offsets;
- the V0.7 branch/policy code imports successor decisions and therefore is not
  OPS-3's no-future-action projection;
- live environment stepping would mutate D2, mobility, segment, and RNG state;
- drawing fading would violate the deterministic median-channel contract.

## Highest-risk implementation details

1. Future D2 must be advanced on a cloned tracker at every native measurement,
   not approximated once per decision.
2. Cell visibility uses the physical cell center, not focal-user elevation.
3. Background load counts last committed served associations and excludes the
   focal user; `_previous_demand` is an ungated demand signal.
4. Adding the focal action to an existing beam uses the maximum of background
   and focal required power. A new beam adds beam circuitry; a first beam on a
   satellite adds satellite baseband power.
5. The receive field must include the receive-gain envelope and
   same-satellite interference override.
6. Once projected feasibility fails, persistence is absorbing; later offsets
   cannot silently restart the segment.
7. Formula evaluation must leave the live environment, D2 tracker, RNG,
   candidate order, Q networks, and action state unchanged.

## Minimal implementation order

1. isolated pure OPS-3 formula module;
2. immutable predecision/background adapter;
3. formula and state-purity unit tests;
4. frozen 12-episode no-training oracle smoke;
5. mandatory 36-episode three-world panel if the smoke is not a hard failure;
6. only then consider Q2 source/state data and a bounded learner preregistration.

This audit establishes implementability only. It supplies no evidence that the
OPS-3 oracle or a learned Q2 improves final EE.
