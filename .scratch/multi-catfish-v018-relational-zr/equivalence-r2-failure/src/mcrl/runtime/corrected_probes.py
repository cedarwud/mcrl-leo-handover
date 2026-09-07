"""Corrected P2/P3/P7 execution against the frozen 2026-08-25 record.

The old convenience scripts are historical smoke runs: they use eight or
twelve hand-picked epochs and P3 runs only one policy.  This module is the
fresh-output execution path for the frozen 200/200/100-episode grid.

The frozen record specifies the epoch *distribution* but not a probe epoch
realisation seed.  The corrective execution addendum therefore keeps the
pre-existing probe master seed ``20260823`` and assigns SeedSequence children
0/1/2 to environment/mobility/action, with child 3 used only to draw episode
epochs.  This is a post-freeze operational correction sealed before the new
results, not a claim that the original record contained the missing seed.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.metadata
import json
import platform
from collections.abc import Mapping, Sequence
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..env.constants import TLE_ROOT_DEFAULT
from ..env.dwell import DwellConfig
from ..env.ephemeris import BlockAlternatingSplit, EpisodeStartSampler, TRAIN
from ..env.mobility import MobilityConfig
from ..env.reference_policy import (
    RANDOM_MASKED,
    REFERENCE_POLICY_NAMES,
    STAY_IF_POSSIBLE,
    build_reference_policy,
)
from ..env.scenario import ScenarioConfig, ScenarioDriver
from ..env.step import PhysicsConfig, StepEnvironment
from ..env.tle import TleArchive
from ..errors import MCRLContractError
from .prereg import PreregRecord, read_prereg
from .probe_harness import ProbeStreams
from .probe_p2 import run_probe_p2
from .probe_p3 import run_probe_p3
from .probe_p7 import run_probe_p7


REPO = Path(__file__).resolve().parents[3]
CANONICAL_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25.json"
CORRECTIVE_PROTOCOL = (
    REPO / "artifacts" / "CORRECTED-PROBE-PROTOCOL-2026-08-25.json"
)
DEFAULT_OUTPUT_DIR = REPO / "artifacts" / "probes-2026-08-25-rerun01"

CORRECTED_PROBE_SEED = 20260823
"""Existing pre-result probe seed retained by the corrective addendum."""

STREAM_LAYOUT: dict[str, int] = {
    "env": 0,
    "mobility": 1,
    "action": 2,
    "episode_epoch": 3,
}

RUNNER_SCHEMA = "mcrl-corrected-probes-v1"
PROTOCOL_SCHEMA = "mcrl-corrected-probe-protocol-v1"
C1_COMPARISON_DECIMALS = 3

PROTOCOL_STATUS = "SEALED-BEFORE-CORRECTED-PROBE-RESULTS"
PROTOCOL_DATE = "2026-08-25"
PROTOCOL_AUTHORITY = (
    "controller instruction '按照你的建議進行' authorizes the recommended "
    "corrected rerun protocol before any corrected probe result is observed"
)
PROTOCOL_CLAIM_BOUNDARY = (
    "This is a post-freeze corrective execution addendum. It does not claim "
    "that the 2026-08-25 prereg record originally contained a probe epoch seed."
)
MASTER_SEED_PROVENANCE = (
    "retained from the pre-result 2026-08-23 P2/P4/P5/P7 probe runner and P2 "
    "artifact; selected before corrected results, not tuned from them"
)
EPOCH_PROTOCOL: dict[str, str] = {
    "distribution": (
        "EpisodeStartSampler over the frozen train split: date uniform over "
        "available file dates and time uniform over [0,86400) seconds, "
        "floor-snapped to the frozen decision step"
    ),
    "matching": (
        "one 200-epoch schedule is drawn once; P2 and each P3 policy use all "
        "200 epochs; P7 arms use the same first 100 epochs"
    ),
    "seed_derivation": (
        "numpy SeedSequence(master_seed).spawn(4); child index 3 draws episode "
        "epochs"
    ),
}
RESULT_POLICY: dict[str, object] = {
    "c1_comparison_decimals": C1_COMPARISON_DECIMALS,
    "c1_comparison_rule": (
        "ROUND_HALF_UP the corrected continuous p95 to the three decimal places "
        "stored by the frozen resolved literal before testing equality"
    ),
    "c1_rule": "p95 of r1 over served steps under stay-if-possible",
    "c3_rule": (
        "p95 of abs(r3) over served steps under stay-if-possible, rounded to the "
        "nearest integer"
    ),
    "p6_on_mapping_change": "BLOCK",
    "p6_on_mapping_match": "UNLOCK",
    "required_artifact_on_change": (
        "a new visible corrective prereg seal that applies the already-declared "
        "deterministic mappings"
    ),
}
OUTPUT_POLICY: dict[str, str] = {
    "default_directory": "artifacts/probes-2026-08-25-rerun01",
    "existing_directory": "REFUSE",
    "historical_artifacts": "PRESERVE",
}


class EpochSampler(Protocol):
    def draw(self, rng: np.random.Generator) -> Any: ...


def read_corrective_protocol(path: str | Path = CORRECTIVE_PROTOCOL) -> dict[str, Any]:
    """Read and verify the post-freeze execution addendum's self-digest."""
    protocol_path = Path(path)
    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MCRLContractError("corrective probe protocol must be a JSON object")
    actual = payload.get("digest")
    hashable = dict(payload)
    hashable.pop("digest", None)
    expected = hashlib.sha256(
        json.dumps(hashable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if actual != expected:
        raise MCRLContractError(
            "corrective probe protocol digest does not match its contents"
        )
    if payload.get("schema") != PROTOCOL_SCHEMA:
        raise MCRLContractError(
            f"unknown corrective probe protocol schema {payload.get('schema')!r}"
        )
    return payload


def _mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MCRLContractError(f"{name} must be a mapping")
    return value


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise MCRLContractError(f"{name} must be a positive integer")
    return value


def _require_policy(actual: object, expected: str, *, probe: str) -> None:
    if actual != expected:
        raise MCRLContractError(
            f"{probe} policy drifted from the corrective runner contract: "
            f"expected {expected!r}, got {actual!r}"
        )


def build_probe_plan(record: PreregRecord) -> dict[str, Any]:
    """Derive the executable grid and corrected seams from one verified seal."""
    record.verify()
    sections = record.sections
    grid = _mapping(sections.get("probe_grid"), name="probe_grid")
    p2 = _mapping(grid.get("P2"), name="probe_grid.P2")
    p3 = _mapping(grid.get("P3"), name="probe_grid.P3")
    p7 = _mapping(grid.get("P7"), name="probe_grid.P7")

    for probe, entry in (("P2", p2), ("P3", p3), ("P7", p7)):
        if entry.get("split_part") != TRAIN:
            raise MCRLContractError(
                f"{probe} must run on the frozen train split, got "
                f"{entry.get('split_part')!r}"
            )

    _require_policy(p2.get("policy"), STAY_IF_POSSIBLE, probe="P2")
    _require_policy(
        p3.get("policy"), "all three reference policies", probe="P3"
    )
    _require_policy(
        p7.get("policy"),
        "random-masked, which stresses the mask hardest",
        probe="P7",
    )

    p2_sweep = _mapping(p2.get("sweep"), name="probe_grid.P2.sweep")
    dwell_steps = p2_sweep.get("dwell_steps")
    if not isinstance(dwell_steps, list) or not dwell_steps:
        raise MCRLContractError("probe_grid.P2 has no dwell_steps sweep")
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in dwell_steps):
        raise MCRLContractError("probe_grid.P2 dwell_steps must be positive integers")

    reference_policy = _mapping(
        sections.get("reference_policy"), name="reference_policy"
    )
    selection_policy = reference_policy.get("name")
    if selection_policy != STAY_IF_POSSIBLE:
        raise MCRLContractError(
            "the P3 selection mapping must use the frozen stay-if-possible "
            f"reference policy, got {selection_policy!r}"
        )
    reference_seed = _positive_int(
        reference_policy.get("seed"), name="reference_policy.seed"
    )
    training = _mapping(sections.get("training"), name="training")
    steps_per_episode = _positive_int(
        training.get("steps_per_episode"), name="training.steps_per_episode"
    )

    warm = _mapping(sections.get("segment_warm_start"), name="segment_warm_start")
    main_arm = _mapping(warm.get("main_arm"), name="segment_warm_start.main_arm")
    sensitivity_arm = _mapping(
        warm.get("sensitivity_arm"), name="segment_warm_start.sensitivity_arm"
    )
    if main_arm.get("mode") != "uniform-episode-length":
        raise MCRLContractError("the P7 main warm-start arm drifted")
    if sensitivity_arm.get("mode") != "uniform-segment-length":
        raise MCRLContractError("the P7 sensitivity warm-start arm drifted")
    segment_age_steps = _positive_int(
        sensitivity_arm.get("segment_age_steps"),
        name="segment_warm_start.sensitivity_arm.segment_age_steps",
    )

    antenna = _mapping(
        sections.get("antenna_and_link_budget"), name="antenna_and_link_budget"
    )
    fading = _mapping(
        antenna.get("fading_draw_grain"),
        name="antenna_and_link_budget.fading_draw_grain",
    )
    warm_identity = warm.get("historical_position_identity")
    fading_identity = fading.get("identity")
    if warm_identity != ["segment_age_steps", "norad_id"]:
        raise MCRLContractError("the corrected warm-start identity is absent")
    if fading_identity != ["user_id", "norad_id", "observation_step"]:
        raise MCRLContractError("the corrected fading path identity is absent")
    if fading.get("candidate_previous_overlap") != "reuse_candidate_draw":
        raise MCRLContractError("candidate/previous fading overlap is not corrected")

    return {
        "schema": RUNNER_SCHEMA,
        "prereg_digest": record.digest,
        "master_seed": CORRECTED_PROBE_SEED,
        "stream_layout": dict(STREAM_LAYOUT),
        "reference_policy_seed": reference_seed,
        "steps_per_episode": steps_per_episode,
        "epoch_protocol": dict(EPOCH_PROTOCOL),
        "P2": {
            "episodes": _positive_int(p2.get("episodes"), name="P2.episodes"),
            "users": _positive_int(p2.get("users"), name="P2.users"),
            "policy": STAY_IF_POSSIBLE,
            "dwell_steps": list(dwell_steps),
        },
        "P3": {
            "episodes": _positive_int(p3.get("episodes"), name="P3.episodes"),
            "users": _positive_int(p3.get("users"), name="P3.users"),
            "policies": list(REFERENCE_POLICY_NAMES),
            "selection_mapping_policy": selection_policy,
        },
        "P7": {
            "episodes": _positive_int(p7.get("episodes"), name="P7.episodes"),
            "users": _positive_int(p7.get("users"), name="P7.users"),
            "policy": RANDOM_MASKED,
            "arms": {
                "main": {"mode": "uniform-episode-length"},
                "sensitivity": {
                    "mode": "uniform-segment-length",
                    "segment_age_steps": segment_age_steps,
                },
            },
        },
        "runtime_invariants": {
            "warm_start_history_key": list(warm_identity),
            "fading_path_key": list(fading_identity),
            "candidate_previous_overlap": fading["candidate_previous_overlap"],
        },
    }


def assert_corrective_protocol_matches_plan(
    protocol: Mapping[str, Any],
    record: PreregRecord,
    plan: Mapping[str, Any],
) -> None:
    """Fail closed if the result-before addendum and executable plan diverge."""
    expected_grid = {
        "P2": {
            "episodes_per_arm": plan["P2"]["episodes"],
            "users": plan["P2"]["users"],
            "policy": plan["P2"]["policy"],
            "dwell_steps": plan["P2"]["dwell_steps"],
        },
        "P3": {
            "episodes_per_policy": plan["P3"]["episodes"],
            "users": plan["P3"]["users"],
            "policies": plan["P3"]["policies"],
            "selection_mapping_policy": plan["P3"]["selection_mapping_policy"],
        },
        "P7": {
            "episodes_per_arm": plan["P7"]["episodes"],
            "users": plan["P7"]["users"],
            "policy": plan["P7"]["policy"],
            "arms": plan["P7"]["arms"],
        },
    }
    actual = {
        "status": protocol.get("status"),
        "date": protocol.get("date"),
        "authority": protocol.get("authority"),
        "claim_boundary": protocol.get("claim_boundary"),
        "augments_prereg": protocol.get("augments_prereg"),
        "augments_prereg_digest": protocol.get("augments_prereg_digest"),
        "master_seed": protocol.get("master_seed"),
        "master_seed_provenance": protocol.get("master_seed_provenance"),
        "stream_layout": protocol.get("stream_layout"),
        "reference_policy_seed": protocol.get("reference_policy_seed"),
        "steps_per_episode": protocol.get("steps_per_episode"),
        "epoch_protocol": protocol.get("epoch_protocol"),
        "result_policy": protocol.get("result_policy"),
        "output_policy": protocol.get("output_policy"),
        "grid": protocol.get("grid"),
    }
    expected = {
        "status": PROTOCOL_STATUS,
        "date": PROTOCOL_DATE,
        "authority": PROTOCOL_AUTHORITY,
        "claim_boundary": PROTOCOL_CLAIM_BOUNDARY,
        "augments_prereg": str(CANONICAL_PREREG.relative_to(REPO)),
        "augments_prereg_digest": record.digest,
        "master_seed": plan["master_seed"],
        "master_seed_provenance": MASTER_SEED_PROVENANCE,
        "stream_layout": plan["stream_layout"],
        "reference_policy_seed": plan["reference_policy_seed"],
        "steps_per_episode": plan["steps_per_episode"],
        "epoch_protocol": EPOCH_PROTOCOL,
        "result_policy": RESULT_POLICY,
        "output_policy": OUTPUT_POLICY,
        "grid": expected_grid,
    }
    if actual != expected:
        differing = sorted(key for key in expected if actual[key] != expected[key])
        raise MCRLContractError(
            "corrective probe protocol disagrees with the executable plan in: "
            + ", ".join(differing)
        )


def draw_matched_epochs(
    sampler: EpochSampler,
    *,
    count: int,
    seed: int = CORRECTED_PROBE_SEED,
) -> tuple[Any, ...]:
    """Draw one shared epoch schedule without consuming probe env randomness."""
    count = _positive_int(count, name="epoch count")
    children = np.random.SeedSequence(seed).spawn(4)
    epoch_rng = np.random.default_rng(children[STREAM_LAYOUT["episode_epoch"]])
    return tuple(sampler.draw(epoch_rng) for _ in range(count))


def create_fresh_output_dir(path: str | Path) -> Path:
    """Create a result root while refusing every overwrite, including empty dirs."""
    output = Path(path)
    if output.exists():
        raise MCRLContractError(
            f"corrected probe output already exists: {output}; choose a fresh rerun id"
        )
    output.mkdir(parents=True, exist_ok=False)
    return output


def _round_half_up(value: float, *, decimals: int) -> Decimal:
    if not np.isfinite(value):
        raise MCRLContractError(f"calibration value must be finite, got {value!r}")
    quantum = Decimal(1).scaleb(-decimals)
    return Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)


