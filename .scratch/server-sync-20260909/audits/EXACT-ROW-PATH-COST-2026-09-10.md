**AFFORDABLE:** for the measured 992-source-row anchor workload, the exact path costs **49.03 s per anchor**, **57.79×** the primitive surrogate's 0.848 s; at 20 anchors × 12 seeds × 9 arm-owned catalogues with no cross-arm reuse, that is **29.42 serial worker-hours** (before shared-cache savings).

# Exact row path cost — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`

No production training run, policy run, or acceptance test was performed. No constant, threshold, sign, seed, horizon, price, guard, acceptance rule, sealed artefact, manifest, or contract was changed. In particular, `PILOT_PRIMITIVE_SOURCE_FALLBACK` remains exactly `True` at `scripts/run_v025_pilot_c3.py:89`; the measurement asserts that value before and after every build. The only writes are this report and `.scratch/exact-row-path-cost/{measure.py,results.json}`. Pre-existing workspace changes were left alone.

The affordability statement is for the measured **source-row component** at this row density. It excludes optional coalition-row/catalogue work (`include_coalition=False`), tape construction, training, learned scoring, realised endpoints, policy continuation, and acceptance. Those exclusions are material and are stated again under “Not reached.”

## Q1. The correct path exists and passes the exact targets through

### Read from code

The dispatcher is `_build_anchor_rows` at `scripts/run_v025_pilot_c3.py:525-543`. Its current constant sends execution to `_build_anchor_rows_primitive`. The dormant branch begins at line 544 and is a real, executable exact route:

1. It constructs the base, incumbent, per-user action configurations and a deduplicated configuration map (`scripts/run_v025_pilot_c3.py:544-565`).
2. It uses `StepEvaluator` on each complete 100-user configuration at the current step, not on the focal link in isolation (`scripts/run_v025_pilot_c3.py:549-569`). The dense evaluator supplies whole-configuration bits, joules, served-user flags, required power, decoding margin and ACM spectral efficiency (`.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:793-901`).
3. It calls the engine's production `_batched_stage2_forecasts` for every valid configuration (`scripts/run_v025_pilot_c3.py:570-579`). That function repeats the full configuration evaluation at offsets 1, 2 and 3 (`.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:1592-1626`). `valid` is exactly “the full profile exists”; `survives` is exactly “the profile exists and every user whose assignment differs from that offset's transition is in `served_phy`” (`run_v025_matrix_probe.py:1563-1589,1627-1638`).
4. It calls the production `c2_persistence_forecast` on the candidate and base projections (`scripts/run_v025_pilot_c3.py:599-607`). That target applies the absorbing rule and the per-lost-offset penalty (`src/mcrl/physics_v025/targets.py:251-310`).
5. It copies `row.valid`, `row.survives`, the evaluated future margin and the evaluated future ACM efficiency into `ForecastObservation` without transformation (`scripts/run_v025_pilot_c3.py:665-672`). `extract_source_rows` then serializes the validity and survival booleans verbatim into Q2 (`src/mcrl/stagec_v025/state.py:414-433`).
6. Its C1 physical target is also exact, though the formula is inlined rather than routed through `c1_difference_surplus`: it uses the candidate-minus-base whole-network bits and joules (`scripts/run_v025_pilot_c3.py:608-610`) and the rekey-aware Phi difference (`scripts/run_v025_pilot_c3.py:612-620`).
7. If coalition rows are requested, the exact branch evaluates the catalogue, ranks valid pairwise coalitions using the exact factor scores, and builds a coalition row (`scripts/run_v025_pilot_c3.py:739-787`). `build_coalition_row` calls the production `coalition_identity` target (`src/mcrl/stagec_v025/coalitions.py:391-425`). This optional branch was read but deliberately excluded from the minimum cost benchmark.

One naming clarification: `matched_anchor_decomposition` is imported by the pilot, but it is **not** a source-row target. It is called later in evaluation/reporting at `scripts/run_v025_pilot_c3.py:1790-1805`. The row builder's production target calls are the forecast/C2 route above and, when enabled, `coalition_identity`; C1 is the exact production formula inlined.

### Verified by running code

