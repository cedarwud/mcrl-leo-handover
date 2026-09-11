# SPECPROFILE — progress checkpoint (FINAL)

Last update: 2026-09-11T02:05Z. Design-phase measurement, not a claim. **Learner-free.**
**Report delivered: `/home/sat/mcrl-v025-specprofile-ws/SPECIALIST-QOS-PROFILE-2026-09-11.md`**
(sha256 `efc78880fbd57f5c4a76b4de18f02bf190fd4b3528c94177e8f78d0fda29db81`).
Host `sat`; interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`; nice 16; BLAS/OMP 1;
never more than 2 python processes; peak RSS 1.894 GiB per process.
`D` = `/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile/`.

## Nothing is running. No detached process of mine remains.

## Completed and delivered

1. **Parity gate PASSED at the full-48 endpoint** — `CAP_050` search winner 62.502712 Mbit/J
   (1200/1200 served, 354/1200 attaining), `RSS_MAX` 41.621560, geometric base 11.027760,
   strongest declared rule at C=50 (`S2_descending_coverage|A2_max_nominal_gain`) 52.042303.
   All four to six decimals. 62.502712 IS a full-48 figure; only the *selection* was boundary-0.
2. **Evaluator rule PASSED** — raising stub installed in all three processes; all three ended
   `scalar_evaluate_calls = 0`.
3. **Erratum 23 handled** — the configuration is called "the `CAP_050` search winner" throughout;
   the label `GAIN_IN_SET` is noted as applied after the fact and absent from the beamcount
   workspace. The declared-rule class (all nine C=50 rules) is profiled separately.
4. **Answer.** The specialist does NOT satisfy every declared co-primary outcome.
   - Handover rate **0.975000 per user-step** (1170/1200 events: 844 satellite changes, 326 beam
     changes); Phi-priced cost **0.839167 kappa per user-step**.
   - complete-service: **PASS** +50.75 pp [+36.42,+63.67] vs base; +50.42 pp [+36.17,+63.50] vs
     incumbent.
   - handover rate: **FAIL** +200.77 % [+69.08, undef] vs base; **FAIL_UNDEFINED_DENOMINATOR** vs
     incumbent (incumbent has 0 handovers by construction).
   - Phi cost: **FAIL** +180.50 % [+57.05, undef] vs base; **FAIL_UNDEFINED_DENOMINATOR** vs
     incumbent.
   - All nine declared C=50 rules fail both handover guards too; two also fail availability.
     `RSS_MAX` fails all three.
5. **Price of passing.** Per-anchor handover/Phi budget (<= 1.05x the base reference at every
   anchor) passes all three guards vs base and reaches **17.257910 Mbit/J, 1001/1200 served,
   192/1200 attaining, 520/1200 complete service** — giving up **45.244802 Mbit/J = 72.389 %**.
   Declared rule under the same budget: 17.200058 (999/1200, 180/1200), -66.950 %.
   Against the incumbent reference the only passing arm is zero-handover = hold the incumbent,
   **10.325892 Mbit/J, 929/1200 served, 115/1200 attaining** (-83.48 %).
   Satellite lock alone (the brief's worked example) halves Phi (0.839167 -> 0.462083 kappa) but
   barely moves the rate (0.975000 -> 0.924167) and still FAILS both: 43.818876 Mbit/J,
   1197/1200 served, 357/1200 attaining.

## Structural facts recorded in the report

- Cell re-keys, re-entries, initial entries and exits are all 0 on this panel (arrays path gives
  `_rekeyed_users() == ()`; `reentry` is unreachable from `_physical_events`; the carrier base has
  0 null users at every anchor). Every event is a beam change, a satellite change, or unchanged.
- At step 0 the declared incumbent IS the same-step base, so with `stay-if-possible` included,
  **7 of 12 anchors have a zero-handover base reference**; hence undefined bootstrap upper
  endpoints (20/10,000 draws for base-referenced contrasts) and a steps-1-3-only sensitivity.
- Carrier invariance: a fixed mapping scores identically across carriers at a step, so the
  effective sample size is 4 physical steps. Re-clustering the bootstrap on 4 steps changes no
  verdict.
- Matched-budget free polish of the search winner RAISES boundary-0 EE and LOWERS the full-48
  endpoint (62.502712 -> 59.516177), quantifying BEAMCOUNT's boundary-0 overstatement warning.

## Artefacts

- Runners `D/run_specprofile.py`, `D/run_specprofile2.py`; mergers `D/merge_specprofile.py`,
  `D/merge_declared.py`; `D/summary.py`; launcher `D/launch.sh`.
- Receipts `D/specprofile-shard-A.json` (6 anchors, 317.4 s), `D/specprofile-shard-B.json`
  (6 anchors, 714.3 s), `D/specprofile-declared-rules.json` (12 anchors, 426.6 s) — all
  `status=COMPLETE`, `scalar_evaluate_calls=0`.
- Merged `D/specprofile-merged.json`, `D/specprofile-declared-rules-merged.json`
  (10,000-resample cluster bootstrap, seed 20260911, clustered by anchor and by physical step).
- Rehearsal `D/rehearsal-specprofile-shard-A.json`, logs `D/rehearsal.log`, `D/rehearsal2.log`,
  `D/shard-A.log`, `D/shard-B.log`, `D/declared.log`.

## To reproduce or resume

Each step checks for its own output first; rerun only what is missing.

```
cd /home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile
SPECPROFILE_SATLOCK_PASSES=4 ./launch.sh A        # -> specprofile-shard-A.json
SPECPROFILE_SATLOCK_PASSES=4 ./launch.sh B        # -> specprofile-shard-B.json
OMP_NUM_THREADS=1 ... nice -n 16 python run_specprofile2.py   # -> specprofile-declared-rules.json
nice -n 16 python merge_specprofile.py            # -> specprofile-merged.json
nice -n 16 python merge_declared.py               # -> specprofile-declared-rules-merged.json
```

Read-only inputs, unchanged: the three BEAMCOUNT shard receipts under
`/home/sat/mcrl-v025-beamcount-ws/.scratch/beamcount/` (SHA-256 in every receipt), the V0.25
pilot/engine/`batch.py`/`energy.py`/`targets.py` under `/home/sat/mcrl-v025-c1c2suff-ws`.
`/home/sat/mcrl-leo-handover` and its `.venv` were not modified.
