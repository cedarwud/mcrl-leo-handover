#!/usr/bin/env bash
set -euo pipefail

# Finalize one completed, isolated R4 server run.  This script is a copier and
# verifier only: it never launches the runner, never edits the frozen source
# closure, and refuses to merge into an existing artifact root.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
server_host="${V018E_SERVER_HOST:-sat}"
server_root="${V018E_SERVER_ROOT:-/home/sat/mcrl-v018-r4-equivalence-20260904-r2}"
artifact_root="${V018E_LOCAL_ARTIFACT_ROOT:-${repo_root}/artifacts/multi-catfish-v018-r4-equivalence-20260904-r1}"
destination="${artifact_root}/server-run-r2"
manifest_expected="${V018E_MANIFEST_SHA256:-0fd88169d63ce02b87534d4f3c0a81559e17df444a2c2c8f556aac3d901382c1}"

manifest_rel=".scratch/multi-catfish-v018-relational-zr/contracts/code-manifest-r4-equivalence.sha256"
contract_rel=".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-R4-SCALE-AWARE-CACHE-EQUIVALENCE-2026-09-04.md"
prereg_receipt_rel=".scratch/multi-catfish-v018-relational-zr/contracts/prereg.sha256"
prereg_rel="artifacts/PREREG-FROZEN-2026-08-25-R2.json"
r1_rel=".scratch/multi-catfish-v018-relational-zr/r1-abort/ee_axis_relational_zr_c3-r1.py"
r2_rel="src/mcrl/runtime/ee_axis_relational_zr_c3.py"
runner_rel=".scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r4_cache_equivalence.py"
sync_rel=".scratch/multi-catfish-v018-relational-zr/perf/sync_v018_r4_equivalence_server.sh"
run_rel=".scratch/multi-catfish-v018-relational-zr/perf/run_v018_r4_equivalence_server.sh"
w178_rel="tests/test_w178_ee_axis_relational_zr_c3_r4_bounds.py"
validator="${repo_root}/.scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r4_equivalence_result.py"
validator_python="${V018E_VALIDATOR_PYTHON:-python3}"

fail_closed() {
  echo "V0.18 R4 equivalence finalize is fail-closed: $*" >&2
  exit 2
}

if [[ ! "${server_host}" =~ ^[A-Za-z0-9_.:@-]+$ ]]; then
  fail_closed "server host contains unsafe characters"
fi
if [[ ! "${server_root}" =~ ^/[A-Za-z0-9._/-]+$ || "${server_root}" == "/" ]]; then
  fail_closed "server root must be a safe non-root absolute path"
fi
if [[ "${artifact_root}" != /* || "${artifact_root}" == "/" || "${artifact_root}" == *..* ]]; then
  fail_closed "local artifact root must be a safe non-root absolute path"
fi
if [[ ! "${manifest_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  fail_closed "manifest digest must be lowercase SHA-256"
fi
if [[ ! "${validator_python}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  fail_closed "validator Python command contains unsafe characters"
fi
if [[ -e "${artifact_root}" || -L "${artifact_root}" ]]; then
  fail_closed "refusing to overwrite existing artifact root ${artifact_root}"
fi

cd "${repo_root}"
for path in "${manifest_rel}" "${contract_rel}" "${prereg_receipt_rel}" \
  "${prereg_rel}" "${r1_rel}" "${r2_rel}" "${runner_rel}" "${sync_rel}" \
  "${run_rel}" "${w178_rel}" "${validator}"; do
  if [[ ! -f "${path}" || -L "${path}" ]]; then
    fail_closed "missing or symlinked local closure file ${path}"
  fi
done
if [[ "$(sha256sum "${manifest_rel}" | awk '{print $1}')" != "${manifest_expected}" ]]; then
  fail_closed "local R4 code-manifest digest mismatch"
fi
sha256sum -c "${manifest_rel}"

# Authenticate the entire synchronized server closure before copying any
# bytes.  The manifest itself is checked against the frozen digest and then
# sha256sum -c verifies every file listed by the frozen R4 code manifest.
remote_files=(
  controller.complete
  result/result.json
  result/receipt.json
  run.log
  server-preflight.log
  server-preflight.receipt
  "${manifest_rel}"
  "${contract_rel}"
  "${prereg_receipt_rel}"
  "${prereg_rel}"
  "${r1_rel}"
  "${r2_rel}"
  "${runner_rel}"
  "${sync_rel}"
  "${run_rel}"
  "${w178_rel}"
)
remote_checks="set -euo pipefail; root='${server_root}';"
for relative in "${remote_files[@]}"; do
  case "${relative}" in
    /*|..|../*|*/../*|*/..) fail_closed "unsafe remote closure path ${relative}";;
  esac
  remote_checks+=" test -f \"\${root}/${relative}\"; test ! -L \"\${root}/${relative}\";"
done
remote_checks+=" test \"\$(sha256sum \"\${root}/${manifest_rel}\" | awk '{print \$1}')\" = '${manifest_expected}';"
remote_checks+=" (cd \"\${root}\"; sha256sum -c '${manifest_rel}');"
remote_checks+=" if pgrep -af '^[^ ]*python[^ ]* .*verify_v018_r4_cache_equivalence.py run' >/dev/null; then echo 'R4 equivalence runner still active' >&2; exit 17; fi;"
ssh "${server_host}" "${remote_checks}"

mapfile -t marker_lines < <(ssh "${server_host}" "cat '${server_root}/controller.complete'")
if [[ "${#marker_lines[@]}" != "3" \
  || "${marker_lines[0]}" != "schema=multi-catfish-mcrl-v018-r4-equivalence-complete-v1" \
  || ! "${marker_lines[1]}" =~ ^exit_status=[0-9]+$ \
  || ! "${marker_lines[2]}" =~ ^workers=[0-9]+$ ]]; then
  fail_closed "remote R4 completion marker is malformed"
fi
exit_status="${marker_lines[1]#exit_status=}"
workers="${marker_lines[2]#workers=}"
if (( workers < 1 || workers > 18 )); then
  fail_closed "remote R4 completion marker has invalid worker count"
fi
if (( exit_status != 0 && exit_status != 1 && exit_status != 2 )); then
  fail_closed "remote R4 completion marker has invalid exit status"
fi

mapfile -t preflight_lines < <(ssh "${server_host}" "cat '${server_root}/server-preflight.receipt'")
if [[ "${#preflight_lines[@]}" != "4" \
  || "${preflight_lines[0]}" != "schema=multi-catfish-mcrl-v018-r4-equivalence-preflight-v1" \
  || "${preflight_lines[1]}" != "manifest_sha256=${manifest_expected}" \
  || "${preflight_lines[2]}" != "pytest_exit=0" \
  || ! "${preflight_lines[3]}" =~ ^log_sha256=[0-9a-f]{64}$ ]]; then
  fail_closed "remote R4 preflight receipt is malformed"
fi
preflight_log_sha="${preflight_lines[3]#log_sha256=}"
remote_preflight_log_sha="$(ssh "${server_host}" "sha256sum '${server_root}/server-preflight.log' | awk '{print \$1}'")"
if [[ "${remote_preflight_log_sha}" != "${preflight_log_sha}" ]]; then
  fail_closed "remote R4 preflight log digest mismatch"
fi

mkdir "${artifact_root}"
mkdir "${destination}" "${destination}/closure"
rsync -a "${server_host}:${server_root}/result" "${destination}/"
rsync -a "${server_host}:${server_root}/controller.complete" "${destination}/"
rsync -a "${server_host}:${server_root}/run.log" "${destination}/"
rsync -a "${server_host}:${server_root}/server-preflight.log" "${destination}/"
rsync -a "${server_host}:${server_root}/server-preflight.receipt" "${destination}/"

# Keep named closure copies beside the result.  The authoritative files remain
# the current checkout; these copies make the exact server run self-auditing.
copy_closure() {
  local relative="$1"
  local name="$2"
  rsync -a "${server_host}:${server_root}/${relative}" "${destination}/closure/${name}"
}
copy_closure "${manifest_rel}" code-manifest-r4-equivalence.sha256
copy_closure "${contract_rel}" MULTI-CATFISH-MCRL-V018-R4-SCALE-AWARE-CACHE-EQUIVALENCE-2026-09-04.md
copy_closure "${prereg_receipt_rel}" prereg.sha256
copy_closure "${prereg_rel}" PREREG-FROZEN-2026-08-25-R2.json
copy_closure "${r1_rel}" ee_axis_relational_zr_c3-r1.py
copy_closure "${r2_rel}" ee_axis_relational_zr_c3.py
copy_closure "${runner_rel}" verify_v018_r4_cache_equivalence.py
copy_closure "${sync_rel}" sync_v018_r4_equivalence_server.sh
copy_closure "${run_rel}" run_v018_r4_equivalence_server.sh
copy_closure "${w178_rel}" test_w178_ee_axis_relational_zr_c3_r4_bounds.py
rsync -a "${validator}" "${destination}/closure/verify_v018_r4_equivalence_result.py"

set +e
"${validator_python}" "${validator}" "${destination}/result" \
  --repo-root "${repo_root}" \
  --contract "${repo_root}/${contract_rel}" \
  --code-manifest "${repo_root}/${manifest_rel}" \
  --code-manifest-sha256 "${manifest_expected}" \
  --preflight-receipt "${destination}/server-preflight.receipt" \
  --preflight-log "${destination}/server-preflight.log" \
  > "${destination}/independent-validation.json"
validation_status=$?
set -e
if (( validation_status != 0 )); then
  fail_closed "independent R4 result validation failed (status ${validation_status})"
fi
if (( exit_status == 0 )); then
  if ! rg -q '"decision": "PASS_R2_CACHE_EQUIVALENCE"' "${destination}/independent-validation.json"; then
    fail_closed "controller success does not match independent PASS decision"
  fi
else
  if ! rg -q '"decision": "STOP_R2_CACHE_EQUIVALENCE"' "${destination}/independent-validation.json"; then
    fail_closed "controller failure does not match independent STOP decision"
  fi
fi

(
  cd "${artifact_root}"
  find server-run-r2 -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > MANIFEST-R2.sha256
)

echo "V0.18 R4 equivalence finalized at ${artifact_root}"
echo "decision receipt: ${destination}/independent-validation.json"
echo "manifest: ${artifact_root}/MANIFEST-R2.sha256"
