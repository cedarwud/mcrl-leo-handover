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

## 14:40 UTC addendum — engineering lane and vertical slices
Owner's standing instructions: (1) delegate all execution to sub-agents / server-side codex (codex is installed and logged in on `sat`; workspace pattern in memory `codex-on-server-sat`); (2) run the vertical slice first — every problem up to and during training must be found by fast iteration before a formal run. Read `.scratch/multi-catfish-v023-c1c2-successor/ENGINEERING-LANE-CHARTER-2026-09-07.md` and `VERTICAL-SLICE-PLAN-2026-09-07.md` (V1–V7 with status) and the handoff report §14–§16. Route C is decided (C1/C2 successor first; C3 via the pre-outcome contingency ladder F1→F4). Scientific declaration sealed (`V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md`, sha `f27d0500…`); execution bindings open until the launch manifest. Git snapshot branch `wip/multi-catfish-v023-20260907` (commit `14174d60…`); commit further snapshots on that branch when a package lands (owner approved committing). Packages landed today (all under `.scratch/`): `multi-catfish-v023-c1c2-provider-factory-v3`, `multi-catfish-v023-two-route-source-training-runner`, `multi-catfish-v023-c1c2-successor-physical-evaluation`, `multi-catfish-v023-c3-contingency-f1`, `multi-catfish-v023-two-route-rehearsal`, `multi-catfish-v023-engineering-lane`, and (in flight) `multi-catfish-v023-c1c2-successor-launch`. Open: 8 blockers on factory v3 + runner (astra audit) being fixed by server-side codex in `/home/sat/mcrl-v023-codex-ws-blockers-20260907` (diff with git, rsync back, re-audit); rehearsal symlink fix; r8 seal; then V2 → freeze → formal stage A.

## 15:20 UTC addendum — live handles for the engineering lane
- Server workspaces (codex, git-seeded copies of the shadow checkout `/home/sat/mcrl-v023-successor-shadow-20260907`): `/home/sat/mcrl-v023-codex-ws-blockers-20260907` (8 blockers fixed; pulled back locally by an operator agent), `/home/sat/mcrl-v023-codex-ws-rehearsal-20260907` (V1 per-shard completion-evidence fix, logs `/home/sat/codex-sol-rehearsal-pershard.log`), `/home/sat/mcrl-v023-codex-ws-baseline-20260907` (baseline adapter `contract_fields` exclusion + stage-B rerun, logs `/home/sat/codex-sol-baseline.log`). Pull results back with rsync of the owned directories, run the local full-tree tests, commit on `wip/multi-catfish-v023-20260907`.
- Shadow verifier for r8: `/home/sat/r8_shadow_verify.sh` (restart helper `/home/sat/r8_shadow_restart.sh`), log `/home/sat/mcrl-v023-r8-shadow-verify.log`; shard completion files are `shard-status/<mode>-world-<id>.terminal.json`. Never `pkill -f` a pattern that appears elsewhere in the same ssh command line (it killed the ssh shell twice).
- Open defects found by the slices: V1 attempt 2 (per-shard `COMPLETE` requirement), V3 (baseline adapter rejects populated `contract_fields`, `baseline_adapter.py:397-400`) — both being fixed on the server; after the baseline fix, extend the stage-B/C gate so its baseline step encodes a state with populated `contract_fields`.
- Reports: `ENGINEERING-LANE-REHEARSAL-RUN-REPORT-2026-09-07.md`, `ENGINEERING-LANE-V3-STAGEB-REHEARSAL-REPORT-2026-09-07.md`, `ENGINEERING-LANE-BLOCKER-FIX-PULLBACK-REPORT-2026-09-07.md` (pending), `ENGINEERING-LANE-SHADOW-CLOSURE-REPORT-2026-09-07.md` (pending), `LATENCY-LEDGER-2026-09-07.md`.
- Next formal steps once green: astra re-audit of factory v3 + runner + launch bundle → r8 seal → V2 on the scratch-sealed staging → bind/freeze → formal stage A (`sync_launch_v023_c1c2_successor_server.sh`) → stage B → stage C rungs; F1 launch authority after the F1 verification report; F2 package in flight.

