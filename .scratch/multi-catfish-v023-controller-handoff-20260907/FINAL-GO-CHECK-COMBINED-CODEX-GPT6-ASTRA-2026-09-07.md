**Stage-C code is final; Stage-A remains FIX_FIRST because the operator procedure still invalidates its own freeze.** The corrected Stage-A freeze may pin the current Stage-C manifest without changing Stage-C code.

Audited HEAD: `f72948fd107beac1967f64511bf514dac8fe4ae7`. Tracked files remained unchanged. No network or SSH; reproduction/test writes stayed under the authorized TMPDIR.

**Requested pytest: 154 passed, 1 skipped in 390.51 s; exit 0.** The skip recognizes the already-fixed BASELINE adapter. The additional E9 figure integration test passed in 55.92 s.

| Item | Verdict | Current evidence |
|---|---|---|
| E1 / Stage-A member authentication | FIXED | All 270 Stage-C members hash-authenticated, including addendum and sidecar; pin agrees. |
| E2 | FIXED | Own reproduction accepts producer-written nested PASS; rejects a rehashed receipt containing nested STOP. |
| E3 | FIXED | Producer-written cumulative barrier accepted; empty provenance and rehashed empty checkpoint/rung artifacts refused. Coverage, cadence and contents checked. |
| E4 | FIXED | Finished verifier authenticates and materializes the A/B supplement; formal admission must match its A/B paths and digests. |
| E5 | FIXED | Canonical BASELINE-first dictionary serialization accepted; reversed explicit `arm_order` refused. |
| E6 | FIXED | Repair uses chunk-local `end-start`; second-chunk terminal-publication repair regression passes. |
| E7 | FIXED | Whole checkpoint/rung comparison retains the sealed exclusions. Own scientific-disposition flip refused. |
| E8 | PROCEDURAL LIMIT | Notification remains self-recorded, without independent owner-origin authentication; README explicitly limits the claim. |
| E9 | NONBLOCKING GAP | Full `verify_finished()` is called, but seven verification boundaries plus materialization are stubbed. Passing test does not establish complete admission integration. |
| Stage-A transport | FIXED | Exact deduplicated union: 246 closure + 14 additions + 23 additional Stage-C members = 283 paths. Server manifest check precedes preflight and refuses missing/stale members. |
| Addendum seal | FIXED | Addendum `9673928f…`, sidecar and acceptance-procedure literal `b6d6ab8b…` authenticate. |
| Operator ordering | **FIX_FIRST** | Commit-first instruction is followed by an incompatible post-bind commit instruction. |
| Replay addition | PASS IN TESTS | Independent epoch-zero replay compares tensors and Adam state; formal/nonformal tokens remain separate; sibling receipt is write-once. |

Both actual manifest checks returned exit 0:

- Stage-C: `675431fa4c7132af35f9c62c49c3265bc434aa9daaeee2afa2cdae1bccb68ad8`
- Launch: `e603106ddad8854ebf3fcc9244a42db6de5611e3a17a9ccb0a9ef16cdd1d02ee`

**The Stage-C dry-run skip need not be reverted before freeze.** I reproduced exit 0 with no manifest in an isolated launcher fixture. Consequently, dry-run success cannot authenticate the bundle. Explicit manifest `--check` and the real launcher’s local/remote checks remain mandatory. Charter rule 11 prohibits missing-closure fallbacks in builders; this skip does not narrow the real launch payload.

Engineering-lane `SHA256SUMS` has 20 valid rows and omits exactly `partial_merge_dryrun.py` and `test_partial_merge_dryrun.py`. This inventory omission remains nonblocking.

The copied r8 manifest and receipt independently hash to `8e1bd59e…` and `e9f84526…`; copied COMPLETE authenticates that manifest. The post-seal load PASS is recorded operator evidence, not a fresh server observation. Rerun #7 remains explicitly BLOCKED; the later passing tests must not relabel it CLEAN.

The minimal fixes are:

1. **Correct [operator step 2(e)](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/prompts/operator-r8-postseal-and-stagea-freeze-launch.md:4): no follow-up commit between binding and execution.** My isolated Git reproduction kept `dirty=False` throughout, but committing generated bindings changed commit/tree and caused `--check` to report `frozen file drifted`. [Binder exclusions affect dirty detection only](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c1c2-successor-launch/bind_v023_c1c2_successor_freeze.py:84). Also remove the claimed exemption for unrelated untracked WIP: the binder scans the whole repository except its named generated files.

2. **Make the server invocation explicit.** Freeze in `/home/sat/mcrl-leo-handover-wip` and export `V023_SUCCESSOR_LOCAL_PYTHON=/home/sat/mcrl-leo-handover/.venv/bin/python`; the launcher otherwise assumes a `.venv` inside that worktree. Run subsequent verifier/replay commands against the transported checkout containing `PREFLIGHT-RECEIPT.json`, using explicit `--repo` or receipt paths. No `/home/u24` dependency was found in the five audited packages’ Python/shell chain; “local” denotes the invoking host. Server Python and self-SSH availability remain unverified.

3. Before launch, obtain the required current real-artifact offline-chain PASS under charter rules 1/6. The available current dry-run artifact and rerun #7 are BLOCKED. Preserve the fresh diagnostic and `REPLAY_ARMS_PASS` gates before Stage B.

ASTRA_STAGEC_CODE_FINAL=YES
ASTRA_STAGEA_GO=FIX_FIRST