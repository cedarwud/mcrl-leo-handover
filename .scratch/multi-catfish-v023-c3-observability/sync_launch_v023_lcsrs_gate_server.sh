#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare a fresh Ubuntu-server checkout for the V0.23 LC-SRS development gate,
# run the server-side preflight/focused tests, and launch the write-once gate
# controller in a unique tmux session.  This wrapper never overwrites a server
# root, a controller, or a tmux session.  It does not run locally, and it does
# not open TEST, perform episode-policy training, or publish a scientific claim.

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
server_host="${V023_SERVER_HOST:-sat}"
server_root="${V023_SERVER_ROOT:-/home/sat/mcrl-v023-lcsrs-gate-20260906-r4}"
session="${V023_TMUX_SESSION:-mcrl-v023-lcsrs-gate-20260906-r4}"
local_python="${V023_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}"
server_python="/home/sat/mcrl-leo-handover/.venv/bin/python"
tle_root="/home/sat/mcrl-runtime/tle-frozen-20260820"
controller="${server_root}/v023_lcsrs_gate_controller.sh"
remote_run="${server_root}/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r4/server-run"
manifest="${repo_root}/.scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.json"
manifest_digest="${repo_root}/.scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.sha256"
preflight="${repo_root}/.scratch/multi-catfish-v023-c3-observability/preflight_v023_lcsrs_observability.py"
prereg="${repo_root}/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
launch_decision="${repo_root}/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md"
launch_decision_sha256="34414bd3d8899e18dcdae139f1b1447be61a626b6f081df1a36f977d07b6924a"
relaunch_decision="${repo_root}/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md"
relaunch_decision_sha256="44fcbdf2f8e4fc2102cca2f722e419016638771404d7a62e180c55965b3f595f"

die() {
  printf 'V023_SERVER_SYNC_ERROR: %s\n' "$*" >&2
  exit 2
}