## 17:20 UTC addendum — state after the vertical slices
- **V1 PASS on r8 shards** (3 and 10 epochs; ~1.25 s/epoch for three arms on 3 shards; exact continuation) — formal stage A is minutes of compute; the long pole is the r8 seal (monitor: terminal shards / COMPLETE). r5/r6 shards are INVALID inputs (receipt code closure drift) — never use them. r8-only rehearsal root: `/home/sat/mcrl-v023-real-shards-rehearsal-r8` (symlinks).
- **V3 PASS** after the baseline adapter fix (committed). **V4/V5** (stage-C 100 episodes, SIGKILL/resume drill, figure smoke) running under an operator agent. **V2-synthetic** (full formal stage-A chain on a producer-written synthetic sealed root) running under an Opus operator; it will CONFIRM the launch-bundle L-items while codex fix pass 2 is landing.
- **Launch bundle:** astra re-audit `REAUDIT-SUCCESSOR-PACKAGES-AND-LAUNCH-BUNDLE-…md` → 6 BLOCKERs + 1 MAJOR (incl. verifier `--no-reconstruct` bypass and 179/246 sync paths missing); codex fix pass 2 in flight (log `scratchpad/codex-sol-launch-fixpass2.log`); after it lands: run the bundle tests, `--dry-run`, then a THIRD astra read-only audit before any formal use.
- **Stage-B/C launch bundle** being written by server codex in `/home/sat/mcrl-v023-codex-ws-stagec-20260907` (log `/home/sat/codex-sol-stagec-launch.log`); pull back with rsync, test, commit, astra audit.
- **F1:** `INVALID_RUN` r1 = pure roundoff in F0 (fixed on server ws `…-f1diag-…`, 41 tests, new preflight `3711b930…`); operator is pulling back, rebuilding the F2 preflight, issuing authority r2 and replaying (tmux `mcrl-v023-c3-f1-20260907-r2`). F2 package + server dry-run + fan-out script ready (`/home/sat/f2-prep/`). agy reviewing F2 read-only; astra drafting the F3 pre-outcome design and auditing the stage-C/figure packages.
- **Ch5 figures:** `.scratch/multi-catfish-v023-ch5-figure-pipeline/` renders from stage-C rung receipts (matplotlib now in `.venv`).
- Git: branch `wip/multi-catfish-v023-20260907`, latest `d371908`; commit after each landing. Artifact page: republish `scratchpad/mcrl-v023-closure-audit.html` once the Opus editor finishes (new URL `983dfec8…`).
- Order of formal steps unchanged: r8 COMPLETE → post-seal load check → V2 on the real staging (offline merge/seal already proven) → third launch-bundle audit green → bind/freeze (r8 digests, closure list) → formal stage A → stage B → freeze stage C → rungs 100/500/1500/3000 → owner notification before 9000. C3: F1 r2 → (survivor) F2 → F3 (design memo) → separately frozen five-arm contract.

## 18:50 UTC addendum — launch readiness state
- Stage-A launch chain: fix passes 2+3 committed (`1e6310e`), 56/56 tests, manifest `8b020cd2…`, `--dry-run` refuses only for the absent r8 root. Third astra audit in flight (`THIRD-AUDIT-STAGEA-LAUNCH-CHAIN-…md`; verdict `GO_WHEN_R8_SEALS` or `FIX_FIRST`). V2-synthetic rerun in flight (no bypasses allowed; verifier positive path via a scratch copy without the `REHEARSAL-NONFORMAL` substring).
- When r8 `COMPLETE` appears AND the third audit says GO AND the V2 rerun is clean: freeze order = regenerate the launch manifest (working tree changed since the last write) → `bind_v023_c1c2_successor_freeze.py --write` against the sealed r8 root → `--check` → `sync_launch_v023_c1c2_successor_server.sh` (it runs preflight + one-epoch diagnostic and starts tmux `mcrl-v023-c1c2-successor-100e-r1`) → watch the 120 s ack → `verify_v023_c1c2_successor.py` on the finished root. Delegate every step to an operator agent; the controller only reads results.
- Stage-B/C: bundle committed (`534277b` + fixes), physical-evaluation/figure fix pass landed (verification operator running: tests, manifest rebuild, commit, shadow sync); then astra audit of the stage-C bundle + packages. Stage B runs immediately after stage A passes; stage C after its freeze.
- C3: F1 r2 replay in flight (operator; local→shadow sync only). On a survivor: F2 authority from the F2 preflight (`625ad7f2…`), `/home/sat/f2-prep/launch_f2_units.sh`; then F3 per `DESIGN-F3-LEARNER-SCREEN-PREOUTCOME-…md`. On no survivor: C3 = not admissible under the pre-declared mechanisms; Ch5 proceeds with two Catfish + the C3 negative result.
- Process rules added today: charter 6–12 (N=1 gate on every change, budget ladder, design-doc stop rule, latency ledger, no silent sync fallbacks, one writer per path, server workspaces pulled back once). agy works only as a harness-tracked background job.

