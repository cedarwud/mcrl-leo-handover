#!/usr/bin/env bash
set -euo pipefail

# Run the frozen V0.18 matched analytic diagnostic panel.  This is still a
# TRAIN-only diagnostic gate: four fresh worlds x three arms x three frozen
# Q1/Q2 lineages, with no learner update and no TEST access.

run_root="${1:-${V018R_SERVER_ROOT:-/home/sat/mcrl-v018-relational-zr-20260904-r2}}"
run_label="${V018R_RUN_LABEL:-r2}"
if [[ "${run_label}" == "r1" ]]; then
  run_dir="${run_root}/analytic-panel"
else
  run_dir="${run_root}/analytic-panel-${run_label}"
fi
max_parallel="${V018R_MAX_PARALLEL:-18}"
python_bin="${V018R_PYTHON_BIN:-/home/sat/mcrl-leo-handover/.venv/bin/python}"
runner=".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py"
contract_path=".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md"
# The default invocation is the isolated R2 panel.  R1 is retained only as an
# explicit legacy override; all R2 receipts carry the provenance below.
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
tle_root="${V018R_TLE_ROOT:-/home/sat/mcrl-runtime/tle-frozen-20260820}"
prereg_path="artifacts/PREREG-FROZEN-2026-08-25-R2.json"
v03_root="artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
q2_root="artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate"

