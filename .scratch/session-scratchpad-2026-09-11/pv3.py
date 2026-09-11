     1	#!/home/sat/mcrl-leo-handover/.venv/bin/python
     2	"""Build Q1-v3 scoring panels through the PANELFIX2/PANELZ adapter seam."""
     3	
     4	from __future__ import annotations
     5	
     6	import argparse
     7	import hashlib
     8	import importlib.util
     9	import json
    10	import math
    11	import os
    12	from pathlib import Path
    13	import resource
    14	import sys
    15	from typing import Mapping
    16	
    17	
    18	WORKSPACE = Path("/home/sat/mcrl-v025-panelv3-ws")
    19	PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
    20	PANELFIX = Path("/home/sat/mcrl-v025-panelfix-ws/scripts/build_stagec_scoring_panel.py")
    21	UPSTREAM = Path("/home/sat/mcrl-v025-witness-ws/scripts/build_stagec_scoring_panel.py")
    22	ORIGINAL_RECEIPT = Path(
    23	    "/home/sat/mcrl-v025-witness-ws/artifacts/"
    24	    "stagec-scoring-panel-first20-v1.receipt.json"
    25	)
    26	Q1V2_PATH = Path("/home/sat/mcrl-v025-design-ws/q1_schema_v2.py")
    27	Q1V3_PATH = Path("/home/sat/mcrl-v025-q1v3-ws/q1_schema_v3.py")
    28	Q1V3_BUILD_PATH = Path("/home/sat/mcrl-v025-q1v3-ws/build_q1_v3_corpora.py")
    29	V3_ROOT = Path(
    30	    "/home/sat/mcrl-v025-q1v3-ws/artifacts/"
    31	    "q1-v3-exact-label-corpus-20260910"
    32	)
    33	CONTROL_ROOT = Path(
    34	    "/home/sat/mcrl-v025-q1v3-ws/artifacts/"
    35	    "q1-v3-control-exact-label-corpus-20260910"
    36	)
    37	Q1_V3_SHA256 = "3850d23fa9cd5a5c2744e60c57e103766ecc73cf46cdf8755382e61e3aaafc01"
    38	Q1_V3_CONTROL_SHA256 = "ee6baea90d824d52bfa1e7c3a775fa191235e6f6db9d85c32674c608740cfc8f"
    39	Q2_V1_SHA256 = "a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c"
    40	EXPECTED_WIDTHS = {"C1": 16, "C2": 22, "C3": 240, "C3_MEMBER": 38}
    41	THREAD_VARS = (
    42	    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    43	    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    44	)
    45	FLAG_ASSERTION = (
    46	    "synthetic_smoke_not_evidence=false asserts that every panel-carried "
    47	    "physical field comes from exact physics on real development anchors; it "
    48	    "does not validate the contaminated reference-object selection path, "
    49	    "determine global evaluator-path authority, or make this development panel claim-grade"
    50	)
    51	
    52	
    53	def load_module(name: str, path: Path):
    54	    spec = importlib.util.spec_from_file_location(name, path)
    55	    if spec is None or spec.loader is None:
    56	        raise RuntimeError(f"cannot import {path}")
    57	    module = importlib.util.module_from_spec(spec)
    58	    sys.modules[name] = module
    59	    spec.loader.exec_module(module)
    60	    return module
    61	
    62	
    63	def sha256(path: Path) -> str:
    64	    digest = hashlib.sha256()
    65	    with path.open("rb") as handle:
    66	        for block in iter(lambda: handle.read(1 << 20), b""):
    67	            digest.update(block)
    68	    return digest.hexdigest()
    69	
    70	
    71	def verify_sidecar(path: Path) -> str:
    72	    actual = sha256(path)
    73	    sidecar = path.with_name(path.name + ".sha256")
    74	    if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != actual:
    75	        raise RuntimeError(f"sidecar mismatch: {path}")
    76	    return actual
    77	
    78	
    79	def beneath_workspace(path: Path) -> bool:
    80	    try:
    81	        path.resolve().relative_to(WORKSPACE.resolve())
    82	    except ValueError:
    83	        return False
    84	    return True
    85	
    86	
    87	def enforce_runtime() -> None:
    88	    if Path(sys.executable).resolve() != PYTHON.resolve():
    89	        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    90	    if any(os.environ.get(name) != "1" for name in THREAD_VARS):
    91	        raise RuntimeError("all BLAS thread variables must equal 1")
    92	    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
    93	        os.nice(16 - os.getpriority(os.PRIO_PROCESS, 0))
    94	    if os.getpriority(os.PRIO_PROCESS, 0) != 16:
    95	        raise RuntimeError("could not enforce nice -n 16")
    96	    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    97	    cap = 4_900_000_000 if hard == resource.RLIM_INFINITY else min(hard, 4_900_000_000)
    98	    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    99	
   100	
   101	def main() -> int:
   102	    parser = argparse.ArgumentParser()
   103	    parser.add_argument("--view", choices=("v3", "v3_control"), required=True)
   104	    parser.add_argument("--checkpoint", type=Path, required=True)
   105	    parser.add_argument("--output", type=Path, required=True)
   106	    parser.add_argument("--resume-dir", type=Path, required=True)
   107	    parser.add_argument("--outcome-cache-dir", type=Path, required=True)
   108	    args = parser.parse_args()
   109	    enforce_runtime()
   110	    if not beneath_workspace(args.output) or not beneath_workspace(args.resume_dir):
   111	        raise RuntimeError("writes must remain below PANELV3 workspace")
   112	    if args.output.exists():
   113	        raise RuntimeError(f"refusing to overwrite {args.output}")
   114	
   115	    panelfix = load_module("panelv3_panelfix", PANELFIX)
   116	    provenance = panelfix.audit_physical_provenance()
   117	    if provenance.get("fixture_physical_values_surviving") != 0:
   118	        raise RuntimeError("fixture physical value survived PANELFIX2 audit")
   119	    provenance = dict(provenance)
   120	    provenance.update({
   121	        "q1_v3_gain_field": (
   122	            "authenticated boundary-0 nominal_gain, independently formula-checked by "
   123	            "Q1-v3 corpus builder and rechecked here row by row"
   124	        ),
   125	        "fixture_physical_values_surviving": 0,
   126	    })
   127	    print("physical provenance PASS: no fixture value survives", flush=True)
   128	
   129	    builder = load_module("panelv3_upstream", UPSTREAM)
   130	    q1v2 = load_module("panelv3_q1v2", Q1V2_PATH)
   131	    q1v3 = load_module("panelv3_q1v3", Q1V3_PATH)
   132	    q1build = load_module("panelv3_q1build", Q1V3_BUILD_PATH)
   133	    original_load_module = builder.load_module
   134	    root = V3_ROOT if args.view == "v3" else CONTROL_ROOT
   135	    q1_digest = Q1_V3_SHA256 if args.view == "v3" else Q1_V3_CONTROL_SHA256
   136	    control = args.view == "v3_control"
   137	    upstream_receipt = json.loads(ORIGINAL_RECEIPT.read_text(encoding="ascii"))
   138	
   139	    def streaming_atomic_json(path: Path, value: object) -> None:
   140	        path.parent.mkdir(parents=True, exist_ok=True)
   141	        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
   142	        encoder = json.JSONEncoder(
   143	            indent=2, sort_keys=True, allow_nan=False, ensure_ascii=True,
   144	        )
   145	        with temporary.open("w", encoding="ascii") as handle:
   146	            for chunk in encoder.iterencode(value):
   147	                handle.write(chunk)
   148	            handle.write("\n")
   149	            handle.flush()
   150	            os.fsync(handle.fileno())
   151	        temporary.replace(path)
   152	
   153	    def discover_panel(limit: int):
   154	        if limit != 20:
   155	            raise RuntimeError("PANELV3 requires exactly global anchors 000--019")
   156	        parents = upstream_receipt["run_identity"]["sources"]
   157	        if [int(row["index"]) for row in parents] != list(range(20)):
   158	            raise RuntimeError("PANELBUILD source prefix drifted")
   159	        sources = []
   160	        for index, parent in enumerate(parents):
   161	            view = (
   162	                root / "views/world-1"
   163	                / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   164	            )
   165	            digest = verify_sidecar(view)
   166	            header = json.loads(view.read_bytes().splitlines()[0])
   167	            actual = (
   168	                int(header["global_anchor_index"]), int(header["step_index"]),
   169	                int(header["carrier_index"]), int(header["q1_slots"]),
   170	                int(header["q2_slots"]),
   171	            )
   172	            expected = (index, index // 3, index % 3, 16, 22)
   173	            if actual != expected:
   174	                raise RuntimeError(f"Q1-v3 anchor generation order/width drifted at {index}")
   175	            sources.append({
   176	                **parent,
   177	                "view_path": str(view),
   178	                "view_sha256": digest,
   179	                "state_view_schema": args.view,
   180	                "q1_schema_sha256": q1_digest,
   181	            })
   182	        return sources
   183	
   184	    def strict_c3(pilot, tape, step_index, base, config, rows_by_action,
   185	                  width: int, member_width: int):
   186	        changed = tuple(
   187	            user for user in sorted(base.mapping)
   188	            if base.mapping[user] != config.mapping[user]
   189	        )
   190	        if len(changed) <= 1:
   191	            return len(changed), [0.0] * width
   192	        context = pilot._coalition_context(
   193	            tape=tape, step_index=step_index, anchor=base, selected=config,
   194	            rows_by_user_action=rows_by_action,
   195	        )
   196	        full = context.invariant_vector(member_width=member_width).tolist()
   197	        if len(full) != width:
   198	            raise RuntimeError(
   199	                f"checkpoint C3 width {width} differs from complete bound encoder "
   200	                f"width {len(full)}; truncation is forbidden"
   201	            )
   202	        return len(changed), full
   203	
   204	    def feature_loader(source: Mapping[str, object], widths: Mapping[str, int]):
   205	        if dict(widths) != EXPECTED_WIDTHS:
   206	            raise RuntimeError(f"Q1-v3 checkpoint shape drifted: {dict(widths)!r}")
   207	        index = int(source["index"])
   208	        path = (
   209	            root / "views/world-1"
   210	            / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   211	        )
   212	        verify_sidecar(path)
   213	        raw_lines = path.read_bytes().splitlines()
   214	        values = [json.loads(line.decode("ascii")) for line in raw_lines]
   215	        header = values[0]
   216	        if (
   217	            header.get("schema") != "mcrl-v025-exact-source-view-shard-v1"
   218	            or header.get("global_anchor_index") != index
   219	            or header.get("q1_slots") != 16
   220	            or header.get("q2_slots") != 22
   221	        ):
   222	            raise RuntimeError(f"Q1-v3 exact-view header drifted: {path}")
   223	        geometry, _physics_digest = q1build.load_physics_geometry(index, len(values) - 1)
   224	        result = {}
   225	        for raw, payload in zip(raw_lines[1:], values[1:], strict=True):
   226	            canonical = json.dumps(
   227	                payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
   228	            ).encode("ascii")
   229	            if raw != canonical or "exact_source_view" not in payload:
   230	                raise RuntimeError("Q1-v3 exact-source row is unauthenticated")
   231	            if (
   232	                payload.get("q1_schema_sha256") != q1_digest
   233	                or payload.get("q2_schema_sha256") != Q2_V1_SHA256
   234	            ):
   235	                raise RuntimeError("Q1-v3 row schema digest drifted")
   236	            action = payload["action"]
   237	            identity = None if action["norad_id"] is None else (
   238	                int(action["norad_id"]), int(action["beam_chain_id"])
   239	            )
   240	            key = (int(payload["user_id"]), identity)
   241	            q1 = tuple(float.fromhex(value) for value in payload["q1_state"])
   242	            q2 = tuple(float.fromhex(value) for value in payload["q2_state"])
   243	            if len(q1) != 16 or len(q2) != 22 or key in result:
   244	                raise RuntimeError("Q1-v3 source row width or identity drifted")
   245	            candidate = geometry[str(payload["exact_source_view"]["row_key"])]
   246	            if bool(payload["null_action"]):
   247	                expected_gain_coordinate = 0.0
   248	                if candidate.get("identity") is not None:
   249	                    raise RuntimeError("null row retained physical focal-link geometry")
   250	            else:
   251	                nominal_gain = float.fromhex(str(candidate["nominal_gain_hex"]))
   252	                recomputed = q1build.independently_recompute_nominal_gain(candidate)
   253	                if abs(recomputed - nominal_gain) / nominal_gain > 2e-14:
   254	                    raise RuntimeError("nominal-gain physical formula audit failed")
   255	                expected_gain_coordinate = (
   256	                    q1v3.decision_boundary_log_nominal_gain_db(nominal_gain)
   257	                    / q1v3.NOMINAL_GAIN_DB_SCALE
   258	                )
   259	            if q1[-1] != (0.0 if control else expected_gain_coordinate):
   260	                raise RuntimeError("Q1-v3 gain coordinate provenance failed")
   261	            result[key] = builder.FeatureRow(q1, q2, bool(payload["outage"]))
   262	        if len(result) != int(header["row_count"]):
   263	            raise RuntimeError("Q1-v3 source row count drifted")
   264	        return result
   265	
   266	    def adapted_module_loader(name: str, path: Path):
   267	        module = original_load_module(name, path)
   268	        if path != builder.PANELCEIL_PATH:
   269	            return module
   270	        original_pilot_loader = module.load_pilot
   271	
   272	        def adapted_pilot_loader():
   273	            pilot = original_pilot_loader()
   274	            original_build_rows = pilot._build_anchor_rows
   275	            resolver_cache = {}
   276	            from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
   277	            geometry_provider = LegacyWorldProvider(role="pilot-source")
   278	
   279	            def build_rows_v3(**kwargs):
   280	                tape = kwargs["tape"]
   281	                step_index = int(kwargs["step_index"])
   282	                cache_key = (int(tape.seed), step_index)
   283	                if cache_key not in resolver_cache:
   284	                    resolver_cache[cache_key] = q1v2.DecisionGeometryResolverV2(
   285	                        tape, geometry_provider, step_index,
   286	                    )
   287	                resolver = resolver_cache[cache_key]
   288	                # Resolve the provider world before the memory-heavy exact full-action
   289	                # pass.  The pass retains allocator arenas, so doing this afterwards can
   290	                # fail the 4.9 GB address-space gate despite a sub-2.1 GB resident peak.
   291	                built = original_build_rows(**kwargs)
   292	                arrays = tape.steps[step_index].arrays
   293	                if arrays is None:
   294	                    raise RuntimeError("Q1-v3 exact regeneration requires provider arrays")
   295	                row_index = arrays._row_index()
   296	                converted = {}
   297	                for key, row in built["rows_by_user_action"].items():
   298	                    angle, elevation = resolver(row)
   299	                    if bool(row.null_action):
   300	                        nominal_gain = None
   301	                    else:
   302	                        user, identity = key
   303	                        array_row = row_index[(user, identity)]
   304	                        nominal_gain = float(arrays.nominal_gain[0, array_row])
   305	                        slant = float(arrays.slants_km[0, array_row])
   306	                        peak_receive = 10.0 ** (q1build.RX_GAIN_MAX_DBI / 10.0)
   307	                        path_factor = q1build.LegacyWorldProvider._nominal_path_without_scintillation(
   308	                            q1build.np.asarray(slant), q1build.np.asarray(elevation),
   309	                            q1build.np.asarray(peak_receive),
   310	                        )
   311	                        recomputed = float(
   312	                            q1build.transmit_gain_linear(q1build.np.asarray(math.degrees(angle)))
   313	                            * path_factor
   314	                        )
   315	                        relative = abs(recomputed - nominal_gain) / nominal_gain
   316	                        # The authenticated shard check above can compare the provider's
   317	                        # serialized angle bit-for-bit.  Regenerated rows instead obtain
   318	                        # the same angle through the public ECEF resolver, whose accepted
   319	                        # geometry seam is 1e-9 degrees.  Keep this redundant formula
   320	                        # check commensurate with that seam; the carried gain itself is
   321	                        # the provider array value, not the recomputation.
   322	                        if relative > 1e-8:
   323	                            raise RuntimeError(
   324	                                f"regenerated nominal-gain formula audit failed: {relative}"
   325	                            )
   326	                    q1 = q1v3.q1_v3_state_from_v1(
   327	                        row.q1_state,
   328	                        off_axis_angle_rad=angle,
   329	                        focal_elevation_deg=elevation,
   330	                        nominal_gain=nominal_gain,
   331	                        null_action=bool(row.null_action),
   332	                        control=control,
   333	                    )
   334	                    converted[key] = builder.FeatureRow(
   335	                        q1, tuple(row.q2_state), bool(row.outage),
   336	                    )
   337	                result = dict(built)
   338	                result["rows_by_user_action"] = converted
   339	                return result
   340	
   341	            pilot._build_anchor_rows = build_rows_v3
   342	            return pilot
   343	
   344	        module.load_pilot = adapted_pilot_loader
   345	        return module
   346	
   347	    def annotated_atomic_json(path: Path, value: object) -> None:
   348	        if isinstance(value, dict) and value.get("schema") == builder.PANEL_SCHEMA:
   349	            c1_widths, c2_widths, c3_widths = set(), set(), set()
   350	            for anchor in value["anchors"]:
   351	                for profile in anchor["profiles"]:
   352	                    c3_widths.add(len(profile["C3"]["invariant_state"]))
   353	                    for route, widths in (("C1", c1_widths), ("C2", c2_widths)):
   354	                        for pair in profile[route]:
   355	                            widths.update((len(pair["reference"]), len(pair["selected"])))
   356	            if (c1_widths, c2_widths, c3_widths) != ({16}, {22}, {240}):
   357	                raise RuntimeError(
   358	                    f"final panel state widths drifted: {c1_widths}/{c2_widths}/{c3_widths}"
   359	                )
   360	            value["synthetic_smoke_not_evidence"] = False
   361	            value["panel_identity"]["name"] = (
   362	                f"panel-q1{args.view} development first-20 Stage-C scoring panel"
   363	            )
   364	            value["panel_identity"]["information_class"] += "; " + FLAG_ASSERTION
   365	        elif isinstance(value, dict) and value.get("schema") == "mcrl-v025-panelbuild-receipt-v1":
   366	            value["synthetic_smoke_not_evidence"] = False
   367	            value["c3_encoding"].update({
   368	                "checkpoint_input_width": 240,
   369	                "production_full_width": 240,
   370	                "global_resource_feature_prefix_count": 6,
   371	                "fixture_limitation": None,
   372	                "width_policy": "exact equality; suffix truncation forbidden",
   373	            })
   374	            value["encoder_binding"] = {
   375	                "view": args.view,
   376	                "q1_schema_sha256": q1_digest,
   377	                "q1_width": 16,
   378	                "q2_schema_sha256": Q2_V1_SHA256,
   379	                "q2_width": 22,
   380	                "c3_member_width": 38,
   381	                "c3_full_width": 240,
   382	            }
   383	            value["physical_provenance_audit"] = provenance
   384	            value["state_provenance"] = {
   385	                "authenticated_rows": (
   386	                    "Q1-v3 corpus rows; gain coordinate rechecked against authenticated "
   387	                    "nominal_gain and provider formula"
   388	                ),
   389	                "missing_reference_actions": (
   390	                    "exact non-primitive evaluator regeneration; Q1-v2 decision geometry; "
   391	                    "provider-array nominal gain; identical Q1-v3 projection"
   392	                ),
   393	                "fixture_state_values_surviving": 0,
   394	            }
   395	            value["reference_object_provenance"] = {
   396	                "total_objects": 40,
   397	                "panelceil_reused": 24,
   398	                "panelceil_anchor_indices": list(range(12)),
   399	                "producer_computed": 16,
   400	                "producer_anchor_indices": list(range(12, 20)),
   401	                "objects_per_anchor": ["certified_fixed_point", "anytime_incumbent_10s"],
   402	                "selection_evaluator_path": (
   403	                    "PANELCEIL first_improvement: fresh realised boundary_indices=(0,) "
   404	                    "StepEvaluator; scalar evaluate(BASE) cache fill, then dense evaluate_many "
   405	                    "candidate microbatches; contaminated mixed path"
   406	                ),
   407	            }
   408	            value["synthetic_flag_semantics"] = FLAG_ASSERTION
   409	            value["material_class"] = "development; not claim-grade"
   410	            value["global_evaluator_path_authority"] = "UNDETERMINED by EVALPATH-2026-09-10"
   411	            value["adapter_chain"] = {
   412	                "panelv3": str(Path(__file__).resolve()),
   413	                "panelfix2": str(PANELFIX),
   414	                "panelz_exact_equality_pattern": (
   415	                    "/home/sat/mcrl-v025-panelz-ws/scripts/build_panel_q1v2z.py"
   416	                ),
   417	                "upstream_panelbuild": str(UPSTREAM),
   418	            }
   419	        streaming_atomic_json(path, value)
   420	
   421	    builder.c3_state = strict_c3
   422	    builder.discover_panel = discover_panel
   423	    builder.load_exact_feature_rows = feature_loader
   424	    builder.load_module = adapted_module_loader
   425	    builder.atomic_json = annotated_atomic_json
   426	    sys.argv = [
   427	        str(Path(__file__).resolve()),
   428	        "--checkpoint", str(args.checkpoint),
   429	        "--output", str(args.output),
   430	        "--resume-dir", str(args.resume_dir),
   431	        "--outcome-cache-dir", str(args.outcome_cache_dir),
   432	        "--limit", "20",
   433	    ]
   434	    result = int(builder.main())
   435	    print(
   436	        f"PEAK_RSS_BYTES={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}",
   437	        flush=True,
   438	    )
   439	    return result
   440	
   441	
   442	if __name__ == "__main__":
   443	    raise SystemExit(main())
