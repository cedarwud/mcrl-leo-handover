# V0.19 normalized-output repair (implementation proposal)

Status: `IMPLEMENTATION_PROPOSAL_NOT_FROZEN`

This isolated lane repairs the conditioning of the relational C3 learner. It
does not revise the EE formula, source target, features, masks, model widths,
optimizer, learning rate, update count, Q1/Q2 bindings, validation metrics, or
deployment sum.

## Unit contract

The source teacher remains the native centered `z3_bits` surface. The learner
target is formed exactly once as `z3_bits / kappa`.

The shared victim scorer has an explicit `output_unit_mode`:

* `raw_bits`: the scorer emits raw-bit contributions and the centered aggregate
  is divided by `kappa` (legacy V0.18-compatible behavior).
* `normalized_bits_per_kappa`: the scorer emits normalized contributions directly
  and the centered aggregate is not divided again.

For the V0.19 candidate, the mode is required in the learner config, run
config, panel plan, adapter config, checkpoint, and validation-prediction
receipt. Missing or mismatched mode fields fail closed. No V0.18 receipt is
rewritten or reinterpreted by this lane.

The two parameterizations are algebraically equivalent under final-layer
scaling: if the normalized scorer parameters are the raw scorer parameters
divided by `kappa`, both heads return the same centered normalized Q3 surface.
The normalized parameterization removes the `1/kappa` factor from the gradient
reaching the shared scorer.

## Execution boundary

Only synthetic tensor/source tests belong to this lane. No simulator, source
harvest, learner gate, world, TEST split, or scientific contract freeze is
authorized by this file.
