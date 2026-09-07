#!/usr/bin/env bash
set -euo pipefail

# Copy one completed V0.18 server panel into a new local artifact root.  The
# source server root and local artifact root are both immutable boundaries:
# this command refuses to merge into either an existing run or an existing
# artifact directory.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_host="${V018R_SERVER_HOST:-sat}"
server_root="${V018R_SERVER_ROOT:-/home/sat/mcrl-v018-relational-zr-20260904-r2}"
# The default finalizer targets the isolated R2 panel.  R1 is retained only as
# an explicit legacy override; V018R_LOCAL_ARTIFACT_ROOT may override the
# derived local root explicitly.
run_label="${V018R_RUN_LABEL:-r2}"
if [[ -n "${V018R_LOCAL_ARTIFACT_ROOT:-}" ]]; then
  artifact_root="${V018R_LOCAL_ARTIFACT_ROOT}"
elif [[ "${run_label}" == "r2" ]]; then
  artifact_root="${repo_root}/artifacts/multi-catfish-v018-relational-zr-20260904-r2"
else
  artifact_root="${repo_root}/artifacts/multi-catfish-v018-relational-zr-20260904-${run_label}"
fi
if [[ "${artifact_root}" != /* ]]; then
  artifact_root="${repo_root}/${artifact_root}"
fi
if [[ "${run_label}" == "r1" ]]; then
  run_dir="${server_root}/analytic-panel"
else
  run_dir="${server_root}/analytic-panel-${run_label}"
fi
destination="${artifact_root}/server-run-${run_label}"
contract_path=".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md"
v018_prereg_path=".scratch/multi-catfish-v018-relational-zr/contracts/prereg.sha256"
code_manifest_path="${V018R_CODE_MANIFEST:-.scratch/multi-catfish-v018-relational-zr/contracts/code-manifest-r2-analytic.sha256}"
code_manifest_expected="${V018R_CODE_MANIFEST_SHA256:-}"
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

fail_closed() {
  echo "V0.18 analytic panel finalize is fail-closed: $*" >&2
  exit 2
}

if [[ ! "${server_root}" =~ ^/[A-Za-z0-9._/-]+$ || "${server_root}" == "/" ]]; then
  fail_closed "V018R_SERVER_ROOT must be a non-root absolute path with safe characters"
fi
if [[ ! "${run_label}" =~ ^[A-Za-z0-9_.-]+$ || "${run_label}" == "." || "${run_label}" == ".." ]]; then
  fail_closed "V018R_RUN_LABEL contains unsafe characters"
fi
if [[ "${run_label}" != "r2" && -z "${V018R_SERVER_ROOT:-}" ]]; then
  fail_closed "a non-r2 panel requires an explicit isolated V018R_SERVER_ROOT"
fi
if [[ ! "${code_manifest_path}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  fail_closed "V018R_CODE_MANIFEST must be repository-relative with safe characters"
fi
if [[ ! "${code_manifest_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  fail_closed "V018R_CODE_MANIFEST_SHA256 is not lowercase SHA-256"
fi
if [[ -n "${performance_addendum}" && ! "${performance_addendum}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  fail_closed "V018R_PERFORMANCE_ADDENDUM must be repository-relative with safe characters"
fi
if [[ -n "${performance_addendum}" && ! "${performance_addendum_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  fail_closed "V018R_PERFORMANCE_ADDENDUM_SHA256 is required and must be lowercase SHA-256"
fi
for digest in "${r1_abort_receipt_expected}" "${r4_result_expected}" "${r4_receipt_expected}" "${r4_artifact_manifest_expected}" "${r4_code_manifest_expected}" "${r4_independent_validation_expected}"; do
  if [[ ! "${digest}" =~ ^[0-9a-f]{64}$ ]]; then
    fail_closed "R1/R4 provenance digest is not lowercase SHA-256"
  fi
done
for path in "${contract_path}" "${v018_prereg_path}" "${code_manifest_path}"; do
  case "${path}" in
    /*|..|../*|*/../*|*/..)
      fail_closed "repository path escapes the synchronized root: ${path}"
      ;;
  esac
done
for provenance_path in "${performance_addendum}" "${r1_abort_receipt}" "${r4_result}" "${r4_receipt}" "${r4_artifact_manifest}" "${r4_code_manifest}" "${r4_independent_validation}"; do
  case "${provenance_path}" in
    /*|..|../*|*/../*|*/..) fail_closed "provenance path escapes the synchronized root: ${provenance_path}";;
  esac
done
if [[ "$(basename "${code_manifest_path}")" == "$(basename "${contract_path}")" || "$(basename "${code_manifest_path}")" == "$(basename "${v018_prereg_path}")" ]]; then
  fail_closed "code-manifest basename collides with the V0.18 contract closure"
fi
if [[ -n "${performance_addendum}" && ( "$(basename "${performance_addendum}")" == "$(basename "${contract_path}")" || "$(basename "${performance_addendum}")" == "$(basename "${v018_prereg_path}")" || "$(basename "${performance_addendum}")" == "$(basename "${code_manifest_path}")" ) ]]; then
  fail_closed "performance addendum basename collides with the V0.18 contract closure"
