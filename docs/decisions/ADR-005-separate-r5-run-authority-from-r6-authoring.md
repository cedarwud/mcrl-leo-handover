# ADR-005: Separate the frozen R5 run authority from the R6 authoring authority

## Status

Accepted for the 2026-08-30 developmental 1500-episode screen.

## Date

2026-08-30

## Context

The two 1500-episode learning-rate matrices were launched from an isolated
Ubuntu checkout against the R2 experiment authorities. Each authority pins 95
files, including the R5 method and C2 documents. Later arms revalidate those
hashes before execution. Editing or synchronizing a pinned document into that
checkout during the matrix would change experiment identity even when the
scientific mechanism itself did not change.

At the same time, several author-facing statements have advanced since R5:

- the C2 V0.3A suite now passes 234 tests rather than 230;
- generic C2 runtime-contract violations abort the arm instead of becoming K0
  fallback;
- bounded B000 and F111 checkpoint/load round-trip gates pass;
- the matrix verifies the 100-episode checkpoint count, zero C2 contract
  errors, resume boundaries, and identical
  `mechanism_environment_source_sha256` across arms;
- the learning-rate selector has an executable U=100 rule; and
- the public F111 label is `Full Multi-Catfish MCRL`.

These changes must be available to figure, slide, and manuscript authors, but
they must not mutate the already launched experiment.

## Decision

Keep the R5 files named in the R2 authority immutable for the duration of the
active matrices. Publish a versioned R6 document set for authoring and review.

The two authority lines have different purposes:

| Authority | Purpose | May change during the active matrices? |
|---|---|---|
| R5 files pinned by the R2 JSON authorities | reproduce and validate the launched run | no |
| R6 document set | explain the current mechanism, executable experiment contract, and claim boundary | only through a new version |

R6 may record a time-stamped launch/running receipt, but it must not convert a
PID, checkpoint, partial arm, or matrix `running` state into a completed result.
Chapter 5 values, the selected learning rate, efficacy conclusions, and any
9000-episode authorization remain outside R6 until the corresponding complete
receipts and scientific adjudication exist.

## Alternatives considered

### Edit the R5 files in place

Rejected because the same paths and hashes are part of the active experiment
identity. A later sync could invalidate cross-arm comparability.

### Delay every documentation correction until training ends

Rejected because authors would continue copying stale test counts, authority
counts, labels, and failure semantics into figures and slides.

### Treat the R6 files as new training authority

Rejected for the active matrices. A new training authority would require a new
freeze and fresh launches; R6 is an authoring overlay until explicitly promoted
after the current matrices close.

## Consequences

- Current Ubuntu runs continue against unchanged R5 hashes.
- Figure and paper work can use R6 immediately without implying efficacy.
- Any R6-to-training promotion requires a separately generated authority and
  may not be applied retroactively to completed or running arms.
- After both 1500-episode matrices complete, a result-status revision must
  reconcile every arm receipt before Chapter 5 or learning-rate claims are
  written.
