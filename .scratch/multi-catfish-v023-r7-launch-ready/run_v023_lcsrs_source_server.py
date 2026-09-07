#!/usr/bin/env python3
"""Launch-ready R7 source-server seam.

Importing this module is intentionally inert.  It does not import the source
adapter, the staged runner, NumPy, PyTorch, the simulator, TLE code, or TEST.
Those modules are loaded only after the frozen launch manifest has been
authenticated by the importable ``launch_source`` seam.

The staged runner remains the owner of source receipt validation, sealing, and
write-once persistence.  This file only binds the authenticated
``V023SourceAdapterConfig`` to one frozen world and injects the runtime source
adapter into ``run_source_stage``.  There is no fallback/scaffold path: a
missing or drifted input fails closed before a source receipt is accepted.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import sys
import traceback
from types import ModuleType
from typing import Any, Mapping, Sequence

from preflight_r7_balanced import validate_manifest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNNER_PATH = HERE / "run_v023_lcsrs_observability_gate.py"
SOURCE_ADAPTER_PATH = HERE / "v023_lcsrs_source_adapter.py"
PREFLIGHT_PATH = HERE / "R7-PREFLIGHT-MANIFEST.json"
PREFLIGHT_DIGEST_PATH = HERE / "R7-PREFLIGHT-MANIFEST.sha256"
EXECUTION_ADDENDUM_PATH = (
    REPO / "docs" / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
)

WORLDS = tuple(range(2026121801, 2026121809))
LINEAGE = 2026092101
SOURCE_FAMILY = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
PLACEBO_KEY_SHA256 = "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"


class V023SourceServerError(RuntimeError):
    """A deliberate source-server boundary or frozen input failed."""


def _load_module(name: str, path: Path) -> ModuleType:
    """Load a sibling server module only after an explicit launch."""

    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023SourceServerError(f"required server module is missing or symlinked: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise V023SourceServerError(f"cannot load server module: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023SourceServerError(f"server module import failed: {target}") from error
    return module


def _assert_write_once(output: Path) -> Path:
    """Reject an existing/symlinked target before any adapter work."""

    target = Path(output).resolve(strict=False)
    if target.exists() or target.is_symlink():
        raise V023SourceServerError(f"refusing to overwrite source output: {target}")
    return target


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=int, choices=WORLDS, required=True)
    parser.add_argument(
        "--tle-root",
        type=Path,
        required=True,
        help="the authenticated external TRAIN TLE root (must match the frozen preflight default)",
    )
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=PREFLIGHT_PATH)
    parser.add_argument("--manifest-digest", type=Path, default=PREFLIGHT_DIGEST_PATH)
    parser.add_argument(
        "--execution-addendum",
        type=Path,
        default=EXECUTION_ADDENDUM_PATH,
    )
    parser.add_argument("--placebo-key", default=PLACEBO_KEY)
    parser.add_argument("--placebo-key-sha256", default=PLACEBO_KEY_SHA256)
    parser.add_argument("--lineage", type=int, default=LINEAGE)
    parser.add_argument("--source-family", default=SOURCE_FAMILY)
    parser.add_argument("--preflight-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _build_config(args: argparse.Namespace, adapter_module: ModuleType) -> Any:
    """Build the adapter's frozen configuration from explicit CLI values."""

    config_type = getattr(adapter_module, "V023SourceAdapterConfig", None)
    adapter_type = getattr(adapter_module, "V023RuntimeSourceAdapter", None)
    if not callable(config_type) or not callable(adapter_type):
        raise V023SourceServerError(
            "source adapter does not expose V023SourceAdapterConfig/V023RuntimeSourceAdapter"
        )
    try:
        return config_type(
            tle_root=Path(args.tle_root).resolve(strict=False),
            prereg=Path(args.prereg).resolve(strict=False),
            manifest=Path(args.manifest).resolve(strict=False),
            manifest_digest=Path(args.manifest_digest).resolve(strict=False),
            execution_addendum=Path(args.execution_addendum).resolve(strict=False),
            placebo_key=str(args.placebo_key),
            placebo_key_sha256=str(args.placebo_key_sha256),
            lineage=int(args.lineage),
            source_family=str(args.source_family),
        )
    except Exception as error:
        raise V023SourceServerError("frozen V0.23 source configuration rejected") from error


