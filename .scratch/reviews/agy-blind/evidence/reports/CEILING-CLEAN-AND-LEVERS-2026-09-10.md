**At the sealed 1.66° point, the clean coordination ceiling is only `+0.844250%`; the evacuation-augmented catalogue is already saturated at its `|A| <= 1` tier and stays flat through `|A| <= 6`, so beam width raises the measured ceiling more than catalogue support.**

# CEILING2 — clean ceiling and lever comparison — 2026-09-10

`DESIGN_PHASE_EXPLORATION_NOT_A_CLAIM`

The two deterministic clean ceilings are **smaller than the published ones**. Coordination falls from `+1.944795%` to `+0.844250%` (−1.100545 percentage points, a 56.59% reduction), and the traversal-order gap falls from `+0.905261%` to `+0.090744%` (−0.814517 points, an 89.98% reduction). The acceleration result is not in that stable category: this run produced `+4.143306%`, larger than both earlier values, precisely because current load allowed fewer moves to finish by 10 wall-clock seconds.

No learner checkpoint, learner output, or loss value was read. Loss is not used as evidence about EE. Only the 12 frozen development anchors were read; no evaluation-only claim date was read. The numerator is full-buffer successfully decoded forward-downlink information bits with no demand cap. The sealed 1.66° design point and all sealed artefacts remain unchanged.

## Verified by running code

### Mandatory clean-path parity gate: passed

The experiment first reproduced all four required `STATICS2` values to six decimals. Had any row failed, no ceiling would have been reported.

| Required arm | Expected clean EE | Measured pooled EE (Mbit/J) | Gate |
|---|---:|---:|:---:|
| `NEAREST_ELIGIBLE` / `BASE` | 11.027760 | 11.027760227532434 | PASS |
| `RSS_MAX` | 41.621560 | 41.621559817145340 | PASS |
| `MYOPIC_GREEDY` | 31.078504 | 31.078503908389287 | PASS |
| `FIRST_IMPROVEMENT_FP` / `U_FIRST` | 31.028111 | 31.028111070819413 | PASS |

This independently reproduces the clean values in [`STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md`](/home/sat/mcrl-v025-rank2-ws/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md:19).

### Evaluator-path assertion: passed

For every selection arm and anchor, the runner created one fresh dense `StepEvaluator(boundary_indices=(0,))`, inserted `BASE` with `evaluate_many`, submitted every candidate through `evaluate_many` in that same evaluator, and read profiles only from its own dense cache. The joint selectors inserted both the carrier `BASE` and clean `U_FIRST` seed before profile reads. All selected endpoints then entered one separate fresh realised dense full-48 evaluator in one `evaluate_many` call per anchor.

`StepEvaluator.evaluate` was replaced with an incrementing raising stub before any measured work. Both width runs ended with:

```text
scalar_evaluate_calls=0
scalar_evaluate_assertion_passed=true
```

The dense-path mechanism is owned by [`run_v025_matrix_probe.py`](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:793); the clean reference pattern is in [`run_cleanpath.py`](/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/run_cleanpath.py:187). The executed runner is [`run_ceiling2.py`](/home/sat/mcrl-v025-ceiling2-ws/.scratch/ceiling2/run_ceiling2.py).

### Part 1 — sealed 1.66° point

Pooled EE is `sum(bits) / sum(joules)` across the 12 anchors and 48 realised boundaries. Absolute endpoint EE is shown on both sides of every ratio.

| Quantity | Numerator endpoint EE (Mbit/J) | Denominator endpoint EE (Mbit/J) | Clean result | Published result |
|---|---:|---:|---:|---:|
| Coordination: PANELCEIL bounded joint / first fixed point − 1 | `31.290066` | `31.028111` | **`+0.844250%`** | `+1.944795%` |
| Traversal: first fixed point / best fixed point − 1 | `31.028111` | `30.999980` | **`+0.090744%`** | `+0.905261%` |
| Acceleration: first fixed point / configuration held at 10 s − 1 | `31.028111` | `29.793668` | **`+4.143306%`** | `+1.045609%` / `+1.840863%` |

