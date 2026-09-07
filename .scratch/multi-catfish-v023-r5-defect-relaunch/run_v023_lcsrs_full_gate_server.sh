#!/usr/bin/env bash
set -Eeuo pipefail

# Explicit Ubuntu-server launcher for the frozen V0.23 LC-SRS development gate.
#
# Stage order is deliberately strict:
#   preflight -> source(8) -> source-manifest -> fit(48) -> composition(48)
#   -> independent final verifier.
#
# This script is resumable only at write-once shard boundaries.  It never
# overwrites an existing receipt, never invokes TEST or episode-policy
# training, and keeps every new receipt under the caller-supplied run root.
# Existing receipts are not trusted as evidence: later stages and the final
# verifier reauthenticate them.  A stale/partial/tampered receipt therefore
# fails closed instead of being repaired in place.

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)

PYTHON=${PYTHON:-"$REPO/.venv/bin/python"}
RUN_ROOT=""
TLE_ROOT=""
PREREG="$REPO/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
DEVICE="cpu"
SOURCE_JOBS=2
FIT_JOBS=4
COMPOSITION_JOBS=2

MANIFEST="$SCRIPT_DIR/PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="$SCRIPT_DIR/PREFLIGHT-MANIFEST.sha256"
PREFLIGHT="$SCRIPT_DIR/preflight_v023_lcsrs_r5.py"
SOURCE_SERVER="$SCRIPT_DIR/run_v023_lcsrs_source_server.py"
RUNNER="$SCRIPT_DIR/run_v023_lcsrs_observability_gate.py"
FIT_SERVER="$SCRIPT_DIR/run_v023_lcsrs_fit_server.py"
COMPOSITION_SERVER="$SCRIPT_DIR/run_v023_lcsrs_composition_server.py"
COMPOSITION_RUNTIME="$SCRIPT_DIR/v023_lcsrs_composition_runtime.py"
FINAL_VERIFIER="$SCRIPT_DIR/verify_v023_lcsrs_final.py"
SOURCE_STAGE_VERIFIER="$SCRIPT_DIR/verify_v023_lcsrs_source_stage.py"
RESULT_SEALER="$SCRIPT_DIR/seal_v023_lcsrs_result_directory.py"
CONTRACT="$REPO/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
EXECUTION_ADDENDUM="$REPO/docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"

CONTRACT_SHA256="1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
LINEAGE=2026092101
FIELD_COMPONENT="MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
PLACEBO_KEY="MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
PLACEBO_KEY_SHA256="7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
RUNTIME_FACTORY="build_runtime"

WORLDS=(2026121705 2026121706 2026121707 2026121708 2026121709 2026121710 2026121711 2026121712)
STUDENT_SEEDS=(2026135101 2026135102 2026135103)
ARMS=(INFORMED MATCHED_PLACEBO)

die() {
  printf 'V023_GATE_ERROR: %s\n' "$*" >&2
  exit 2
}

usage() {
  cat <<'EOF'
Usage:
  run_v023_lcsrs_full_gate_server.sh --run-root PATH --tle-root PATH [options]

Required:
  --run-root PATH       new/resumable run root; all generated receipts stay here
  --tle-root PATH       external TRAIN TLE root; must equal the frozen preflight default

Options:
  --prereg PATH         frozen preregistration (default: repository R2 prereg)
  --device DEVICE       fit/composition device (default: cpu)
  --source-jobs N       source parallelism, 1..8 (default: 2)
  --fit-jobs N          fit parallelism, 1..8 (default: 4)
  --composition-jobs N  composition parallelism, 1..8 (default: 2)
  --help                show this help without touching a run root

The launcher performs no episode-policy training and never opens TEST.
Stage order: source(8) -> source-manifest -> fit(48) -> composition(48) -> final verifier.
V0.23 source generation and 48 fits are heavy CPU work; use the Ubuntu server.
EOF
}

