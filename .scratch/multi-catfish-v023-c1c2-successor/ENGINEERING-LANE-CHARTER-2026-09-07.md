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

## Addendum 14:50 UTC — defaults adopted unprompted (owner's feedback: propose methods, do not wait to be asked)
6. **N=1 full-chain gate on every change:** `offline_realartifact_dryrun.py` with the stage-A chain spec (and later a stage-C spec) runs after any edit to a successor package, against the newest real artifact available; a launcher may not run while that gate is red.
7. **Budget ladder on one code path:** rehearsals run 1 → 10 → 100 epochs (and 1 → 10 → 100 episodes) through the same modules as the formal run; the formal run changes only the budget, the root and the authority.
8. **Design-document stop rule:** no new version family or contract until the current one has produced at least one development curve (or a valid STOP token). Method notes go into the existing package README, not a new `docs/` family.
9. **Latency ledger:** every defect found today onward is logged in `LATENCY-LEDGER-2026-09-07.md` with the layer it lived in, how it was found, and the minutes it cost; the ledger is reviewed at each hand-back.
10. **Shared typed schema module (next structural step, after the current blocker fixes land):** one module both producer and consumer import for receipt keys, array names/dtypes/layouts and token literals, so the static scanner becomes a backstop rather than the first line of defence.
11. **No silent fallbacks in sync/closure logic (18:10 UTC):** a manifest or sync-list builder must fail closed when the closure list is absent; a fallback that narrows coverage is forbidden (it produced 189/246 missing paths in the stage-C bundle and cost three launches earlier today).
12. **One writer per path at a time (16:35 UTC):** never give two agents write access to the same directory concurrently; a server codex workspace is pulled back exactly once, after which the local repo is the only source of truth and the sync direction is local → shadow only.