The corrected fixed point completed 4,210 strict moves; 2,446 had completed by the 10-second checkpoints summed over anchors. The bounded joint catalogue was exhausted at all anchors: 3,764 rows total, 313.67 per anchor (range 226–417). A strict joint improvement occurred at 12/12 anchors, the all-anchor mean winning changed-set size was 2.583 users, and joint selection took 0.967 s/anchor (range 0.494–2.262).

**Acceleration warning.** This is not a stable ceiling. `BEAMSWEEP` already measured the same nominal quantity as `+1.045609%` and `+1.840863%` solely because a different number of search moves completed inside ten wall-clock seconds. This run's `+4.143306%` is a third, load-dependent value, not a more authoritative constant. During the 1.66° run on 20 logical CPUs, the 1-minute load average moved from 3.979 to 17.427 (5-minute: 3.857 to 12.219; 15-minute: 4.645 to 8.368). First-improvement completion time ranged from 29.706 to 72.542 s/anchor. Machine speed and competing load directly change the denominator configuration.

### Catalogue-object correction

The premise that produced Part 2 conflates two distinct catalogues:

- The old `+1.944795%` figure used PANELCEIL's custom `U_FIRST`-local catalogue: same-beam occupant subsets of size 2–4, victim-plus-top-2/top-3 contributors, and common-destination complete-beam evacuations. Its implementation is [`run_panelceil.py`](/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py:459).
- The 36,788-row `{0:37, 1:28,960, 2:7,104, ...}` census is the production `bounded-union-v2` catalogue: shortlisted unilaterals, top-10/top-two pairs, two global proposals, and one evacuation per active beam. Its implementation is [`run_v025_matrix_probe.py`](/home/sat/mcrl-v025-c1c2suff-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:543), and the measured histogram is in [`C3-DECLARED-TARGET-LEARNABILITY-2026-09-10.md`](/home/sat/mcrl-v025-coalgen-ws/C3-DECLARED-TARGET-LEARNABILITY-2026-09-10.md:5).

Therefore `|A| <= 2` is **not** the literal support of the catalogue that produced the old coordination ceiling; that catalogue already contained size-3, size-4, and evacuation moves. Part 1 above recomputes the historical PANELCEIL object. Part 2 below is a separately declared, nested, production-shaped support diagnostic around the clean `U_FIRST` seed. Keeping them separate avoids silently changing what “coordination ceiling” means.

### Part 2 — coalition-support lever at 1.66°

The nested diagnostic holds width, seed, top-10 user ranking, two declared shortlist alternatives per ranked user, field, guard, objective, batch sizes, and complete beam evacuations fixed. It includes all shortlisted unilateral rows; then admits top-10/top-two combination rows through the requested maximum cardinality. Complete beam evacuations are included at every level as the requested explicit exception. The production catalogue's two global 100-user S0 rows are excluded so that cardinality support is the only changing catalogue feature.

The cap was 30,000 cumulative rows per anchor at every level. Counts below include one `U_FIRST` seed per anchor. Every catalogue was exhausted; **none was truncated**. Consequently none of these ceilings carries the “truncation understates its own ceiling” qualification. If the cap had bound, it would have been reported as a lower bound.

| Support (plus evacuations) | Catalogue rows, total over 12 (mean; range/anchor) | Joint EE (Mbit/J) | Coordination over clean `U_FIRST=31.028111` | Anchors with strict improvement | Mean winning changed set, all anchors (conditional) | Cumulative selector s/anchor |
|---|---:|---:|---:|---:|---:|---:|
| `|A| <= 1` | 8,888 (740.67; 730–761) | 31.133049 | **`+0.338203%`** | 2/12 | 0.333 (2.000) | 1.887 |
| `|A| <= 2` | 11,048 (920.67; 910–941) | 31.133049 | **`+0.338203%`** | 2/12 | 0.333 (2.000) | 2.215 |
| `|A| <= 3` | 22,568 (1,880.67; 1,870–1,901) | 31.133049 | **`+0.338203%`** | 2/12 | 0.333 (2.000) | 3.895 |
| `|A| <= 4` | 62,888 (5,240.67; 5,230–5,261) | 31.133049 | **`+0.338203%`** | 2/12 | 0.333 (2.000) | 9.782 |
| `|A| <= 6` | 320,936 (26,744.67; 26,734–26,765) | 31.133049 | **`+0.338203%`** | 2/12 | 0.333 (2.000) | 47.597 |

