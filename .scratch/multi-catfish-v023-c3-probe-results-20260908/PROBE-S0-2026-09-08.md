# S0 deployable set-decoder diagnostic

Claim ceiling: `TRAIN_DEVELOPMENT_DIAGNOSTIC_PROBE_S0_NO_LEARNER_NO_ADMISSION_NO_TEST`

| Arm | Pooled EE (bits/J) | % vs BASE | Service | Served / opportunities |
|---|---:|---:|---:|---:|
| BASE | 124,075,740.547231 | +0.000000% | 99.791667% | 11975 / 12000 |
| B(U1 oracle) | 126,547,715.769454 | +1.992311% | 99.783333% | 11974 / 12000 |
| B(J1 oracle) | 126,832,819.836554 | +2.222094% | 99.766667% | 11972 / 12000 |
| S0 deployable | 126,324,776.402952 | +1.812631% | 99.791667% | 11975 / 12000 |
| S0-U deployable | 125,965,446.280702 | +1.523026% | 99.791667% | 11975 / 12000 |
| S0-J deployable | 126,263,243.469835 | +1.763038% | 99.791667% | 11975 / 12000 |

## Choice agreement

| Comparison | Matches | Fraction |
|---|---:|---:|
| S0 vs ORACLE U1 | 2 / 120 | 1.667% |
| S0 vs ORACLE J1 | 35 / 120 | 29.167% |
| S0 U vs ORACLE U1 | 27 / 120 | 22.500% |
| S0 J vs ORACLE J1 | 36 / 120 | 30.000% |

## Information-gap diagnostic

Per-anchor nominal-vs-realised Spearman rank correlation: mean 0.910408, median 0.922043, range [0.687133, 0.984614] over 120 defined anchors.

All arm scores above use realised E1 tape rows; nominal values are selection-only.
