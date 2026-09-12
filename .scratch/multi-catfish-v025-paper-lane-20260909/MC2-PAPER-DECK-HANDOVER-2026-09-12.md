# MC2 paper / symbol-table / deck handover — file locations and the facts they may use

Written 2026-09-12 by the MC2 controller session for the session taking over the paper, symbol table and deck.
The training side (mechanism, DEV runs, formal S1) stays with the controller session; everything below is what the
writing side needs. **No MC2 learner result exists yet** — ep-100 had not been launched when this was written.

## 1. Authority files — read-only, never edited, deltas only

| class | authority | note |
|---|---|---|
| Thesis (Chinese) | `artifacts/chinese-word-v023-lcsrs-20260905-r2/mcrl-thesis-ZH-v023-method-draft-20260905.docx` (sha256 `367c11f6…`) | V0.23-era science; the `.pdf` beside it is an output, not an authority |
| Symbol table | `artifacts/chinese-word-v025-unified-symbols-20260909/active-symbol-table-v025-20260909.md` + `SYMBOL-COLLISION-AUDIT-v025-20260909.md` + `SUPERSEDES.md` | collision rules: single-letter / single-digit sub- and superscripts, no multi-letter labels, no hats, compound indices from atomic parts |
| Deck style + equation pipeline | `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/pilot-build/lc-srs-pilot-native-v4.pptx` with `build_pilot.py` and `native-formulas.json` | native OMML equations |
| Deck content skeleton | `artifacts/multi-catfish-teaching-deck-v023-20260905-r1/agy-pilot/STORYBOARD.md` (+ `PILOT-SLIDE-SPEC.md`, `SCIENCE-CLAIM-MAP.md`) | |
| Register of all of the above | `.scratch/multi-catfish-v025-physics-successor/V025-SINGLE-AUTHORITY-REGISTER-2026-09-09.md` (revised 09-12) | §5: **the register itself went stale once — check the authority directory for a later `SUPERSEDES.md` before trusting it** |
| Physical formula definitions win over everything | `2026-08-17-simplified-ee-presentation-spec.md` | |

Working rule (register §2): new paper / symbol / deck work is a **delta** under
`.scratch/multi-catfish-v025-paper-lane-20260909/`; nothing writes to `artifacts/` or `docs/`.

## 2. Science source of record for the MC2 round

| what | where |
|---|---|
| **The mechanism contract (r2)** — roles, judge, both intervention rules, invariants, cells, seeds, all declared readings | `/home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md` (branch `mc2/judge-override-20260912`, commit `d026ab71`; r0 `67e175bd`, r1 `9d3625c4`, r2 `b6573b58`) |
| Pre-training diagnostic (non-learned rule rollouts, override rates, parity receipts) | same worktree, `.scratch/mc2/CONTROLLER-PROBE-READOUT-2026-09-12.md`; raw JSON on sat `/home/sat/mcrl-v025-mc2-ws/controller-probe/probe-*.json` |
| Method co-sign, code read, verified citations, independent readout tooling | same worktree, `.scratch/mc2/B/CONTRACT-COSIGN.md`, `CODE-READ.md`, `LITERATURE-DELTA.md`, `b_readout.py`, `b_output_change.py` |
| Fresh-context cross-model (Gemini) design review | same worktree, `.scratch/mc2/agy/AGY-CONTRACT-REVIEW-r1.md` (+ its brief) |
| **Controller rulings: current physics + MC2 symbols** | `/home/u24/papers/mcrl-leo-handover/.scratch/mc2-controller/RULING-CURRENT-PHYSICS-AND-MC2-SYMBOLS-2026-09-12.md` (commit `2d90931e`) |
| Takeover record + the six handoff corrections | `.scratch/mc2-controller/CONTROLLER-MC2-TAKEOVER-2026-09-12.md` |
| k = 8 failure (the set-valued attempt that this round replaces) | `.scratch/catfish2-successor/CONTROLLER-K8-FAIL-AND-SEARCH-EXHAUSTED-2026-09-12.md`; its raw numbers `/home/u24/papers/mcrl-leo-handover-cf2s-multi/.scratch/catfish2-successor/results/LANE-M-K8-RESULT.json` |
| E1 (the established single-Catfish DEV result) | `.scratch/dev-training/E1-RESULT-2026-09-12.md` |
| Headline decomposition (backbone vs catfish) and its two caveats | `.scratch/dev-training/CONTROLLER-HEADLINE-DECOMPOSITION-2026-09-12.md` |
| What the original CDRL / RIS catfish actually is | `.scratch/catfish-facts/CATFISH-MECHANISM-FACTS-2026-09-11.md`; primary-ish source `/home/u24/papers/modqn-paper-reproduction/docs/catfish-explainer-package/07-true-catfish-formulas.md`, `00-README-START-HERE.md` |
| DQfD family grounding (already done, do not redo) | `.scratch/dqfd-grounding/DQFD-FAMILY-GROUNDING-2026-09-11.md` |
| Every citable number with its conditions | `.scratch/RESULTS-REGISTRY.md` |
| Lane registry (who ran what, which agent, which progress file) | `.scratch/AGENT-REGISTRY.md`, the MC2 block at the end |

