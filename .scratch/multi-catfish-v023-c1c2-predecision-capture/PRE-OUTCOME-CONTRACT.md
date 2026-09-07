# V0.23 C1/C2 pre-outcome capture contract

Status: **pre-outcome source capture only**.  This contract authorizes a
bounded TRAIN simulator source traversal for worlds `2026121705` through
`2026121712`.  It does not authorize a learner, evaluation, TEST, an episode
policy, a target, or an efficacy claim.

This file is the additive **R4** revision of the source-stage contract.  R3 is
preserved as a failed-closed attempt and is not reused as a server output root.

## Frozen execution boundary

The companion `CODE-MANIFEST.json` is the byte-addressed manifest for this
contract.  `preflight_v023_c1c2_predecision.py` verifies that manifest and
reruns the original V0.23 observability preflight before any world is opened.
The original manifest, its digest file, the frozen preregistration, the
source adapter, the neutral adapter, the V2 materializer, and the required
tests are all explicit manifest bindings.  The external TLE root is not copied
into the repository; its identity is the original V0.23 TLE file-set digest,
root argument `--tle-root`, and frozen root default recorded in the manifest.

The fixed panel is:

| item | frozen value |
| --- | --- |
| split | `TRAIN` |
| worlds | `2026121705` … `2026121712` (exactly eight) |
| source concurrency | `4` workers, compute-only; no semantic seed or ordering change |
| C1 panel neutral seed | `3733296141` |
| C1 derivation domain | `mcrl-v023-c1c2-neutral-seed-v1|route=C1|panel=v023-train-panel-2026121705-2026121712-predecision` |
| C2 panel neutral seed | `3936591716` |
| C2 derivation domain | `mcrl-v023-c1c2-neutral-seed-v1|route=C2|panel=v023-train-panel-2026121705-2026121712-predecision` |

The two domain strings are provenance labels for the frozen externally
supplied panel seeds.  They are recorded in the contract, manifest, and final
receipt; they are not recomputed from a result and are never selected after a
capture is observed.

## R4 C1 heterogeneous-profile control

R3 completed the eight per-world source captures and panel capture, then failed
closed at panel-level C1 materialization.  The failure was exposed by
source-only predecision structure: the informed C1 anchors did not all have
one common tuple of legal physical-alternative counts across focal users.
The diagnosis used only the already authorized source-stage records (including
the C1 dull-frontier score field) and was made before opening any candidate
target, downstream outcome, reward, or efficacy EE result.  R3's captures
remain historical failure receipts; they are not relabelled or used as an
efficacy observation.

The former one-common-profile requirement is replaced for R4 by the frozen
source rule:

`c1-cluster-profile-matched-randomized-predecision-v2`

The C1 neutral arm is constructed from the sealed predecision opportunity
universe as follows:

1. Preserve the original exactly-uniform anchor-subset draw when all informed
   anchors share one profile.
2. When profiles are heterogeneous, derive each informed anchor's feasible
   neutral-anchor set from predecision profile counts only, then use the frozen
   panel seed to randomize a complete one-to-one bipartite matching.  The
   matching uses augmenting paths, so it fails closed when no complete
   assignment exists rather than silently falling back to a greedy partial
   assignment.
3. Within each matched anchor and required alternative-count stratum, sample
   focal users uniformly without replacement and emit all legal physical
   alternatives for each selected user.

The seeded matcher is a randomized feasible matching procedure; it is **not**
claimed to be uniform over all feasible perfect matchings.  Its inputs are
limited to sealed predecision identities, masks, slot tables, and legal
physical-opportunity counts.  Frontier rank, target, rate, power, reward,
outcome, downstream trace, and EE values are forbidden inputs.  Informed
anchors remain eligible in the neutral candidate pool; overlap is permitted
and the final receipt must report the selected-anchor overlap
`|A_informed ∩ A_neutral| / |A_informed|` together with the exact profile
preservation check.  This overlap is a source-design diagnostic, not an
efficacy result.

