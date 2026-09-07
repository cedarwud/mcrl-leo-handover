#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 SSH_HOST [EPOCHS] [SHARD_ROOT] [TRAIN_SEED]" >&2
}

if (( $# < 1 || $# > 4 )); then
  usage
  exit 64
fi

remote_host=$1
epochs=${2:-3}
shard_root=${3:-/home/sat/mcrl-v023-real-shards-rehearsal}
train_seed=${4:-2927175120652069826}
shadow_checkout=/home/sat/mcrl-v023-successor-shadow-20260907

if [[ ! "$remote_host" =~ ^[A-Za-z0-9._@:-]+$ ]]; then
  echo "refusing unsafe SSH host" >&2
  exit 64
fi
if [[ ! "$epochs" =~ ^[1-9][0-9]*$ ]]; then
  echo "epochs must be a positive integer" >&2
  exit 64
fi
if [[ "$train_seed" != 2927175120652069826 ]]; then
  echo "rehearsal train seed must be exactly 2927175120652069826" >&2
  exit 64
fi
case "$shard_root" in
  /home/sat/mcrl-v023-c1c2-targets-*|*sealed*|*SEALED*)
    echo "refusing a formal/sealed shard root: $shard_root" >&2
    exit 64
    ;;
esac

package_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$package_dir/../.." && pwd -P)
cd -- "$repo_root"

required_paths=(
  src
  .scratch/multi-catfish-v023-two-route-rehearsal
  .scratch/multi-catfish-v023-two-route-source-training-runner
  .scratch/multi-catfish-v023-c1c2-provider-factory-v3
  .scratch/multi-catfish-v023-target-batch-adapter
  .scratch/multi-catfish-v023-c1c2-successor
  .scratch/multi-catfish-v023-heterogeneous-trainer
)
for required_path in "${required_paths[@]}"; do
  if [[ ! -e "$required_path" || -L "$required_path" ]]; then
    echo "required sync input is missing or a symlink: $required_path" >&2
    exit 66
  fi
done

ssh -- "$remote_host" bash -s -- "$shadow_checkout" <<'REMOTE_PREP'
set -euo pipefail
checkout=$1
if [[ -L "$checkout" ]]; then
  echo "refusing symlink shadow checkout" >&2
  exit 73
fi
mkdir -p -- "$checkout"
REMOTE_PREP

rsync -aR \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  -- \
  src/ \
  .scratch/multi-catfish-v023-two-route-rehearsal/ \
  .scratch/multi-catfish-v023-two-route-source-training-runner/ \
  .scratch/multi-catfish-v023-c1c2-provider-factory-v3/ \
  .scratch/multi-catfish-v023-target-batch-adapter/ \
  .scratch/multi-catfish-v023-c1c2-successor/ \
  .scratch/multi-catfish-v023-heterogeneous-trainer/ \
  "$remote_host:$shadow_checkout/"

ssh -- "$remote_host" bash -s -- \
  "$shadow_checkout" "$epochs" "$shard_root" "$train_seed" <<'REMOTE_RUN'
set -euo pipefail
checkout=$1
epochs=$2
shard_root=$3
train_seed=$4
python=/home/sat/mcrl-leo-handover/.venv/bin/python

if [[ "$train_seed" != 2927175120652069826 ]]; then
  echo "rehearsal train seed must be exactly 2927175120652069826" >&2
  exit 64
fi
case "$shard_root" in
  /home/sat/mcrl-v023-c1c2-targets-*|*sealed*|*SEALED*)
    echo "refusing a formal/sealed shard root: $shard_root" >&2
    exit 64
    ;;
esac
if [[ ! -d "$shard_root/informed" || ! -d "$shard_root/neutral" ]]; then
  echo "rehearsal shard root lacks informed/neutral directories" >&2
  exit 66
fi
if [[ ! -x "$python" ]]; then
  echo "server Python is unavailable: $python" >&2
  exit 66
fi

utc_timestamp=$(date -u +%Y%m%dT%H%M%SZ)
output_root="/home/sat/mcrl-v023-two-route-REHEARSAL-NONFORMAL-$utc_timestamp"
case "$output_root" in
  /home/sat/mcrl-v023-c1c2-targets-*|*sealed*|*SEALED*)
    echo "internal protected-root guard fired" >&2
    exit 70
    ;;
esac
if [[ -e "$output_root" || -L "$output_root" ]]; then
  echo "refusing pre-existing output root: $output_root" >&2
  exit 73
fi

cd -- "$checkout"
export PYTHONPATH="$checkout/src"
export OMP_NUM_THREADS=2
(
  printf '%s\n' 1000 > /proc/self/oom_score_adj
  exec "$python" \
    .scratch/multi-catfish-v023-two-route-rehearsal/rehearsal_two_route_training_real_shards.py \
    --shard-root "$shard_root" \
    --output-root "$output_root" \
    --model-config .scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json \
    --epochs "$epochs" \
    --train-seed "$train_seed"
)
echo "REHEARSAL_OUTPUT_ROOT=$output_root"
REMOTE_RUN
