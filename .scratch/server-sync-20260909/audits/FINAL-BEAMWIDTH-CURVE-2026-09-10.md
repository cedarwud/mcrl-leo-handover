**No. The strict-clearance, correctly paired corrected-rule gap at 1.66° is +0.899421%; at 3.32° it is +1.154601%.**

# Final strict-clearance, correctly paired beam-width curve

`DIAGNOSTIC_NOT_CLAIM`

All five widths reached all 8/8 anchors under both provisioning rules: 40/40 anchors per rule and 80/80 paired rule-width evaluations overall. No learner, training, or policy run was performed. The sealed one-sided beam half-power angle remains 1.66°; the other widths are diagnostic points. No sealed constant, threshold, sign, seed, horizon, price, service guard, acceptance rule, cap, catalogue rule, or declared provisioning rule was changed or replaced.

## Direct answers

1. At the sealed 1.66° design point, the corrected-rule correctly paired gap is **+0.899421%**, with 1/8 negative anchors. Therefore the answer to whether it remains negative is **no**.

2. At the source's own 3.32° one-sided width, the corrected-rule correctly paired gap is **+1.154601%**, with 4/8 negative anchors.

3. The correctly paired corrected-rule curve is `+0.899421%`, `+0.820174%`, `+1.154601%`, `+2.156154%`, `+4.022219%` and is **not monotone** over the sampled widths. The correctly paired sealed-rule curve is `+3.618798%`, `+10.834491%`, `+12.549948%`, `+19.960312%`, `+26.186258%` and is **strictly increasing**.

No wider width is presented as a remedy for the 1.66° result; any antenna change is a separate design decision outside this diagnostic.

## Correctly paired curve

Pooled efficiency is `sum(bits) / sum(joules)` across the same eight anchors. Negative-anchor counts use each anchor's independently committed 48-boundary efficiency.

| One-sided width | SEALED `J_from_first/U_first` | Negative anchors | STRICT corrected `J_from_first/U_first` | Negative anchors |
|---:|---:|---:|---:|---:|
| 1.66° | +3.618798% | 1/8 | +0.899421% | 1/8 |
| 2.40° | +10.834491% | 0/8 | +0.820174% | 2/8 |
| 3.32° | +12.549948% | 0/8 | +1.154601% | 4/8 |
| 4.50° | +19.960312% | 0/8 | +2.156154% | 2/8 |
| 6.65° | +26.186258% | 0/8 | +4.022219% | 2/8 |

## Pooled efficiency and every pairing

`Published` is `J_from_best/U_best`; `correct` is `J_from_first/U_first`. The two cross-pairings are shown because they make the search-order/seed accounting explicit. EE units are Mbit/J.

| Rule | Width | `U_best` EE | `U_first` EE | `J_from_best` EE | `J_from_first` EE | Published gap | Correct gap | `J_best/U_first` | `J_first/U_best` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `SEALED` | 1.66° | 26.762144 | 31.197313 | 28.502170 | 32.326281 | +6.501817% | +3.618798% | -8.639024% | +20.791072% |
| `SEALED` | 2.40° | 25.520418 | 26.541898 | 28.173719 | 29.417578 | +10.396775% | +10.834491% | +6.148092% | +15.270752% |
| `SEALED` | 3.32° | 28.956269 | 25.513267 | 32.304457 | 28.715169 | +11.562912% | +12.549948% | +26.618269% | -0.832636% |
| `SEALED` | 4.50° | 19.449378 | 14.568755 | 22.296534 | 17.476724 | +14.638803% | +19.960312% | +53.043506% | -10.142502% |
| `SEALED` | 6.65° | 3.145927 | 5.072770 | 4.465599 | 6.401138 | +41.948593% | +26.186258% | -11.969220% | +103.473852% |
| `STRICT` | 1.66° | 43.359180 | 42.912629 | 43.282521 | 43.298595 | -0.176800% | +0.899421% | +0.861963% | -0.139729% |
| `STRICT` | 2.40° | 42.232804 | 42.747801 | 43.055641 | 43.098407 | +1.948336% | +0.820174% | +0.720132% | +2.049597% |
| `STRICT` | 3.32° | 42.739629 | 44.218784 | 43.742303 | 44.729335 | +2.346006% | +1.154601% | -1.077553% | +4.655412% |
| `STRICT` | 4.50° | 42.227965 | 41.644413 | 43.498060 | 42.542330 | +3.007711% | +2.156154% | +4.451130% | +0.744450% |
| `STRICT` | 6.65° | 33.583600 | 41.320836 | 36.324946 | 42.982850 | +8.162750% | +4.022219% | -12.090487% | +27.987619% |

## Served counts

`served_PHY` means positive realised decoding time. Each width/rule has 800 anchor-user observations.

| Rule | Width | `U_best` | `U_first` | `J_from_best` | `J_from_first` |
|---|---:|---:|---:|---:|---:|
| `SEALED` | 1.66° | 779/800 | 782/800 | 790/800 | 786/800 |
| `SEALED` | 2.40° | 761/800 | 753/800 | 774/800 | 776/800 |
| `SEALED` | 3.32° | 701/800 | 668/800 | 729/800 | 713/800 |
| `SEALED` | 4.50° | 528/800 | 473/800 | 607/800 | 555/800 |
| `SEALED` | 6.65° | 158/800 | 219/800 | 220/800 | 278/800 |
| `STRICT` | 1.66° | 800/800 | 800/800 | 800/800 | 800/800 |
| `STRICT` | 2.40° | 800/800 | 800/800 | 800/800 | 800/800 |
| `STRICT` | 3.32° | 800/800 | 800/800 | 800/800 | 800/800 |
| `STRICT` | 4.50° | 781/800 | 779/800 | 781/800 | 787/800 |
| `STRICT` | 6.65° | 678/800 | 758/800 | 711/800 | 769/800 |

## Rate-target attainment

This is the separate count of users whose integrated achieved rate reaches the fixed 50 Mbit/s target; it is not combined with served count. Each width/rule again has 800 observations.

| Rule | Width | `U_best` | `U_first` | `J_from_best` | `J_from_first` |
|---|---:|---:|---:|---:|---:|
| `SEALED` | 1.66° | 0/800 | 0/800 | 0/800 | 0/800 |
| `SEALED` | 2.40° | 0/800 | 0/800 | 0/800 | 0/800 |
| `SEALED` | 3.32° | 0/800 | 0/800 | 0/800 | 0/800 |
| `SEALED` | 4.50° | 0/800 | 0/800 | 0/800 | 0/800 |
| `SEALED` | 6.65° | 0/800 | 0/800 | 0/800 | 0/800 |
| `STRICT` | 1.66° | 540/800 | 546/800 | 539/800 | 548/800 |
| `STRICT` | 2.40° | 497/800 | 481/800 | 492/800 | 492/800 |
| `STRICT` | 3.32° | 434/800 | 431/800 | 427/800 | 434/800 |
| `STRICT` | 4.50° | 347/800 | 329/800 | 357/800 | 327/800 |
| `STRICT` | 6.65° | 242/800 | 243/800 | 254/800 | 241/800 |

## Change from the previously published gap

For each width and rule, the percentage-point change is decomposed by the exact path `J_from_best/U_best` → `J_from_best/U_first` → `J_from_first/U_first`. The first step is the search-order part (replace the unilateral denominator while holding the old joint arm fixed); the second is the seed part (rebuild the joint arm from `U_first` while holding that denominator fixed). These two parts sum exactly to `correct gap − published gap`; this is an accounting identity, not a causal allocation.

| Rule | Width | Published gap | Search-order part | Intermediate `J_best/U_first` | Seed part | Correct gap | Net change |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SEALED` | 1.66° | +6.501817% | -15.140841 pp | -8.639024% | +12.257822 pp | +3.618798% | -2.883019 pp |
| `SEALED` | 2.40° | +10.396775% | -4.248684 pp | +6.148092% | +4.686399 pp | +10.834491% | +0.437715 pp |
| `SEALED` | 3.32° | +11.562912% | +15.055357 pp | +26.618269% | -14.068321 pp | +12.549948% | +0.987036 pp |
| `SEALED` | 4.50° | +14.638803% | +38.404703 pp | +53.043506% | -33.083194 pp | +19.960312% | +5.321509 pp |
| `SEALED` | 6.65° | +41.948593% | -53.917814 pp | -11.969220% | +38.155478 pp | +26.186258% | -15.762335 pp |
| `STRICT` | 1.66° | -0.176800% | +1.038764 pp | +0.861963% | +0.037458 pp | +0.899421% | +1.076221 pp |
| `STRICT` | 2.40° | +1.948336% | -1.228204 pp | +0.720132% | +0.100041 pp | +0.820174% | -1.128162 pp |
| `STRICT` | 3.32° | +2.346006% | -3.423559 pp | -1.077553% | +2.232155 pp | +1.154601% | -1.191405 pp |
| `STRICT` | 4.50° | +3.007711% | +1.443419 pp | +4.451130% | -2.294976 pp | +2.156154% | -0.851556 pp |
| `STRICT` | 6.65° | +8.162750% | -20.253237 pp | -12.090487% | +16.112706 pp | +4.022219% | -4.140531 pp |

## Pairing, search, and clearance provenance

The unilateral arm calls the first-improvement implementation directly from the read-only harness file `/home/sat/mcrl-v025-harness-ws/harness/anytime.py`, SHA-256 `003bdee1df908fddf652f2f8069c31a6297a7f7178bbb83338d09b3f4add9928`. The adapter does not contain a local copy of that search. It uses users in sorted order, sealed legal-option order, microbatches of 16, commits the first strict `F` improvement satisfying the unchanged neutral-baseline served-count guard, and completes the terminal no-move pass.

The joint arm calls the read-only harness reseeding routine in `/home/sat/mcrl-v025-harness-ws/harness/reseeded_span.py`, file SHA-256 `78367ea81862d8ac10b4c6ebb373dcd251fab274578fe7844a34bc213ba4e69e`. That routine independently completes the alternate sweep from each supplied seed and calls this beam runner's unchanged `build_joint_candidates`. The catalogue remains same-beam subsets of size 2–4 with the 1,024-generation cap, victim plus top-2/top-3 physical contributors, complete-beam evacuations, and the 4,096 global cap. Every new joint arm records `U_first` as its seed and a strict boundary-0 objective improvement on 8/8 anchors at every rule-width point.

The strict corrected arm uses the hash-pinned dense implementation SHA-256 `bf9f3cfecba54125c6a7736f550032e6bd7292f03f8fc6281f1d02979c14a85f` through `.scratch/beamwidth/strict_clearance_adapter.py`. Selection and both committed first-search arms use that strict evaluator throughout; no simple-division receipt supplies a corrected-rule metric. The existing strict clearance fixture and ladder-adapter audits are run before the curve jobs.

Standing `U_best` and `J_from_best` committed metrics are retained verbatim from the prior sealed and strict-clearance beam receipts. New `U_first` and `J_from_first` configurations are each evaluated alone over all 48 realised boundaries. Selection remains at realised boundary 0; no committed result is fed back into selection.

The worlds are `V025_PROBE_R2/world/1` and `/2`, steps 0–3, with 100 users per anchor. The world digests, TLE dates, training seeds, neutral nearest-eligible baseline configuration, exact binary64 objective with `eta_ref = 19,720,681.00172232 bit/J`, tie-break, price, served-count guard, rate target, caps, and all other sealed inputs are checked or inherited unchanged.

## Exact reproduction command

Run from `/home/sat/mcrl-v025-beam-ws`:

```bash
bash .scratch/beamwidth/run_final_beamwidth_curve.sh
```

The wrapper uses `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, one BLAS/OpenMP thread per job, `nice -n 15`, at most three concurrent jobs, and resumable per-rule/per-width receipts. It finishes by rebuilding this Markdown file and byte-checking that a second report build is identical.

