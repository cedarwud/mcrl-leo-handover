#!/usr/bin/env python3
"""Build a bounded multi-row informed Phase-I corpus for V0.3.

This runner is deliberately between the one-row engineering smoke and the
10--20 source-episode learnability pilot.  It materializes complete informed
C1/C3 selections from one keyed opening world and obtains several independent
real C2 temporal pairs on fresh TRAIN-only source seeds.  It never updates a
Q network and it makes no held-out EE claim.
"""

from __future__ import annotations

import argparse
import json
import math
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
import run_c2_v03_real_temporal_pair_smoke as c2_pair_smoke  # noqa: E402
import run_v03_opening_real_smoke as opening_smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_c1_selector import (  # noqa: E402
    C1FrontierConfig,
    select_c1_source,
)
from mcrl.runtime.ee_axis_opening_dataset import (  # noqa: E402
    EEAxisOpeningDataset,
    write_opening_dataset,
)
from mcrl.runtime.ee_axis_opening_runner import (  # noqa: E402
    materialize_opening_opportunity,
)
from mcrl.runtime.ee_axis_source_selectors import select_c3_source  # noqa: E402
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import (  # noqa: E402
    EEAxisTemporalDataset,
    write_temporal_dataset,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)


SCHEMA = "multi-catfish-mcrl-v03-phase1-informed-corpus-v1"
CLAIM_CEILING = "MULTIROW_SOURCE_CONSTRUCTION_ONLY_NOT_LEARNABILITY_OR_EE_EFFICACY"
SOURCE_SEED = opening_smoke.DEVELOPMENT_SEED
C2_SOURCE_SEEDS = tuple(SOURCE_SEED + offset for offset in range(8))
DEFAULT_C2_ROWS = 4
DEFAULT_C3_ANCHORS = 2


class Phase1CorpusError(RuntimeError):
    """The bounded informed corpus could not be closed."""


def _source_manifest_sha256() -> str:
    paths = list(_default_code_paths())
    paths.extend(sorted(C2_V03.glob("*.py")))
    paths.extend(
        [
            Path(opening_smoke.__file__),
            Path(c2_pair_smoke.__file__),
            Path(__file__),
        ]
    )
    unique = sorted({path.resolve() for path in paths}, key=lambda path: str(path))
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise Phase1CorpusError(f"source closure has missing files: {missing}")
    return _code_sha256(unique)