fi
if [[ "${artifact_root}" != /* || "${artifact_root}" == "/" || "${artifact_root}" == *..* ]]; then
  fail_closed "local artifact root must be a non-root absolute path without parent traversal"
fi

if [[ -e "${artifact_root}" || -L "${artifact_root}" ]]; then
  fail_closed "refusing to overwrite existing local V0.18 artifact root ${artifact_root}"
fi

cd "${repo_root}"

# Authenticate the local copy source as well as the remote closure.  This
# prevents a local checkout mutation between sync and finalize from being
# recorded beside an otherwise valid server result.
test -f "${contract_path}" && test ! -L "${contract_path}"
test -f "${v018_prereg_path}" && test ! -L "${v018_prereg_path}"
(
  cd "$(dirname "${v018_prereg_path}")"
  sha256sum -c "$(basename "${v018_prereg_path}")"
)
test -f "${code_manifest_path}" && test ! -L "${code_manifest_path}"
test "$(sha256sum "${code_manifest_path}" | awk '{print $1}')" = "${code_manifest_expected}"
(
  cd "$(dirname "${code_manifest_path}")"
  sha256sum -c "$(basename "${code_manifest_path}")"
)
if [[ -n "${performance_addendum}" ]]; then
  test -f "${performance_addendum}" && test ! -L "${performance_addendum}"
  test "$(sha256sum "${performance_addendum}" | awk '{print $1}')" = "${performance_addendum_expected}"
fi
for provenance_file in "${r1_abort_receipt}" "${r4_result}" "${r4_receipt}" "${r4_artifact_manifest}" "${r4_code_manifest}" "${r4_independent_validation}"; do
  test -f "${provenance_file}" && test ! -L "${provenance_file}"
done
test "$(sha256sum "${r1_abort_receipt}" | awk '{print $1}')" = "${r1_abort_receipt_expected}"
test "$(sha256sum "${r4_result}" | awk '{print $1}')" = "${r4_result_expected}"
test "$(sha256sum "${r4_receipt}" | awk '{print $1}')" = "${r4_receipt_expected}"
test "$(sha256sum "${r4_artifact_manifest}" | awk '{print $1}')" = "${r4_artifact_manifest_expected}"
test "$(sha256sum "${r4_code_manifest}" | awk '{print $1}')" = "${r4_code_manifest_expected}"
test "$(sha256sum "${r4_independent_validation}" | awk '{print $1}')" = "${r4_independent_validation_expected}"

ssh "${server_host}" "test -f '${run_dir}/controller.complete' && test ! -L '${run_dir}/controller.complete' && test -f '${run_dir}/merged/result.json' && test ! -L '${run_dir}/merged/result.json' && test -f '${run_dir}/merged/result-seal.json' && test ! -L '${run_dir}/merged/result-seal.json' && test -f '${server_root}/server-preflight.log' && test ! -L '${server_root}/server-preflight.log' && test -f '${server_root}/${performance_addendum}' && test ! -L '${server_root}/${performance_addendum}' && test -f '${server_root}/${r1_abort_receipt}' && test ! -L '${server_root}/${r1_abort_receipt}' && test -f '${server_root}/${r4_result}' && test ! -L '${server_root}/${r4_result}' && test -f '${server_root}/${r4_receipt}' && test ! -L '${server_root}/${r4_receipt}' && test -f '${server_root}/${r4_artifact_manifest}' && test ! -L '${server_root}/${r4_artifact_manifest}' && test -f '${server_root}/${r4_code_manifest}' && test ! -L '${server_root}/${r4_code_manifest}' && test -f '${server_root}/${r4_independent_validation}' && test ! -L '${server_root}/${r4_independent_validation}'"

mapfile -t marker_lines < <(ssh "${server_host}" "cat '${run_dir}/controller.complete'")
if [[ "${#marker_lines[@]}" != "3" \
  || "${marker_lines[0]}" != "schema=multi-catfish-mcrl-v018-analytic-panel-complete-v1" \
  || "${marker_lines[1]}" != "task_count=36" \
  || "${marker_lines[2]}" != max_parallel=* ]]; then
  echo "V0.18 controller completion marker is malformed" >&2
  exit 3
fi
marker_max_parallel="${marker_lines[2]#max_parallel=}"
if [[ ! "${marker_max_parallel}" =~ ^[0-9]+$ ]] \
  || (( marker_max_parallel < 1 || marker_max_parallel > 18 )); then
  echo "V0.18 completion marker has invalid max_parallel" >&2
  exit 4
fi
if [[ -n "${V018R_MAX_PARALLEL:-}" && "${marker_max_parallel}" != "${V018R_MAX_PARALLEL}" ]]; then
  echo "V0.18 completion marker max_parallel disagrees with requested setting" >&2
  exit 5
fi

# Re-authenticate the exact configured closure immediately before copying the
# result.  The addendum and R1/R4 files are immutable provenance receipts; this
# wrapper deliberately does not change their contents or status.
ssh "${server_host}" "set -euo pipefail; cd '${server_root}'; test -f '${contract_path}' && test ! -L '${contract_path}'; (cd '$(dirname "${v018_prereg_path}")'; sha256sum -c '$(basename "${v018_prereg_path}")'); test -f '${code_manifest_path}' && test ! -L '${code_manifest_path}'; test \"\$(sha256sum '${code_manifest_path}' | awk '{print \$1}')\" = '${code_manifest_expected}'; (cd '$(dirname "${code_manifest_path}")'; sha256sum -c '$(basename "${code_manifest_path}")'); test \"\$(sha256sum '${performance_addendum}' | awk '{print \$1}')\" = '${performance_addendum_expected}'; test \"\$(sha256sum '${r1_abort_receipt}' | awk '{print \$1}')\" = '${r1_abort_receipt_expected}'; test \"\$(sha256sum '${r4_result}' | awk '{print \$1}')\" = '${r4_result_expected}'; test \"\$(sha256sum '${r4_receipt}' | awk '{print \$1}')\" = '${r4_receipt_expected}'; test \"\$(sha256sum '${r4_artifact_manifest}' | awk '{print \$1}')\" = '${r4_artifact_manifest_expected}'; test \"\$(sha256sum '${r4_code_manifest}' | awk '{print \$1}')\" = '${r4_code_manifest_expected}'; test \"\$(sha256sum '${r4_independent_validation}' | awk '{print \$1}')\" = '${r4_independent_validation_expected}'; if [[ '${run_label}' != 'r1' ]]; then test ! -e '${server_root}/analytic-panel' && test ! -L '${server_root}/analytic-panel'; test ! -e '${server_root}/analytic-panel-r1' && test ! -L '${server_root}/analytic-panel-r1'; fi"

mkdir "${artifact_root}"
mkdir "${artifact_root}/contracts" "${artifact_root}/contracts/v015"
mkdir "${destination}"

# Preserve the exact configured V0.18 contract, prereg receipt, code-manifest
# receipt, and optional performance addendum alongside the server result.  The
# original source locations remain the verification authority; these are
# immutable final-artifact copies.  Explicit files prevent a future R2
# closure from silently inheriting an R1 receipt with a different label.
rsync -a \
  "${repo_root}/${contract_path}" \
  "${repo_root}/${v018_prereg_path}" \
  "${repo_root}/${code_manifest_path}" \
  "${artifact_root}/contracts/"
rsync -a \
  "${repo_root}/${performance_addendum}" \
  "${repo_root}/${r1_abort_receipt}" \
  "${repo_root}/${r4_result}" \
  "${repo_root}/${r4_receipt}" \
  "${repo_root}/${r4_artifact_manifest}" \
  "${repo_root}/${r4_code_manifest}" \
  "${repo_root}/${r4_independent_validation}" \
  "${artifact_root}/contracts/"
rsync -a \
  "${repo_root}/${v015_contract_dir}/" \
  "${artifact_root}/contracts/v015/"
rsync -a "${server_host}:${run_dir}" "${destination}/"
rsync -a "${server_host}:${server_root}/server-preflight.log" "${destination}/"

panel_name="analytic-panel"
if [[ "${run_label}" != "r1" ]]; then
  panel_name="analytic-panel-${run_label}"
fi
if [[ ! -d "${destination}/${panel_name}" || -L "${destination}/${panel_name}" ]]; then
  fail_closed "final artifact is missing copied analytic panel ${panel_name}"
fi

for required in "${contract_path}" "${v018_prereg_path}" "${code_manifest_path}" "${performance_addendum}" "${r1_abort_receipt}" "${r4_result}" "${r4_receipt}" "${r4_artifact_manifest}" "${r4_code_manifest}" "${r4_independent_validation}"; do
  copied="${artifact_root}/contracts/$(basename "${required}")"
  if [[ ! -f "${copied}" || -L "${copied}" ]]; then
    fail_closed "final artifact is missing copied V0.18 closure file ${required}"
  fi
done
test "$(sha256sum "${artifact_root}/contracts/$(basename "${code_manifest_path}")" | awk '{print $1}')" = "${code_manifest_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${performance_addendum}")" | awk '{print $1}')" = "${performance_addendum_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${r1_abort_receipt}")" | awk '{print $1}')" = "${r1_abort_receipt_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${r4_result}")" | awk '{print $1}')" = "${r4_result_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${r4_receipt}")" | awk '{print $1}')" = "${r4_receipt_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${r4_artifact_manifest}")" | awk '{print $1}')" = "${r4_artifact_manifest_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${r4_code_manifest}")" | awk '{print $1}')" = "${r4_code_manifest_expected}"
test "$(sha256sum "${artifact_root}/contracts/$(basename "${r4_independent_validation}")" | awk '{print $1}')" = "${r4_independent_validation_expected}"

manifest_path="${artifact_root}/MANIFEST-R1.sha256"
if [[ "${run_label}" != "r1" ]]; then
  manifest_path="${artifact_root}/MANIFEST-${run_label}.sha256"
fi
(
  cd "${artifact_root}"
  find contracts "server-run-${run_label}" -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > "${manifest_path}"
)

echo "V0.18 analytic panel finalized at ${artifact_root}"
echo "manifest: ${manifest_path}"
