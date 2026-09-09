#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare a fresh Ubuntu checkout and launch only TRAIN physical C1/C2 target
# generation. A dry run never invokes ssh, rsync, mkdir remotely, or tmux.

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
server_host="${V023_SERVER_HOST:-sat}"
server_root="${V023_SERVER_ROOT:-/home/sat/mcrl-v023-c1c2-target-generation-20260906-d40}"
output_root="${V023_TARGET_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-targets-20260906-d40}"
session="${V023_TMUX_SESSION:-mcrl-v023-c1c2-target-generation-20260906-d40}"
local_python="${V023_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}"
server_python="${V023_SERVER_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
tle_root="${V023_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
capture_root="${V023_CAPTURE_ROOT:-/home/sat/mcrl-v023-c1c2-predecision-20260906-r4/capture-run}"
source_authority_root="${V023_SOURCE_AUTHORITY_ROOT:-/home/sat/mcrl-v023-c1c2-predecision-20260906-r4}"
capture="${capture_root}/panel-capture.json"
materialization="${capture_root}/materialized-source"
manifest="${repo_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.json"
manifest_digest="${repo_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.sha256"
preflight="${repo_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/preflight_v023_c1c2_targets.py"
checkpoint_audit="${repo_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/audit_v023_c1c2_checkpoint_closure.py"
short_benchmark="${repo_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/run_v023_c1c2_short_benchmarks.py"
dry_run=0

