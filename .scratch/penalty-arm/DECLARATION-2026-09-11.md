# PENALTYARM — declarations fixed before any arm's result was read

Written 2026-09-11, after the OFF and PENALTY pilots were launched and before
any episode log from either was opened, and before the NULL_PENALTY arm was
configured. Nothing below may be revised after a number is seen.

## 1. What is run

| arm | mechanism | source of every value |
|---|---|---|
| `OFF` | `PenaltyConfig(kind="none")` | — the unpenalised path, bit-identical to the pre-port trainer (test `test_off_is_bit_identical_to_no_penalty_config`) |
| `PENALTY` | sibling preset **`TB-SRANK-kumar`**: Kumar Eq. (6) spectral penalty, **α = 1e-3** | `tier1b/TB-SRANK-kumar.yaml:62`; identical to the sibling's code default `KUMAR_ALPHA_DEFAULT` (`penalties.py:62`); identical to arXiv:2010.14498 p.9 verbatim |
| `NULL_PENALTY` | `kind="null_grad"` — an isotropic random vector of **the PENALTY arm's own measured per-head penalty-gradient L2 norm**, added to `.grad` after the TD backward | norms measured from PENALTY's logged `penalty_grad_norm_mean`, per head, averaged over its 500 episodes |

500 episodes, checkpoint every 100, seeds `(train 42, env 1337, mobility 7)`,
learning rate 1e-3, all three arms on the same pinned tree.

## 2. Values taken from the sibling rather than from my judgement

- coefficient α = 1e-3 (`TB-SRANK-kumar`)
- Φ = penultimate activations over the TD minibatch, **raw, not mean-centered**
- penalty added **after** the TD reduction, to the already-reduced scalar MSE
- **per head**, three times per update, each inside its own backward — this is
  the sibling's own resolution of the same three-head shape, not mine
- **no schedule**: constant α, every update, from update 0
- non-finite penalty is **skipped entirely**, not zeroed
- the logged TD loss stays **TD-only**, captured before the penalty is added

## 3. Marked UNSPECIFIED; my choice declared, not tuned

- **Which of the six presets runs.** The sibling offers six (three `decorr`,
  three `srank`) and never ran any. One PENALTY arm is authorised. I run
  `TB-SRANK-kumar` because it is simultaneously Kumar's published α and the
  sibling's code default. All six are ported and named in
  `SIBLING_PRESETS`; five are not run. **No sweeping**, whatever the result.
- **The `decorr` kind cannot be ported faithfully.** The sibling's Q rows are
  "the U=100 users of ONE env step", drawn from a step-context snapshot it
  carries beside the minibatch. This trainer's `update()` has only a
  128-transition replay minibatch spanning many users and many timesteps.
  The ported `decorr` branch computes a **different quantity** and is not run.
- **The NULL control matches a NORM, not a direction distribution.** In a
  ~20k-parameter space an isotropic random vector is nearly orthogonal to any
  fixed direction, whereas the penalty's gradient is not. This control bounds
  the reading "a perturbation of this size would have done it"; it does not
  reproduce the penalty's gradient geometry. Stated as a limit of the control.

## 4. Declared reading, fixed before the numbers

- **`PENALTY` > `OFF` and `NULL_PENALTY` ≈ `OFF`** → the representation
  structure is what helps. Strongest outcome.
- **`PENALTY` ≈ `NULL_PENALTY` > `OFF`** → the *perturbation* is what helps.
  Report as such; do **not** attribute it to the penalty's structure. This is
  a useful result, not a failure: it says optimise the perturbation directly
  and stop looking for better structure.
- **Neither beats `OFF`** → the mechanism does not transfer to this physics.
  Report and stop. **Do not sweep the coefficient.**
- **All three ≈ equal** → the arm did not engage; diagnose by the *logged
  penalty trajectory*, not by the endpoint metric (this is the sibling's own
  stated discipline for a null on a penalty arm).

Additional, carried from the sibling's disclosed hazard: a null on a penalty
arm has two readings — "the mechanism does not help" and "the penalty never
escaped its own flat region" — and they are separated only by whether the
**logged penalty value actually fell**. The penalty trajectory is logged per
episode per head for exactly this reason.

**500 episodes is not convergence.** The frozen reference is 9000. No number
from this study may be compared against a 9000-episode checkpoint, and every
statement of a result carries this sentence.

## 5. What would make me re-run rather than report

Only a surprise, and then at larger n with the re-run reported as a re-run.
Not: an inconvenient number, a missing separation, or a wrong sign.
