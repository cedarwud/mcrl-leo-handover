#!/usr/bin/env bash
# After stage-C fix pass 6 is committed on the server workspace branch codex/stagec-fix6: fetch, merge, re-pin the stage-C code
# manifest on the merged tree, refresh the supersession record digests, commit. Then the controller launches the second ultra review.
set -euo pipefail
B=.scratch/multi-catfish-v023-c1c2-successor-stagec-launch
git fetch -q ssh://sat/home/sat/mcrl-v023-codex-ws-stagec-fix6 codex/stagec-fix6:refs/remotes/sat-codex/stagec-fix6
git merge -q --no-edit -m "merge stage-C fix pass 6 (codex/stagec-fix6; ultra delta review items 1-10)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" refs/remotes/sat-codex/stagec-fix6
PYTHONPATH=$PWD/src .venv/bin/python $B/build_v023_c1c2_successor_stagec_manifest.py --write | tail -1
PYTHONPATH=$PWD/src .venv/bin/python $B/build_v023_c1c2_successor_stagec_manifest.py --check | tail -1
NEW=$(sha256sum $B/V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256 | cut -c1-64); N=$(grep -c . $B/V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256)
R=.scratch/multi-catfish-v023-c1c2-successor/STAGEC-CODE-MANIFEST-SUPERSESSION-2026-09-08.md
printf '\n## Re-pin after fix pass 6 (%s UTC)\nSuccessor manifest after fix pass 6: entries %s, file sha256 `%s` (commit %s). The 907bc753… pin was never bound (ultra review FIX_FIRST). Second scoped ultra review requested against this digest.\n' "$(date -u +%FT%TZ)" "$N" "$NEW" "$(git rev-parse --short HEAD)" >> "$R"
git add -A -- $B .scratch/multi-catfish-v023-c1c2-successor-physical-evaluation .scratch/multi-catfish-v023-ch5-figure-pipeline .scratch/multi-catfish-v023-two-route-source-training-runner .scratch/multi-catfish-v023-c1c2-successor
git commit -q -m "stage-C code manifest re-pinned after fix pass 6 (entries $N, $NEW)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
echo "LANDED $(git rev-parse --short HEAD) manifest=$NEW entries=$N"
