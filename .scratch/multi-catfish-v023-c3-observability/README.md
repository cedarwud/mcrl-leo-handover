# V0.23 LC-SRS observability gate

This directory contains the implemented execution chain; it is not a result
directory and does not itself establish efficacy.  The frozen method contract
is the repository authority:

`docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md`

The server gate has five ordered, resumable stages:

1. `source`: one all-pairs/controls physical source shard per world (8).
2. `source-manifest`: verifies all eight source shards and publishes the
   immutable hash consumed by fits.
3. `fit`: one held-out-world × student-seed × arm shard (8 × 3 × 2 = 48).
4. `composition`: 48 matched held-out full-roster composition shards.
5. `final`: independent 8/48/48 integrity, C1/C2 context, and Section-14
   adjudication.

`run_v023_lcsrs_full_gate_server.sh` is the only complete heavy launcher.  It
binds the production source, fit, composition, and final-verifier seams;
permits bounded parallelism; refuses overwrites; and creates `COMPLETE` only
after the final receipt says `PASS_FINAL_INTEGRITY`.  A C3 STOP or REDESIGN
decision is retained verbatim and is never promoted to GO.  The launcher opens
TRAIN development worlds only and performs no episode-policy training.

The explicit server-side fit seam is
`v023_lcsrs_fit_adapter.V023LearnerAdapter`, invoked by
`run_v023_lcsrs_fit_server.py`.  It reopens every source JSON/NPZ through the
typed fail-closed loader, prepares one exact leave-one-world-out fold, builds
the frozen matched placebo, invokes the production 2,000-update fit only when
the server entrypoint is deliberately run, and evaluates unchanged held-out
SUPPORTED rows itself.  Tests inject a fake fit function and perform no
optimizer update.  Model state and held-out predictions/targets are numeric
`allow_pickle=False` NPZ sidecars with atomic write-once hashes; the runner
still owns the final fit-receipt seal.  The later verifier can call
`verify_v023_fit_sidecars` to reopen the sealed JSON, model tensors, metrics,
losses, and placebo receipt independently before computing composition
predicates.

`plan`, `source-manifest`, and all receipt validators are non-heavy and do not
open the simulator, TLE, learner, or TEST.  The Python `source` and `fit`
stages accept only an explicitly injected server adapter; the safe CLI supplies
none and therefore fails closed.  This keeps the staged interface live without
turning a schema scaffold into a physical or learner result.

## Safe checks

```text
.venv/bin/python preflight_v023_lcsrs_observability.py \
  --manifest PREFLIGHT-MANIFEST.json \
  --manifest-digest PREFLIGHT-MANIFEST.sha256 \
  --repo /home/u24/papers/mcrl-leo-handover \
  --prereg /home/u24/papers/mcrl-leo-handover/artifacts/PREREG-FROZEN-2026-08-25-R2.json

.venv/bin/python run_v023_lcsrs_observability_gate.py \
  plan --output /tmp/v023-plan.json

.venv/bin/python verify_v023_lcsrs_observability_gate.py \
  /tmp/v023-plan.json --kind plan
```

The legacy local shell launcher remains plan-only.  Every shard writer refuses
overwrites and uses an fsync + atomic rename.  Ubuntu workers can therefore
resume at shard boundaries; downstream stages reopen and authenticate any
skipped receipt.

After all eight source receipts exist, publish the fit input hash with:

```text
.venv/bin/python run_v023_lcsrs_observability_gate.py source-manifest \
  --source-directory <gate-root> \
  --output <gate-root>/source-manifest.json \
  --preflight-sha256 <manifest-file-sha256>
```

The fit stage requires that manifest and never constructs the source hash at
merge time.

## Current boundary

The implementation and synthetic verifier suite cover canonical JSON/NPZ,
frozen identities and hashes, exact 8/48/48 coverage, source-manifest
completeness, C1/C2 provenance, target-free Q2 state, formula arithmetic,
common-field/source joins, held-out learner metrics, full-roster composition,
service predicates, and split/episode closure.  The preflight manifest binds
the production callback runtime and every independent verifier.

The physical source, 2,000-update fits, and composition panel have not yet been
run.  Therefore the only current claim is launch readiness after final review;
there is no C3 gate result and no efficacy claim yet.
