#!/usr/bin/env python3
"""Run the bounded R7-I1 R4 verifier repair and seal only verified evidence."""

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
REPAIR_RELATIVE = Path(".scratch/multi-catfish-v023-r7-domain-repair-r4")
R7_RELATIVE = Path(".scratch/multi-catfish-v023-r7-launch-ready")
PACKAGE = CHECKOUT_ROOT / REPAIR_RELATIVE
R7_PACKAGE = CHECKOUT_ROOT / R7_RELATIVE

MANIFEST = PACKAGE / "V023-R7-DOMAIN-REPAIR-R4-MANIFEST.sha256"
MANIFEST_PIN = PACKAGE / "V023-R7-DOMAIN-REPAIR-R4-MANIFEST-FROZEN.sha256"
WRAPPER = PACKAGE / "verify_v023_lcsrs_final_domain_repair_r4.py"
CONTRACT = PACKAGE / "V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-R4-2026-09-07.md"
SEALER = R7_PACKAGE / "seal_v023_lcsrs_result_directory.py"

INVALID = RUN_ROOT / "final-verification.json"
CORRECTED = RUN_ROOT / "final-verification-domain-repair-r4.json"
REPAIR_RECEIPT = RUN_ROOT / "domain-repair-r4-receipt.json"
AUTHORITY = RUN_ROOT / "repair-authority-r4"

