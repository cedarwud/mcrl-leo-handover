# Mandatory server acceptance — Stage-C chunk equivalence

Run only on the Ubuntu server from a real git checkout whose commit contains
the complete Stage-C closure. A shadow directory without `.git` is invalid.
The checkout must pass the manifest `--check` before any acceptance episode.

The acceptance is explicitly non-formal and emits no scientific result. The
default comparison is sequential 200 versus 2×100. For the three learned arms,
`--episodes 100 --chunks 2 --non-formal` admits exactly 2×50 for this acceptance
only; formal Stage-C chunks remain 100-aligned. At the measured rate, each
learned-arm rehearsal costs about 25 minutes instead of 45+ minutes.

```bash
ssh sat
cd /home/sat/mcrl-v023-c1c2-successor-stagec-20260907-r1-checkout
test -d .git
git status --short --branch
git rev-parse HEAD
test -x /home/sat/mcrl-leo-handover/.venv/bin/python

export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD/src" TMPDIR="$PWD/.tmp"
echo 1000 > /proc/self/oom_score_adj
mkdir -p "$TMPDIR"

BUNDLE="$PWD/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch"
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
BINDINGS="$BUNDLE/V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json"
SUPPLEMENT="$BUNDLE/STAGE-AB-ADMISSION-SUPPLEMENT.json"
RUNTIME=/home/sat/mcrl-v023-c1c2-successor-stagec-controller-20260907-r1/stage-c-admission/stage-c-runtime-admission.json
ACCEPT_ROOT=/home/sat/mcrl-v023-successor-stagec-equivalence-20260908

"$PY" "$BUNDLE/build_v023_c1c2_successor_stagec_manifest.py" --check
test -f "$BINDINGS" -a -f "$BINDINGS.sha256"
test -f "$SUPPLEMENT" -a -f "$SUPPLEMENT.sha256"
test -f "$RUNTIME" -a -f "$RUNTIME.sha256"
test ! -e "$ACCEPT_ROOT"
```

Run BASELINE with the default 200/2×100 comparison:

```bash
"$PY" "$BUNDLE/accept_stage_c_chunk_equivalence.py" \
  --bindings "$BINDINGS" --admission-supplement "$SUPPLEMENT" \
  --runtime-admission "$RUNTIME" --arm BASELINE \
  --output "$ACCEPT_ROOT/BASELINE"
```

Run each learned arm with the bounded non-formal 100/2×50 rehearsal:

```bash
for arm in FULL2 DROP_C1 DROP_C2; do
  "$PY" "$BUNDLE/accept_stage_c_chunk_equivalence.py" \
    --bindings "$BINDINGS" --admission-supplement "$SUPPLEMENT" \
    --runtime-admission "$RUNTIME" --arm "$arm" \
    --episodes 100 --chunks 2 --non-formal \
    --output "$ACCEPT_ROOT/$arm"
done
```

The comparison is bitwise binary64 through canonical JSON. It compares episode
receipts, exact persisted boundary states, and the actual merged checkpoints,
rungs, receipts, and resume states. The only excluded provenance keys are:
`schema`, `status`, `chunk_id`, `range`, `start_boundary`, `end_boundary`,
`start_boundary_state_sha256`, `end_boundary_state_sha256`, `threads`,
`runtime`, `parent_checkpoint`, `ordered_episode_records`,
`ordered_episode_record_digest`, `started_utc`, `ended_utc`, and
`execution_mode`. The script applies this list; merely reporting it is not an
acceptance.

After all four receipts pass, seal the aggregate engineering-evidence bundle:

```bash
"$PY" "$BUNDLE/build_stage_c_chunk_acceptance_bundle.py" \
  --bindings "$BINDINGS" \
  --receipts "$ACCEPT_ROOT/FULL2/ACCEPTANCE.json" \
             "$ACCEPT_ROOT/DROP_C1/ACCEPTANCE.json" \
             "$ACCEPT_ROOT/DROP_C2/ACCEPTANCE.json" \
             "$ACCEPT_ROOT/BASELINE/ACCEPTANCE.json" \
  --output "$BUNDLE/STAGEC-CHUNK-ACCEPTANCE-BUNDLE.json"
```

Formal launch authenticates that bundle and each named receipt. Missing,
reordered, non-PASS, code-drifted, or procedure-drifted evidence fails closed.
