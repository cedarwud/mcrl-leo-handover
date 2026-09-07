#!/usr/bin/env bash
set -euo pipefail

# Template only.  It copies a completed, separately frozen learner gate into
# a new local artifact root.  It does not infer success, alter a result, or
# make any world/seed/threshold choice.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
server_host="${V018R_SERVER_HOST:-sat}"
server_root="${V018R_SERVER_ROOT:-}"
contract_rel="${V018R_LEARNER_CONTRACT:-}"
contract_expected="${V018R_LEARNER_CONTRACT_SHA256:-}"
code_manifest_rel="${V018R_CODE_MANIFEST:-}"
code_manifest_expected="${V018R_CODE_MANIFEST_SHA256:-}"
remote_result_rel="${V018R_LEARNER_REMOTE_RESULT:-}"
remote_complete_rel="${V018R_LEARNER_REMOTE_COMPLETE:-}"
local_artifact_root="${V018R_LOCAL_ARTIFACT_ROOT:-}"

fail_closed() {
  echo "V018 relational learner finalize is fail-closed: $*" >&2
  exit 2
}

[[ -n "${contract_rel}" ]] || fail_closed "V018R_LEARNER_CONTRACT is not set"
[[ -n "${server_root}" ]] || fail_closed "V018R_SERVER_ROOT is not set"
[[ "${server_root}" = /* && "${server_root}" != "/" ]] || fail_closed "V018R_SERVER_ROOT must be a non-root absolute path"
[[ -n "${contract_expected}" ]] || fail_closed "V018R_LEARNER_CONTRACT_SHA256 is not set"
[[ -n "${code_manifest_rel}" ]] || fail_closed "V018R_CODE_MANIFEST is not set"
[[ -n "${code_manifest_expected}" ]] || fail_closed "V018R_CODE_MANIFEST_SHA256 is not set"
[[ -n "${remote_result_rel}" ]] || fail_closed "V018R_LEARNER_REMOTE_RESULT is not set"
[[ -n "${remote_complete_rel}" ]] || fail_closed "V018R_LEARNER_REMOTE_COMPLETE is not set"
[[ -n "${local_artifact_root}" ]] || fail_closed "V018R_LOCAL_ARTIFACT_ROOT is not set"
[[ "${contract_expected}" =~ ^[0-9a-f]{64}$ ]] || fail_closed "learner contract digest is not lowercase SHA-256"
[[ "${code_manifest_expected}" =~ ^[0-9a-f]{64}$ ]] || fail_closed "code manifest digest is not lowercase SHA-256"

validate_relative() {
  local field="$1"
  local value="$2"
  case "${value}" in
    /*|..|../*|*/../*|*/..)
      fail_closed "${field} must stay below the isolated server root: ${value}"
      ;;
  esac
}
validate_relative contract "${contract_rel}"
validate_relative code-manifest "${code_manifest_rel}"
validate_relative remote-result "${remote_result_rel}"
validate_relative remote-complete "${remote_complete_rel}"

destination="${local_artifact_root}"
[[ "${destination}" = /* ]] || destination="${repo_root}/${destination}"
[[ ! -e "${destination}" && ! -L "${destination}" ]] \
  || fail_closed "refusing to overwrite local artifact root ${destination}"

ssh "${server_host}" "
  set -euo pipefail
  cd '${server_root}'
  test -f '${contract_rel}' && test ! -L '${contract_rel}'
  grep -Fq FROZEN_BEFORE_OUTCOME '${contract_rel}'
  test \"\$(sha256sum '${contract_rel}' | awk '{print \$1}')\" = '${contract_expected}'
  cd \"\$(dirname '${code_manifest_rel}')\"
  sha256sum -c \"\$(basename '${code_manifest_rel}')\"
  cd '${server_root}'
  test -f '${remote_complete_rel}' && test ! -L '${remote_complete_rel}'
  test -f '${remote_result_rel}' && test ! -L '${remote_result_rel}'
"

mkdir -p "${destination}"
rsync -aR \
  "${server_host}:${server_root}/${contract_rel}" \
  "${server_host}:${server_root}/${code_manifest_rel}" \
  "${server_host}:${server_root}/${remote_result_rel}" \
  "${server_host}:${server_root}/${remote_complete_rel}" \
  "${destination}/"

(
  cd "${destination}"
  find . -type f ! -name MANIFEST.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > MANIFEST.sha256
)

echo "V018 relational learner result finalized without overwrite: ${destination}"