WORLDS = tuple(range(2026121801, 2026121809))
SEEDS = tuple(range(2026135201, 2026135204))
ARMS = ("informed", "matched_placebo")
EXPECTED_PREFLIGHT_MANIFEST_SHA256 = (
    "9b08e3acc1d1d9b0cf506c3137f8e4013345ed8fb6f54c385a312ddb8570772a"
)
EXPECTED_SEALER_SHA256 = (
    "0ac192e8bb79c9bb0deba751c595839a4723c4dede0770604cfc9f6636022a91"
)
EXPECTED_R3_ADAPTER_SHA256 = (
    "7d242eb2ca31835ba2471334b7ab90f8d68f4c817a367a5f3f2c72fb518fff2d"
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

R2_AUTHORITY = RUN_ROOT / "repair-authority-r2"
R2_LOG = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r2.log")
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

R3_AUTHORITY = RUN_ROOT / "repair-authority-r3"
R3_LOG = Path("/home/sat/mcrl-v023-r7-domain-repair-20260907-r3.log")
EXPECTED_R3_MANIFEST_SHA256 = (
    "4a1fb2ef124212757bdabe00bd578b5cd009977e9b4c64017b4a22ebe5990c90"
)
EXPECTED_R3_MANIFEST_PIN_SHA256 = (
    "1da52c78556bc8a1c2c61d281aabc05172ed477eaff0de5b270ead0e5b139c61"
)
EXPECTED_R3_LOG_SHA256 = (
    "c76640b6b40068ad24def04d3eabcefc94d9a0ac2ba280254be4ff7a10b62fc4"
)
EXPECTED_R3_LOG_SIZE = 12_279
EXPECTED_R3_LOG_MARKERS = (
    "V023_R7_DOMAIN_REPAIR_FAILED:",
    "composition/source identity array missing: pair_source_key",
)
EXPECTED_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_AND_IMPORT_CLOSURE_REPAIR_"
    "NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)

EXPECTED_MANIFEST_MEMBERS = {
    "V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-R4-2026-09-07.md",
    "verify_v023_lcsrs_final_domain_repair_r4.py",
    "run_v023_r7_domain_repair_server_r4.py",
    "sync_launch_v023_r7_domain_repair_server_r4.sh",
    "test_v023_r7_domain_repair_r4.py",
}
PREVIOUS_MANIFEST_MEMBERS = {
    "V023-R7-FINAL-VERIFIER-DOMAIN-REPAIR-CONTRACT-2026-09-07.md",
    "verify_v023_lcsrs_final_domain_repair.py",
    "run_v023_r7_domain_repair_server.py",
    "sync_launch_v023_r7_domain_repair_server.sh",
    "test_v023_r7_domain_repair.py",
}


class RepairControllerR4Error(RuntimeError):
    """The frozen R4 repair controller failed closed."""


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RepairControllerR4Error(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RepairControllerR4Error(f"expected JSON file: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RepairControllerR4Error(f"malformed JSON: {path}") from error
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    if not isinstance(value, dict) or raw not in (canonical, canonical + b"\n"):
        raise RepairControllerR4Error(f"noncanonical JSON: {path}")
    return value


def _verify_manifest_tree(
    *,
    authority: Path,
    expected_manifest_sha256: str,
    expected_pin_sha256: str,
    expected_members: set[str],
    label: str,
) -> None:
    manifest = authority / "V023-R7-DOMAIN-REPAIR-MANIFEST.sha256"
    pin = authority / "V023-R7-DOMAIN-REPAIR-MANIFEST-FROZEN.sha256"
    if (
        sha256(manifest) != expected_manifest_sha256
        or sha256(pin) != expected_pin_sha256
    ):
        raise RepairControllerR4Error(f"{label} authority evidence drifted")
    if pin.read_text(encoding="ascii").split() != [
        expected_manifest_sha256,
        manifest.name,
    ]:
        raise RepairControllerR4Error(f"{label} repair manifest pin disagrees")
    members: set[str] = set()
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise RepairControllerR4Error(f"malformed {label} repair manifest line")
        digest, relative = parts
        member = Path(relative)
        if member.is_absolute() or ".." in member.parts or member.name != relative:
            raise RepairControllerR4Error(f"unsafe {label} repair authority member")
        if relative in members or sha256(authority / member) != digest:
            raise RepairControllerR4Error(f"{label} repair authority drifted: {relative}")
        members.add(relative)
    if members != expected_members:
        raise RepairControllerR4Error(f"{label} repair authority closure drifted")


def verify_package() -> str:
    manifest_sha = sha256(MANIFEST)
    sha256(MANIFEST_PIN)  # Require a regular, nonsymlinked pin file.
    pin = MANIFEST_PIN.read_text(encoding="ascii").splitlines()
    if len(pin) != 1 or pin[0].split() != [manifest_sha, MANIFEST.name]:
        raise RepairControllerR4Error("R4 repair manifest pin disagrees")
    members: set[str] = set()
    for line in MANIFEST.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise RepairControllerR4Error("malformed R4 repair manifest line")
        digest, relative = parts
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != path.name:
            raise RepairControllerR4Error(f"unsafe R4 repair manifest path: {relative}")
        if relative in members or sha256(PACKAGE / path) != digest:
            raise RepairControllerR4Error(f"R4 repair manifest mismatch: {relative}")
        members.add(relative)
    if members != EXPECTED_MANIFEST_MEMBERS:
        raise RepairControllerR4Error(
            f"R4 repair manifest closure drifted: {sorted(members)}"
        )
    return manifest_sha


def require_unsealed_root() -> None:
    if RUN_ROOT.is_symlink() or not RUN_ROOT.is_dir():
        raise RepairControllerR4Error("R7-I1 root is absent or symlinked")
    launch = read_json(RUN_ROOT / "LAUNCH-METADATA.json")
    if (
        launch.get("output_root") != RUN_ROOT.as_posix()
        or launch.get("split") != "TRAIN_DEVELOPMENT"
        or launch.get("test_split_opened") is not False
        or launch.get("episode_training") is not False
    ):
        raise RepairControllerR4Error("R7-I1 launch metadata drifted")
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
            raise RepairControllerR4Error(f"R4 repair output already exists: {forbidden}")


def verify_existing_authority() -> None:
    if sha256(SEALER) != EXPECTED_SEALER_SHA256:
        raise RepairControllerR4Error("frozen R7 result sealer digest drifted")
    authority = read_json(RUN_ROOT / "authority" / "AUTHORITY.json")
    if (
        authority.get("schema")
        != "multi-catfish-mcrl-v023-lcsrs-r7-balanced-authority-snapshot-v1"
        or authority.get("preflight_manifest_sha256")
        != EXPECTED_PREFLIGHT_MANIFEST_SHA256
        or authority.get("test_split_opened") is not False
        or authority.get("episode_training") is not False
    ):
        raise RepairControllerR4Error("existing R7 authority receipt drifted")
    entries = authority.get("entries")
    if not isinstance(entries, dict) or set(entries) != {
        "contract",
        "execution_addendum",
        "preflight_manifest",
        "preflight_manifest_digest",
    }:
        raise RepairControllerR4Error("existing R7 authority closure drifted")
    for role, binding in entries.items():
        if not isinstance(binding, dict):
            raise RepairControllerR4Error(f"invalid R7 authority binding: {role}")
        relative = Path(str(binding.get("path", "")))
        path = RUN_ROOT / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not path.resolve().is_relative_to(RUN_ROOT.resolve())
            or sha256(path) != binding.get("sha256")
        ):
            raise RepairControllerR4Error(f"existing R7 authority hash drifted: {role}")


def verify_r1_entry_failure() -> None:
    _verify_manifest_tree(
        authority=R1_AUTHORITY,
        expected_manifest_sha256=EXPECTED_R1_MANIFEST_SHA256,
        expected_pin_sha256=EXPECTED_R1_MANIFEST_PIN_SHA256,
        expected_members=PREVIOUS_MANIFEST_MEMBERS,
        label="R1",
    )
    if sha256(R1_LOG) != EXPECTED_R1_LOG_SHA256:
        raise RepairControllerR4Error("R1 failure log drifted")
    if (
        "NPZ domain dispatch count drifted: {'source': 0, 'composition': 0}"
        not in R1_LOG.read_text(encoding="utf-8")
    ):
        raise RepairControllerR4Error("R1 zero-load failure signal is absent")
    for unexpected in (
        RUN_ROOT / "final-verification-domain-repair.json",
        RUN_ROOT / "domain-repair-receipt.json",
    ):
        if unexpected.exists() or unexpected.is_symlink():
            raise RepairControllerR4Error(f"unexpected R1 corrected output exists: {unexpected}")


def verify_r2_entry_failure() -> None:
    _verify_manifest_tree(
        authority=R2_AUTHORITY,
        expected_manifest_sha256=EXPECTED_R2_MANIFEST_SHA256,
        expected_pin_sha256=EXPECTED_R2_MANIFEST_PIN_SHA256,
        expected_members=PREVIOUS_MANIFEST_MEMBERS,
        label="R2",
    )
    if R2_LOG.is_symlink() or not R2_LOG.is_file():
        raise RepairControllerR4Error("R2 failure log is unavailable")
    text = R2_LOG.read_text(encoding="utf-8", errors="replace")
    for marker in EXPECTED_R2_LOG_MARKERS:
        if marker not in text:
            raise RepairControllerR4Error(f"R2 failure marker is absent: {marker}")
    for unexpected in (
        RUN_ROOT / "final-verification-domain-repair-r2.json",
        RUN_ROOT / "domain-repair-r2-receipt.json",
    ):
        if unexpected.exists() or unexpected.is_symlink():
            raise RepairControllerR4Error(f"unexpected R2 corrected output exists: {unexpected}")


def verify_r3_entry_failure() -> None:
    _verify_manifest_tree(
        authority=R3_AUTHORITY,
        expected_manifest_sha256=EXPECTED_R3_MANIFEST_SHA256,
        expected_pin_sha256=EXPECTED_R3_MANIFEST_PIN_SHA256,
        expected_members=PREVIOUS_MANIFEST_MEMBERS,
        label="R3",
    )
    if R3_LOG.is_symlink() or not R3_LOG.is_file():
        raise RepairControllerR4Error("R3 failure log is unavailable")
    if R3_LOG.stat().st_size != EXPECTED_R3_LOG_SIZE:
        raise RepairControllerR4Error("R3 failure log size drifted")
    if sha256(R3_LOG) != EXPECTED_R3_LOG_SHA256:
        raise RepairControllerR4Error("R3 failure log digest drifted")
    text = R3_LOG.read_text(encoding="utf-8", errors="replace")
    for marker in EXPECTED_R3_LOG_MARKERS:
        if marker not in text:
            raise RepairControllerR4Error(f"R3 failure marker is absent: {marker}")
    for unexpected in (
        RUN_ROOT / "final-verification-domain-repair-r3.json",
        RUN_ROOT / "domain-repair-r3-receipt.json",
    ):
        if unexpected.exists() or unexpected.is_symlink():
            raise RepairControllerR4Error(f"unexpected R3 corrected output exists: {unexpected}")


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
            raise RepairControllerR4Error(
                f"R7 writer is still active: {command_path.parent.name}"
            )

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
        raise RepairControllerR4Error("R7-I1 file inventory changed during quiescence check")


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
                fits.append(
                    RUN_ROOT / "fit" / f"world-{world}" / f"seed-{seed}" / f"{arm}.json"
                )
                compositions.append(
                    RUN_ROOT
                    / "composition"
                    / f"world-{world}"
                    / f"seed-{seed}"
                    / f"{arm}.json"
                )
    for path in (*sources, *fits, *compositions):
        if path.is_symlink() or not path.is_file():
            raise RepairControllerR4Error(f"panel member missing or symlinked: {path}")
    return sources, fits, compositions


def _receipt_authorizes_seal(receipt: dict[str, Any]) -> bool:
    pair = receipt.get("pair_key_reconstruction")
    c2 = receipt.get("c2_diagnostic_normalization")
    q2_precision = receipt.get("q2_delta_precision")
    if (
        not isinstance(pair, dict)
        or not isinstance(c2, dict)
        or not isinstance(q2_precision, dict)
    ):
        return False
    return bool(
        receipt.get("schema")
        == "multi-catfish-mcrl-v023-r7-final-verifier-domain-repair-v4"
        and receipt.get("status") == "PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R4"
        and receipt.get("claim_ceiling") == EXPECTED_CLAIM_CEILING
        and receipt.get("corrected_status") == "PASS_FINAL_INTEGRITY"
        and receipt.get("corrected_integrity_status") == "VERIFIED"
        and receipt.get("test_split_opened") is False
        and receipt.get("episode_training") is False
        and receipt.get("learner_update") is False
        and receipt.get("scientific_claim") is False
        and receipt.get("contract_sha256") == sha256(CONTRACT)
        and receipt.get("repair_adapter_sha256") == sha256(WRAPPER)
        and receipt.get("r3_adapter_sha256") == EXPECTED_R3_ADAPTER_SHA256
        and receipt.get("original_verifier_sha256")
        == "3cc573717f010d8b67ede027d05ef79f4c69497e9654d6766df50e88e9aa4717"
        and receipt.get("invalid_verification_sha256")
        == "2b14fb95b9599b1c6abd50a63ab7adaaf61e31a8bbf448ada625b4242fd6a64f"
        and receipt.get("preflight_manifest_sha256")
        == EXPECTED_PREFLIGHT_MANIFEST_SHA256
        and receipt.get("corrected_verification_sha256") == sha256(CORRECTED)
        and receipt.get("domain_dispatch")
        == {
            "source": "source-array-v1",
            "composition": "v023-composition-array-v1",
            "source_loads": 8,
            "composition_loads": 48,
        }
        and receipt.get("pair_profile_broadcast")
        == {
            "operation": "np.broadcast_to(expected_profiles[None, :, :], profile_actions[p].shape)",
            "draw_count": 32,
            "scoped_target": "composition pair profile actions",
        }
        and receipt.get("sibling_import_path_scoped") is True
        and pair.get("arrays_reconstructed")
        == ["pair_source_key", "pair_destination_keys"]
        and pair.get("source_only") is True
        and pair.get("json_topology_derivation") is True
        and pair.get("source_npz_physical_derivation") is True
        and pair.get("both_derivations_agreed") is True
        and pair.get("all_enumerated_pairs") is True
        and pair.get("pair_retained_filter_applied") is False
        and pair.get("pair_order_preserved") is True
        and pair.get("dtype") == "int64"
        and pair.get("c_order") is True
        and pair.get("shapes")
        == {"pair_source_key": "(P,2)", "pair_destination_keys": "(P,2,2)"}
        and pair.get("source_worlds") == 8
        and pair.get("join_applications") == 48
        and type(pair.get("source_pair_rows")) is int
        and pair["source_pair_rows"] > 0
        and c2.get("applied") is True
        and c2.get("input_container") == "list-of-per-pair-objects"
        and c2.get("output_container") == "single-object"
        and c2.get("pair_order_preserved") is True
        and c2.get("all_rows_preserved") is True
        and c2.get("per_pair_scalar_provenance_preserved") is True
        and c2.get("shared_fields_asserted_equal")
        == [
            "kind",
            "diagnostic_lambda_bits_per_j_hex",
            "target_filter_applied",
            "target_free_inference",
            "runtime_default_lambda_used_for_target",
        ]
        and c2.get("count_fields_summed")
        == ["exposure_count", "nontrivial_count"]
        and c2.get("list_containers") == 72
        and c2.get("mapping_passthrough") == 0
        and c2.get("pair_objects") == pair["source_pair_rows"]
        and c2.get("rows") == pair["source_pair_rows"]
        and q2_precision.get("expected_computed_in") == "float32-as-writer"
        and q2_precision.get("rows_checked") == pair["source_pair_rows"]
        and q2_precision.get("member_deltas_checked")
        == 2 * pair["source_pair_rows"]
        and q2_precision.get("scoped_target")
        == "_context_status expected_q2_delta"
    )


def run() -> None:
    verify_package()
    require_unsealed_root()
    verify_existing_authority()
    verify_r1_entry_failure()
    verify_r2_entry_failure()
    verify_r3_entry_failure()
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
    corrected = read_json(CORRECTED)
    if (
        corrected.get("status") != "PASS_FINAL_INTEGRITY"
        or corrected.get("integrity_status") != "VERIFIED"
        or corrected.get("source_count") != 8
        or corrected.get("fit_count") != 48
        or corrected.get("composition_count") != 48
        or corrected.get("scientific_claim") is not False
        or corrected.get("test_split_opened") is not False
        or corrected.get("episode_training") is not False
        or not _receipt_authorizes_seal(receipt)
    ):
        raise RepairControllerR4Error("R4 repair receipt did not authorize sealing")
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
        raise RepairControllerR4Error("result sealer did not publish COMPLETE")


def main() -> int:
    try:
        run()
    except Exception as error:
        print(f"V023_R7_DOMAIN_REPAIR_R4_CONTROLLER_FAILED: {error}", file=sys.stderr)
        return 2
    print(f"V023_R7_DOMAIN_REPAIR_R4_CONTROLLER_PASS: {RUN_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