## Machine-readable evidence and hashes

```text
a035c17491b6a743b39b65c4cdbdf453d4aa7a4180ced5b4fc3055a355709c64  .scratch/beamwidth/final-sealed-one-sided-1.66.json
2fc7eafdacd051f305cad0dc40bc9d161d48e990c6aa9d7191f0d696cbf61ae6  .scratch/beamwidth/final-sealed-one-sided-2.40.json
20c33a54d624f94f41bfc017bb6e03f0fd8176a5197ae976fd0c03419641f217  .scratch/beamwidth/final-sealed-one-sided-3.32.json
3396bc361adfa858aadc986a15fd380b8f89cc5e4d43a20d3e8253a4ca9e78aa  .scratch/beamwidth/final-sealed-one-sided-4.50.json
edfb8a2801e7d994cfcb276f0fee012092ef97a1f45e60f2f73e9454a735b885  .scratch/beamwidth/final-sealed-one-sided-6.65.json
35732966ad6008f50338f85187ba718ca1dda22d714489d6bf48e7992cbf1b9b  .scratch/beamwidth/final-strict-one-sided-1.66.json
df8246251da94b79c84754734d890bae3826c73247f249e573b2e99986c0bb46  .scratch/beamwidth/final-strict-one-sided-2.40.json
46859c30605e4fea98f630a11f239035fc6a000d1f31904adfaf0578b40d904c  .scratch/beamwidth/final-strict-one-sided-3.32.json
0b67359d3250d84ec6e9a2e79f8a8de37386bcf88fcd46f8bdfd44930b7cb9c3  .scratch/beamwidth/final-strict-one-sided-4.50.json
f5f13132afe9ccab269a8b10b6aedf6ca46f7fc3e7ff0fd0b0e689c9bada53df  .scratch/beamwidth/final-strict-one-sided-6.65.json
003bdee1df908fddf652f2f8069c31a6297a7f7178bbb83338d09b3f4add9928  /home/sat/mcrl-v025-harness-ws/harness/anytime.py
78367ea81862d8ac10b4c6ebb373dcd251fab274578fe7844a34bc213ba4e69e  /home/sat/mcrl-v025-harness-ws/harness/reseeded_span.py
8aa37ebf1e444d1d9c335cad510cdb5ee4c32dd5143bb56e7cc85937b62ed985  .scratch/beamwidth/run_beamwidth_network.py
390ac38a10e4dbf9908ba5b2ec4bbd50fb8f87527ae3dfe4c702b04011d06c88  .scratch/beamwidth/strict_clearance_adapter.py
497735b791f4f1d42b7b66db8364d263d636b9d7d971b84ea3677ec23b4461a6  .scratch/beamwidth/final_beamwidth_curve.py
a3657713ed7c2cf27b5f01922214a909c9f1831537b705fb2bc6516b55f8488e  .scratch/beamwidth/run_final_beamwidth_curve.sh
```

Every final receipt embeds all eight anchor rows, exact configuration IDs and assignments, first-improvement terminal certificates, joint-selection certificates, selection evaluation counts, separate committed bits/joules/served/target metrics, world identities, source receipt hashes, and its own canonical SHA-256 digest.

Widths not reached: **none**.
