# Controller finding — positive interaction exists in the corrected engine, expressed as energy efficiency
Recorded 2026-09-09. `DIAGNOSTIC_NOT_CLAIM`. Two independent runs on the corrected engine commit `75c5c78c`, using the sealed stage-4h calibration without recomputing or tuning anything, both report WITNESS FOUND on all four mechanisms.

## The result in energy efficiency
Mechanism 1, decode-threshold cliff via interference, selection view. `EE = B/E`.

| configuration | bits, Gb | energy, J | EE, Mbit/J | vs anchor | served |
|---|---:|---:|---:|---:|---:|
| anchor | 23.568 | 799.044 | 29.496 | — | 4 |
| move A alone | 22.735 | 805.060 | 28.240 | −4.26 % | 4 |
| move B alone | 18.604 | 799.044 | 23.283 | −21.06 % | 3 |
| **both together** | 29.621 | 805.060 | **36.794** | **+24.74 %** | 4 |

Realised view: +22.77 %.

**Each move alone loses energy efficiency. The two together gain about a quarter.** That is super-additivity measured in the primary outcome, not in a proxy.

## Why this one is not bought by dropping users
The served count at the joint move is 4, equal to the anchor. The service guard holds. Credited bits rise because a user that could not decode now decodes, not because a hard user left the roster. Both reports confirm independently that a `NO_MODE` transmission is not counted as served, so the roster cannot be gamed this way.

This distinguishes it from the minimal pilot, where the FULL arm reached the highest pooled efficiency while carrying the lowest availability of any arm.

## What it does and does not establish
It establishes that the corrected physics **can** produce a positive interaction that is visible in energy efficiency with service preserved. It is a constructed synthetic geometry with five users, not the hundred-user evaluation worlds, and it says nothing about how often such coalitions occur, whether a learner can find them, or whether the coordinator can select one inside its decision budget.

The second report notes that its own mechanism-1 variant has positive interaction but a **negative** joint change, so interaction and profit are separate properties and must not be conflated.

## Standing
No threshold, sign, seed, horizon, price, acceptance rule or claim condition changed. No run is authorised. Nothing here may enter the paper or support a claim about C1, C2 or C3.
