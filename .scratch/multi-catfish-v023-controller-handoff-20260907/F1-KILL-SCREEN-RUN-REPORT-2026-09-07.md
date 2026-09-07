# F1 Kill-Screen Run Report — 2026-09-07

**Outcome: `INVALID_RUN`** (fail-closed on an F0 integrity check, before any tape step was written). No retry performed, per protocol.

## Launch authority

Created `.scratch/multi-catfish-v023-c3-contingency-f1/F1-LAUNCH-AUTHORITY-2026-09-07-r1.json` (+ `.sha256`, both chmod 0444).
`sha256 = 9bf367cb72d1a6f005fdab09e885a8b8c069e265208e8798ee28026f6b6bb382`.

Content is exactly the 8 keys `_validate_launch_authority` compares by strict dict equality: `schema=multi-catfish-mcrl-v023-c3-contingency-f1-v1-launch-authority`, `status=FROZEN_LAUNCH_AUTHORITY`, `claim_ceiling` and `bindings` copied verbatim from the preflight manifest, `preflight_manifest={"path":".scratch/multi-catfish-v023-c3-contingency-f1/F1-PREFLIGHT-MANIFEST.json","sha256":"495d90d2e1dac41abac87f28aad3f75eaa7e1c448910ea27edcc172a12496e24"}`, `test_split_opened=false`, `episode_training=false`, `learner_update=false`. Confirmed by running `_validate_launch_authority` directly (local and server) via a small script that imports the runner module.

**Deviation, recorded per hard rule ("fix the authority file, never the runner"):** I tested adding `frozen_at_utc=2026-09-07T15:10:43Z`, `frozen_by="controller (Claude Fable 5.1) under owner delegation 2026-09-07"`, `ladder_branch="STOP_PHYSICS -> open F0/F1 for D and F"`, `r7_result_sha256=dfcc70e441e2ec2c3be20608124c704c6d5c80b4d902a1aa7b75328faadbd2f7`. The validator rejected the file with any extra top-level key (`launch authority does not pin the exact F1 preflight/bindings`, verified empirically) because it does full dict equality, not a superset check. The four fields above are recorded here instead of inside the JSON; the r7 hash also independently matches the preflight's pinned `r7_stop_receipt.sha256`.

## Commands run

```
rsync -a --exclude __pycache__ .scratch/multi-catfish-v023-c3-contingency-f1/ \
  sat:/home/sat/mcrl-v023-successor-shadow-20260907/.scratch/multi-catfish-v023-c3-contingency-f1/

ssh sat 'tmux new-session -d -s mcrl-v023-c3-f1-20260907-r1; tmux send-keys -t mcrl-v023-c3-f1-20260907-r1 -l -- \
  "cd /home/sat/mcrl-v023-successor-shadow-20260907 && echo 1000 > /proc/self/oom_score_adj; \
   PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 PYTHONPATH=$PWD/src /home/sat/mcrl-leo-handover/.venv/bin/python \
   .scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py \
   --preflight-manifest .scratch/multi-catfish-v023-c3-contingency-f1/F1-PREFLIGHT-MANIFEST.json \
   --launch-authority .scratch/multi-catfish-v023-c3-contingency-f1/F1-LAUNCH-AUTHORITY-2026-09-07-r1.json \
   --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
   --output /home/sat/mcrl-v023-c3-contingency-f1-20260907-r1 \
   2>&1 | tee /home/sat/mcrl-v023-c3-contingency-f1-20260907-r1.log" Enter'
```

Server digests matched local: preflight `495d90d2…496e24`, authority `9bf367cb…6bb382` (both `sha256sum -c` OK).

## Result

- Wall time: **~36 s** (tmux launch 2026-09-07 15:14:07 UTC → receipt/log mtime 15:14:43.8 UTC).
- Peak RSS: **not available** — process exited before the first 60 s sample in the bounded wait loop.
- Tape: **not produced** (`tape_complete=false`, `tape_sha256=null` in the receipt) — the crash occurred inside tape generation, before any step or candidate was written.
- Receipt: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1/receipt.json`, `sha256=cfb6fa9e40a0acc844b034ec6bfa6fc205ff9071fdd72e23b88bb5e25cef906a`.
- BASE/D/F pooled EE, service, and "changes ≥1 legal action" counts: **not computed** — `metrics=null`, `kill_rules=null` in the receipt (INVALID_RUN short-circuits scoring).

**Exact error** (from `run_v023_c3_contingency_f1.py:1380` → `c3_contingency_f0.py:923→902→821→777`, raised in `CostShareResult.__post_init__` at `c3_contingency_f0.py:623`, while validating the **reference/BASE** profile's cost shares — i.e. this recurs on the very first candidate regardless of order):

```
F1_ERROR: total share energy does not equal beam plus satellite share
c3_contingency_f0.C3F0Error: total share energy does not equal beam plus satellite share
```

## Roots

- Shadow checkout: `/home/sat/mcrl-v023-successor-shadow-20260907`
- Output root: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1` (receipt.json only)
- Log: `/home/sat/mcrl-v023-c3-contingency-f1-20260907-r1.log`
- tmux session `mcrl-v023-c3-f1-20260907-r1`: still present, idle at shell prompt (left as-is, not killed)

Per protocol: stopping here, no retry, no attempt to repair `c3_contingency_f0.py`.
