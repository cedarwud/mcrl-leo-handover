#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 --bindings PATH --admission-supplement PATH --acceptance-bundle PATH --runtime-admission PATH --arm ARM --barrier 100|500|1500|3000 --chunks-root DIR --arm-merge-root DIR [--previous-arm-merge DIR] [--max-workers N] [--merge]" >&2
}

bindings= supplement= acceptance= runtime_admission= arm= barrier= chunks_root= arm_merge_root= previous_arm_merge= max_workers=
merge_only=0
while (($#)); do
  case "$1" in
    --bindings) bindings=$2; shift 2 ;;
    --admission-supplement) supplement=$2; shift 2 ;;
    --acceptance-bundle) acceptance=$2; shift 2 ;;
    --runtime-admission) runtime_admission=$2; shift 2 ;;
    --arm) arm=$2; shift 2 ;;
    --barrier) barrier=$2; shift 2 ;;
    --chunks-root) chunks_root=$2; shift 2 ;;
    --arm-merge-root) arm_merge_root=$2; shift 2 ;;
    --previous-arm-merge) previous_arm_merge=$2; shift 2 ;;
    --max-workers) max_workers=$2; shift 2 ;;
    --merge) merge_only=1; shift ;;
    *) usage; exit 2 ;;
  esac
done

[[ -n "$bindings" && -n "$supplement" && -n "$acceptance" && -n "$runtime_admission" && -n "$arm" && -n "$barrier" && -n "$chunks_root" && -n "$arm_merge_root" ]] || { usage; exit 2; }
[[ "$arm" =~ ^(FULL2|DROP_C1|DROP_C2|BASELINE)$ ]] || { echo "invalid arm" >&2; exit 2; }
case "$barrier" in
  100) previous=0 ;;
  500) previous=100 ;;
  1500) previous=500 ;;
  3000) previous=1500 ;;
  *) echo "barrier must be one of 100, 500, 1500, 3000" >&2; exit 2 ;;
esac

here=$(cd "$(dirname "$0")" && pwd -P)
repo=$(cd "$here/../.." && pwd -P)
python=${V023_STAGEC_PYTHON:-$repo/.venv/bin/python}
controller=$here/run_v023_c1c2_successor_stage_c_chunks.py
common_args=(--bindings "$bindings" --admission-supplement "$supplement" --acceptance-bundle "$acceptance" --runtime-admission "$runtime_admission")
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$repo/src" TMPDIR="$repo/.tmp"
"$python" "$controller" check-launch "${common_args[@]}" --arm "$arm" >/dev/null
if ((previous > 0)); then
  [[ -n "$previous_arm_merge" ]] || { echo "barrier $barrier requires --previous-arm-merge for cumulative $previous" >&2; exit 2; }
  "$python" "$controller" check-barrier "${common_args[@]}" --arm "$arm" --completed "$previous" --arm-merge-root "$previous_arm_merge" >/dev/null
fi

cumulative_roots=()
for ((start=0; start<barrier; start+=100)); do
  end=$((start + 100))
  cumulative_roots+=("$chunks_root/$(printf '%s-%06d-%06d' "$arm" "$start" "$end")")
done
if ((merge_only)); then
  for root in "${cumulative_roots[@]}"; do
    [[ -f "$root/chunk-receipt.json" ]] || { echo "missing complete chunk: $root" >&2; exit 2; }
  done
  exec "$python" "$controller" merge-arm "${common_args[@]}" --arm "$arm" --chunk-roots "${cumulative_roots[@]}" --output "$arm_merge_root"
fi

pending=()
for ((start=previous; start<barrier; start+=100)); do
  end=$((start + 100))
  root="$chunks_root/$(printf '%s-%06d-%06d' "$arm" "$start" "$end")"
  [[ -f "$root/chunk-receipt.json" ]] || pending+=("$root")
done
if ((${#pending[@]} == 0)); then
  echo "current barrier interval already complete; run with --merge"
  exit 0
fi

cores=$(getconf _NPROCESSORS_ONLN)
reserve_capacity=$((cores - 2))
((reserve_capacity >= 1)) || { echo "chunk launch requires at least three logical cores" >&2; exit 2; }
command -v flock >/dev/null || { echo "flock is required for shared capacity allocation" >&2; exit 2; }
capacity_lock=${V023_STAGEC_CAPACITY_LOCK:-/tmp/v023-stagec-capacity.lock}
exec 9>"$capacity_lock"
flock -x 9
occupied=$(pgrep -af 'run_v023_c1c2_successor_stage_c_chunks.py run-chunk' | grep -v 'pgrep -af' | wc -l || true)
available=$((reserve_capacity - occupied))
((available >= 1)) || { echo "no aggregate Stage-C capacity: cores=$cores occupied_workers=$occupied reserve=2" >&2; exit 2; }
if [[ -z "$max_workers" ]]; then max_workers=$available; fi
[[ "$max_workers" =~ ^[1-9][0-9]*$ ]] || { echo "--max-workers must be positive" >&2; exit 2; }
((max_workers <= available)) || { echo "--max-workers exceeds aggregate available capacity ($available; occupied=$occupied)" >&2; exit 2; }

mkdir -p "$chunks_root"
workers=$max_workers
if ((workers > ${#pending[@]})); then workers=${#pending[@]}; fi
session="v023-stagec-${arm,,}-barrier-${barrier}"
tmux has-session -t "$session" 2>/dev/null && { echo "tmux session already exists: $session" >&2; exit 2; }
for ((worker=0; worker<workers; worker++)); do
  commands=()
  for ((index=worker; index<${#pending[@]}; index+=workers)); do
    root=${pending[index]}
    name=$(basename "$root")
    start=$((10#${name: -13:6}))
    end=$((10#${name: -6:6}))
    printf -v command 'echo 1000 > /proc/self/oom_score_adj && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=%q TMPDIR=%q %q %q run-chunk --bindings %q --admission-supplement %q --acceptance-bundle %q --runtime-admission %q --arm %q --start %d --end %d --chunk-root %q' \
      "$repo/src" "$repo/.tmp" "$python" "$controller" "$bindings" "$supplement" "$acceptance" "$runtime_admission" "$arm" "$start" "$end" "$root"
    commands+=("$command")
  done
  joined=${commands[0]}
  for ((command_index=1; command_index<${#commands[@]}; command_index++)); do joined+=" && ${commands[command_index]}"; done
  if ((worker == 0)); then
    tmux new-session -d -s "$session" -n "worker-$worker" "$joined"
  else
    tmux new-window -t "$session" -n "worker-$worker" "$joined"
  fi
done
flock -u 9
exec 9>&-
echo "launched session=$session workers=$workers arm=$arm barrier=$barrier interval=$((previous + 1))-$barrier aggregate_occupied_before=$occupied"