def assert_decision_count(
    result: Mapping[str, object], *, expected: int, label: str
) -> None:
    """Require the actual user-decision rows promised by the frozen grid."""
    actual = result.get("decision_steps")
    if isinstance(actual, bool) or not isinstance(actual, (int, np.integer)):
        raise MCRLContractError(f"{label} did not report an integer decision_steps")
    if int(actual) != int(expected):
        raise MCRLContractError(
            f"{label} expected {int(expected)} decision rows, got {int(actual)}"
        )


def summarise_calibration_gate(
    record: PreregRecord,
    p3_results: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Compare corrected canonical-policy P3 outputs with the frozen mappings."""
    record.verify()
    policy = str(record.sections["reference_policy"]["name"])
    if policy not in p3_results:
        raise MCRLContractError(
            f"P3 did not report the selection-mapping policy {policy!r}"
        )
    result = p3_results[policy]
    r1 = _mapping(
        result.get("r1_over_served_steps"),
        name=f"P3[{policy}].r1_over_served_steps",
    )
    try:
        observed_c1 = float(r1["p95"])
        observed_c3 = int(result["qd_scale_p95_rounded"])
        decision_steps = int(result["decision_steps"])
        mappings = record.sections["selection_mappings"]
        frozen_c1 = float(mappings["Q-F c1 calibration scale"]["resolved"])
        frozen_c3 = int(mappings["Q-D r3 calibration scale"]["resolved"])
    except (KeyError, TypeError, ValueError) as error:
        raise MCRLContractError("P3 calibration output is incomplete") from error

    observed_c1_at_precision = _round_half_up(
        observed_c1, decimals=C1_COMPARISON_DECIMALS
    )
    frozen_c1_at_precision = _round_half_up(
        frozen_c1, decimals=C1_COMPARISON_DECIMALS
    )
    c1_match = observed_c1_at_precision == frozen_c1_at_precision
    c3_match = observed_c3 == frozen_c3
    unlocked = c1_match and c3_match
    return {
        "selection_mapping_policy": policy,
        "decision_steps": decision_steps,
        "c1": {
            "rule": "p95 of r1 over served steps",
            "frozen": frozen_c1,
            "corrected_observed": observed_c1,
            "comparison_decimals": C1_COMPARISON_DECIMALS,
            "frozen_at_comparison_precision": str(frozen_c1_at_precision),
            "observed_at_comparison_precision": str(observed_c1_at_precision),
            "matches_frozen": c1_match,
        },
        "c3": {
            "rule": "p95 of |r3| over served steps, rounded to nearest integer",
            "frozen": frozen_c3,
            "corrected_observed": observed_c3,
            "matches_frozen": c3_match,
        },
        "p6_unlocked": unlocked,
        "required_next_action": "run_p6" if unlocked else "corrective_refreeze",
    }


def _environment(
    archive: TleArchive,
    *,
    users: int,
    dwell_steps: int | None = None,
    physics: PhysicsConfig | None = None,
) -> StepEnvironment:
    scenario_kwargs: dict[str, object] = {
        "mobility": MobilityConfig(num_users=users)
    }
    if dwell_steps is not None:
        scenario_kwargs["dwell"] = DwellConfig(steps=dwell_steps)
    driver = ScenarioDriver(archive, ScenarioConfig(**scenario_kwargs))
    return StepEnvironment(driver, physics=physics or PhysicsConfig())


def _json_default(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    raise TypeError(f"cannot encode {type(value).__name__}")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _runtime_source_paths(prereg_path: Path) -> tuple[Path, ...]:
    paths = list((REPO / "src" / "mcrl").rglob("*.py"))
    paths.extend(
        (
            REPO / "scripts" / "run_corrected_probes.py",
            REPO / "pyproject.toml",
            CORRECTIVE_PROTOCOL,
            prereg_path,
        )
    )
    return tuple(sorted(set(paths), key=lambda path: str(path)))


def _source_hashes(prereg_path: Path) -> dict[str, str]:
    return {
        str(path.relative_to(REPO) if path.is_relative_to(REPO) else path): _sha256(path)
        for path in _runtime_source_paths(prereg_path)
    }


def _installed_dependency_versions() -> dict[str, str]:
    distributions = {
        "numpy": "numpy",
        "sgp4": "sgp4",
        "PyYAML": "PyYAML",
        "torch": "torch",
    }
    versions = {"python": platform.python_version()}
    for label, distribution in distributions.items():
        try:
            versions[label] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[label] = "MISSING"
    return versions


def build_probe_fingerprint(
    record: PreregRecord,
    prereg_path: str | Path = CANONICAL_PREREG,
) -> dict[str, object]:
    """Hash every live code/dependency input that can change probe meaning."""
    prereg_path = Path(prereg_path).resolve()
    sources = _source_hashes(prereg_path)
    source_bundle = hashlib.sha256()
    for label, digest in sources.items():
        source_bundle.update(label.encode("utf-8"))
        source_bundle.update(b"\0")
        source_bundle.update(digest.encode("ascii"))
        source_bundle.update(b"\0")
    payload: dict[str, object] = {
        "schema": "mcrl-corrected-probe-fingerprint-v1",
        "prereg_digest": record.digest,
        "corrective_protocol_digest": read_corrective_protocol()["digest"],
        "ephemeris_file_set_sha256": record.sections["ephemeris"][
            "file_set_sha256"
        ],
        "source_bundle_sha256": source_bundle.hexdigest(),
        "source_files_sha256": sources,
        "dependencies": _installed_dependency_versions(),
    }
    return payload | {"fingerprint_sha256": _json_sha256(payload)}


def assert_probe_fingerprint_unchanged(
    expected: Mapping[str, object],
    record: PreregRecord,
    prereg_path: str | Path,
) -> None:
    actual = build_probe_fingerprint(record, prereg_path)
    if actual != dict(expected):
        raise MCRLContractError(
            "corrected probe code/dependency fingerprint changed during execution"
        )


def assert_live_ephemeris_unchanged(
    record: PreregRecord, archive: TleArchive
) -> None:
    from .training_pipeline import assert_ephemeris_matches_record

    # Never revalidate through ``archive`` itself: TleArchive caches both its
    # path set and loaded daily files.  A new instance is what makes this check
    # see mid-run additions, removals, or byte edits.
    fresh_archive = TleArchive(Path(archive.root))
    assert_ephemeris_matches_record(record, archive=fresh_archive)


def validate_corrected_probe_setup(
    prereg_path: Path = CANONICAL_PREREG,
) -> tuple[PreregRecord, dict[str, Any], TleArchive, tuple[dt.datetime, ...]]:
    """Validate the seal/live ephemeris and materialise the matched schedule."""
    from .training_pipeline import assert_p6_protocol_matches_record

    prereg_path = Path(prereg_path).resolve()
    record = read_prereg(prereg_path)
    assert_p6_protocol_matches_record(record)
    plan = build_probe_plan(record)
    protocol = read_corrective_protocol()
    assert_corrective_protocol_matches_plan(protocol, record, plan)
    archive = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
    assert_live_ephemeris_unchanged(record, archive)
    _environment(archive, users=int(plan["P3"]["users"])).assert_ready_to_train()
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    count = max(
        int(plan[probe]["episodes"]) for probe in ("P2", "P3", "P7")
    )
    epochs = draw_matched_epochs(sampler, count=count)
    return record, plan, archive, epochs


def run_corrected_probes(
    prereg_path: Path = CANONICAL_PREREG,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    """Run P3/P7/P2, save each result, and leave P6 closed on scale drift."""
    prereg_path = Path(prereg_path).resolve()
    record, plan, archive, epochs = validate_corrected_probe_setup(prereg_path)
    run_fingerprint = build_probe_fingerprint(record, prereg_path)
    output = create_fresh_output_dir(output_dir)
    policy_seed = int(plan["reference_policy_seed"])
    steps_per_episode = int(plan["steps_per_episode"])

    result_files = {
        "P3": {
            name: f"p3-{name}.json" for name in plan["P3"]["policies"]
        },
        "P7": {"main": "p7-main.json", "sensitivity": "p7-sensitivity.json"},
        "P2": "p2.json",
    }
    manifest: dict[str, object] = {
        "schema": RUNNER_SCHEMA,
        "status": "sealed-before-results",
        "corrective_protocol": {
            "path": str(CORRECTIVE_PROTOCOL.relative_to(REPO)),
            "digest": read_corrective_protocol()["digest"],
            "claim": (
                "post-freeze execution addendum; frozen distribution retained; "
                "historical probe master seed retained; no old result overwritten"
            ),
        },
        "prereg_path": str(prereg_path),
        "prereg_digest": record.digest,
        "plan": plan,
        "epochs": [epoch.isoformat() for epoch in epochs],
        "result_files": result_files,
        "run_fingerprint": run_fingerprint,
    }
    manifest_digest = hashlib.sha256(
        json.dumps(
            manifest,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            default=_json_default,
        ).encode("utf-8")
    ).hexdigest()
    manifest["manifest_digest"] = manifest_digest
    _write_json(output / "execution-manifest.json", manifest)
    _write_json(
        output / "status.json",
        {
            "status": "running",
            "manifest_digest": manifest_digest,
            "completed": [],
        },
    )

    completed: list[str] = []
    try:
        p3_epochs = epochs[: int(plan["P3"]["episodes"])]
        p3_results: dict[str, Mapping[str, object]] = {}
        for policy_name in plan["P3"]["policies"]:
            assert_probe_fingerprint_unchanged(
                run_fingerprint, record, prereg_path
            )
            print(f"P3 {policy_name}: starting {len(p3_epochs)} episodes", flush=True)
            streams = ProbeStreams.spawn(CORRECTED_PROBE_SEED)
            result = run_probe_p3(
                prereg=record,
                policy=build_reference_policy(policy_name, policy_seed),
                environment=_environment(
                    archive, users=int(plan["P3"]["users"])
                ),
                epochs=p3_epochs,
                env_rng=streams.env,
                mobility_rng=streams.mobility,
                action_rng=streams.action,
            )
            assert_decision_count(
                result,
                expected=(
                    len(p3_epochs) * int(plan["P3"]["users"]) * steps_per_episode
                ),
                label=f"P3/{policy_name}",
            )
            assert_probe_fingerprint_unchanged(
                run_fingerprint, record, prereg_path
            )
            p3_results[policy_name] = result
            filename = result_files["P3"][policy_name]
            _write_json(output / filename, result)
            completed.append(f"P3:{policy_name}")
            _write_json(
                output / "status.json",
                {
                    "status": "running",
                    "manifest_digest": manifest_digest,
                    "completed": completed,
                },
            )
            print(f"P3 {policy_name}: complete", flush=True)

        p7_epochs = epochs[: int(plan["P7"]["episodes"])]
        p7_results: dict[str, Mapping[str, object]] = {}
        for arm_name, arm in plan["P7"]["arms"].items():
            assert_probe_fingerprint_unchanged(
                run_fingerprint, record, prereg_path
            )
            print(f"P7 {arm_name}: starting {len(p7_epochs)} episodes", flush=True)
            physics_kwargs: dict[str, object] = {
                "segment_warm_start": arm["mode"]
            }
            if "segment_age_steps" in arm:
                physics_kwargs["segment_age_steps"] = arm["segment_age_steps"]
            result = run_probe_p7(
                prereg=record,
                policy=build_reference_policy(RANDOM_MASKED, policy_seed),
                environment=_environment(
                    archive,
                    users=int(plan["P7"]["users"]),
                    physics=PhysicsConfig(**physics_kwargs),
                ),
                epochs=p7_epochs,
                streams=ProbeStreams.spawn(CORRECTED_PROBE_SEED),
            )
            assert_decision_count(
                result,
                expected=(
                    len(p7_epochs) * int(plan["P7"]["users"]) * steps_per_episode
                ),
                label=f"P7/{arm_name}",
            )
            assert_probe_fingerprint_unchanged(
                run_fingerprint, record, prereg_path
            )
            p7_results[arm_name] = result
            _write_json(output / result_files["P7"][arm_name], result)
            completed.append(f"P7:{arm_name}")
            _write_json(
                output / "status.json",
                {
                    "status": "running",
                    "manifest_digest": manifest_digest,
                    "completed": completed,
                },
            )
            print(f"P7 {arm_name}: complete", flush=True)

        p2_epochs = epochs[: int(plan["P2"]["episodes"])]
        assert_probe_fingerprint_unchanged(run_fingerprint, record, prereg_path)
        print(f"P2: starting {len(p2_epochs)} episodes per arm", flush=True)
        p2_result = run_probe_p2(
            prereg=record,
            policy_factory=lambda: build_reference_policy(
                STAY_IF_POSSIBLE, policy_seed
            ),
            environment_factory=lambda n: _environment(
                archive, users=int(plan["P2"]["users"]), dwell_steps=n
            ),
            epochs=p2_epochs,
            seed=CORRECTED_PROBE_SEED,
            dwell_candidates=plan["P2"]["dwell_steps"],
        )
        p2_arms = _mapping(p2_result.get("arms"), name="P2.arms")
        expected_p2_arms = {f"N={n}" for n in plan["P2"]["dwell_steps"]}
        if set(p2_arms) != expected_p2_arms:
            raise MCRLContractError(
                "P2 result arms disagree with the frozen dwell sweep"
            )
        for arm_name, arm_result in p2_arms.items():
            assert_decision_count(
                _mapping(arm_result, name=f"P2.{arm_name}"),
                expected=(
                    len(p2_epochs) * int(plan["P2"]["users"]) * steps_per_episode
                ),
                label=f"P2/{arm_name}",
            )
        assert_probe_fingerprint_unchanged(run_fingerprint, record, prereg_path)
        _write_json(output / result_files["P2"], p2_result)
        completed.append("P2")
        _write_json(
            output / "status.json",
            {
                "status": "running",
                "manifest_digest": manifest_digest,
                "completed": completed,
            },
        )
        print("P2: complete", flush=True)

        assert_probe_fingerprint_unchanged(run_fingerprint, record, prereg_path)
        assert_live_ephemeris_unchanged(record, archive)
        calibration = summarise_calibration_gate(record, p3_results)
        summary: dict[str, object] = {
            "status": "complete",
            "manifest_digest": manifest_digest,
            "prereg_digest": record.digest,
            "calibration_gate": calibration,
            "p6_unlocked": calibration["p6_unlocked"],
            "P2": {
                "episodes_per_arm": len(p2_epochs),
                "arms": list(p2_result["arms"]),
            },
            "P3": {
                "episodes_per_policy": len(p3_epochs),
                "policies": list(p3_results),
            },
            "P7": {
                "episodes_per_arm": len(p7_epochs),
                "arms": list(p7_results),
            },
        }
        _write_json(output / "summary.json", summary)
        _write_json(
            output / "status.json",
            {
                "status": "complete",
                "manifest_digest": manifest_digest,
                "completed": completed,
                "p6_unlocked": calibration["p6_unlocked"],
            },
        )
        return summary
    except Exception as error:
        _write_json(
            output / "status.json",
            {
                "status": "failed",
                "manifest_digest": manifest_digest,
                "completed": completed,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise
