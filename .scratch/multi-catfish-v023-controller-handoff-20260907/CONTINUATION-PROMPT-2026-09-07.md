# Continuation prompt — Multi-Catfish MCRL V0.23 execution closure (resume after compact)

Paste this as the first message of the continuation session. Time reference: 2026-09-07 12:55 UTC (Taipei 20:55).

You are the sole fresh-context execution controller for `/home/u24/papers/mcrl-leo-handover`, continuing the
2026-09-07 session whose full audit is in `.scratch/multi-catfish-v023-controller-handoff-20260907/`
(read `HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.md` §0, §1b, §11, §12 first; then this file). Memory
files under `~/.claude/projects/-home-u24-papers-mcrl-leo-handover/memory/` (index MEMORY.md) hold the
distilled rulings and pitfalls. Reply to the user in Traditional Chinese; keep code/paths verbatim.

## Goal and boundaries (unchanged)
Reach genuine three-Catfish training (C1/C2/C3 = Q1/Q2/Q3, evaluated by EE; desired physical order
FULL > DROP_C1, DROP_C2, DROP_C3 > BASELINE is a goal, never forced). Preserve all dirty WIP; no TEST
split; never tune seeds/thresholds/formulas/horizons/lambda/acceptance rules against results; heavy compute
only on ssh host `sat` with `/home/sat/mcrl-leo-handover/.venv/bin/python`; local work with `./.venv`;
episode training checkpoints every 100 episodes; notify the user before 9000 episodes; no new scientific
gates; narrow positive + mutation-negative + real vertical-slice checks only; receipts over polling;
always separate verified fact / inference / execution readiness / efficacy; loss values and oracle
directions are never EE evidence. Do not touch paper/symbols/figures.

## Working style the user asked for (binding)
- Delegate by task type; do not do everything on Fable: codex `gpt-6-astra` (read-only, `--sandbox read-only`,
  effort max) for adjudications — decide with it instead of asking the user; codex `gpt-5.6-sol`
  (`--sandbox workspace-write`, effort high/ultra) for scoped implementation; agy
  `--model "Gemini 3.8 Flash (High)"` for read-only reviews (it times out on long tasks); Claude Sonnet
  sub-agents for read-only audits. Run CLIs as `setsid nohup bash -c "codex exec ... </dev/null > log 2>&1;
  echo CODEX_EXIT=\$? >> log" &` — the harness kills plain background tasks whenever the LOCAL machine
  (15 GB, other sessions' tsc/codex) runs low on memory. Wait with the `Monitor` tool, not Bash waiters.
- Fast iteration: before any multi-hour run, exercise every consumer step against REAL artifacts offline
  (in-memory probes, dry-run tools, scratch inventories). Seven consumer/producer mismatches were found
  this way today; each would have cost 40 min–3 h on the server. Consumer aligns to producer; add a test
  that derives its expectation from the producer's code/output (never a hand-typed literal).
- One corrected attempt per line without asking; a second failure on the same line → report the exact
  failing boundary and ask. Everything else (implementation, tests, server launches, diagnostics) is yours.

## STATE CHANGE 12:54–13:10 UTC — read this first
- **R7 gate is sealed: integrity `VERIFIED`, decision `STOP_PHYSICS_R7`.** Root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1` now has `result.json`, `verification.json`, `MANIFEST.sha256` (sha `63ecb5a8…`), `COMPLETE`; local copies in `r7-sealed-receipts/`; numbers in `R7-STOP-PHYSICS-RESULT-2026-09-07.md`; narrative in the handoff report §0 (top paragraph) and §13. Deciding predicate `physical_signature`: 11-vs-00 pooled ratio-of-sums EE −0.049%, 2/8 worlds positive. Also false: `learned_composition`, `topology_consistency`, `harmful_partial` (would have given `REDESIGN_INTERFACE_R7` even if physics had passed). Learner panel and C1/C2 context passed.
- **Consequence (by design, verified on the server 12:58 UTC):** the post-R7 provider factory refuses the root (`R7 final result c3_decision is not the frozen GO value`), so the V2 100E launcher cannot start. Contract §7: a valid non-GO ends the LC-SRS successor route; no relaxation, no seed/world swap, no rerun selected by outcome, no CSE/EC promotion without its own declared formula and falsifier. **Do not** author an R5, rewrite the factory/launcher/manifests to accept a non-GO, relabel arms, or "try" the 100E anyway. The execution mandate for the R7 → 100E line has ended; what remains is a design decision that belongs to the user.
- **Still running / pending:** r8 C1/C2 target generation (independent claim ceiling; keep it, seal it, run the post-seal load check — its targets are reusable by any successor that keeps C1/C2); codex gpt-6-astra read-only adjudication of the STOP (log in the previous session's scratchpad `codex-astra-r7-stop.log`; output file `ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md` in the handoff dir — if the file exists, append its VERIFIED/RECOMMENDATION to report §13; if it never appears, re-dispatch with the prompt in `prompt-astra-r7-stop.md` if that file still exists, otherwise rebuild it from §13's questions).
- **Clean state achieved after the STOP:** V2 bundle repointed to `-ops3-r8`, manifest rebuilt `233a818765f2d67049a32ac74516162507bd075bc1fbf23261063a9d57be7c0f` (90 entries, 60 tests pass); runner tests 7 pass (runner module untouched); plumbing rehearsal script + 3 tests staged, not run. These are kept as plumbing for a successor, not as a launch path.

## Live state at 12:53 UTC (historical — superseded by the state change above)

**R7 line.** Real R4 repair run in progress since 12:17 UTC: tmux `mcrl-v023-r7-domain-repair-20260907-r4`
on `sat`, log `/home/sat/mcrl-v023-r7-domain-repair-20260907-r4.log` (0 bytes until it ends), package
`.scratch/multi-catfish-v023-r7-domain-repair-r4/` (manifest `f90381cf…`; R3 installs + pair-key
reconstruction + list-typed `c2_diagnostic` normalisation + float32 `q2_delta` recomputation). The third
read-only scratch inventory with all three corrections had **0 findings**
(`R7-FINAL-VERIFIER-INVENTORY-R4D-SCRATCH-20260907.json`). Expected ~40 min. Outcomes:
- sealed: R7 root `/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1` gains `result.json`, `verification.json`,
  `MANIFEST.sha256`, `COMPLETE`; read `result.json` `c3_decision`/`status`. Then run the prepared R7-half
  provider rehearsal (read-only): `ssh sat 'cd /home/sat/mcrl-v023-learner-rehearsal-checkout-20260907 &&
  PYTHONDONTWRITEBYTECODE=1 /home/sat/mcrl-leo-handover/.venv/bin/python rehearsal_factory_v2_r7_half.py
  /home/sat/mcrl-v023-learner-rehearsal-checkout-20260907 /home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1
  /home/sat/mcrl-v023-r7-launch-ready-20260906-r4'`. A non-GO decision is a scientific result (ends the
  LC-SRS C3 route) — report, do not repair.
- `V023_R7_DOMAIN_REPAIR_R4_FAILED` / INVALID: do NOT author R5; report the exact message; the user decides.
**C1/C2 line.** r8 launched 12:37 UTC via
`.scratch/multi-catfish-v023-c1c2-target-generation-launch/sync_launch_v023_c1c2_targets_server.sh`
(CODE-MANIFEST `79a181a3…`, 30 bindings): server root `/home/sat/mcrl-v023-c1c2-target-generation-20260907-ops3-r8`,
output `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`, staging `…-ops3-r8-mode-shards/`, tmux
`mcrl-v023-c1c2-target-generation-20260907-ops3-r8`. At 12:53 benchmarks 4/6 done; then 16 shards (80–178 min
each, ~77 GB RAM total), then the controller's merge + sealer (first real execution; the per-shard
authentication was proven on the real r6 shard, merge/seal on a synthetic 16-shard test). If the controller
writes `FAILED` AFTER shards completed, do not recompute: run the read-only dry-run tool
`dryrun_v023_c1c2_controller_postshard.py` (command in `HANDOFF…md` / codex summary) against the staging
to see the merge/seal failure, fix the consumer, and re-run merge/seal on the existing staging. Preserved
failed roots: r5 (6 complete shards), r6 (FAILED, 1 complete shard), r7 (empty, launcher failed pre-compute).
**Provider/100E line.** V2 bundle `.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/` implements
DECISION A (factory v2 with `r7_code_root` = `/home/sat/mcrl-v023-r7-launch-ready-20260906-r4`, hardened-P
closure 18 A + 33 L files, launcher order seed → R7 closure vs seed → overlay → learner-manifest verify →
factory preflight → one-epoch diagnostic gate → controller → tmux + 120 s ack). A codex task was moving its
target root from `-ops3-r6` to `-ops3-r8` (check `grep -rn ops3-r6` returns nothing, then
`build_v023_100e_launch_manifest.py --check`, pytest of the bundle dir, and `--dry-run`). Server rehearsal
checkout `/home/sat/mcrl-v023-learner-rehearsal-checkout-20260907` = R7 seed + 90-entry overlay; re-overlay
after any manifest change (`rsync -aR --files-from=<manifest paths> . sat:<checkout>/`).
**codex tasks that may still be running (logs lived in the previous session's scratchpad and may be gone;
judge by files + tests):** (1) runner test-debt: only
`.scratch/multi-catfish-v023-five-arm-training-runner/test_v023_five_arm_source_training_runner.py` may change
(4 tests fed C2 as the retired 228 batch); (2) V2 r8-move (above); (3) non-formal one-world plumbing
rehearsal: new files `rehearsal_v023_one_world_plumbing_fresh_models.py`, its test and
`REHEARSAL-README.md` in `.scratch/multi-catfish-v023-real-one-world-plumbing/` — run it on the server
rehearsal checkout after syncing the dirs its README names; it is `formal:false`, untrained models, timing
and plumbing only.
**Test status (last local run):** C1/C2 launch+generator suites 81 pass; V2 bundle 47+8 pass; factory v2
19+ pass; target adapter 18 pass; bridge pass; runner tests 4 failing until codex finishes.

