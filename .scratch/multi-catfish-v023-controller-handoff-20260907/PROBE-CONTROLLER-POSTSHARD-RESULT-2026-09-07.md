# Read-only probe: controller post-shard authentication against real shard outputs (2026-09-07 11:40 UTC)

Script: `probe_controller_postshard.py` (this directory). Loads the r6 controller and generator by
path from `/home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r6`, patches ONLY
`CLAIM_CEILING` to the producer's literal (the known r6 failure) in the probe process, derives the
authenticated 16-shard schedule (`_expected_schedule`), then runs `_read_receipt` and
`_validate_shard` on every real shard directory. Writes nothing.

| staging | shard | `_read_receipt` | `_validate_shard` |
|---|---|---|---|
| r6 | neutral:2026121708 | PASS | FAIL `OPS-3 q2_state is not the target-free feature projection` |
| r5 | informed:2026121705 | PASS | FAIL `target receipt output code closure drifted from the live OPS-3/D40 closure` (expected: old generator) |
| r5 | informed:2026121711 | PASS | same |
| r5 | neutral:2026121705 | PASS | same |
| r5 | neutral:2026121707 | PASS | same |
| r5 | neutral:2026121708 | PASS | same |
| r5 | neutral:2026121709 | PASS | same |

Conclusion: after the claim-ceiling fix the controller would STILL reject every r7 shard at
`_validate_shard` with a fourth consumer-side check (`q2_state` vs "target-free feature
projection"), i.e. r7 would have failed again after ~3 h of compute. The adapter's own
`_ops3_route_batch` accepted the same rows (`state == features.astype(float32).T.reshape(-1)`),
so the controller's recomputation differs from both the producer and the downstream consumer.
This must be diagnosed and fixed offline (local repro on the 3-row real excerpt) before r7.