## Freeze order (astra third audit, 16:46 UTC) — follow exactly when r8 seals and fix pass 4 is green
1. Stabilise checkout/HEAD (commit everything; no concurrent editors); authenticate the stage-C code manifest/pin (`62180dbd…` or its successor), the scientific authority and the attached review.
2. Bind: rederive learner manifest, provider config + sidecar, execution bindings + sidecar — including current git identity, r8 receipts and the stage-C code bindings (no deferrals of the three stage-C items).
3. Manifest: regenerate the launch manifest + sidecar after those files exist; run both `--check` modes.
4. Preflight: sync authenticated inputs; create a fresh server `PREFLIGHT-RECEIPT.json` + sidecar (must carry launch-manifest hash, bindings hash, requested output root).
5. Diagnostic: regenerate the scratch checkpoint and diagnostic receipt + sidecars; behavioural and identity gates must pass.
6. Launch: formal wrapper (tmux `mcrl-v023-c1c2-successor-100e-r1`), then the independent verifier/sealer. Any intervening code/authority change invalidates downstream derivations.

## 19:30 UTC addendum — where each line stands (UTC 17:30 wall clock on the server)
- **Stage-A launch chain:** third astra audit `FIX_FIRST` (L3 stage-C deferrals must be bound before stage A; N1/L5 preflight-receipt authority; R1 formal constants placement; 08 fixture provenance) → codex fix pass 4 in flight; V2 rerun found defect C (preflight pins the r8 root) → fixed (`codex-sol-preflight-target-root`). Next: operator verifies both (tests, manifest `--write/--check`, dry-run), commits; V2 rerun #3 (no bypasses; verifier positive path via a scratch copy without the `REHEARSAL-NONFORMAL` substring; add a SIGKILL-mid-epoch resume drill); then astra **ultra** GO check; then freeze per the six-step order when r8 seals.
- **r8:** 10/16 shards terminal, all shadow-verified; the controller's real merge+seal path exercised green on 9 real shards (`ENGINEERING-LANE-PARTIAL-MERGE-DRYRUN-REPORT-…md`); expect COMPLETE ~19:00–20:00 UTC; the r8 launch checkout lacks the target-batch adapter (irrelevant to the run; successor consumers use the shadow/local trees).
- **Stage-B/C:** astra audit `FIX_FIRST` (3/5/2; B2 constructor digest-only, M2 admission path/mapping, M1 continuation bypass, M4 seal, owner-marker = procedural control, N1 verifier gaps, N2 git enforcement) → codex stage-C fix pass 2 in flight → operator verify + commit + manifest rebuild → astra re-check; stage C is not on the critical path until stage A passes.
- **C3:** F1 r2 replay running (tmux `mcrl-v023-c3-f1-20260907-r2`); on completion → astra **ultra** adjudication of the token/tape before any F2 authority. F2 ready (`/home/sat/f2-prep/`, preflight `625ad7f2…`). F3: implementation in flight from design R1; design **R2** (`DESIGN-F3-…-R2-…md`) applies agy's four fixes → correction pass on the implementation before any F3 authority.
- **Rules:** one writer per path; server workspaces pulled back once; local → shadow sync only; agy via harness-tracked background; no silent sync fallbacks; controller delegates all execution.

## IF YOU ARE RUNNING ON THE SERVER (`sat`) — read this first (added 18:30 UTC)
You are the controller session on `sat`, inside tmux `mcrl-controller`, working tree `/home/sat/mcrl-leo-handover-wip`
(git worktree of `wip/multi-catfish-v023-20260907`; commit here; push to `origin` when the owner has pushed/allowed it).
Differences from the local session: python for repo code = `/home/sat/mcrl-leo-handover/.venv/bin/python` with
`PYTHONPATH=/home/sat/mcrl-leo-handover-wip/src` (there is no `.venv` in the worktree; never modify
`/home/sat/mcrl-leo-handover` itself — its venv is shared by every server script); codex is installed and logged in
(`codex exec … --sandbox workspace-write` runs directly in the worktree — no rsync/pull-back needed; still one writer per
path); agy is not installed (skip agy reviews or run them locally later); no ssh needed — server paths are local; heavy
runs go into tmux windows of this same server. The engineering-lane shadow `/home/sat/mcrl-v023-successor-shadow-20260907`
is synced FROM the worktree (`rsync -a --exclude __pycache__ <worktree>/.scratch/<pkg>/ <shadow>/.scratch/<pkg>/`).
Re-arm watchers from here: r8 (`ls /home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8-mode-shards/shard-status/*.terminal.json | wc -l`,
`COMPLETE`/`FAILED` in `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8`), F1 r2 (`tmux has-session -t mcrl-v023-c3-f1-20260907-r2`,
`/home/sat/mcrl-v023-c3-contingency-f1-20260907-r2/receipt.json`), shadow verifier log `/home/sat/mcrl-v023-r8-shadow-verify.log`.
The local session's monitors are gone; the report/ledger/plan files in `.scratch/multi-catfish-v023-controller-handoff-20260907/`
are the state. Delegate execution to codex (server) and Claude sub-agents; the controller only reads, decides, dispatches.
