# V0.23 R7 final-verifier inventory

This directory contains a read-only diagnostic harness for the frozen R7 final
verifier. It is **not a repair, seal, verification receipt, or verdict
authority**. The harness never writes to the run root or checkout. Its only
outputs are `inventory.json` and `inventory.json.sha256` in a new, absent
`--output` directory outside the run root.

Before loading code, the harness requires these byte identities:

- frozen verifier: `3cc573717f010d8b67ede027d05ef79f4c69497e9654d6766df50e88e9aa4717`;
- frozen R3 adapter: `7d242eb2ca31835ba2471334b7ab90f8d68f4c817a367a5f3f2c72fb518fff2d`.

It imports and reuses the R3 adapter's `_load_original()`,
`_install_domain_dispatch(module)`, `_install_pair_profile_broadcast(module)`,
and `_temporary_import_path(dir)` implementations. The frozen source files are
never rewritten. The following named validators alone receive an in-memory AST
record transform. Each matching verifier-error raise is replaced by a recorder
call; loop iterations and single-generator dictionary comprehensions capture
cascade exceptions so later shards or identities still run:

- `_authenticate_launch_manifest`: 5 raise sites;
- `_read_manifest`: 9 raise sites;
- `_source_raw_identity`: 2 raise sites;
- `_verify_composition_shard`: 5 raise sites;
- `_validate_composition_arrays`: 34 raise sites;
- `_validate_ratio_arrays`: 3 raise sites;
- `_join_composition_source`: 8 raise sites;
- `_fit_panel_metrics`: 7 raise sites;
- `_composition_metrics`: 1 raise site;
- `_context_status`: 7 raise sites;
- `verify_cross_arm_identity`: 4 raise sites;
- `verify_v023_final_gate`: 17 raise sites;
- `verify_source_world_science`: 23 raise sites;
- `verify_source_panel_science`: 2 raise sites;
- `verify_fit_science`: 14 raise sites;
- `verify_v023_fit_artifact`: 12 raise sites.

Every finding records its stage (`source`, `fit`, `composition`,
`identity_join`, or `decision`), shard/path identity, message, and whether it
is a primary verifier message or a cascade exception. The report also records
the expected/actual source and composition NPZ dispatch counts (8 and 48) and
the array-name sets from the first loaded source and composition NPZ files.
The transformed top-level verifier is invoked exactly once with the real panel
paths. Successful calls and shard failures reached there are memoized; after a
cascade, as-yet-unreached shard validators run, and a failed aggregate may be
retried after shard coverage is complete. Any top-level return is explicitly
non-authoritative. The harness does not change a threshold, predicate,
decision function, or verdict.

The controller—not this local preparation session—may run the server command:

```bash
/home/sat/mcrl-leo-handover/.venv/bin/python /home/sat/mcrl-v023-r7-launch-ready-20260906-r4/.scratch/multi-catfish-v023-r7-final-verifier-inventory/inventory_v023_lcsrs_final_verifier.py --run-root /home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1 --checkout /home/sat/mcrl-v023-r7-launch-ready-20260906-r4 --output /home/sat/mcrl-v023-r7-final-verifier-inventory-20260907
```

At startup the script inserts
`<checkout>/src` at the front of `sys.path` before any verifier import that
could resolve `mcrl`, avoiding the server virtual environment's stale editable
install.

Run only the focused local tests with bytecode and pytest cache writes disabled:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest -p no:cacheprovider -q .scratch/multi-catfish-v023-r7-final-verifier-inventory/test_inventory_v023_lcsrs_final_verifier.py
```
