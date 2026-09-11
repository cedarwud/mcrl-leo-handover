# CF3PILOT — takeover guide for a fresh agent

This guide gives the commands, in order, for a fresh agent taking over the pilot.

- **Last known state:** `PROGRESS.md`, whose first line is `HANDOFF-SAFE`.
- **The design:** the declaration and Amendments 1-3 in `.scratch/multi-catfish-v025-physics-successor/`, plus
  `DECLARATION-ADDENDUM.md` in this directory. All of it is frozen; do not redesign.

## Where everything is
| what | where |
|---|---|
| code (branch `cf3/pilot-20260911`) | local worktree `/home/u24/papers/mcrl-leo-handover-cf3`. Training tree = commit `f297334e`. Post-job/report scripts = `102b2d4d`. |
| server workspace | `sat:/home/sat/mcrl-v025-cf3-pilot-ws` (= `$WS`) |
| training tree on sat (frozen; never restage while runs exist) | `$WS/tree` (`$WS/tree/COMMIT` = f297334e) |
| python | `/home/sat/mcrl-leo-handover/.venv/bin/python` (read-only; never modify it or `/home/sat/mcrl-leo-handover`) |
| pinned TLE archive | `$WS/tle-pinned-427e6a91` (file_set sha256 `427e6a91…8fe9`); always `export MCRL_TLE_ROOT=$WS/tle-pinned-427e6a91` |
| calibration (eta_0, s_B, s_E, RANDOM reference) | `$WS/premeasure/calibration.json` (sha256 `59952214…562d`) |
| source pools (Amendment 3) | `$WS/pools/s{0,1,2}/*.npz` + `.json` sidecars |
| **pool hashes** | `$WS/pools/POOL-SIDECAR-HASHES.json` (sha256 `8ebbae85…7c7c`); npz hashes also in `$WS/runs/RUN-MANIFEST.json` |
| runs (12 = A0/A1/A2/A3 × seeds 0-2, 1000 ep) | `$WS/runs/<ARM>-<NAME>-s<K>/` (`status.json`, `readings.jsonl`, `episode-logs.json`, `resume.pt`, `policy-epNNNNN.pt`); logs `$WS/runs/<ARM>-s<K>.log` |
| learning check (ep 500) | `$WS/runs/learning-check/` (`A1-s{0,1,2}.json`, `DECISION.json`) |
| post-training job (detached) | `$WS/diag/cf3_postjob.py`, PID recorded in PROGRESS; log `$WS/report/postjob.log` |
| outputs | `$WS/report/` (`REPORT-DONE` or `REPORT-FAILED`, `CF3-SUMMARY.json`, `CF3-TABLES.md`, `POOL-VERIFY.json`, `GENERATOR-IDENTITY.json`, `RUN-STATES.json`, or `LEARNING-CHECK-STOP.json`); evals `$WS/eval/<ARM>s<K>.json` |

## 1. Check status
```bash
ssh sat 'cd /home/sat/mcrl-v025-cf3-pilot-ws; ls report; cat report/postjob.log; \
  for f in runs/A*/status.json; do python3 -c "import json;s=json.load(open(\"$f\"));print(\"$f\",s[\"status\"],s.get(\"episodes_completed\"))"; done; \
  cat runs/learning-check/DECISION.json 2>/dev/null; tail -n1 runs/*.log'
```
- **Progress readings** (greedy calibration EE at 100/250/500/750/1000) are the rows of each `readings.jsonl`. They are
  progress only.
- **The post-job:** `pgrep -a -f diag/cf3_postjob.py` lists it (do not kill by pattern; see "What not to do").

## 2. If a run died or failed: relaunch / resume (same code only)
```bash
ssh sat 'cd /home/sat/mcrl-v025-cf3-pilot-ws/tree && export MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91 && \
  /home/sat/mcrl-leo-handover/.venv/bin/python scripts/cf3_launch.py --root ../runs --calibration ../premeasure/calibration.json \
  --pools ../pools --expect 12 --memory-max 5G --memory-max-cf 7G --dry-run'
```
- Read the plan first. Then run the same command without `--dry-run`. **Do not pass `--init-manifest`**: the manifest
  exists and must match.
- The launcher skips finished and live runs. Other runs resume from `resume.pt`, which is bit-identical (tested).
  Resume refuses any code, calibration or pool mismatch (fail closed).
- If the post-job has already written `REPORT-FAILED` because a run died, delete **only** `report/REPORT-FAILED`
  after the relaunched runs finish, then restart the post-job (§3).