## Native Q1+Q2 reference anchor

At each native ten-slot TRAIN anchor, the bridge calls the authenticated V0.23
source adapter seam `_native_q12_anchor`.  That seam:

1. encodes the native current state and verifies its state and observation
   provenance;
2. evaluates the frozen Q1 and Q2 networks in inference mode on their native
   state surfaces;
3. forms the exact float32 `Q1 + Q2` surface and applies the native action mask;
4. chooses the lowest native action index on a tie (the adapter's masked
   `argmax`); and
5. returns the detached reference action, current slot/mask data, and source
   digests used by the C1/C2 records.

The bridge never substitutes a legacy Q1/Q2 array, a target, a post-action
observation, or a newly sampled action.  The Q1/Q2 parameter digests are also
checked before and after the ten-slot traversal.

## C1 source record

For every current anchor `t = 0..9`, the bridge calls the existing
`capture_c1_dull_rollout_sample` seam.  This retains only the dull frontier
scores and the predecision reference context required by the C1 selector:

* system and per-user dull frontier EE scores;
* native reference actions and contemporaneous slot tables;
* source seed/step and C1 anchor digest;
* state schema/state digest and common Q1/Q2 provenance.

The bridge computes the authenticated live simulator/RNG digest immediately
before and after this C1 call.  A change fails closed.  This guard is required
because the seam internally uses `evaluate_actions`; the capture may proceed
only when that evaluation is physics-only and leaves live state and RNG bytes
unchanged.  No candidate-vs-reference target, downstream outcome trace, or
evaluation result is persisted as a C1 target.

## C2 predecision anchor

C2 is emitted only at `t = 1..9` when all of the following hold:

* the frozen native Q1+Q2 reference action is not `NO_OP`;
* its current slot table resolves to a served physical key
  `(norad_id, cell_id)`; and
* that key differs from the previous served physical association for the
  focal user, compared by the physical pair and never by flat action index.

The anchor stores the contemporaneous slot table, current nonnegative
candidate-SINR vector, current state/observation digests, reference physical
key, previous incumbent physical key, and the exact V0.23 C2 horizon and
release grammar.  Duplicate physical aliases are rejected.

The informed row is deterministic from those predecision values:

1. if the previous incumbent physical key is a legal non-reference physical
   alternative, hold it (`incumbent-hold`); otherwise
2. choose the legal non-reference physical alternative with maximum current
   candidate SINR, breaking ties by `(norad_id, cell_id, action)` ascending
   (`max-lagged-candidate-sinr-rival`).

The horizon is exactly `4` and the release grammar is exactly
`C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE`.  No candidate is executed by
this capture and no C2 outcome/rate/power/reward/episode field is accepted.

## V2 and stage order

The bridge and `materialize_v023_c1c2.py` share the V2 C2 anchor digest
function.  Exact keys, canonical ASCII JSON, lowercase SHA-256 fields,
common source/checkpoint/state provenance, and forbidden outcome/TEST fields
are validated before any write.  The panel merge repeats V2 validation on all
world files and rebuilds C1/C2 source selection once over the complete panel.

The controller has one irreversible stage order:

`inherited preflight -> eight per-world write-once captures -> one panel merge -> one V2 materialization -> hash seal -> COMPLETE marker`.

It refuses an existing output root, existing world/panel/materialization
targets, and stale output files.  A failed or partial root is not repaired or
reused; an operator must choose a new fresh server root.  The sync launcher
likewise refuses an existing remote root and a reused tmux session.

The only positive claim after a complete R4 seal is:

> TRAIN simulator source traversal completed for the frozen eight-world panel;
> C1 dull frontier EE scores and C2 predecision SINR anchors were retained,
> V2 source selections were materialized with the frozen C1 profile-matching
> rule, and the selected-anchor overlap/profile audit was recorded.  No
> learner, TEST, downstream target, evaluation, or efficacy work was performed.

This receipt is not a target and is not evidence of C1/C2 efficacy.
