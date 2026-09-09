# V025 — controller decisions after the stage-4d real-anchor gate (2026-09-09 ≈ 00:20 UTC; before any formal successor outcome)

Stage 4d result: catalogue 1 004 rows (PASS ≤ 1 500); complete 14-arm anchor 34.4 s (PASS ≤ 60 s); provider + anchor 55.9 s (PASS); coordinator selection path 24.7 s (FAIL vs 10 s), dominated by the five-boundary stage-2 forecasts at 18.3 s. Everything else of the 4c gate landed (O(|A|) decomposition, exhaustive S_UNI, 167 tests, 22 independent KATs).

1. **Declared parallelism first (not an approximation):** the coordinator's compute budget is defined on the declared worker count of 4 processes (contract v1 §F2; stage C spec decision 8). Stage 4e implements the 4-worker parallel evaluation of stage 1 and stage 2 (configuration-level sharding; deterministic reduction; identical results to the serial path — KAT) and re-measures the selection path wall time on 4 workers.
2. **If still above 10 s, the next pre-declared step:** stage-2 forecasts evaluated at one boundary per offset step (the decision instant of each of the three offsets) instead of five, keeping three offsets and M = 64; report the top-1 agreement with the five-boundary continuation on the rehearsal anchors.
3. **Then, if still above 10 s:** M = 64 → 48. No further step without a controller decision.
4. Order is binding: 1 → 2 → 3, each measured; the smallest sufficient step is sealed with its measured time; labels, committed-profile evaluation and the endpoint remain at 48 boundaries throughout (KAT).
5. The wall-time measurement uses the declared clock rules (spec decision 8: monotonic, cold per anchor, 4 workers) and the full path catalogue → stage 1 → stage 2 → selection → validation.
