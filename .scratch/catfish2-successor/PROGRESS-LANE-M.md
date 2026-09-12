# PROGRESS — LANE-M (generic N-teacher set-valued MULTI-D3)

Worktree: /home/u24/papers/mcrl-leo-handover-cf2s-multi
Branch: catfish2/multid3-20260912, base 27f69edf
Deliverable: .scratch/catfish2-successor/LANE-M-MULTID3-2026-09-12.md

## Rule reminders (self)
- NEVER launch a learner arm. DEV/DEVVAL episode sets only if anything runs at all.
- Do not consume DEV k = 8 or k = 9.
- Never touch /home/sat/mcrl-v025-cf2s-b0-ws/ (four J shards live), nor other worktrees.
- git add named paths only.

## Steps
- [x] S0 read Amendment 15 (§0, §6, §7), Amendment 14 §8, E0 freeze doc
- [x] S1 read cf_dev.py / cf_teacher.py / cf_ratio.py / run_dev_e0.py arm table
- [x] S2 implement generic MULTI-D3 + matched 2-proposal null
- [x] S3 twelve tests
- [x] S4 mutants
- [x] S5 arm registration
- [ ] S6 deliverable + commit

## S2 receipt (2026-09-12)
Implemented, all in worktree `mcrl-leo-handover-cf2s-multi`:
- `src/mcrl/algorithms/cf_teacher.py`: `MULTI_MECHANISM_ID`, `MULTI_NULL_ID`, the
  teacher-source registry (`register_teacher_source` / `teacher_source` /
  `canonical_teacher_set` / `teacher_action_slots`), `membership_from_slots`
  (dedup + order-invariance + legality all STRUCTURAL via a boolean mask),
  `random_legal_action_slots` (matched null, distinct, without replacement),
  cardinality diagnostics, and `d3_set_margin_loss`.
- `src/mcrl/algorithms/cf_dev.py`: `MultiD3Spec`, `EXPECTED_TEACHER`,
  `NULL_BASE_FOR`, mechanisms `D3-multi` / `D3-multi-null`, replay label format
  v2 carrying A_CF, `teacher_labels_ext`, the multi teacher loss, Amendment 15
  section 7 diagnostics in the episode log, resume/checkpoint plumbing.
- `scripts/dev_e0_common.py`: arms 8 (FULL) and 9 (matched null), `multi_spec`,
  `spec_key`, `arm_name(arm, teachers)`, `multi_spec` in the config payload.
- `scripts/run_dev_e0.py` / `scripts/dev_e0_launch.py`: `--teachers` /
  `--n-proposals` and the `ARM:K:T0+Ti` / `ARM:K:nN` spec grammar. NOT LAUNCHED.
- `tests/test_cf_dev.py`: two-line update where the internal label tuple arity
  leaked into a test; all 22 pre-existing tests green.

## S3-S5 receipt (2026-09-12)
- `tests/test_cf_multid3.py`: 16 tests, all PASS (the twelve requirements plus the
  no-weights test, two null tests and arm registration). `tests/test_cf_dev.py`
  22/22 still green.
- Bit-identity receipts:
  - T2 loss+grad sha256 (both implementations) =
    631b09919603553294ef39834015991d7e8a2e64a4bccd5e002656e793866b6c
  - T1 parameter sha256 D3-T0 == FULL{T0} =
    8889f45e388403189a079a0e858cbcc57cabf1e52fe3da17207bb187341d300d
- Mutants: 11 named, run by `.scratch/catfish2-successor/run_mutants_lane_m.sh`,
  log `.scratch/catfish2-successor/mutants-lane-m.log`.
- Arms claimed: 8 = D3-multi (FULL, parameterised over the teacher set),
  9 = D3-multi-null (matched null, parameterised over the cardinality).
- FINDING for the controller: the declared two-proposal null is cardinality-matched
  only when the teachers never agree. Measured, structural, reported in the
  deliverable section 4. The Bernoulli-matched remedy is implemented and tested but
  NOT selected and NOT registered as an arm.
- Handover from the closed TDELTA-CANARY-PREP lane folded in: `_null_generator`,
  `D3_MECHANISMS`, `TEACHER_OF`, `MATCHED_NULL_ARM`, the conditional-identity-block
  hash pattern. `series_memo()` NOT used and NOT enabled (no parity receipt).

## S6 k = 8 integration (controller record 716f104e), 2026-09-12
- T_DELTA and T_TAIL are CLOSED; T_NEXT is the sole surviving second-source
  candidate and this k = 8 matrix is the only remaining path to a second Catfish.
- Bernoulli cardinality-matched null SELECTED as the k = 8 scientific comparator;
  p_singleton frozen at 9395/24000 = 0.39145833333333335 with numerator,
  denominator, rational, decimal, T_NEXT source identity and P0 artefact digest
  all in the config hash.  The rejected fixed two-proposal null keeps a DIFFERENT
  identity, key, run directory and hash; it cannot be selected accidentally.
- Training-only teacher-context seam: cft.TeacherContext + needs_context sources.
  T0 and every existing arm unchanged, behaviourally and in config hash.
- Exact committed Lane N cf_tnext.py (25448632) copied in, sha verified.
- SOURCE RECEIPT PASS: 24,000 decisions, 0 action mismatches, 0 legal violations,
  0 seam RNG mutations, 0 seam env mutations, action-trace sha256
  0568b2220a02898527e2a3d4dbc609da0c0aaf2f24dca81a282f9d555fbd9bee == Lane N.
- Five prospective k = 8 manifests built and checked; all hashes/keys/dirs distinct,
  shared identities shared, 300 / stop-after 100 / read depth 100 asserted.
- Tests: 67/67 green (test_cf_multid3 20, test_cf_dev 22, test_cf_tnext 25).
