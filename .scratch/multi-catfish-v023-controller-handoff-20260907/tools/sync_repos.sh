#!/usr/bin/env bash
# GitHub is the hub. Local has no GitHub credential, so it talks to GitHub through the server bare relay (ssh):
#   local wip ──push──▶ relay (/home/sat/mcrl-gh-mirror.git) ──push──▶ GitHub origin
#   server workspaces ──push (server has credentials)──▶ GitHub  ;  local ◀──fetch── relay ◀──fetch── GitHub
#   server records reader: /home/sat/mcrl-hub (clone of GitHub wip) — `git pull` before any server job reads records.
# History was rewritten once on 2026-09-08 (two >100 MB blobs dropped); commit map in tools/history-rewrite-commit-map-2026-09-08.txt.
set -u
LOCAL=/home/u24/papers/mcrl-leo-handover; WIP=wip/multi-catfish-v023-20260907; cd $LOCAL
echo "== 1. local -> relay -> GitHub ($WIP)"
git push -q relay "+refs/heads/$WIP:refs/heads/$WIP" && ssh sat "cd /home/sat/mcrl-gh-mirror.git && git push -q origin refs/heads/$WIP:refs/heads/$WIP 2>&1 | grep -v '^remote:' | tail -1; git ls-remote --heads origin refs/heads/$WIP | cut -c1-10"
echo "== 2. server workspace branches -> GitHub (from each workspace; server credentials), then -> local via relay"
ssh sat 'for spec in "mcrl-v025-codex-ws-engine v025/engine" "mcrl-v025-codex-ws-provider v025/provider" "mcrl-v025-codex-ws-synth v025/synth" "mcrl-v023-codex-ws-c3s-baselines c3s/diagnostic-arms"; do set -- $spec; git -C /home/sat/$1 remote get-url github >/dev/null 2>&1 || git -C /home/sat/$1 remote add github https://github.com/cedarwud/mcrl-leo-handover.git; MAX=$(git -C /home/sat/$1 rev-list --objects $2 | git -C /home/sat/$1 cat-file --batch-check="%(objecttype) %(objectsize) %(rest)" | awk "\$1==\"blob\"{print \$2}" | sort -n | tail -1); if [ "$MAX" -lt 95000000 ]; then git -C /home/sat/$1 push -q --force github "refs/heads/$2:refs/heads/server/$2" 2>&1 | grep -v "^remote:" | tail -1; echo "  pushed $2 (max blob $MAX)"; else echo "  SKIP $2: history still holds a $MAX-byte blob (legacy workspace; migrate by re-cloning from GitHub)"; fi; done'
ssh sat 'cd /home/sat/mcrl-gh-mirror.git && git fetch -q origin "+refs/heads/server/*:refs/heads/server/*" "+refs/heads/'"$WIP"':refs/heads/'"$WIP"'"' && git fetch -q relay "+refs/heads/server/*:refs/heads/server/*" && git branch --list "server/*" | sed 's/^/  local /'
echo "== 3. server records reader"
ssh sat 'git -C /home/sat/mcrl-hub pull -q --ff-only && echo "  /home/sat/mcrl-hub at $(git -C /home/sat/mcrl-hub log --oneline -1 | cut -c1-60)"'
echo "== 4. receipts backup (server run outputs are not in git)"
ssh sat 'cd /home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen && tar czf /home/sat/diag-receipts-backup.tgz diag2-run-*/ diag3-run-*/ 2>/dev/null'; mkdir -p $LOCAL/artifacts/server-receipts-backup && scp -q sat:/home/sat/diag-receipts-backup.tgz $LOCAL/artifacts/server-receipts-backup/diag-receipts-backup-latest.tgz && echo "  backup copied"
echo "== done $(date -u +%FT%TZ)"
