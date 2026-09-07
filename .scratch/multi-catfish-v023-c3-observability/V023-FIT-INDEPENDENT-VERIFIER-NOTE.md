# V0.23 independent fit-artifact verifier

Status: implemented as a non-heavy, read-only verification boundary.  The
verifier does not import the runner or any production source/fit/model code;
it uses only the Python standard library and NumPy.  It opens no simulator,
training loop, optimizer, TEST split, or scientific decision.

## Checks performed

`verify_v023_fit_artifact()` requires an explicit authenticated
`source-manifest.json` (and may also receive the exact eight source index
paths).  It verifies:

* canonical ASCII JSON, duplicate-key rejection, receipt seals, frozen schema,
  contract/preflight/claim-ceiling hashes, split flags, and the exact
  2026121705--2026121712 source panel;
* every source child byte hash and NPZ digest sidecar, array metadata,
  finite/non-object numeric content, exact nine phase identities, Q1+Q2/
  reference-action binding, pair identity/retention/class/32-draw means, and
  the authenticated source `SUPPORTED` cells.  When the production shard's
  optional world-local `placebo_strata` aggregate is present, its rows,
  cyclic mappings, counts, coverage, key, and content digest are rebuilt from
  those same S rows;
* exact held-out-world LOO membership, training/held-out anchor digests and
  order, and held-out metrics identity arrays.  The target vector is rebuilt
  from the authenticated source pair means, so a self-consistent replacement
  label still fails;
* model NPZ bytes, digest sidecar, fixed tensor metadata, finite numeric
  tensors, and no-pickle loading;
* metrics JSON/NPZ bytes and metadata, fixed identities, prediction/target
  arrays, held-out content digest, tie-aware Spearman, sign threshold and all
  denominators;
* the nested fit-receipt body and sidecar, exactly 2,000 finite losses,
  loss-array digest, source-anchor digest list, and arm-specific informed or
  matched-placebo target-source digest.  The target-source digest is bound to
  the authenticated surface digest (not the enclosing record digest), while
  identity and placebo receipts retain the enclosing record digest; and
* the nested placebo body and sidecar, fixed key/hash, fold-local world
  identities, deterministic within-world strata/cyclic mappings, coverage
  (at least 80%), target-array metadata, and no held-out target participation.

The companion W-199 tests use synthetic numeric artifacts and exercise model,
metrics, fit-receipt, and placebo tampering, arbitrary self-consistent labels,
held-out leakage, object dtype, and missing identity failures.  They run with:

```text
.venv/bin/python -m pytest -q tests/test_w199_ee_axis_lcsrs_fit_independent.py
```

## Exact unresolved gap (intentional fail-closed status)

The production model sidecar stores tensor bytes and a declared
`logical_network_sha256`, but does not serialize an independent, stdlib/NumPy
recomputable head algorithm/schema digest.  Recomputing that logical digest
would require reconstructing the typed production head and its hashing
contract, which this verifier is explicitly forbidden to import.  Therefore
the verifier only cross-binds the declared logical digest to the nested and
top-level receipts, sets `logical_network_hash_verified=false`, and returns
`FIT_ARTIFACT_VERIFIED_WITH_GAPS` with `gate_ready=false`; it never returns a
scientific or gate `PASS`.  A future schema must add an independently
specified parameter-name/order and hash-domain contract before this gap can be
closed.

Full-roster composition, physical mechanics, and final C3 decision arithmetic
remain outside the fit-artifact schema and are not inferred here.