worlds=(2026120401 2026120402 2026120403 2026120404)
arms=(BASE EXACT_ZR NOMINAL_ZR)
lineages=(2026092101 2026092102 2026092103)
focused_tests=(
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

fail_closed() {
  echo "V0.18 analytic panel launch is fail-closed: $*" >&2
  exit 2
}

if [[ ! "${run_root}" =~ ^/[A-Za-z0-9._/-]+$ || "${run_root}" == "/" ]]; then
  fail_closed "run root must be a non-root absolute path with safe characters"
fi
if [[ ! "${run_label}" =~ ^[A-Za-z0-9_.-]+$ || "${run_label}" == "." || "${run_label}" == ".." ]]; then
  fail_closed "V018R_RUN_LABEL contains unsafe characters"
fi
if [[ "${run_label}" != "r2" && -z "${V018R_SERVER_ROOT:-}" && "$#" -eq 0 ]]; then
  fail_closed "a non-r2 panel requires an explicit isolated V018R_SERVER_ROOT"
fi
if [[ ! "${python_bin}" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  fail_closed "V018R_PYTHON_BIN must be an absolute path with safe characters"
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
for path in "${contract_path}" "${v018_prereg_path}" "${code_manifest_path}" "${prereg_path}"; do
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

if [[ ! "${max_parallel}" =~ ^[0-9]+$ ]] || (( max_parallel < 1 || max_parallel > 18 )); then
  echo "V018R_MAX_PARALLEL must be an integer from 1 through 18" >&2
  exit 2
fi
if [[ ! -d "${run_root}" || -L "${run_root}" ]]; then
  echo "missing or symlinked isolated V0.18 root ${run_root}" >&2
  exit 3
fi
if [[ -e "${run_dir}" || -L "${run_dir}" ]]; then
  echo "refusing to overwrite existing V0.18 run directory ${run_dir}" >&2
  exit 4
fi

cd "${run_root}"

# Re-authenticate immediately before opening any shard.  This catches a
# post-sync mutation and keeps the panel fail-closed even if invoked without
# the synchronisation wrapper.
(
  cd "$(dirname "${v018_prereg_path}")"
  sha256sum -c "$(basename "${v018_prereg_path}")"
)
(
  test -f "${code_manifest_path}" && test ! -L "${code_manifest_path}"
  test "$(sha256sum "${code_manifest_path}" | awk '{print $1}')" = "${code_manifest_expected}"
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
(
  cd "${v015_contract_dir}"
  sha256sum -c prereg.sha256
)
env PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 "${python_bin}" -m pytest -q "${focused_tests[@]}"

mkdir "${run_dir}"
mkdir "${run_dir}/logs" "${run_dir}/shards"

run_one() {
  local world="${1:?world is required}"
  local arm="${2:?arm is required}"
  local lineage="${3:?lineage is required}"
  local output="${run_dir}/shards/${world}-${arm}-${lineage}"
  local log="${run_dir}/logs/${world}-${arm}-${lineage}.log"

  if [[ -e "${output}" || -L "${output}" || -e "${log}" || -L "${log}" ]]; then
    echo "refusing to overwrite shard output or log for ${world}/${arm}/${lineage}" >&2
    return 5
  fi

  # Noclobber protects the log boundary if a duplicate task or a concurrent
  # invocation ever reaches this function.
  set -C
  env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
    "${python_bin}" "${runner}" shard \
      --world "${world}" \
      --arm "${arm}" \
      --lineage "${lineage}" \
      --tle-root "${tle_root}" \
      --prereg "${prereg_path}" \
      --v03-root "${v03_root}" \
      --q2-root "${q2_root}" \
      --contract "${contract_path}" \
      --performance-addendum "${performance_addendum}" \
      --performance-addendum-sha256 "${performance_addendum_expected}" \
      --r2-code-manifest "${code_manifest_path}" \
      --r2-code-manifest-sha256 "${code_manifest_expected}" \
      --r1-abort-receipt "${r1_abort_receipt}" \
      --r1-abort-receipt-sha256 "${r1_abort_receipt_expected}" \
      --r4-result "${r4_result}" \
      --r4-result-sha256 "${r4_result_expected}" \
      --r4-receipt "${r4_receipt}" \
      --r4-receipt-sha256 "${r4_receipt_expected}" \
      --r4-artifact-manifest "${r4_artifact_manifest}" \
      --r4-artifact-manifest-sha256 "${r4_artifact_manifest_expected}" \
      --r4-code-manifest "${r4_code_manifest}" \
      --r4-code-manifest-sha256 "${r4_code_manifest_expected}" \
      --r4-independent-validation "${r4_independent_validation}" \
      --r4-independent-validation-sha256 "${r4_independent_validation_expected}" \
      --output "${output}" > "${log}" 2>&1
}

export -f run_one
export python_bin runner contract_path tle_root prereg_path v03_root q2_root run_dir
export performance_addendum performance_addendum_expected code_manifest_path code_manifest_expected
export r1_abort_receipt r1_abort_receipt_expected r4_result r4_result_expected
export r4_receipt r4_receipt_expected r4_artifact_manifest r4_artifact_manifest_expected
export r4_code_manifest r4_code_manifest_expected r4_independent_validation r4_independent_validation_expected

task_count=$(( ${#worlds[@]} * ${#arms[@]} * ${#lineages[@]} ))
if (( task_count != 36 )); then
  echo "V0.18 panel declaration must contain exactly 36 tasks" >&2
  exit 6
fi

merge_world_args=()
merge_lineage_args=()
for world in "${worlds[@]}"; do
  merge_world_args+=(--world "${world}")
done
for lineage in "${lineages[@]}"; do
  merge_lineage_args+=(--lineage "${lineage}")
done

for world in "${worlds[@]}"; do
  for arm in "${arms[@]}"; do
    for lineage in "${lineages[@]}"; do
      printf '%s\0%s\0%s\0' "${world}" "${arm}" "${lineage}"
    done
  done
done | xargs -0 -n 3 -P "${max_parallel}" bash -c 'run_one "$1" "$2" "$3"' _

shards=()
logs=()
for world in "${worlds[@]}"; do
  for arm in "${arms[@]}"; do
    for lineage in "${lineages[@]}"; do
      shard_dir="${run_dir}/shards/${world}-${arm}-${lineage}"
      shard_file="${shard_dir}/shard.json"
      log_file="${run_dir}/logs/${world}-${arm}-${lineage}.log"
      if [[ ! -d "${shard_dir}" || -L "${shard_dir}" || ! -f "${shard_file}" || -L "${shard_file}" ]]; then
        echo "missing or non-regular V0.18 shard receipt ${shard_file}" >&2
        exit 7
      fi
      mapfile -t shard_entries < <(find "${shard_dir}" -mindepth 1 -maxdepth 1 -print)
      if [[ "${#shard_entries[@]}" != "1" || "${shard_entries[0]}" != "${shard_file}" ]]; then
        echo "V0.18 shard directory is not canonical ${shard_dir}" >&2
        exit 8
      fi
      if [[ ! -s "${log_file}" || -L "${log_file}" ]]; then
        echo "missing, symlinked, or empty V0.18 shard log ${log_file}" >&2
        exit 9
      fi
      if grep -Eq 'Traceback|Error|FAILED|Killed' "${log_file}"; then
        echo "error marker in ${log_file}" >&2
        exit 10
      fi
      shards+=("${shard_file}")
      logs+=("${log_file}")
    done
  done
done

mapfile -t shard_dirs < <(find "${run_dir}/shards" -mindepth 1 -maxdepth 1 -print | sort)
if [[ "${#shard_dirs[@]}" != "36" ]]; then
  echo "expected exactly 36 canonical V0.18 shard directories, found ${#shard_dirs[@]}" >&2
  exit 11
fi
mapfile -t log_entries < <(find "${run_dir}/logs" -mindepth 1 -maxdepth 1 -print | sort)
if [[ "${#log_entries[@]}" != "36" ]]; then
  echo "expected exactly 36 canonical V0.18 shard logs, found ${#log_entries[@]}" >&2
  exit 12
fi

merge_log="${run_dir}/merge.log"
if [[ -e "${merge_log}" || -L "${merge_log}" || -e "${run_dir}/merged" || -L "${run_dir}/merged" ]]; then
  echo "refusing to overwrite V0.18 merge output or log" >&2
  exit 13
fi

set -C
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 PYTHONPATH=src \
  "${python_bin}" "${runner}" merge \
    --shards "${shards[@]}" \
    --output "${run_dir}/merged" \
    "${merge_world_args[@]}" \
    "${merge_lineage_args[@]}" \
    --contract "${contract_path}" \
    --performance-addendum "${performance_addendum}" \
    --performance-addendum-sha256 "${performance_addendum_expected}" \
    --r2-code-manifest "${code_manifest_path}" \
    --r2-code-manifest-sha256 "${code_manifest_expected}" \
    --r1-abort-receipt "${r1_abort_receipt}" \
    --r1-abort-receipt-sha256 "${r1_abort_receipt_expected}" \
    --r4-result "${r4_result}" \
    --r4-result-sha256 "${r4_result_expected}" \
    --r4-receipt "${r4_receipt}" \
    --r4-receipt-sha256 "${r4_receipt_expected}" \
    --r4-artifact-manifest "${r4_artifact_manifest}" \
    --r4-artifact-manifest-sha256 "${r4_artifact_manifest_expected}" \
    --r4-code-manifest "${r4_code_manifest}" \
    --r4-code-manifest-sha256 "${r4_code_manifest_expected}" \
    --r4-independent-validation "${r4_independent_validation}" \
    --r4-independent-validation-sha256 "${r4_independent_validation_expected}" \
    > "${merge_log}" 2>&1

if [[ ! -f "${run_dir}/merged/result.json" || -L "${run_dir}/merged/result.json" \
  || ! -f "${run_dir}/merged/result-seal.json" || -L "${run_dir}/merged/result-seal.json" ]]; then
  echo "V0.18 merge did not produce regular result and seal files" >&2
  exit 14
fi

if [[ -e "${run_dir}/controller.complete" || -L "${run_dir}/controller.complete" ]]; then
  echo "refusing to overwrite V0.18 completion marker" >&2
  exit 15
fi
(
  set -C
  printf 'schema=multi-catfish-mcrl-v018-analytic-panel-complete-v1\ntask_count=%s\nmax_parallel=%s\n' \
    "${task_count}" "${max_parallel}" > "${run_dir}/controller.complete"
)

echo "V0.18 analytic panel complete: ${run_dir}"
