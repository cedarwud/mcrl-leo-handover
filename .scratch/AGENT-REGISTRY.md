# Agent registry — resume after any interruption

Last updated: 2026-09-11 ~09:40Z (after the second usage-limit reset). **Read this first after a session restart, a usage limit, or a crash.**

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

## Running — Claude sub-agents

| name | agentId | workspace | report (first line = verdict) | current task |
|---|---|---|---|---|
| **B0CORRECT** | `a1f2ae507b9ec7674` | local `.scratch/b0-corrected` + `/home/sat/mcrl-v025-b0-ws` | `B0-CORRECTED-BASELINE-2026-09-11.md` | **resumed** — D-1 behind a flag (default eq.16, B1 stands), D-2 per-step floor, pin TLE archive across hosts, commit PENALTYARM port separately, merge b0 branch, rerun BASELINE_EQ16 + SHARED_BOOTSTRAP pilots |
| **CURATE** | `a989dbbca3b5748b8` | local `.scratch/curation` | `.scratch/RESULTS-REGISTRY.md`, `.scratch/DOCUMENT-STATUS.md` | read-mostly: provenance registry of every citable number, cross-condition comparisons in in-force docs, in-force reading list. Creates new files only |
| **CFSCREEN** | `af73f19801f7967c8` | local `.scratch/catfish-screens` | `CATFISH-SCREENS-2026-09-11.md` | zero-training: representability (BC probe), action/state distinctness of C1/C2/C3 sources, margin scale |

**Second usage-limit interruption 2026-09-11 ~09:30Z.** POWERACCT and PENALTYARM were
terminated; FEASFRONT and B0CORRECT survived. Both terminated agents resumed by
`SendMessage`. PENALTYARM's resume message also carried two coordination notes (B0 tree,
`max`-accounting caveat) — **re-send those if it is ever replaced by a fresh agent.**

Completed today and not to be resumed: LFDSCREEN, ENDPOINTREV-astra, C1VSGAIN,
SPECPROFILE, CATFISHSURFACE, ZCLOSE, ZWHY, R23HISTORY, DQFDGROUND, CATFISHFACT,
**ACRMSOURCE** `ae8b8402e12022648` (`.scratch/acrm-provenance/ACRM-PROVENANCE-2026-09-11.md`), **POWERACCT** `ab622bcc795b950d8` (`.scratch/beam-power-accounting/BEAM-POWER-ACCOUNTING-2026-09-11.md`), **PENALTYARM** `a846df68eb09cb7ab` (`.scratch/penalty-arm/PENALTY-ARM-2026-09-11.md`; server ws is `mcrl-v025-penalty-arm-ws`), **FEASFRONT** `a295ca3c20644fd7b` (`.scratch/feasible-frontier/FEASIBLE-FRONTIER-2026-09-11.md`), **EEGAP** `a774b381a016fc9c4` (`.scratch/ee-magnitude/EE-MAGNITUDE-RECONCILIATION-2026-09-11.md`), **HARVEST** `ad98bdcb7c81b29a0` (`.scratch/concept-harvest/CONCEPT-HARVEST-2026-09-11.md`), **CAPPENALTY** `aec999753c170e5f3` (`.scratch/cap-penalty/CAP-PENALTY-2026-09-11.md`).

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
ZWHY `a052c52941f6c5fb4` (`.scratch/zscore-transfer/ZSCORE-TRANSFER-2026-09-11.md`).

A completed agent is still resumable by `SendMessage` to its agentId — CATFISHSURFACE was
resumed twice this way and produced its most important findings on the second resume.

## Monitors to re-arm after a restart

- codex chain completions: `tail -F /home/sat/mcrl-v023-codex-audits/parallel-20260909/chain.log | grep finished|FAIL|attempt [2-9]`
- server health: `tail -F /home/sat/bigtmp/watch_health.log | grep LOAD HIGH|MEMORY LOW|^ORPHAN|ENOSPC`
