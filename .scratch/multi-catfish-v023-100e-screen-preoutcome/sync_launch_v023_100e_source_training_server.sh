#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare a fresh Ubuntu-server checkout and launch exactly one 100-epoch
# source-training run.  The command below does not start a run in this
# repository: it first authenticates the sealed R7 and C1/C2 roots, copies a
# complete R7 checkout as an immutable dependency seed, reruns the 100E
# factory preflight, and only then creates one tmux session.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "${script_dir}/../.." && pwd -P)
server_host=${V023_SERVER_HOST:-sat}
server_root=${V023_SERVER_ROOT:-/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1-checkout}
r7_seed_root=${V023_R7_SEED_ROOT:-/home/sat/mcrl-v023-r7-launch-ready-20260906-r4}
output_root=/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1
tmux_session=${V023_TMUX_SESSION:-mcrl-v023-five-arm-source-training-20260907-100e-r1}
local_python=${V023_LOCAL_PYTHON:-${repo_root}/.venv/bin/python}
server_python=${V023_SERVER_PYTHON:-/home/sat/mcrl-leo-handover/.venv/bin/python}

package_relative=.scratch/multi-catfish-v023-100e-screen-preoutcome
package=${repo_root}/${package_relative}
launch_manifest=${package}/V023-100E-LAUNCH-MANIFEST.sha256
launch_manifest_pin=${package}/V023-100E-LAUNCH-MANIFEST-FROZEN.sha256
contract=${package}/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md
model_config=${package}/V023-100E-MODEL-CONFIG.json
provider_config=${package}/V023-100E-POST-R7-PROVIDER-CONFIG.json
preflight=${package}/preflight_v023_100e_source_training.py
sealer=${package}/verify_v023_100e_source_training.py
launcher=${package}/sync_launch_v023_100e_source_training_server.sh
runner_relative=.scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py
factory_relative=.scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py
runner=${repo_root}/${runner_relative}
factory=${repo_root}/${factory_relative}
manifest_relative=${package_relative}/V023-100E-LAUNCH-MANIFEST.sha256
remote_manifest=${server_root}/${manifest_relative}
remote_contract=${server_root}/${package_relative}/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md
remote_model_config=${server_root}/${package_relative}/V023-100E-MODEL-CONFIG.json
remote_provider_config=${server_root}/${package_relative}/V023-100E-POST-R7-PROVIDER-CONFIG.json
remote_preflight=${server_root}/${package_relative}/preflight_v023_100e_source_training.py
remote_sealer=${server_root}/${package_relative}/verify_v023_100e_source_training.py
remote_runner=${server_root}/${runner_relative}
remote_factory=${server_root}/${factory_relative}
remote_receipt=${server_root}/${package_relative}/PREFLIGHT-RECEIPT.json
remote_receipt_digest=${remote_receipt}.sha256
remote_controller=${server_root}/v023-100e-source-training-controller.sh
remote_log=${server_root}/v023-100e-source-training-controller.log

