# START HERE — V0.23 LC-SRS successor-gate review package

Package date: 2026-09-06  
Package status: `REVIEW_INPUT__R6_RAW_GATE_FAILED__FRESH_GATE_REVIEW`  
Audience: two independent GPT-6 Astra Pro/ChatGPT review contexts  
Claim ceiling: development and process evidence only; no efficacy claim

## Purpose

This package asks two fresh, independent reviewers to adjudicate the next
scientifically legitimate step after the one-shot V0.23 LC-SRS learner gate.
The package preserves the frozen method, gate contract, R6 preparation decision,
pre-outcome contingency ladder, fast-screen calculator, Fable C3 audits, and
the current five-arm admission seam. It does not authorize a run and contains
no result artifact that should be treated as a live launch receipt.

The two required prompts are:

1. `CHATGPT-QA-PROMPT.md` — package-grounded scientific-legitimacy,
   integration-readiness, process-flaw, and next-contract adjudication.
2. `CHATGPT-DEEP-RESEARCH-PROMPT.md` — independent primary-literature review
   of imbalance-aware gate metrics, shared-cost/externality credit assignment,
   Shapley/current-slot residuals, and validation design.

Run the prompts in separate fresh contexts. Do not show either response to the
other reviewer before both responses are returned. Neither prompt permits
training, simulation, TEST access, threshold tuning against R6, or file edits.

## Read first

1. `CURRENT-STATUS.md` for the time-bounded status and provenance labels.
2. `CLAIM-CEILING.md` for what a reviewer may and may not conclude.
3. `EVIDENCE-MAP.md` and `SOURCE-PATH-MAP.md` for claim/source navigation.
4. `authority/METHOD-FREEZE.md` and `authority/LC-SRS-GATE-CONTRACT.md` for
   the frozen method and one-shot gate.
5. `authority/R6-RELAUNCH-DECISION.md` for the pre-launch R6 contract.
6. `authority/CONTINGENCY-LADDER.md` for the locked candidate order and
   pre-outcome branch rules.
7. `authority/FABLE-C3-SOURCE-AUDIT.md`,
   `authority/ROOT-FABLE-C3-ADJUDICATION.md`, and
   `authority/FABLE-51-C3-POSTGATE-AUDIT.md` for the C3/Fable boundary.
8. `fast-screen/compute_fit_screen.py` and `five-arm/` for the metric and
   execution-seam details.

## Current headline

The supplied R6 result remains a raw frozen-gate failure: informed sign
accuracy `0.8293051359516616` minus matched-placebo sign accuracy
`0.7915407854984894` is `0.03776435045317217`, below the frozen `0.05` gap.
The informed Spearman value was `0.8367467202782021`; the sign-labelled rows
were `1038` positive and `286` negative (`78.4%` positive). Development-only
balanced accuracies by seed suggest class imbalance but do not rescue R6.
See `CURRENT-STATUS.md` for the exact handoff provenance and separation of
this predicate from the independent composition/runtime defect.

The current process direction supplied with this package is
`CONTINUE_LCSRS_FRESH_GATE`: retain LC-SRS as the candidate, do not
auto-promote CSE or EC, and consider one prospective fresh TRAIN gate with a
pre-registered balanced-sign estimand while still reporting raw accuracy and
retaining physical, composition, and service requirements. A failed fresh
gate receives no second metric revision.

## Stop boundary

After returning one final classification token, the reviewer stops. The
reviewer must not edit this package, launch the simulator, train a learner,
open TEST, promote a candidate from a development-only sign, invent an
unbounded candidate family, or reinterpret an infrastructure defect as
scientific efficacy.
