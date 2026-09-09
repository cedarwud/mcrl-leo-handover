**Correctly paired coordination span (`J_from_first` over `U_first`): `SEALED` +4.6046% (1/20 negative anchors); `MARGIN_Q` +1.2913% (6/20 negative anchors).**

# Reseeded coordination span — V0.25 twenty-anchor panel

`DIAGNOSTIC_NOT_CLAIM`. No learner, training run, or policy run was performed. No sealed constant, threshold, sign, seed, horizon, price, service guard, acceptance rule, sealed artefact, or frozen manifest was changed.

## Direct answers

1. **Same-search coordination span:** **SEALED +4.6046%**; **MARGIN_Q +1.2913%**.

2. **Does the joint selector beat its own better seed?** In the selection-time objective, yes: strict improvement on 20/20 `SEALED` anchors and 20/20 `MARGIN_Q` anchors. In committed EE, `SEALED` is positive/zero/negative on 19/0/1 anchors; `MARGIN_Q` is 14/0/6. The signed per-anchor values are below.

3. **How much was search-order artefact?** The archived headline changes from +6.3590% to +4.6046% under `SEALED`, an overstatement of 1.7544 percentage points. Under `MARGIN_Q`, it changes from +0.5448% to +1.2913%, an understatement of 0.7465 points. The exact three-way decomposition below separates unilateral search order, correctly paired coordination, and joint-seed effect.

The selection-time and committed signs answer different questions: selection uses the fixed one-boundary exact `F`, while the reported coordination span uses the 48-boundary committed EE.

## Pooled committed endpoint

Efficiency is pooled as `sum(bits) / sum(joules)` over the same twenty anchors.

| rule | arm | bits (Tbit) | joules | EE (Mbit/J) |
|---|---|---:|---:|---:|
| `SEALED` | `BASELINE` | 0.545927 | 146564.590466 | 3.724824 |
| `SEALED` | `U_best` | 1.660780 | 58332.519445 | 28.470904 |
| `SEALED` | `U_first` | 1.717485 | 55786.246295 | 30.786890 |
| `SEALED` | `J_from_best` | 1.694405 | 55955.362098 | 30.281369 |
| `SEALED` | `J_from_first` | 1.743418 | 54135.834423 | 32.204505 |
| `MARGIN_Q` | `BASELINE` | 1.390585 | 175288.780717 | 7.933111 |
| `MARGIN_Q` | `U_best` | 3.202141 | 74453.115992 | 43.008830 |
| `MARGIN_Q` | `U_first` | 3.169342 | 72515.853404 | 43.705511 |
| `MARGIN_Q` | `J_from_best` | 3.201929 | 74044.803194 | 43.243127 |
| `MARGIN_Q` | `J_from_first` | 3.173127 | 71676.877602 | 44.269883 |

## Served count and rate-target attainment (separate outcomes)

`served_PHY` counts positive realised decoding time. `rate_target_attained` counts users whose integrated committed bits reach the fixed rate target. They are reported independently and are not combined into one service measure.

| rule | arm | served_PHY count | rate-target attained | anchor-user observations |
|---|---|---:|---:|---:|
| `SEALED` | `BASELINE` | 826 | 0 | 2000 |
| `SEALED` | `U_best` | 1939 | 0 | 2000 |
| `SEALED` | `U_first` | 1961 | 0 | 2000 |
| `SEALED` | `J_from_best` | 1957 | 0 | 2000 |
| `SEALED` | `J_from_first` | 1967 | 0 | 2000 |
| `MARGIN_Q` | `BASELINE` | 1165 | 426 | 2000 |
| `MARGIN_Q` | `U_best` | 2000 | 1359 | 2000 |
| `MARGIN_Q` | `U_first` | 2000 | 1353 | 2000 |
| `MARGIN_Q` | `J_from_best` | 2000 | 1349 | 2000 |
| `MARGIN_Q` | `J_from_first` | 2000 | 1358 | 2000 |

## All four pairings

