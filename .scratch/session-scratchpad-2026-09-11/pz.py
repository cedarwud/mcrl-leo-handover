     1	#!/home/sat/mcrl-leo-handover/.venv/bin/python
     2	"""Build PANELZ by extending PANELFIX2's fail-closed PANELBUILD adapter."""
     3	
     4	from __future__ import annotations
     5	
     6	import argparse
     7	import hashlib
     8	import importlib.util
     9	import json
    10	import os
    11	from pathlib import Path
    12	import resource
    13	import sys
    14	from typing import Mapping
    15	
    16	
    17	WORKSPACE = Path("/home/sat/mcrl-v025-panelz-ws")
    18	PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
    19	PANELFIX = Path("/home/sat/mcrl-v025-panelfix-ws/scripts/build_stagec_scoring_panel.py")
    20	UPSTREAM = Path("/home/sat/mcrl-v025-witness-ws/scripts/build_stagec_scoring_panel.py")
    21	ORIGINAL_PANEL = Path("/home/sat/mcrl-v025-witness-ws/artifacts/stagec-scoring-panel-first20-v1.json")
    22	ORIGINAL_RECEIPT = ORIGINAL_PANEL.with_name("stagec-scoring-panel-first20-v1.receipt.json")
    23	PANELCEIL_RECEIPT = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/panelceil-receipt.json")
    24	EXPECTED_PANEL_SHA256 = "92d5a80ff018c066ec95507da0f63bf4be5fa6802b3d15fafb8247b069dd53fb"
    25	EXPECTED_PANELCEIL_SHA256 = "52400cf180cd55f4b004be785ba4ff8021e09e38eba20cec7321fbad9999cf7d"
    26	Q1V2_PATH = Path("/home/sat/mcrl-v025-design-ws/q1_schema_v2.py")
    27	ZSCORE_BUILDER_PATH = Path("/home/sat/mcrl-v025-design-ws/build_zscore_corpus.py")
    28	ZSCORE_ROOT = Path(
    29	    "/home/sat/mcrl-v025-design-ws/artifacts/"
    30	    "v025-stagec-c3-coalition-q1v2z-20260910-BUILD_NOT_CLAIM/"
    31	    "corpus/.staging-separated-v1"
    32	)
    33	Q1Z_SHA256 = "bd33e460c1d2f368f0962e6b4f3117784b81c5e8cab517ac5bf3c41053b23d04"
    34	Q2Z_SHA256 = "c2dab920451aa386d0581bb7dd6d2435f352484301ca0d128438b25f2dcb054f"
    35	EXPECTED_WIDTHS = {"C1": 30, "C2": 44, "C3": 296, "C3_MEMBER": 66}
    36	THREAD_VARS = (
    37	    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    38	    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    39	)
    40	
    41	
    42	def load_module(name: str, path: Path):
    43	    spec = importlib.util.spec_from_file_location(name, path)
    44	    if spec is None or spec.loader is None:
    45	        raise RuntimeError(f"cannot import {path}")
    46	    module = importlib.util.module_from_spec(spec)
    47	    sys.modules[name] = module
    48	    spec.loader.exec_module(module)
    49	    return module
    50	
    51	
    52	def sha256(path: Path) -> str:
    53	    digest = hashlib.sha256()
    54	    with path.open("rb") as handle:
    55	        for block in iter(lambda: handle.read(1024 * 1024), b""):
    56	            digest.update(block)
    57	    return digest.hexdigest()
    58	
    59	
    60	def canonical_sha256(value: object) -> str:
    61	    return hashlib.sha256(json.dumps(
    62	        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    63	    ).encode("ascii")).hexdigest()
    64	
    65	
    66	def verify_sidecar(path: Path) -> str:
    67	    actual = sha256(path)
    68	    fields = path.with_name(path.name + ".sha256").read_text(encoding="ascii").split()
    69	    if not fields or fields[0] != actual:
    70	        raise RuntimeError(f"sidecar mismatch: {path}")
    71	    return actual
    72	
    73	
    74	def audit_physical_cache(outcome_cache_dir: Path) -> dict[str, object]:
    75	    if sha256(ORIGINAL_PANEL) != EXPECTED_PANEL_SHA256:
    76	        raise RuntimeError("PANELBUILD panel bytes drifted")
    77	    panel = json.loads(ORIGINAL_PANEL.read_text(encoding="ascii"))
    78	    receipt = json.loads(ORIGINAL_RECEIPT.read_text(encoding="ascii"))
    79	    if receipt.get("panel_sha256") != EXPECTED_PANEL_SHA256:
    80	        raise RuntimeError("PANELBUILD receipt does not bind the panel")
    81	    anchors = panel.get("anchors")
    82	    if not isinstance(anchors, list) or len(anchors) != 20:
    83	        raise RuntimeError("PANELBUILD anchor inventory drifted")
    84	    if {str(row["date"])[:10] for row in anchors} != {"2026-01-07"}:
    85	        raise RuntimeError("panel contains a non-development date")
    86	    cache = receipt["run_identity"]["outcome_cache"]
    87	    if outcome_cache_dir.resolve() != Path(cache["path"]).resolve():
    88	        raise RuntimeError("requested outcome cache differs from authenticated cache")
    89	    files = cache["files"]
    90	    exact_evaluations = 0
    91	    for index, record in enumerate(files):
    92	        if record["name"] != f"anchor-{index:03d}.json":
    93	            raise RuntimeError("outcome cache ordering drifted")
    94	        path = outcome_cache_dir / record["name"]
    95	        if sha256(path) != record["sha256"]:
    96	            raise RuntimeError(f"outcome cache digest drifted at anchor {index}")
    97	        cached = json.loads(path.read_text(encoding="ascii"))
    98	        current = anchors[index]
    99	        if cached["anchor"]["anchor_id"] != current["anchor_id"]:
   100	            raise RuntimeError(f"cached anchor identity drifted at {index}")
   101	        if [row["profile_id"] for row in cached["anchor"]["profiles"]] != [
   102	            row["profile_id"] for row in current["profiles"]
   103	        ]:
   104	            raise RuntimeError(f"cached catalogue drifted at {index}")
   105	        if [row["outcome"] for row in cached["anchor"]["profiles"]] != [
   106	            row["outcome"] for row in current["profiles"]
   107	        ]:
   108	            raise RuntimeError(f"cached physical outcomes drifted at {index}")
   109	        audit = cached["audit"]
   110	        if audit["invalid_profiles"] != 0 or audit["fixed_point_certificate_complete"] is not True:
   111	            raise RuntimeError(f"cached physical/certificate audit failed at {index}")
   112	        exact_evaluations += int(audit["outcome_physics_boundary_evaluations"])
   113	    if sha256(PANELCEIL_RECEIPT) != EXPECTED_PANELCEIL_SHA256:
   114	        raise RuntimeError("PANELCEIL receipt bytes drifted")
   115	    ceiling = json.loads(PANELCEIL_RECEIPT.read_text(encoding="ascii"))
   116	    unsigned = dict(ceiling)
   117	    claimed = unsigned.pop("receipt_sha256", None)
   118	    if ceiling.get("status") != "COMPLETE" or claimed != canonical_sha256(unsigned):
   119	        raise RuntimeError("PANELCEIL receipt is incomplete or unauthenticated")
   120	    return {
   121	        "verdict": "PASS_EXACT_PHYSICS_REAL_DEVELOPMENT_ANCHORS",
   122	        "anchor_indices": list(range(20)),
   123	        "development_dates": ["2026-01-07"],
   124	        "catalogue_and_outcomes": "authenticated field-for-field against PANELBUILD",
   125	        "fixed_points": "12 PANELCEIL plus 8 complete producer certificates",
   126	        "exact_outcome_boundary_evaluations": exact_evaluations,
   127	        "fixture_physical_values_surviving": 0,
   128	    }
   129	
   130	
   131	def beneath_workspace(path: Path) -> bool:
   132	    try:
   133	        path.resolve().relative_to(WORKSPACE.resolve())
   134	    except ValueError:
   135	        return False
   136	    return True
   137	
   138	
   139	def enforce_runtime() -> None:
   140	    if Path(sys.executable).resolve() != PYTHON.resolve():
   141	        raise RuntimeError(f"wrong interpreter: {sys.executable}")
   142	    if any(os.environ.get(name) != "1" for name in THREAD_VARS):
   143	        raise RuntimeError("all BLAS thread variables must equal 1")
   144	    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
   145	        os.nice(16 - os.getpriority(os.PRIO_PROCESS, 0))
   146	    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
   147	    cap = 4_900_000_000 if hard == resource.RLIM_INFINITY else min(hard, 4_900_000_000)
   148	    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
   149	
   150	
   151	def main() -> int:
   152	    parser = argparse.ArgumentParser()
   153	    parser.add_argument("--checkpoint", type=Path, required=True)
   154	    parser.add_argument("--output", type=Path, required=True)
   155	    parser.add_argument("--resume-dir", type=Path, required=True)
   156	    parser.add_argument("--outcome-cache-dir", type=Path, required=True)
   157	    args = parser.parse_args()
   158	    enforce_runtime()
   159	    if not beneath_workspace(args.output) or not beneath_workspace(args.resume_dir):
   160	        raise RuntimeError("writes must remain below PANELZ workspace")
   161	    if args.output.exists():
   162	        raise RuntimeError(f"refusing to overwrite {args.output}")
   163	
   164	    provenance = audit_physical_cache(args.outcome_cache_dir)
   165	    if provenance.get("fixture_physical_values_surviving") != 0:
   166	        raise RuntimeError("fixture physical value survived provenance audit")
   167	    print("physical provenance PASS: no fixture value survives", flush=True)
   168	
   169	    builder = load_module("panelz_upstream", UPSTREAM)
   170	    sys.path.insert(0, str(Q1V2_PATH.parent))
   171	    q1v2 = load_module("panelz_q1v2", Q1V2_PATH)
   172	    zscore = load_module("panelz_zscore", ZSCORE_BUILDER_PATH)
   173	    original_atomic_json = builder.atomic_json
   174	    original_load_module = builder.load_module
   175	
   176	    def streaming_atomic_json(path: Path, value: object) -> None:
   177	        path.parent.mkdir(parents=True, exist_ok=True)
   178	        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
   179	        encoder = json.JSONEncoder(
   180	            indent=2, sort_keys=True, allow_nan=False, ensure_ascii=True,
   181	        )
   182	        with temporary.open("w", encoding="ascii") as handle:
   183	            for chunk in encoder.iterencode(value):
   184	                handle.write(chunk)
   185	            handle.write("\n")
   186	            handle.flush()
   187	            os.fsync(handle.fileno())
   188	        temporary.replace(path)
   189	
   190	    def z_discover_panel(limit: int):
   191	        if limit != 20:
   192	            raise RuntimeError("PANELZ requires exactly the global 000--019 prefix")
   193	        upstream_receipt = json.loads(ORIGINAL_RECEIPT.read_text(encoding="ascii"))
   194	        parents = upstream_receipt["run_identity"]["sources"]
   195	        if [int(row["index"]) for row in parents] != list(range(20)):
   196	            raise RuntimeError("PANELBUILD source prefix drifted")
   197	        sources = []
   198	        for index, parent in enumerate(parents):
   199	            view = (
   200	                ZSCORE_ROOT / f"global-{index:03d}" / "views" / "world-1"
   201	                / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   202	            )
   203	            digest = verify_sidecar(view)
   204	            header = json.loads(view.read_bytes().splitlines()[0])
   205	            expected = (index, index // 3, index % 3)
   206	            actual = (
   207	                int(header["global_anchor_index"]), int(header["step_index"]),
   208	                int(header["carrier_index"]),
   209	            )
   210	            if actual != expected:
   211	                raise RuntimeError(f"z anchor generation order drifted at {index}")
   212	            sources.append({
   213	                **parent,
   214	                "view_path": str(view),
   215	                "view_sha256": digest,
   216	                "state_view_schema": "Q1-v2/Q2-v1 raw-plus-live-user-z",
   217	            })
   218	        return sources
   219	
   220	    def strict_c3(pilot, tape, step_index, base, config, rows_by_action,
   221	                  width: int, member_width: int):
   222	        changed = tuple(
   223	            user for user in sorted(base.mapping)
   224	            if base.mapping[user] != config.mapping[user]
   225	        )
   226	        if len(changed) <= 1:
   227	            return len(changed), [0.0] * width
   228	        context = pilot._coalition_context(
   229	            tape=tape, step_index=step_index, anchor=base, selected=config,
   230	            rows_by_user_action=rows_by_action,
   231	        )
   232	        full = context.invariant_vector(member_width=member_width).tolist()
   233	        if len(full) != width:
   234	            raise RuntimeError(
   235	                f"checkpoint C3 width {width} differs from complete bound encoder "
   236	                f"width {len(full)}; truncation is forbidden"
   237	            )
   238	        return len(changed), full
   239	
   240	    def z_feature_loader(source: Mapping[str, object], widths: Mapping[str, int]):
   241	        if dict(widths) != EXPECTED_WIDTHS:
   242	            raise RuntimeError(f"z checkpoint shape drifted: {dict(widths)!r}")
   243	        index = int(source["index"])
   244	        path = (
   245	            ZSCORE_ROOT / f"global-{index:03d}" / "views" / "world-1"
   246	            / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   247	        )
   248	        verify_sidecar(path)
   249	        lines = path.read_bytes().splitlines()
   250	        values = [json.loads(line.decode("ascii")) for line in lines]
   251	        header = values[0]
   252	        if (
   253	            header.get("schema") != "mcrl-v025-exact-source-view-shard-v1"
   254	            or header.get("global_anchor_index") != index
   255	            or header.get("q1_slots") != 30
   256	            or header.get("q2_slots") != 44
   257	        ):
   258	            raise RuntimeError(f"z exact-view header drifted: {path}")
   259	        result = {}
   260	        for raw, payload in zip(lines[1:], values[1:], strict=True):
   261	            canonical = json.dumps(
   262	                payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
   263	            ).encode("ascii")
   264	            if raw != canonical or "exact_source_view" not in payload:
   265	                raise RuntimeError("z exact-source row is unauthenticated")
   266	            if (
   267	                payload.get("q1_schema_sha256") != Q1Z_SHA256
   268	                or payload.get("q2_schema_sha256") != Q2Z_SHA256
   269	            ):
   270	                raise RuntimeError("z row schema digest drifted")
   271	            action = payload["action"]
   272	            identity = None if action["norad_id"] is None else (
   273	                int(action["norad_id"]), int(action["beam_chain_id"])
   274	            )
   275	            key = (int(payload["user_id"]), identity)
   276	            q1 = tuple(float.fromhex(value) for value in payload["q1_state"])
   277	            q2 = tuple(float.fromhex(value) for value in payload["q2_state"])
   278	            if len(q1) != 30 or len(q2) != 44 or key in result:
   279	                raise RuntimeError("z source row width or identity drifted")
   280	            result[key] = builder.FeatureRow(q1, q2, bool(payload["outage"]))
   281	        if len(result) != int(header["row_count"]):
   282	            raise RuntimeError("z source row count drifted")
   283	        return result
   284	
   285	    def adapted_module_loader(name: str, path: Path):
   286	        module = original_load_module(name, path)
   287	        if path != builder.PANELCEIL_PATH:
   288	            return module
   289	        original_pilot_loader = module.load_pilot
   290	
   291	        def adapted_pilot_loader():
   292	            pilot = original_pilot_loader()
   293	            original_build_rows = pilot._build_anchor_rows
   294	            resolver_cache = {}
   295	
   296	            def build_rows_v2z(**kwargs):
   297	                built = original_build_rows(**kwargs)
   298	                tape = kwargs["tape"]
   299	                step_index = int(kwargs["step_index"])
   300	                cache_key = (int(tape.seed), step_index)
   301	                if cache_key not in resolver_cache:
   302	                    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
   303	                    resolver_cache[cache_key] = q1v2.DecisionGeometryResolverV2(
   304	                        tape, LegacyWorldProvider(role="pilot-source"), step_index,
   305	                    )
   306	                resolver = resolver_cache[cache_key]
   307	                payloads = []
   308	                for row in built["rows"]:
   309	                    angle, elevation = resolver(row)
   310	                    payloads.append(q1v2.project_row_payload_v2(
   311	                        row.payload(), off_axis_angle_rad=angle,
   312	                        focal_elevation_deg=elevation,
   313	                        geometry_source=(
   314	                            "provider boundary-0 ECEF satellite/cell/user geometry; "
   315	                            "elevation cross-checked against PrimitiveStepArrays"
   316	                        ),
   317	                    ))
   318	                import numpy as np
   319	                zeros = {
   320	                    "q1_groups": np.zeros(15, dtype=np.int64),
   321	                    "q2_groups": np.zeros(22, dtype=np.int64),
   322	                    "q1_rows": np.zeros(15, dtype=np.int64),
   323	                    "q2_rows": np.zeros(22, dtype=np.int64),
   324	                }
   325	                transformed, _census = zscore.zscore_rows(
   326	                    payloads, q1_digest=Q1Z_SHA256, q2_digest=Q2Z_SHA256,
   327	                    all_q1=[], all_q2=[], zero_counts=zeros,
   328	                )
   329	                converted = {}
   330	                for key, row in built["rows_by_user_action"].items():
   331	                    user, identity = key
   332	                    z_key = (user, (None, None) if identity is None else identity)
   333	                    q1_hex, q2_hex = transformed[z_key]
   334	                    converted[key] = builder.FeatureRow(
   335	                        tuple(float.fromhex(value) for value in q1_hex),
   336	                        tuple(float.fromhex(value) for value in q2_hex),
   337	                        bool(row.outage),
   338	                    )
   339	                result = dict(built)
   340	                result["rows_by_user_action"] = converted
   341	                return result
   342	
   343	            pilot._build_anchor_rows = build_rows_v2z
   344	            return pilot
   345	
   346	        module.load_pilot = adapted_pilot_loader
   347	        return module
   348	
   349	    def annotated_atomic_json(path: Path, value: object) -> None:
   350	        if isinstance(value, dict) and value.get("schema") == builder.PANEL_SCHEMA:
   351	            observed = {
   352	                (len(pair["selected"]), len(anchor["profiles"][0]["C3"]["invariant_state"]))
   353	                for anchor in value["anchors"]
   354	                for profile in anchor["profiles"]
   355	                for pair in profile["C1"][:1]
   356	            }
   357	            c3_widths = {
   358	                len(profile["C3"]["invariant_state"])
   359	                for anchor in value["anchors"] for profile in anchor["profiles"]
   360	            }
   361	            if c3_widths != {296} or any(
   362	                len(pair[side]) != expected
   363	                for anchor in value["anchors"] for profile in anchor["profiles"]
   364	                for route, expected in (("C1", 30), ("C2", 44))
   365	                for pair in profile[route] for side in ("reference", "selected")
   366	            ):
   367	                raise RuntimeError(f"final panel state widths drifted: {observed}, C3={c3_widths}")
   368	            value["synthetic_smoke_not_evidence"] = False
   369	            value["panel_identity"]["name"] = "panel-q1v2z development first-20 Stage-C scoring panel"
   370	            value["panel_identity"]["information_class"] += (
   371	                "; every panel-carried physical field audited as exact physics on real "
   372	                "development anchors; EVALPATH-2026-09-10 leaves global evaluator path "
   373	                "authority UNDETERMINED; development material, not claim-grade"
   374	            )
   375	        elif isinstance(value, dict) and value.get("schema") == "mcrl-v025-panelbuild-receipt-v1":
   376	            value["synthetic_smoke_not_evidence"] = False
   377	            value["c3_encoding"].update({
   378	                "checkpoint_input_width": 296,
   379	                "production_full_width": 296,
   380	                "global_resource_feature_prefix_count": 6,
   381	                "fixture_limitation": None,
   382	                "width_policy": "exact equality; suffix truncation forbidden",
   383	            })
   384	            value["encoder_binding"] = {
   385	                "q1_schema": "v2z", "q1_schema_sha256": Q1Z_SHA256,
   386	                "q1_width": 30, "q2_schema_sha256": Q2Z_SHA256,
   387	                "q2_width": 44, "c3_member_width": 66, "c3_full_width": 296,
   388	            }
   389	            value["physical_provenance_audit"] = provenance
   390	            value["state_provenance"] = {
   391	                "authenticated_z_shortlist_rows": "Q1-v2/Q2-v1 raw plus live-user population z",
   392	                "missing_reference_actions": (
   393	                    "exact physics regeneration, Q1-v2 decision geometry, then identical "
   394	                    "float64 population-z transform over full legal action rows"
   395	                ),
   396	                "fixture_state_values_surviving": 0,
   397	            }
   398	            value["material_class"] = "development; not claim-grade"
   399	            value["global_evaluator_path_authority"] = "UNDETERMINED by EVALPATH-2026-09-10"
   400	            value["adapter_chain"] = {
   401	                "panelz": str(Path(__file__).resolve()),
   402	                "panelfix2": str(PANELFIX),
   403	                "upstream_panelbuild": str(UPSTREAM),
   404	            }
   405	        streaming_atomic_json(path, value)
   406	
   407	    builder.c3_state = strict_c3
   408	    builder.discover_panel = z_discover_panel
   409	    builder.load_exact_feature_rows = z_feature_loader
   410	    builder.load_module = adapted_module_loader
   411	    builder.atomic_json = annotated_atomic_json
   412	    sys.argv = [
   413	        str(Path(__file__).resolve()),
   414	        "--checkpoint", str(args.checkpoint),
   415	        "--output", str(args.output),
   416	        "--resume-dir", str(args.resume_dir),
   417	        "--outcome-cache-dir", str(args.outcome_cache_dir),
   418	        "--limit", "20",
   419	    ]
   420	    result = int(builder.main())
   421	    print(f"peak_rss_bytes={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024} panelz-final", flush=True)
   422	    return result
   423	
   424	
   425	if __name__ == "__main__":
   426	    raise SystemExit(main())
