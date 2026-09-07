# SMC-ER Figure QA Report

QA date: 2026-08-27  
Scope: nine editable non-results figure drafts only. Chapter 5, result figures, and experiment numbers were not modified.

## Outcome

All nine SVG sources pass structural validation and all nine produced distinct `1600 × 920` Chromium screenshots. The nine-up browser gallery also rendered as one full-page contact sheet. At this stage the package is suitable for human structural/scientific review, not camera-ready insertion.

The render and validator results are engineering evidence. They do not show that SMC-ER is effective, that any consumer gate has passed, that C1/C2/C3 improves EE, or that the C3 fork is valid outside its declared assumptions.

## Authority refresh check

The live paper algorithm and concept-freeze documents were revised in place to their R3 content during figure production. The controller detected the digest drift, stopped promotion, reread both live files completely, and rechecked the nine figures against the refreshed role, routing, C2 option, and C3 certificate constraints. The R3 concept explicitly keeps the three-interval option horizon out of the Chapter 4 theory figures, so no pilot value was frozen into these drawings.

Current live hashes after that refresh are:

- Paper algorithm v0.4-R3: `0e67e6aa570158dd1433afe98d4992ed278db1cb5d586f6aff6680e0c7696d2e`
- Concept/algorithm freeze v0.1-R3: `00add9617a2955ca770b25a67168d01736ebb5b6a149a94593d638b1c04953dd`
- Non-results authoring contract: `6a5dc7e4305f36d90a057293e5059e7d7e5c60130811f47de3f26d56e5ff73e8`

The current handoff hash is `57e12fddc3aa913273eb5b62b438df48762c279f07aa69d8e744b23a0aec6293`; the current production prompt hash is `479c9b3094cea07067ebbfa1d200f12cd09d7d9d04b86e07f92f554d0333e2e5`. Those two digests did not drift. The handoff opens all nine structural rows but does not open camera-ready promotion.

## Structural and mechanical checks

- SVG validator: PASS for all nine sources; see `receipts/svg-validation.txt`.
- Unique IDs and local references: PASS for all nine sources.
- Forbidden implementation identifiers: no matches for `local_snr_greedy`, `masked_uniform`, `source_policy_version`, `Q1_C1`, `Q2_C2`, `Q3_C3`, `D_CF`, arm IDs, coordinator, decoder, or intent exchange.
- Figure 2-1 Chapter-4 leakage: no visible `Q_j`, `Q_j^M`, `D_M`, `F_j`, Catfish, SMC-ER, ACRM, EXP, or consumer-gate label. Its accessible description also avoids the acronym.
- C3 bindings: the source/destination load convention, `+2` condition, exact R3 identity, separate system-power safeguard, non-reward statement, lagged-versus-current alias check, and current shadow-only state are all present in Fig. 4-5.
- Deployment boundary: no specialist-to-deployment arrow. Fig. 4-1 and Fig. 4-7 show Main-only evaluation/deployment; Fig. 4-7 explicitly removes all three specialists.
- Routing boundary: Fig. 4-1, Fig. 4-2, Fig. 4-6, and Fig. 4-7 use separate `F_1`, `F_2`, and `F_3` gate carriers. No shared all-stream gate is drawn.

## Per-figure review

