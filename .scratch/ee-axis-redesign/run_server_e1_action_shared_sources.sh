#!/usr/bin/env bash
set -euo pipefail

repo=/home/sat/mcrl-leo-handover-e1-action-shared-20260901
python=/home/sat/mcrl-leo-handover/.venv/bin/python
runner=.scratch/ee-axis-redesign/run_v03_e1_action_shared_sources.py
output=artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901
log_dir=.scratch/ee-axis-redesign/e1-action-shared-server-logs-20260901

cd "$repo"
mkdir -p "$log_dir"

printf '%s\n' prepare > "$log_dir/stage.txt"
/usr/bin/time -p -o "$log_dir/prepare.time" \
  env PYTHONDONTWRITEBYTECODE=1 "$python" "$runner" prepare \
  --output-dir "$output" \
  > "$log_dir/prepare.stdout" 2> "$log_dir/prepare.stderr"

printf '%s\n' generate > "$log_dir/stage.txt"
/usr/bin/time -p -o "$log_dir/generate.time" \
  env PYTHONDONTWRITEBYTECODE=1 "$python" "$runner" generate \
  --output-dir "$output" \
  > "$log_dir/generate.stdout" 2> "$log_dir/generate.stderr"

printf '%s\n' verify > "$log_dir/stage.txt"
/usr/bin/time -p -o "$log_dir/verify.time" \
  env PYTHONDONTWRITEBYTECODE=1 "$python" "$runner" verify \
  --output-dir "$output" \
  > "$log_dir/verify.stdout" 2> "$log_dir/verify.stderr"

printf '%s\n' independent-verify > "$log_dir/stage.txt"
/usr/bin/time -p -o "$log_dir/independent-verify.time" \
  env PYTHONDONTWRITEBYTECODE=1 "$python" \
  .scratch/ee-axis-redesign/verify_v03_e1_action_shared_sources.py \
  --source-root "$output" \
  --output-dir artifacts/multi-catfish-v03-e1-action-shared-source-verification-20260901 \
  --expected-preoutcome-authority-sha256 \
  873515d81d916cdc0bdd7af51a5e8feeeed7b336c82e730f96ad62115e4d54c4 \
  > "$log_dir/independent-verify.stdout" \
  2> "$log_dir/independent-verify.stderr"

sha256sum \
  "$output/action-shared-supplement-receipt.json" \
  "$output/action-shared-supplement-receipt-seal.json" \
  > "$log_dir/final.sha256"
printf '%s\n' complete > "$log_dir/stage.txt"
