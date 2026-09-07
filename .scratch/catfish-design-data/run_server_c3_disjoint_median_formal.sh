#!/usr/bin/env bash
set -uo pipefail

c3_repo_root=/home/sat/mcrl-c3-shadow-20260827-v1
c3_python_bin=/home/sat/mcrl-leo-handover/.venv/bin/python
c3_tle_root=/home/sat/mcrl-runtime/tle-frozen-20260820
c3_runner="$c3_repo_root/.scratch/catfish-design-data/run_c3_disjoint_median_shadow.py"
c3_expected_runner_sha=6b0c8177b0ec436925d5e9c1eb8533a3906cfe8980033e43be23923dfb578a55
c3_output="$c3_repo_root/.scratch/catfish-design-data/c3-disjoint-median-shadow-seeds-2026082801-2026082805-v1.json"
c3_observations="$c3_repo_root/.scratch/catfish-design-data/c3-disjoint-median-shadow-seeds-2026082801-2026082805-observations-v1.npz"
c3_receipt="$c3_repo_root/.scratch/catfish-design-data/c3-disjoint-median-shadow-seeds-2026082801-2026082805-receipt-v1.json"
c3_log="$c3_repo_root/.scratch/catfish-design-data/c3-disjoint-median-shadow-seeds-2026082801-2026082805-v1.log"
c3_exit="$c3_repo_root/.scratch/catfish-design-data/c3-disjoint-median-shadow-seeds-2026082801-2026082805-v1.exit"

cd "$c3_repo_root" || exit 98
for c3_destination in \
  "$c3_output" "$c3_observations" "$c3_receipt" "$c3_log" "$c3_exit"
do
  if [[ -e "$c3_destination" ]]; then
    echo "refusing to overwrite: $c3_destination" >&2
    exit 97
  fi
done

c3_actual_runner_sha=$(/usr/bin/sha256sum "$c3_runner" | /usr/bin/cut -d' ' -f1)
if [[ "$c3_actual_runner_sha" != "$c3_expected_runner_sha" ]]; then
  echo "runner SHA-256 mismatch" >&2
  exit 96
fi

{
  echo "runner_sha256=$c3_actual_runner_sha"
  echo "host=$(hostname)"
  echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  /usr/bin/time -v "$c3_python_bin" "$c3_runner" \
    --tle-root "$c3_tle_root" \
    --seeds 2026082801 2026082802 2026082803 2026082804 2026082805 \
    --max-steps 10 \
    --output "$c3_output" \
    --observations-output "$c3_observations" \
    --receipt-output "$c3_receipt"
  c3_status=$?
  echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "exit_status=$c3_status"
} >"$c3_log" 2>&1

printf '%s\n' "$c3_status" >"$c3_exit"
exit "$c3_status"
