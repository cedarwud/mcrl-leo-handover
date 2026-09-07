# Multi-Catfish MCRL V0.6 C2-k1 bounded learner preregistration

Date: 2026-09-02
Status: `PREOUTCOME_IMPLEMENTED_TESTED_PENDING_UBUNTU_STATE_AUTHORITY_AND_FREEZE`
Claim ceiling: `BOUNDED_Q2_LEARNER_SCREEN_ONLY_NO_TEST_NO_CH5_NO_LONG_TRAINING`

## 1. Conditional launch boundary

This preregistration was written before the C2-k1 T1 source-oracle shards
completed.  All three source processes have now exited, but no shard exit
receipt, partial source, merged source, target, diagnostic, or outcome has
been opened.  It does not
authorize a learner by itself.  Every learner command must fail closed unless
the independently verified T1 verdict is exactly

```text
AUTHORIZE_ONE_BOUNDED_C2_K1_LEARNER_SCREEN
```

`T1_INVALID_NO_TRAINING`, `C2_K1_SOURCE_FALSIFIED_NO_TRAINING`, a missing
verdict, a partial shard, or any other value forbids every Q2 optimizer step.
The T1 source rows must not be inspected to alter this plan's architecture,
loss, learning rate, update budget, seed, checkpoint, or evaluation rule.

Before the T1 verdict or any T1 diagnostic is opened, the dedicated V0.6
Q2-only learner and evaluator bytes, their contract tests, the exact
machine-readable learner plan, the authenticated target-free state sidecar
and live-replay verification receipt, and all three fresh-Q2 update-0
parameter digests must exist and be independently sealed by SHA-256.  The T1
verifier must emit a write-once verdict artifact and seal; a caller-supplied
string never authorizes training.  The exact v2 verdict artifact and seal bind
the T1-preregistration file digest and the frozen T1 verifier code-authority
digest.  The learner consumer independently requires that verifier digest to
equal the exact `PREPARE_LIVE` code-authority digest.  The pre-reveal freeze
additionally binds the verdict-writer bytes.

The single allowed freeze root is
`artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/freeze`.
Before any file is written there, the runner must authenticate the recovered
107-file pre-learner simulator closure against `PREPARE_LIVE`, then require
every one of those files to remain byte-identical and permit exactly seven
learner-only extensions:

```text
src/mcrl/algorithms/ee_axis_v06_c2_k1.py
src/mcrl/runtime/ee_axis_v06_c2_k1_formal_verdict_writer.py
src/mcrl/runtime/ee_axis_v06_c2_k1_learner.py
src/mcrl/runtime/ee_axis_v06_c2_k1_learner_contract_v2.py
src/mcrl/runtime/ee_axis_v06_c2_k1_learner_prep.py
src/mcrl/runtime/ee_axis_v06_c2_k1_q13.py
src/mcrl/runtime/ee_axis_v06_c2_k1_state_authority.py
```

The pre-reveal freeze stores and seals that simulator-extension receipt, the
complete bounded runner code authority, and the exact W102--W110 test bytes.
Training and DESIGN-EVAL must reauthenticate the same paths and receipts; a
relocated prepare, baseline, seal, freeze root, train directory, or evaluation
directory fails closed.

## 2. Scientific question

The bounded screen asks:

> Can one fresh Q2, trained only on the full-support C2-k1 comparisons from
> its matching frozen Q1+Q3 continuation lineage, generalize to fresh
> physical worlds such that adding Q2 improves canonical ratio-of-sums EE
> relative to the same frozen policy without Q2, while preserving service?

T1 passing proves only exact source-oracle headroom.  This screen separately
tests estimation and deployment generalization.  It is not final confirmation
and does not establish that `FULL` exceeds frozen Main.

The fit has only 12 distinct predecision states.  Each is a
complete-28-support frozen-Main-departure anchor paired with all 28 actions.
DESIGN-EVAL applies Q2 to all users and later steps, including partial-mask
states absent from this fit.  A failure therefore cannot by itself separate
estimator error, partial-mask extrapolation, every-step application, all-user
application, or the extension from the source window to ten decisions.

## 3. Frozen learner family

There are three independent model lineages.  For each lineage, Q1 and Q3 are
the exact frozen heads authenticated by T1.  A new Q2 is initialized and
trained; Q1 and Q3 have no optimizer and must remain byte-identical.

