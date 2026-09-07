#!/usr/bin/env python3
"""Target-free design probe for an action-balanced C2 schedule selector.

This probe materializes no pair outcomes and writes no experiment artifact. It
keeps the binding maximum of five focal users per world anchor, replays the
already sealed 20-seed pool with a larger per-seed cluster ceiling, and reports
schedule action topology for the originally unsupported contrasts.
"""

from __future__ import annotations

from collections import Counter
import importlib.util
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location(
    "action_shared_source_for_balanced_probe",
    HERE / "run_v03_e1_action_shared_sources.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot import sealed action-shared source machinery")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
wrapper._install_protocol()
source = wrapper.source


PROBE_SEEDS = tuple(range(2026092201, 2026092221))
NEEDED_ACTIONS = (0, 4, 7, 9, 14, 18)


def run(*, source_root: Path, tle_root: Path) -> dict[str, object]:
    _manifest, prereg, _seals = source._load_authority(source_root)
    source_manifest_sha256 = str(prereg["source_manifest_sha256"])
    checkpoint_sha256 = str(prereg["checkpoint_sha256"])
    environment_source_sha256 = str(prereg["environment_source_sha256"])
    reward_source_sha256 = str(prereg["reward_source_sha256"])
    base_record = source.read_prereg(source.BASE_PREREG)

    original_cluster_cap = source.C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED
    if source.C2_MAX_FOCAL_USERS_PER_ANCHOR != 5:
        raise RuntimeError("binding C2 focal-user cap changed")
    source.C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED = 50
    schedules = {}
    receipts = []
    try:
        with tempfile.TemporaryDirectory(prefix="mcrl-c2-balanced-topology-") as tmp:
            archive = source.c2_probe._frozen_archive(
                base_record, tle_root, Path(tmp) / "frozen-tle"
            )
            trainer, checkpoint = source.loader._verify_and_load_trainer(
                base_record,
                archive,
                run_dir=source.BASE_CHECKPOINT_DIR,
                users=source.USERS,
            )
            if checkpoint.get("checkpoint_sha256") != checkpoint_sha256:
                raise RuntimeError("Main checkpoint differs from sealed source")
            for seed in PROBE_SEEDS:
                schedule, receipt = source._discover_c2_schedule(
                    trainer=trainer,
                    archive=archive,
                    seed=seed,
                    prereg_sha256=str(prereg["prereg_sha256"]),
                    source_manifest_sha256=source_manifest_sha256,
                    checkpoint_sha256=checkpoint_sha256,
                    environment_source_sha256=environment_source_sha256,
                    reward_source_sha256=reward_source_sha256,
                )
                schedules[seed] = schedule
                receipts.append(receipt)
    finally:
        source.C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED = original_cluster_cap

    pair_counts = Counter(
        (int(cluster.reference_action), int(cluster.candidate_action))
        for schedule in schedules.values()
        for cluster in schedule.clusters
    )
    evidence = {
        str(action): {
            "clusters": sum(
                action in (int(cluster.reference_action), int(cluster.candidate_action))
                for schedule in schedules.values()
                for cluster in schedule.clusters
            ),
            "seeds": sorted(
                seed
                for seed, schedule in schedules.items()
                if any(
                    action
                    in (int(cluster.reference_action), int(cluster.candidate_action))
                    for cluster in schedule.clusters
                )
            ),
        }
        for action in NEEDED_ACTIONS
    }
    return {
        "schema": "multi-catfish-mcrl-v03-c2-action-balanced-topology-probe-v1",
        "status": "DESIGN_DIAGNOSTIC_ONLY",
        "source_seeds": list(PROBE_SEEDS),
        "maximum_focal_users_per_world_anchor": 5,
        "maximum_scheduled_clusters_per_seed": 50,
        "target_values_read": False,
        "pair_outcomes_materialized": False,
        "validation_dataset_documents_opened": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "receipts": receipts,
        "needed_action_evidence": evidence,
        "pair_counts": {
            f"{reference}->{candidate}": count
            for (reference, candidate), count in sorted(pair_counts.items())
        },
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(source_root=args.source_root, tle_root=args.tle_root),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )
