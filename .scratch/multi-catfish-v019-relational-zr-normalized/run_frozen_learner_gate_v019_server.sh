#!/usr/bin/env bash
set -uo pipefail

v019_checkout=/home/sat/mcrl-v019-relational-q3-gate-20260904-r1
v019_python=/home/sat/mcrl-leo-handover/.venv/bin/python
v019_worker="$v019_checkout/.scratch/multi-catfish-v019-relational-zr-normalized"
v019_contract="$v019_worker/contracts/MULTI-CATFISH-MCRL-V019-RELATIONAL-Q3-LEARNER-PREREG-FROZEN-2026-09-04.md"
v019_code_manifest="$v019_worker/contracts/CODE-MANIFEST-FROZEN-2026-09-04.sha256"
v019_panel="$v019_checkout/learned-q3-panel-v019-r1"
v019_plan="$v019_checkout/frozen-panel-plan-v019-r1.json"
v019_source_complete="$v019_panel/source-panel.complete"
v019_config="$v019_panel/learner-run-config.json"
v019_learner_output="$v019_panel/learner-output"
v019_gate_output="$v019_panel/gate-output"
v019_learner_log="$v019_panel/learner.log"
v019_gate_log="$v019_panel/gate.log"
v019_complete="$v019_panel/learner-gate.complete"
v019_prelearner_verification="$v019_panel/panel-prelearner-verification.json"

cd "$v019_checkout" || exit 70
test -f "$v019_source_complete" || exit 71
grep -qx 'exit_code=0' "$v019_source_complete" || exit 72
grep -qx 'receipt_count=21' "$v019_source_complete" || exit 73
grep -qx 'metadata_count=21' "$v019_source_complete" || exit 74
test ! -e "$v019_learner_output" || exit 75
test ! -e "$v019_gate_output" || exit 76
test ! -e "$v019_complete" || exit 77
test ! -e "$v019_prelearner_verification" || exit 78
sha256sum -c --quiet "$v019_code_manifest" || exit 79
"$v019_python" "$v019_worker/learner/verify_frozen_panel_closure_v019.py" \
    --plan "$v019_plan" \
    --panel-root "$v019_panel" \
    > "$v019_prelearner_verification" || exit 80

v019_status=0
PYTHONUNBUFFERED=1 "$v019_python" "$v019_worker/learner/relational_learner_runner_v019.py" \
    --contract "$v019_contract" \
    --config "$v019_config" \
    --output "$v019_learner_output" \
    > "$v019_learner_log" 2>&1 || v019_status=$?
if [ "$v019_status" -eq 0 ]; then
    PYTHONUNBUFFERED=1 "$v019_python" "$v019_worker/gate/relational_gate_orchestrator_v019.py" \
        --contract "$v019_contract" \
        --code-manifest "$v019_code_manifest" \
        --learner-config "$v019_config" \
        --learner-output "$v019_learner_output" \
        --output "$v019_gate_output" \
        > "$v019_gate_log" 2>&1 || v019_status=$?
fi

printf "exit_code=%s\n" "$v019_status" > "$v019_complete"
exit "$v019_status"
