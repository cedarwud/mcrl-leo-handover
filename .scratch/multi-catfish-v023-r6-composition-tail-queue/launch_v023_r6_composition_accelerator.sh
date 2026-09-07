#!/usr/bin/env bash
set -Eeuo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

# Server-side, composition-only acceleration for the already-running R6 gate.
#
# This wrapper is deliberately not a replacement for the R6 full runner.  It
# launches only the twenty fixed tail identities below, with the same composition
# server arguments used by run_v023_lcsrs_full_gate_server.sh.  It never runs a
# source stage, fit stage, final verifier, TEST split, or episode training.
#
# The wrapper has no SSH path and does not create a server root.  A live
# controller pid and an operator-provided, same-run memory proof are required.
# The preflight also rejects an active target worker, partial sidecars, and any
# unexpected composition concurrency.  All generated accelerator receipts stay
# outside the full-run result tree so the full-run MANIFEST.sha256 remains
# owned by the original controller.

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
R6_DIR="$REPO/.scratch/multi-catfish-v023-r6-fit-binding-fix"

PYTHON="${PYTHON:-$REPO/.venv/bin/python}"
SERVER_ROOT="${V023_SERVER_ROOT:-/home/sat/mcrl-v023-lcsrs-gate-20260906-r6}"
RUN_ROOT="${V023_RUN_ROOT:-$SERVER_ROOT/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r6/server-run}"
LOG_ROOT="${V023_ACCELERATOR_LOG_ROOT:-$SERVER_ROOT/composition-tail-queue-20260906}"
PREREG="${V023_PREREG:-$REPO/artifacts/PREREG-FROZEN-2026-08-25-R2.json}"
CONTROLLER_PID="${V023_CONTROLLER_PID:-}"
MEMORY_PROOF="${V023_MEMORY_PROOF:-}"

PREFLIGHT="$SCRIPT_DIR/preflight_v023_r6_composition_accelerator.py"
BASE_PREFLIGHT="$R6_DIR/preflight_v023_lcsrs_r6.py"
MANIFEST="$R6_DIR/PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="$R6_DIR/PREFLIGHT-MANIFEST.sha256"
COMPOSITION_SERVER="$R6_DIR/run_v023_lcsrs_composition_server.py"
COMPOSITION_RUNTIME="$R6_DIR/v023_lcsrs_composition_runtime.py"
SOURCE_MANIFEST="$RUN_ROOT/source-manifest.json"
CONTRACT_SHA256="1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
EXPECTED_PREFLIGHT_SHA256="761436f04fe322679068e2482b672bee53628115872ef0bcf21be537ad2fc446"
EXPECTED_TLE_ROOT="/home/sat/mcrl-runtime/tle-frozen-20260820"
DEVICE=cpu
ACCELERATOR_JOBS=6

WORLDS=(2026121705 2026121706 2026121707 2026121708 2026121709 2026121710 2026121711 2026121712)
STUDENT_SEEDS=(2026135101 2026135102 2026135103)
ARMS=(INFORMED MATCHED_PLACEBO)

die() {
  printf 'V023_COMPOSITION_ACCELERATOR_NO-GO: %s\n' "$*" >&2
  exit 4
}

usage() {
  cat <<'EOF'
Usage:
  launch_v023_r6_composition_accelerator.sh \
    --controller-pid PID --memory-proof PATH [options]

This script is server-side only.  It has no SSH/launch-to-server behavior.
The defaults point at the prepared R6 Ubuntu root; pass paths explicitly when
auditing a fixture.

Required for a launch:
  --controller-pid PID     live v023_lcsrs_gate_controller.sh pid
  --memory-proof PATH      same-run incremental RSS proof for six new workers

Options:
  --repo-root PATH         R6 checkout containing this script's scratch tree
  --server-root PATH       prepared R6 root
  --run-root PATH          existing full-run result root
  --log-root PATH          new receipt/log directory outside run-root
  --python PATH            server Python executable
  --prereg PATH            frozen R2 preregistration
  --help                   show this help without touching a path

Fixed composition panel: worlds 2026121709--1711, all three seeds and both
arms, plus world 2026121712 seed 2026135101 and both arms (20 targets).
At most six existing workers plus six queue workers gives a total cap of 12.
EOF
}

