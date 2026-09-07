#!/usr/bin/env bash
set -Eeuo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "${script_dir}/../.." && pwd -P)
server_host=${V023_SUCCESSOR_SERVER_HOST:-sat}
checkout=/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout
target_root=/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8
output_root=/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1
tmux_session=mcrl-v023-c1c2-successor-100e-r1
server_python=${V023_SUCCESSOR_SERVER_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}
local_python=${V023_SUCCESSOR_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}

bundle_rel=.scratch/multi-catfish-v023-c1c2-successor-launch
successor_rel=.scratch/multi-catfish-v023-c1c2-successor
factory_rel=.scratch/multi-catfish-v023-c1c2-provider-factory-v3
runner_rel=.scratch/multi-catfish-v023-two-route-source-training-runner
bundle=${repo_root}/${bundle_rel}
bind=${bundle}/bind_v023_c1c2_successor_freeze.py
builder=${bundle}/build_v023_c1c2_successor_launch_manifest.py
preflight=${bundle}/preflight_v023_c1c2_successor.py
diagnostic=${bundle}/run_v023_c1c2_successor_one_epoch_diagnostic.py
formal_runner=${bundle}/run_v023_c1c2_successor_formal.py
verifier=${bundle}/verify_v023_c1c2_successor.py
manifest=${bundle}/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json
bindings=${bundle}/V023-C1C2-SUCCESSOR-EXECUTION-BINDINGS.json
learner_manifest=${bundle}/V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json
provider_config=${bundle}/V023-C1C2-SUCCESSOR-PROVIDER-CONFIG.json
model_config=${repo_root}/${successor_rel}/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json
declaration=${repo_root}/${successor_rel}/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md

remote_bundle=${checkout}/${bundle_rel}
remote_bind=${remote_bundle}/bind_v023_c1c2_successor_freeze.py
remote_preflight=${remote_bundle}/preflight_v023_c1c2_successor.py
remote_diagnostic=${remote_bundle}/run_v023_c1c2_successor_one_epoch_diagnostic.py
remote_formal_runner=${remote_bundle}/run_v023_c1c2_successor_formal.py
remote_verifier=${remote_bundle}/verify_v023_c1c2_successor.py
remote_manifest=${remote_bundle}/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json
remote_bindings=${remote_bundle}/V023-C1C2-SUCCESSOR-EXECUTION-BINDINGS.json
remote_learner_manifest=${remote_bundle}/V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json
remote_provider_config=${remote_bundle}/V023-C1C2-SUCCESSOR-PROVIDER-CONFIG.json
remote_model_config=${checkout}/${successor_rel}/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json
remote_declaration=${checkout}/${successor_rel}/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md
remote_preflight_receipt=${remote_bundle}/PREFLIGHT-RECEIPT.json
remote_diagnostic_root=${checkout}/successor-one-epoch-diagnostic-scratch
remote_diagnostic_receipt=${remote_diagnostic_root}/one-epoch-diagnostic.json
remote_startup_marker=${checkout}/SUCCESSOR-STARTUP.json
remote_log=${checkout}/successor-source-training.log

die() {
  printf 'SUCCESSOR_LAUNCH_REFUSED: %s\n' "$*" >&2
  exit 2
}

quote_command() {
  printf '%q ' "$@"
  printf '\n'
}

usage() {
  printf '%s\n' \
    'Usage: sync_launch_v023_c1c2_successor_server.sh [--dry-run]' \
    '       sync_launch_v023_c1c2_successor_server.sh --check-diagnostic-receipt PATH'
}

