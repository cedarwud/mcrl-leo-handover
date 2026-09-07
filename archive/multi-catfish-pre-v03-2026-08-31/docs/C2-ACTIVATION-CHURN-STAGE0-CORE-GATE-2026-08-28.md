# C2 activation-churn Stage-0 core gate

Date: 2026-08-28  
Status: deterministic semantic core PASS; operational runner, support census,
learner, Main routing, and efficacy remain NO-GO

## Implemented scope

The prospective V3 design is bound to:

- `.scratch/catfish-design-data/C2-ACTIVATION-CHURN-STAGE0-SPEC-V3-2026-08-28.md`;
- `.scratch/catfish-stage0/c2_activation_churn_core.py`; and
- `.scratch/catfish-stage0/test_c2_activation_churn_core.py`.

A separate read-only canonical-runtime seam now exists at
`.scratch/catfish-stage0/c2_activation_churn_runtime_adapter.py`. It verifies
the exact scalarized-Main weights before inference, receipts the complete
Q-table/mask/action surface, and projects an existing canonical action
evaluation into the power-identity core by calling the canonical PA functions.
It does not implement a second power model or select a C2 candidate.

The core contains no environment, checkpoint, filesystem, RNG, learner,
replay, runner, seed, or outcome dependency. It validates supplied canonical
values and does not implement another link-budget, power, or reward model.

The executable semantics cover:

- physical-ID remapping and the incumbent-hold or one-relocation-plus-hold
  grammar over `H=3` and first release;
- exact reference-only beam and satellite `off -> on -> off` identities;
- the pulse-or-lower-complete-energy mechanism condition without treating a
  pulse as an energy result;
- reconstruction of beam maxima, PA supply, circuit, baseband, fixed, and
  complete system-power identities from supplied canonical terms;
- strict system-total canonical `r_2` improvement during the hold and still
  through first release, including explicit release-event, outage, re-entry,
  and served-to-unserved guards;
- useful-bits nonloss and strict EE-surplus as binary pre-outcome membership
  tests only;
- layer-order, candidate-order invariance, and the declared
  `C2-PERSIST-R`/`C2-STAY`/`C2-CHURN-CERT-R` supports, with `C2-I` unavailable
  at Stage-0; and
- the five-partition, at-least-20 two-choice-anchor support floor without
  imputation.

Controller review added fail-closed validation for Boolean receipt fields,
negative useful bits, Boolean layer evidence, and invalid support-floor
parameters. Fable Max follow-up also corrected first-failure ordering: a failed
hold interval is now receipted before a later missing-release failure. The
prospective census schedule was shifted from structurally ineligible reset step
`0` to steps `1..6`, retaining 150 attempts without a known-zero denominator.

## Verification

```text
.venv/bin/python -m pytest -q \
  .scratch/catfish-stage0/test_c2_activation_churn_core.py
```

Result: `43 passed`.

The core plus runtime-seam command passes `51` tests:

```text
.venv/bin/python -m pytest -q \
  .scratch/catfish-stage0/test_c2_activation_churn_core.py \
  .scratch/catfish-stage0/test_c2_activation_churn_runtime_adapter.py
```

A combined non-outcome regression covering the current C2/C3 primitives, the
role-targeted Main updater, ratio-of-sums evaluator, and preserved historical
adapter surfaces passed `268` tests. One additional historical scalarized-C2
closure test correctly refused the now-drifted legacy method digest; it was not
relabelled as a current pass or repaired by changing its frozen digest.

| File | SHA-256 |
|---|---|
| C2 V3 specification | `427d24de673b3bd76b5e3cd1e343dd003247a04d2193567e659525558b660c08` |
| C2 V3 pure core | `0d7f85714779366cf8c18ca07adbb9f7ac0367cb34deef28f24a5134ee3f15d1` |
| C2 V3 core tests | `cf8cb3d1ab032266430f26b2a9697886e3d6c680fb4a015375664aa80ad4ea11` |
| C2 V3 runtime adapter | `61a93feea69d4411fbcbbb970c709a22a69f0585937b56472a962f27342f6dc9` |
| C2 V3 runtime-adapter tests | `c35647454947eca44c6d432be8be7e902f76b3a86a1329a951f837b78e7e7582` |

## Remaining gates

The following are intentionally not closed:

1. loading the corrected checkpoint into the already-tested scalarized-Main
   seam inside a complete anchor runner;
2. anchor reconstruction, twin equality, domain-separated RNG, preview/commit
   parity, closure hashing, no-overwrite output, and repeatability fixtures;
3. canonical runtime adapter and complete V3 runner;
4. frozen 150-row support census and its two-choice floor;
5. C2 observational-alias, action-pivotality, and atomic-bundle consumer gate;
6. learned `Q_2^F` versus same-certified-support random and stay controls; and
7. fresh-seed Main-only ratio-of-sums EE and canonical `r_2` efficacy.

Therefore this gate establishes implementable, falsifiable C2 semantics only.
It does not establish support frequency, learnability, EE improvement, or a
successful second Catfish.
