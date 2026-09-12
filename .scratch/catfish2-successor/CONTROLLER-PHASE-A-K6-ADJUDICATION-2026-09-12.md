# Controller adjudication — Phase-A `T_H` at DEV k = 6: **continue to k = 7**

Date 2026-09-12. Read against Amendment 14 §6b verbatim. Every number below I re-derived myself from the raw DEVVAL
JSONs in `/home/sat/mcrl-v025-cf2s-ws/runs-phaseA-k6/`, not from the lane's report.

## 1. Independent verification

| arm | EE (M bit/J) | vs D0 | served | p10 (Mbit/s) | p10/D0 | bits/D0 | joules/D0 | min served-user rate |
|---|---|---|---|---|---|---|---|---|
| `D0` | 97.717 | — | 0.99717 | 69.41 | 1.000 | 1.0000 | 1.0000 | 0.301 M |
| **`D3-T_H`** | **101.847** | **+4.23 %** | 0.99717 | 133.84 | **1.928** | 1.1724 | 1.1249 | **12.969 M** |
| `D3-null` | 62.655 | −35.88 % | 0.92663 | 14.20 | 0.205 | 0.5230 | 0.8157 | 0.000 |

Paired over the 24 DEVVAL episodes: **23/24** against `D0` (mean +4.36 %, min −2.94 %, max +10.10 %); **24/24**
against the matched null, pooled ratio **×1.6255**. `seed_index` 6, pinned TLE `427e6a91…` on all three.

**The comparability check that mattered.** The lane ran `--episodes 300 --stop-after 100` rather than
`--episodes 100`, because `--episodes 100` would compress the frozen ε decay from 67 to 22 — a hyperparameter change
§6a forbids. I verified that this is not a deviation: **every E0 100-episode run also carries
`episodes_target = 300, episodes_completed = 100`.** The k = 6 numbers are therefore comparable to E0's ep-100
numbers, which is what the seed-noise clause depends on. The interpretive choice was declared before launch and is
correct.

`D3-null` at −35.88 % with served 0.92663 and a minimum served-user rate of exactly 0 reproduces the E0 hard-null
behaviour (−39 to −55 %, served ≈ 0.92). The harness is behaving as it did.

## 2. Amendment 14 §6b, clause by clause

| clause | result |
|---|---|
| EE direction positive against **both** `D0` and the matched null | **PASS** — +4.23 % and ×1.6255 |
| paired DEVVAL direction positive | **PASS** — 23/24 vs D0, 24/24 vs null |
| `served` no worse than −0.5 pp | **PASS** — Δ **0.000 pp**, identical to five decimals |
| `p10 ≥ 0.5 × D0` | **PASS** — ×1.928 |
| bits ratio `≥ 0.95 × D0` | **PASS** — ×1.1724 |
| **not inside development seed noise** | **NOT CLEARED BY THE EE GAP ALONE** — see §3 |

## 3. The clause that does not pass, stated plainly

**+4.23 % on one seed is inside the one-seed noise band and establishes nothing by itself.** The only comparable
reference is the seed-to-seed spread of the arm-vs-`D0` gap at ep 100 in E0 (+9.11 / +13.34 / +9.23 %, range 4.23 pp,
s.d. 2.41 pp): T_H's entire effect is the size of that spread. And k = 6's `D0` (97.717 M) is the weakest development
`D0` measured so far, which **inflates** a relative gap rather than deflating it.

The lane raised this against itself rather than being caught at it, and it is right. Two further limits I add:

- The 23/24 pairing is a **within-seed** statistic. It says the effect is consistent across episodes at k = 6; it says
  nothing about whether a different seed would show it, which is exactly the open question.
- The E0 spread is a proxy, not a null distribution. We have no replicate `D0` at a fixed seed, so no direct estimate
  of what gap seed luck alone produces.

## 4. Why the lane continues anyway

§6b's continuation test is "does k = 6 carry **usable positive transfer**", and the closing condition is its absence.
Transfer is present, and three things sit outside any plausible noise band:

1. **The matched-null margin, ×1.6255 with 24/24 pairing.** This is the load-bearing control, and it is not close.
2. **The behavioural signature is large and specific**: minimum served-user rate ×43.1 (0.301 → 12.969 Mbit/s) at
   **identical** service, p10 ×1.928, `H_inter` 0.6455 → 0.2369, `H_intra` 0.10996 → 0.00254.
3. **`T_H`'s target differs from T0's on 41.2 % of student-visited decisions**, so this arm is not a relabelled
   `D3-T0`. No `D3-T0` arm was run, and none was required — §6 forbids framing the question that way.

**Ruling: replicate at DEV k = 7, 100 episodes, `D0` / `D3-T_H` / matched `D3-null`, nothing else.** k = 7 is the
instrument the seed-noise question needs; running it is what resolves §3 rather than arguing about it. No hysteresis
sweep, no third seed, no `D3-T0` arm, no scope change.

## 5. What this is not

- **`T_H` is not Catfish #2, and a clean k = 7 will not make it one.** That is earned only by §9's
  `FULL − T0-only` drop-one on both seeds, beyond a resolution declared before the FULL runs.
- **This is not a handover-energy effect.** Joules rose **12.5 %** and bits **17.2 %**. `T_H` buys a much better rate
  tail at somewhat more energy, for a net EE gain — a continuity / rate-tail effect, exactly the role Amendment 14 §6
  declared, and the handover-energy framing would be wrong in the paper because handover has no physical energy cost
  in v023 physics.
- The `+17.2 % bits / +12.5 % joules` operating point is very different from `D3-T0`'s. That is the reason a
  set-valued FULL could in principle combine them, and it is **not** evidence that it will.

## 6. Recorded for §9, before the FULL runs exist

The practical resolution for `FULL − T0-only` must be declared from existing E0 / E1 variation **before** any FULL
result is seen. Nothing in this adjudication may be used to set it, and the k = 6 gap size in particular may not be
reused as a threshold.
