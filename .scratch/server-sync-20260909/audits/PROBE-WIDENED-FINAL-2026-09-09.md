Report written; orphans cleared; sibling arms (`acm2`, Codex's widened) running untouched.

---

# WIDENED interaction-existence arm — `PROBE_NOT_CLAIM`

**Status: NO CENSUS PRODUCED. Zero anchors completed.**
2026-09-09, headless Claude Opus 5 run, workspace `/home/sat/mcrl-v025-probe-ws-widened`.
Everything below is labelled `PROBE_NOT_CLAIM`. Nothing here may enter the paper, select a configuration, regime, margin or sealed rule, or be cited for or against C1, C2 or C3. **No result in this document is pooled with the original neighbourhood's, because this arm produced no result to pool.**

This is a blocker-and-provenance report, not a results report. The per-regime, per-family tables the brief asks for are **empty**: not "null within budget", but "never computed". Read section 5 before reading anything as evidence of absence.

## 1. The sealed declaration does not exist

The brief opens: *"Read the sealed declaration `V025-CONTROLLER-DECISIONS-PROBE-NEIGHBOURHOOD-2026-09-09.md` first. Copy it from `/home/sat/mcrl-hub` or ask git for it."*

**That file does not exist anywhere.** Searched:

| where | result |
|---|---|
| `/home/sat/mcrl-hub` working tree | absent |
| `git ls-files` | absent; 22 other `V025-CONTROLLER-DECISIONS-*` files present |
| `git log --all -- '*PROBE-NEIGHBOURHOOD*'` | no commit ever touched that path |
| `git log --all --diff-filter=D` | never added and deleted |
| `git stash list`, all 20 local/remote branches | absent |
| `find /home/sat -name '*PROBE-NEIGHBOURHOOD*'` | absent |
| content grep across the tree | **one hit only: `claude-widened.md`, the brief itself** |

The controller's `chain.log` records `06:50:06Z widened probe arm start (declared pre-outcome…)` — the chain believes a declaration exists. It was never written.

1. **The authorization is missing.** The declaration's stated job is to say *why widening an existence search is admissible* — the anti-p-hacking device separating a pre-registered superset search from post-hoc specification search. Its absence doesn't by itself make the arm illegitimate (the brief names the four families before any widened result existed, timestamped 06:20:27Z), but then **the brief is the pre-registration of record, not the declaration.**
2. **The HONEST LIMITS paragraph cannot be "reproduced".** There is no final section to reproduce. I did **not** invent one and present it as reproduced — fabricating the provenance of the one paragraph whose job is to be trustworthy is the worst available failure. Section 6 is authored by this run and labelled as such.

## 2. Both declared setup branches were unusable

**Branch A** — `mcrl-v025-probe-ws-acmfix` existed when I stat'ed it at 07:44:0x and was gone 20 s later. `chain.log`: `07:43:00Z corrected-ACM probe STOPPED: workspace was half-corrected (stale 215791-byte runner…)`. It now exists as `…-acmfix-BROKEN-stale-runner`. **Copying it on first sight — exactly what the brief instructs — would have silently inherited the condemned physics.**

**Branch B** — the literal fallback reproduces that same condemned state. The runner the probe loads (`RUNNER = HERE / "run_v025_matrix_probe.py"`, line 40) lives *outside* `src/mcrl/physics_v025/`:

| runner | bytes | `fading_quantile_alpha` |
|---|---|---|
| `probe-ws` (pre-fix) | 215 791 | **0** |
| `codex-ws-engine` (stage-4h) | 295 312 | **30** |

Swapping only the physics corrects the physics and leaves the pre-fix runner — byte-for-byte the state that stopped the sibling arm 40 minutes earlier.

**What I built instead:** the **pre-fix coherent** state plus the families only, since this arm's sole admissible reading is *superset of the original neighbourhood*, and that comparison is meaningful only on the engine the original arm runs. Verified: physics (17 files), runner, and both helper scripts byte-identical to `probe-ws`; the only differing file is `probe_interaction_existence.py` (`273b1eb8…` → `ca42e2d7…`). This is a **recorded deviation** — the brief asked for corrected ACM.

**Tape reuse — by digest identity, not assertion.** All four tape-build inputs in `CODE-DIGESTS.txt` match my workspace exactly (`tapes.py d330aead…`, `provider_legacy.py bce57c8c…`, `targets.py a612f55c…`, runner `d430baf3…`); the only differing file plays no part in tape construction. Tapes hard-linked, verified by inode. Had I taken corrected physics this argument would **not** hold — `acm2` reached the same conclusion independently (`07:45:38Z … fresh tapes, fresh calibration`).

## 3. The four families were implemented and are ready

| family | designed candidates/anchor |
|---|---|
| `pairwise-marginal` | C(10,2)=45 × 16 = **720** |
| `pairwise-straddle` | ≤100 × 16 = **1 600** |
| `vacate-and-fill` | **1 per active beam** |
| `triples-marginal` | C(5,3)=10 × 8 = **80** |

Original three families untouched. No threshold, sign, seed, horizon, λ, κ, η_ref moved; service guard, `Psi` decomposition and certified-`u` procedure untouched. Compiles; no traceback in any of the 12 unit logs.

## 4. The workspace was deleted underneath the run

Launched 16 units at 08:17:26Z (6 concurrent, `nice -n 10`). At 08:20:47Z `chain.log` records:

> `witness and widened moved from claude to codex; workspaces rebuilt as trusted git repos`

**The controller reassigned this arm to Codex and rebuilt the workspace while my units were running.** My six workers were left with `cwd = …widened (deleted)`. ~3 min 20 s elapsed against a per-anchor cost dominated by a 240 s `u`-search: **no anchor completed; `units/*.jsonl` held 0 rows.** I killed the six orphans (burning six cores against a deleted inode, contending with Codex's run and `acm2`'s nine processes) and left both live arms untouched. I did not write into the rebuilt workspace.

## 5. The census, stated honestly

| regime | family | improving `G` | improving `F` | positive-`Psi` | max `Psi_A^u` | coalition | candidates |
|---|---|---|---|---|---|---|---|
| `a-r0`, `R1`, `R3`, `R4`, `R6`, `R7` | all seven | — | — | — | — | — | **0** |

**Total search budget actually consumed: 0 candidates, 0 of 36 planned anchors.** Designed budget was ≈1.7 × 10⁵ candidate evaluations across 36 anchors in a 3-hour / 6-concurrent envelope.

**This is not a null result.** A null reads "none found within budget"; this reads "the search never ran". Any absence of positive `Psi` must be quoted from Codex's run, not this one.

## 6. HONEST LIMITS

**Authored by this run** — *not* a reproduction of the sealed declaration's final section, because that declaration does not exist. It must not be cited as carrying the declaration's authority.

This arm produced no measurement. The four families are implemented and digest-pinned but never executed, so nothing here bears on whether positive interaction exists in any regime. The prepared engine state is **pre-fix**, still carrying the genie-ACM defect; the correction moves availability 0.791 → 0.453 and pooled EE 18.94e6 → 5.66e6 bit/J at identical joules, so a null on pre-fix physics would not carry over. Enlarging a candidate set can only *find* interaction, never establish absence: every family is a bounded heuristic neighbourhood around a `u` certified only to a 240 s budget and 40 sweeps, and `Psi` is defined on `F` while the coordinator ranks `F + κΦ` (D6), so the `G` and `F` counts answer different questions and neither alone is decisive. The families target indifference and blocking because that is *a priori* where joint moves pay — a positive finding would carry weaker weight than one from uniform sampling, a negative finding weaker weight than exhaustive search. Never pool with the original neighbourhood: the two are nested by construction, and pooling would double-count shared families and misstate any per-family rate.

## 7. What the controller should do

1. **Write the declaration**, or drop the "reproduce its final section" clause.
2. **Fix the fallback in `claude-widened.md`**: take `run_v025_matrix_probe.py` from the same snapshot as `src/mcrl/physics_v025/`, or the corrected-physics branch silently reproduces the condemned state.
3. **Choose the engine state deliberately** — pre-fix coherent (superset relation intact) or post-fix coherent (comparable to `acm2`, needs fresh tapes *and* calibration). Not a graft.
4. **Serialize reassignment against in-flight work** — rebuilding a workspace under a running arm cost this one its entire compute window.

The four-family patch is small and re-appliable; only `probe_interaction_existence.py` is touched. Full report at `/home/sat/mcrl-v023-codex-audits/parallel-20260909/PROBE-WIDENED-REPORT-2026-09-09.md`.

`PROBE_NOT_CLAIM`
