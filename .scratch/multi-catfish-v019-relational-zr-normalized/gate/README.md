# V0.19 fresh-world learned-Q3 gate

Status: `IMPLEMENTATION_READY__NOT_RUN`

This directory is the V0.19 versioned source-only gate seam.  It is copied
from the V0.18 report/verifier/orchestrator structure, but its runner and raw
prediction authority is the V0.19 normalized-output learner:

* `relational_validation_report_v019.py`
* `verify_relational_validation_report_v019.py`
* `relational_gate_orchestrator_v019.py`

The gate accepts exactly one scorer unit:

```text
normalized_bits_per_kappa
```

The value is required in the external validation config, learner result,
checkpoint payload and checkpoint config, prediction metadata, validation
report/seal, gate result, orchestrator summary, and independent verification.
Any `raw_bits` value or missing/mismatched marker fails closed.  The learner
acceptance/null/background/Q1-Q2 semantics are otherwise unchanged from the
frozen contract; this seam does not select worlds or seeds and does not alter
the acceptance thresholds.

The tests use only synthetic source/receipt fixtures and mock orchestration.
They do not open a simulator, read fresh worlds or VALIDATION/TEST data, run a
learner, or create a scientific gate result.  A later runtime owner may invoke
`relational_gate_orchestrator_v019.py` only after the V0.19 fresh source and
learner outputs have been produced and authenticated.

## Remaining runtime binding

The caller must provide a new frozen V0.19 contract/code manifest, a V0.19
runner config with `output_unit_mode=normalized_bits_per_kappa`, authenticated
TRAIN and VALIDATION source closures, and the three exactly-100-update learner
outputs.  No such runtime artifacts are selected or opened by this package.
