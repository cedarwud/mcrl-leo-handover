#!/usr/bin/env bash
set -Eeuo pipefail

# Wait for, authenticate, and fetch one completed V0.23 LC-SRS server run.
# This script is read-only toward the server.  It refuses every local
# overwrite, stages rsync into a new artifact root, and runs the independent
# final verifier before publishing the fetched run.  A server COMPLETE marker
# is not a scientific efficacy result: the verifier may still report a C3
# HOLD/STOP decision under the TRAIN-development claim ceiling.

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
server_host="${V023_SERVER_HOST:-sat}"
server_root="${V023_SERVER_ROOT:-/home/sat/mcrl-v023-lcsrs-gate-20260906-r5}"
remote_run="${server_root}/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r5/server-run"
local_parent="${V023_LOCAL_ROOT:-${repo_root}/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r5}"
staging="${local_parent}/.server-run.staging"
local_run="${local_parent}/server-run"
audit_root="${local_parent}/independent-audit"
package_manifest="${local_parent}/FETCHED-PACKAGE-MANIFEST.sha256"
local_python="${V023_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}"
server_python="/home/sat/mcrl-leo-handover/.venv/bin/python"
verifier="${repo_root}/.scratch/multi-catfish-v023-r5-defect-relaunch/verify_v023_lcsrs_final.py"
source_stage_verifier="${repo_root}/.scratch/multi-catfish-v023-r5-defect-relaunch/verify_v023_lcsrs_source_stage.py"
wait_seconds="${V023_WAIT_SECONDS:-172800}"
poll_seconds="${V023_POLL_SECONDS:-60}"
contract_sha256="1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
result_metadata_sha256="a8ba77be1bec687eee49cb8487283bddb328ae3778fa6fe99bff9e710329fba1"

die() {
  printf 'V023_SERVER_FINALIZE_ERROR: %s\n' "$*" >&2
  exit 2
}

