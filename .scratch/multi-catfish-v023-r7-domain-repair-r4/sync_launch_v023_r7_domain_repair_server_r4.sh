#!/usr/bin/env bash
set -Eeuo pipefail

# Sync and launch the one integrity-only R7-I1 R4 verifier repair. The dry-run
# exits before every ssh/rsync/tmux path and therefore cannot contact a server.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
SERVER_HOST=${V023_SERVER_HOST:-sat}
SERVER_ROOT=/home/sat/mcrl-v023-r7-launch-ready-20260906-r4
RUN_ROOT=/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1
REMOTE_PACKAGE=$SERVER_ROOT/.scratch/multi-catfish-v023-r7-domain-repair-r4
SERVER_PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python
SESSION=mcrl-v023-r7-domain-repair-20260907-r4
LOG=/home/sat/mcrl-v023-r7-domain-repair-20260907-r4.log
MANIFEST=$SCRIPT_DIR/V023-R7-DOMAIN-REPAIR-R4-MANIFEST.sha256
MANIFEST_PIN=$SCRIPT_DIR/V023-R7-DOMAIN-REPAIR-R4-MANIFEST-FROZEN.sha256
DRY_RUN=false

die() { printf 'V023_R7_DOMAIN_REPAIR_R4_LAUNCH_FAILED: %s\n' "$*" >&2; exit 2; }

if (($#)); then
  [[ "$#" == 1 && "$1" == "--dry-run" ]] || die "only --dry-run is accepted"
  DRY_RUN=true
fi

[[ -f "$MANIFEST" && ! -L "$MANIFEST" ]] || die "R4 repair manifest is missing"
[[ -f "$MANIFEST_PIN" && ! -L "$MANIFEST_PIN" ]] || die "R4 repair manifest pin is missing"
manifest_sha=$(sha256sum "$MANIFEST" | awk '{print $1}')
read -r pinned_sha pinned_name < "$MANIFEST_PIN"
[[ "$pinned_sha" == "$manifest_sha" && "$pinned_name" == "$(basename -- "$MANIFEST")" ]] \
  || die "R4 repair manifest pin disagrees"

mapfile -t MEMBERS < <(awk -F '  ' '{print $2}' "$MANIFEST")
[[ "${#MEMBERS[@]}" == 5 ]] || die "R4 repair manifest must contain exactly five files"
expected=$'V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-R4-2026-09-07.md\nrun_v023_r7_domain_repair_server_r4.py\nsync_launch_v023_r7_domain_repair_server_r4.sh\ntest_v023_r7_domain_repair_r4.py\nverify_v023_lcsrs_final_domain_repair_r4.py'
actual=$(printf '%s\n' "${MEMBERS[@]}" | sort)
[[ "$actual" == "$expected" ]] || die "R4 repair manifest closure drifted"
for name in "${MEMBERS[@]}"; do
  [[ "$name" != */* && "$name" != .* ]] || die "unsafe R4 repair member: $name"
  [[ -f "$SCRIPT_DIR/$name" && ! -L "$SCRIPT_DIR/$name" ]] \
    || die "R4 repair member missing: $name"
done
(cd "$SCRIPT_DIR" && sha256sum -c "$(basename -- "$MANIFEST")" >/dev/null) \
  || die "local R4 repair manifest verification failed"
bash -n "$SCRIPT_DIR/sync_launch_v023_r7_domain_repair_server_r4.sh"
"$REPO/.venv/bin/python" -m py_compile \
  "$SCRIPT_DIR/verify_v023_lcsrs_final_domain_repair_r4.py" \
  "$SCRIPT_DIR/run_v023_r7_domain_repair_server_r4.py"

if [[ "$DRY_RUN" == true ]]; then
  printf 'V023_R7_DOMAIN_REPAIR_R4_DRY_RUN_PASS manifest_sha256=%s\n' "$manifest_sha"
  exit 0
fi

# Authenticate the unsealed root and all R1/R2/R3 failure evidence before the
# first additive R4 write (the package sync).
ssh -- "$SERVER_HOST" "$SERVER_PYTHON - '$SERVER_ROOT' '$RUN_ROOT' '$REMOTE_PACKAGE' '$LOG' '$SESSION'" <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys

checkout = Path(sys.argv[1])
root = Path(sys.argv[2])
package = Path(sys.argv[3])
log = Path(sys.argv[4])
session = sys.argv[5]

def regular(path):
    return not path.is_symlink() and path.is_file()

def digest(path):
    if not regular(path):
        raise SystemExit(f"expected regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()

previous_members = {
    "V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md",
    "run_v023_r7_domain_repair_server.py",
    "sync_launch_v023_r7_domain_repair_server.sh",
    "test_v023_r7_domain_repair.py",
    "verify_v023_lcsrs_final_domain_repair.py",
}

def verify_previous(authority, manifest_sha, pin_sha, label):
    manifest = authority / "V023-R7-DOMAIN-REPAIR-MANIFEST.sha256"
    pin = authority / "V023-R7-DOMAIN-REPAIR-MANIFEST-FROZEN.sha256"
    if digest(manifest) != manifest_sha or digest(pin) != pin_sha:
        raise SystemExit(f"{label} repair authority digest drifted")
    if pin.read_text(encoding="ascii").split() != [manifest_sha, manifest.name]:
        raise SystemExit(f"{label} repair manifest pin disagrees")
    members = set()
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise SystemExit(f"malformed {label} repair manifest line")
        member_sha, relative = parts
        member = Path(relative)
        if member.is_absolute() or ".." in member.parts or member.name != relative:
            raise SystemExit(f"unsafe {label} repair authority member")
        if relative in members or digest(authority / member) != member_sha:
            raise SystemExit(f"{label} repair authority drifted: {relative}")
        members.add(relative)
    if members != previous_members:
        raise SystemExit(f"{label} repair authority closure drifted")

if checkout.is_symlink() or not checkout.is_dir():
    raise SystemExit("frozen server checkout is unavailable")
if root.is_symlink() or not root.is_dir():
    raise SystemExit("R7-I1 root is unavailable")
invalid = root / "final-verification.json"
if digest(invalid) != "2b14fb95b9599b1c6abd50a63ab7adaaf61e31a8bbf448ada625b4242fd6a64f":
    raise SystemExit("original invalid verification digest drifted")
authority_path = root / "authority" / "AUTHORITY.json"
if not regular(authority_path):
    raise SystemExit("existing R7 authority receipt is unavailable")
authority = json.loads(authority_path.read_text(encoding="ascii"))
if authority.get("preflight_manifest_sha256") != "9b08e3acc1d1d9b0cf506c3137f8e4013345ed8fb6f54c385a312ddb8570772a":
    raise SystemExit("existing R7 authority preflight binding drifted")
entries = authority.get("entries", {})
if set(entries) != {"contract", "execution_addendum", "preflight_manifest", "preflight_manifest_digest"}:
    raise SystemExit("existing R7 authority closure drifted")
for role, binding in entries.items():
    relative = Path(str(binding.get("path", "")))
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not path.resolve().is_relative_to(root.resolve())
        or digest(path) != binding.get("sha256")
    ):
        raise SystemExit(f"existing R7 authority hash drifted: {role}")

verify_previous(
    root / "repair-authority",
    "e72b2cc566d0376c5c8d9bfafc3b28718fa757d4cab25f28f2b19703dd0b1f59",
    "1ec0296abf541748f463411567264a7a1f25368aa4115f6f6747dd7bcf9022f8",
    "R1",
)
r1_log = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r1.log")
if digest(r1_log) != "fe5eebb609be38e8ca16fc734e8464f97a370aea65c291f4d50d564292dc0419":
    raise SystemExit("R1 failure log drifted")
if "NPZ domain dispatch count drifted: {'source': 0, 'composition': 0}" not in r1_log.read_text(encoding="utf-8"):
    raise SystemExit("R1 zero-load failure signal is absent")

verify_previous(
    root / "repair-authority-r2",
    "e6f433eeafbe8bcbf43c81e241a60a2f428a8fdd06275f95e3e4a6f0fdfd710b",
    "bdfca2665b26ff134da05326498d2e28cb7313e2dff0584ec4a935d82b40b216",
    "R2",
)
r2_log = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r2.log")
if not regular(r2_log):
    raise SystemExit("R2 failure log is unavailable")
r2_text = r2_log.read_text(encoding="utf-8", errors="replace")
for marker in ("V023_R7_DOMAIN_REPAIR_FAILED:", "NPZ domain dispatch count drifted:"):
    if marker not in r2_text:
        raise SystemExit(f"R2 failure marker is absent: {marker}")

verify_previous(
    root / "repair-authority-r3",
    "4a1fb2ef124212757bdabe00bd578b5cd009977e9b4c64017b4a22ebe5990c90",
    "1da52c78556bc8a1c2c61d281aabc05172ed477eaff0de5b270ead0e5b139c61",
    "R3",
)
r3_log = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r3.log")
if r3_log.stat().st_size != 12279 or digest(r3_log) != "c76640b6b40068ad24def04d3eabcefc94d9a0ac2ba280254be4ff7a10b62fc4":
    raise SystemExit("R3 failure log size/digest drifted")
r3_text = r3_log.read_text(encoding="utf-8", errors="replace")
for marker in ("V023_R7_DOMAIN_REPAIR_FAILED:", "composition/source identity array missing: pair_source_key"):
    if marker not in r3_text:
        raise SystemExit(f"R3 failure marker is absent: {marker}")

for path in (
    root / "final-verification-domain-repair.json",
    root / "domain-repair-receipt.json",
    root / "final-verification-domain-repair-r2.json",
    root / "domain-repair-r2-receipt.json",
    root / "final-verification-domain-repair-r3.json",
    root / "domain-repair-r3-receipt.json",
):
    if path.exists() or path.is_symlink():
        raise SystemExit(f"unexpected previous corrected output exists: {path}")

markers = (
    "run_v023_lcsrs_full_gate_server.sh", "run_v023_lcsrs_source_server.py",
    "run_v023_lcsrs_fit_server.py", "run_v023_lcsrs_composition_server.py",
    "verify_v023_lcsrs_final.py",
)
for command_path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        command = command_path.read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace")
    except OSError:
        continue
    if root.as_posix() in command and any(marker in command for marker in markers):
        raise SystemExit(f"R7 writer is still active: {command_path.parent.name}")
for path in (
    root / "COMPLETE", root / "MANIFEST.sha256", root / "result.json",
    root / "verification.json", root / "final-verification-domain-repair-r4.json",
    root / "domain-repair-r4-receipt.json", root / "repair-authority-r4",
    package, log,
):
    if path.exists() or path.is_symlink():
        raise SystemExit(f"R4 repair collision: {path}")
status = subprocess.run(
    ["tmux", "has-session", "-t", session],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
).returncode
if status == 0:
    raise SystemExit("R4 repair tmux session already exists")
if status != 1:
    raise SystemExit("R4 repair tmux existence check failed")
print("V023_R7_DOMAIN_REPAIR_R4_REMOTE_PREFLIGHT_PASS")
PY

cd "$REPO"
PACKAGE_RELATIVE=.scratch/multi-catfish-v023-r7-domain-repair-r4
rsync -aR \
  "$PACKAGE_RELATIVE/V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-R4-2026-09-07.md" \
  "$PACKAGE_RELATIVE/verify_v023_lcsrs_final_domain_repair_r4.py" \
  "$PACKAGE_RELATIVE/run_v023_r7_domain_repair_server_r4.py" \
  "$PACKAGE_RELATIVE/sync_launch_v023_r7_domain_repair_server_r4.sh" \
  "$PACKAGE_RELATIVE/test_v023_r7_domain_repair_r4.py" \
  "$PACKAGE_RELATIVE/V023-R7-DOMAIN-REPAIR-R4-MANIFEST.sha256" \
  "$PACKAGE_RELATIVE/V023-R7-DOMAIN-REPAIR-R4-MANIFEST-FROZEN.sha256" \
  "$SERVER_HOST:$SERVER_ROOT/"

ssh -- "$SERVER_HOST" "cd '$REMOTE_PACKAGE' && sha256sum -c '$(basename -- "$MANIFEST_PIN")' >/dev/null && sha256sum -c '$(basename -- "$MANIFEST")' >/dev/null && '$SERVER_PYTHON' -m py_compile verify_v023_lcsrs_final_domain_repair_r4.py run_v023_r7_domain_repair_server_r4.py && test ! -e '$LOG' && test ! -L '$LOG' && tmux new-session -d -s '$SESSION' \"cd '$SERVER_ROOT' && exec '$SERVER_PYTHON' '$REMOTE_PACKAGE/run_v023_r7_domain_repair_server_r4.py' > '$LOG' 2>&1\" && tmux has-session -t '$SESSION'"

printf 'V023_R7_DOMAIN_REPAIR_R4_LAUNCHED server=%s session=%s log=%s\n' \
  "$SERVER_HOST" "$SESSION" "$LOG"
