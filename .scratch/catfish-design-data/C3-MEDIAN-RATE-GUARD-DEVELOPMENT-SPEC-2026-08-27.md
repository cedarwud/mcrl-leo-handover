# C3 median-channel rate-guard development protocol

Status: frozen final guard-development alternative on the already-read seed
`2026082701`. This seed may select a rule but may not validate it. No further
guard family or threshold will be developed on this seed.

Date: 2026-08-27

## Motivation

The 112-D observation-rate proxy selected only 3/20 power-certified candidates
and all three still lost realised throughput. Its state SINR assumes candidate
start power and previous-step interference, so it is an indirect branch proxy.

This final development alternative uses the exact current pre-state and both
joint action branches, but replaces the two random propagation terms with their
declared deterministic reference values:

```text
Rician power gain = 1
shadow loss       = 0 dB
```

All geometry, association/segment state, recurrence power, beam maxima,
interference, load sharing, and fixed actions remain branch-exact. Neither
actual current-slot fading draw nor realised reward/rate/EE/successor is read.

## Single rule

For the already-certified power-relief support, retain a candidate iff

```text
R_median(candidate) - R_median(reference) >= 0.
```

This is a throughput non-inferiority safety filter, not an EE score or ranking
rule. There is no coefficient, margin, subgroup, or threshold sweep.

## Development decision

Report coverage, realised immediate EE and throughput directions, and mean and
median deltas on the already-read seed. It qualifies for a disjoint-seed gate
only if it retains at least two candidates, has positive mean realised EE, and
does not have negative mean realised throughput. Otherwise this rule is
rejected.

If both this rule and the previously developed observation-rate rule qualify,
prefer this median-channel rule because it is branch-exact and directly guards
the physical throughput quantity. If this rule fails, the observation-rate
rule may advance only as an exploratory validation with an explicit actual-
throughput non-inferiority endpoint. No efficacy or training claim follows.
