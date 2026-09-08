#!/usr/bin/env bash
# Controller act: seal a candidate contract (C-A / C-B / C-C) body read-only + sha256 sidecar, commit, deliver to the server E1 checkout.
# Usage: bash seal_candidate_contract.sh <A|B|C>   — run ONLY after the candidate's implementation review says READY_TO_SEAL.
set -euo pipefail
ID=${1:?A|B|C}
C=.scratch/multi-catfish-v023-c3-existence-e1/candidates/V023-C3-CANDIDATE-$ID-CONTRACT-2026-09-08.md
test -f "$C" || { echo "contract missing: $C"; exit 2; }
test ! -e "$C.sha256" || { echo "sidecar already exists — refusing"; exit 2; }
D=$(sha256sum "$C" | cut -c1-64)
printf '%s  %s\n' "$D" "$(basename "$C")" > "$C.sha256"
chmod 0444 "$C" "$C.sha256"
echo "CANDIDATE_${ID}_CONTRACT_SEALED sha256=$D"
git add -- "$C" "$C.sha256"
git commit -q -m "candidate C-$ID contract sealed (controller): $D

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
bash .scratch/multi-catfish-v023-server-pipeline/sync_server_e1_checkout.sh | tail -1
echo "next on the server E1 checkout: chmod 0444 both files; build the candidate's preflight manifest; build its launch authority; --dry-run; run"
