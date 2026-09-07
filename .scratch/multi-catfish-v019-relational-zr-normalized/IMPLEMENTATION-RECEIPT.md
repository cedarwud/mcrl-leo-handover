# V0.19 normalized-output implementation receipt

Status: `IMPLEMENTATION_ONLY_NOT_SCIENTIFICALLY_FROZEN`

Pure checks completed on 2026-09-04:

```text
.venv/bin/pytest -q .scratch/multi-catfish-v019-relational-zr-normalized/tests
8 passed
```

The lane adds an isolated V0.19 head, learner, runner, run-plan builder, panel
plan builder, and source-adapter config parser. The V0.18 source/learner files
and frozen receipts remain untouched. No simulator, source harvest, learner
gate, world, or TEST split was opened.

The production candidate mode is `normalized_bits_per_kappa`; `raw_bits` is
available only as an explicit legacy-compatible mode. The source target remains
native `z3_bits`, and the learner divides it by `kappa` exactly once.
