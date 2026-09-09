# Controller finding — the ephemeris archive is 124 times larger than our usage, and the constellation grew 34 % across it
Recorded 2026-09-09. Verified by reading the archive and counting the files. `DIAGNOSTIC_NOT_CLAIM`.

## What is on disk
`~/demo/tle_data/starlink/tle` is a symlink to `/home/sat/mcrl-runtime/tle-frozen-20260820`, the frozen authority archive: **373 daily files, 2025-07-27 to 2026-08-20, 569 MB**. Several workspaces carry a copy named `tle-frozen-20260820-authority-v1`. The engine's `DEFAULT_TLE_ROOT` points at the symlink, so the frozen archive is what production uses.

A second symlink, `tle-live-full-20260824`, points at a live archive that runs **19 days further, to 2026-09-08**.

## What we use
**Three days out of 373.** Training draws on `V025_PROBE/world/1` and `world/2`; evaluation used `world/3`, a single date, `2025-11-16`.

The 180-row coalition corpus is 90 anchors times two worlds. Ten times the worlds would give ten times the anchors from the unchanged generation rule, with real geographic and temporal variety rather than more slices of the same two days. So the corpus shortage and the one-date statistics problem are **the same defect**: too few worlds were generated. I had been treating them as two findings.

## The constellation grew by a third across the archive
| date | satellites |
|---|---:|
| 2025-08-01 | 8,044 |
| 2025-12-01 | 8,990 |
| 2026-04-01 | 10,100 |
| 2026-08-20 | 10,746 |

That is **+33.6 %** from the oldest sampled point to the newest.

This makes a measurement discipline mandatory rather than advisable. A date-to-date variance estimated across widely separated dates mixes geometric variation with a growing constellation. Sizing an experiment from that number could either demand too many dates or mistake a trend for random variation. The variance must therefore be reported **twice**: within a single month, which isolates geometry, and across the full span, which includes growth.

The existing sealed world manifests already span 2025-07 to 2026-05, so this confound is present in what we have, not only in what we might generate.

## Which archive to use, and why it is not a freshness question
**Continue using the frozen archive.** Its purpose is reproducibility: a live archive grows daily, so the same experiment re-run tomorrow would build different worlds. The sealed declarations also carry a TLE date convention and forbid a TEST split, and selecting dates from a moving archive risks drawing a date that was meant to be held out.

Data volume was never the constraint. 373 days is 124 times our current usage.

The 19 extra live days have one legitimate use, later: an external freshness check against the current constellation, explicitly outside the frozen set and carrying no statistical claim. Doing it now would add a variable to an experiment that has not started, and would require freezing and hashing a new archive version.

## Standing
No threshold, sign, seed, horizon, price, service guard, acceptance rule or claim condition changes. No run is authorised. Whether to generate more worlds, and how many, is the owner's decision once the per-world cost measurement lands.
