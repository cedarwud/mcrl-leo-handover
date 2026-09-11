#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Build the Q1-v4 corpus family on the 93-anchor exact-label corpus.

Reads (never writes): the 93-anchor exact-label corpus (exact93-ws), the
datepool exact-source physics shards and manifest, the Q1 v2/v3 schema modules,
and the 22-anchor Q1-v3 corpus (cross-check only).  No physics world or
evaluator is constructed; every added value is computed from serialized,
digest-authenticated boundary-0 state.  Writes only under ROOT/artifacts.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
import time
from typing import Mapping, Sequence

ROOT = Path("/home/sat/mcrl-v025-q1v4-ws")
PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python").resolve()
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
CORPUS93 = Path("/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910")
CORPUS93_DIGEST = "db2b4007323530e7f239491858fe7bf41a54f62b468470051a82e4a3a178c94b"
DATEPOOL = Path("/home/sat/mcrl-v025-datepool-ws/artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM")
MANIFEST = DATEPOOL / "BUILD_NOT_CLAIM-manifest.json"
V3_CORPUS = Path("/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-exact-label-corpus-20260910")
V3_CORPUS_DIGEST = "a3e139737306df759b3febe4089eecbc3f0105da5314b578bdebbb18d0b6f59c"
Q1_V2_MODULE = Path("/home/sat/mcrl-v025-design-ws/q1_schema_v2.py")
Q1_V3_MODULE = Path("/home/sat/mcrl-v025-q1v3-ws/q1_schema_v3.py")
SRC = Path("/home/sat/mcrl-v025-retrain-ws/src")
PHYSICS_FILES = {
    "batch.py": "1b0064399d550213ed4937482112ac020bf39e4ef09348f989b881b6d6206b9e",
    "acm.py": "a797e894377b78d4d1fd2e6be41d63a331cefb43c20a6882a67ee09c15fc7ff5",
    "channel.py": "8c3a9b38bb26938be70785b9c8ec60a1a8d4be912a46924a9c27f6c7ee9ffa83",
    "constants_v025.py": "7863e136423bfac77a0c710d95f9e8b3fe36b928c0dc1ef1bb3b2f69a0ab1112",
}
OUT_TAG = "exact-label-corpus-93-20260911"
OUTPUTS = {name: ROOT / "artifacts" / f"q1v4-{name}-{OUT_TAG}" for name in
           ("none", "gain_only", "congestion_only", "both")}
RECEIPT = ROOT / "artifacts/q1v4-build-verification.json"
FAMILY = ROOT / "artifacts/q1v4-schema-family.json"
TABLE = ROOT / "artifacts/q1v4-feature-table.npz"

ANCHORS = 93
EXPECTED_SOURCE_ROWS = 90_938
EXPECTED_COALITION_ROWS = 19_116
EXPECTED_Q1_V1_DIGEST = "c002ea883a4ab727f9e00cc15866f5b9d37abca645963fd3db2f2db7c6cc887a"
EXPECTED_Q2_DIGEST = "a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c"
SOURCE_SCHEMA = "mcrl-v025-exact-source-view-shard-v1"
COALITION_SCHEMA = "mcrl-v025-stagec-c3-coalition-shard-v2"
PHYSICS_HEADER_SCHEMA = "mcrl-v025-exact-source-physics-shard-v1"
SAMPLE_SIZE = 2_000
SAMPLE_SEED = 20260910
MAX_AS_BYTES = 4_900_000_000

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))
import numpy as np  # noqa: E402

import mcrl  # noqa: E402
from mcrl.physics_v025.acm import rate_target_sinr  # noqa: E402
from mcrl.physics_v025.channel import noise_power_w, transmit_gain_linear  # noqa: E402
from mcrl.physics_v025.constants_v025 import (  # noqa: E402
    BEAM_BANDWIDTH_HZ, BEAM_RF_CAP_W, RATE_TARGET_BPS, RX_GAIN_MAX_DBI,
)
from mcrl.physics_v025.provider_legacy import LegacyWorldProvider  # noqa: E402
import q1_schema_v4 as v4  # noqa: E402


