# Ruling — C1VSGAIN returns row 3: kill all current-design trainings

Date: 2026-09-11. Applies `V025-CONTROLLER-DECLARATION-TRAINING-PAUSE-2026-09-11.md`
without revision, as that declaration requires.

## The rule, quoted from the declaration written before the result existed

> Let D1 = `C1_ONLY - RSS_MAX` and D2 = `C1_ONLY - S0_TOP1_UNCONDITIONAL`, pooled over the
> 93 anchors, with anchor-cluster bootstrap intervals.
>
> | outcome | action |
> |---|---|
> | lower bounds of **both** D1 and D2 > 0 | resume all |
> | D2 lower bound > 0 but D1 interval includes 0 or is negative | resume only the 22-anchor pair |
> | **D2 interval includes 0 or is negative** | **kill all current-design trainings** |
>
> No revision of this rule after C1VSGAIN reports.

## The result

93 development anchors, one full-48 realised endpoint, pooled EE (Mbit/J), served and
attainment beside every figure.

| arm | EE | served | attain |
|---|---:|---:|---:|
| BASE | 10.1469 | 0.7992 | 0.1201 |
| **C1_ONLY** | **35.2347** | 0.9858 | 0.2678 |
| C1+Psi (exact C3) | 34.6094 | 0.9966 | 0.2526 |
| `S0_TOP1_UNCONDITIONAL` | 37.5256 | 0.9981 | 0.2766 |
| `RSS_MAX` | 37.6639 | 0.9984 | 0.2761 |
| sealed catalogue ceiling | 39.2898 | 0.9983 | 0.2794 |
| strongest **declared rule** `S2\|A2` | 47.5792 | 0.9981 | 0.2894 |
| `GAIN_IN_SET` (per-anchor b0 pick of three max-gain declared rules) | 50.3435 | 1.0000 | 0.3113 |
| `GAIN_IN_SET_LADDER` (**search winner**, BEAMCOUNT procedure replicated) | 62.5081 | 1.0000 | 0.3271 |

- **D1 = −2.4292 (−6.450%), 95% CI [−11.52%, −1.26%]** — entirely negative. 19 W / 46 L / 28 T.
- **D2 = −2.2909 (−6.105%), 95% CI [−11.24%, −0.86%]** — entirely negative. 5 W / 26 L / 62 T.

**D2's interval is negative. Row 3 applies: kill all.**

Against the strongest declared rule C1 is −25.945% [−36.80%, −11.39%]; against the search
winner −43.632% [−54.32%, −29.20%], winning 6 of 93.

**All three axes move together** — EE, service and attainment all lose. C1 is not trading
EE for service.

## C3's oracle marginal, measured on the same panel

`C1+Psi − C1_ONLY` = **−0.6253 Mbit/J, −1.775%, CI [−8.99%, +4.00%] covering zero.**
It changes 46 of 93 decisions, 28 of them for the worse. `Psi` uses the sealed
`set_score_decomposition` identity, residual <= 7.89e-14 on single-user configurations —
which also proves this harness recomputes the sealed C1 labels from physics.

## Why C1 loses, from the report

- **83 of 93 C1 choices are simply one of the two `s0` network-wide proposals.** Using a
  perfect C1 to choose between those two is worth **−0.37 Mbit/J** relative to not
  choosing.
- **C1's own non-`s0` picks are where it bleeds**: 10 of 93 anchors, pooled 11.8597 at
  86.8% service, against 18.0821 at 100% for the unconditional `s0` proposal — −34.4% EE
  and −13.2 pp service, winning 1 anchor.
- **The real ceiling is the sealed catalogue**: its best member (39.2898) is below every
  in-set gain rule, and the search winner exceeds that ceiling at 79 of 93 anchors while
  lighting on average 26.55 beams against `RSS_MAX`'s 47.58 and BASE's 56.05.

## Integrity notes carried from the report

- **Parity**: BASE 10.146875431594404 and C1_ONLY 35.23470844487427 are **bit-identical**
  to C2TARGET; 91,547 catalogue members identical; 4 shared anchors match BEAMCOUNT exactly.
- **Disclosed parity shortfall**: the cap ladder was truncated to {8,20,30,50} on budget,
  missing 9/10/15 inheritance at world1/step1, giving 61.7024 against their 64.9012. **So
  LADDER is a lower bound on the search winner and C1's shortfall is understated.**
- **The two reference classes were never pooled.** BEAMCOUNT's 52.042303 / 62.502712 are a
  12-anchor panel and are **not** parity targets for these 93-anchor figures; the
  closeness of 62.5081 to 62.502712 is coincidence and is labelled as such.
- **Erratum 23 moved none of its conclusions** — the correction arrived before any
  conclusion was drawn, and the harness separated the classes from the start. All EE is
  scored at full 48; only within-rule selection uses b0, and the cap-50 winner's b0 EE
  exceeds its own full-48 at 93 of 93 anchors (83.807 vs 64.129 mean).
- **Compliance**: scalar `evaluate` replaced with a raising counting stub in all three
  evaluators, **zero calls across four passes**; BASE always inside the first
  `evaluate_many` batch. Two disclosures: the endpoint evaluator is one fresh instance per
  anchor but batched; the sealed catalogue builder uses scalar evaluate internally
  (unmodified sealed code). A win-counting defect in `combine.py` (1e-16 noise breaking
  ties) was found and every win/loss figure recomputed directly.

## Action

**Kill all current-design trainings** — the 44 SIGSTOPped processes whose working
directory is `/home/sat/mcrl-v025-seedpar-ws`, `/home/sat/mcrl-v025-exacttrain-ws`, or
`/home/sat/mcrl-v025-q1v3-ws` (8 + 3 + 2 python workers plus their drivers, sleepers and
codex sandboxes).

**Blocked**: the kill command was refused by the permission classifier
(`Interfere With Workloads`). The action is declared and owner-approved in advance by the
declaration above, but requires the owner to run or approve it. Command:

```
ssh sat 'ME=$$; T=""; for p in $(ps -eo pid,stat --no-headers | awk "\$2 ~ /^T/ {print \$1}"); do
  [ "$p" = "$ME" ] && continue; c=$(readlink /proc/$p/cwd 2>/dev/null)
  case "$c" in /home/sat/mcrl-v025-seedpar-ws|/home/sat/mcrl-v025-exacttrain-ws|/home/sat/mcrl-v025-q1v3-ws) T="$T $p";; esac
done; echo "killing:$T"; kill -9 $T; sleep 2; ps -eo pid,stat --no-headers | awk "\$2 ~ /^T/" | wc -l; uptime'
```

**Not covered by this ruling**: one SIGSTOPped python in
`/home/sat/mcrl-v025-exact93-ws`. EXACT93 is recorded complete; this is a leftover, it is
consuming zero CPU, and the declaration does not name it. **Left alone** rather than
killed, because exceeding a declared rule in the direction it happens to point is the
same failure as revising it.

## What this closes

The current three-route design has **no demonstrated value at the oracle layer**. A
learned head cannot exceed its exact oracle, so no learned C1, C2 or C3 built on these
labels can beat an unconditional gain-ranked proposal. **This is independent of the
demonstration-RL closure and of the objective question** — those concern the MODQN
physics; this concerns the V0.25 stage-C route design.
