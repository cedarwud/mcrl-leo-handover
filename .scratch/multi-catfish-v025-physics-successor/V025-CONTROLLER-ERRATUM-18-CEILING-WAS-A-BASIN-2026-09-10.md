# Erratum 18 — the "ceiling" I built the whole route argument on is a local basin, and a one-line rule is 3.1x above it

Date: 2026-09-10 ~15:30Z · Controller
Source: `/home/sat/mcrl-v025-rank-ws/STATIC-BASELINE-FAMILY-2026-09-10.md` (both parity gates
reproduce the sealed `PANELCEIL` receipt exactly, 12/12 configuration IDs)

## What I said, repeatedly, for most of a day

> "The panel ceilings are +1.944795% (coordination), +1.045609% (acceleration),
> +0.905261% (traversal order). This route's ceiling is low; even done perfectly it is not
> worth much."

I stated this without condition, and I used it to tell the owner that the whole approach was
capped. In erratum 17's discussion I noted it might be **local**, as an inference. It is now
**measured**.

## What is true

On the same 12 anchors, same full-buffer numerator, same legal set, same provisioning, same
48-boundary endpoint evaluation:

| arm | pooled EE (Mbit/J) | bits | joules | served |
|---|---:|---:|---:|---:|
| `RSS_MAX` — demand-blind greedy on link gain | **41.621560** | 1.6536e12 | 39,730 | **1200/1200** |
| `MYOPIC_GREEDY` | 28.668530 | 1.5276e12 | 53,284 | 1186/1200 |
| `FIRST_IMPROVEMENT_FP` — the certified fixed point | 13.430253 | 1.2559e12 | 93,512 | 1036/1200 |
| `RANDOM` | 11.233999 | 1.2886e12 | 114,706 | 1102/1200 |
| `NEAREST_ELIGIBLE` — geometric BASE | 11.027760 | 1.1213e12 | 101,679 | 960/1200 |
| `ROUND_ROBIN` | 3.441227 | 7.5375e11 | 219,036 | 798/1200 |

**`RSS_MAX` is 3.099x the certified fixed point and 3.774x the geometric base.** It uses
**less** information than the learned selector — no demand, no occupancy, no interference, no
energy, no fading. It is not winning by dropping users: it is the **only** arm at full service,
with **31.7% more bits** and **57.5% less energy** than the fixed point.

**Because it has strictly more bits and strictly less energy, `F(RSS_MAX) > F(FP)` for every
`eta >= 0`.** The certified first-improvement fixed point is not a good point of its own
objective. It is a local optimum of a **single-user move class** in a bad basin.

Every ceiling I quoted was measured over a catalogue constructed from a profile inside that
basin. **A +1.944795% ceiling sits on a point that a one-line rule beats by +209.9%.**

## Second result, on the owner's own test

**`RANDOM` (11.233999) beats the geometric base (11.027760) by +1.87%.** The sub-random check
the owner asked for is failed by the geometric base.

## Third result, and it cuts against the hypothesis that prompted the measurement

The measurement was commissioned partly to test a sibling project's finding that shared-Q +
argmax collapses onto few beams and that spreading users fixes it. On this panel the opposite
holds: **`ROUND_ROBIN`, at 100 active beams — one user per beam, maximally spread — is the
worst arm by a factor of 12.1**, paying 5.5x the energy for less than half the bits.
`RSS_MAX`, the **most concentrated** arm (47.8 beams) with the **lowest** `argmax_distinct`
(5.25), is the best. This is consistent with the recorded physics (per-beam power is a max over
served users; opening a beam pays a near-full PA).

**So the reference frame is broken, but not in the way the hypothesis predicted.** `CROWDCOST`
is running the controlled version of this.

## What this changes

- **No statement of the form "this route's ceiling is X%" stands.** Every one was measured
  inside the basin. They must be recomputed against a reference that is not.
- **The kills taken on magnitude-against-BASE are now measured to have been taken against a
  reference 3.8x below a trivial rule.** `KILLTRIAGE` is enumerating them.
- **The C3 kill is the one most directly implicated.** Escaping a basin where no unilateral
  move helps but a joint move does **is** the interaction route. The oracle-marginals probe
  that found `exact C3 <= 0` in every cell computed those marginals **around BASE**. `BASIN`
  Part 4 recomputes the same quantity around `RSS_MAX`. **This is not a revival** — it tests
  whether the sign depends on the reference profile.
- **`eta_ref` is now a first-order suspect**, not a bookkeeping item. `BASIN` Part 2 checks
  whether `F` ranks the six arms in EE order at all.

## The honest shape of it

I spent the day measuring headroom, ceilings and route contrasts around a profile that a
demand-blind one-liner beats threefold, and reporting those measurements as properties of the
method. The measurements were arithmetically right. **The reference was wrong, and I never
checked it, because no non-learned comparison family had ever been run on this panel.**
The owner asked for one this afternoon.
