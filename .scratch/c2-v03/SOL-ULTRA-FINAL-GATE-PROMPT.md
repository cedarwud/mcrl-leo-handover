# Goal

Act as a fresh-context adversarial scientific and code reviewer. Decide whether the current C2 Temporal Fork implementation is ready to be integrated into a bounded 1500/3000-episode Multi-Catfish MCRL trend experiment. This is not an efficacy review: tests and smoke runs must not be treated as proof that EE improves.

# Authority

Inspect the current worktree. Treat code, tests, and generated JSON evidence as authoritative over prose. Read at least:

- `.scratch/c2-v03/c2_temporal_fork_core.py`
- `.scratch/c2-v03/c2_temporal_fork_selection.py`
- `.scratch/c2-v03/c2_temporal_fork_trainer_backend.py`
- `.scratch/c2-v03/c2_temporal_fork_option_runner.py`
- `.scratch/c2-v03/c2_temporal_fork_learning_adapter.py`
- `.scratch/c2-v03/c2_temporal_fork_torch_adapter.py`
- `.scratch/c2-v03/c2_temporal_fork_combined_carrier.py`
- `.scratch/c2-v03/c2_temporal_fork_joint_transaction.py`
- `.scratch/c2-v03/c2_temporal_fork_training_step.py`
- their tests under `.scratch/c2-v03/`
- `artifacts/c2-v03-multianchor-census-after-ee-gate-fix-20260829.json`
- `artifacts/c2-v03-real-backend-k4-full-option-smoke-20260829.json`

The three paper documents under `docs/` may be stale; use them only to identify documentation drift.

# Review questions

1. Verify the admission mathematics after removal of `E_C <= E_M` and activation/resource-path gates. Given `B_C >= B_M`, `E_M > 0`, and robustly positive `S=(B_C-B_M)-(B_M/E_M)(E_C-E_M)`, determine whether `EE_C > EE_M` follows and identify numerical or semantic counterexamples.
2. Audit K0/K1/K>=2 selection, fixed complete candidate schedule, cross-focal anchors, selected-object binding, behavior probability, and pre-live Q2F policy/network no-drift.
3. Audit the fixed one-to-four-step observed return with zero bootstrap, adverse-outcome retention, early-terminal no-padding behavior, nonterminal candidate expiry, and full served-vector/source-lineage binding.
4. Audit source-age zero, duplicate prevention, and the at-most-once atomic Q2F-plus-Main transaction including rollback of parameters, optimizers, gradients, RNG, counters, and ledgers.
5. Audit the formal training seam. Look especially for trainer/object identity mismatches, missing episode-loop integration, checkpoint/cadence gaps, replay warmup mistakes, and any path that can execute live work or mutate state outside the joint transaction.
6. Judge whether the mechanism is unnecessarily complex. If a simpler design preserves a real Q2F role and a defensible causal path to EE, specify it precisely.
7. State what the three-anchor census and real K4 option smoke establish, and what they do not establish. Decide whether they are sufficient to begin implementing the bounded runner, and whether any code blocker remains before launching 1500/3000 episodes.

# Boundaries

Read only. Do not edit files and do not start training. Distinguish verified evidence, inference, and missing evidence. Cite exact file and line numbers for every blocker. Do not reject merely because efficacy is unproven; this gate is about scientific coherence and runner safety before a bounded trend experiment.

# Output

Return:

1. `VERDICT: GO_FOR_RUNNER_INTEGRATION`, `VERDICT: REVISE_BEFORE_RUNNER`, or `VERDICT: NO_GO`.
2. Blocking findings, ordered by severity.
3. Nonblocking risks and documentation drift.
4. The minimum exact fixes, if any.
5. A concise experiment recommendation separating pre-launch gates from questions that only data can answer.
