#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""OOSPANEL: out-of-sample development Stage-C scoring panels.

Scientific producer: PANELBUILD's ``build_anchor`` (witness-ws), imported and
called unmodified.  Adapters reused from existing workspaces:

* PANELFIX/PANELZ/PANELV3 fail-closed C3 rule (exact width equality, no slicing);
* PANELFIX Q1-v2 projection, PANELZ population-z transform, PANELV3 Q1-v3 /
  Q1-v3-control projection, applied to exact non-primitive source rows;
* RANK2 clean evaluator path for the two reference objects: one fresh dense
  ``StepEvaluator(boundary_indices=(0,))`` per anchor with BASE entering through
  ``evaluate_many``; endpoints re-evaluated in one separate fresh realised
  full-48 ``evaluate_many`` batch; scalar ``StepEvaluator.evaluate`` replaced by
  a raising stub on that surface (zero calls asserted).

Development anchors only.  No evaluation-only claim date is read.  All writes
stay below /home/sat/mcrl-v025-oospanel-ws.  No route marginal is computed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

THREAD_VARIABLES = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
for _name in THREAD_VARIABLES:
    os.environ[_name] = "1"

WORKSPACE = Path("/home/sat/mcrl-v025-oospanel-ws")
PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
UPSTREAM = Path("/home/sat/mcrl-v025-witness-ws/scripts/build_stagec_scoring_panel.py")
Q1V2_PATH = Path("/home/sat/mcrl-v025-design-ws/q1_schema_v2.py")
ZSCORE_PATH = Path("/home/sat/mcrl-v025-design-ws/build_zscore_corpus.py")
Q1V3_PATH = Path("/home/sat/mcrl-v025-q1v3-ws/q1_schema_v3.py")
Q1V3_BUILD_PATH = Path("/home/sat/mcrl-v025-q1v3-ws/build_q1_v3_corpora.py")
FRAGMENTS = WORKSPACE / ".scratch/fragments"
ARTIFACTS = WORKSPACE / "artifacts"
MAX_RSS_BYTES = 5_000_000_000
ADDRESS_SPACE_GUARD = 12_000_000_000
TAPE_STEPS = 33
GEOMETRY_SOURCE = (
    "provider boundary-0 ECEF satellite/cell/user geometry; "
    "elevation cross-checked against PrimitiveStepArrays"
)

# ---------------------------------------------------------------- anchors ---
# Declared before any outcome was computed.  Rule: the first ten anchors, in
# the exact-source within-world generation order (step, then carrier order
# nearest/stay/random), of two declared development worlds whose start dates
# are not a training-source date of any learner corpus.
CARRIERS = ("nearest-eligible", "stay-if-possible", "random-masked")
PANEL_WORLDS = ("V025_PROBE/world/3", "V025_PROBE_R2/world/1")
PER_WORLD = 10
# DATE-ALLOCATION-DECISION-2026-09-10.md (sha256 1d747cc4...65a5) lines 49-52:
# committed development dates per role.  Tape start dates must fall inside.
DECLARED_DEVELOPMENT_DATES = {
    "V025_PROBE/world/3": ("Earlier evaluation world 3 -- Remains development evaluation",
                           ("2025-11-16",)),
    "V025_PROBE_R2/world/1": ("PROBE_R2 -- Remain development",
                              ("2026-05-30", "2025-07-28", "2026-05-01", "2026-05-28")),
    "V025_PROBE/world/1": ("Earlier source worlds 1/2 -- Remain source/development",
                           ("2026-01-07", "2026-03-11")),
    "V025_PROBE/world/2": ("Earlier source worlds 1/2 -- Remain source/development",
                           ("2026-01-07", "2026-03-11")),
}


def panel_specs() -> list[dict[str, object]]:
    specs = []
    for world_id in PANEL_WORLDS:
        for within in range(PER_WORLD):
            step, carrier_index = divmod(within, len(CARRIERS))
            specs.append({
                "panel_index": len(specs), "world_id": world_id,
                "anchor_index_within_world": within, "step_index": step,
                "carrier_index": carrier_index, "carrier": CARRIERS[carrier_index],
                "anchor_id": f"{world_id}|{step}|{CARRIERS[carrier_index]}",
                "declared_180_order_global_index": None,
            })
    return specs


# ---------------------------------------------------------------- schemas ---
SCHEMAS = ("q1v1", "q1v2", "q1v2z", "q1v3", "q1v3-control")
SCHEMA_RUNS = {
    "q1v1": ("/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910", 4000),
    "q1v2": ("/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z", 500),
    "q1v2z": ("/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z", 500),
    "q1v3": ("/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-step-decay-16seed-4000-20260910", 4000),
    "q1v3-control": ("/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-step-decay-16seed-4000-20260910", 4000),
}
IN_SAMPLE_RECEIPTS = {
    "q1v1": "/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.receipt.json",
    "q1v2": "/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v2.receipt.json",
    "q1v2z": "/home/sat/mcrl-v025-panelz-ws/artifacts/panel-q1v2z.receipt.json",
    "q1v3": "/home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3.receipt.json",
    "q1v3-control": "/home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3-control.receipt.json",
}
EXPECTED_WIDTHS = {
    "q1v1": {"C1": 16, "C2": 22, "C3": 240, "C3_MEMBER": 38},
    "q1v2": {"C1": 15, "C2": 22, "C3": 236, "C3_MEMBER": 36},
    "q1v2z": {"C1": 30, "C2": 44, "C3": 296, "C3_MEMBER": 66},
    "q1v3": {"C1": 16, "C2": 22, "C3": 240, "C3_MEMBER": 38},
    "q1v3-control": {"C1": 16, "C2": 22, "C3": 240, "C3_MEMBER": 38},
}


# ---------------------------------------------------------------- helpers ---
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("ascii")).hexdigest()


def peak_rss() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_rss(label: str = "") -> int:
    value = peak_rss()
    if value >= MAX_RSS_BYTES:
        raise MemoryError(f"peak RSS {value} is not below 5 GB ({label})")
    return value


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def beneath_workspace(path: Path) -> bool:
    try:
        Path(path).resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        return False
    return True


def streaming_json(path: Path, value: object) -> None:
    if not beneath_workspace(path):
        raise RuntimeError(f"write outside workspace refused: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoder = json.JSONEncoder(indent=2, sort_keys=True, allow_nan=False, ensure_ascii=True)
    with temporary.open("w", encoding="ascii") as handle:
        for chunk in encoder.iterencode(value):
            handle.write(chunk)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def enforce_runtime() -> None:
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if any(os.environ.get(name) != "1" for name in THREAD_VARIABLES):
        raise RuntimeError("all BLAS/OMP thread variables must equal 1")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        os.nice(15 - os.getpriority(os.PRIO_PROCESS, 0))
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("could not enforce nice -n 15")
    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = ADDRESS_SPACE_GUARD if hard == resource.RLIM_INFINITY else min(hard, ADDRESS_SPACE_GUARD)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


# ------------------------------------------------------- scalar guard -------
class EvaluateGuard:
    def __init__(self) -> None:
        self.strict_phase: str | None = None
        self.strict_calls = 0
        self.strict_by_phase: Counter = Counter()
        self.phase = "other"
        self.hits: Counter = Counter()
        self.misses: Counter = Counter()

    def snapshot(self) -> dict[str, object]:
        return {
            "strict_surface_scalar_evaluate_calls": self.strict_calls,
            "strict_surface_calls_by_phase": dict(self.strict_by_phase),
            "non_reference_scalar_evaluate_cache_hits_by_phase": dict(self.hits),
            "non_reference_scalar_evaluate_cache_misses_by_phase": dict(self.misses),
        }


GUARD = EvaluateGuard()


def install_guard(engine) -> None:
    original = engine.StepEvaluator.evaluate
    if getattr(original, "__oospanel_guard__", False):
        return

    def guarded(self, config):
        if GUARD.strict_phase is not None:
            GUARD.strict_calls += 1
            GUARD.strict_by_phase[GUARD.strict_phase] += 1
            raise AssertionError(
                f"scalar StepEvaluator.evaluate is forbidden on the clean path ({GUARD.strict_phase})"
            )
        if config.configuration_id in self._evaluated:
            GUARD.hits[GUARD.phase] += 1
        else:
            GUARD.misses[GUARD.phase] += 1
        return original(self, config)

    guarded.__oospanel_guard__ = True
    guarded.__wrapped__ = original
    engine.StepEvaluator.evaluate = guarded

    original_catalogue = engine._catalogue_with_census

    def phased_catalogue(*args, **kwargs):
        previous = GUARD.phase
        GUARD.phase = "catalogue"
        try:
            return original_catalogue(*args, **kwargs)
        finally:
            GUARD.phase = previous

    engine._catalogue_with_census = phased_catalogue


# ------------------------------------------------------------- context ------
class Context:
    """Process-wide handles and per-anchor hand-off state."""

    def __init__(self) -> None:
        enforce_runtime()
        self.builder = load_module("oospanel_upstream_panelbuild", UPSTREAM)
        self.panelceil = self.builder.load_module("oospanel_panelceil", self.builder.PANELCEIL_PATH)
        self.pilot = self.panelceil.load_pilot()       # inserts c1c2suff-ws/src on sys.path
        self.engine = self.pilot.ENGINE
        self.calibration = self.builder.load_calibration(self.pilot)
        install_guard(self.engine)
        self.q1v2 = load_module("oospanel_q1v2", Q1V2_PATH)
        sys.path.insert(0, str(ZSCORE_PATH.parent))
        self.zscore = load_module("oospanel_zscore", ZSCORE_PATH)
        self.q1v3 = load_module("oospanel_q1v3", Q1V3_PATH)
        self.q1build = load_module("oospanel_q1build", Q1V3_BUILD_PATH)
        self.setting = self.engine._setting("a-r0")
        self.run_setting = self.engine.run_setting_for("a-r0")
        self.input_sha256 = {
            str(path): sha256(Path(path)) for path in (
                UPSTREAM, self.builder.PANELCEIL_PATH, self.builder.PILOT_PATH,
                self.builder.CALIBRATION_PATH, Q1V2_PATH, ZSCORE_PATH, Q1V3_PATH,
                Q1V3_BUILD_PATH, Path(__file__).resolve(),
            )
        }
        self.schema_bindings = bind_schemas(self.builder)
        # hand-off state
        self.loader_rows: dict | None = None
        self.search = None
        self.full_built = None
        original_rows = self.pilot._build_anchor_rows
        pilot = self.pilot
        ctx = self

        def captured_rows(**kwargs):
            if pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK is not False:
                raise RuntimeError("primitive provider fallback is enabled; refusing feature build")
            previous = GUARD.phase
            GUARD.phase = "features_full_legal" if kwargs.get("full_legal_actions") else "features_shortlist"
            try:
                built = original_rows(**kwargs)
            finally:
                GUARD.phase = previous
            if kwargs.get("full_legal_actions"):
                ctx.full_built = built
            return built

        self.pilot._build_anchor_rows = captured_rows
        self.builder.c3_state = self.fail_closed_c3_state
        self.builder.load_exact_feature_rows = self.feature_loader
        self.tapes: dict[str, object] = {}
        self.providers: dict[str, object] = {}
        self.tape_records: dict[str, dict] = {}
        self.resolvers: dict[tuple[str, int], object] = {}

    # upstream seam: PANELFIX/PANELZ/PANELV3 exact-equality C3 rule
    @staticmethod
    def fail_closed_c3_state(pilot, tape, step_index, base, config, rows_by_action,
                             width: int, member_width: int):
        changed = tuple(user for user in sorted(base.mapping)
                        if base.mapping[user] != config.mapping[user])
        if len(changed) <= 1:
            return len(changed), [0.0] * width
        context = pilot._coalition_context(
            tape=tape, step_index=step_index, anchor=base, selected=config,
            rows_by_user_action=rows_by_action,
        )
        full = context.invariant_vector(member_width=member_width).tolist()
        if len(full) != width:
            raise RuntimeError(
                f"checkpoint C3 width {width} differs from complete bound encoder width "
                f"{len(full)}; truncation is forbidden"
            )
        return len(changed), full

    # upstream seam: state rows for the schema currently being encoded
    def feature_loader(self, source, widths):
        if self.loader_rows is None:
            raise RuntimeError("feature rows were not staged for this anchor/schema")
        for row in self.loader_rows.values():
            if len(row.q1_state) != widths["C1"] or len(row.q2_state) != widths["C2"]:
                raise RuntimeError("staged feature width differs from checkpoint width")
        return dict(self.loader_rows)

    def world(self, world_id: str):
        if world_id in self.tapes:
            return self.tapes[world_id], self.providers[world_id]
        from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
        from mcrl.physics_v025.tapes import build_world_tape
        started = time.perf_counter()
        provider = LegacyWorldProvider(role="pilot-source")
        tape = build_world_tape(domain=world_id, provider=provider, steps=TAPE_STEPS, start_time_s=0.0)
        attestation = provider.attestation(world_seed=tape.seed, steps=TAPE_STEPS)
        start_date = str(tape.protocol.start_utc)[:10]
        role, declared = DECLARED_DEVELOPMENT_DATES[world_id]
        if tape.protocol.split != "TRAIN" or attestation.split.upper() != "TRAIN":
            raise RuntimeError(f"{world_id} is not a TRAIN-split development world")
        if start_date not in declared:
            raise RuntimeError(f"{world_id} start date is not a declared development date for {role}")
        splits = sorted({str(part) for _date, part in attestation.opened_tle_splits})
        if any(part.upper() == "TEST" for part in splits):
            raise RuntimeError("development tape opened a TEST-split TLE file")
        self.tapes[world_id] = tape
        self.providers[world_id] = provider
        self.tape_records[world_id] = {
            "world_id": world_id, "world_seed": int(tape.seed), "tape_digest": tape.digest,
            "start_utc": str(tape.protocol.start_utc), "start_date": start_date,
            "split": tape.protocol.split, "attestation_split": attestation.split,
            "opened_tle_file_count": len(attestation.opened_tle_splits),
            "opened_tle_split_parts": splits,
            "declared_development_role": role,
            "declared_development_source": "DATE-ALLOCATION-DECISION-2026-09-10.md lines 49-52",
            "provider_role_label": "pilot-source",
            "steps": TAPE_STEPS, "construction_seconds": time.perf_counter() - started,
        }
        print(f"tape {world_id} date={start_date} split={tape.protocol.split} "
              f"peak_rss_bytes={check_rss('tape')}", flush=True)
        return tape, provider

    def resolver(self, world_id: str, tape, provider, step: int):
        key = (world_id, step)
        if key not in self.resolvers:
            self.resolvers[key] = self.q1v2.DecisionGeometryResolverV2(tape, provider, step)
        return self.resolvers[key]


def bind_schemas(builder) -> dict[str, dict[str, object]]:
    """Bind each encoding to its training launch-receipt schema digests."""

    result = {}
    for schema in SCHEMAS:
        run, epoch = SCHEMA_RUNS[schema]
        launch = json.loads(Path(run, "launch-receipt.json").read_text(encoding="ascii"))
        features = launch["feature_schema"]
        in_sample = json.loads(Path(IN_SAMPLE_RECEIPTS[schema]).read_text(encoding="ascii"))
        binding = in_sample["encoder_binding"]
        if (features["q1_schema_sha256"], features["q2_schema_sha256"]) != (
            binding["q1_schema_sha256"], binding["q2_schema_sha256"]
        ):
            raise RuntimeError(f"{schema}: launch-receipt digests differ from in-sample panel binding")
        seed = launch["seed_list"][0]
        checkpoint = Path(run, "checkpoints", f"learner-{seed}-epoch-{epoch:06d}.json")
        widths = builder.checkpoint_shape(checkpoint)
        if widths != EXPECTED_WIDTHS[schema]:
            raise RuntimeError(f"{schema}: checkpoint widths {widths} differ from expected")
        result[schema] = {
            "run": run, "q1_schema_sha256": features["q1_schema_sha256"],
            "q2_schema_sha256": features["q2_schema_sha256"],
            "launch_receipt_sha256": sha256(Path(run, "launch-receipt.json")),
            "width_checkpoint": str(checkpoint), "width_checkpoint_sha256": sha256(checkpoint),
            "widths": widths, "in_sample_panel_receipt": IN_SAMPLE_RECEIPTS[schema],
        }
    return result


# -------------------------------------------------------------- encoding ----
def identity_key(row):
    if bool(row.null_action):
        return (int(row.user_id), None)
    return (int(row.user_id), (int(row.action.norad_id), int(row.action.beam_chain_id)))


def encode_all(ctx: Context, built, tape, step: int, resolver) -> tuple[dict, dict]:
    """Encode one exact row population into all five schemas.

    Transforms are those of PANELFIX (v2), PANELZ (z over the population),
    PANELV3 (v3 / control, provider-array nominal gain with the redundant
    formula check).  Returns ({schema: {key: FeatureRow}}, stats).
    """
    FeatureRow = ctx.builder.FeatureRow
    q1v2, q1v3, q1build, zscore = ctx.q1v2, ctx.q1v3, ctx.q1build, ctx.zscore
    arrays = tape.steps[step].arrays
    if arrays is None:
        raise RuntimeError("exact encoding requires provider arrays")
    row_index = arrays._row_index()
    rows = list(built["rows"])
    by_key = built["rows_by_user_action"]
    if len(rows) != len(by_key) or any(identity_key(row) not in by_key for row in rows):
        raise RuntimeError("row population and keyed rows disagree")
    out = {schema: {} for schema in SCHEMAS}
    payloads = []
    max_gain_relative = 0.0
    for row in rows:
        key = identity_key(row)
        angle, elevation = resolver(row)
        null = bool(row.null_action)
        q1_v1 = tuple(float(value) for value in row.q1_state)
        q2 = tuple(float(value) for value in row.q2_state)
        outage = bool(row.outage)
        out["q1v1"][key] = FeatureRow(q1_v1, q2, outage)
        out["q1v2"][key] = FeatureRow(
            q1v2.upgrade_q1_state_v2(q1_v1, off_axis_angle_rad=angle,
                                     focal_elevation_deg=elevation, null_action=null),
            q2, outage,
        )
        if null:
            nominal_gain = None
        else:
            user, identity = key
            array_row = row_index[(user, identity)]
            nominal_gain = float(arrays.nominal_gain[0, array_row])
            slant = float(arrays.slants_km[0, array_row])
            peak_receive = 10.0 ** (q1build.RX_GAIN_MAX_DBI / 10.0)
            path_factor = q1build.LegacyWorldProvider._nominal_path_without_scintillation(
                q1build.np.asarray(slant), q1build.np.asarray(elevation),
                q1build.np.asarray(peak_receive),
            )
            recomputed = float(
                q1build.transmit_gain_linear(q1build.np.asarray(math.degrees(angle))) * path_factor
            )
            relative = abs(recomputed - nominal_gain) / nominal_gain
            max_gain_relative = max(max_gain_relative, relative)
            if relative > 1e-8:
                raise RuntimeError(f"regenerated nominal-gain formula audit failed: {relative}")
        for schema, control in (("q1v3", False), ("q1v3-control", True)):
            out[schema][key] = FeatureRow(
                q1v3.q1_v3_state_from_v1(
                    q1_v1, off_axis_angle_rad=angle, focal_elevation_deg=elevation,
                    nominal_gain=nominal_gain, null_action=null, control=control,
                ),
                q2, outage,
            )
        payloads.append(q1v2.project_row_payload_v2(
            row.payload(), off_axis_angle_rad=angle, focal_elevation_deg=elevation,
            geometry_source=GEOMETRY_SOURCE,
        ))
    import numpy as np
    zeros = {
        "q1_groups": np.zeros(15, dtype=np.int64), "q2_groups": np.zeros(22, dtype=np.int64),
        "q1_rows": np.zeros(15, dtype=np.int64), "q2_rows": np.zeros(22, dtype=np.int64),
    }
    z_digests = ctx.schema_bindings["q1v2z"]
    transformed, census = zscore.zscore_rows(
        payloads, q1_digest=z_digests["q1_schema_sha256"], q2_digest=z_digests["q2_schema_sha256"],
        all_q1=[], all_q2=[], zero_counts=zeros,
    )
    for row in rows:
        key = identity_key(row)
        z_key = (key[0], (None, None) if key[1] is None else key[1])
        q1_hex, q2_hex = transformed[z_key]
        out["q1v2z"][key] = FeatureRow(
            tuple(float.fromhex(value) for value in q1_hex),
            tuple(float.fromhex(value) for value in q2_hex),
            bool(row.outage),
        )
    for schema in SCHEMAS:
        widths = EXPECTED_WIDTHS[schema]
        for row in out[schema].values():
            if len(row.q1_state) != widths["C1"] or len(row.q2_state) != widths["C2"]:
                raise RuntimeError(f"{schema} encoded width drifted")
            if not all(math.isfinite(v) for v in row.q1_state + row.q2_state):
                raise RuntimeError(f"{schema} encoded state is non-finite")
    stats = {
        "rows": len(rows), "z_population": census,
        "max_regenerated_gain_formula_relative_error": max_gain_relative,
        "resolver_max_elevation_crosscheck_error_deg": float(
            resolver.maximum_elevation_crosscheck_error_deg
        ),
    }
    return out, stats


# ----------------------------------------------------- clean reference path ---
def make_clean_first_improvement(ctx: Context):
    panelceil = ctx.panelceil

    def clean_first_improvement(runner, calibration, tape, step_index, base, incumbent, run_setting):
        """panelceil.first_improvement with the two scalar reads made dense.

        Identical traversal (ascending users, declared legal-option order,
        ordered microbatches of 16, first strict guarded-F improvement,
        terminal zero-move certificate).  BASE enters the same fresh
        boundary-0 evaluator through evaluate_many; every profile is read
        from the dense cache; scalar evaluate raises.
        """
        GUARD.strict_phase = "reference_selection"
        try:
            evaluator = panelceil.new_selection_evaluator(runner, tape, step_index, incumbent, run_setting)
            evaluator.evaluate_many((base,))
            base_profile = evaluator._evaluated.get(base.configuration_id)
            if base_profile is None:
                raise RuntimeError("dense BASE is physically invalid")
            guard = panelceil.served(base_profile)
            started = time.perf_counter()
            options, census = runner._legal_options(tape, step_index)
            rekeys = runner._rekeyed_users(tape, step_index)
            current = base
            moves = [(0.0, base)]
            passes_with_moves = comparisons = submissions = 0
            while True:
                pass_started = time.perf_counter() - started
                moves_this_pass = 0
                terminal_counts = {
                    "legal_unilateral_alternatives_evaluated": 0,
                    "physically_invalid_alternatives": 0,
                    "service_guard_rejected_alternatives": 0,
                    "strictly_improving_alternatives": 0,
                }
                for user in sorted(options):
                    current_profile = evaluator._evaluated.get(current.configuration_id)
                    if current_profile is None:
                        raise RuntimeError("current iterate absent from the dense cache")
                    current_value = panelceil.objective(
                        runner, calibration, incumbent, current, current_profile, rekeys
                    )
                    identities = [row for row in options[user] if row != current.mapping[user]]
                    accepted = None
                    for offset in range(0, len(identities), panelceil.UNILATERAL_BATCH_SIZE):
                        batch = tuple(panelceil.candidate(
                            runner, base, current, user, identity, "panelceil-first-improvement",
                        ) for identity in identities[offset:offset + panelceil.UNILATERAL_BATCH_SIZE])
                        evaluator.evaluate_many(batch)
                        submissions += len(batch)
                        terminal_counts["legal_unilateral_alternatives_evaluated"] += len(batch)
                        for row in batch:
                            comparisons += 1
                            profile = evaluator._evaluated.get(row.configuration_id)
                            if profile is None:
                                terminal_counts["physically_invalid_alternatives"] += 1
                                continue
                            if panelceil.served(profile) < guard:
                                terminal_counts["service_guard_rejected_alternatives"] += 1
                                continue
                            value = panelceil.objective(runner, calibration, incumbent, row, profile, rekeys)
                            if value > current_value:
                                terminal_counts["strictly_improving_alternatives"] += 1
                                accepted = row
                                break
                        if accepted is not None:
                            current = accepted
                            moves_this_pass += 1
                            moves.append((time.perf_counter() - started, current))
                            break
                pass_finished = time.perf_counter() - started
                if moves_this_pass == 0:
                    if terminal_counts["strictly_improving_alternatives"] != 0:
                        raise RuntimeError("zero-move certificate contains an improvement")
                    break
                passes_with_moves += 1
            best_alternatives = {}
            for user in sorted(options):
                rows = []
                for identity in options[user]:
                    if identity == current.mapping[user]:
                        continue
                    row = panelceil.candidate(runner, base, current, user, identity,
                                              "panelceil-terminal-alternate")
                    profile = evaluator._evaluated.get(row.configuration_id)
                    if profile is not None:
                        rows.append((panelceil.objective(runner, calibration, incumbent, row, profile, rekeys),
                                     row.configuration_id, identity))
                if rows:
                    best_alternatives[user] = min(rows, key=lambda item: (-item[0], item[1]))[2]
            moves_by_budget = sum(1 for elapsed, _config in moves[1:] if elapsed <= 10.0)
            receipt = {
                "algorithm": "deterministic cyclic first-improvement",
                "candidate_order": "ascending user ID; each user's declared legal-option order",
                "microbatch_size": panelceil.UNILATERAL_BATCH_SIZE,
                "baseline_served_guard": guard,
                "legal_option_census": census,
                "accepted_moves": len(moves) - 1,
                "accepted_moves_by_10s": moves_by_budget,
                "passes_with_moves": passes_with_moves,
                "total_passes_including_certificate": passes_with_moves + 1,
                "candidate_comparisons_through_certificate": comparisons,
                "physically_submitted_candidates_through_certificate": submissions,
                "last_improvement_seconds": moves[-1][0],
                "finding_seconds": pass_started,
                "terminal_certificate_seconds": pass_finished - pass_started,
                "total_including_certificate_seconds": pass_finished,
                "selection_physical_boundary_evaluations": evaluator.physical_evaluations,
                "evaluator_path": (
                    "one fresh realised StepEvaluator(boundary_indices=(0,)); BASE populated by "
                    "evaluate_many before any read; all candidate microbatches through the same "
                    "evaluate_many cache; profiles read from _evaluated only; scalar evaluate raises"
                ),
                "termination_certificate": {
                    "complete": True,
                    "statement": "Every legal unilateral alternative was evaluated at the final iterate and none strictly improves guarded F.",
                    **terminal_counts,
                },
            }
            run = panelceil.SearchRun(current, moves, receipt, best_alternatives)
            del evaluator
        finally:
            GUARD.strict_phase = None
        ctx.search = run
        return run

    return clean_first_improvement


def make_replay_first_improvement(ctx: Context):
    def replay(runner, calibration, tape, step_index, base, incumbent, run_setting):
        run = ctx.search
        if run is None or run.moves[0][1].assignments != base.assignments:
            raise RuntimeError("no clean search recorded for this anchor")
        return run
    return replay


def endpoint_batch(ctx: Context, tape, step: int, incumbent, configs: dict, anchor: dict) -> dict:
    """One separate fresh realised full-48 evaluate_many batch for the endpoints."""
    builder, engine = ctx.builder, ctx.engine
    GUARD.strict_phase = "endpoint_batch"
    try:
        evaluator = engine.StepEvaluator(
            tape, engine._setting("a-r0"), step, transition_from=incumbent,
            cell_rekeyed_users=engine._rekeyed_users(tape, step), field="realised",
            counter=engine.EvaluationCounter(), run_setting=ctx.run_setting,
            boundary_indices=tuple(range(48)),
        )
        unique = {}
        for config in configs.values():
            unique.setdefault(config.configuration_id, config)
        evaluator.evaluate_many(tuple(unique.values()))
        by_id = {profile["profile_id"]: profile for profile in anchor["profiles"]}
        result = {}
        for name, config in configs.items():
            profile = evaluator._evaluated.get(config.configuration_id)
            if profile is None:
                raise RuntimeError(f"endpoint {name} is physically invalid in the endpoint batch")
            separate = builder.outcome(ctx.pilot, tape, step, incumbent, profile)
            pid = builder.profile_id(config.configuration_id)
            catalogue = by_id[pid]["outcome"]
            result[name] = {
                "profile_id": pid, "endpoint_batch_outcome": separate,
                "catalogue_outcome_equal": separate == catalogue,
            }
            if separate != catalogue:
                raise RuntimeError(f"endpoint {name}: separate dense batch differs from catalogue outcome")
        result["_batch"] = {
            "configs_in_single_evaluate_many_call": len(unique),
            "boundary_evaluations": evaluator.physical_evaluations,
        }
        del evaluator
    finally:
        GUARD.strict_phase = None
    return result


# ---------------------------------------------------------------- worker ----
def fragment_paths(panel_index: int) -> dict[str, Path]:
    paths = {schema: FRAGMENTS / schema / f"anchor-{panel_index:02d}.json" for schema in SCHEMAS}
    paths["core"] = FRAGMENTS / "core" / f"anchor-{panel_index:02d}.json"
    return paths


def build_one(ctx: Context, spec: dict, total: int) -> None:
    builder, pilot = ctx.builder, ctx.pilot
    world_id, step, carrier = spec["world_id"], int(spec["step_index"]), spec["carrier"]
    index = int(spec["panel_index"])
    started = time.perf_counter()
    tape, provider = ctx.world(world_id)
    resolver = ctx.resolver(world_id, tape, provider, step)
    base = ctx.engine._base_configuration(tape, step, carrier)
    incumbent = ctx.engine._base_configuration(tape, max(0, step - 1), carrier)
    guard_before = GUARD.snapshot()

    # 1. EXACTGEN2 view emulation: exact non-primitive shortlist rows.
    ctx.full_built = None
    previous = pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK
    pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK = False
    try:
        t0 = time.perf_counter()
        shortlist = pilot._build_anchor_rows(
            tape=tape, setting=ctx.setting, run_setting=ctx.run_setting,
            calibration=ctx.calibration, step_index=step, carrier=carrier,
            anchor_index=index, include_coalition=False, full_legal_actions=False,
        )
        shortlist_seconds = time.perf_counter() - t0
    finally:
        pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK = previous
    if shortlist["base"].assignments != base.assignments or shortlist["incumbent"].assignments != incumbent.assignments:
        raise RuntimeError("shortlist builder base/incumbent drifted")
    ctx.full_built = None
    views, view_stats = encode_all(ctx, shortlist, tape, step, resolver)
    shortlist_physics_calls = int(shortlist["physics_calls"])
    del shortlist
    gc.collect()
    print(f"anchor {index + 1}/{total} shortlist rows={view_stats['rows']} "
          f"seconds={shortlist_seconds:.1f} peak_rss_bytes={check_rss('shortlist')}", flush=True)

    source = {
        "index": index, "step_index": step, "carrier": carrier, "world_id": world_id,
        "anchor_index_within_world": spec["anchor_index_within_world"],
        "view_path": None, "view_sha256": None,
        "feature_source": "exact non-primitive shortlist rows (EXACTGEN2 view emulation) built in process",
    }

    # 2. Q1-v1 pass: catalogue, clean references, full-48 outcomes, states.
    ctx.search = None
    ctx.panelceil.first_improvement = make_clean_first_improvement(ctx)
    ctx.loader_rows = views["q1v1"]
    t0 = time.perf_counter()
    anchor_v1, audit_v1 = builder.build_anchor(
        pilot=pilot, panelceil=ctx.panelceil, calibration=ctx.calibration, tape=tape,
        source=source, widths=EXPECTED_WIDTHS["q1v1"], reused=None, cached_anchor=None,
        total=total,
    )
    v1_seconds = time.perf_counter() - t0
    search = ctx.search
    if search is None:
        raise RuntimeError("clean search was not invoked")
    fixed = search.selected
    anytime = ctx.panelceil.config_at(search, 10.0)
    if (anchor_v1["certified_fixed_point_profile_id"] != builder.profile_id(fixed.configuration_id)
            or anchor_v1["anytime_incumbent_profile_id"] != builder.profile_id(anytime.configuration_id)):
        raise RuntimeError("panel reference IDs differ from the clean search")

    full_stats = None
    full_enc = None
    if ctx.full_built is not None:
        full_enc, full_stats = encode_all(ctx, ctx.full_built, tape, step, resolver)
        full_physics_calls = int(ctx.full_built["physics_calls"])
        ctx.full_built = None
        gc.collect()
    else:
        full_physics_calls = 0
    missing_regenerated = int(audit_v1["missing_view_actions_regenerated_exactly"])

    # 3. Endpoints in one separate fresh realised dense full-48 batch.
    endpoints = endpoint_batch(ctx, tape, step, incumbent, {
        "base": base, "certified_fixed_point": fixed, "anytime_incumbent": anytime,
    }, anchor_v1)

    # 4. Remaining schemas: same catalogue/outcomes/references, re-encoded states.
    ctx.panelceil.first_improvement = make_replay_first_improvement(ctx)
    anchors = {"q1v1": anchor_v1}
    audits = {"q1v1": audit_v1}
    for schema in SCHEMAS[1:]:
        merged = dict(views[schema])
        if full_enc is not None:
            for key, row in full_enc[schema].items():
                merged.setdefault(key, row)
        ctx.loader_rows = merged
        anchor_s, audit_s = builder.build_anchor(
            pilot=pilot, panelceil=ctx.panelceil, calibration=ctx.calibration, tape=tape,
            source=source, widths=EXPECTED_WIDTHS[schema], reused=None,
            cached_anchor=anchor_v1, total=total,
        )
        if int(audit_s["missing_view_actions_regenerated_exactly"]) != 0:
            raise RuntimeError(f"{schema}: unexpected second exact regeneration")
        for field in ("anchor_id", "world_id", "date", "world_seed", "base_profile_id",
                      "certified_fixed_point_profile_id", "anytime_incumbent_profile_id"):
            if anchor_s[field] != anchor_v1[field]:
                raise RuntimeError(f"{schema}: {field} differs from the Q1-v1 physical content")
        if [p["profile_id"] for p in anchor_s["profiles"]] != [p["profile_id"] for p in anchor_v1["profiles"]]:
            raise RuntimeError(f"{schema}: catalogue drifted")
        if [p["outcome"] for p in anchor_s["profiles"]] != [p["outcome"] for p in anchor_v1["profiles"]]:
            raise RuntimeError(f"{schema}: outcomes drifted")
        if [p["C3"]["coalition_size"] for p in anchor_s["profiles"]] != [
            p["C3"]["coalition_size"] for p in anchor_v1["profiles"]
        ]:
            raise RuntimeError(f"{schema}: coalition sizes drifted")
        if EXPECTED_WIDTHS[schema]["C2"] == 22 and [p["C2"] for p in anchor_s["profiles"]] != [
            p["C2"] for p in anchor_v1["profiles"]
        ]:
            raise RuntimeError(f"{schema}: Q2-v1 state differs from Q1-v1 panel")
        anchors[schema] = anchor_s
        audits[schema] = audit_s
    # PANELV3 control check: identical except Q1 slot 15 (C1) / pooled member coordinates.
    for p3, pc in zip(anchors["q1v3"]["profiles"], anchors["q1v3-control"]["profiles"], strict=True):
        for a, b in zip(p3["C1"], pc["C1"], strict=True):
            for side in ("reference", "selected"):
                if a[side][:15] != b[side][:15] or b[side][15] != 0.0:
                    raise RuntimeError("control C1 differs outside slot 15 or slot 15 nonzero")
    guard_after = GUARD.snapshot()
    if guard_after["strict_surface_scalar_evaluate_calls"] != 0:
        raise AssertionError("strict surface recorded scalar evaluate calls")

    feature_source = (
        "exact non-primitive shortlist rows (EXACTGEN2 view emulation); "
        + (f"{missing_regenerated} required actions outside the shortlist regenerated by the exact "
           "full-legal branch (primitive fallback disabled)" if missing_regenerated else
           "no required action outside the shortlist")
    )
    for schema in SCHEMAS:
        audit = dict(audits[schema])
        audit["feature_source"] = feature_source + f"; encoded as {schema}"
        audit["missing_view_actions_regenerated_exactly"] = missing_regenerated
        audit["feature_physics_boundary_evaluations"] = shortlist_physics_calls + full_physics_calls
        audit["fixed_point_source"] = "producer computation on the clean dense path"
        audit["global_anchor_index"] = None
        audit["panel_index"] = index
        audit["outcome_physics_boundary_evaluations"] = audits["q1v1"]["outcome_physics_boundary_evaluations"]
        streaming_json(fragment_paths(index)[schema], {
            "spec": spec, "anchor": anchors[schema], "audit": audit,
        })
    receipt = dict(search.receipt)
    core = {
        "spec": spec, "tape": ctx.tape_records[world_id],
        "reference_search": receipt,
        "reference_profile_ids": {
            "base": anchor_v1["base_profile_id"],
            "certified_fixed_point": anchor_v1["certified_fixed_point_profile_id"],
            "anytime_incumbent": anchor_v1["anytime_incumbent_profile_id"],
        },
        "certified_equals_anytime": fixed.assignments == anytime.assignments,
        "endpoint_batch": endpoints,
        "guard_before": guard_before, "guard_after": guard_after,
        "shortlist": {**view_stats, "physics_calls": shortlist_physics_calls, "seconds": shortlist_seconds},
        "full_legal": None if full_stats is None else {**full_stats, "physics_calls": full_physics_calls},
        "missing_actions_regenerated": missing_regenerated,
        "q1v1_pass_seconds": v1_seconds,
        "catalogue_profiles": len(anchor_v1["profiles"]),
        "wall_seconds": time.perf_counter() - started,
        "peak_rss_bytes": check_rss("anchor"),
        "input_sha256": ctx.input_sha256,
    }
    streaming_json(fragment_paths(index)["core"], core)
    print(f"OOS anchor {index + 1}/{total} COMPLETE {spec['anchor_id']} "
          f"profiles={len(anchor_v1['profiles'])} moves={receipt['accepted_moves']} "
          f"moves_by_10s={receipt['accepted_moves_by_10s']} missing_regenerated={missing_regenerated} "
          f"wall_s={core['wall_seconds']:.1f} peak_rss_bytes={core['peak_rss_bytes']}", flush=True)
    del anchors, audits, views, full_enc
    gc.collect()


def worker(args) -> int:
    specs = panel_specs()
    wanted = [specs[i] for i in args.indices]
    if len({spec["world_id"] for spec in wanted}) != 1:
        raise RuntimeError("one worker process builds one world (one tape in memory)")
    ctx = Context()
    print(f"worker indices={args.indices} peak_rss_bytes={check_rss('imports')}", flush=True)
    for spec in wanted:
        paths = fragment_paths(int(spec["panel_index"]))
        if all(path.is_file() for path in paths.values()):
            print(f"anchor {int(spec['panel_index']) + 1}/{len(specs)} resume-complete", flush=True)
            continue
        build_one(ctx, spec, len(specs))
    print(f"worker done peak_rss_bytes={check_rss('final')}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("worker")
    w.add_argument("--indices", type=int, nargs="+", required=True)
    sub.add_parser("specs")
    args = parser.parse_args()
    if args.command == "specs":
        print(json.dumps(panel_specs(), indent=1))
        return 0
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
