# Date-variance diagnostic — stopped at split audit

**Paired log-contrast sample standard deviation: NOT MEASURED (`n = 0` dates).** The task's mandatory stop condition triggered before world generation: the repository has a clear TRAIN/TEST/embargo ephemeris split, but it has no date-level rule that prevents evaluation dates from also being used for training. No TLE file content was opened, no world tape was generated, and no arm outcome was evaluated.

`DIAGNOSTIC_NOT_CLAIM` — 2026-09-09

## Why execution stopped

The active ephemeris rule is unambiguous but only two-way:

- 7 calendar days TRAIN;
- 1 embargo day;
- 7 calendar days TEST;
- 1 embargo day;
- repeat every 16 days from archive date `2025-07-27`.

The implementation defines `TRAIN`, `TEST`, and the non-sampling label `EMBARGO`, but no validation/evaluation date pool (`src/mcrl/env/ephemeris.py:163-179,182-310`). The normal provider is fail-closed against TEST starts and TEST-file reads (`src/mcrl/physics_v025/provider_legacy.py:145-158,161-211`). The one-day embargo means the provider's date-1/date/date+1 element window cannot reach a TEST date from a TRAIN start.

That protection does not establish evaluation-versus-training disjointness:

1. The current V0.25 Stage 8 contract places evaluation on about 600 **TRAIN** worlds over about 161 dates and says “no TEST split” (`.scratch/multi-catfish-v025-physics-successor/V025-STAGES-6-8-CONTRACT-v0-2026-09-08.md:19-21`).
2. The allocation guard rejects a `CLAIM_PANEL` date shared with a successor development role, but it never compares evaluation dates with training-source dates (`.scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py:5726-5743`).
3. The governing freshness amendment excludes probe, calibration, rehearsal, KAT, and synthetic-real dates from the claim panel; training-source dates are not included in that exclusion (`.scratch/multi-catfish-v025-physics-successor/V025-PHYSICS-SUCCESSOR-PRIORITY-DECLARATION-v1.5-AMENDMENT-2026-09-08.md:7-9`).
4. The unrelated E1 train/validation/test partition is by `source_seed`, not by date (`src/mcrl/runtime/ee_axis_e1_split.py:12-14,120-151`).

Therefore the code does not prove that an evaluation date cannot collide with a training date. Choosing a non-TEST evaluation pool would require guessing an allocation rule, which the task expressly forbids.

## Filename-only TLE inventory

`TleArchive` obtains its catalogue by matching and sorting `starlink_YYYYMMDD.tle` directory-entry names; file contents are loaded only by a separate lazy `load()` path (`src/mcrl/env/tle.py:42,213-283`). A directory-name census found **373 available daily files** spanning **2025-07-27 through 2026-08-20**.

This is an exact compact enumeration: every calendar date in that inclusive span is available except these 17 dates:

`2025-08-02`, `2025-08-07`, `2025-08-22`, `2025-09-17`, `2025-10-18`, `2025-10-25`, `2025-11-09`, `2026-01-12`, `2026-02-25`, `2026-03-04`, `2026-03-14`, `2026-03-15`, `2026-06-17`, `2026-06-21`, `2026-06-30`, `2026-07-25`, `2026-08-04`.

Applying the executable split to filenames only gives:

| Part | Existing files | May be opened by this diagnostic? |
|---|---:|---|
| TRAIN | 166 | Only after an evaluation/training allocation rule is supplied |
| EMBARGO | 47 | No start dates |
| TEST | 160 | **No — reserved and untouched** |

The TEST calendar blocks, listed so the prohibition is auditable, are:

`2025-08-04..2025-08-10`; `2025-08-20..2025-08-26`; `2025-09-05..2025-09-11`; `2025-09-21..2025-09-27`; `2025-10-07..2025-10-13`; `2025-10-23..2025-10-29`; `2025-11-08..2025-11-14`; `2025-11-24..2025-11-30`; `2025-12-10..2025-12-16`; `2025-12-26..2026-01-01`; `2026-01-11..2026-01-17`; `2026-01-27..2026-02-02`; `2026-02-12..2026-02-18`; `2026-02-28..2026-03-06`; `2026-03-16..2026-03-22`; `2026-04-01..2026-04-07`; `2026-04-17..2026-04-23`; `2026-05-03..2026-05-09`; `2026-05-19..2026-05-25`; `2026-06-04..2026-06-10`; `2026-06-20..2026-06-26`; `2026-07-06..2026-07-12`; `2026-07-22..2026-07-28`; `2026-08-07..2026-08-13`.

## Dates already used or reserved