def log(message: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {message} peak_rss={peak_rss_bytes()}", flush=True)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def owned_python_processes() -> list[int]:
    pids = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            name = (entry / "comm").read_text(encoding="ascii").strip()
            if not name.startswith("python"):
                continue
            cwd = os.readlink(entry / "cwd")
        except (OSError, ValueError):
            continue
        if cwd.startswith(str(ROOT)):
            pids.append(int(entry.name))
    return sorted(pids)


def enforce_runtime() -> None:
    if Path(sys.executable).resolve() != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
        raise RuntimeError("niceness is below 16")
    wrong = {n: os.environ.get(n) for n in THREAD_VARS if os.environ.get(n) != "1"}
    if wrong:
        raise RuntimeError(f"BLAS/thread pins drifted: {wrong}")
    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MAX_AS_BYTES if hard == resource.RLIM_INFINITY else min(MAX_AS_BYTES, hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    if len(owned_python_processes()) > 3:
        raise RuntimeError(f"python-process cap exceeded: {owned_python_processes()}")
    if not str(Path(mcrl.__file__).resolve()).startswith(str(SRC)):
        raise RuntimeError(f"mcrl resolved outside the V0.25 source tree: {mcrl.__file__}")


def assert_resources() -> None:
    if peak_rss_bytes() >= 5_000_000_000:
        raise MemoryError("peak RSS reached the 5 GB ceiling")
    if len(owned_python_processes()) > 3:
        raise RuntimeError("python-process cap exceeded during run")


def verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    fields = sidecar.read_text(encoding="ascii").strip().split()
    actual = file_sha256(path)
    if len(fields) != 2 or fields[0] != actual or fields[1] != path.name:
        raise RuntimeError(f"SHA-256 sidecar disagreement: {path}")
    return actual


def read_canonical_jsonl(path: Path) -> list[dict[str, object]]:
    raw = path.read_bytes().splitlines()
    values = [json.loads(line.decode("ascii")) for line in raw]
    if any(line != canonical_bytes(value) for line, value in zip(raw, values, strict=True)):
        raise RuntimeError(f"JSONL is not canonical: {path}")
    return values


def write_jsonl(path: Path, values: Sequence[Mapping[str, object]]) -> str:
    if path.exists() or path.with_suffix(path.suffix + ".sha256").exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    digest = hashlib.sha256()
    with temporary.open("wb") as handle:
        for value in values:
            encoded = canonical_bytes(value) + b"\n"
            handle.write(encoded)
            digest.update(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    hexdigest = digest.hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(f"{hexdigest}  {path.name}\n", encoding="ascii")
    if verify_sidecar(path) != hexdigest:
        raise AssertionError("written shard sidecar did not round-trip")
    return hexdigest


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def corpus_inventory(corpus: Path) -> tuple[list[dict[str, str]], str]:
    files = sorted(p for p in (corpus / "views").rglob("*.jsonl") if p.is_file())
    inventory = [{"path": p.relative_to(corpus).as_posix(), "sha256": verify_sidecar(p)} for p in files]
    return inventory, canonical_sha256(inventory)


def fraction(payload: Mapping[str, object]) -> Fraction:
    raw = payload["fraction"]
    value = Fraction(int(raw[0]), int(raw[1]))
    if payload["float_hex"] != float.hex(float(value)):
        raise RuntimeError("exact rational/float-hex disagreement")
    return value


def label_identity(row: Mapping[str, object]) -> tuple[bool, bool]:
    extension = row["exact_source_view"]
    c1 = extension["c1_difference_surplus"]
    c2 = extension["c2_persistence_forecast"]
    c1_residual = abs(float.fromhex(row["c1_label_normalized_hex"]) - float.fromhex(c1["normalized_total"]["float_hex"]))
    c2_residual = abs(float.fromhex(row["c2_label_normalized_hex"]) - float.fromhex(c2["normalized_total"]["float_hex"]))
    c1_ok = fraction(c1["decomposition_residual"]) == 0 and c1_residual <= 1e-12
    c2_ok = (fraction(c2["decomposition_residual"]) == 0
             and fraction(c2["label_bits"]) == fraction(c2["forecast_surplus_bits"]) - fraction(c2["persistence_penalty_bits"])
             and c2_residual <= 1e-12)
    return c1_ok, c2_ok


def action_key(user_id: int, action: Mapping[str, object]) -> tuple:
    norad, beam = action["norad_id"], action["beam_chain_id"]
    return (int(user_id), None if norad is None else int(norad), None if beam is None else int(beam))


def recompute_nominal_gain(geometry: Mapping[str, object]) -> float:
    angle = float.fromhex(geometry["true_off_axis_angle_deg_hex"])
    slant = float.fromhex(geometry["slant_km_hex"])
    elevation = float.fromhex(geometry["elevation_deg_hex"])
    path = LegacyWorldProvider._nominal_path_without_scintillation(
        np.asarray(slant), np.asarray(elevation), np.asarray(10.0 ** (RX_GAIN_MAX_DBI / 10.0)))
    return float(transmit_gain_linear(np.asarray(angle)) * path)


def live(geometry: Mapping[str, object]) -> bool:
    return bool(geometry.get("present_in_tape") is True and geometry["visible"]
                and geometry["d2_eligible"] and geometry["cell_reachable"])


def load_physics(path: Path, index: int, world: int, expected_rows: int):
    context = None
    rows: dict[str, dict[str, object]] = {}
    with path.open("r", encoding="ascii") as handle:
        header = json.loads(next(handle))
        if (header.get("schema") != PHYSICS_HEADER_SCHEMA or int(header["global_anchor_index"]) != index
                or int(header["world_index"]) != world):
            raise RuntimeError(f"physics header identity drifted at global-{index:03d}")
        for line in handle:
            payload = json.loads(line)
            schema = payload["schema"]
            if schema == "mcrl-v025-exact-source-anchor-context-v1":
                if context is not None:
                    raise RuntimeError("two anchor contexts")
                context = payload
            elif schema == "mcrl-v025-exact-source-row-physics-v1":
                key = str(payload["row_key"])
                if key in rows:
                    raise RuntimeError("duplicate physics row key")
                rows[key] = {
                    "user_id": int(payload["user_id"]),
                    "candidate": payload["candidate_geometry_offsets_0_1_2_3"][0],
                    "default": payload["default_geometry_offsets_0_1_2_3"][0],
                }
    if context is None or len(rows) != expected_rows:
        raise RuntimeError(f"physics inventory mismatch at global-{index:03d}")
    return header, context, rows


def main() -> int:
    started = time.perf_counter()
    sys.dont_write_bytecode = True
    enforce_runtime()
    for path in (*OUTPUTS.values(), RECEIPT, FAMILY, TABLE):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite existing output: {path}")
    for name, expected in PHYSICS_FILES.items():
        actual = file_sha256(SRC / "mcrl/physics_v025" / name)
        if actual != expected:
            raise RuntimeError(f"cited physics source drifted: {name} {actual}")

    q1v2 = load_module("authenticated_q1_schema_v2", Q1_V2_MODULE)
    q1v3 = load_module("authenticated_q1_schema_v3", Q1_V3_MODULE)
    v4.bind_authorities(q1v2, q1v3)

    # ---- physics constants, bound into every congestion schema ----------------
    noise_w = noise_power_w(BEAM_BANDWIDTH_HZ)
    gamma_table = {n: rate_target_sinr(RATE_TARGET_BPS, BEAM_BANDWIDTH_HZ, n) for n in range(1, 101)}
    physics_constants = {
        "RATE_TARGET_BPS": float.hex(RATE_TARGET_BPS),
        "BEAM_BANDWIDTH_HZ": float.hex(BEAM_BANDWIDTH_HZ),
        "NOISE_W": float.hex(noise_w),
        "BEAM_RF_CAP_W": float.hex(BEAM_RF_CAP_W),
        "CAP_HIT_TOLERANCE_W": float.hex(v4.CAP_HIT_TOLERANCE_W),
        "GAMMA_1_TO_13": json.dumps([None if gamma_table[n] is None else float.hex(gamma_table[n]) for n in range(1, 14)]),
    }
    if BEAM_RF_CAP_W != 1.65 or RATE_TARGET_BPS != 50_000_000.0:
        raise RuntimeError("a-r0 cap or rate target drifted")
    max_feasible = max(n for n, g in gamma_table.items() if g is not None)

    # ---- schema family: every subset, digest, fail-closed widths --------------
    family = []
    for added in v4.all_subsets():
        schema = v4.subset_schema(added, physics_constants)
        widths = v4.subset_widths(added)
        family.append({"added_fields": list(added), "q1_schema_sha256": canonical_sha256(schema), **widths,
                       "projection_indices_into_stored_vector": list(v4.projection_indices(added))})
    named = {}
    for name, added in v4.NAMED_SUBSETS.items():
        schema = v4.subset_schema(added, physics_constants)
        widths = v4.subset_widths(added)
        if widths != v4.EXPECTED_WIDTHS[name]:
            raise RuntimeError(f"fail-closed width derivation failed for {name}: {widths}")
        named[name] = {"added_fields": list(added), "schema": schema,
                       "q1_schema_sha256": canonical_sha256(schema), **widths,
                       "projection_indices_into_stored_vector": list(v4.projection_indices(added))}
    if named["none"]["q1_schema_sha256"] != v4.Q1_V2_SCHEMA_SHA256:
        raise RuntimeError("none subset is not Q1 v2")
    if named["gain_only"]["q1_schema_sha256"] != v4.Q1_V3_SCHEMA_SHA256:
        raise RuntimeError("gain_only subset is not Q1 v3")
    if len({row["q1_schema_sha256"] for row in family}) != len(family):
        raise RuntimeError("two subsets share a schema digest")
    log(f"schema family ready: {len(family)} subsets; both={named['both']['q1_schema_sha256']}")

    # ---- authenticate inputs --------------------------------------------------
    inventory93, digest93 = corpus_inventory(CORPUS93)
    if digest93 != CORPUS93_DIGEST or len(inventory93) != 2 * ANCHORS:
        raise RuntimeError(f"93-anchor corpus authority drifted: {digest93} files={len(inventory93)}")
    _v3inv, v3digest = corpus_inventory(V3_CORPUS)
    if v3digest != V3_CORPUS_DIGEST:
        raise RuntimeError("v3 cross-check corpus drifted")
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
    records = sorted(manifest["anchor_records"], key=lambda r: int(r["global_anchor_index"]))
    if [int(r["global_anchor_index"]) for r in records] != list(range(ANCHORS)):
        raise RuntimeError("manifest is not the contiguous 93-anchor prefix")
    log(f"inputs authenticated: corpus93={digest93} v3={v3digest}")

    # ---- per-anchor build -----------------------------------------------------
    samples = {"C1": [], "C2": [], "C3": []}
    argmax_groups = {"C1": 0, "C2": 0, "C1+C2": 0}
    argmax_diff = {"C1": 0, "C2": 0, "C1+C2": 0}
    c3_argmax = {"groups": 0, "different": 0, "exact_ties": 0}
    table_rows = []
    anchors_out = []
    stats = Counter()
    gain_db_range = [math.inf, -math.inf]
    gain_recompute_max = 0.0
    incumbent_recompute_max = 0.0
    v3_crosscheck_rows = 0
    split_world = Counter()
    congestion_hist = {name: Counter() for name in v4.CONGESTION_FIELDS}
    v2_power_values = Counter()
    v2_prevmax_values = Counter()
    output_digests = {name: [] for name in OUTPUTS}

    for position, rec in enumerate(records, 1):
        index = int(rec["global_anchor_index"])
        world = int(rec["world_index"])
        view_name = Path(rec["view_relative_path"]).name
        source_path = CORPUS93 / "views" / f"world-{world}" / view_name
        coalition_path = CORPUS93 / "views" / f"world-{world}" / f"COALITION_BUILD-c3-anchor-{index:03d}.jsonl"
        physics_path = DATEPOOL / "physics" / rec["physics_relative_path"]
        if verify_sidecar(source_path) != rec["view_sha256"]:
            raise RuntimeError("93-corpus source view is not the manifest's view")
        coalition_sha = verify_sidecar(coalition_path)
        physics_sha = verify_sidecar(physics_path)
        if physics_sha != rec["physics_sha256"]:
            raise RuntimeError("physics shard is not the manifest's physics")
        values = read_canonical_jsonl(source_path)
        header, rows = values[0], values[1:]
        if (header.get("schema") != SOURCE_SCHEMA or int(header["global_anchor_index"]) != index
                or int(header["world_index"]) != world or int(header["row_count"]) != len(rows)
                or int(header["q1_slots"]) != 16 or int(header["q2_slots"]) != 22):
            raise RuntimeError(f"source header drifted at global-{index:03d}")
        _pheader, context, physics = load_physics(physics_path, index, world, len(rows))
        if context["cell_rekeyed_users"]:
            raise RuntimeError(f"cell-rekeyed users present at global-{index:03d}; base mapping semantics unverified")
        base = {int(u): (None if i is None else (int(i[0]), int(i[1]))) for u, i in context["default_mapping"]}
        default_geo: dict[int, dict] = {}
        for prow in physics.values():
            user = prow["user_id"]
            geo = prow["default"]
            if user in default_geo and default_geo[user] != geo:
                raise RuntimeError("a user's default geometry differs between its rows")
            default_geo[user] = geo
        members: dict[tuple[int, int], list[int]] = defaultdict(list)
        for user, identity in base.items():
            if identity is None:
                continue
            geo = default_geo.get(user)
            if geo is None or geo.get("identity") != list(identity):
                raise RuntimeError("default geometry identity disagrees with default_mapping")
            if live(geo):
                members[identity].append(user)
            else:
                stats["base_mapped_user_not_live"] += 1
        incumbent_gain: dict[int, float] = {}
        for user, geo in default_geo.items():
            if geo.get("identity") is None:
                continue
            g = float.fromhex(geo["nominal_gain_hex"])
            recomputed = recompute_nominal_gain(geo)
            rel = abs(recomputed - g) / g
            incumbent_recompute_max = max(incumbent_recompute_max, rel)
            if not (g > 0.0 and math.isfinite(g)) or rel > 2e-14:
                raise RuntimeError("incumbent nominal gain fails formula recompute")
            incumbent_gain[user] = g

        subset_rows = {name: [] for name in OUTPUTS}
        lookup: dict[tuple, dict[str, object]] = {}
        user_groups: dict[int, list[tuple[int, float, float, float, float]]] = defaultdict(list)
        for row in rows:
            if (row.get("q1_schema_sha256") != EXPECTED_Q1_V1_DIGEST or row.get("q2_schema_sha256") != EXPECTED_Q2_DIGEST
                    or row.get("setting_id") != "a-r0" or row.get("split") != "TRAIN"):
                raise RuntimeError("source row schema/setting/split drifted")
            split_world[(row["split"], row["world_id"])] += 1
            c1_ok, c2_ok = label_identity(row)
            if not (c1_ok and c2_ok):
                raise RuntimeError("exact target identity failed")
            ext = row["exact_source_view"]
            row_key = str(ext["row_key"])
            prow = physics.get(row_key)
            if prow is None or prow["user_id"] != int(row["user_id"]):
                raise RuntimeError(f"authenticated physics row absent or misattributed: {row_key}")
            cand = prow["candidate"]
            user = int(row["user_id"])
            null_action = row["null_action"]
            if type(null_action) is not bool:
                raise RuntimeError("null_action is not boolean")
            if null_action:
                stats["null_rows"] += 1
                if cand != {"identity": None, "present_in_tape": False, "step_index": int(header["step_index"])}:
                    raise RuntimeError("null row geometry is not the absent-link record")
                angle = elevation = 0.0
                nominal_gain = None
                focal_live = False
                gains: list[float] = []
            else:
                stats["legal_rows"] += 1
                identity = (int(row["action"]["norad_id"]), int(row["action"]["beam_chain_id"]))
                if cand.get("present_in_tape") is not True or cand.get("identity") != list(identity):
                    raise RuntimeError("source action/physics identity disagreement")
                ai = int(row["action_index"])
                if row["action_mask"][ai] is not True:
                    raise RuntimeError("non-null row is not a legal option")
                angle = float.fromhex(cand["true_off_axis_angle_rad_hex"])
                elevation = float.fromhex(cand["elevation_deg_hex"])
                nominal_gain = float.fromhex(cand["nominal_gain_hex"])
                rel = abs(recompute_nominal_gain(cand) - nominal_gain) / nominal_gain
                gain_recompute_max = max(gain_recompute_max, rel)
                if rel > 2e-14:
                    raise RuntimeError("focal nominal gain fails formula recompute")
                db = 10.0 * math.log10(nominal_gain)
                gain_db_range = [min(gain_db_range[0], db), max(gain_db_range[1], db)]
                focal_live = live(cand)
                if not focal_live:
                    stats["legal_focal_not_live"] += 1
                incumbents = [v for v in members.get(identity, []) if v != user]
                gains = [incumbent_gain[v] for v in incumbents]
            old = tuple(float.fromhex(x) for x in row["q1_state"])
            v2_state = q1v3.q1_v2_state_from_v1(old, off_axis_angle_rad=angle, focal_elevation_deg=elevation,
                                                null_action=null_action)
            v2_auth = q1v2.upgrade_q1_state_v2(old, off_axis_angle_rad=angle, focal_elevation_deg=elevation,
                                              null_action=null_action)
            if v2_state != v2_auth:
                raise RuntimeError("v3-module v2 projection disagrees with the authoritative v2 module")
            if not null_action and abs(v2_state[3] * 10.0 - len(gains)) > 1e-12:
                raise RuntimeError("recomputed live incumbent count disagrees with v2 background occupancy")
            v3_state = q1v3.q1_v3_state_from_v1(old, off_axis_angle_rad=angle, focal_elevation_deg=elevation,
                                                nominal_gain=nominal_gain, null_action=null_action)
            if v3_state[:15] != v2_state:
                raise RuntimeError("v3 is not v2 plus gain on this row")
            raw_cong = v4.incumbent_congestion(null_action=null_action, focal_live=focal_live, incumbent_gains=gains,
                                               gamma=lambda n: gamma_table[n], noise_w=noise_w, cap_w=BEAM_RF_CAP_W)
            if not null_action and len(gains) + (1 if focal_live else 0) > max_feasible:
                stats["n_after_beyond_acm_table"] += 1
            cong = v4.normalized_congestion(raw_cong)
            for name, value in zip(v4.CONGESTION_FIELDS, raw_cong):
                congestion_hist[name][value if name.endswith("join") and "count" in name else round(value, 2)] += 1
            full = (*v3_state, *cong)
            full_hex = [float.hex(x) for x in full]
            v2_power_values[full_hex[1]] += 0 if null_action else 1
            v2_prevmax_values[full_hex[13]] += 0 if null_action else 1
            projections = {}
            for name, added in v4.NAMED_SUBSETS.items():
                projected = v4.project(full_hex, added)
                if len(projected) != named[name]["q1_width"]:
                    raise RuntimeError("projection width drifted")
                projections[name] = projected
            if projections["none"] != [float.hex(x) for x in v2_state]:
                raise RuntimeError("none projection is not the v2 vector")
            if projections["gain_only"] != [float.hex(x) for x in v3_state]:
                raise RuntimeError("gain_only projection is not the v3 vector")
            lineage = {
                "schema": "mcrl-v025-stagec-q1-v4-visible-primitives-lineage-v1",
                "parent_q1_v1_visible_primitives_sha256": row["visible_primitives_sha256"],
                "row_key": row_key, "boundary_offset": 0,
                "off_axis_angle_rad_hex": float.hex(angle), "focal_elevation_deg_hex": float.hex(elevation),
                "nominal_gain_hex": None if nominal_gain is None else float.hex(nominal_gain),
                "incumbent_nominal_gains_hex": [float.hex(g) for g in gains],
                "focal_live": focal_live,
                "physics_shard_sha256": physics_sha,
            }
            for name in OUTPUTS:
                child = dict(row)
                child["q1_state"] = projections[name]
                child["q1_schema_sha256"] = named[name]["q1_schema_sha256"]
                child["visible_primitives_sha256"] = canonical_sha256({**lineage, "subset": name,
                                                                        "added_fields": named[name]["added_fields"]})
                if set(child) != set(row) or any(child[k] != row[k] for k in set(row) - {"q1_state", "q1_schema_sha256", "visible_primitives_sha256"}):
                    raise RuntimeError("a source row field outside the Q1 view changed")
                subset_rows[name].append(child)
            key = action_key(user, row["action"])
            if key in lookup:
                raise RuntimeError("duplicate user/action source row")
            surrogate = ext["surrogate"]
            lookup[key] = {"parent_q1": list(row["q1_state"]), "proj": projections,
                           "exact_c1": float.fromhex(row["c1_label_normalized_hex"]),
                           "surrogate_c1": float.fromhex(surrogate["c1_normalized_total_hex"])}
            ai = int(row["action_index"])
            e1 = float.fromhex(row["c1_label_normalized_hex"]); s1 = float.fromhex(surrogate["c1_normalized_total_hex"])
            e2 = float.fromhex(row["c2_label_normalized_hex"]); s2 = float.fromhex(surrogate["c2_normalized_total_hex"])
            user_groups[user].append((ai, e1, s1, e2, s2))
            if not bool(row["reference_action"]):
                samples["C1"].append({"exact_hex": row["c1_label_normalized_hex"], "surrogate_hex": surrogate["c1_normalized_total_hex"],
                                      "lost": None})
                samples["C2"].append({"exact_hex": row["c2_label_normalized_hex"], "surrogate_hex": surrogate["c2_normalized_total_hex"],
                                      "lost": int(ext["c2_persistence_forecast"]["lost_offsets"])})
            table_rows.append((index, user, ai, len(row["action_mask"]), int(null_action), int(bool(row["reference_action"])),
                               *full))
        # argmax disagreement per (anchor,user), tie-break lowest action_index among equal maxima
        for user, items in user_groups.items():
            for route, ei, si in (("C1", 1, 2), ("C2", 3, 4)):
                def best(col):
                    top = max(item[col] for item in items)
                    return min(item[0] for item in items if item[col] == top)
                argmax_groups[route] += 1
                argmax_diff[route] += int(best(ei) != best(si))
            sums = [(it[0], it[1] + it[3], it[2] + it[4]) for it in items]
            te = max(s[1] for s in sums); ts = max(s[2] for s in sums)
            argmax_groups["C1+C2"] += 1
            argmax_diff["C1+C2"] += int(min(s[0] for s in sums if s[1] == te) != min(s[0] for s in sums if s[2] == ts))

        destinations = {}
        for name, root in OUTPUTS.items():
            out_header = dict(header)
            out_header["q1_slots"] = named[name]["q1_width"]
            destination = root / "views" / f"world-{world}" / view_name
            destinations[name] = write_jsonl(destination, [out_header, *subset_rows[name]])
        del subset_rows

        # ---- coalition shard ----------------------------------------------------
        cvalues = read_canonical_jsonl(coalition_path)
        cheader, crows = cvalues[0], cvalues[1:]
        if cheader.get("schema") != COALITION_SCHEMA or int(cheader["row_count"]) != len(crows) or cheader.get("split") != "TRAIN":
            raise RuntimeError(f"coalition header drifted at global-{index:03d}")
        out_crows = {name: [] for name in OUTPUTS}
        exact_psi = []
        surrogate_psi = []
        for crow in crows:
            objective = float.fromhex(crow["objective_delta_normalized_hex"])
            ec1 = float.fromhex(crow["c1_normalized_hex"])
            epsi = float.fromhex(crow["psi_normalized_hex"])
            if abs(ec1 + epsi - objective) > 1e-12:
                raise RuntimeError("exact C3 identity failed")
            children = {name: json.loads(json.dumps(crow)) for name in OUTPUTS}
            selected_keys = []
            for m_index, member in enumerate(crow["context"]["members"]):
                uid = int(member["user_id"])
                sel = lookup[action_key(uid, member["selected_action"])]
                ref = lookup[action_key(uid, member["reference_action"])]
                if member["selected_q1_row_hex"] != sel["parent_q1"] or member["incumbent_q1_row_hex"] != ref["parent_q1"]:
                    raise RuntimeError("coalition member Q1 row differs from exact-source parent")
                for name in OUTPUTS:
                    children[name]["context"]["members"][m_index]["selected_q1_row_hex"] = sel["proj"][name]
                    children[name]["context"]["members"][m_index]["incumbent_q1_row_hex"] = ref["proj"][name]
                selected_keys.append(action_key(uid, member["selected_action"]))
            exact_from_source = math.fsum(lookup[k]["exact_c1"] for k in selected_keys)
            if abs(ec1 - exact_from_source) > 1e-9:
                raise RuntimeError("exact C3 C1/source identity failed")
            s_c1 = math.fsum(lookup[k]["surrogate_c1"] for k in selected_keys)
            spsi = objective - s_c1
            samples["C3"].append({"exact_hex": crow["psi_normalized_hex"], "surrogate_hex": float.hex(spsi), "lost": None})
            exact_psi.append(epsi)
            surrogate_psi.append(spsi)
            blank = json.loads(json.dumps(crow))
            for member in blank["context"]["members"]:
                member["selected_q1_row_hex"] = member["incumbent_q1_row_hex"] = None
            for name in OUTPUTS:
                cmp_child = json.loads(json.dumps(children[name]))
                for member in cmp_child["context"]["members"]:
                    member["selected_q1_row_hex"] = member["incumbent_q1_row_hex"] = None
                if cmp_child != blank:
                    raise RuntimeError("a coalition field outside member Q1 vectors changed")
                out_crows[name].append(children[name])
        te = max(exact_psi); ts = max(surrogate_psi)
        ae = min(i for i, v in enumerate(exact_psi) if v == te)
        as_ = min(i for i, v in enumerate(surrogate_psi) if v == ts)
        c3_argmax["groups"] += 1
        c3_argmax["different"] += int(ae != as_)
        c3_argmax["exact_ties"] += int(sum(v == te for v in exact_psi) > 1)
        cdest = {}
        for name, root in OUTPUTS.items():
            material = out_crows[name]
            out_cheader = {**cheader, "context_payloads_sha256": canonical_sha256([r["context"] for r in material]),
                           "rows_sha256": canonical_sha256(material)}
            cdest[name] = write_jsonl(root / "views" / f"world-{world}" / coalition_path.name, [out_cheader, *material])
        del out_crows, crows, cvalues

        # ---- cross-check gain_only against the existing v3 corpus on its 22 anchors
        if world == 1 and index < 22:
            v3_rows = read_canonical_jsonl(V3_CORPUS / "views/world-1" / view_name)[1:]
            mine = read_canonical_jsonl(OUTPUTS["gain_only"] / "views/world-1" / view_name)[1:]
            if len(v3_rows) != len(mine):
                raise RuntimeError("v3 cross-check row count differs")
            for a, b in zip(v3_rows, mine, strict=True):
                if a["exact_source_view"]["row_key"] != b["exact_source_view"]["row_key"] or a["q1_state"] != b["q1_state"] \
                        or a["q1_schema_sha256"] != b["q1_schema_sha256"]:
                    raise RuntimeError("gain_only differs from the authenticated v3 corpus")
                v3_crosscheck_rows += 1
            if file_sha256(OUTPUTS["gain_only"] / "views/world-1" / coalition_path.name) != \
                    file_sha256(V3_CORPUS / "views/world-1" / coalition_path.name):
                stats["v3_coalition_bytes_differ"] += 1
            else:
                stats["v3_coalition_bytes_identical"] += 1
            del v3_rows, mine
        anchors_out.append({"global_anchor_index": index, "world_index": world, "world_id": header["world_id"],
                            "step_index": header["step_index"], "carrier": header["carrier"],
                            "source_rows": len(rows), "coalition_rows": int(cheader["row_count"]),
                            "source_parent_sha256": rec["view_sha256"], "coalition_parent_sha256": coalition_sha,
                            "physics_sha256": physics_sha, "outputs": {n: {"source": destinations[n], "coalition": cdest[n]} for n in OUTPUTS}})
        stats["source_rows"] += len(rows)
        stats["coalition_rows"] += int(cheader["row_count"])
        del values, rows, physics, lookup
        gc.collect()
        assert_resources()
        log(f"anchor {position}/{ANCHORS} global-{index:03d} world={world} rows={stats['source_rows']} "
            f"coalition={stats['coalition_rows']}")

    if stats["source_rows"] != EXPECTED_SOURCE_ROWS or stats["coalition_rows"] != EXPECTED_COALITION_ROWS:
        raise RuntimeError(f"row totals drifted: {stats}")

    # ---- output corpora digests (runner definition: sorted views inventory) ---
    corpus_digests = {}
    for name, root in OUTPUTS.items():
        inv, digest = corpus_inventory(root)
        if len(inv) != 2 * ANCHORS:
            raise RuntimeError("output inventory incomplete")
        corpus_digests[name] = digest

    # ---- provenance samples ---------------------------------------------------
    provenance = {}
    for route in ("C1", "C2", "C3"):
        frame = samples[route]
        rng_name = f"EXACTTRAIN/{SAMPLE_SEED}/{route}"
        picked = random.Random(rng_name).sample(frame, SAMPLE_SIZE)
        matches = [r for r in picked if r["exact_hex"] == r["surrogate_hex"]]
        full_matches = [r for r in frame if r["exact_hex"] == r["surrogate_hex"]]
        entry = {
            "sampling_frame_rows": len(frame), "sample_size": SAMPLE_SIZE, "rng_seed": rng_name,
            "surrogate_exact_matches": len(matches), "surrogate_match_fraction": len(matches) / SAMPLE_SIZE,
            "full_frame_matches": len(full_matches), "full_frame_match_fraction": len(full_matches) / len(frame),
            "matched_value_census_sample": {k: v for k, v in Counter(float.fromhex(r["exact_hex"]) for r in matches).most_common(8)},
            "matched_value_census_full": {k: v for k, v in Counter(float.fromhex(r["exact_hex"]) for r in full_matches).most_common(8)},
        }
        if route == "C2":
            entry["matched_lost_offsets_full"] = dict(Counter(r["lost"] for r in full_matches))
            entry["frame_lost_offsets"] = dict(Counter(r["lost"] for r in frame))
            unmatched_lost3 = sum(1 for r in frame if r["lost"] == 3 and r["exact_hex"] != r["surrogate_hex"])
            entry["frame_lost3_unmatched"] = unmatched_lost3
        provenance[route] = entry
    provenance["argmax_disagreement"] = {
        route: {"groups": argmax_groups[route], "different": argmax_diff[route],
                "fraction": argmax_diff[route] / argmax_groups[route],
                "tie_break": "lowest action_index among equal maxima"} for route in argmax_groups}
    provenance["argmax_disagreement"]["C3"] = {**c3_argmax, "fraction": c3_argmax["different"] / c3_argmax["groups"],
                                               "tie_break": "lowest coalition-row position among equal maxima",
                                               "surrogate_psi": "objective_delta - sum(surrogate C1 of selected members)"}
    log("provenance: " + json.dumps({r: provenance[r]["surrogate_exact_matches"] for r in ("C1", "C2", "C3")}))

    # ---- analysis table ------------------------------------------------------
    arr = np.asarray(table_rows, dtype=np.float64)
    np.savez_compressed(TABLE.with_suffix(""), table=arr,
                        columns=np.asarray(["anchor", "user", "action_index", "table_len", "null", "reference",
                                            *[f.name for f in v4.FULL_FEATURES]]))
    table_sha = file_sha256(TABLE)

    receipt = {
        "schema": "mcrl-v025-q1v4-build-verification-v1", "artifact_label": "BUILD_NOT_CLAIM",
        "no_ee_computed": True, "no_training": True,
        "anchor_set": {"count": ANCHORS, "corpus": str(CORPUS93), "corpus_digest": digest93,
                       "source_rows": stats["source_rows"], "coalition_rows": stats["coalition_rows"],
                       "split_world_rows": {f"{k[0]}|{k[1]}": v for k, v in split_world.items()},
                       "physics_manifest_sha256": file_sha256(MANIFEST)},
        "named_subsets": {n: {k: v for k, v in named[n].items() if k != "schema"} | {"corpus_digest": corpus_digests[n], "corpus_root": str(OUTPUTS[n])}
                          for n in named},
        "physics_constants": physics_constants, "max_acm_feasible_occupancy": max_feasible,
        "physics_sources_sha256": PHYSICS_FILES,
        "stats": dict(stats),
        "gain_db_range": gain_db_range,
        "focal_gain_formula_recompute_max_relative": gain_recompute_max,
        "incumbent_gain_formula_recompute_max_relative": incumbent_recompute_max,
        "v3_crosscheck_rows_bit_identical": v3_crosscheck_rows,
        "congestion_raw_value_census": {k: {str(kk): vv for kk, vv in sorted(v.items())[:40]} for k, v in congestion_hist.items()},
        "v2_nominal_required_power_over_cap_distinct_values_on_legal_rows": {k: v for k, v in v2_power_values.items() if v},
        "v2_previous_beam_max_rf_over_cap_distinct_values_on_legal_rows": {k: v for k, v in v2_prevmax_values.items() if v},
        "provenance": provenance,
        "anchors": anchors_out,
        "feature_table": {"path": str(TABLE), "sha256": table_sha},
        "resources": {"interpreter": str(Path(sys.executable).resolve()), "nice": os.getpriority(os.PRIO_PROCESS, 0),
                      "threads": {n: os.environ[n] for n in THREAD_VARS}, "peak_rss_bytes": peak_rss_bytes(),
                      "wall_s": time.perf_counter() - started, "mcrl_source": str(Path(mcrl.__file__).resolve())},
    }
    write_json(FAMILY, {"schema": "mcrl-v025-q1v4-schema-family-v1", "named": named, "all_subsets": family,
                        "physics_constants": physics_constants, "consumer_selection": (
                            "Point the unchanged production runner at artifacts/q1v4-<subset>-" + OUT_TAG +
                            " and register the digest-keyed adapter from q1v4_reader.py for that subset; any other "
                            "subset is project_subset_view.py over the 'both' view (column projection only)")})
    write_json(RECEIPT, receipt)
    log(f"BUILD COMPLETE corpus digests={json.dumps(corpus_digests)} wall={time.perf_counter()-started:.1f}s")
    print(f"PEAK_RSS_BYTES={peak_rss_bytes()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
