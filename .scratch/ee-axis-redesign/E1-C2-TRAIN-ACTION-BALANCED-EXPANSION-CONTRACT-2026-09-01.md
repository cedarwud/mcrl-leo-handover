# E1 C2 TRAIN action-balanced source redesign contract

Status: implemented and unit-tested; no formal prepare, generation, validation,
EE, or test outcome was executed in this implementation turn.

## Why this is a source redesign

The sealed v1 supplement exhausted the single fixed pool
`2026092201..2026092220`. It restored all five originally unsupported C2
validation contrasts, but failed only the preregistered redundancy gate:
actions 4 and 14 had two clusters from two seeds, while the gate remains three
clusters from at least two seeds. That failed prepare is not a GO authority and
cannot be consumed by validation V3.

The redesign changes only the source schedule selector. It does not lower the
three-cluster/two-seed gate, add a replacement pool, increase focal users per
world anchor, inspect validation rows, or use an outcome/target to select a
schedule.

## Sealed inputs

The formal runner requires exact operator-supplied hashes and independently
authenticates every corresponding JSON document and seal:

| Input | Required SHA-256 |
|---|---|
| exhausted v1 authority | `feaddcc8b5ada02cc09f8bedf56cb7f0823bf422031f9235a371c89c39140ffa` |
| exhausted v1 authority seal | `ea4f12b9efb6bcc361c9d3fa15a5116b8d72ac398aee6cdaa5659f0e3f4c3131` |
| exhausted v1 prepare result | `ffc9a2cb9b89413f9f4be70991f2b3aa978a9476251e8b0e30718f5d7392e87d` |
| exhausted v1 prepare-result seal | `055cf6be00221c355e2a03f70f36ca1b0b8822618ee5ee8983cd15c32072cdcd` |
| legal target-free cap-50 topology probe | `265dec78460ac22b81159cf9dba968319ac2774642599c8d6eb5cc8a62643044` |

The failed receipt is admitted only when all 20 fixed seeds were inspected,
no generation attempt/result/temporal dataset exists, all original contrasts
are connected, every needed action has at least two seeds, and at least one
needed action still fails the unchanged three-cluster gate. The receipt is then
cross-bound to the live base source publication, independent verifier, census,
source prereg/manifest, Main checkpoint, environment/reward source hashes, and
source control-file manifest.

The legal probe must cover the same fixed pool with focal cap 5, discovery cap
50, and no outcomes. Its sealed evidence was:

| action | clusters | seeds |
|---:|---:|---:|
| 0 | 120 | 20 |
| 4 | 17 | 10 |
| 7 | 307 | 20 |
| 9 | 23 | 13 |
| 14 | 82 | 20 |
| 18 | 41 | 17 |

It reported 518 candidate clusters, 4–6 world anchors per seed, no discovery
errors, and no materialized outcomes. The probe is design evidence only; the
formal prepare independently re-discovers and seals its own topology.

## Selector and stopping rule

The v2 authority is written and sealed before the first formal
`_discover_c2_schedule` call. It fixes:

- candidate seed order: exactly `2026092201..2026092220`;
- partition/route: TRAIN/C2 only;
- per-seed candidate discovery ceiling: 50 clusters;
- focal cap: at most 5 clusters per world anchor;
- per action/seed selector: deterministic first 2 available clusters in
  `(anchor_step, focal_user, cluster_sha256)` order;
- per-seed published minimum: at least 12 unique clusters from at least 3 world
  anchors;
- aggregate gate: each originally needed action has at least 3 clusters from at
  least 2 seeds, and every original unsupported contrast is graph-connected;
- selection: shortest passing prefix of the same fixed pool;
- second/replacement pool: forbidden.

For each seed, the full candidate schedule is sealed before its topology is
used by the selector. The reduced schedule is then sealed separately. Missing
or insufficient seeds stop the strict prefix; they are never skipped.

## Prepare output contract

`prepare-result.json` and its seal always bind the v2 authority and include:

