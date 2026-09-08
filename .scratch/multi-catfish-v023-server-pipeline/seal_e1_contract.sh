#!/usr/bin/env bash
# Controller act: seal the E1 contract (body read-only + sha256 sidecar in the runner's expected format), commit, deliver to the
# server E1 checkout, then build the preflight manifest + launch authority there and run --dry-run. Run ONLY after
# ASTRA_E1_IMPL=READY_TO_SEAL. Refuses if the contract or sidecar is already sealed/present.
set -euo pipefail
E1=.scratch/multi-catfish-v023-c3-existence-e1
C=$E1/V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md
test -f "$C" || { echo "contract missing"; exit 2; }
test ! -e "$C.sha256" || { echo "sidecar already exists — refusing"; exit 2; }
D=$(sha256sum "$C" | cut -c1-64)
printf '%s  %s\n' "$D" "$(basename "$C")" > "$C.sha256"
chmod 0444 "$C" "$C.sha256"
echo "E1_CONTRACT_SEALED sha256=$D"
git add -- "$C" "$C.sha256"
git commit -q -m "E1 contract sealed (controller): $D

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
bash .scratch/multi-catfish-v023-server-pipeline/sync_server_e1_checkout.sh | tail -1
echo "next (server, in /home/sat/mcrl-leo-handover-e1): chmod 0444 the two files if git did not preserve the mode; build_e1_preflight_manifest.py; build_e1_launch_authority.py; run_v023_c3_existence_e1.py --dry-run"