## 3. Deltas already written (hand these forward; both lanes were stopped mid-round)

**Paper** — `.scratch/multi-catfish-v025-paper-lane-20260909/mc2-paper-20260912/`:
`SEC-METHOD-MC2-DELTA.md` (ch.4 replacement: one multi-catfish spine + v1/v2 as two replaceable rules, Algorithm box,
corrected CDRL table, borrowed-technique paragraph), `TAB-BASELINE-ABLATION-SKELETON.md` (8-cell ep-100 matrix,
qualification clauses, identifiability labels, formal table), `SYMBOL-DELTA.md` (15 symbol rows + collision checks),
`CLAIM-BOUNDARY.md` (now / waits-for-DEV / waits-for-formal + the six corrections), `SEC-PROBLEM-SETUP-DELTA.md`,
`CITATION-DELTA.md`, `PROGRESS-C.md` (**read this first** — it lists which files are final and which still need the
§2 rulings applied).

**Deck** — `.scratch/multi-catfish-v025-paper-lane-20260909/mc2-deck-20260912/`:
`build_mc2_pages.py`, `native_math.py`, `native-formulas-mc2.json`, `mc2-pages-r1.pptx`, `mc2-pages-r1.pdf`,
`figures/` (`fig_specialist_geometry`, `fig_dilution`, `fig_complementarity`, `fig_catfish_vs_learner_flow`,
`fig_deployment` — each as `.py` + `.svg` + `.png`), `renders/`, `PROGRESS-D.md` (**read this first** — which pages are
real, which are placeholders, what was visually checked).

