# Ruling — the penalty track: what the sibling's effect was, and why it does not transfer here

Date: 2026-09-11. Sources: `.scratch/cap-penalty/CAP-PENALTY-2026-09-11.md`,
`.scratch/penalty-arm/PENALTY-ARM-2026-09-11.md`, `.scratch/concept-harvest/CONCEPT-HARVEST-2026-09-11.md`.

## The owner's memory was right — about the capacity penalty

| wave | episodes | result | control |
|---|---|---|---|
| M4 | 12,000 | EE 523.78 → 613.05 (**+89.28, 6/6**); served 0.892 → 0.991; cap-dropped users 0.108 → 0.009 | OFF reused from an earlier batch |
| ABL9K | 9,000 | L5 − L2 **+134.59, CI [116.0, 153.2], 6/6** | L2, L4 |
| EP2K | 2,000 | penalty arms separate from all others at all 20 checkpoints | L2-L4 |

Confirmed at source by CAPPENALTY. Caveats: sibling estimand (per-user mean of ratios, radiated-power
denominator — not comparable to pooled EE here); the sibling itself later marked these as predating
later code fixes, invalid for its current protocol, and dropped them from its thesis.

**Its loss is the preference mass outside each satellite's top-`k_cap` beams** — exactly what the cap
drops. **With no cap that mass is zero by construction.** The owner's hypothesis ("拿掉上限 penalty
就失效") is true for this penalty, by its definition.

The decorrelation / srank penalties never ran in the sibling beyond a 3-episode smoke test.

## Why it does not transfer, by this project's measurements

1. **No cap here, and adding one breaks the declared endpoint.** A per-satellite cap of 3 on this
   harness serves only **58%** of user-steps and delivers **0.48x** the bits; pooled EE rises 1.162x
   only because fewer lit beams cut interference. That fails the declared C-S service guard
   (−0.5 pp non-inferiority) by roughly 40 points. A cap is not adopted; the capacity penalty has no
   target without one.
2. **srank has no collapse to repair.** Uncapped, OFF's effective rank holds ~40/50 (PENALTYARM);
   capped, only head 0 dips (34.0 vs 40.8) and recovers, and the G-3 indicators show no policy
   collapse. The penalty holds head 0 but lowers heads 1-2 by 3-7 from episode 200.
3. PENALTYARM and the capped comparison are single-seed at 500 episodes; nothing is claimed as an
   effect. A resolvable capped test (~8 seeds x 3 arms, ~5 CPU-h at 500 ep, ~93 CPU-h at 9,000) would
   measure the **capped** MDP, not this project's — **not funded**.

**Ruling:** the penalty is **not** a component of the current design. It stays **dropped on this
project's measurements** (no collapse; no cap), and is revisited only if a later run on the corrected
tree shows Q-row collapse. If the owner wants a cap for its own sake, that is a separate physics
decision, and the service guard would have to change with it.

## Process note

CAPPENALTY placed its cap flag **outside `src/`** because a 2026-08-22 ruling forbids a cap socket in
the live tree and a gate test enforces it — correct, and recorded as the one deviation from its brief.
