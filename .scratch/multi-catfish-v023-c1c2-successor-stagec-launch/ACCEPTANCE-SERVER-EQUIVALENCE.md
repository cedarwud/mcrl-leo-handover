# Mandatory server acceptance — Stage-C chunk equivalence

Run only on the Ubuntu server from a real git checkout whose commit contains
the complete Stage-C closure. A shadow directory without `.git` is invalid.
The checkout must pass the manifest `--check` before any acceptance episode.

The launch acceptance is formal engineering evidence and emits no scientific
result. Its comparison is sequential 200 versus 2×100 for every arm. A separate
`--episodes 100 --chunks 2 --non-formal` mode admits exactly 2×50 as a rehearsal
only; its receipt records `formal:false` and `rehearsal_chunk:50`, and neither it
nor a bundle made from rehearsal receipts is admissible launch evidence. Formal
Stage-C chunks remain 100-aligned.

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

Run every arm with the default formal 200/2×100 comparison:

```bash
for arm in FULL2 DROP_C1 DROP_C2 BASELINE; do
  "$PY" "$BUNDLE/accept_stage_c_chunk_equivalence.py" \
    --bindings "$BINDINGS" --admission-supplement "$SUPPLEMENT" \
    --runtime-admission "$RUNTIME" --arm "$arm" \
    --output "$ACCEPT_ROOT/$arm"
done
```

Optional: run a bounded non-formal 100/2×50 rehearsal under a separate root.
This output is diagnostic only and the launch verifier refuses it:

```bash
"$PY" "$BUNDLE/accept_stage_c_chunk_equivalence.py" \
  --bindings "$BINDINGS" --admission-supplement "$SUPPLEMENT" \
  --runtime-admission "$RUNTIME" --arm FULL2 \
  --episodes 100 --chunks 2 --non-formal \
  --output "$ACCEPT_ROOT-REHEARSAL/FULL2"
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

After all four formal receipts pass, seal the aggregate engineering-evidence
bundle:

```bash
"$PY" "$BUNDLE/build_stage_c_chunk_acceptance_bundle.py" \
  --bindings "$BINDINGS" \
  --receipts "$ACCEPT_ROOT/FULL2/ACCEPTANCE.json" \
             "$ACCEPT_ROOT/DROP_C1/ACCEPTANCE.json" \
             "$ACCEPT_ROOT/DROP_C2/ACCEPTANCE.json" \
             "$ACCEPT_ROOT/BASELINE/ACCEPTANCE.json" \
  --output "$BUNDLE/STAGEC-CHUNK-ACCEPTANCE-BUNDLE.json"
```

Formal launch authenticates that bundle and each named formal receipt. Missing,
reordered, non-PASS, rehearsal/non-formal, code-drifted, or procedure-drifted
evidence fails closed.