## 3. Re-run the evaluation / report by hand
The post-job is idempotent: it exits if a marker exists, and it reuses existing `eval/*.json`.
```bash
ssh sat 'cd /home/sat/mcrl-v025-cf3-pilot-ws && setsid nohup /home/sat/mcrl-leo-handover/.venv/bin/python diag/cf3_postjob.py \
  --ws /home/sat/mcrl-v025-cf3-pilot-ws > diag/postjob.stdout 2>&1 < /dev/null & disown'
```
Manual pieces, each run from `$WS`:
- eval one checkpoint: `(cd tree && MCRL_TLE_ROOT=… $PY scripts/cf3_eval.py --label A2s0 --checkpoint ../runs/A2-CF3-s0/policy-ep01000.pt --kind cf --out ../eval/A2s0.json --repeat)`.
  Use `--kind modqn` for A0.
- pools: `python3 diag/cf3_verify_pools.py --pools pools --root runs --out report/POOL-VERIFY.json` (exit 1 = mismatch; stop).
- reading: `$PY diag/cf3_report.py --eval-dir eval --root runs --out report/CF3-SUMMARY.json --pool-verify report/POOL-VERIFY.json`,
  then `$PY diag/cf3_render.py report/CF3-SUMMARY.json report/CF3-TABLES.md`.

## 4. Copy results back and write the report
```bash
mkdir -p /home/u24/papers/mcrl-leo-handover/.scratch/cf3-pilot/report
scp -r sat:/home/sat/mcrl-v025-cf3-pilot-ws/report/. /home/u24/papers/mcrl-leo-handover/.scratch/cf3-pilot/report/
scp -r sat:/home/sat/mcrl-v025-cf3-pilot-ws/eval /home/u24/papers/mcrl-leo-handover/.scratch/cf3-pilot/report/eval
```
Then write `.scratch/cf3-pilot/CF3-PILOT-2026-09-11.md`:
- **First line:** one bolded sentence giving the four arms' mean pooled EE, whether C-S holds (C-H is information only
  since Amendment 2), and which declared branch occurred.
- **Below it:** the provenance header from `.scratch/curation/PROVENANCE-HEADER.md`. Fill it with:
  - physics/harness = MODQN harness, users 100;
  - estimand = pooled Σbits/ΣJ divided once, full-buffer;
  - power = consumed, per-beam max (MODQN default);
  - host = sat, archive pinned 427e6a91, harness placebo RANDOM 52,420,510.0956937 bit-identical;
  - evaluation = fresh env per episode, seeds 9_111_000+i / 9_112_000+i, i = 0..23, greedy;
  - commit f297334e;
  - A0 = eq.16 per-head max, gamma 0.9; A1-A3 = shared continuation, gamma 1, lambda fixed 0; D-2 per-step floor
    (A0); pools per Amendment 3;
  - checkpoint = final `policy-ep01000.pt`;
  - n = 24 eval episodes × 3 seeds per arm;
  - status = PILOT.
- **Body:** the tables in `report/CF3-TABLES.md`, which were generated from JSON (never type numbers by hand).
- **Name the study** a "three-source catfish-inspired off-policy replay pilot". It uses static offline source pools
  (Amendment 3 correction), so A2 vs A1 means "static directed-data prefill", not online catfish.
- **Claims:** direction only, 3 seeds, every seed shown. Give the dE_sys caveat for C3 (PROGRESS, "dE_sys
  diagnostic").

## The declared reading (addendum H, Amendments 2-3)
- X > Y iff the seed-mean final-checkpoint pooled EE of X > that of Y **and** X beats Y on ≥ 2 of the 3 same-index
  seed pairs.
- **Branch 1:** A2 > A3 and A2 > A1 and C-S non-inferior (served vs A1, 95% episode-cluster bootstrap lower bound
  > −0.5 pp) → directional signal.
- **Branch 2:** A2 ≈ A3 (neither > the other), with A2 > A1 and A3 > A1 → extra experience, not the demonstrators.
- **Branch 3:** not (A2 > A1) → no catfish effect at pilot scale.
- Anything else → "none of the declared branches".
- A1 vs A0 and A2 vs A0 are read separately with the same rule.
- `cf3_report.py` applies exactly this rule.

## What NOT to do
- Do not change the design, the constants, the seeds, the arms, or the reading. Do not add arms or tune anything.
- Do not restage or modify `$WS/tree`, `$WS/pools`, `$WS/premeasure`, `$WS/runs/RUN-MANIFEST.json`, or the shared
  venv.
- Do not resume across a code change. Do not use `--init-manifest` on the existing `runs/`.
- Do not kill with an unanchored `pkill -f`/`pgrep -f` pattern (it can hit your own ssh shell). Kill only exact PIDs
  whose `/proc/<pid>/cmdline` and cwd you have checked.
- Do not compare these numbers with anything measured on another TLE archive (FEASFRONT, catfish-surface, earlier
  pilots), or with the aborted launch in `$WS/runs-aborted-e8a04ccf-hold/`.
- Do not describe any difference as an effect beyond what 3 seeds support. Do not pre-fill any result.
- If the learning check stopped A1-A3 (`DECISION.json` pass = false): report with `report/LEARNING-CHECK-STOP.json`
  (loss curves, eta/lambda, per-head reward means). **Do not debug or relaunch**; wait for the coordinator.
