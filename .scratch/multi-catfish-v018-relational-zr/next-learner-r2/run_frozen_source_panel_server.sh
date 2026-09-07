#!/usr/bin/env bash
set -uo pipefail

v018_checkout=/home/sat/mcrl-v018-relational-learner-20260904-r1
v018_python=/home/sat/mcrl-leo-handover/.venv/bin/python
v018_worker="$v018_checkout/.scratch/multi-catfish-v018-relational-zr/next-learner-r2"
v018_panel="$v018_checkout/learned-q3-panel-r1"
v018_manifest="$v018_panel/panel-manifest.json"
v018_assignments="$v018_panel/source-assignments.tsv"
v018_logs="$v018_panel/source-logs"
v018_receipts="$v018_panel/source-receipts"
v018_complete="$v018_panel/source-panel.complete"

cd "$v018_checkout" || exit 70
test -f "$v018_manifest" || exit 71
test ! -e "$v018_complete" || exit 72
mkdir -p "$v018_logs" "$v018_receipts"

"$v018_python" -c '
import json, sys
manifest = json.load(open(sys.argv[1], "r", encoding="ascii"))
entries = manifest["adapter_configs"]
if len(entries) != 21:
    raise SystemExit("source rectangle is not 21")
for entry in entries:
    print(entry["path"], entry["config_sha256"], sep="\t")
' "$v018_manifest" > "$v018_assignments"

export V018_PYTHON_BIN="$v018_python"
export V018_ADAPTER="$v018_worker/relational_simulator_source_adapter.py"
export V018_SOURCE_LOG_DIR="$v018_logs"
export V018_SOURCE_RECEIPT_DIR="$v018_receipts"

v018_status=0
xargs -P 18 -n 2 sh -c '
    v018_config=$1
    v018_config_sha=$2
    v018_name=$(basename "$v018_config" .json)
    v018_log="$V018_SOURCE_LOG_DIR/$v018_name.log"
    v018_receipt="$V018_SOURCE_RECEIPT_DIR/$v018_name.complete"
    v018_job_status=0
    PYTHONUNBUFFERED=1 "$V018_PYTHON_BIN" "$V018_ADAPTER" \
        --config "$v018_config" \
        --config-sha256 "$v018_config_sha" \
        > "$v018_log" 2>&1 || v018_job_status=$?
    printf "exit_code=%s\nconfig=%s\nconfig_sha256=%s\n" \
        "$v018_job_status" "$v018_config" "$v018_config_sha" > "$v018_receipt"
    exit "$v018_job_status"
' _ < "$v018_assignments" || v018_status=$?

v018_receipt_count=$(find "$v018_receipts" -maxdepth 1 -type f -name '*.complete' | wc -l)
v018_metadata_count=$(find "$v018_panel/sources" -mindepth 3 -maxdepth 3 -type f -name metadata.json | wc -l)
printf "exit_code=%s\nreceipt_count=%s\nmetadata_count=%s\n" \
    "$v018_status" "$v018_receipt_count" "$v018_metadata_count" > "$v018_complete"
exit "$v018_status"
