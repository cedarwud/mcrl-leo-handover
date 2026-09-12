# Stop gate between the `T_DELTA` S diagnostic and everything downstream

Date 2026-09-12. **Owner correction to Amendment 14 execution.** It opens no branch and changes no scientific
threshold. Sent to `CF2S-PHASE-B0` before its shards finished.

## 1. Accepted state

`T_H` **CLOSED** — do not reopen. Phase A **finished**. `S1-PREP` **PARKED**. `T_DELTA`'s exact-path parity
**PASSED** — no further parity work. The four-shard shared-state **S diagnostic is now the only scientific critical
path in the project.**

## 2. The gate

The B0 brief implicitly allowed `S → J/C generation → R_repr clone` without returning to the controller. It no longer
does. On completion of the four S shards: aggregate S, write the exact measurements, **STOP**, return S to the
controller. **No process may be launched after S** — no J, no C, no clone fit, no further expensive diagnostic — until
S is adjudicated.

## 3. S is adjudicated on inherited gates only

No threshold may be invented or tuned from the S result. The existing Catfish-2 conventions apply where they
structurally do:

- **behavioural distinctness**: action disagreement ≥ **25 %**;
- **positive-value support**: candidate-better fraction ≥ **0.30** *and* **`CR ≥ 0.5`**, with **Σ positive and Σ
  negative reported explicitly** rather than folded into the ratio;
- the pre-declared **QoS-invalid fraction**, definition unchanged.

**If S fails distinctness, or either positive-value condition, `T_DELTA` closes immediately** — no J/C, no `R_repr`
fit, no RL learner — and the bounded Catfish-2 search returns to the owner as **exhausted**. If S passes, the
controller may then authorise the already-declared J/C + frozen `R_repr` stage. Nothing is authorised in advance.

## 4. Progress logs are not results

The live shard logs reportedly show large action disagreement. They are incomplete and contain no `CR` or
candidate-better adjudication. **Large disagreement alone is not a pass**, and Stage 0 is the proof: every arm there
with disagreement ≥ 25 % had `CR ≤ 0.485`, and the only arm reaching `CR ≥ 0.5` differed from T0 on 0.24 % of
decisions. Only the completed aggregate counts.

## 5. Scope

The +20.27 % decomposition finding is useful paper framing and is already recorded (`6efeba0f`). It **opens no
experiment and does not alter the Catfish-2 search.** No further registry, framing, baseline-decomposition, reviewer
or old-lane cleanup work may consume the critical path.

**Priority is exactly: finish S → adjudicate S → either close immediately or authorise J/C + `R_repr`.** That is the
fast-fail boundary.
