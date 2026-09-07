# One-epoch provider diagnostic review (codex gpt-5.6-sol, read-only, 2026-09-07)

1. [run_v023_one_epoch_provider_diagnostic.py:553](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:553) — The “no second division” check is lexical. Code dividing by `10.0`, `config.kappa`, or a helper would still pass because it only searches for `"kappa_bits"`. Fix: replace source inspection with a behavioral check on a cloned pre-update model, independently calculating C2 residuals from the delivered `normalized_target_deltas` and comparing the trainer’s reported loss components.

2. [run_v023_one_epoch_provider_diagnostic.py:563](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:563) — `load_target_artifact=None` skips producer-versus-delivered C2 equality but can still produce PASS. Fix: make the loader mandatory, or record `c2_labels_delivered_equal_producer_target_delta_no_second_division` as failed when absent.

3. [run_v023_one_epoch_provider_diagnostic.py:209](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:209) — `_identity()` accepts whitespace-only and over-512-character identities, unlike the runner’s contract at [v023_five_arm_source_training_runner.py:363](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:363). The subsequent presence check is tautological. Fix: reuse the runner accessor or enforce nonempty, trimmed, ≤512-character identity validation locally.

4. [run_v023_one_epoch_provider_diagnostic.py:149](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:149) — `_jsonable()` leaves values such as `bytes`, sets, tensors, or custom metadata objects unchanged. Serialization then fails inside `finish()`; the exception path calls the same failing `finish()` again, producing no failure receipt. Fix: validate/canonicalize metadata and identity payloads before execution and provide a serialization-safe minimal failure receipt fallback.

No defects found in C3 pair-slot reindexing, adapter aggregation order, recorded-batch aliasing/immutability under the real bridge, checkpoint tensor/bytes comparison, sampler restoration, or wrapper cursor behavior. The focused pytest command could not start because the sandbox exposes no writable temporary directory.

DEFECTS_FOUND
tokens used
312,754
1. [run_v023_one_epoch_provider_diagnostic.py:553](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:553) — The “no second division” check is lexical. Code dividing by `10.0`, `config.kappa`, or a helper would still pass because it only searches for `"kappa_bits"`. Fix: replace source inspection with a behavioral check on a cloned pre-update model, independently calculating C2 residuals from the delivered `normalized_target_deltas` and comparing the trainer’s reported loss components.

2. [run_v023_one_epoch_provider_diagnostic.py:563](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:563) — `load_target_artifact=None` skips producer-versus-delivered C2 equality but can still produce PASS. Fix: make the loader mandatory, or record `c2_labels_delivered_equal_producer_target_delta_no_second_division` as failed when absent.

3. [run_v023_one_epoch_provider_diagnostic.py:209](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:209) — `_identity()` accepts whitespace-only and over-512-character identities, unlike the runner’s contract at [v023_five_arm_source_training_runner.py:363](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py:363). The subsequent presence check is tautological. Fix: reuse the runner accessor or enforce nonempty, trimmed, ≤512-character identity validation locally.

4. [run_v023_one_epoch_provider_diagnostic.py:149](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py:149) — `_jsonable()` leaves values such as `bytes`, sets, tensors, or custom metadata objects unchanged. Serialization then fails inside `finish()`; the exception path calls the same failing `finish()` again, producing no failure receipt. Fix: validate/canonicalize metadata and identity payloads before execution and provide a serialization-safe minimal failure receipt fallback.

No defects found in C3 pair-slot reindexing, adapter aggregation order, recorded-batch aliasing/immutability under the real bridge, checkpoint tensor/bytes comparison, sampler restoration, or wrapper cursor behavior. The focused pytest command could not start because the sandbox exposes no writable temporary directory.

DEFECTS_FOUND
