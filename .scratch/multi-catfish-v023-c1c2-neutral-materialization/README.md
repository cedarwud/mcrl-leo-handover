# V0.23 C1/C2 predecision materialization seam

Status: **plumbing only — R4 requires a fresh sealed V0.23 panel**.

The prior R3 source captures are preserved as failed-closed historical
receipts.  They exposed heterogeneous C1 predecision anchor profiles at the
panel materialization boundary and are not silently reused or relabelled.

`materialize_v023_c1c2.py` is a deterministic, TRAIN-only source-stage
boundary for the later five-arm source ablation.  It accepts one canonical
ASCII JSON capture containing both C1 dull-rollout records and C2 temporal
predecision anchors from the same `pool_id`/`pool_sha256`.  It then:

1. validates the typed, outcome-blind records and their provenance;
2. runs the existing pure C1 lower-frontier selector;
3. samples the C1 cluster-profile-matched randomized neutral source with a
   frozen seed (uniform anchor draw for a homogeneous profile; exact-profile
   one-to-one matching for heterogeneous profiles);
4. authenticates the source-stage C2 informed rows against the same anchor
   universe; and
5. samples the existing C2 equal-budget neutral source with a frozen seed.

The output contains `c1-informed.json`, `c1-neutral.json`,
`c2-informed.json`, `c2-neutral.json`, `receipt.json`, and a SHA-256 manifest.
Every route pair is required to have equal source-row budgets.  C1 and C2 do
not share a learner update count or initialization: those are route-specific
and belong to the later learner-screen contract.

For heterogeneous C1 profiles, the seeded matching uses only sealed
predecision identities and legal-opportunity counts.  It is not uniform over
all feasible perfect matchings; informed anchors remain eligible in the
neutral pool, overlap is allowed, and a completed receipt must report the
selected-anchor overlap and exact profile-preservation audit.

This seam never imports the simulator, evaluates a branch, reads a target or
outcome, runs an episode, updates a learner, opens TEST, or tunes a source from
an observed result.  It rejects target/rate/power/reward/outcome/episode/TEST
fields and refuses to overwrite an output directory.

## Capture contract

The source-stage bridge must provide one canonical JSON object with this
shape (all omitted details are intentionally fail-closed):

```json
{
  "schema": "multi-catfish-mcrl-v023-c1-c2-predecision-capture-v2",
  "split": "TRAIN",
  "pool_id": "world-...",
  "pool_sha256": "<sha256 of the canonical pool object>",
  "provenance": {
    "source_manifest_sha256": "<sha256>",
    "checkpoint_sha256": "<sha256>",
    "state_schema": "<current V0.3 state schema>",
    "state_schema_sha256": "<sha256>"
  },
  "c1": {
    "frontier_config": {
      "lower_anchor_fraction": 0.5,
      "lower_user_fraction": 0.5,
      "max_anchors": null,
      "max_focal_users_per_anchor": null
    },
    "neutral_seed": 123,
    "records": ["<C1DullRolloutRecord fields plus state_sha256>"]
  },
  "c2": {
    "neutral_seed": 456,
    "anchors": [
      {
        "anchor_sha256": "<authenticated anchor digest>",
        "world_id": 2026121705,
        "source_seed": 2026121705,
        "source_manifest_sha256": "<same provenance digest>",
        "checkpoint_sha256": "<same provenance digest>",
        "state_schema": "<current V0.3 state schema>",
        "state_schema_sha256": "<same provenance digest>",
        "state_sha256": "<sha256>",
        "observation_sha256": "<sha256>",
        "step_index": 1,
        "focal_user": 0,
        "reference_action": 0,
        "reference_physical_key": [1, 1],
        "incumbent_physical_key": [2, 2],
        "candidate_sinr": ["<28 finite nonnegative values>"],
        "slot_table": {
          "norad_ids": ["<28 ints>"],
          "cell_ids": ["<28 ints>"],
          "mask": ["<28 bools>"]
        },
        "legal_alternatives": ["<exact rows derived from slot_table>"],
        "horizon_steps": 4,
        "release_grammar": "<current frozen C2 policy version>"
      }
    ],
    "informed": [
      {
        "anchor_sha256": "<anchor>",
        "step_index": 0,
        "focal_user": 0,
        "reference_action": 0,
        "reference_physical_key": [1, 1],
        "candidate_action": 1,
        "candidate_physical_key": [2, 2],
        "source_rule": "incumbent-hold"
      }
    ]
  }
}
```

`pool_sha256` is computed over:

```text
{"pool_id": ..., "provenance": ..., "c1_frontier_config": ...,
 "c1_neutral_seed": ..., "c1_records": ..., "c2_neutral_seed": ...,
 "c2_anchors": ..., "c2_informed": ...}
```

using the module's canonical JSON encoder.  The C1 record objects must contain
the exact fields needed by `C1DullRolloutRecord`, plus `state_sha256`, so the
materializer can recompute the original C1 anchor identity from the state,
slot tables, reference actions, step, and source seed.  They also include
frontier scores and TRAIN/dull-rollout provenance.  C2
anchors must preserve their current slot table, candidate-SINR vector,
incumbent physical key, world/seed, state/observation digests, and common
lineage.  Their authenticated digest also binds the frozen horizon and release
grammar.  The materializer rejects physical aliases, recomputes both the action-to-physical mapping and
the literal hold-if-legal, otherwise maximum-lagged-SINR-rival rule.  A merely
legal candidate cannot be relabelled as informed C2.  This seam does not infer
a candidate from old target-bearing V0.20/V0.14 arrays.

## Current blocker and launch input

The read-only live-artifact audit at
`.scratch/multi-catfish-v023-c1c2-live-artifact-audit/AUDIT.md` proves that the
existing V0.20 C1/E1 and C2/V0.14 bytes are not this capture: they lack the
predecision slot-table/temporal opportunity fields.  Therefore no command can
be run against current artifacts without an unsupported relabeling.

The next source-stage implementation must persist the typed C1 and C2
predecision objects while the contemporaneous observation is still open, bind
them to the world/source/checkpoint digests, compute `pool_sha256`, and write a
canonical capture.  That source capture is heavy/server work; this materializer
itself is **non-heavy** once the capture exists (JSON validation and source
selection only, normally seconds to minutes depending on row count).

Example after a valid capture has been produced:

```text
python3 .scratch/multi-catfish-v023-c1c2-neutral-materialization/materialize_v023_c1c2.py \
  --capture /path/to/v023-train-predecision-capture.json \
  --output .scratch/multi-catfish-v023-c1c2-neutral-materialization/materialized-source
```

The command is source preparation only.  A successful receipt is not a
learner result and does not establish C1/C2 EE efficacy.
