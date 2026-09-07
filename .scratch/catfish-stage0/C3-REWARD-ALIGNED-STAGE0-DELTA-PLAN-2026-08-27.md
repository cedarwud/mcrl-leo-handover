# C3 reward-aligned Stage-0 delta plan

Date: 2026-08-27  
Status: bounded pure-core implementation authorized; no operational runner,
scientific execution, seed reveal, or Main-consumer authority.

The bounded implementation surface is only
`.scratch/catfish-stage0/c3_reward_aligned_core.py`, its targeted test module,
and the v2 specification. It establishes fail-closed engineering semantics for
later runner work; passing those tests is not scientific evidence.

## Why the current runner cannot be executed

The existing `run_c3_stage0.py`, tests, and
`C3-PERSISTENT-POWER-STAGE0-SPEC-2026-08-27.md` are sealed around a
power-primary C3. The current proposed method instead makes canonical
`r_{3,u}=-U_{s,v}` the direct C3 reward and demotes power to a separate
certificate/safeguard/diagnostic. Running the old closure would answer the
wrong question even if every test passed.

## Keepable infrastructure

- exact reset-and-prefix replay;
- common-anchor fingerprints;
- independent forecast and realised RNG namespaces;
- physical-ID remapping after candidate-table rebuilds;
- preview/commit parity;
- non-focal physical-action equality;
- branch retention regardless of outcome sign;
- eligible-load and ungated-demand capture;
- served-user, active-beam, active-satellite, event, power, rate, and EE logs;
- five-seed disjointness and fail-closed closure manifests.

These surfaces require new hashes and tests. Their presence does not allow the
old formal closure or old revealed seeds to be reused.

## Required semantic replacements

| Old Stage-0 surface | Reward-aligned replacement |
|---|---|
| strict unique source power maximum | hard-safe same-satellite source/destination pair; not a role objective |
| source load at least two | reference-fork pre-move eligible loads satisfy `U_{s,v}(h) >= U_{s,v'}(h)+2` at every certified interval |
| top cumulative avoided payload energy | simple `C3-GAP` reference ranks largest eligible-load gap; power relief is a tie-breaker only |
| power/EE t95 as the direct pass endpoint | extended canonical `r3` through first release and episode total is primary |
| `C3-RANK-R` / old `C3-CERT-R` pair | `C3-SAFE-R`, `C3-LOAD-R`, `C3-CERT-R`, and `C3-GAP` support/ranking ladder |
| three-interval outcome only | retain the certificate window, then continue through first post-release interval and episode end |
| one joint power filter count | separate hard-safe, load-only, power-only, joint-pass, and sign-disagreement counts |
| unconditional implementation promotion | separate Main-consumer gate; C3 remains shadow-only unless that gate passes |

## Exact construction identity

For a reference-fork move from `(s,v)` to `(s,v')`, source eligible load
includes the focal user and destination eligible load excludes it. With all
non-focal associations fixed,

```text
Delta sum_u r_{3,u}(h)
  = 2 * (U_{s,v}(h) - U_{s,v'}(h) - 1).
```

The integer strict-improvement condition is

```text
U_{s,v}(h) >= U_{s,v'}(h) + 2.
```

The runner must assert this identity directly from post-feasibility
`eligible_load_by_beam`; `demand_by_beam` is logged only for the consumer-gap
diagnostic and must not substitute for eligible load.

## Certificate layers

1. **Hard-safe support:** same satellite, different already-active physical
   destination, valid/service-feasible focal holds, physical-ID continuity,
   identical non-focal actions, and unchanged served/active sets.
2. **Load support:** the exact `+2` condition holds at every certified interval.
3. **Power safeguard:** reference system power minus candidate system power is
   nonnegative at every interval and strictly positive at least once.
4. **Joint certificate:** hard-safe + load + power + declared event conditions.

Load and power statistics have different units. The runner must never add them
or expose a combined learning reward.

## Non-learning arms

- `reference`: focal user retains the source association.
- `C3-SAFE-R`: uniform hard-safe destination.
- `C3-LOAD-R`: uniform strict-load destination before the power safeguard.
- `C3-CERT-R`: uniform destination from the joint certificate.
- `C3-GAP`: maximum eligible-load gap inside the joint certificate, then
  larger forecast power relief, then physical ID.

`C3-I` is not a Stage-0 arm because Stage-0 contains no learner. It belongs to
the later matched pilot and must be compared with both `C3-CERT-R` and
`C3-GAP`.

## Outcome and gate separation

- Within-certificate `r3` gain is a construction assertion, not a statistical
  result and not a t-test endpoint.
- Primary empirical Stage-0 readout: paired cumulative canonical `r3` through
  the first post-release interval and over the episode.
- Supporting readouts: payload energy, ratio-of-sums EE, useful bits, service,
  and additional `phi1/phi2` events.
- A negative supporting EE result must be reported as such; it cannot be
  relabelled as an EE-helpful C3.
- Main routing is evaluated separately. The present Main state exposes lagged
  ungated demand while C3 uses current eligible load; no Stage-0 role result
  alone authorizes C3-to-Main transfer.

## Files that must be superseded together

- `.scratch/catfish-design-data/C3-PERSISTENT-POWER-STAGE0-SPEC-2026-08-27.md`;
- `.scratch/catfish-stage0/run_c3_stage0.py`;
- `.scratch/catfish-stage0/test_run_c3_stage0.py`;
- C3 hash/schema dependencies inside `.scratch/catfish-stage0/run_c2_stage0.py`
  and its tests;
- seed/closure manifests and every expected SHA-256 constant.

Do not patch these operational surfaces incrementally before the reviewed
method snapshot is fixed. The bounded pure core is not that replacement. The
operational replacement must use a new schema version, new RNG namespaces, and
wholly new gate seeds revealed only after the new closure is hashed.
