# Compact Fable review packet: proposed C2/C3 Multi-Catfish

Status: review input only. No runtime or training authority.

## Architecture

- C1: unchanged R1 `r1_u=R_u/P_system`, RIS-inspired EXP/ACRM.
- C2: temporal-damage Catfish. Candidate reward exactly decomposes the
  one-interval loss between steady-state EE and a time/energy handover ledger.
  R2 physics remains not closed because `E_HO` and the primary mapping are
  unresolved.
- C3: spatial-power Catfish. All Catfish act only during training; Main MODQN
  is the only deployed policy. Streams mix complete executed transitions, not
  action votes; no auction/coordinator exists.

## Proposed R3 reward

For served user `u`, remove only that user while holding all other executed
actions fixed:

```text
P_minus_u = system power without u
d_u       = P_system - P_minus_u
r3_u      = -d_u  [W]
```

Analytically, if its beam load exceeds one, `d_u` is the PA supply difference
between the beam maximum and the maximum after removing `u`. If it is the only
user, `d_u` also contains beam circuit power and, for the satellite's last
beam, baseband power. The sum over users is not `-P_system`.

For two service-preserving focal actions with all other actions fixed:

```text
r3_u(a') - r3_u(a) = P_system(a) - P_system(a').
```

Thus local reward direction exactly matches unilateral system-power direction.
Execution-infeasible valid actions receive a model-derived `-C_out`, but this
is accounting only; hard/lexicographic service safety remains required.

## Proposed C3 action mechanism

Reference: focal continues its incumbent (`NONE`). Candidate: one legal
different beam on the same satellite (`phi1`), destination already active.
Source stays active, focal is its strict unique power maximum, candidate power
does not exceed destination maximum, all other actions/link powers and the
served/active sets remain fixed. Then the live PA formula certifies:

```text
Delta P_system
  = P_supply(p_source_next) - P_supply(p_source_max) < 0.
```

C3 deliberately incurs `phi1`; that temporal cost stays in the full vector and
must be evaluated through R2 rather than hidden.

## Evidence and fixed development decisions

Legacy-narrow seed `2026082701`, 1,000 user-steps:

- 9 source-qualified states, 21 candidates, 20 power-certified, zero identity
  failures, maximum power residual `8.97e-14 W`;
- mean power delta `-0.4748 W`;
- power-only: 5/20 immediate EE positive, mean `-569629 bit/J`; 18/20 throughput
  negative. Therefore power-only C3 is rejected as EE-safe.

Observation-SINR joint-rate guard, prespecified without threshold:

- retained 3/20; 2/3 EE positive; mean EE `+4332 bit/J`;
- all three realised throughput-negative. It only weakly qualified for an
  exploratory disjoint-seed gate under its own development protocol.

Median-channel branch-exact throughput guard: evaluate both branches at Rician
gain 1 and shadow loss 0 dB, retain only predicted throughput-noninferior
candidates:

- retained exactly 5/20 and all 5 were immediate-EE positive;
- mean EE `+78422 bit/J` (`+0.0868%` relative);
- mean power `-0.1480%` relative;
- mean realised throughput `-32.1 Mbps` (`-0.0614%` relative), with 2 positive
  and 3 negative rows.

Its frozen development protocol required nonnegative mean realised throughput,
so its formal decision is `REJECT_MEDIAN_RATE_RULE`. No pre-existing project
throughput non-inferiority margin was found; inventing one from these five rows
is forbidden.

## Open structural gates

- Main state is 112-D and lacks segment-start gain and exact current link/beam
  power. C3 can use an exact training-only eligibility mask, but Main transfer
  may face observational aliasing.
- C3 changes `NONE` to `phi1`; the accepted temporal ledger and `E_HO` do not
  yet exist.
- Non-focal marginal rewards also change and may update their unchanged local
  actions in Main replay.
- Factorial off slots use uniform random actions from identical post-safety
  support, so effects mean informed selection versus matched random.

## Questions requiring a verdict

Choose exactly one verdict:

- `PASS_TO_NEXT_SHADOW`: a specifically defined disjoint-seed, non-training
  gate is scientifically justified;
- `REVISE`: reward/mechanism or safety/transfer design needs exact changes
  first;
- `DROP_C3`: this path is no longer credible as an EE Catfish.

Answer these points:

1. Is marginal R3 physically and causally valid for Main and C3?
2. Must the rejected median rule remain rejected, or can it be validated on new
   seeds under a claim limited to EE plus disclosed throughput? No post-hoc
   margin may be introduced.
3. What exact temporal constraint is possible before `E_HO` closes?
4. Is hidden-state aliasing fatal or testable? Specify the smallest test.
5. Give fatal/major issues, the next minimal non-heavy experiment, and the
   current claim ceiling. Do not authorise implementation or training.
