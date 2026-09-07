#!/usr/bin/env bash
set -Eeuo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

repo=/home/sat/mcrl-v023-lcsrs-gate-20260906-r6
run_root=$repo/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r6/server-run
fit=$run_root/fit/world-2026121712/seed-2026135102/informed.json
output=$repo/composition-diagnostic-detail-world1712-seed5102-informed/result.json
log=$repo/composition-diagnostic-detail-world1712-seed5102-informed/trace.log
server=$repo/.scratch/multi-catfish-v023-r6-fit-binding-fix/run_v023_lcsrs_composition_server.py
trace=$repo/.scratch/multi-catfish-v023-r6-composition-diagnostic/trace_composition_failure.py
runtime=$repo/.scratch/multi-catfish-v023-r6-fit-binding-fix/v023_lcsrs_composition_runtime_diagnostic.py
python=/home/sat/mcrl-leo-handover/.venv/bin/python

mkdir -p "$(dirname "$output")"
if [[ -e "$output" || -L "$output" ]]; then
  printf 'diagnostic output already exists: %s\n' "$output" >&2
  exit 3
fi

fit_sha=$(sha256sum "$fit" | awk '{print $1}')
read -r model_bytes model_logical < <(
  "$python" -c 'import json,sys; p=json.load(open(sys.argv[1], encoding="ascii")); print(p["model_sha256"], p["network_sha256"])' "$fit"
)
preflight_sha=$(sha256sum "$repo/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json" | awk '{print $1}')
source_sha=$(
  "$python" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="ascii"))["source_manifest_sha256"])' "$run_root/source-manifest.json"
)

exec "$python" "$trace" \
  --server-module "$server" \
  --held-out-world 2026121712 \
  --student-seed 2026135102 \
  --arm INFORMED \
  --source-directory "$run_root" \
  --source-manifest "$run_root/source-manifest.json" \
  --preflight-sha256 "$preflight_sha" \
  --source-manifest-sha256 "$source_sha" \
  --fit-receipt "$fit" \
  --fit-receipt-sha256 "$fit_sha" \
  --model-bytes-sha256 "$model_bytes" \
  --model-sha256 "$model_logical" \
  --contract-sha256 1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a \
  --output "$output" \
  --device cpu \
  --runtime-module "$runtime" \
  --runtime-factory build_runtime >"$log" 2>&1
