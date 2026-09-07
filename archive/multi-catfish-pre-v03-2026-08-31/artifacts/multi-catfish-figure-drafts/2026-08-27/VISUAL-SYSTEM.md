# SMC-ER Visual System

This system keeps all nine drafts recognizably within one paper while allowing the physical scene and algorithm diagrams to use different compositions. Color is always paired with a line style, boundary, shape, or explicit role label.

## Palette

| Token | Hex | Role |
|---|---:|---|
| Paper | `#FBFAF6` | Figure background and manuscript-neutral field. |
| Ink | `#24313A` | Executed physical flow, primary body text, state progression. |
| Main navy | `#17324D` | Main learner, Main replay/update, evaluation/deployment, selected serving link. |
| Main tint | `#E7EEF4` / `#E8EFF5` | Main-owned containers and selected physical regions. |
| Specialist ochre | `#9B5E2E` | Training-only specialist roles and complete executed bundles. |
| Specialist tint | `#F5E9DE` / `#F7E9DD` | Specialist-owned cards and private replay. |
| Physical teal | `#1F7A78` | Physical/end-point relations, eligible destination, empirical supporting routes. |
| Physical tint | `#E3F2F1` | Physical state, service, and supporting-endpoint cards. |
| Conditional rust | `#B44939` | Consumer gates, conditional routes, fail/shadow lineage, removal boundary. |
| Conditional tint | `#F7E7E3` / `#FFF1EE` | Gate, warning, and shadow-only fields. |
| Neutral line | `#AAB3B8` / `#66727B` | Target copies, future/inactive path, annotations, and secondary structure. |

## Typography

- Diagram prose: `Noto Sans`, with Arial/sans-serif fallback.
- Mathematical labels: `FreeSerif`, kept as editable SVG text rather than rasterized formula pictures.
- Figure title: 34–36 SVG units, navy, bold.
- Major card title: 24–31 units, bold.
- Normal figure text: 20–25 units.
- Micro-labels: 16–19 units only where a dense full-width carrier requires them; these are explicitly held for final print-scale proof.
- Every SVG uses a `1600 × 920` viewBox and declares a `160 mm × 92 mm` physical aspect ratio.

## Shape and role semantics

| Visual form | Meaning |
|---|---|
| Double navy rounded container | Main learner or Main-owned boundary. |
| Ochre clipped-corner card | Independent training-only specialist or specialist-owned artifact. |
| Rust diamond | Source-specific conditional gate. It is never a coordinator, decoder, or action selector. |
| Rust dashed rounded card | Gate-fail shadow lineage or current shadow-only status. |
| Teal rounded card | Physical state, physical endpoint, or empirical supporting endpoint. |
| Gray dashed rear copy | Target-network copy or inactive/future route, as labelled locally. |
| Crossed specialist card in Phase III | Specialists removed before evaluation/deployment. |

## Arrow semantics

| Stroke | Meaning |
|---|---|
| Solid dark, medium width | Executed physical/state progression. |
| Solid ochre, wide | Complete executed experience bundle; the bundle remains atomic. |
| Solid navy, wide | Main-owned admission, update, or deployment flow. |
| Rust dashed | Conditional gate pass/fail relation; a nearby label states the outcome. |
| Teal dashed | Empirical or supporting interaction only; it does not assert benefit or causality. |
| Gray dotted/dashed | Parameter synchronization, target copy, or an inactive route that opens only after its named gate passes. |

Arrow width does not encode measured magnitude, effect size, confidence, or success. No arrow denotes voting, auction, reward fusion, action fusion, intent exchange, parameter fusion, coordinator output, or post-training override.

## Stable role treatment

- Main/deployment: navy, double border, explicit `MAIN LEARNER` or `Main only` label.
- Specialists/training: ochre clipped cards, explicit `TRAINING-ONLY` label, `F_j` role, and private replay.
- Conditional status: rust diamond plus dashed routing; F3 additionally carries `CURRENT SHADOW-ONLY`.
- Physical-only figure: teal/navy geometry, with no training-role carrier.
- Baseline-only figure: prose teaching card, with no Chapter 4 learner symbols or specialist semantics.

## Caption and status style

- The in-figure title states the reader task, not a result claim.
- All drafts carry an `EDITABLE DRAFT` badge.
- Unvalidated mechanisms may be labelled `PROPOSED`, `CONDITIONAL`, `TRAINING-ONLY`, or `CURRENT SHADOW-ONLY`; there are no success badges.
- The manuscript captions are frozen in `CAPTIONS.md`. They describe line semantics and claim boundaries without reporting an experiment result.
