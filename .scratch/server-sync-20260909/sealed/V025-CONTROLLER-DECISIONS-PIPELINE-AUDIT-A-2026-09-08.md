# V025 — controller decisions on pipeline audit A (worlds, splits, seeds, panels) (2026-09-08 ≈ 18:25 UTC)

1. Date-fresh claim panel: v1.5 §4 (role-wise date reservation; legacy overlap recorded).
2. Cluster key and crossed dependence: separate `world_seed` / `learner_seed`; two-way pigeonhole bootstrap primary (v1.5 §3); worlds pooled within a cell.
3. Provider/tape seam attestation: split identity, start UTC, TLE hashes, split-rule digest, provider digest are protocol outputs; no hardcoded `TRAIN`; verified before units open (stage 4b item 5).
4. TEST never read: a shared world factory is the only production entry point for successor runners; every realised start date and opened TLE file is recorded and checked against the split.
5. TLE nearest-epoch convention: retained and documented as non-causal benchmark convention (v1.5 §5).
6. D2 prime seam: the provider fix pass carries the forward-tape seam KAT; the successor's D2 state at the decision instant comes from the legacy backward history (provider decision item 7/window direction).
7. World identity: the allocation manifest records start UTC, layout digest, mobility/fading stream identities, TLE hashes, split, role, learner seed, world seed.
8. N = 4 refresh cadence only: confirmed (cadence audit + audit A); documented in the system model.
9. UTC/frame approximations: bounded once in the provider report (`VERIFY_SOURCE`).
