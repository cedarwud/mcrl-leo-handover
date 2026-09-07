#!/usr/bin/env python3
"""Run the bounded R7-I1 domain/import/pair-profile R3 repair, then seal it.

This controller performs integrity verification only.  It reuses the existing
8/48/48 TRAIN-development panel and never imports or launches a simulator,
learner, TEST evaluator, or episode-training entry point.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


RUN_ROOT = Path("/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1")
CHECKOUT_ROOT = Path("/home/sat/mcrl-v023-r7-launch-ready-20260906-r4")
REPAIR_RELATIVE = Path(".scratch/multi-catfish-v023-r7-domain-repair-r3")
R7_RELATIVE = Path(".scratch/multi-catfish-v023-r7-launch-ready")
PACKAGE = CHECKOUT_ROOT / REPAIR_RELATIVE
R7_PACKAGE = CHECKOUT_ROOT / R7_RELATIVE

MANIFEST = PACKAGE / "V023-R7-DOMAIN-REPAIR-MANIFEST.sha256"
MANIFEST_PIN = PACKAGE / "V023-R7-DOMAIN-REPAIR-MANIFEST-FROZEN.sha256"
WRAPPER = PACKAGE / "verify_v023_lcsrs_final_domain_repair.py"
CONTRACT = PACKAGE / "V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md"
SEALER = R7_PACKAGE / "seal_v023_lcsrs_result_directory.py"

INVALID = RUN_ROOT / "final-verification.json"
CORRECTED = RUN_ROOT / "final-verification-domain-repair-r3.json"
REPAIR_RECEIPT = RUN_ROOT / "domain-repair-r3-receipt.json"
AUTHORITY = RUN_ROOT / "repair-authority-r3"

WORLDS = tuple(range(2026121801, 2026121809))
SEEDS = tuple(range(2026135201, 2026135204))
ARMS = ("informed", "matched_placebo")
EXPECTED_PREFLIGHT_MANIFEST_SHA256 = (
    "9b08e3acc1d1d9b0cf506c3137f8e4013345ed8fb6f54c385a312ddb8570772a"
)
EXPECTED_SEALER_SHA256 = (
    "0ac192e8bb79c9bb0deba751c595839a4723c4dede0770604cfc9f6636022a91"
)
R1_AUTHORITY = RUN_ROOT / "repair-authority"
R1_LOG = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r1.log")
EXPECTED_R1_MANIFEST_SHA256 = (
    "e72b2cc566d0376c5c8d9bfafc3b28718fa757d4cab25f28f2b19703dd0b1f59"
)
EXPECTED_R1_MANIFEST_PIN_SHA256 = (
    "1ec0296abf541748f463411567264a7a1f25368aa4115f6f6747dd7bcf9022f8"
)
EXPECTED_R1_LOG_SHA256 = (
    "fe5eebb609be38e8ca16fc734e8464f97a370aea65c291f4d50d564292dc0419"
)
R2_LOG = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r2.log")
R2_AUTHORITY = RUN_ROOT / "repair-authority-r2"
EXPECTED_R2_MANIFEST_SHA256 = (
    "e6f433eeafbe8bcbf43c81e241a60a2f428a8fdd06275f95e3e4a6f0fdfd710b"
)
EXPECTED_R2_MANIFEST_PIN_SHA256 = (
    "bdfca2665b26ff134da05326498d2e28cb7313e2dff0584ec4a935d82b40b216"
)
EXPECTED_R2_LOG_MARKERS = (
    "V023_R7_DOMAIN_REPAIR_FAILED:",
    "NPZ domain dispatch count drifted:",
)

EXPECTED_MANIFEST_MEMBERS = {
    "V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md",
    "verify_v023_lcsrs_final_domain_repair.py",
    "run_v023_r7_domain_repair_server.py",
    "sync_launch_v023_r7_domain_repair_server.sh",
    "test_v023_r7_domain_repair.py",
}


class RepairControllerError(RuntimeError):
    """The frozen repair controller failed closed."""


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RepairControllerError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RepairControllerError(f"expected JSON file: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RepairControllerError(f"malformed JSON: {path}") from error
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    if not isinstance(value, dict) or raw not in (canonical, canonical + b"\n"):
        raise RepairControllerError(f"noncanonical JSON: {path}")
    return value


def verify_package() -> str:
    manifest_sha = sha256(MANIFEST)
    pin = MANIFEST_PIN.read_text(encoding="ascii").splitlines()
    if len(pin) != 1 or pin[0].split() != [manifest_sha, MANIFEST.name]:
        raise RepairControllerError("repair manifest pin disagrees")
    members: set[str] = set()
    for line in MANIFEST.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise RepairControllerError("malformed repair manifest line")
        digest, relative = parts
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != path.name:
            raise RepairControllerError(f"unsafe repair manifest path: {relative}")
        if relative in members or sha256(PACKAGE / path) != digest:
            raise RepairControllerError(f"repair manifest mismatch: {relative}")
        members.add(relative)
    if members != EXPECTED_MANIFEST_MEMBERS:
        raise RepairControllerError(f"repair manifest closure drifted: {sorted(members)}")
    return manifest_sha


def require_unsealed_root() -> None:
    if RUN_ROOT.is_symlink() or not RUN_ROOT.is_dir():
        raise RepairControllerError("R7-I1 root is absent or symlinked")
    launch = read_json(RUN_ROOT / "LAUNCH-METADATA.json")
    if (
        launch.get("output_root") != RUN_ROOT.as_posix()
        or launch.get("split") != "TRAIN_DEVELOPMENT"
        or launch.get("test_split_opened") is not False
        or launch.get("episode_training") is not False
    ):
        raise RepairControllerError("R7-I1 launch metadata drifted")
    for forbidden in (
        RUN_ROOT / "COMPLETE",
        RUN_ROOT / "MANIFEST.sha256",
        RUN_ROOT / "result.json",
        RUN_ROOT / "verification.json",
        CORRECTED,
        REPAIR_RECEIPT,
        AUTHORITY,
    ):
        if forbidden.exists() or forbidden.is_symlink():
            raise RepairControllerError(f"repair output already exists: {forbidden}")


def verify_existing_authority() -> None:
    if sha256(SEALER) != EXPECTED_SEALER_SHA256:
        raise RepairControllerError("frozen R7 result sealer digest drifted")
    authority = read_json(RUN_ROOT / "authority" / "AUTHORITY.json")
    if (
        authority.get("schema")
        != "multi-catfish-mcrl-v023-lcsrs-r7-balanced-authority-snapshot-v1"
        or authority.get("preflight_manifest_sha256")
        != EXPECTED_PREFLIGHT_MANIFEST_SHA256
        or authority.get("test_split_opened") is not False
        or authority.get("episode_training") is not False
    ):
        raise RepairControllerError("existing R7 authority receipt drifted")
    entries = authority.get("entries")
    if not isinstance(entries, dict) or set(entries) != {
        "contract",
        "execution_addendum",
        "preflight_manifest",
        "preflight_manifest_digest",
    }:
        raise RepairControllerError("existing R7 authority closure drifted")
    for role, binding in entries.items():
        if not isinstance(binding, dict):
            raise RepairControllerError(f"invalid R7 authority binding: {role}")
        relative = Path(str(binding.get("path", "")))
        path = RUN_ROOT / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not path.resolve().is_relative_to(RUN_ROOT.resolve())
            or sha256(path) != binding.get("sha256")
        ):
            raise RepairControllerError(f"existing R7 authority hash drifted: {role}")


def verify_r1_entry_failure() -> None:
    """Authenticate that R1 stopped before any corrected verifier output."""

    manifest = R1_AUTHORITY / "V023-R7-DOMAIN-REPAIR-MANIFEST.sha256"
    pin = R1_AUTHORITY / "V023-R7-DOMAIN-REPAIR-MANIFEST-FROZEN.sha256"
    if (
        sha256(manifest) != EXPECTED_R1_MANIFEST_SHA256
        or sha256(pin) != EXPECTED_R1_MANIFEST_PIN_SHA256
        or sha256(R1_LOG) != EXPECTED_R1_LOG_SHA256
    ):
        raise RepairControllerError("R1 entry-failure evidence drifted")
    pin_parts = pin.read_text(encoding="ascii").split()
    if pin_parts != [EXPECTED_R1_MANIFEST_SHA256, manifest.name]:
        raise RepairControllerError("R1 repair manifest pin disagrees")
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise RepairControllerError("malformed R1 repair manifest line")
        digest, relative = parts
        member = Path(relative)
        if member.is_absolute() or ".." in member.parts or member.name != relative:
            raise RepairControllerError("unsafe R1 repair authority member")
        if sha256(R1_AUTHORITY / member) != digest:
            raise RepairControllerError(f"R1 repair authority drifted: {relative}")
    log_text = R1_LOG.read_text(encoding="utf-8")
    if (
        "NPZ domain dispatch count drifted: {'source': 0, 'composition': 0}"
        not in log_text
    ):
        raise RepairControllerError("R1 zero-load failure signal is absent")
    for unexpected in (
        RUN_ROOT / "final-verification-domain-repair.json",
        RUN_ROOT / "domain-repair-receipt.json",
    ):
        if unexpected.exists() or unexpected.is_symlink():
            raise RepairControllerError(f"unexpected R1 corrected output exists: {unexpected}")


def verify_r2_entry_failure() -> None:
    """Authenticate the R2 postcondition-order failure before R3 starts."""

    if R2_LOG.is_symlink() or not R2_LOG.is_file():
        raise RepairControllerError("R2 failure log is unavailable")
    log_text = R2_LOG.read_text(encoding="utf-8", errors="replace")
    for marker in EXPECTED_R2_LOG_MARKERS:
        if marker not in log_text:
            raise RepairControllerError(f"R2 failure marker is absent: {marker}")
    manifest = R2_AUTHORITY / "V023-R7-DOMAIN-REPAIR-MANIFEST.sha256"
    pin = R2_AUTHORITY / "V023-R7-DOMAIN-REPAIR-MANIFEST-FROZEN.sha256"
    if (
        sha256(manifest) != EXPECTED_R2_MANIFEST_SHA256
        or sha256(pin) != EXPECTED_R2_MANIFEST_PIN_SHA256
    ):
        raise RepairControllerError("R2 authority evidence drifted")
    pin_parts = pin.read_text(encoding="ascii").split()
    if pin_parts != [EXPECTED_R2_MANIFEST_SHA256, manifest.name]:
        raise RepairControllerError("R2 repair manifest pin disagrees")
    members: set[str] = set()
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise RepairControllerError("malformed R2 repair manifest line")
        digest, relative = parts
        member = Path(relative)
        if member.is_absolute() or ".." in member.parts or member.name != relative:
            raise RepairControllerError("unsafe R2 repair authority member")
        if sha256(R2_AUTHORITY / member) != digest:
            raise RepairControllerError(f"R2 repair authority drifted: {relative}")
        members.add(relative)
    if members != EXPECTED_MANIFEST_MEMBERS:
        raise RepairControllerError("R2 repair authority closure drifted")
    for unexpected in (
        RUN_ROOT / "final-verification-domain-repair-r2.json",
        RUN_ROOT / "domain-repair-r2-receipt.json",
    ):
        if unexpected.exists() or unexpected.is_symlink():
            raise RepairControllerError(f"unexpected R2 corrected output exists: {unexpected}")


def require_quiescent_panel() -> None:
    markers = (
        "run_v023_lcsrs_full_gate_server.sh",
        "run_v023_lcsrs_source_server.py",
        "run_v023_lcsrs_fit_server.py",
        "run_v023_lcsrs_composition_server.py",
        "verify_v023_lcsrs_final.py",
    )
    for command_path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            command = command_path.read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except OSError:
            continue
        if RUN_ROOT.as_posix() in command and any(marker in command for marker in markers):
            raise RepairControllerError(f"R7 writer is still active: {command_path.parent.name}")

    def snapshot() -> dict[str, tuple[int, int]]:
        return {
            path.relative_to(RUN_ROOT).as_posix(): (
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in RUN_ROOT.rglob("*")
            if path.is_file() and not path.is_symlink()
        }

    before = snapshot()
    time.sleep(2.0)
    after = snapshot()
    if before != after:
        raise RepairControllerError("R7-I1 file inventory changed during quiescence check")


def snapshot_authority() -> None:
    AUTHORITY.mkdir(mode=0o755)
    for name in sorted(EXPECTED_MANIFEST_MEMBERS):
        shutil.copyfile(PACKAGE / name, AUTHORITY / name)
    shutil.copyfile(MANIFEST, AUTHORITY / MANIFEST.name)
    shutil.copyfile(MANIFEST_PIN, AUTHORITY / MANIFEST_PIN.name)


def panel_paths() -> tuple[list[Path], list[Path], list[Path]]:
    sources = [RUN_ROOT / "source" / f"world-{world}.json" for world in WORLDS]
    fits: list[Path] = []
    compositions: list[Path] = []
    for world in WORLDS:
        for seed in SEEDS:
            for arm in ARMS:
                fits.append(RUN_ROOT / "fit" / f"world-{world}" / f"seed-{seed}" / f"{arm}.json")
                compositions.append(
                    RUN_ROOT / "composition" / f"world-{world}" / f"seed-{seed}" / f"{arm}.json"
                )
    for path in (*sources, *fits, *compositions):
        if path.is_symlink() or not path.is_file():
            raise RepairControllerError(f"panel member missing or symlinked: {path}")
    return sources, fits, compositions


def run() -> None:
    verify_package()
    require_unsealed_root()
    verify_existing_authority()
    verify_r1_entry_failure()
    verify_r2_entry_failure()
    require_quiescent_panel()
    sources, fits, compositions = panel_paths()
    snapshot_authority()
    command = [
        sys.executable,
        str(WRAPPER),
        "--source",
        *(str(path) for path in sources),
        "--fit",
        *(str(path) for path in fits),
        "--composition",
        *(str(path) for path in compositions),
        "--source-manifest",
        str(RUN_ROOT / "source-manifest.json"),
        "--launch-manifest",
        str(R7_PACKAGE / "R7-PREFLIGHT-MANIFEST.json"),
        "--launch-manifest-digest",
        str(R7_PACKAGE / "R7-PREFLIGHT-MANIFEST.sha256"),
        "--invalid-verification",
        str(INVALID),
        "--contract",
        str(CONTRACT),
        "--output",
        str(CORRECTED),
        "--receipt",
        str(REPAIR_RECEIPT),
    ]
    subprocess.run(command, cwd=CHECKOUT_ROOT, check=True)
    receipt = read_json(REPAIR_RECEIPT)
    if (
        receipt.get("status") != "PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R3"
        or receipt.get("corrected_status") != "PASS_FINAL_INTEGRITY"
        or receipt.get("corrected_integrity_status") != "VERIFIED"
        or receipt.get("test_split_opened") is not False
        or receipt.get("episode_training") is not False
        or receipt.get("scientific_claim") is not False
        or receipt.get("contract_sha256") != sha256(CONTRACT)
        or receipt.get("repair_adapter_sha256") != sha256(WRAPPER)
        or receipt.get("preflight_manifest_sha256")
        != EXPECTED_PREFLIGHT_MANIFEST_SHA256
        or receipt.get("corrected_verification_sha256") != sha256(CORRECTED)
        or receipt.get("domain_dispatch")
        != {
            "source": "source-array-v1",
            "composition": "v023-composition-array-v1",
            "source_loads": 8,
            "composition_loads": 48,
        }
        or receipt.get("sibling_import_path_scoped") is not True
        or receipt.get("pair_profile_broadcast")
        != {
            "operation": "np.broadcast_to(expected_profiles[None, :, :], profile_actions[p].shape)",
            "draw_count": 32,
            "scoped_target": "composition pair profile actions",
        }
    ):
        raise RepairControllerError("repair receipt did not authorize sealing")
    subprocess.run(
        [
            sys.executable,
            str(SEALER),
            "seal",
            "--run-root",
            str(RUN_ROOT),
            "--verification",
            str(CORRECTED),
            "--kind",
            "full",
        ],
        cwd=CHECKOUT_ROOT,
        check=True,
    )
    if not (RUN_ROOT / "COMPLETE").is_file():
        raise RepairControllerError("result sealer did not publish COMPLETE")


def main() -> int:
    try:
        run()
    except Exception as error:
        print(f"V023_R7_DOMAIN_REPAIR_CONTROLLER_FAILED: {error}", file=sys.stderr)
        return 2
    print(f"V023_R7_DOMAIN_REPAIR_CONTROLLER_PASS: {RUN_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
