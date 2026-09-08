# Assumptions audit — brief (controller, 2026-09-08 13:15 UTC)

Owner's directive: "擴大檢查：把原本以為理所當然的條件都拿出來重新檢視；如果是這麼基礎的公式跟實作的問題，就難怪怎麼解都解不了。"
Trigger: the energy model was found to hold a segment-anchored gain-inversion power recurrence (p(t) = p⁰·G^T(θ(τ))/G^T(θ(t)), reset to p⁰ = 0.825 W at every handover) with zero handover energy in the endpoint but a handover penalty in the training reward — a non-standard forward-link model that manufactures a "renewal premium" and explains much of two weeks of C3 failures and the C3-S +2.9 %.

## Scope
Every assumption in the simulator, the reward/training stack and the evaluation harness that has been treated as given. Slices (one fresh-context auditor each; overlap is fine, silence is not):
- **A. Geometry, ephemeris, mobility, time base** — `src/mcrl/env/d2.py`, `scenario.py`, `dwell.py`, TLE/ephemeris code, `docs/EPHEMERIS-NOTES.md`, `docs/D2-NOTES.md`; 30.08 s = 47 × 0.640 s step; elevation masks; visibility; user mobility; dwell N = 4.
- **B. Channel, antenna, interference, bandwidth, bits** — `src/mcrl/env/link_budget.py` (path loss, atmosphere, Rician K, shadowing, antenna patterns, G/T, noise), interference and frequency reuse (500 MHz / 3), equal bandwidth split, keyed fading fields, Shannon bits; `docs/LINK-BUDGET-NOTES.md`.
- **D. Service, QoS, action contract, masks, candidates, handover classes** — `src/mcrl/env/service.py`, `candidates.py`, `action_contract.py`, masks in `step.py`; what "served" means and why it saturates; feasibility/outage; handover classes and dwell rule.
- **E. Reward, targets, training** — `src/mcrl/runtime/energy_efficiency.py`, `ee_surplus_targets.py`, `reward_calibration.py`, `replay_buffer.py`, `trainer_env.py`, `trainer_spec.py`, `src/mcrl/algorithms/modqn.py`, the V0.23 successor training package under `.scratch/multi-catfish-v023-c1c2-successor*/` and `.scratch/multi-catfish-v023-two-route-source-training-runner/`; λ and κ derivation; Φ; per-head bootstrap; r1 aggregation; TD targets; masks in training vs deployment; what C1/C2 actually inject ("Catfish" mechanism).
- **F. Evaluation, estimand, statistics** — pooled EE Σbits/Σjoules; service margin 0.001; TRAIN/VALIDATION/TEST split rules; world plans and seeds; chunked ladders with HELD/FALSIFIED; FULL/DROP/BASELINE and `ALL_NEUTRAL_CONTROL` semantics; verifiers; `.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/`, `.scratch/multi-catfish-v023-c1c2-successor/`, stage-C code.
- (Energy/PA/system power is covered by the parallel EE-formula audit and the astra adjudication — do not duplicate, but cross-reference.)

## Deliverable per slice (Markdown, ≤ 220 lines, English)
1. A **summary table** ranked by impact: assumption | where implemented (file:line) | what the docs say (file:line or "undocumented") | standard practice / literature status | who or what it distorts (EE level; policy-vs-policy comparisons; C1/C2/C3 marginals; training signal) | magnitude estimate | verdict: KEEP / DECLARE / FIX / SENSITIVITY / UNKNOWN.
2. Per-item detail with the decisive evidence and a **known-answer test** (hand-computable fixture) that would pin it.
3. **Code-vs-docs disagreements** found.
4. **The three assumptions you would overturn first** and why.
Rules: read-only; no git state changes; light Python only; do not propose tuning constants against outcomes; do not propose opening the TEST split; be adversarial to the project's own framing.
