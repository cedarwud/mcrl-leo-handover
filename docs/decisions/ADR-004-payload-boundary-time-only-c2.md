# ADR-004: Payload-boundary time-only C2

## Status

Accepted for the C2 **design boundary and algebra only**. This record does not
select a handover-time table, edit the environment or rewards, authorise a
preregistration change, or authorise training. Its remaining gates are
explicitly listed below.

This decision was made before viewing any C2 treatment-training outcome. It
supersedes only the proposal that nonzero incremental handover energy must be
inside C2's primary denominator. It does not supersede the R2 physical-source
audit or the frozen baseline.

## Date

2026-08-27

## Context

The canonical system power is the partial satellite-payload model in equation
(3.16): per-beam PA supply, per-radiating-beam circuit power, and one baseband
term per active satellite. It excludes UE, gateway, and other procedure-side
power. Canonical R1 therefore already reports payload energy efficiency,

```text
eta0 = sum_u R_u / P_system.
```

ADR-003 initially proposed a temporal extension containing both useful-time
loss and an incremental event-energy term `E_HO`. The R2 provenance audit found
no source that supplies a boundary-compatible satellite handover energy value.
Adding terrestrial UE or base-station components would change the canonical
denominator rather than complete it.

Fable Max independently reviewed the narrowed design and returned `REVISE`,
not an effectiveness pass. It found the algebra and boundary coherent but
required an explicit boundary ruling, frozen event semantics, a no-double-
discount rule, and completion of the event-to-time mapping before numeric use.

## Decision

### 1. Keep the primary C2 endpoint inside the canonical payload boundary

C2's proposed physical endpoint is named
**payload-boundary time-only temporal EE**. It accounts for useful payload bits
lost during interruption while retaining the canonical payload-energy
denominator. It neither assigns nor estimates physical handover-procedure
energy.

For decision interval `Delta`, define

```text
B0       = Delta * sum_u R_u
E0       = Delta * P_system
L        = sum_u R_u * T_u
eta0     = B0 / E0
eta_time = (B0 - L) / E0
r2_time,u = -R_u*T_u/E0.
```

Then

```text
sum_u r2_time,u = eta_time - eta0 = -L/E0 <= 0.
```

The domain is

```text
E0 > 0, R_u >= 0, and 0 <= T_u <= Delta.
```

`B0` and `L` must use the identical non-interruption-discounted steady-state
rate array. If a future rate already includes the same interruption, applying
`R_u*T_u` again is forbidden.

### 2. Exclude procedure energy; do not call it zero

`E_HO` is absent from the primary formula because UE, gateway, random-access,
and other procedure-energy components are outside the declared canonical
payload boundary. The statement is not `physical E_HO = 0`.

A future component-level event-energy study may define an extended-boundary
sensitivity

```text
eta_extended = (B0 - L) / (E0 + H), H >= 0,
```

but it must name all components, avoid double counting, and remain separate
from canonical R1 and primary C2. For fixed `B0`, `L`, and `E0`, time-only
damage is a lower bound on the damage under any added `H>=0`.

### 3. Retain the live decision clock

The C2 transition interval remains the live agent decision interval
`Delta = 47 * 0.640 s = 30.08 s`. The `0.640 s` D2 measurement clock is not an
agent action/reward interval and may not replace `Delta` in training or primary
evaluation.

A 0.640-s calculation may be reported only as a labelled scale sensitivity.
Using it operationally would require a new multi-step interruption state and a
different environment contract.

### 4. Freeze non-successful-event semantics

- `NONE`: `T=0`.
- Episode start: warm-start simulator convention, `T=0`.
- Re-entry after an unserved interval: `T=0` in this successful-handover
  ledger; it may not silently inherit the different-satellite time.
- The unserved interval's zero delivered bits and the service gate carry its
  outage damage.

C2's boundary-persistence collector admits only service-preserving focal
branches, so an unserved/re-entry path cannot be used to evade the C2 penalty.

### 5. Keep event times symbolic until the mapping gate closes

No numeric `T_phi1` or `T_phi2` is accepted by this ADR. The currently sourced
3GPP reference values remain conditional sensitivities:

```text
intra-satellite FR2-NTN cell handover: 62 ms interruption, 72 ms full delay
inter-satellite electronic-VSAT case: 142 ms interruption, 152 ms full delay
```

Before attaching either pair to live classes, a dated ruling must close:

1. SAN procedure applicability;
2. simulated beam/cell to PCell mapping;
3. electronic versus mechanical steering for the 0.6-m terminal;
4. PRACH, SMTC, synchronization, and frequency assumptions; and
5. interruption-time versus full-delay semantics.

No coefficient may be enlarged to make C2 visible. If the sourced mapping is
negligible at 30.08 s, C2 fails as an EE specialist and may remain only a
continuity/QoS objective.

## Why C2 remains distinct from C1

C1 samples the immediate rate/payload-power frontier through unchanged R1.
C2 is event-local and cross-time: it values avoided interruption and can
prefer persistence at a current boundary even when the immediate canonical EE
comparison is close or points toward switching. Its private reward selects
which complete transitions C2 explores; Main still learns from the unchanged
canonical reward vector in those transitions.

This is only a causal distinction. It does not prove that C2 will learn a
different useful policy or improve held-out temporal EE.

## Required non-training gate

Before implementation or training, replay a frozen transition corpus through
the symbolic/time-sensitivity ledger and verify at every step:

1. `sum r2_time == eta_time - eta0` within an absolute tolerance;
2. event-free `eta_time == eta0`;
3. all domain guards and exact units;
4. identical rate inputs in `B0` and `L`;
5. re-entry and episode-start `T=0` semantics;
6. no UE/gateway/procedure-energy term enters `E0`; and
7. the 30.08-s primary scale is reported separately from any 0.640-s
   sensitivity.

The receipt must also report service and steady-state `eta0`. A positive
time-only result may advance C2 to state-sufficiency and isolated-role tests;
it cannot authorise heavy training by itself.

## Consequences and claim ceiling

Allowed: C2 has a coherent, exact, payload-boundary temporal-EE formula and a
distinct boundary-persistence hypothesis.

Not allowed: physical handover energy is zero; 62/142 ms are accepted project
parameters; C2 improves EE; C2 is learnable; C2 is novel; or Multi-Catfish is
effective.
