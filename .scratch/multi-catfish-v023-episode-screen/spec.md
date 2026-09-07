# Multi-Catfish MCRL V0.23 episode-screen seam

Status: `DRAFT_PRE_R3__NON_AUTHORITY__NO_EXECUTION`  
Date: 2026-09-05

This SDD defines a deep module and its public interface for a future bounded
episode screen.  It does not authorize simulation, episode training, a server
launch, a TEST read, or a scientific claim.  Promotion requires the V0.23 gate
decision, a separate frozen episode-screen contract, and an explicit launch
receipt.

## 1. Purpose and authority boundary

The module puts arm routing, environment stepping, checkpoint/resume, and
Chapter-5-shaped sweep emission behind one seam.  A caller supplies a frozen
screen request and an opaque execution adapter; the caller never loops over
episodes, selects a Catfish route, writes a checkpoint, or computes a metric
from an individual row.

The current method freeze permits Chapter-4 method prose to be frozen before
the C3 outcome, but explicitly does not establish learnability, composition
benefit, C1/C2 qualification, FULL-over-ablation ordering, or EE efficacy
(`docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md`, sections
"Still open before any gate or episode training" and "Claim ceiling").  The
current gate contract separately states that it cannot authorize 100, 500,
1500, 3000, or 9000 episode training and that episode training needs a new
frozen contract (`docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`,
section 0).

Accordingly, this file is an implementation-design seam only.  Its presence
does not change `NO-GO`, does not promote C3, and does not replace the current
authority documents.

## 2. Public module interface

The public module is named `EpisodeScreen`.  It is deliberately deep: the
interface has only plan, execute, resume, and receipt-digest operations while
the implementation owns arm construction, action selection, environment
stepping, state capture, atomic persistence, and sweep aggregation.

```text
ArmName = FULL | BASELINE | DROP_C1 | DROP_C2 | DROP_C3

EpisodeScreen.plan(ScreenRequest) -> ScreenPlan
EpisodeScreen.execute(ScreenPlan, OpaqueExecutionAdapter) -> SealedScreenReceipt
EpisodeScreen.resume(CheckpointRef, OpaqueExecutionAdapter) -> SealedScreenReceipt
EpisodeScreen.digest(SealedScreenReceipt) -> ReceiptDigest
```

`plan` is pure validation and hash construction.  `execute` and `resume` are
the only operations that may advance an episode stream.  `digest` exposes
only an immutable receipt digest and status; it cannot expose outcome rows.
There is no public `step`, `select_action`, `route`, `checkpoint`, `write`,
`plot`, `open_result`, or `post_process` method.

### 2.1 `ScreenRequest`

The request contains only these caller-visible values:

* a unique `screen_id` and schema version;
* an ordered, non-empty subset of the five primary `ArmName` values;
* one pre-registered bounded episode count (`E_short`, later 1500 or 3000
  only after promotion);
* TRAIN world identifiers, training seeds, and a common-random-field binding;
* an immutable sweep grid and output schema version;
* `checkpoint_period = 100`;
* authenticated bindings for the baseline policy, Q1/Q2 background, and any
  C3 artifact or deterministic generation rule used by the selected arms; and
* an execution-admission token.

The request must not contain an adaptive threshold, sign filter, outcome-based
arm choice, or a TEST identifier.  The implementation rejects any request
whose episode count is 9000, whose split is not TRAIN, whose hash binding is
missing, or whose configuration is changed after the first outcome is sealed.

### 2.2 Opaque execution adapter

`OpaqueExecutionAdapter` is an implementation adapter, not a second public
policy interface.  It provides a deterministic stream of canonical episode
inputs/results to `EpisodeScreen`; it owns simulator/environment stepping,
mobility, fading, and native state restoration.  A synthetic deterministic
adapter is the only adapter allowed for the first-slice plumbing criterion.

The public caller cannot ask the adapter to run one user, one action, one
route, or one arbitrary step.  This keeps arm routing and environment
stepping local to the module and makes the seam testable without importing a
simulator or TLE.

## 3. Frozen primary arms

The following five names are the complete primary screen vocabulary.  They are
not interchangeable with source-learner diagnostics.