For each of the two exact builds, the harness retained the production forecast objects and asserted the encoded Q2 validity and survival values against them for every row and offset. It checked `992 rows × 3 offsets × 2 flags = 5,952` flags per anchor with no mismatch (`.scratch/exact-row-path-cost/measure.py:77-90,127-139,181-187`). This verifies the pass-through in execution as well as by inspection.

### Precisely what the primitive route avoids

An “evaluation” below is one **complete configuration at one physical boundary**, the unit incremented by `EvaluationCounter.boundary_evaluations` (`run_v025_matrix_probe.py:793-901,1028-1032`). It is not a focal-user gain lookup.

On both measured anchors the exact route produced 992 source rows: 100 reference rows and 892 non-reference rows. It deduplicated these to 894 current complete configurations, evaluated those 894 at boundary 0, and evaluated the same 894 at each of the three future offsets:

```text
current:   894 configurations × 1 boundary =   894
forecast:  894 configurations × 3 offsets  = 2,682
total:                                      = 3,576 configuration-boundary evaluations
```

That is 3.605 evaluations per emitted row (`3,576 / 992`) or 4.009 per non-reference row if the shared reference work is charged to the 892 non-reference rows. The reference configuration and any other identical configuration IDs are cached rather than reevaluated.

The primitive route evaluates only the current base configuration. Because it calls scalar `StepEvaluator.evaluate(base)` (`scripts/run_v025_pilot_c3.py:383-390`), that one configuration traverses all 48 physical boundaries, giving 48 configuration-boundary evaluations per anchor. Every candidate-current and candidate-future value is then produced from provider-array lookups and focal nominal-gain ratios (`scripts/run_v025_pilot_c3.py:323-352,398-465`); it performs **no candidate whole-configuration evaluation and no future whole-configuration evaluation**. Its measured evaluation cost is therefore `48 / 992 = 0.0484` per emitted row. The exact/primitive evaluation-count ratio is `3,576 / 48 = 74.5×`.

The avoided work is the coupled 100-user evaluation—candidate assignment matrix, interference/background recomputation, coupled RF power certificate, served set, bits, joules, margins and ACM modes—once now and once at each of three future steps for every distinct configuration. The surrogate substitutes focal geometric legality and nominal-gain arithmetic for all of it.

## Q2. Measured cost

### Minimum real configuration

The benchmark used:

- real world `V025_PROBE/world/1`, fixed world seed `5261619120743994529`;
- 100 users and the real `LegacyWorldProvider(role="pilot-source")`;
- four tape steps, the minimum needed for anchor step 0 plus offsets 1, 2 and 3;
- exact setting `a-r0`, nominal field, production shortlist, boundary 0, and the existing inherited calibration;
- anchors 0 and 1: the same physical step with `nearest-eligible` and `stay-if-possible`, respectively;
- 992 source rows per anchor (100 reference, 892 non-reference);
- `include_coalition=False` and `full_legal_actions=False`, the smallest options that exercise the real source-row and production C1/C2 forecast path.

Each path/anchor ran in a fresh child process. Tape construction happened before measurement. Native resident memory was sampled from `/proc/self/status` every 1 ms during the builder; “incremental peak” is peak RSS minus the immediately pre-builder RSS (`.scratch/exact-row-path-cost/measure.py:49-74,142-220`). Absolute peak RSS includes the already-resident tape and imported engine; incremental RSS is more directly attributable to the row build. Timings are single measurements, not confidence intervals.

| Anchor / carrier | Path | Row wall time | Complete configuration-boundary evaluations | Peak RSS | Incremental peak RSS | Exact/primitive wall ratio |
|---|---:|---:|---:|---:|---:|---:|
| 0 / nearest-eligible | primitive | 0.8361 s | 48 | 810.63 MiB | 15.41 MiB | — |
| 0 / nearest-eligible | exact | 49.7626 s | 3,576 | 854.81 MiB | 58.56 MiB | 59.52× |
| 1 / stay-if-possible | primitive | 0.8607 s | 48 | 812.32 MiB | 15.29 MiB | — |
| 1 / stay-if-possible | exact | 48.2874 s | 3,576 | 854.71 MiB | 57.64 MiB | 56.11× |
| **Two-anchor mean** | **primitive** | **0.8484 s** | **48** | **811.47 MiB** | **15.35 MiB** | — |
| **Two-anchor mean** | **exact** | **49.0250 s** | **3,576** | **854.76 MiB** | **58.10 MiB** | **57.79×** |

