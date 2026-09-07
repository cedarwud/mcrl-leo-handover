# V0.18 next learner-readiness inventory

Date: 2026-09-04 (Asia/Taipei)

Scope: read-only inventory after the V0.18 relational-ZR C3 design seam.  No
simulator, source outcome, learner update, episode, or TEST byte was opened by
this inventory.  The V0.18 analytic contract, formula, relational encoder, and
relational head were not modified.

## Current authority boundary

The analytic gate remains the only next executable decision.  Its frozen
contract is
`.scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md`.
It allows only four fresh TRAIN worlds, three frozen Q1/Q2 lineages, and the
three matched `BASE`/`EXACT_ZR`/`NOMINAL_ZR` arms.  A pass authorizes one
separately frozen relational-Q3 learner gate; it does not authorize episode
training or TEST access.

The design note
`.scratch/multi-catfish-v018-relational-zr/spec.md` is explicitly a draft, not
authority.  The learner seam
`.scratch/multi-catfish-v018-relational-zr/learner-seam-draft.md` is likewise
implementation-only and says `DO NOT TRAIN` until the analytic gate passes.

The current pure head
`src/mcrl/algorithms/ee_axis_relational_zr_c3_head.py` remains intentionally only
a forward scorer.  It has one shared victim scorer, fixed centring on the
reference action, native-mask preservation, and compatibility-gated positive
contributions.  W176 contains six pure head tests; it does not establish
learnability.  A non-authoritative preparation lane now supplies a separate
structured source closure, learner wrapper, gate arithmetic, and fail-closed
server templates under
`.scratch/multi-catfish-v018-relational-zr/next-learner-draft/`; none of these
opens a simulator or changes the head.

## Existing V0.14 material that is reusable as a pattern

The V0.14 learner receipt was read from
`artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/`.
The authenticated files have these hashes:

| file | SHA-256 |
|---|---|
| `result.json` | `289949275e9241cc5b885b1fc588a69e97446f755d9cf4f3ccfe9542f03f6c7c` |
| `result-seal.json` | `b9f9bb231c8df2b1d8a61d02d7e274fb484fac1f5d39626908941e8f958868dd` |
| `authority.json` | `9de934468e79abe2ad6854b4f617fcb9521109e4d2bff6c7225962daef0877f4` |

The receipt is `STOP_LEARNABILITY_GATE`: frozen Q2 passed with mean skill
`0.835429...` across all three initializations, while the old action-set Q3
failed with mean skill `-0.037319...`; no TEST, episode training, or EE
efficacy claim was made.  The existing V0.14 runner provides useful patterns
for immutable source shards, complete-world split validation, cyclic batches,
Adam updates, write-once checkpoints, strict reload, and per-initialization
receipts.  It cannot be reused as the V0.18 learner itself because it expects
flat `[N,A,D]` state surfaces and `EEAxisV014PairwiseLearner`, whereas V0.18
requires structured `[N,A,7]` action context plus `[N,A,V,6]` victim tokens and
the new `RelationalZRC3QNetwork`.

The frozen Q1 rung-10 heads and learned-Q2 rung-3000 checkpoints are already
authenticated by the V0.15 helper used by the analytic runner.  They remain
frozen inputs; no Q1/Q2 update is part of the next learner gate.

## If `PASS_ANALYTIC_DIAGNOSTIC` is returned: minimum 100-update gate

The following items are still missing.  They must be implemented and frozen
before opening any new learner-source outcome.  The list is deliberately
limited to one Q3 learner attempt; it does not introduce another architecture
or a second target.

### 1. A separate learner contract (must wait for the analytic decision)

Freeze a new pre-outcome contract containing, at minimum:

- fresh TRAIN source worlds, complete-world TRAIN/validation split, three
  initialization seeds, lineage-to-checkpoint mapping, keyed-field namespace,
  and source behavior policy `Q1 + learned-Q2`;
- exact source schema and array digests, with action context `[N,A,7]`, victim
  tokens `[N,A,V,6]`, native action mask, victim mask, reference action, and
  predecision compatibility bit;