The answer is decisive for this bounded construction: **the ceiling does not keep rising with coalition support.** It is already saturated in the first row. Because `U_FIRST` is a certified unilateral fixed point, the two improvements at `|A| <= 1 + evacuations` must be complete-beam evacuations; both winners change two users. Adding all bounded top-10/top-two pairs and then all admitted size-3 through size-6 combinations changes neither winner, absolute pooled EE, improvement-anchor count, nor ceiling.

### Part 3 — clean 2.40° diagnostic

The width was overridden only in memory before rebuilding a new tape; 1.66° remains sealed. Absolute EE and service are included so that a larger ratio cannot be mistaken for an automatically better operating point.

| Quantity | Numerator endpoint EE (Mbit/J) | Denominator endpoint EE (Mbit/J) | Clean 2.40° result |
|---|---:|---:|---:|
| Coordination: PANELCEIL bounded joint / first fixed point − 1 | `32.080547` | `31.617710` | **`+1.463854%`** |
| Traversal: first fixed point / best fixed point − 1 | `31.617710` | `30.963088` | **`+2.114201%`** |
| Acceleration: first fixed point / configuration held at 10 s − 1 | `31.617710` | `23.244781` | **`+36.020683%`** |

| Width | Carrier `BASE` EE | First-fixed EE | Joint EE | First served / target | Joint served / target |
|---:|---:|---:|---:|---:|---:|
| sealed 1.66° | 11.027760 | 31.028111 | 31.290066 | 1200/1200 / 342/1200 | 1200/1200 / 349/1200 |
| diagnostic 2.40° | 10.126402 | 31.617710 | 32.080547 | 1200/1200 / 300/1200 | 1200/1200 / 299/1200 |

At 2.40°, fixed-point EE is 0.589599 Mbit/J (+1.900%) above 1.66°, and joint EE is 0.790481 Mbit/J (+2.526%) above 1.66°. But the carrier base is lower, and rate-target attainment falls by 42 users at the fixed point and 50 users at the joint endpoint. This is not a uniformly better operating point.

The 2.40° acceleration number is especially unstable. Only 1,363 of 3,988 fixed-point moves completed by the 10-second checkpoints. On 20 logical CPUs, the 1-minute load average was 35.295 at start and 16.000 at end (5-minute: 26.717 to 15.971; 15-minute: 15.382 to 15.309). First-improvement search ranged from 55.090 to 265.460 s/anchor, and total anchor work ranged from 140.169 to 646.298 s. `+36.020683%` describes this loaded run; it is not a hardware- or load-invariant ceiling.

The optional 3.32° width was not rerun. Parts 1–3 completed, but the 2.40° tail was not “comfortable”: the full run took 4,108.866 s and several anchors took more than five minutes. Reusing the contaminated old 3.32° ratio would defeat this exercise.

### Execution and resource evidence

| Width | Tape regeneration total (s) | Tape s/anchor | Full runner total (s) | Full runner s/anchor | Peak RSS | Result |
|---:|---:|---:|---:|---:|---:|:---|
| 1.66° | 151.226 | 12.602 | 1,764.524 | 147.044 | 2.625 GiB (2,819,084,288 B) | 12/12 complete |
| 2.40° | 250.285 | 20.857 | 4,108.866 | 342.406 | 2.376 GiB (2,551,275,520 B) | 12/12 complete |

Each run used one Python process, niceness 15, the required interpreter, and `OMP`, `OPENBLAS`, `MKL`, `NUMEXPR`, `VECLIB`, and `BLIS` thread counts all equal to one. A 4.9 GB resident-memory watchdog was active. Both runs printed `anchor k/12` for all anchors and final peak RSS. The hard limits were respected.

Receipt integrity was checked after completion:

```text
ea844c31c75ab747b0296f6e8453348deb5ca3a84780f2c7c0b0415b3b84cab4  .scratch/ceiling2/run_ceiling2.py
020ce0d34fb3e1f1729dd622f3c3526799bd7611874eca6c4fce05d9a7ab659e  .scratch/ceiling2/ceiling2-width-1.66.json
2333495c0b912f4c0a9518ebecb6c407c75c45da48723d26119a816e0096379f  .scratch/ceiling2/ceiling2-width-2.40.json
```

Both stored canonical receipt digests independently recomputed exactly. The primary-source audit is [`source-map.md`](/home/sat/mcrl-v025-ceiling2-ws/.scratch/ceiling2/source-map.md); the complete receipts are [`ceiling2-width-1.66.json`](/home/sat/mcrl-v025-ceiling2-ws/.scratch/ceiling2/ceiling2-width-1.66.json) and [`ceiling2-width-2.40.json`](/home/sat/mcrl-v025-ceiling2-ws/.scratch/ceiling2/ceiling2-width-2.40.json).

## Derived on paper from verified aggregates

The three ceiling formulas are:

- coordination = `EE(J_PANEL_BOUNDED) / EE(U_FIRST) - 1`;
- traversal = `EE(U_FIRST) / EE(U_BEST) - 1`;
- acceleration = `EE(U_FIRST) / EE(U_FIRST_AT_10s) - 1`.

For the support diagnostic, `J_PANEL_BOUNDED` is replaced by that level's nested-catalogue winner. No ratio is an average of per-anchor EEs.

### Part 4 — lever moved per measured cost

| Lever | Measured ceiling movement | Measured wall cost per anchor | Movement per incremental full-run second | What changes in the system |
|---|---:|---:|---:|---|
| Beam width, 1.66° → 2.40° | PANELCEIL coordination `0.844250% → 1.463854%`: **+0.619604 pp** | Tape regeneration `12.602 → 20.857 s`; full diagnostic runner `147.044 → 342.406 s` (+195.362 s, heavily load-confounded) | about **0.00317 pp/s** using the full measured increment | **Physical design parameter**: changes coverage, interference, EE, and QoS of the deployed system |
| Catalogue support, `|A| <= 2 → <= 6` | Nested support coordination `0.338203% → 0.338203%`: **+0.000000 pp** | Selector `2.215 → 47.597 s` (+45.382 s) | **0 pp/s** | **Decision-time compute parameter**: enlarges candidate evaluation and consumes the 10 s decision budget |

The wall-cost comparison is descriptive, not a benchmark: the width runs saw very different machine load, and width changes physics while support changes online computation. Still, the ranking is not close. Catalogue size grew from 11,048 to 320,936 panel rows and selector time grew about 21.5×, with zero ceiling movement. Beam width produced a measurable +0.619604-point coordination change and higher absolute fixed/joint EE, at the price of a physical redesign and worse target attainment in this clean run.

## Inferred

1. **Coalition cardinality is not the binding constraint inside the tested top-10/top-two production-shaped catalogue.** The result saturates before pairs; support through size six adds no value. This directly answers the requested bounded-support experiment.
2. **Beam width is the stronger of the two tested levers**, but it is not strong in the owner's sense. The required 2.40° diagnostic raises clean PANELCEIL coordination only from `0.844250%` to `1.463854%`.
3. **Neither lever gets the coordination ceiling into double digits.** Catalogue support reaches only `0.338203%` in its separately declared candidate object even after 47.597 selector seconds/anchor; 2.40° reaches `1.463854%` at the cost of changing the deployed physical system. The 2.40° acceleration ratio is double-digit, but it is a load-sensitive timing artefact class, not a double-digit coordination result.
4. Saturation of this bounded construction does **not** prove that global coordination has little to do. The tested catalogue still fixes the top-10 user shortlist and two alternatives per ranked user, and the old PANELCEIL catalogue is a different local object. What is ruled out is the specific hypothesis that merely extending coalition cardinality from pairs through six within this bounded proposal family unlocks material headroom.

The owner's standing concern survives the clean rerun: at the sealed point the stable coordination opportunity is below 1%, and neither tested lever makes it remotely double-digit.
