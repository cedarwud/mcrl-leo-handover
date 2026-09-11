# Adversarial review: objective re-specification (2026-09-11)

Reviewer: fresh-context adversary. Read-only, no jobs run.
Output: `.scratch/reviews/objrespec/ADVERSARY-OBJECTIVE-RESPEC-2026-09-11.md`

## Status — COMPLETE

- [x] Progress file
- [x] Located physics: `src/mcrl/env/{link_budget,service,interference,step}.py`,
      `src/mcrl/runtime/{energy_efficiency,reward_calibration}.py`
- [x] Finding 1 (r3): power arithmetic VERIFIED (6.266 W / 2.455 W reproduce exactly);
      the `B/U` cancellation claim is FALSE as stated (beam total = B x mean SE, not
      U-invariant); occupancy has a numerator channel and an interference channel
- [x] Finding 2 (r2): zero-joule handover VERIFIED; p0 reset VERIFIED at
      `step.py:786-808` + `link_budget.py:379`
- [x] Finding 3: NOT a statistical artefact (epochs independently drawn
      `ephemeris.py:421`; fading rng consumption action-independent `step.py:1375-1388`;
      estimand defect <=0.06%; eval seeds exist in the frozen run's status.json).
      IS a physics artefact: the entry anchor.
- [x] Finding 4: 62/142 ms confirmed against `docs/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md`,
      which already gated this exact proposal `R2_PHYS = NOT_CLOSED`
- [x] Literature: handover-penalty reward terms standard in LEO RL handover; CMORL
      constraint form is the published alternative to deletion
- [x] Sealed successor check: V025 v1.1+ amendment already REMOVES the entry anchor and
      ADDS occupancy->required-power. Both proposal premises are reversed by it.
- [x] Verdict written: REJECT

## Key arithmetic (all reproducible from repo constants)
- p_sat = 1.65 * 10^0.5 = 5.21776 W; xi(p0) = 0.35*sqrt(0.825/5.21776) = 0.139169
- new beam = 0.825/0.139169 + 0.338 = 6.26606 W  [matches claimed 6.267]
- p0->p_max supply bump = 8.38342 - 5.92806 = 2.45536 W  [matches claimed 2.455]
- 142 ms / 30.08 s = 0.47207%; 62 ms / 30.08 s = 0.20612%
- gap after interruption term: 1.19771 -> 1.19526 (+19.53%); closes 0.24 of 19.77 pp
- interruption needed to close the gap: f = 0.34516 -> 10.38 s/handover = 68-167x sourced
- price ratio r2 vs interruption: 13.71% of r1 vs 0.047% of bits = ~290x
