#!/usr/bin/env bash
set -euo pipefail

repo_root=${1:?repo root is required}
output_root=${2:?output root is required}
worker_count=${3:-10}
python_bin=${PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}
tle_root=${TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}
controlled_module=${MCRL_V05_CONTROLLED_TAPE_MODULE:-/tmp/mcrl-ee-axis-v05-c2-controlled-tape-20260901.py}

case ${worker_count} in
  ''|*[!0-9]*) echo "worker_count must be a positive integer" >&2; exit 2 ;;
esac
if (( worker_count < 1 )); then
  echo "worker_count must be positive" >&2
  exit 2
fi

cd "${repo_root}"
prepare_file="${output_root}/prepare.json"
shard_dir="${output_root}/shards"
log_dir="${output_root}/logs"
mkdir -p "${shard_dir}" "${log_dir}"
test -f "${prepare_file}"

run_one() {
  local policy=$1
  local seed=$2
  local anchor_index=$3
  local prefix
  local output_file
  local log_file
  local -a seed_args=()

  : "${prepare_file:?prepare_file was not exported to the shard worker}"
  : "${shard_dir:?shard_dir was not exported to the shard worker}"
  : "${log_dir:?log_dir was not exported to the shard worker}"

  if [[ ${policy} == main ]]; then
    prefix=main
  else
    prefix="q13-${seed}"
    seed_args=(--initialization-seed "${seed}")
  fi
  output_file="${shard_dir}/${prefix}-anchor-$(printf '%02d' "${anchor_index}").json"
  log_file="${log_dir}/${prefix}-anchor-$(printf '%02d' "${anchor_index}").log"
  if [[ -e ${output_file} ]]; then
    echo "refusing to overwrite ${output_file}" >&2
    return 3
  fi
  env \
    MCRL_V05_CONTROLLED_TAPE_MODULE="${controlled_module}" \
    PYTHONUNBUFFERED=1 \
    "${python_bin}" \
    .scratch/c3-v04/run_v05_c2_controlled_source.py shard \
    --tle-root "${tle_root}" \
    --prepare-file "${prepare_file}" \
    --anchor-index "${anchor_index}" \
    --tape-policy "${policy}" \
    "${seed_args[@]}" \
    --output-file "${output_file}" \
    >"${log_file}" 2>&1
}

export -f run_one
export repo_root output_root python_bin tle_root controlled_module
export prepare_file shard_dir log_dir

job_file=$(mktemp)
trap 'rm -f "${job_file}"' EXIT
for anchor_index in $(seq 0 11); do
  printf 'main none %s\n' "${anchor_index}" >>"${job_file}"
done
for seed in 2026092101 2026092102 2026092103; do
  for anchor_index in $(seq 0 11); do
    printf 'q13 %s %s\n' "${seed}" "${anchor_index}" >>"${job_file}"
  done
done

xargs -P "${worker_count}" -n 3 bash -c 'run_one "$1" "$2" "$3"' _ <"${job_file}"

actual=$(find "${shard_dir}" -maxdepth 1 -type f -name '*.json' | wc -l)
if [[ ${actual} -ne 48 ]]; then
  echo "expected 48 shard files, found ${actual}" >&2
  exit 4
fi
printf 'CONTROLLED_SOURCE_SHARDS_COMPLETE count=%s workers=%s\n' "${actual}" "${worker_count}"
