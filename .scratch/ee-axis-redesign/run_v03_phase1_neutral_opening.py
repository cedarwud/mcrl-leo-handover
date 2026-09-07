#!/usr/bin/env python3
"""Build equal-budget neutral C1/C3 opening data for V0.3 ablations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
for path in (HERE, C2_V03, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_c2_v03_deterministic_plumbing_probe as c2_probe  # noqa: E402
import run_c2_v03_real_backend_smoke as c2_backend_smoke  # noqa: E402
import run_v03_opening_real_smoke as opening_smoke  # noqa: E402
import run_v03_phase1_informed_corpus as informed_runner  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_c1_selector import (  # noqa: E402
    C1FrontierConfig,
    C1_NEUTRAL_SOURCE_RULE,
    sample_c1_neutral_source,
    select_c1_source,
)
from mcrl.runtime.ee_axis_opening_dataset import (  # noqa: E402
    EEAxisOpeningDataset,
    write_opening_dataset,
)
from mcrl.runtime.ee_axis_opening_runner import materialize_opening_opportunity  # noqa: E402
from mcrl.runtime.ee_axis_source_selectors import (  # noqa: E402
    sample_c3_neutral_source,
    select_c3_source,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import _code_sha256, _default_code_paths  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-phase1-neutral-opening-v1"
CLAIM_CEILING = "EQUAL_BUDGET_NEUTRAL_SOURCE_CONSTRUCTION_ONLY_NOT_EE_EFFICACY"
C1_NEUTRAL_SEED = 2026083161
C3_NEUTRAL_SEED = 2026083162
DEFAULT_C3_ANCHORS = 2


class NeutralOpeningError(RuntimeError):
    """The matched neutral opening corpus could not be closed."""


def _source_manifest_sha256() -> str:
    paths = list(_default_code_paths())
    paths.extend(
        [
            Path(opening_smoke.__file__),
            Path(informed_runner.__file__),
            Path(__file__),
        ]
    )
    unique = sorted({path.resolve() for path in paths}, key=lambda path: str(path))
    return _code_sha256(unique)


def _materialize_c3_neutral(
    trainer: Any,
    archive: Any,
    *,
    field: KeyedFadingField,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
    max_anchors: int,
) -> tuple[tuple[Any, ...], tuple[dict[str, int], ...]]:
    wrapped, env_rng, _action_rng, _control_rng, states, masks, observation = (
        opening_smoke._reset(archive, field=field)
    )
    selection_rng = np.random.default_rng(C3_NEUTRAL_SEED)
    results: list[Any] = []
    receipts: list[dict[str, int]] = []
    admitted_anchors = 0
    for _ in range(opening_smoke.MAX_SOURCE_STEPS):
        reference = opening_smoke._main_actions(
            trainer, wrapped, states, masks, observation, env_rng
        )
        state = encode_ee_axis_state(wrapped.environment, observation)
        anchor_sha256 = opening_smoke._canonical_sha256(
            {
                "schema": "multi-catfish-mcrl-v03-c3-phase1-anchor-v1",
                "seed": opening_smoke.DEVELOPMENT_SEED,
                "step_index": int(observation.step_index),
                "state_sha256": state.state_sha256,
                "reference_actions": [int(value) for value in reference.tolist()],
            }
        )
        informed = select_c3_source(
            wrapped.environment,
            observation,
            anchor_sha256=anchor_sha256,
            reference_actions=reference,
            max_focal_users=1,
            state=state,
        )
        if informed is not None and admitted_anchors < max_anchors:
            neutral = sample_c3_neutral_source(informed, rng=selection_rng)
            if neutral.budget != informed.budget:
                raise NeutralOpeningError("C3 neutral/informed budgets disagree")
            for opportunity in neutral.opportunities:
                results.append(
                    materialize_opening_opportunity(
                        wrapped.environment,
                        observation=observation,
                        state_observation=state,
                        opportunity=opportunity,
                        source_policy_version=opening_smoke.SOURCE_POLICY_VERSION,
                        source_manifest_sha256=source_manifest_sha256,
                        checkpoint_sha256=checkpoint_sha256,
                        common_random_field=field,
                        other_route_source_rule=C1_NEUTRAL_SOURCE_RULE,
                        rng=env_rng,
                        lambda_bits_per_j=opening_smoke.LAMBDA_BITS_PER_J,
                        interval_s=interval_s,
                    )
                )
            receipts.append(
                {
                    "step_index": int(observation.step_index),
                    "informed_budget": informed.budget,
                    "neutral_budget": neutral.budget,
                    "eligible_opportunities": len(neutral.all_opportunities),
                }
            )
            admitted_anchors += 1
        following = opening_smoke._next(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    if admitted_anchors != max_anchors or not results:
        raise NeutralOpeningError(
            f"requested {max_anchors} C3 anchors, materialized {admitted_anchors}"
        )
    return tuple(results), tuple(receipts)


def run_neutral_opening(
    *, output_dir: Path, tle_root: Path, c3_anchors: int = DEFAULT_C3_ANCHORS
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite neutral opening corpus: {output_dir}")
    started = time.perf_counter()
    source_manifest_sha256 = _source_manifest_sha256()
    record = read_prereg(REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-neutral-opening-") as temporary:
        archive = c2_probe._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = loader._verify_and_load_trainer(
            record,
            archive,
            run_dir=REPO / "artifacts" / "training-2026-08-25-rerun01" / "main",
            users=c2_backend_smoke.USERS,
        )
        checkpoint_sha256 = str(checkpoint["checkpoint_sha256"])
        network_before = c2_backend_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        # Reuse the exact informed field root so neutral and informed opening
        # comparisons receive the same keyed physical randomness.
        field = KeyedFadingField.from_components(
            "multi-catfish-mcrl-v03-phase1-opening-corpus-v1",
            checkpoint_sha256,
            opening_smoke.DEVELOPMENT_SEED,
        )
        interval_s = float(
            loader._make_environment(archive, users=c2_backend_smoke.USERS)
            .environment.driver.config.ephemeris.time_step_s
        )
        samples = opening_smoke._collect_c1_records(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
        )
        informed_c1 = select_c1_source(
            (sample.record for sample in samples),
            config=C1FrontierConfig(
                lower_anchor_fraction=0.5,
                lower_user_fraction=0.5,
                max_anchors=2,
                max_focal_users_per_anchor=1,
            ),
        )
        if informed_c1 is None:
            raise NeutralOpeningError("dull rollout produced no matched informed C1 plan")
        neutral_c1 = sample_c1_neutral_source(
            informed_c1,
            rng=np.random.default_rng(C1_NEUTRAL_SEED),
        )
        if neutral_c1.budget != informed_c1.budget:
            raise NeutralOpeningError("C1 neutral/informed budgets disagree")
        c1_results = opening_smoke._materialize_c1(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            opportunities=neutral_c1.opportunities,
        )
        c3_results, c3_receipts = _materialize_c3_neutral(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            max_anchors=c3_anchors,
        )
        if not c2_backend_smoke._networks_equal(trainer, network_before):
            raise NeutralOpeningError("neutral opening construction mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise NeutralOpeningError("neutral opening construction wrote Main replay")
        dataset = EEAxisOpeningDataset.from_results((*c1_results, *c3_results))

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        write_opening_dataset(staging / "opening-do.json", dataset)
        payload = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "training": False,
            "source_manifest_sha256": source_manifest_sha256,
            "checkpoint_sha256": checkpoint_sha256,
            "common_random_field_sha256": field.root_digest,
            "selection_seeds": {"C1": C1_NEUTRAL_SEED, "C3": C3_NEUTRAL_SEED},
            "budgets": {
                "C1_informed": informed_c1.budget,
                "C1_neutral": neutral_c1.budget,
                "C3_informed": sum(row["informed_budget"] for row in c3_receipts),
                "C3_neutral": sum(row["neutral_budget"] for row in c3_receipts),
            },
            "rows": {"C1": len(dataset.c1_pairs), "C3": len(dataset.c3_pairs)},
            "c3_anchor_receipts": list(c3_receipts),
            "opening_dataset_sha256": dataset.verify(),
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
            "elapsed_s": time.perf_counter() - started,
        }
        (staging / "receipt.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        shutil.move(str(staging), str(output_dir))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-phase1-neutral-opening-20260831",
    )
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--c3-anchors", type=int, default=DEFAULT_C3_ANCHORS)
    args = parser.parse_args()
    payload = run_neutral_opening(
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        c3_anchors=args.c3_anchors,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
