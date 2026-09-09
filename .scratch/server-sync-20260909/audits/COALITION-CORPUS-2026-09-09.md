# Coalition corpus — 2026-09-09

**New trainable coalition-size histogram: {'2': 6921, '3': 4691, '4': 270, '5': 36, '6': 6}. Occupancy-activation is admitted by 180 of 180 anchors.**

`PILOT_NOT_CLAIM`

## Outcome

Generated 11924 exact interaction rows across 180 anchors, versus the audited 180-row baseline: 66.24x as many coalition rows. Against 176,223 per-user rows, the interaction ratio improved from about 1:979 to 1:14.8. Coalitions per anchor have distribution {'min': 27.0, 'p05': 31.0, 'p50': 46.0, 'p95': 122.04999999999998, 'max': 132.0, 'mean': 66.24444444444444, 'mean_abs': 66.24444444444444}. Family counts over unique rows are {'aggressor-relief': 360, 'beam-evacuation': 3115, 'nested-subsets': 342, 'occupancy-2-diminishing': 1446, 'occupancy-activation': 6816, 'pair-catalogue': 180}.

The authenticated corpus is `artifacts/v025-mechanism-coalition-corpus-20260909-PILOT_NOT_CLAIM`. It contains 180 learner-readable v2 coalition shards, a family index, a nested-mask scalar-observation ledger, and the manifest. The corpus remains `PILOT_NOT_CLAIM`.

## Family coverage

- `pair-catalogue`: 180 rows. All 180 archived one-per-anchor action selections were reconstructed unchanged, so the old design points remain a configuration subset. Under the single canonical exact evaluator/cache used for every family, 0 labels match both archived interaction and objective delta bit-for-bit and 180 differ. The mismatches are retained in the manifest: the legacy artifacts used a call-order-dependent primitive evaluator path, so their action selections are comparable but their old labels are not reused as exact targets.
- `occupancy-activation`: 6816 trainable rows across 180 anchors, by changed-user size {'2': 3408, '3': 3408}. Every seed beam starts at occupancy exactly 1 and two legal arrivals take it to occupancy 3. The exact activation core is retained as a pair; where a legal outside action exists, a three-change context probe adds a third changed user so the learner directly sees third-order variation around the same activation. The first activating occupancy is recomputed from `q10(elevation) * Gamma(n)` using the full Rician×shadow distribution and the engine tables at the weakest actual link elevation among incumbents and selected arrivals. The numerical rule is deterministic: 192-point Gauss–Hermite integration of the Rician×shadow CDF followed by a 60-step bisection root solve, authenticated at the 10-degree value `q10 = 0.42923539`; the lowest threshold remains `0.7174947935658479`. Its exact-Psi sign/distribution ledger is {'min': -19.624999353828237, 'p05': -3.3181896523061862, 'p50': 0.16522505801497983, 'p95': 2.729016840442762, 'max': 16.397973279040425, 'mean': -0.24167713063389645, 'mean_abs': 1.204984129199215, 'count': 6816, 'negative_count': 2969, 'zero_count': 5, 'positive_count': 3842}.
- `occupancy-2-diminishing`: 1446 rows across 180 anchors, kept separate from occupancy activation. These start at occupancy 2 and add two users, so the first arrival crosses occupancy 3 and the second exposes the corrected diminishing population. Its exact-Psi sign/distribution ledger is {'min': -15.905713051515226, 'p05': -1.8473536626402725, 'p50': -0.4803333922829859, 'p95': 3.196784853348526, 'max': 15.998312922851756, 'mean': -0.024575281042599848, 'mean_abs': 1.1907413666394215, 'count': 1446, 'negative_count': 1004, 'zero_count': 2, 'positive_count': 440}.
- `aggressor-relief`: 360 rows. Per admitting anchor, the victim with greatest top-three nominal cross-gain burden and its top two/top three contributors move to their own first different legal action in the sealed shortlist, yielding sizes 3 and 4.
- `beam-evacuation`: 3115 rows. Every beam with 2 or 3 occupants is evacuated when every occupant has a different legal alternative. This selection uses occupancy and legal-action identity only; it consults no decode threshold.
- `nested-subsets`: 342 unique rows across 6 six-user blocks. Each block has all 64 subset masks evaluated and all 64 Möbius coefficients emitted, giving 57 non-trivial residual-label occurrences. These are **64 scalar observations, not 57 independent measurements**.

## Exact-label convention and cache

Every size-`k` interaction row uses `k + 2` distinct sealed-objective configurations: the anchor baseline, each of the `k` singleton action changes evaluated exactly, and the joint coalition. Each family-index row carries the exact numerator/denominator receipt for all of those values and the residual. The implemented convention is **exact singleton differences**; no learned singleton estimate enters any label. Consequently the target is the interaction itself, not interaction plus singleton-model error.

The cache key is a canonical SHA-256 over four complete axes: (1) anchor identity and assignments (world, seed, step, carrier, anchor configuration), (2) context (objective convention, transition configuration, rekeyed users), (3) the complete proposed-action assignment, and (4) evaluator configuration (engine schema, setting/run-setting digest, nominal field, boundary set, physics digest, calibration digest). This explicitly includes the anchor, context, proposed actions, and evaluator configuration. Once an anchor baseline and its exact singleton action values are cached, an additional coalition label costs one new joint evaluation; the R3 audit separately requires its pair configurations. Cache requests/hits were 69766/31256; physical configuration evaluations including the order audit were 38510.

## Order audit

For every valid coalition of size at least three, the audit computed exact pair interactions under the same proposed member actions and then `R3(A) = Psi(A) - Σ_{pairs⊂A} Psi(pair)`. In normalized units the distribution is {'min': -30.715730406042656, 'p05': -0.7869919880521803, 'p50': 3.72660681171265e-14, 'p95': 4.2090683426211655, 'max': 15.179469211218574, 'mean': 0.45368889233665705, 'mean_abs': 0.7747374442322291, 'count': 5003, 'fraction_abs_gt_1e-6': 0.597041774935039, 'fraction_abs_gt_1e-3': 0.3849690185888467}. As a descriptive scale check (not an acceptance rule), `|R3| > 1e-3` occurs in 38.50% of rows; this is **material** for model specification. A pairwise-only interaction model is therefore misspecified for this corpus.

## Integrity and invariants

The manifest digest is `ea40ba982b56e434276dddb957da76d4f6668196773e57ce191976e83bb650c1`; family index `b8f55dc15e91155a32aa706a4908aff3bf6ee281565f9ca0644d76679e7da047`; nested observations `b9a86345f052525ed5f972660247447cc211151989a1984e4f53ac1cf0e9b55f`. Invalid proposed configurations skipped after exact evaluation: 0.

No threshold, sign, seed, horizon, price, service guard, or acceptance rule was changed. The generator expands only which exact sealed-objective coalitions are labeled. No encoder feature is used to compute a label.
