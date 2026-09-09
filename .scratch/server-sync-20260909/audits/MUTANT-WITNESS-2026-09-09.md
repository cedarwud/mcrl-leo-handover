| mutant | executed | rejected | assertion that fired | semantic / runnable verdict |
|---|---:|---:|---|---|
| replace the structured coupling with the existing scalar summary | yes | yes | `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 0.9999997749296758` | Yes. The historical scalar-collapse replay returns the current 129-value pair-block shape, runs through the production head, and fails semantically rather than by exception. |
| broadcast that scalar into the correctly shaped pair matrix | yes | yes | `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 0.9999997749296758` | Yes. Endpoint and presence slots retain their correct dimensions; every present gain is replaced by the identical scalar summary. |
| keep the values but attach them to the wrong resource pairs | yes | yes | `structured pairwise-coupling obligation violated: dominant oracle twin must score positive, got -0.9999997749296758` | Yes. The exact gain multiset, endpoint slots, and shape are retained, while gains are rotated among source endpoints. |
| pass the block into the model interface but bypass the branch that consumes it | yes | yes | `structured pairwise-coupling obligation violated: dominant oracle twin must score positive, got -0.9999999958776927` | Yes. The real invariant vector, including the correctly shaped pair block, is constructed and passed to the head; only the pair slice is zeroed at the consumption seam. |
| replace the head with a constant positive output | yes | yes | `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 1.0` | Yes. The replacement returns a valid scalar and reaches the negative-side assertion; it does not crash. |

## Regression witness result

**Established — `DIAGNOSTIC_NOT_CLAIM`.** The test-only switch is
`MCRL_TEST_CROSS_GAIN_MUTANT`. The following sequence was run against
`test_designated_pairwise_cross_gain_obligation`:

1. `MCRL_TEST_CROSS_GAIN_MUTANT=historical_scalar_summary`: **FAIL**, pytest
   exit 1. The designated assertion reported
   `structured pairwise-coupling obligation violated: diffuse oracle twin must score negative, got 0.9999997749296758`.
2. switch unset (repaired implementation): **PASS**, pytest exit 0. The
   production `SetInteractionHead` scores were `+0.999329299739067` for the
   dominant twin and `-0.999329299739067` for the diffuse twin.
3. `MCRL_TEST_CROSS_GAIN_MUTANT=historical_scalar_summary` replayed: **FAIL**,
   pytest exit 1, with the same designated assertion text and value as step 1.

The old collapse is executable test code, not a prose reconstruction. It puts
the already-existing victim `interference_summary` into one position of a
zeroed pair block of the repaired width. Thus the historical replay is runnable
and shape-preserving while discarding endpoint-bound structure.

## Oracle-backed information twins

`CROSSGAIN-REPAIR-2026-09-09.md` was present when this task began, so no polling
delay or no-handoff fallback was needed.

The diagnostic uses `mcrl.physics_v025.resolution.resolve_configuration` with
the real `FixedRF`, `Geometry`, `RadiationConfig`, `ACMRate`, and
`HardwareInventory` implementations. For each twin it evaluates the four
profiles `00`, `10`, `01`, and `11`. Decision 0 activates `beam-a`; decision 1
activates `beam-b` and `beam-c`. `coalition_identity` then evaluates exactly

`Psi = F(11) - F(10) - F(01) + F(00)`.

No `synergy`, `antagonistic`, or asserted-answer fixture supplies these signs.
Both contexts use the same non-coupling payload, members, actions, affected
beam rows, occupancies, activation flags, capacities, margins, and global
features. Removing `pairwise_cross_gain_terms` makes both the canonical payload
bytes and the complete reduced invariant vectors exactly equal.

The forbidden scalar is also exactly equal: the victim
`interference_summary` is `9 * 2^-44`, represented as
`0x1.2000000000000p-41`; every other beam has zero in both twins. The pair
structures are:

- dominant: `(7, 1, 1) * 2^-44` from `beam-a`, `beam-b`, and `beam-c` into
  `victim`;
- diffuse: `(3, 3, 3) * 2^-44` over the same endpoint set.

Both `math.fsum` totals equal the scalar exactly, but one distribution has one
dominant contributor and the other has three equal weak contributors.

The exact normalized oracle interactions are:

- dominant:
  `9233611111111174999999 / 1000000000000000 = +9233611.111111175`;
- diffuse:
  `-24811041666666725000001 / 1000000000000000 = -24811041.666666724`.

Eight complete re-evaluations of each four-profile identity had maximum exact
spread `0`. The declared diagnostic margin is `eps = 1,000,000` normalized
units, strictly above the observed numerical noise and 9.23 times smaller than
the nearer signed oracle result. Therefore the dominant result is above
`+eps`, and the diffuse result is below `-eps`.

## What the mutant assertions establish

All five variants are runnable semantic mutants. The first four preserve the
model input shape; the fifth preserves the scalar output contract. Each is
executed under `_test_only_mutant`, and the meta-test requires its execution
counter to be positive. It catches only `AssertionError`, then requires the
failure message to name the structured pairwise-coupling obligation. A
`KeyError`, shape error, or other exception would fail the test rather than be
counted as a killed mutant.

The endpoint mutant rotates values among existing source-key slots, so its
failure depends on endpoint association rather than on the multiset of gains.
The bypass mutant first constructs the real production invariant vector and
then suppresses only the pair slice at the head seam, so its rejection tests
consumption rather than argument presence. The constant-positive mutant passes
the positive assertion and is rejected specifically by the negative one.

## Honest limit

This is an indistinguishability witness: it proves that the reduced scalar
representation is insufficient for this admissible engine-evaluated pair. It
does **not** prove that the full representation is sufficient everywhere, that
the architecture can use every relevant distinction, that training will find
one, or that any learned distinction will generalise. That limitation is in
the regression test's docstring.

The production head in this diagnostic is manually parameterized only to
isolate encoder and consumption semantics. No fit was performed, so this
report makes no “this setup can fit this diagnostic distinction” claim and no
generalisation claim.

## Verification

Primary deterministic command (two tests, including all five mutants):

```text
nice -n 10 env -u MCRL_TEST_CROSS_GAIN_MUTANT PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q tests/stagec_v025/test_pairwise_cross_gain_mutants.py
```

Result:

```text
..                                                                       [100%]
```

The module also passed `py_compile`, and `git diff --check` passed. An optional
full `tests/stagec_v025` compatibility run was stopped after ten minutes while
inside an existing slow acceptance test; two tests had passed and no failure
had appeared. This report does not claim a full-suite pass from that interrupted
run.

No production file, physics implementation, threshold, sign, seed, horizon,
price, service guard, acceptance rule, or file under `src/mcrl/env/` was
changed. The only code change is the diagnostic test module.

## Workspace note

The requested `pilot-ws` handoff was read successfully, but this session's
filesystem policy permits writes only in the clean repaired snapshot at
`/home/sat/mcrl-v025-mutants-ws` (commit `a59ae43`). The test and this report
were therefore written and verified there; the dirty sibling
`/home/sat/mcrl-v025-pilot-ws` was not modified.
