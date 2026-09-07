# Vertical-slice rehearsal plan (engineering lane, 2026-09-07 14:40 UTC)

Owner's instruction (14:38 UTC): run the vertical slice first — find every problem that can occur up to and during
training by fast iteration, before any formal run. All slices are ENGINEERING LANE: `formal:false`, output roots named
`*REHEARSAL-NONFORMAL*`, claim ceiling `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`, never bound into any manifest,
never cited as evidence. Executed by operator sub-agents / server-side codex, never by the controller.

| # | slice | inputs | what it must expose | status |
|---|---|---|---|---|
| V1 | two-route rehearsal trainer on real r5/r6 shards, 3 → 10 epochs, export/reload/resume, per-phase timings | `/home/sat/mcrl-v023-real-shards-rehearsal` | adapter→provider→model→optimizer path on real rows; per-update / per-epoch cost | FAIL #1 (symlink guard) → fix dispatched → rerun |
| V2 | FULL formal stage-A chain on a scratch-sealed r8 root: offline postshard merge+seal of the 16 r8 staging shards into scratch → factory v3 → one-epoch diagnostic → formal two-route runner CLI 100 epochs → verify | r8 staging shards (as soon as all 16 `.complete.json` exist, before the official seal) | every formal consumer against the real r8 data; only the root digest differs from the formal launch | waits for 16/16 shards + blocker fixes |
| V3 | stage-B plumbing diagnostic with FRESH untrained two-route exports + BASELINE on the declared one world | TLE root, baseline adapter, successor model config | checkpoint schema round-trip, deployment rule, keyed field, TLE binding, baseline admission, 10-step timing | dispatch now (light) |
| V4 | stage-C four-arm physical runner, first 100 episodes + checkpoint + resume + rung receipt, fresh or V1 exports | world plan `866d28e0…`, baseline | τ per episode per arm, checkpoint/resume cadence, receipt shapes, RAM | after r8 shards finish (RAM) |
| V5 | interruption drills: kill the runner mid-epoch (stage A) and mid-episode (stage C), resume from the last checkpoint; verify exact continuation | V1/V4 roots | resume correctness, write-once collisions, marker handling | after V1/V4 pass |
| V6 | verify/sealer negatives: run the formal verifiers against the rehearsal roots and confirm they REJECT non-formal output; run them against a formal-shaped fixture and confirm PASS | launch bundle | verifier↔writer agreement before the formal run | after launch bundle lands |
| V7 | C3 contingency F1 tape generation + kill screen (science lane, cheap: one world, two steps) | F1 corrected package, frozen launch authority | D/F vs BASE on the shared tape | after F1 verification; needs its launch authority sealed first |

Rules: one corrected attempt per failure inside a slice without asking; consumer aligns to producer; every fix gets a
producer-derived test; failures are logged in the handoff report §16 with the minutes they cost.
