# V0.23 C1/C2 materialization report

Date: 2026-09-06
Status: `PLUMBING_READY__WAITING_FOR_V023_PREDECISION_CAPTURE`

## Verified inputs and boundary

The source-only audit in
`.scratch/multi-catfish-v023-c1c2-live-artifact-audit/AUDIT.md` was read with
its loader and the current C1/C2 runtime seams.  Its conclusion is preserved:
the pinned V0.20 Q1/Q2 bytes are valid background fit inputs, but they are not
V0.23 predecision C1/C2 source objects.  E1 C1 rows lack frontier scores and
slot tables; V0.14 C2 rows lack contemporaneous temporal opportunities.  No
current materialization was therefore launched and no old row was relabelled.

The V0.20 repricing runner and Q1/Q2 source paths were inspected for lineage,
but this seam intentionally does not import or rewrite them.  Learner update
counts remain route-local (Q1=10, Q2=3000, and future C3=2000); this source
materializer does not impose a cross-route learner budget.

## What was added

`materialize_v023_c1c2.py` accepts the V2 canonical ASCII JSON capture containing:

* typed C1 `C1DullRolloutRecord` payloads;
* authenticated C2 `C2PredecisionAnchor` payloads with world/seed, lineage,
  state/observation digests, incumbent identity, candidate SINR, and the
  contemporaneous slot table;
* C2 informed rows emitted by the live predecision source grammar; and
* one `pool_id` plus recomputed `pool_sha256` covering all three collections.

It verifies TRAIN-only provenance and current state-schema digests, calls the
existing pure C1 lower-frontier selector, calls the existing C1
cluster-matched neutral sampler, validates C2 informed rows against the same
anchor universe, and calls the existing C2 equal-budget neutral sampler.  It
then writes four source selections and a manifest with immutable write-once
semantics.  Equal budgets are checked separately for C1 and C2; no assumption
is made that the two routes have equal learner update counts or initializations.

For C2 it recomputes the legal physical alternatives from the slot table and
then recomputes the exact informed choice: incumbent hold when that physical
key is legal, otherwise maximum lagged candidate-SINR non-Main rival with the
runtime tie break.  It therefore does not trust a supplied rule label or a
merely legal candidate.  The complete pool seal also binds the frontier
configuration and both neutral seeds.  C1 `NO_OP_ACTION=-1` references remain
valid when their slot table has no legal action.

The implementation rejects target/rate/power/reward/outcome/episode/TEST
fields, source aliases, head-drop metadata, malformed physical identities,
illegal candidates, duplicate opportunities, provenance drift, and pool-digest
drift.  It has no simulator, learner, training, TEST, or episode execution
path.

## Remaining launch input

The source-stage bridge must first persist, for each TRAIN world, the live
predecision C1 dull-rollout records and C2 anchor/opportunity records while
the contemporaneous observation and slot table are available.  It must seal
the capture in the schema documented in `README.md`.  That capture step is
heavy/server work and remains outside this directory.  Once supplied, this
materializer is non-heavy JSON/source selection work and can be run with:

```text
python3 .scratch/multi-catfish-v023-c1c2-neutral-materialization/materialize_v023_c1c2.py \
  --capture /path/to/v023-train-predecision-capture.json \
  --output .scratch/multi-catfish-v023-c1c2-neutral-materialization/materialized-source
```

The resulting receipt is only a source-preparation receipt; it cannot be used
as an EE efficacy claim or as a substitute for the later route-specific
learner screen and matched physical ablation.

## Checks

```text
python3 -m py_compile .scratch/multi-catfish-v023-c1c2-neutral-materialization/materialize_v023_c1c2.py
.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c1c2-neutral-materialization
```

Result after the independent provenance/rule audit: `11 passed`.
