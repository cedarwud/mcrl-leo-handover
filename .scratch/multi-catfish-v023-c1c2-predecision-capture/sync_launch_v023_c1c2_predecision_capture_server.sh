#!/usr/bin/env bash
set -Eeuo pipefail

# Sync the authenticated source closure to a fresh Ubuntu server root, run
# cheap server-side checks, and start the bounded controller in a new tmux
# session.  This is scaffolding only; it is intentionally not invoked by the
# local implementation/tests.  It never reuses a root or tmux session.

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
server_host="sat"
server_root="/home/sat/mcrl-v023-c1c2-predecision-20260906-r4"
tmux_session="mcrl-v023-c1c2-predecision-20260906-r4"
server_python="/home/sat/mcrl-leo-handover/.venv/bin/python"
tle_root="/home/sat/mcrl-runtime/tle-frozen-20260820"
output_root="${server_root}/capture-run"
controller_log="${server_root}/controller.log"
dry_run=0

usage() {
  cat <<'EOF'
Usage:
  sync_launch_v023_c1c2_predecision_capture_server.sh [options]

Options:
  --server-host HOST       Ubuntu SSH host (default: sat)
  --server-root PATH       fresh absolute server checkout root
  --tmux-session NAME      new tmux session name
  --server-python PATH     server Python executable
  --tle-root PATH          frozen external TRAIN TLE root
  --output-root PATH       fresh controller output root
  --dry-run                validate local closure and print the remote plan
  -h, --help               show this help

The command performs no local simulator, learner, evaluation, TEST, or
training work.  A real invocation creates a fresh server root and starts the
TRAIN-only controller only after server-side checks pass.
EOF
}

die() {
  printf 'V023_C1C2_SYNC_ERROR: %s\n' "$*" >&2
  exit 2
}

is_clean_absolute_path() {
  local value="$1"
  [[ "${value}" =~ ^/[A-Za-z0-9._/-]+$ ]] || return 1
  [[ "${value}" != *"//"* ]] || return 1
  [[ "${value}" != */./* && "${value}" != */../* && "${value}" != */. && "${value}" != */.. ]] || return 1
}

