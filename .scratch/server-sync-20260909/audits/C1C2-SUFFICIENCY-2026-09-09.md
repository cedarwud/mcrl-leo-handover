# C1/C2 feature sufficiency diagnostic — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`

## Verdict first

- **C1 collision found:** yes, at the production target/encoder contract. Two admissible network states have byte-identical 16-scalar Q1 and 22-scalar Q2 rows, while exact `c1_difference_surplus` is `11/10` versus `-33/10`. The gap is `22/5 = 4.4`, so any deterministic scalar predictor on this encoded row incurs squared loss at least `(4.4/2)^2 = 121/25 = 4.84` on one member of the pair. This is a constructed contract-level witness; the separate exhaustive scan of the existing row corpus did not find a naturally occurring C1 collision.
- **C2 collision found:** yes, including a real legacy-provider/evaluator witness. Two production rows for the same user/action at the same physical step have byte-identical Q1 and Q2 inputs, but exact `c2_persistence_forecast` is approximately `5.4095145003632172` versus `19.346696956352321`. The exact gap is approximately `13.937182455989104`, giving a squared-loss lower bound of approximately `48.561263702882613`.
- **Regression witness:** with `PILOT_PRIMITIVE_SOURCE_FALLBACK = True`, the new exact-singleton acceptance test fails; after changing only that flag to `False`, all four C1/C2 checks pass; after restoring it to `True`, the same C1 assertion fails again. The flag is restored to `True` in the final tree, so the test intentionally remains red on the defective path.

No production learner was trained. The only fitted estimator was the Task 3 diagnostic k-nearest-neighbor regressor.

## What the heads actually receive

`src/mcrl/stagec_v025/state.py` defines 16 Q1 features and 22 Q2 features. `src/mcrl/stagec_v025/learner.py:271` implements `LinearHead.score(self, state)` using only that one numeric sequence. No action identity, association map, geometry, cross-gain matrix, coupled-power result, network outcome, projected outcome, provenance digest, action mask, or other auxiliary branch enters the scalar head. The pairwise trainer evaluates the same scalar head separately on the reference and candidate rows.

Accordingly, `head_auxiliary_inputs = []` for both witnesses below. The test `tests/stagec_v025/test_c1c2_feature_sufficiency.py` checks the dimensions, absence of an auxiliary input, byte equality, and unequal exact targets.

## Task 1 — C1 collision

### Two states

Both states use the same focal action `(norad_id=1001, beam_chain_id=7)` and the same production `ActionEvaluation` values: current margin `4 dB`, required power/cap `0.5`, mode SE `2 bit/s/Hz`, one background occupant, active beam and satellite, off-axis angle `0.25 rad`, remaining D2/visibility `60/90 s`, phase 2, previous load one, current power-cap margin `0.825 W`, and three valid/surviving forecast summaries with margins `3, 2, 1 dB` and SE `2 bit/s/Hz`.

Only structure discarded by the encoder changes:

| Quantity | State A | State B |
|---|---:|---:|
| Background associations | user 1→`(1001,7)`, user 2→`(2002,4)` | user 17→`(1001,7)`, user 23→`(2003,2)` |
| Example focal cross gains | `1e-13`, `2e-14` | `8e-11`, `3e-11` |
| Background coupled powers | `0.4 W`, `0.3 W` | `1.4 W`, `1.2 W` |
| Candidate whole-network outcome | 220 bits, 22 J, Phi `-1/2` | 180 bits, 24 J, Phi `-1/2` |
| Shared default outcome | 200 bits, 20 J, Phi `0` | 200 bits, 20 J, Phi `0` |

These values are accepted by the production `NetworkOutcome.build`, `OffsetProjection`, `seal_action_evaluation`, and `extract_source_rows` invariants: bits, joules, powers and capacities are nonnegative; availability is in range; projected powers are below the `1.65 W` cap; offsets are ordered; and forecasts are finite and recompute background power. Different background topology and coupled powers can change whole-network bits and joules while preserving the focal aggregate summaries retained by Q1/Q2. This is a target/encoder-contract admissibility proof, not a claim that these two rows were observed in the legacy tape.

