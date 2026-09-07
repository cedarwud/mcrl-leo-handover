#!/usr/bin/env python3
"""Exercise one known-support C3 paired path outside the formal seed set."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import run_c3_disjoint_median_shadow as formal

from mcrl.runtime.prereg import read_prereg
from mcrl.runtime.training_pipeline import _code_sha256, _default_code_paths


DEVELOPMENT_SEED = 2026082701
MAX_STEPS = 3


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(formal.TLE_ROOT_DEFAULT).expanduser(),
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if formal.base.v1._sha256(formal.SPEC) != formal.SPEC_SHA256:
        raise RuntimeError("formal C3 specification changed")
    if (
        formal.base.v1._sha256(formal.SOURCE_DRIFT_MANIFEST)
        != formal.SOURCE_DRIFT_MANIFEST_SHA256
    ):
        raise RuntimeError("C3 source-drift manifest changed")
    if _code_sha256(_default_code_paths()) != formal.EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("analysis source differs from reviewed fingerprint")

    prereg = formal.base.v1.DEFAULT_PREREG
    record = read_prereg(prereg)
    if record.digest != formal.EXPECTED_PREREG_DIGEST:
        raise RuntimeError("frozen preregistration digest changed")
    if formal.base.v1._sha256(prereg) != formal.EXPECTED_PREREG_FILE_SHA256:
        raise RuntimeError("frozen preregistration file changed")

    store = formal._empty_observation_store()
    with tempfile.TemporaryDirectory(prefix="mcrl-c3-pair-path-smoke-") as temporary:
        archive = formal.base.v1._frozen_archive(
            record,
            args.tle_root,
            Path(temporary) / "frozen-tle",
        )
        trainer, checkpoint = formal.base.v1._verify_and_load_trainer(
            record,
            archive,
            run_dir=formal.base.v1.DEFAULT_INPUT / "main",
            users=formal.USERS,
        )
        if checkpoint["checkpoint_sha256"] != formal.EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint changed")
        if (
            checkpoint["launched_code_sha256"]
            != formal.EXPECTED_LAUNCHED_CODE_SHA256
        ):
            raise RuntimeError("launched code fingerprint changed")
        wrapped = formal.base.v1._make_environment(archive, users=formal.USERS)
        rollout = formal.run_seed(
            trainer=trainer,
            wrapped=wrapped,
            seed=DEVELOPMENT_SEED,
            max_steps=MAX_STEPS,
            observation_store=store,
        )

    paired = rollout["paired_rows"]
    if not paired:
        raise RuntimeError("known-support development smoke exercised no paired path")
    failures = list(rollout["engineering_failures"])
    if failures:
        raise RuntimeError("paired-path engineering failure: " + "; ".join(failures))
    for row in paired:
        if int(row["paired"]["horizon_intervals"]) <= 1:
            raise RuntimeError("paired-path smoke did not exercise Q1 continuation")
        checks = row["paired"]["cloned_state_checks"]["checks"]
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError("clone evidence failed: " + ", ".join(failed))

    print(
        json.dumps(
            {
                "schema": "mcrl-c3-paired-path-development-smoke-v1",
                "status": "pass",
                "formal_adjudication": False,
                "development_seed": DEVELOPMENT_SEED,
                "steps": rollout["steps"],
                "census_user_steps": rollout["census_user_steps"],
                "paired_rows": len(paired),
                "paired_locations": [
                    {
                        "step_index": row["step_index"],
                        "focal_user": row["focal_user"],
                        "reference_action": row["reference_action"],
                        "candidate_action": row["candidate_action"],
                        "engineering_failures": row["paired"][
                            "engineering_failures"
                        ],
                        "clone_checks": row["paired"]["cloned_state_checks"][
                            "checks"
                        ],
                    }
                    for row in paired
                ],
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