| Figure | Scientific content | Symbols | Arrow semantics | C3 gate / shadow | Main-only deployment | Small-size readability | Clipping / overlap / overflow | Render evidence |
|---|---|---|---|---|---|---|---|---|
| Fig. 2-1 | PASS against the source-bound baseline card: feasible mask, three objective networks, weighted scalarization/exploration, environment, complete transition, replay, three TD lanes. | PASS; intentionally prose-only before Chapter 4. | PASS; state/action flow, transition return, TD samples, and target synchronization are visually distinct. | N/A. | N/A; no specialist exists. | REVIEW: major labels read at 160 mm; final PDF proof still required. | PASS at 1600×920; no visible clipping or collision. | `png/fig2-1-main-modqn-baseline.png` |
| Fig. 3-1 | PASS: satellites, users, occupied and empty beams, selected/candidate links, same/cross-satellite handover, off-axis geometry, and physical chain. | PASS against the active symbol table; no learner notation. | PASS; solid selected link, dashed candidate, handover arcs, and physical chain are differentiated by line and label. | N/A. | N/A; no learner exists. | REVIEW: geometry and labels read at full-width render; manuscript compositor proof remains. | PASS at 1600×920; no visible clipping or collision. | `png/fig3-1-physical-leo-system.png` |
| Fig. 4-1 | PASS: three training-only specialists, complete bundles, independent consumer gates, conditional/shadow outcomes, Main-only deployment. | PASS for `F_j`, `Q_j^F`, `Q_j^M`, bundle and replay roles. | PASS; wide ochre bundles, rust conditional gates, and navy deployment are separately encoded. | PASS; F3 is labelled current shadow-only and its pass path is conditioned on alias check. | PASS; only trained Main crosses the deployment divider. | REVIEW: gate micro-labels are the limiting text. | PASS at 1600×920 after C3-card and route-label correction. | `png/fig4-1-method-overview.png` |
| Fig. 4-2 | PASS: four logical learners, six online Q functions, independent replay and target copies, whole-Main bundle consequence. | PASS; each specialist owns exactly one `Q_j^F` and `D_j^F`; Main owns three heads. | PASS; each specialist bundle reaches its own gate, while gate-pass routes target Main replay rather than the same-number head. | PASS; F3 potential route is inactive and current shadow-only is explicit. | N/A in this topology carrier; no deployment endpoint is drawn. | REVIEW: readable full-width; final equation-font substitution may improve consistency. | PASS at 1600×920; long-wait browser render eliminated the earlier image-load race. | `png/fig4-2-learner-topology.png` |
| Fig. 4-3 | PASS: named/neutral source control, Source Gate A, EE strata, immutable C1-only prefill, online C1 execution, private ACRM, later full bundle, consumer gate. | PASS; no engineering source identifiers appear. | PASS; prefill enters only `D_1^F`; only the later executed joint bundle reaches the Main-consumer gate. | N/A. | PASS locally: Main is the only evaluation/deployment learner shown. | REVIEW: mechanism-factor microcopy is smallest and may need enlargement. | PASS at 1600×920 after title, gate-body, and bundle-label correction. | `png/fig4-3-c1-energy-frontier.png` |
| Fig. 4-4 | PASS: trigger, physical-ID binding, hold, continue, early terminate, release, direct unchanged canonical R2, empirical EE interaction. | PASS; candidate-table index is explicitly excluded from physical-ID binding. | PASS; executed progression is solid, early termination is rust dashed, EE interaction is teal dashed. | N/A. | N/A in this specialist mechanism carrier. | REVIEW: early-terminate body is acceptable full-width; final print proof remains. | PASS at 1600×920 after termination-card wrap and release-route correction. | `png/fig4-4-c2-temporal-continuity.png` |
| Fig. 4-5 | PASS against the binding correction: source includes focal user, destination excludes it, destination is already active, exact identity and strict `+2` condition are separate, safeguards remain separate from R3. | PASS; `U_{s,v}`, `U_{s,v'}`, `n_{s,v}`, `r_3`, and system `ΔP^N` roles are not fused. | PASS; direct R3 endpoint is solid, power/EE supporting endpoint is dashed, and Main route is conditional. | PASS; observational-alias consumer gate is explicit; gate fail/current state routes to `CURRENT SHADOW-ONLY`; possible `D_M` route opens only after pass. | N/A in this specialist mechanism carrier. | REVIEW: formula and bundle microcopy require final compositor proof. | PASS at 1600×920 after formula baseline and gate/shadow spacing correction. | `png/fig4-5-c3-spatial-load-power.png` |
| Fig. 4-6 | PASS: atomic joint bundle, all rows, full `U×3` reward matrix, retain adverse outcomes, per-source gates, fixed quotas, total bundle weight one, all three Main updates. | PASS; private shaping, option state, and `ΔP^N` diagnostic stay outside Main reward. | PASS; Main origin is directly admitted, F1/F2 pass/fail are conditional, and F3 route is inactive until pass. | PASS; F3 is visibly current shadow-only. | N/A in this routing carrier; Main is the only consumer learner. | REVIEW: full-width placement is required; column-width use is not approved. | PASS at 1600×920 after quota-heading and shadow-label correction. | `png/fig4-6-atomic-experience-routing.png` |
| Fig. 4-7 | PASS: Phase I C1-only prefill, Phase II independent collection/update/gating/Main update, Phase III specialist removal and Main-only action. | PASS; no engineering identifiers or retired topology symbols. | PASS; the Phase-I no-route card blocks prefill from Main; Phase-II gate outcomes are conditional; Phase-III flow is Main-only. | PASS; Phase-II F3 route ends at current shadow-only. | PASS; all specialists are crossed out and only Main reaches masked-greedy deployment. | REVIEW: Phase-II outcome micro-labels assume full-width placement. | PASS at 1600×920 after source-gate spacing, no-route card, and footer correction. | `png/fig4-7-training-deployment-flow.png` |

## Browser and pixel evidence

- Each figure PNG is an actual Chromium screenshot of its editable SVG through `source/render-wrapper.html`, with a fixed `1600 × 920` viewport and a 1.5 s load wait on the final dense carriers.
- Every final figure PNG reports `1600 × 920`, 8-bit RGB, non-interlaced.
- The browser gallery is `gallery/index.html`.
- The full-page comparison screenshot is `gallery/contact-sheet.png` (`1800 × 1661`).
- Browser renderability and screenshot dimensions do not substitute for Microsoft PowerPoint, PDF compositor, desktop font, or human print-scale acceptance.

## Open human gates

1. Scientific-author confirmation of the C3 identity and declared reference-fork assumptions.
2. Human review of arrow meaning across Fig. 4-1, Fig. 4-2, Fig. 4-6, and Fig. 4-7.
3. Final manuscript-size PDF proof, especially the 16–19-unit micro-labels in dense figures.
4. Desktop font and compositor review before any camera-ready promotion.
5. Final-figure handoff and manuscript insertion authorization.
