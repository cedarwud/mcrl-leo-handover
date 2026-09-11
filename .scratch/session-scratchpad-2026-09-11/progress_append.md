
---

# Addendum 2026-09-11T03:10Z — the declared handover interruption: NOT EXPRESSIBLE, stopped

Appended to the report under `## Under the declared handover interruption`.
Report sha256 is now recomputed (see below); the earlier `efc78880…` is superseded.

## Nothing is running. No detached process of mine remains.

Two background-task notifications reported "failed, exit 255" for shard B and the declared-rule
pass. Those are stale SSH wrapper channels, not the runs: both receipts exist with
`status = COMPLETE` and `scalar_evaluate_calls = 0`, and both were merged. No rerun is needed.

## The question asked

Re-score the same configurations under the declared handover interruption
(0.062 s / 0.142 s, `constants_v025.py:68-69`), with and without, to test whether charging the
physical cost of churn dissolves the 62.502712 -> 17.257910 trade-off.

## The answer: it cannot be scored here, and no number was substituted

**Verified by running code** (`D/verify_treatment.py`, read-only, no physics):

1. The interruption is a **matrix treatment code**, not a free constant:
   `PhysicsSetting.interruption in {"off","on"}` (matrix.py:24,34-35), set by the treatment letter
   (matrix.py:79-90: `"H" -> ("0","0","on","ACM")`, `"SH" -> ("0","f","on","ACM")`), consumed only
   at adapter.py:273 as `interruption_enabled = setting.interruption == "on"`.
   **10 of the 31 declared settings carry `"on"`**: a-rH, a-rSH, a-γH, a-γSH, a′-rH, a′-rSH,
   a′-γH, a′-γSH, bH, bSH. 21 carry `"off"`.
2. The condition selecting 0.062 vs 0.142 is integration.py:78-89: skip `initial_entry`/`reentry`;
   0.062 iff `kind == "same_satellite_beam_change"`; else 0.142. `_interruption_events`
   (probe:743-758) maps `cell_rekey -> same_satellite_beam_change`, so a re-key is Phi-priced 0
   but would open a 0.062 s blackout — inert on this panel (no re-keys).
   Both constants are `VERIFY_SOURCE`; the 3GPP source is not reachable from this host and was
   NOT verified.
3. **Which anchors carry it: none, and the question is mis-shaped.** The treatment is a property
   of the matrix cell, not the anchor. All 12 anchors are the single cell `a-r0`, treatment `"0"`,
   interruption `"off"`. So is BEAMCOUNT, CLEANPATH, CEILING2, COORDVALUE — the whole V0.25
   development record is interruption-off.
4. **The mandated dense path cannot express it, by construction.**
   `batch.evaluate_ar_tdm_catalogue` has **no interruption parameter** (signature verified by
   `inspect.signature`) and never sees an event ledger; the profile hard-wires
   `useful = dict(decoding)` (probe:852); and `StepEvaluator.evaluate_many` takes the dense path
   only when `self.setting.label == "a-r0"` (probe:798), falling through to scalar
   `self.evaluate` (probe:800) for every other label — and every interruption-on label is another
   label. **"Dense batch" and "interruption on" are mutually exclusive in this engine.**
5. `a-rH` IS runnable off the mandated path (`run_setting_for("a-rH")` returns a sealed setting;
   `geometry_for` works on the arrays panel, tapes.py:869-879) — but (i) the mandatory evaluator
   rule replaces scalar `evaluate` with a raising stub, and (ii) the scalar path additionally
   merges `discontinuities_from_event_ledger` (probe:193-213, adapter.py:269-271), so an `a-rH`
   scalar figure would differ from the reported `a-r0` dense figures by **two** changes at once
   and would not be the requested one-factor contrast.

**STOP taken.** No interruption-scored EE reported, no constant substituted, no treatment
approximated, no arm re-scored or re-selected. None of the three pre-declared readings is reached.
Everything previously reported stands unchanged — it is all `a-r0`, interruption off.

## Two things the declared code does fix (verified by reading primary source)

- **The effect would be numerator-only.** Joules accumulate outside the per-user loop
  (integration.py:129) and no blackout term is ever subtracted from them; only `bits` and `useful`
  carry `- removed_bits` / `- removed_time` (integration.py:151-152). Consistent with the
  companion audit's zero-joule handover.
- **Declared window scale** (derived arithmetic on the frozen receipts, `D/blackout_scale.py`;
  NOT a measurement, NOT a bound, and explicitly does not license "the ranking is unchanged"):
  0.062 s and 0.142 s are 0.2061 % and 0.4721 % of the 30.08 s decision interval. Blackout seconds
  over the 36,096 user-seconds of tape: incumbent 0.000 (0.0000 %), budgeted arms 49.6 (0.1374 %),
  base 50.438 (0.1397 %), RSS_MAX 130.838 (0.3625 %), search winner 140.060 (0.3880 %), declared
  rule 141.810 (0.3929 %); widest spread 0.2506 pp. **Unverified assumption**: bits removed equal
  the time fraction only if the rate over the first 0.142 s equals its 30.08 s mean; the rate
  profile over the first subinterval was not inspected.

## What would have to be built (owner decision; neither costed)

- (a) Give `evaluate_ar_tdm_catalogue` a per-user blackout argument, expose a dense `useful_time_s`
  distinct from `decoding_time_s`, and widen the `label != "a-r0"` gate at probe:798. Keeps the
  evaluator rule and all parity targets intact; needs a versioned physics successor.
- (b) Run scalar `a-r0` AND scalar `a-rH` over the same 12 anchors and same 7 configurations and
  report the **within-scalar** difference, which differences the discontinuity mechanism away.
  No engine edit, exact, but needs an explicit exemption from the mandatory evaluator rule and the
  non-batch path is far more expensive. **This is the one I would propose first.**

## New artefacts

- `D/verify_treatment.py` — the enumeration and source-line verification above (read-only).
- `D/blackout_scale.py` — arithmetic on `D/specprofile-merged.json` and
  `D/specprofile-declared-rules-merged.json`; produces no EE.
- `D/interruption_section.md` — the appended report section, verbatim.
