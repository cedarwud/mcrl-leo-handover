# Mandatory server acceptance — Stage-C chunk equivalence

This is a heavy, server-only acceptance run. Budget about 12--20 minutes for
`BASELINE`, then 1.5--2 hours wall time for the three learned arms when run in
parallel (about 4.5 core-hours total), based on the measured 13.6 seconds per
learned episode. Each arm executes 200 direct sequential episodes plus two
100-episode chunks. Do not run this on WSL2.

## Setup

```bash
ssh sat
cd /home/sat/mcrl-v023-successor-shadow-20260907
git status --short --branch
git rev-parse HEAD
test -x .venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD/src"
export TMPDIR="$PWD/.tmp"
echo 1000 > /proc/self/oom_score_adj
mkdir -p "$TMPDIR"

BUNDLE="$PWD/.scratch/multi-catfish-v023-c1c2-successor-stagec-launch"
BINDINGS="$BUNDLE/V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json"
EARLY="$BUNDLE/early_baseline_admission.json"
RUNTIME="/home/sat/mcrl-v023-successor-stagec-admission/stage-c-runtime-admission.json"
ACCEPT_ROOT="/home/sat/mcrl-v023-successor-stagec-equivalence-20260908"
test -f "$BINDINGS"
test -f "$BINDINGS.sha256"
test -f "$EARLY"
test -f "$EARLY.sha256"
test ! -e "$ACCEPT_ROOT"
```

The checkout and artifacts must first be synchronized through
`sync_launch_v023_c1c2_successor_stagec_server.sh`; do not copy individual
Python files around the manifest. The learned-arm commands additionally require
the Stage-A/B-generated `$RUNTIME` file and its sidecar.

## BASELINE first

```bash
"$PWD/.venv/bin/python" "$BUNDLE/accept_stage_c_chunk_equivalence.py" \
  --bindings "$BINDINGS" \
  --arm BASELINE \
  --early-baseline-admission "$EARLY" \
  --output "$ACCEPT_ROOT/BASELINE"
```

Require exit 0 and
`status=PASS_BITWISE_CHUNK_EQUIVALENCE` in `BASELINE/ACCEPTANCE.json` before
starting learned-arm acceptance. This acceptance reads no Stage-A export and no
Stage-B PASS receipt.

## Learned arms

```bash
test -f "$RUNTIME"
test -f "$RUNTIME.sha256"
tmux new-session -d -s v023-stagec-equivalence -n FULL2 \
  "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='$PWD/src' TMPDIR='$PWD/.tmp' '$PWD/.venv/bin/python' '$BUNDLE/accept_stage_c_chunk_equivalence.py' --bindings '$BINDINGS' --arm FULL2 --runtime-admission '$RUNTIME' --output '$ACCEPT_ROOT/FULL2'"
tmux new-window -t v023-stagec-equivalence -n DROP_C1 \
  "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='$PWD/src' TMPDIR='$PWD/.tmp' '$PWD/.venv/bin/python' '$BUNDLE/accept_stage_c_chunk_equivalence.py' --bindings '$BINDINGS' --arm DROP_C1 --runtime-admission '$RUNTIME' --output '$ACCEPT_ROOT/DROP_C1'"
tmux new-window -t v023-stagec-equivalence -n DROP_C2 \
  "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='$PWD/src' TMPDIR='$PWD/.tmp' '$PWD/.venv/bin/python' '$BUNDLE/accept_stage_c_chunk_equivalence.py' --bindings '$BINDINGS' --arm DROP_C2 --runtime-admission '$RUNTIME' --output '$ACCEPT_ROOT/DROP_C2'"
tmux attach -t v023-stagec-equivalence
```

## Final acceptance check

```bash
for arm in BASELINE FULL2 DROP_C1 DROP_C2; do
  test -f "$ACCEPT_ROOT/$arm/ACCEPTANCE.json"
  test -f "$ACCEPT_ROOT/$arm/ACCEPTANCE.json.sha256"
  (cd "$ACCEPT_ROOT/$arm" && sha256sum -c ACCEPTANCE.json.sha256)
  "$PWD/.venv/bin/python" -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["status"]=="PASS_BITWISE_CHUNK_EQUIVALENCE"; assert p["episodes"]==200; assert p["chunks"]==[[1,100],[101,200]]' "$ACCEPT_ROOT/$arm/ACCEPTANCE.json"
done
```

The script compares every episode receipt and each 100/200 cumulative pool by
canonical binary64 JSON bytes, and compares the exact persisted boundary state
at 100 and 200. The only excluded receipt fields are the explicitly listed
chunk provenance fields in each `ACCEPTANCE.json`. Until all four files pass,
formal chunk execution remains pending.
