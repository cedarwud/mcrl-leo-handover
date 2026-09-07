#!/usr/bin/env bash
set -euo pipefail

dry_run=0
while (($#)); do
  case "$1" in
    --dry-run) dry_run=1 ;;
    *) echo "usage: $0 [--dry-run]" >&2; exit 2 ;;
  esac
  shift
done

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
package_rel=.scratch/multi-catfish-v023-c1c2-successor-stagec-launch
package="$repo_root/$package_rel"
host=${V023_STAGEC_SERVER_HOST:-sat}
checkout=${V023_STAGEC_SERVER_CHECKOUT:-/home/sat/mcrl-v023-c1c2-successor-stagec-20260907-r1-checkout}
seed_checkout=${V023_STAGEC_SERVER_SEED_CHECKOUT:-/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1-checkout}
stage_a=${V023_STAGEA_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-successor-source-training-20260907-100e-r1}
stage_b=${V023_STAGEB_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-successor-stageb-20260907-r1}
stage_c=${V023_STAGEC_OUTPUT_ROOT:-/home/sat/mcrl-v023-c1c2-successor-stagec-20260907-r1}
run_root=${V023_STAGEC_RUN_ROOT:-/home/sat/mcrl-v023-c1c2-successor-stagec-controller-20260907-r1}
python_bin=${V023_STAGEC_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}
check_python=$python_bin
if [[ "$dry_run" == 1 && -z "${V023_STAGEC_PYTHON:-}" ]]; then check_python="$repo_root/.venv/bin/python"; fi
tle_root=${V023_STAGEC_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}
sync_list="$package/V023-C1C2-SUCCESSOR-STAGEC-SYNC-LIST.txt"

die() { echo "STAGEC_PREPARE_ERROR: $*" >&2; exit 2; }
for value in "$checkout" "$seed_checkout" "$stage_a" "$stage_b" "$stage_c" "$run_root" "$tle_root"; do
  [[ "$value" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe server path: $value"
done
[[ "$host" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe server host"
[[ -x "$check_python" ]] || die "python is not executable: $check_python"

export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export PYTHONPATH="$repo_root/src"
if [[ "$dry_run" == 1 ]]; then export TMPDIR=${TMPDIR:-$repo_root/.tmp}; else export TMPDIR=$repo_root/.tmp; fi
mkdir -p "$TMPDIR"
"$check_python" "$package/build_v023_c1c2_successor_stagec_manifest.py" --check >/dev/null

local_commit=$(git -C "$repo_root" rev-parse HEAD)
local_tree=$(git -C "$repo_root" rev-parse 'HEAD^{tree}')
bindings="$checkout/$package_rel/${BINDINGS_NAME:-V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json}"
plan="$run_root/V023-C1C2-SUCCESSOR-9000-WORLD-PLAN.json"
remote_env="PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 PYTHONPATH='${checkout}/src' TMPDIR='${checkout}/.tmp'"
prepare="test -d '${seed_checkout}/.git' && test \"\$(git -C '${seed_checkout}' rev-parse HEAD)\" = '${local_commit}' && test \"\$(git -C '${seed_checkout}' rev-parse 'HEAD^{tree}')\" = '${local_tree}' && test ! -e '${checkout}' && test ! -e '${run_root}' && test ! -e '${stage_a}' && test ! -e '${stage_b}' && test ! -e '${stage_c}' && cp -a '${seed_checkout}' '${checkout}' && mkdir '${run_root}' && mkdir -p '${checkout}/.tmp'"
verify_checkout="test -d '${checkout}/.git' && test \"\$(git -C '${checkout}' rev-parse HEAD)\" = '${local_commit}' && test \"\$(git -C '${checkout}' rev-parse 'HEAD^{tree}')\" = '${local_tree}' && cd '${checkout}' && git diff --quiet --exit-code && ${remote_env} '${python_bin}' '${checkout}/${package_rel}/build_v023_c1c2_successor_stagec_manifest.py' --check"
bind_cmd="cd '${checkout}' && echo 1000 > /proc/self/oom_score_adj && ${remote_env} '${python_bin}' '${checkout}/${package_rel}/bind_v023_c1c2_successor_stagec_freeze.py' --stage-a-output '${stage_a}' --plan-output '${plan}' --stage-b-output '${stage_b}' --stage-c-output '${stage_c}' --tle-root '${tle_root}'"

if [[ "$dry_run" == 1 ]]; then
  echo "DRY_RUN TMPDIR=$TMPDIR"
  echo "DRY_RUN mode=prepare-and-bind-only-no-stage-b-no-stage-c-launch"
  echo "ssh $host $prepare"
  echo "rsync -aR --files-from='$sync_list' '$repo_root/' '$host:$checkout/'"
  echo "ssh $host $verify_checkout"
  echo "ssh $host $bind_cmd"
  echo "BINDINGS=$host:$bindings"
  exit 0
fi

ssh "$host" "$prepare"
rsync -aR --files-from="$sync_list" "$repo_root/" "$host:$checkout/"
ssh "$host" "$verify_checkout"
ssh "$host" "$bind_cmd"
echo "STAGEC_PREPARED_AND_PROSPECTIVELY_BOUND checkout=$host:$checkout bindings=$host:$bindings"
echo "NO_STAGE_B_OR_STAGE_C_PROCESS_LAUNCHED"
