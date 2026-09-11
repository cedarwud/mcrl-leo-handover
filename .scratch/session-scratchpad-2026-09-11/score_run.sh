#!/bin/bash
# CONVSCORE: gated scoring of one completed run at one epoch with the UNMODIFIED scorer.
# Usage: score_run.sh TAG RUNDIR PANEL PANEL_RECEIPT EXPECTED_PANEL_SHA256 EPOCH
# Refuses (non-zero exit, no scoring) unless:
#   - RUNDIR/training-result.json exists (run complete),
#   - exactly 16 checkpoints exist at EPOCH, one per launch-receipt seed, sidecars match,
#   - launch-receipt Q1/Q2 schema SHA-256 == panel receipt encoder_binding Q1/Q2 SHA-256,
#   - panel file SHA-256 == EXPECTED_PANEL_SHA256 == panel receipt panel_sha256,
#   - scorer SHA-256 == 8a83bc98... (the accepted unmodified scorer).
set -u
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
TAG="$1"; RUNDIR="$2"; PANEL="$3"; PREC="$4"; WANT_PANEL="$5"; EPOCH="$6"
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
SCORER=/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py
WANT_SCORER=8a83bc9865fdbf665fe3815197059fc68c11efd73c319d96bcc412b5a8c5ed9d
WS=/home/sat/mcrl-v025-convscore-ws
EP=$(printf "%06d" "$EPOCH")
OUT=$WS/artifacts/score-${TAG}-epoch-${EP}
date -u +"START %Y-%m-%dT%H:%M:%SZ"
echo "TAG=$TAG RUNDIR=$RUNDIR EPOCH=$EPOCH"
[ -s "$RUNDIR/training-result.json" ] || { echo "GATE_FAIL run incomplete: no training-result.json"; exit 10; }
got=$(sha256sum "$SCORER" | cut -d" " -f1); [ "$got" = "$WANT_SCORER" ] || { echo "GATE_FAIL scorer sha $got"; exit 11; }
got=$(sha256sum "$PANEL" | cut -d" " -f1); [ "$got" = "$WANT_PANEL" ] || { echo "GATE_FAIL panel sha $got"; exit 12; }
echo "PANEL_SHA256=$got SCORER_SHA256=$WANT_SCORER"
"$PY" - "$RUNDIR" "$PREC" "$WANT_PANEL" "$EPOCH" <<'EOF' || exit 13
import json, sys, hashlib
from pathlib import Path
rd, prec, want, ep = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
lr = json.load(open(rd / "launch-receipt.json")); pr = json.load(open(prec))
fs, eb = lr["feature_schema"], pr["encoder_binding"]
ok = (fs["q1_schema_sha256"] == eb["q1_schema_sha256"] and fs["q2_schema_sha256"] == eb["q2_schema_sha256"]
      and pr["panel_sha256"] == want)
print("DIGEST_MATCH", ok, fs["q1_schema_sha256"][:16], eb["q1_schema_sha256"][:16], fs["q2_schema_sha256"][:16], eb["q2_schema_sha256"][:16])
seeds = lr["seed_list"]
missing = [s for s in seeds if not (rd / "checkpoints" / f"learner-{s}-epoch-{ep:06d}.json").exists()]
print("SEEDS", len(seeds), "MISSING_AT_EPOCH", missing)
sys.exit(0 if ok and len(seeds) == 16 and not missing else 1)
EOF
mapfile -t CKS < <(ls -1 "$RUNDIR"/checkpoints/*epoch-${EP}.json | sort)
[ "${#CKS[@]}" -eq 16 ] || { echo "GATE_FAIL checkpoint count ${#CKS[@]}"; exit 14; }
for c in "${CKS[@]}"; do
  want=$(cut -d" " -f1 < "${c}.sha256"); got=$(sha256sum "$c" | cut -d" " -f1)
  [ "$want" = "$got" ] || { echo "SIDECAR_MISMATCH $c"; exit 15; }
  echo "CKSHA $(basename "$c") $got"
done
echo "SIDECARS_VERIFIED_OK"
/usr/bin/time -v nice -n 16 "$PY" "$SCORER" --checkpoints "${CKS[@]}" --panel "$PANEL" --output "$OUT" 2>&1 | grep -v "^anchor "
rc=${PIPESTATUS[0]}
echo "SCORER_EXIT=$rc"
date -u +"END %Y-%m-%dT%H:%M:%SZ"
exit $rc
