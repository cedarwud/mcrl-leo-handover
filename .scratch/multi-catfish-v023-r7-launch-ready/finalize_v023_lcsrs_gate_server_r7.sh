#!/usr/bin/env bash
set -Eeuo pipefail

# Read-only server finalizer/fetcher for the one-shot R7 Gate.  It never
# repairs, overwrites, reruns, opens TEST, trains an episode policy, or turns
# a development receipt into an efficacy claim.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
SERVER_HOST=${V023_SERVER_HOST:-sat}
SERVER_ROOT=${V023_SERVER_ROOT:-/home/sat/mcrl-v023-r7-launch-ready-20260906-r4}
RUN_ROOT=/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1
LOCAL_ROOT=${V023_LOCAL_ROOT:-$REPO/artifacts/multi-catfish-v023-lcsrs-gate-20260906-r7-i1}
LOCAL_PYTHON=${V023_LOCAL_PYTHON:-$REPO/.venv/bin/python}
WAIT_SECONDS=${V023_WAIT_SECONDS:-0}
POLL_SECONDS=${V023_POLL_SECONDS:-30}
REMOTE_RUN="$RUN_ROOT"
SERVER_PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python

die() { printf 'R7_FINALIZE_ERROR: %s\n' "$*" >&2; exit 2; }
usage() {
  cat <<'EOF'
Usage: finalize_v023_lcsrs_gate_server_r7.sh

Authenticates a completed R7 result tree and fetches it without overwriting
existing local data.  The server is never modified.
EOF
}
if (($#)); then
  [[ "$#" == 1 && ( "$1" == "--help" || "$1" == "-h" ) ]] || die "unknown argument: $1"
  usage
  exit 0
fi
[[ "$SERVER_ROOT" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe server checkout root"
[[ "$RUN_ROOT" == "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1" ]] || die "output root drifted"
[[ -x "$LOCAL_PYTHON" ]] || die "local Python is not executable: $LOCAL_PYTHON"
[[ "$WAIT_SECONDS" =~ ^[0-9]+$ && "$POLL_SECONDS" =~ ^[1-9][0-9]*$ ]] || die "wait/poll values are invalid"

deadline=$((SECONDS + WAIT_SECONDS))
while ! ssh "$SERVER_HOST" "test -f '$REMOTE_RUN/COMPLETE' && test ! -L '$REMOTE_RUN/COMPLETE'"; do
  (( WAIT_SECONDS > 0 && SECONDS < deadline )) || die "remote R7 run is not complete"
  sleep "$POLL_SECONDS"
done

# Verify the server's write-once result tree before copying any byte locally.
ssh "$SERVER_HOST" "$SERVER_PYTHON - '$REMOTE_RUN' '$SERVER_ROOT/.scratch/multi-catfish-v023-r7-launch-ready/R7-PREFLIGHT-MANIFEST.json'" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
manifest = Path(sys.argv[2])
if not root.is_dir() or root.is_symlink():
    raise SystemExit("remote R7 result root is missing or symlinked")
if not manifest.is_file() or manifest.is_symlink():
    raise SystemExit("remote R7 launch manifest is missing or symlinked")
complete = root / "COMPLETE"
listing = root / "MANIFEST.sha256"
result = root / "result.json"
for path in (complete, listing, result):
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"remote result binding is missing or symlinked: {path}")
lines = listing.read_text(encoding="ascii").splitlines()
if not lines:
    raise SystemExit("remote result manifest is empty")
listed = set()
for line in lines:
    digest, name = line.split("  ", 1)
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise SystemExit("malformed remote result digest")
    path = Path(name.removeprefix("./"))
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit("unsafe remote result path")
    target = root / path
    if not target.is_file() or target.is_symlink():
        raise SystemExit(f"missing remote result file: {name}")
    if path.as_posix() in listed:
        raise SystemExit("duplicate remote result path")
    listed.add(path.as_posix())
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"remote result hash mismatch: {name}")
actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not p.is_symlink() and p.name not in {"MANIFEST.sha256", "COMPLETE"}}
if listed != actual:
    raise SystemExit("remote result manifest does not cover exact file set")
complete_fields = complete.read_text(encoding="ascii").split()
if complete_fields != [hashlib.sha256(listing.read_bytes()).hexdigest(), "MANIFEST.sha256"]:
    raise SystemExit("remote COMPLETE marker is not bound to MANIFEST.sha256")
payload = json.loads(result.read_text(encoding="ascii"))
if payload.get("status") not in {"PASS_FINAL_INTEGRITY", "PASS_SOURCE_STAGE_INTEGRITY"}:
    raise SystemExit("remote result is not an authenticated R7 result")
if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
    raise SystemExit("remote result crossed TEST or episode-training boundary")
if payload.get("scientific_claim") is not False:
    raise SystemExit("remote result opened a scientific efficacy claim")
manifest_raw = manifest.read_bytes()
manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
digest_sidecar = manifest.with_name("R7-PREFLIGHT-MANIFEST.sha256")
if not digest_sidecar.is_file() or digest_sidecar.is_symlink():
    raise SystemExit("remote launch-manifest digest sidecar is missing or symlinked")
if digest_sidecar.read_text(encoding="ascii").split() != [manifest_sha, manifest.name]:
    raise SystemExit("remote launch-manifest digest sidecar disagrees")
launch = json.loads(manifest_raw.decode("ascii"))
if launch.get("status") != "FROZEN_PRE_OUTCOME" or launch.get("launch") != "AUTHORIZED_ONE_SHOT":
    raise SystemExit("remote launch manifest is not frozen/authorized")
if payload.get("preflight_manifest_sha256") != manifest_sha:
    raise SystemExit("remote result is not bound to the fetched launch manifest")
code_link = launch.get("code_manifest")
if not isinstance(code_link, dict) or not isinstance(code_link.get("path"), str) or not isinstance(code_link.get("sha256"), str):
    raise SystemExit("remote launch manifest code binding is malformed")
repo = next((parent for parent in manifest.parents if (parent / "docs").is_dir() and (parent / ".scratch").is_dir()), None)
if repo is None:
    raise SystemExit("remote checkout root cannot be identified")
code_path = repo / code_link["path"]
if not code_path.is_file() or code_path.is_symlink() or hashlib.sha256(code_path.read_bytes()).hexdigest() != code_link["sha256"]:
    raise SystemExit("remote code-manifest bytes disagree with the launch manifest")
code_digest_path = code_path.with_name("R7-LAUNCH-CODE-MANIFEST.sha256")
if not code_digest_path.is_file() or code_digest_path.is_symlink() or code_digest_path.read_text(encoding="ascii").split() != [code_link["sha256"], code_path.name]:
    raise SystemExit("remote code-manifest digest sidecar disagrees")
if payload.get("code_manifest_sha256") not in {None, code_link["sha256"]}:
    raise SystemExit("remote result code-manifest binding disagrees")
decision_link = next(
    (item for item in launch.get("bindings", []) if isinstance(item, dict) and item.get("role") == "launch_decision"),
    None,
)
if not isinstance(decision_link, dict) or not isinstance(decision_link.get("path"), str) or not isinstance(decision_link.get("sha256"), str):
    raise SystemExit("remote launch-decision binding is malformed")
decision_path = repo / decision_link["path"]
if not decision_path.is_file() or decision_path.is_symlink() or hashlib.sha256(decision_path.read_bytes()).hexdigest() != decision_link["sha256"]:
    raise SystemExit("remote launch-decision bytes disagree with the launch manifest")
if payload.get("launch_decision_sha256") not in {None, decision_link["sha256"]}:
    raise SystemExit("remote result launch-decision binding disagrees")
print("R7_REMOTE_RESULT_VERIFIED")
PY

[[ ! -e "$LOCAL_ROOT" && ! -L "$LOCAL_ROOT" ]] || die "refusing to overwrite local fetched root: $LOCAL_ROOT"
STAGING="${LOCAL_ROOT}.staging"
[[ ! -e "$STAGING" && ! -L "$STAGING" ]] || die "staging path already exists"
mkdir -p "$STAGING"
rsync -a --delete-delay "$SERVER_HOST:$REMOTE_RUN/" "$STAGING/"
(
  cd "$STAGING"
  sha256sum -c MANIFEST.sha256
)
mkdir "$LOCAL_ROOT"
rsync -a --delete-delay "$STAGING/" "$LOCAL_ROOT/"
rmdir "$STAGING"
printf 'R7_RESULT_FETCHED local=%s remote=%s\n' "$LOCAL_ROOT" "$SERVER_HOST:$REMOTE_RUN"
