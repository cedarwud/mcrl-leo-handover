# Engineering-lane F2 prep report — 2026-09-07

**Scope: F2 preparation only.** No F2 execution; no launch authority created.

## Closure additions
Computed F2's transitive closure via `expected_code_bindings()`/`CODE_BINDING_PATHS` in `run_v023_c3_contingency_f2.py`, cross-checked against every path+hash in `F2-PREFLIGHT-MANIFEST.json` (all verified present locally, hashes match). 11 paths are new versus `SHADOW-CLOSURE-LIST-2026-09-07.txt`:
- 6 F2 package files: `README.md`, `build_f2_preflight_manifest.py`, `run_v023_c3_contingency_f2.py`, `test_run_v023_c3_contingency_f2.py`, `F2-PREFLIGHT-MANIFEST.json`, `F2-PREFLIGHT-MANIFEST.sha256`
- `multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py` (multi-lineage head loader)
- lineages `2026092102` and `2026092103`: rung-003000 checkpoint + `authority.json` each (lineage `2026092101` was already listed)

Full list saved to a local `F2-CLOSURE-ADDITIONS.txt` in my scratchpad (not `/tmp`, per standing scratchpad policy — contents match the list above verbatim). Repo's `SHADOW-CLOSURE-LIST.txt` left unedited. Of the 11, only the F2 package directory was actually absent from `/home/sat/mcrl-v023-successor-shadow-20260907`; the other 5 were already there byte-identical (an earlier wholesale copy of `v020-c3-source-audit/` had carried them) — verified by sha256 on both sides before and after. Rsynced the F2 package (minus `__pycache__`) plus all 5 addition files as a no-op verification pass.

## Dry-run
`run_v023_c3_contingency_f2.py --dry-run` in the shadow checkout → `F2_DRY_RUN_PASS`, exit 0, first attempt. No missing-file retry needed.

## Fan-out script
Wrote (did not execute) `/home/sat/f2-prep/launch_f2_units.sh` + `/home/sat/f2-prep/README.txt` (sequence: sealed F1 result path -> build F2 launch authority per the runner's `validate_launch_authority` fields -> script `--dry-run` -> real launch). `--dry-run` (tested on the server with placeholder AUTH/OUT) prints 15 lines: 1 `tmux new-session` + 11 `new-window` for the 12 world:lineage units + 1 merge-watcher window that polls `units/*/receipt.json` (needs all 12) then runs `--merge` once. Each unit gets `oom_score_adj=1000`, `OMP_NUM_THREADS=1`, its own log under `$OUT-logs/`. Re-running the script resumes: it skips any unit with an existing receipt or an already-running window. Verified clean: exit 0, no stray files or tmux sessions left behind.

## F1 progress observed
F1 is **not running** — it already finished `INVALID_RUN` (matches the parallel `F1-KILL-SCREEN-RUN-REPORT-2026-09-07.md`): `C3F0Error` "total share energy does not equal beam plus satellite share" at `c3_contingency_f0.py:623`, reached from `run_v023_c3_contingency_f1.py:1380`, ~36s after launch, before any tape step completed. No survivor, so F2 is not (yet) launchable, and no usable wall time exists to scale to F2's 10-step units — flagged as pending in `README.txt`. F1's tmux session and output root were only read, never touched.
