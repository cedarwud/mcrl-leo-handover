#!/usr/bin/env bash
set -uo pipefail

v019_checkout=/home/sat/mcrl-v019-relational-q3-gate-20260904-r1
v019_python=/home/sat/mcrl-leo-handover/.venv/bin/python
v019_worker="$v019_checkout/.scratch/multi-catfish-v019-relational-zr-normalized"
v019_panel="$v019_checkout/learned-q3-panel-v019-r1"
v019_plan="$v019_checkout/frozen-panel-plan-v019-r1.json"
v019_code_manifest="$v019_worker/contracts/CODE-MANIFEST-FROZEN-2026-09-04.sha256"
v019_manifest="$v019_panel/panel-manifest.json"
v019_assignments="$v019_panel/source-assignments.tsv"
v019_logs="$v019_panel/source-logs"
v019_receipts="$v019_panel/source-receipts"
v019_complete="$v019_panel/source-panel.complete"
v019_preharvest_verification="$v019_panel/panel-preharvest-verification.json"

cd "$v019_checkout" || exit 70
test -f "$v019_manifest" || exit 71
test ! -e "$v019_complete" || exit 72
test ! -e "$v019_preharvest_verification" || exit 75
sha256sum -c --quiet "$v019_code_manifest" || exit 76
"$v019_python" "$v019_worker/learner/verify_frozen_panel_closure_v019.py" \
    --plan "$v019_plan" \
    --panel-root "$v019_panel" \
    > "$v019_preharvest_verification" || exit 77
mkdir -p "$v019_logs" "$v019_receipts"

"$v019_python" -c '
import json, sys
manifest = json.load(open(sys.argv[1], "r", encoding="ascii"))
entries = manifest["adapter_configs"]
if len(entries) != 21:
    raise SystemExit("source rectangle is not 21")
for entry in entries:
    print(entry["path"], entry["config_sha256"], sep="\t")
' "$v019_manifest" > "$v019_assignments"

export V019_PYTHON_BIN="$v019_python"
export V019_ADAPTER="$v019_worker/learner/relational_simulator_source_adapter_v019.py"
export V019_SOURCE_LOG_DIR="$v019_logs"
export V019_SOURCE_RECEIPT_DIR="$v019_receipts"

v019_status=0
xargs -P 18 -n 2 sh -c '
    v019_config=$1
    v019_config_sha=$2
    v019_name=$(basename "$v019_config" .json)
    v019_log="$V019_SOURCE_LOG_DIR/$v019_name.log"
    v019_receipt="$V019_SOURCE_RECEIPT_DIR/$v019_name.complete"
    v019_job_status=0
    PYTHONUNBUFFERED=1 "$V019_PYTHON_BIN" "$V019_ADAPTER" \
        --config "$v019_config" \
        --config-sha256 "$v019_config_sha" \
        > "$v019_log" 2>&1 || v019_job_status=$?
    printf "exit_code=%s\nconfig=%s\nconfig_sha256=%s\n" \
        "$v019_job_status" "$v019_config" "$v019_config_sha" > "$v019_receipt"
    exit "$v019_job_status"
' _ < "$v019_assignments" || v019_status=$?

v019_receipt_count=$(find "$v019_receipts" -maxdepth 1 -type f -name '*.complete' | wc -l)
v019_metadata_count=$(find "$v019_panel/sources" -mindepth 3 -maxdepth 3 -type f -name metadata.json | wc -l)
printf "exit_code=%s\nreceipt_count=%s\nmetadata_count=%s\n" \
    "$v019_status" "$v019_receipt_count" "$v019_metadata_count" > "$v019_complete"
exit "$v019_status"
