#!/bin/bash
# Deliver the local WIP branch head to a SEPARATE server checkout for the C3 existence screen E1,
# without touching the pipeline worktree /home/sat/mcrl-leo-handover-wip (single-writer rule).
# Usage: bash sync_server_e1_checkout.sh   (repo root; local branch committed)
set -euo pipefail
BR=wip/multi-catfish-v023-20260907
R=/home/sat/mcrl-leo-handover            # original clone: object store only; its tree and .venv are never modified
E=/home/sat/mcrl-leo-handover-e1         # E1 checkout (git worktree of R on its own branch)
EBR=e1/multi-catfish-v023-20260908
LOCAL=$(git rev-parse HEAD)
B=$(mktemp /tmp/e1-inc-XXXXXX.bundle)
if ssh -o ConnectTimeout=25 sat "test -d $E/.git || test -f $E/.git"; then
  REMOTE=$(ssh -o ConnectTimeout=25 sat "git -C $E rev-parse HEAD")
  if [ "$LOCAL" = "$REMOTE" ]; then echo "SERVER_E1_CHECKOUT_UP_TO_DATE $LOCAL"; rm -f "$B"; exit 0; fi
  git bundle create "$B" "$REMOTE..$BR" >/dev/null 2>&1
  scp -q "$B" sat:/home/sat/e1-inc.bundle
  ssh -o ConnectTimeout=25 sat "set -e; git -C $R bundle verify /home/sat/e1-inc.bundle >/dev/null; git -C $R fetch -q /home/sat/e1-inc.bundle $BR:refs/remotes/bundle-e1/$BR; git -C $E merge -q --ff-only refs/remotes/bundle-e1/$BR; git -C $E log --oneline -1; echo porcelain=\$(git -C $E status --porcelain | wc -l)"
else
  BASE=$(ssh -o ConnectTimeout=25 sat "git -C $R rev-parse --verify -q refs/remotes/bundle/$BR || git -C $R rev-parse HEAD")
  git bundle create "$B" "$BASE..$BR" >/dev/null 2>&1 || git bundle create "$B" "$BR" >/dev/null 2>&1
  scp -q "$B" sat:/home/sat/e1-inc.bundle
  ssh -o ConnectTimeout=25 sat "set -e; git -C $R bundle verify /home/sat/e1-inc.bundle >/dev/null; git -C $R fetch -q /home/sat/e1-inc.bundle $BR:refs/remotes/bundle-e1/$BR; git -C $R worktree add -q -b $EBR $E refs/remotes/bundle-e1/$BR; git -C $E log --oneline -1; echo porcelain=\$(git -C $E status --porcelain | wc -l)"
fi
rm -f "$B"
echo "SERVER_E1_CHECKOUT_SYNCED $LOCAL"
