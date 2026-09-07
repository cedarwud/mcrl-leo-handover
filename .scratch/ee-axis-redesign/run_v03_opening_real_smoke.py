#!/usr/bin/env python3
"""Real-TLE/checkpoint C1+C3 opening-source smoke for MCRL V0.3.

This is an engineering smoke, not an efficacy experiment.  It loads the
frozen 9,000-episode Main checkpoint, binds one keyed common-random fading
field, and proves that the current C1 and C3 selectors can each materialize a
real 228-D opening pair.  The Main networks, replay, and checkpoint remain
read-only and no V0.3 Q network is trained here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
import run_c2_v03_real_backend_smoke as c2_smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_c1_dull_source import (  # noqa: E402
    capture_c1_dull_rollout_sample,
    local_snr_dull_actions,
)
from mcrl.runtime.ee_axis_c1_selector import (  # noqa: E402
    C1FrontierConfig,
    select_c1_source,
)
from mcrl.runtime.ee_axis_opening_dataset import EEAxisOpeningDataset  # noqa: E402
from mcrl.runtime.ee_axis_opening_runner import (  # noqa: E402
    materialize_opening_opportunity,
)
from mcrl.runtime.ee_axis_source_selectors import (  # noqa: E402
    C3_NEUTRAL_SOURCE_RULE,
    select_c3_source,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)


DEVELOPMENT_SEED = 2026082801
MAX_SOURCE_STEPS = 4
SOURCE_POLICY_VERSION = 1
LAMBDA_BITS_PER_J = 84_994_621.12635651


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _environment(archive: Any, *, field: KeyedFadingField):
    wrapped = loader._make_environment(archive, users=c2_smoke.USERS)
    if wrapped.environment._started:
        raise RuntimeError("keyed fading must be bound before reset")
    wrapped.environment._fading_field = field
    return wrapped


def _reset(
    archive: Any,
    *,
    field: KeyedFadingField,
    source_seed: int = DEVELOPMENT_SEED,
):
    wrapped = _environment(archive, field=field)
    env_rng, mobility_rng, action_rng, control_rng = loader._evaluation_rngs(
        source_seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    return (
        wrapped,
        env_rng,
        action_rng,
        control_rng,
        states,
        masks,
        observation,
    )


def _main_actions(trainer: Any, wrapped: Any, states: Any, masks: Any, observation: Any, env_rng: Any):
    actions, _physical = c2_smoke._main_decision(
        trainer, wrapped, states, masks, observation, env_rng
    )
    return np.asarray(actions, dtype=np.int64)


def _next(wrapped: Any, actions: np.ndarray, env_rng: np.random.Generator):
    result = wrapped.step(actions, env_rng)
    if result.done:
        return None
    return result.user_states, result.action_masks, wrapped.last_outcome.observation


def _collect_c1_records(
    trainer: Any,
    archive: Any,
    *,
    field: KeyedFadingField,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    source_seed: int = DEVELOPMENT_SEED,
    max_source_steps: int = MAX_SOURCE_STEPS,
):
    if type(max_source_steps) is not int or max_source_steps < 1:
        raise ValueError("max_source_steps must be a positive integer")
    wrapped, env_rng, _action_rng, _control_rng, states, masks, observation = _reset(
        archive, field=field, source_seed=source_seed
    )
    samples = []
    for _ in range(max_source_steps):
        reference = _main_actions(
            trainer, wrapped, states, masks, observation, env_rng
        )
        sample = capture_c1_dull_rollout_sample(
            wrapped.environment,
            observation=observation,
            reference_actions=reference,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            source_seed=source_seed,
            rng=env_rng,
        )
        samples.append(sample)
        following = _next(wrapped, sample.dull_actions, env_rng)
        if following is None:
            break
        states, masks, observation = following
    return tuple(samples)


def _materialize_c1(
    trainer: Any,
    archive: Any,
    *,
    field: KeyedFadingField,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
    opportunities: tuple[Any, ...],
    source_seed: int = DEVELOPMENT_SEED,
    max_source_steps: int = MAX_SOURCE_STEPS,
):
    if type(max_source_steps) is not int or max_source_steps < 1:
        raise ValueError("max_source_steps must be a positive integer")
    by_step: dict[int, list[Any]] = {}
    for opportunity in opportunities:
        by_step.setdefault(int(opportunity.step_index), []).append(opportunity)
    wrapped, env_rng, _action_rng, _control_rng, states, masks, observation = _reset(
        archive, field=field, source_seed=source_seed
    )
    results = []
    for _ in range(max_source_steps):
        for opportunity in by_step.get(int(observation.step_index), []):
            result = materialize_opening_opportunity(
                wrapped.environment,
                observation=observation,
                state_observation=encode_ee_axis_state(
                    wrapped.environment, observation
                ),
                opportunity=opportunity,
                source_policy_version=SOURCE_POLICY_VERSION,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                common_random_field=field,
                other_route_source_rule=C3_NEUTRAL_SOURCE_RULE,
                rng=env_rng,
                lambda_bits_per_j=LAMBDA_BITS_PER_J,
                interval_s=interval_s,
            )
            results.append(result)
        dull = local_snr_dull_actions(observation)
        following = _next(wrapped, dull, env_rng)
        if following is None:
            break
        states, masks, observation = following
    if not results:
        raise RuntimeError("selected C1 opportunity was not reached on deterministic replay")
    return tuple(results)


def _materialize_c3(
    trainer: Any,
    archive: Any,
    *,
    field: KeyedFadingField,
    source_manifest_sha256: str,
    checkpoint_sha256: str,
    interval_s: float,
):
    wrapped, env_rng, _action_rng, _control_rng, states, masks, observation = _reset(
        archive, field=field
    )
    for _ in range(MAX_SOURCE_STEPS):
        reference = _main_actions(
            trainer, wrapped, states, masks, observation, env_rng
        )
        state = encode_ee_axis_state(wrapped.environment, observation)
        anchor_sha256 = _canonical_sha256(
            {
                "schema": "multi-catfish-mcrl-v03-c3-opening-smoke-anchor-v1",
                "seed": DEVELOPMENT_SEED,
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
            max_focal_users=1,
            state=state,
        )
        if plan is not None:
            opportunity = plan.opportunities[0]
            return materialize_opening_opportunity(
                wrapped.environment,
                observation=observation,
                state_observation=state,
                opportunity=opportunity,
                source_policy_version=SOURCE_POLICY_VERSION,
                source_manifest_sha256=source_manifest_sha256,
                checkpoint_sha256=checkpoint_sha256,
                common_random_field=field,
                other_route_source_rule="c1-audit-only-not-admitted-v1",
                rng=env_rng,
                lambda_bits_per_j=LAMBDA_BITS_PER_J,
                interval_s=interval_s,
            )
        following = _next(wrapped, reference, env_rng)
        if following is None:
            break
        states, masks, observation = following
    raise RuntimeError("no eligible C3 opening source found in bounded smoke")


def run_smoke(
    *,
    tle_root: Path,
    dataset_out: list[EEAxisOpeningDataset] | None = None,
    source_manifest_override: str | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    record = read_prereg(REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-opening-smoke-") as temporary:
        archive = c2_probe._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = loader._verify_and_load_trainer(
            record,
            archive,
            run_dir=REPO / "artifacts" / "training-2026-08-25-rerun01" / "main",
            users=c2_smoke.USERS,
        )
        checkpoint_sha256 = str(checkpoint["checkpoint_sha256"])
        source_manifest_sha256 = (
            _code_sha256(_default_code_paths())
            if source_manifest_override is None
            else source_manifest_override
        )
        if (
            not isinstance(source_manifest_sha256, str)
            or len(source_manifest_sha256) != 64
            or any(value not in "0123456789abcdef" for value in source_manifest_sha256)
        ):
            raise ValueError("source manifest override must be lowercase SHA-256")
        field = KeyedFadingField.from_components(
            "multi-catfish-mcrl-v03-opening-real-smoke-v1",
            checkpoint_sha256,
            DEVELOPMENT_SEED,
        )
        interval_s = float(
            loader._make_environment(archive, users=c2_smoke.USERS)
            .environment.driver.config.ephemeris.time_step_s
        )
        samples = _collect_c1_records(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
        )
        selection = select_c1_source(
            (sample.record for sample in samples),
            config=C1FrontierConfig(
                lower_anchor_fraction=0.5,
                lower_user_fraction=0.5,
                max_anchors=1,
                max_focal_users_per_anchor=1,
            ),
        )
        if selection is None:
            raise RuntimeError("bounded dull rollout produced no eligible C1 source")
        c1_results = _materialize_c1(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
            opportunities=(selection.opportunities[0],),
        )
        c3_result = _materialize_c3(
            trainer,
            archive,
            field=field,
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
            interval_s=interval_s,
        )
        dataset = EEAxisOpeningDataset.from_results((*c1_results, c3_result))
        c1_batch = dataset.c1_batch()
        c3_batch = dataset.c3_batch()
        payload = {
            "schema": "multi-catfish-mcrl-v03-opening-real-smoke-v1",
            "status": "PASS",
            "claim_ceiling": "REAL_OPENING_SOURCE_PLUMBING_ONLY_NOT_LEARNABILITY_OR_EFFICACY",
            "training": False,
            "evaluation_seed": DEVELOPMENT_SEED,
            "checkpoint_sha256": checkpoint_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "common_random_field_sha256": field.root_digest,
            "state_dim": int(c1_batch.pair_batch.states.shape[1]),
            "c1_rows": len(c1_batch.comparison_sha256s),
            "c3_rows": len(c3_batch.comparison_sha256s),
            "c1_target_surplus_bits": [
                float(value) for value in c1_batch.pair_batch.target_surplus_bits
            ],
            "c3_target_surplus_bits": [
                float(value) for value in c3_batch.pair_batch.target_surplus_bits
            ],
            "opening_dataset_sha256": dataset.verify(),
            "elapsed_s": time.perf_counter() - started,
        }
        if dataset_out is not None:
            if dataset_out:
                raise RuntimeError("dataset_out must be an empty caller-owned list")
            dataset_out.append(dataset)
        return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(TLE_ROOT_DEFAULT).expanduser(),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO
        / "artifacts"
        / "multi-catfish-v03-opening-real-smoke-20260831.json",
    )
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(f"refusing to overwrite smoke output: {args.output}")
    payload = run_smoke(tle_root=args.tle_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
