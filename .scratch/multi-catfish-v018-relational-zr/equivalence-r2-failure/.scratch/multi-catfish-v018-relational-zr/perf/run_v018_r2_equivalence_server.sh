#!/usr/bin/env bash
set -euo pipefail

run_root="${1:-${V018E_SERVER_ROOT:-/home/sat/mcrl-v018-r2-equivalence-20260904-r1}}"
python_bin="${V018E_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
tle_root="${V018E_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
workers="${V018E_WORKERS:-18}"
manifest=".scratch/multi-catfish-v018-relational-zr/contracts/code-manifest-r2-equivalence.sha256"
manifest_expected="${V018E_MANIFEST_SHA256:?V018E_MANIFEST_SHA256 is required}"
runner=".scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r2_cache_equivalence.py"
output="${run_root}/result"
log="${run_root}/run.log"
marker="${run_root}/controller.complete"

fail_closed() {
  echo "V0.18 R2 equivalence run is fail-closed: $*" >&2
  exit 2
}

if [[ ! "${run_root}" =~ ^/[A-Za-z0-9._/-]+$ || "${run_root}" == "/" ]]; then
  fail_closed "run root must be a safe non-root absolute path"
fi
if [[ ! "${python_bin}" =~ ^/[A-Za-z0-9._/-]+$ || ! "${tle_root}" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  fail_closed "Python and TLE roots must be safe absolute paths"
fi
if [[ ! "${workers}" =~ ^[0-9]+$ ]] || (( workers < 1 || workers > 18 )); then
  fail_closed "workers must be an integer from 1 through 18"
fi
if [[ ! "${manifest_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  fail_closed "manifest digest must be lowercase SHA-256"
fi
if [[ ! -d "${run_root}" || -L "${run_root}" || ! -d "${tle_root}" || -L "${tle_root}" ]]; then
  fail_closed "run or TLE root is missing/symlinked"
fi
if [[ -e "${output}" || -L "${output}" || -e "${log}" || -L "${log}" || -e "${marker}" || -L "${marker}" ]]; then
  fail_closed "refusing to overwrite an equivalence output, log, or marker"
fi

cd "${run_root}"
test "$(sha256sum "${manifest}" | awk '{print $1}')" = "${manifest_expected}"
sha256sum -c "${manifest}"
if [[ ! -s server-preflight.log || -L server-preflight.log \
  || ! -f server-preflight.receipt || -L server-preflight.receipt ]]; then
  fail_closed "authenticated server preflight receipt is missing"
fi
mapfile -t preflight < server-preflight.receipt
if [[ "${#preflight[@]}" != "4" \
  || "${preflight[0]}" != "schema=multi-catfish-mcrl-v018-r2-equivalence-preflight-v1" \
  || "${preflight[1]}" != "manifest_sha256=${manifest_expected}" \
  || "${preflight[2]}" != "pytest_exit=0" \
  || ! "${preflight[3]}" =~ ^log_sha256=[0-9a-f]{64}$ ]]; then
  fail_closed "server preflight receipt is malformed"
fi
if [[ "$(sha256sum server-preflight.log | awk '{print $1}')" != "${preflight[3]#log_sha256=}" ]]; then
  fail_closed "server preflight log digest mismatch"
fi
if pgrep -af '[r]un_v018_analytic_diagnostic.py' >/dev/null; then
  fail_closed "an old V0.18 analytic process is still active"
fi

set +e
env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  "${python_bin}" "${runner}" run \
    --output "${output}" \
    --workers "${workers}" \
    --tle-root "${tle_root}" > "${log}" 2>&1
status=$?
set -e

set -C
printf 'schema=multi-catfish-mcrl-v018-r2-equivalence-complete-v1\nexit_status=%s\nworkers=%s\n' \
  "${status}" "${workers}" > "${marker}"
exit "${status}"
