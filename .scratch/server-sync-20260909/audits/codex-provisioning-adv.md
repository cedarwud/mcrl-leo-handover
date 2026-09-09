Workspace: the current directory, `/home/sat/mcrl-v025-selector-ws`. Read-only access to sibling `mcrl-v025-*-ws` workspaces and to `/home/sat/mcrl-v023-codex-audits/parallel-20260909/` is fine. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment, and modify nothing sealed.

`DIAGNOSTIC_NOT_CLAIM`. This is an adjudication, not an experiment. Change no constant, threshold, sign, seed, horizon, price, guard or acceptance rule.

# The decision on the table

A project is about to authorise a versioned change to its declared physics. **Your job is to make the strongest possible case against doing it**, and only then, if you cannot sustain that case, to say so.

Do not confirm. The controller already favours the change and has said so; an agreement obtained after the requester states a position carries little evidential weight. Argue the other side properly, and report every attack you tried, including the ones that failed.

## The alleged defect

Transmit power is solved so that the **nominal** signal-to-noise ratio equals the selected mode's threshold exactly. The transmitted mode is then chosen from that same ratio **after** multiplying it by an elevation-dependent tenth-percentile fading quantile. The de-rating is applied at selection and never compensated at provisioning.

Reported consequences, all on real panels:
- 207,607 of 275,616 transmission instances produce no transmitted mode; all 91,584 single-user instances deliver nothing;
- zero of 2,000 users attain the 50 Mbit/s per-user target on a twenty-anchor panel, in any arm; zero of 12,000 selector-by-user-step results attain it across a five-point beam-width sweep;
- the provisioning rule leaves a measured margin of 9.16e-9 dB at occupancy one;
- removing the per-beam power cap restores none of the occupancy-one failures; removing the de-rating restores 66 %.

## The proposed change

Provision against the threshold divided by the same quantile the selection is later judged at, at two sites and their dense twins. Reported effects: the transmitted mode becomes the target mode; rate-target attainment goes from 0 to 1,364 of 2,000; radiated power rises by 1.107 to 4.830 dB; the cap binds from occupancy ten rather than twelve; the coordination span falls from +6.359 % to about +0.51 %, and at the currently modelled beam width it becomes **−0.303 %**.

Supporting documents you may read: `LADDER-CODEX-2026-09-10.md`, `LADDER-CLAUDE-2026-09-10.md`, `LIT-PHYSICS-2026-09-10.md`, `BEAMWIDTH-MARGIN-2026-09-10.md`, `PER-USER-METRIC-2026-09-10.md`, and the controller records under `.scratch/multi-catfish-v025-physics-successor/` in any sibling workspace.

# Attacks you must at minimum construct and evaluate

**A1. It is not a defect but a declared conservative design.** Both halves are declared. Argue that provisioning to a nominal operating point and then reading the mode at a design percentile is a coherent planning convention, and that the correct reading of the low-occupancy result is a conservative model, not an error. What would have to be true for this to hold, and is it?

**A2. The proposed rule is worse.** Under it every user draws 1 to 5 dB more power and therefore emits that much more interference into the coupled fixed point. Construct the case that the corrected rule degrades the network overall, and check it against the reported per-width service numbers.

**A3. The fix is being chosen for its consequences.** The correction destroys the project's headline result and makes coordination negative at the modelled design point, but it also justifies moving to a wider beam where coordination is positive again. Examine whether the change and the beam-width move together constitute an outcome-selected pair, and what discipline would prevent that reading.

**A4. The evidence is narrower than claimed.** Three sources are said to agree. Two are language models, one commissioned by the controller after the other; the third is a reading of twelve papers chosen by the controller. Attack the independence of that agreement.

**A5. The cost is understated.** Every existing figure must be recomputed. Estimate what is actually invalidated and whether the project can afford it, and whether a narrower remedy — documenting the convention, or reporting both rules side by side without changing the declared physics — achieves the scientific purpose at lower cost.

**A6. Anything else you find.** In particular, look for a reason the reported rate-target attainment of zero could be an instrumentation artefact rather than a physical consequence.

# Output

Write `PROVISIONING-ADVERSARIAL-2026-09-10.md` and print it in full as your final message.

Lead with one line: whether the change should proceed, and if not, the single strongest reason.

For each attack give a verdict of `BLOCKS_THE_CHANGE`, `CONSTRAINS_IT`, or `FAILS`, with specifics. End with the conditions you would attach if the change proceeds — what must be preserved, what must be recomputed, and what must be disclosed — written so that a hostile reviewer reading only that paragraph could not accuse the project of changing its model to suit its results.