- exact-ZR `z3` surface as a label only; nominal predecision variables are the
  only learner inputs; no `ActionEvaluation`, realized physics, target sign,
  teacher action, future state, or outcome-derived filter may cross the input
  boundary;
- fixed Q3 architecture/optimizer/`kappa`/`beta`, CPU execution, deterministic
  batch schedule, exactly 100 updates, and write-once checkpoint/reread rules;
- fixed validation skill/support gate and exact stop tokens.  No favorable
  seed, rung, threshold, rescaling, feature, or horizon choice may be made
  after outcomes are visible.

This contract cannot be frozen before knowing that the analytic gate actually
authorizes the learner route.  A prose draft can be prepared, but it is not an
execution authority.

### 2. Structured V0.18 source harvester and reader

The current analytic runner writes shard/result JSON and digests, not a
trainable relational source dataset.  A new source-only runner must therefore
materialize immutable NPZ (or an equivalent non-pickle format) rows containing
the nominal observation tensors and exact-ZR target surface separately.  It
must:

1. encode and persist the relational observation before opening the exact
   counterfactual teacher;
2. store the exact target and compatibility as label/receipt fields only;
3. validate masks, reference centring, finite values, victim padding, array
   immutability, world/lineage identity, common keyed field, and all file/array
   digests;
4. keep TRAIN/validation separation by complete world, with no TEST path; and
5. reject any realised fading/SINR/rate/energy/power or `ActionEvaluation` field
   appearing in the feature payload.

No existing V0.14 source shard can be silently reinterpreted as this schema:
its `q3_states` are the retired 287-dimensional flat ZR state.

### 3. Relational-Q3 learner adapter and checkpoint receipt

The forward head needs a separate learner wrapper (the head source itself is
not to be changed in this inventory).  The wrapper must implement one
independent Q3 network and one optimizer with the fixed zero-bootstrap
pairwise surface loss:

- score the structured relational inputs through the one shared victim scorer;
- compare every legal candidate against the stored reference surface;
- divide native-bit targets by the frozen common `kappa`;
- retain the fixed gauge term, if selected in the learner contract;
- update only Q3, with no Bellman target, target network, Q1/Q2 gradient, or
  deployment coordinator; and
- expose deterministic `update`, `q_values`, strict checkpoint save/load, and
  parameter digest functions.

The checkpoint must bind the contract hash, source closure hash, code-manifest
hash, initialization seed, update count exactly `100`, network config,
optimizer state, and `TEST=false`/`episode_training=false` metadata.  A
checkpoint at 100 is the only binding learner endpoint unless a future
contract explicitly declares additional diagnostic rungs before source access.

### 4. Learner-gate adjudicator and verification

Add a pure gate analogous to the V0.14 head/joint adjudicators, but operating
on the structured relational head.  It must verify source closure before
training, use fixed 100 updates for every initialization, strictly reload each
checkpoint, and report per-initialization plus pooled metrics.  The contract
must decide in advance whether the binding clauses are the inherited
positive-validation-skill/support clauses, a fixed joint-support clause, or
both.  It must not turn a post-outcome diagnostic into a new acceptance gate.

Required pure/runtime tests include:

- source NPZ round-trip, canonical metadata, digests, no-pickle loading, and
  complete-world split checks;
- reference-centred Q3 and native-mask invariants on structured inputs;
- victim permutation/padding and user/action identity invariants;
- deterministic same-seed training, finite loss/gradient/parameters, and
  strict checkpoint round-trip at update 100;
- proof that only Q3 parameters change and Q1/Q2 receipts remain byte-stable;
- fixed batch schedule and exact update-count enforcement; and
- pure learner-gate stop/pass order and malformed/incomplete-panel rejection.

## Prepared server orchestration template (still inert before a pass)

The existing V0.18 analytic server wrappers do not provide a learner gate.  A
guarded template set is now prepared (but must not be configured or launched
before the new learner contract is frozen):

