#!/usr/bin/env bash
set -euo pipefail

# Copy one completed R3 equivalence check from its isolated server root into a
# new immutable local artifact root.  This is intentionally a finalizer only:
# it never starts the runner and never edits the frozen contract or manifest.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
server_host="${V018E_SERVER_HOST:-sat}"
server_root="${V018E_SERVER_ROOT:-/home/sat/mcrl-v018-r2-equivalence-20260904-r3}"
artifact_root="${V018E_LOCAL_ARTIFACT_ROOT:-${repo_root}/artifacts/multi-catfish-v018-r3-equivalence-20260904-r1}"
destination="${artifact_root}/server-run-r3"

manifest_rel=".scratch/multi-catfish-v018-relational-zr/contracts/code-manifest-r2-equivalence.sha256"
manifest_expected="${V018E_MANIFEST_SHA256:?V018E_MANIFEST_SHA256 is required}"
contract_rel=".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-R3-CACHE-EQUIVALENCE-CHECK-2026-09-04.md"
prereg_receipt_rel=".scratch/multi-catfish-v018-relational-zr/contracts/prereg.sha256"
prereg_rel="artifacts/PREREG-FROZEN-2026-08-25-R2.json"
r1_rel=".scratch/multi-catfish-v018-relational-zr/r1-abort/ee_axis_relational_zr_c3-r1.py"
r2_rel="src/mcrl/runtime/ee_axis_relational_zr_c3.py"
runner_rel=".scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r2_cache_equivalence.py"
validator="${repo_root}/.scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r2_equivalence_result.py"
validator_python="${V018E_VALIDATOR_PYTHON:-python3}"

fail_closed() {
  echo "V0.18 R2 equivalence finalize is fail-closed: $*" >&2
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
if [[ ! -f "${manifest_rel}" || -L "${manifest_rel}" ]]; then
  fail_closed "local R2 code manifest is missing or symlinked"
fi
if [[ "$(sha256sum "${manifest_rel}" | awk '{print $1}')" != "${manifest_expected}" ]]; then
  fail_closed "local R2 code manifest digest mismatch"
fi
sha256sum -c "${manifest_rel}"
if [[ ! -f "${validator}" || -L "${validator}" ]]; then
  fail_closed "independent result validator is missing or symlinked"
fi

# Authenticate the isolated R3 server root before copying any bytes.  Every
# required item is checked as a regular non-symlink file; sha256sum -c also
# authenticates the complete synchronized code closure, not only the four
# hashes carried in result.json.
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
)
remote_checks="set -euo pipefail; root='${server_root}';"
for relative in "${remote_files[@]}"; do
  case "${relative}" in
    /*|..|../*|*/../*|*/..) fail_closed "unsafe remote closure path ${relative}";;
  esac
  remote_checks+=" test -f \"\${root}/${relative}\"; test ! -L \"\${root}/${relative}\";"
done
remote_checks+=" test \"\$(sha256sum \"\${root}/${manifest_rel}\" | awk '{print \$1}')\" = '${manifest_expected}';"
remote_checks+=" (cd \"\${root}\"; sha256sum -c \"${manifest_rel}\");"
remote_checks+=" if pgrep -af '[v]erify_v018_r2_cache_equivalence.py' >/dev/null; then echo 'equivalence runner still active' >&2; exit 17; fi;"
ssh "${server_host}" "${remote_checks}"

mapfile -t marker_lines < <(ssh "${server_host}" "cat '${server_root}/controller.complete'")
if [[ "${#marker_lines[@]}" != "3" \
  || "${marker_lines[0]}" != "schema=multi-catfish-mcrl-v018-r2-equivalence-complete-v1" \
  || ! "${marker_lines[1]}" =~ ^exit_status=[0-9]+$ \
  || ! "${marker_lines[2]}" =~ ^workers=[0-9]+$ ]]; then
  fail_closed "remote controller completion marker is malformed"
fi
exit_status="${marker_lines[1]#exit_status=}"
workers="${marker_lines[2]#workers=}"
if (( workers < 1 || workers > 18 )); then
  fail_closed "remote completion marker has invalid worker count"
fi
if (( exit_status != 0 && exit_status != 1 && exit_status != 2 )); then
  fail_closed "remote completion marker has invalid exit status"
fi

mapfile -t preflight_lines < <(ssh "${server_host}" "cat '${server_root}/server-preflight.receipt'")
if [[ "${#preflight_lines[@]}" != "4" \
  || "${preflight_lines[0]}" != "schema=multi-catfish-mcrl-v018-r2-equivalence-preflight-v1" \
  || "${preflight_lines[1]}" != "manifest_sha256=${manifest_expected}" \
  || "${preflight_lines[2]}" != "pytest_exit=0" \
  || ! "${preflight_lines[3]}" =~ ^log_sha256=[0-9a-f]{64}$ ]]; then
  fail_closed "remote server preflight receipt is malformed"
fi
preflight_log_sha="${preflight_lines[3]#log_sha256=}"
remote_preflight_log_sha="$(ssh "${server_host}" "sha256sum '${server_root}/server-preflight.log' | awk '{print \$1}'")"
if [[ "${remote_preflight_log_sha}" != "${preflight_log_sha}" ]]; then
  fail_closed "remote server preflight log digest mismatch"
fi

mkdir "${artifact_root}"
mkdir "${destination}" "${destination}/closure"
rsync -a "${server_host}:${server_root}/result" "${destination}/"
rsync -a "${server_host}:${server_root}/controller.complete" "${destination}/"
rsync -a "${server_host}:${server_root}/run.log" "${destination}/"
rsync -a "${server_host}:${server_root}/server-preflight.log" "${destination}/"
rsync -a "${server_host}:${server_root}/server-preflight.receipt" "${destination}/"

# Preserve the exact remote R3 source identities beside the output.  The
# independent validator still authenticates against the current local frozen
# checkout; these copies make the server closure auditable from the artifact.
for relative in "${manifest_rel}" "${contract_rel}" "${prereg_receipt_rel}" \
  "${prereg_rel}" "${r1_rel}" "${r2_rel}" "${runner_rel}"; do
  base="$(basename "${relative}")"
  rsync -a "${server_host}:${server_root}/${relative}" "${destination}/closure/${base}"
done
rsync -a "${validator}" "${destination}/closure/"

set +e
"${validator_python}" "${validator}" \
  "${destination}/result" \
  --repo-root "${repo_root}" \
  --contract "${repo_root}/${contract_rel}" \
  --code-manifest "${repo_root}/${manifest_rel}" \
  --code-manifest-sha256 "${manifest_expected}" \
  > "${destination}/independent-validation.json"
validation_status=$?
set -e
if (( validation_status != 0 )); then
  fail_closed "independent result validation failed (status ${validation_status})"
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
  find server-run-r3 -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > MANIFEST-R3.sha256
)

echo "V0.18 R3 equivalence finalized at ${artifact_root}"
echo "decision receipt: ${destination}/independent-validation.json"
echo "manifest: ${artifact_root}/MANIFEST-R3.sha256"