dry_run=0
diagnostic_only=
while (($#)); do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    --check-diagnostic-receipt)
      (($# >= 2)) || die '--check-diagnostic-receipt requires a path'
      diagnostic_only=$2
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

if [[ -n "$diagnostic_only" ]]; then
  "$local_python" "$preflight" --diagnostic-receipt "$diagnostic_only" \
    || die 'diagnostic receipt is not PASS'
  exit 0
fi

[[ -x "$local_python" ]] || die "local Python is unavailable: $local_python"
for path in "$bind" "$builder" "$preflight" "$diagnostic" "$formal_runner" "$verifier"; do
  [[ -f "$path" && ! -L "$path" ]] || die "launch input is missing or symlinked: $path"
done

local_bind_cmd=("$local_python" "$bind" --repo "$repo_root" --target-root "$target_root" --check)
local_manifest_cmd=("$local_python" "$builder" --repo "$repo_root" --check)

if ((dry_run)); then
  "${local_bind_cmd[@]}" || die 'execution bindings are not current'
  "${local_manifest_cmd[@]}" || die 'launch manifest is not current'
  mapfile -t dry_paths < <("$local_python" "$builder" --repo "$repo_root" --paths)
  ((${#dry_paths[@]} > 0)) || die 'launch manifest has no payload paths'
  dry_rsync=(rsync -aR --protect-args)
  for relative in "${dry_paths[@]}"; do
    dry_rsync+=("./$relative")
  done
  dry_rsync+=("./$bundle_rel/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json")
  dry_rsync+=("./$bundle_rel/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json.sha256")
  dry_rsync+=("${server_host}:${checkout}/")
  dry_provider_sha=$(sha256sum "$provider_config" | awk '{print $1}')
  dry_remote_env="export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH='$checkout/src:$checkout:$checkout/$factory_rel:$checkout/$runner_rel'"
  dry_factory_env="export MCRL_V023_C1C2_PROVIDER_CONFIG_PATH='$remote_provider_config' MCRL_V023_C1C2_PROVIDER_CONFIG_SHA256='$dry_provider_sha' MCRL_V023_C1C2_LEARNER_MANIFEST_PATH='$remote_learner_manifest'"
  printf 'LOCAL '
  quote_command "${local_bind_cmd[@]}"
  printf 'LOCAL '
  quote_command "${local_manifest_cmd[@]}"
  printf 'REMOTE '
  quote_command ssh -- "$server_host" "test ! -e '$output_root' && test ! -L '$output_root'"
  printf 'RSYNC '
  printf '(cd %q && ' "$repo_root"
  quote_command "${dry_rsync[@]}"
  printf ')\n'
  printf 'REMOTE ssh -- %q %q\n' "$server_host" \
    "set -Eeuo pipefail; cd '$checkout'; '$server_python' '$remote_bind' --repo '$checkout' --verify-learner-manifest-only"
  printf 'REMOTE ssh -- %q %q\n' "$server_host" \
    "set -Eeuo pipefail; cd '$checkout'; $dry_remote_env; $dry_factory_env; test ! -e '$output_root' && test ! -L '$output_root'; '$server_python' '$remote_preflight' --repo '$checkout' --bindings '$remote_bindings' --manifest '$remote_manifest' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --declaration '$remote_declaration' --output-root '$output_root' --receipt '$remote_preflight_receipt' --target-root '$target_root' --formal"
  printf 'REMOTE ssh -- %q %q\n' "$server_host" \
    "set -Eeuo pipefail; cd '$checkout'; $dry_remote_env; $dry_factory_env; test ! -e '$remote_diagnostic_root' && test ! -L '$remote_diagnostic_root'; '$server_python' '$remote_diagnostic' --repo '$checkout' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --output-root '$remote_diagnostic_root'"
  printf 'REMOTE ssh -- %q %q\n' "$server_host" \
    "set -Eeuo pipefail; $dry_remote_env; '$server_python' '$remote_preflight' --diagnostic-receipt '$remote_diagnostic_receipt' --diagnostic-preflight-receipt '$remote_preflight_receipt'"
  dry_controller="set -Eeuo pipefail; $dry_remote_env; $dry_factory_env; umask 077; '$server_python' -c \"import json,os; p='$remote_startup_marker'; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,(json.dumps({'status':'CONTROLLER_STARTED','output_root':'$output_root'},sort_keys=True,separators=(',',':'))+'\\n').encode('ascii')); os.close(fd)\"; '$server_python' '$remote_formal_runner' --output-root '$output_root' --epochs 100 --provider-factory v023_c1c2_provider_factory_v3:make_provider --model-config-json '$remote_model_config' --train-seed 2927175120652069826 --preflight-receipt '$remote_preflight_receipt' --execute; '$server_python' '$remote_verifier' --repo '$checkout' --output-root '$output_root' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --preflight-receipt '$remote_preflight_receipt' --write"
  printf 'REMOTE ssh -- %q %q\n' "$server_host" \
    "set -Eeuo pipefail; test ! -e '$output_root' && test ! -L '$output_root'; test ! -e '$remote_startup_marker' && test ! -L '$remote_startup_marker'; test ! -e '$remote_log' && test ! -L '$remote_log'; tmux new-session -d -s '$tmux_session' \"$dry_controller >>'$remote_log' 2>&1\""
  printf 'PATHS tmux=%s log=%s startup=%s output=%s\n' "$tmux_session" "$remote_log" "$remote_startup_marker" "$output_root"
  exit 0
fi

"${local_bind_cmd[@]}" || die 'execution bindings are not current'
"${local_manifest_cmd[@]}" || die 'launch manifest is not current'

"$local_python" - "$provider_config" <<'PY' || die 'provider config contains a forbidden token'
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]).parent))
from successor_launch_common import reject_forbidden_config
reject_forbidden_config(json.loads(Path(sys.argv[1]).read_text(encoding="ascii")))
PY

remote_absence="test ! -e '$output_root' && test ! -L '$output_root'"
ssh -- "$server_host" "$remote_absence" || die "output root exists or cannot be checked: $output_root"

mapfile -t payload_paths < <("$local_python" "$builder" --repo "$repo_root" --paths)
((${#payload_paths[@]} > 0)) || die 'launch manifest has no payload paths'
rsync_args=(rsync -aR --protect-args)
for relative in "${payload_paths[@]}"; do
  [[ "$relative" != /* && "$relative" != *..* ]] || die "unsafe manifest path: $relative"
  rsync_args+=("./$relative")
done
rsync_args+=("./$bundle_rel/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json")
rsync_args+=("./$bundle_rel/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json.sha256")
rsync_args+=("${server_host}:${checkout}/")
(cd "$repo_root" && "${rsync_args[@]}") || die 'authenticated launch closure sync failed'

remote_env="export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH='$checkout/src:$checkout:$checkout/$factory_rel:$checkout/$runner_rel'"
ssh -- "$server_host" "set -Eeuo pipefail; cd '$checkout'; $remote_env; '$server_python' '$remote_bind' --repo '$checkout' --verify-learner-manifest-only" \
  || die 'server learner manifest verification failed'

provider_sha=$(sha256sum "$provider_config" | awk '{print $1}')
factory_env="export MCRL_V023_C1C2_PROVIDER_CONFIG_PATH='$remote_provider_config' MCRL_V023_C1C2_PROVIDER_CONFIG_SHA256='$provider_sha' MCRL_V023_C1C2_LEARNER_MANIFEST_PATH='$remote_learner_manifest'"
preflight_command="set -Eeuo pipefail; cd '$checkout'; $remote_env; $factory_env; test ! -e '$output_root' && test ! -L '$output_root'; '$server_python' '$remote_preflight' --repo '$checkout' --bindings '$remote_bindings' --manifest '$remote_manifest' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --declaration '$remote_declaration' --output-root '$output_root' --receipt '$remote_preflight_receipt' --target-root '$target_root' --formal"
ssh -- "$server_host" "$preflight_command" || die 'factory-v3 preflight failed'

diagnostic_command="set -Eeuo pipefail; cd '$checkout'; $remote_env; $factory_env; test ! -e '$remote_diagnostic_root' && test ! -L '$remote_diagnostic_root'; '$server_python' '$remote_diagnostic' --repo '$checkout' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --output-root '$remote_diagnostic_root'"
ssh -- "$server_host" "$diagnostic_command" || die 'one-epoch diagnostic execution failed'
ssh -- "$server_host" "set -Eeuo pipefail; $remote_env; '$server_python' '$remote_preflight' --diagnostic-receipt '$remote_diagnostic_receipt' --diagnostic-preflight-receipt '$remote_preflight_receipt'" \
  || die 'one-epoch diagnostic did not produce an authenticated PASS receipt'

ssh -- "$server_host" "$remote_absence" || die "output root appeared before launch: $output_root"
controller="set -Eeuo pipefail; $remote_env; $factory_env; umask 077; '$server_python' -c \"import json,os; p='$remote_startup_marker'; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,(json.dumps({'status':'CONTROLLER_STARTED','output_root':'$output_root'},sort_keys=True,separators=(',',':'))+'\\n').encode('ascii')); os.close(fd)\"; '$server_python' '$remote_formal_runner' --output-root '$output_root' --epochs 100 --provider-factory v023_c1c2_provider_factory_v3:make_provider --model-config-json '$remote_model_config' --train-seed 2927175120652069826 --preflight-receipt '$remote_preflight_receipt' --execute; '$server_python' '$remote_verifier' --repo '$checkout' --output-root '$output_root' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --preflight-receipt '$remote_preflight_receipt' --write"
ssh -- "$server_host" "set -Eeuo pipefail; test ! -e '$remote_startup_marker' && test ! -L '$remote_startup_marker'; test ! -e '$remote_log' && test ! -L '$remote_log'; tmux new-session -d -s '$tmux_session' \"$controller >>'$remote_log' 2>&1\"" \
  || die 'tmux source-training controller failed to start'

acknowledged=0
for _ in $(seq 1 24); do
  if ssh -- "$server_host" "test -f '$remote_startup_marker' && tmux has-session -t '$tmux_session' 2>/dev/null" >/dev/null 2>&1; then
    acknowledged=1
    break
  fi
  sleep 5
done
((acknowledged)) || die "startup was not acknowledged within 120 s: $remote_startup_marker"
printf 'SUCCESSOR_SOURCE_TRAINING_LAUNCHED tmux=%s log=%s startup=%s output=%s preflight=%s\n' \
  "$tmux_session" "$remote_log" "$remote_startup_marker" "$output_root" "$remote_preflight_receipt"
