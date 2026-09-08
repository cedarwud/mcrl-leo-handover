# C3-S confirmatory v2 implementation report (2026-09-08)

## Outcome

The confirmatory package now implements the astra B/C/D amendments without launching any simulator episode. The runner uses 100-user, 30-step episodes (3,000 opportunities/episode); accepts every frozen coordinator configuration `LITE,V-J,V-U,V-M,V-C,V-H,V-P,V-L2,FULL`; resolves the arm by matrix SUPPORT/complete mean-total-latency/tie order with the v1-qualified LITE fallback; persists 30 full decision records per episode; applies early futility only at N=100/500; and reserves contribution HELD for N=3,000.

The adapter imports the matrix hook implementation directly. V-C inactive steps use FULL2’s current proposal, V-H state is reset per fresh episode and retained within it, and V-P/V-L2 use their frozen persistence/lookahead hooks. No `sys.modules` alias is installed. `ALL_NEUTRAL_CONTROL` is never assigned the label `BASELINE`.

Preflight binds the separately sealed plan-v2 digest, sealed screen/matrix contracts, matrix and v1 terminal-receipt digests, resolved configuration, attempt-3 stage-A PASS, epoch-100/200-update export manifest, FULL2 checkpoint and Q1/Q2 parameter hashes, formal stage-B PASS, world plan, physical inputs, and code bytes. Missing or invalid provenance refuses. Optional speed-up rebinding requires a sealed independently reviewed bit-identical equivalence receipt whose new digest is current code; the matrix winner cannot be reranked.

## Verification

No training, physical episode, TEST access, or outcome computation was performed.

Commands run:

```bash
PYTHONPATH="src:.scratch/multi-catfish-v023-c3s-confirmatory" \
  /home/sat/mcrl-leo-handover/.venv/bin/python -m py_compile \
  .scratch/multi-catfish-v023-c3s-confirmatory/*.py

PYTHONPATH="src:.scratch/multi-catfish-v023-c3s-confirmatory" \
  /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -ra \
  .scratch/multi-catfish-v023-c3s-confirmatory/test_c3s_confirmatory.py

PYTHONPATH="src:.scratch/multi-catfish-v023-c3s-confirmatory" \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-confirmatory/build_c3s_confirm_world_plan.py \
  --check .scratch/multi-catfish-v023-c3s-confirmatory/C3S-CONFIRM-WORLD-PLAN-9000.json
```

Pytest summary: `11 passed in 1.63s`.

Synthetic coverage includes 30-step/opportunity accounting, all configuration IDs, FULL2 proposal behavior on control/cadence-inactive decisions, matrix winner/tie/fallback/unresolved cases, LITE audit integrity hold, N=100/500 early futility and `RUNG_HELD`, N=1,500 nonterminal release, N=3,000 HELD/FALSIFIED and exact service boundary, on-disk decision records, equivalence-receipt authentication, v1/matrix complete-timing parsing, and the failure-decomposition identity/no-feedback rule.

## Non-executing estimator

Source: v1 terminal receipt SHA-256 `a66b481303a28c31b49f127e302d304ac1ef34de5eb526dd2e3949bb5196ea69`; complete-decision means FULL2=1.8847855 s, LITE=49.4308090 s, FULL=66.7924050 s. Main includes both arms; acceptance includes each arm’s sequential-200 versus 2×100 executions.

| configuration | N | coordinator only h | control h | main pair h | acceptance h | total h |
|---|---:|---:|---:|---:|---:|---:|
| LITE | 100 | 41.192 | 1.571 | 42.763 | 171.052 | 213.815 |
| LITE | 500 | 205.962 | 7.853 | 213.815 | 171.052 | 384.867 |
| LITE | 1,500 | 617.885 | 23.560 | 641.445 | 171.052 | 812.497 |
| LITE | 3,000 | 1,235.770 | 47.120 | 1,282.890 | 171.052 | 1,453.942 |
| FULL | 100 | 55.660 | 1.571 | 57.231 | 228.924 | 286.155 |
| FULL | 500 | 278.302 | 7.853 | 286.155 | 228.924 | 515.079 |
| FULL | 1,500 | 834.905 | 23.560 | 858.465 | 228.924 | 1,087.389 |
| FULL | 3,000 | 1,669.810 | 47.120 | 1,716.930 | 228.924 | 1,945.854 |

Variant-specific `V-*` estimates require `--matrix-timing` and read `pooled.latency_by_arm.<configuration>.mean_hex`; no guessed timing replaces a missing matrix value.

## CLI surface

```text
run_v023_c3s_confirmatory.py --estimate --configuration CONFIG [--episodes N] [--screen-timing V1] [--matrix-timing MATRIX]
run_v023_c3s_confirmatory.py --dry-run --configuration CONFIG
run_v023_c3s_confirmatory.py --verify-equivalence OLD NEW --decision-record ARCHIVE... --equivalence-reviewer NAME --output RECEIPT
run_v023_c3s_confirmatory.py --benchmark-uncontended --code-path CODE --decision-record D01 ... D30 --output RECEIPT
run_v023_c3s_confirmatory.py --decompose --result FALSIFIED --code-path REPLAY --decision-record PAIRED_ARCHIVE... --output RECEIPT
run_v023_c3s_confirmatory.py --accept --arm ARM --output OUT --launch-authority AUTHORITY
run_v023_c3s_confirmatory.py --run-chunk --arm ARM --start K --end K+100 --output OUT --launch-authority AUTHORITY
run_v023_c3s_confirmatory.py --merge-arm --arm ARM --chunk-root ROOT... --output OUT --launch-authority AUTHORITY
run_v023_c3s_confirmatory.py --merge-two --arm-root FULL2_ROOT --arm-root C3S_ROOT --output OUT --launch-authority AUTHORITY

build_c3s_confirm_preflight.py --plan-contract PLAN_V2 --screen-contract SCREEN --matrix-contract MATRIX_CONTRACT --matrix-receipt MATRIX_RESULT --v1-receipt V1_RESULT --stage-a-pass STAGE_A_PASS --stage-a-manifest EPOCH_0100 --stage-b-pass STAGE_B_PASS --world-plan PLAN --prereg PREREG --tle-manifest TLE_MANIFEST --tle-root TLE_ROOT --output-root ABSENT_ROOT --reviewer NAME --freeze-timestamp-utc TIME --output PREFLIGHT

build_c3s_confirm_launch_authority.py --preflight PREFLIGHT --mode formal --release-boundary N --chunk-start K --chunk-end K+100 [--previous-rung-receipt PREVIOUS_HELD] --acceptance-receipt FULL2_ACCEPT --acceptance-receipt C3S_ACCEPT --output-root ROOT --output AUTHORITY --launch-arguments ...
```

## Open items before launch

- Seal plan v2 scientifically before appending mechanical outcome-derived digests.
- Obtain a complete valid matrix terminal receipt plus its bitwise LITE-equivalence audit and resolve the configuration mechanically. The current matrix package does not itself provide that audit field, so preflight correctly remains `ARM_UNRESOLVED` until the audited receipt exists.
- Obtain and authenticate stage-A attempt #3 PASS, its epoch-100/200-update manifest and exact FULL2 export/parameter hashes, followed by formal stage-B PASS.
- If optimized code is selected, run independent archived-decision equivalence and seal the receipt; then run the fixed 30-decision uncontended benchmark.
- Run both arms’ isolated sequential-200 versus 2×100 acceptance, independently verify each rung, and issue per-rung/per-chunk launch authorities. None of these execution items was authorized or run here.
