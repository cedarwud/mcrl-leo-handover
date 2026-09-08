## VERIFIED

Read-only local inspection only; no network, SSH, simulator, or edits. All preflight-listed code hashes match; the field-root digest recomputes correctly. No tape file exists in the F1 implementation directory.

Below, **R** means [run_v023_c3_contingency_f1.py](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py).

- **Units:** R:1175–1177 preserves the normalized float32 Q1+Q2 sum; R:1237–1244 supplies raw-bit D/F targets; R:675 adds them directly. The [model configuration:12](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json:12) fixes κ = 10097071012.757404 for Q1/Q2 and identifies Q3’s normalized output at line 43.
- **Oracle precedent:** V009 adds `q3_values` (runner:968–969), whose producer divides by κ in [ee_axis_pnfe.py:253](/home/u24/papers/mcrl-leo-handover/src/mcrl/runtime/ee_axis_pnfe.py:253). V011 likewise produces `z3/kappa` (`ee_axis_joint_c3.py:262`). V013/V015 add normalized zero-marginal surfaces (`ee_axis_zero_marginal_c3.py:630`; respective runners:653–655 and 569–571). Most explicitly, the [V022 contract:104](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v022-c3-coalition-residual/COALITION-RESIDUAL-MECHANICS-PROBE-CONTRACT-2026-09-05.md:104) requires `masked_argmax(Q1+Q2+z3/kappa)`; `ee_axis_coalition_residual_c3.py:433` implements the conversion.
- **Field:** R:67/1196 binds the R7 component and fresh F1 world. This matches [R7 source adapter:113](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py:113). The separate development-evaluation contract uses the V020 component at line 31.

## INFERRED

The [ladder:73–80](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md:73) leaves composition implicit. Existing conventions make **Q1+Q2+z/κ** its plainest faithful interpretation.

Dividing raw bits by the already-frozen system κ is a **unit conversion**, allowed under this reading. It preserves the coefficient-one composition; raw addition effectively weights the physical correction by κ relative to the heads. The prohibition addresses discretionary target reweighting, not conversion into the heads’ established unit. Candidate-only `argmax(z)` lacks comparable support. Raw addition need not equal it exactly, particularly at ties.

Given the stipulated absence of outcomes, neither interpretation is evidence of outcome tuning. Raw addition is nevertheless dimensionally wrong; pre-outcome timing does not validate it. Comparing both after opening the tape and choosing the preferred result would be tuning.

The ladder does not uniquely mandate a namespace. Keeping the already-bound R7 component is the most faithful continuity choice. A common component introduces no arm-specific random-field mismatch, although changing it changes the realization and potentially the winner. Shared randomness does not guarantee an unchanged ranking or establish efficacy.

## RULING

**Use fixed `z/κ`; keep `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1`.** Record the clarification and reseal affected bindings before tape generation.

Other implementation findings:

- **Correct:** R:482/984–994 measures realized served-user fraction, pooled over both steps; EE is summed interval bits divided by summed joules. R:1013–1014 implements the inclusive service margin and strict EE inequality. With 200 opportunities, one lost served-user-step exceeds 0.001.
- **Correct:** R:895–901 verifies masked selections; R:1057–1060 requires at least one changed legal action across either step. R:1033–1036 gives D priority. R:1274 advances the shared BASE trajectory, appropriate for this tape screen.
- **Integrity defect:** R:1012–1016 can return `integrity=False`, but R:1029–1036 ignores bundle integrity unless separately supplied. An isolated in-memory probe returned `F1_SURVIVES_F` for invalid D/passing F, and `FAST_SCREEN_NO_SUPPORT` for both nonfinite. Exceptions correctly produce `INVALID_RUN` at R:1321–1333; false integrity must also propagate globally.
- **Validation gap:** R:902 validates deployment profiles individually without matching their user count and interval to BASE; R:882 also omits enforcing 100 users.
- **Conditional execution defect:** R:619/673 rejects empty-mask users, although [action_contract.py:580](/home/u24/papers/mcrl-leo-handover/src/mcrl/env/action_contract.py:580) permits their NOOP. If encountered, this is an execution failure, not candidate failure.

ASTRA_F1_COMPOSITION=Z_OVER_KAPPA ASTRA_F1_FIELD=KEEP_R7_COMPONENT