With `eta_ref = lambda = 2` and `kappa = 10`, production `c1_difference_surplus` gives:

```text
C1_A = ((220-200) - 2*(22-20))/10 + (-1/2-0) = 11/10
C1_B = ((180-200) - 2*(24-20))/10 + (-1/2-0) = -33/10
absolute difference = 22/5
squared-loss lower bound = (difference/2)^2 = 121/25
```

### Identical encoded input, byte for byte

Q1 scalar values, in Python hexadecimal float form, for **both** states:

```text
[0x1.999999999999ap-3, 0x1.0000000000000p-1,
 0x1.0000000000000p-1, 0x1.999999999999ap-4,
 0x1.0000000000000p+0, 0x1.0000000000000p+0,
 0x1.0000000000000p-2, 0x1.0000000000000p-1,
 0x1.8000000000000p-1, 0x1.5555555555555p-1,
 0x0.0p+0,                0x1.999999999999ap-4,
 0x1.0000000000000p+0, 0x1.0000000000000p+0,
 0x1.999999999999ap-2, 0x0.0p+0]
```

Q1 as 16 big-endian binary64 values (128 bytes), for both states:

```text
3fc999999999999a3fe00000000000003fe00000000000003fb999999999999a3ff00000000000003ff00000000000003fd00000000000003fe00000000000003fe80000000000003fe555555555555500000000000000003fb999999999999a3ff00000000000003ff00000000000003fd999999999999a0000000000000000
```

Q2 scalar values, for **both** states:

```text
[0x1.999999999999ap-3, 0x0.0p+0,
 0x1.0000000000000p-1, 0x1.8000000000000p-1,
 0x1.5555555555555p-1, 0x1.999999999999ap-4,
 0x1.0000000000000p+0, 0x1.0000000000000p+0,
 0x1.0000000000000p-1, 0x0.0p+0,
 0x1.0000000000000p+0, 0x1.0000000000000p+0,
 0x1.3333333333333p-3, 0x1.0000000000000p-1,
 0x1.0000000000000p+0, 0x1.0000000000000p+0,
 0x1.999999999999ap-4, 0x1.0000000000000p-1,
 0x1.0000000000000p+0, 0x1.0000000000000p+0,
 0x1.999999999999ap-5, 0x1.0000000000000p-1]
```

Q2 as 22 big-endian binary64 values (176 bytes), for both states:

```text
3fc999999999999a00000000000000003fe00000000000003fe80000000000003fe55555555555553fb999999999999a3ff00000000000003ff00000000000003fe000000000000000000000000000003ff00000000000003ff00000000000003fc33333333333333fe00000000000003ff00000000000003ff00000000000003fb999999999999a3fe00000000000003ff00000000000003ff00000000000003fa999999999999a3fe0000000000000
```

### Existing-row negative search for C1

I also scanned all 176,223 source rows in the existing two-world corpus, grouping on the exact concatenated Q1+Q2 tuple. There were 5,230 duplicate groups overall and 4,701 among nonreference rows. Every duplicate was another carrier view of the same physical step; there were no cross-step or cross-world duplicate groups. Exact relabeling of the first carrier pair found no C1 difference. Thus the corpus search alone did **not** find an empirical C1 collision; it neither proves nor suggests sufficiency beyond that finite corpus. The constructed admissible contract witness above is the C1 insufficiency proof.

## Task 1 — C2 collision

### Real evaluator states

This witness comes from the existing real legacy-provider tape `V025_PROBE/world/1`, step 0, user 6, action `(65028,44)`. State A is source anchor 0 with carrier rule `nearest-eligible`; state B is source anchor 1 with carrier rule `stay-if-possible`. The production evaluator and `_batched_stage2_forecasts` recomputed both singleton configurations and their three offsets. Among these two anchors there are 62 exact C2 collision groups.

For the selected group, the candidate/default normalized physical terms at offset 1 are the same in both states:

```text
candidate: bits/kappa=125.63281341025531, eta*joules/kappa=96.27152690774090
default:   bits/kappa=119.31271970410177, eta*joules/kappa=98.36094770195058
valid=1 in both
```

