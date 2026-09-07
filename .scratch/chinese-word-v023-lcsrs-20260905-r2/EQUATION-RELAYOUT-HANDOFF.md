# Handoff — Chapter 3 equation re-layout (interleave equations with prose)

> ✅ **DONE 2026-06-29 in commit `03cad45`** — ch3 §3.1.1–§3.2 equations interleaved with prose (ZH `mc-modqn-base.md` + EN twin + regenerated bilingual), 49/49 display eqs numbered, 0 LaTeX leak, build verified, 2 pages eyeballed. **Handoff CLOSED — do NOT re-execute.** (Spec below kept for provenance.)

> Created 2026-06-29 by the bilingual-thesis session. This is the spec for the ONE
> remaining "排版" task the USER flagged: Chapter 3 currently **block-dumps**
> equations at the top of each subsection and explains them afterwards. The MODQN
> paper (and this thesis's own ch4) instead introduce **one equation at a time,
> inline with the sentence that defines it**. Re-lay-out ch3 to match.
>
> **Recommended: run this in a FRESH conversation** (this one is long), optionally
> as a Workflow (design below). All prior work is committed; HEAD has the figure
> renumber + formality passes. G1 `modqn.py` `aa877676` must stay untouched.

## The target convention (grounded — from the paper + ch4)

Authority = `paper-source/txt_layout/2024_09_Handover_for_Multi-Beam_LEO_Satellite_Networks_A_Multi-Objective_Reinforcement_Learning_Method.layout.txt`.
The paper's System Model + Problem Formulation read like:

> "The channel gain `G_{i,l,v}(t)` … can be expressed as **[Eq 1]**, where ξ and
> f_c are …"  → "The SNR … is **[Eq 2]**, where p is …"  → "According to the
> Shannon formula, the rate … is given by **[Eq 3]**, where B is …"

i.e. **prose lead-in → the single display equation → "where …" symbol gloss →
next lead-in → next equation**. Never a stack of equations followed by a wall of
prose. `thesis-mc/ch4-method.md` already does exactly this (each `$$…\tag{4.x}$$`
sits right after the sentence introducing it) — use ch4 as the in-repo style model.

## What is wrong now (ch3 only)

`thesis-mc/mc-modqn-base.md` (ch3 = §3.1.1–§3.1.4 + §3.2) and its EN twin
`thesis-mc/en/mc-modqn-base.en.md`:

- §3.1.1 stacks eqs (3.1)–(3.5) then prose. §3.1.2 stacks (3.6)–(3.11). §3.1.3
  stacks (3.12)–(3.19). §3.1.4 stacks (3.20)–(3.25). **§3.2 stacks all 14 of
  (3.26)–(3.39)** then a `（一）…（六）` prose block. This is the "誰看得懂" problem.

## The job

For each of §3.1.1, §3.1.2, §3.1.3, §3.1.4, §3.2 (ZH **and** EN, kept parallel):
**move each `$$…\tag{3.x}$$` (or matrix-numbered) block out of the top stack and
place it immediately AFTER the sentence that first introduces it**, then make the
lead-in read naturally (paper-style "…定義如式 (3.x)：" / "…is defined as in Eq.
(3.x):" instead of the current "如式 (3.x) 所示，…" which assumes the eq is elsewhere).

The prose already references the equations in numeric order, so the anchors are
unambiguous. Concretely:

| subsection | eqs | prose anchor for each (ZH) — place the eq right after this clause |
|---|---|---|
| 3.1.1 | 3.1–3.5 | (3.1) "本文以 𝒰、𝒮、𝒱 分別表示…" · (3.2) "全系統…以…𝒦 表示" · (3.3) "需滿足…的限制" · (3.4) "以 z 表示波束是否啟用…限制使用者只能連接至已啟用的波束" · (3.5) "波束 (s,v)…所服務的使用者數量定義為" |
| 3.1.2 | 3.6–3.11 | (3.6) 斜距 · (3.7) 偏軸角 · (3.8) FSPL · (3.9) 大尺度路徑損耗 · (3.10) 線性衰減係數 · (3.11) 複合鏈路增益 |
| 3.1.3 | 3.12–3.19 | (3.12) 期望接收訊號功率 · (3.13)/(3.14) 同/跨衛星干擾 · (3.15) SINR · (3.16) 候選頻寬 · (3.17) 候選吞吐量 · (3.18)/(3.19) 實際 SINR/吞吐量 |
| 3.1.4 | 3.20–3.25 | (3.20) 狀態 · (3.21)/(3.22) 動作遮罩/可行動作集合 · (3.23)/(3.24) 動作 one-hot/限制 · (3.25) 聯合動作 |
| 3.2 | 3.26–3.39 | keep the `（一）…（六）` structure; place (3.26) after the P1/P2/P3 lead-in; (3.27)(3.28) in （一）; (3.29) in （二）; (3.30)(3.31) in （三）; (3.32)(3.33)(3.34)(3.35) in （四）; (3.36)(3.37)(3.38) in （五）; (3.39) in （六） |

(The matched EN clauses are the literal translations already present in
`en/mc-modqn-base.en.md` — anchor off the same Eq numbers.)

## Hard constraints (do NOT break)

1. **Equation numbers are FIXED** — (3.1)…(3.39) keep their labels; you are only
   MOVING and re-introducing them, never renumbering. Every `如式 (3.x)` cross-ref
   elsewhere stays valid.
2. **ZH and EN must stay block-parallel** — the bilingual interleaver
   (`tools/build_bilingual.py`) walks the two block sequences in lockstep and
   ABORTS on any structural mismatch. After editing, rebuild with
   `bash tools/build_bilingual.sh` and confirm it prints "BUILT" with no AlignError,
   and that the docx still has **49/49 display eqs numbered, 0 LaTeX leak**.
3. Preserve every `[FIG-x-y]`, `[TABLE-5.x]`, `\[…\]`, `[N]` citation, `$…$` math,
   and `grounded`/`hypothesis` tag verbatim. Only prose flow + equation POSITION change.
4. Don't touch §3.3, §3.4, ch4, ch5, ch6, the matrix/`\tag` body of any equation,
   or any tooling. ZH = formal register already set this session — match it.
5. Verify: `tools/ris_preprocess.py` still numbers the moved `\tag` eqs (B1) — it
   keys off `\tag{}`, so moving the block is fine.

## Figure mapping (for the research-visual-lab session to rename picture files)

The thesis now uses 章-圖 tokens; the picture files must be renamed to match:

| old token | new (thesis 圖) | subsection | content |
|---|---|---|---|
| FIG-1 | 1-1 | ch1 | method overview |
| FIG-2 | 3-1 | §3.1.1 | system model |
| FIG-3 | 3-2 | §3.2 | MODQN architecture |
| FIG-4 | 4-1 | §4.1 | overall architecture |
| FIG-C | 4-2 | §4.2 | asymmetric discount |
| FIG-D | 4-3 | §4.2 | value-stratified replay |
| FIG-B | 4-4 | §4.3 | congestion context χ_u |
| FIG-A | 4-5 | §4.4 | coordinated beam allocation |
| FIG-5 | 4-6 | §4.5 | training procedure |
| FIG-5.1 | 5-1 | §5.2 | multi-metric bar |
| FIG-5.2 | 5-2 | §5.3 | efficiency–fairness/coverage |
| FIG-5.3 | 5-3 | §5.5 | capacity sweep lines |
| FIG-5.4 | 5-4 | §5.5 | objective-dimension ablation |

## Suggested Workflow (parallel, if running as one)

Pipeline of 5 items (the 5 subsections). Each item = one agent that edits BOTH the
ZH span and the EN span of that subsection in lockstep (so they stay parallel),
given: this spec + the rule "interleave per the anchor table, paper-style lead-ins,
keep eq numbers/refs/tags". Then a final verify stage: run `build_bilingual.sh`,
assert no AlignError + 49/49 eqs + 0 leak, render 2 pages (a 3.1.x page + the 3.2
page) and eyeball. Because the 5 subsections are disjoint text spans in the same 2
files, run them **sequentially within one agent per file** OR with file-level locking
— do NOT let 5 agents write the same file concurrently (they will clobber). Safer:
one agent does all of §3.1.1–§3.2 in `mc-modqn-base.md` + `mc-modqn-base.en.md`
in order, then the verify stage. Parallelism gain here is small (one file pair);
the value of a workflow is the structured verify gate, not fan-out.
