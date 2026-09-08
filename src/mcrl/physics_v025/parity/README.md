# V0.25 target parity integration

This package adapts the read-only V0.23 differential-audit suite from:

`/home/sat/mcrl-v023-codex-ws-bughunt/.scratch/multi-catfish-v023-differential-audit/target_parity_suite/`

Source SHA-256 values at integration time (2026-09-08):

- `declared_c3_oracle.py`: `de78ca61397b722f9c38b48b859576fd636fb04f094f97b62d461a6e545de128`
- `ops3_parity.py`: `693526370bcac6a6d4c4abaae10e2bb0051eb59eb8c6501ee34c2efd029f523f`
- `physics_extractor.py`: `debe48420bbd9a6809af553120babfd47c5991f787d5ef365dcfc24f7e42b6fd`
- `tests/test_target_parity.py`: `bf26eab44321cdd309a82527dc2215fd6f5898c4f4c9f0b4bcd23650a79db99a`

The V0.25 adaptation replaces NumPy/legacy imports with exact endpoint types,
requires explicit λ/η/κ at every producer, calls the production C3 formula for
cross-checking, and follows both additive and atomic decoder choices through
the same four physical endpoint profiles. It deliberately has no dependency
on `mcrl.env` and does not use the legacy `t3_energy` field.