expected_contract_sha256=7f417ca66d935ba3748dc7204a0ee241ad70ff491ed6cdae69a92e7f71ae20b6
expected_model_config_sha256=2fab1e4a0b61bf88a428709815d078d9b613b06b645c4d9cef7e46b2220b78ec
expected_provider_config_sha256=939582ffb8537eef865c1a71d8c324ad475059a0d96dd29e36da39ea18ee9f7b
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
launch one source-training controller in tmux.  --dry-run performs only local
manifest/configuration checks and never contacts the server.
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
[[ "$output_root" == "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1" ]] || die "output root drifted"
[[ "$server_root" != "$output_root" ]] || die "checkout and output root must be distinct"
[[ "$tmux_session" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe tmux session"
for path in "$launch_manifest" "$launch_manifest_pin" "$contract" "$model_config" "$provider_config" "$preflight" "$sealer" "$launcher" "$runner" "$factory"; do
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
    "contract": "7f417ca66d935ba3748dc7204a0ee241ad70ff491ed6cdae69a92e7f71ae20b6",
    "model": "2fab1e4a0b61bf88a428709815d078d9b613b06b645c4d9cef7e46b2220b78ec",
    "provider": "939582ffb8537eef865c1a71d8c324ad475059a0d96dd29e36da39ea18ee9f7b",
}

def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"missing or symlinked file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()

if output != Path("/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1"):
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
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-MODEL-CONFIG.json",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-MODEL-CONFIG.sha256",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-POST-R7-PROVIDER-CONFIG.json",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-POST-R7-PROVIDER-CONFIG.sha256",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/preflight_v023_100e_source_training.py",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/verify_v023_100e_source_training.py",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/sync_launch_v023_100e_source_training_server.sh",
    ".scratch/multi-catfish-v023-100e-screen-preoutcome/test_v023_100e_source_training_server.py",
    ".scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py",
    ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py",
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
    "r7_root": "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1",
    "schedule_seed": 1113171504590631764,
    "schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v1",
    "target_root": "/home/sat/mcrl-v023-c1c2-targets-20260906-d40-r4",
}:
    raise SystemExit("provider config values drifted")
print("V023_100E_LOCAL_MANIFEST_CONFIG_PASS")
PY

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
ssh -- "$server_host" "$server_python - '$r7_seed_root' '$server_root' '$output_root'" <<'PY'
import hashlib
from pathlib import Path
import sys

seed, checkout, output = map(Path, sys.argv[1:])
if seed.is_symlink() or not seed.is_dir():
    raise SystemExit("R7 seed checkout is missing or symlinked")
for path in (checkout, output):
    if path.exists() or path.is_symlink():
        raise SystemExit(f"future path already exists: {path}")

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

verify_sealed(Path("/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1"), "R7")
verify_sealed(Path("/home/sat/mcrl-v023-c1c2-targets-20260906-d40-r4"), "C1C2")
print("V023_100E_PREREQUISITE_SEALS_PASS")
PY

check_remote_absent "dedicated checkout" "test -e '$server_root' || test -L '$server_root'"
check_remote_absent "source-training output root" "test -e '$output_root' || test -L '$output_root'"
check_remote_absent "tmux session" "tmux has-session -t '$tmux_session' 2>/dev/null"
check_remote_absent "controller" "test -e '$remote_controller' || test -L '$remote_controller'"

ssh -- "$server_host" "mkdir -- '$server_root'"
# The seed is the already-authenticated complete R7 checkout.  Copying its
# contents into the new root keeps the original checkout read-only and gives
# the post-R7 factory all 166 R7 preflight bindings plus their runtime files.
ssh -- "$server_host" "cp -a -- '$r7_seed_root/.' '$server_root/'"
rsync -aR --exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/' \
  "${sync_paths[@]}" "$server_host:$server_root/"

# Reauthenticate the copied R7 closure and the current launch manifest in the
# dedicated root before any source-training output root is created.
ssh -- "$server_host" "PYTHONDONTWRITEBYTECODE=1 '$server_python' - '$server_root' '$server_root/.scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json'" <<'PY'
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1])
manifest = Path(sys.argv[2])
digest = manifest.with_name("R7-PREFLIGHT-MANIFEST.sha256")
preflight = root / ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py"
prereg = root / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
for path in root.rglob("*"):
    if path.is_symlink():
        raise SystemExit(f"dedicated checkout contains a symlink: {path}")
for path in (manifest, digest, preflight, prereg):
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"R7 seeded closure file is missing or symlinked: {path}")
command = [sys.executable, str(preflight), "--manifest", str(manifest), "--manifest-digest", str(digest), "--repo", str(root), "--prereg", str(prereg)]
subprocess.run(command, cwd=root, check=True, stdout=subprocess.DEVNULL)
print("V023_100E_R7_SEEDED_CLOSURE_PASS")
PY