while (($#)); do
  case "$1" in
    --repo-root)
      (($# >= 2)) || die "--repo-root needs a value"
      REPO=$2
      shift 2
      ;;
    --server-root)
      (($# >= 2)) || die "--server-root needs a value"
      SERVER_ROOT=$2
      shift 2
      ;;
    --run-root)
      (($# >= 2)) || die "--run-root needs a value"
      RUN_ROOT=$2
      shift 2
      ;;
    --log-root)
      (($# >= 2)) || die "--log-root needs a value"
      LOG_ROOT=$2
      shift 2
      ;;
    --python)
      (($# >= 2)) || die "--python needs a value"
      PYTHON=$2
      shift 2
      ;;
    --prereg)
      (($# >= 2)) || die "--prereg needs a value"
      PREREG=$2
      shift 2
      ;;
    --controller-pid)
      (($# >= 2)) || die "--controller-pid needs a value"
      CONTROLLER_PID=$2
      shift 2
      ;;
    --memory-proof)
      (($# >= 2)) || die "--memory-proof needs a value"
      MEMORY_PROOF=$2
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

[[ -n "$CONTROLLER_PID" && "$CONTROLLER_PID" =~ ^[1-9][0-9]*$ ]] || die "--controller-pid is required and must be a positive integer"
[[ -n "$MEMORY_PROOF" ]] || die "--memory-proof is required; memory safety is otherwise unverified"
# The production R6 runner itself uses the checkout venv's conventional
# ``bin/python -> python3`` symlink.  Require an executable, but do not reject
# that authenticated production interpreter solely because it is a symlink.
[[ -x "$PYTHON" ]] || die "Python executable is missing or not executable: $PYTHON"
[[ -d "$REPO" && ! -L "$REPO" ]] || die "repository root is missing or symlinked: $REPO"
[[ -d "$SERVER_ROOT" && ! -L "$SERVER_ROOT" ]] || die "server root is missing or symlinked: $SERVER_ROOT"
[[ -d "$RUN_ROOT" && ! -L "$RUN_ROOT" ]] || die "full-run result root is missing or symlinked: $RUN_ROOT"
[[ -f "$MEMORY_PROOF" && ! -L "$MEMORY_PROOF" ]] || die "memory proof is missing or symlinked: $MEMORY_PROOF"

SERVER_ROOT=$(readlink -f -- "$SERVER_ROOT") || die "server root cannot be resolved"
RUN_ROOT=$(readlink -f -- "$RUN_ROOT") || die "run root cannot be resolved"
REPO=$(readlink -f -- "$REPO") || die "repository root cannot be resolved"
LOG_ROOT=$(readlink -m -- "$LOG_ROOT") || die "log root cannot be resolved"
R6_DIR="$REPO/.scratch/multi-catfish-v023-r6-fit-binding-fix"
PREFLIGHT="$REPO/.scratch/multi-catfish-v023-r6-composition-tail-queue/preflight_v023_r6_composition_accelerator.py"
BASE_PREFLIGHT="$R6_DIR/preflight_v023_lcsrs_r6.py"
MANIFEST="$R6_DIR/PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="$R6_DIR/PREFLIGHT-MANIFEST.sha256"
COMPOSITION_SERVER="$R6_DIR/run_v023_lcsrs_composition_server.py"
COMPOSITION_RUNTIME="$R6_DIR/v023_lcsrs_composition_runtime.py"
SOURCE_MANIFEST="$RUN_ROOT/source-manifest.json"

[[ "$RUN_ROOT" == "$SERVER_ROOT/"* ]] || die "run root is outside declared server root"
[[ "$LOG_ROOT" != "$RUN_ROOT" && "$LOG_ROOT" != "$RUN_ROOT/"* ]] || die "log root must stay outside the full-run result root"
for required in "$PREFLIGHT" "$BASE_PREFLIGHT" "$MANIFEST" "$MANIFEST_DIGEST" "$COMPOSITION_SERVER" "$COMPOSITION_RUNTIME" "$PREREG"; do
  [[ -f "$required" && ! -L "$required" ]] || die "required input is missing or symlinked: $required"
done

# A fresh log root is itself write-once.  This avoids appending a new launch
# onto an old receipt and gives every acceleration attempt a unique audit lane.
if [[ -e "$LOG_ROOT" || -L "$LOG_ROOT" ]]; then
  die "refusing to reuse an existing accelerator log root: $LOG_ROOT"
fi
mkdir -p "$LOG_ROOT"
[[ -d "$LOG_ROOT" && ! -L "$LOG_ROOT" ]] || die "cannot create regular accelerator log root"
LOG_FILE="$LOG_ROOT/accelerator.log"
[[ ! -e "$LOG_FILE" && ! -L "$LOG_FILE" ]] || die "accelerator log already exists"
exec >"$LOG_FILE" 2>&1

printf 'V023_COMPOSITION_ACCELERATOR_START server_root=%s run_root=%s controller_pid=%s\n' "$SERVER_ROOT" "$RUN_ROOT" "$CONTROLLER_PID"
printf 'V023_COMPOSITION_TAIL_QUEUE_PANEL worlds=2026121709,2026121710,2026121711 all_seeds=2026135101,2026135102,2026135103 plus_world=2026121712 plus_seed=2026135101 arms=INFORMED,MATCHED_PLACEBO queue_jobs=6 total_max=12\n'

"$PYTHON" "$BASE_PREFLIGHT" \
  --manifest "$MANIFEST" \
  --manifest-digest "$MANIFEST_DIGEST" \
  --repo "$REPO" \
  --prereg "$PREREG" \
  || die "the exact R6 base preflight failed"

PREFLIGHT_SHA256=$(sha256sum "$MANIFEST" | awk '{print $1}')
[[ "$PREFLIGHT_SHA256" == "$EXPECTED_PREFLIGHT_SHA256" ]] || die "R6 preflight manifest digest drifted"
PREFLIGHT_RECEIPT="$LOG_ROOT/PREFLIGHT-RECEIPT.json"

set +e
"$PYTHON" "$PREFLIGHT" \
  --repo-root "$REPO" \
  --run-root "$RUN_ROOT" \
  --server-root "$SERVER_ROOT" \
  --controller-pid "$CONTROLLER_PID" \
  --memory-proof "$MEMORY_PROOF" \
  --receipt "$PREFLIGHT_RECEIPT"
preflight_status=$?
set -e
case "$preflight_status" in
  0)
    ;;
  3)
    printf 'V023_COMPOSITION_TAIL_QUEUE_SKIP: all twenty target outputs already pass sidecar validation\n'
    exit 0
    ;;
  *)
    die "composition accelerator preflight returned status $preflight_status"
    ;;
esac

SOURCE_MANIFEST_SHA256=$("$PYTHON" - "$SOURCE_MANIFEST" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="ascii"))
value = payload.get("source_manifest_sha256")
if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
    raise SystemExit("source manifest digest is malformed")
print(value)
PY
) || die "source manifest digest could not be authenticated"

fit_hashes() {
  # This is byte-for-byte the hash extraction used by the R6 full runner.
  "$PYTHON" - "$1" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="ascii"))
fit_sha = hashlib.sha256(path.read_bytes()).hexdigest()
model_bytes = payload.get("model_sha256")
model_logical = payload.get("network_sha256")
for value, label in ((fit_sha, "fit"), (model_bytes, "model bytes"), (model_logical, "model")):
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise SystemExit(f"{label} digest is malformed")
print(f"{fit_sha} {model_bytes} {model_logical}")
PY
}

PIDS=()
start_job() {
  "$@" &
  PIDS+=("$!")
}

wait_jobs() {
  local status=0 pid
  for pid in "${PIDS[@]}"; do
    if ! wait "$pid"; then
      status=1
    fi
  done
  PIDS=()
  return "$status"
}

guard_target() {
  local world=$1 seed=$2 arm=$3
  local ignored=(--ignore-pid "$$")
  local pid
  for pid in "${PIDS[@]}"; do
    ignored+=(--ignore-pid "$pid")
  done
  set +e
  "$PYTHON" "$PREFLIGHT" \
    --repo-root "$REPO" \
    --run-root "$RUN_ROOT" \
    --server-root "$SERVER_ROOT" \
    --controller-pid "$CONTROLLER_PID" \
    --memory-proof "$MEMORY_PROOF" \
    --only-target "$world" "$seed" "$arm" \
    "${ignored[@]}" \
    >/dev/null
  local status=$?
  set -e
  return "$status"
}

for world in 2026121709 2026121710 2026121711 2026121712; do
  if [[ "$world" == 2026121712 ]]; then
    queue_seeds=(2026135101)
  else
    queue_seeds=(2026135101 2026135102 2026135103)
  fi
  for seed in "${queue_seeds[@]}"; do
    for arm in INFORMED MATCHED_PLACEBO; do
      if guard_target "$world" "$seed" "$arm"; then
        fit_output="$RUN_ROOT/fit/world-$world/seed-$seed/${arm,,}.json"
        composition_output="$RUN_ROOT/composition/world-$world/seed-$seed/${arm,,}.json"
        [[ -f "$fit_output" && ! -L "$fit_output" ]] || die "fit receipt missing before composition: $fit_output"
        [[ ! -e "$composition_output" && ! -L "$composition_output" ]] || die "target output appeared before launch: $composition_output"
        read -r fit_sha model_bytes model_logical < <(fit_hashes "$fit_output") || die "fit receipt hashes could not be read: $fit_output"
        printf 'V023_COMPOSITION_ACCELERATOR_LAUNCH_TARGET world=%s seed=%s arm=%s output=%s fit_sha256=%s model_bytes_sha256=%s model_sha256=%s\n' \
          "$world" "$seed" "$arm" "$composition_output" "$fit_sha" "$model_bytes" "$model_logical"
        mkdir -p "$(dirname -- "$composition_output")"
        # Keep this invocation identical to the R6 full runner's composition
        # command, including fit hashes, contract, device, and runtime factory.
        start_job "$PYTHON" "$COMPOSITION_SERVER" \
          --held-out-world "$world" \
          --student-seed "$seed" \
          --arm "$arm" \
          --source-directory "$RUN_ROOT" \
          --source-manifest "$SOURCE_MANIFEST" \
          --preflight-sha256 "$PREFLIGHT_SHA256" \
          --source-manifest-sha256 "$SOURCE_MANIFEST_SHA256" \
          --fit-receipt "$fit_output" \
          --fit-receipt-sha256 "$fit_sha" \
          --model-bytes-sha256 "$model_bytes" \
          --model-sha256 "$model_logical" \
          --contract-sha256 "$CONTRACT_SHA256" \
          --output "$composition_output" \
          --device "$DEVICE" \
          --runtime-module "$COMPOSITION_RUNTIME" \
          --runtime-factory build_runtime
        if ((${#PIDS[@]} >= ACCELERATOR_JOBS)); then
          wait_jobs || die "composition worker failed; no scientific result was emitted"
        fi
      else
        status=$?
        [[ "$status" == 3 ]] || die "target preflight returned status $status for $world/$seed/$arm"
        printf 'V023_COMPOSITION_ACCELERATOR_SKIP_TARGET world=%s seed=%s arm=%s\n' "$world" "$seed" "$arm"
      fi
    done
  done
done
wait_jobs || die "composition worker failed; no scientific result was emitted"

COMPLETION_RECEIPT="$LOG_ROOT/COMPLETION-RECEIPT.json"
"$PYTHON" "$PREFLIGHT" \
  --repo-root "$REPO" \
  --run-root "$RUN_ROOT" \
  --server-root "$SERVER_ROOT" \
  --mode completion \
  --receipt "$COMPLETION_RECEIPT" \
  || die "completed composition sidecars did not pass the write-once receipt check"

printf 'V023_COMPOSITION_ACCELERATOR_COMPLETE receipt=%s\n' "$COMPLETION_RECEIPT"
