# V0.23 C1/C2 neutral-source adapter

This directory contains a small, read-only binding seam for the later true
five-arm source ablation.  It is deliberately separate from the shared
runtime and authority files.

`v023_c1c2_neutral_adapters.py` accepts already materialized source objects and
returns `C1C2SourceBindingBundle`.  It re-verifies the objects, checks their
route-specific source rules, and records the source digest, source identity,
row budget, learner initialization count, learner update count, and common
binding digest.  It does not call a selector or expose a simulator,
rollout, episode, learner, or training operation.

## Route contract

| Route | Informed object | Neutral object | Required neutral construction |
| --- | --- | --- | --- |
| C1 | `C1SourceSelection` with `c1-exp-dull-rollout-lower-frontier-v1` | `C1SourceSelection` with `c1-cluster-profile-matched-randomized-predecision-v2` | `sample_c1_cluster_matched_neutral_source` |
| C2 | An authenticated C2 source with `c2-hold-or-max-lagged-sinr-rival-predecision-v1` (or an authenticated temporal batch whose rows are all admitted informed rules) | `C2SourceSelection` with `c2-equal-budget-uniform-predecision-v1` | `sample_c2_neutral_source` |

For each route the adapter requires equal informed/neutral row budgets and
equal route-local learner initialization/configuration/update budgets.  It
does not require C1 and C2 to share those learner settings: the authenticated
current values may remain Q1=10 updates and Q2=3000 updates.  C1 also compares
the selected anchor/user physical-alternative cluster profile.  C2 checks that
the neutral selection's declared `informed_budget` is exactly the informed row
count and that informed and neutral objects expose the exact same sealed
physical-opportunity universe.  Its universe digest is retained in the pair's
structural signature.  Source digests and identities must be distinct within
and across the two route pairs.  Embedded common provenance, when present,
must match the shared binding exactly.

For C1, the V2 neutral sampler preserves the original exactly-uniform anchor
draw when the informed profiles are homogeneous.  If they are heterogeneous,
it uses a frozen-seed randomized one-to-one exact-profile bipartite matching,
then samples users uniformly without replacement inside each required
alternative-count stratum.  The matcher is not uniform over all feasible
perfect matchings and consults only sealed predecision structure.  Informed
anchors remain eligible in the neutral pool, so overlap is allowed and must be
reported with the profile-preservation audit.  This is a source-construction
diagnostic, not an efficacy claim.

The common binding is TRAIN-only and includes only the shared world IDs,
source seeds, and their collection digests.  Learner initialization IDs,
configuration digest, and update count are carried separately by each route.
TEST identifiers, episode/outcome/reward metadata,
head-drop metadata, source aliasing, and provenance/config drift fail closed.
The adapter does not infer a baseline, replace source ablation with head drop,
or generate an implicit digest for a C1 artifact.

## Current live-artifact blockers

These are intentionally documented rather than bypassed:

1. The V0.23 R4 LC-SRS Gate on the Ubuntu server must finish and seal its
   source/result root before its C1/C2 source objects can be authenticated.
   The adapter must not read a partially written worker directory.
2. R3 produced source captures but failed closed at C1 materialization when
   its one-common-profile assumption met heterogeneous predecision profiles.
   R3 is historical evidence only; a fresh R4 panel/materialization must be
   sealed before using the source objects.
3. A current V0.23 C1 informed `C1SourceSelection` and its receipt digest are
   still required.  The older V0.20 repriced Q1/Q2 artifacts are historical
   source-reuse evidence and are not silently relabelled as a V0.23 arm.
4. A current V0.23 C2 informed source artifact (or a verified temporal route
   batch) and its receipt digest are still required.  The V0.14 OPS3 panel is
   not assumed to be the current H-A/LC-SRS informed source.
5. After the informed sources are sealed, the C1 cluster-matched and C2
   equal-budget neutral selections must be generated from the same source
   universe and bound with the same frozen common contract.  No neutral source
   is synthesized by this adapter.
6. A later integrator must compose these two pair attestations with the C3
   provider and explicit pre-Catfish baseline in the existing five-arm plan,
   then separately pass the learner-screen and matched physical-evaluation
   gates.  This directory authorizes none of those runs.

## Validation performed

The focused tests use only synthetic pre-decision fixtures plus the two
existing in-memory selector APIs.  No simulator, training, episode, or TEST
split was opened.

```text
.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-c1c2-neutral-adapters/test_v023_c1c2_neutral_adapters.py
12 passed
```

The module and tests also pass `py_compile` and `git diff --check` for this
directory.
