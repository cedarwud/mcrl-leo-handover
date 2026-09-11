# Declaration — current-design trainings paused pending C1VSGAIN; resume/kill rule fixed now

Date: 2026-09-11 ~01:15Z · Controller · owner instruction: stop anything that no longer serves the need

## Stopped (obsolete)

- **TRIOBJ** — measured the bits/energy/time decomposition that all six cross-model reviews reject
  as post-hoc and contradicting the sealed route definitions.
- **SOLO** — its necessity test against BASE is non-discriminating (RANDOM passes it); the decisive
  contrast is measured more directly by C1VSGAIN.
- **MODQNZ** (earlier) — decisive pair done; z line closed.

## Paused with SIGSTOP (zero CPU, fully reversible)

Every training of the **current design** (labels priced with `eta`, inheriting an objective that cannot
order configurations by EE): SEEDPAR 93-anchor (8 parallel + the sequential PID 3131678),
EXACTTRAIN2 22-anchor (3), Q1V3TRAIN v3 and v3-control (2), and their drivers.

**Why pause rather than run:** a learned head cannot exceed its exact oracle. If exact C1 does not beat
the gain heuristic it mostly selects, no learned C1 will, and these ~14 processes produce nothing
decision-relevant.

## Rule for C1VSGAIN's result — fixed before it exists

Let D1 = `C1_ONLY - RSS_MAX` and D2 = `C1_ONLY - S0_TOP1_UNCONDITIONAL`, pooled over the 93 anchors,
with anchor-cluster bootstrap intervals.

| outcome | action |
|---|---|
| lower bounds of **both** D1 and D2 > 0 | **resume all** (SIGCONT); learned C1 at scale is worth measuring out-of-sample |
| D2 lower bound > 0 but D1 interval includes 0 or is negative | resume **only** the 22-anchor pair (Q1V3 v3 vs v3-control, EXACTTRAIN2 as its baseline); **kill** SEEDPAR 93-anchor |
| D2 interval includes 0 or is negative | **kill all** current-design trainings; no route has demonstrated value beyond an unconditional gain-ranked proposal |

No revision of this rule after C1VSGAIN reports.
