# Multi-Catfish MCRL V0.19 normalized-Q3 TRAIN-only preflight

Status: `FROZEN_BEFORE_PREFLIGHT_OUTCOME`

Claim ceiling: implementation conditioning evidence only.  A `GO_FRESH_GATE`
result is not a learned-Q3 validation result, a physical EE result, a Catfish
efficacy claim, or permission to start the five-arm episode screen.

## 1. Purpose and strict boundary

This bounded preflight answers one implementation question:

> With the V0.19 `normalized_bits_per_kappa` output parameterization, does the
> fixed pairwise learner receive a non-suppressed first gradient and reduce
> TRAIN pair-MSE below the same-batch all-zero reference over the final 20
> scheduled updates?

Only the already-opened V0.18 TRAIN source closures may be read, from this
exact root:

```text
/home/sat/mcrl-v018-relational-learner-20260904-r1/learned-q3-panel-r1/sources/TRAIN
```

The runner authenticates exactly twelve closures: four V0.18 TRAIN worlds by
three existing source lineages.  It never opens a path under `VALIDATION` or
`TEST`, never starts a simulator, never runs a source harvest, and never reads
an outcome-bearing file outside the authenticated source closure.  Q1 and Q2
are not loaded, updated, or replaced; their frozen bindings are irrelevant to
this conditioning-only check.

After authenticating the complete twelve-closure rectangle, this one
development learner deliberately selects only lineage `2026092101` and its
four TRAIN worlds.  The production learner binds one initialization to one
Q1/Q2 background lineage; mixing all three lineages in a single preflight
learner would test a different, invalid conditioning problem.  The other
eight closures are authenticated for completeness but never enter an update.

No V0.18 frozen contract, source, learner receipt, shared authority, paper, or
symbol table is edited by this preflight lane.

## 2. Development identities

The preflight uses exactly one new initialization/schedule pair, recorded by
the pre-outcome seed census in `SEED-CENSUS-DEV-2026-09-04.md`:

```text
initialization_seed = 2026120491
schedule_seed       = 2026120492
```

The schedule is deterministic, cycles the four selected TRAIN source closures
in sorted `world_seed` order, and samples 512 distinct row indices without
replacement from each 1000-row closure for each of exactly 100 updates.  The
schedule is authored by these constants before any source target is opened; it
is not tuned after a loss or gradient is observed.

## 3. Fixed learner profile

The following values are closed before execution and must appear unchanged in
the canonical receipt:

| field | value |
|---|---|
| `action_dim` | `28` |
| `action_context_dim` | `7` |
| `victim_token_dim` | `6` |
| shared scorer hidden layers | `(100, 50, 50)` |
| activation | `tanh` |
| optimizer | `Adam` |
| learning rate | `0.001` |
| batch size | `512` |
| updates | exactly `100` |
| `beta` | `0.0` |
| `kappa` | `0x1.2cea89d260f2ap+33` bits |
| scorer output units | `normalized_bits_per_kappa` |

The native target remains `z3_bits`.  The learner divides it by `kappa`
exactly once.  The normalized scorer emits the same `bits/kappa` surface
directly, so the forward surface is algebraically unchanged while the
gradient no longer carries an additional final `1/kappa` factor.  No target,
feature, mask, architecture, optimizer, learning rate, or deployment sum is
changed here.

## 4. Predeclared predicates

The predicates below are fixed before execution and are not relaxed after an
observed result.

1. On the first valid scheduled batch (one with at least one legal
   non-reference comparison), compute global gradient RMS over all trainable
   Q3 parameter elements immediately before `Adam.step()`.  It must satisfy

   ```text
   first_gradient_rms >= 1e-5 = 1000 * Adam epsilon
   ```

2. For updates 81--100, compute the pre-step legal non-reference pair-MSE on
   the learner's `target_surface_bits / kappa` scale and the all-zero Q3
   pair-MSE on the same row/action masks.  The arithmetic mean of the learner
   MSE must satisfy

   ```text
   mean(last20 TRAIN pair-MSE)
       < mean(last20 ZERO-null pair-MSE).
   ```

The receipt may include loss, gradient, output-standard-deviation, comparison
count, and parameter-movement diagnostics, but no diagnostic becomes an
additional acceptance predicate.  A missing, non-finite, malformed, or
boundary-violating value fails closed.

## 5. Mechanical decision and next boundary

The runner writes one canonical JSON receipt and a companion SHA-256 file.  It
returns:

- `GO_FRESH_GATE` only when all 100 updates complete, the source closure and
  unit checks pass, the first-gradient predicate passes, and the final-window
  MSE predicate passes;
- `ABORT` otherwise, including any source, kappa, mode, seed, path, finiteness,
  or receipt error.

`GO_FRESH_GATE` authorizes only preparation/review of the separately frozen
V0.19 fresh-world learned-Q3 gate.  It does not itself open VALIDATION, run
episode training, run the five-arm C1/C2/C3 screen, or authorize 9000 episodes.
The parent lane must freeze a new contract before any fresh-world gate.

## 6. Reproducibility and evidence discipline

The receipt records the contract and seed-census hashes, all twelve source
file and array hashes, the selected source lineage and its four used source
identities, both development seeds, every fixed
hyperparameter, all predicate values, update count, Q1/Q2 immutability, and
the closed access boundary.  The output directory is write-once.

This document is intentionally a pre-outcome draft.  It must not be rewritten
to explain or improve an observed preflight result.  A failed preflight means
the normalized implementation is not ready for the fresh-world gate; it does
not mean the physical C3 direction is ineffective.