[[ -x "${local_python}" ]] || die "local Python is missing or not executable: ${local_python}"
[[ -f "${verifier}" && ! -L "${verifier}" ]] || die "local independent verifier is missing: ${verifier}"
[[ -f "${source_stage_verifier}" && ! -L "${source_stage_verifier}" ]] || die "local source-stage verifier is missing: ${source_stage_verifier}"
[[ "${server_root}" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe V023_SERVER_ROOT: ${server_root}"
[[ "${server_root}" != */.. && "${server_root}" != */. ]] || die "unsafe V023_SERVER_ROOT: ${server_root}"
[[ "${wait_seconds}" =~ ^[0-9]+$ && "${wait_seconds}" -gt 0 ]] || die "V023_WAIT_SECONDS must be a positive integer"
[[ "${poll_seconds}" =~ ^[0-9]+$ && "${poll_seconds}" -gt 0 ]] || die "V023_POLL_SECONDS must be a positive integer"

if [[ "${local_parent}" != /* ]]; then
  local_parent="${repo_root}/${local_parent}"
  staging="${local_parent}/.server-run.staging"
  local_run="${local_parent}/server-run"
  audit_root="${local_parent}/independent-audit"
  package_manifest="${local_parent}/FETCHED-PACKAGE-MANIFEST.sha256"
fi
case "${local_parent}" in
  "${repo_root}"/artifacts/*) ;;
  *) die "local artifact root must stay under ${repo_root}/artifacts" ;;
esac

if [[ -e "${local_parent}" || -L "${local_parent}" ]]; then
  die "refusing to overwrite local artifact root: ${local_parent}"
fi

ssh "${server_host}" true || die "cannot reach Ubuntu server ${server_host}"

start_epoch="$(date +%s)"
while :; do
  if ssh "${server_host}" "test -e '${remote_run}/FAILED' || test -L '${remote_run}/FAILED'"; then
    die "server run published FAILED: ${server_host}:${remote_run}/FAILED"
  fi
  if ssh "${server_host}" "test -f '${remote_run}/COMPLETE' && test ! -L '${remote_run}/COMPLETE'"; then
    break
  fi
  now_epoch="$(date +%s)"
  elapsed=$((now_epoch - start_epoch))
  if ((elapsed >= wait_seconds)); then
    die "timed out waiting for ${server_host}:${remote_run}/COMPLETE after ${wait_seconds}s"
  fi
  remaining=$((wait_seconds - elapsed))
  sleep_for="${poll_seconds}"
  ((sleep_for > remaining)) && sleep_for="${remaining}"
  sleep "${sleep_for}"
done

# Recheck every server receipt hash and the completion envelope before any
# bytes are staged locally.  The Python block uses only stdlib and performs no
# simulator, learner, TEST, or episode operation.
ssh "${server_host}" \
  "set -euo pipefail; \
   test -d '${remote_run}' && test ! -L '${remote_run}'; \
   test ! -e '${remote_run}/FAILED' && test ! -L '${remote_run}/FAILED'; \
   cd '${remote_run}'; \
   sha256sum -c MANIFEST.sha256; \
   '${server_python}' - '${remote_run}' '${server_root}/.scratch/multi-catfish-v023-r5-defect-relaunch/PREFLIGHT-MANIFEST.json' '${contract_sha256}'" <<'REMOTE_VERIFY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
manifest = Path(sys.argv[2])
expected_contract = sys.argv[3]
expected_addendum = "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
results_path = root / "MANIFEST.sha256"
complete_path = root / "COMPLETE"
result_path = root / "result.json"

if complete_path.is_symlink() or not complete_path.is_file():
    raise SystemExit("COMPLETE marker is missing or symlinked")
if results_path.is_symlink() or not results_path.is_file():
    raise SystemExit("MANIFEST.sha256 is missing or symlinked")
if manifest.is_symlink() or not manifest.is_file():
    raise SystemExit("server preflight manifest is missing or symlinked")
if result_path.is_symlink() or not result_path.is_file():
    raise SystemExit("result.json is missing or symlinked")
manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
if not manifest_digest:
    raise SystemExit("server preflight manifest digest is empty")
authority_root = root / "authority"
authority_receipt_path = authority_root / "AUTHORITY.json"
contract_copy = authority_root / "MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
addendum_copy = authority_root / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
preflight_copy = authority_root / "PREFLIGHT-MANIFEST.json"
preflight_digest_copy = authority_root / "PREFLIGHT-MANIFEST.sha256"
for required in (
    authority_receipt_path,
    contract_copy,
    addendum_copy,
    preflight_copy,
    preflight_digest_copy,
):
    if required.is_symlink() or not required.is_file():
        raise SystemExit(f"authority copy is missing or symlinked: {required.name}")
if hashlib.sha256(contract_copy.read_bytes()).hexdigest() != expected_contract:
    raise SystemExit("copied contract digest disagrees")
if hashlib.sha256(addendum_copy.read_bytes()).hexdigest() != expected_addendum:
    raise SystemExit("copied addendum digest disagrees")
if preflight_copy.read_bytes() != manifest.read_bytes():
    raise SystemExit("copied preflight manifest disagrees with server authority")
if preflight_digest_copy.read_text(encoding="ascii").split() != [
    manifest_digest,
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
lines = results_path.read_text(encoding="ascii").splitlines()
if not lines:
    raise SystemExit("MANIFEST.sha256 is empty")
listed = set()
for line in lines:
    digest, name = line.split("  ", 1)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise SystemExit("MANIFEST.sha256 contains a malformed digest")
    relative = Path(name.removeprefix("./"))
    if relative.is_absolute() or ".." in relative.parts:
        raise SystemExit("MANIFEST.sha256 contains an unsafe path")
    target = root / relative
    if target.is_symlink() or not target.is_file():
        raise SystemExit(f"MANIFEST.sha256 names a missing or symlinked file: {name}")
    normalized = relative.as_posix()
    if normalized in listed:
        raise SystemExit(f"MANIFEST.sha256 repeats a path: {name}")
    listed.add(normalized)
actual = set()
for path in root.rglob("*"):
    relative_name = path.relative_to(root).as_posix()
    if path.is_symlink():
        raise SystemExit(f"result tree contains a symlink: {relative_name}")
    if path.is_dir():
        continue
    if not path.is_file():
        raise SystemExit(f"result tree contains a special node: {relative_name}")
    if relative_name not in {"MANIFEST.sha256", "COMPLETE"}:
        actual.add(relative_name)
if listed != actual:
    raise SystemExit("MANIFEST.sha256 does not cover the exact result file set")
complete_fields = complete_path.read_text(encoding="ascii").split()
if complete_fields != [hashlib.sha256(results_path.read_bytes()).hexdigest(), "MANIFEST.sha256"]:
    raise SystemExit("COMPLETE does not bind MANIFEST.sha256")

result = json.loads(result_path.read_text(encoding="ascii"))
if result.get("contract_sha256") != expected_contract:
    raise SystemExit("result contract hash disagrees")
if result.get("preflight_manifest_sha256") != manifest_digest:
    raise SystemExit("result preflight hash disagrees")
if result.get("scientific_claim") is not False:
    raise SystemExit("result opened a scientific claim")
if result.get("test_split_opened") is not False or result.get("episode_training") is not False:
    raise SystemExit("result crossed a closed boundary")
full = (
    result.get("status") == "PASS_FINAL_INTEGRITY"
    and result.get("integrity_status") == "VERIFIED"
    and (result.get("source_count"), result.get("fit_count"), result.get("composition_count"))
    == (8, 48, 48)
)
insufficient = (
    result.get("status") == "PASS_SOURCE_STAGE_INTEGRITY"
    and result.get("integrity_status") == "VERIFIED_SOURCE_ONLY"
    and result.get("c3_decision") == "INSUFFICIENT_PAIRS"
    and (result.get("source_count"), result.get("fit_count"), result.get("composition_count"))
    == (8, 0, 0)
)
if not (full or insufficient):
    raise SystemExit("result is neither a verified full gate nor an insufficient-pairs stop")
print("V023_SERVER_RECEIPTS_VERIFIED")
REMOTE_VERIFY

mkdir -p "${local_parent}"
mkdir "${staging}"
mkdir "${audit_root}"
rsync -a "${server_host}:${remote_run}/" "${staging}/"

[[ -f "${staging}/COMPLETE" && ! -L "${staging}/COMPLETE" ]] || die "staged COMPLETE is missing"
[[ -f "${staging}/MANIFEST.sha256" && ! -L "${staging}/MANIFEST.sha256" ]] || die "staged MANIFEST.sha256 is missing"
(
  cd "${staging}"
  sha256sum -c MANIFEST.sha256
)

source_args=()
for world in 2026121705 2026121706 2026121707 2026121708 2026121709 2026121710 2026121711 2026121712; do
  source_args+=("${staging}/source/world-${world}.json")
done

result_kind=$("${local_python}" - "${staging}/result.json" <<'PY'
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
if payload.get("status") == "PASS_FINAL_INTEGRITY":
    print("FULL")
elif payload.get("c3_decision") == "INSUFFICIENT_PAIRS":
    print("INSUFFICIENT")
else:
    raise SystemExit("unrecognized fetched result kind")
PY
) || die "cannot classify fetched result"

if [[ "${result_kind}" == "FULL" ]]; then
  fit_args=()
  composition_args=()
  for world in 2026121705 2026121706 2026121707 2026121708 2026121709 2026121710 2026121711 2026121712; do
    for seed in 2026135101 2026135102 2026135103; do
      for arm in informed matched_placebo; do
        fit_args+=("${staging}/fit/world-${world}/seed-${seed}/${arm}.json")
        composition_args+=("${staging}/composition/world-${world}/seed-${seed}/${arm}.json")
      done
    done
  done
  "${local_python}" "${verifier}" \
    --source "${source_args[@]}" \
    --fit "${fit_args[@]}" \
    --composition "${composition_args[@]}" \
    --source-manifest "${staging}/source-manifest.json" \
    --output "${audit_root}/independent-final-verification.json" >/dev/null

  "${local_python}" - \
    "${audit_root}/independent-final-verification.json" \
    "${staging}/verification.json" \
    "${staging}/result.json" \
    "${result_metadata_sha256}" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
if payload.get("status") != "PASS_FINAL_INTEGRITY":
    raise SystemExit("local independent verifier did not pass integrity")
if payload.get("scientific_claim") is not False:
    raise SystemExit("local independent verifier opened a scientific claim")
if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
    raise SystemExit("local independent verifier crossed a closed boundary")
saved_verification = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
if saved_verification != payload:
    raise SystemExit("saved verification.json disagrees with independent recomputation")
saved_result = json.loads(Path(sys.argv[3]).read_text(encoding="ascii"))
metadata = {
    "design_basis": saved_result.pop("design_basis", None),
    "thresholds": saved_result.pop("thresholds", None),
}
encoded = json.dumps(
    metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
).encode("ascii")
if hashlib.sha256(encoded).hexdigest() != sys.argv[4]:
    raise SystemExit("saved result threshold/design metadata drifted")
if saved_result != payload:
    raise SystemExit("saved result.json disagrees with independent full verification")
PY
else
  "${local_python}" "${source_stage_verifier}" \
    --source "${source_args[@]}" \
    --preflight-sha256 "$(sha256sum "${staging}/authority/PREFLIGHT-MANIFEST.json" | awk '{print $1}')" \
    --output "${audit_root}/independent-source-stage-verification.json" >/dev/null
  "${local_python}" - \
    "${audit_root}/independent-source-stage-verification.json" \
    "${staging}/verification.json" \
    "${staging}/result.json" \
    "${staging}/source-stage-verification.json" \
    "${result_metadata_sha256}" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
if payload.get("status") != "VERIFIED_SOURCE_STAGE":
    raise SystemExit("local independent source-stage verifier did not verify")
if payload.get("decision") != "INSUFFICIENT_PAIRS":
    raise SystemExit("local independent source-stage decision disagrees")
if payload.get("fit_launched") is not False or payload.get("episode_training") is not False:
    raise SystemExit("local independent source-stage verifier crossed a closed boundary")
saved_verification = json.loads(Path(sys.argv[2]).read_text(encoding="ascii"))
if saved_verification != payload:
    raise SystemExit("saved verification.json disagrees with source-stage recomputation")
archived_source_stage = json.loads(Path(sys.argv[4]).read_text(encoding="ascii"))
if archived_source_stage != payload:
    raise SystemExit("archived source-stage verification disagrees with recomputation")
saved_result = json.loads(Path(sys.argv[3]).read_text(encoding="ascii"))
metadata = {
    "design_basis": saved_result.get("design_basis"),
    "thresholds": saved_result.get("thresholds"),
}
encoded = json.dumps(
    metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
).encode("ascii")
if hashlib.sha256(encoded).hexdigest() != sys.argv[5]:
    raise SystemExit("saved early result threshold/design metadata drifted")
source_panel = payload.get("source_panel")
if not isinstance(source_panel, dict):
    raise SystemExit("independent source-stage report lacks source panel")
expected_denominators = {
    "pair_count": source_panel.get("pair_count"),
    "mechanics_pass_count": source_panel.get("mechanics_pass_count"),
    "target_support_count": source_panel.get("target_support_count"),
    "placebo_folds": source_panel.get("placebo_folds"),
    "world_results": source_panel.get("world_results"),
}
source_predicates = source_panel.get("predicates")
if not isinstance(source_predicates, dict):
    raise SystemExit("independent source-stage report lacks predicates")
expected_predicates = {
    **source_predicates,
    "held_out_learner": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "world_stability": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "action_exposure": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "literal_11": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "harmful_partial": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "topology_consistency": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "teacher_composition": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "learned_composition": "NOT_EVALUATED_SOURCE_STAGE_STOP",
    "service": "NOT_EVALUATED_SOURCE_STAGE_STOP",
}
expected_result = {
    "schema": "multi-catfish-mcrl-v023-lcsrs-result-v1",
    "status": "PASS_SOURCE_STAGE_INTEGRITY",
    "integrity_status": "VERIFIED_SOURCE_ONLY",
    "c3_decision": "INSUFFICIENT_PAIRS",
    "context_status": source_panel.get("context_status"),
    "context": {"c1": source_panel.get("c1"), "c2": source_panel.get("c2")},
    "scientific_claim": False,
    "claim_ceiling": payload.get("claim_ceiling"),
    "contract_sha256": payload.get("contract_sha256"),
    "preflight_manifest_sha256": payload.get("preflight_manifest_sha256"),
    "source_count": payload.get("source_count"),
    "fit_count": 0,
    "composition_count": 0,
    "source_stage_receipt_sha256": hashlib.sha256(
        Path(sys.argv[4]).read_bytes()
    ).hexdigest(),
    "test_split_opened": False,
    "episode_training": False,
    "no_rescue": True,
    "predicates": expected_predicates,
    "denominators": expected_denominators,
    "source_panel": source_panel,
    "thresholds": metadata["thresholds"],
    "design_basis": metadata["design_basis"],
}
if saved_result != expected_result:
    raise SystemExit("saved early result.json disagrees with independent projection")
PY
fi

if [[ -e "${local_run}" || -L "${local_run}" ]]; then
  die "refusing to overwrite local fetched run: ${local_run}"
fi
mv "${staging}" "${local_run}"
[[ ! -e "${package_manifest}" && ! -L "${package_manifest}" ]] \
  || die "refusing to overwrite fetched package manifest"
(
  cd "${local_parent}"
  mapfile -d '' evidence < <(
    find . -type f \
      ! -path './FETCHED-PACKAGE-MANIFEST.sha256' \
      -print0 | sort -z
  )
  ((${#evidence[@]} > 0))
  for path in "${evidence[@]}"; do
    sha256sum -- "${path}"
  done > FETCHED-PACKAGE-MANIFEST.sha256
)
printf 'V023_GATE_FETCHED %s\n' "${local_run}"
