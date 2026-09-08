# Target parity suite

Read-only successor checks with no V0.23 type dependency at import time:

- `build_ops3_surface_explicit` makes the calibration multiplier mandatory;
- `declared_c3_oracle` evaluates only the atomic `00/10/01/11` catalogue;
- `PhysicsSnapshotExtractor` captures physics/fading without changing results;
- `assert_reward_endpoint_identity` checks `sum reward = B - eta*E`.

Add this audit directory to `PYTHONPATH`, then import `target_parity_suite` from
the V0.25 engine. The V0.23 OPS-3 implementation is imported lazily only when
the explicit wrapper is called without an injected successor `builder`.
