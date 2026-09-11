# Agent registry — resume after any interruption

Last updated: 2026-09-11 ~00:50Z. **Read this first after a session restart, a usage limit, or a crash.**

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

| name | agentId | workspace | report (first line = verdict) |
|---|---|---|---|
| SOLO | `aad297dbf1b91554c` | `/home/sat/mcrl-v025-solo-ws` | `SOLO-ROUTES-2026-09-11.md` |
| TRIOBJ | `aac6285bfb87e962d` | `/home/sat/mcrl-v025-triobj-ws` | `TRI-OBJECTIVE-FEASIBILITY-2026-09-11.md` |
| MULTISTEP | `aa086e16457bc9f4c` | `/home/sat/mcrl-v025-multistep-ws` | `MULTISTEP-ENDPOINT-2026-09-11.md` |
| C3REACH | `a93a81aafe6ff06f7` | `/home/sat/mcrl-v025-c3reach-ws` | `C3-REACH-2026-09-11.md` |
| OOSPANEL | `a4a1ff602a3b13275` | `/home/sat/mcrl-v025-oospanel-ws` | `OOS-PANELS-2026-09-11.md` |
| SEEDPAR | `a795bc9610ed76c65` | `/home/sat/mcrl-v025-seedpar-ws` | `SEEDPAR-2026-09-11.md` |
| BEAMCOUNT | `ab265b1f2c82f21d9` | `/home/sat/mcrl-v025-beamcount-ws` | `BEAM-COUNT-CAP-2026-09-10.md` |
| HCELL | `a3b6026f8954242c5` | `/home/sat/mcrl-v025-hcell-ws` | `H-CELL-EFFECT-2026-09-11.md` |
| BLIND (Claude) | `ab2b10931331b1b0c` | local `.scratch/reviews/` | `BLIND-CLAIM-STRUCTURE-2026-09-11.md` |
| ADVERSARY (Claude) | `a4228d7117ff1cced` | local `.scratch/reviews/` | `ADVERSARY-NARRATIVE-2026-09-11.md` |

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
Q1V4 `a078dfa0019061e54` · QCOLLINEAR `a85190aaabc698990`.

## Monitors to re-arm after a restart

- codex chain completions: `tail -F /home/sat/mcrl-v023-codex-audits/parallel-20260909/chain.log | grep finished|FAIL|attempt [2-9]`
- server health: `tail -F /home/sat/bigtmp/watch_health.log | grep LOAD HIGH|MEMORY LOW|^ORPHAN|ENOSPC`
