#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare a fresh Ubuntu-server checkout and launch exactly one authenticated
# R7 TRAIN-development Gate in a fresh tmux session.  This script does not
# launch episode training, TEST, or a five-arm efficacy evaluation.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
SERVER_HOST=${V023_SERVER_HOST:-sat}
SERVER_ROOT=${V023_SERVER_ROOT:-/home/sat/mcrl-v023-r7-launch-ready-20260906-r4}
RUN_ROOT=/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1
TMUX_SESSION=mcrl-v023-lcsrs-gate-20260906-r7-i1
SERVER_PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python
LOCAL_PYTHON=${V023_LOCAL_PYTHON:-$REPO/.venv/bin/python}
TLE_ROOT=/home/sat/mcrl-runtime/tle-frozen-20260820
TLE_SHA256=427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9
PACKAGE="$SCRIPT_DIR"
MANIFEST="$PACKAGE/R7-PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST="$PACKAGE/R7-PREFLIGHT-MANIFEST.sha256"
CODE_MANIFEST="$PACKAGE/R7-LAUNCH-CODE-MANIFEST.json"
CODE_DIGEST="$PACKAGE/R7-LAUNCH-CODE-MANIFEST.sha256"
PREFLIGHT="$PACKAGE/preflight_r7_balanced.py"
LAUNCH_DECISION="$REPO/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-R7-LAUNCH-DECISION-2026-09-06.md"
PREREG="$REPO/artifacts/PREREG-FROZEN-2026-08-25-R2.json"

die() { printf 'R7_SYNC_ERROR: %s\n' "$*" >&2; exit 2; }

usage() {
  cat <<'EOF'
Usage: sync_launch_v023_lcsrs_gate_server_r7.sh

Uses the frozen R7 launch manifest and environment defaults to prepare a fresh
Ubuntu checkout and launch one TRAIN-development Gate in tmux.  It performs
no episode training, TEST access, or efficacy evaluation.
EOF
}

