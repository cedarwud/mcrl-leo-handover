All eight deliverables are written to `/home/sat/mcrl-hub-copy/.scratch/multi-catfish-v025-paper-lane-20260909/`.

| File | Content |
|---|---|
| `DELTA-MAP.md` | Δ1–Δ10 physics/method change table, then every section of the draft (front matter → references) marked KEEP / REWRITE / DELETE / NEW with a one-line reason, including equation-level calls (3.11–3.12 DELETE, 3.17 DELETE, 3.28–3.29 DELETE, Table 5-3 DELETE, "約束的作用範圍" DELETE) |
| `SEC-SYSTEM-MODEL-REWRITE.md` | Replacement §3 text: memoryless rate-target power control, ACM staircase + equal-airtime TDM, coupled capped fixed point with certificates, served ⇔ γ ≥ γ⁻ after joint resolution, saturation-efficiency PA reading, energy boundary, new §3.2 single-objective formulation, new §3.3 declared idealisations |
| `SEC-METHOD-REWRITE.md` | Replacement §4 text: two-layer decision, Ω/dᵢ/Ψ_𝒦 decomposition + identity, margin-adjusted selection view, target/transmitted MODCOD pair, per-arm ranking keys, bounded catalogue + two-stage scoring, set-conditioned interaction head, comparators + Υ + re-anchoring, claim ladder / admission trichotomy / terminology |
| `SYMBOL-ADDITIONS.md` | q^α, Ω^q, dᵢ, Ψ_𝒦, Υ, m^r/m^q (+ℳ, ν_m, γ_m, Γ_r, R⋆), a¹ — each with definition, first appearance, and an explicit collision check; plus two prerequisite moves (Ψ_u→Φ_u, G(x)→Ω(a)) and a §10.11 amendment list |
| `TAB-I-model-assumptions.md` | 6 groups, ~70 rows, each with source type (STD/LIT/DER/CONV/DECL/SYN/INH/MEAS) and VERIFY_SOURCE status (—/OPEN/CHECKED/INHERITED) |
| `TAB-II-comparator-contract.md` | Per-comparator contract rows, factor-arm ranking-key table, 14-item equalisation checklist, mandatory report schema, wording constraints |
| `DEVIATION-REGISTER-DELTA.md` | D-0 power-model succession (verbatim disclosure sentence) through D-7, plus **D-8** listing M-1…M-10 as amendments that followed development inspection, D-9 freeze rule, D-10 open items |
| `LIMITATIONS-REGISTER.md` | L-1…L-7 = the seven named limitations, L-8 secondary register, L-9 future work derived from them, L-10 conclusion-section guardrails |

Verification points:
- The v1.8 §3 energy-boundary sentence is byte-identical to the sealed source (394 chars, programmatic diff = MATCH); the v1.8 §7 deployability sentence also appears verbatim in both files that need it.
- Retrospective-TLE and ideal-atomic-application are stated in `SEC-SYSTEM-MODEL-REWRITE.md` §3.3, i.e. where the model is defined, not in a footnote.
- No result numbers; outcome-dependent sentences carry `⟨結果待填⟩`.
- Nothing under `docs/`, no `.docx`, and nothing in `/home/sat/mcrl-paper-sources/` was written — original mtimes are unchanged at 2026-09-05.

Two things you should know rather than discover later:

1. **`figures/` and `_work/` inside the output directory are not mine.** They contain `figure1-angle-power-ee.*`, `figure1_compute.py`, and a 40 KB `SUCCESSOR-BRIEF.md`, all written at 03:17–03:20 by a concurrent process. I did not create, read, or modify them.
2. **One symbol carries residual risk, disclosed in the file rather than hidden:** ν_m (spectral efficiency) is visually close to the beam index v in a Word document. `SYMBOL-ADDITIONS.md` A-6 gives the disambiguation rule and a fallback glyph (ε_m) if typesetting review rejects it. Separately, D(a) collides with the one-off antenna-diameter D in §3.1.2 — I flagged it and proposed resolving it at final typesetting rather than silently overloading.
