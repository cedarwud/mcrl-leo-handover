# Task (gpt-5.6-sol): stage-A launcher fix pass 12 — local-host tmux controller start is mis-quoted (engineering only)

Workspace: `/home/sat/mcrl-v023-codex-ws-stagea-fix12` (clone of the wip worktree at commit `f165e969`), branch `stagea/fix12`. Do not touch `/home/sat/mcrl-leo-handover-wip` or any other checkout, any sealed/read-only file, `*.sha256`, or anything under `docs/`. Commit at the end and write `FIX12-DONE` (containing the commit id) in the workspace root.

## The defect (verbatim from the operator's STOP note)
`.scratch/multi-catfish-v023-c1c2-successor-launch/sync_launch_v023_c1c2_successor_server.sh`:
```sh
run_remote() {
  if ((local_host)); then
    bash -c "$1"          # <-- local path (V023_SUCCESSOR_SERVER_HOST=local, added in fix pass 10)
  else
    ssh -- "$server_host" "$1"
  fi
}
```
The tmux-controller command string `$1` embeds an unescaped nested double-quoted `python -c "import json,os; p='…/SUCCESSOR-STARTUP.json'; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); …"` inside the already double-quoted `tmux new-session -d -s '<name>' "set -Eeuo pipefail; …"` argument. Under `bash -c "$1"` the inner `"` closes the string early and bash parses `os.open(p,os.O_WRONLY|…)` as shell → `syntax error near unexpected token '('` → `SUCCESSOR_LAUNCH_REFUSED: tmux source-training controller failed to start`. Everything before it passed (bindings, launch manifest, learner manifest, preflight, one-epoch diagnostic). The dry-run mode did not catch it because it never assembles/executes the controller start.

## Required fix (smallest, behaviour-preserving)
1. Build the tmux-controller body as a **transient script file** inside the transported checkout (e.g. `<checkout>/successor-controller-<session>.sh`, mode 0700, created with O_EXCL, content = the exact `set -Eeuo pipefail; …` program that was previously inlined, with the python `-c` snippet moved into a heredoc-safe form or a tiny helper script), and start it with `tmux new-session -d -s '<name>' "bash '<abs path to script>'"`. Use the SAME mechanism for both the local path and the ssh path so they cannot diverge again (for ssh, transport the script with the checkout or write it via a single-quoted heredoc; keep `printf %q` quoting for any interpolated path).
2. Record the controller script's sha256 in the startup receipt/log line that already reports the tmux session start, so the receipt binds what actually ran.
3. Do NOT change: any science, the training/verification commands and their argument order, output paths, the write-once semantics (`SUCCESSOR-STARTUP.json` O_EXCL), the receipts' schemas, the `--dry-run` semantics, or the existing gate. If the launch manifest / bindings digest the launcher file itself, say so in the report (the operator will re-run the binder as part of the replay).
4. **Offline tests that would have caught this class** (add to the launch package's test file): (a) assemble the controller program for a synthetic checkout and run `bash -n` on it; (b) actually start a tmux session in a temporary `TMUX_TMPDIR` with `V023_SUCCESSOR_SERVER_HOST=local` and stubbed python/paths, and assert the controller script ran to its first log line and the startup receipt appeared; (c) a shell-quoting regression: a path containing a space and a single quote must still work. Keep the full test file under 2 minutes.
5. Run the launch package's complete test suite with `/home/sat/mcrl-leo-handover/.venv/bin/python -m pytest` (thread env vars = 1) and paste the summary line into `.scratch/multi-catfish-v023-c1c2-successor-launch/FIX12-REPORT-2026-09-08.md` together with: the diff summary, whether any digest-bound file changed (list them), and the exact operator replay steps (bind --write/--check → launch manifest --write/--check → gate `--reuse-from …fix11` → step 3 dry-run → real launch).

Constraints: no `sys.modules` aliasing; OMP/BLAS thread vars 1; no TEST split; nothing outcome-driven; `ALL_NEUTRAL_CONTROL` never relabelled `BASELINE`.
