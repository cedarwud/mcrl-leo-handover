#!/usr/bin/env python3
"""Post-gate launcher skeleton for the V0.19 five-arm TRAIN screen.

The launcher keeps the heavy/runtime part explicit while making the normal
post-gate path one function call.  It does not launch anything when imported
or when called with ``--print-inputs``.  After the V0.19 learner gate returns
``PASS_LEARNER_GATE``, the caller supplies the three Q3 checkpoint paths and
hashes (plus their initialization/source-lineage mapping), then this module
reuses the already-frozen Q1/Q2/Main runtime helpers and invokes the pure
five-arm loop.  No TEST world and no learner update are reachable here.

The default helper assembly mirrors the existing physical paths:

* Q1: frozen V0.3 checkpoint loader;
* Q2: frozen V0.14 learned-Q2 checkpoint loader and OPS-3 carrier state;
* Q3: V0.19 normalized relational learner checkpoint;
* MAIN: the independent frozen scalarized legacy policy;
* environment/RNG/archive: the canonical TRAIN-only server helpers.

No output directory is created until :meth:`V019PostPassRuntime.run` is
called explicitly.  This is intentionally a skeleton rather than a CLI that
can accidentally start a physical run from mutable defaults.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
V019_ROOT = HERE.parent
REPO = V019_ROOT.parents[1]
for _path in (REPO, REPO / "src", V019_ROOT / "learner"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402

from v019_physical_adapter import (  # noqa: E402
    V019PhysicalAdapter,
    V019PhysicalAdapterError,
    V019PostPassRuntime,
    V019Q3Head,
    V019Q3Panel,
    authenticate_gate_result,
    load_q3_head,
    screen,
)


DEFAULT_USERS = 100
DEFAULT_STEPS = 10
DEFAULT_EPISODES = 100
RUNTIME_INPUT_SCHEMA = "multi-catfish-mcrl-v019-five-arm-runtime-inputs-v1"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V019PhysicalAdapterError(f"cannot import runtime helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_existing_runtime_helpers() -> tuple[ModuleType, ModuleType, ModuleType, ModuleType]:
    """Load old helpers lazily; import has no environment or training side effect."""

    v015 = _load_module(
        REPO / ".scratch" / "multi-catfish-v015-c3-learned-context" / "run_v015_c3_learned_context_oracle.py",
        "mcrl_v019_v015_frozen_helpers",
    )
    v015_source = _load_module(
        REPO / ".scratch" / "multi-catfish-v015-c3-reference-gate" / "run_v015_reference_source_shard.py",
        "mcrl_v019_v015_physical_source_helpers",
    )
    main_loader = _load_module(
        REPO / "scripts" / "run_head_pivotality_probe.py",
        "mcrl_v019_main_runtime_loader",
    )
    main_source = _load_module(
        REPO / ".scratch" / "c3-v04" / "run_v04_c3_source.py",
        "mcrl_v019_main_policy_source",
    )
    return v015, v015_source, main_loader, main_source


@dataclass(frozen=True)
class RuntimeAssemblyInputs:
    """Explicit post-gate paths and world identity required for assembly."""

    gate_result_path: Path
    gate_result_sha256: str
    q3_checkpoint_paths_by_initialization: Mapping[int, Path]
    q3_checkpoint_sha256_by_initialization: Mapping[int, str]
    q3_source_lineage_by_initialization: Mapping[int, int]
    v03_root: Path
    q2_root: Path
    main_dir: Path
    prereg_path: Path
    tle_root: Path
    archive_root: Path
    field_component: str
    evaluation_seeds: tuple[int, ...]
    main_policy_sha256: str

    def verify_shape(self) -> None:
        if (
            len(self.q3_checkpoint_paths_by_initialization) != 3
            or len(self.q3_checkpoint_sha256_by_initialization) != 3
            or len(self.q3_source_lineage_by_initialization) != 3
        ):
            raise V019PhysicalAdapterError("post-gate Q3 inputs must contain exactly three initializations")
        if set(self.q3_checkpoint_paths_by_initialization) != set(self.q3_source_lineage_by_initialization):
            raise V019PhysicalAdapterError("Q3 checkpoint and source-lineage maps disagree")
        if len(self.evaluation_seeds) != DEFAULT_EPISODES or len(set(self.evaluation_seeds)) != DEFAULT_EPISODES:
            raise V019PhysicalAdapterError("post-gate physical screen requires 100 unique TRAIN world seeds")
        if not isinstance(self.field_component, str) or not self.field_component.strip():
            raise V019PhysicalAdapterError("field_component must be nonempty")


def assemble_post_pass_runtime(inputs: RuntimeAssemblyInputs) -> V019PostPassRuntime:
    """Authenticate PASS, load all frozen heads, and prepare callbacks/spec.

    This performs setup only.  It does not reset an environment or execute an
    episode; the returned runtime's ``run(output_dir=...)`` method is the
    explicit execution boundary.
    """

    inputs.verify_shape()
    v015, v015_source, main_loader, main_source = load_existing_runtime_helpers()
    gate = authenticate_gate_result(
        inputs.gate_result_path,
        expected_result_sha256=inputs.gate_result_sha256,
    )
    if set(inputs.q3_checkpoint_paths_by_initialization) != set(inputs.q3_checkpoint_sha256_by_initialization):
        raise V019PhysicalAdapterError("Q3 checkpoint path/hash maps have different initializations")
    heads: dict[int, V019Q3Head] = {}
    for init_raw, checkpoint in inputs.q3_checkpoint_paths_by_initialization.items():
        init = int(init_raw)
        heads[init] = load_q3_head(
            checkpoint,
            expected_checkpoint_sha256=inputs.q3_checkpoint_sha256_by_initialization[init],
            initialization_seed=init,
            source_lineage=int(inputs.q3_source_lineage_by_initialization[init]),
            contract_sha256=gate.contract_sha256,
            source_sha256=gate.source_sha256,
            code_manifest_sha256=gate.code_manifest_sha256,
            kappa_bits=float(OPS3_KAPPA_BITS),
        )
    panel = V019Q3Panel(gate=gate, heads_by_initialization=heads)
    panel.verify()
    q2_gate = v015.validate_v014_gate_receipts(inputs.q2_root)
    record = read_prereg(inputs.prereg_path)
    archive = main_loader._frozen_archive(record, inputs.tle_root, inputs.archive_root)
    main_trainer, _main_receipt = main_loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=inputs.main_dir,
        users=DEFAULT_USERS,
    )

    def q1_loader(source_lineage: int) -> tuple[Any, Mapping[str, Any]]:
        return v015.load_frozen_q1(inputs.v03_root, int(source_lineage))

    def q2_loader(source_lineage: int) -> tuple[Any, Mapping[str, Any]]:
        return v015.load_frozen_q2(
            inputs.q2_root,
            lineage=int(source_lineage),
            gate_receipt=q2_gate,
        )

    adapter = V019PhysicalAdapter(
        panel=panel,
        archive=archive,
        q1_loader=q1_loader,
        q2_loader=q2_loader,
        make_environment=lambda bound_archive, users: main_loader._make_environment(
            bound_archive, users=users
        ),
        rng_factory=v015._V013.screen._evaluation_rngs,
        main_trainer=main_trainer,
        main_actions=main_source._main_decision,
        main_policy_sha256=inputs.main_policy_sha256,
        q2_state_encoder=v015.encode_ee_axis_v014_q2_states,
        required_power_and_opening=v015_source.current_required_power_and_opening,
        field_component=inputs.field_component,
        field_factory=lambda component, seed: KeyedFadingField.from_components(component, seed),
        main_network_snapshot=main_source._network_snapshot,
        main_network_equal=main_source._networks_equal,
        main_replay_size=main_source._replay_size,
        users=DEFAULT_USERS,
        steps=DEFAULT_STEPS,
        kappa_bits=float(OPS3_KAPPA_BITS),
        pmax_w=float(v015_source.BEAM_POWER_MAX_W),
    )

    field_roots = tuple(
        (
            int(seed),
            KeyedFadingField.from_components(inputs.field_component, int(seed)).root_digest,
        )
        for seed in inputs.evaluation_seeds
    )
    bindings: list[screen.LineageBinding] = []
    for init, head in sorted(panel.heads_by_initialization.items()):
        q1, q1_receipt = q1_loader(head.source_lineage)
        q2, q2_receipt = q2_loader(head.source_lineage)
        del q1, q2
        q1_checkpoint = q1_receipt.get("checkpoint_sha256")
        q2_checkpoint = q2_receipt.get("checkpoint_sha256")
        if not isinstance(q1_checkpoint, str) or not isinstance(q2_checkpoint, str):
            raise V019PhysicalAdapterError("frozen Q1/Q2 receipt lacks checkpoint digest")
        bindings.append(
            screen.LineageBinding(
                initialization_seed=int(init),
                source_lineage=int(head.source_lineage),
                q1_checkpoint_sha256=q1_checkpoint,
                q2_checkpoint_sha256=q2_checkpoint,
                q3_checkpoint_sha256=head.checkpoint_sha256,
            )
        )
    spec = screen.V019FiveArmScreenSpec(
        evaluation_seeds=tuple(int(seed) for seed in inputs.evaluation_seeds),
        field_component=inputs.field_component,
        field_root_digests=field_roots,
        lineage_bindings=tuple(bindings),
        main_policy_sha256=inputs.main_policy_sha256,
        episodes=DEFAULT_EPISODES,
        checkpoint_every_episodes=100,
        users=DEFAULT_USERS,
        steps=DEFAULT_STEPS,
        evaluation_split="TRAIN",
        claim_ceiling=screen.CLAIM_CEILING,
        output_unit_mode="normalized_bits_per_kappa",
    )
    spec.verify()
    return V019PostPassRuntime(spec=spec, adapter=adapter)


def required_runtime_inputs() -> dict[str, object]:
    """Return a machine-readable post-gate fill-in checklist."""

    return {
        "schema": RUNTIME_INPUT_SCHEMA,
        "execution": "explicit V019PostPassRuntime.run(output_dir=...) only",
        "required_after_pass": [
            "gate_result_path_and_sha256",
            "three_q3_checkpoint_paths_hashes_initialization_seeds",
            "initialization_to_source_lineage_mapping",
            "frozen_q1_q2_main_roots_and_receipts",
            "canonical_prereg_tle_root_and_new_archive_root",
            "100_new_train_world_seeds_and_field_component",
            "main_policy_sha256",
            "new_empty_output_dir",
        ],
        "fixed": {
            "arms": ["FULL", "DROP_C1", "DROP_C2", "DROP_C3", "MAIN"],
            "episodes": 100,
            "checkpoint_every_episodes": 100,
            "users": 100,
            "steps": 10,
            "split": "TRAIN",
            "q3_output_unit_mode": "normalized_bits_per_kappa",
            "q3_reference": "argmax_safe(Q1+Q2)",
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-inputs",
        action="store_true",
        help="print the post-gate binding checklist without opening a simulator",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.print_inputs:
        raise SystemExit(
            "refusing implicit physical execution; use --print-inputs or call assemble_post_pass_runtime(...).run(...) explicitly"
        )
    import json

    print(json.dumps(required_runtime_inputs(), indent=2, sort_keys=True))
    return 0


__all__ = [
    "RUNTIME_INPUT_SCHEMA",
    "RuntimeAssemblyInputs",
    "V019PostPassRuntime",
    "assemble_post_pass_runtime",
    "load_existing_runtime_helpers",
    "main",
    "required_runtime_inputs",
]


if __name__ == "__main__":  # pragma: no cover - explicit checklist CLI
    raise SystemExit(main())
