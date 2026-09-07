#!/usr/bin/env bash
set -euo pipefail

# Synchronise the immutable V0.18 analytic-diagnostic closure to the Ubuntu
# server.  This script is intentionally a preflight only: it does not start a
# shard, a simulator, or a learner.  The server root is created atomically by
# a plain mkdir after an existence check, so a retry cannot overwrite a prior
# run.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V018R_SERVER_HOST:-sat}"
server_root="${V018R_SERVER_ROOT:-/home/sat/mcrl-v018-relational-zr-20260904-r2}"
python_bin="${V018R_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
run_label="${V018R_RUN_LABEL:-r2}"

# The default closure is the isolated R2 panel.  R1 is retained only as an
# explicit legacy override; it is never selected implicitly.
v018_contract=".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md"
v018_prereg_receipt=".scratch/multi-catfish-v018-relational-zr/contracts/prereg.sha256"
v018_code_receipt="${V018R_CODE_MANIFEST:-.scratch/multi-catfish-v018-relational-zr/contracts/code-manifest-r2-analytic.sha256}"
v018_code_receipt_expected="${V018R_CODE_MANIFEST_SHA256:-}"
performance_addendum="${V018R_PERFORMANCE_ADDENDUM:-.scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-PERFORMANCE-EQUIVALENCE-ADDENDUM-R2-2026-09-04.md}"
performance_addendum_expected="${V018R_PERFORMANCE_ADDENDUM_SHA256:-3175f148adfebbd11c97337bb8872ce9802fb4d7c25ceb00ca9efd934c23ae85}"
r1_abort_receipt="${V018R_R1_ABORT_RECEIPT:-.scratch/multi-catfish-v018-relational-zr/r1-abort/ABORT-RECEIPT.md}"
r1_abort_receipt_expected="${V018R_R1_ABORT_RECEIPT_SHA256:-ff9fdec11e33226a240c8820500a5a8b886478cc5c5746d8901326ae51a804c2}"
r4_artifact_root="${V018R_R4_ARTIFACT_ROOT:-artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/server-run-r2}"
r4_result="${V018R_R4_RESULT:-${r4_artifact_root}/result/result.json}"
r4_result_expected="${V018R_R4_RESULT_SHA256:-23fcc75a3b397e75a9524532448c116788041ffa8d16baffb26b2c480252f20c}"
r4_receipt="${V018R_R4_RECEIPT:-${r4_artifact_root}/result/receipt.json}"
r4_receipt_expected="${V018R_R4_RECEIPT_SHA256:-693db73fd9bcb76fe11e3aad444d102f1232e7ffed0491d722814101e31bfaa3}"
r4_artifact_manifest="${V018R_R4_ARTIFACT_MANIFEST:-artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/MANIFEST-R2.sha256}"
r4_artifact_manifest_expected="${V018R_R4_ARTIFACT_MANIFEST_SHA256:-bc4223967301a5172eb1f996c347ac2794e35a32f7bc80e0bd020e924aab78c8}"
r4_code_manifest="${V018R_R4_CODE_MANIFEST:-${r4_artifact_root}/closure/code-manifest-r4-equivalence.sha256}"
r4_code_manifest_expected="${V018R_R4_CODE_MANIFEST_SHA256:-0fd88169d63ce02b87534d4f3c0a81559e17df444a2c2c8f556aac3d901382c1}"
r4_independent_validation="${V018R_R4_INDEPENDENT_VALIDATION:-${r4_artifact_root}/independent-validation.json}"
r4_independent_validation_expected="${V018R_R4_INDEPENDENT_VALIDATION_SHA256:-8c0515b4cade750c875aa538f05ae12c92b401bf03811524cfec35e33bfd03f4}"
v015_contract_dir="artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1/contracts"
v015_prereg_receipt="${v015_contract_dir}/prereg.sha256"