## Ordered next steps (REPLACED — see below)
1. Read R4 outcome → act as above. 2. Wait for r8 `COMPLETE`; run the read-only post-seal check
(`/home/sat/mcrl-v023-postseal-target-check-20260907/postseal_target_load_check.py <src> <adapter> <root>`,
sync the current adapter `3b8a2268…` first). 3. Confirm the V2 bundle points at r8, manifest `--check`,
dry-run; re-overlay the rehearsal checkout. 4. Launch
`bash .scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh`
(creates `/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout`, output `…-100e-r2`, tmux
`…-100e-r2`); it runs the one-epoch diagnostic itself and refuses to start the controller unless it passes.
Watch its log for the startup acknowledgement; 100 epochs, checkpoint at epoch 100, then the sealer.
5. After `PASS_SOURCE_TRAINING_INTEGRITY`: formal one-world plumbing (contract §5), then the episode ladder
100 → 500 → 1500/3000 → 9000 with receipts every 100 episodes; notify the user before 9000.
6. Keep `HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.md` §12 and the memory files current; republish the
artifact `https://claude.ai/code/artifact/0b130c2a-2c59-4b73-8467-adea41db3fe9` (Artifact tool with `url`).

## Ordered next steps after the STOP
1. Collect the astra adjudication; append to report §13; if it disagrees with the STOP derivation, do not act on it — report the disagreement to the user with both readings.
2. When r8 reaches `COMPLETE`: run the read-only post-seal check (`/home/sat/mcrl-v023-postseal-target-check-20260907/postseal_target_load_check.py <src> <adapter> <root>`, sync adapter `3b8a2268…` first); record the sealed target-root digests in the report ledger. If the controller writes `FAILED` after the shards completed, use `dryrun_v023_c1c2_controller_postshard.py` against the staging to fix the consumer and re-run merge/seal on the existing shards (one corrected attempt).
3. Republish the artifact `https://claude.ai/code/artifact/983dfec8-bc7f-493d-a726-5fff26fdbd3e` from the refreshed HTML (Artifact tool with `url`; the older 0b130c2a… link is dead); update the memory files.
4. Report to the user in Traditional Chinese: the STOP, its derivation, what it does and does not mean, and the decision they own (successor declaration with a fresh formula + falsifier, or C3/three-Catfish redesign). No computation on a successor before its contract is declared and frozen.

## Pitfalls already paid for
Server venv `mcrl` is an editable install of a stale tree: every server script must `sys.path.insert(0,
<checkout>/src)` (launchers export PYTHONPATH). `preflight_v023_c1c2_targets.py` rejects CODE-MANIFEST paths
containing `r5`, `test_split`, `episode_training`. The C1/C2 launcher syncs only listed dirs — test fixtures
must live inside the launch package. Diagnostics on the server while shards run: `OMP_NUM_THREADS=1`,
`echo 1000 > /proc/<pid>/oom_score_adj`. The frozen `DetachedQ12Snapshot` digest is not backward compatible —
never rebuild historical snapshot digests with the live class. Never rewrite frozen manifests or sealed
artifacts; no `sys.modules` aliasing; `ALL_NEUTRAL_CONTROL` is never `BASELINE`.
