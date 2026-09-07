# Multi-Catfish MCRL V0.18 performance-equivalence addendum R2

Status: `FROZEN_AFTER_R4_EQUIVALENCE_AND_OPUS_MAX`

Date: 2026-09-04 (Asia/Taipei)

This addendum changes implementation cost only.  The formula, source fields,
three arms, four TRAIN worlds, three frozen lineages, ten-step horizon,
common keyed field, endpoint metrics, thresholds, stop tokens, and claim
ceiling remain exactly those frozen by
`MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md`.

## Reason for replacement execution

The original R1 closure rebuilt full-network nominal interference separately
for every focal-user/action branch in both the nominal surface and relational
encoder.  Eighteen server shards remained runnable at one CPU core each for
approximately 66 minutes 37 seconds and produced zero shard receipts.  This
was diagnosed before any R1 endpoint or partial shard result was available.

R1 is therefore eligible to be stopped only as `ABORTED_PERFORMANCE_NO_RESULT`.
Its server root and logs must be preserved.  No R1 file may enter an R2 merge,
and an R1 process may not remain alive when R2 starts.

## Semantics-preserving implementation change

For one sealed predecision anchor, the implementation now computes the
reference interference once, caches fixed physical beam-to-reference-victim
couplings, and evaluates a unilateral focal branch by applying only the
origin-beam and candidate-beam maximum-power deltas.  Non-focal users retain
the same serving links and wanted signals, so this is an algebraic refactor of
the original full-network branch reconstruction.  The focal-user rate and
victim token remain excluded exactly as in R1.

No approximate fading, reduced user set, reduced action mask, altered ZR
aggregation, altered compatibility rule, new feature, or new decision rule is
introduced.

## Pre-outcome equivalence evidence

The following evidence must be green before this status can be frozen:

1. W177 retains the original branch-by-branch implementation and checks the
   optimized nominal `delta`, `q3`, and interference-shift tokens against it.
2. W140, W141, W148, and W173--W177 all pass together.
3. On a 100-user initial predecision anchor from the already-declared first
   V0.18 TRAIN world, no action, exact teacher, learner, or TEST path is opened.
   The optimized full 2,800-action surface and encoder are timed.  At least 16
   branches spanning eight focal users are independently reconstructed by the
   retained full-network reference and all non-focal rates/interference values
   agree within `rtol=1e-12`, rate `atol=1e-9`, and interference
   `atol=1e-18`.
4. The R2 code manifest is frozen after these checks and authenticated both
   locally and on the server before a shard starts.
5. Interleaving two different predecision contexts and then repeating the
   first must reproduce every surface, observation array, and content digest
   exactly, demonstrating that the cache is anchor-local rather than global.

Observed preparation evidence before freezing: 57 focused tests passed; the
100-user optimized surface took 11.547271231 s and encoder 13.031044048 s;
16 retained-reference branches took 36.362181321 s and passed the numerical
differential.  The extrapolated legacy full-surface time of 6,363.381731176 s
is diagnostic, not an observed endpoint.  A separate legacy full-surface
attempt was interrupted after more than three minutes without completion.

## R2 execution and evidence boundary

R2 reuses the original exact world/arm/lineage matrix and is not a second
scientific sample.  It replaces R1 solely because R1 has no completed shard
receipt and the replacement was selected from runtime evidence rather than an
outcome sign.  The R2 result must carry the original contract hash, this
addendum hash, the R2 code-manifest hash, and an explicit pointer to the
preserved R1 abort receipt.

R2 remains a TRAIN-only analytic diagnostic.  It performs no learner update,
episode training, TEST access, efficacy claim, threshold relaxation, or
post-outcome selection.

## Frozen closure

The required equivalence evidence completed without opening an action, exact
teacher, learner, episode-training, or TEST path:

- R4 contract SHA-256:
  `0367b4fec0695e480b519a891e114551137afdbf4aa360b4a449f193bd7eb96c`;
- R4 result SHA-256:
  `23fcc75a3b397e75a9524532448c116788041ffa8d16baffb26b2c480252f20c`;
- R4 receipt SHA-256:
  `693db73fd9bcb76fe11e3aad444d102f1232e7ffed0491d722814101e31bfaa3`;
- R4 code-manifest SHA-256:
  `0fd88169d63ce02b87534d4f3c0a81559e17df444a2c2c8f556aac3d901382c1`;
- finalized R4 artifact-manifest SHA-256:
  `bc4223967301a5172eb1f996c347ac2794e35a32f7bc80e0bd020e924aab78c8`;
- independent-validation SHA-256:
  `8c0515b4cade750c875aa538f05ae12c92b401bf03811524cfec35e33bfd03f4`;
- R1 abort-receipt SHA-256:
  `ff9fdec11e33226a240c8820500a5a8b886478cc5c5746d8901326ae51a804c2`.

R4 returned `PASS_R2_CACHE_EQUIVALENCE` in all three frozen contexts.  The
complete branch maps, masks, focal exclusion, and selected actions were exact.
The primitive, propagated-delta, victim-token, and Q3 deviations had zero
violations under their preregistered bounds.  The full R4 preflight contained
62 passing focused tests: the prior 57-test closure plus five W178 bound tests.

The post-result Opus Max adjudication is recorded at
`.scratch/multi-catfish-v018-relational-zr/reviews/OPUS-MAX-R4-POSTRESULT-ADJUDICATION-2026-09-04.md`,
SHA-256
`6b83e897c4a503149b1029f4506da62e3703aa125bf7e5bf179fb866725a42cb`.
It found no blocker and returned `GO_V018_ANALYTIC_R2`.  Its raw session
transcript SHA-256 is
`77516794836c349eeba06509b4854adfa61d4f57fdbb65e2b316b12c058f9981`.

This freeze authorizes only creation and authentication of a distinct
analytic-R2 code manifest followed by execution of the already-preregistered
V0.18 TRAIN analytic panel.  It does not authorize reuse of the R4 equivalence
manifest or any change to the scientific matrix.
