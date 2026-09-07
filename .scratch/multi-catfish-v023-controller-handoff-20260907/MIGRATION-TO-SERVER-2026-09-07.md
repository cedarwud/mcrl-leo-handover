# Migrating the controller to the server (2026-09-07, owner's instruction 18:20 UTC)

Goal: once the local sub-agents finish, the controller session itself runs on `sat` inside tmux, so training and
the remaining engineering-lane work continue when the local machine is off. Everything is committed and pushed to
`origin/wip/multi-catfish-v023-20260907`; the server works from a git worktree of that branch.

## What moves, what stays
- **Moves:** the controller session (Claude Code on `sat`, already installed: 2.1.193), codex tasks (codex installed and
  logged in on `sat`), all server runs (already there), monitors (re-armed from the server session).
- **Stays local (optional):** agy (Gemini) is not installed on `sat`; if needed, run its read-only reviews locally later or
  install it there. Files > 10 MB are not in git (`GIT-EXCLUDED-LARGE-FILES-2026-09-07.tsv`); the successor chain's
  246-path closure contains none of them, so the worktree is complete for stage A/B/C and F1–F3. Rsync individual large
  artifacts on demand.

## Server layout (do not disturb running roots)
- `/home/sat/mcrl-leo-handover` — original clone at `42a8247 init`; its `.venv` is the interpreter every server script
  uses (`/home/sat/mcrl-leo-handover/.venv/bin/python`). Leave this checkout as is (the venv's editable install points
  here; scripts set `PYTHONPATH` to their own checkout).
- `/home/sat/mcrl-leo-handover-wip` — NEW git worktree of `wip/multi-catfish-v023-20260907` (created by
  `git -C /home/sat/mcrl-leo-handover fetch origin && git -C /home/sat/mcrl-leo-handover worktree add
  /home/sat/mcrl-leo-handover-wip wip/multi-catfish-v023-20260907`). This is the controller's working tree on the
  server: commit here, push from here. `PYTHONPATH=/home/sat/mcrl-leo-handover-wip/src` for anything run from it.
- `/home/sat/mcrl-v023-successor-shadow-20260907` — engineering-lane shadow (rsync target); after migration, sync
  direction becomes worktree → shadow (same rule: one writer per path, local→server only until the local session ends).
- Running/sealed roots: `…-c1c2-targets-20260907-ops3-r8*` (r8), `…-c3-contingency-f1-20260907-r2` (F1 replay),
  `…-lcsrs-gate-20260906-r7-i1` (sealed R7) — never written by the controller.

## Start the server controller (owner runs these once; then the local session can be closed)
```bash
ssh sat
tmux new -s mcrl-controller
cd /home/sat/mcrl-leo-handover-wip
claude            # first time: complete the login prompt in the terminal
# then paste the contents of:
#   .scratch/multi-catfish-v023-controller-handoff-20260907/CONTINUATION-PROMPT-2026-09-07.md
# (or start with:  claude "$(cat .scratch/multi-catfish-v023-controller-handoff-20260907/CONTINUATION-PROMPT-2026-09-07.md)")
```
Detach with `Ctrl-b d`; reattach with `tmux attach -t mcrl-controller`.

## Handover checklist (local controller, before closing)
1. Wait for local codex tasks to finish (fix pass 5, stage-C chunking); verify, commit, push.
2. Update `CONTINUATION-PROMPT-2026-09-07.md` (server paths, worktree, "you are on sat now" section) and push.
3. On the server: worktree up to date (`git -C /home/sat/mcrl-leo-handover-wip pull --ff-only`), `claude` authenticated,
   `codex` works, shadow checkout synced from the worktree.
4. Re-arm server-side watchers from the new session (r8 terminal shards / COMPLETE, F1 r2 tmux, shadow verifier log).
5. Local monitors die with the local session — nothing depends on them once the server session is up.