v018_tests=(
  tests/test_w140_ee_axis_zero_marginal_c3.py
  tests/test_w141_ee_axis_zero_marginal_c3_live.py
  tests/test_w148_ee_axis_v014_q2_state.py
  tests/test_w173_ee_axis_relational_zr_c3.py
  tests/test_w174_ee_axis_v018_gate.py
  tests/test_w175_v018_analytic_diagnostic.py
  tests/test_w176_ee_axis_relational_zr_c3_head.py
  tests/test_w177_ee_axis_relational_zr_c3_performance.py
  tests/test_w178_ee_axis_relational_zr_c3_r4_bounds.py
  tests/test_w179_v018_analytic_r2_provenance.py
)

cd "${repo_root}"

if [[ ! "${server_root}" =~ ^/[A-Za-z0-9._/-]+$ || "${server_root}" == "/" ]]; then
  echo "refusing sync: V018R_SERVER_ROOT must be a non-root absolute path with safe characters" >&2
  exit 2
fi
if [[ ! "${run_label}" =~ ^[A-Za-z0-9_.-]+$ || "${run_label}" == "." || "${run_label}" == ".." ]]; then
  echo "refusing sync: V018R_RUN_LABEL contains unsafe characters" >&2
  exit 2
fi
if [[ "${run_label}" != "r2" && -z "${V018R_SERVER_ROOT:-}" ]]; then
  echo "refusing sync: a non-r2 closure requires an explicit isolated V018R_SERVER_ROOT" >&2
  exit 2
