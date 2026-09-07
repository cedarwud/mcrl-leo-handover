Act as a skeptical senior reviewer of a multi-objective reinforcement-learning
mechanism for LEO handover. Read these local files completely:

1. `.scratch/catfish-oracle-gate/V2-RESULT-BRIEF-FOR-OPUS.md`
2. `.scratch/catfish-oracle-gate/SPEC-v2-STATE-ONLY.md`
3. `.scratch/catfish-oracle-gate/state-only-confirmation-derived-v2.json`
4. `src/mcrl/env/service.py`, especially `r3_counting`
5. `src/mcrl/env/step_types.py`, especially `RewardComponents`

Answer every review question in the brief. Try to falsify the proposed R2/R3
roles. Give one primary recommendation, not a menu, and a concrete frozen
learnability gate with numerical pass/fail thresholds. Flag leakage, reward
duplication, hidden coordination, causal gaps, or insufficient observability.
Do not edit files, run training, browse, or infer results not in the receipts.
Keep opportunity, supervised separability, RL learnability, joint composition,
and long-horizon evidence explicitly separate.