**Exact state at handover (lane C's own report; `PROGRESS-C.md` §2 lists every pending change with its location):**
- *final as written*: `SEC-METHOD-MC2-DELTA.md` (all rulings applied — `S`, `π^A`/`π^F`, `a^A`/`a^F`, `κ` only as the
  judge key, the three k8 specialty numbers labelled "對 D0，一個訓練種子，ep 100" with their `LANE-M-K8-RESULT.json`
  source, §4.1.1 rule-level motivation, v1/v2 in one frame, corrected CDRL table) and `CITATION-DELTA.md`;
- *still need the rulings applied*: `SEC-PROBLEM-SETUP-DELTA.md` (drop the `【需裁定】` on physics, state it as the
  current model, correct the legacy list, `Q`→`S`), `SYMBOL-DELTA.md` (rewrite: `S` not bare `Q`, add `π^A`/`π^F`/`a^F`,
  `κ` reserved for the judge key, §10.7 112→113 is ruled not asked), `TAB-BASELINE-ABLATION-SKELETON.md`
  (`a^B`→`a^F`, drop the §1.3 pending note), `CLAIM-BOUNDARY.md` (one guardrail bullet: physics settled, nothing
  regenerates);
- *open items*, collected in `PROGRESS-C.md` §4: three code-level `【待核】` (P-03 exclusions, (3.27) re-entry rules, the
  TD loss form), two owner items (the §10.14.7 energy-boundary sentence, the formal S1 floors verbatim), the citation
  `待核` ([29] DAgger string, [28] author order/pages, CDRL page numbers second-hand), opening §10.15, and the formal
  manifest (owned by lane E / the controller).

**One notation decision is still open and it propagates**: because `κ` is reserved for the judge key, the normalised
output scale (code `s_B`) has no ruled glyph. The method delta currently writes it `β`, and the frozen margin `m = 0.15`
is expressed in those units, so whatever glyph is chosen appears in every loss and settings line. That one is for the
new session (and ultimately the owner's symbol table).

**Deck state at handover (lane D's own report; `PROGRESS-D.md` has the resume detail):** `build_mc2_pages.py` builds all
8 pages and is syntax-valid; the 5 figure scripts and their PNG/SVG are current, including a new
`fig_complementarity.py` drawn from the real P0 rollout numbers and a shared v1/v2 flow figure with a swappable rule
box. **`mc2-pages-r1.pptx` / `.pdf` / `renders/*.png` are STALE** — built before the page-2 chart and the notation fix,
so rebuild and re-render before trusting them. Open items: (1) rebuild + re-render; (2) page 6's native `deploy` formula
(argmax with a nested sub+sup inside a subscript) renders broken in LibreOffice — diagnosed, not fixed; (3) the
`π^A`/`π^F`, `a^A`/`a^F` ruling is applied in the flow figure but **not** at three named lines of
`build_mc2_pages.py` (page 4 footer, page 5 table, page 5 note — exact old/new text in `PROGRESS-D.md` §5); (4) the
one-time "code letter B = `π^F`" clarification was drafted but never inserted (candidate: page 7 caption); (5) pages 7
and 8 have never been visually inspected, only character-budget checked; (6) the probe evidence was added to page 2 only,
not to page 4; (7) `NOTES.md` (page-by-page claim status) was never written.

## 4. Numbers that exist, with the labels they must carry

- **E1, established DEV**: `D3-T0` vs paired `D0`, 3 fresh DEV seeds, ep 300, 24 DEVVAL episodes: **+9.42 %** seed mean;
  **72/72** paired episodes positive for `D3-T0` (the other 72/72 belongs to `D2-T0` — never write 144/144); QoS floors
  clear. Also: the gain decays with depth (12.71 → 9.72 → 9.42 % at ep 100/200/300) and nothing proves it survives to
  ep 1000.
- **k = 8, DEV, ONE training seed, 24 evaluation episodes, ep 100**: `D0` 100.789, `T0-only` 112.487,
  `T_NEXT-only` 109.086, `FULL{T0,T_NEXT}` 107.852, Bernoulli null 79.746 M bit/J. `T_NEXT-only` joules ×0.856 and
  53.4 vs 62.6 beams against `D0` come from `LANE-M-K8-RESULT.json`, not from the adjudication table. The ordering is the
  measurement; "the stronger teacher was diluted" is the proposed mechanism and was **never causally isolated**; the
  60.7 % two-member rate does not prove it.
- **Controller probe, DEV, NON-LEARNED rule rollouts, P0 collection, 24 episodes, pooled Σbits/Σjoules**: T0 116.963;
  `T_NEXT` 103.111 (−11.84 %); composite (judge arbitrating per user) **124.130 (+6.13 %, 24/24 paired, median +5.96 %,
  min +2.35 %)** with bits ×1.012, joules ×0.953, served +0.004 pp, p10 +6.5 %; composite with uniform random proposals
  instead of `T_NEXT` 119.691 (+2.33 %, 24/24), so the composite beats it by +3.71 % (23/24). Override rates 0.286
  (`a^F`) and 0.141 (`a^R`) at T0's background, 0.308 / 0.155 at the frozen `D3-T0` learner's. Judge–step parity exact,
  zero RNG contamination. **This is a rule-level statement about the target, not a learner result.**
- **Headline decomposition**: `D3-T0` is +20.27 % over the frozen 9000-episode MODQN eq-(16) DEVVAL figure while `D0`
  alone is +9.92 % (`1.0992 × 1.0942 = 1.2027`). The split must be reported, but those two numbers have comparability
  limits (the baseline term is one of six mutually incomparable values for that checkpoint) and **may not enter the
  formal abstract**; formal numbers come from same-protocol comparisons in S1.

## 5. Rules that apply to the writing side

1. DEV, formal and unverified hypotheses stay visibly separate; the MC2 method section is a **candidate under DEV
   screening** and may not be written as an established result.
2. Do not port the closed V0.25 stage-C coordinator route (`F = B − η_ref·E − Φ`, `G = F + κΦ`, C1/C2/C3 as a route,
   S_UNI / S3 coordinator), the old capacity penalty, or the frozen demo simulator's physics. The **current** physics is
   what the code runs: segment-anchored recurrence link power, service = legal ∧ `p ≤ p⁺`, no beam cap.
3. Notation: `S = Q̃_B − η̃ Q̃_E − λ Q̃_H` (λ = 0); specialists `π^A` (anchor, T0) and `π^F` (foresight, T_NEXT) with
   actions `a^A`, `a^F`; judge `κ = (n_served, B − η₀E)`, a **fixed-η₀ training surrogate, not EE**. Code and cell names
   keep the letter `B` for the foresight source — state the mapping once.
4. Two specialists, never three; both are **scripted rules, not RL agents**; deployment is the main learner's masked
   argmax only — no teacher, no judge, no coordinator.
5. No invented numbers, no placeholder that looks like a result; use `⟨DEV 待填⟩` / `⟨formal 待填⟩`.
6. `artifacts/` and `docs/` are never written; the owner merges deltas.

## 6. Where the next numbers will come from (owned by the controller session, not the writing side)

ep-100 selection matrix (8 cells × DEV seeds k = 10, 11) in `/home/sat/mcrl-v025-mc2-ws/runs-ep100/`, ep-300
confirmation in `…/runs-ep300/`; per-cell raw files `devval-ep00100.json` / `devval-ep00300.json`; the controller's
aggregate `MC2-EP100-RESULT.json`; the independent recomputation via `.scratch/mc2/B/b_readout.py`. The contract's §7
is what decides which version is primary and whether it survives — the writing side should take numbers only from the
controller's readout records, never from a run directory directly.
