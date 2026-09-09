# Open decision for the owner — there is no rule keeping evaluation dates off training dates
Recorded 2026-09-09. Found because a commissioned job **stopped rather than guess**, which was the correct behaviour. No world was generated and no ephemeris file was opened.

## The gap
The executable ephemeris split is a 16-day cycle from 2025-07-27: **7 days TRAIN, 1 embargo, 7 days TEST, 1 embargo**. The code defines `TRAIN`, `TEST` and a non-sampling `EMBARGO`, and the provider is fail-closed against TEST starts and TEST file reads. The embargo day means a TRAIN start's element window cannot reach a TEST date.

**That protection is entirely about TEST. Nothing separates evaluation dates from training dates.**

Four places confirm it:
* the Stage 8 contract places evaluation on about 600 **TRAIN** worlds across about 161 dates while declaring "no TEST split";
* the allocation guard rejects a claim-panel date shared with a successor development role, but never compares evaluation dates against training-source dates;
* the freshness amendment excludes probe, calibration, rehearsal, KAT and synthetic-real dates from the claim panel, and **training-source dates are not in that exclusion list**;
* the only train/validation/test partition in the codebase splits by source seed, not by date.

## Why it matters more than the defects I spent today on
Everything else found today affects **whether we can get a result**. This affects **whether a result would mean anything**. If evaluation worlds are built from dates the learner trained on, part of any gain may be memorisation of specific constellation geometry rather than generalisation, and no amount of bootstrap or seed count detects that.

I had also been misreading the non-negotiable. "No TEST split" does not mean no TEST partition exists; the partition exists and is enforced. It means the headline result does not rely on it. The train-versus-evaluation question is a separate one that the sealed documents never answer.

## Inventory, for whichever option is chosen
373 daily files, 2025-07-27 to 2026-08-20, of which **166 are TRAIN**. Seventeen calendar dates inside that span are missing from the archive: 2025-08-02, 08-07, 08-22, 09-17, 10-18, 10-25, 11-09, 2026-01-12, 02-25, 03-04, 03-14, 03-15, 06-17, 06-21, 06-30, 07-25, 08-04. Any spread of dates must route around those gaps.

## Three options, with what each costs
**A. Carve an evaluation pool out of TRAIN.** Reserve a declared subset of the 166 TRAIN dates for evaluation only, never for source generation, with its own embargo against the training dates. Costs training dates, which is the resource we have most of. Keeps "no TEST split" literally true. Requires an amendment naming the pool and the embargo.

**B. Use TEST as the evaluation pool.** Clean by construction and already enforced fail-closed. But it directly contradicts the sealed non-negotiable, and it spends the held-out set on an experiment that is not the final claim.

**C. Declare the overlap and quantify it.** Keep the present arrangement, state plainly in the paper that evaluation dates may coincide with training dates, and measure the size of the effect by comparing results on overlapping and non-overlapping dates. Honest and cheap, but it puts a known weakness in the paper that a reviewer will find first.

My reading is that **A** is the only one that both preserves the sealed constraint and produces a defensible result, and that the cost is small because training dates are abundant. But this changes a sealed contract, so it is the owner's decision and I will not act on it.

## What is blocked until it is decided
Generating worlds on more dates, which is the longest-lead item and the fix for both the one-date statistics problem and the 180-row corpus. Nothing else stops.

## Standing
No threshold, sign, seed, horizon, price, service guard, acceptance rule or claim condition changes here. No run is authorised. This records a gap and presents options.
