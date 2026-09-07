#!/bin/bash
# Incremental sync of the local WIP branch to the server worktree via git bundle (no GitHub dependency).
# Usage: bash sync_server_worktree.sh   (run from the repo root; local branch must be committed)
set -euo pipefail
BR=wip/multi-catfish-v023-20260907
R=/home/sat/mcrl-leo-handover
W=/home/sat/mcrl-leo-handover-wip
LOCAL=$(git rev-parse HEAD)
REMOTE=$(ssh -o ConnectTimeout=25 sat "git -C $W rev-parse HEAD")
if [ "$LOCAL" = "$REMOTE" ]; then echo "SERVER_WORKTREE_UP_TO_DATE $LOCAL"; exit 0; fi
B=$(mktemp /tmp/wip-inc-XXXXXX.bundle)
git bundle create "$B" "$REMOTE..$BR" >/dev/null 2>&1
scp -q "$B" sat:/home/sat/wip-inc.bundle
ssh -o ConnectTimeout=25 sat "set -e; git -C $R bundle verify /home/sat/wip-inc.bundle >/dev/null; git -C $R fetch -q /home/sat/wip-inc.bundle $BR:refs/remotes/bundle/$BR; git -C $W merge -q --ff-only refs/remotes/bundle/$BR; git -C $W log --oneline -1; git -C $W status --porcelain | wc -l"
rm -f "$B"
echo "SERVER_WORKTREE_SYNCED $LOCAL"
