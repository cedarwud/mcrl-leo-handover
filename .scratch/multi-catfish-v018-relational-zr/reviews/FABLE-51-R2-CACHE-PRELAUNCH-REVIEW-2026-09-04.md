# Fable 5.1 pre-launch review: V0.18 R2 cache equivalence

Date: 2026-09-04 (Asia/Taipei)

Mode: fresh-context, read-only review through `claude --model fable --effort max`.
Claude session: `85121f5d-44c5-49f4-8600-5caf5aacfb3c`.

## Scope and evidence boundary

The reviewer inspected the retained branch-by-branch R1 runtime, the cached
R2 runtime, the 100-user/every-legal-action equivalence runner, W177, and the
V0.18 dependencies.  It did not edit files, open TEST, execute an action,
train a learner, or inspect an efficacy outcome.

## Finding

The cache, multiprocessing fork/global handoff, branch dispatch, focal-user
exclusion, raw non-focal rate/interference comparisons, TRAIN-only boundary,
and masked-argmax comparison were judged structurally correct.

The sole blocking finding was that byte-exact `content_digest` equality would
create a false STOP: R1 and R2 reorder floating-point operations even when
their arrays agree within the frozen tolerances.  On nine synthetic contexts,
the reviewer observed zero byte-identical digests while victim-token maximum
absolute differences were only about `1e-22` through `1e-50`; action context,
`delta`, and `q3` were otherwise bit-exact.

## Disposition

Before any full equivalence comparison was opened, the runner and frozen
acceptance were changed so that array tolerances and exact masked argmax are
binding while `content_digest` equality is retained only as a diagnostic.
The final R3 contract also records the later receipt-only fingerprint plumbing
correction separately.  This review does not certify those later file bytes;
their identities are instead bound by the R3 contract and code manifest.

Reviewer terminal token before disposition: `STOP_R2_EQUIVALENCE`.