fi
if [[ ! "${python_bin}" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  echo "refusing sync: V018R_PYTHON_BIN must be an absolute path with safe characters" >&2
  exit 2
fi
if [[ ! "${v018_code_receipt}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "refusing sync: V018R_CODE_MANIFEST must be repository-relative with safe characters" >&2
  exit 2
fi
if [[ ! "${v018_code_receipt_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "refusing sync: V018R_CODE_MANIFEST_SHA256 is not lowercase SHA-256" >&2
  exit 2
fi
if [[ -n "${performance_addendum}" && ! "${performance_addendum}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "refusing sync: V018R_PERFORMANCE_ADDENDUM must be repository-relative with safe characters" >&2
  exit 2
fi
if [[ -n "${performance_addendum}" && ! "${performance_addendum_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "refusing sync: V018R_PERFORMANCE_ADDENDUM_SHA256 is required and must be lowercase SHA-256" >&2
  exit 2
fi
if [[ ! "${r1_abort_receipt_expected}" =~ ^[0-9a-f]{64}$ || ! "${r4_result_expected}" =~ ^[0-9a-f]{64}$ || ! "${r4_receipt_expected}" =~ ^[0-9a-f]{64}$ || ! "${r4_artifact_manifest_expected}" =~ ^[0-9a-f]{64}$ || ! "${r4_code_manifest_expected}" =~ ^[0-9a-f]{64}$ || ! "${r4_independent_validation_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "refusing sync: R1/R4 provenance digest is not lowercase SHA-256" >&2
  exit 2
fi
if [[ "$(basename "${v018_code_receipt}")" == "$(basename "${v018_contract}")" || "$(basename "${v018_code_receipt}")" == "$(basename "${v018_prereg_receipt}")" ]]; then
  echo "refusing sync: code-manifest basename collides with the V0.18 contract closure" >&2
  exit 2
fi
for provenance_path in "${performance_addendum}" "${r1_abort_receipt}" "${r4_result}" "${r4_receipt}" "${r4_artifact_manifest}" "${r4_code_manifest}" "${r4_independent_validation}"; do
  case "${provenance_path}" in
    /*|..|../*|*/../*|*/..) echo "refusing sync: provenance path escapes repository: ${provenance_path}" >&2; exit 2;;
  esac
done

resolve_repo_file() {
  local relative="$1"
  if [[ "${relative}" = /* || "${relative}" == *..* ]]; then
    echo "refusing sync: path must be repository-relative without parent traversal: ${relative}" >&2
    exit 2
  fi
  local resolved="${repo_root}/${relative}"
  if [[ ! -f "${resolved}" || -L "${resolved}" ]]; then
    echo "refusing sync: missing or symlinked file ${relative}" >&2
    exit 2
  fi
  printf '%s\n' "${resolved}"
}

v018_contract_file="$(resolve_repo_file "${v018_contract}")"
v018_prereg_file="$(resolve_repo_file "${v018_prereg_receipt}")"
v018_code_file="$(resolve_repo_file "${v018_code_receipt}")"
if [[ -n "${performance_addendum}" ]]; then
  performance_addendum_file="$(resolve_repo_file "${performance_addendum}")"
fi
r1_abort_receipt_file="$(resolve_repo_file "${r1_abort_receipt}")"
r4_result_file="$(resolve_repo_file "${r4_result}")"
r4_receipt_file="$(resolve_repo_file "${r4_receipt}")"
r4_artifact_manifest_file="$(resolve_repo_file "${r4_artifact_manifest}")"
r4_code_manifest_file="$(resolve_repo_file "${r4_code_manifest}")"
r4_independent_validation_file="$(resolve_repo_file "${r4_independent_validation}")"

for path in "${v018_contract_file}" "${v018_prereg_file}" "${v018_code_file}" "${repo_root}/${v015_prereg_receipt}"; do
  if [[ ! -f "${path}" || -L "${path}" ]]; then
    echo "refusing sync: missing or symlinked receipt ${path#${repo_root}/}" >&2
    exit 1
  fi
done
if [[ ! -f "${performance_addendum_file}" || -L "${performance_addendum_file}" || ! -f "${r1_abort_receipt_file}" || -L "${r1_abort_receipt_file}" || ! -f "${r4_result_file}" || -L "${r4_result_file}" || ! -f "${r4_receipt_file}" || -L "${r4_receipt_file}" || ! -f "${r4_artifact_manifest_file}" || -L "${r4_artifact_manifest_file}" || ! -f "${r4_code_manifest_file}" || -L "${r4_code_manifest_file}" || ! -f "${r4_independent_validation_file}" || -L "${r4_independent_validation_file}" ]]; then
  echo "refusing sync: missing or symlinked analytic-R2 provenance file" >&2
  exit 1
fi
for path in "${v018_tests[@]}"; do
  if [[ ! -f "${path}" || -L "${path}" ]]; then
    echo "refusing sync: missing or symlinked focused test ${path}" >&2
    exit 1
  fi
done

# Authenticate both the V0.18 source/code closure and the frozen V0.15
# contract required by the imported learned-Q2 helper before any bytes leave
# this checkout.
(
  cd "$(dirname "${v018_contract_file}")"
  sha256sum -c "$(basename "${v018_prereg_file}")"
  test "$(sha256sum "${v018_code_file}" | awk '{print $1}')" = "${v018_code_receipt_expected}"
  cd "$(dirname "${v018_code_file}")"
  sha256sum -c "$(basename "${v018_code_file}")"
)
(
  cd "${v015_contract_dir}"
  sha256sum -c "$(basename "${v015_prereg_receipt}")"
)
test "$(sha256sum "${performance_addendum_file}" | awk '{print $1}')" = "${performance_addendum_expected}"
test "$(sha256sum "${r1_abort_receipt_file}" | awk '{print $1}')" = "${r1_abort_receipt_expected}"
test "$(sha256sum "${r4_result_file}" | awk '{print $1}')" = "${r4_result_expected}"
test "$(sha256sum "${r4_receipt_file}" | awk '{print $1}')" = "${r4_receipt_expected}"
test "$(sha256sum "${r4_artifact_manifest_file}" | awk '{print $1}')" = "${r4_artifact_manifest_expected}"
test "$(sha256sum "${r4_code_manifest_file}" | awk '{print $1}')" = "${r4_code_manifest_expected}"
test "$(sha256sum "${r4_independent_validation_file}" | awk '{print $1}')" = "${r4_independent_validation_expected}"

if ssh "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  echo "refusing to overwrite existing ${server_host}:${server_root}" >&2
  exit 2
fi

# Do not use mkdir -p here.  If another process wins the race after the
# existence check, mkdir must fail closed instead of adopting that directory.
ssh "${server_host}" "mkdir '${server_root}'"

rsync -aR \
  pyproject.toml \
  src \
  scripts/run_head_pivotality_probe.py \
  "${v018_tests[@]}" \
  .scratch/c3-v04/run_v04_c3_500_update_screen.py \
  .scratch/c3-v04/run_v04_c3_learnability_gate.py \
  .scratch/c3-v04/run_v04_c3_source.py \
  .scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py \
  .scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py \
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py \
  .scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r4_cache_equivalence.py \
  .scratch/multi-catfish-v018-relational-zr/sync_v018_analytic_server.sh \
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_panel_server.sh \
  .scratch/multi-catfish-v018-relational-zr/finalize_v018_analytic_server.sh \
  .scratch/multi-catfish-v018-relational-zr/r1-abort/ABORT-RECEIPT.md \
  .scratch/multi-catfish-v018-relational-zr/r1-abort/ee_axis_relational_zr_c3-r1.py \
  .scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-PERFORMANCE-EQUIVALENCE-ADDENDUM-R2-2026-09-04.md \
  artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/MANIFEST-R2.sha256 \
  artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/server-run-r2/result/result.json \
  artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/server-run-r2/result/receipt.json \
  artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/server-run-r2/independent-validation.json \
  artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/server-run-r2/closure/code-manifest-r4-equivalence.sha256 \
  "${v018_contract}" \
  "${v018_prereg_receipt}" \
  "${v018_code_receipt}" \
  "${v015_contract_dir}" \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 \
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate \
  "${server_host}:${server_root}/"

rsync -aR \
  "${performance_addendum}" \
  "${r1_abort_receipt}" \
  "${r4_result}" \
  "${r4_receipt}" \
  "${r4_artifact_manifest}" \
  "${r4_code_manifest}" \
  "${r4_independent_validation}" \
  "${server_host}:${server_root}/"

# Persist the preflight receipt on the server.  A failing hash or focused test
# leaves this log behind for diagnosis but never allows a panel to start.
focused_tests="${v018_tests[*]}"
ssh "${server_host}" "set -euo pipefail; cd '${server_root}'; exec > server-preflight.log 2>&1; (cd '$(dirname "${v018_prereg_receipt}")'; sha256sum -c '$(basename "${v018_prereg_receipt}")'); test \"\$(sha256sum '${v018_code_receipt}' | awk '{print \$1}')\" = '${v018_code_receipt_expected}'; (cd '$(dirname "${v018_code_receipt}")'; sha256sum -c '$(basename "${v018_code_receipt}")'); test \"\$(sha256sum '${performance_addendum}' | awk '{print \$1}')\" = '${performance_addendum_expected}'; test \"\$(sha256sum '${r1_abort_receipt}' | awk '{print \$1}')\" = '${r1_abort_receipt_expected}'; test \"\$(sha256sum '${r4_result}' | awk '{print \$1}')\" = '${r4_result_expected}'; test \"\$(sha256sum '${r4_receipt}' | awk '{print \$1}')\" = '${r4_receipt_expected}'; test \"\$(sha256sum '${r4_artifact_manifest}' | awk '{print \$1}')\" = '${r4_artifact_manifest_expected}'; test \"\$(sha256sum '${r4_code_manifest}' | awk '{print \$1}')\" = '${r4_code_manifest_expected}'; test \"\$(sha256sum '${r4_independent_validation}' | awk '{print \$1}')\" = '${r4_independent_validation_expected}'; (cd '${v015_contract_dir}'; sha256sum -c '$(basename "${v015_prereg_receipt}")'); env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 '${python_bin}' -m pytest -q ${focused_tests}"

echo "V0.18 analytic closure synced and preflight-tested at ${server_host}:${server_root}"
