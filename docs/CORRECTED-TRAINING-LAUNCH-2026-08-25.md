# Corrected P6/main launch receipt (2026-08-25)

**Status: RUNNING. This receipt proves launch and guard passage only; it is not
a completion or scientific-acceptance record.**

The corrected R2 pipeline entered P6 on the Ubuntu server after both local and
server verification completed.

| Field | Receipt |
|---|---|
| Server checkout | `/home/sat/mcrl-leo-handover-20260825-corrected` |
| tmux | `mcrl-corrected-p6-main-20260825` |
| Output | `artifacts/training-2026-08-25-rerun01/` |
| Launch | `2026-08-25T03:50:35.778783+00:00` (`11:50:35` Asia/Taipei) |
| Validation complete | `2026-08-25T03:50:59.415576+00:00` |
| R2 self-digest | `3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4` |
| R2 byte SHA-256 | `8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543` |
| Training code SHA-256 | `544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4` |
| First-arm fingerprint | `18d5786ba814d14435e350ff92668c0ed53284d9084432110d8d835f1548fe08` |
| First arm | P6 `alpha = 0.01`, matched frozen seeds |
| Reward scales | `(2029238.4328742754, 1.0, 6.0)` |
| Dependencies | Python 3.13.3, NumPy 2.5.2, SGP4 2.27, PyYAML 6.0.3, Torch 2.13.0 |
| First durable boundary | 100/9000 episodes at `2026-08-25T03:53:46.910457+00:00` |
| Resume checkpoint SHA-256 | `234f43a7915b95080b69324c3b02d2aec2405834b9ddb2e9818fa59bd51b6e39` |
| 100-episode log SHA-256 | `ba152852c8b8e250c31bad957a6a026fe98d9045d1624b15180a2fe871e63999` |

Pre-launch evidence:

- local full suite: 820 collected, 819 passed, 1 skipped;
- server full suite: 820 collected, 819 passed, 1 skipped;
- local and server `run_server_training.py validate`: PASS;
- remote old seal, corrective protocol, summary, manifest and selected P3
  evidence hashes matched the R2 record;
- fresh output directory and tmux name did not exist before launch.

The launcher writes an atomic resume checkpoint every 100 episodes and records
source/dependency/TLE/config fingerprints. P6 runs `alpha = 0.01`, `0.003`, and
`0.001` in frozen order; only after all eligible arms finish does the frozen
selector choose the independent main run's learning rate.

Expected wall time is approximately 16 hours based on the defective-runtime
historical run. Actual completion must be established from
`pipeline-status.json`, all arm statuses, final checkpoint/log hashes and the
separate exit receipt. A live PID or tmux session is not completion evidence.
