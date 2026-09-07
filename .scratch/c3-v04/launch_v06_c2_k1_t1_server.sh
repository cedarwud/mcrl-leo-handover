#!/usr/bin/env bash
set -euo pipefail

# Frozen, pre-outcome Ubuntu launch boundary for the V0.6 C2-k1 T1 gate.
# This file is included in PREPARE_LIVE code_authority.  All outcome-bearing
# stages are single-attempt and refuse to overwrite an existing output.

readonly CHECKOUT=/home/sat/mcrl-leo-handover-v06-c2-k1-20260901
readonly PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python
readonly PYTHON_BINARY=/usr/bin/python3.13
readonly PYTHON_VERSION='Python 3.13.3'
readonly PYTHON_SHA256=b40f256663e21cd40985c79fde2328f68fb4710a1071e37b953099c188fce901
readonly RUNNER="$CHECKOUT/.scratch/c3-v04/run_v06_c2_k1_t1.py"
readonly TLE_ROOT=/home/sat/mcrl-runtime/tle-frozen-20260820
readonly SIMULATOR_PREREG="$CHECKOUT/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
readonly T1_PREREG="$CHECKOUT/docs/MULTI-CATFISH-MCRL-V06-C2-K1-T1-PREREG-2026-09-01.md"
readonly MAIN_DIR="$CHECKOUT/artifacts/training-2026-08-25-rerun01/main"
readonly GATE_DIR="$CHECKOUT/artifacts/multi-catfish-v04-c3-learnability-20260901-r2"
readonly Q13_SOURCE_DIR="$CHECKOUT/artifacts/multi-catfish-v04-c3-source-20260901-r2"
readonly V03_ROOT="$CHECKOUT/artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
readonly PREPARE_DIR="$CHECKOUT/artifacts/multi-catfish-v06-c2-k1-t1-prepare-live-final-20260902-r1"
readonly PREPARE="$PREPARE_DIR/prepare-live.json"
readonly GATE_ROOT="$CHECKOUT/artifacts/multi-catfish-v06-c2-k1-t1-source-gate-20260902-r1"
readonly SHARD_DIR="$GATE_ROOT/shards"
readonly MERGED_DIR="$GATE_ROOT/merged"
readonly LAUNCH_ROOT="$CHECKOUT/artifacts/multi-catfish-v06-c2-k1-t1-launch-20260902-r1"
readonly LOG_DIR="$LAUNCH_ROOT/logs"
readonly RECEIPT_DIR="$LAUNCH_ROOT/exit-receipts"

usage() {
  echo "usage: $0 prepare | shard {q13-a|q13-b|q13-c} | merge | verify" >&2
  exit 64
}

preflight() {
  [[ -d "$CHECKOUT" && -d "$TLE_ROOT" && -f "$RUNNER" ]]
  [[ -x "$PYTHON" && -f "$PYTHON_BINARY" ]]
  [[ "$($PYTHON --version 2>&1)" == "$PYTHON_VERSION" ]]
  [[ "$(readlink -f "$PYTHON")" == "$PYTHON_BINARY" ]]
  [[ "$(sha256sum "$PYTHON" | cut -d' ' -f1)" == "$PYTHON_SHA256" ]]
  [[ -f "$SIMULATOR_PREREG" && -f "$T1_PREREG" && -d "$MAIN_DIR" ]]
  [[ -d "$GATE_DIR" && -d "$Q13_SOURCE_DIR" && -d "$V03_ROOT" ]]
}

run_once() {
  local stage=$1
  local timeout_seconds=$2
  shift 2
  local stdout_path="$LOG_DIR/$stage.stdout.log"
  local stderr_path="$LOG_DIR/$stage.stderr.log"
  local receipt_path="$RECEIPT_DIR/$stage.json"
  local claim_path="$RECEIPT_DIR/$stage.claim"
  mkdir -p "$LOG_DIR" "$RECEIPT_DIR"
  if ! mkdir "$claim_path" 2>/dev/null; then
    echo "stage $stage already has an attempt claim" >&2
    exit 73
  fi
  if [[ -e "$receipt_path" || -e "$stdout_path" || -e "$stderr_path" ]]; then
    echo "refusing a second attempt for stage $stage" >&2
    exit 73
  fi
  set +e
  timeout --signal=TERM --kill-after=120s "$timeout_seconds" \
    "$@" >"$stdout_path" 2>"$stderr_path"
  local exit_code=$?
  set -e
  local timed_out=false
  if [[ $exit_code -eq 124 ]]; then
    timed_out=true
  fi
  printf '{"attempt":1,"exit_code":%d,"replacement":false,"retry":false,"stage":"%s","timed_out":%s}\n' \
    "$exit_code" "$stage" "$timed_out" >"$receipt_path"
  return "$exit_code"
}

