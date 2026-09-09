# V025 — design freeze and closure rule (controller, 2026-09-09 ≈ 02:45 UTC; sealed before any formal successor outcome)

The review loop has no stopping condition as it stands: each round of outside opinion or fresh-context audit produces amendments, which produce another round. This rule closes it.

## 1. Freeze point
The successor design is **frozen when engine stage 4g passes its audit**. From that moment the sealed set is: declarations v1.0–v1.9 and their errata, the contingency ladder and its amendment, the stages 6–8 contract v1 with amendments v1.1–v1.2, and every controller decision record in force. No further scientific change is made before the a-r0 matrix.

## 2. Admissibility test for a late finding (all four must hold)
A finding arriving after the freeze is acted on **only if**:
1. it can change the **sign** of a load-bearing certificate or the **branch** of the admission trichotomy — stated in one sentence, with which certificate;
2. it names a **test that fails now and passes after the change**, executable in under an hour;
3. it is confirmed by a source independent of the one that raised it (a second reviewer, or a measurement);
4. the change does not require re-running work already completed under the freeze, or, if it does, the re-run fits in one overnight window.
A finding that fails any of the four is recorded in `LIMITATIONS-AND-FUTURE-WORK-REGISTER.md` with its reasoning and is reported in the paper's limitations section. This is not a way to hide problems: the register is published with the work.

## 3. What continues after the freeze
Outside opinions and audits continue, because their findings still shape the **limitations, the claim wording and the next study** — but they no longer gate the matrix. Engineering fixes that change no scientific quantity (speed, memory, logging, reporting fields) remain allowed at any time and are listed in the stage reports.

## 4. Standard of evidence for calling something a defect
Every item recorded as a defect carries: the failing test or the changed number, the independent confirmation, and what it would have done to a certificate. An item with none of these is labelled **precautionary**, not a defect, and is not used to justify delay. The register `V025-DEFECT-REGISTER-2026-09-09.md` applies this standard retrospectively to everything acted on so far, so that the owner can audit which changes were demonstrated and which were precautionary.

## 5. Deadline discipline
If stage 4g's audit does not return READY within two further engine passes, the controller stops adding scope, runs the matrix on the last audited configuration, and reports every unresolved item in the register as a declared limitation.