The absolute peak-RSS ratio is only 1.053× because the approximately 796 MiB pre-builder tape/engine baseline dominates. The exact builder's incremental peak is 3.79× the primitive builder's. Fresh four-step tape construction took 25.41–27.53 s (mean 26.35 s) but is excluded from both row-path timings; a shared resident tape is common setup, not a reason to choose incorrect labels.

### Exact reproduction

```bash
cd /home/sat/mcrl-v025-c1c2suff-ws
nice -n 15 env PYTHONPATH=src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/exact-row-path-cost/measure.py
```

Machine-readable output is `.scratch/exact-row-path-cost/results.json`. At the time of this report:

```text
measure.py  SHA-256 031855957cb4386499663c69702c4429e8cfc71c74c88f8d9d4604dd162b1361
results.json SHA-256 9b55e774c1575e3f9a9c81349160f08e7e56be717c536f6f328051c6b5370640
run_v025_pilot_c3.py SHA-256 95103bb96caaa130659fa0d509f19409574b406798a173e278a7d9dac12b7435
```

The exact worker does not edit or assign the pilot constant. It executes the existing `_build_anchor_rows` code object with a private globals dictionary in which only the diagnostic dispatch lookup is false (`.scratch/exact-row-path-cost/measure.py:112-124`), while repeatedly asserting the module/source value remains true (`measure.py:142-146,181-182`).

## Q3. Projection to the nine-arm panel

### Stated assumptions

I used the previously specified matched-anchor tier of 20 anchors for each of 12 seeds, hence `20 × 12 = 240` anchor-seed pairs and `240 × 9 = 2,160` arm-anchor-seed builds. This is not a projection from one anchor: the per-anchor input is the mean of the two real anchors above. It is nevertheless a narrow projection from one world and one physical step, and assumes each coming arm catalogue has the measured 992-row/894-configuration density.

With **no cross-arm configuration reuse**:

```text
exact wall       = 2,160 × 49.025035 s = 105,894.08 s = 29.415 h
primitive wall   = 2,160 ×  0.848375 s =   1,832.49 s =  0.509 h = 30.54 min
surrogate saving = 2,160 × 48.176660 s = 104,061.59 s = 28.906 h

exact evaluations       = 2,160 × 3,576 = 7,724,160
primitive evaluations   = 2,160 ×    48 =   103,680
surrogate evaluations saved             = 7,620,480
```

That 29.42-hour source-row component is affordable: it is roughly a serial worker-day plus five hours, is batchable, and does not justify training on known-wrong targets. Peak memory is per concurrent worker, not multiplied when builds are serial.

The stipulated shared physical cache can reduce the total, but “each arm has its own seed and catalogue” means it is unsound to assume ninefold reuse. A cache hit is valid only for an identical full evaluation context, not merely the same focal action. With the unmeasured extreme of perfect nine-arm whole-build reuse, the arithmetic lower bound would be `240 × 49.025035 s = 11,766.01 s = 3.268 h` exact and `240 × 0.848375 s = 203.61 s = 3.39 min` primitive. This is a lower bound, **not** the forecast: the actual position between 3.268 and 29.415 hours depends on the union of full configuration/context keys across the nine arm-owned catalogues. The current measurement did not build that union.

For a different anchor or seed count, the no-reuse source-row estimate is:

```text
exact seconds     = anchors × seeds × 9 × 49.025035
primitive seconds = anchors × seeds × 9 × 0.848375
```

The primitive path would save the hours above only by changing training features and labels. That is not an admissible saving.

## Q4. Is there a sound middle?

Yes, but only where it is observationally equivalent to the exact route.

