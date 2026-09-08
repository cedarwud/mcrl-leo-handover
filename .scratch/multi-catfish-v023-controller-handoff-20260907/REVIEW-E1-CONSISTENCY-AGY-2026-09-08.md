# agy (Gemini) read-only consistency review — E1 contract + candidates — 2026-09-08 00:45 UTC

Invocation: agy --sandbox --effort high --print=<prompt with all seven documents inlined> (no tools). Verdict: AGY_E1_REVIEW=CONSISTENT; one NON-BLOCKING item (dominance reduction must be per Dinkelbach iteration) adopted into the controller review.

1. **[NOTE] E1 Optimisation & Closure Implication** (`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:34-70`)
   In E1 §2, BASE is in every choice set \(\mathcal X_p\) (line 43), is feasible (\(s_{\rm BASE} \ge s_{\rm BASE} - 0.001\)), and yields ratio \(\eta_{\rm BASE}\). With \(\delta = 0\), `HEADROOM` requires certified \(V(\mathcal X) > \eta_{\rm BASE}\) (lines 67–68). If \(V(\mathcal X) \le \eta_{\rm BASE}\), the maximum attainable ratio is \(\eta_{\rm BASE}\). Because BASE achieves \(\eta_{\rm BASE}\) and ties resolve lexicographically BASE first (line 62), the certified optimal profile vector under `CLOSED` is BASE. Thus, `CLOSED ⇒ optimum = BASE` is mathematically implied.

2. **[NON-BLOCKING] Dominance Reduction Timing** (`CONTROLLER-REVIEW-E1-CONTRACT-2026-09-08.md:21-27`)
   Dinkelbach's inner problem \(\max_y \sum (B_{px} - q E_{px})y_{px}\) subject to pooled service \(\ge N(s_{\rm BASE}-0.001)\) is solved exactly by DP over anchor index and cumulative served count. Item 5 notes choice sets "may be reduced beforehand by exact dominance (for each anchor and each distinct served count keep the profile maximising B − qE)". Because \(B - qE\) depends on \(q\), this reduction must execute within each Dinkelbach iteration for the current \(q\) (or prune only profiles dominated across all \(q \ge 0\)); static pre-Dinkelbach pruning across arbitrary \(q\) would not be exact.

3. **[NOTE] World Derivation Rule & Seeds** (`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:94-98`, `CONTROLLER-REVIEW-E1-CONTRACT-2026-09-08.md:31-36`)
   Per instruction, code execution was not used. The rule text is unambiguous. Derived seeds (`861587764845384088`, `3943897440191533562`, `5747196377242098234`, `4004348767321774260`) are identical across `CONTROLLER-REVIEW-E1` (lines 33–36), `CANDIDATE-A` (lines 115–116), `CANDIDATE-B` (line 91), and `CANDIDATE-C` (line 93).

4. **[NOTE] Candidate Admission Cell Mapping** (`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:72-78`, `V023-C3-CANDIDATE-A-CONTRACT-2026-09-08.md:9-10`, `V023-C3-CANDIDATE-B-CONTRACT-2026-09-08.md:7-8`, `V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md:12-14`, `CONTROLLER-REVIEW-CANDIDATES-2026-09-08.md:11-13`)
   Admission cells match E1 §3's table: Joint candidate C-A requires Joint `HEADROOM` (with Unilateral `HEADROOM` or `CLOSED`); Unilateral candidates C-B and C-C require Unilateral `HEADROOM` (with Joint `HEADROOM` or `CLOSED`).

5. **[NOTE] Constant Consistency** (`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:100,112,128-129`, `V023-C3-CANDIDATE-A-CONTRACT-2026-09-08.md:46,64-65,118,133`, `V023-C3-CANDIDATE-B-CONTRACT-2026-09-08.md:54,70,93-94,112`, `V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md:60,64,95,97,113`)
   All constants match across documents: \(\lambda = 118424222.8550065\) bits/J, \(\kappa = 10097071012.757404\) bits, \(\Delta t = 30.08\) s (\(47 \times 0.640\) s), service margin \(= 0.001\), users \(= 100\), lineages = `2026092101–03`. Panel steps align with memo rules: E1 uses 10 steps (`0..9`, 120 anchors; E1 line 100, Memo line 60), while candidate kill screens use 2 steps (`0..1`, 24 anchors; C-A line 118, C-B line 94, C-C line 97, Memo line 109).

6. **[NOTE] Forbidden Moves & Gate Interpretation** (`V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:11,79,135`, `ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md:28`, `V023-C3-CANDIDATE-A-CONTRACT-2026-09-08.md:12,146`, `V023-C3-CANDIDATE-B-CONTRACT-2026-09-08.md:9,129`, `V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md:17,127`)
   No draft permits residual ranking, quiet tuning, or favorable regime selection. All documents state that E1 and candidate kill screens serve as closure tests rather than learner admission or paper efficacy gates.

7. **[NOTE] Ruling Memo Requirements & Mandatory Disclosures** (`ADJUDICATION-C3-FUTURE-PATH-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md:22-35`, `V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md:9-10`, `V023-C3-CANDIDATE-A-CONTRACT-2026-09-08.md:5-6`, `V023-C3-CANDIDATE-B-CONTRACT-2026-09-08.md:5-6`, `V023-C3-CANDIDATE-C-CONTRACT-2026-09-08.md:5-6`)
   All four contract drafts incorporate the verbatim mandatory disclosure required by the memo. Causal mechanism, information interface, formula, deployment, panel, falsifier, and forbidden moves are fully specified across all candidate contracts without omissions.

AGY_E1_REVIEW=CONSISTENT