- schema/status and `authority_sha256`;
- base source, independent verifier, census result and seal digests;
- all four exhausted-expansion hashes and the legal-probe hash;
- fixed candidate and selected seed orders;
- full-candidate and published schedule file digests;
- per-seed discovery and action-balanced selection receipts;
- final C2 graph report;
- empty temporal dataset maps;
- `generation_attempted=false`, `replacement_seed_pool_used=false`,
  `second_seed_pool_used=false`;
- `validation_dataset_bytes_opened=false`, `test_split_opened=false`, and
  `held_out_ee_evaluated=false`.

Only `READY_FOR_ONE_TIME_GENERATION` authorizes generate. Any other status is
terminal `INSUFFICIENT_COVERAGE` for this fixed design.

## Generate output contract

Generate reauthenticates every dependency and code/helper hash, reloads every
selected schedule, and reloads the sealed Main checkpoint. It creates a
write-once generation-attempt marker before materialization. The only outcome
materializer is the existing `_generate_c2_for_seed`; the only publisher is
the existing `write_temporal_dataset`.

The final consumer-facing result keeps
`multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-result-v1`. A pass requires
all selected datasets plus a graph report that still meets the unchanged gate.
The result and seal contain:

- schema/status/completion status and authority SHA;
- base/independent/census/failed-expansion/legal-probe closure;
- selected schedule file digests;
- temporal paths, file hashes, and dataset hashes;
- final completed-row C2 graph report;
- `source_partition="TRAIN"`, `held_out=false`;
- all validation/test/held-out flags false.

Validation V3 now accepts this final result only with the formal v2 authority,
the formal runner's current hash, exact fixed-prefix semantics, cap 50/focal 5,
and all unchanged gates. It rejects the failed v1 authority even if paired with
a forged `PASS` status. No V3 preoutcome authority may be built until formal
generation produces an authentic final pass.

## Server usage

Topology discovery and especially outcome generation should run in the Ubuntu
server checkout after syncing these files and the sealed inputs, confirming the
same Python environment, checkpoint, prereg, and frozen TLE archive. Generation
can be long-running and must not be launched in the local WSL/browser session.

Prepare (replace path placeholders only; do not change hashes):

```bash
.venv/bin/python .scratch/ee-axis-redesign/run_v03_e1_c2_train_action_balanced_expansion.py prepare \
  --source-root <base-4-3-0-source-root> \
  --independent-root <independent-verifier-root> \
  --census-root <action-graph-census-root> \
  --failed-expansion-root <exhausted-v1-expansion-root> \
  --legal-probe-receipt <legal-probe-result.json> \
  --output-dir <new-empty-formal-redesign-root> \
  --tle-root <frozen-tle-root> \
  --expected-failed-authority-sha256 feaddcc8b5ada02cc09f8bedf56cb7f0823bf422031f9235a371c89c39140ffa \
  --expected-failed-authority-seal-sha256 ea4f12b9efb6bcc361c9d3fa15a5116b8d72ac398aee6cdaa5659f0e3f4c3131 \
  --expected-failed-prepare-result-sha256 ffc9a2cb9b89413f9f4be70991f2b3aa978a9476251e8b0e30718f5d7392e87d \
  --expected-failed-prepare-result-seal-sha256 055cf6be00221c355e2a03f70f36ca1b0b8822618ee5ee8983cd15c32072cdcd \
  --expected-legal-probe-receipt-sha256 265dec78460ac22b81159cf9dba968319ac2774642599c8d6eb5cc8a62643044
```

Only after inspecting an authentic `READY_FOR_ONE_TIME_GENERATION` receipt:

```bash
.venv/bin/python .scratch/ee-axis-redesign/run_v03_e1_c2_train_action_balanced_expansion.py generate \
  --source-root <base-4-3-0-source-root> \
  --independent-root <independent-verifier-root> \
  --census-root <action-graph-census-root> \
  --failed-expansion-root <exhausted-v1-expansion-root> \
  --legal-probe-receipt <legal-probe-result.json> \
  --output-dir <same-formal-redesign-root> \
  --tle-root <same-frozen-tle-root>
```

Do not invoke validation, EE, or test consumers in either command.
