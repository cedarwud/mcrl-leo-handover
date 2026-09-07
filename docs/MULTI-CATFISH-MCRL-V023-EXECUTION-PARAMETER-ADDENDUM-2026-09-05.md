# V0.23 LC-SRS execution-parameter addendum

Status: `SEALED_BEFORE_SOURCE_OR_LEARNER_OUTCOME`

Parent contract:
`MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`

This addendum closes one execution parameter that the parent contract names
as frozen but did not give a literal value.  It does not change the LC-SRS
formula, state, topology, worlds, draws, folds, model, optimizer, thresholds,
or decision precedence.

## 1. Frozen matched-placebo key

The exact UTF-8 matched-placebo key is:

```text
MCRL_V023_LCSRS_MATCHED_PLACEBO_V1
```

Its SHA-256 is:

```text
7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825
```

Every leave-one-world-out fold uses this same key with the parent contract's
world-local stratum and deterministic nonzero cyclic-shift construction.  The
held-out world never contributes a row, target, transform, or statistic to
the fold's permutation.  All three student seeds in a fold consume the same
fold-specific permuted target source.

## 2. Integrity consequence

The preflight manifest and every learner receipt must bind this addendum and
the key digest above.  A missing or different literal key, a seed-specific
key, a key selected after any source or learner outcome, or a permutation that
crosses worlds makes the run `INVALID_RUN`.

This clarification was sealed before any V0.23 physical source shard or
learner fit was executed.  It is not an outcome-driven rescue and cannot be
changed after the first source outcome is opened.
