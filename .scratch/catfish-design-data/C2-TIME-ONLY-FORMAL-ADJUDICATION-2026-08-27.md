# C2 time-only formal adjudication — 2026-08-27

## Decision

`DROP_C2_TIME_ONLY_EE_DIRECTION`

The frozen time-only ledger is algebraically and operationally verified, but
it does not justify C2 as an EE specialist at the live `Delta = 30.08 s`
decision interval. No C2 reward implementation, state-mapping exercise, short
pilot, or heavy training is authorized from this result.

This decision applies to the time-only EE direction specified in ADR-004 and
`C2-TIME-ONLY-IDENTITY-SCALE-SPEC-2026-08-27.md`. It does not decide whether a
separately specified C2 can improve the canonical R2 handover/continuity
objective.

## Bound artifact

- Formal result:
  `c2-time-only-identity-scale-seeds-2026082401-2026082410-v1.json`
- SHA-256:
  `38a5e38e3803e1e6f0cacc12a95e2cf99c4b890c96926e66c33c4e792a77c463`
- Runner SHA-256:
  `815a39e74a2e83fae1484fe9f68279120e9ee2d3ea0750f45cde51443a656a34`
- Formal runner decision: `IDENTITY_SCALE_PASS`
- Cross-model adjudication:
  `FABLE-MAX-C2-FORMAL-RESULT-ADJUDICATION-2026-08-27.md`
- Cross-model verdict: `DROP_C2_TIME_ONLY_EE_DIRECTION`

## Verified engineering result

- Process exit was zero; formal artifact transfer hashes match.
- All 15 authority checks and all 9 input-parity checks pass.
- There are 758 eligible and 242 ineligible focal rows over ten seeds.
- All ledger identities, units, event semantics, exactly-one-focal checks,
  preview/commit checks, and common-RNG checks pass.
- The only service-unsafe eligible row is retained and disclosed; removing it
  in a descriptive sensitivity does not alter the scientific decision.

Therefore this is not an implementation failure. `IDENTITY_SCALE_PASS` means
the scale estimate is trustworthy; it does not mean the mechanism is useful.

## Primary-clock scientific result

At `Delta = 30.08 s`:

- Main reference interruption-time damage: mean `0.3250%`, ten-seed t95
  `[0.3145%, 0.3356%]`.
- Structural maximum under the conditional `T <= 0.142 s` surface:
  `0.142/30.08 = 0.472%`; the observed maximum reaches this ceiling.
- Exact-stay paired result, all 758 eligible rows: pooled
  `+42,400.2 bits/J`, 393/758 positive rows, 7/10 positive seed means, and
  seed-t95 `[-29,845, +108,138] bits/J`.
- Service-safe 757-row sensitivity: pooled `+42,895.6 bits/J`, 393/757
  positive rows, 7/10 positive seed means, and seed-t95
  `[-29,212, +108,330] bits/J`.

The paired interval crosses zero, and even a state mapper cannot enlarge the
structurally bounded time-only EE pool. Coefficient amplification is forbidden.

The `0.640 s` D2 surface is a useful scale sensitivity but is not the live
action/reward interval. Turning it into an operational endpoint would require
a new multi-step interruption state, a different environment contract, a new
ADR, and new disjoint evidence.

## Consequence for the three-role design

C2 must no longer be described as a validated or advancing time-only EE
specialist. Two honest alternatives remain:

1. drop C2 entirely; or
2. define a genuinely new C2 whose direct endpoint is the canonical R2
   handover/continuity objective, with EE and service as safeguards and
   interaction endpoints rather than pretending its private reward is a large
   direct EE term.

The second alternative requires a new pre-result specification. It may not
reuse the failed time-only effect as evidence of effectiveness, and it may not
quietly operationalize the `0.640 s` sensitivity.

## Claim ceiling

Allowed: the time-only algebra is correct; the primary-clock signal is small;
the C2 time-only EE direction was dropped under its frozen rule.

Not allowed: C2 improves EE; timing parameters are accepted project values;
state mapping can rescue the failed scale; or a replacement C2 is effective.
