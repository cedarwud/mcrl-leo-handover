# Engineering lane charter (2026-09-07 14:00 UTC)

Adopted from the two fresh-context audits (Claude Opus and codex gpt-6-astra, `.scratch/multi-catfish-v023-controller-handoff-20260907/FRESH-CONTEXT-SLOWNESS-AUDIT-*.md`).

Two lanes:
- **SCIENCE lane** — frozen, one shot, sealed, adjudicated: contracts, declarations, launch manifests, sealed roots,
  scientific tokens. Rules unchanged: no TEST; no tuning of formulas/signs/thresholds/seeds/horizons/lambda/budgets/
  acceptance rules against results; no rerun selected by outcome; sealed artifacts and frozen manifests never rewritten.
- **ENGINEERING lane** — unlimited, unfrozen, read-only against artifacts, running continuously: offline real-artifact
  dry-runs of every consumer chain, static producer↔consumer contract scans, timing rehearsals with `formal:false`,
  per-shard verification as shards complete, pre-declared kill screens' plumbing. Claim ceiling for everything it
  produces: `ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT`. Nothing from this lane is evidence of efficacy or a
  selector for any scientific choice.

Operating rules:
1. No launcher runs before its offline real-artifact dry-run is green (non-fail-fast, every step reported).
2. Every consumer imports producer-owned constants (claim ceilings, schema tokens, layouts, horizons) and carries a
   parity test; the static contract scan runs on every new consumer before review.
3. Rehearsals use the server shadow checkout `/home/sat/mcrl-v023-successor-shadow-20260907` and the real shard set
   `/home/sat/mcrl-v023-real-shards-rehearsal`; they never write into sealed or running roots.
4. Failures in this lane are fixed immediately without adjudication; only the science lane needs rulings.
5. Version control: the recommendation to commit the whole working tree to a branch (content unchanged, no history
   rewrite) and to bind future freezes to commit SHA + tree hash in addition to manifests is pending the owner's word,
   because committing is an action the owner asked to be consulted on.
