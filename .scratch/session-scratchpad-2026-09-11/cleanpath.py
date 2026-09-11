     1	#!/usr/bin/env python3
     2	"""Rebuild the frozen six-arm static family on dense-only evaluator paths.
     3	
     4	Selection: each search arm gets one fresh boundary-0 StepEvaluator.  BASE is
     5	dense-populated through evaluate_many before any profile is read, and all
     6	candidates use that same evaluator.  Endpoints: all six selected profiles enter one separate fresh realised
     7	full-48 evaluate_many call per anchor.  Scalar StepEvaluator.evaluate is
     8	replaced by a fail-closed assertion for the whole measured surface.
     9	"""
    10	
    11	from __future__ import annotations
    12	
    13	from collections import Counter
    14	from fractions import Fraction
    15	import gc
    16	import hashlib
    17	import importlib.util
    18	import json
    19	import math
    20	import os
    21	from pathlib import Path
    22	import random
    23	import resource
    24	import sys
    25	import time
    26	
    27	
    28	WORKSPACE = Path("/home/sat/mcrl-v025-rank2-ws")
    29	PANEL_RUNNER = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/run_panelceil.py")
    30	PANEL_RECEIPT = Path("/home/sat/mcrl-v025-ceiling30-ws/.scratch/panelceil/panelceil-receipt.json")
    31	PUBLISHED_RECEIPT = Path("/home/sat/mcrl-v025-rank-ws/.scratch/statics/statics-receipt.json")
    32	OUTPUT = WORKSPACE / ".scratch/cleanpath/cleanpath-receipt.json"
    33	PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
    34	THREAD_VARS = (
    35	    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    36	    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    37	)
    38	MAX_RSS_BYTES = 5_000_000_000
    39	RANDOM_SEED = 20260910
    40	ARM_NAMES = (
    41	    "RANDOM", "ROUND_ROBIN", "RSS_MAX", "NEAREST_ELIGIBLE",
    42	    "MYOPIC_GREEDY", "FIRST_IMPROVEMENT_FP",
    43	)
    44	SEARCH_ARMS = ("MYOPIC_GREEDY", "FIRST_IMPROVEMENT_FP")
    45	PUBLISHED_EE_MBIT_J = {
    46	    "RANDOM": 11.233999,
    47	    "ROUND_ROBIN": 3.441227,
    48	    "RSS_MAX": 41.621560,
    49	    "NEAREST_ELIGIBLE": 11.027760,
    50	    "MYOPIC_GREEDY": 28.668530,
    51	    "FIRST_IMPROVEMENT_FP": 13.430253,
    52	}
    53	SCALAR_EVALUATE_CALLS = 0
    54	
    55	
    56	def sha256(path: Path) -> str:
    57	    digest = hashlib.sha256()
    58	    with path.open("rb") as handle:
    59	        for block in iter(lambda: handle.read(1024 * 1024), b""):
    60	            digest.update(block)
    61	    return digest.hexdigest()
    62	
    63	
    64	def canonical_digest(payload: dict) -> str:
    65	    unsigned = dict(payload)
    66	    unsigned.pop("receipt_sha256", None)
    67	    return hashlib.sha256(json.dumps(
    68	        unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False,
    69	    ).encode("utf-8")).hexdigest()
    70	
    71	
    72	def atomic_write(payload: dict) -> None:
    73	    payload["receipt_sha256"] = canonical_digest(payload)
    74	    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    75	    temporary = OUTPUT.with_name(f".{OUTPUT.name}.{os.getpid()}.tmp")
    76	    temporary.write_text(
    77	        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
    78	        encoding="utf-8",
    79	    )
    80	    temporary.replace(OUTPUT)
    81	
    82	
    83	def peak_rss_bytes() -> int:
    84	    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    85	
    86	
    87	def check_runtime() -> None:
    88	    if sys.executable != PYTHON:
    89	        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    90	    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
    91	        raise RuntimeError("niceness is below 15")
    92	    bad = {name: os.environ.get(name) for name in THREAD_VARS if os.environ.get(name) != "1"}
    93	    if bad:
    94	        raise RuntimeError(f"thread pins are not all one: {bad}")
    95	    if peak_rss_bytes() >= MAX_RSS_BYTES:
    96	        raise MemoryError(f"peak RSS {peak_rss_bytes()} is not below 5 GB")
    97	
    98	
    99	def load_panel():
   100	    name = "cleanpath_panelceil_reference"
   101	    spec = importlib.util.spec_from_file_location(name, PANEL_RUNNER)
   102	    if spec is None or spec.loader is None:
   103	        raise RuntimeError("cannot load PANELCEIL runner")
   104	    module = importlib.util.module_from_spec(spec)
   105	    sys.modules[name] = module
   106	    spec.loader.exec_module(module)
   107	    return module
   108	
   109	
   110	def forbid_scalar_evaluate(runner) -> None:
   111	    """Fail the run if any code on the measured surface calls scalar evaluate."""
   112	    original = runner.StepEvaluator.evaluate
   113	
   114	    def forbidden(*args, **kwargs):
   115	        del args, kwargs
   116	        global SCALAR_EVALUATE_CALLS
   117	        SCALAR_EVALUATE_CALLS += 1
   118	        raise AssertionError("scalar StepEvaluator.evaluate is forbidden on clean path")
   119	
   120	    forbidden.__name__ = "scalar_evaluate_forbidden_on_clean_path"
   121	    forbidden.__wrapped__ = original
   122	    runner.StepEvaluator.evaluate = forbidden
   123	    assert runner.StepEvaluator.evaluate is forbidden
   124	
   125	
   126	def fresh_evaluator(runner, tape, step_index, incumbent, run_setting, field, boundaries):
   127	    return runner.StepEvaluator(
   128	        tape, runner._setting("a-r0"), step_index,
   129	        transition_from=incumbent,
   130	        cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
   131	        field=field, counter=runner.EvaluationCounter(),
   132	        run_setting=run_setting, boundary_indices=boundaries,
   133	    )
   134	
   135	
   136	def configured(runner, base, mapping, kind: str):
   137	    return runner._configuration(base, mapping, kind=kind)
   138	
   139	
   140	def random_configuration(runner, tape, step_index: int, base, anchor_index: int):
   141	    options, _ = runner._legal_options(tape, step_index)
   142	    rng = random.Random(RANDOM_SEED + anchor_index)
   143	    mapping = {
   144	        user: (None if not identities else identities[rng.randrange(len(identities))])
   145	        for user, identities in sorted(options.items())
   146	    }
   147	    return configured(runner, base, mapping, "cleanpath-random")
   148	
   149	
   150	def round_robin_configuration(runner, tape, step_index: int, base):
   151	    options, _ = runner._legal_options(tape, step_index)
   152	    loads: Counter[tuple[int, int]] = Counter()
   153	    mapping = {}
   154	    for user, identities in sorted(options.items()):
   155	        if not identities:
   156	            mapping[user] = None
   157	            continue
   158	        _, identity = min(
   159	            enumerate(identities), key=lambda item: (loads[item[1]], item[0])
   160	        )
   161	        mapping[user] = identity
   162	        loads[identity] += 1
   163	    return configured(runner, base, mapping, "cleanpath-round-robin")
   164	
   165	
   166	def rss_max_configuration(runner, tape, step_index: int, base):
   167	    options, _ = runner._legal_options(tape, step_index)
   168	    arrays = tape.steps[step_index].arrays
   169	    if arrays is None:
   170	        raise RuntimeError("frozen exact panel must expose primitive arrays")
   171	    row_of = arrays._row_index()
   172	    mapping = {}
   173	    for user, identities in sorted(options.items()):
   174	        if not identities:
   175	            mapping[user] = None
   176	            continue
   177	        _, identity = min(
   178	            enumerate(identities),
   179	            key=lambda item: (
   180	                -float(arrays.nominal_gain[0, row_of[(user, item[1])]]), item[0]
   181	            ),
   182	        )
   183	        mapping[user] = identity
   184	    return configured(runner, base, mapping, "cleanpath-rss-max")
   185	
   186	
   187	def dense_search(panel, runner, calibration, tape, step_index, base, incumbent,
   188	                 run_setting, *, field: str, rule: str, converged: bool, kind: str):
   189	    """Run one search arm using only one fresh dense boundary-0 evaluator."""
   190	    evaluator = fresh_evaluator(
   191	        runner, tape, step_index, incumbent, run_setting, field, (0,)
   192	    )
   193	    options, census = runner._legal_options(tape, step_index)
   194	    rekeys = runner._rekeyed_users(tape, step_index)
   195	
   196	    # BASE enters through the same dense-only evaluator as every candidate.
   197	    # Populate it before the first read while preserving the frozen candidate
   198	    # microbatch shape exactly; this is the established SURFACE clean path.
   199	    evaluator.evaluate_many((base,))
   200	    base_profile = evaluator._evaluated.get(base.configuration_id)
   201	    if base_profile is None:
   202	        raise RuntimeError("dense BASE is invalid")
   203	    guard = panel.served(base_profile)
   204	
   205	    current = base
   206	    passes = moves = comparisons = submitted = 0
   207	    started = time.perf_counter()
   208	    while True:
   209	        moves_this_pass = 0
   210	        for user in sorted(options):
   211	            current_profile = evaluator._evaluated.get(current.configuration_id)
   212	            if current_profile is None:
   213	                raise RuntimeError("current profile absent from dense cache")
   214	            current_value: Fraction = panel.objective(
   215	                runner, calibration, incumbent, current, current_profile, rekeys
   216	            )
   217	            candidates = tuple(
   218	                panel.candidate(runner, base, current, user, identity, kind)
   219	                for identity in options[user]
   220	                if identity != current.mapping[user]
   221	            )
   222	            accepted = None
   223	            if rule == "first":
   224	                for offset in range(0, len(candidates), panel.UNILATERAL_BATCH_SIZE):
   225	                    batch = candidates[offset:offset + panel.UNILATERAL_BATCH_SIZE]
   226	                    evaluator.evaluate_many(batch)
   227	                    submitted += len(batch)
   228	                    for row in batch:
   229	                        comparisons += 1
   230	                        profile = evaluator._evaluated.get(row.configuration_id)
   231	                        if profile is None or panel.served(profile) < guard:
   232	                            continue
   233	                        value = panel.objective(
   234	                            runner, calibration, incumbent, row, profile, rekeys
   235	                        )
   236	                        if value > current_value:
   237	                            accepted = row
   238	                            break
   239	                    if accepted is not None:
   240	                        break
   241	            elif rule == "best":
   242	                for offset in range(0, len(candidates), panel.UNILATERAL_BATCH_SIZE):
   243	                    batch = candidates[offset:offset + panel.UNILATERAL_BATCH_SIZE]
   244	                    evaluator.evaluate_many(batch)
   245	                    submitted += len(batch)
   246	                eligible = [(current_value, current.configuration_id, current)]
   247	                for row in candidates:
   248	                    comparisons += 1
   249	                    profile = evaluator._evaluated.get(row.configuration_id)
   250	                    if profile is None or panel.served(profile) < guard:
   251	                        continue
   252	                    value = panel.objective(
   253	                        runner, calibration, incumbent, row, profile, rekeys
   254	                    )
   255	                    eligible.append((value, row.configuration_id, row))
   256	                selected = min(eligible, key=lambda item: (-item[0], item[1]))[2]
   257	                if selected.mapping[user] != current.mapping[user]:
   258	                    accepted = selected
   259	            else:
   260	                raise ValueError(rule)
   261	            if accepted is not None:
   262	                current = accepted
   263	                moves += 1
   264	                moves_this_pass += 1
   265	        passes += 1
   266	        if not converged or moves_this_pass == 0:
   267	            break
   268	        if passes > 100:
   269	            raise RuntimeError("search exceeded 100 passes")
   270	
   271	    detail = {
   272	        "field": field,
   273	        "rule": rule,
   274	        "passes_mode": "converged" if converged else "one",
   275	        "moves": moves,
   276	        "passes_including_certificate": passes,
   277	        "guard": guard,
   278	        "comparisons": comparisons,
   279	        "submitted_candidate_slots": submitted,
   280	        "legal_option_census": census,
   281	        "selection_seconds": time.perf_counter() - started,
   282	        "base_entered_dense_before_candidates_in_same_evaluator": True,
   283	        "scalar_evaluate_calls": SCALAR_EVALUATE_CALLS,
   284	        "physical_boundary_evaluations": evaluator.physical_evaluations,
   285	    }
   286	    del evaluator
   287	    gc.collect()
   288	    return current, detail
   289	
   290	
   291	def diversity(config, options) -> dict[str, float | int]:
   292	    chosen = [identity for identity in config.mapping.values() if identity is not None]
   293	    counts = Counter(chosen)
   294	    user_count = len(config.mapping)
   295	    ordinals = []
   296	    for user, identity in sorted(config.mapping.items()):
   297	        if identity is not None:
   298	            ordinals.append(options[user].index(identity))
   299	    return {
   300	        "modal_frac": 0.0 if not counts else max(counts.values()) / user_count,
   301	        "active_beams": len(counts),
   302	        "active_satellites": len({identity[0] for identity in counts}),
   303	        "argmax_distinct": len(set(ordinals)),
   304	        "assigned_users": len(chosen),
   305	        "user_count": user_count,
   306	    }
   307	
   308	
   309	def endpoint_metrics(panel, runner, tape, step_index, incumbent, run_setting, configs):
   310	    """One fresh full-48 realised evaluator and one batch call for all six arms."""
   311	    evaluator = fresh_evaluator(
   312	        runner, tape, step_index, incumbent, run_setting,
   313	        "realised", tuple(range(48)),
   314	    )
   315	    evaluator.evaluate_many(tuple(configs[name] for name in ARM_NAMES))
   316	    result = {}
   317	    for name in ARM_NAMES:
   318	        config = configs[name]
   319	        profile = evaluator._evaluated.get(config.configuration_id)
   320	        if profile is None:
   321	            raise RuntimeError(f"invalid committed config for {name}")
   322	        result[name] = panel.metric(profile)
   323	    del evaluator
   324	    gc.collect()
   325	    return result
   326	
   327	
   328	def summarize(values):
   329	    return {
   330	        "mean": math.fsum(values) / len(values),
   331	        "min": min(values),
   332	        "max": max(values),
   333	    }
   334	
   335	
   336	def pool(anchors, arm: str) -> dict[str, object]:
   337	    rows = [anchor["arms"][arm]["committed"] for anchor in anchors]
   338	    bits = math.fsum(float(row["bits"]) for row in rows)
   339	    joules = math.fsum(float(row["joules"]) for row in rows)
   340	    diversities = [anchor["arms"][arm]["diversity"] for anchor in anchors]
   341	    return {
   342	        "bits": bits,
   343	        "joules": joules,
   344	        "ee_mbit_per_j": bits / joules / 1e6,
   345	        "served_count": sum(int(row["served_count"]) for row in rows),
   346	        "rate_target_attained_count": sum(
   347	            int(row["rate_target_attained_count"]) for row in rows
   348	        ),
   349	        "user_count": sum(int(row["user_count"]) for row in rows),
   350	        "modal_frac": summarize([float(row["modal_frac"]) for row in diversities]),
   351	        "active_beams": summarize([float(row["active_beams"]) for row in diversities]),
   352	        "active_satellites": summarize([
   353	            float(row["active_satellites"]) for row in diversities
   354	        ]),
   355	        "argmax_distinct": summarize([
   356	            float(row["argmax_distinct"]) for row in diversities
   357	        ]),
   358	    }
   359	
   360	
   361	def published_search_counts(published_anchor: dict, arm: str) -> tuple[int, int]:
   362	    detail = published_anchor["arms"][arm]["detail"]
   363	    if arm == "MYOPIC_GREEDY":
   364	        return int(detail["users_changing_choice"]), 1
   365	    return int(detail["accepted_moves"]), int(detail["total_passes_including_certificate"])
   366	
   367	
   368	def main() -> int:
   369	    check_runtime()
   370	    overall_started = time.perf_counter()
   371	    panel = load_panel()
   372	    panel_receipt = json.loads(PANEL_RECEIPT.read_text(encoding="utf-8"))
   373	    published = json.loads(PUBLISHED_RECEIPT.read_text(encoding="utf-8"))
   374	    frozen = published.get("panel")
   375	    if not isinstance(frozen, list) or len(frozen) != 12:
   376	        raise RuntimeError("published receipt does not contain the 12 frozen anchors")
   377	    if panel_receipt.get("status") != "COMPLETE":
   378	        raise RuntimeError("PANELCEIL receipt is not complete")
   379	    if published.get("status") != "COMPLETE":
   380	        raise RuntimeError("published static receipt is not complete")
   381	    if panel_receipt.get("receipt_sha256") != panel.canonical_digest(panel_receipt):
   382	        raise RuntimeError("PANELCEIL receipt digest failed")
   383	    if published.get("receipt_sha256") != canonical_digest(published):
   384	        raise RuntimeError("published static receipt digest failed")
   385	
   386	    pilot = panel.load_pilot()
   387	    runner = pilot.ENGINE
   388	    calibration = panel.load_calibration(pilot)
   389	    run_setting = runner.run_setting_for("a-r0")
   390	    forbid_scalar_evaluate(runner)
   391	    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
   392	    from mcrl.physics_v025.tapes import build_world_tape
   393	
   394	    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB before tape", flush=True)
   395	    tape_started = time.perf_counter()
   396	    tape = build_world_tape(
   397	        domain=pilot.TRAIN_WORLDS[0], provider=LegacyWorldProvider(role="pilot-source"),
   398	        steps=33, start_time_s=0.0,
   399	    )
   400	    tape_seconds = time.perf_counter() - tape_started
   401	    check_runtime()
   402	    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB after tape", flush=True)
   403	
   404	    payload = {
   405	        "schema": "mcrl-v025-static-baseline-family-cleanpath-v1",
   406	        "status": "RUNNING",
   407	        "claim_status": "DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM",
   408	        "panel": frozen,
   409	        "panel_count": len(frozen),
   410	        "panel_enumeration": "12 frozen declarations from digest-checked published receipt; transient staging paths not read",
   411	        "panel_runner_sha256": sha256(PANEL_RUNNER),
   412	        "panel_receipt_sha256": panel_receipt["receipt_sha256"],
   413	        "published_receipt_file_sha256": sha256(PUBLISHED_RECEIPT),
   414	        "published_receipt_sha256": published["receipt_sha256"],
   415	        "runner_sha256": None,
   416	        "world_tape": {
   417	            "domain": tape.domain, "seed": tape.seed, "digest": tape.digest,
   418	            "construction_seconds": tape_seconds,
   419	        },
   420	        "python": sys.executable,
   421	        "niceness": os.getpriority(os.PRIO_PROCESS, 0),
   422	        "process_count": 1,
   423	        "thread_pins": {name: os.environ[name] for name in THREAD_VARS},
   424	        "random_seed": RANDOM_SEED,
   425	        "selection_path": {
   426	            "evaluator": "fresh StepEvaluator(field per arm, boundary_indices=(0,))",
   427	            "population": "one evaluate_many-only cache; BASE is populated before reads, then candidates use the same evaluator",
   428	            "profile_reads": "StepEvaluator._evaluated after dense population",
   429	            "scalar_evaluate_fail_closed": True,
   430	        },
   431	        "endpoint_path": {
   432	            "evaluator": "one separate fresh realised StepEvaluator(boundary_indices=range(48)) per anchor",
   433	            "population": "one evaluate_many call containing all six selected profiles",
   434	        },
   435	        "anchors": [],
   436	    }
   437	
   438	    for position, panel_row in enumerate(frozen, 1):
   439	        index = int(panel_row["global_anchor_index"])
   440	        step_index = int(panel_row["step_index"])
   441	        carrier = str(panel_row["carrier"])
   442	        base = runner._base_configuration(tape, step_index, carrier)
   443	        incumbent = runner._base_configuration(tape, max(0, step_index - 1), carrier)
   444	        options, _ = runner._legal_options(tape, step_index)
   445	        configs = {
   446	            "NEAREST_ELIGIBLE": base,
   447	            "RANDOM": random_configuration(runner, tape, step_index, base, index),
   448	            "ROUND_ROBIN": round_robin_configuration(runner, tape, step_index, base),
   449	            "RSS_MAX": rss_max_configuration(runner, tape, step_index, base),
   450	        }
   451	        details = {}
   452	        configs["MYOPIC_GREEDY"], details["MYOPIC_GREEDY"] = dense_search(
   453	            panel, runner, calibration, tape, step_index, base, incumbent, run_setting,
   454	            field="nominal", rule="best", converged=False,
   455	            kind="cleanpath-myopic-greedy",
   456	        )
   457	        configs["FIRST_IMPROVEMENT_FP"], details["FIRST_IMPROVEMENT_FP"] = dense_search(
   458	            panel, runner, calibration, tape, step_index, base, incumbent, run_setting,
   459	            field="realised", rule="first", converged=True,
   460	            kind="cleanpath-first-improvement",
   461	        )
   462	        committed = endpoint_metrics(
   463	            panel, runner, tape, step_index, incumbent, run_setting, configs
   464	        )
   465	        published_anchor = published["anchors"][index]
   466	        arms = {}
   467	        for name in ARM_NAMES:
   468	            published_id = published_anchor["arms"][name]["configuration_id"]
   469	            arm = {
   470	                "selection_evaluator_touched": name in SEARCH_ARMS,
   471	                "configuration_id": configs[name].configuration_id,
   472	                "published_configuration_id": published_id,
   473	                "configuration_matches_published": configs[name].configuration_id == published_id,
   474	                "committed": committed[name],
   475	                "diversity": diversity(configs[name], options),
   476	            }
   477	            if name in SEARCH_ARMS:
   478	                published_moves, published_passes = published_search_counts(
   479	                    published_anchor, name
   480	                )
   481	                arm["selection"] = details[name]
   482	                arm["published_moves"] = published_moves
   483	                arm["published_passes_including_certificate"] = published_passes
   484	            arms[name] = arm
   485	        payload["anchors"].append({
   486	            "global_anchor_index": index,
   487	            "anchor_id": f"{panel_row['world_id']}|{step_index}|{carrier}",
   488	            "step_index": step_index,
   489	            "carrier": carrier,
   490	            "arms": arms,
   491	            "peak_rss_bytes": peak_rss_bytes(),
   492	        })
   493	        payload["pooled"] = {arm: pool(payload["anchors"], arm) for arm in ARM_NAMES}
   494	        payload["peak_rss_bytes"] = peak_rss_bytes()
   495	        check_runtime()
   496	        atomic_write(payload)
   497	        print(
   498	            f"anchor {position}/{len(frozen)} completed peak RSS "
   499	            f"{peak_rss_bytes()/2**30:.3f} GiB "
   500	            + json.dumps({
   501	                "global": index,
   502	                "myopic_moves": details["MYOPIC_GREEDY"]["moves"],
   503	                "fp_moves": details["FIRST_IMPROVEMENT_FP"]["moves"],
   504	                "fp_passes": details["FIRST_IMPROVEMENT_FP"]["passes_including_certificate"],
   505	            }, sort_keys=True),
   506	            flush=True,
   507	        )
   508	
   509	    payload["pooled"] = {arm: pool(payload["anchors"], arm) for arm in ARM_NAMES}
   510	    payload["published_comparison"] = {
   511	        arm: {
   512	            "published_rounded_6_mbit_per_j": PUBLISHED_EE_MBIT_J[arm],
   513	            "published_receipt_mbit_per_j": float(published["pooled"][arm]["ee_bit_per_j"]) / 1e6,
   514	            "clean_mbit_per_j": float(payload["pooled"][arm]["ee_mbit_per_j"]),
   515	            "clean_minus_published_receipt_mbit_per_j": (
   516	                float(payload["pooled"][arm]["ee_mbit_per_j"])
   517	                - float(published["pooled"][arm]["ee_bit_per_j"]) / 1e6
   518	            ),
   519	            "configuration_ids_matching": sum(
   520	                bool(row["arms"][arm]["configuration_matches_published"])
   521	                for row in payload["anchors"]
   522	            ),
   523	        }
   524	        for arm in ARM_NAMES
   525	    }
   526	    payload["scalar_evaluate_calls"] = SCALAR_EVALUATE_CALLS
   527	    assert SCALAR_EVALUATE_CALLS == 0
   528	    payload["status"] = "COMPLETE"
   529	    payload["peak_rss_bytes"] = peak_rss_bytes()
   530	    payload["wall_seconds"] = time.perf_counter() - overall_started
   531	    payload["runner_sha256"] = sha256(Path(__file__))
   532	    atomic_write(payload)
   533	    check_runtime()
   534	    print(f"peak RSS {peak_rss_bytes()/2**30:.3f} GiB final ({peak_rss_bytes()} bytes)", flush=True)
   535	    print(json.dumps({
   536	        arm: payload["pooled"][arm]["ee_mbit_per_j"] for arm in ARM_NAMES
   537	    }, sort_keys=True), flush=True)
   538	    print(f"scalar_evaluate_calls={SCALAR_EVALUATE_CALLS}", flush=True)
   539	    return 0
   540	
   541	
   542	if __name__ == "__main__":
   543	    raise SystemExit(main())
