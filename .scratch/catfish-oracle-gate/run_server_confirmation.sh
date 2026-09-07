#!/usr/bin/env bash
# Heavy matched evaluation for the Ubuntu server.
# Expected wall time after the measured parity pilot: about 20-30 minutes.

set -uo pipefail

repo=/home/sat/mcrl-catfish-oracle-gate-20260826
python=/home/sat/mcrl-leo-handover/.venv/bin/python
runner="$repo/.scratch/catfish-oracle-gate/run_oracle_gate.py"
spec="$repo/.scratch/catfish-oracle-gate/SPEC-v1-FROZEN-PILOT.md"
output="$repo/.scratch/catfish-oracle-gate/confirmation-seeds-10-k10-v1.json"
log="$repo/.scratch/catfish-oracle-gate/confirmation-seeds-10-k10-v1.log"
receipt="$repo/.scratch/catfish-oracle-gate/confirmation-seeds-10-k10-v1.terminal.txt"
tle_root=/home/sat/mcrl-runtime/tle-frozen-20260820
expected_runner=b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb
expected_spec=e0395bd7735649074fb4993e4a2ef4c6e42f9639b831cb8b4d88e7fef8de835b
expected_checkpoint=e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b
checkpoint="$repo/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"

for path in "$output" "$log" "$receipt"; do
    if [[ -e "$path" ]]; then
        echo "refusing to overwrite existing path: $path" >&2
        exit 64
    fi
done

actual_runner=$(sha256sum "$runner" | awk '{print $1}')
actual_spec=$(sha256sum "$spec" | awk '{print $1}')
actual_checkpoint=$(sha256sum "$checkpoint" | awk '{print $1}')
if [[ "$actual_runner" != "$expected_runner" ]]; then
    echo "runner digest mismatch" >&2
    exit 65
fi
if [[ "$actual_spec" != "$expected_spec" ]]; then
    echo "spec digest mismatch" >&2
    exit 66
fi
if [[ "$actual_checkpoint" != "$expected_checkpoint" ]]; then
    echo "checkpoint digest mismatch" >&2
    exit 67
fi

started_utc=$(date --utc --iso-8601=seconds)
full_suite_exit=99
focused_exit=99
runner_exit=99
verify_exit=99

cd "$repo" || exit 68
{
    echo "started_utc=$started_utc"
    echo "repo=$repo"
    echo "runner_sha256=$actual_runner"
    echo "spec_sha256=$actual_spec"
    echo "checkpoint_sha256=$actual_checkpoint"
    echo "python=$($python --version 2>&1)"

    "$python" -m pytest -q
    full_suite_exit=$?
    echo "full_suite_exit=$full_suite_exit"

    if [[ "$full_suite_exit" -eq 0 ]]; then
        "$python" -m pytest -q .scratch/catfish-oracle-gate/test_oracle_gate.py
        focused_exit=$?
    fi
    echo "focused_exit=$focused_exit"

    if [[ "$full_suite_exit" -eq 0 && "$focused_exit" -eq 0 ]]; then
        /usr/bin/time -v "$python" "$runner" \
            --tle-root "$tle_root" \
            --focal-users-per-step 10 \
            --seeds \
                2026082401 2026082402 2026082403 2026082404 2026082405 \
                2026082406 2026082407 2026082408 2026082409 2026082410 \
            --output "$output"
        runner_exit=$?
    fi
    echo "runner_exit=$runner_exit"

    if [[ "$runner_exit" -eq 0 ]]; then
        "$python" -c 'import json, sys; from pathlib import Path; d=json.loads(Path(sys.argv[1]).read_text()); assert d["status"] == "complete"; assert d["stage"] == "confirmation"; assert d["evaluation_seeds"] == list(range(2026082401, 2026082411)); assert d["focal_users_per_step"] == 10; assert d["baseline_preview_equals_committed_step_every_time"]; assert d["fractional_ee_identity_pass_every_time"]; assert d["exactly_one_focal_physical_action_changed_every_time"]' "$output"
        verify_exit=$?
    fi
    echo "verify_exit=$verify_exit"
} >"$log" 2>&1

finished_utc=$(date --utc --iso-8601=seconds)
terminal_exit=0
if [[ "$full_suite_exit" -ne 0 || "$focused_exit" -ne 0 || "$runner_exit" -ne 0 || "$verify_exit" -ne 0 ]]; then
    terminal_exit=1
fi

{
    echo "schema=mcrl-catfish-oracle-confirmation-terminal-v1"
    echo "started_utc=$started_utc"
    echo "finished_utc=$finished_utc"
    echo "full_suite_exit=$full_suite_exit"
    echo "focused_exit=$focused_exit"
    echo "runner_exit=$runner_exit"
    echo "verify_exit=$verify_exit"
    echo "terminal_exit=$terminal_exit"
    echo "runner_sha256=$actual_runner"
    echo "spec_sha256=$actual_spec"
    echo "checkpoint_sha256=$actual_checkpoint"
    if [[ -f "$output" ]]; then
        sha256sum "$output"
    else
        echo "output_sha256=MISSING"
    fi
} >"$receipt"

exit "$terminal_exit"
