# Multi-Catfish MCRL V0.3B C2 reactive-release implementation receipt

Date: 2026-08-31  
Status: **implementation/test gate complete; fresh scientific gate pending;
training NO-GO**

## Implemented policy

The C2 candidate branch uses the selected policy
`hold-while-legal, then monotone branch-local Main release`:

1. At each candidate-branch offset, count matches for the held physical key in
   that branch's contemporaneous predecision action table.
2. Hold only while the match count is exactly one.
3. On the first support loss, latch `release_reason=support_expired` and the
   corresponding `release_offset`.
4. From that offset onward, execute complete contemporaneous branch-local Main.
5. Never read a future offset, reference-branch state, target, or outcome to
   trigger release, and never reacquire the held key.
6. If support remains unique for the full horizon, use the planned horizon
   release.

Every V0.3B row binds the held physical key, per-offset match count, release
offset/reason, and `c2_policy_version`. Old or missing policy versions fail
closed in replay, ledger, runtime snapshot, and learner paths. A legacy
expiry prefix without an admitted suffix produces an explicit no-admission
receipt and cannot enter learning or a joint transaction.

## Implemented surfaces

The implementation is currently isolated under `.scratch/c2-v03/`. The
reactive policy and its compatibility checks span:

- `c2_temporal_fork_core.py`
- `c2_temporal_fork_forecast_adapter.py`
- `c2_temporal_fork_trainer_backend.py`
- `c2_temporal_fork_option_runner.py`
- `c2_temporal_fork_learning_adapter.py`
- `c2_temporal_fork_torch_adapter.py`
- `c2_temporal_fork_episode_runner.py`
- `c2_temporal_fork_training_step.py`

This receipt does not claim that the scratch implementation has passed a
fresh physical-headroom gate or been promoted into a long-training launch
authority.

## Verification

Command:

~~~text
./.venv/bin/pytest -q \
  .scratch/c2-v03/test_*.py \
  tests/test_w39_c2_keyed_gate.py \
  tests/test_w40_c2_gate_runner_integrity.py
~~~

Result: **256/256 collected tests passed** on 2026-08-31. Edited modules also
passed Python byte-code compilation.

The tests cover first-expiry latching, no reacquisition, horizon release,
release metadata, candidate-branch contemporaneous support counting,
policy-version fail-closed behavior, replay/runtime persistence, and
no-admission behavior for an obsolete expiry prefix.

## Claim ceiling and next gate

This closes the implementation/test prerequisite only. It does not reopen
training and does not prove physical headroom, learnability, or EE efficacy.
Before any learnability pilot:

1. freeze a new source manifest and preregistration;
2. use a fresh non-overlapping seed block;
3. run the keyed-fading reactive-release physical-headroom gate;
4. adjudicate completion, service, release-offset diversity, anchor-level
   replication, and fallback-branch coverage under the frozen rule.

Until that gate is sealed, C2 remains authoring-GO but training-NO-GO.
