#!/usr/bin/env bash
set -euo pipefail
echo 1000 > /proc/self/oom_score_adj

dry_run=0
case "${1:-}" in
  --dry-run) dry_run=1 ;;
  "") ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 2 ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
package_rel=".scratch/multi-catfish-v023-c1c2-successor-stagec-launch"
package="${repo_root}/${package_rel}"
host="${V023_STAGEC_SERVER_HOST:-sat}"
checkout="${V023_STAGEC_SERVER_CHECKOUT:-/home/sat/mcrl-v023-c1c2-successor-stagec-20260907-r1-checkout}"
seed_checkout="${V023_STAGEC_SERVER_SEED_CHECKOUT:-/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout}"
stage_a="${V023_STAGEA_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1}"
stage_b="${V023_STAGEB_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-successor-stageb-20260907-r1}"
stage_c="${V023_STAGEC_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-successor-stagec-20260907-r1}"
run_root="${V023_STAGEC_RUN_ROOT:-/home/sat/mcrl-v023-c1c2-successor-stagec-controller-20260907-r1}"
session="${V023_STAGEC_TMUX_SESSION:-mcrl-v023-c1c2-successor-stagec-20260907-r1}"
python_bin="${V023_STAGEC_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
tle_root="${V023_STAGEC_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
manifest="${package}/V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256"
pin="${package}/V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST-FROZEN.sha256"
sync_list="${package}/V023-C1C2-SUCCESSOR-STAGEC-SYNC-LIST.txt"

die() { echo "STAGEC_LAUNCH_ERROR: $*" >&2; exit 2; }
for value in "$checkout" "$seed_checkout" "$stage_a" "$stage_b" "$stage_c" "$run_root" "$tle_root"; do
  [[ "$value" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe server path: $value"
done
[[ "$session" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe tmux session"
[[ "$host" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe server host"
[[ -x "$python_bin" ]] || [[ "$dry_run" == 1 ]] || die "python is not executable"

export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 PYTHONPATH="${repo_root}/src" TMPDIR="${repo_root}/.tmp"
mkdir -p "$TMPDIR"
"$python_bin" "$package/build_v023_c1c2_successor_stagec_manifest.py" --check >/dev/null

bindings="${checkout}/${package_rel}/V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json"
plan="${run_root}/V023-C1C2-SUCCESSOR-9000-WORLD-PLAN.json"
preflight_receipt="${run_root}/stagec-preflight.json"
startup_marker="${run_root}/stagec-startup-000100.json"
controller_log="${run_root}/stagec-controller-000100.log"

remote_env="PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 PYTHONPATH='${checkout}/src' TMPDIR='${checkout}/.tmp'"
prepare="test -d '${seed_checkout}' && test ! -L '${seed_checkout}' && test ! -e '${checkout}' && test ! -L '${checkout}' && test ! -e '${run_root}' && test ! -L '${run_root}' && test ! -e '${stage_b}' && test ! -L '${stage_b}' && test ! -e '${stage_c}' && test ! -L '${stage_c}' && ! tmux has-session -t '${session}' 2>/dev/null && mkdir '${checkout}' && cp -a '${seed_checkout}/.' '${checkout}/' && mkdir '${run_root}' && mkdir -p '${checkout}/.tmp'"
bind_cmd="cd '${checkout}' && echo 1000 > /proc/self/oom_score_adj && ${remote_env} '${python_bin}' '${checkout}/${package_rel}/bind_v023_c1c2_successor_stagec_freeze.py' --stage-a-output '${stage_a}' --plan-output '${plan}' --stage-b-output '${stage_b}' --stage-c-output '${stage_c}' --tle-root '${tle_root}'"
preflight_cmd="cd '${checkout}' && echo 1000 > /proc/self/oom_score_adj && ${remote_env} '${python_bin}' '${checkout}/${package_rel}/preflight_v023_c1c2_successor_stagec.py' --bindings '${bindings}' --output '${stage_c}' --receipt '${preflight_receipt}'"
stage_b_cmd="cd '${checkout}' && V023_STAGEC_PYTHON='${python_bin}' '${checkout}/${package_rel}/run_v023_c1c2_successor_stage_b.sh' --bindings '${bindings}' --output '${stage_b}'"
tmux_cmd="cd '${checkout}' && tmux new-session -d -s '${session}' \"cd '${checkout}' && echo 1000 > /proc/self/oom_score_adj && ${remote_env} '${python_bin}' '${checkout}/${package_rel}/run_v023_c1c2_successor_stage_c.py' --bindings '${bindings}' --preflight-receipt '${preflight_receipt}' --stage-b-root '${stage_b}' --output '${stage_c}' --pause-at 100 --startup-marker '${startup_marker}' > '${controller_log}' 2>&1\""

if [[ "$dry_run" == 1 ]]; then
  echo "DRY_RUN sync-list=code-manifest-closure+${package_rel}"
  echo "ssh ${host} ${prepare}"
  echo "rsync -aR --files-from='${sync_list}' '${repo_root}/' '${host}:${checkout}/'"
  echo "ssh ${host} ${bind_cmd}"
  echo "ssh ${host} ${preflight_cmd}"
  echo "ssh ${host} ${stage_b_cmd}"
  echo "ssh ${host} ${tmux_cmd}"
  echo "ssh ${host} wait-up-to-120s-for='${startup_marker}'+tmux-session='${session}'"
  echo "LOG_PATH=${host}:${controller_log}"
  echo "STAGE_B_ROOT=${host}:${stage_b}"
  echo "STAGE_C_ROOT=${host}:${stage_c}"
  exit 0
fi

ssh "$host" "$prepare"
rsync -aR --files-from="$sync_list" "${repo_root}/" "${host}:${checkout}/"
ssh "$host" "$bind_cmd"
ssh "$host" "$preflight_cmd"
ssh "$host" "$stage_b_cmd"
ssh "$host" "$tmux_cmd"

acknowledged=0
for _ in $(seq 1 120); do
  if ssh "$host" "test -f '${startup_marker}' && tmux has-session -t '${session}' 2>/dev/null"; then
    acknowledged=1
    break
  fi
  sleep 1
done
[[ "$acknowledged" == 1 ]] || die "no startup marker plus live tmux acknowledgement within 120 s"
echo "STAGEC_STARTUP_ACKNOWLEDGED marker=${host}:${startup_marker} session=${session}"
echo "LOG_PATH=${host}:${controller_log}"
echo "STAGE_B_ROOT=${host}:${stage_b}"
echo "STAGE_C_ROOT=${host}:${stage_c}"
