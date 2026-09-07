# RETRACTED: C3 same-class eligibility contradiction

Status: **retracted on 2026-08-27 after live counterevidence**. This note is
retained so the failed reasoning is auditable. It grants no implementation or
training authority and must not be cited as a valid support proof.

Date: 2026-08-27

## Audited proposal

ADR-003 SHA-256
`1bba4ba25eea4f9388699ae7613f9121835b9422357e7d0e9ea79f54e78ff9d5`
required all of the following for a one-user relocation:

1. source load at least two;
2. the focal user is the strict unique source-beam power maximum;
3. the destination differs from the source; and
4. the reference and relocation have the same handover class.

## Retracted argument

The argument assumed that every feasible continuing segment has link power at
least `p0`.

There are only two cases.

### Reference continues the incumbent

The reference handover class is `NONE`. A relocation to a different physical
beam is necessarily `INTRA_SATELLITE` or `INTER_SATELLITE`. Therefore the
same-class condition fails.

### Reference is itself a handover

The focal user's reference link starts a new segment at `p0`. Because source
load is at least two, at least one other served source user has link power at
least `p0`. Therefore the focal user cannot be the strict unique source
maximum. The bottleneck condition fails.

The episode-start special case also assigns `NONE` to all first-step actions,
but all new segments start at `p0`; with source load at least two, the strict
unique-maximum condition again fails.

That conclusion is invalid for the live implementation.

## Counterevidence and cause

The frozen exploratory intra-satellite shadow census at seed `2026082701`
observed continuing feasible link powers below `p0=0.825 W`, including a source
maximum of `0.7783096266 W`. Equation (3.12),

```text
p(t) = p0 * G(theta_start) / G(theta_now),
```

can fall below `p0` when transmit gain improves after the segment start. The
code comment that the recurrence "only ever raises power" is therefore not a
safe premise for this case proof. A reference handover starts the focal user at
`p0`, while continuing co-users on the source can be below `p0`; same-class
support is not analytically impossible.

The same-class design is still rejected as the primary mechanism because it
excludes the intended continuing-bottleneck challenge, does not isolate R2,
and has no established support/learnability advantage. Those are design
grounds, not a zero-support theorem.

## Minimal viable correction to test

Do not pretend that C3 can reduce an incumbent power bottleneck without a
handover. Define the conflict explicitly:

- reference: the focal user persists on its continuing incumbent (`NONE`);
- C3 alternative: a valid different beam on the same satellite
  (`INTRA_SATELLITE`), already active under the fixed other-user actions;
- source: load at least two and focal is the strict unique power maximum;
- destination: the new-link power is no greater than its existing maximum;
- effect: active beams/satellites and service are unchanged, so the live PA
  identity certifies a strict immediate decrease in `P_system`;
- cost: C3 deliberately incurs one `phi1` temporal event, which remains in the
  complete reward vector and is opposed by C2 rather than hidden by an
  impossible same-class filter.

This corrected mechanism is a hypothesis. Its source/destination support,
state sufficiency, temporal trade-off, immediate EE direction, and transfer to
Main still require separate shadow and representability gates.
