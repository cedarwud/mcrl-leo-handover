#!/usr/bin/env bash
set -uo pipefail

v018_checkout=/home/sat/mcrl-v018-relational-learner-20260904-r1
v018_python=/home/sat/mcrl-leo-handover/.venv/bin/python
v018_worker="$v018_checkout/.scratch/multi-catfish-v018-relational-zr/next-learner-r2"
v018_contract="$v018_worker/contracts/MULTI-CATFISH-MCRL-V018-RELATIONAL-Q3-LEARNER-PREREG-FROZEN-2026-09-04.md"
v018_code_manifest="$v018_worker/contracts/CODE-MANIFEST-FROZEN-2026-09-04.sha256"
v018_panel="$v018_checkout/learned-q3-panel-r1"
v018_source_complete="$v018_panel/source-panel.complete"
v018_config="$v018_panel/learner-run-config.json"
v018_learner_output="$v018_panel/learner-output"
v018_gate_output="$v018_panel/gate-output"
v018_learner_log="$v018_panel/learner.log"
v018_gate_log="$v018_panel/gate.log"
v018_complete="$v018_panel/learner-gate.complete"

cd "$v018_checkout" || exit 70
test -f "$v018_source_complete" || exit 71
grep -qx 'exit_code=0' "$v018_source_complete" || exit 72
grep -qx 'receipt_count=21' "$v018_source_complete" || exit 73
grep -qx 'metadata_count=21' "$v018_source_complete" || exit 74
test ! -e "$v018_learner_output" || exit 75
test ! -e "$v018_gate_output" || exit 76
test ! -e "$v018_complete" || exit 77

v018_status=0
PYTHONUNBUFFERED=1 "$v018_python" "$v018_worker/relational_learner_runner.py" \
    --contract "$v018_contract" \
    --config "$v018_config" \
    --output "$v018_learner_output" \
    > "$v018_learner_log" 2>&1 || v018_status=$?
if [ "$v018_status" -eq 0 ]; then
    PYTHONUNBUFFERED=1 "$v018_python" "$v018_worker/relational_gate_orchestrator.py" \
        --contract "$v018_contract" \
        --code-manifest "$v018_code_manifest" \
        --learner-config "$v018_config" \
        --learner-output "$v018_learner_output" \
        --output "$v018_gate_output" \
        > "$v018_gate_log" 2>&1 || v018_status=$?
fi

printf "exit_code=%s\n" "$v018_status" > "$v018_complete"
exit "$v018_status"
