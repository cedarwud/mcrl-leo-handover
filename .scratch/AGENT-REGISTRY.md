# Agent registry — resume after any interruption

## RESUME-NOW — updated 2026-09-11 18:05 UTC (2026-09-12 02:05 Taipei). Controller = Opus 5, effort xhigh. READ THIS FIRST after any limit / crash.

Quota facts today: the daily cost cap (HTTP 402, $80/day), the per-model session limit (429 "session limit", ~5 h rolling; opus
reset last at 00:10 Taipei) and the sonnet **weekly** limit (resets 04:00 Taipei = 20:00 UTC) have each killed agents. A limit kills
the agents, never the detached `sat` jobs. Resume = `SendMessage(to=<agentId>, message=<block below> + "It is now <UTC>. Delta:
<from a read-only check>")`. Before sending: read that agent's PROGRESS.md; check its `sat` processes by cwd + cmdline
(`ssh sat 'for p in $(pgrep -u sat python); do echo $p $(readlink /proc/$p/cwd) $(tr "\0" " " </proc/$p/cmdline|cut -c1-120); done'`);
never let an agent relaunch a live or finished item.

### Live Claude sub-agents (4, all opus)

| name | agentId | workspace / PROGRESS | deliverable | state at 18:05 UTC | detached processes |
|---|---|---|---|---|---|
| **LP-ORACLE** (critical path) | `a931738d2046dbe76` | `.scratch/h4-probe/PROGRESS.md` (§T2-*); task `.scratch/h4-probe/LP-AND-ORACLE-TASK.md`; sat ws `/home/sat/mcrl-v025-h4-probe-ws/` | `.scratch/h4-probe/ORACLE-CELLS-2026-09-11.md` (LP report DONE: `LP-PROBE-2026-09-11.md`) | v4 oracle shards running: rate-floored A-real/B-real R1 **evaluation** first (A-floor done, B-floor in progress), then **B-real-floor R1 calibration, A-real-floor R1 calibration**, then R2 eval / reverse / unfloored cal (downstream). All v4 items carry 28-action advantage vectors. Unfloored A/B R1 eval done (controller-verified, provisional) | sat PIDs **3529259–3529262** (`scripts/oracle_cells.py --shard K --nshards 4 --results-dir …/results-oracle`, cwd `…/h4-probe-ws/tree`); relaunch = the same 4 commands once none is alive (idempotent) |
| **B1-CREDIT → HARNESS** | `ae9d69e8a6fa8791b` | `.scratch/b1-credit/PROGRESS.md`; worktree `/home/u24/papers/mcrl-leo-handover-b1` (branch `b1/difference-reward-20260912`, credit code **not yet committed**) | (1) `.scratch/b1-credit/B1-CREDIT-IMPLEMENTATION-2026-09-12.md` with first line incl. "lighting-price credit oracle-first: PASS/FAIL"; (2) then `.scratch/b1-credit/D-LADDER-HARNESS-2026-09-12.md` | credit module + wiring + 8 tests written; diag ep0/ep1 finished; mutant runner done; **now: the lighting-price greedy-rule screen** (controller addition 18:00 UTC), then report + commit, then the D0–D4 harness (Amendment 5 §I.5). **No optimizer step ever** | local only, ≤ 2 procs; none alive at 18:00 |
| **T0REPR** | `a7953d10497ac8773` | `.scratch/t0-repr/PROGRESS.md`; sat ws `/home/sat/mcrl-v025-t0-repr-ws/` (≤ 3 procs) | `.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md` (`R_repr` one-hot + soft, both sets) | placebo + collection done; soft-clone τ fits running; a declared 400-epoch sensitivity follows the 100-epoch clones (verdict read on the 100-epoch clones) | sat PIDs **3544260, 3544261** (`scripts/t0_clone.py --kind soft --taus …`, cwd the ws) |
| **CEILING2** (downstream) | `aeff029c95c8d0633` | `.scratch/ee-ceiling/PROGRESS.md`; sat ws `/home/sat/mcrl-v025-ceiling-ws/` (cap 4 procs) | `.scratch/ee-ceiling/EE-CEILING-2026-09-11.md` (not yet written) | all cells done incl. bits/joules halves, initB1/initrand basins, **T_JOINT rate-floor action-dump re-run** (`results/tjoint-ratefloor-npz/`, `tjoint-ratefloor-parity.json`); remaining: the report | none alive at 18:00 |

Resume messages (send verbatim + time + delta):
- **LP-ORACLE** → *"Resume the oracle-cell task after an API limit. Read your `.scratch/h4-probe/PROGRESS.md` (§T2-13/14 and the controller
  notes) and `.scratch/h4-probe/LP-AND-ORACLE-TASK.md`. Check the v4 `oracle_cells.py` shards on sat by cwd + cmdline; if none is alive
  and items remain, relaunch the same four commands (the queue is idempotent). Priority order unchanged: rate-floored A/B R1 evaluation →
  B-real-floor R1 calibration → A-real-floor R1 calibration → R2 / reverse / unfloored calibration. Then write
  `ORACLE-CELLS-2026-09-11.md` applying Amendment 1 rules 1–4 to the floored cells and stating Amendment 4 §2's B2 conditions. ≤ 4 processes."*