die() { printf 'V023_C1C2_TARGET_SYNC_ERROR: %s\n' "$*" >&2; exit 2; }
is_clean_abs() { [[ "$1" =~ ^/[A-Za-z0-9._/-]+$ && "$1" != *'//' && "$1" != */./* && "$1" != */../* ]]; }

while (($#)); do
  case "$1" in
    --server-host) (($# >= 2)) || die "--server-host needs a value"; server_host="$2"; shift 2;;
    --server-root) (($# >= 2)) || die "--server-root needs a value"; server_root="$2"; shift 2;;
    --output-root) (($# >= 2)) || die "--output-root needs a value"; output_root="$2"; shift 2;;
    --tmux-session) (($# >= 2)) || die "--tmux-session needs a value"; session="$2"; shift 2;;
    --source-authority-root) (($# >= 2)) || die "--source-authority-root needs a value"; source_authority_root="$2"; shift 2;;
    --dry-run) dry_run=1; shift;;
    -h|--help) sed -n '1,24p' "$0"; exit 0;;
    *) die "unknown argument: $1";;
  esac
done

# These paths depend on command-line-overridable ``server_root`` and must be
# derived only after argument parsing.
controller="${server_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/run_v023_c1c2_targets_server.py"
log="${server_root}/controller.log"
short_benchmark_root="${server_root}/short-benchmark-receipts"
server_short_benchmark="${server_root}/.scratch/multi-catfish-v023-c1c2-target-generation-launch/run_v023_c1c2_short_benchmarks.py"
frozen_three_route="${source_authority_root}/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py"
restored_three_route="${server_root}/src/mcrl/algorithms/ee_axis_lcsrs_three_route.py"

[[ -d "$repo_root" && ! -L "$repo_root" ]] || die "repository root is invalid"
[[ -x "$local_python" ]] || die "local Python is missing: $local_python"
[[ -f "$checkpoint_audit" && ! -L "$checkpoint_audit" ]] || die "checkpoint closure audit is missing: $checkpoint_audit"
[[ -f "$short_benchmark" && ! -L "$short_benchmark" ]] || die "short benchmark runner is missing: $short_benchmark"
for path in "$server_root" "$output_root" "$tle_root" "$capture_root" "$source_authority_root"; do
  is_clean_abs "$path" || die "unsafe absolute path: $path"
done
[[ "$server_root" =~ ^/home/sat/ ]] || die "server root must be below /home/sat"
[[ "$output_root" =~ ^/home/sat/ ]] || die "output root must be below /home/sat"
[[ "$output_root" != "$server_root" ]] || die "output root must be distinct from server root"
[[ "$session" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe tmux session"
cd "$repo_root"

sync_paths=(
  pyproject.toml src scripts tests
  artifacts/PREREG-FROZEN-2026-08-25-R2.json
  docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R6-FIT-BINDING-2026-09-06.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md
  .scratch/multi-catfish-v023-c1c2-target-generation
  .scratch/multi-catfish-v023-c1c2-target-generation-launch
  .scratch/multi-catfish-v023-c1c2-neutral-materialization
  .scratch/multi-catfish-v023-c1c2-predecision-capture
  .scratch/multi-catfish-v023-c1c2-neutral-adapters
  .scratch/multi-catfish-v023-r6-fit-binding-fix
  .scratch/multi-catfish-v023-r7-launch-ready
  .scratch/multi-catfish-v020-c3-source-audit
  .scratch/multi-catfish-v014-learner
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py
  .scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md
  .scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py
  .scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py
  .scratch/c3-v04/run_v04_c3_500_update_screen.py
  .scratch/c3-v04/run_v04_c3_learnability_gate.py
  .scratch/c3-v04/run_v04_c3_source.py
  artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1/contracts/MULTI-CATFISH-MCRL-V015-C3-LEARNED-CONTEXT-ORACLE-PREREG-2026-09-03.md
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result.json
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/authority.json
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result-seal.json
  docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md
)
for relative in "${sync_paths[@]}"; do
  [[ -e "$repo_root/$relative" && ! -L "$repo_root/$relative" ]] || die "sync dependency missing: $relative"
done

code_manifest_sha256="$(sha256sum "$manifest" | awk '{print $1}')"
"$local_python" "$preflight" --manifest "$manifest" --manifest-digest "$manifest_digest" --repo "$repo_root" >/dev/null \
  || die "local target-generation preflight failed"

if ((dry_run)); then
  printf 'V023_C1C2_TARGET_SYNC_DRY_RUN_PASS\n'
  printf 'server=%s\nserver_root=%s\noutput=%s\nshort_benchmark_root=%s\ntmux=%s\ncontroller=%s\nlog=%s\ncapture=%s\nmaterialization=%s\nsource_authority_root=%s\ncode_manifest_sha256=%s\n' \
    "$server_host" "$server_root" "$output_root" "$short_benchmark_root" "$session" "$controller" "$log" "$capture" "$materialization" "$source_authority_root" "$code_manifest_sha256"
  exit 0
fi

# The R4 capture and the target generator are both bound to the repriced V0.20
# d40 Q1/Q2 checkpoint.  Verify that closure before SSH rather than allowing a
# legacy MODQN checkpoint to enter the replay path.
"$local_python" "$checkpoint_audit" --repo "$repo_root" --require-ready >/dev/null \
  || die "checkpoint closure audit failed; no remote root was created"

if ssh -- "$server_host" "test -e '$server_root' || test -L '$server_root'"; then die "remote server root exists: $server_root"; else [[ $? -eq 1 ]] || die "cannot inspect server root"; fi
if ssh -- "$server_host" "test -e '$output_root' || test -L '$output_root'"; then die "remote output root exists: $output_root"; else [[ $? -eq 1 ]] || die "cannot inspect output root"; fi
if ssh -- "$server_host" "tmux has-session -t '$session' 2>/dev/null"; then die "tmux session exists: $session"; else [[ $? -eq 1 ]] || die "cannot inspect tmux"; fi
ssh -- "$server_host" "mkdir -- '$server_root'"
rsync -aR --exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/' \
  "${sync_paths[@]}" "$server_host:$server_root/"

ssh -- "$server_host" "set -Eeuo pipefail; \
  test -x '$server_python'; test -d '$tle_root' && test ! -L '$tle_root'; \
  test -d '$source_authority_root' && test ! -L '$source_authority_root'; \
  test -f '$frozen_three_route' && test ! -L '$frozen_three_route'; \
  cp -- '$frozen_three_route' '$restored_three_route'; \
  test -f '$capture' && test ! -L '$capture'; test -d '$materialization' && test ! -L '$materialization'; \
  test -f '$materialization/MANIFEST.sha256' && test ! -L '$materialization/MANIFEST.sha256'; \
  cd '$server_root'; export PYTHONDONTWRITEBYTECODE=1; \
  '$server_python' '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/preflight_v023_c1c2_targets.py' \
    --manifest '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.json' \
    --manifest-digest '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.sha256' \
    --repo '$server_root' --require-r6-runtime-closure >/dev/null; \
  V023_LOCAL_PYTHON='$server_python' '$server_python' -m pytest -q \
    '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/test_v023_c1c2_target_generation_launch.py' \
    '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/test_v023_c1c2_short_benchmarks.py'; \
  test ! -e '$short_benchmark_root' && test ! -L '$short_benchmark_root'; \
  '$server_python' '$server_short_benchmark' \
    --python '$server_python' --capture '$capture' --materialization-dir '$materialization' \
    --tle-root '$tle_root' --prereg '$server_root/artifacts/PREREG-FROZEN-2026-08-25-R2.json' \
    --manifest '$server_root/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json' \
    --manifest-digest '$server_root/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256' \
    --execution-addendum '$server_root/docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md' \
    --code-manifest '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.json' \
    --code-manifest-digest '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.sha256' \
    --output '$short_benchmark_root' --timeout-s 540 >/dev/null; \
  '$server_python' '$server_short_benchmark' \
    --python '$server_python' --capture '$capture' --materialization-dir '$materialization' \
    --tle-root '$tle_root' --prereg '$server_root/artifacts/PREREG-FROZEN-2026-08-25-R2.json' \
    --manifest '$server_root/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json' \
    --manifest-digest '$server_root/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256' \
    --execution-addendum '$server_root/docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md' \
    --code-manifest '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.json' \
    --code-manifest-digest '$server_root/.scratch/multi-catfish-v023-c1c2-target-generation-launch/CODE-MANIFEST.sha256' \
    --output '$short_benchmark_root' --timeout-s 540 --validate >/dev/null; \
  '$server_python' -m py_compile '$controller'; \
  test ! -e '$log' && test ! -L '$log'; : > '$log'; \
  tmux new-session -d -s '$session' \"cd '$server_root' && exec '$server_python' '$controller' \
    --python '$server_python' --capture '$capture' --materialization-dir '$materialization' \
    --output '$output_root' --tle-root '$tle_root' --prereg '$server_root/artifacts/PREREG-FROZEN-2026-08-25-R2.json' \
    --manifest '$server_root/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json' \
    --manifest-digest '$server_root/.scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256' \
    --execution-addendum '$server_root/docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md' \
    >> '$log' 2>&1\""
printf 'V023_C1C2_TARGET_SYNC_LAUNCH_PASS: server=%s root=%s output=%s tmux=%s log=%s\n' "$server_host" "$server_root" "$output_root" "$session" "$log"