while (($#)); do
  case "$1" in
    --run-root)
      (($# >= 2)) || die "--run-root needs a value"
      RUN_ROOT=$2
      shift 2
      ;;
    --tle-root)
      (($# >= 2)) || die "--tle-root needs a value"
      TLE_ROOT=$2
      shift 2
      ;;
    --prereg)
      (($# >= 2)) || die "--prereg needs a value"
      PREREG=$2
      shift 2
      ;;
    --device)
      (($# >= 2)) || die "--device needs a value"
      DEVICE=$2
      shift 2
      ;;
    --source-jobs)
      (($# >= 2)) || die "--source-jobs needs a value"
      SOURCE_JOBS=$2
      shift 2
      ;;
    --fit-jobs)
      (($# >= 2)) || die "--fit-jobs needs a value"
      FIT_JOBS=$2
      shift 2
      ;;
    --composition-jobs)
      (($# >= 2)) || die "--composition-jobs needs a value"
      COMPOSITION_JOBS=$2
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

[[ -n "$RUN_ROOT" ]] || die "--run-root is required"
[[ -n "$TLE_ROOT" ]] || die "--tle-root is required"
[[ "$RUN_ROOT" == /* ]] || die "--run-root must be an absolute path"
[[ -x "$PYTHON" ]] || die "Python executable is missing or not executable: $PYTHON"
PYTHON_RESOLVED=$(readlink -f -- "$PYTHON") || die "Python executable cannot be resolved: $PYTHON"
[[ -f "$PYTHON_RESOLVED" && -x "$PYTHON_RESOLVED" ]] || die "resolved Python is not executable: $PYTHON_RESOLVED"

check_jobs() {
  local name=$1 value=$2
  [[ "$value" =~ ^[1-8]$ ]] || die "$name must be an integer in 1..8"
}
check_jobs source-jobs "$SOURCE_JOBS"
check_jobs fit-jobs "$FIT_JOBS"
check_jobs composition-jobs "$COMPOSITION_JOBS"

for required in \
  "$MANIFEST" "$MANIFEST_DIGEST" "$PREFLIGHT" "$SOURCE_SERVER" "$RUNNER" \
  "$FIT_SERVER" "$COMPOSITION_SERVER" "$COMPOSITION_RUNTIME" "$FINAL_VERIFIER" \
  "$SOURCE_STAGE_VERIFIER" "$RESULT_SEALER" "$CONTRACT" \
  "$EXECUTION_ADDENDUM" "$PREREG"; do
  [[ -f "$required" && ! -L "$required" ]] || die "required input is missing or symlinked: $required"
done

# Resolve user paths without creating them.  Existing symlink roots are
# rejected because the launcher must own a single, unambiguous run directory.
normalize_path() {
  "$PYTHON" - "$1" <<'PY'
from pathlib import Path
import sys

value = Path(sys.argv[1])
if not value.is_absolute():
    raise SystemExit("path must be absolute")
if value.exists() and value.is_symlink():
    raise SystemExit("path is a symlink")
print(value.resolve(strict=False))
PY
}

RUN_ROOT=$(normalize_path "$RUN_ROOT") || die "invalid run root"
[[ "$TLE_ROOT" == /* ]] || die "--tle-root must be an absolute path"
[[ "$PREREG" == /* ]] || die "--prereg must be an absolute path"
TLE_ROOT=$(normalize_path "$TLE_ROOT") || die "invalid TLE root"
PREREG=$(normalize_path "$PREREG") || die "invalid preregistration path"

[[ -d "$TLE_ROOT" && ! -L "$TLE_ROOT" ]] || die "TLE root is missing or symlinked: $TLE_ROOT"

# Authenticate the external preflight before any physical stage.  The
# preflight command is intentionally stdout-suppressed; its canonical receipt
# is not copied into the run root and no existing file is overwritten.
"$PYTHON" "$PREFLIGHT" \
  --manifest "$MANIFEST" \
  --manifest-digest "$MANIFEST_DIGEST" \
  --repo "$REPO" \
  --prereg "$PREREG" >/dev/null || die "V0.23 preflight failed; no source work was started"

PREFLIGHT_SHA256=$(sha256sum "$MANIFEST" | awk '{print $1}')
[[ "$PREFLIGHT_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "preflight manifest digest is malformed"

# Composition runtime reconstructs the TLE root from the frozen preflight
# configuration rather than from a mutable composition CLI argument.  Require
# source and composition to use the same resolved root.
FROZEN_TLE_ROOT=$("$PYTHON" - "$MANIFEST" <<'PY'
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
root = payload["configuration"]["tle"]["root_default"]
print(Path(root).expanduser().resolve(strict=False))
PY
) || die "cannot read frozen TLE root from preflight"
[[ "$TLE_ROOT" == "$FROZEN_TLE_ROOT" ]] || die "--tle-root disagrees with frozen preflight root"

SOURCE_ROOT="$RUN_ROOT/source"
FIT_ROOT="$RUN_ROOT/fit"
COMPOSITION_ROOT="$RUN_ROOT/composition"
SOURCE_MANIFEST="$RUN_ROOT/source-manifest.json"
SOURCE_STAGE_OUTPUT="$RUN_ROOT/source-stage-verification.json"
FINAL_OUTPUT="$RUN_ROOT/final-verification.json"
LAUNCH_METADATA="$RUN_ROOT/LAUNCH-METADATA.json"
RESULT_MANIFEST="$RUN_ROOT/MANIFEST.sha256"
COMPLETE_MARKER="$RUN_ROOT/COMPLETE"

mkdir -p "$RUN_ROOT"
[[ -d "$RUN_ROOT" && ! -L "$RUN_ROOT" ]] || die "run root is not a regular directory"

# Create a run identity marker exactly once, or compare it byte-for-byte in a
# resumable invocation.  This blocks accidental continuation with a different
# contract, preflight, TLE root, or device.
"$PYTHON" - "$LAUNCH_METADATA" "$RUN_ROOT" "$PREFLIGHT_SHA256" "$TLE_ROOT" "$PREREG" "$DEVICE" "$CONTRACT_SHA256" <<'PY'
import json
import os
from pathlib import Path
import sys

target = Path(sys.argv[1])
root = Path(sys.argv[2]).resolve(strict=False)
expected = {
    "schema": "multi-catfish-mcrl-v023-lcsrs-server-run-v1",
    "contract_sha256": sys.argv[7],
    "preflight_manifest_sha256": sys.argv[3],
    "tle_root": sys.argv[4],
    "prereg": sys.argv[5],
    "device": sys.argv[6],
    "split": "TRAIN_DEVELOPMENT",
    "test_split_opened": False,
    "episode_training": False,
    "source_count": 8,
    "fit_count": 48,
    "composition_count": 48,
}
if target.exists() or target.is_symlink():
    if target.is_symlink() or not target.is_file():
        raise SystemExit("launch metadata is not a regular file")
    raw = target.read_bytes()
    try:
        actual = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SystemExit("launch metadata is not ASCII JSON") from error
    canonical = json.dumps(actual, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if raw not in (canonical, canonical + b"\n") or actual != expected:
        raise SystemExit("existing run root metadata disagrees with this launch")
    raise SystemExit(0)

if any(root.iterdir()):
    raise SystemExit("existing non-empty run root has no matching launch metadata")
target.parent.mkdir(parents=True, exist_ok=True)
encoded = json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    with os.fdopen(fd, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
except Exception:
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass
    raise
PY

# Snapshot the exact frozen contract, addendum, preflight manifest, and binding
# digest inside the result tree before any physical source work.  A resumable
# invocation must match these bytes exactly.
"$PYTHON" "$RESULT_SEALER" prepare \
  --run-root "$RUN_ROOT" \
  --contract "$CONTRACT" \
  --addendum "$EXECUTION_ADDENDUM" \
  --preflight-manifest "$MANIFEST" \
  --preflight-digest "$MANIFEST_DIGEST" >/dev/null \
  || die "immutable authority snapshot failed; no source work was started"

mkdir -p "$SOURCE_ROOT" "$FIT_ROOT" "$COMPOSITION_ROOT"

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

source_path() {
  printf '%s/source/world-%s.json\n' "$RUN_ROOT" "$1"
}

fit_path() {
  printf '%s/fit/world-%s/seed-%s/%s.json\n' "$RUN_ROOT" "$1" "$2" "${3,,}"
}

composition_path() {
  printf '%s/composition/world-%s/seed-%s/%s.json\n' "$RUN_ROOT" "$1" "$2" "${3,,}"
}

# Stage 1: exactly eight source worlds.  Existing paths are only skipped as
# resumability hints; source-manifest, fit, composition, and final verification
# reopen the bytes and reject incomplete/tampered sidecars.
for world in "${WORLDS[@]}"; do
  output=$(source_path "$world")
  if [[ -e "$output" || -L "$output" ]]; then
    [[ -f "$output" && ! -L "$output" ]] || die "source output is not a regular file: $output"
    continue
  fi
  mkdir -p "$(dirname -- "$output")"
  start_job "$PYTHON" "$SOURCE_SERVER" \
    --world "$world" \
    --tle-root "$TLE_ROOT" \
    --prereg "$PREREG" \
    --manifest "$MANIFEST" \
    --manifest-digest "$MANIFEST_DIGEST" \
    --execution-addendum "$EXECUTION_ADDENDUM" \
    --placebo-key "$PLACEBO_KEY" \
    --placebo-key-sha256 "$PLACEBO_KEY_SHA256" \
    --lineage "$LINEAGE" \
    --source-family "$FIELD_COMPONENT" \
    --preflight-sha256 "$PREFLIGHT_SHA256" \
    --output "$output"
  if ((${#PIDS[@]} >= SOURCE_JOBS)); then
    wait_jobs || die "source stage failed; no later stage was started"
  fi
done
wait_jobs || die "source stage failed; no later stage was started"

# Stage 2: the existing runner verifies all source JSON/sidecars and seals the
# fit-input manifest.  A pre-existing manifest is retained write-once and is
# reopened by every fit/composition/final verifier rather than overwritten.
if [[ -e "$SOURCE_MANIFEST" || -L "$SOURCE_MANIFEST" ]]; then
  [[ -f "$SOURCE_MANIFEST" && ! -L "$SOURCE_MANIFEST" ]] || die "source manifest is not a regular file"
else
  "$PYTHON" "$RUNNER" source-manifest \
    --source-directory "$RUN_ROOT" \
    --output "$SOURCE_MANIFEST" \
    --preflight-sha256 "$PREFLIGHT_SHA256" || die "source manifest stage failed"
fi

SOURCE_MANIFEST_SHA256=$("$PYTHON" - "$SOURCE_MANIFEST" <<'PY'
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
value = payload.get("source_manifest_sha256")
if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
    raise SystemExit("source manifest digest is malformed")
print(value)
PY
) || die "source manifest digest could not be authenticated"

# Authenticate the complete source denominator before launching any learner.
# Insufficient exposure is a valid frozen decision, not a fit-adapter crash.
SOURCE_ARGS=()
for world in "${WORLDS[@]}"; do
  SOURCE_ARGS+=("$(source_path "$world")")
done
if [[ -e "$SOURCE_STAGE_OUTPUT" || -L "$SOURCE_STAGE_OUTPUT" ]]; then
  [[ -f "$SOURCE_STAGE_OUTPUT" && ! -L "$SOURCE_STAGE_OUTPUT" ]] \
    || die "source-stage verification is not a regular file"
  "$PYTHON" "$SOURCE_STAGE_VERIFIER" \
    --source "${SOURCE_ARGS[@]}" \
    --preflight-sha256 "$PREFLIGHT_SHA256" \
    --verify-existing "$SOURCE_STAGE_OUTPUT" \
    || die "cached source-stage receipt disagrees with recomputed source numerics"
else
  "$PYTHON" "$SOURCE_STAGE_VERIFIER" \
    --source "${SOURCE_ARGS[@]}" \
    --preflight-sha256 "$PREFLIGHT_SHA256" \
    --output "$SOURCE_STAGE_OUTPUT" \
    || die "source-stage coverage verification failed; no fit was started"
fi
SOURCE_STAGE_DECISION=$("$PYTHON" - "$SOURCE_STAGE_OUTPUT" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
if path.is_symlink() or not path.is_file():
    raise SystemExit("source-stage receipt is missing or symlinked")
raw = path.read_bytes()
payload = json.loads(raw.decode("ascii"))
canonical = json.dumps(
    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
).encode("ascii")
if raw not in (canonical, canonical + b"\n"):
    raise SystemExit("source-stage receipt is not canonical")
if payload.get("status") != "VERIFIED_SOURCE_STAGE":
    raise SystemExit("source-stage receipt is not verified")
if payload.get("fit_launched") is not False or payload.get("learner_update") is not False:
    raise SystemExit("source-stage receipt falsely claims learner work")
print(payload.get("decision"))
PY
) || die "source-stage decision could not be authenticated"
if [[ "$SOURCE_STAGE_DECISION" == "INSUFFICIENT_PAIRS" ]]; then
  "$PYTHON" "$RESULT_SEALER" seal \
    --run-root "$RUN_ROOT" \
    --verification "$SOURCE_STAGE_OUTPUT" \
    --kind source-insufficient >/dev/null \
    || die "insufficient-pairs result closure failed"
  printf 'V023_GATE_COMPLETE: %s (INSUFFICIENT_PAIRS; no fit launched)\n' "$RUN_ROOT/result.json"
  exit 0
fi
[[ "$SOURCE_STAGE_DECISION" == "SOURCE_STAGE_READY_FOR_FIT" ]] \
  || die "unexpected source-stage decision: $SOURCE_STAGE_DECISION"

# Stage 3: 8 worlds x 3 student seeds x 2 arms = 48 fit shards.
PIDS=()
for world in "${WORLDS[@]}"; do
  for seed in "${STUDENT_SEEDS[@]}"; do
    for arm in "${ARMS[@]}"; do
      output=$(fit_path "$world" "$seed" "$arm")
      if [[ -e "$output" || -L "$output" ]]; then
        [[ -f "$output" && ! -L "$output" ]] || die "fit output is not a regular file: $output"
        continue
      fi
      mkdir -p "$(dirname -- "$output")"
      start_job "$PYTHON" "$FIT_SERVER" \
        --held-out-world "$world" \
        --student-seed "$seed" \
        --arm "$arm" \
        --source-directory "$RUN_ROOT" \
        --source-manifest "$SOURCE_MANIFEST" \
        --preflight-sha256 "$PREFLIGHT_SHA256" \
        --output "$output" \
        --device "$DEVICE"
      if ((${#PIDS[@]} >= FIT_JOBS)); then
        wait_jobs || die "fit stage failed; composition was not started"
      fi
    done
  done
done
wait_jobs || die "fit stage failed; composition was not started"

# Extract a fit receipt's byte and model hashes without importing Torch or any
# production module.  The composition server independently reopens every fit
# sidecar and rejects a mismatch; these values only bind its typed CLI spec.
fit_hashes() {
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

# Stage 4: composition is deliberately after all 48 fits.  Each worker gets
# one independently keyed world/seed/arm and the existing production runtime
# callback factory; there is no coordinator or post-selection action edit.
PIDS=()
for world in "${WORLDS[@]}"; do
  for seed in "${STUDENT_SEEDS[@]}"; do
    for arm in "${ARMS[@]}"; do
      fit_output=$(fit_path "$world" "$seed" "$arm")
      composition_output=$(composition_path "$world" "$seed" "$arm")
      [[ -f "$fit_output" && ! -L "$fit_output" ]] || die "fit receipt missing before composition: $fit_output"
      if [[ -e "$composition_output" || -L "$composition_output" ]]; then
        [[ -f "$composition_output" && ! -L "$composition_output" ]] || die "composition output is not a regular file: $composition_output"
        continue
      fi
      read -r fit_sha model_bytes model_logical < <(fit_hashes "$fit_output") || die "fit receipt hashes could not be read: $fit_output"
      mkdir -p "$(dirname -- "$composition_output")"
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
        --runtime-factory "$RUNTIME_FACTORY"
      if ((${#PIDS[@]} >= COMPOSITION_JOBS)); then
        wait_jobs || die "composition stage failed; final verification was not started"
      fi
    done
  done
done
wait_jobs || die "composition stage failed; final verification was not started"

# Stage 5: final verification is write-once as well.  Its independent checker
# reopens all 8 source, 48 fit, and 48 composition artifacts, recomputes the
# closed-boundary predicates, and emits INVALID_RUN before a scientific token.
if [[ -e "$FINAL_OUTPUT" || -L "$FINAL_OUTPUT" ]]; then
  die "final verification already exists; use a new run root for a new final pass"
fi

FIT_ARGS=()
COMPOSITION_ARGS=()
for world in "${WORLDS[@]}"; do
  for seed in "${STUDENT_SEEDS[@]}"; do
    for arm in "${ARMS[@]}"; do
      FIT_ARGS+=("$(fit_path "$world" "$seed" "$arm")")
      COMPOSITION_ARGS+=("$(composition_path "$world" "$seed" "$arm")")
    done
  done
done

"$PYTHON" "$FINAL_VERIFIER" \
  --source "${SOURCE_ARGS[@]}" \
  --fit "${FIT_ARGS[@]}" \
  --composition "${COMPOSITION_ARGS[@]}" \
  --source-manifest "$SOURCE_MANIFEST" \
  --output "$FINAL_OUTPUT" || die "final verifier rejected the complete panel"

# The final verifier serializes INVALID_RUN as evidence and intentionally exits
# zero, so the shell must not equate process success with verified integrity.
# Authenticate the canonical final receipt before publishing any completion
# marker.  A scientific STOP/REDESIGN token is allowed only after integrity
# passed; it is not converted into GO here.
"$PYTHON" - "$FINAL_OUTPUT" <<'PY' || die "final receipt did not pass integrity"
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
if path.is_symlink() or not path.is_file():
    raise SystemExit("final receipt is missing or symlinked")
raw = path.read_bytes()
try:
    payload = json.loads(raw.decode("ascii"))
except (UnicodeDecodeError, json.JSONDecodeError) as error:
    raise SystemExit("final receipt is not ASCII JSON") from error
canonical = json.dumps(
    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
).encode("ascii")
if raw not in (canonical, canonical + b"\n"):
    raise SystemExit("final receipt is not canonical JSON")
if payload.get("status") != "PASS_FINAL_INTEGRITY":
    raise SystemExit("final receipt status is not PASS_FINAL_INTEGRITY")
if payload.get("integrity_status") != "VERIFIED":
    raise SystemExit("final receipt integrity status is not VERIFIED")
if (
    payload.get("source_count") != 8
    or payload.get("fit_count") != 48
    or payload.get("composition_count") != 48
):
    raise SystemExit("final receipt panel counts drifted")
if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
    raise SystemExit("final receipt crossed a closed boundary")
PY

if [[ -e "$RESULT_MANIFEST" || -L "$RESULT_MANIFEST" || -e "$COMPLETE_MARKER" || -L "$COMPLETE_MARKER" ]]; then
  die "completion receipt already exists; refusing to overwrite"
fi
"$PYTHON" "$RESULT_SEALER" seal \
  --run-root "$RUN_ROOT" \
  --verification "$FINAL_OUTPUT" \
  --kind full >/dev/null \
  || die "immutable full-result closure failed"

printf 'V023_GATE_COMPLETE: %s\n' "$RUN_ROOT/result.json"
