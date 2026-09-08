# Read-only adjudication (gpt-6-astra): shadow-replay diagnostic + V-E addendum draft

You are the read-only adjudicator for the MCRL V0.23 C3-S line. Do not modify files. Write your verdict as a single Markdown document to stdout (the caller redirects it).

Context you must read (paths relative to the workspace root):
1. `.scratch/multi-catfish-v023-c3s-variants/V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md` (sealed nine-arm matrix; running now on a separate worktree).
2. `.scratch/multi-catfish-v023-c3s-variants-chatgpt-package-20260908/OUTSIDE-ROUND4-CHATGPT-QA-2026-09-08.md` and `…/OUTSIDE-ROUND4-CHATGPT-DEEP-RESEARCH-LITERATURE-REVIEW-2026-09-08.md` (outside round 4).
3. What codex gpt-5.6-sol just produced in this workspace: `.scratch/multi-catfish-v023-c3s-variants/CODEX-SOL-DIAG-VE-REPORT-2026-09-08.md`, `run_v023_c3s_shadow_replay.py`, `test_shadow_replay.py`, the V-E changes in `variant_policy.py` / `variants_config*.json` / `run_v023_c3s_variants.py`, `test_variant_ve.py`, and `ADDENDUM-B-VE-EXPECTED-SCORING-DRAFT-2026-09-08.md`.
4. Failure history you must keep in view: `.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md` §1 and the oracle-marginals / S0 probe results under `.scratch/multi-catfish-v023-c3-probe-results-20260908/`.

Answer, with file/line citations, in this order (each ≤ 12 lines):

A. **Shadow replay is non-decisional and exact?** Does the replay reproduce the screened arm bit-identically (seeds, policy code path, initial state assertion) and does the extra same-state BASE evaluation leave the environment state provably unchanged? Is the (a)+(b) decomposition identity exact and correctly attributed (immediate same-state benefit vs trajectory-divergence remainder)? Any way it could be misread as a rescue rerun or leak into progression? Verdict: `SHADOW_OK` / `SHADOW_FIX_FIRST` (list fixes).

B. **V-E as a tenth arm.** Is the expected-scoring definition consistent with "deployment-available statistics only" (distribution, never the realised keyed field)? Are K = 4 and the `C3S_VE/scenario/{1..4}` seed derivation fixed by declaration with no outcome path? Common-random-number property across candidates? Does adding V-E pre-outcome (before any nine-arm result is consulted) keep multiplicity honest, and is the disclosure obligation in the draft sufficient? Given the history (EXACT_ZR +0.985 % / NOMINAL_ZR weaker / EXPECTED_ZR stop was about learned labels, S0 nominal selection captured ≈90 % of the exact one-step headroom), rate the prior that V-E converts headroom in closed loop where LITE would not: `LOW` / `MODERATE` / `HIGH`, one paragraph of reasoning. Verdict: `VE_SEAL_AS_IS` / `VE_AMEND_THEN_SEAL` (exact amendments) / `VE_DO_NOT_RUN`.

C. **Ordering.** The controller will (i) let the sealed nine-arm matrix finish, (ii) run V-E only if its launch authority is built before any nine-arm result is read, (iii) run the shadow replay only on a NO_SUPPORT outcome. State whether (ii) is achievable given the chain timing, or whether V-E must instead be declared as a separately timestamped second screen that discloses exposure. One paragraph.

D. **Anything that would make a reviewer reject the eventual paper section** if these two tools are used as intended. Bullets only.

End with one line: `ASTRA_DIAG_VE_VERDICT: <A verdict> | <B verdict> | <B prior>`.