- **B1-CREDIT → HARNESS** → *"Resume after an API limit. Read your `.scratch/b1-credit/PROGRESS.md` and continue from the first incomplete step:
  the lighting-price greedy-rule oracle-first screen (controller addition 18:00 UTC; Amendment 5 'Controller finding'), then the B1 report and
  commit, then the D0–D4 harness (Amendment 5 §I.5). Hard boundary unchanged: no optimizer step, no training; local ≤ 2 processes."*
- **T0REPR** → *"Resume the T0 representability screen after an API limit. Read your `.scratch/t0-repr/PROGRESS.md`; check your sat processes in
  `/home/sat/mcrl-v025-t0-repr-ws/` by cwd + cmdline; never refit a clone whose output exists; continue from the first incomplete step; the
  declared 100-epoch clones decide admission, the 400-epoch fits are a sensitivity. ≤ 3 processes."*
- **CEILING2** → *"Resume after an API limit. Read your `.scratch/ee-ceiling/PROGRESS.md`; all cells are done; write
  `EE-CEILING-2026-09-11.md` with parity first, the standard wording of Amendment 3 §1 (lower bounds; rate-floored +23.9 % as the defensible
  headline; the base search's p10 tail), the sweep-depth numbers and the T_JOINT dump parity. Blindness to the pilot outputs unchanged."*

### Completed agents (do not resume unless a follow-up is needed)
VALIDITY-FABLE `ab15c86158b2b327e` (fable; blind report + phase 2a done in `.scratch/validity-audit/VALIDITY-AUDIT-BLIND-2026-09-11.md`;
**phase 2b still owed**: when the ceiling report and the oracle report exist, `SendMessage` it both paths plus Amendments 3–5 and ask whether the
verdict changes — it is resumable) · REPORTWRITER `af80cc36ea6c8b4ae` (sonnet; `24cb8615`) · Q9A-CURATE `a29cef00400322355` (sonnet; `1c2d0ba3`) ·
B0AUDIT `a75e535219ff956d2` (sonnet; `7a7c47ab`) · H4PROBE `a721c0c4171804491` (sonnet; **weekly limit until 20:00 UTC**; its LP/oracle work was
taken over by LP-ORACLE) · AGY-VALIDITY and AGY-CHECK-2 (agy, done; not resumable).

### Controller state to restore
- In force: Ruling 2 + Amendments 1–5 (`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-*-2026-09-1[12].md`); decisions log
  `.scratch/WORK-QUEUE-DECISIONS-2026-09-11.md`; external checks `.scratch/reviews/external-gpt/DR19-GPT6-CONTROLLER-CHECK-2026-09-12.md`.
- **No learner training is authorised.** Amendment 5 Part II is a delay-triggered contingency only (five-condition trigger; lighting-price credit
  only if its own greedy rule passes the B1 screen; sealed results).
- Next controller actions, in order: (1) when the floored A/B R1 evaluation cells land — aggregate independently (as in
  `.scratch/h4-probe/CONTROLLER-INDEPENDENT-AGGREGATE-2026-09-12.md`) and read Amendment 1 rules 1–4 and Amendment 4 §2 condition 1;
  (2) if condition 1 holds, B2 condition 3 needs the T_SEQ clone on the floored calibration cells; (3) on B1's report — check the PASS/FAIL line
  and the tests; then the harness report → **agy diff review before any launch**; (4) on T0's report — `R_repr` admission; (5) phase 2b to
  VALIDITY-FABLE; (6) Q9b curation (H4, LP, ceiling, oracle rows) with sonnet after 20:00 UTC.
- Monitors: none armed (agents notify on completion).


### (history) previous RESUME-NOW block, 2026-09-11 afternoon — superseded by the block above

#### RESUME-NOW (old) — 2026-09-11 afternoon session (controller = Fable 5.1). Read this block first after any limit / crash.

Three Claude agents are live, all resumable with `SendMessage(to=<agentId>, message=<block below>)`. **Before sending**: read that
agent's `PROGRESS.md`, put the delta into the message (what is already done, what is live on `sat` by cwd + cmdline), and never
relaunch a running or finished computation. The daily cost limit (HTTP 402, $80/day) kills all agents at once; detached `sat`
jobs keep running.

| name | agentId | model | workspace / PROGRESS | deliverable | dispatched → resumed |
|---|---|---|---|---|---|
| **VALIDITY-FABLE** | `ab15c86158b2b327e` | fable | `.scratch/validity-audit/PROGRESS.md` (brief `PROMPT-BLIND.md`) | `.scratch/validity-audit/VALIDITY-AUDIT-BLIND-2026-09-11.md` | 12:20 → 12:36 UTC → **died again 12:45 UTC with HTTP 429 "session limit · resets 10:30pm Asia/Taipei" (= 14:30 UTC)**; owner reported the limit lifted at 12:47 UTC → **resumed again 12:48 UTC** by SendMessage (the 22:33 Taipei cron was cancelled) |
| **CEILING2** | `aeff029c95c8d0633` | opus | `.scratch/ee-ceiling/PROGRESS.md` (brief `PROMPT.md`); sat ws `/home/sat/mcrl-v025-ceiling-ws/` | `.scratch/ee-ceiling/EE-CEILING-2026-09-11.md` + `results/*.json` | 12:20 → 12:36 UTC; **still running at 12:46** |
| **REPORTWRITER** | `af80cc36ea6c8b4ae` | sonnet | `.scratch/cf3-pilot/PROGRESS.md` (heading `REPORTWRITER`; brief `REPORT-WRITER-PROMPT.md`) | `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md` + commit of named paths | 12:27 → 12:36 UTC → **COMPLETED 12:45 UTC, commit `24cb8615`**; all provenance checks passed, 32/32 sha256 matched; controller has NOT read the report |
| AGY-VALIDITY | — (agy, not resumable) | Gemini 3.8 Flash (High) | `.scratch/reviews/validity-agy/` | **DONE 12:33** (`VALIDITY-AUDIT-AGY-BLIND-…md`; see `CONTROLLER-CHECK-…md`) | — |
| **Q9A-CURATE** | `a29cef00400322355` | sonnet | `.scratch/curation/PROGRESS-Q9.md` | registry rows for the pilot + document-status rows; commit of the three named paths | 13:05 UTC → **DONE 13:27 UTC, commit `1c2d0ba3`**: 45 rows `P3-01..45` in RESULTS-REGISTRY §4x (242 values cross-checked, 0 mismatches), trap 6 added to §0, DOCUMENT-STATUS §1b (4 rows) |
| **H4PROBE → LP PROBE** (same agent, resumed 14:30 UTC with a second task: the beam-lighting-price rule family LP(c, m), simultaneous and sequential; report `.scratch/h4-probe/LP-PROBE-2026-09-11.md`). **Queued next for the same agent (send when the LP report lands):** the oracle cells A-real / B-real of `V025-CONTROLLER-AMENDMENT-1-ORACLE-FIRST-SCREEN-2026-09-11.md` §2 (simultaneous best response to `A m=2dB`'s joint action with the realised evaluator; one sequential sweep; order sensitivity 99..0 on ≥ 6 episodes; η = reference step's bits/joules; rate distribution on every cell) | `a721c0c4171804491` | sonnet | `.scratch/h4-probe/PROGRESS.md`; sat ws `/home/sat/mcrl-v025-h4-probe-ws/` | `.scratch/h4-probe/H4-PROBE-2026-09-11.md` — η→0 argmax-flip probe on the 9 final checkpoints + explicit own-bits rule + reference rules on both episode sets | 13:15 UTC → **DONE 13:55 UTC** (`H4-PROBE-2026-09-11.md`): η→0 flips 11–42 % of decisions on the trained checkpoints, closed-loop EE −8.1…+3.1 % (no consistent sign); explicit own-bits rule below every learner; both placebos bit-for-bit, 9/9 deployed rollouts match the pilot's eval JSONs; no sat process left |
| **B0AUDIT** | `a75e535219ff956d2` | sonnet | `.scratch/b0-corrected/HOUSEKEEPING-PROGRESS.md` | `.scratch/b0-corrected/B0-BRANCH-EQUIVALENCE-AUDIT-2026-09-11.md`; tag `archive/b0-corrected-baseline-20260911`; worktree `/home/u24/papers/mcrl-leo-handover-b0` removed only if all four commits are ported; branch never deleted | 13:40 UTC → **DONE 13:50 UTC, commit `7a7c47ab`**: 2 commits identical, 2 superseded in HEAD; tag created; worktree kept (removal left to the owner) |
| **LP-ORACLE (takeover)** | `a931738d2046dbe76` | **opus** | `.scratch/h4-probe/PROGRESS.md` (heading "TAKEOVER 2"); task file `.scratch/h4-probe/LP-AND-ORACLE-TASK.md`; sat ws `/home/sat/mcrl-v025-h4-probe-ws/` | `.scratch/h4-probe/LP-PROBE-2026-09-11.md` then `.scratch/h4-probe/ORACLE-CELLS-2026-09-11.md` (A-real/B-real × two references, order sensitivity, parity first) | 14:55 UTC. **Why a takeover:** the sonnet agent `a721c0c4171804491` hit a *weekly* limit (429, resets 04:00 Asia/Taipei) at 14:45 with the LP grid (4 detached `lp_grid.py`, PIDs 3482477/3482530/3482583/3482636) still running on sat. Do not resume the sonnet agent before the reset; resume the opus agent with the standard block if interrupted |
| **B1-CREDIT** | `ae9d69e8a6fa8791b` | opus | `.scratch/b1-credit/PROGRESS.md` (brief `PROMPT.md`); worktree `/home/u24/papers/mcrl-leo-handover-b1`, branch `b1/difference-reward-20260912` from `102b2d4d`; local only | `.scratch/b1-credit/B1-CREDIT-IMPLEMENTATION-2026-09-12.md` — difference-reward + lighting-price credit, tests, no-training diagnostic, cost benchmark; **no training** | 16:30 UTC; resume: "read your PROGRESS.md; continue from the first incomplete step; no optimizer steps" |
| **T0REPR** | `a7953d10497ac8773` | opus | `.scratch/t0-repr/PROGRESS.md`; sat ws `/home/sat/mcrl-v025-t0-repr-ws/` (≤ 3 processes) | `.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md` — T0 = LP-prev(1,0) placebo, ≥ 100 training-like episodes, one-hot + soft clones, closed-loop `R_repr` on both sets | 17:45 UTC (Amendment 5 §I.4); resume with the standard block |
| (queue changes 17:40 UTC) | — | — | B1-CREDIT's T0 follow-on **cancelled**; its next task = D0–D4 harness (Amendment 5 §I.5), no training. CEILING2 capped at 4 processes; its remaining items downstream. LP-ORACLE: floored R1 evaluation → floored R1 calibration (B first) → R2 / reverse / unfloored calibration | — |
| **AGY-CHECK-2** | — (agy, detached; pid in `.scratch/reviews/validity-agy-2/agy.pid` = 497902) | Gemini 3.8 Flash (High) | `.scratch/reviews/validity-agy-2/` (prompt `PROMPT.md`, log `agy.log`) | `AGY-CHECK-OF-FABLE-AUDIT-2026-09-11.md` — adversarial re-derivation of the Fable audit's 14 load-bearing claims | 13:05 UTC → **DONE 13:18 UTC**: 8/14 confirmed, 6 corrections, DEAD-PATH survives with corrections; controller adjudication in `WORK-QUEUE-DECISIONS-2026-09-11.md` |

**State changes at 13:05 UTC:** VALIDITY-FABLE **blind report DONE** (`VALIDITY-AUDIT-BLIND-2026-09-11.md`, verdict DEAD-PATH as framed); controller unblinded and read the pilot report; **phase 2a sent** to VALIDITY-FABLE (pilot result only; it appends section K to its own report); **phase 2b** (ceiling) still to send when `.scratch/ee-ceiling/EE-CEILING-2026-09-11.md` exists. CEILING2 received a brief amendment (per-user throughput reporting; variants rate-floor / nominal-information / compound beam-emptying / multi-init only if the base search exceeds +3 % over the best rule). If this session dies: resume VALIDITY-FABLE with "continue phase 2a per the controller's last message; then wait for part 2"; resume CEILING2 with the standard block plus "the amendment in your PROGRESS.md stands".

**⚠ 15:00 UTC 2026-09-11 (= 23:00 Asia/Taipei): quota state.** opus session limit hit by **CEILING2** `aeff029c95c8d0633` and **LP-ORACLE** `a931738d2046dbe76` (resets **00:10 Asia/Taipei = 16:10 UTC**); sonnet **weekly** limit hit by `a721c0c4171804491` (resets 04:00 Taipei = 20:00 UTC). Detached work on sat continues: ceiling search (19 `ceiling_search.py` processes: base 24 episodes + round-1/2 variants, ws `/home/sat/mcrl-v025-ceiling-ws/`, outputs under `results/search-*/`), LP grid (4 `lp_grid.py`, ws `/home/sat/mcrl-v025-h4-probe-ws/results-lp/`). **Both opus agents resumed by SendMessage at 16:13 UTC (00:13 Taipei) after the owner reported the limit lifted; the cron was cancelled.** Delta at resume: base search 24/24, free/nominal/ratefloor 6/6, compound 5/6 (1 running), bits/joules 3/6 (second halves never launched); LP grid 97 files, 1 process finishing. If they die again, send by hand:
- CEILING2 → *"Resume CEILING: interrupted by an opus session limit at ~15:00 UTC; now <time>. Read your `.scratch/ee-ceiling/PROGRESS.md`; check by cwd + cmdline which `ceiling_search.py` processes are still running under `/home/sat/mcrl-v025-ceiling-ws/` and which result files exist; never relaunch a live or finished cell; launch only missing cells and stay ≤ 10 concurrent processes. Then apply the controller's amendment 3 (per-sweep EE from the η trajectories; parity first in the report; rate distribution per variant; 'lower bound, not ceiling' wording) and finish steps 8–11. Blindness to the pilot outputs unchanged."*
- LP-ORACLE → *"Resume: interrupted by an opus session limit right after reading the brief; now <time>. Read `.scratch/h4-probe/LP-AND-ORACLE-TASK.md` and `.scratch/h4-probe/PROGRESS.md`; check the `lp_grid.py` processes / `results-lp/` on sat by cwd + cmdline; finish the LP report, then the oracle cells as specified. Constraints unchanged."*

**Resume messages (send verbatim, then append "It is now <time UTC>. Delta: <what PROGRESS.md shows as done; what is live on sat>."):**

- VALIDITY-FABLE → *"Resume the blind validity audit: your run was interrupted by a daily API cost limit. Read your own
  `.scratch/validity-audit/PROGRESS.md` first and continue from where it stops; every item ticked there is done — do not re-read
  those artefacts. All rules in `.scratch/validity-audit/PROMPT-BLIND.md` are unchanged (blindness: no ssh, forbidden paths,
  PROGRESS.md ≤ line 148, forecast ≤ line 57, no gpt4.md, nothing under `.scratch/ee-ceiling/` except PROMPT.md, nothing under
  `.scratch/reviews/validity-agy/`; no files outside `.scratch/validity-audit/`; no edits; no training). Update PROGRESS.md after
  each analysis section. Return only the report's first line and the Traditional Chinese executive summary."*
- CEILING2 → *"Resume CEILING: your run was interrupted by a daily API cost limit. Read your own `.scratch/ee-ceiling/PROGRESS.md`
  first; continue from the first incomplete step, idempotently (check each step's output before computing). Check by cwd +
  cmdline whether any detached process of yours is still running under `/home/sat/mcrl-v025-ceiling-ws/` before launching
  anything; never relaunch a live or finished job. All constraints in `.scratch/ee-ceiling/PROMPT.md` unchanged (blind to the
  pilot outputs, ≤ 4 processes, `nice -n 16`, 1 BLAS thread, < 5 GB, `setsid nohup` for long runs, placebo bit-for-bit first,
  benchmark and declare the budget in PROGRESS.md before the counted run, exact-PID kills only). Return the report's first line
  and the wall time used."*
- REPORTWRITER → *"Resume REPORTWRITER: your run was interrupted by a daily API cost limit. Read `.scratch/cf3-pilot/PROGRESS.md`
  (your heading REPORTWRITER, if present) and `.scratch/cf3-pilot/REPORT-WRITER-PROMPT.md`; continue idempotently (sha256 check
  against sat, re-copy only mismatches, write the report from the generated tables, commit only the named paths). Your final
  message must contain no numbers, no arm ordering and no branch outcome."*

**Controller state to restore with them:**
- **Blind rule still in force**: do not open `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`, `.scratch/cf3-pilot/report/`,
  `sat:ws/report/`, `sat:ws/eval/`, any `readings.jsonl`, or `.scratch/cf3-pilot/PROGRESS.md` lines 149–182 until the Fable blind
  report exists.
- **On VALIDITY-FABLE completion**: read its report (the artefact, not the summary) → then read the pilot report (Q3b) →
  `SendMessage` phase 2 to VALIDITY-FABLE with the pilot report path and, when available, `.scratch/ee-ceiling/EE-CEILING-2026-09-11.md`,
  asking whether the verdict changes → dispatch an agy adversarial check of the Fable report (new dir `.scratch/reviews/validity-agy-2/`,
  same agy command form) → Q9 curation (sonnet) → update HANDOFF.
- **On CEILING2 completion**: read its report; feed it to phase 2; registry rows in Q9.
- **On REPORTWRITER completion**: its message carries no numbers; do not open the report until the Fable blind report exists.
- No session monitors need re-arming (agents notify on completion; the `REPORT-DONE` and agy-exit monitors already fired).
- Decisions and gating: `.scratch/WORK-QUEUE-DECISIONS-2026-09-11.md` (Q4–Q7 gated/deferred; Q8 awaits owner OK; Q9 after Q3b).
- If agy must be re-run: `cd .scratch/reviews/validity-agy && agy -p "$(cat PROMPT.md)" --dangerously-skip-permissions --model "Gemini 3.8 Flash (High)" --print-timeout 120m </dev/null > agy.log 2>&1` (detached with `setsid nohup`).

---

> **Session of 2026-09-11 ~12:20 UTC (controller = Fable 5.1). Live agents now — decisions in `.scratch/WORK-QUEUE-DECISIONS-2026-09-11.md`:**
> - **VALIDITY-FABLE** `ab15c86158b2b327e` (model fable, fresh context) — blind validity audit per `.scratch/validity-audit/PROMPT-BLIND.md`; writes `.scratch/validity-audit/VALIDITY-AUDIT-BLIND-2026-09-11.md` + `PROGRESS.md`. **Phase 2 pending:** after the blind report exists, `SendMessage` it the pilot report path + the ceiling report path and ask whether the verdict changes. Resume: "Read your `.scratch/validity-audit/PROGRESS.md`, continue from the last completed section; blindness rules unchanged."
> - **CEILING2** `aeff029c95c8d0633` (model opus) — EE ceiling measurement per `.scratch/ee-ceiling/PROMPT.md`; sat workspace `/home/sat/mcrl-v025-ceiling-ws/`; writes `.scratch/ee-ceiling/EE-CEILING-2026-09-11.md` + `PROGRESS.md`. Resume: "Read your `PROGRESS.md`; check your detached sat processes by cwd+cmdline before relaunching; continue from the first incomplete step."
> - **REPORTWRITER** `af80cc36ea6c8b4ae` (model sonnet) — TAKEOVER §4: copies `sat:ws/report/` back and writes `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`; its final message carries no numbers. Dispatched ~12:27 UTC after `REPORT-DONE` appeared (~12:25).
> - **AGY-VALIDITY** — **COMPLETED ~12:33 UTC** (agy Gemini 3.8 Flash (High), ~10 min): `.scratch/reviews/validity-agy/VALIDITY-AUDIT-AGY-BLIND-2026-09-11.md`, verdict DEAD-PATH. **Controller check found verified errors** (cross-archive numbers, wrong bits/joules ratios, non-existent citation, Q4–Q7 misdescribed): `CONTROLLER-CHECK-2026-09-11.md` in the same dir. Treat as hypotheses only.
> - Controller rule in force: **do not open** `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`, `.scratch/cf3-pilot/report/` or `sat:ws/report/` until both blind audits are written.
> - **Interruption ~12:30 UTC: all three Claude agents (VALIDITY-FABLE, CEILING2, REPORTWRITER) were terminated by the daily API cost limit (HTTP 402, $80/day).** State at resume (12:35, read-only): Fable had finished reading items 1–5/7 and was mid-way through the code (no analysis written); CEILING2 had staged `tree/` on sat, nothing running; REPORTWRITER had copied `report/` back, no report file yet. **All three resumed by `SendMessage` at 12:36 UTC** with delta messages (what is done, what to verify, constraints unchanged). If they die again with 402, wait for the limit reset and repeat.
>
> **Previous handoff block (~11:20 UTC):** Read `.scratch/HANDOFF-2026-09-11.md` first. At handoff (~11:20 UTC) the only live agent is
> **no agent**. CEILING (`a6bc6cea99e44c3fc`) was stopped ~12:10 UTC before writing anything (re-dispatch per HANDOFF §6b Q1 if still wanted). **CF3PILOT has COMPLETED** (commit `01739a74`); the pilot report is produced by the
> detached post-job on `sat` (PID 3438182) into `ws/report/`; the final `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md` must be
> written by a fresh agent per `.scratch/cf3-pilot/TAKEOVER.md` §4 — **after** the blind part of the validity audit (HANDOFF §2b).

Last updated: 2026-09-11 ~09:35Z UTC (after the THIRD usage-limit reset; all four agents resumed). **Read this first after a session restart, a usage limit, or a crash.**

## FIRST THING AFTER A RESTART — the four live agents and their ready-to-send resume messages

Check each workspace's `PROGRESS.md` first; then send the block below **verbatim** to each agentId
still unfinished. **CF3PILOT first** — it is the critical path; its dependency (`READY FOR PILOT: 363845e8`) is already met.

**1. B0CORRECT `a1f2ae507b9ec7674` — COMPLETED, do not resume.** — `.scratch/b0-corrected/PROGRESS.md`
> Resume B0CORRECT after a usage limit. Read your `PROGRESS.md` and continue from the last completed
> step; do not redo completed steps; check for your detached `sat` processes before relaunching.
> Priority order (unchanged): (1) PENALTYARM's port as its own commit, then your D-2/D-3/fixup onto
> `wip/multi-catfish-v023-20260907`, no history rewriting; (2) D-1 behind a flag, default eq. (16),
> W-08 assertions restored; (3) D-2 per-step worst-served floor; (4) pin one TLE archive by sha256 on
> both hosts, RANDOM_MASKED bit-identical on both; then write the top line
> `READY FOR PILOT: <sha> ; TLE archive <path> sha256 <hash>`. **Items 1-4 DONE (09:06Z). Item 5 (reruns)
> SKIPPED by controller** — just finalise the report (incl. which figures used the unpinned archive) and stop.

**2. CF3PILOT `a6a39605fae28be63` — COMPLETED, do not resume.** — `.scratch/cf3-pilot/PROGRESS.md`, server `/home/sat/mcrl-v025-cf3-pilot-ws`
> (historical) Resume CF3PILOT after a usage limit. **Amendment 1 (`V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md`)
> supersedes conflicting parts of the declaration: gamma=1, common vector replay 8/9 + 1/27 x3, eta fixed to ep 500,
> pinned-archive source rollout before launch, C2 activation logging, isolated worktree `cf3/pilot-20260911`.**
> Read your `PROGRESS.md` and continue from the last completed
> step; check by cwd and command line whether any detached training/eval process of yours is still
> running on `sat` before relaunching anything — **never relaunch a run that is still alive**, and
> never restart a finished seed. The design is frozen in
> `V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md` (+ your
> `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md`). Do not launch until `READY FOR PILOT:` exists in
> `.scratch/b0-corrected/PROGRESS.md`. List any sub-agents you spawned in `PROGRESS.md`.

**3. CFSCREEN `af73f19801f7967c8` — COMPLETED, do not resume.** — `.scratch/catfish-screens/PROGRESS.md`
> Resume CFSCREEN after a usage limit. Read your `PROGRESS.md`, continue from the last completed
> screen, do not redo completed screens. Results are diagnostics, not gates. Report to
> `.scratch/catfish-screens/CATFISH-SCREENS-2026-09-11.md`. List any sub-agents you spawned.

**4. CURATE `a989dbbca3b5748b8` — COMPLETED, do not resume.** — `.scratch/curation/PROGRESS.md`
> Resume CURATE after a usage limit. Read your `PROGRESS.md`, continue from the last completed
> section. Create new files only — do not move, rename, delete or edit existing files. Deliverables:
> `.scratch/RESULTS-REGISTRY.md`, `.scratch/DOCUMENT-STATUS.md`, `.scratch/curation/PROVENANCE-HEADER.md`.
> List any sub-agents you spawned.

**`fork` sub-agents** `a4644bab74d559124`, `a35d4634cf4c5439e`, `a360dd6a762afdefe` were **spawned by CURATE**
(confirmed in `.scratch/curation/PROGRESS.md`; they write `rows-A/B/C.md` to the session scratchpad).
All three were killed by the third limit; CURATE was told to finish their parts itself, not re-fork. **Do not
resume a fork directly; resume its parent**, which knows what it needs. If no parent claims one,
leave it.

**Standing corrections a *fresh* replacement agent must be given** (a resumed one already has them):
- CF3PILOT / anything evaluating: TLE archive must be the pinned one; cross-host numbers are
  incomparable; final checkpoint only; C-H `H_inter <= 0.6016`, C-S −0.5 pp.
- Anything citing numbers: read `.scratch/RESULTS-REGISTRY.md` (**landed**, 503 rows) and `.scratch/DOCUMENT-STATUS.md` (in-force reading list); the
  −425,009.885 bit/J beam slope is **V0.25-only**; sibling numbers are **REFERENCE-ONLY**.
- Success gate is **beating baseline MODQN (eq. 16)**; non-learned rules are diagnostic, never a bar.

## How to resume a Claude sub-agent

Claude sub-agent transcripts persist. Resume with `SendMessage(to=<agentId>, message=...)` — it
continues with its full context. Before sending, check its workspace for `PROGRESS.md` and its
report, so the message can say exactly what is already done. Template:

> Resume <NAME>: the controlling session was interrupted at <time>; it is now <time>. Read your own
> `PROGRESS.md` in <workspace> and continue from the last completed step. Do not redo completed steps.
> Check whether any detached server process you launched is still running (by cwd and command line)
> before relaunching anything. All original constraints still hold.

If a transcript cannot be resumed, dispatch a fresh agent with the original prompt **plus** the
instruction to read `PROGRESS.md` first — the checkpoint file is what makes that possible.

**Third usage-limit interruption 2026-09-11 ~09:25Z UTC.** All four live agents and CURATE's three forks
terminated. State at resume: B0CORRECT had posted `READY FOR PILOT: 363845e8` + pinned TLE archive `427e6a91…`;
CF3PILOT was still at step 0 (reading) with nothing on `sat`. All four resumed by `SendMessage`; B0CORRECT told to
skip its optional reruns and finalise; CF3PILOT given the early-stop check again in case it was not delivered.
**New standing fact:** everything built on the catfish-surface harness ran on the UNPINNED archive `e07f3e1e…` and
is not comparable to pinned-archive numbers.

## Running — Claude sub-agents

| name | agentId | workspace | report (first line = verdict) | current task |
|---|---|---|---|---|

**Second usage-limit interruption 2026-09-11 ~09:30Z.** POWERACCT and PENALTYARM were
terminated; FEASFRONT and B0CORRECT survived. Both terminated agents resumed by
`SendMessage`. PENALTYARM's resume message also carried two coordination notes (B0 tree,
`max`-accounting caveat) — **re-send those if it is ever replaced by a fresh agent.**

Completed today and not to be resumed: LFDSCREEN, ENDPOINTREV-astra, C1VSGAIN,
SPECPROFILE, CATFISHSURFACE, ZCLOSE, ZWHY, R23HISTORY, DQFDGROUND, CATFISHFACT,
**ACRMSOURCE** `ae8b8402e12022648` (`.scratch/acrm-provenance/ACRM-PROVENANCE-2026-09-11.md`), **POWERACCT** `ab622bcc795b950d8` (`.scratch/beam-power-accounting/BEAM-POWER-ACCOUNTING-2026-09-11.md`), **PENALTYARM** `a846df68eb09cb7ab` (`.scratch/penalty-arm/PENALTY-ARM-2026-09-11.md`; server ws is `mcrl-v025-penalty-arm-ws`), **FEASFRONT** `a295ca3c20644fd7b` (`.scratch/feasible-frontier/FEASIBLE-FRONTIER-2026-09-11.md`), **EEGAP** `a774b381a016fc9c4` (`.scratch/ee-magnitude/EE-MAGNITUDE-RECONCILIATION-2026-09-11.md`), **HARVEST** `ad98bdcb7c81b29a0` (`.scratch/concept-harvest/CONCEPT-HARVEST-2026-09-11.md`), **CAPPENALTY** `aec999753c170e5f3` (`.scratch/cap-penalty/CAP-PENALTY-2026-09-11.md`), **CFSCREEN** `af73f19801f7967c8` (`.scratch/catfish-screens/CATFISH-SCREENS-2026-09-11.md`), **B0CORRECT** `a1f2ae507b9ec7674` (`.scratch/b0-corrected/B0-CORRECTED-BASELINE-2026-09-11.md`, commit `db30b334`; READY `363845e8`; TLE pinned `427e6a91…`), **CURATE** `a989dbbca3b5748b8` (`.scratch/RESULTS-REGISTRY.md`, `.scratch/DOCUMENT-STATUS.md`), **CF3REVIEW** `af8d412c9162118a5` (`.scratch/cf3-review/CF3-CODE-REVIEW-2026-09-11.md`: 0 INVALIDATES, 1 BIASES — stale report script on sat).

**Usage-limit interruption 2026-09-11 ~04:20Z.** All five running agents were terminated
mid-task by an HTTP 429 session limit; four were resumed by `SendMessage` after the reset
and continued from their `PROGRESS.md`. This is the protocol working — record it as the
precedent. **OOSPANEL** `a4a1ff602a3b13275` was **not** resumed: its out-of-sample panels
are conditional on C1 surviving C1VSGAIN, so it is held until that gate returns. Its
workspace `/home/sat/mcrl-v025-oospanel-ws` and `PROGRESS.md` are intact; re-dispatch with
the original prompt plus "read `PROGRESS.md` first" if the gate goes C1's way.

Every one of these has a pre-declared reading of its outcome written **before** it runs —
see the ruling and declaration files in `.scratch/multi-catfish-v025-physics-successor/`.
A resumed agent keeps its full context, so a resume message states only the delta.

Corrections issued to running agents after erratum 23 (must be re-sent if an agent is
replaced by a fresh one): C1VSGAIN and SPECPROFILE were both told that **62.502712 is the
`CAP_050` boundary-0 search winner, not a declared rule**; the strongest **declared** rule
at C=50 is **52.042303**; and **41.28 is a mean active-beam count, not an EE**.

## Paused / stopped (2026-09-11 ~01:16Z, owner instruction on cost)

- **SEEDPAR** agent `a795bc9610ed76c65` STOPPED; its 8 training processes + sequential PID 3131678 are
  **SIGSTOPped** (state T). Resume the processes with `kill -CONT`, resume the agent with SendMessage;
  its `/home/sat/mcrl-v025-seedpar-ws/PROGRESS.md` and `scripts/helper_chain.sh` hold the plan.
- **EXACTTRAIN2** and **Q1V3TRAIN** (codex): trainings and drivers SIGSTOPped.
- Resume/kill rule: `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md`, decided by C1VSGAIN.
  **Decided: row 3, KILL ALL** (`V025-CONTROLLER-RULING-C1VSGAIN-KILL-ALL-2026-09-11.md`).
  **EXECUTED 2026-09-11 ~07:55Z with owner authorisation**: 44 processes + PID 3131678 (SEEDPAR's
  sequential stage-C run, cwd `exact93-ws` — wrongly excluded earlier, see
  `V025-CONTROLLER-DECLARATION-CONSTRAINED-ENDPOINT-2026-09-11.md`). Zero stopped processes remain.
- **SOLO** `aad297dbf1b91554c`, **TRIOBJ** `aac6285bfb87e962d` STOPPED as obsolete (not to resume).
- **MULTISTEP** `aa086e16457bc9f4c` and **HCELL** `a3b6026f8954242c5` STOPPED 2026-09-11 ~13:30Z
  as no longer matching the direction (C2 continuation abandoned; handover interruption not
  core). Not to resume without a new reason. **C3REACH** `a93a81aafe6ff06f7` stopped earlier
  (premise evaporated).

## Running — other model families

| name | how it runs | resume |
|---|---|---|
| **CF3-AGY-2** | agy Gemini 3.8 Flash (High), cwd `.scratch/reviews/cf3-agy-2` | **COMPLETED: 0 INVALIDATES, 0 BIASES → GO given ~11:15 UTC.** Reviewed diff `e8a04ccf..f297334e`. Not resumable — if `CF3-AGY-REVIEW-2.md` is absent, re-run `agy -p "$(cat PROMPT.md)" --dangerously-skip-permissions --model "Gemini 3.8 Flash (High)" --print-timeout 60m </dev/null` in that dir |
| **CF3-AGY** | agy Gemini 3.8 Flash (High) | **COMPLETED** — `.scratch/reviews/cf3-agy/CF3-AGY-REVIEW.md`: 0 INVALIDATES, 0 BIASES |
| XBLIND-ASTRA | codex `gpt-6-astra` ultra, server, `run_resumable2.sh`; ws `/home/sat/mcrl-v025-xblind-astra-ws` | **auto** — the runner resumes its codex session on failure; check `chain.log` |
| XADV-ASTRA | same; ws `/home/sat/mcrl-v025-xadv-astra-ws` | auto |
| agy blind | `agy -p ... --model "Gemini 3.8 Flash (High)" --print-timeout 60m`, local, cwd `.scratch/reviews/agy-blind` | **not resumable** — if `BLIND-REVIEW.md` is absent, re-run the same command |
| agy adversary | same, cwd `.scratch/reviews/agy-adversary` | re-run if `ADVERSARY-REVIEW.md` is absent |

Long server compute launched by any agent is detached (`setsid nohup`) and survives the agent.
The server health monitor labels such processes `UNOWNED-BUT-WORKING :: DO NOT KILL`.

## Completed (for reference)

EXACT93 `a30e930829944c569` · RAWDUP `a2c0a8e01e8945947` · ZSCORE-SCORE `ac3aadfd88c9d995d` ·
CONVSCORE `a5cfd73bdf2c2cd83` · ETAFIX `afc99c03b4bda2f2e` · C2TARGET `a4bf94ec75e752e2e` ·
Q1V4 `a078dfa0019061e54` · QCOLLINEAR `a85190aaabc698990` · BLIND `ab2b10931331b1b0c` · ADVERSARY `a4228d7117ff1cced` · MODQNZ (codex, stopped after decisive pair) · XBLIND-ASTRA · XADV-ASTRA · agy blind · agy adversary ·
BEAMCOUNT `ab265b1f2c82f21d9` (`/home/sat/mcrl-v025-beamcount-ws/BEAM-COUNT-CAP-2026-09-10.md`) ·
CATFISHFACT `a47a739890d0f71c2` (`.scratch/catfish-facts/CATFISH-MECHANISM-FACTS-2026-09-11.md`) ·
DQFDGROUND `a607d537e44ffdffb` (`.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md`) ·
R23HISTORY `a18c130ee37778407` (`.scratch/reward-history/R2-R3-CHANGE-HISTORY-2026-09-11.md`) ·
ZWHY `a052c52941f6c5fb4` (`.scratch/zscore-transfer/ZSCORE-TRANSFER-2026-09-11.md`) ·
REPORTWRITER `f508c755-8fc6-4503-9548-0225a1607848` (`.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`).

A completed agent is still resumable by `SendMessage` to its agentId — CATFISHSURFACE was
resumed twice this way and produced its most important findings on the second resume.

## Monitors to re-arm after a restart

- ~~codex chain completions~~ — **stopped 2026-09-11** (owner: no codex for now). Do not re-arm.
- server health: `tail -F /home/sat/bigtmp/watch_health.log | grep LOAD HIGH|MEMORY LOW|^ORPHAN|ENOSPC`
