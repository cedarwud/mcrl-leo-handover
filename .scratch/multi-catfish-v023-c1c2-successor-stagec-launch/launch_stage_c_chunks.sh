#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 --bindings PATH --arm ARM --chunks-root DIR --arm-merge-root DIR [--early-baseline-admission PATH|--runtime-admission PATH] [--max-workers N] [--merge]" >&2
}

bindings=
arm=
chunks_root=
arm_merge_root=
early_admission=
runtime_admission=
max_workers=
merge_only=0
while (($#)); do
  case "$1" in
    --bindings) bindings=$2; shift 2 ;;
    --arm) arm=$2; shift 2 ;;
    --chunks-root) chunks_root=$2; shift 2 ;;
    --arm-merge-root) arm_merge_root=$2; shift 2 ;;
    --early-baseline-admission) early_admission=$2; shift 2 ;;
    --runtime-admission) runtime_admission=$2; shift 2 ;;
    --max-workers) max_workers=$2; shift 2 ;;
    --merge) merge_only=1; shift ;;
    *) usage; exit 2 ;;
  esac
done

[[ -n "$bindings" && -n "$arm" && -n "$chunks_root" && -n "$arm_merge_root" ]] || { usage; exit 2; }
[[ "$arm" =~ ^(FULL2|DROP_C1|DROP_C2|BASELINE)$ ]] || { echo "invalid arm" >&2; exit 2; }
cores=$(getconf _NPROCESSORS_ONLN)
capacity=$((cores - 2))
((capacity >= 1)) || { echo "chunk launch requires at least three logical cores" >&2; exit 2; }
if [[ -z "$max_workers" ]]; then max_workers=$capacity; fi
[[ "$max_workers" =~ ^[1-9][0-9]*$ ]] || { echo "--max-workers must be positive" >&2; exit 2; }
((max_workers <= capacity)) || { echo "--max-workers exceeds cores-2 ($capacity)" >&2; exit 2; }

here=$(cd "$(dirname "$0")" && pwd -P)
repo=$(cd "$here/../.." && pwd -P)
python=${V023_STAGEC_PYTHON:-$repo/.venv/bin/python}
controller=$here/run_v023_c1c2_successor_stage_c_chunks.py
mkdir -p "$chunks_root"

chunk_roots=()
for ((start=0; start<3000; start+=100)); do
  end=$((start + 100))
  root=$chunks_root/$(printf '%s-%06d-%06d' "$arm" "$start" "$end")
  chunk_roots+=("$root")
done

if ((merge_only)); then
  for root in "${chunk_roots[@]}"; do
    [[ -f "$root/chunk-receipt.json" ]] || { echo "missing complete chunk: $root" >&2; exit 2; }
  done
  exec "$python" "$controller" merge-arm --arm "$arm" --chunk-roots "${chunk_roots[@]}" --output "$arm_merge_root"
fi

if [[ "$arm" == BASELINE ]]; then
  [[ -n "$early_admission" && -z "$runtime_admission" ]] || { echo "BASELINE requires only --early-baseline-admission" >&2; exit 2; }
  admission_args=(--early-baseline-admission "$early_admission")
else
  [[ -n "$runtime_admission" && -z "$early_admission" ]] || { echo "learned arm requires only --runtime-admission" >&2; exit 2; }
  admission_args=(--runtime-admission "$runtime_admission")
fi

session="v023-stagec-${arm,,}-chunks"
tmux has-session -t "$session" 2>/dev/null && { echo "tmux session already exists: $session" >&2; exit 2; }

pending=()
for root in "${chunk_roots[@]}"; do
  if [[ -f "$root/chunk-receipt.json" ]]; then
    continue
  fi
  pending+=("$root")
done
if ((${#pending[@]} == 0)); then
  echo "all chunks already complete; run with --merge"
  exit 0
fi

workers=$max_workers
if ((workers > ${#pending[@]})); then workers=${#pending[@]}; fi
for ((worker=0; worker<workers; worker++)); do
  commands=()
  for ((index=worker; index<${#pending[@]}; index+=workers)); do
    root=${pending[index]}
    name=$(basename "$root")
    start=$((10#${name: -13:6}))
    end=$((10#${name: -6:6}))
    printf -v command 'echo 1000 > /proc/self/oom_score_adj && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=%q TMPDIR=%q %q %q run-chunk --bindings %q --arm %q --start %d --end %d --chunk-root %q' \
      "$repo/src" "$repo/.tmp" "$python" "$controller" "$bindings" "$arm" "$start" "$end" "$root"
    for argument in "${admission_args[@]}"; do printf -v command '%s %q' "$command" "$argument"; done
    commands+=("$command")
  done
  joined=${commands[0]}
  for ((command_index=1; command_index<${#commands[@]}; command_index++)); do
    joined+=" && ${commands[command_index]}"
  done
  if ((worker == 0)); then
    tmux new-session -d -s "$session" -n "worker-$worker" "$joined"
  else
    tmux new-window -t "$session" -n "worker-$worker" "$joined"
  fi
done
echo "launched session=$session workers=$workers arm=$arm pending_chunks=${#pending[@]}"
