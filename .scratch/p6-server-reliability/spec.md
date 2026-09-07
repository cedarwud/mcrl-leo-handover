# P6 server reliability closure

Completion criterion: the public server-training CLI, pipeline, and trainer
checkpoint seams can resume an interrupted episode-boundary checkpoint without
changing the deterministic result; they fail closed on protocol, ephemeris,
dependency, provenance, evaluation-finiteness, and artifact drift; the full
test suite passes before the corrected tree is synchronized to the Ubuntu
server and the P6-to-main chain is launched there.

Public seams under test:

- `scripts/run_server_training.py` argument and exit behavior.
- `mcrl.runtime.training_pipeline` validation, reuse, failure-state, and
  orchestration behavior.
- `MODQNTrainer.train` plus its explicit training-state save/restore contract.

Out of scope: scientific-rule changes, alternative P6 selection criteria,
browser work, unrelated worktree files, commits, and pushes.
