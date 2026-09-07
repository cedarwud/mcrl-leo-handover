VERDICT: REVISE_BEFORE_RUNNER

The mechanism is scientifically coherent enough to continue runner implementation, but the current implementation is not safe to launch for 1500/3000 episodes. This review is pinned to runner SHA-256 `c326c11b…`, learning-adapter `32989976…`, and the artifact hashes shown below; the worktree changed repeatedly during review.

## Blocking findings

1. **Critical — real two- or three-step terminal prefixes cannot reach the learning path.**

   The backend advances the live environment, detects `done`, then raises before constructing the payload ([trainer backend, lines 363–377](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_trainer_backend.py:363)). Consequently, the option runner’s terminal handling after `_step_payload` is unreachable for terminals at offsets 1 or 2 ([option runner, lines 220–245](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_option_runner.py:220)). The environment has advanced, but the observed terminal transition is lost and no joint transaction occurs.

   Opening-terminal length 1 and full/release length 4 can work; real lengths 2 and 3 cannot. This contradicts the otherwise-correct core contract for actual terminal prefixes ([core, lines 1027–1046](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_core.py:1027)).

   Candidate expiry has a related problem: the runner breaks with a nonterminal prefix ([option runner, lines 225–235](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_option_runner.py:225)), after which core closure rejects it. That is fail-stop, but it occurs after live mutation and produces no durable failure receipt.

2. **High — later anchors can claim a stale Main-policy digest.**

   The runner computes `checkpoint_sha256` once at episode start ([episode runner, lines 739–745](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:739)). C2 is deliberately primed with an ordinary step before its first forecast ([lines 798–806](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:798)), and that step can update Main through the carrier before the later forecast ([lines 917–926](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:917)). The later backend nevertheless receives the episode-start digest ([lines 636–646](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:636)).

   Exact object identity is checked, but it cannot detect in-place network drift. From episode 2 onward, when replay is warm, the certificate can therefore bind the wrong Main bytes.

3. **High — the “complete fixed schedule” is not durably bound to selection.**

   The runner’s rule is deterministic—ascending departure users, capped at nine—but forecast exceptions are logged separately and omitted from `prepared_candidates` ([episode runner, lines 632–670](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:632)). Selection validates only the sequence supplied by its caller ([selection, lines 665–727](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_selection.py:665)), while its durable receipt hashes the passed support, not the ordered schedule and all pass/fail/error outcomes ([selection, lines 587–630](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_selection.py:587)).

   Thus K0/K1/K≥2 is correct conditional on the supplied completed set, but the final transaction cannot prove that every scheduled focal candidate was attempted exactly once.

4. **High — the current episode runner is not a reproducible trend-experiment carrier.**

   - It is explicitly a ≤24-episode developmental CLI ([episode runner, lines 1068–1076](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:1068)); the programmatic entry lacks that guard ([lines 1007–1038](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:1007)).
   - Runtime state is saved but not loadable and omits source environments, trajectory state, environment RNGs, and open-option state ([lines 219–246](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:219)). There is no resume argument or resume path.
   - Treatment logs retain only Main reward sums and C2 counts, not useful-bit and energy numerators, ratio-of-sums EE, service, or matching arm-level metrics ([lines 947–955](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:947)). B000 delegates to a different legacy result schema.
   - The authority hash excludes every `.scratch/c2-v03` implementation file: `_default_code_paths()` hashes `src/mcrl`, one script, and `pyproject.toml` only ([training pipeline, lines 385–389](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/training_pipeline.py:385)).
   - Main replay admission and C1/C3 specialist/replay updates occur before the joint C2 transaction ([episode runner, lines 402–426](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:402), [lines 495–498](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_episode_runner.py:495)). Joint rollback cannot restore these, source environments, or live option execution. No failure-status journal makes an interrupted run safely distinguishable from a completed one.

## Verified mechanism properties

### Admission mathematics

\[
S=(B_C-B_M)-\frac{B_M}{E_M}(E_C-E_M)
  =B_C-\frac{B_M}{E_M}E_C
  =E_C(EE_C-EE_M).
\]

Therefore, the premises as stated are insufficient: `E_C>0` is also required.