[[ -d "${repo_root}" && ! -L "${repo_root}" ]] || die "repository root is not a regular directory"
[[ -x "${local_python}" ]] || die "local Python is missing or not executable: ${local_python}"
[[ "${server_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe V023_SERVER_ROOT: ${server_root}"
[[ "${server_root}" != */.. && "${server_root}" != */. ]] || die "unsafe V023_SERVER_ROOT: ${server_root}"
[[ "${session}" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe V023_TMUX_SESSION: ${session}"

cd "${repo_root}"

# Keep this list explicit.  The physical source adapter imports the audited
# V0.20/V0.18/V0.15/V0.13 closure and the repriced Q1/Q2 receipts; copying a
# broad repository or relying on an already existing server checkout would
# make the server result non-reproducible.
sync_paths=(
  pyproject.toml
  src
  scripts
  artifacts/PREREG-FROZEN-2026-08-25-R2.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092001.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092002.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092003.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092004.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092005.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092006.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/opening-2026092007.json
  artifacts/multi-catfish-v03-e1-action-shared-supplement-20260901/source-data/receipt.json
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/authority.json
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/authority-seal.json
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/result.json
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/result-seal.json
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/checkpoints/init-2026092101-rung-000010.pt
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/checkpoints/init-2026092102-rung-000010.pt
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1/checkpoints/init-2026092103-rung-000010.pt
  artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/FROZEN-AUTHORITY.json
  artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/contracts/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/source-panel/shards
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/authority.json
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result.json
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result-seal.json
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/checkpoints/init-2026108101-rung-003000.pt
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/checkpoints/init-2026108102-rung-003000.pt
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/checkpoints/init-2026108103-rung-003000.pt
  artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1/contracts/MULTI-CATFISH-MCRL-V015-C3-LEARNED-CONTEXT-ORACLE-PREREG-2026-09-03.md
  docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md
  docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md
  .scratch/c3-v04
  .scratch/zero-energy-c3-v013
  .scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py
  .scratch/multi-catfish-v014-learner/run_v014_learner_gate.py
  .scratch/multi-catfish-v014-learner/run_v014_source_shard.py
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py
  .scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md
  .scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md
  .scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md
  .scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md
  .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py
  .scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_q1_q2.py
  .scratch/multi-catfish-v020-c3-source-audit/q1-repricing/reprice_c1.py
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108001-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108002-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108003-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108004-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108005-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108006-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108007-2026092101/q2_target_bits_repriced.npy
  .scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit
  .scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.json
  .scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.sha256
  .scratch/multi-catfish-v023-c3-observability/preflight_v023_lcsrs_observability.py
  .scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_observability_gate.py
  .scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_full_gate_server.sh
  .scratch/multi-catfish-v023-c3-observability/sync_launch_v023_lcsrs_gate_server.sh
  .scratch/multi-catfish-v023-c3-observability/finalize_v023_lcsrs_gate_server.sh
  .scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_source_server.py
  .scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_fit_server.py
  .scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_composition_server.py
  .scratch/multi-catfish-v023-c3-observability/v023_lcsrs_composition_runtime.py
  .scratch/multi-catfish-v023-c3-observability/v023_lcsrs_source_adapter.py
  .scratch/multi-catfish-v023-c3-observability/v023_lcsrs_fit_adapter.py
  .scratch/multi-catfish-v023-c3-observability/v023_lcsrs_composition_adapter.py
  .scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_scientific.py
  .scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_source_stage.py
  .scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_fit_independent.py
  .scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_final.py
  .scratch/multi-catfish-v023-c3-observability/seal_v023_lcsrs_result_directory.py
  .scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_observability_gate.py
  .scratch/multi-catfish-v023-c3-observability/SOURCE-ARTIFACT-SCHEMA.md
  .scratch/multi-catfish-v023-c3-observability/test_v023_lcsrs_observability_scaffold.py
  .scratch/multi-catfish-v023-c3-observability/test_v023_lcsrs_source_adapter.py
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
)

for relative in "${sync_paths[@]}"; do
  source="${repo_root}/${relative}"
  [[ -e "${source}" && ! -L "${source}" ]] || die "sync dependency is missing or symlinked: ${relative}"
done
[[ "$(sha256sum "${launch_decision}" | awk '{print $1}')" == "${launch_decision_sha256}" ]] \
  || die "launch decision digest drifted"
[[ "$(sha256sum "${relaunch_decision}" | awk '{print $1}')" == "${relaunch_decision_sha256}" ]] \
  || die "R4 relaunch decision digest drifted"

# Authenticate the local inputs before creating anything on the server.
"${local_python}" "${preflight}" \
  --manifest "${manifest}" \
  --manifest-digest "${manifest_digest}" \
  --repo "${repo_root}" \
  --prereg "${prereg}" >/dev/null || die "local V0.23 preflight failed; no server root was created"

ssh "${server_host}" true || die "cannot reach Ubuntu server ${server_host}"
if ssh "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  die "refusing to overwrite ${server_host}:${server_root}"
fi
if ssh "${server_host}" "tmux has-session -t '${session}' 2>/dev/null"; then
  die "refusing to reuse tmux session ${session}"
fi
ssh "${server_host}" "mkdir -- '${server_root}'"

# Do not copy caches or prior run receipts into the fresh checkout.  All paths
# above are relative to the new root; rsync's -R preserves that authority.
rsync -aR \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache/' \
  "${sync_paths[@]}" \
  "${server_host}:${server_root}/"

ssh "${server_host}" \
  "set -euo pipefail; \
   test -x '${server_python}'; \
   test -d '${tle_root}' && test ! -L '${tle_root}'; \
   test \"\$(sha256sum '${server_root}/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md' | awk '{print \$1}')\" = '${launch_decision_sha256}'; \
   test \"\$(sha256sum '${server_root}/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md' | awk '{print \$1}')\" = '${relaunch_decision_sha256}'; \
   test \"\$(readlink -f /home/sat/demo/tle_data/starlink/tle)\" = '${tle_root}'; \
   cd '${server_root}'; \
   export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONUNBUFFERED=1; \
   '${server_python}' '${server_root}/.scratch/multi-catfish-v023-c3-observability/preflight_v023_lcsrs_observability.py' \
     --manifest '${server_root}/.scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.json' \
     --manifest-digest '${server_root}/.scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.sha256' \
     --repo '${server_root}' \
     --prereg '${server_root}/artifacts/PREREG-FROZEN-2026-08-25-R2.json' >/dev/null; \
   bash -n '${server_root}/.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_full_gate_server.sh'; \
   PYTHONDONTWRITEBYTECODE=1 '${server_python}' -m py_compile \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_source_server.py' \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_fit_server.py' \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_composition_server.py' \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/v023_lcsrs_composition_runtime.py' \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_source_stage.py' \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/seal_v023_lcsrs_result_directory.py' \
     '${server_root}/.scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_final.py'; \
   PYTHONDONTWRITEBYTECODE=1 '${server_python}' -m pytest -q \
     .scratch/multi-catfish-v023-c3-observability/test_v023_lcsrs_observability_scaffold.py \
     .scratch/multi-catfish-v023-c3-observability/test_v023_lcsrs_source_adapter.py \
     tests/test_w181_ee_axis_coalition_residual_c3.py \
     tests/test_w182_ee_axis_lcsrs_c3_state.py \
     tests/test_w183_ee_axis_lcsrs_c3_head.py \
     tests/test_w184_ee_axis_lcsrs_c3_encoder.py \
     tests/test_w185_ee_axis_lcsrs_three_route.py \
     tests/test_w186_ee_axis_lcsrs_c3_dataset.py \
     tests/test_w187_ee_axis_lcsrs_c3_learner.py \
     tests/test_w188_ee_axis_lcsrs_c3_placebo.py \
     tests/test_w189_ee_axis_lcsrs_c3_teacher.py \
     tests/test_w190_ee_axis_lcsrs_c3_topology.py \
     tests/test_w191_native_observation_provenance.py \
     tests/test_w192_ee_axis_lcsrs_c3_pipeline.py \
     tests/test_w193_ee_axis_lcsrs_c3_gate_metrics.py \
     tests/test_w194_ee_axis_lcsrs_c3_gate_fit.py \
     tests/test_w195_ee_axis_lcsrs_c3_source_artifact.py \
     tests/test_w196_ee_axis_lcsrs_fit_adapter.py \
     tests/test_w197_ee_axis_lcsrs_composition_adapter.py \
     tests/test_w198_ee_axis_lcsrs_scientific_verifier.py \
     tests/test_w199_ee_axis_lcsrs_fit_independent.py \
     tests/test_w200_ee_axis_lcsrs_composition_runtime.py \
     tests/test_w201_ee_axis_lcsrs_final_verifier.py \
     tests/test_w202_ee_axis_lcsrs_server_launch_glue.py \
     tests/test_w203_ee_axis_lcsrs_source_stage.py \
     tests/test_w204_ee_axis_lcsrs_result_seal.py \
     tests/test_w205_v023_step_result_contract.py"

if ssh "${server_host}" "test -e '${controller}' || test -L '${controller}'"; then
  die "refusing to overwrite remote controller ${controller}"
fi

# The controller is generated only inside the fresh server root.  Its source
# is intentionally not a repository authority binding; the repository gate
# script remains the authenticated implementation.  Completion is published
# only after the final verifier has returned PASS_FINAL_INTEGRITY and a
# write-once receipt manifest has been sealed.
ssh "${server_host}" "umask 077; cat > '${controller}'" <<'REMOTE_CONTROLLER'
#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON="/home/sat/mcrl-leo-handover/.venv/bin/python"
TLE_ROOT="/home/sat/mcrl-runtime/tle-frozen-20260820"
RUN_ROOT="${ROOT}/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r4/server-run"
GATE="${ROOT}/.scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_full_gate_server.sh"
PREREG="${ROOT}/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
CONTRACT_SHA256="1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
MANIFEST="${ROOT}/.scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="${ROOT}/.scratch/multi-catfish-v023-c3-observability/PREFLIGHT-MANIFEST.sha256"
PREFLIGHT_SHA256="$(sha256sum "${MANIFEST}" | awk '{print $1}')"
LAUNCH_DECISION="${ROOT}/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md"
LAUNCH_DECISION_SHA256="34414bd3d8899e18dcdae139f1b1447be61a626b6f081df1a36f977d07b6924a"
RELAUNCH_DECISION="${ROOT}/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md"
RELAUNCH_DECISION_SHA256="44fcbdf2f8e4fc2102cca2f722e419016638771404d7a62e180c55965b3f595f"

export PYTHON OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONUNBUFFERED=1
mkdir -p "${RUN_ROOT}"

write_failed() {
  local status="${1:-1}"
  if [[ ! -e "${RUN_ROOT}/FAILED" && ! -L "${RUN_ROOT}/FAILED" ]]; then
    local temporary
    temporary="$(mktemp "${RUN_ROOT}/.failed.XXXXXX")"
    printf 'status=FAILED\nexit_status=%s\n' "${status}" > "${temporary}"
    if ! ln "${temporary}" "${RUN_ROOT}/FAILED"; then
      rm -f -- "${temporary}"
    else
      rm -f -- "${temporary}"
    fi
  fi
}

on_error() {
  local status=$?
  trap - ERR
  write_failed "${status}"
  exit "${status}"
}

trap on_error ERR

[[ -f "${LAUNCH_DECISION}" && ! -L "${LAUNCH_DECISION}" ]] || {
  printf 'V023_CONTROLLER_ERROR: launch decision is missing or symlinked\n' >&2
  exit 21
}
[[ "$(sha256sum "${LAUNCH_DECISION}" | awk '{print $1}')" == "${LAUNCH_DECISION_SHA256}" ]] || {
  printf 'V023_CONTROLLER_ERROR: launch decision digest drifted\n' >&2
  exit 22
}
[[ -f "${RELAUNCH_DECISION}" && ! -L "${RELAUNCH_DECISION}" ]] || {
  printf 'V023_CONTROLLER_ERROR: R4 relaunch decision is missing or symlinked\n' >&2
  exit 23
}
[[ "$(sha256sum "${RELAUNCH_DECISION}" | awk '{print $1}')" == "${RELAUNCH_DECISION_SHA256}" ]] || {
  printf 'V023_CONTROLLER_ERROR: R4 relaunch decision digest drifted\n' >&2
  exit 26
}

if bash "${GATE}" \
  --run-root "${RUN_ROOT}" \
  --tle-root "${TLE_ROOT}" \
  --prereg "${PREREG}" \
  --source-jobs 2 \
  --fit-jobs 4 \
  --composition-jobs 2; then
  "${PYTHON}" - "${RUN_ROOT}" "${CONTRACT_SHA256}" "${PREFLIGHT_SHA256}" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "result.json"
manifest = root / "MANIFEST.sha256"
complete = root / "COMPLETE"
for required in (path, manifest, complete):
    if required.is_symlink() or not required.is_file():
        raise SystemExit(f"completion file is missing or symlinked: {required.name}")
listed = set()
for line in manifest.read_text(encoding="ascii").splitlines():
    digest, relative_text = line.split("  ", 1)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise SystemExit("MANIFEST.sha256 contains a malformed digest")
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise SystemExit("MANIFEST.sha256 contains an unsafe path")
    name = relative.as_posix()
    if name in listed:
        raise SystemExit(f"MANIFEST.sha256 repeats a path: {name}")
    target = root / relative
    if target.is_symlink() or not target.is_file():
        raise SystemExit(f"MANIFEST.sha256 names a missing or symlinked file: {name}")
    listed.add(name)
actual = set()
for candidate in root.rglob("*"):
    name = candidate.relative_to(root).as_posix()
    if candidate.is_symlink():
        raise SystemExit(f"result tree contains a symlink: {name}")
    if candidate.is_dir():
        continue
    if not candidate.is_file():
        raise SystemExit(f"result tree contains a special node: {name}")
    if name not in {"MANIFEST.sha256", "COMPLETE"}:
        actual.add(name)
if listed != actual:
    raise SystemExit("MANIFEST.sha256 does not cover the exact result file set")
authority_root = root / "authority"
contract_copy = authority_root / "MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
addendum_copy = authority_root / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
preflight_copy = authority_root / "PREFLIGHT-MANIFEST.json"
preflight_digest_copy = authority_root / "PREFLIGHT-MANIFEST.sha256"
authority_receipt_path = authority_root / "AUTHORITY.json"
for required in (
    contract_copy,
    addendum_copy,
    preflight_copy,
    preflight_digest_copy,
    authority_receipt_path,
):
    if required.is_symlink() or not required.is_file():
        raise SystemExit(f"authority copy is missing or symlinked: {required.name}")
if hashlib.sha256(contract_copy.read_bytes()).hexdigest() != sys.argv[2]:
    raise SystemExit("copied contract digest disagrees")
if hashlib.sha256(addendum_copy.read_bytes()).hexdigest() != "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070":
    raise SystemExit("copied addendum digest disagrees")
if hashlib.sha256(preflight_copy.read_bytes()).hexdigest() != sys.argv[3]:
    raise SystemExit("copied preflight manifest disagrees")
if preflight_digest_copy.read_text(encoding="ascii").split() != [
    sys.argv[3],
    "PREFLIGHT-MANIFEST.json",
]:
    raise SystemExit("copied preflight digest sidecar disagrees")
authority_receipt = json.loads(authority_receipt_path.read_text(encoding="ascii"))
expected_entries = {
    "contract": contract_copy,
    "execution_addendum": addendum_copy,
    "preflight_manifest": preflight_copy,
    "preflight_manifest_digest": preflight_digest_copy,
}
entries = authority_receipt.get("entries")
if not isinstance(entries, dict) or set(entries) != set(expected_entries):
    raise SystemExit("authority receipt entry set disagrees")
for role, authority_path in expected_entries.items():
    entry = entries[role]
    if (
        not isinstance(entry, dict)
        or entry.get("path") != authority_path.relative_to(root).as_posix()
        or entry.get("sha256")
        != hashlib.sha256(authority_path.read_bytes()).hexdigest()
    ):
        raise SystemExit(f"authority receipt binding disagrees for {role}")
payload = json.loads(path.read_text(encoding="ascii"))
if payload.get("contract_sha256") != sys.argv[2]:
    raise SystemExit("result contract hash disagrees")
if payload.get("preflight_manifest_sha256") != sys.argv[3]:
    raise SystemExit("result preflight hash disagrees")
if payload.get("scientific_claim") is not False:
    raise SystemExit("result opened a scientific claim")
if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
    raise SystemExit("result crossed a closed boundary")
full = (
    payload.get("status") == "PASS_FINAL_INTEGRITY"
    and payload.get("integrity_status") == "VERIFIED"
    and (payload.get("source_count"), payload.get("fit_count"), payload.get("composition_count"))
    == (8, 48, 48)
)
insufficient = (
    payload.get("status") == "PASS_SOURCE_STAGE_INTEGRITY"
    and payload.get("integrity_status") == "VERIFIED_SOURCE_ONLY"
    and payload.get("c3_decision") == "INSUFFICIENT_PAIRS"
    and (payload.get("source_count"), payload.get("fit_count"), payload.get("composition_count"))
    == (8, 0, 0)
)
if not (full or insufficient):
    raise SystemExit("result is neither a verified full gate nor a verified insufficient-pairs stop")
manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
if complete.read_text(encoding="ascii").split() != [manifest_digest, "MANIFEST.sha256"]:
    raise SystemExit("COMPLETE does not bind MANIFEST.sha256")
PY
  [[ -f "${RUN_ROOT}/MANIFEST.sha256" && ! -L "${RUN_ROOT}/MANIFEST.sha256" ]] || {
    printf 'V023_CONTROLLER_ERROR: full gate did not publish MANIFEST.sha256\n' >&2
    exit 24
  }
  [[ -f "${RUN_ROOT}/COMPLETE" && ! -L "${RUN_ROOT}/COMPLETE" ]] || {
    printf 'V023_CONTROLLER_ERROR: full gate did not publish COMPLETE\n' >&2
    exit 25
  }
  (
    cd "${RUN_ROOT}"
    sha256sum -c MANIFEST.sha256
  )
  printf 'V023_GATE_COMPLETE: %s\n' "${RUN_ROOT}"
else
  status=$?
  trap - ERR
  write_failed "${status}"
  exit "${status}"
fi
REMOTE_CONTROLLER
ssh "${server_host}" "chmod 700 '${controller}'"

ssh "${server_host}" \
  "tmux new-session -d -s '${session}' \"cd '${server_root}' && exec '${controller}' > '${server_root}/server-controller.log' 2>&1\""

printf 'V023_GATE_LAUNCHED host=%s root=%s run=%s tmux=%s\n' \
  "${server_host}" "${server_root}" "${remote_run}" "${session}"
