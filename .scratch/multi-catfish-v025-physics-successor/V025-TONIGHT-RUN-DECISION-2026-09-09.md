# V025 — what must be true to run the a-r0 matrix tonight (controller, 2026-09-09 ≈ 03:40 UTC; sealed before any formal outcome)

The owner's priority is to see results today. This separates the conditions that are scientific from the ones that are engineering, so the run is not blocked by the wrong thing.

## 1. Mandatory before the matrix opens (scientific correctness)
1. The confirmed ACM defect is fixed: `m_target`, `m_tx` and the realised outcome are distinct; `m_tx` is chosen from the causally available margin-adjusted nominal view; bits are credited against `threshold(m_tx)` only.
2. v1.9 §1–§4: the margin does not re-solve power; it applies only to the wanted link's predicted reception; the quantile is of the full fading product; each arm ranks, prunes and tie-breaks with its own key.
3. The suite is green with no test deleted, and the committed-profile endpoint is unchanged by the selection-time approximations.
4. The formal manifests and the a-r0 calibration are produced by the sealed procedure, and the attempt registry records `STARTED` before any unit opens.
If any of these fails, the matrix does not run tonight.

## 2. Engineering targets — a miss is recorded, not a blocker
The 10 s coordinator selection budget and the ≤ 60 s per-anchor total are **deployability** targets. Missing them changes what may be claimed about deployment; it does not make the physics regime map wrong. If the measured selection time exceeds 10 s, the matrix still runs, and: the measured mean and p95 per decision are reported in the seal package and beside every figure; the deployability sentence is weakened to "the coordinator as evaluated exceeds the declared 10 s budget by X; an operational variant is future work"; and the cost projection for the confirmatory evaluation is recomputed from the measured mean.

## 3. Freeze deadline applied
Stage 4h is the last design pass (freeze rule §5: two further passes after the freeze was written; 4e and 4h). If the 4h audit does not return READY, the controller runs the matrix on the 4h tree provided §1 holds, and every unresolved audit row is recorded in the limitations register and reported with the results. No further design pass is opened before the matrix.

## 4. Order tonight
`a-r0` first (four sealed worlds, 90 anchors per world, 13 + 2 reporting arms). Then, within the remaining budget and in this order: panel E (architecture: a′-r0, a-γ0, b0 — these are sealed settings and reuse the same tapes), then panel A (rate target 25 / 100), then panel B (circuit power 0.1 / 1.0). Panels C and D are synthetic and run separately. Anything not finished tonight is reported as `未執行`, never silently dropped.

## 5. What "results today" means
Tonight's deliverable is the **physics regime map**: the certificates, the admission trichotomy's outcome, and the CH5 sweep panels that the completed settings support. The learned-policy contrasts are not part of tonight; the pilot's numbers remain `PILOT_NOT_CLAIM`.
