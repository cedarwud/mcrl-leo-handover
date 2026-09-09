You are auditing the physics of a LEO satellite handover simulator. Work in this repository (the current directory). Use the interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python` with `PYTHONPATH=src` and `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment; work only on copies inside this workspace.

`DIAGNOSTIC_NOT_CLAIM`. No training run and no policy run is authorised. Do not change any constant, threshold, sign, seed, horizon, price, service guard or acceptance rule in the declared physics; if you evaluate a variant, do it on a clearly separated copy and label it.

# The question

The physics model is the successor labelled `V025-ANGLE-RATE-TPC-TDM-ACM`. Read its implementation under `src/mcrl/physics_v025/` and the coalition/evaluation code that uses it. Establish from the code, not from any summary, how the following chain works:

- how per-user rate targets and the multiplexing rule determine a required spectral efficiency as a function of how many users share a beam;
- how that required spectral efficiency selects a transmission mode from the mode table, and what happens when no eligible mode exists;
- how transmit power is provisioned relative to the selected mode's threshold;
- what fading or quantile factor, if any, is applied between the provisioned signal-to-noise ratio and the one used for decoding;
- what the per-beam power cap does when the required power exceeds it.

Cite `file:line` for every step.

Then answer the central question:

**A beam carrying a single user is reported as delivering no credited bits, while the same beam carrying three users delivers bits. Is that a necessary consequence of the declared physics, or is it an artefact of a specific implementation choice?**

Work out the arithmetic yourself over the sealed constants. In particular, determine which of these is doing the work, and quantify each:

1. the per-beam power cap binding;
2. the required spectral efficiency exceeding the table's maximum;
3. the decoding threshold falling below the table's minimum, i.e. the selection running off the bottom of the ladder;
4. the provisioning rule leaving no margin between the nominal operating point and the threshold;
5. something else you find in the code.

Give counts over a real evaluated panel, not only an argument. If more than one is involved, apportion them.

# Deliverables

**D1.** The causal chain with `file:line` citations and the arithmetic at occupancies 1, 2, 3 and beyond, over the actual sealed constants.

**D2.** A quantified attribution across the candidate causes above, from a real panel of evaluated boundaries. Report how many boundaries produce no transmitted mode, and how many of those would still produce none if each candidate cause were removed one at a time.

**D3.** Your verdict, in one sentence at the very top of the report, on whether "a lightly loaded beam cannot be served" is physics under this model or an artefact of how the model was implemented. If it is an artefact, name the exact line that creates it.

**D4.** If, and only if, you find it is an artefact: state what the minimal, physically defensible alternative provisioning rule would be, and what would happen to the per-beam power cap under it at each occupancy. Do not implement a policy change to the sealed model; describe it and, if cheap, measure it on a copy.

# Honesty requirements

- If the answer is that the effect is genuine physics under this model, say so plainly and early. Do not manufacture a defect.
- If you cannot reach a deliverable in the time available, complete the earlier ones fully and say plainly which you did not reach. Partial and honest beats complete and guessed.
- Distinguish clearly between what you verified by running code, what you derived on paper, and what you inferred.
- Write `LADDER-INDEPENDENT-2026-09-10.md` in the workspace root and print it in full as your final message.