| Choice | Frozen value |
|---|---|
| Q2 state | V0.3 causal Q2 state, 228 float32 entries |
| actions | 28 common legal action slots |
| Q2 architecture | masked mean/max action-aligned scorer |
| exact Q2 class | `mcrl.algorithms.ee_axis_v06_c2_k1.EEAxisV06C2K1Trainer`, containing exactly one `MaskedMeanMaxQNetwork` |
| hidden widths | `(100, 50, 50)` |
| activation | `tanh` |
| optimizer | Adam |
| Adam parameters | `lr=0.001`, `betas=(0.9,0.999)`, `eps=1e-8`, `weight_decay=0`, `amsgrad=False` |
| target scale | \(\kappa=10{,}097{,}071{,}012.757404\) bit; binary64 `0x1.2cea89d260f2ap+33` |
| gauge coefficient | \(\beta=0.1\); binary64 `0x1.999999999999ap-4` |
| Q2 loss weight | `1.0` |
| config loss weights | `(1.0, 1.0, 1.0)`; only index 1 is operative, all three remain fixed for digest stability |
| batch | all 336 rows of the matching lineage in fixed world/action order |
| sampling | full batch, no shuffle, no replacement, no sign filter |
| optimizer steps | exactly 100 |
| checkpoints | update 0 and update 100; update 100 is the fixed primary model |
| device | CPU deterministic path |
| deterministic execution | PyTorch deterministic algorithms enabled; one CPU thread |

For each lineage the dedicated constructor calls `torch.manual_seed(q2_seed)`
and immediately instantiates exactly one `MaskedMeanMaxQNetwork`; no other
network or stochastic draw may occur between the seed call and construction.
Its update-0 parameter digest is sealed before T1 reveal.  The existing
gate-selected container retains its resident legacy Q2 only as part of the
authenticated frozen container.  The bounded learner never calls its
`forward()` or `state_dict()`, never sums it, never copies it into the fresh
trainer, and never places it on an optimizer path; it has zero influence on
training and DESIGN-EVAL actions.  Q1 and fresh Q2 consume
the V0.3 causal state; Q3 consumes the distinct V0.4 C3 state.

The three fresh Q2 initialization seeds are fixed as:

| T1 lineage | Frozen Q1+Q3 initialization | Fresh Q2 seed |
|---|---:|---:|
| `q13-a` | `2026092101` | `2026102101` |
| `q13-b` | `2026092102` | `2026102102` |
| `q13-c` | `2026092103` | `2026102103` |

No learning-rate arm, loss arm, update ladder, early stopping, best-checkpoint
selection, cross-lineage pooling, or post-outcome retry exists.  Update 100 is
used even if an earlier diagnostic loss is smaller.

Each lineage may write only to `freeze/train-{lineage}`.  A write-once attempt
artifact is created before its first optimizer step.  DESIGN-EVAL may write
only to `freeze/design-eval`, with its own write-once attempt artifact created
before the first DESIGN-EVAL seed is opened.  An interrupted or valid failed
attempt therefore cannot be redirected to a new output directory and retried.

The 100-update budget is the first rung of the already sealed V0.4
`(100, 500, 1500)` ladder and was chosen without C2-k1 outcomes.  A failed
screen cannot distinguish underfitting from misspecification and does not
authorize a later rung.

## 4. Target-free state sidecar

Before opening T1 targets, one write-once state sidecar must bind the 12
prepared anchors to the exact target-free `PREPARE_LIVE` authority.  For each
anchor it stores only:

- pool, world, step, focal user, and anchor digest;
- the focal 228-D V0.3 causal state as exact float32 hex values;
- the 28-entry Boolean action mask and reference Main action;
- state-schema, simulator-manifest, Q1/Q3-lineage, code, preregistration, and
  prepare digests; and
- an explicit assertion that no post-decision or counterfactual target,
  branch rate, branch power, EE, service outcome, oracle action, or T1 source
  row was read or stored.  Normalized committed-previous-slot features such
  as prior recurrence power remain valid causal inputs.

The sidecar must contain exactly 12 distinct anchors.  Its verifier rejects
missing, extra, repeated, non-finite, wrong-shape, outcome-bearing, or
digest-inconsistent content.  The sidecar may repeat the same focal state for
the three lineage-specific Q2 batches because the opening physical state is
common; targets and frozen continuation policies remain lineage-specific.

Production acceptance additionally requires a second live replay of all 12
anchors to reproduce every exact float32 state, action mask, reference action,
physical candidate mapping, CRN root, and encoder digest.  The T1
preregistration authority is
`e9fe8e83ba01f99076ce435b2499ae919cabbf55659433549a6a576e7a6c065f`.

## 5. Training rows and loss

