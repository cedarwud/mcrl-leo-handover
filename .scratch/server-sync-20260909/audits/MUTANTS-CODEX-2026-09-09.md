| mutant | executed | rejected | assertion that fired | semantic / runnable verdict |
|---|---:|---:|---|---|
| replace the structured coupling with the existing scalar summary | yes | yes | `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 0.9999997749296758` | Yes. Shape-preserving and rejected semantically. |
| broadcast that scalar into the correctly shaped pair matrix | yes | yes | `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 0.9999997749296758` | Yes. Endpoint and presence slots retain correct dimensions. |
| keep the values but attach them to the wrong resource pairs | yes | yes | `structured pairwise-coupling obligation violated: dominant oracle twin must score positive, got -0.9999997749296758` | Yes. The exact gain multiset and shape are retained. |
| pass the block into the model interface but bypass the branch that consumes it | yes | yes | `structured pairwise-coupling obligation violated: dominant oracle twin must score positive, got -0.9999999958776927` | Yes. The real invariant vector is constructed before the pair slice is bypassed. |
| replace the head with a constant positive output | yes | yes | `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 1.0` | Yes. It returns a valid scalar and fails the negative-side obligation. |

## Regression witness result

**Established — `DIAGNOSTIC_NOT_CLAIM`.**

The test-only switch is `MCRL_TEST_CROSS_GAIN_MUTANT`. The observed sequence was:

1. Historical scalar collapse: **FAIL**, pytest exit 1.
2. Repaired implementation: **PASS**, pytest exit 0.
3. Historical scalar collapse replay: **FAIL**, pytest exit 1 with the same assertion and value.

Repaired production-head scores:

- dominant: `+0.999329299739067`
- diffuse: `-0.999329299739067`

The historical replay uses the existing victim `interference_summary` in a correctly sized 129-value pair block while discarding endpoint-bound structure.

## Oracle-backed information twins

`CROSSGAIN-REPAIR-2026-09-09.md` was present immediately.

The diagnostic evaluates `00`, `10`, `01`, and `11` through the real V0.25 `resolve_configuration` path using `FixedRF`, `Geometry`, `RadiationConfig`, `ACMRate`, and `HardwareInventory`. `coalition_identity` evaluates:

`Psi = F(11) - F(10) - F(01) + F(00)`.

No asserted `synergy` or `antagonistic` label supplies the signs.

Removing `pairwise_cross_gain_terms` makes the twins’ canonical payload bytes and reduced invariant vectors exactly equal. All non-coupling features and every `interference_summary` are identical.

The victim scalar total is exactly `9 × 2^-44`, represented as `0x1.2000000000000p-41`.

- dominant structure: `(7, 1, 1) × 2^-44`
- diffuse structure: `(3, 3, 3) × 2^-44`

Both totals are exactly equal.

Exact normalized interactions:

- dominant: `+9233611.111111175`
- diffuse: `-24811041.666666724`

Eight complete evaluations had maximum exact spread `0`. The declared `eps` is `1,000,000`, above observed numerical noise and safely inside both signed margins.

## Honest limit

This witness proves only that the reduced scalar representation is insufficient for this admissible engine-evaluated pair. It does not prove that the full representation is sufficient everywhere, that the architecture can use every distinction, that training will find one, or that a learned distinction will generalize.

That limitation is included in the test docstring. The production head is manually parameterized solely to isolate encoder and consumption semantics; no fitting or generalization claim is made.

## Verification

```text
nice -n 10 env -u MCRL_TEST_CROSS_GAIN_MUTANT PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/stagec_v025/test_pairwise_cross_gain_mutants.py
```

```text
..                                                                       [100%]
```

`py_compile` and `git diff --check` also passed. The optional full Stage-C suite was interrupted after ten minutes inside an existing slow acceptance test; two tests had passed and no failure had appeared. No full-suite pass is claimed.

No production file, physics implementation, threshold, sign, seed, horizon, price, service guard, acceptance rule, or `src/mcrl/env/` file changed.

Files:

- [mutant test](/home/sat/mcrl-v025-mutants-ws/tests/stagec_v025/test_pairwise_cross_gain_mutants.py)
- [full report](/home/sat/mcrl-v025-mutants-ws/MUTANT-WITNESS-2026-09-09.md)

The requested `pilot-ws` was read-only under this session’s filesystem policy, so the clean repaired `mutants-ws` snapshot was used and the dirty pilot sibling was not modified. The diagnosing-bugs workflow supplied the deterministic red-capable loop and explicit red/green/red evidence. Elapsed goal time: approximately 31 minutes 49 seconds.
