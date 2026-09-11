     1	#!/home/sat/mcrl-leo-handover/.venv/bin/python
     2	"""Derive the paired Q1-v3 control panel by an exact zero-coordinate transform."""
     3	
     4	from __future__ import annotations
     5	
     6	import argparse
     7	import hashlib
     8	import json
     9	import os
    10	from pathlib import Path
    11	import resource
    12	import sys
    13	
    14	
    15	ROOT = Path("/home/sat/mcrl-v025-panelv3-ws")
    16	PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
    17	CONTROL_CORPUS = Path(
    18	    "/home/sat/mcrl-v025-q1v3-ws/artifacts/"
    19	    "q1-v3-control-exact-label-corpus-20260910"
    20	)
    21	CONTROL_SCHEMA_SHA256 = "ee6baea90d824d52bfa1e7c3a775fa191235e6f6db9d85c32674c608740cfc8f"
    22	CONTROL_CORPUS_SHA256 = "cc2ebaa9bed84c0bac38dcdd7d9acce355176b265ae40ba841f89f96f8adc000"
    23	C3_GAIN_COORDINATES = (16, 32, 54, 70)
    24	THREAD_VARS = (
    25	    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    26	    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    27	)
    28	
    29	
    30	def sha256(path: Path) -> str:
    31	    digest = hashlib.sha256()
    32	    with path.open("rb") as handle:
    33	        for block in iter(lambda: handle.read(1 << 20), b""):
    34	            digest.update(block)
    35	    return digest.hexdigest()
    36	
    37	
    38	def canonical_sha256(value: object) -> str:
    39	    return hashlib.sha256(json.dumps(
    40	        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    41	    ).encode("ascii")).hexdigest()
    42	
    43	
    44	def write_json(path: Path, value: object) -> None:
    45	    path.parent.mkdir(parents=True, exist_ok=True)
    46	    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    47	    encoder = json.JSONEncoder(indent=2, sort_keys=True, allow_nan=False, ensure_ascii=True)
    48	    with temporary.open("x", encoding="ascii") as handle:
    49	        for chunk in encoder.iterencode(value):
    50	            handle.write(chunk)
    51	        handle.write("\n")
    52	        handle.flush()
    53	        os.fsync(handle.fileno())
    54	    temporary.replace(path)
    55	
    56	
    57	def verify_checkpoint(path: Path) -> None:
    58	    payload = json.loads(path.read_text(encoding="ascii"))
    59	    shapes = {
    60	        (
    61	            len(payload["arms"][arm]["C1"]["weights_hex"][0]),
    62	            len(payload["arms"][arm]["C2"]["weights_hex"][0]),
    63	            len(payload["arms"][arm]["C3"]["weights_hex"][0]),
    64	            payload["arms"][arm]["C3"]["member_width"],
    65	        )
    66	        for arm in payload["arms"]
    67	    }
    68	    if shapes != {(16, 22, 240, 38)}:
    69	        raise RuntimeError(f"control checkpoint shape drifted: {shapes}")
    70	
    71	
    72	def main() -> int:
    73	    parser = argparse.ArgumentParser()
    74	    parser.add_argument("--v3-panel", type=Path, required=True)
    75	    parser.add_argument("--v3-receipt", type=Path, required=True)
    76	    parser.add_argument("--control-checkpoint", type=Path, required=True)
    77	    parser.add_argument("--output", type=Path, required=True)
    78	    args = parser.parse_args()
    79	    if Path(sys.executable).resolve() != PYTHON.resolve():
    80	        raise RuntimeError("wrong interpreter")
    81	    if any(os.environ.get(name) != "1" for name in THREAD_VARS):
    82	        raise RuntimeError("thread pins drifted")
    83	    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
    84	        os.nice(16 - os.getpriority(os.PRIO_PROCESS, 0))
    85	    if os.getpriority(os.PRIO_PROCESS, 0) != 16:
    86	        raise RuntimeError("niceness drifted")
    87	    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    88	    cap = 4_900_000_000 if hard == resource.RLIM_INFINITY else min(hard, 4_900_000_000)
    89	    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    90	    if not args.output.resolve().is_relative_to(ROOT.resolve()):
    91	        raise RuntimeError("output outside PANELV3 workspace")
    92	    if args.output.exists():
    93	        raise RuntimeError(f"refusing to overwrite {args.output}")
    94	    verify_checkpoint(args.control_checkpoint)
    95	
    96	    panel = json.loads(args.v3_panel.read_text(encoding="ascii"))
    97	    changed_c1 = changed_c3 = 0
    98	    for index, anchor in enumerate(panel["anchors"], 1):
    99	        for profile in anchor["profiles"]:
   100	            for pair in profile["C1"]:
   101	                for side in ("reference", "selected"):
   102	                    if len(pair[side]) != 16:
   103	                        raise RuntimeError("Q1-v3 C1 width drifted")
   104	                    if pair[side][15] != 0.0:
   105	                        changed_c1 += 1
   106	                    pair[side][15] = 0.0
   107	            state = profile["C3"]["invariant_state"]
   108	            if len(state) != 240:
   109	                raise RuntimeError("Q1-v3 C3 width drifted")
   110	            for coordinate in C3_GAIN_COORDINATES:
   111	                if state[coordinate] != 0.0:
   112	                    changed_c3 += 1
   113	                state[coordinate] = 0.0
   114	        print(f"anchor {index}/20 control-coordinate-transform", flush=True)
   115	    if changed_c1 == 0 or changed_c3 == 0:
   116	        raise RuntimeError("informative and control panels are not scorer-visibly distinct")
   117	    panel["panel_identity"]["name"] = (
   118	        "panel-q1v3-control development first-20 Stage-C scoring panel"
   119	    )
   120	    panel["panel_identity"]["information_class"] += (
   121	        "; paired control replaces only decision_boundary_log_nominal_gain_db "
   122	        "with normalized literal 0.0"
   123	    )
   124	    write_json(args.output, panel)
   125	    panel_digest = sha256(args.output)
   126	    args.output.with_name(args.output.name + ".sha256").write_text(
   127	        f"{panel_digest}  {args.output.name}\n", encoding="ascii",
   128	    )
   129	
   130	    receipt = json.loads(args.v3_receipt.read_text(encoding="ascii"))
   131	    sources = receipt["run_identity"]["sources"]
   132	    for index, source in enumerate(sources):
   133	        view = (
   134	            CONTROL_CORPUS / "views/world-1"
   135	            / f"BUILD_NOT_CLAIM-exact-source-anchor-{index:03d}.jsonl"
   136	        )
   137	        digest = sha256(view)
   138	        sidecar = view.with_name(view.name + ".sha256").read_text(encoding="ascii").split()[0]
   139	        if digest != sidecar:
   140	            raise RuntimeError(f"control corpus sidecar mismatch at {index}")
   141	        source["view_path"] = str(view)
   142	        source["view_sha256"] = digest
   143	        source["state_view_schema"] = "v3_control"
   144	        source["q1_schema_sha256"] = CONTROL_SCHEMA_SHA256
   145	        receipt["audits"][index]["source"] = dict(source)
   146	    receipt["run_identity"]["checkpoint_sha256"] = sha256(args.control_checkpoint)
   147	    receipt["run_identity"]["control_corpus_sha256"] = CONTROL_CORPUS_SHA256
   148	    receipt["run_digest"] = canonical_sha256(receipt["run_identity"])
   149	    receipt["panel"] = str(args.output.resolve())
   150	    receipt["panel_sha256"] = panel_digest
   151	    receipt["encoder_binding"]["view"] = "v3_control"
   152	    receipt["encoder_binding"]["q1_schema_sha256"] = CONTROL_SCHEMA_SHA256
   153	    receipt["state_provenance"] = {
   154	        "authenticated_rows": (
   155	            "paired control corpus authenticated; first 15 Q1 coordinates retained "
   156	            "and the declared last coordinate is exactly normalized 0.0"
   157	        ),
   158	        "control_derivation": (
   159	            "exact scorer-visible transform of audited v3 panel: C1 slot 15 and "
   160	            "C3 pooled member slots 16,32,54,70 set to 0.0; no physical core changed"
   161	        ),
   162	        "fixture_state_values_surviving": 0,
   163	    }
   164	    receipt["adapter_chain"]["control_deriver"] = str(Path(__file__).resolve())
   165	    receipt["control_transform_counts"] = {
   166	        "nonzero_c1_coordinates_replaced": changed_c1,
   167	        "nonzero_c3_coordinates_replaced": changed_c3,
   168	    }
   169	    receipt_path = args.output.with_name(args.output.stem + ".receipt.json")
   170	    write_json(receipt_path, receipt)
   171	    print(f"panel_sha256={panel_digest}", flush=True)
   172	    print(f"PEAK_RSS_BYTES={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}", flush=True)
   173	    return 0
   174	
   175	
   176	if __name__ == "__main__":
   177	    raise SystemExit(main())
