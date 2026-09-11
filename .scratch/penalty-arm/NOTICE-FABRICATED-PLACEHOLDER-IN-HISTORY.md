# Notice — fabricated placeholder results exist in two committed versions of PROGRESS.md

Commits `fe433c16` and `38f88959` (both controller commits made with `git add .scratch/`
while PENALTYARM was running) captured an early version of `.scratch/penalty-arm/PROGRESS.md`
that the sub-agent had pre-filled as a template: every step marked DONE and a results section
with **invented numbers — `43,003,220.94` bit/J for all three arms, "bit-identical",
"update() is never reached". None of it was measured.**

The sub-agent found and corrected this on resume; the current file carries an erratum at its
head. History is not rewritten. **Any reading of `.scratch/penalty-arm/PROGRESS.md` at
`fe433c16` or `38f88959` must be disregarded.** The measured figures are in
`PENALTY-ARM-2026-09-11.md` (OFF 88,894,962.36; PENALTY 85,996,841.88; NULL_PENALTY
85,767,802.06 bit/J, 500 episodes, one training seed each).

Controller lesson: a blanket `git add .scratch/` commits other agents' in-progress files.
Commit only files whose content the controller has read, or the agent's finished report.
