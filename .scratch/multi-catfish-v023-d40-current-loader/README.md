# D40 current-loader scratch seam

This directory is the complete ownership boundary for the V0.23
`PLUMBING_ONLY` D40/current-model adapter. It does not edit or import a
simulator launch path, open TEST, train, evaluate, or change any source,
authority, artifact, or other scratch directory.

The authenticated source is the exact regular file

```text
.scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt
```

with SHA-256

```text
d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc
```

The adapter reads the actual V0.20 split payload (`q1.q_networks[0]` and
`q2.q`), rejects a legacy Q3, and compares every selected state-dict key,
shape, dtype, and relevant configuration field before mutating the current
`EEAxisLCSRSThreeRoute`. Loading is transactional and Q3 is never sourced from
D40; a constructed current model receives Q3 only from its explicit
deterministic seed.

The current real result is intentionally fail-closed: D40 Q1 has a masked
mean/max scorer whose first scorer weight is `(100, 28)`, D40 Q2 has a V0.14
action-set scorer whose first scorer weight is `(100, 48)`, and the current
action-shared Q1/Q2 heads require `(100, 12)`. The public loader raises
`D40CompatibilityError` with those field-level mismatches and performs no
approximation or scientific-value conversion.

The structural success-path tests use state dictionaries produced by the
actual current class only to prove exact-copy, Q3 isolation, malformed
rejection, transactional rollback, and checkpoint round-trip mechanics. They
are not D40 admission or an evaluability/gate result.

Run only the bounded local tests:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q \
  .scratch/multi-catfish-v023-d40-current-loader/test_d40_current_loader.py
```