The exact projection says `survives=0` at offset 1 in state A, making later offsets absorbing losses, but `survives=1` at all three offsets in state B. The stored 22-scalar Q2 vectors say valid/surviving at all three offsets in **both** rows, so the head cannot see this difference. Exact production targets are:

```text
C2_A = 60102789335062397912351470235270 /
       11110569965387252983357173269901
     = 5.4095145003632172...

C2_B = 2149528301326970807719944431070731 /
       111105699653872529833571732699010
     = 19.346696956352321...

absolute difference =
  516166802658782276198809909572677 /
  37035233217957509944523910899670
  = 13.937182455989104...

squared-loss lower bound = 48.561263702882613...
```

### Identical real encoded input, byte for byte

Q1 float values for both real states:

```text
[-0x1.8930fea2e94e6p-3, 0x1.2e7506d9e3e5dp-6,
  0x1.e8207e761dbfdp-2, 0x0.0p+0,
  0x0.0p+0,                0x1.0000000000000p+0,
  0x0.0p+0,                0x1.5acb6f46508e0p+0,
  0x1.f92c5f92c5f93p+0, 0x0.0p+0,
  0x0.0p+0,                0x0.0p+0,
  0x0.0p+0,                0x1.0000000000000p+0,
  0x1.2e7506d9e3e5dp-6, 0x0.0p+0]
```

Q1 big-endian binary64 bytes for both real states:

```text
bfc8930fea2e94e63f92e7506d9e3e5d3fde8207e761dbfd000000000000000000000000000000003ff000000000000000000000000000003ff5acb6f46508e03fff92c5f92c5f9300000000000000000000000000000000000000000000000000000000000000003ff00000000000003f92e7506d9e3e5d0000000000000000
```

Q2 float values for both real states:

```text
[-0x1.8930fea2e94e6p-3, 0x1.e6d426f9e31dfp+0,
  0x1.5acb6f46508e0p+0, 0x1.f92c5f92c5f93p+0,
  0x0.0p+0,                0x0.0p+0,
  0x0.0p+0,                0x1.0000000000000p+0,
  0x1.f68c57c930e0dp-1, 0x0.0p+0,
  0x1.0000000000000p+0, 0x1.0000000000000p+0,
 -0x1.88049eca8d9cdp-3, 0x1.e8207e761dbfdp+0,
  0x1.0000000000000p+0, 0x1.0000000000000p+0,
 -0x1.ff9e74e3596bdp-2, 0x1.e8207e761dbfdp+0,
  0x1.0000000000000p+0, 0x1.0000000000000p+0,
 -0x1.720fc11a780aep-1, 0x1.e8207e761dbfdp+0]
```

Q2 big-endian binary64 bytes for both real states:

```text
bfc8930fea2e94e63ffe6d426f9e31df3ff5acb6f46508e03fff92c5f92c5f930000000000000000000000000000000000000000000000003ff00000000000003fef68c57c930e0d00000000000000003ff00000000000003ff0000000000000bfc88049eca8d9cd3ffe8207e761dbfd3ff00000000000003ff0000000000000bfdff9e74e3596bd3ffe8207e761dbfd3ff00000000000003ff0000000000000bfe720fc11a780ae3ffe8207e761dbfd
```

This is a real, simulator-generated physical collision, not merely a finite-precision near-match.

## Task 2 — missing exact-label acceptance test

Added `tests/stagec_v025/test_c1c2_exact_label_acceptance.py`. It uses two real legacy-provider anchors. To keep runtime bounded, each anchor retains one user and three genuine legal singleton configurations: its reference, one nonreference action, and null. It calls production `_build_anchor_rows`, independently evaluates those configurations with `StepEvaluator`, independently generates future projections with `_batched_stage2_forecasts`, and then calls the public production target definitions `c1_difference_surplus` and `c2_persistence_forecast` as the oracle.

The asserted absolute tolerance is `1e-9` in normalized target units with zero relative tolerance. Production targets are exact `Fraction` arithmetic until the row boundary; the comparison crosses two binary64 conversions. `1e-9` is therefore deliberately looser than expected roundoff but more than seven orders tighter than the smallest observed proxy mismatch (`0.03547`). No physics or acceptance constant was changed.

