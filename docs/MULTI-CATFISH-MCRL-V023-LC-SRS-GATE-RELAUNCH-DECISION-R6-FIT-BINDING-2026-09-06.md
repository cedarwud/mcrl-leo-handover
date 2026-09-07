# Multi-Catfish MCRL V0.23 LC-SRS gate relaunch decision R6

Date: 2026-09-06  
Status: **R6 PREPARED; NOT LAUNCHED**  
Boundary: **TRAIN-development Gate only; no TEST, no episode-policy training, no efficacy claim**

## 1. Verified R5 terminal state

R5 used the frozen eight TRAIN-development worlds and completed its complete
source stage before terminating in the first fit batch.  The server timestamps
were:

* launch metadata: 2026-09-06 03:13:56 UTC;
* source-stage verification: 2026-09-06 04:41:39 UTC;
* terminal `FAILED`: 2026-09-06 04:43:57 UTC.

The source-stage decision was `SOURCE_STAGE_READY_FOR_FIT`, with eight source
worlds and no learner update recorded by that receipt.  The relevant immutable
server-file hashes are:

| R5 file | SHA-256 |
|---|---|
| `source-manifest.json` | `cd95e9754f5585685416f9f857c0beb5ef178735d2b5fc1b43c93ed13c9a9e35` |
| `source-stage-verification.json` | `0eb5f8c36e2d155d5747df1454aa128f517c1daca6aa12b3d54c1e2137ca60ee` |
| `FAILED` | `601436141026ec07db9a024a158ef80a5aafa0c6ac6e495dc0dd1a0795d2f262` |
| `server-controller.log` | `ec4d4d88ded8ba1a408a4e2b7b07e9ec907c23e8ba0b97248418a423043d2847` |

R5 emitted no successful fit shard and did not start composition.

## 2. Defect diagnosis

The production source learner receives `LCSRSAnchorSurface` values and its
generic receipt therefore used each `surface.content_digest`.  The Gate-level
fit adapter and independent verifier correctly require the stronger
`LCSRSAnchorRecord.content_digest`, which also binds world, phase, anchor
identity, and detached Q1/Q2 provenance.  These are intentionally different
digest domains.  Consequently every first-batch fit completed its numerical
updates and then failed closed with:

```text
V023LearnerAdapterError: fit receipt training anchors drifted
```

This is a fit-receipt binding defect.  It is not a source-coverage failure,
simulator-physics failure, target-formula change, learner-outcome decision, or
negative C3 scientific result.

## 3. Frozen R6 correction

R6 makes one semantic correction in
`src/mcrl/runtime/ee_axis_lcsrs_c3_gate_fit.py`: after the generic source
learner returns, the Gate wrapper immutably rebinds only
`source_anchor_sha256s` to the ordered full-record identities

```text
tuple(record.content_digest for record in source.training_records)
```

The target-source digest, initialization and final network digests, losses,
optimizer configuration, update count, batch size, folds, seeds, source
formula, matched placebo, composition rule, and all scientific thresholds are
unchanged.  The strict fit adapter and independent verifier are not relaxed.

The production-path regression must demonstrate all of the following before
launch:

1. surface and full-record digests differ on a valid fold;
2. the Gate wrapper emits the ordered full-record digests;
3. every other fit-receipt field remains byte-for-value unchanged; and
4. the fit adapter and independent verifier continue to reject a wrong digest
   domain.

## 4. Relaunch and evidence policy

Although the R5 source panel passed its source-stage verifier, R6 will use a
fresh server root, a fresh preflight manifest, and fresh regeneration of all
eight source worlds.  This avoids introducing a second source-code provenance
domain into the existing one-manifest Gate merely to save one source run.
R5 remains preserved as failed-run evidence and is never overwritten.

The prepared R6 server identity is:

* root: `/home/sat/mcrl-v023-lcsrs-gate-20260906-r6`;
* tmux: `mcrl-v023-lcsrs-gate-20260906-r6`;
* result root:
  `artifacts/multi-catfish-v023-lcsrs-gate-20260906-r6/server-run`.

The stage order remains preflight, eight source worlds, source-stage gate,
48 fixed fits, 48 compositions, independent verification, and immutable
result sealing.  Any new failure stops at its boundary; it must not be
interpreted as efficacy without the final scientific verifier.

## 5. Decision

R6 is authorized for preparation and, after its manifest, focused tests,
production-path digest regression, and server-side preflight all pass, for a
fresh Ubuntu launch under the user's standing conditional execution
authorization.  Launch status and scientific status remain separate.

