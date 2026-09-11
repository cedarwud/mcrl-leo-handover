     1	#!/home/sat/mcrl-leo-handover/.venv/bin/python
     2	"""Build the authenticated Stage-C dual-axis scoring panel.
     3	
     4	The exact-source and PANELCEIL workspaces are read-only inputs.  This program
     5	writes resumable anchor fragments and the final panel only below this workspace.
     6	"""
     7	
     8	from __future__ import annotations
     9	
    10	import argparse
    11	from dataclasses import dataclass
    12	from fractions import Fraction
    13	import hashlib
    14	import importlib.util
    15	import json
    16	import math
    17	import os
    18	from pathlib import Path
    19	import resource
    20	import sys
    21	import time
    22	from typing import Mapping, Sequence
    23	
    24	
    25	THREAD_VARIABLES = (
    26	    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    27	    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    28	)
    29	for _variable in THREAD_VARIABLES:
    30	    os.environ[_variable] = "1"
    31	
    32	WORKSPACE = Path("/home/sat/mcrl-v025-witness-ws")
    33	PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
    34	SOURCE_ROOT = Path("/home/sat/mcrl-v025-c1c2suff-ws")
    35	PILOT_PATH = SOURCE_ROOT / "scripts/run_v025_pilot_c3.py"
    36	CALIBRATION_PATH = (
    37	    SOURCE_ROOT / "artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM"
    38	    / "PILOT_NOT_CLAIM-calibration.json"
    39	)
    40	PANELCEIL_PATH = Path(
    41	    "/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py"
    42	)
    43	PANELCEIL_RECEIPT = Path(
    44	    "/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/panelceil-receipt.json"
    45	)
    46	EXACT_ROOT = Path(
    47	    "/home/sat/mcrl-v025-datepool-ws/artifacts/"
    48	    "v025-exact-source-20260910-BUILD_NOT_CLAIM"
    49	)
    50	STAGING = EXACT_ROOT / ".staging-separated-v1"
    51	DEFAULT_CHECKPOINT = Path(
    52	    "/home/sat/mcrl-v025-retrain-ws/.scratch/"
    53	    "training-runner-checkpoint-kat-20260910-final/fixture-checkpoint/"
    54	    "learner-6407676579069309528-epoch-000100.json"
    55	)
    56	DEFAULT_OUTPUT = WORKSPACE / "artifacts/stagec-scoring-panel-first20-v1.json"
    57	DEFAULT_RESUME = WORKSPACE / ".scratch/panelbuild"
    58	PANEL_SCHEMA = "mcrl-v025-dual-axis-scoring-panel-v1"
    59	SMOKE_CHECKPOINT_SHA256 = (
    60	    "bcf99d209c62782eb524ff609e2008d8e8a59828e733791a9e1d9b43fb310428"
    61	)
    62	NUMERATOR = (
    63	    "sum of saturated full-buffer successfully decoded forward-downlink information bits; "
    64	    "rate target is a power-control setpoint; no demand cap"
    65	)
    66	ENERGY_BOUNDARY = (
    67	    "modelled partial-payload DC energy: user-link PA supply, per-beam chain circuitry, "
    68	    "and common processing increment; declared idle states included"
    69	)
    70	TRAVERSAL = (
    71	    "ascending users; declared legal options; first strict improvement in ordered "
    72	    "microbatches of 16"
    73	)
    74	MAX_RSS_BYTES = 5_000_000_000
    75	OUTCOME_BATCH_SIZE = 8
    76	CARRIERS = ("nearest-eligible", "stay-if-possible", "random-masked")
    77	
    78	
    79	@dataclass(frozen=True, slots=True)
    80	class FeatureRow:
    81	    q1_state: tuple[float, ...]
    82	    q2_state: tuple[float, ...]
    83	    outage: bool
    84	
    85	
    86	def sha256(path: Path) -> str:
    87	    digest = hashlib.sha256()
    88	    with path.open("rb") as handle:
    89	        for block in iter(lambda: handle.read(1024 * 1024), b""):
    90	            digest.update(block)
    91	    return digest.hexdigest()
    92	
    93	
    94	def canonical_sha256(value: object) -> str:
    95	    return hashlib.sha256(json.dumps(
    96	        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    97	    ).encode("ascii")).hexdigest()
    98	
    99	
   100	def peak_rss_bytes() -> int:
   101	    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
   102	
   103	
   104	def check_rss() -> int:
   105	    value = peak_rss_bytes()
   106	    if value >= MAX_RSS_BYTES:
   107	        raise MemoryError(f"peak RSS {value} is not below 5 GB")
   108	    return value
   109	
   110	
   111	def enforce_runtime() -> None:
   112	    if Path(sys.executable).resolve() != PYTHON.resolve():
   113	        raise RuntimeError(f"wrong interpreter: {sys.executable}; required {PYTHON}")
   114	    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
   115	        os.nice(15 - os.getpriority(os.PRIO_PROCESS, 0))
   116	    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
   117	        raise RuntimeError("could not enforce nice -n 15")
   118	    bad = {name: os.environ.get(name) for name in THREAD_VARIABLES
   119	           if os.environ.get(name) != "1"}
   120	    if bad:
   121	        raise RuntimeError(f"BLAS thread pins drifted: {bad}")
   122	    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
   123	    new_hard = MAX_RSS_BYTES if hard == resource.RLIM_INFINITY else min(hard, MAX_RSS_BYTES)
   124	    resource.setrlimit(resource.RLIMIT_AS, (min(MAX_RSS_BYTES, new_hard), new_hard))
   125	
   126	
   127	def atomic_json(path: Path, value: object) -> None:
   128	    path.parent.mkdir(parents=True, exist_ok=True)
   129	    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
   130	    temporary.write_text(
   131	        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
   132	        encoding="ascii",
   133	    )
   134	    temporary.replace(path)
   135	
   136	
   137	def load_module(name: str, path: Path):
   138	    spec = importlib.util.spec_from_file_location(name, path)
   139	    if spec is None or spec.loader is None:
   140	        raise RuntimeError(f"cannot import {path}")
   141	    module = importlib.util.module_from_spec(spec)
   142	    sys.modules[name] = module
   143	    spec.loader.exec_module(module)
   144	    return module
   145	
   146	
   147	def checkpoint_shape(path: Path) -> dict[str, int]:
   148	    payload = json.loads(path.read_text(encoding="ascii"))
   149	    result: dict[str, int] = {}
   150	    for route in ("C1", "C2", "C3"):
   151	        heads = [payload["arms"][arm][route] for arm in payload["arms"]]
   152	        widths = {len(head["weights_hex"][0]) for head in heads}
   153	        if len(widths) != 1:
   154	            raise RuntimeError(f"checkpoint {route} widths differ by arm")
   155	        result[route] = next(iter(widths))
   156	    member_widths = {payload["arms"][arm]["C3"]["member_width"] for arm in payload["arms"]}
   157	    if len(member_widths) != 1:
   158	        raise RuntimeError("checkpoint C3 member widths differ by arm")
   159	    result["C3_MEMBER"] = int(next(iter(member_widths)))
   160	    return result
   161	
   162	
   163	def verify_sidecar(path: Path, expected: str) -> None:
   164	    if sha256(path) != expected:
   165	        raise RuntimeError(f"authenticated input changed: {path}")
   166	    sidecar = path.with_name(path.name + ".sha256")
   167	    if not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != expected:
   168	        raise RuntimeError(f"missing or mismatched SHA-256 sidecar: {path}")
   169	
   170	
   171	def load_exact_feature_rows(source: Mapping[str, object], widths: Mapping[str, int]):
   172	    path = Path(str(source["view_path"]))
   173	    raw_lines = path.read_bytes().splitlines()
   174	    values = [json.loads(line.decode("ascii")) for line in raw_lines]
   175	    if not values or values[0].get("schema") != "mcrl-v025-exact-source-view-shard-v1":
   176	        raise RuntimeError(f"exact source-view header drifted: {path}")
   177	    if values[0].get("global_anchor_index") != source["index"]:
   178	        raise RuntimeError("exact source-view anchor identity drifted")
   179	    result = {}
   180	    for raw, payload in zip(raw_lines[1:], values[1:], strict=True):
   181	        canonical = json.dumps(
   182	            payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
   183	        ).encode("ascii")
   184	        if raw != canonical or "exact_source_view" not in payload:
   185	            raise RuntimeError("exact source-view row is noncanonical or lacks its receipt")
   186	        action = payload["action"]
   187	        identity = (
   188	            None if action["norad_id"] is None
   189	            else (int(action["norad_id"]), int(action["beam_chain_id"]))
   190	        )
   191	        q1 = tuple(float.fromhex(value) for value in payload["q1_state"])
   192	        q2 = tuple(float.fromhex(value) for value in payload["q2_state"])
   193	        if len(q1) != widths["C1"] or len(q2) != widths["C2"]:
   194	            raise RuntimeError("authenticated exact source-view feature width drifted")
   195	        key = (int(payload["user_id"]), identity)
   196	        if key in result:
   197	            raise RuntimeError(f"duplicate exact feature row: {key}")
   198	        result[key] = FeatureRow(q1, q2, bool(payload["outage"]))
   199	    if len(result) != int(values[0]["row_count"]):
   200	        raise RuntimeError("exact source-view row count drifted")
   201	    return result
   202	
   203	
   204	def discover_panel(limit: int) -> list[dict[str, object]]:
   205	    rows = []
   206	    for index in range(limit):
   207	        root = STAGING / f"global-{index:03d}"
   208	        result_path = root / f"BUILD_NOT_CLAIM-anchor-{index:03d}.result.json"
   209	        if not result_path.is_file():
   210	            break
   211	        payload = json.loads(result_path.read_text(encoding="ascii"))
   212	        step_index, carrier_index = divmod(index, len(CARRIERS))
   213	        expected = (index, 1, step_index, carrier_index, CARRIERS[carrier_index])
   214	        actual = (
   215	            payload["global_anchor_index"], payload["world_index"], payload["step_index"],
   216	            payload["carrier_index"], payload["carrier"],
   217	        )
   218	        if actual != expected:
   219	            raise RuntimeError(f"declared generation order drifted at global anchor {index}")
   220	        physics = root / "physics" / str(payload["physics_relative_path"])
   221	        view = root / "views" / str(payload["view_relative_path"])
   222	        verify_sidecar(physics, str(payload["physics_sha256"]))
   223	        verify_sidecar(view, str(payload["view_sha256"]))
   224	        rows.append({
   225	            "index": index, "step_index": step_index, "carrier": payload["carrier"],
   226	            "world_id": payload["world_id"], "result_path": str(result_path),
   227	            "result_sha256": sha256(result_path), "physics_path": str(physics),
   228	            "physics_sha256": payload["physics_sha256"], "view_path": str(view),
   229	            "view_sha256": payload["view_sha256"],
   230	        })
   231	    if not rows:
   232	        raise RuntimeError("exact-source corpus has no contiguous anchor prefix")
   233	    return rows
   234	
   235	
   236	def load_calibration(pilot):
   237	    payload = json.loads(CALIBRATION_PATH.read_text(encoding="ascii"))
   238	    ratio = lambda name: Fraction(*payload[name])
   239	    return pilot.PilotCalibration(
   240	        eta_ref=ratio("eta_ref"), lambda_bits_per_j=ratio("lambda_bits_per_j"),
   241	        kappa_bits_per_user_step=ratio("kappa_bits_per_user_step"),
   242	        bits_ref=ratio("bits_ref"), joules_ref=ratio("joules_ref"),
   243	        users=int(payload["users"]),
   244	    )
   245	
   246	
   247	def panelceil_snapshot() -> tuple[dict[int, dict[str, object]], dict[str, object] | None]:
   248	    if not PANELCEIL_RECEIPT.is_file():
   249	        return {}, None
   250	    try:
   251	        payload = json.loads(PANELCEIL_RECEIPT.read_text(encoding="ascii"))
   252	    except (OSError, json.JSONDecodeError):
   253	        return {}, None
   254	    if payload.get("status") != "COMPLETE":
   255	        return {}, {"status": payload.get("status"), "path": str(PANELCEIL_RECEIPT)}
   256	    claimed = payload.get("receipt_sha256")
   257	    unsigned = dict(payload)
   258	    unsigned.pop("receipt_sha256", None)
   259	    if claimed != canonical_sha256(unsigned):
   260	        raise RuntimeError("PANELCEIL receipt authentication failed")
   261	    rows = {int(row["global_anchor_index"]): row for row in payload["anchors"]}
   262	    return rows, {
   263	        "status": "COMPLETE", "path": str(PANELCEIL_RECEIPT),
   264	        "file_sha256": sha256(PANELCEIL_RECEIPT), "receipt_sha256": claimed,
   265	        "anchor_count": len(rows),
   266	    }
   267	
   268	
   269	def mapping_from_receipt(rows: Sequence[Sequence[object]]) -> dict[int, tuple[int, int] | None]:
   270	    return {
   271	        int(user): None if identity is None else (int(identity[0]), int(identity[1]))
   272	        for user, identity in rows
   273	    }
   274	
   275	
   276	def profile_id(configuration_id: str) -> str:
   277	    return "profile:" + hashlib.sha256(configuration_id.encode("ascii")).hexdigest()
   278	
   279	
   280	def outcome(pilot, tape, step_index: int, incumbent, profile) -> dict[str, float | int]:
   281	    attained = profile.score.rate_target_attained
   282	    if attained is None:
   283	        raise RuntimeError("physical profile omitted rate-target attainment")
   284	    rekeys = pilot.ENGINE._rekeyed_users(tape, step_index)
   285	    events = pilot.ENGINE._physical_events(
   286	        incumbent, profile.config, cell_rekeyed_users=rekeys,
   287	    )
   288	    users = len(profile.config.assignments)
   289	    return {
   290	        "full_buffer_bits": float(profile.bits), "joules": float(profile.joules),
   291	        "rate_target_attained": sum(bool(value) for value in attained.values()),
   292	        "rate_target_opportunities": len(attained),
   293	        "service_available": sum(bool(value) for value in profile.score.served_phy.values()),
   294	        "service_opportunities": users,
   295	        "handovers": sum(event.kind in {"beam_change", "satellite_change", "cell_rekey"}
   296	                         for event in events),
   297	        "handover_opportunities": users, "deadline_misses": 0, "decisions": 0,
   298	    }
   299	
   300	
   301	def receipt_outcome(pilot, tape, step_index: int, incumbent, config,
   302	                    metric: Mapping[str, object]) -> dict[str, float | int]:
   303	    events = pilot.ENGINE._physical_events(
   304	        incumbent, config,
   305	        cell_rekeyed_users=pilot.ENGINE._rekeyed_users(tape, step_index),
   306	    )
   307	    users = int(metric["user_count"])
   308	    return {
   309	        "full_buffer_bits": float(metric["bits"]), "joules": float(metric["joules"]),
   310	        "rate_target_attained": int(metric["rate_target_attained_count"]),
   311	        "rate_target_opportunities": users, "service_available": int(metric["served_count"]),
   312	        "service_opportunities": users,
   313	        "handovers": sum(event.kind in {"beam_change", "satellite_change", "cell_rekey"}
   314	                         for event in events),
   315	        "handover_opportunities": users, "deadline_misses": 0, "decisions": 0,
   316	    }
   317	
   318	
   319	def c3_state(pilot, tape, step_index: int, base, config, rows_by_action,
   320	             width: int, member_width: int) -> tuple[int, list[float]]:
   321	    changed = tuple(user for user in sorted(base.mapping)
   322	                    if base.mapping[user] != config.mapping[user])
   323	    if len(changed) <= 1:
   324	        return len(changed), [0.0] * width
   325	    context = pilot._coalition_context(
   326	        tape=tape, step_index=step_index, anchor=base, selected=config,
   327	        rows_by_user_action=rows_by_action,
   328	    )
   329	    full = context.invariant_vector(member_width=member_width).tolist()
   330	    # The production context currently has six trailing global-resource
   331	    # scalars.  A checkpoint declares how many of that ordered prefix it owns.
   332	    fixed_width = len(full) - len(context.global_resource_features)
   333	    globals_owned = width - fixed_width
   334	    if globals_owned < 1 or globals_owned > len(context.global_resource_features):
   335	        raise RuntimeError(
   336	            f"checkpoint C3 width {width} cannot encode production context width {len(full)}"
   337	        )
   338	    return len(changed), full[:fixed_width + globals_owned]
   339	
   340	
   341	def build_anchor(*, pilot, panelceil, calibration, tape, source: Mapping[str, object],
   342	                 widths: Mapping[str, int], reused: Mapping[str, object] | None,
   343	                 cached_anchor: Mapping[str, object] | None,
   344	                 total: int) -> tuple[dict[str, object], dict[str, object]]:
   345	    index = int(source["index"])
   346	    step_index = int(source["step_index"])
   347	    carrier = str(source["carrier"])
   348	    setting = pilot.ENGINE._setting("a-r0")
   349	    run_setting = pilot.ENGINE.run_setting_for("a-r0")
   350	    base = pilot.ENGINE._base_configuration(tape, step_index, carrier)
   351	    incumbent = pilot.ENGINE._base_configuration(tape, max(0, step_index - 1), carrier)
   352	    started = time.perf_counter()
   353	
   354	    catalogue, census = pilot.ENGINE._catalogue_with_census(
   355	        tape, step_index, base, setting=setting, calibration=calibration,
   356	        counter=pilot.ENGINE.EvaluationCounter(), run_setting=run_setting,
   357	    )
   358	
   359	    reused_names: list[str] = []
   360	    reused_metrics: dict[tuple[tuple[int, tuple[int, int] | None], ...], Mapping[str, object]] = {}
   361	    if reused is not None:
   362	        if reused.get("anchor_id") != f"{source['world_id']}|{step_index}|{carrier}":
   363	            raise RuntimeError(f"PANELCEIL anchor identity mismatch at {index}")
   364	        first_metric = reused["committed"]["U_FIRST"]
   365	        anytime_metric = reused["committed"]["U_FIRST_AT_10"]
   366	        fixed = pilot.ENGINE._configuration(
   367	            base, mapping_from_receipt(first_metric["assignments"]), kind="panelbuild-reused-fixed",
   368	        )
   369	        anytime = pilot.ENGINE._configuration(
   370	            base, mapping_from_receipt(anytime_metric["assignments"]), kind="panelbuild-reused-anytime",
   371	        )
   372	        if not reused["first_improvement"]["termination_certificate"]["complete"]:
   373	            raise RuntimeError("PANELCEIL first-improvement certificate is incomplete")
   374	        reused_metrics[fixed.assignments] = first_metric
   375	        reused_metrics[anytime.assignments] = anytime_metric
   376	        reused_names.extend(("certified_fixed_point", "anytime_incumbent_10s"))
   377	    else:
   378	        search = panelceil.first_improvement(
   379	            pilot.ENGINE, calibration, tape, step_index, base, incumbent, run_setting,
   380	        )
   381	        if not search.receipt["termination_certificate"]["complete"]:
   382	            raise RuntimeError("first-improvement search lacks a complete terminal certificate")
   383	        fixed = search.selected
   384	        if cached_anchor is None:
   385	            anytime = panelceil.config_at(search, 10.0)
   386	        else:
   387	            expected_fixed = str(cached_anchor["certified_fixed_point_profile_id"])
   388	            expected_anytime = str(cached_anchor["anytime_incumbent_profile_id"])
   389	            if profile_id(fixed.configuration_id) != expected_fixed:
   390	                raise RuntimeError("recomputed fixed-point identity differs from outcome cache")
   391	            matching = [config for _elapsed, config in search.moves
   392	                        if profile_id(config.configuration_id) == expected_anytime]
   393	            if not matching:
   394	                raise RuntimeError("cached 10-second incumbent is absent from recomputed search path")
   395	            anytime = matching[-1]
   396	
   397	    unique = {row.assignments: row for row in catalogue}
   398	    unique[fixed.assignments] = fixed
   399	    unique[anytime.assignments] = anytime
   400	    ordered = (base,) + tuple(sorted(
   401	        (row for assignments, row in unique.items() if assignments != base.assignments),
   402	        key=lambda row: row.configuration_id,
   403	    ))
   404	
   405	    rows_by_action = load_exact_feature_rows(source, widths)
   406	    required_actions = {
   407	        (user, config.mapping[user])
   408	        for config in ordered for user in base.mapping
   409	        if config.mapping[user] != base.mapping[user]
   410	    }
   411	    required_actions.update((user, identity) for user, identity in base.assignments)
   412	    missing_actions = sorted(
   413	        required_actions - set(rows_by_action),
   414	        key=lambda row: (row[0], (-1, -1) if row[1] is None else row[1]),
   415	    )
   416	    feature_evaluations = 0
   417	    feature_source = "authenticated exact-source view"
   418	    if missing_actions:
   419	        previous_fallback = pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK
   420	        pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK = False
   421	        try:
   422	            built = pilot._build_anchor_rows(
   423	                tape=tape, setting=setting, run_setting=run_setting,
   424	                calibration=calibration, step_index=step_index, carrier=carrier,
   425	                anchor_index=index, include_coalition=False, full_legal_actions=True,
   426	            )
   427	        finally:
   428	            pilot.PILOT_PRIMITIVE_SOURCE_FALLBACK = previous_fallback
   429	        if built["base"].assignments != base.assignments or built["incumbent"].assignments != incumbent.assignments:
   430	            raise RuntimeError("exact feature builder base/incumbent drifted")
   431	        exact_full = built["rows_by_user_action"]
   432	        absent = set(missing_actions) - set(exact_full)
   433	        if absent:
   434	            raise RuntimeError(f"exact physics did not supply required actions: {sorted(absent)!r}")
   435	        rows_by_action.update({key: exact_full[key] for key in missing_actions})
   436	        feature_evaluations = int(built["physics_calls"])
   437	        feature_source = "authenticated exact-source view plus exact targeted-action regeneration"
   438	
   439	    cached_outcomes = {}
   440	    if cached_anchor is not None:
   441	        if cached_anchor.get("anchor_id") != f"{source['world_id']}|{step_index}|{carrier}":
   442	            raise RuntimeError("outcome-cache anchor identity drifted")
   443	        cached_outcomes = {
   444	            str(profile["profile_id"]): profile["outcome"]
   445	            for profile in cached_anchor["profiles"]
   446	        }
   447	
   448	    evaluator = pilot.ENGINE.StepEvaluator(
   449	        tape, setting, step_index, transition_from=incumbent,
   450	        cell_rekeyed_users=pilot.ENGINE._rekeyed_users(tape, step_index),
   451	        field="realised", counter=pilot.ENGINE.EvaluationCounter(),
   452	        run_setting=run_setting, boundary_indices=tuple(range(48)),
   453	    )
   454	    to_evaluate = [
   455	        row for row in ordered
   456	        if row.assignments not in reused_metrics
   457	        and profile_id(row.configuration_id) not in cached_outcomes
   458	    ]
   459	    for offset in range(0, len(to_evaluate), OUTCOME_BATCH_SIZE):
   460	        evaluator.evaluate_many(tuple(to_evaluate[offset:offset + OUTCOME_BATCH_SIZE]))
   461	        check_rss()
   462	
   463	    profiles = []
   464	    invalid = []
   465	    for config in ordered:
   466	        metric = reused_metrics.get(config.assignments)
   467	        if metric is not None:
   468	            physical = receipt_outcome(pilot, tape, step_index, incumbent, config, metric)
   469	        elif profile_id(config.configuration_id) in cached_outcomes:
   470	            physical = cached_outcomes[profile_id(config.configuration_id)]
   471	        else:
   472	            evaluated = evaluator._evaluated.get(config.configuration_id)
   473	            if evaluated is None:
   474	                invalid.append(config.configuration_id)
   475	                continue
   476	            physical = outcome(pilot, tape, step_index, incumbent, evaluated)
   477	        pairs_c1 = []
   478	        pairs_c2 = []
   479	        for user in sorted(base.mapping):
   480	            if config.mapping[user] == base.mapping[user]:
   481	                continue
   482	            reference = rows_by_action[(user, base.mapping[user])]
   483	            selected = rows_by_action[(user, config.mapping[user])]
   484	            pairs_c1.append({"reference": list(reference.q1_state), "selected": list(selected.q1_state)})
   485	            pairs_c2.append({"reference": list(reference.q2_state), "selected": list(selected.q2_state)})
   486	        size, state = c3_state(
   487	            pilot, tape, step_index, base, config, rows_by_action,
   488	            widths["C3"], widths["C3_MEMBER"],
   489	        )
   490	        if pairs_c1 and (len(pairs_c1[0]["reference"]) != widths["C1"]
   491	                         or len(pairs_c2[0]["reference"]) != widths["C2"]):
   492	            raise RuntimeError("checkpoint and exact feature widths differ")
   493	        profiles.append({
   494	            "profile_id": profile_id(config.configuration_id),
   495	            "catalogue_order": len(profiles), "C1": pairs_c1, "C2": pairs_c2,
   496	            "C3": {"coalition_size": size, "invariant_state": state},
   497	            "outcome": physical,
   498	        })
   499	    by_assignment = {row.assignments: profile_id(row.configuration_id) for row in ordered}
   500	    if fixed.assignments not in by_assignment or anytime.assignments not in by_assignment:
   501	        raise RuntimeError("reference profile was lost from the common catalogue")
   502	    anchor_id = f"{source['world_id']}|{step_index}|{carrier}"
   503	    anchor = {
   504	        "anchor_id": anchor_id, "world_id": source["world_id"],
   505	        "date": pilot._utc_at(tape, step_index), "world_seed": tape.seed,
   506	        "base_profile_id": profile_id(base.configuration_id),
   507	        "certified_fixed_point_profile_id": by_assignment[fixed.assignments],
   508	        "anytime_incumbent_profile_id": by_assignment[anytime.assignments],
   509	        "profiles": profiles, "arm_instrumentation": None,
   510	    }
   511	    audit = {
   512	        "anchor_id": anchor_id, "global_anchor_index": index,
   513	        "source": dict(source), "catalogue_mode": census["catalogue_mode"],
   514	        "catalogue_profiles_before_full_horizon_filter": len(ordered),
   515	        "catalogue_profiles_emitted": len(profiles), "invalid_profiles": len(invalid),
   516	        "fixed_point_source": "PANELCEIL" if reused is not None else "producer computation",
   517	        "fixed_point_certificate_complete": True,
   518	        "fixed_point_traversal_order": TRAVERSAL,
   519	        "anytime_budget_s": 10.0,
   520	        "catalogue_profile_id_sha256": canonical_sha256(
   521	            [profile["profile_id"] for profile in profiles]
   522	        ),
   523	        "reused_objects": reused_names,
   524	        "feature_source": feature_source,
   525	        "missing_view_actions_regenerated_exactly": len(missing_actions),
   526	        "feature_physics_boundary_evaluations": feature_evaluations,
   527	        "outcome_physics_boundary_evaluations": evaluator.counter.boundary_evaluations,
   528	        "wall_seconds": time.perf_counter() - started, "peak_rss_bytes": check_rss(),
   529	    }
   530	    print(
   531	        f"anchor {index + 1}/{total} profiles={len(profiles)} "
   532	        f"peak_rss_bytes={audit['peak_rss_bytes']}", flush=True,
   533	    )
   534	    return anchor, audit
   535	
   536	
   537	def main() -> int:
   538	    parser = argparse.ArgumentParser()
   539	    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
   540	    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
   541	    parser.add_argument("--resume-dir", type=Path, default=DEFAULT_RESUME)
   542	    parser.add_argument("--outcome-cache-dir", type=Path)
   543	    parser.add_argument("--limit", type=int, default=20)
   544	    args = parser.parse_args()
   545	    enforce_runtime()
   546	    if args.limit < 1 or args.limit > 20:
   547	        raise RuntimeError("limit must be in 1..20")
   548	    if args.output.exists():
   549	        raise RuntimeError(f"refusing to overwrite {args.output}")
   550	    checkpoint_digest = sha256(args.checkpoint)
   551	    widths = checkpoint_shape(args.checkpoint)
   552	    sources = discover_panel(args.limit)
   553	    print(f"panel prefix {len(sources)}/{args.limit}", flush=True)
   554	    print(f"peak_rss_bytes={check_rss()} before imports", flush=True)
   555	
   556	    panelceil_hash = sha256(PANELCEIL_PATH)
   557	    pilot_hash = sha256(PILOT_PATH)
   558	    panelceil = load_module("panelbuild_panelceil", PANELCEIL_PATH)
   559	    pilot = panelceil.load_pilot()
   560	    calibration = load_calibration(pilot)
   561	    reused, reuse_receipt = panelceil_snapshot()
   562	    if reuse_receipt is None:
   563	        print("PANELCEIL reuse unavailable: receipt absent", flush=True)
   564	    elif not reused:
   565	        print(f"PANELCEIL reuse unavailable: receipt status={reuse_receipt['status']}", flush=True)
   566	    else:
   567	        print(f"PANELCEIL reuse available for {len(reused)} anchors", flush=True)
   568	
   569	    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
   570	    from mcrl.physics_v025.tapes import build_world_tape
   571	    tape = build_world_tape(
   572	        domain=pilot.TRAIN_WORLDS[0], provider=LegacyWorldProvider(role="pilot-source"),
   573	        steps=33, start_time_s=0.0,
   574	    )
   575	    print(f"peak_rss_bytes={check_rss()} after tape", flush=True)
   576	    anchors = []
   577	    audits = []
   578	    run_identity = {
   579	        "checkpoint_sha256": checkpoint_digest, "widths": widths,
   580	        "pilot_sha256": pilot_hash, "panelceil_script_sha256": panelceil_hash,
   581	        "panelceil_receipt": reuse_receipt,
   582	        "sources": sources,
   583	        "feature_source_contract": "authenticated exact view; exact physics for required absent actions",
   584	        "outcome_cache": (
   585	            None if args.outcome_cache_dir is None else {
   586	                "path": str(args.outcome_cache_dir.resolve()),
   587	                "files": [
   588	                    {"name": path.name, "sha256": sha256(path)}
   589	                    for path in sorted(args.outcome_cache_dir.glob("anchor-*.json"))
   590	                ],
   591	            }
   592	        ),
   593	    }
   594	    run_digest = canonical_sha256(run_identity)
   595	    fragment_root = args.resume_dir / run_digest
   596	    for source in sources:
   597	        fragment = fragment_root / f"anchor-{int(source['index']):03d}.json"
   598	        cached_anchor = None
   599	        if args.outcome_cache_dir is not None:
   600	            cache_path = args.outcome_cache_dir / f"anchor-{int(source['index']):03d}.json"
   601	            if not cache_path.is_file():
   602	                raise RuntimeError(f"outcome cache omitted {cache_path}")
   603	            cached_anchor = json.loads(cache_path.read_text(encoding="ascii"))["anchor"]
   604	        if fragment.is_file():
   605	            saved = json.loads(fragment.read_text(encoding="ascii"))
   606	            if saved.get("run_digest") != run_digest:
   607	                raise RuntimeError(f"resume fragment input drift: {fragment}")
   608	            anchor, audit = saved["anchor"], saved["audit"]
   609	            print(
   610	                f"anchor {int(source['index']) + 1}/{len(sources)} resume-complete "
   611	                f"peak_rss_bytes={check_rss()}", flush=True,
   612	            )
   613	        else:
   614	            anchor, audit = build_anchor(
   615	                pilot=pilot, panelceil=panelceil, calibration=calibration, tape=tape,
   616	                source=source, widths=widths, reused=reused.get(int(source["index"])),
   617	                cached_anchor=cached_anchor,
   618	                total=len(sources),
   619	            )
   620	            atomic_json(fragment, {"run_digest": run_digest, "anchor": anchor, "audit": audit})
   621	        anchors.append(anchor)
   622	        audits.append(audit)
   623	
   624	    anchor_ids = [row["anchor_id"] for row in anchors]
   625	    dates = list(dict.fromkeys(str(row["date"])[:10] for row in anchors))
   626	    worlds = list(dict.fromkeys(str(row["world_id"]) for row in anchors))
   627	    seeds = list(dict.fromkeys(int(row["world_seed"]) for row in anchors))
   628	    smoke = checkpoint_digest == SMOKE_CHECKPOINT_SHA256
   629	    panel = {
   630	        "schema": PANEL_SCHEMA,
   631	        "panel_identity": {
   632	            "name": "EXACTGEN2 declared first-20 Stage-C scoring panel",
   633	            "information_class": (
   634	                "causal decision-instant exact C1/C2 and physical C3 state; outcomes and "
   635	                "reference endpoints use realised 48-boundary full-buffer evaluation"
   636	            ),
   637	            "estimand": (
   638	                "pooled sum(full-buffer decoded bits)/sum(modelled partial-payload DC "
   639	                "joules) over 48 realised boundaries, with operational co-metrics"
   640	            ),
   641	            "numerator": NUMERATOR, "energy_boundary": ENERGY_BOUNDARY,
   642	            "anchors": anchor_ids, "worlds": worlds, "dates": dates,
   643	            "world_seeds": seeds, "fixed_point_traversal_order": TRAVERSAL,
   644	            "provisioning_rule": (
   645	                "first min(20, available) authenticated exact-source anchors in global "
   646	                "generation order; per anchor, the deployed bounded-union-v2 catalogue "
   647	                "plus the two named reference profiles; base first then configuration-ID order"
   648	            ),
   649	        },
   650	        "reference_objects": {
   651	            "certified_fixed_point": {
   652	                "name": "offline certified guarded-F first-improvement fixed point",
   653	                "construction": (
   654	                    "exact realised boundary-0 deterministic cyclic first-improvement from "
   655	                    "the anchor base; complete no-strict-improvement terminal certificate"
   656	                ),
   657	                "information_class": "exact realised boundary-0 oracle; no future-boundary information",
   658	                "budget_s": None, "fixed_point_traversal_order": TRAVERSAL,
   659	            },
   660	            "anytime_incumbent": {
   661	                "name": "10 s anytime first-improvement incumbent",
   662	                "construction": (
   663	                    "last fully evaluated and accepted iterate no later than 10.0 seconds "
   664	                    "under the same ordered first-improvement traversal"
   665	                ),
   666	                "information_class": "exact realised boundary-0 oracle available by the 10 s checkpoint",
   667	                "budget_s": 10.0, "fixed_point_traversal_order": TRAVERSAL,
   668	            },
   669	        },
   670	        "coordinator_budget_s": 10.0,
   671	        "runner_instrumentation": {
   672	            "producer": str(Path(__file__).resolve()),
   673	            "physics_evaluations_per_arm_recorded": False,
   674	            "wall_clock_to_decision_per_arm_recorded": False,
   675	            "missing_fields_required_addition": (
   676	                "the five-arm online runner must record per-arm physics evaluations and "
   677	                "wall-clock time to committed decision; panel construction timings are not substitutes"
   678	            ),
   679	        },
   680	        "anchors": anchors, "synthetic_smoke_not_evidence": smoke,
   681	        "full_buffer_no_demand_cap": True,
   682	    }
   683	    atomic_json(args.output, panel)
   684	    panel_digest = sha256(args.output)
   685	    args.output.with_name(args.output.name + ".sha256").write_text(
   686	        f"{panel_digest}  {args.output.name}\n", encoding="ascii",
   687	    )
   688	    receipt = {
   689	        "schema": "mcrl-v025-panelbuild-receipt-v1", "panel": str(args.output.resolve()),
   690	        "panel_sha256": panel_digest, "anchor_count": len(anchors), "run_identity": run_identity,
   691	        "run_digest": run_digest, "audits": audits, "process_count": 1,
   692	        "nice": os.getpriority(os.PRIO_PROCESS, 0),
   693	        "thread_pins": {name: os.environ[name] for name in THREAD_VARIABLES},
   694	        "peak_rss_bytes": check_rss(), "synthetic_smoke_not_evidence": smoke,
   695	        "c3_encoding": {
   696	            "checkpoint_input_width": widths["C3"],
   697	            "member_width": widths["C3_MEMBER"],
   698	            "production_full_width": 240,
   699	            "global_resource_feature_prefix_count": widths["C3"] - 234,
   700	            "ordered_global_resource_features": [
   701	                "changed_user_fraction", "affected_beam_fraction",
   702	                "occupancy_before_per_user", "occupancy_after_per_user",
   703	                "pairwise_cross_gain_sum", "pairwise_cross_gain_max",
   704	            ],
   705	            "fixture_limitation": (
   706	                "the nominated synthetic smoke fixture owns only the first three ordered "
   707	                "global-resource features; this dry run is not deployable C3 evidence"
   708	                if smoke else None
   709	            ),
   710	        },
   711	    }
   712	    atomic_json(args.output.with_name(args.output.stem + ".receipt.json"), receipt)
   713	    if sha256(PILOT_PATH) != pilot_hash or sha256(PANELCEIL_PATH) != panelceil_hash:
   714	        raise RuntimeError("read-only source code changed during panel construction")
   715	    print(f"panel_sha256={panel_digest}", flush=True)
   716	    print(f"peak_rss_bytes={check_rss()} final", flush=True)
   717	    return 0
   718	
   719	
   720	if __name__ == "__main__":
   721	    raise SystemExit(main())