The domain-to-seed rule and TRAIN sampler make these starts exactly reproducible from filenames without opening TLE contents (`src/mcrl/physics_v025/tapes.py:37-65`; `src/mcrl/runtime/training_pipeline.py:868-872`; `src/mcrl/env/ephemeris.py:381-427`).

### Formal sealed provider manifests

| Role/domain | World seed | Start UTC | Date part |
|---|---:|---|---|
| `V025_PROBE_R2/world/1` | 3525272352645343090 | 2026-05-30T06:47:04.960000+00:00 | TRAIN |
| `V025_PROBE_R2/world/2` | 3445540383109071487 | 2025-07-28T22:44:07.680000+00:00 | TRAIN |
| `V025_PROBE_R2/world/3` | 7939426026589121673 | 2026-05-01T09:17:28.960000+00:00 | TRAIN |
| `V025_PROBE_R2/world/4` | 7968277797828994069 | 2026-05-28T11:42:22.080000+00:00 | TRAIN |
| `V025_CAL_R2/world/1` | 2110504498518604920 | 2026-08-05T16:27:07.520000+00:00 | TRAIN |
| `V025_CAL_R2/world/2` | 3688583418787175730 | 2025-11-22T16:21:06.560000+00:00 | TRAIN |

### Earlier V0.25 development namespace

| Domain | World seed | Start UTC | Recorded use |
|---|---:|---|---|
| `V025_PROBE/world/1` | 5261619120743994529 | 2026-01-07T09:03:56.800000+00:00 | training corpus; development/rehearsal |
| `V025_PROBE/world/2` | 2841976778378234394 | 2026-03-11T00:59:09.440000+00:00 | training corpus |
| `V025_PROBE/world/3` | 3539351422561826982 | 2025-11-16T01:35:45.280000+00:00 | sole completed evaluation date |
| `V025_PROBE/world/4` | 6141307851813268626 | 2026-03-28T13:02:34.880000+00:00 | quarantined development namespace |

All are TRAIN dates. The reconstruction of world 3 agrees with the stated completed evaluation date, `2025-11-16`.

### Full reported allocation ledger

The reported active 24-identity allocation covers 22 distinct dates:

`2025-07-28`, `2025-08-14`, `2025-10-02`, `2025-10-31`, `2025-11-02`, `2025-11-22`, `2025-12-05`, `2025-12-23`, `2025-12-24`, `2026-01-07`, `2026-01-20`, `2026-01-23`, `2026-01-25`, `2026-02-06`, `2026-02-08`, `2026-03-28`, `2026-04-30`, `2026-05-01`, `2026-05-28`, `2026-05-30`, `2026-06-15`, `2026-08-05`.

It consists of PROBE 4, CALIBRATION 2, REHEARSAL 1, KAT 8, SYNTHETIC_REAL 4, SMOKE 1, and CLAIM_PANEL 4 identities (`.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE4H-REPORT-2026-09-09.md:82-86`). The four reserved claim dates are `2026-02-06`, `2026-01-25`, `2026-03-28`, and `2025-12-05`; no claim-panel outcome was opened. Adding the earlier training/evaluation namespace yields a conservative **24 distinct TRAIN dates already used or reserved**.

## Requested measurements not run

The following are intentionally absent because they require generating/evaluating candidate dates after the unresolved split decision:

| Requested output | Status |
|---|---|
| World tapes on at least 12 dates | Not generated |
| World digest and start time per candidate date | Not generated |
| Satellite count per used ephemeris file | Not measured; no TLE content opened |
| BASELINE / certified iterated-unilateral / bounded perfect-knowledge evaluations | Not run |
| Per-date `log(EE_oracle) - log(EE_unilateral)` | Not measured |
| Across-date mean, SD, minimum, maximum, outliers | Undefined (`n = 0`) |
| Wide-date versus within-month variance | Not measured |
| One-tape wall time, core time, and peak disk | Not measured |
| 20/50/100-world cost projections | Not computed from an unperformed benchmark |

No confirmatory experiment was sized, no threshold/sign/seed/horizon/price/service guard/acceptance rule was changed, and no sealed manifest was touched.

## Required owner decision to resume

Specify a prospective, outcome-blind partition of non-TEST dates into at least:

- dates eligible for training-source generation; and
- dates eligible for this learner-free evaluation diagnostic,

with an executable disjointness check and a ruling on whether the 24 already used/reserved dates are excluded. Once that rule is supplied, the measurement can resume without opening any TEST date.

The fuller source-by-source audit is in `.scratch/date-variance/inventory.md`.

Method note: the research workflow's primary-source requirement is why every substantive split and inventory conclusion above is tied directly to executable repository code or an immutable project record.
