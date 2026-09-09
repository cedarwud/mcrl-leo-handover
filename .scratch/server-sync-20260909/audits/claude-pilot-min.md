# Minimal pilot (PILOT_NOT_CLAIM): one end-to-end pass that MUST finish
Workspace `/home/sat/mcrl-v025-pilot-ws` (already prepared; a previous agent left partial code in `scripts/` and partial outputs in `artifacts/` — reuse anything that works). Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Budget: 45 core-minutes, hard.
Scope deliberately tiny, and completion beats completeness:
* rows from **world 1 only**, **5 anchors**, the nearest-eligible carrier only;
* **2 learner seeds**, **200 source epochs** (not the sealed 2000 — this is a pilot, state that in the report);
* arms: FULL, DROP_C3, BASELINE only (skip DROP_C1/DROP_C2 if time is short, and say so);
* evaluate on **world 3, 5 anchors**, against the exact S0 and the iterated S_UNI.
Report `V025-PILOT-MIN-REPORT-2026-09-09.md`: realised pooled EE per arm, FULL vs DROP_C3, FULL vs S0, FULL vs S_UNI, the matched-anchor g_A/g_I decomposition, the tie frequency for C2, wall time per phase, and a DEFECTS section. Label everything `PILOT_NOT_CLAIM`. If a component is missing, implement the smallest thing that satisfies the schema and say so. Do not stop to perfect anything.
