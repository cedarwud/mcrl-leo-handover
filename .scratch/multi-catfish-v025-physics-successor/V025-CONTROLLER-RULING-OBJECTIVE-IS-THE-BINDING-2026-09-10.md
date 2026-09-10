# Ruling — the objective, not the catalogue, is the binding; C3-as-coordination has no necessity here

Date: 2026-09-10 ~23:55Z · Controller
Sources, both learner-free, both with the evaluator rule asserted in code (raising stub, zero
scalar calls) and parity passed:
- `CEILING-CLEAN-AND-LEVERS-2026-09-10.md` (`/home/sat/mcrl-v025-ceiling2-ws`)
- `COORDINATION-VALUE-2026-09-10.md` (`/home/sat/mcrl-v025-coord-ws`)

## Established

| quantity | value | reference / class / estimand / numerator |
|---|---:|---|
| clean coordination ceiling, 1.66 deg | **+0.844250%** | clean first-improvement fixed point / learner-free dev panel / relative pooled-EE ceiling / full-buffer |
| (published, contaminated) | +1.944795% | withdrawn — erratum 19 |
| traversal-order gap | +0.090744% | same; was +0.905261% |
| coordination ceiling, 2.40 deg | +1.463854% | same, diagnostic width, changes the deployed system |
| catalogue coalition support | **saturated at `\|A\| <= 1`, flat through `\|A\| <= 6`** | same |
| smallest EE-improving move from `RSS_MAX` | **k = 1 at 12/12 anchors** (86 / 145 / 368 / 1,129 improving singletons by step) | `RSS_MAX` / learner-free / count / realised pooled EE |
| **best EE improvement that `F` rejects, from `RSS_MAX`** | **+7.852367 Mbit/J** (~18.9% of 41.621560) | `RSS_MAX` / learner-free / absolute pooled-EE change / full-buffer |
| improving moves inside current catalogue support | 1 / 11,847 (0.0084%); multi-user 0 / 5,814 | — |
| acceleration ceiling | +4.143306% this run | **load-dependent — not a stable quantity; not used** |

## Rulings

**1. C3 as "coordination is necessary" is refuted on learner-free grounds at the sealed operating
point.** From both good operating points, single-user moves improve realised EE at every anchor.
This is **not** confounded by the surrogate-label defect or by non-convergence — no learner was
read. It stands.

**Unlike the earlier `k=1` from `BASE` (near-tautological — see `near-tautological-results`),
this one is not:** `RSS_MAX` and the crowded endpoint are *good* points, and the question was
whether a joint move is required to improve *from there*. It is not.

**2. Catalogue widening is closed.** Support saturates at `|A| <= 1`. Adding multi-user rows
buys nothing. The C3 "candidates" binding from `APPROACH` is **not** released by wider support.

**3. The owner's standing concern is confirmed on clean numbers:** the stable coordination
opportunity at the sealed point is **below 1%**, and neither tested lever makes it double-digit.

**4. The largest opportunity on the board is the objective.** `F` rejects an EE improvement worth
**+7.852367 Mbit/J** from `RSS_MAX`, and `BASIN2` showed `F`-driven first-improvement *descends*
from `RSS_MAX` to `31.812902`. **`F` both rejects good moves and accepts bad ones.** Every route
marginal on this project has been measured against `F`.

**Priority order, effective now:**
1. **Objective alignment** — `ETAFIX` (in flight, resumed): does any `eta` make `F` order the arms
   as EE does? If not, the additive-EE closure (`SIBLING-CONCEPT-TRANSFER` #1) is the repair.
2. **C1 gain feature** — Q1 v3 training (in flight). Per-user, and per-user moves are exactly
   what COORDVALUE shows carries the EE.
3. **C2** — `C2TARGET` (in flight, resumed): is a perfect oracle C2 worth anything.
4. **C3** — **no further coordination-mechanism work is dispatched** until the objective is fixed.
   A coordination route measured against a misaligned objective cannot be read either way.

## What this puts to the owner, and I will not decide it

The owner's requirement is **three Catfish each raising EE**. On learner-free evidence, the third
route's defined job — coordination — has no necessity at this operating point and a ceiling below
1%. The honest options, to be decided **after** the objective is fixed and re-measured:

- **redefine C3's job** to something with measured headroom here (not chosen to make the number
  come out — the definition must be justified independently of its effect);
- **change the operating regime** (e.g. beam width) where coordination headroom is larger —
  a physical-system change, disclosed as such;
- **report two routes raising EE and C3 as a negative result**, with this evidence.

These change what the paper claims. They are the owner's call.