def _materialize_c3_corpus(
    trainer: Any,
    archive: Any,
    *,
    field: KeyedFadingField,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
    max_anchors: int,
    max_focal_users_per_anchor: int = 1,
    source_seed: int = SOURCE_SEED,
    max_source_steps: int = opening_smoke.MAX_SOURCE_STEPS,
) -> tuple[Any, ...]:
    if type(max_source_steps) is not int or max_source_steps < 1:
        raise Phase1CorpusError("max_source_steps must be a positive integer")
    wrapped, env_rng, _action_rng, _control_rng, states, masks, observation = (
        opening_smoke._reset(archive, field=field, source_seed=source_seed)
    )
    results: list[Any] = []
    admitted_anchors = 0
    for _ in range(max_source_steps):
        reference = opening_smoke._main_actions(
            trainer, wrapped, states, masks, observation, env_rng
        )
        state = encode_ee_axis_state(wrapped.environment, observation)
        anchor_sha256 = opening_smoke._canonical_sha256(
            {
                "schema": "multi-catfish-mcrl-v03-c3-phase1-anchor-v1",
                "seed": source_seed,
                "step_index": int(observation.step_index),
                "state_sha256": state.state_sha256,
                "reference_actions": [int(value) for value in reference.tolist()],
            }
        )
        plan = select_c3_source(
            wrapped.environment,
            observation,
            anchor_sha256=anchor_sha256,
            reference_actions=reference,
            max_focal_users=max_focal_users_per_anchor,
            state=state,
        )
        if plan is not None and admitted_anchors < max_anchors:
            # The informed source promise is full physical enumeration for
            # each selected focal user; do not truncate plan.opportunities.
            for opportunity in plan.opportunities:
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
                        other_route_source_rule="c1-audit-only-not-admitted-v1",
                        rng=env_rng,
                        lambda_bits_per_j=opening_smoke.LAMBDA_BITS_PER_J,
                        interval_s=interval_s,
                    )
                )
            admitted_anchors += 1
        following = opening_smoke._next(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    if admitted_anchors != max_anchors or not results:
        raise Phase1CorpusError(
            f"requested {max_anchors} informed C3 anchors, materialized {admitted_anchors}"
        )
    return tuple(results)


def _opening_corpus(
    *,
    tle_root: Path,
    source_manifest_sha256: str,
    c3_anchors: int,
    source_seed: int = SOURCE_SEED,
    c1_anchors: int = 2,
    c1_focal_users_per_anchor: int = 1,
    c3_focal_users_per_anchor: int = 1,
    max_source_steps: int = opening_smoke.MAX_SOURCE_STEPS,
) -> tuple[EEAxisOpeningDataset, dict[str, Any]]:
    if type(max_source_steps) is not int or max_source_steps < 1:
        raise Phase1CorpusError("max_source_steps must be a positive integer")
    minimum_c1_scan = 2 * c1_anchors
    if max_source_steps < minimum_c1_scan:
        raise Phase1CorpusError(
            "max_source_steps cannot support the requested lower-frontier C1 anchors"
        )
    if c3_anchors > max_source_steps:
        raise Phase1CorpusError("max_source_steps cannot support the requested C3 anchors")
    record = read_prereg(REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-opening-corpus-") as temporary:
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
        field = KeyedFadingField.from_components(
            "multi-catfish-mcrl-v03-phase1-opening-corpus-v1",
            checkpoint_sha256,
            source_seed,
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
            source_seed=source_seed,
            max_source_steps=max_source_steps,
        )
        selection = select_c1_source(
            (sample.record for sample in samples),
            config=C1FrontierConfig(
                lower_anchor_fraction=0.5,
                lower_user_fraction=0.5,
                max_anchors=c1_anchors,
                max_focal_users_per_anchor=c1_focal_users_per_anchor,
            ),
        )
        if selection is None:
            raise Phase1CorpusError("dull rollout produced no informed C1 plan")
        c1_results = opening_smoke._materialize_c1(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            opportunities=selection.opportunities,
            source_seed=source_seed,
            max_source_steps=max_source_steps,
        )
        c3_results = _materialize_c3_corpus(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            max_anchors=c3_anchors,
            max_focal_users_per_anchor=c3_focal_users_per_anchor,
            source_seed=source_seed,
            max_source_steps=max_source_steps,
        )
        if not c2_backend_smoke._networks_equal(trainer, network_before):
            raise Phase1CorpusError("opening source generation mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise Phase1CorpusError("opening source generation wrote Main replay")
        dataset = EEAxisOpeningDataset.from_results((*c1_results, *c3_results))
        receipt = {
            "checkpoint_sha256": checkpoint_sha256,
            "source_seed": source_seed,
            "common_random_field_sha256": field.root_digest,
            "dull_rollout_records": len(samples),
            "c1_selected_anchors": len(selection.selected_anchor_sha256s),
            "c1_selected_focal_users": len(selection.selected_focal_users),
            "c1_rows": len(dataset.c1_pairs),
            "c3_anchors": c3_anchors,
            "c3_focal_users_per_anchor": c3_focal_users_per_anchor,
            "c3_rows": len(dataset.c3_pairs),
            "source_steps": max_source_steps,
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
        }
        return dataset, receipt


def _temporal_corpus(
    *,
    tle_root: Path,
    source_manifest_sha256: str,
    requested_rows: int,
) -> tuple[EEAxisTemporalDataset, tuple[dict[str, Any], ...]]:
    pairs: list[Any] = []
    receipts: list[dict[str, Any]] = []
    for seed in C2_SOURCE_SEEDS:
        box: list[Any] = []
        try:
            receipt = c2_pair_smoke.run_real_temporal_pair_smoke(
                tle_root=tle_root,
                users=100,
                seed=seed,
                max_anchor_steps=6,
                max_candidates=1,
                materialization_out=box,
                source_manifest_override=source_manifest_sha256,
            )
        except Exception as error:
            receipts.append(
                {
                    "seed": seed,
                    "status": "NO_COMPLETE_PAIR",
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            continue
        if len(box) != 1:
            raise Phase1CorpusError("C2 source call did not return exactly one pair")
        pairs.append(box[0].pair)
        receipts.append(
            {
                "seed": seed,
                "status": "COMPLETE_PAIR",
                "anchor_step": receipt["anchor_step"],
                "comparison_sha256": box[0].pair.comparison_sha256,
                "target_surplus_bits": float(
                    box[0].pair.zeta2_temporal_surplus_bits
                ),
                "elapsed_s": float(receipt["elapsed_s"]),
            }
        )
        if len(pairs) == requested_rows:
            break
    if len(pairs) != requested_rows:
        raise Phase1CorpusError(
            f"requested {requested_rows} complete C2 rows, materialized {len(pairs)}"
        )
    return EEAxisTemporalDataset.from_pairs(pairs), tuple(receipts)


def run_corpus(
    *,
    output_dir: Path,
    tle_root: Path,
    c2_rows: int = DEFAULT_C2_ROWS,
    c3_anchors: int = DEFAULT_C3_ANCHORS,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite Phase-I corpus: {output_dir}")
    if type(c2_rows) is not int or not 2 <= c2_rows <= len(C2_SOURCE_SEEDS):
        raise ValueError("c2_rows must be between 2 and the sealed seed budget")
    if type(c3_anchors) is not int or not 1 <= c3_anchors <= opening_smoke.MAX_SOURCE_STEPS:
        raise ValueError("c3_anchors is outside the bounded opening schedule")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_manifest_sha256 = _source_manifest_sha256()
    opening, opening_receipt = _opening_corpus(
        tle_root=tle_root,
        source_manifest_sha256=source_manifest_sha256,
        c3_anchors=c3_anchors,
        source_seed=SOURCE_SEED,
    )
    temporal, temporal_receipts = _temporal_corpus(
        tle_root=tle_root,
        source_manifest_sha256=source_manifest_sha256,
        requested_rows=c2_rows,
    )
    if opening.checkpoint_sha256 != temporal.checkpoint_sha256:
        raise Phase1CorpusError("opening and temporal sources use different Main checkpoints")
    if opening.source_manifest_sha256 != temporal.source_manifest_sha256:
        raise Phase1CorpusError("opening and temporal sources use different manifests")
    opening_lambda = float(opening.rows[0].raw_pair.lambda_bits_per_j)
    if not math.isclose(
        opening_lambda,
        float(temporal.lambda_bits_per_j),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise Phase1CorpusError("opening and temporal sources use different lambda0")

    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        write_opening_dataset(staging / "opening-do.json", opening)
        write_temporal_dataset(staging / "temporal-dt.json", temporal)
        payload = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "training": False,
            "source_manifest_sha256": source_manifest_sha256,
            "checkpoint_sha256": opening.checkpoint_sha256,
            "lambda_bits_per_j": opening_lambda,
            "rows": {
                "C1": len(opening.c1_pairs),
                "C2": len(temporal.rows),
                "C3": len(opening.c3_pairs),
            },
            "opening_dataset_sha256": opening.verify(),
            "temporal_dataset_sha256": temporal.verify(),
            "opening_receipt": opening_receipt,
            "temporal_source_receipts": list(temporal_receipts),
            "elapsed_s": time.perf_counter() - started,
        }
        (staging / "receipt.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        shutil.move(str(staging), str(output_dir))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-phase1-informed-corpus-20260831",
    )
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(TLE_ROOT_DEFAULT).expanduser(),
    )
    parser.add_argument("--c2-rows", type=int, default=DEFAULT_C2_ROWS)
    parser.add_argument("--c3-anchors", type=int, default=DEFAULT_C3_ANCHORS)
    args = parser.parse_args()
    payload = run_corpus(
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        c2_rows=args.c2_rows,
        c3_anchors=args.c3_anchors,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
