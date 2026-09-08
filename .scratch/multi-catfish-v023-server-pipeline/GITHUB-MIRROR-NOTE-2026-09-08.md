# GitHub mirror branch (2026-09-08)
GitHub rejects files > 100 MB. The working branch `wip/multi-catfish-v023-20260907` contains two 106 MB copies of the sealed r8 receipt
(controller copy under `r8-sealed-receipts/`, and the fix-pass-10 test fixture `tests/fixtures/r8-receipt.json`). The working branch is
shared with every server checkout (wip / e1 / v024 / codex/*) and is NOT rewritten. For GitHub, a filtered mirror branch
`gh/wip-multi-catfish-v023-20260907` is produced with `git filter-repo --invert-paths` on those two paths only (all other content and the
commit graph are otherwise identical; the commit ids differ). Push it with:
    git push -u origin gh/wip-multi-catfish-v023-20260907
The sealed receipt itself lives on the server root `/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8/` (sha256 e9f84526…).
Regenerate the mirror after new commits: clone the repo into a scratch dir, run the same two filter-repo commands, fetch the branch back.