| rule | pairing | pooled EE gain | negative / zero / positive anchors |
|---|---|---:|---:|
| `SEALED` | `J_from_first` over `U_first` — correct | +4.6046% | 1 / 0 / 19 |
| `SEALED` | `J_from_best` over `U_best` — archived | +6.3590% | 0 / 0 / 20 |
| `SEALED` | `J_from_best` over `U_first` — cross | -1.6420% | 10 / 0 / 10 |
| `SEALED` | `J_from_first` over `U_best` — cross | +13.1137% | 4 / 0 / 16 |
| `MARGIN_Q` | `J_from_first` over `U_first` — correct | +1.2913% | 6 / 0 / 14 |
| `MARGIN_Q` | `J_from_best` over `U_best` — archived | +0.5448% | 7 / 0 / 13 |
| `MARGIN_Q` | `J_from_best` over `U_first` — cross | -1.0580% | 12 / 0 / 8 |
| `MARGIN_Q` | `J_from_first` over `U_best` — cross | +2.9321% | 5 / 0 / 15 |

## Does each joint selector beat its own seed?

Each cell is the anchor-local committed-EE gain and its sign. Selection was by the fixed one-boundary exact `F`, so a negative committed-EE cell does not imply that the selector accepted a negative selection-objective move.

| anchor | SEALED `J_best/U_best` | SEALED `J_first/U_first` | MARGIN_Q `J_best/U_best` | MARGIN_Q `J_first/U_first` |
|---|---:|---:|---:|---:|
| w1/s0 | +4.7981% | +6.8713% | -0.5228% | +1.8039% |
| w1/s1 | +5.6570% | +0.0107% | +0.5861% | +0.3640% |
| w1/s2 | +13.9471% | +3.8169% | -0.1811% | +0.1976% |
| w1/s3 | +17.4406% | +4.4635% | +4.9218% | +2.0278% |
| w1/s4 | +0.8477% | +1.5106% | +0.2004% | +1.2358% |
| w2/s0 | +2.2482% | +6.5311% | -4.3708% | +2.9777% |
| w2/s1 | +3.2898% | +0.2548% | -0.7138% | +0.4280% |
| w2/s2 | +2.2762% | -0.2352% | +0.4533% | -0.7026% |
| w2/s3 | +3.2013% | +5.8301% | -3.3906% | +4.2107% |
| w2/s4 | +15.2744% | +5.0148% | -0.2864% | +8.9056% |
| w3/s0 | +4.8745% | +12.2317% | +0.2905% | -0.1882% |
| w3/s1 | +7.0890% | +1.4900% | +0.0494% | -0.4443% |
| w3/s2 | +2.5118% | +4.6250% | +0.3928% | +0.5603% |
| w3/s3 | +11.0076% | +8.3361% | +1.8153% | +3.6564% |
| w3/s4 | +7.1191% | +0.0574% | +1.0276% | -0.3806% |
| w4/s0 | +1.8291% | +2.3105% | +0.1248% | +0.3330% |
| w4/s1 | +5.1151% | +0.6590% | +0.6220% | -1.1516% |
| w4/s2 | +6.2235% | +7.7349% | +6.9428% | +0.1173% |
| w4/s3 | +9.1980% | +12.7865% | -0.0578% | +0.6206% |
| w4/s4 | +2.2844% | +1.2361% | +1.9222% | -0.0012% |

## Search-order artefact and exact decomposition

The archived pooled span is decomposed additively in EE, with every term divided by `U_best` EE:

`(J_best − U_best) / U_best = (U_first − U_best) / U_best + (J_first − U_first) / U_best + (J_best − J_first) / U_best`.

The three terms are respectively the unilateral search-order effect, correctly paired coordination (expressed on the archived denominator), and the joint-seed effect. This is an exact accounting identity, not a causal model.

| rule | archived span | search-order term | correct coordination term | joint-seed term | search-order / archived |
|---|---:|---:|---:|---:|---:|
| `SEALED` | +6.3590% | +8.1346% | +4.9792% | -6.7547% | 127.92% |
| `MARGIN_Q` | +0.5448% | +1.6199% | +1.3122% | -2.3873% | 297.35% |

The corresponding exact multiplicative identity is `J_best/U_best = (U_first/U_best) × (J_first/U_first) × (J_best/J_first)`. Thus the search-order term can exceed 100% of the archived span when reseeding and correctly paired coordination offset part of it; percentages in the last column are shares of a signed net span, not bounded mixture weights.

## Joint configurations and coalition sizes

