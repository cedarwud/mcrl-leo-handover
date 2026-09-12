# Controller takeover — MC2 genuine Multi-Catfish round (2026-09-12, new controller session 1f482c61)

## 1. Live state, verified before any action (≈ 04:29 UTC)

- Main repo `/home/u24/papers/mcrl-leo-handover`, branch `wip/multi-catfish-v023-20260907`, HEAD read from git =
  `98bf37c832d38a93b42d47fc17b5acfecdf8b58e` (= the handoff check value). 112 pre-existing status lines (modified
  `.scratch/dev-training/E1-LAUNCH…`, `PROGRESS.md`, deleted `dr*-prompts/`, `gpt*`, untracked `.scratch/ee-ceiling/`,
  `external-package/`, …) — **not touched, not reset, not included in any commit of this round.**
- Lane M `/home/u24/papers/mcrl-leo-handover-cf2s-multi`, branch `catfish2/multid3-20260912`, HEAD =
  `6136c5149c49875b985955456cce468702821018`, clean; k8 learner code `f129e34057f7533ee1aca763503732356ebbef9d` present.
- `sat`: anchored `/proc/*/exe` scan → **zero python processes**; load 0.00; 91 GB RAM; 20 cores. Local: no mcrl learner
  (only unrelated tooling). The old controller transcript `f508c755…` was last written 04:16 UTC; a `claude --resume`
  process (PID 675557) sits idle in this repo's cwd and is left alone.
- DEV seed use on `sat` (every `status.json` under the dev / cf2s / catfish2 / cf3 workspaces): DEV index k = 0…8 only;
  k = 9 unused; formal `9_111_000+i / 9_112_000+i` untouched; no S1 root.

## 2. Corrections to the 2026-09-12 handoff narrative (owner ruling; no new experiment needed)

1. E1 ep 300: `D3-T0` is **72/72** paired DEVVAL episodes positive (3 seeds × 24); the other 72/72 belongs to `D2-T0`.
   They must not be summed into "144/144" for `D3-T0`.
2. k = 8: the 24 evaluation episodes come from **one training seed**; they are not 24 independent training replicates.
3. "FULL worse than both singletons" is a **measurement**. "The stronger teacher was diluted" is a plausible but
   **not causally isolated** explanation; the 60.726 % two-member rate does not prove it.
4. Beating a random null does not show that every harness is bug-free.
5. The old +20.27 % / +9.92 % comparisons against the frozen 9000-episode MODQN have comparability limits and may not
   enter the formal abstract. The design that separates backbone and Catfish effects stays; formal numbers come from
   same-protocol comparisons.
6. k = 9 is the DEV index left over from the old authorisation, not "the only usable random seed".

## 3. This round

Owner ruling 2026-09-12: genuine Multi-Catfish (≥ 2 specialists with real roles, independently removable, measurable
contribution); single T0 kept as the strong baseline; Amendment 15 / k8 failure and closures stay; T_H / T_DELTA /
T_TAIL / T_B-T_E not reopened; integration redesign authorised in a new version / worktree / manifest / DEV runs.

- Worktree `/home/u24/papers/mcrl-leo-handover-mc2`, branch `mc2/judge-override-20260912`, base `6136c514`.
- Contract: `…-mc2/.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md` (r0; co-sign by lane B).
- Seeds: selection k = 10, 11 (ep 100); confirmation k = 12, 13, 14 (ep 300); reserve 15–17; k = 9 unused;
  new DEV-NULL base `9_243_000`.
- Owners: A engineering/training, B method/independent readout, C paper deltas, D deck/figures (see registry block).