- Mathematical counterexample outside the code contract: `B_M=100`, `E_M=10`, `B_C=200`, `E_C=-1` gives `S=210>0`, but `EE_C=-200<10`.
- With `E_C=0`, candidate EE is undefined.
- Current code requires both energies to be strictly positive ([core, lines 550–571](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_core.py:550)). Under that condition, robustly positive `S` does imply strict forecast `EE_C>EE_M`. Removing `E_C≤E_M` is mathematically correct: for example, `100/10` versus `120/11` has higher candidate energy but higher EE and positive surplus.
- Decimal arithmetic, finiteness checks, and the relative-plus-ULP floor provide no evident numerical false-positive path ([core, lines 456–480](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_core.py:456), [lines 578–612](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_core.py:578)).

Semantically, this proves only the measured four-interval forecast-system EE. The adapter uses all-user rate sums and system power over the same intervals ([forecast adapter, lines 488–493](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_forecast_adapter.py:488)). If that power signal omits activation or resource-path costs, or if populations/windows differ, the algebra improves a proxy rather than physical EE.

### Selection and learning objects

- K0 fallback, K1 forced/unranked control, K≥2 Q2F epsilon-greedy selection, matched-random probability, deterministic ties, and behavior probabilities are implemented correctly ([selection, lines 734–781](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_selection.py:734)).
- Cross-focal context removes only `focal_user` and binds the shared state/Main/environment context ([selection, lines 217–228](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_selection.py:217)).
- Consumer revalidation uses selected-object identity and recomputes probabilities ([selection, lines 879–923](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_selection.py:879)).
- Q2F policy version and online-network bytes are rechecked pre-live ([training step, lines 99–121](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_training_step.py:99)).
- The latest adapter now requires and compares complete served vectors and reward-source lineage ([learning adapter, lines 1009–1030](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_learning_adapter.py:1009), [lines 1282–1289](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_learning_adapter.py:1282)).

The core’s adverse-outcome retention, actual 1–4-step terminal-prefix rule, zero bootstrap, and no nonterminal padding are sound in isolation. The blocker is the live backend’s inability to deliver lengths 2–3.

### Atomic transaction

The narrow Q2F-plus-Main transaction is strong:

- Source age is frozen to zero ([combined carrier, line 55](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_combined_carrier.py:55)).
- Duplicate and cross-ledger consumption is preflighted before mutation ([joint transaction, lines 688–727](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_joint_transaction.py:688)).
- Specialist/Main parameters, optimizers, online gradients, relevant NumPy RNGs, counters, process NumPy/CPU-Torch RNG, and ledgers are snapshotted and restored ([joint transaction, lines 173–294](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_joint_transaction.py:173), [lines 818–867](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_joint_transaction.py:818)).
- Warmup occurs before RNG or optimizer access ([lines 806–816](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_joint_transaction.py:806)).

This does not extend atomically to the surrounding environments, Main replay insertion, or earlier C1/C3 updates.

## Evidence and nonblocking risks

The three-anchor census establishes one checkpoint/seed’s opportunity incidence and cost: 11 attempts, 10 completed forecasts, four passes, classes K0=2/K1=0/K≥2=1, approximately 4.48 seconds per candidate ([census, lines 352–382](/home/u24/papers/mcrl-leo-handover/artifacts/c2-v03-multianchor-census-after-ee-gate-fix-20260829.json:352)). It does not exercise K1, learned Q2F, live execution, joint updates, multiple seeds, or efficacy.

The K4 smoke establishes one real matched-random selection with probability 0.25 and one complete four-step option with zero bootstrap ([smoke, lines 202–226](/home/u24/papers/mcrl-leo-handover/artifacts/c2-v03-real-backend-k4-full-option-smoke-20260829.json:202), [lines 745–769](/home/u24/papers/mcrl-leo-handover/artifacts/c2-v03-real-backend-k4-full-option-smoke-20260829.json:745)). It explicitly performs no training or replay write. It does not test Q2F ranking, early termination, expiry, warmup, rollback, episode cadence, or EE improvement.

Both artifacts use the incomplete source hash above, so they are not cryptographically bound to the current C2 modules.

Other risks:

- Cross-focal candidates use focal-specific forecast streams because the seed includes `anchor_sha256` and `focal_user` ([trainer backend, lines 436–452](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_trainer_backend.py:436)). Each reference/candidate pair is fair, but different focal candidates are compared under different future mobility draws.
- The current episode runner uses the same Main and Q2F objects by construction, but the injectable training seam can bypass Main identity checking when `runner_fn` is supplied ([training step, lines 330–340](/home/u24/papers/mcrl-leo-handover/.scratch/c2-v03/c2_temporal_fork_training_step.py:330)). Move this invariant inside the seam unconditionally.
- An admitted option encountered during Main replay warmup is not queued for later Q2F learning. This can be valid only if explicitly preregistered as zero training dose and counted separately.
- The exact latest hashes could not receive a clean pytest run in this read-only sandbox because no writable temporary directory was available. Current episode-runner tests are predominantly mocked and do not cover real mid-terminal, expiry, resume, metric parity, or failure recovery.

Documentation drift is material: the paper algorithm claims full-schedule binding, real early-terminal retention, and rollback of all mutable state ([paper algorithm, lines 373–394](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md:373)); the concept freeze still describes exactly one source step followed immediately by specialist routing ([concept freeze, lines 125–164](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md:125)).

## Minimum exact fixes

1. Make the live step path return the actual payload before acting on early `done`. Forecast branches may still fail closed, but live execution must close and retain terminal prefixes of lengths 1, 2, 3, or 4. Add real tests for terminal offsets 0–3 and typed expiry after offsets 1–2.

2. Recompute and bind Main’s current online-network digest immediately before every candidate schedule, then rehash it immediately pre-live. Move Main identity enforcement inside `run_c2_training_step` regardless of injected wrappers; similarly bind a stable Q2F owner identity, not only equal bytes/version.

3. Create an immutable schedule receipt before forecasting. It must contain the ordered scheduled focal/physical identities, cap/rule, shared context, forecast-stream IDs, and an outcome for every item: pass, certificate fail, or contract error. Hash it into selection, training, and joint receipts.

4. Finish the long-run carrier: full load/resume, step/episode cursor, all source environments and RNGs, replays, open-option state, failure journal, code manifest including all C2 modules, and identical treatment/baseline useful-bit, energy, service, reward, and ratio-of-sums EE telemetry.

5. Resolve warmup explicitly: either persist an admitted closed option until the joint transaction can update exactly once, or preregister it as observed-but-zero-dose. Do not conflate a carrier call with an optimizer step.

6. Run a writable-environment structural pilot covering real K0, K1, learned K≥2, matched random, warmup crossing, terminal prefixes, expiry, injected failures at each transaction stage, deterministic interruption/resume, and exact per-step update counts.

## Simpler defensible design

The current provenance and atomic checks are justified; bulk-stepping inside nested orchestration and duplicate injectable seams are not. A simpler design has four objects:

1. `CandidateSchedule`: one sealed, complete pre-outcome schedule and forecast receipt.
2. `TemporalOptionState`: advanced by exactly one primitive C2 environment step per ordinary episode-loop slot.
3. `ClosedOption`: immutable actual 1–4-step sequence, zero bootstrap, complete lineage, terminal/no-padding semantics.
4. `commit_closed_option`: the sole Q2F-plus-combined-Main transaction.

K0 falls back, K1 is forced, and only K≥2 invokes Q2F. Q2F keeps a real role by learning actual canonical R2 returns and ranking only candidates already certified for positive forecast EE and system-R2 direction. Association choices change service, rate, and power, giving a defensible causal path to EE; realized EE remains empirical.

## Experiment recommendation

The census and K4 smoke are sufficient to justify and size bounded-runner implementation. They are not sufficient to launch 1500/3000 episodes.

Pre-launch gates are the six fixes above, clean current-hash tests, a completed real developmental runner smoke, deterministic resume equivalence, and matched metric schemas. Run 1500 first; continue to the preregistered 3000 checkpoint only on integrity/safety criteria, not because interim EE looks favorable.

Only data can answer support frequency, Q2F-versus-random realized R2, realized service/throughput/power/ratio-of-sums EE, inter-role interactions, variance, and efficacy. Tests, census counts, and smoke runs cannot establish improvement.