def _verify_frozen_tle(tle_root: Path, *, receipt: Mapping[str, Any]) -> None:
    """Verify the exact frozen TLE file set before loading source physics."""

    configuration = receipt.get("configuration")
    if not isinstance(configuration, Mapping):
        raise V023SourceServerError("launch receipt has no TLE configuration")
    tle = configuration.get("tle")
    if not isinstance(tle, Mapping):
        raise V023SourceServerError("launch receipt has no frozen TLE binding")
    expected_root = Path(str(tle.get("root_default", ""))).resolve(strict=False)
    expected_digest = str(tle.get("file_set_sha256", ""))
    if Path(tle_root).resolve(strict=False) != expected_root:
        raise V023SourceServerError("source TLE root disagrees with the frozen launch manifest")
    if len(expected_digest) != 64 or expected_digest.lower() != expected_digest:
        raise V023SourceServerError("frozen TLE file-set digest is malformed")
    if not expected_root.is_dir() or expected_root.is_symlink():
        raise V023SourceServerError("frozen TLE root is missing or symlinked")
    sys.path.insert(0, str(REPO / "src"))
    try:
        from mcrl.env.tle import TleArchive
        from mcrl.env.ephemeris import file_set_hash
        archive = TleArchive(expected_root)
        actual = file_set_hash(archive.manifest_rows(list(archive.dates)))
    except Exception as error:
        raise V023SourceServerError("frozen TLE file-set verification failed") from error
    if actual != expected_digest:
        raise V023SourceServerError("frozen TLE file-set digest drifted")


def launch_source(
    args: argparse.Namespace,
    *,
    runner_module: ModuleType | None = None,
    adapter_module: ModuleType | None = None,
) -> Path:
    """Run exactly one source shard through the injected production seam.

    ``runner_module`` and ``adapter_module`` are optional test seams.  Normal
    execution always loads the byte-addressed sibling modules here, after CLI
    parsing and the write-once check.
    """

    receipt = validate_manifest(
        Path(args.manifest),
        manifest_digest_path=Path(args.manifest_digest),
        repo=REPO,
        prereg_path=Path(args.prereg),
    )
    _verify_frozen_tle(Path(args.tle_root), receipt=receipt)
    output = _assert_write_once(Path(args.output))
    runner = runner_module or _load_module(
        "mcrl_v023_lcsrs_gate_runner_server", RUNNER_PATH
    )
    adapter = adapter_module or _load_module(
        "mcrl_v023_lcsrs_source_adapter_server", SOURCE_ADAPTER_PATH
    )
    source_spec_type = getattr(runner, "SourceShardSpec", None)
    run_stage = getattr(runner, "run_source_stage", None)
    adapter_type = getattr(adapter, "V023RuntimeSourceAdapter", None)
    if not callable(source_spec_type) or not callable(run_stage) or not callable(adapter_type):
        raise V023SourceServerError("runner/adapter source seam is incomplete")
    config = _build_config(args, adapter)
    try:
        runtime_adapter = adapter_type(config)
        spec = source_spec_type(
            world=int(args.world),
            output=output,
            preflight_manifest_sha256=str(args.preflight_sha256),
        )
        result = run_stage(spec, adapter=runtime_adapter)
    except Exception as error:
        raise V023SourceServerError("V0.23 source shard failed closed") from error
    if not isinstance(result, Path):
        # The current runner returns Path.  Do not silently accept a different
        # adapter return contract, because the shell launcher uses this as its
        # resumability boundary.
        raise V023SourceServerError("source runner returned an untyped output path")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = launch_source(args)
    except V023SourceServerError as error:
        print(
            f"SOURCE_ERROR world={args.world} pid={os.getpid()}: {error}",
            file=sys.stderr,
        )
        traceback.print_exception(error, file=sys.stderr)
        return 2
    print(f"SOURCE_PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
