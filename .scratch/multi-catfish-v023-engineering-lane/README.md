# V0.23 engineering lane: read-only contract and real-artifact rehearsal tools

Everything in this directory is unfrozen engineering diagnostics with claim
ceiling:

`ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`

These tools must never be cited as evidence of learner quality, physical
benefit, EE improvement, convergence, TEST performance, or efficacy. They do
not change a scientific gate or authorize a launch. This implementation task
ran no simulator and no real learner update. A future chain may execute only
the callables explicitly listed in its spec; the ready Stage-A spec includes
one scratch source epoch as requested. Input artifacts remain read-only, and
generated reports, checkpoints, and rehearsal outputs go only under an
explicitly supplied scratch root.

## Static producer/consumer contract scan

`contract_scan.py` parses Python source without importing it. A JSON spec names
each producer and consumer module, writer/reader callables, and optional
semantic bindings between differently named constants. The report includes:

- schema, status, claim-ceiling, mode, route, and unit tokens;
- producer dictionary/write keys versus consumer `[...]`, `.get(...)`, and
  referenced `*FIELDS` key sets;
- `np.savez` array names and inferred `np.asarray` dtype/shape expectations;
- configured layout/dimension/horizon constants; and
- configured numeric constants used by both sides.

Every item is labelled `MATCH`, `MISMATCH`, `CONSUMER_ONLY`, or
`PRODUCER_ONLY`, with source `file:line`. A missing concurrently written module
blocks only that pair. No source file is modified.

Run all shipped successor boundaries:

```bash
./.venv/bin/python \
  .scratch/multi-catfish-v023-engineering-lane/contract_scan.py \
  --repo . \
  --spec .scratch/multi-catfish-v023-engineering-lane/specs/v023_successor_contract_pairs.json \
  --output /tmp/v023-contract-scan
```

Use repeated `--pair NAME` options to select boundaries. Pair names are:

- `a-generator-to-target-batch-adapter`
- `b1-generator-to-controller`
- `b2-generator-to-sealer`
- `c-adapter-to-provider-factory-v3`
- `d-provider-factory-v3-to-two-route-runner`

Exit codes are 0 for a completed scan without direct mismatches, 1 when at
least one direct mismatch is found, 3 when at least one selected pair is
blocked and none mismatch, and 2 for harness/configuration failure. A complete
scan may legitimately contain one-sided items; inspect those rather than
treating exit 0 as interface approval.

The mutation-negative spec intentionally diverges every supported category:

```bash
./.venv/bin/python \
  .scratch/multi-catfish-v023-engineering-lane/contract_scan.py \
  --repo . \
  --spec .scratch/multi-catfish-v023-engineering-lane/specs/selftest_contract.json \
  --output /tmp/v023-contract-selftest
```

The unavailable pre-fix server copies are not simulated or claimed as scanned.
The fixture instead proves that the scanner detects the same classes of drift
that underlay the seven historical failures: literals/claim ceilings,
receipt/key assumptions, NPZ names, dtype/shape, feature/action layout, and
horizon/sample constants.

## Offline real-artifact dry-run

`offline_realartifact_dryrun.py` executes an ordered JSON-described callable
chain. Arguments can refer to named input artifacts, prior step results,
module constants, SHA-256 identities, and safe paths below a new scratch output
root. Modules and attributes are resolved only when their step is reached. A
missing module, callable, artifact, or prior result yields `BLOCKED`; an
exception yields `FAIL`; independent later steps still run.

Before execution, every input file is SHA-256 hashed. Directory identity is a
canonical tree digest over every relative file path, size, and SHA-256, with
the per-file identities retained in the report. The same inventory is repeated
after execution. A Python audit hook blocks attempted file writes, renames,
links, removals, metadata changes, or directory creation under input roots.
This is defense in depth, so specs must also pass every write destination via a
`{"scratch": "safe/relative/path"}` reference.

The final stdout line is exactly one of:

```text
DRYRUN_<name>_PASS
DRYRUN_<name>_FAIL
DRYRUN_<name>_BLOCKED
```

The report is `<output>/dryrun-report.json`. Exit codes are 0, 2, and 3 for
PASS, FAIL, and BLOCKED respectively.

The ready Stage-A spec authenticates/loads a sealed target through the adapter,
constructs factory-v3 providers, exercises `next_batch`, builds the two-route
runner, performs one epoch in scratch, exports and reloads the exact one-epoch
orchestrator/model/provider-sampler state, resumes it in fresh objects, and
performs the next epoch. It resolves unfinished inputs lazily:

```bash
./.venv/bin/python \
  .scratch/multi-catfish-v023-engineering-lane/offline_realartifact_dryrun.py \
  --repo . \
  --spec .scratch/multi-catfish-v023-engineering-lane/specs/successor_stage_a_chain.json \
  --artifact target_root=/absolute/path/to/sealed-target-root \
  --output /tmp/v023-stage-a-dryrun
```

The current spec expects the learner manifest at
`.scratch/multi-catfish-v023-two-route-source-training-runner/LEARNER-MANIFEST.json`.
Until that file and the real target root exist, affected steps correctly report
BLOCKED. A pre-seal staging spec can use the same mechanism to add controller
merge and sealer verification callables; the included self-test demonstrates
the full authenticate → load → merge → seal-verify sequence.

List configured real-artifact candidates without running a chain:

```bash
./.venv/bin/python \
  .scratch/multi-catfish-v023-engineering-lane/offline_realartifact_dryrun.py \
  --list-real-artifacts \
  .scratch/multi-catfish-v023-engineering-lane/specs/real_artifact_candidates.json
```

The controller may replace or extend that JSON list with server paths. Listing
only reads and hashes candidates; it does not authenticate their scientific
meaning.

## Tests

The tests are self-contained. They include a producer-owned positive contract
fixture, deliberate contract mutations in every category, a complete consumer
chain, attempted input mutation, non-fail-fast continuation, missing lazy
modules/artifacts, and real-artifact listing.

```bash
./.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-engineering-lane
```
