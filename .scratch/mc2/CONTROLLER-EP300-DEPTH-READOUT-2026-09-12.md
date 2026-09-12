# Controller readout — ep-300 depth diagnostic on the selection seeds, and the owner's priority rule

Date 2026-09-12. **Development lane; a depth diagnostic on the SELECTION seeds k = 10, 11 — never a confirmation.**
Declared before it was read (`CONTROLLER-EP100-DECISION-2026-09-12.md` §5). The 16 selection runs were resumed from
their `resume.pt` at ep 100 to the configured budget of 300 (same configuration identity, code `11466998`, TLE
`427e6a91…`); every file was read raw by the controller (episode and TLE asserted per file). Lane B's independent
recomputation is the second path.

## 1. Seed-mean pooled EE by depth (M bit/J, 24 DEVVAL episodes; per-seed in brackets)

| cell | ep 100 | ep 200 | ep 300 |
|---|---:|---:|---:|
| `D0` | 97.07 (93.99 / 100.15) | 103.92 (104.03 / 103.81) | 98.83 (100.91 / 96.75) |
| `D3-T0` | 112.98 (112.71 / 113.25) | 112.52 (112.47 / 112.57) | **113.41** (113.13 / 113.69) |
| `B-only` | 104.37 | 107.13 | 105.17 |
| `v1 FULL` | 109.85 | 112.11 | 110.56 (111.47 / 109.64) |
| `v1 B-null` | 110.33 | 110.59 | 110.52 |
| `v2 A-only` | 109.36 | 110.26 | 108.91 |
| `v2 FULL` | 109.85 | 106.25 | 107.81 (107.10 / 108.51) |
| `v2 B-null` | 105.32 | 107.53 | 103.46 |

## 2. The owner's priority rule (ruling 2026-09-12 15:36 §6), applied

An old version earns priority for a three-fresh-seed confirmation only if **all** required magnitudes, nulls and QoS
floors pass at ep 300 with **both** selection seeds positive; FULL/T0 turning positive alone is not enough, and the
ep-100 FAIL is not withdrawn.

| clause at ep 300 | v1 | v2 |
|---|---|---|
| FULL vs own A-only ≥ +1.0 % | −2.51 % (−1.46 / −3.56) FAIL | −1.00 % (−2.38 / +0.38) FAIL |
| FULL vs `D3-T0` ≥ +1.0 % | −2.51 % FAIL; paired 6/24, 0/24 | **−4.94 %** (−5.33 / −4.55) FAIL; paired 0/24, 0/24 |
| FULL vs B-only > 0, both seeds | +5.12 % pass | +2.50 % pass |
| FULL vs own B-null > 0, both seeds | +0.05 % (+1.79 / −1.69) FAIL | +4.23 % pass |
| QoS floors per seed | pass | pass |
| min-margin score | −2.51 % | −4.94 % |

**Neither old version qualifies.** The shortfall against the unconditional anchor does not close with depth: it holds
for v1 (−2.77 → −2.51 %) and widens for v2 (−2.77 → −4.94 %). The label channel stays closed on depth as well as at
ep 100.

**Consequence (owner's rule, applied mechanically): v3 proceeds, and the first fresh confirmation seeds, k = 12, 13, 14,
go to v3.** k = 15, 16, 17 stay unused. No v4 and no weight sweep are authorised; if v3 fails its own confirmation, the
data go to the owner.

## 3. Wording limits carried forward (owner ruling §8)

These numbers **support** poor transfer of a judge-gated relabelling to the learner at this budget; they do not prove
that the gated policy is unrepresentable, and three points that differ in both dose and source do not prove the effect
is independent of content.
