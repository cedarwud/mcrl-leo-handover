# Controller erratum 14 — I conflated the source claim with the coordination claim all day
Recorded 2026-09-10 after the owner asked why coordination kept dominating the reporting and whether it was the three components' mechanism. It is not. `DIAGNOSTIC_NOT_CLAIM`.

## The two things I merged
**The catfish mechanism, from the source.** Two agents, not three: a catfish agent and a main agent. The catfish collects rare, high-reward experiences and periodically supplies them to the main agent — the source calls it experience-level knowledge transfer, with a training batch of 70 % main replay and 30 % catfish replay at intervention. Its three strategies are **training-time interventions**: experience stratification, asymmetric discounting, and an adaptive competitive reward. The motivation is stimulating exploration through an introduced competitor. **None of it concerns coordination.**

**Coordination, in our system.** Joint multi-user association changes against one-at-a-time changes. That is a property of the selector's decision structure and has no counterpart in the source.

Our three components are neither. They are prediction heads whose outputs feed a fixed ranking rule. The only thing that maps to the source is the **ablation style**: the contract's intervention is neutral-source substitution of one route's training data, with all heads retained, updated and deployed — which is a training-time intervention in the source's manner.

## The contract already separated them, and I did not
- **§C3** is the learned neutral-source experiment, whose claim wording is that informative source training for a route improved pooled efficiency relative to the specified neutral source training. **This is the owner's requirement.**
- **§C4** is headed *coordination attribution, beyond the source claim*, and requires the full arm to beat both the third component's drop arm and the unilateral-equipped comparator.

The contract itself labels coordination as **beyond** the source claim. I spent the day reporting §C4 as though it were the project's central question.

## Why this matters, in both directions
**It relieves one thing.** A small coordination span does not by itself doom the owner's requirement. Because a drop arm can select *worse* than the fallback when its head is poorly informed, the full-minus-drop gap is **not** bounded by the joint-search span — the owner corrected me on exactly this, and a pilot measured a gap of +15.6 % where the span was under one per cent. The two claims can succeed or fail independently.

**It does not relieve the other.** If the coordination span at the chosen design point is negative — and under corrected provisioning at the width we currently model it is −0.303 % — then the whole learned system is worse than simply running the unilateral search, and no result about the components answers that.

## What changes in how I report
Two terms, never merged again:
- **component efficacy (§C3)** — whether each of the three routes' informative training raises pooled efficiency;
- **coordination span (§C4)** — what joint moves are worth over unilateral moves.

Almost everything measured today is the second. **The first has never been measured at scale**: the only run touching it was a two-seed, one-world, five-anchor engineering pilot in which six of ten decisions fell outside the training support.

## Standing
No sealed value, threshold or claim condition changes. This is a reporting correction, and it is the fourteenth of the day — the first that no external review caught, only the owner.
