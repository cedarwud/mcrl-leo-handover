#!/usr/bin/env bash
set -uo pipefail

c2_repo_root=/home/sat/mcrl-c2-scale-20260827-v1
c2_python_bin=/home/sat/mcrl-leo-handover/.venv/bin/python
c2_tle_root=/home/sat/mcrl-runtime/tle-frozen-20260820
c2_runner="$c2_repo_root/.scratch/catfish-design-data/run_c2_time_only_identity_scale.py"
c2_expected_runner_sha=815a39e74a2e83fae1484fe9f68279120e9ee2d3ea0750f45cde51443a656a34
c2_output="$c2_repo_root/.scratch/catfish-design-data/c2-time-only-identity-scale-seeds-2026082401-2026082410-v1.json"
c2_log="$c2_repo_root/.scratch/catfish-design-data/c2-time-only-identity-scale-seeds-2026082401-2026082410-v1.log"
c2_exit="$c2_repo_root/.scratch/catfish-design-data/c2-time-only-identity-scale-seeds-2026082401-2026082410-v1.exit"

cd "$c2_repo_root" || exit 98
for c2_destination in "$c2_output" "$c2_log" "$c2_exit"
do
  if [[ -e "$c2_destination" ]]; then
    echo "refusing to overwrite: $c2_destination" >&2
    exit 97
  fi
done

c2_actual_runner_sha=$(/usr/bin/sha256sum "$c2_runner" | /usr/bin/cut -d' ' -f1)
if [[ "$c2_actual_runner_sha" != "$c2_expected_runner_sha" ]]; then
  echo "runner SHA-256 mismatch" >&2
  exit 96
fi

{
  echo "runner_sha256=$c2_actual_runner_sha"
  echo "host=$(hostname)"
  echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  /usr/bin/time -v "$c2_python_bin" "$c2_runner" \
    --tle-root "$c2_tle_root" \
    --seeds 2026082401 2026082402 2026082403 2026082404 2026082405 \
      2026082406 2026082407 2026082408 2026082409 2026082410 \
    --max-steps 10 \
    --output "$c2_output"
  c2_status=$?
  echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "exit_status=$c2_status"
} >"$c2_log" 2>&1

printf '%s\n' "$c2_status" >"$c2_exit"
exit "$c2_status"