# Perform the exact factory preflight and then validate every receipt field in
# a second remote Python process.  The split keeps failures identifiable and
# avoids treating a missing receipt as a GO.
ssh -- "$server_host" "set -Eeuo pipefail; cd '$server_root'; export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH='$server_root/src:$server_root:$server_root/.scratch/multi-catfish-v023-post-r7-provider-factory'; '$server_python' '$remote_preflight' --repo '$server_root' --manifest '$remote_manifest' --manifest-sha256 '$code_sha256' --provider-config '$remote_provider_config' --model-config '$remote_model_config' --contract '$remote_contract' --output-root '$output_root' --receipt '$remote_receipt' >/dev/null" \
  || die "factory/preflight exact GO failed"
input_sha256=$(ssh -- "$server_host" "$server_python - '$remote_receipt' '$remote_receipt_digest' '$remote_manifest' '$remote_contract' '$remote_model_config' '$remote_provider_config' '$output_root' '$code_sha256' '$expected_contract_sha256' '$expected_model_config_sha256' '$expected_provider_config_sha256' '$expected_schedule_seed'" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys

receipt_path, receipt_digest_path, manifest_path, contract_path, model_path, provider_path, output_root, code_sha, contract_sha, model_sha, provider_sha, schedule_seed = sys.argv[1:]
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
    "schema": "multi-catfish-mcrl-v023-100e-source-training-preflight-v1",
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
if binding.get("schema") != "multi-catfish-mcrl-v023-100e-source-training-preflight-v1-input-binding":
    raise SystemExit("100E preflight input binding schema drifted")
if binding.get("provider_config_sha256") != provider_sha or binding.get("model_config_sha256") != model_sha:
    raise SystemExit("100E preflight input configuration digest drifted")
if hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest() != code_sha:
    raise SystemExit("100E preflight launch manifest digest drifted")
for path, expected_sha in ((contract_path, contract_sha), (model_path, model_sha), (provider_path, provider_sha)):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_sha:
        raise SystemExit(f"100E preflight configuration hash drifted: {path}")
print(receipt["input_sha256"])
PY
) || die "factory/preflight exact GO failed"
[[ "$input_sha256" =~ ^[0-9a-f]{64}$ ]] || die "remote preflight returned malformed input sha256"

# Build a write-once server controller.  The controller is the only process
# that invokes the source runner.  Its ERR trap writes a terminal FAILED
# receipt whenever the runner has created the exact output root; the final
# verifier writes COMPLETE only after its independent provider/runner audit.
ssh -- "$server_host" "$server_python - '$remote_controller' '$server_root' '$output_root' '$remote_manifest' '$remote_contract' '$remote_model_config' '$remote_provider_config' '$remote_preflight' '$remote_sealer' '$remote_receipt' '$code_sha256' '$expected_contract_sha256' '$input_sha256' '$expected_train_seed' '$expected_provider_config_sha256'" <<'PY'
import os
from pathlib import Path
import sys

target, checkout, output, manifest, contract, model, provider, preflight, sealer, preflight_receipt, code_sha, authority_sha, input_sha, train_seed, provider_config_sha = sys.argv[1:]
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
PREFLIGHT={preflight!r}
SEALER={sealer!r}
PREFLIGHT_RECEIPT={preflight_receipt!r}
PYTHON={sys.executable!r}
CODE_SHA256={code_sha!r}
AUTHORITY_SHA256={authority_sha!r}
INPUT_SHA256={input_sha!r}
TRAIN_SEED={train_seed!r}
FACTORY_SPEC=v023_post_r7_provider_factory:make_provider
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
printf 'V023_100E_SOURCE_TRAINING_LAUNCHED server=%s checkout=%s output=%s tmux=%s code_sha256=%s input_sha256=%s\n' \
  "$server_host" "$server_root" "$output_root" "$tmux_session" "$code_sha256" "$input_sha256"