- a closure sync script for the new source runner, learner wrapper, tests,
  frozen Q1/Q2 receipts, V0.13/V0.15 helpers, and the new contract;
- a server runner that performs only the declared TRAIN source/100-update
  learner gate, uses one CPU thread per process, refuses overwrite, and writes
  per-initialization status/checkpoints;
- an independent server/local verifier and a finalizer that copies only a
  completed learner receipt into a new artifact root and writes a manifest.

The templates refuse to proceed before all of the following are supplied:
the future contract path and SHA-256, the future code-manifest path and
SHA-256, an explicit learner runner/config, and an isolated output root.  The
sync template's default preflight is synthetic-only.  No production world,
lineage, seed, threshold, source outcome, checkpoint, or TEST path is encoded
in the templates.

The server root and max-parallel choice must be declared in that contract.  A
server launch before the analytic pass would violate the current V0.18 gate.

## Can be prepared now vs. must wait

### Safe to prepare now

- this inventory and a non-authoritative API/contract draft;
- pure source-schema, learner-loss, checkpoint, and gate unit tests using
  synthetic arrays only;
- static import/dependency checks and server-script templates that refuse to
  run without a later frozen learner contract;
- authentication of the existing frozen Q1/Q2 receipt closure.

### Must wait for `PASS_ANALYTIC_DIAGNOSTIC`

- opening any new source world or exact-ZR target for learner data;
- freezing the learner contract as an execution authority;
- running the relational-Q3 optimizer or writing learner checkpoints;
- selecting/accepting a learned Q3 checkpoint for deployment; and
- any 100-episode, 1500-episode, or 9000-episode physical training/ablation.

The preparation lane added only pure, synthetic-ready components; it did not
freeze their production values or create source outcomes/checkpoints.  The
existing analytic wrappers remain the only current launch machinery until a
post-pass learner contract is frozen.  The new templates are intentionally
fail-closed and are not current launch machinery.

## Preparation files added (non-authoritative)

- `next-learner-draft/relational_source_schema.py`: immutable structured
  no-pickle NPZ reader/writer, array/metadata digests, feature denylist, and
  complete-world split validation.
- `next-learner-draft/relational_q3_learner.py`: one relational Q3 network and
  optimizer, fixed pairwise zero-bootstrap surface loss, q-value access,
  strict checkpoint round-trip, and parameter digest.
- `next-learner-draft/relational_q3_gate.py`: pure exact-100-update gate
  arithmetic with explicit thresholds and a pre-outcome frozen-contract hash.
- `next-learner-draft/tests/test_next_learner_draft.py`: eight synthetic-only
  tests covering source, learner, checkpoint, and gate seams.
- `next-learner-draft/sync_v018_relational_learner_template.sh`,
  `run_v018_relational_learner_template.sh`, and
  `finalize_v018_relational_learner_template.sh`: guarded server templates;
  all fail closed when no future frozen learner contract is supplied.

## Files inspected and untouched

- `.scratch/multi-catfish-v018-relational-zr/spec.md`
- `.scratch/multi-catfish-v018-relational-zr/learner-seam-draft.md`
- `src/mcrl/algorithms/ee_axis_relational_zr_c3_head.py`
- `tests/test_w176_ee_axis_relational_zr_c3_head.py`
- `.scratch/multi-catfish-v014-learner/run_v014_learner_gate.py`
- `.scratch/multi-catfish-v014-learner/run_v014_source_shard.py`
- `artifacts/multi-catfish-v014-learnability-20260903-r1/contracts/MULTI-CATFISH-MCRL-V014-LEARNABILITY-PREREG-2026-09-03.md`
- `artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result.json`
- `artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result-seal.json`
- `artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/authority.json`

The preparation files listed above were created in the non-authoritative draft
directory and are covered by the synthetic test result; the frozen V0.18
analytic contract, formula, head, and shared authority remain untouched.

No frozen contract, formula, shared authority, source receipt, head source, or
server result was changed.
