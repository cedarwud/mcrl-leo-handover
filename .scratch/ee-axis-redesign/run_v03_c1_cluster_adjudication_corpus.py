#!/usr/bin/env python3
"""Build matched informed/cluster-neutral C1 corpora for adjudication.

This runner corrects the earlier row-budget control confound.  Both arms use
the same number of anchors, focal-user clusters, legal physical alternatives,
counterfactual evaluations, and Q1 updates.  It performs source generation
only; no Q network is trained and no EE-efficacy claim is made.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Iterable

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
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_c1_selector import (  # noqa: E402
    C1FrontierConfig,
    C1SourceSelection,
    sample_c1_cluster_matched_neutral_source,
    select_c1_source,
)
from mcrl.runtime.ee_axis_opening_dataset import (  # noqa: E402
    EEAxisOpeningDataset,
    write_opening_dataset,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)


SCHEMA = "multi-catfish-mcrl-v03-c1-cluster-adjudication-corpus-v1"
CLAIM_CEILING = "MATCHED_C1_SOURCE_CONSTRUCTION_ONLY_NOT_EE_EFFICACY"
DEFAULT_SOURCE_SEEDS = tuple(opening_smoke.DEVELOPMENT_SEED + i for i in range(4))
DEFAULT_MAX_ANCHORS = 8
DEFAULT_USERS_PER_ANCHOR = 4
DEFAULT_NEUTRAL_SEED = 2026083107
FIELD_SEED = 2026083108


class C1AdjudicationCorpusError(RuntimeError):
    """The matched C1 adjudication corpus could not be closed."""


def _source_manifest_sha256() -> str:
    paths = list(_default_code_paths())
    paths.extend(sorted(C2_V03.glob("*.py")))
    paths.extend((Path(opening_smoke.__file__), Path(__file__)))
    unique = sorted({path.resolve() for path in paths}, key=lambda path: str(path))
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise C1AdjudicationCorpusError(
            f"source closure has missing files: {missing}"
        )
    return _code_sha256(unique)


def _group_sizes(selection: C1SourceSelection) -> tuple[int, ...]:
    counts = Counter(
        (row.anchor_sha256, row.focal_user) for row in selection.opportunities
    )
    return tuple(sorted(int(value) for value in counts.values()))


def _anchors_to_user_counts(selection: C1SourceSelection) -> tuple[int, ...]:
    counts = Counter(anchor for anchor, _user in selection.selected_focal_users)
    return tuple(sorted(int(value) for value in counts.values()))


def _materialize(
    trainer: Any,
    archive: Any,
    *,
    field: KeyedFadingField,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
    selection: C1SourceSelection,
    source_seeds: tuple[int, ...],
    anchor_source_seeds: dict[str, int],
) -> EEAxisOpeningDataset:
    results: list[Any] = []
    for seed in source_seeds:
        opportunities = tuple(
            row
            for row in selection.opportunities
            if anchor_source_seeds.get(row.anchor_sha256) == seed
        )
        if not opportunities:
            continue
        results.extend(
            opening_smoke._materialize_c1(
                trainer,
                archive,
                field=field,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                interval_s=interval_s,
                opportunities=opportunities,
                source_seed=seed,
            )
        )
    if len(results) != selection.budget:
        raise C1AdjudicationCorpusError(
            "materialized C1 row count disagrees with the sealed selection"
        )
    return EEAxisOpeningDataset.from_results(results)


def _target_summary(dataset: EEAxisOpeningDataset) -> dict[str, Any]:
    values = np.asarray(
        [pair.zeta1_focal_surplus_bits for pair in dataset.c1_pairs],
        dtype=np.float64,
    )
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise C1AdjudicationCorpusError("C1 target vector is empty or non-finite")
    return {
        "count": int(values.size),
        "negative": int(np.count_nonzero(values < 0.0)),
        "zero": int(np.count_nonzero(values == 0.0)),
        "positive": int(np.count_nonzero(values > 0.0)),
        "mean_bits": float(np.mean(values)),
        "median_bits": float(np.median(values)),
        "minimum_bits": float(np.min(values)),
        "maximum_bits": float(np.max(values)),
    }


def run_corpus(
    *,
    output_dir: Path,
    tle_root: Path,
    source_seeds: Iterable[int] = DEFAULT_SOURCE_SEEDS,
    max_anchors: int = DEFAULT_MAX_ANCHORS,
    users_per_anchor: int = DEFAULT_USERS_PER_ANCHOR,
    neutral_seed: int = DEFAULT_NEUTRAL_SEED,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite C1 corpus: {output_dir}")
    seeds = tuple(int(seed) for seed in source_seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("source_seeds must be a nonempty unique sequence")
    if type(max_anchors) is not int or max_anchors <= 0:
        raise ValueError("max_anchors must be a positive exact integer")
    if type(users_per_anchor) is not int or users_per_anchor <= 0:
        raise ValueError("users_per_anchor must be a positive exact integer")
    if type(neutral_seed) is not int or neutral_seed < 0:
        raise ValueError("neutral_seed must be a nonnegative exact integer")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_manifest_sha256 = _source_manifest_sha256()
    record = read_prereg(REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-c1-cluster-") as temporary:
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
            SCHEMA, checkpoint_sha256, FIELD_SEED
        )
        interval_s = float(
            loader._make_environment(archive, users=c2_backend_smoke.USERS)
            .environment.driver.config.ephemeris.time_step_s
        )

        samples: list[Any] = []
        per_seed_records: dict[str, int] = {}
        for seed in seeds:
            current = opening_smoke._collect_c1_records(
                trainer,
                archive,
                field=field,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                source_seed=seed,
            )
            samples.extend(sample.record for sample in current)
            per_seed_records[str(seed)] = len(current)

        informed = select_c1_source(
            samples,
            config=C1FrontierConfig(
                lower_anchor_fraction=0.5,
                lower_user_fraction=0.5,
                max_anchors=max_anchors,
                max_focal_users_per_anchor=users_per_anchor,
            ),
        )
        if informed is None:
            raise C1AdjudicationCorpusError(
                "multi-seed dull rollout produced no informed C1 plan"
            )
        anchor_source_seeds = {
            sample.anchor_sha256: int(sample.source_seed) for sample in samples
        }
        if len(anchor_source_seeds) != len(samples):
            raise C1AdjudicationCorpusError(
                "dull-rollout anchors are not unique across source seeds"
            )
        neutral = sample_c1_cluster_matched_neutral_source(
            informed,
            rng=np.random.default_rng(neutral_seed),
        )
        if (
            informed.budget != neutral.budget
            or len(informed.selected_anchor_sha256s)
            != len(neutral.selected_anchor_sha256s)
            or len(informed.selected_focal_users)
            != len(neutral.selected_focal_users)
            or _group_sizes(informed) != _group_sizes(neutral)
            or _anchors_to_user_counts(informed)
            != _anchors_to_user_counts(neutral)
        ):
            raise C1AdjudicationCorpusError(
                "informed and neutral C1 cluster budgets are not exactly matched"
            )

        informed_dataset = _materialize(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            selection=informed,
            source_seeds=seeds,
            anchor_source_seeds=anchor_source_seeds,
        )
        neutral_dataset = _materialize(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            selection=neutral,
            source_seeds=seeds,
            anchor_source_seeds=anchor_source_seeds,
        )
        if not c2_backend_smoke._networks_equal(trainer, network_before):
            raise C1AdjudicationCorpusError("C1 source generation mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise C1AdjudicationCorpusError("C1 source generation wrote Main replay")

    for dataset in (informed_dataset, neutral_dataset):
        if dataset.source_manifest_sha256 != source_manifest_sha256:
            raise C1AdjudicationCorpusError("C1 dataset manifest drifted")
        if dataset.checkpoint_sha256 != checkpoint_sha256:
            raise C1AdjudicationCorpusError("C1 dataset checkpoint drifted")
        if dataset.common_random_field_sha256 != field.root_digest:
            raise C1AdjudicationCorpusError("C1 dataset random field drifted")
        if not math.isclose(
            float(dataset.rows[0].raw_pair.lambda_bits_per_j),
            opening_smoke.LAMBDA_BITS_PER_J,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise C1AdjudicationCorpusError("C1 dataset lambda0 drifted")

    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.", dir=output_dir.parent
    ) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        write_opening_dataset(staging / "informed-opening-do.json", informed_dataset)
        write_opening_dataset(
            staging / "cluster-neutral-opening-do.json", neutral_dataset
        )
        payload = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "training": False,
            "source_manifest_sha256": source_manifest_sha256,
            "checkpoint_sha256": checkpoint_sha256,
            "common_random_field_sha256": field.root_digest,
            "lambda_bits_per_j": opening_smoke.LAMBDA_BITS_PER_J,
            "source_seeds": list(seeds),
            "neutral_selection_seed": neutral_seed,
            "dull_rollout_records_by_seed": per_seed_records,
            "matched_budget": {
                "anchors": len(informed.selected_anchor_sha256s),
                "focal_user_clusters": len(informed.selected_focal_users),
                "rows_physical_evaluations_q1_updates": informed.budget,
                "users_per_anchor_profile": list(
                    _anchors_to_user_counts(informed)
                ),
                "legal_alternatives_per_user_profile": list(
                    _group_sizes(informed)
                ),
            },
            "informed": {
                "source_rule": informed.source_rule,
                "dataset_sha256": informed_dataset.verify(),
                "targets": _target_summary(informed_dataset),
            },
            "cluster_neutral": {
                "source_rule": neutral.source_rule,
                "dataset_sha256": neutral_dataset.verify(),
                "targets": _target_summary(neutral_dataset),
            },
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
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
        required=True,
    )
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(TLE_ROOT_DEFAULT).expanduser(),
    )
    parser.add_argument(
        "--source-seed",
        type=int,
        action="append",
        dest="source_seeds",
        help="repeat for each TRAIN-only source seed",
    )
    parser.add_argument("--max-anchors", type=int, default=DEFAULT_MAX_ANCHORS)
    parser.add_argument(
        "--users-per-anchor", type=int, default=DEFAULT_USERS_PER_ANCHOR
    )
    parser.add_argument("--neutral-seed", type=int, default=DEFAULT_NEUTRAL_SEED)
    args = parser.parse_args()
    payload = run_corpus(
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        source_seeds=(
            DEFAULT_SOURCE_SEEDS
            if args.source_seeds is None
            else tuple(args.source_seeds)
        ),
        max_anchors=args.max_anchors,
        users_per_anchor=args.users_per_anchor,
        neutral_seed=args.neutral_seed,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