1. **Cache complete evaluations by complete context.** A sound key must bind the world/tape and step, boundary set, field, setting/run-setting, complete assignment, transition/incumbent, and rekeyed-user context. Cache the exact `EvaluatedProfile`, then derive validity, the changed-user set and survival from the correct offset transition. This is exact reuse across duplicate rows and overlapping arm catalogues. The existing per-anchor exact builder already deduplicates configuration IDs and its `StepEvaluator` caches profiles (`run_v025_matrix_probe.py:788-805,897-905`); a panel-wide cache can extend that idea without changing a value.
2. **Evaluate the union, not each arm's duplicates.** Preserve every arm's seed, proposal, catalogue membership and scores. Form the union of exact full-context keys across the nine catalogues, batch each unique key once, then let every arm look up the identical exact result. This is sound. Deduplicating only by focal `(user, action)` is not sound because the background configuration and transition determine the result.
3. **Build exact rows only for rows that really enter training** if—and only if—the cheaper prefilter is proven not to affect inclusion, sampling weights, reference choice, catalogue construction, any input feature, or any label. Rows that are certainly discarded and have no upstream selection effect need no target. Using the primitive value to decide which rows survive the filter is circular and unsound.
4. **Proven invalid short-circuits may be possible.** If a configuration can be proven invalid by the exact evaluator's own preconditions, it can receive the exact invalid projection without running the coupled solver. Geometric legality being true is not such a proof of validity, and the existing primitive predicate is already known not to match. This optimization needs a differential proof before use; it was not implemented here.
5. **Absorption alone does not currently justify dropping later evaluations.** After a failure the C2 scalar target stops consuming later physical outcomes, but the encoded Q2 row still stores every later offset's validity, survival, margin and ACM efficiency (`src/mcrl/stagec_v025/state.py:61-85,426-433`). Skipping those evaluations would still change training inputs.

A cheaper option that changes **any** training label is not acceptable. Nor is a cheaper option that leaves the scalar label alone but changes a training feature, row membership, weight, reference, catalogue or arm ranking.

## Q5. Other quantities corrupted by the fallback

The problem is broader than validity and survival. The following is the complete fallback-specific proxy sweep of `ActionEvaluation` and the optional coalition-row selection path.

| Quantity written by primitive path | Primitive supplier | Exact/production supplier | Locations |
|---|---|---|---|
| Current candidate decoding margin (`nominal_sinr_margin_at_rate_target_db` and the duplicated Q2 `candidate_current_nominal_decoding_margin_db`) | Base configuration margin plus focal nominal-gain dB ratio | Complete candidate profile's evaluated minimum decoding margin | primitive `scripts/run_v025_pilot_c3.py:403-412,437-455`; exact `:599-635,657` |
| Current candidate required power ratio and cap margin (`nominal_required_power_over_cap`, `required_power_cap_margin_w`) | Base maximum power divided by focal gain ratio, clipped to `[0,10^6]`; cap margin derived from it | Complete candidate profile's coupled `required_power_w_max` | primitive `:411,440,458`; exact `:630,634,664` |
| `previous_beam_max_rf_over_cap` as emitted by this path | The same surrogate required-power ratio, capped at 1 | The exact branch uses the candidate profile's evaluated ratio, capped at 1 | primitive `:411,453`; exact `:630,653-655` |
| Current candidate ACM spectral efficiency (`nominal_mode_spectral_efficiency`) | Base mean ACM efficiency multiplied by a clipped focal gain ratio | Complete candidate profile's evaluated mean ACM efficiency | primitive `:404-412,441`; exact `:599,635` |
| Forecast `valid` | Set equal to focal future geometric legality | Full future configuration profile exists | primitive `:416-430`; production `run_v025_matrix_probe.py:1563-1589,1625-1638` |
| Forecast `survival` | Same focal geometric-legality boolean as `valid` | Every user changed relative to the future transition is served | primitive `scripts/run_v025_pilot_c3.py:418-430`; production `run_v025_matrix_probe.py:1627-1638` |
| Forecast minimum decoding margin | Current base margin plus focal future/base nominal-gain dB ratio | Full future profile's evaluated minimum margin | primitive `scripts/run_v025_pilot_c3.py:418-432`; exact pass-through `:665-672` |
| Forecast mean ACM spectral efficiency | Current surrogate SE multiplied again by a clipped future focal-gain ratio | Full future profile's evaluated mean ACM efficiency | primitive `:412,418-433`; exact pass-through `:665-672` |
| `forecast_se_trend_bit_s_hz_per_s` | Difference of the first proxy forecast SE and proxy current SE | Difference of exact first-forecast and exact current-profile SE | primitive `:457`; exact `:659-663` |
| C1 physical label (`c1_label_bits`) | `kappa × tanh(log focal gain ratio)`, or `-kappa` for null/geometrically illegal | Whole-network candidate-minus-base bits minus `eta ×` whole-network joule change | primitive `:403-409,460`; exact `:599,608-610,674` |
| C1 Phi difference (`c1_phi_difference`) | Calls `_phi_for` without the current step's `cell_rekeyed_users` | Rekey-aware candidate-minus-base Phi | primitive `:434,461`; exact `:612-620,675` |
| C2 physical label (`c2_label_bits`) | Sum of three focal future gain-ratio proxies with proxy-legality losses | Production `c2_persistence_forecast` over full candidate/base `NetworkOutcome`s plus exact validity/survival and absorbing penalty | primitive `:413-427,462`; exact `:599-607,676`; target `src/mcrl/physics_v025/targets.py:289-310` |
| Current `outage` | Negation of focal geometric legality | Negation of focal membership in the complete candidate profile's `served_phy` | primitive `scripts/run_v025_pilot_c3.py:465`; exact `:679` |
| Optional coalition selected for the C3 training row | Lexicographically smallest pairwise configuration | Highest exact `C1+C3` factor score, then configuration ID | primitive `:501-514`; exact `:739-787` |
| Optional coalition member Q1 states and `missing_incumbent` | Inherited from primitive source rows; coalition `missing_incumbent` is actually sourced from primitive `row.outage` | Inherited from exact source rows and exact served-set outage | `scripts/run_v025_pilot_c3.py:844-856,910-955` plus the source fields above |