- **SEALED:** the two joint arms commit the same configuration on **0/20** anchors. Selected coalition-size counts (`0` means the seed remained selected): `J_from_best` {"3": 8, "4": 6, "5": 2, "6": 2, "8": 1, "9": 1}; `J_from_first` {"11": 2, "3": 10, "4": 3, "6": 2, "7": 1, "8": 1, "9": 1}.
- **MARGIN_Q:** the two joint arms commit the same configuration on **0/20** anchors. Selected coalition-size counts (`0` means the seed remained selected): `J_from_best` {"2": 6, "3": 9, "4": 5}; `J_from_first` {"2": 4, "3": 15, "4": 1}.

## Method and invariants

The converged `U_first` assignments were reused from the completed anytime receipts, produced by the exact first-improvement implementation digest `003bdee1df908fddf652f2f8069c31a6297a7f7178bbb83338d09b3f4add9928`. `U_best`, `J_from_best`, and the neutral baseline were reconstructed from the archived standing-harness receipts. The new run rebuilt and exhausted the joint catalogue independently from each seed; no deadline was applied.

Both joint arms invoke the same sealed `build_joint_candidates` implementation in `sealed/.scratch/ladder-floor-20260910/oracle_runner.py` (SHA-256 `2879a86cecafb9c20647641748ea2c855433f7bcce80e0cdac6843c510a42f68`), with occupant subset max size 4, occupant subset cap 1024, and joint candidate cap 4096. Only the unilateral seed—and therefore seed-derived occupancies, interference contributors, and physically best alternatives—changes.

For **both** `J_from_best` and `J_from_first`, on **every anchor**, the served-count guard reference is that anchor's neutral `BASELINE` selection-time `served_PHY` count. It is not reset to either unilateral seed. The objective remains exact binary64 `F = B − eta_ref·E`, the price and tie-break are unchanged, and committed reporting uses all 48 realised boundaries at `fading_quantile_alpha = 0.10`.

As an internal reproduction control, every newly rebuilt `J_from_best` selection had to match the archived joint configuration exactly. The committed bits, joules, EE, and served counts for `BASELINE`, `U_best`, `U_first`, and `J_from_best` are retained verbatim from their source receipts. Each was also re-evaluated alone to obtain rate-target attainment; configuration, assignments, and served count had to match, while last-bit numeric deltas caused by dense-batch composition are recorded in `summary.standing_metric_singleton_re_evaluation_max_abs_delta` rather than substituted into the standing measurements. `J_from_first` is a new singleton 48-boundary evaluation.

## Reproduction

From `/home/sat/mcrl-v025-harness-ws`:

```console
$ env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m harness.reseeded_span run --variant SEALED --out receipts/reseeded-span-sealed.json --resume
$ env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m harness.reseeded_span run --variant MARGIN_Q --out receipts/reseeded-span-margin-q.json --resume
$ env PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m harness.reseeded_span report --sealed receipts/reseeded-span-sealed.json --margin receipts/reseeded-span-margin-q.json --out RESEEDED-SPAN-2026-09-10.md
```

Receipts:

- `receipts/reseeded-span-sealed.json` — receipt SHA-256 `f1fd49229a297295a0addadebc3f929ddd333272bbe9e8d698ce22bc18dd09ba`; source anytime receipt `0863215a4602cd102f3f98e0cb24523e1d4bad57a653a88ffca1e4b285cc453c`; source archived receipt `a358cda5cf7bbb361b24c2916168f9e7965461ce062cc2daab1fd5b1e62201fe`.
- `receipts/reseeded-span-margin-q.json` — receipt SHA-256 `f225f34d9edfb942029d677ae1847ef6d0dd32ee4ba9a922e3bfed8726325a72`; source anytime receipt `d3b1f1612bf5ecaa3ad6563597af3243ab576435423535a55c4acccc3c07c546`; source archived receipt `d0d39ae5b6b7aa7bc9e4849700747704d87b2be7438b40c33ff91e1552c2e1b1`.

## What was not reached

No learner, training, policy, tuning, new local-search order, new catalogue family, expanded cap, changed guard, statistical inference, or timing claim was attempted. This diagnostic covers only the fixed twenty anchors and the two existing provisioning rules. It does not revisit the five-point beam-width curve or thirty-date interval; their coordination quantities remain stale until recomputed with correctly paired seeds. No sealed artefact or frozen manifest was modified.