if (($#)); then
  [[ "$#" == 1 && ( "$1" == "--help" || "$1" == "-h" ) ]] || die "unknown argument: $1"
  usage
  exit 0
fi

[[ -x "$LOCAL_PYTHON" ]] || die "local Python is not executable: $LOCAL_PYTHON"
[[ "$SERVER_ROOT" =~ ^/home/sat/[A-Za-z0-9._/-]+$ ]] || die "unsafe server checkout root"
[[ "$SERVER_ROOT" != "$RUN_ROOT" ]] || die "server checkout and output root must be distinct"
[[ "$TMUX_SESSION" =~ ^[A-Za-z0-9_.-]+$ ]] || die "unsafe tmux session"
[[ "$RUN_ROOT" == "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1" ]] || die "output root drifted"
[[ "$TLE_ROOT" == "/home/sat/mcrl-runtime/tle-frozen-20260820" ]] || die "TLE root drifted"

cd "$REPO"
"$LOCAL_PYTHON" "$PREFLIGHT" --manifest "$MANIFEST" --manifest-digest "$MANIFEST_DIGEST" --repo "$REPO" --prereg "$PREREG" >/dev/null || die "local frozen launch preflight failed"

PACKAGE_RELATIVE=.scratch/multi-catfish-v023-r7-launch-ready
GATE="$SERVER_ROOT/$PACKAGE_RELATIVE/run_v023_lcsrs_full_gate_server.sh"

# Expand the authenticated code-manifest paths into an explicit transfer list.
mapfile -t SYNC_PATHS < <("$LOCAL_PYTHON" - "$CODE_MANIFEST" "$CODE_MANIFEST" "$MANIFEST" "$MANIFEST_DIGEST" "$CODE_DIGEST" "$LAUNCH_DECISION" "$PREREG" <<'PY'
import json
from pathlib import Path
import sys

code = json.loads(Path(sys.argv[1]).read_text(encoding="ascii"))
paths = [item["path"] for item in code["bindings"]]
paths.extend(Path(arg).resolve().relative_to(Path.cwd().resolve()).as_posix() for arg in sys.argv[2:])
for value in dict.fromkeys(paths):
    print(value)
PY
) || die "code manifest transfer list could not be built"
for relative in "${SYNC_PATHS[@]}"; do
  [[ "$relative" != /* && "$relative" != *..* ]] || die "unsafe sync path: $relative"
  [[ -f "$REPO/$relative" && ! -L "$REPO/$relative" ]] || die "sync dependency missing or symlinked: $relative"
done

# These checks happen before creating either the checkout root or tmux session.
# An unreachable server is not equivalent to an absent path: only the remote
# predicate's ordinary false result (status 1) may continue.
check_remote_absent() {
  local label=$1 predicate=$2 status=0
  ssh "$SERVER_HOST" "$predicate" >/dev/null 2>&1 || status=$?
  case "$status" in
    0) die "remote $label already exists" ;;
    1) : ;;
    *) die "remote $label existence check failed (ssh status $status)" ;;
  esac
}
check_remote_absent "checkout root" "test -e '$SERVER_ROOT' || test -L '$SERVER_ROOT'"
check_remote_absent "output root" "test -e '$RUN_ROOT' || test -L '$RUN_ROOT'"
check_remote_absent "tmux session" "tmux has-session -t '$TMUX_SESSION' 2>/dev/null"

# Existing package/contract copies are harmless.  A prior result/run that
# contains any fresh R7 world or learner seed is a hard collision.  Skip the
# canonical checkout and launch-package roots explicitly; otherwise their
# frozen schedule text would look like a prior result merely because it is
# present in source code.
ssh "$SERVER_HOST" "$SERVER_PYTHON -" <<'PY'
import hashlib
from pathlib import Path

tokens = ("2026121801", "2026121802", "2026121803", "2026121804", "2026121805", "2026121806", "2026121807", "2026121808", "2026135201", "2026135202", "2026135203")
root = Path("/home/sat")
invalid_root = root / "mcrl-v023-lcsrs-gate-20260906-r7"
invalid_log = root / "mcrl-v023-r7-launch-ready-20260906-r2" / "r7-controller.log"
expected_invalid_files = {
    "LAUNCH-METADATA.json": "23db7c145cdaa2bdd94778ba0ea8cd171d0d5f19c753a58c16de90a6b50933a7",
    "authority/AUTHORITY.json": "a0745e64c4c28b043bdeca1faab52bd8fc25b5e76991261beae375eaacb8e4f8",
    "authority/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md": "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070",
    "authority/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md": "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5",
    "authority/R7-PREFLIGHT-MANIFEST.json": "5b9e2537b714e48883889afcfb142aab07011d5f9517997077070ab9bb83a013",
    "authority/R7-PREFLIGHT-MANIFEST.sha256": "c31b726764d9ccae46b90f628005d5541a5a9f6ac36bb14f77c0b73119fe8b23",
}
if not invalid_root.is_dir() or invalid_root.is_symlink():
    raise SystemExit("declared R7 infrastructure-invalid root is absent or symlinked")
actual_invalid_files = {
    path.relative_to(invalid_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in invalid_root.rglob("*")
    if path.is_file() and not path.is_symlink()
}
if actual_invalid_files != expected_invalid_files:
    raise SystemExit("R7 infrastructure-invalid root inventory or hashes drifted")
for empty_name in ("source", "fit", "composition"):
    directory = invalid_root / empty_name
    if not directory.is_dir() or directory.is_symlink() or any(directory.iterdir()):
        raise SystemExit(f"R7 infrastructure-invalid {empty_name} directory is not empty")
if (
    not invalid_log.is_file()
    or invalid_log.is_symlink()
    or hashlib.sha256(invalid_log.read_bytes()).hexdigest()
    != "0208e82508f73af7ca9d18af15903191fbaa474e77c5230e6aeb1740c167f21c"
    or b"launch receipt has no TLE configuration" not in invalid_log.read_bytes()
):
    raise SystemExit("R7 infrastructure-invalid controller receipt drifted")
print("R7_INVALID_I0_AUTHENTICATED")
for candidate in sorted(root.glob("mcrl-*")):
    if not candidate.is_dir() or candidate.name in {"mcrl-runtime", "mcrl-leo-handover"}:
        continue
    if candidate.name.startswith("mcrl-v023-r7-launch-ready-"):
        continue
    if candidate == invalid_root:
        continue
    for path in candidate.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if any(token.encode() in data for token in tokens):
            raise SystemExit(f"fresh R7 identity collides with prior result/run: {path}")
print("R7_REMOTE_PRIOR_RUN_SCAN_PASS")
PY

ssh "$SERVER_HOST" "mkdir -- '$SERVER_ROOT'"
# The transfer list is repository-relative and this shell is already in the
# repository.  Keeping it relative is essential: prefixing absolute local
# paths would recreate ``home/u24/...`` below the remote checkout instead of
# placing files at their authenticated repository-relative destinations.
rsync -aR --exclude='__pycache__/' --exclude='*.pyc' "${SYNC_PATHS[@]}" "$SERVER_HOST:$SERVER_ROOT/"

# Verify TLE only after the fresh checkout has been materialised, and import
# the verifier's package from that checkout.  The old pre-root check imported
# the server's standing handover tree, so it could not detect a missing or
# shadowed package in the transfer we were about to execute.
ssh "$SERVER_HOST" "PYTHONPATH='$SERVER_ROOT/src:$SERVER_ROOT' '$SERVER_PYTHON' - '$SERVER_ROOT' '$TLE_ROOT' '$TLE_SHA256'" <<'PY'
from pathlib import Path
import sys

checkout = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2])
expected = sys.argv[3]
if not root.is_dir() or root.is_symlink():
    raise SystemExit("frozen TLE root is missing or symlinked")
import mcrl
module_path = Path(mcrl.__file__).resolve()
if not module_path.is_relative_to(checkout):
    raise SystemExit(f"fresh checkout import shadowed by {module_path}")
from mcrl.env.tle import TleArchive
from mcrl.env.ephemeris import file_set_hash
archive = TleArchive(root)
actual = file_set_hash(archive.manifest_rows(list(archive.dates)))
if actual != expected:
    raise SystemExit(f"TLE file-set digest drifted: {actual}")
print("R7_TLE_FROZEN", actual, "MCRL", module_path)
PY

ssh "$SERVER_HOST" "set -Eeuo pipefail; cd '$SERVER_ROOT'; export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1; '$SERVER_PYTHON' '$SERVER_ROOT/$PACKAGE_RELATIVE/preflight_r7_balanced.py' --manifest '$SERVER_ROOT/$PACKAGE_RELATIVE/R7-PREFLIGHT-MANIFEST.json' --manifest-digest '$SERVER_ROOT/$PACKAGE_RELATIVE/R7-PREFLIGHT-MANIFEST.sha256' --repo '$SERVER_ROOT' --prereg '$SERVER_ROOT/artifacts/PREREG-FROZEN-2026-08-25-R2.json' >/dev/null; bash -n '$GATE'; PYTHONDONTWRITEBYTECODE=1 '$SERVER_PYTHON' -m py_compile '$SERVER_ROOT/$PACKAGE_RELATIVE/run_v023_lcsrs_source_server.py' '$SERVER_ROOT/$PACKAGE_RELATIVE/run_v023_lcsrs_fit_server.py' '$SERVER_ROOT/$PACKAGE_RELATIVE/run_v023_lcsrs_composition_server.py' '$SERVER_ROOT/$PACKAGE_RELATIVE/verify_v023_lcsrs_final.py'"

# Exercise the exact source-consumer boundary before any world worker or run
# root is created.  This authenticates the TLE binding and the inherited Q1/Q2
# inputs, but performs no simulator step and writes no scientific output.
ssh "$SERVER_HOST" "PYTHONPATH='$SERVER_ROOT/src:$SERVER_ROOT' '$SERVER_PYTHON' - '$SERVER_ROOT' '$TLE_ROOT'" <<'PY'
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

root = Path(sys.argv[1])
tle_root = Path(sys.argv[2])
package = root / ".scratch/multi-catfish-v023-r7-launch-ready"
import mcrl
if not Path(mcrl.__file__).resolve().is_relative_to(root.resolve()):
    raise SystemExit(f"source consumer imported mcrl outside frozen checkout: {mcrl.__file__}")
source_path = package / "run_v023_lcsrs_source_server.py"
sys.path.insert(0, str(package))
spec = importlib.util.spec_from_file_location("r7_source_consumer_smoke", source_path)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load R7 source server for consumer smoke")
server = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = server
spec.loader.exec_module(server)
manifest = package / "R7-PREFLIGHT-MANIFEST.json"
manifest_digest = package / "R7-PREFLIGHT-MANIFEST.sha256"
prereg = root / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
receipt = server.validate_manifest(
    manifest,
    manifest_digest_path=manifest_digest,
    repo=root,
    prereg_path=prereg,
)
configuration = receipt.get("configuration")
bindings = receipt.get("bindings")
if not isinstance(configuration, dict) or not isinstance(bindings, list):
    raise SystemExit("validated preflight receipt omitted source-consumer fields")
server._verify_frozen_tle(tle_root, receipt=receipt)
adapter = server._load_module("r7_source_adapter_consumer_smoke", server.SOURCE_ADAPTER_PATH)
args = SimpleNamespace(
    tle_root=tle_root,
    prereg=prereg,
    manifest=manifest,
    manifest_digest=manifest_digest,
    execution_addendum=root / "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
    placebo_key=server.PLACEBO_KEY,
    placebo_key_sha256=server.PLACEBO_KEY_SHA256,
    lineage=server.LINEAGE,
    source_family=server.SOURCE_FAMILY,
)
runtime = adapter.V023RuntimeSourceAdapter(server._build_config(args, adapter))
authenticated = runtime._authenticate(
    expected_manifest_sha256=receipt["manifest_file_sha256"]
)
if not isinstance(authenticated, tuple) or len(authenticated) != 6:
    raise SystemExit("source adapter authentication returned an invalid contract")
print("R7_SOURCE_CONSUMER_SMOKE_PASS")
PY

CONTROLLER="$SERVER_ROOT/r7_controller.sh"
ssh "$SERVER_HOST" "test ! -e '$CONTROLLER' && test ! -L '$CONTROLLER'" || die "remote controller path already exists"
ssh "$SERVER_HOST" "umask 077; python3 - '$CONTROLLER' '$SERVER_ROOT' '$RUN_ROOT' '$PACKAGE_RELATIVE' '$SERVER_PYTHON' '$TLE_ROOT'" <<'PY'
import os
from pathlib import Path
import sys

target = Path(sys.argv[1])
root, run_root, package, python, tle = sys.argv[2:]
remote_prereg = f"{root}/artifacts/PREREG-FROZEN-2026-08-25-R2.json"
body = f'''#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHON="{python}"
export PYTHONPATH="{root}/src:{root}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONUNBUFFERED=1
exec >>"{root}/r7-controller.log" 2>&1
exec "{root}/{package}/run_v023_lcsrs_full_gate_server.sh" --run-root "{run_root}" --tle-root "{tle}" --prereg "{remote_prereg}" --source-jobs 8 --fit-jobs 8 --composition-jobs 8
'''
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
with os.fdopen(fd, "w", encoding="ascii", newline="") as handle:
    handle.write(body)
PY

ssh "$SERVER_HOST" "tmux new-session -d -s '$TMUX_SESSION' '$CONTROLLER'"
printf 'R7_GATE_LAUNCHED server=%s checkout=%s run_root=%s tmux=%s\n' "$SERVER_HOST" "$SERVER_ROOT" "$RUN_ROOT" "$TMUX_SESSION"
