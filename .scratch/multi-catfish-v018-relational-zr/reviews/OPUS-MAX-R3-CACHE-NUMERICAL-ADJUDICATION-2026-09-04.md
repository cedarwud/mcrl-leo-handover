# Opus Max adjudication of the V0.18 R3 cache-equivalence stop

Status: `READ_ONLY_EXTERNAL_ADJUDICATION_COMPLETE`

Date: 2026-09-04 (Asia/Taipei)

Model invocation: `claude --model opus --effort max --output-format json`

Claude session: `a5f8eca7-a225-48c5-81f9-8bdc28022804`

## Scope and evidence boundary

This was a read-only numerical-method and scientific-gate review.  It did not
edit source, execute an action, open TEST, run a learner, or authorize episode
training.  The reviewer inspected the frozen R3 contract, its STOP result and
log, the equivalence runner, the current R2 cache implementation, and the
sealed R1 branch-by-branch implementation.

R3 result identity:

- result SHA-256:
  `dfb13a54a57023529e1e75d27e3b7816143a11313392bc6497c3f5207420a651`;
- receipt SHA-256:
  `8ae7c53ecc5f023b68a855f2118bfdcff4229b4d009638b31153781a84f6d909`;
- frozen R3 contract SHA-256:
  `2cd580080435a7809d8b9a565cd5906ad06e02d21f6cf8d16300a6f4b55d7c29`.

## Verified interpretation

1. The failing `280000 = 100 x 28 x 100` tensor was the complete `delta`
   surface, not the raw-rate primitive.  The preceding all-branch non-focal
   rate and interference comparisons completed successfully.
2. R1 recomputes each candidate interference sum from zero.  R2 starts from
   the reference sum and applies at most two signed beam corrections.  The
   beam/load algebra is the same, while the floating-point association differs.
3. The observed delta discrepancies were power-of-two multiples of about
   `1.7929e-6` bits, with a maximum `7.17164949e-6` bits.  They correspond to
   roughly 0.5--5 ULP of the `(noise + interference)` denominator after the
   Shannon-rate and interval lever arm.
4. The frozen `delta` absolute tolerance `1e-9` bits was therefore below the
   attainable floating-point floor for a correctly reassociated cache.  The
   R3 STOP remains valid as a receipt, but it does not diagnose a physical or
   branch-semantic mismatch.
5. R3 aborted before the complete `q3`, victim-token, score, and masked-argmax
   comparisons, so none of those downstream checks may be claimed as passed.

## Required R4 boundary

The reviewer required one new pre-outcome R4 contract rather than changing or
reinterpreting R3.  R4 must retain all users, legal branches, and the three
frozen contexts, and must:

- keep primitive rate/interference tolerances unchanged;
- compare `delta` against a fixed `C=64` propagated floating-point bound and a
  separate `1e-3`-bit hard ceiling;
- report the same verdict under diagnostic `C` values `1, 8, 64, 512, 4096`;
- keep the existing `q3` tolerance unchanged;
- require exact action-context values, victim-token columns 0--4, masks,
  reference actions, branch power/load maps, focal exclusion, and masked
  argmax;
- use a fixed propagated interference/asinh bound only for victim-token column
  5;
- instrument zero-coupling entries, coupling coverage, clamp activations, and
  branch-key collisions;
- evaluate all three contexts and persist all deviations even on STOP;
- serialize an undefined margin/deviation ratio as JSON `null`, never
  `Infinity`.

Observed R3 discrepancies must not be used to tune a round-number tolerance,
drop per-victim comparisons, weaken primitive or q3 checks, sample branches,
or edit either sealed implementation.

## Verdict

`GO_R4_SCALE_AWARE_EQUIVALENCE`

This verdict authorizes only the bounded R4 implementation-equivalence check.
It is not an equivalence PASS, C3 efficacy evidence, a learner gate, or episode
training authorization.
