# E1 engineering changelog

## Fix pass 4 — Astra R4 runtime-binding closure

- Replaced the `threadpoolctl`/`numpy.show_config()` acceptance fallback with
  `effective_thread_pools()`. It enumerates loaded files from
  `/proc/self/maps`, loads each recognised OpenBLAS, MKL, BLIS, GNU OpenMP,
  Intel OpenMP, or LLVM OpenMP runtime through `ctypes`, invokes its runtime
  thread-count getter, and binds its library kind, mapped path, file SHA-256,
  exact API symbol, and returned value.
- Runtime authentication now refuses when no BLAS/OpenMP pool can be inspected,
  when a recognised runtime cannot expose its required getter, or when any
  inspected pool differs from one. The existing environment and effective
  PyTorch thread checks remain fail-closed.
- `numpy.show_config()` text and digest remain in provenance with
  `acceptance_evidence: false`; build configuration never authenticates a live
  pool size. No `threadpoolctl` dependency was added.
- Added server-runtime evidence, missing-inspector refusal, ctypes pool-value
  refusal, and an isolated actual `torch.set_num_threads(1 -> 2 -> 1)`
  regression.

## Fix pass 3 — Astra R3 blocking items (a)–(d)

- Item (a) — runtime bindings: authenticate the declared one-thread process
  rule against every OpenMP/BLAS/NumExpr environment binding and PyTorch's
  effective intra-op and inter-op counts. When available, bind and enforce
  every effective BLAS/OpenMP count reported by `threadpoolctl`; otherwise
  bind the full `numpy.show_config()` evidence and its SHA-256 with the
  environment and effective PyTorch counts. Refuse any mismatch.
- Item (b) — budget: charge full nonnegative elapsed time even when it exceeds
  the reservation, retain an overdrawn ledger as valid exhausted evidence,
  and move merge settlement after terminal staging, atomic publication,
  immutable verification, and readback so publication time is charged.
- Item (c) — interruption coverage: catch interruption delivered while the
  unit or merge settlement mask is restored and publish an immutable
  INCOMPLETE receipt after the exactly-once ledger settlement.
- Item (d) — tests: replace the same-process reservation exercise with two
  parent-controlled competing processes that prove locked reservation
  visibility, exhausted-pool refusal, full elapsed charging, and exactly-once
  settlement. Add execute-unit interrupted-publication/resume coverage,
  unit/merge deferred-settlement interruption coverage, merge
  publication-time accounting, and runtime thread mismatch refusals.

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