### Required True → False → True witness

1. With `PILOT_PRIMITIVE_SOURCE_FALLBACK = True`:

   ```text
   FAILED test_production_c1_labels_equal_exact_evaluator_singletons[0]
   AssertionError: production C1 label disagrees with exact evaluator singleton:
   anchor=0 user=0 action=(65028, 55)
   actual=0.16304247271668615 exact=0.12756951502457881 abs_tol=1e-09
   ```

   The C2-specific run also fires:

   ```text
   FAILED test_production_c2_labels_equal_exact_evaluator_singletons[0]
   AssertionError: production C2 label disagrees with exact evaluator singleton:
   anchor=0 user=0 action=(65028, 43)
   actual=0.15938602060975687 exact=-3 abs_tol=1e-09
   ```

2. After changing only the flag to `False`:

   ```text
   .... [100%]
   4 passed
   ```

3. After restoring the flag to `True`, the first C1 assertion above fails again with the same actual and exact values.

The exact command was:

```text
nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python \
  -m pytest -q tests/stagec_v025/test_c1c2_exact_label_acceptance.py -x
```

## Task 3 — held-out explainability

The diagnostic `scripts/diagnose_v025_c1c2_sufficiency.py --anchors 30` read existing rows from `artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM/rows/world-1`, then replaced their proxy labels with exact evaluator C1/C2 targets. It retained 26,345 valid nonreference rows from 30 source anchors (10 physical steps × 3 carrier views).

The deterministic seed was `20260909`. Splitting was by whole physical step—not source shard—so byte-identical carrier views could not leak across partitions:

- train steps: 1, 2, 4, 6, 7, 8, 9;
- validation step: 5;
- held-out test steps: 0, 3;
- held-out rows: 5,280.

The Q-only model was standardized inverse-distance k-nearest-neighbor regression with `k` selected from `{1,3,7,15,31}` on the validation step. The comparator was a fitted ordinary least-squares readout given the discarded exact target-sufficient terms: whole-network candidate/default bits, energy and Phi for C1; and per-offset candidate/default bits, energy, validity and survival with the production absorbing rule expanded for C2.

| Route | Q-only held-out EV | Q-only RMSE | Discarded-structure EV | Structure RMSE | EV gap |
|---|---:|---:|---:|---:|---:|
| C1 | `-0.3355476799` | `3.4683937281` | `1.0` | `2.66e-13` | `1.3355476799` |
| C2 | `0.2106516781` | `3.3856461561` | `1.0` | `1.02e-14` | `0.7893483219` |

Selected `k=31` for both routes. C1 held-out target variance was `8.3419683433`; C2 was `14.3690049981`. The fitted structure coefficients recover the production definitions to rounding: C1 coefficients are intercept approximately zero followed by `[+1,-1,+1,-1,+1,-1]`; C2 coefficients are intercept approximately zero followed by `[+1,+1,+1,-1]` for the three live offset surpluses and lost-offset count.

The large empirical gaps say that, on these anchors, the discarded target structure is binding for this flexible Q-only estimator. Negative C1 explained variance means its residual variance exceeds the variance of the held-out targets. These finite-sample scores are not a mathematical upper bound on every possible architecture; the collision pairs, not the regression, provide the formal impossibility and squared-loss bounds.

## Reproduction and files

```text
PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python \
  -m pytest -q tests/stagec_v025/test_c1c2_feature_sufficiency.py

nice -n 15 env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python \
  scripts/diagnose_v025_c1c2_sufficiency.py --anchors 30
```

Changed or added for this diagnostic:

- `C1C2-SUFFICIENCY-2026-09-09.md` (this report)
- `scripts/diagnose_v025_c1c2_sufficiency.py`
- `tests/stagec_v025/test_c1c2_feature_sufficiency.py`
- `tests/stagec_v025/test_c1c2_exact_label_acceptance.py`

No threshold, sign, seed, horizon, price, service guard, or acceptance rule was changed. The fallback flag is restored to its original `True` value solely to complete the requested red/green/red witness.