while (($#)); do
  case "$1" in
    --server-host)
      (($# >= 2)) || die "--server-host needs a value"
      server_host="$2"
      shift 2
      ;;
    --server-root)
      (($# >= 2)) || die "--server-root needs a value"
      server_root="$2"
      shift 2
      ;;
    --tmux-session)
      (($# >= 2)) || die "--tmux-session needs a value"
      tmux_session="$2"
      shift 2
      ;;
    --server-python)
      (($# >= 2)) || die "--server-python needs a value"
      server_python="$2"
      shift 2
      ;;
    --tle-root)
      (($# >= 2)) || die "--tle-root needs a value"
      tle_root="$2"
      shift 2
      ;;
    --output-root)
      (($# >= 2)) || die "--output-root needs a value"
      output_root="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -d "${repo_root}" && ! -L "${repo_root}" ]] || die "repository root is not a directory"
[[ "${server_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe server root: ${server_root}"
is_clean_absolute_path "${server_root}" || die "server root must be a clean absolute path: ${server_root}"
is_clean_absolute_path "${output_root}" || die "output root must be a clean absolute path: ${output_root}"
is_clean_absolute_path "${tle_root}" || die "TLE root must be a clean absolute path: ${tle_root}"
is_clean_absolute_path "${server_python}" || die "server Python must be a clean absolute path: ${server_python}"
case "${output_root}" in
  "${server_root}"/*) ;;
  *) die "output root must be below the fresh server root: ${output_root}" ;;
esac
[[ "${tmux_session}" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe tmux session name"

cd -- "${repo_root}"

# These directories are closure roots, not a broad authority reset.  The
# source adapter's authenticated V0.20/V0.18/V0.15/V0.13 imports and frozen
# Q1/Q2 receipts live below them.  The controller's CODE-MANIFEST then checks
# the exact byte-addressed files inside this copied closure.
sync_paths=(
  pyproject.toml
  src
  scripts
  docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R6-FIT-BINDING-2026-09-06.md
  artifacts/PREREG-FROZEN-2026-08-25-R2.json
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1
  artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1
  artifacts/multi-catfish-v014-learnability-20260903-r1
  artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1
  .scratch/c3-v04
  .scratch/zero-energy-c3-v013
  .scratch/multi-catfish-v014-learner
  .scratch/multi-catfish-v015-c3-learned-context
  .scratch/multi-catfish-v018-relational-zr
  .scratch/multi-catfish-v020-c3-source-audit
  .scratch/multi-catfish-v023-c1c2-predecision-capture
  .scratch/multi-catfish-v023-c1c2-neutral-materialization
  .scratch/multi-catfish-v023-c1c2-neutral-adapters
  .scratch/multi-catfish-v023-r6-fit-binding-fix
  tests/test_w181_ee_axis_coalition_residual_c3.py
  tests/test_w182_ee_axis_lcsrs_c3_state.py
  tests/test_w183_ee_axis_lcsrs_c3_head.py
  tests/test_w184_ee_axis_lcsrs_c3_encoder.py
  tests/test_w185_ee_axis_lcsrs_three_route.py
  tests/test_w186_ee_axis_lcsrs_c3_dataset.py
  tests/test_w187_ee_axis_lcsrs_c3_learner.py
  tests/test_w188_ee_axis_lcsrs_c3_placebo.py
  tests/test_w189_ee_axis_lcsrs_c3_teacher.py
  tests/test_w190_ee_axis_lcsrs_c3_topology.py
  tests/test_w191_native_observation_provenance.py
  tests/test_w192_ee_axis_lcsrs_c3_pipeline.py
  tests/test_w193_ee_axis_lcsrs_c3_gate_metrics.py
  tests/test_w194_ee_axis_lcsrs_c3_gate_fit.py
  tests/test_w195_ee_axis_lcsrs_c3_source_artifact.py
  tests/test_w196_ee_axis_lcsrs_fit_adapter.py
  tests/test_w197_ee_axis_lcsrs_composition_adapter.py
  tests/test_w198_ee_axis_lcsrs_scientific_verifier.py
  tests/test_w199_ee_axis_lcsrs_fit_independent.py
  tests/test_w200_ee_axis_lcsrs_composition_runtime.py
  tests/test_w201_ee_axis_lcsrs_final_verifier.py
  tests/test_w202_ee_axis_lcsrs_server_launch_glue.py
  tests/test_w203_ee_axis_lcsrs_source_stage.py
  tests/test_w204_ee_axis_lcsrs_result_seal.py
  tests/test_w205_v023_step_result_contract.py
  tests/test_w47_ee_axis_c1_selector.py
)

for relative in "${sync_paths[@]}"; do
  [[ -e "${repo_root}/${relative}" && ! -L "${repo_root}/${relative}" ]] \
    || die "sync dependency is missing or symlinked: ${relative}"
done

manifest="${repo_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/CODE-MANIFEST.json"
preflight="${repo_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/preflight_v023_c1c2_predecision.py"
code_manifest_sha256="$(sha256sum "${manifest}" | awk '{print $1}')"
[[ "${code_manifest_sha256}" =~ ^[0-9a-f]{64}$ ]] || die "code manifest digest is malformed"

# Authenticate the local code closure before opening an SSH/server boundary.
"${V023_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}" "${preflight}" \
  --manifest "${manifest}" \
  --code-manifest-sha256 "${code_manifest_sha256}" \
  --repo "${repo_root}" >/dev/null \
  || die "local predecision preflight failed; no server root was created"

if ((dry_run)); then
  printf 'V023_C1C2_SYNC_DRY_RUN_PASS\n'
  printf 'server=%s\nroot=%s\ntmux=%s\noutput=%s\ncontroller_log=%s\ncode_manifest_sha256=%s\n' \
    "${server_host}" "${server_root}" "${tmux_session}" "${output_root}" "${controller_log}" "${code_manifest_sha256}"
  exit 0
fi

if ssh -- "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  die "refusing to overwrite remote server root: ${server_host}:${server_root}"
else
  root_status=$?
  [[ "${root_status}" -eq 1 ]] || die "could not inspect remote server root (ssh status ${root_status})"
fi
if ssh -- "${server_host}" "tmux has-session -t '${tmux_session}' 2>/dev/null"; then
  die "refusing to reuse tmux session: ${tmux_session}"
else
  tmux_status=$?
  [[ "${tmux_status}" -eq 1 ]] || die "could not inspect remote tmux session (ssh status ${tmux_status})"
fi
ssh -- "${server_host}" "mkdir -- '${server_root}'"

# Preserve relative paths and omit bytecode/cache noise.  The destination was
# proven fresh above; there is no --delete and no overwrite recovery path.
rsync -aR \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache/' \
  "${sync_paths[@]}" \
  "${server_host}:${server_root}/"

controller="${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/run_v023_c1c2_predecision_capture_controller.py"
remote_manifest="${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/CODE-MANIFEST.json"
remote_preflight="${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/preflight_v023_c1c2_predecision.py"
ssh -- "${server_host}" \
  "set -Eeuo pipefail; \
   test -x '${server_python}'; \
   test -d '${tle_root}' && test ! -L '${tle_root}'; \
   '${server_python}' '${remote_preflight}' \
     --manifest '${remote_manifest}' \
     --code-manifest-sha256 '${code_manifest_sha256}' \
     --repo '${server_root}' >/dev/null; \
   PYTHONDONTWRITEBYTECODE=1 '${server_python}' -m py_compile \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/preflight_v023_c1c2_predecision.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/run_v023_c1c2_predecision_capture_controller.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/run_v023_c1c2_predecision_capture_server.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/merge_v023_c1c2_predecision_captures.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/v023_c1c2_predecision_capture.py'; \
   bash -n '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/sync_launch_v023_c1c2_predecision_capture_server.sh'; \
   PYTHONDONTWRITEBYTECODE=1 '${server_python}' -m pytest -q \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/test_v023_c1c2_predecision_capture.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-predecision-capture/test_v023_c1c2_predecision_infrastructure.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-neutral-materialization/test_materialize_v023_c1c2.py' \
     '${server_root}/.scratch/multi-catfish-v023-c1c2-neutral-adapters/test_v023_c1c2_neutral_adapters.py' \
     '${server_root}/tests/test_w47_ee_axis_c1_selector.py'; \
   test ! -e '${controller_log}' && test ! -L '${controller_log}'; \
   : > '${controller_log}'; \
   tmux new-session -d -s '${tmux_session}' \
     \"cd '${server_root}' && exec '${server_python}' '${controller}' \
       --repo '${server_root}' \
       --python '${server_python}' \
       --tle-root '${tle_root}' \
       --output-root '${output_root}' \
       --code-manifest '${remote_manifest}' \
       --code-manifest-sha256 '${code_manifest_sha256}' \
       >> '${controller_log}' 2>&1\"; \
   liveness=0; \
   output_status=pending; \
   for attempt in 1 2 3 4 5 6 7 8 9 10; do \
     pane_dead=\"\$(tmux list-panes -t '${tmux_session}:0.0' -F '#{pane_dead}' 2>/dev/null || true)\"; \
     if tmux has-session -t '${tmux_session}' 2>/dev/null && test \"\$pane_dead\" = 0; then \
       liveness=1; \
       if test -d '${output_root}' && test ! -L '${output_root}'; then output_status=present; fi; \
       break; \
     fi; \
     sleep 1; \
   done; \
   if test \"\$liveness\" -ne 1; then \
     printf 'V023_C1C2_SYNC_LAUNCH_ERROR: controller did not survive 10s liveness window; log=%s\\n' '${controller_log}' >&2; \
     tail -n 100 '${controller_log}' >&2 || true; \
     exit 1; \
   fi; \
   printf 'V023_C1C2_CONTROLLER_LIVE: session=%s output=%s log=%s\\n' '${tmux_session}' \"\$output_status\" '${controller_log}'"

printf 'V023_C1C2_SYNC_LAUNCH_PASS: server=%s root=%s tmux=%s log=%s\n' \
  "${server_host}" "${server_root}" "${tmux_session}" "${controller_log}"
