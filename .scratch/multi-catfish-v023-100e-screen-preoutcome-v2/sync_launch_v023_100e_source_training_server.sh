#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare a fresh Ubuntu-server checkout and launch exactly one V2 100-epoch
# source-training run.  The command below does not start a run in this
# repository: it first authenticates the sealed R7 and C1/C2 roots,
# reauthenticates and copies the complete R7 checkout as an immutable dependency
# seed, reruns the 100E factory preflight, requires the non-formal one-epoch
# provider diagnostic and its authenticated PASS receipt, and only then creates
# one tmux session.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "${script_dir}/../.." && pwd -P)
server_host=${V023_SERVER_HOST:-sat}
server_root=${V023_SERVER_ROOT:-/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout}
r7_result_root=${V023_R7_RESULT_ROOT:-/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1}
r7_seed_root=${V023_R7_SEED_ROOT:-/home/sat/mcrl-v023-r7-launch-ready-20260906-r4}
target_root=${V023_TARGET_ROOT:-/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8}
output_root=/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2
tmux_session=${V023_TMUX_SESSION:-mcrl-v023-five-arm-source-training-20260907-100e-r2}
local_python=${V023_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}
server_python=${V023_SERVER_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}

package_relative=.scratch/multi-catfish-v023-100e-screen-preoutcome-v2
package=${repo_root}/${package_relative}
launch_manifest=${package}/V023-100E-LAUNCH-MANIFEST.sha256
launch_manifest_pin=${package}/V023-100E-LAUNCH-MANIFEST-FROZEN.sha256
contract=${package}/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md
model_config=${package}/V023-100E-MODEL-CONFIG.json
provider_config=${package}/V023-100E-POST-R7-PROVIDER-CONFIG.json
preflight=${package}/preflight_v023_100e_source_training.py
sealer=${package}/verify_v023_100e_source_training.py
diagnostic=${package}/run_v023_one_epoch_provider_diagnostic.py
launcher=${package}/sync_launch_v023_100e_source_training_server.sh
runner_relative=.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py
factory_relative=.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py
runner=${repo_root}/${runner_relative}
factory=${repo_root}/${factory_relative}
manifest_relative=${package_relative}/V023-100E-LAUNCH-MANIFEST.sha256
remote_manifest=${server_root}/${manifest_relative}
remote_contract=${server_root}/${package_relative}/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md
remote_model_config=${server_root}/${package_relative}/V023-100E-MODEL-CONFIG.json
remote_provider_config=${server_root}/${package_relative}/V023-100E-POST-R7-PROVIDER-CONFIG.json
remote_preflight=${server_root}/${package_relative}/preflight_v023_100e_source_training.py
remote_sealer=${server_root}/${package_relative}/verify_v023_100e_source_training.py
remote_diagnostic=${server_root}/${package_relative}/run_v023_one_epoch_provider_diagnostic.py
remote_runner=${server_root}/${runner_relative}
remote_factory=${server_root}/${factory_relative}
remote_receipt=${server_root}/${package_relative}/PREFLIGHT-RECEIPT.json
remote_receipt_digest=${remote_receipt}.sha256
remote_diagnostic_root=${server_root}/v023-100e-one-epoch-diagnostic
remote_diagnostic_receipt=${remote_diagnostic_root}/one-epoch-provider-diagnostic.json
remote_diagnostic_receipt_digest=${remote_diagnostic_receipt}.sha256
remote_controller=${server_root}/v023-100e-source-training-controller.sh
remote_log=${server_root}/v023-100e-source-training-controller.log
remote_startup_marker=${server_root}/v023-100e-source-training-startup.json

expected_contract_sha256=5b84ac3b857fba6717c4c9ca34e48ed433a2945fbbc1006b8619db2ca60d6932
expected_model_config_sha256=81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7
expected_provider_config_sha256=c6c8dc6347a838bd4e437f73127929a8594c3e1aa66ca060a33a8bcb659583ba
expected_schedule_seed=1113171504590631764
expected_train_seed=2927175120652069826

die() {
  printf 'V023_100E_SOURCE_TRAINING_SYNC_ERROR: %s\n' "$*" >&2
  exit 2
}

usage() {
  cat <<'EOF'
Usage: sync_launch_v023_100e_source_training_server.sh [--dry-run]

Authenticate the frozen 100E launch closure, seed a fresh server checkout
from the complete R7 checkout, run the exact R7/C1/C2 provider preflight, and
require the authenticated one-epoch provider diagnostic before launching one
source-training controller in tmux.  --dry-run performs only local manifest/
configuration checks and never contacts the server.
EOF
}