| Arm | Public meaning | Required binding |
|---|---|---|
| `FULL` | All three admitted Catfish route contributions are active in the one-pass deployment score. | Q1, Q2, and an admitted exact C3 artifact/hash or completely frozen C3 generation-rule hash. |
| `BASELINE` | The exact frozen pre-Catfish Main baseline policy is evaluated without Catfish contributions. | An explicit baseline policy artifact/hash; it must not be inferred from a zero surface or from an archived launcher. |
| `DROP_C1` | The C1 contribution is deterministically excluded while the remaining arm bindings are held fixed. | Q2/C3 and the selected drop-mode binding. |
| `DROP_C2` | The C2 contribution is deterministically excluded while the remaining arm bindings are held fixed. | Q1/C3 and the selected drop-mode binding. |
| `DROP_C3` | The C3 contribution is deterministically excluded while the remaining arm bindings are held fixed. | Q1/Q2 and an explicit C3-omission binding; no C3 learner artifact is needed for the omitted contribution. |

For every primary arm, the screen uses the same declared worlds, seeds,
initial state, masks, common random field, episode count, and sweep grid.  The
only intentional arm difference is the hash-bound policy/route binding.  The
screen records that difference and rejects accidental drift.

The names are frozen now; the exact drop implementation is deliberately an
unresolved launch decision.  The launch contract must choose one mode and use
it consistently:

1. `HEAD_DROP`: retain a trained three-head checkpoint and set the named
   contribution to zero at composition; or
2. `SOURCE_ABLATION`: replace the named source with its equal-budget neutral
   source and retrain the affected route.

The current V0.23 gate contract distinguishes these questions and says that
later FULL/DROP-C1/DROP-C2/DROP-C3 efficacy claims require retrained source
ablations under a new contract.  This SDD therefore does not silently turn a
head drop into a source-ablation claim.

`SINGLE_C1`, `SINGLE_C2`, `SINGLE_C3`, `ZERO_SURFACE`, and `TEACHER_ORACLE`
are optional diagnostic arms in a separate namespace.  They must never be
counted as primary arms, substituted for BASELINE, or used to establish the
five-arm ordering.

## 4. Deterministic and hash-bound admission

Admission is checked before any outcome is opened.  Every selected arm has an
arm binding digest, and the whole request has a `run_fingerprint` covering
the method/schema version, worlds, seeds, field, masks, model/config hashes,
arm bindings, episode count, checkpoint period, and sweep grid.

### 4.1 Pre-R3 behavior

`DROP_C3` may be executed before the R3 scientific result **only in a
separately authorized quarantine run** because the named C3 contribution is
omitted.  Its Q1/Q2 background and all other bindings must still be
authenticated.  Its output is `SEALED_PENDING_GATE` and cannot be opened,
compared, tuned against, or cited before gate admission.

`FULL` may be planned or executed only when its exact C3 artifact/hash, or a
completely frozen deterministic C3 generation rule and hash, is bound in the
admission token.  A future pre-R3 quarantine execution still produces a sealed
receipt; the binding does not bypass the current V0.23 episode-training NO-GO.

Before `R3 decision + CONTEXT_DIAGNOSTICS_PASS` and a promoted episode-screen
launch contract, the current checkout authorizes only the synthetic plumbing
adapter below.  In particular, real simulator episodes for BASELINE,
DROP_C1, DROP_C2, or FULL must not be launched merely because DROP_C3 is
structurally executable.  If R3 holds or fails, scientific arm receipts stay
sealed and the next action is a new contract or redesign, not outcome-based
rescaling or sign reversal.

### 4.2 Post-gate behavior

After a gate outcome that explicitly permits a separate learner-screen
contract, and after the independent context status is admitted, the launch
contract may admit the five arms.  It must bind all five policy/source
artifacts before execution.  No arm may be added, removed, renamed, or
reinterpreted after an outcome is opened.

The sealed-result state machine is:

```text
PLANNED -> RUNNING -> SEALED_PENDING_GATE -> OPENED_AFTER_ADMISSION
                                      \-> INVALID (receipt/hash failure)
```

`OPENED_AFTER_ADMISSION` requires an explicit gate-admission token whose
fingerprint covers the sealed run.  There is no public operation that opens a
receipt with a missing, stale, or mismatched token.

## 5. Checkpoint and resume contract

The implementation writes an atomic checkpoint at the end of every 100th
completed episode (`100, 200, ...`).  The caller sees only a `CheckpointRef`;
temporary files, fsync, rename, and directory layout remain inside the
module.

Each checkpoint is a content-addressed record containing:

* `screen_id`, `run_fingerprint`, arm name, schema version, and completed
  episode index;
* all applicable Q1, Q2, and Q3 network states and optimizer states.  A
  primary three-route arm records all three networks/optimizers; an arm with
  an intentionally absent or immutable route records that state explicitly
  with its binding digest rather than silently dropping a field;
* Python, NumPy, Torch, environment, mobility, and fading RNG states that
  are applicable to the declared CPU execution;
