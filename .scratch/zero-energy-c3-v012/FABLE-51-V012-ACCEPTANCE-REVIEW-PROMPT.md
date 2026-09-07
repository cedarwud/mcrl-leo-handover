# Fresh-context method adjudication: Multi-Catfish C3 V0.12

You are an independent scientific-method reviewer. Work only from the facts
below; do not assume prior conversation context and do not browse or inspect
the repository. Separate verified development evidence, inference, and
proposal. This is TRAIN-development oracle evidence, not learned-policy,
held-out, or efficacy evidence.

## Immutable research objective and architecture

- The only final objective is canonical ratio-of-sums energy efficiency:
  total delivered bits / total network energy.
- Exactly three independent 28-action heads must remain: Q1, Q2, Q3.
- Deployment is one common safe mask, left-to-right unweighted Q1+Q2+Q3,
  smallest-index masked argmax, and one Main action.
- No mixer, head weight, sign flip, coordinator, auction, second mask, or
  post-training override is allowed.
- C1 and execution-equivalent OPS3-C2 are fixed. Only C3 is under review.

## Prior causal evidence

V0.11 C3 candidates decreased EE by -4.444% and -1.489%. They increased
active-beam steps by +43% to +48%, and exposed joint actions usually increased
current network energy. This motivated a zero-energy-supported current-slot
non-focal C3 redesign.

## Frozen V0.12 designs

Both candidate teachers use the C3-free Q1+O2 action b0 as reference. Positive
C3 credit is allowed only for a unilateral action whose exact current-slot
physical signature matches b0 bit-for-bit: served vector, active beam set,
active satellite set, per-beam RF power, and total network power. Negative
non-focal harm always remains. The executed joint action at every exposed
anchor must add no active beam/satellite and must not increase current network
power.

- ZR: current non-focal rate redistribution, with positive gains gated by the
  exact zero-energy signature.
- HR: current non-focal insertion-harm relief, with positive relief gated by
  the same signature.

Candidate order was frozen as ZR first, HR second. Two fresh TRAIN worlds,
three frozen Q1 lineages, ten steps, and DROP_C3/FULL_ZR/FULL_HR yielded 18
episodes. The prereg also imposed trajectory-level service noninferiority,
active-beam-step nonincrease, and active-satellite-step nonincrease. Rules
cannot be retroactively changed.

## Authenticated V0.12 development result

ZR and HR selected identical actions/outcomes in this panel.

- DROP_C3: 60.2091e12 bits, 502418.752 J, 119.838518 Mbit/J,
  2597 active-beam steps, 304 active-satellite steps, service 6000/6000.
- FULL: 57.5451e12 bits, 477173.470 J, 120.595844 Mbit/J,
  2468 active-beam steps, 310 active-satellite steps, service 6000/6000.
- FULL vs DROP: EE +0.631956%; bits about -4.42%; energy about -5.02%;
  active-beam steps -129; active-satellite steps +6; service unchanged.
- Both worlds are EE-positive: +0.148808% and +1.085793%.
- Each world has 2/3 positive lineages; service is 3/3 noninferior in both.
- Mechanics, formula identities, target spread, supported-positive count,
  exposure, changed-action compatibility, and per-exposed-anchor joint support
  all pass.
- The only frozen hard-stops are pooled and per-world active-satellite-step
  nonincrease. Therefore the binding V0.12 decision is and must remain
  STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM.

## Questions

1. Is trajectory-level active-satellite-step nonincrease scientifically
   necessary as a hard acceptance condition when exact total network energy is
   already the denominator, total energy falls materially, service is equal,
   active-beam steps fall, and each exposed current joint action itself adds no
   satellite/beam or network power?
2. Does +6 satellite-steps reveal a structural C3 flaw requiring another C3
   formula redesign, or a redundant/overconstrained surrogate gate?
3. Because V0.12 cannot be retroactively passed, what is the single next
   methodologically valid step? Specify a pre-outcome contract using new TRAIN
   worlds. State whether the replacement guard should be exact trajectory
   energy nonincrease, no extra guard beyond EE+service, or something else.
4. Given identical ZR/HR policies here and the frozen preference for the
   simpler ZR, should HR be retired from the next confirmation or retained as a
   comparator?
5. What evidence would authorize the separate state-only Q3 learnability gate,
   while avoiding tuning on the observed V0.12 worlds?

End with exactly one decision token on its own line:

- `FRESH_WORLD_CONFIRM_ZR_REVISED_ACCEPTANCE`
- `REDESIGN_C3_FORMULA_FIRST`
- `STOP_THREE_HEAD_METHOD`
- `INVALID_RETROACTIVE_PASS`

Do not recommend retroactively calling V0.12 a pass. Do not propose changing
Q1/Q2, head weights, deployment, or the final EE formula.
