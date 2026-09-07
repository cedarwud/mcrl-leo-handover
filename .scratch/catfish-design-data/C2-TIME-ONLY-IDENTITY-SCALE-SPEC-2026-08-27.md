# Frozen C2 payload-boundary time-only identity and scale gate

Status: frozen non-training legacy sensitivity under ADR-004. No reward,
runtime, parameter, Main-transfer, preregistration, manuscript, or training
authority.

Date: 2026-08-27

## Question

Does the accepted C2 time-only algebra execute exactly on live full-system
branches, and what is the conditional 62/142-ms signal scale on the existing
boundary-persistence support?

This gate cannot accept 62/142 ms as project parameters or prove C2 learning.

## Frozen inputs and census

- Legacy completed Main checkpoint and preregistration used by the existing v2
  state-observable C2 receipt, with their existing SHA receipts.
- Evaluation seeds `2026082401` through `2026082410`.
- 100 users, ten decision steps, and the same ten focal users per step selected
  by the frozen evaluation action RNG as v2: 1,000 focal rows.
- Reference joint action: masked-greedy Q1-only Main.
- Challenger: exact visible incumbent stay for one focal user, with all other
  actions fixed. Ineligible rows are retained.
- Every proposal is fixed before its counterfactual outcome. No outcome filter,
  fitting, threshold, or parameter sweep is allowed.

The runner must reproduce the v2 support counts before its scale result is
read: 758 exact-stay eligible rows and one service-unsafe challenger. A mismatch
is `INPUT_PARITY_FAILURE`, not a new scientific result.

## Event semantics

For each evaluated branch, derive `T_u` from the pre-step ledger and realised
association, not merely from the current three-class R2 value:

- episode start (`previous is None`): `T_u=0`;
- previous or current unserved: `T_u=0`, with outage/service reported
  separately;
- same physical satellite and cell: `T_u=0`;
- same satellite, different cell: conditional `T_u=0.062 s`;
- different satellite: conditional `T_u=0.142 s`.

Thus live re-entry may remain `phi2` in the canonical diagnostic reward while
being `T=0` in this successful-handover temporal ledger. The distinction must
be counted and disclosed.

The 62/142-ms table is a 3GPP conditional sensitivity only. ADR-004's
SAN/PCell/electronic-VSAT/PRACH/SMTC/interruption-semantics gate remains open.

## Exact ledger

For each branch and decision interval `Delta=30.08 s`, use the identical
non-interruption-discounted live rate array in both terms:

```text
B0       = Delta * sum_u R_u
E0       = Delta * P_system
L        = sum_u R_u*T_u
eta0     = B0/E0
eta_time = (B0-L)/E0
r2_u     = -R_u*T_u/E0.
```

Require on every branch:

```text
abs(sum_u r2_u - (eta_time-eta0)) <= 1e-9 * max(1, abs(eta0))
```

and exact `eta_time=eta0` when every `T_u=0`. Require `E0>0`, finite
nonnegative rates and power, and `0<=T_u<=Delta`.

Repeat only the scale calculation at `Delta=0.640 s`, using the same branch
outcomes and event table. Label it `D2_CLOCK_SCALE_SENSITIVITY`; it is not a
transition, training target, or primary endpoint.

No UE, gateway, PRACH, or procedure-energy term may enter either denominator.

## Paired outputs

For every eligible challenger report at both clocks:

- reference and stay `eta0`, `eta_time`, `L`, and `E0`;
- `Delta eta_time = stay-reference`;
- service, throughput, and payload-power changes;
- focal reference/stay event semantics and `T`;
- all-system `N_phi1`, `N_phi2`, re-entry count, episode-start count, and
  unserved count; and
- preview/common-RNG and exactly-one-focal-action parity.

Aggregate by seed and over all eligible rows. Report, but do not threshold-tune,
the fraction and seed count with positive `Delta eta_time`, the mean paired
effect, and its ten-seed t95 interval. Also report the absolute relative damage
`(eta0-eta_time)/eta0` under the Main reference steps to decide whether the
30.08-s signal is scientifically negligible.

## Decision

- `IDENTITY_SCALE_PASS`: all identities/input parity/engineering checks pass
  and the numeric scale is reported.
- `INPUT_PARITY_FAILURE`: support or input receipts differ from v2.
- `IDENTITY_FAILURE`: any algebra, event-boundary, one-focal, preview, RNG, or
  unit check fails.

`IDENTITY_SCALE_PASS` advances only to the remaining R2 mapping,
state-sufficiency, and isolated-role gates. It does not require a positive
effect and does not authorise training. If the conditional time-only damage or
paired opportunity is negligible at 30.08 s, C2 must be retained as a QoS
hypothesis or dropped as an EE specialist; no coefficient may be enlarged.
