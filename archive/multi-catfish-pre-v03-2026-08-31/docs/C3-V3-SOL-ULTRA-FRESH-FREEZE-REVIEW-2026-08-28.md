# C3 V3 Sol Ultra fresh-context freeze review

Date: 2026-08-28  
Review type: read-only, fresh-context, pre-outcome design audit  
Model: GPT-5.6 Sol, reasoning effort ultra  
Verdict: `FREEZE_STAGE0_SPEC`

## Independent conclusion

The reviewer found the revised C3 design coherent and preferable to the simpler
compliant alternatives considered:

- strict-load-only would lack an EE safeguard;
- mandatory strict power decrease would wrongly discard the power-tied,
  useful-bit-improving path;
- a one-step or no-release certificate would miss delayed reversal; and
- a direct power/EE reward would violate C3's canonical-`r_3`-only role.

The frozen mechanism is therefore:

```text
same-satellite high-load -> low-load already-active relocation
  + exact canonical system-r3 identity
  + H=3 and first release
  + complete power nonincrease at every offset
  + useful-bits nonloss and strict forecast ratio-of-sums EE surplus
  -> Q3-only canonical donor, if later dual observability/routing gates pass
```

The review also confirmed that C2 and C3 are not the same mechanism. C2 begins
where scalarized Main leaves an incumbent and tests temporal activation/event
churn; C3 begins where Main continues a source and tests spatial load
redistribution.

## Review-triggered closure

During the audit, the C3 specification was corrected to gate the executed
decision-relevant distinction separately for specialist `Q_3^F` and Main
consumer `Q_3^M`. The pure validator now exposes both observation channels.
Neither gate is currently passed; C3 remains shadow-only and `beta_3=0`.

The reviewer recommended freezing the same opportunity threshold as C2 before
any census: five partitions, steps `1..6`, five focal users per step, all 150
rows retained, at least one two-choice certified anchor per partition, and at
least 20 in total. Controller follow-up added that rule prospectively and added
exact-coverage/floor fixtures. This follow-up implements the review
recommendation; the reviewer did not inspect any census result because none
exists.

Current post-follow-up bindings:

| Surface | SHA-256 |
|---|---|
| C3 V3 specification | `f338c4cbc980ffca4fcf79ad97a1001c665c0e6418af9a907a2c53dfa7c5fe0d` |
| C3 V3 pure core | `24c0a54b2fccdaaf48e8fdeff89fe5fbaa01348e19242e833534e3f7b7d23801` |
| C3 V3 focused tests | `e5d30c2246a15abb2d5f265c05de3bf5293b313d2aed7fa6024fcf630f8b438f` |
| role-targeted updater | `3d7e488deda216f34e24a4ad587d78b52f652a36e195119092948be158c0b6b3` |
| updater/evaluator tests | `44665da9e527cc374ce09fdda7ce344cd290e0608402b4e5d75ffabecdf9b04f` |

The current focused C3 core suite passes `52` tests; the diagonal
updater/evaluator suite passes `43` tests.

## Remaining gates

`FREEZE_STAGE0_SPEC` freezes design semantics only. Before a shadow census:

1. add and test a canonical read-only adapter and complete top-level runner;
2. close checkpoint-backed scalarized-Main forks, deep-twin equality and
   fingerprints, recurrence/PA/fixed-power ledger, preview/commit parity,
   repeatability, no-overwrite, and no-seed/no-outcome guards; and
3. closure-bind the partition IDs, deterministic focal permutation, RNG
   namespaces, files, and hashes.

Before any C3 learning or routing, both specialist and Main observability gates
must independently pass. If either fails, the smallest permitted redesign is
one preregistered, decision-time-computable pre-action load/forecast sufficient
statistic exposed identically to `Q_3^F` and `Q_3^M`; post-action eligible load
may not leak backward.

Before any outcome-bearing route, production reference equivalence,
source-age/behavior provenance, resume, and atomic-checkpoint restoration also
remain required. Two-phase ledger admission is tested, but an exception may
still require restoration from the exact pre-update checkpoint.

## Claim ceiling

Allowed: a prospective, falsifiable, one-to-one three-role design with tested
validator/updater primitives and a conditional exact C3 canonical-`r_3` plus
forecast-EE certificate.

Not allowed: adequate V3 support, current-state learnability, routing readiness,
transfer, realised or fresh-seed EE improvement, singleton acceptance, C123
superiority, stochastic non-degradation, training readiness, effectiveness, or
novelty. Formal training remains NO-GO.
