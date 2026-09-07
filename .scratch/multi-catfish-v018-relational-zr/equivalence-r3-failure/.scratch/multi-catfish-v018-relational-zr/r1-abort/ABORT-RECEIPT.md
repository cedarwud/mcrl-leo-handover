# V0.18 R1 performance-abort receipt

Status: `ABORTED_PERFORMANCE_NO_RESULT`

- Server root: `/home/sat/mcrl-v018-relational-zr-20260904-r1`
- tmux session: `v018-analytic`
- Session created: `2026-09-03 18:02:14 UTC`
- Shard logs created: `2026-09-03 18:02:16 UTC`
- Terminated: `2026-09-03 19:08:51 UTC`
- Approximate live duration: 66 minutes 37 seconds
- Processes before termination: 18 runnable shard workers, each at about one
  CPU core
- Completed `shard.json` files before termination: 0
- Shard log files: 18, each exactly 0 bytes
- `result.json`: absent
- `result-seal.json`: absent
- `controller.complete`: absent
- Matching shard processes after termination: 0
- Server root deleted or overwritten: no

Authenticated server bytes before termination:

- `src/mcrl/runtime/ee_axis_relational_zr_c3.py`:
  `6a3d61940175f0e4e422fa4ac9818fd64652dd4f6e699408f6189cec164425a2`
- `.scratch/multi-catfish-v018-relational-zr/contracts/code-manifest.sha256`:
  `b6d6b1169c8d0aaf02eb7d7051a5e88bd2aec60536904e964eba540134c37fb3`
- `server-preflight.log`:
  `7fe332f0e642c5eb091cce747fd2e62dac4f4d8129b532654c77107807ac8524`

The session was stopped solely because a pre-result performance diagnosis
showed that R1 rebuilt complete network interference for every branch.  No
endpoint, action trace, partial shard receipt, sign, or scientific result was
available or used to choose the replacement implementation.  R1 is not a
failed C3 experiment and none of its files may be merged with R2.
