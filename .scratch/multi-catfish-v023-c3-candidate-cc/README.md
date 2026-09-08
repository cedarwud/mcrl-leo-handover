# C-C exact-primary-tie fast screen

This directory contains the tape-only implementation of candidate C-C. It does
not train a learner, open TEST, make an efficacy claim, or run new physics. Its
claim ceiling is
`TRAIN_DEVELOPMENT_C3_CANDIDATE_CC_FAST_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`.

## Plainest reading

For each E1 anchor at step 0 or 1, the runner reconstructs the exact float32
Q1+Q2 maximum set for every user under the native mask. BASE is the lowest
native action in that set. The focal user is the lowest user index whose maximum
set contains at least two physically distinct actions. All other users stay at
BASE. Among the focal user's tied actions, C-C chooses the complete unilateral
profile with the lowest interval network energy; an energy tie goes to the
lowest native action index.

The selected profile's bits, joules, served count, and corrected-F0 receipt come
from that same E1 unilateral row. BASE uses the E1 reference row. Signed zeros
compare equal, while adjacent float32 values do not. Physical aliases do not
create exposure, and duplicate non-BASE aliases invalidate the input.

The merge requires all 12 units and exactly 24 anchors / 2,400 service
opportunities. It converts each canonical binary64 hex accounting scalar to its
exact rational value before summing and comparing. A valid panel emits
`C_C_FAST_SCREEN_SUPPORT` only when there is a legal physical change, pooled EE
is strictly above BASE, and service is no worse than BASE minus 0.001. Otherwise
it emits `C_C_FAST_SCREEN_NO_SUPPORT` with every applicable declared reason.
Any integrity failure emits `INVALID_RUN` when a write-once receipt can safely be
published.

The E1 schema has every required field. Both the E1 source builder and an
immutable unit tape were checked for `q1_q2_float32`, `action_masks`,
`action_physical_keys`, `reference_actions`, BASE metrics/F0, and unilateral
candidate metrics/F0. No field is missing, so no F1 re-simulation fallback is
used or needed.

## Exact seal and launch order

All commands use the server interpreter and the required one-thread runtime:

```bash
export PYTHONPATH=/home/sat/mcrl-leo-handover-e1/src
export TMPDIR=/home/sat/mcrl-leo-handover-e1/.tmp
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
CC=/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3-candidate-cc
E1=/home/sat/mcrl-v023-c3-existence-e1-20260908-r1
CONTRACT=/home/sat/mcrl-leo-handover-e1/.scratch/multi-catfish-v023-c3-existence-e1/candidates/V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md
OUT=$CC/run-output
```

1. The controller resolves the contract placeholders, reviews the final C-C
   implementation, then seals the contract itself as mode 0444 and places a
   mode-0444 `${CONTRACT}.sha256` sidecar containing
   `<sha256><two spaces><basename>`. Candidate tooling never writes the contract
   or its sidecar.
2. With source files final, build the write-once preflight. This binds the sealed
   contract path/digest, panel/runtime, candidate code, E1 runner, and tape
   extractor.

   ```bash
   "$PY" "$CC/build_cc_preflight_manifest.py" --output "$CC/CC-PREFLIGHT-MANIFEST.json"
   ```

3. Build one write-once launch authority for each exact unit invocation and a
   separate one for merge. The builder authenticates the admitted E1 terminal
   receipt and hashes all 12 E1 unit tapes. Example unit authority:

   ```bash
   UNIT=861587764845384088:2026092101
   AUTH=$CC/CC-LAUNCH-AUTHORITY-861587764845384088-2026092101.json
   "$PY" "$CC/build_cc_launch_authority.py" \
     --preflight-manifest "$CC/CC-PREFLIGHT-MANIFEST.json" \
     --contract "$CONTRACT" --from-e1-root "$E1" --output-root "$OUT" \
     --output "$AUTH" --launch-arguments -- \
     --preflight-manifest "$CC/CC-PREFLIGHT-MANIFEST.json" \
     --launch-authority "$AUTH" --from-e1-root "$E1" --output "$OUT" \
     --unit "$UNIT"
   ```

   The merge authority uses its own path and replaces the final
   `--unit "$UNIT"` with `--merge`.
4. Only after the corresponding authority exists may the exact bound unit or
   merge command be executed. Units may be run in any order; merge comes only
   after all 12 immutable unit receipts exist. Never reuse a unit authority for
   another unit or for merge, and never edit a sealed artifact.

## Verification without launch

Synthetic tests:

```bash
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q "$CC/test_run_v023_c3_candidate_cc.py"
```

The pre-seal dry run is intentionally a refusal:

```bash
PYTHONDONTWRITEBYTECODE=1 "$PY" "$CC/run_v023_c3_candidate_cc.py" --dry-run
```

Until the controller seal exists, the expected diagnostic is
`C_C_ERROR: C-C contract is not sealed read-only with matching .sha256 sidecar`
and the exit status is 2. The dry run is simulator-inert.
