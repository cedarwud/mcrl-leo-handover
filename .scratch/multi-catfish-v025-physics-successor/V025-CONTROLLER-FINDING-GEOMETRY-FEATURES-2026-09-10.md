# Controller finding — the learner sees geometry only in compressed form, and one angle has no slot at all
Recorded 2026-09-10, prompted by the owner asking whether off-axis angle is the right quantity to influence power and efficiency, or whether it should be elevation. `DIAGNOSTIC_NOT_CLAIM`. Read from code and from today's row-path audit; nothing run, nothing sealed modified.

**This record corrects an overstatement I made an hour earlier.**

## The two angles are not substitutes
**Off-axis angle** sets the transmit antenna gain toward a user through the pattern law, and it varies strongly **between candidate beams at the same instant** — it is what distinguishes beams on the same satellite.

**Elevation angle** sets slant range, atmospheric path length and the fading statistics; our fading quantile is elevation-binned, at 0.5137 for thirty degrees against 0.42923539 for ten. It varies mainly **between satellites** and is nearly common across beams of one satellite.

So off-axis discriminates beams, elevation discriminates satellites, and a handover decision does both. For our candidate sets — many of which are beams on the same satellite — **off-axis is the more decision-relevant of the two**, because in those comparisons elevation and often occupancy barely move.

## What the per-user feature vector actually contains
Sixteen scalars: nominal margin at the rate target; required power over cap; mode spectral efficiency; background occupancy excluding the focal user; beam and satellite active flags; **off-axis angle in radians**; remaining D2 and visibility time; refresh phase; four previous-association flags and loads; previous beam maximum radiated power over cap; and a missing-incumbent flag.

**There is no elevation feature at all**, and the off-axis slot is filled with a hard-coded zero at both row-building sites — the surrogate path and the exact path alike, so switching paths does not repair it.

## The correction I owe
I told the owner an hour ago that the learner "has never seen off-axis variation". **That is wrong.** The first three features — margin, required power over cap and spectral efficiency — are **downstream of both angles**: they are computed from the antenna gain and the path, and even the surrogate versions are built from a focal nominal-gain ratio, which carries the off-axis dependence.

**The learner is not blind to geometry.** The accurate statement is narrower: it sees geometry only through three conflated scalars, never as separated quantities, and the raw angle slot that the designers provided is constant.

## Why the narrower defect still matters
The pattern is a Bessel-form function of the angle. Recovering it from three derived scalars that also fold in path loss and the current operating point is not obviously possible, and nothing in the feature set lets the head separate **off-axis** from **elevation** from **occupancy**. In exactly the comparisons that matter most — two beams of one satellite — those three scalars differ almost solely because of off-axis, but the head cannot know that is the reason.

## Why this is a different class of repair from the two that failed today
Both first-route repairs I proposed today bought nothing. The admissible power-headroom feature was constant across all thirty anchors. The resource-context coordinates failed for a structural reason: their useful variation is coalition-level while that route's interface is action-local, so only 28 of 163 slots varied at all.

**An angle is action-local.** The off-axis angle of a focal user under a candidate beam, and the elevation of that beam's satellite, are properties of the focal user-action pair. That interface fits them. So this candidate is not in the class that failed.

## Standing
No repair is proposed and none is dispatched. Two of my own have already bought nothing, and the third should be reasoned through rather than tried. This is recorded so the option is on the table with its physics stated, and so that the hard-coded zero is registered as a defect independent of the row-path decision.