dry_run=0
while (($#)); do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

is_safe_abs() {
  [[ "$1" =~ ^/[A-Za-z0-9._/-]+$ && "$1" != *'//'* && "$1" != */./* && "$1" != */../* ]]
}

[[ -d "$repo_root" && ! -L "$repo_root" ]] || die "repository root is unavailable"
[[ -x "$local_python" ]] || die "local Python is missing or not executable: $local_python"
is_safe_abs "$server_python" || die "unsafe server Python path: $server_python"
for path in "$server_root" "$r7_seed_root" "$output_root"; do
  is_safe_abs "$path" || die "unsafe absolute path: $path"
done
[[ "$server_root" =~ ^/home/sat/ ]] || die "dedicated checkout must be below /home/sat"
[[ "$r7_seed_root" =~ ^/home/sat/ ]] || die "R7 seed must be below /home/sat"
[[ "$output_root" == "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2" ]] || die "output root drifted"
[[ "$target_root" == "/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8" ]] || die "target root drifted from the frozen V2 contract"
[[ "$r7_result_root" == "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1" ]] || die "R7 result root drifted from the frozen V2 contract"
[[ "$tmux_session" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe tmux session"
for path in "$launch_manifest" "$launch_manifest_pin" "$contract" "$model_config" "$provider_config" "$preflight" "$sealer" "$diagnostic" "$launcher" "$runner" "$factory"; do
  [[ -f "$path" && ! -L "$path" ]] || die "required launch input is missing or symlinked: $path"
done
cd "$repo_root"

# This check is deliberately local and independent of any remote result.  It
# also forces the parent agent to rebuild the launch manifest after adding the
# sealer/launcher files; a stale 31-entry placeholder cannot launch.
read -r pinned_code_sha256 pinned_manifest_name < "$launch_manifest_pin"
[[ "$pinned_code_sha256" =~ ^[0-9a-f]{64}$ ]] || die "launch manifest pin is malformed"
[[ "$pinned_manifest_name" == "V023-100E-LAUNCH-MANIFEST.sha256" ]] || die "launch manifest pin names the wrong file"
read -r code_sha256 _ < <(sha256sum "$launch_manifest")
[[ "$code_sha256" == "$pinned_code_sha256" ]] || die "launch manifest disagrees with its external pin"
"$local_python" - "$repo_root" "$launch_manifest" "$contract" "$model_config" "$provider_config" "$output_root" "$code_sha256" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys

repo, manifest, contract, model, provider, output = map(Path, sys.argv[1:7])
manifest_sha = sys.argv[7]
digest_re = re.compile(r"^[0-9a-f]{64}$")
expected = {
    "contract": "5b84ac3b857fba6717c4c9ca34e48ed433a2945fbbc1006b8619db2ca60d6932",
    "model": "81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7",
    "provider": "c6c8dc6347a838bd4e437f73127929a8594c3e1aa66ca060a33a8bcb659583ba",
}

def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"missing or symlinked file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()

if output != Path("/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2"):
    raise SystemExit("output root is not the frozen exact path")
if not digest_re.fullmatch(manifest_sha):
    raise SystemExit("launch manifest digest is malformed")
if sha(manifest) != manifest_sha:
    raise SystemExit("launch manifest digest drifted")
lines = manifest.read_text(encoding="ascii").splitlines()
if not lines:
    raise SystemExit("launch manifest is empty")
seen = set()
for line in lines:
    parts = line.split("  ")
    if len(parts) != 2 or not digest_re.fullmatch(parts[0]):
        raise SystemExit("launch manifest line is malformed")
    relative = parts[1]
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts or "\\" in relative or relative in seen:
        raise SystemExit(f"unsafe or repeated launch path: {relative}")
    seen.add(relative)
    if sha(repo / path) != parts[0]:
        raise SystemExit(f"launch manifest entry drifted: {relative}")
required = {
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.sha256",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-POST-R7-PROVIDER-CONFIG.json",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-POST-R7-PROVIDER-CONFIG.sha256",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/verify_v023_100e_source_training.py",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/test_v023_100e_source_training_server.py",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py",
    ".scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py",
}
if required - seen:
    raise SystemExit("launch manifest omits required 100E bindings: " + ", ".join(sorted(required - seen)))
for key, path in {"contract": contract, "model": model, "provider": provider}.items():
    actual = sha(path)
    if actual != expected[key]:
        raise SystemExit(f"{key} digest drifted: {actual}")
    sidecar = path.with_suffix(".sha256")
    if sidecar.read_text(encoding="ascii") != f"{actual}  {path.name}\n":
        raise SystemExit(f"{key} digest sidecar drifted")
provider_payload = json.loads(provider.read_text(encoding="ascii"))
if provider.read_bytes() != (json.dumps(provider_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii"):
    raise SystemExit("provider config is not canonical JSON")
if provider_payload != {
    "epoch_budget": 100,
    "r7_code_root": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4",
    "r7_root": "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1",
    "schedule_seed": 1113171504590631764,
    "schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2",
    "target_root": "/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8",
}:
    raise SystemExit("provider config values drifted")
model_payload = json.loads(model.read_text(encoding="utf-8"))
if not isinstance(model_payload, dict) or set(model_payload) != {"q1", "q2", "q3"}:
    raise SystemExit("V2 model config must expose separate q1, q2, and q3 records")
if model_payload["q1"].get("state_dim") != 228 or model_payload["q1"].get("action_dim") != 28:
    raise SystemExit("Q1 model config is not the 228-D action-shared form")
if model_payload["q2"].get("action_dim") != 28 or model_payload["q2"].get("local_feature_dim") != 16 or model_payload["q2"].get("global_feature_dim") != 0:
    raise SystemExit("Q2 model config is not the 28-action/16-local-feature OPS-3 form")
if model_payload["q2"].get("hidden_layers") != [100, 50, 50] or model_payload["q2"].get("activation") != "tanh":
    raise SystemExit("Q2 model config head drifted")
print("V023_100E_LOCAL_MANIFEST_CONFIG_PASS")
PY

# Read the authenticated config field locally.  Its equality to the launcher
# override is checked on the server by resolving both existing paths strictly;
# dry-run deliberately makes no remote call.
configured_r7_code_root=$("$local_python" - "$provider_config" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="ascii"))
value = payload.get("r7_code_root")
if not isinstance(value, str) or not Path(value).is_absolute():
    raise SystemExit("provider config r7_code_root is missing or invalid")
print(value)
PY
) || die "provider config r7_code_root could not be read"

if ((dry_run)); then
  printf 'V023_100E_SOURCE_TRAINING_DRY_RUN_PASS server=%s checkout=%s output=%s tmux=%s code_sha256=%s\n' \
    "$server_host" "$server_root" "$output_root" "$tmux_session" "$code_sha256"
  exit 0
fi

# Expand the authenticated manifest into an explicit transfer list.  The
# complete R7 checkout is seeded separately below because this 100E manifest
# intentionally binds the new learner seam rather than duplicating the R7
# 166-file closure.
mapfile -t sync_paths < <("$local_python" - "$launch_manifest" <<'PY'
from pathlib import Path
import sys

manifest = Path(sys.argv[1])
for line in manifest.read_text(encoding="ascii").splitlines():
    _, relative = line.split("  ", 1)
    print(relative)
PY
)
sync_paths+=("$manifest_relative")
for relative in "${sync_paths[@]}"; do
  [[ "$relative" != /* && "$relative" != *..* && "$relative" != *'\\'* ]] || die "unsafe sync path: $relative"
  [[ -f "$repo_root/$relative" && ! -L "$repo_root/$relative" ]] || die "sync dependency missing or symlinked: $relative"
done

check_remote_absent() {
  local label=$1 predicate=$2 status=0
  ssh -- "$server_host" "$predicate" >/dev/null 2>&1 || status=$?
  case "$status" in
    0) die "remote $label already exists" ;;
    1) : ;;
    *) die "remote $label existence check failed (ssh status $status)" ;;
  esac
}

ssh -- "$server_host" "test -d '$r7_seed_root' && test ! -L '$r7_seed_root'" \
  || die "complete R7 seed checkout is unavailable: $server_host:$r7_seed_root"

# Verify the two prerequisite roots before creating this launch checkout.
# Only their terminal seal and whole-tree hashes are read here; factory
# preflight is the component that reads their authenticated result payloads.
ssh -- "$server_host" "$server_python - '$r7_seed_root' '$server_root' '$output_root' '$r7_result_root' '$target_root' '$configured_r7_code_root'" <<'PY'
import hashlib
from pathlib import Path
import sys

seed, checkout, output, r7_result, target, configured_seed = map(Path, sys.argv[1:])
if seed.is_symlink() or not seed.is_dir():
    raise SystemExit("R7 seed checkout is missing or symlinked")
if configured_seed.is_symlink() or not configured_seed.is_dir():
    raise SystemExit("provider-config R7 code root is missing or symlinked")
if seed.resolve(strict=True) != configured_seed.resolve(strict=True):
    raise SystemExit("resolved R7 seed root disagrees with provider config r7_code_root")

def verify_sealed(root: Path, label: str) -> None:
    if root.is_symlink() or not root.is_dir():
        raise SystemExit(f"{label} root is missing or symlinked")
    complete = root / "COMPLETE"
    manifest = root / "MANIFEST.sha256"
    failed = root / "FAILED"
    for path in (complete, manifest):
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"{label} seal file is missing or symlinked: {path}")
    if failed.exists() or failed.is_symlink():
        raise SystemExit(f"{label} root is FAILED")
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if complete.read_text(encoding="ascii") != f"{manifest_sha}  MANIFEST.sha256\n":
        raise SystemExit(f"{label} COMPLETE is not bound to MANIFEST.sha256")
    listed = set()
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ")
        if len(parts) != 2 or len(parts[0]) != 64:
            raise SystemExit(f"{label} manifest line is malformed")
        relative = Path(parts[1])
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in listed:
            raise SystemExit(f"{label} manifest path is unsafe or repeated")
        target = root / relative
        if target.is_symlink() or not target.is_file():
            raise SystemExit(f"{label} manifest names a missing or symlinked file")
        if hashlib.sha256(target.read_bytes()).hexdigest() != parts[0]:
            raise SystemExit(f"{label} manifest hash mismatch: {relative}")
        listed.add(relative.as_posix())
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"{label} root contains a symlink: {path}")
        relative = path.relative_to(root).as_posix()
        if path.is_file() and relative not in {"MANIFEST.sha256", "COMPLETE"}:
            actual.add(relative)
    if listed != actual:
        raise SystemExit(f"{label} manifest does not cover its whole tree")

verify_sealed(r7_result, "R7")
verify_sealed(target, "C1C2")
resolved_paths = {
    seed.resolve(strict=True),
    checkout.resolve(strict=False),
    output.resolve(strict=False),
}
if len(resolved_paths) != 3:
    raise SystemExit("R7 seed, learner checkout, and output paths must resolve distinctly")
for path in (checkout, output):
    if path.exists() or path.is_symlink():
        raise SystemExit(f"future path already exists: {path}")
print("V023_100E_PREREQUISITE_SEALS_PASS")
PY

check_remote_absent "dedicated checkout" "test -e '$server_root' || test -L '$server_root'"
check_remote_absent "source-training output root" "test -e '$output_root' || test -L '$output_root'"
check_remote_absent "tmux session" "tmux has-session -t '$tmux_session' 2>/dev/null"
check_remote_absent "controller" "test -e '$remote_controller' || test -L '$remote_controller'"
check_remote_absent "startup marker" "test -e '$remote_startup_marker' || test -L '$remote_startup_marker'"

# Reauthenticate the immutable historical closure against the seed itself,
# before any successor learner bytes are overlaid into the new checkout.
ssh -- "$server_host" "PYTHONDONTWRITEBYTECODE=1 '$server_python' - '$r7_seed_root' '$r7_result_root/authority/R7-PREFLIGHT-MANIFEST.json' '$r7_result_root/authority/R7-PREFLIGHT-MANIFEST.sha256'" <<'PY'
from pathlib import Path
import subprocess
import sys

seed = Path(sys.argv[1])
manifest = Path(sys.argv[2])
digest = Path(sys.argv[3])
preflight = seed / ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py"
prereg = seed / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
seed_manifest = seed / ".scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json"
seed_digest = seed_manifest.with_name("R7-PREFLIGHT-MANIFEST.sha256")
for path in seed.rglob("*"):
    if path.is_symlink():
        raise SystemExit(f"R7 seed checkout contains a symlink: {path}")
for path in (manifest, digest, preflight, prereg, seed_manifest, seed_digest):
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"R7 seed closure file is missing or symlinked: {path}")
if seed_manifest.read_bytes() != manifest.read_bytes():
    raise SystemExit("R7 seed preflight manifest differs from sealed authority bytes")
if seed_digest.read_bytes() != digest.read_bytes():
    raise SystemExit("R7 seed preflight digest differs from sealed authority bytes")
command = [sys.executable, str(preflight), "--manifest", str(manifest), "--manifest-digest", str(digest), "--repo", str(seed), "--prereg", str(prereg)]
subprocess.run(command, cwd=seed, check=True, stdout=subprocess.DEVNULL)
print("V023_100E_R7_SEED_CLOSURE_PASS")
PY

ssh -- "$server_host" "mkdir -- '$server_root'"
# The seed is the already-authenticated complete R7 checkout.  Copying its
# contents into the new root keeps the original checkout read-only and gives
# the post-R7 factory all 166 R7 preflight bindings plus their runtime files.
ssh -- "$server_host" "cp -a -- '$r7_seed_root/.' '$server_root/'"

# Overlay only the successor learner-manifest entries, then authenticate every
# entry in a separate process before importing factory or runner code.
rsync -aR --exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/' \
  "${sync_paths[@]}" "$server_host:$server_root/"
ssh -- "$server_host" "PYTHONDONTWRITEBYTECODE=1 '$server_python' - '$server_root' '$remote_manifest' '$code_sha256'" <<'PY'
import hashlib
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve(strict=True)
manifest = Path(sys.argv[2])
expected_manifest_sha = sys.argv[3]
digest_re = re.compile(r"^[0-9a-f]{64}$")
if root.is_symlink() or not root.is_dir():
    raise SystemExit("learner checkout is missing or symlinked")
if manifest.is_symlink() or not manifest.is_file():
    raise SystemExit("learner launch manifest is missing or symlinked")
if not digest_re.fullmatch(expected_manifest_sha):
    raise SystemExit("learner launch-manifest digest is malformed")
if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected_manifest_sha:
    raise SystemExit("learner launch-manifest digest drifted")
for path in root.rglob("*"):
    if path.is_symlink():
        raise SystemExit(f"learner checkout contains a symlink: {path}")
seen = set()
for line in manifest.read_text(encoding="ascii").splitlines():
    parts = line.split("  ")
    if len(parts) != 2 or not digest_re.fullmatch(parts[0]):
        raise SystemExit("learner launch-manifest line is malformed")
    declared, relative_text = parts
    relative = Path(relative_text)
    if (
        not relative_text
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in relative_text
        or relative_text in seen
    ):
        raise SystemExit(f"learner launch-manifest path is unsafe or repeated: {relative_text}")
    candidate = root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise SystemExit(f"learner launch-manifest entry is missing or symlinked: {relative_text}")
    if not candidate.resolve(strict=True).is_relative_to(root):
        raise SystemExit(f"learner launch-manifest entry escapes checkout: {relative_text}")
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != declared:
        raise SystemExit(f"learner launch-manifest entry drifted: {relative_text}")
    seen.add(relative_text)
if not seen:
    raise SystemExit("learner launch manifest is empty")
print(f"V023_100E_LEARNER_MANIFEST_PASS entries={len(seen)}")
PY

# Perform the exact factory preflight and then validate every receipt field in
# a second remote Python process.  The split keeps failures identifiable and
# avoids treating a missing receipt as a GO.
ssh -- "$server_host" "set -Eeuo pipefail; cd '$server_root'; export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH='$server_root/src:$server_root:$server_root/.scratch/multi-catfish-v023-post-r7-provider-factory'; '$server_python' '$remote_preflight' --repo '$server_root' --manifest '$remote_manifest' --manifest-sha256 '$code_sha256' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --contract '$remote_contract' --output-root '$output_root' --receipt '$remote_receipt' >/dev/null" \
  || die "factory/preflight exact GO failed"
input_sha256=$(ssh -- "$server_host" "$server_python - '$remote_receipt' '$remote_receipt_digest' '$remote_manifest' '$remote_contract' '$remote_model_config' '$remote_provider_config' '$output_root' '$code_sha256' '$expected_contract_sha256' '$expected_model_config_sha256' '$expected_provider_config_sha256' '$expected_schedule_seed' '$configured_r7_code_root'" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys

receipt_path, receipt_digest_path, manifest_path, contract_path, model_path, provider_path, output_root, code_sha, contract_sha, model_sha, provider_sha, schedule_seed, r7_code_root = sys.argv[1:]
receipt_file = Path(receipt_path)
receipt_sidecar = Path(receipt_digest_path)
if receipt_file.is_symlink() or not receipt_file.is_file() or receipt_sidecar.is_symlink() or not receipt_sidecar.is_file():
    raise SystemExit("100E preflight receipt is missing or symlinked")
receipt_raw = receipt_file.read_bytes()
receipt = json.loads(receipt_raw.decode("ascii"))
canonical = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
if receipt_raw != canonical:
    raise SystemExit("100E preflight receipt is not canonical JSON")
receipt_digest = hashlib.sha256(receipt_raw).hexdigest()
if receipt_sidecar.read_text(encoding="ascii") != f"{receipt_digest}  {receipt_file.name}\n":
    raise SystemExit("100E preflight receipt digest sidecar disagrees")
expected = {
    "schema": "multi-catfish-mcrl-v023-100e-source-training-preflight-v2",
    "status": "PASS_FROZEN_PREOUTCOME_100E_PREFLIGHT",
    "epoch_budget": 100,
    "route_updates": 300,
    "checkpoint_epochs": [100],
    "train_seed": 2927175120652069826,
    "schedule_seed": int(schedule_seed),
    "source_split": "SOURCE_TRAIN",
    "test_split_opened": False,
    "simulator_episode_opened": False,
    "authority_sha256": contract_sha,
    "code_sha256": code_sha,
    "output_root": str(output_root),
}
for key, value in expected.items():
    if receipt.get(key) != value:
        raise SystemExit(f"100E preflight field drifted: {key}")
if not isinstance(receipt.get("input_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["input_sha256"]):
    raise SystemExit("100E preflight input_sha256 is malformed")
if receipt.get("claim_ceiling") != "TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_ONLY_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY":
    raise SystemExit("100E preflight claim ceiling drifted")
binding = receipt.get("input_binding")
if not isinstance(binding, dict):
    raise SystemExit("100E preflight input binding is missing")
if binding.get("schema") != "multi-catfish-mcrl-v023-100e-source-training-preflight-v2-input-binding":
    raise SystemExit("100E preflight input binding schema drifted")
if binding.get("provider_config_sha256") != provider_sha or binding.get("model_config_sha256") != model_sha:
    raise SystemExit("100E preflight input configuration digest drifted")
provider_payload = binding.get("provider_identity_payload")
provider_fields = {
    "schema", "target_manifest_sha256", "c3_schedule_receipt_sha256",
    "epoch_budget", "c3_source_ids", "r7_code_root",
    "r7_preflight_manifest_sha256", "r7_code_manifest_sha256",
    "r7_result_manifest_sha256", "r7_gate_result_sha256",
    "r7_authentication_runtime_sha256", "r7_authentication_runtime",
}
if not isinstance(provider_payload, dict) or set(provider_payload) != provider_fields:
    raise SystemExit("100E preflight provider identity payload field set drifted")
if provider_payload.get("schema") != "multi-catfish-mcrl-v023-post-r7-provider-identity-v2":
    raise SystemExit("100E preflight provider identity schema drifted")
if provider_payload.get("epoch_budget") != 100:
    raise SystemExit("100E preflight provider identity epoch budget drifted")
if provider_payload.get("r7_code_root") != r7_code_root:
    raise SystemExit("100E preflight provider r7_code_root drifted")
source_ids = provider_payload.get("c3_source_ids")
if (
    not isinstance(source_ids, dict)
    or set(source_ids) != {"neutral", "informed"}
    or any(not isinstance(value, str) or not value for value in source_ids.values())
    or source_ids["neutral"] == source_ids["informed"]
):
    raise SystemExit("100E preflight provider C3 source IDs drifted")
for field in (
    "target_manifest_sha256", "c3_schedule_receipt_sha256",
    "r7_preflight_manifest_sha256", "r7_code_manifest_sha256",
    "r7_result_manifest_sha256", "r7_gate_result_sha256",
    "r7_authentication_runtime_sha256",
):
    if not isinstance(provider_payload.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", provider_payload[field]):
        raise SystemExit(f"100E preflight provider digest drifted: {field}")
runtime = provider_payload.get("r7_authentication_runtime")
runtime_paths = (
    ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py",
    ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py",
    ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py",
    "src/mcrl/__init__.py",
    "src/mcrl/errors.py",
    "src/mcrl/algorithms/__init__.py",
    "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py",
    "src/mcrl/env/__init__.py",
    "src/mcrl/env/action_contract.py",
    "src/mcrl/runtime/__init__.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_dataset.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_fit.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_metrics.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_learner.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_state.py",
    "src/mcrl/runtime/finiteness.py",
)
if (
    not isinstance(runtime, list)
    or any(not isinstance(item, dict) or set(item) != {"path", "sha256"} for item in runtime)
    or [item["path"] for item in runtime] != list(runtime_paths)
    or any(not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in runtime)
):
    raise SystemExit("100E preflight provider authentication runtime drifted")
compact_runtime = json.dumps(runtime, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
if hashlib.sha256(compact_runtime).hexdigest() != provider_payload["r7_authentication_runtime_sha256"]:
    raise SystemExit("100E preflight provider authentication runtime digest disagrees")
compact_provider = json.dumps(provider_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
expected_identity = "multi-catfish-mcrl-v023-post-r7-provider-factory-v2:" + hashlib.sha256(compact_provider).hexdigest()
if binding.get("provider_identity") != expected_identity:
    raise SystemExit("100E preflight provider identity does not bind its payload")
compact_binding = (json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
if hashlib.sha256(compact_binding).hexdigest() != receipt["input_sha256"]:
    raise SystemExit("100E preflight input_sha256 does not bind its input payload")
if hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest() != code_sha:
    raise SystemExit("100E preflight launch manifest digest drifted")
for path, expected_sha in ((contract_path, contract_sha), (model_path, model_sha), (provider_path, provider_sha)):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_sha:
        raise SystemExit(f"100E preflight configuration hash drifted: {path}")
print(receipt["input_sha256"])
PY
) || die "factory/preflight exact GO failed"
[[ "$input_sha256" =~ ^[0-9a-f]{64}$ ]] || die "remote preflight returned malformed input sha256"

# The one-epoch diagnostic is a mandatory non-formal execution gate.  Its root
# must be fresh, and it runs as a new process inside the learner checkout with
# the exact environment used by the factory preflight above.
diagnostic_root_status=0
ssh -- "$server_host" "test -e '$remote_diagnostic_root' || test -L '$remote_diagnostic_root'" >/dev/null 2>&1 \
  || diagnostic_root_status=$?
case "$diagnostic_root_status" in
  0) die "one-epoch provider diagnostic root already exists; failed_checks=[diagnostic_root_not_absent]" ;;
  1) : ;;
  *) die "one-epoch provider diagnostic root absence check failed (ssh status $diagnostic_root_status); failed_checks=[diagnostic_root_absence_check]" ;;
esac
diagnostic_summary=$(ssh -- "$server_host" "set -Eeuo pipefail; cd '$server_root'; export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH='$server_root/src:$server_root:$server_root/.scratch/multi-catfish-v023-post-r7-provider-factory'; '$server_python' '$remote_diagnostic' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --output-root '$remote_diagnostic_root'" 2>&1) \
  || die "one-epoch provider diagnostic execution failed; failed_checks=${diagnostic_summary:-unavailable}"
diagnostic_validation=$(ssh -- "$server_host" "$server_python - '$remote_diagnostic_receipt' '$remote_diagnostic_receipt_digest' '$remote_receipt'" 2>&1 <<'PY'
import hashlib
import json
from pathlib import Path
import sys

diagnostic_path, diagnostic_digest_path, preflight_path = map(Path, sys.argv[1:])
failed_checks = "unreadable"

def fail(message: str) -> None:
    raise SystemExit(f"{message}; failed_checks={failed_checks!r}")

if (
    diagnostic_path.is_symlink()
    or not diagnostic_path.is_file()
    or diagnostic_digest_path.is_symlink()
    or not diagnostic_digest_path.is_file()
):
    fail("one-epoch provider diagnostic receipt or sidecar is missing or symlinked")
raw = diagnostic_path.read_bytes()
try:
    receipt = json.loads(raw.decode("ascii"))
except (UnicodeDecodeError, json.JSONDecodeError) as error:
    fail(f"one-epoch provider diagnostic receipt is unreadable: {error}")
failed_checks = receipt.get("failed_checks")
canonical = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
if raw != canonical:
    fail("one-epoch provider diagnostic receipt is not canonical JSON")
digest = hashlib.sha256(raw).hexdigest()
if diagnostic_digest_path.read_text(encoding="ascii") != f"{digest}  {diagnostic_path.name}\n":
    fail("one-epoch provider diagnostic receipt sidecar disagrees")
if receipt.get("status") != "PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC":
    fail("one-epoch provider diagnostic status is not PASS")
if failed_checks != []:
    fail("one-epoch provider diagnostic reported failed checks")
try:
    preflight = json.loads(preflight_path.read_text(encoding="ascii"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
    fail(f"100E preflight receipt cannot be reread: {error}")
binding = preflight.get("input_binding")
expected_identity = binding.get("provider_identity") if isinstance(binding, dict) else None
if not isinstance(expected_identity, str) or not expected_identity:
    fail("100E preflight provider identity is missing")
if receipt.get("provider_identity") != expected_identity:
    fail("one-epoch provider identity disagrees with 100E preflight")
print(f"V023_100E_ONE_EPOCH_DIAGNOSTIC_PASS provider_identity={expected_identity}")
PY
) || die "one-epoch provider diagnostic receipt validation failed; failed_checks=${diagnostic_validation:-unavailable}"
[[ "$diagnostic_validation" == V023_100E_ONE_EPOCH_DIAGNOSTIC_PASS\ provider_identity=* ]] \
  || die "one-epoch provider diagnostic validation returned an unexpected acknowledgement; failed_checks=[diagnostic_acknowledgement]"

# Build a write-once server controller.  The controller is the only process
# that invokes the source runner.  Its ERR trap writes a terminal FAILED
# receipt whenever the runner has created the exact output root; the final
# verifier writes COMPLETE only after its independent provider/runner audit.
ssh -- "$server_host" "$server_python - '$remote_controller' '$server_root' '$output_root' '$remote_manifest' '$remote_contract' '$remote_model_config' '$remote_provider_config' '$remote_preflight' '$remote_sealer' '$remote_receipt' '$code_sha256' '$expected_contract_sha256' '$input_sha256' '$expected_train_seed' '$expected_provider_config_sha256' '$remote_startup_marker'" <<'PY'
import os
from pathlib import Path
import sys

target, checkout, output, manifest, contract, model, provider, preflight, sealer, preflight_receipt, code_sha, authority_sha, input_sha, train_seed, provider_config_sha, startup_marker = sys.argv[1:]
body = f'''#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
CHECKOUT={checkout!r}
RUN_ROOT={output!r}
MANIFEST={manifest!r}
CONTRACT={contract!r}
MODEL_CONFIG={model!r}
PROVIDER_CONFIG={provider!r}
PROVIDER_CONFIG_SHA256={provider_config_sha!r}
STARTUP_MARKER={startup_marker!r}
PREFLIGHT={preflight!r}
SEALER={sealer!r}
PREFLIGHT_RECEIPT={preflight_receipt!r}
PYTHON={sys.executable!r}
CODE_SHA256={code_sha!r}
AUTHORITY_SHA256={authority_sha!r}
INPUT_SHA256={input_sha!r}
TRAIN_SEED={train_seed!r}
FACTORY_SPEC=v023_post_r7_provider_factory_v2:make_provider
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$CHECKOUT/src:$CHECKOUT:$CHECKOUT/.scratch/multi-catfish-v023-post-r7-provider-factory"
export MCRL_V023_POST_R7_PROVIDER_CONFIG_PATH="$PROVIDER_CONFIG"
export MCRL_V023_POST_R7_PROVIDER_CONFIG_SHA256="$PROVIDER_CONFIG_SHA256"
exec >>"$CHECKOUT/v023-100e-source-training-controller.log" 2>&1

write_failed() {{
  status=$?
  trap - ERR
  command_text=${{BASH_COMMAND:-unknown}}
  if [[ -d "$RUN_ROOT" && ! -L "$RUN_ROOT" && ! -e "$RUN_ROOT/COMPLETE" && ! -e "$RUN_ROOT/FAILED" ]]; then
    "$PYTHON" - "$RUN_ROOT" "$status" "$command_text" <<'PYFAIL'
import hashlib
import json
import os
from pathlib import Path
import sys

root = Path(sys.argv[1])
marker = root / "FAILED"
if root.is_dir() and not root.is_symlink() and not marker.exists() and not marker.is_symlink() and not (root / "COMPLETE").exists():
    reason = " ".join(sys.argv[3].split())[:1000] or "source-training controller failed"
    payload = {{"schema": "multi-catfish-mcrl-v023-100e-source-training-failure-v1", "status": "FAILED_SOURCE_TRAINING_INTEGRITY", "exit_status": int(sys.argv[2]), "reason": reason}}
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\\n").encode("ascii")
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
PYFAIL
  fi
  exit "$status"
}}
trap write_failed ERR

# Write-once startup marker: the launcher acknowledges controller startup only
# after this file exists together with a live tmux session.
"$PYTHON" - "$STARTUP_MARKER" "$RUN_ROOT" "$CHECKOUT" <<'PYSTART'
import json
import os
import sys
import time

marker, run_root, checkout = sys.argv[1:4]
payload = {{"schema": "multi-catfish-mcrl-v023-100e-source-training-startup-v1", "status": "CONTROLLER_STARTED", "controller_pid": os.getppid(), "run_root": run_root, "checkout": checkout, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}}
data = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\\n").encode("ascii")
fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as stream:
    stream.write(data)
    stream.flush()
    os.fsync(stream.fileno())
PYSTART

"$PYTHON" "$CHECKOUT/.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py" \\
  --output-root "$RUN_ROOT" --epochs 100 --provider-factory "$FACTORY_SPEC" \\
  --model-config-json "$MODEL_CONFIG" --train-seed "$TRAIN_SEED" \\
  --authority-sha256 "$AUTHORITY_SHA256" --code-sha256 "$CODE_SHA256" \\
  --input-sha256 "$INPUT_SHA256" --source-split SOURCE_TRAIN --execute

"$PYTHON" "$SEALER" --repo "$CHECKOUT" --output-root "$RUN_ROOT" \\
  --launch-manifest "$MANIFEST" --launch-manifest-sha256 "$CODE_SHA256" \\
  --provider-config "$PROVIDER_CONFIG" --model-config "$MODEL_CONFIG" \\
  --contract "$CONTRACT" --authority-sha256 "$AUTHORITY_SHA256" \\
  --code-sha256 "$CODE_SHA256" --input-sha256 "$INPUT_SHA256" \\
  --preflight-receipt "$PREFLIGHT_RECEIPT"
'''
target_path = Path(target)
if target_path.exists() or target_path.is_symlink():
    raise SystemExit("controller path already exists")
fd = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
with os.fdopen(fd, "w", encoding="ascii", newline="") as stream:
    stream.write(body)
PY

ssh -- "$server_host" "set -Eeuo pipefail; test -x '$remote_controller'; bash -n '$remote_controller'; '$server_python' -m py_compile '$remote_runner' '$remote_factory' '$remote_preflight' '$remote_sealer'; test ! -e '$remote_log' && test ! -L '$remote_log'; tmux new-session -d -s '$tmux_session' '$remote_controller'"
# Bounded remote startup acknowledgement: at most 120 s for the write-once
# startup marker plus a live tmux session.  tmux creation alone is not enough.
acknowledged=0
for _ in $(seq 1 24); do
  if ssh -- "$server_host" "test -f '$remote_startup_marker' && tmux has-session -t '$tmux_session' 2>/dev/null" >/dev/null 2>&1; then
    acknowledged=1
    break
  fi
  sleep 5
done
((acknowledged)) || die "controller startup was not acknowledged within 120 s: marker=$remote_startup_marker session=$tmux_session (inspect $remote_log)"
startup_json=$(ssh -- "$server_host" "cat '$remote_startup_marker'")
printf 'V023_100E_SOURCE_TRAINING_STARTUP_ACKNOWLEDGED %s\n' "$startup_json"
printf 'V023_100E_SOURCE_TRAINING_LAUNCHED server=%s checkout=%s output=%s tmux=%s code_sha256=%s input_sha256=%s\n' \
  "$server_host" "$server_root" "$output_root" "$tmux_session" "$code_sha256" "$input_sha256"
