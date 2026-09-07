# Opus Max post-result adjudication of V0.18 R4

Status: `READ_ONLY_EXTERNAL_ADJUDICATION_COMPLETE`

Date: 2026-09-04 (Asia/Taipei)

Model invocation: `claude --model opus --effort max --output-format json`

Claude session: `8d079c5a-3a33-450d-9901-ea0e2ff6a1f5`

Raw session transcript:
`OPUS-MAX-R4-POSTRESULT-SESSION-2026-09-04.jsonl`, SHA-256
`77516794836c349eeba06509b4854adfa61d4f57fdbb65e2b316b12c058f9981`.

## Evidence adjudicated

- R4 result SHA-256:
  `23fcc75a3b397e75a9524532448c116788041ffa8d16baffb26b2c480252f20c`;
- R4 receipt SHA-256:
  `693db73fd9bcb76fe11e3aad444d102f1232e7ffed0491d722814101e31bfaa3`;
- R4 contract SHA-256:
  `0367b4fec0695e480b519a891e114551137afdbf4aa360b4a449f193bd7eb96c`;
- R4 code-manifest SHA-256:
  `0fd88169d63ce02b87534d4f3c0a81559e17df444a2c2c8f556aac3d901382c1`;
- finalized artifact manifest SHA-256:
  `bc4223967301a5172eb1f996c347ac2794e35a32f7bc80e0bd020e924aab78c8`.

## Verified interpretation

Opus independently read the persisted result, receipt, contract, code
closure, independent validator, R1 abort receipt, performance addendum, and
analytic preregistration.  It concluded that all three frozen contexts pass
the complete primitive, propagated-delta, hard-ceiling, Q3, state/token,
branch-map, focal-exclusion, cache-locality, and exact masked-argmax gates.
The observed deviations lie at the floating-point reassociation floor; even
the diagnostic `C=1` propagated bound has zero violations.  Therefore the R1
versus R2 cache-equivalence blocker is closed.

`state_content_digest_equal=false` is not a hidden blocker.  Five of the six
digest inputs are bit-exact.  The only non-bit-exact input is the
preregistered bounded victim-token column 5, whose maximum deviation is a few
ULP and well inside its derived bound.  The separate R2-to-R2 interleaved
anchor test remains bit-exact and excludes persistent cache state.

The review found no blocker.  It recorded four disclosure-only observations:
one exact score tie in diagnostic context `h=2`; coupling classification is
undefined for reference-unserved victims even though their values remain
covered by the primary gates; one harmless overwritten diagnostic assignment
in the instrument; and the preparation benchmark touched only step zero of
the first preregistered TRAIN world without action, endpoint, direction, or
learner access.

## Claim ceiling and verdict

R4 is implementation-equivalence evidence from one old TRAIN world, one
lineage, one initial anchor, and three contexts.  It is not C3 efficacy,
learnability, episode-training, or TEST evidence.

The performance-equivalence addendum may be frozen.  The already
preregistered V0.18 analytic R2 may run only after it receives a distinct
analytic-R2 code manifest; the R4 equivalence manifest cannot be reused.

`GO_V018_ANALYTIC_R2`
