# Catfish state-only gate report — 2026-08-26

## Decision

The requested three-independent-Catfish design cannot be frozen from the
current evidence.

- R1 remains the direct system-EE role.
- R2 has a real exact-stay opportunity signal, but its end-to-end EE effect is
  unidentified until physical handover time/energy costs are modelled.
- Both evaluated independent R3 directions are blocked. The old inactive-beam
  role was not learnable from the frozen focal state; the new
  activation-regularised load-potential (ARLP) role failed its formal
  new-seed gate.

No runtime reward, policy, checkpoint, or training configuration was changed,
and no RL training was launched by these gates.

## Evidence by role

| Role | Verified evidence | Current ruling |
|---|---|---|
| R1 — direct EE | Q1 is the direct EE reference used in every matched counterfactual. | Keep as the direct objective; this is not by itself proof of a new Catfish mechanism. |
| R2 — exact continuity | 758 eligible exact-stay rows; 393 were EE-positive and service-safe (`51.847%`), with positive opportunities in 10/10 seeds. | Provisional only. Immediate local physics does not contain the missing `T_HO/E_HO`, so full handover EE remains unidentified. |
| Old R3 — inactive split | The opportunity label existed in 211/1,000 held-out rows, but the frozen state-only scorer achieved AUROC `0.549769` and AP `0.249874`; accepted DeltaEE had seed-t95 `[-0.154952,+0.212658] Mbit/J`. | Block reward training. State/action identity, not focal state, explained most apparent signal. |
| New R3 — ARLP | Formal v4 result below. | `FAIL_DROP_ARLP_R3_DIRECTION`. Do not train or retune it. |

## Why R3 was redesigned

Opening a previously inactive beam carries a minimum analytic consumed-power
increment of `6.265900454 W` at segment start (`5.927900454 W` PA supply plus
`0.338 W` circuit power). The old R3 split subset empirically added
`6.3101 W` on average and had mean DeltaEE `-0.18695 Mbit/J`. This exposed a
specific defect: generic load spreading ignored a dominant activation cost.

V4 therefore froze

```text
C3 = sum_b U_b^2 / 6 + B_active
r3_ARLP,u = -[(2 U_bu - 1)/6 + I{U_bu = 1}],
```

with the exact served-load accounting identity

```text
-r3_ARLP,u = C3(all) - C3(all except u).
```

The focal proposal used only its live mask, access, previous demand, and
candidate SINR. It was frozen before Q1; a uniform matched-random alternative
was frozen afterward but before any outcome. All three previews used common
random numbers and only Q1 committed.

## Formal v4 result

The Ubuntu-server run used untouched seeds `2026082601`--`2026082610`, 100
users, ten steps, and ten data-blind focal users per step. It produced 1,000
rows, 917 of which were eligible (84--97 in every seed). Forty-five focused
tests passed. The server verifier and a second local verifier both passed, and
the receipt hashes matched.

| Frozen condition | Estimate | Seed evidence | Result |
|---|---:|---:|---:|
| Coverage | `917/1000 = 91.7%` | at least 84 eligible per seed | PASS |
| `C3_reference - C3_ARLP` | `-0.048528` | 4/10 positive; t95 `[-0.101805,+0.009075]` | FAIL |
| `EE_ARLP - EE_Q1` | `-0.190279 Mbit/J` | 0/10 positive; t95 `[-0.276338,-0.104871]` | FAIL |
| `EE_ARLP - EE_random` | `+0.387609 Mbit/J` | 10/10 positive; t95 `[+0.316836,+0.456571]` | PASS |
| ARLP service safety | `1/917 = 0.1091%` unsafe | random `48/917 = 5.2345%` | PASS |

The result is informative rather than null: ARLP is much better and safer
than a random physical alternative. However, it loses to Q1 in every seed and
does not reliably improve even its own realised C3. Under the frozen all-pass
rule, useful structure relative to random is insufficient to justify an
independent R3 Catfish.

## Interpretation and claim ceiling

Verified:

- The v4 implementation and accounting identities replay.
- The candidate fails the preregistered formal gate.
- It may not be retuned or rescued on these seeds.

Supported inference:

- Previous demand is stale relative to simultaneous current actions, so a
  focal-only marginal-cost proposal cannot reliably control realised load or
  activation. The formal result is consistent with this structural
  information problem.

Not proved:

- The experiment does not prove that every conceivable R3 reward is
  impossible.
- It does not test a trained ARLP policy, long-horizon learning, or composition
  of three trained specialists.
- It does not authorise a coordinator, auction, or post-training action gate.

Native Claude Opus Max (`--model opus --effort max`, resolved by the JSON
receipt to `claude-opus-5`) independently judged the gate application sound
and maintained the failure. It also corrected the design implication: R1
already prices realised PA, circuit, baseband, and congestion costs, so C3 or
`B_active` must not be added again. Its proposed R1 EE difference reward is a
new, untested reviewer hypothesis rather than an experimental result.

## Design ruling and next gate

The honest present design is not three complete roles; it is one complete role
plus one provisional role:

1. **R1: direct EE** — retain.
2. **R2: temporal continuity** — retain only as a hypothesis and next identify
   physical `T_HO/E_HO`; then run a frozen matched EE gate.
3. **R3: spatial efficiency** — drop the independent old-split and ARLP lines.
   Do not add their abstract activation penalty to R1, whose physical EE
   denominator already contains the realised activation power.

Therefore the next scientifically justified work is the R2 physical-parameter
gate. A possible R1 EE difference reward is a separate design candidate that
would first need a new specification and untouched seeds; it is not an
approved continuation of v4. This is not another R3 reward-training run. A
future independent R3 would require a materially different observation/credit
contract, a new preregistration, and wholly new seeds; it cannot be called the
current design's third Catfish.

## Primary artifacts

- `SPEC-v4-ARLP-SHADOW.md` — frozen v4 hypothesis and pass rule.
- `run_arlp_shadow_gate.py` — frozen runner,
  SHA-256 `35219a1353c44644d0f1acf7e78f3277497aa447fab7f3be01b3383779e2a82e`.
- `verify_arlp_shadow_receipt.py` — fail-closed receipt verifier.
- `arlp-shadow-confirmation-seeds-10-k10-v4.json` — formal receipt,
  SHA-256 `8efb3068537a10dd8896d07d5410986976b40a6181532ded876648c4474e01a2`.
- `arlp-shadow-confirmation-seeds-10-k10-v4.verify.json` — server verification;
  the same receipt was separately verified locally.
- `CLAUDE-OPUS-MAX-V4-RESULT-RECEIPT.md` — native Claude Opus Max JSON-run
  receipt and claim boundary.