* the complete restorable environment state, current episode cursor, action
  masks, common-field cursor, and their hashes;
* episode logs through the checkpoint, cumulative bits/energy/service totals,
  the last sealed receipt digest, and the exact byte offset/canonicalization
  version; and
* the complete config, method/schema digests, model/artifact hashes, adapter
  identity, and admission-token digest.

`resume` first verifies every stored digest and fingerprint, then resumes at
the next episode.  A mismatch is a hard failure; it may not silently restart,
skip an episode, merge logs, or change an arm.  An uninterrupted run and a
resumed run with the same binding must therefore have the same canonical
arm-scoped receipt bytes.

## 6. EE and sweep receipt interface

The module aggregates raw TRAIN episode quantities before division.  For every
arm, world, seed, and frozen sweep point it emits:

```text
ArmSweepReceipt {
  run_fingerprint,
  arm,
  sweep_point,
  episode_start,
  episode_end,
  total_bits_B,
  total_energy_E,
  ee_ratio_of_sums_eta = B / E,
  service_fraction_S,
  cumulative_receipt_sha256,
  status
}
```

`total_bits_B`, `total_energy_E`, and `service_fraction_S` are required raw
aggregates.  `eta` is the Chapter-5-comparable ratio of sums, never a mean of
per-row EE values.  The output also retains world/seed/episode provenance and
the sweep grid so that arm comparisons use matched denominators.  Any
additional diagnostics are additive and cannot replace these fields.

Sweep points, aggregation order, units, and rounding/canonicalization are
frozen in the request before execution.  The module emits sealed JSON/receipt
objects; chart rendering is downstream and cannot alter the scientific
receipt.  No result is treated as efficacy evidence until the corresponding
gate and episode-screen contract admit it.

## 7. Safety invariants and rejected paths

The implementation must reject or make unreachable all of the following:

* TEST worlds, TEST identifiers, or a mixed TRAIN/TEST run;
* 9000 episodes, an implicit promotion to 1500/3000, or an episode count not
  declared before execution;
* a coordinator, auction, vote, matching stage, joint decoder, iterative
  allocation, fallback, or post-selection repair;
* the legacy `scripts/run_server_training.py` P6/MODQN pipeline, old P6
  preregistration, archived launchers, archived checkpoints, or archived
  reward descriptions;
* outcome-dependent route signs, rescaling, horizon changes, lambda changes,
  threshold changes, seed changes, or arm selection; and
* treating C3 source-panel diagnostics (`INFORMED`, `MATCHED_PLACEBO`,
  `ZERO-SURFACE`, `TEACHER-ORACLE`) as the five primary episode-policy arms.

The current V0.23 three-route inference seam remains the only policy shape:
three independent Q functions and one masked sum/argmax.  The current
`ee_axis_lcsrs_three_route.py` checkpoint methods are a useful serialization
primitive, but they are not evidence of an episode loop or a complete screen.

## 8. First-slice checkable criterion

`FIRST_SLICE_PASS` is true iff a synthetic deterministic adapter, with no
simulator, TLE, fading service, or TEST access, runs `N = 200` episodes for
all five primary arms under one fixed synthetic binding and then satisfies all
of the following in one test:

1. the uninterrupted execution writes checkpoints at episodes 100 and 200;
2. a second execution stops after episode 100, resumes from that checkpoint,
   and reaches episode 200; and
3. for every arm, the resumed and uninterrupted runs have byte-identical
   canonical arm-scoped cumulative receipts and equal final receipt/checkpoint
   SHA-256 digests.

The test may compare bytes and hashes only; it must not interpret the
synthetic numbers as EE evidence.  Passing this criterion proves only that the
public seam hides arm routing, checkpoint/resume, and sweep emission
correctly.  It does not authorize a real episode run.

## 9. Unresolved decisions before promotion

The following are intentionally not guessed by this SDD:

1. the R3 scientific decision and independent `context_status`;
2. the admitted C3 artifact/generation-rule hash for `FULL`;
3. the exact baseline artifact/hash and its provenance;
4. `HEAD_DROP` versus `SOURCE_ABLATION` for the three DROP arms;
5. the scientific short-screen episode count (`E_short`, selected before any
   outcome; the synthetic criterion's `N=200` is not that decision);
6. the exact sweep axes, learning-rate arms, world/seed count, and promotion
   predicates for 1500 and 3000;
7. the complete restorable state schema for the concrete server environment;
   and
8. the explicit launch token and result-opening token after the V0.23 gate.

No unresolved item may be settled by reading a sealed result.  Until these
items are resolved in a promoted contract, the only legitimate execution of
this design is the synthetic first-slice criterion.