Consequently the fallback corrupts both C1 and C2 target values, multiple Q1 and Q2 inputs, outage, rekey-sensitive Phi, and—when coalition generation is enabled—the identity/context of the C3 training example. The C3 identity target is exact **for whichever coalition was selected**; the corruption is that the fallback can select a different coalition and supplies proxy member states.

Fields not replaced by fallback-specific proxies are the action identity; current/base mapping counts and activity flags; remaining D2/visibility time; refresh phase; previous association/load/activity flags; `missing_incumbent`; exact incumbent/base margin; terminal flag; and the explicit legal flag. Two path-independent caveats remain: both branches hard-code `off_axis_angle_rad=0.0` (`scripts/run_v025_pilot_c3.py:445,639`), and both define `previous_beam_max_rf_over_cap` from the candidate required-power ratio rather than separately evaluating a previous-beam quantity (`:453,653-655`). The exact route does not repair those pre-existing semantics; they are not introduced by the fallback.

The primitive provenance hashes truthfully label the method `provider-primitive-fallback` / `provider-primitive-boundary-0` (`scripts/run_v025_pilot_c3.py:467-476`), and `visible_primitives_sha256` authenticates whatever values were supplied (`src/mcrl/stagec_v025/state.py:176-199`). Authentication therefore makes the surrogate rows tamper-evident; it does not make their quantities production-exact.

## Evidence classification and limits

**Verified by execution:** both builders ran on two real anchors; wall time, evaluator counts and RSS were measured; 5,952 exact validity/survival flag pass-through assertions per anchor passed; the fallback constant was true before and after; and the production pilot source file's hash was unchanged.

**Read from code:** the complete evaluation/target route, C1/C2 formulas, absorbing rule, optional C3 route, every proxy supplier listed above, and the cache key requirements implied by evaluator inputs.

**Inferred/projected:** the 29.415-hour no-cross-arm-reuse panel cost, 28.906-hour surrogate saving, and 3.268-hour perfect-reuse lower bound. They are arithmetic projections from the two-anchor means, not measured panel runtimes. “Affordable” is an engineering judgement about that source-row component, not a scientific claim.

**Not reached:** a full nine-arm union or its actual cache-hit rate; arm-specific catalogue sizes; optional coalition-row/catalogue timing; `full_legal_actions=True`; other worlds, steps or forecast boundary sets; repeated timing trials; a full panel; training; learned scoring/ranking; realised outcomes; continuation; policy behavior; pooled energy efficiency; any production run; or any acceptance test. I therefore do not claim an end-to-end panel wall time or a nine-arm cache saving beyond the explicit bounds.
