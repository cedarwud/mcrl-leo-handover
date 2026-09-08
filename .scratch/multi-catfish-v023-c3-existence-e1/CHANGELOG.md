# E1 engineering changelog

## Fix pass 2 — Astra re-review items 4–7

- Item 4 — runtime bindings: record NumPy, PyTorch, and SGP4 versions; CPU
  model/core count/platform/machine/kernel; OMP, OpenBLAS, MKL, NumExpr, and
  effective torch thread settings; and the virtual-environment root,
  `pyvenv.cfg` path/digest, `sys.prefix`, and resolved interpreter. The server
  interpreter assertion is a mockable boundary.
- Item 5 — lifecycle: replace independent usage checks with a single locked
  57,600 worker-second ledger carrying visible reservations and exactly-once
  end charges. Unit, existing-unit verification, merge, and COMPLETE-terminal
  verification all reserve and charge. Resource/interruption exceptions during
  COMPLETE revalidation publish INCOMPLETE. Receipt and terminal files use
  same-directory staging plus interruption-safe atomic rename; abandoned stage
  paths are removed/ignored. Failures after a unit rename publish global
  invalidation. Unit and merge entry points refuse an existing global marker
  first and report its SHA-256.
- Item 6 — tests: cover two-worker reservations, mocked exact interruption
  charging, COMPLETE revalidation interruption and solver exhaustion,
  stage/rename interruption with clean resume, post-unit-rename invalidation,
  global-marker precedence, dominance changes observed through real solver
  iterations, runtime bindings, and host-portable interpreter mocking.
- Item 7 — seal tooling: add `build_e1_launch_authority.py`, which refuses
  overwrite, an unsealed/wrong contract, an absent or unsigned preflight, a
  noncanonical TLE root, and inconsistent launch argv. It emits only the exact
  validator key set plus an immutable `.sha256` sidecar. The round-trip test
  validates a built authority and rejects a sidecar-resealed mutation of every
  top-level field. README records the controller-contract → preflight → launch
  authority → dry-run → unit order.

Items 1–3 remain the accepted fix-pass-1 implementation. This pass changes no
scientific choice, panel, lineage, step/user count, keyed-field rule, tie rule,
catalog rule, or lambda/kappa role.
