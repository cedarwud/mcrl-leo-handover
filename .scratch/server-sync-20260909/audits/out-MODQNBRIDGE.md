Implemented the option-independent MODQN bridge.

Headline finding: the V0.25 → legacy observation projection cannot be completed without invention. Only the 28 access fields are derivable; the remaining 84 SINR, angle, and prior-load fields require an owner-approved modeling choice.

Delivered:

- [Technical report](/home/sat/mcrl-v025-bridge-ws/MODQN-BRIDGE-2026-09-10.md:1)
- [Fail-closed bridge implementation](/home/sat/mcrl-v025-bridge-ws/src/modqn_bridge/bridge.py:1)
- [Test suite](/home/sat/mcrl-v025-bridge-ws/tests/test_modqn_bridge.py:1)

Verified:

- All 28 slot/physical-identity round trips are structurally exact.
- Every legal option in two production-shaped KAT rosters round-trips exactly.
- Missing observation fields and jointly invalid profiles fail closed.
- Legacy tie and empty-mask behavior matches the actual adapter.
- 11 tests passed in 0.91 seconds with one Python process and 620.78 MiB peak RSS.
- Checkpoint remained unchanged at SHA-256 `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.

No evaluator execution, training, EE calculation, claim, or protected-source modification was performed.
