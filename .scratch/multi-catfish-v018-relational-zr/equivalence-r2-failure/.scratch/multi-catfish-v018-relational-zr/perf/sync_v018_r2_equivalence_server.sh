#!/usr/bin/env bash
set -euo pipefail

# Synchronise the implementation-equivalence closure only.  This script does
# not open an outcome, execute an environment action, or start the check.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
server_host="${V018E_SERVER_HOST:-sat}"
server_root="${V018E_SERVER_ROOT:-/home/sat/mcrl-v018-r2-equivalence-20260904-r1}"
python_bin="${V018E_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
manifest=".scratch/multi-catfish-v018-relational-zr/contracts/code-manifest-r2-equivalence.sha256"
manifest_expected="${V018E_MANIFEST_SHA256:?V018E_MANIFEST_SHA256 is required}"

focused_tests=(
  tests/test_w140_ee_axis_zero_marginal_c3.py
  tests/test_w141_ee_axis_zero_marginal_c3_live.py
  tests/test_w148_ee_axis_v014_q2_state.py
  tests/test_w173_ee_axis_relational_zr_c3.py
  tests/test_w174_ee_axis_v018_gate.py
  tests/test_w175_v018_analytic_diagnostic.py
  tests/test_w176_ee_axis_relational_zr_c3_head.py
  tests/test_w177_ee_axis_relational_zr_c3_performance.py
)

fail_closed() {
  echo "V0.18 R2 equivalence sync is fail-closed: $*" >&2
  exit 2
}

if [[ ! "${server_root}" =~ ^/[A-Za-z0-9._/-]+$ || "${server_root}" == "/" ]]; then
  fail_closed "server root must be a safe non-root absolute path"
fi
if [[ ! "${python_bin}" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  fail_closed "Python path must be a safe absolute path"
fi
if [[ ! "${manifest_expected}" =~ ^[0-9a-f]{64}$ ]]; then
  fail_closed "manifest digest must be lowercase SHA-256"
fi

cd "${repo_root}"
for path in "${manifest}" "${focused_tests[@]}"; do
  if [[ ! -f "${path}" || -L "${path}" ]]; then
    fail_closed "missing or symlinked closure file ${path}"
  fi
done
if [[ "$(sha256sum "${manifest}" | awk '{print $1}')" != "${manifest_expected}" ]]; then
  fail_closed "local manifest digest mismatch"
fi
sha256sum -c "${manifest}"

if ssh "${server_host}" "test -e '${server_root}' || test -L '${server_root}'"; then
  fail_closed "refusing to overwrite ${server_host}:${server_root}"
fi
ssh "${server_host}" "mkdir '${server_root}'"

rsync -aR \
  pyproject.toml \
  src \
  scripts/run_head_pivotality_probe.py \
  "${focused_tests[@]}" \
  .scratch/c3-v04/run_v04_c3_500_update_screen.py \
  .scratch/c3-v04/run_v04_c3_learnability_gate.py \
  .scratch/c3-v04/run_v04_c3_source.py \
  .scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py \
  .scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py \
  .scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py \
  .scratch/multi-catfish-v018-relational-zr/perf/verify_v018_r2_cache_equivalence.py \
  .scratch/multi-catfish-v018-relational-zr/perf/sync_v018_r2_equivalence_server.sh \
  .scratch/multi-catfish-v018-relational-zr/perf/run_v018_r2_equivalence_server.sh \
  .scratch/multi-catfish-v018-relational-zr/r1-abort/ee_axis_relational_zr_c3-r1.py \
  .scratch/multi-catfish-v018-relational-zr/r1-abort/ABORT-RECEIPT.md \
  .scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md \
  .scratch/multi-catfish-v018-relational-zr/contracts/prereg.sha256 \
  .scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-R2-CACHE-EQUIVALENCE-CHECK-2026-09-04.md \
  "${manifest}" \
  artifacts/PREREG-FROZEN-2026-08-25-R2.json \
  artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1 \
  artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate \
  artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1/contracts \
  "${server_host}:${server_root}/"

focused="${focused_tests[*]}"
ssh "${server_host}" "set -euo pipefail; cd '${server_root}'; test \"\$(sha256sum '${manifest}' | awk '{print \$1}')\" = '${manifest_expected}'; sha256sum -c '${manifest}'; test ! -n \"\$(pgrep -af '[r]un_v018_analytic_diagnostic.py' || true)\"; env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 '${python_bin}' -m pytest -q ${focused} > server-preflight.log 2>&1; log_sha=\$(sha256sum server-preflight.log | awk '{print \$1}'); printf 'schema=multi-catfish-mcrl-v018-r2-equivalence-preflight-v1\nmanifest_sha256=%s\npytest_exit=0\nlog_sha256=%s\n' '${manifest_expected}' \"\${log_sha}\" > server-preflight.receipt"

echo "V0.18 R2 equivalence closure synced and preflight-tested at ${server_host}:${server_root}"