After and only after the formal T1 authorization, each verified source row is
joined to its sidecar state by the sealed anchor key.  For lineage \(r\), the
batch contains all 12 worlds and all 28 candidate actions:

\[
12\times28=336\text{ rows}.
\]

The reference action is the frozen Main opening action for that anchor.  The
candidate action is the enumerated native action.  The Q2 loss is

\[
\ell_2=
\frac{1}{336}\sum_n
\left(
 Q_2(s_n,a_n^C)-Q_2(s_n,a_n^M)
 -\frac{\zeta_{2,n}}{\kappa}
\right)^2
+\beta\frac{1}{336}\sum_n Q_2(s_n,a_n^M)^2.
\]

The reference-equals-reference control remains in the batch.  Positive, zero,
negative, and all-dark complete rows are retained.  No Bellman bootstrap,
target network, legacy reward, clipping, route weight, Q1/Q3 gradient, or
cross-lineage target average is allowed.

## 6. Fresh DESIGN-EVAL block

The fixed DESIGN-EVAL physical seeds are

```text
2026103001, 2026103002, 2026103003, 2026103004, 2026103005,
2026103006, 2026103007, 2026103008, 2026103009, 2026103010
```

They are disjoint from T1's `2026101001..2026101030` pool and every named Q2
initialization seed.  They may be opened once only after all three update-100
checkpoints are sealed and independently verified.  They are DESIGN-EVAL,
not TEST and not final confirmation.

For every physical seed and matching model lineage, run ten decision steps
with 100 users under two matched arms:

- `FULL`: one common safe mask and
  \(\arg\max[Q_1+Q_2+Q_3]\) at every decision step;
- `DROP_C2`: the same frozen Q1/Q3, common safe mask, and
  \(\arg\max[Q_1+Q_3]\) at every decision step.

At each decision Q1 and fresh Q2 receive the V0.3 state, while Q3 receives
the V0.4 C3 state.  The resident legacy Q2 is never evaluated, copied, or
summed by the bounded learner.
Ties select the lowest legal action index, matching NumPy `argmax`.  An empty
mask executes `NO_OP=-1` and does not evaluate Q2 for that user-step.
`DROP_C2` does not call the fresh Q2 at all; only `FULL` evaluates it.

The DESIGN-EVAL keyed-field component is
`multi-catfish-mcrl-v06-c2-k1-design-eval-field-v1`, rooted by the frozen
simulator source-manifest digest, Main checkpoint digest, simulator-prereg
digest, and physical DESIGN-EVAL seed.  Both arms share that root but evolve
their own branch-local states and masks.

The arms share the keyed exogenous random field but evolve on their own states
and legal supports.  There is no action tape, cross-branch action import,
repair, coordinator, or post-training override.  The evaluator produces
exactly \(10\times3=30\) matched lineage-world comparisons per arm.

Frozen Main may be recorded once per physical world as a diagnostic only.  It
is not a promotion gate in this bounded learner screen and may not select a
checkpoint or trigger a retry.

## 7. Necessary gates

All gates must pass.

### G-L — learner mechanics

- the formal T1 verdict is the exact authorization string;
- the single canonical freeze root, 107-file simulator baseline, and exactly
  seven learner-only extensions reauthenticate before training and evaluation;
- the formal-verdict verifier code-authority digest equals the digest frozen
  in `PREPARE_LIVE`;
- state sidecar and all 1008 source rows verify against their frozen digests;
- each lineage consumes exactly its own 336 rows once per optimizer step;
- all three Q2 models complete exactly 100 finite optimizer steps;
- Q1 and Q3 remain byte-identical and receive no gradient;
- the bounded learner never calls resident legacy Q2 `forward()` or
  `state_dict()`, and never copies or sums that network;
- only update 0 and 100 checkpoints exist and update 100 is reloaded exactly;
- no TEST, partial T1 outcome, old C2 source, or outcome-based selection is
  opened; and
- no retry, replacement, extra seed, hyperparameter arm, or checkpoint choice
  occurs.
- before any DESIGN-EVAL seed opens, `DROP_C2` replayed at all 12 sealed T1
  anchors reproduces all 36 PREPARE_LIVE Q1+Q3 score vectors and `a_D`
  actions bit-for-bit; and
- the learner consumes a sealed formal-verdict artifact and file seal, never
  a caller-provided verdict literal;
- the formal verdict, complete source, state sidecar, independent live-replay
  receipt, prepare authority, and each lineage's exact 336-row batch receipt
  are reauthenticated before DESIGN-EVAL; and
