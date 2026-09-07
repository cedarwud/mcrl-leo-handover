# Fable Max review receipt: payload-boundary time-only C2

Status: completed external-model review. Review credit only; no runtime,
parameter, training, or manuscript authority.

Date: 2026-08-27

## Invocation

- CLI: `claude -p ... --model fable --effort max --output-format json --dangerously-skip-permissions`
- Canonical model reported by the CLI: `claude-fable-5`
- Session: `cc63d49d-ebd8-4c68-87ee-2e419de00222`
- Terminal reason: `completed`
- Duration: `270950 ms` API time
- Permission denials: none
- Reviewer scope: ADR-003, R2 provenance matrix, canonical payload-power
  definition, and current reward assembly only

## Verdict

```text
REVISE
```

The reviewer found no fatal algebraic or system-boundary contradiction, but it
did not authorise the proposal as a primary metric in its current wording.

## Verified by the reviewer

For

```text
B0       = Delta * sum_u R_u
E0       = Delta * P_system
L        = sum_u R_u * T_u
eta_time = (B0 - L) / E0
r2_u     = -R_u*T_u/E0,
```

the reviewer verified

```text
sum_u r2_u = eta_time - eta0
```

with units of bit/J under `E0>0`, `R_u>=0`, and `0<=T_u<=Delta`.
It also verified that the canonical `P_system` is a partial satellite-payload
boundary: per-beam PA supply, per-beam circuit, and per-active-satellite
baseband power. Therefore excluding UE, gateway, and other procedure energy is
boundary-consistent if it is stated as an exclusion, not described as a claim
that physical handover energy is zero.

For any hypothetical nonnegative out-of-boundary event energy `H`, the
time-only damage is no larger than the `(E0+H)` damage. It is therefore a lower
bound on the extended-boundary temporal damage, not an inflated one.

## Required revisions before a numeric C2 gate

1. Make a dated boundary ruling that the primary C2 endpoint is explicitly
   **payload-boundary time-only temporal EE**. Keep any procedure-energy model
   as a separately declared boundary expansion.
2. Freeze `R_u` as the non-interruption-discounted steady-state slot rate and
   forbid applying `R_u*T_u` when the same outage is already present in `R_u`.
3. Freeze re-entry and episode start at `T=0`; do not silently map them to an
   inter-satellite successful-handover time. The actual unserved interval and
   service gate carry the outage damage.
4. Keep SAN, beam-to-PCell, electronic-VSAT, PRACH/SMTC,
   interruption-versus-full-delay, and clock representation as explicit open
   gates before attaching 62/142 ms or 72/152 ms to the live classes.
5. Keep steady-state `eta0`, service, and the no-coefficient-enlargement
   falsifier beside the temporal endpoint.

## Required next test

The reviewer requested a non-training absolute identity/scale replay test over
the frozen legacy transitions:

- verify the additive identity at every step;
- verify event-free equality `eta_time=eta0`;
- verify domains and the no-double-discount rule;
- verify the payload-only boundary has no injected UE/gateway energy term; and
- report the temporal damage scale at both 30.08-s and 0.640-s clocks.

This remains legacy-narrow sensitivity until the geometry and event mappings
are closed. It cannot establish learning benefit.

## Independent caution

The review's statement that an unserved state automatically dominates a
152-ms event must be rechecked against the actual environment clock and reward
aggregation. It is not adopted merely because the reviewer stated it.

## Claim ceiling

The review supports a coherent C2 proposal and its next non-training test. It
does not close `R2_PHYS`, prove C2 learnability, prove C2 improves canonical or
temporal EE, establish novelty, or authorise heavy training.
