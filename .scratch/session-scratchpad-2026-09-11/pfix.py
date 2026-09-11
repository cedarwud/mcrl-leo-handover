     1	#!/home/sat/mcrl-leo-handover/.venv/bin/python
     2	"""Schema-bound, fail-closed adapter for PANELBUILD's scoring-panel producer.
     3	
     4	The scientific construction remains owned by the original PANELBUILD module.
     5	This adapter binds its feature reader to Q1 v1 or Q1 v2, rejects any C3 width
     6	other than the complete encoder vector, and gates the panel's synthetic flag on
     7	an independent audit of the cached physical content.
     8	"""
     9	
    10	from __future__ import annotations
    11	
    12	import argparse
    13	import gc
    14	import hashlib
    15	import importlib.util
    16	import json
    17	import os
    18	from pathlib import Path
    19	import resource
    20	import sys
    21	from typing import Mapping
    22	
    23	
    24	WORKSPACE = Path("/home/sat/mcrl-v025-panelfix-ws")
    25	PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
    26	UPSTREAM_BUILDER = Path(
    27	    "/home/sat/mcrl-v025-witness-ws/scripts/build_stagec_scoring_panel.py"
    28	)
    29	ORIGINAL_PANEL = Path(
    30	    "/home/sat/mcrl-v025-witness-ws/artifacts/stagec-scoring-panel-first20-v1.json"
    31	)
    32	ORIGINAL_RECEIPT = ORIGINAL_PANEL.with_name(
    33	    "stagec-scoring-panel-first20-v1.receipt.json"
    34	)
    35	PANELCEIL_RECEIPT = Path(
    36	    "/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/panelceil-receipt.json"
    37	)
    38	Q1_V2_MODULE = Path("/home/sat/mcrl-v025-design-ws/q1_schema_v2.py")
    39	Q1_V2_STAGING = Path(
    40	    "/home/sat/mcrl-v025-design-ws/artifacts/"
    41	    "v025-stagec-c3-coalition-q1v2-20260910-BUILD_NOT_CLAIM/"
    42	    "corpus/.staging-separated-v1"
    43	)
    44	Q1_V1_STAGING = Path(
    45	    "/home/sat/mcrl-v025-coalgen-ws/artifacts/"
    46	    "v025-stagec-c3-coalition-20260910-BUILD_NOT_CLAIM/"
    47	    "corpus/.staging-separated-v1"
    48	)
    49	EXACT_FINAL_ROOT = Path(
    50	    "/home/sat/mcrl-v025-datepool-ws/artifacts/"
    51	    "v025-exact-source-20260910-BUILD_NOT_CLAIM"
    52	)
    53	EXACT_FINAL_MANIFEST = EXACT_FINAL_ROOT / "BUILD_NOT_CLAIM-manifest.json"
    54	EXPECTED_PANEL_SHA256 = (
    55	    "92d5a80ff018c066ec95507da0f63bf4be5fa6802b3d15fafb8247b069dd53fb"
    56	)
    57	EXPECTED_PANELCEIL_SHA256 = (
    58	    "52400cf180cd55f4b004be785ba4ff8021e09e38eba20cec7321fbad9999cf7d"
    59	)
    60	Q1_V1_SHA256 = "c002ea883a4ab727f9e00cc15866f5b9d37abca645963fd3db2f2db7c6cc887a"
    61	Q1_V2_SHA256 = "66ed4a3f9222ac7f20f4334ffab92f6164d2dad203cbac7f7d4e1728ae4ad654"
    62	Q2_V1_SHA256 = "a891dd9831d76bccd981cef054ff204fa1d49c3cf6e5f3265015f16f1057019c"
    63	THREAD_VARIABLES = (
    64	    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    65	    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    66	)
    67	FLAG_ASSERTION = (
    68	    "synthetic_smoke_not_evidence=false asserts that every panel-carried "
    69	    "physical field comes from exact physics on real development anchors; it "
    70	    "does not assert that a checkpoint used during construction is evidence, "
    71	    "does not determine global evaluator-path authority, and does not make "
    72	    "this development panel claim-grade"
    73	)
    74	
    75	
    76	def sha256(path: Path) -> str:
    77	    digest = hashlib.sha256()
    78	    with path.open("rb") as handle:
    79	        for block in iter(lambda: handle.read(1024 * 1024), b""):
    80	            digest.update(block)
    81	    return digest.hexdigest()
    82	
    83	
    84	def canonical_sha256(value: object) -> str:
    85	    return hashlib.sha256(json.dumps(
    86	        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    87	    ).encode("ascii")).hexdigest()
    88	
    89	
    90	def load_module(name: str, path: Path):
    91	    spec = importlib.util.spec_from_file_location(name, path)
    92	    if spec is None or spec.loader is None:
    93	        raise RuntimeError(f"cannot import {path}")
    94	    module = importlib.util.module_from_spec(spec)
    95	    sys.modules[name] = module
    96	    spec.loader.exec_module(module)
    97	    return module
    98	
    99	
   100	def below_workspace(path: Path) -> bool:
   101	    try:
   102	        path.resolve().relative_to(WORKSPACE.resolve())
   103	    except ValueError:
   104	        return False
   105	    return True
   106	
   107	
   108	def verify_sidecar(path: Path, expected: str | None = None) -> str:
   109	    actual = sha256(path)
   110	    if expected is not None and actual != expected:
   111	        raise RuntimeError(f"authenticated file changed: {path}")
   112	    sidecar = path.with_name(path.name + ".sha256")
   113	    if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != actual:
   114	        raise RuntimeError(f"sidecar mismatch: {path}")
   115	    return actual
   116	
   117	
   118	def resolved_sources(receipt: Mapping[str, object]) -> list[dict[str, object]]:
   119	    """Resolve deleted staging paths to receipt-identical retained files."""
   120	
   121	    resolved = []
   122	    for source in receipt["run_identity"]["sources"]:
   123	        index = int(source["index"])
   124	        original_physics = str(source["physics_path"])
   125	        marker = "/physics/"
   126	        if marker not in original_physics:
   127	            raise RuntimeError(f"source physics path has no retained-relative seam at {index}")
   128	        physics_relative = original_physics.split(marker, 1)[1]
   129	        row = dict(source)
   130	        row["physics_path"] = str(EXACT_FINAL_ROOT / "physics" / physics_relative)
   131	        row["view_path"] = str(
   132	            Q1_V1_STAGING / f"global-{index:03d}" / "views" / "world-1"
   133	            / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   134	        )
   135	        row["retained_copy_binding"] = "original receipt SHA-256, not mutable datepool manifest"
   136	        resolved.append(row)
   137	    if [row["index"] for row in resolved] != list(range(20)):
   138	        raise RuntimeError("resolved exact-source prefix is not global 000--019")
   139	    return resolved
   140	
   141	
   142	def audit_physical_provenance() -> dict[str, object]:
   143	    """Authenticate every provenance link used by the outcome-cache rebuild."""
   144	
   145	    if sha256(ORIGINAL_PANEL) != EXPECTED_PANEL_SHA256:
   146	        raise RuntimeError("sealed-input panel bytes drifted")
   147	    receipt = json.loads(ORIGINAL_RECEIPT.read_text(encoding="ascii"))
   148	    if receipt.get("panel_sha256") != EXPECTED_PANEL_SHA256:
   149	        raise RuntimeError("PANELBUILD receipt does not bind the nominated panel")
   150	    if receipt.get("anchor_count") != 20:
   151	        raise RuntimeError("PANELBUILD receipt is not the declared first-20 panel")
   152	
   153	    panel = json.loads(ORIGINAL_PANEL.read_text(encoding="ascii"))
   154	    anchors = panel.get("anchors")
   155	    if not isinstance(anchors, list) or len(anchors) != 20:
   156	        raise RuntimeError("panel anchor inventory drifted")
   157	    if panel.get("synthetic_smoke_not_evidence") is not True:
   158	        raise RuntimeError("historical marker unexpectedly changed")
   159	    if {str(row.get("date"))[:10] for row in anchors} != {"2026-01-07"}:
   160	        raise RuntimeError("panel is not confined to the declared development date")
   161	
   162	    sources = resolved_sources(receipt)
   163	    if [row["index"] for row in sources] != list(range(20)):
   164	        raise RuntimeError("exact-source prefix is not global 000--019")
   165	    for source in sources:
   166	        for name in ("physics", "view"):
   167	            path = Path(source[f"{name}_path"])
   168	            expected = str(source[f"{name}_sha256"])
   169	            if sha256(path) != expected:
   170	                raise RuntimeError(f"{name} authentication failed at anchor {source['index']}")
   171	            verify_sidecar(path, expected)
   172	        result_path = Path(source["result_path"])
   173	        if result_path.is_file() and sha256(result_path) != source["result_sha256"]:
   174	            raise RuntimeError(f"staging result authentication failed at anchor {source['index']}")
   175	
   176	    cache = receipt["run_identity"]["outcome_cache"]
   177	    files = cache["files"]
   178	    if [row["name"] for row in files] != [f"anchor-{i:03d}.json" for i in range(20)]:
   179	        raise RuntimeError("outcome-cache file inventory drifted")
   180	    exact_outcome_boundary_evaluations = 0
   181	    producer_reference_anchors = 0
   182	    for index, row in enumerate(files):
   183	        path = Path(cache["path"]) / row["name"]
   184	        if sha256(path) != row["sha256"]:
   185	            raise RuntimeError(f"outcome cache authentication failed at anchor {index}")
   186	        cached = json.loads(path.read_text(encoding="ascii"))
   187	        cached_anchor = cached["anchor"]
   188	        audit = cached["audit"]
   189	        current = anchors[index]
   190	        if cached_anchor["anchor_id"] != current["anchor_id"]:
   191	            raise RuntimeError(f"outcome cache anchor identity drifted at {index}")
   192	        cached_profiles = cached_anchor["profiles"]
   193	        current_profiles = current["profiles"]
   194	        if [item["profile_id"] for item in cached_profiles] != [
   195	            item["profile_id"] for item in current_profiles
   196	        ]:
   197	            raise RuntimeError(f"cached catalogue drifted at anchor {index}")
   198	        if [item["outcome"] for item in cached_profiles] != [
   199	            item["outcome"] for item in current_profiles
   200	        ]:
   201	            raise RuntimeError(f"cached exact outcomes drifted at anchor {index}")
   202	        if audit.get("invalid_profiles") != 0:
   203	            raise RuntimeError(f"cached physical profiles were rejected at anchor {index}")
   204	        all_local_evaluations = 48 * len(cached_profiles)
   205	        distinct_reference_ids = {
   206	            cached_anchor["certified_fixed_point_profile_id"],
   207	            cached_anchor["anytime_incumbent_profile_id"],
   208	        }
   209	        panelceil_reuse_evaluations = 48 * (
   210	            len(cached_profiles) - len(distinct_reference_ids)
   211	        )
   212	        allowed_evaluations = (
   213	            {all_local_evaluations, panelceil_reuse_evaluations}
   214	            if index < 12 else {all_local_evaluations}
   215	        )
   216	        observed_evaluations = audit.get("outcome_physics_boundary_evaluations")
   217	        if observed_evaluations not in allowed_evaluations:
   218	            raise RuntimeError(f"outcomes lack full 48-boundary evaluation at anchor {index}")
   219	        exact_outcome_boundary_evaluations += int(observed_evaluations)
   220	        if index >= 12:
   221	            if (
   222	                audit.get("fixed_point_source") != "producer computation"
   223	                or audit.get("fixed_point_certificate_complete") is not True
   224	            ):
   225	                raise RuntimeError(f"producer reference provenance failed at anchor {index}")
   226	            producer_reference_anchors += 1
   227	        del cached
   228	
   229	    if sha256(PANELCEIL_RECEIPT) != EXPECTED_PANELCEIL_SHA256:
   230	        raise RuntimeError("PANELCEIL receipt bytes drifted")
   231	    panelceil = json.loads(PANELCEIL_RECEIPT.read_text(encoding="ascii"))
   232	    claimed = panelceil.get("receipt_sha256")
   233	    unsigned = dict(panelceil)
   234	    unsigned.pop("receipt_sha256", None)
   235	    if claimed != canonical_sha256(unsigned) or panelceil.get("status") != "COMPLETE":
   236	        raise RuntimeError("PANELCEIL receipt is unauthenticated or incomplete")
   237	    ceiling_rows = panelceil.get("anchors")
   238	    if not isinstance(ceiling_rows, list) or [row["global_anchor_index"] for row in ceiling_rows] != list(range(12)):
   239	        raise RuntimeError("PANELCEIL reuse is not exactly anchors 000--011")
   240	    for index, ceiling in enumerate(ceiling_rows):
   241	        if (
   242	            ceiling.get("source_base_configuration_and_incumbent_mappings_verified") is not True
   243	            or ceiling["first_improvement"]["termination_certificate"].get("complete") is not True
   244	        ):
   245	            raise RuntimeError(f"PANELCEIL exact reference failed at anchor {index}")
   246	        current = anchors[index]
   247	        by_id = {row["profile_id"]: row for row in current["profiles"]}
   248	        for field, metric_name in (
   249	            ("certified_fixed_point_profile_id", "U_FIRST"),
   250	            ("anytime_incumbent_profile_id", "U_FIRST_AT_10"),
   251	        ):
   252	            outcome = by_id[current[field]]["outcome"]
   253	            metric = ceiling["committed"][metric_name]
   254	            expected = {
   255	                "full_buffer_bits": float(metric["bits"]),
   256	                "joules": float(metric["joules"]),
   257	                "rate_target_attained": int(metric["rate_target_attained_count"]),
   258	                "rate_target_opportunities": int(metric["user_count"]),
   259	                "service_available": int(metric["served_count"]),
   260	                "service_opportunities": int(metric["user_count"]),
   261	            }
   262	            if any(outcome[name] != value for name, value in expected.items()):
   263	                raise RuntimeError(f"PANELCEIL endpoint metric drifted at anchor {index}")
   264	
   265	    summary = {
   266	        "verdict": "PASS_EXACT_PHYSICS_REAL_DEVELOPMENT_ANCHORS",
   267	        "common_catalogue": "real development-anchor engine catalogue; authenticated profile-ID equality",
   268	        "full_buffer_outcomes": "exact realised 48-boundary physics; authenticated cache equality",
   269	        "certified_fixed_point": "12 authenticated PANELCEIL plus 8 complete producer computations",
   270	        "same_budget_anytime_incumbent": "same traversal, last accepted iterate by 10.0 s",
   271	        "anchor_indices": list(range(20)),
   272	        "development_dates": ["2026-01-07"],
   273	        "panelceil_anchors": 12,
   274	        "producer_reference_anchors": producer_reference_anchors,
   275	        "exact_outcome_boundary_evaluations": exact_outcome_boundary_evaluations,
   276	        "fixture_physical_values_surviving": 0,
   277	        "historical_flag_referred_to": "construction-nominated synthetic checkpoint",
   278	        "rebuilt_flag_refers_to": "panel-carried physical content",
   279	    }
   280	    del panel, anchors, receipt, panelceil
   281	    gc.collect()
   282	    return summary
   283	
   284	
   285	def main() -> int:
   286	    parser = argparse.ArgumentParser()
   287	    parser.add_argument("--q1-schema", choices=("v1", "v2"), required=True)
   288	    parser.add_argument("--checkpoint", type=Path, required=True)
   289	    parser.add_argument("--output", type=Path, required=True)
   290	    parser.add_argument("--resume-dir", type=Path, required=True)
   291	    parser.add_argument("--outcome-cache-dir", type=Path, required=True)
   292	    parser.add_argument("--limit", type=int, default=20)
   293	    args = parser.parse_args()
   294	    if Path(sys.executable).resolve() != PYTHON.resolve():
   295	        raise RuntimeError(f"wrong interpreter: {sys.executable}")
   296	    if not below_workspace(args.output) or not below_workspace(args.resume_dir):
   297	        raise RuntimeError("all writes must remain below the PANELFIX workspace")
   298	    if args.output.exists():
   299	        raise RuntimeError(f"refusing to overwrite {args.output}")
   300	    if any(os.environ.get(name) != "1" for name in THREAD_VARIABLES):
   301	        raise RuntimeError("all BLAS thread variables must equal 1")
   302	    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
   303	        os.nice(15 - os.getpriority(os.PRIO_PROCESS, 0))
   304	
   305	    provenance = audit_physical_provenance()
   306	    print("physical provenance PASS: no fixture value survives", flush=True)
   307	    print(f"peak_rss_bytes={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024} after provenance", flush=True)
   308	
   309	    builder = load_module("panelfix_upstream_builder", UPSTREAM_BUILDER)
   310	    q1v2 = load_module("panelfix_q1_schema_v2", Q1_V2_MODULE) if args.q1_schema == "v2" else None
   311	    original_atomic_json = builder.atomic_json
   312	    original_load_module = builder.load_module
   313	    original_feature_loader = builder.load_exact_feature_rows
   314	    original_receipt_for_sources = json.loads(ORIGINAL_RECEIPT.read_text(encoding="ascii"))
   315	
   316	    def fail_closed_c3_state(pilot, tape, step_index, base, config, rows_by_action,
   317	                             width: int, member_width: int):
   318	        changed = tuple(
   319	            user for user in sorted(base.mapping)
   320	            if base.mapping[user] != config.mapping[user]
   321	        )
   322	        if len(changed) <= 1:
   323	            return len(changed), [0.0] * width
   324	        context = pilot._coalition_context(
   325	            tape=tape, step_index=step_index, anchor=base, selected=config,
   326	            rows_by_user_action=rows_by_action,
   327	        )
   328	        full = context.invariant_vector(member_width=member_width).tolist()
   329	        if len(full) != width:
   330	            raise RuntimeError(
   331	                f"checkpoint C3 width {width} differs from complete bound encoder width {len(full)}; truncation is forbidden"
   332	            )
   333	        return len(changed), full
   334	
   335	    def v2_feature_loader(source: Mapping[str, object], widths: Mapping[str, int]):
   336	        if args.q1_schema == "v1":
   337	            return original_feature_loader(source, widths)
   338	        if widths != {"C1": 15, "C2": 22, "C3": 236, "C3_MEMBER": 36}:
   339	            raise RuntimeError(f"Q1-v2 checkpoint shape drifted: {dict(widths)!r}")
   340	        index = int(source["index"])
   341	        path = (
   342	            Q1_V2_STAGING / f"global-{index:03d}" / "views" / "world-1"
   343	            / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   344	        )
   345	        verify_sidecar(path)
   346	        raw_lines = path.read_bytes().splitlines()
   347	        values = [json.loads(line.decode("ascii")) for line in raw_lines]
   348	        header = values[0]
   349	        if (
   350	            header.get("schema") != "mcrl-v025-exact-source-view-shard-v1"
   351	            or header.get("global_anchor_index") != index
   352	            or header.get("q1_slots") != 15
   353	            or header.get("q2_slots") != 22
   354	        ):
   355	            raise RuntimeError(f"Q1-v2 exact-view header drifted: {path}")
   356	        result = {}
   357	        for raw, payload in zip(raw_lines[1:], values[1:], strict=True):
   358	            canonical = json.dumps(
   359	                payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
   360	            ).encode("ascii")
   361	            if raw != canonical or "exact_source_view" not in payload:
   362	                raise RuntimeError("Q1-v2 exact-source row is unauthenticated")
   363	            if (
   364	                payload.get("q1_schema_sha256") != Q1_V2_SHA256
   365	                or payload.get("q2_schema_sha256") != Q2_V1_SHA256
   366	            ):
   367	                raise RuntimeError("Q1-v2 row schema digest drifted")
   368	            action = payload["action"]
   369	            identity = None if action["norad_id"] is None else (
   370	                int(action["norad_id"]), int(action["beam_chain_id"])
   371	            )
   372	            q1 = tuple(float.fromhex(value) for value in payload["q1_state"])
   373	            q2 = tuple(float.fromhex(value) for value in payload["q2_state"])
   374	            key = (int(payload["user_id"]), identity)
   375	            if len(q1) != 15 or len(q2) != 22 or key in result:
   376	                raise RuntimeError("Q1-v2 exact-source row shape or identity drifted")
   377	            result[key] = builder.FeatureRow(q1, q2, bool(payload["outage"]))
   378	        if len(result) != int(header["row_count"]):
   379	            raise RuntimeError("Q1-v2 exact-source row count drifted")
   380	        return result
   381	
   382	    def adapted_module_loader(name: str, path: Path):
   383	        module = original_load_module(name, path)
   384	        if path != builder.PANELCEIL_PATH or args.q1_schema != "v2":
   385	            return module
   386	        original_pilot_loader = module.load_pilot
   387	
   388	        def adapted_pilot_loader():
   389	            pilot = original_pilot_loader()
   390	            original_build_rows = pilot._build_anchor_rows
   391	            resolver_cache = {}
   392	
   393	            def build_rows_v2(**kwargs):
   394	                built = original_build_rows(**kwargs)
   395	                tape = kwargs["tape"]
   396	                step_index = int(kwargs["step_index"])
   397	                cache_key = (int(tape.seed), step_index)
   398	                if cache_key not in resolver_cache:
   399	                    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
   400	                    resolver_cache[cache_key] = q1v2.DecisionGeometryResolverV2(
   401	                        tape, LegacyWorldProvider(role="pilot-source"), step_index,
   402	                    )
   403	                resolver = resolver_cache[cache_key]
   404	                converted = {}
   405	                for key, row in built["rows_by_user_action"].items():
   406	                    angle, elevation = resolver(row)
   407	                    converted[key] = builder.FeatureRow(
   408	                        q1v2.upgrade_q1_state_v2(
   409	                            row.q1_state,
   410	                            off_axis_angle_rad=angle,
   411	                            focal_elevation_deg=elevation,
   412	                            null_action=bool(row.null_action),
   413	                        ),
   414	                        tuple(row.q2_state),
   415	                        bool(row.outage),
   416	                    )
   417	                result = dict(built)
   418	                result["rows_by_user_action"] = converted
   419	                return result
   420	
   421	            pilot._build_anchor_rows = build_rows_v2
   422	            return pilot
   423	
   424	        module.load_pilot = adapted_pilot_loader
   425	        return module
   426	
   427	    def annotated_atomic_json(path: Path, value: object) -> None:
   428	        if isinstance(value, dict) and value.get("schema") == builder.PANEL_SCHEMA:
   429	            widths = {len(profile["C3"]["invariant_state"])
   430	                      for anchor in value["anchors"] for profile in anchor["profiles"]}
   431	            expected = 240 if args.q1_schema == "v1" else 236
   432	            if widths != {expected}:
   433	                raise RuntimeError(f"final panel C3 widths are not exactly {{{expected}}}: {widths}")
   434	            value["synthetic_smoke_not_evidence"] = False
   435	            value["panel_identity"]["information_class"] += "; " + FLAG_ASSERTION
   436	        elif isinstance(value, dict) and value.get("schema") == "mcrl-v025-panelbuild-receipt-v1":
   437	            expected = 240 if args.q1_schema == "v1" else 236
   438	            value["synthetic_smoke_not_evidence"] = False
   439	            value["c3_encoding"]["checkpoint_input_width"] = expected
   440	            value["c3_encoding"]["production_full_width"] = expected
   441	            value["c3_encoding"]["global_resource_feature_prefix_count"] = 6
   442	            value["c3_encoding"]["fixture_limitation"] = None
   443	            value["c3_encoding"]["width_policy"] = "exact equality; suffix truncation forbidden"
   444	            value["encoder_binding"] = {
   445	                "q1_schema": args.q1_schema,
   446	                "q1_schema_sha256": Q1_V1_SHA256 if args.q1_schema == "v1" else Q1_V2_SHA256,
   447	                "q1_width": 16 if args.q1_schema == "v1" else 15,
   448	                "q2_schema_sha256": Q2_V1_SHA256,
   449	                "q2_width": 22,
   450	                "c3_member_width": 38 if args.q1_schema == "v1" else 36,
   451	                "c3_full_width": expected,
   452	            }
   453	            value["physical_provenance_audit"] = provenance
   454	            value["synthetic_flag_semantics"] = FLAG_ASSERTION
   455	            value["material_class"] = "development; not claim-grade"
   456	            value["global_evaluator_path_authority"] = "UNDETERMINED by EVALPATH-2026-09-10"
   457	            value["adapter"] = {
   458	                "path": str(Path(__file__).resolve()),
   459	                "sha256": sha256(Path(__file__)),
   460	                "upstream_builder": str(UPSTREAM_BUILDER),
   461	                "upstream_builder_sha256": sha256(UPSTREAM_BUILDER),
   462	                "q1_v2_module_sha256": None if q1v2 is None else sha256(Q1_V2_MODULE),
   463	            }
   464	        original_atomic_json(path, value)
   465	
   466	    builder.c3_state = fail_closed_c3_state
   467	    builder.load_exact_feature_rows = v2_feature_loader
   468	    builder.load_module = adapted_module_loader
   469	    builder.atomic_json = annotated_atomic_json
   470	    builder.discover_panel = lambda limit: resolved_sources(original_receipt_for_sources)[:limit]
   471	    sys.argv = [
   472	        str(Path(__file__).resolve()),
   473	        "--checkpoint", str(args.checkpoint),
   474	        "--output", str(args.output),
   475	        "--resume-dir", str(args.resume_dir),
   476	        "--outcome-cache-dir", str(args.outcome_cache_dir),
   477	        "--limit", str(args.limit),
   478	    ]
   479	    return int(builder.main())
   480	
   481	
   482	if __name__ == "__main__":
   483	    raise SystemExit(main())