- every DESIGN-EVAL row binds the V0.3 and V0.4-C3 initial-state hashes,
  initial mask, keyed-field root, action trace, action-flip count, raw bits,
  energy, EE ratio, and row digest before gate adjudication.

The result artifact must contain an explicit machine-adjudicated `G-L` entry.
Promotion is the conjunction `G-L AND G-E AND G-S`; successful execution of
the evaluator cannot silently stand in for `G-L`.

### G-E — held-out marginal EE

Using raw pooled ratio-of-sums EE over the 30 matched comparisons:

- pooled `FULL` EE is strictly greater than pooled `DROP_C2` EE;
- at least two of three lineage-specific EE contrasts are positive; and
- at least 7 of 10 physical-world contrasts are positive after pooling that
  world's three fixed lineages before forming the ratio difference.

Exactly zero is not positive.  The independent physical unit is the world,
not a user, decision step, action, or model lineage.

The `>=7/10` sign requirement alone passes symmetric independent noise with
probability `176/1024 = 0.171875`; the joint G-E null pass rate depends on
correlation and is approximately bounded by `0.043..0.172`.  G-E is a
design-screen threshold, not a significance test, and passing only authorizes
a fresh confirmation.

### G-S — service protection

- pooled `FULL` served user-step fraction is not below `DROP_C2`; and
- at least two of three lineage-specific served-fraction contrasts are
  nonnegative.

Service is a separate guard and never remasks the realised-rate EE numerator.

## 8. Diagnostics that cannot rescue or veto the gates

Report training loss at updates 0 and 100, finite parameter norms, pairwise
target MAE, Q2 action-flip rate relative to `DROP_C2`, delivered bits, energy,
served fraction, outage, and EE by lineage and physical world.  Also report
`FULL` versus frozen Main diagnostically.  None may replace G-L/G-E/G-S,
select another checkpoint, or justify a second learner arm.

Also report, by lineage and world, `q2_surface_median_abs`,
`q13_surface_median_abs`, `q2_to_q13_magnitude`, and the fraction of deployed
user-decisions with complete 28-action support.  These diagnose too-small Q2
surfaces and partial-mask extrapolation but cannot rescue or veto a gate.

## 9. Stop and promotion rules

- A structural, provenance, state, checkpoint, or runtime failure yields
  `C2_K1_LEARNER_INVALID_NO_RETRY`.  No efficacy interpretation is allowed.
- A structurally valid failure of G-E or G-S yields
  `C2_K1_LEARNER_NOT_CONFIRMED`.  The exact source remains valid headroom
  evidence, but this fixed learner/representation is not promoted.  No
  learning-rate, update-count, loss, seed, checkpoint, replacement-world, or
  fresh-seed rescue is authorized.  This consumes T1's one bounded-screen
  authorization.  Any successor requires a new source-level preregistration
  that declares every prior C2-k1 learner screen and outcome.
- Passing all gates yields
  `AUTHORIZE_FRESH_C2_K1_CONFIRMATORY_ABLATION_ONLY`.  It is not final C2 or
  Chapter 5 evidence.

Final C2 acceptance still requires a separately preregistered fresh
confirmation that `FULL > DROP_C2`.  Final Multi-Catfish acceptance still
requires one unified held-out evaluation showing `FULL > DROP_C1`,
`FULL > DROP_C2`, `FULL > DROP_C3`, and `FULL > Main`, with the service guard.
No 1500/3000/9000 simulator-episode run is authorized here, and the user must
be explicitly notified before any 9000-episode run.

## 10. Compute boundary

State-sidecar implementation, synthetic tests, contract review, and document
freezing are non-heavy local work.  If T1 authorizes the screen, Q2 fitting is
expected to take minutes; the matched DESIGN-EVAL simulation is heavy,
non-GUI work and must run on the Ubuntu server.  Estimated combined wall time
after a conformant runner exists is 15--45 minutes.  The exact launcher and
output paths must be frozen in a pre-reveal receipt before the T1 verdict is
opened, without changing any scientific choice above.  The runner, tests,
three update-0 checkpoints, and their parameter digests are part of that
receipt.

Fresh Opus Max and Sol Ultra reviews completed before freeze.  Their two
substantive findings were converted into hard gates: the canonical Ubuntu
checkout must authenticate as 107 baseline files plus exactly the seven
declared extensions, and DESIGN-EVAL uses a bounded-runner Q1/Q3-only
immutability snapshot that cannot call resident-Q2 `state_dict()`.

The current local pre-outcome implementation gate is 109/109 passing tests
across W102--W110, plus successful Python compilation and `git diff --check`.
This is implementation/provenance evidence only; it is not evidence that C2
improves EE.
