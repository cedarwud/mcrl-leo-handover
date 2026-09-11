#!/bin/bash
# OOSPANEL acceptance: one real checkpoint against one OOS panel with the UNMODIFIED scorer.
# Adapted from /home/sat/mcrl-v025-convscore-ws/scripts/score_run.sh (same digest/SHA gates),
# restricted to one checkpoint and writing only below the OOSPANEL workspace.
# Usage: score_one.sh TAG CHECKPOINT PANEL PANEL_RECEIPT EXPECTED_PANEL_SHA256
# Refuses (non-zero exit, no scoring) unless:
#   - scorer SHA-256 == 8a83bc98... (the accepted unmodified scorer),
#   - panel file SHA-256 == EXPECTED_PANEL_SHA256 == panel receipt panel_sha256,
#   - the checkpoint's run launch-receipt Q1/Q2 schema SHA-256 == panel receipt encoder_binding,
#   - the checkpoint's seed is in the launch-receipt seed list and its sidecar verifies.
set -u
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
TAG="$1"; CK="$2"; PANEL="$3"; PREC="$4"; WANT_PANEL="$5"
PY=/home/sat/mcrl-leo-handover/.venv/bin/python
SCORER=/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py
WANT_SCORER=8a83bc9865fdbf665fe3815197059fc68c11efd73c319d96bcc412b5a8c5ed9d
WS=/home/sat/mcrl-v025-oospanel-ws
OUT=$WS/.scratch/acceptance/score-${TAG}
RUNDIR=$(dirname "$(dirname "$CK")")
date -u +"START %Y-%m-%dT%H:%M:%SZ"
echo "TAG=$TAG CHECKPOINT=$CK RUNDIR=$RUNDIR"
[ -e "$OUT" ] && { echo "GATE_FAIL output exists: $OUT"; exit 16; }
got=$(sha256sum "$SCORER" | cut -d" " -f1); [ "$got" = "$WANT_SCORER" ] || { echo "GATE_FAIL scorer sha $got"; exit 11; }
got=$(sha256sum "$PANEL" | cut -d" " -f1); [ "$got" = "$WANT_PANEL" ] || { echo "GATE_FAIL panel sha $got"; exit 12; }
echo "PANEL_SHA256=$got SCORER_SHA256=$WANT_SCORER"
"$PY" - "$RUNDIR" "$PREC" "$WANT_PANEL" "$CK" <<'EOF' || exit 13
import json, sys
from pathlib import Path
rd, prec, want, ck = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
lr = json.load(open(rd / "launch-receipt.json")); pr = json.load(open(prec))
fs, eb = lr["feature_schema"], pr["encoder_binding"]
ok = (fs["q1_schema_sha256"] == eb["q1_schema_sha256"] and fs["q2_schema_sha256"] == eb["q2_schema_sha256"]
      and pr["panel_sha256"] == want)
print("DIGEST_MATCH", ok, fs["q1_schema_sha256"][:16], eb["q1_schema_sha256"][:16], fs["q2_schema_sha256"][:16], eb["q2_schema_sha256"][:16])
seed = ck.name.split("-")[1]
in_list = seed in {str(s) for s in lr["seed_list"]}
print("SEED", seed, "IN_LAUNCH_SEED_LIST", in_list)
sys.exit(0 if ok and in_list else 1)
EOF
want=$(cut -d" " -f1 < "${CK}.sha256"); got=$(sha256sum "$CK" | cut -d" " -f1)
[ "$want" = "$got" ] || { echo "SIDECAR_MISMATCH $CK"; exit 15; }
echo "CKSHA $(basename "$CK") $got SIDECAR_VERIFIED_OK"
/usr/bin/time -v nice -n 15 "$PY" "$SCORER" --checkpoints "$CK" --panel "$PANEL" --output "$OUT" 2>&1
rc=$?
echo "SCORER_EXIT=$rc"
date -u +"END %Y-%m-%dT%H:%M:%SZ"
exit $rc
