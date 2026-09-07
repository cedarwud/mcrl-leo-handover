# C3 reward-aligned Stage-0 core gate

Date: 2026-08-28  
Status: deterministic validator primitives PASS; canonical adapter, support
census, consumer/observability gate, learner, routing, and efficacy remain
NO-GO

## Implemented scope

The prospective C3 V3 design is bound to:

- `.scratch/catfish-design-data/C3-REWARD-ALIGNED-STAGE0-SPEC-V3-2026-08-28.md`;
- `.scratch/catfish-stage0/c3_reward_aligned_v3_core.py`; and
- `.scratch/catfish-stage0/test_c3_reward_aligned_v3_core.py`.

The pure module imports only the Python standard library. It does not open an
environment, checkpoint, filesystem artifact, RNG, seed manifest, learner,
optimizer, replay, census, or outcome. It validates caller-supplied canonical
facts; it does not implement a second reward, link-budget, or power model.

The implemented validator primitives cover:

- exact `(0.5, 0.3, 0.2)` scalarization and stable masked-greedy tie behavior;
- unique physical-ID remapping, same-satellite/already-active relocation,
  three forced intervals, and first release verified against separately
  supplied scalarized-Main actions;
- exact eligible-load reconstruction, `-sum_b U_b^2`, the integer `+2` load
  guard, and the one-user system-`r_3` delta;
- recurrence maximum, PA supply, circuit, baseband, fixed, and complete system
  power identities from supplied terms;
- complete-power nonincrease at all four offsets, allowing an equality-only
  power window at this layer;
- useful-bits nonloss and strict EE surplus, including the power-tied path in
  which useful bits must strictly increase;
- hold and through-release system-`r_3`, service, re-entry, event, non-focal
  action, active-set, and preview/commit checks;
- nested SAFE/LOAD/CERT support, identical CERT/GAP membership, and GAP ranking
  by direct load gap plus frozen physical ID only; and
- separate specialist/Main observational-alias detection and `C3-I` absence at
  Stage-0; and
- top-level candidate-certificate composition that retains the first failing
  layer and its offset instead of collapsing failures into a bare Boolean; and
- exact five-partition schedule coverage plus the preregistered per-partition
  and pooled 20-anchor two-choice support floor, without imputation.

Controller hardening rejects truthy non-Booleans, Boolean numeric power/proxy
fields, negative useful bits, duplicate GAP support IDs, malformed or
dimension-drifting observations, missing recurrence terms, and omitted fixed
power components.

## Verification

```text
.venv/bin/python -m pytest -q \
  .scratch/catfish-stage0/test_c3_reward_aligned_v3_core.py
```

Result: `55 passed`.

The broader current/nonsealed C2/C3 and diagonal-updater regression passed
`271` tests. One preserved historical scalarized-C2 closure test separately
refused its drifted legacy method digest, as its fail-closed seal requires.

| File | SHA-256 |
|---|---|
| C3 V3 specification | `f338c4cbc980ffca4fcf79ad97a1001c665c0e6418af9a907a2c53dfa7c5fe0d` |
| C3 V3 pure core | `89e4663db80b7c1bacd900bb3264e628a787e9604e36c8e5e68166c4041171e3` |
| C3 V3 focused tests | `c23a396cdd9abc0b74c1af3912094a8ba0a37f3a87cfefd765eeabc86e911cfe` |

## Claim ceiling and remaining gates

This gate supports only: the tested pure validator primitives behave as
declared on deterministic positive and negative fixtures. It does not yet
support the broader statement that the complete V3 Stage-0 semantics pass.

Before a support census, the following remain required:

1. a canonical read-only adapter exposing the complete recurrence/power ledger
   without reimplementing physics;
2. checkpoint-backed scalarized-Main action receipts for both forks;
3. anchor reconstruction, deep-twin field equality and fingerprints;
4. preview/commit, deterministic repeatability, import/call, no-overwrite, and
   no-seed/no-outcome guards; and
5. closure-bound partition IDs, focal permutation material, RNG namespaces,
   and hashes for the already-frozen 150-row/20-anchor floor.

Even a later positive census would establish only pre-outcome opportunity
frequency. C3 remains shadow-only, effective `beta_3=0`, and formal training is
NO-GO until the specialist and Main consumer can observe the relevant
decision-time distinction and all routing gates pass.
