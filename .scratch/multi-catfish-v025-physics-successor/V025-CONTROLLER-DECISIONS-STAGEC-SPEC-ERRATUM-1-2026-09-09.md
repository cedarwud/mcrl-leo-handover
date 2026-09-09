# Stage-C spec decisions — erratum 1 (controller, 2026-09-09 ≈ 02:30 UTC)

Found by the seal-integrity check (`SEAL-INTEGRITY-2026-09-09.md`, list 3, the only unreconciled contradiction among 43 in-scope artefacts): `V025-CONTROLLER-DECISIONS-STAGEC-SPEC-2026-09-08.md` item 6 still says **twelve** learner seeds, while `V025-STAGES-6-8-CONTRACT-v1.1-AMENDMENT-2026-09-09.md` item 1 raised the count to **sixteen** on the measured real-merger calibration.

**Correction:** the learner-seed count is **16**, derived from the domains `V025_LEARNER/seed/{1..16}` by the repository seed rule. Item 6 of the stage-C spec decisions is superseded to that extent; everything else in that item (domain-derived seeds, no hand-picked integers, the external BASELINE's implementation sha256 recorded in the allocation manifest) stands.

**Convention recorded once, so the next integrity check has no ambiguity:** sealed artefacts — declarations, amendments, errata, contracts and the contingency ladder — carry a `.sha256` sidecar and are written read-only; controller *decision records* are versioned in git and are not separately sidecarred, because git already hashes them and they are working records that later decisions may supersede. The integrity check treats a missing sidecar on a decision record as expected, not as a defect.
