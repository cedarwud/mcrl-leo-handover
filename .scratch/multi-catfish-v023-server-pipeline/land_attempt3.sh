#!/usr/bin/env bash
# Run ONLY after ASTRA_STAGEC_CODE_FINAL=YES on the current tree. Removes attempt #2's never-run binder outputs from the wip
# worktree (recorded), fast-forwards the worktree to local HEAD, verifies cleanliness, and prints the operator hand-off line.
set -euo pipefail
W=/home/sat/mcrl-leo-handover-wip
LOCAL=$(git rev-parse HEAD)
ssh -o BatchMode=yes sat "cd $W && echo '== before' && git status --porcelain && git checkout -q -- .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-LAUNCH-MANIFEST.json.sha256 && rm -f .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-EXECUTION-BINDINGS.json .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-EXECUTION-BINDINGS.json.sha256 .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-LEARNER-MANIFEST.json .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-PROVIDER-CONFIG.json .scratch/multi-catfish-v023-c1c2-successor-launch/V023-C1C2-SUCCESSOR-PROVIDER-CONFIG.json.sha256 && echo '== after cleanup porcelain lines:' && git status --porcelain | wc -l"
bash .scratch/multi-catfish-v023-controller-handoff-20260907/sync_server_worktree.sh | tail -1
ssh -o BatchMode=yes sat "cd $W && echo HEAD=\$(git rev-parse HEAD) porcelain=\$(git status --porcelain | wc -l) && PYTHONPATH=$W/src /home/sat/mcrl-leo-handover/.venv/bin/python .scratch/multi-catfish-v023-c1c2-successor-stagec-launch/build_v023_c1c2_successor_stagec_manifest.py --check | tail -1"
echo "ATTEMPT3_READY local=$LOCAL — dispatch prompts/operator-stagea-attempt3.md with <<HEAD_AFTER_FIX10_LANDS>> = $LOCAL"