require_success() {
  local stage=$1
  local receipt_path="$RECEIPT_DIR/$stage.json"
  local expected
  expected=$(printf '{"attempt":1,"exit_code":0,"replacement":false,"retry":false,"stage":"%s","timed_out":false}' "$stage")
  [[ -f "$receipt_path" && "$(<"$receipt_path")" == "$expected" ]] || {
    echo "required successful receipt is missing or invalid: $stage" >&2
    exit 66
  }
}

preflight
[[ $# -ge 1 ]] || usage
case "$1" in
  prepare)
    [[ $# -eq 1 ]] || usage
    [[ ! -e "$PREPARE_DIR" ]] || { echo "prepare output already exists" >&2; exit 73; }
    run_once prepare 3600 env -C "$CHECKOUT" PYTHONPATH=src "$PYTHON" "$RUNNER" prepare-live \
      --tle-root "$TLE_ROOT" \
      --simulator-prereg "$SIMULATOR_PREREG" \
      --t1-prereg "$T1_PREREG" \
      --main-dir "$MAIN_DIR" \
      --gate-dir "$GATE_DIR" \
      --q13-source-dir "$Q13_SOURCE_DIR" \
      --v03-root "$V03_ROOT" \
      --output-dir "$PREPARE_DIR"
    ;;
  shard)
    [[ $# -eq 2 ]] || usage
    readonly LINEAGE=$2
    case "$LINEAGE" in q13-a|q13-b|q13-c) ;; *) usage ;; esac
    require_success prepare
    [[ -f "$PREPARE" && -f "$PREPARE_DIR/prepare-live-seal.json" ]] || {
      echo "sealed PREPARE_LIVE is missing" >&2; exit 66;
    }
    mkdir -p "$SHARD_DIR"
    readonly SHARD_OUTPUT="$SHARD_DIR/$LINEAGE.json"
    [[ ! -e "$SHARD_OUTPUT" ]] || { echo "shard output already exists" >&2; exit 73; }
    run_once "shard-$LINEAGE" 14400 env -C "$CHECKOUT" PYTHONPATH=src "$PYTHON" "$RUNNER" shard \
      --prepare "$PREPARE" \
      --t1-prereg "$T1_PREREG" \
      --tle-root "$TLE_ROOT" \
      --prereg "$SIMULATOR_PREREG" \
      --main-dir "$MAIN_DIR" \
      --gate-dir "$GATE_DIR" \
      --q13-source-dir "$Q13_SOURCE_DIR" \
      --v03-root "$V03_ROOT" \
      --lineage "$LINEAGE" \
      --output "$SHARD_OUTPUT"
    ;;
  merge)
    [[ $# -eq 1 ]] || usage
    require_success shard-q13-a
    require_success shard-q13-b
    require_success shard-q13-c
    [[ ! -e "$MERGED_DIR" ]] || { echo "merged output already exists" >&2; exit 73; }
    run_once merge 600 env -C "$CHECKOUT" PYTHONPATH=src "$PYTHON" "$RUNNER" merge \
      --shards "$SHARD_DIR/q13-a.json" "$SHARD_DIR/q13-b.json" "$SHARD_DIR/q13-c.json" \
      --prepare "$PREPARE" \
      --t1-prereg "$T1_PREREG" \
      --output-dir "$MERGED_DIR"
    ;;
  verify)
    [[ $# -eq 1 ]] || usage
    require_success merge
    run_once verify 600 env -C "$CHECKOUT" PYTHONPATH=src "$PYTHON" "$RUNNER" verify \
      --source "$MERGED_DIR/source.json" \
      --prepare "$PREPARE" \
      --t1-prereg "$T1_PREREG"
    ;;
  *) usage ;;
esac
