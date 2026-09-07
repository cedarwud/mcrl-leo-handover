# GPT-6 Astra Pro/ChatGPT Deep Research adjudication prompt

## Goal

Act as an independent research scientist in reinforcement learning,
multi-agent credit assignment, wireless/satellite resource allocation, and
experimental design. Use the attached V0.23 review package as project input
and conduct a primary-literature-only review of whether one fresh prospective
TRAIN gate is legitimate after the R6 raw sign-gap failure, and whether the
project should retain LC-SRS or promote a CSE/EC contingency. Return one
evidence-grounded decision, not an execution plan.

Run this lane in a fresh context. Do not read, request, or rely on the answer
from `CHATGPT-QA-PROMPT.md`; the two adjudications must remain independent.

## Project input and non-negotiable boundary

Read `START-HERE.md`, `CURRENT-STATUS.md`, `CLAIM-CEILING.md`,
`EVIDENCE-MAP.md`, and `SOURCE-PATH-MAP.md` before searching. Treat project
facts as supplied evidence with their labels, not as literature. The current
R6 handoff reports informed Spearman `0.8367467202782021`, informed raw sign
accuracy `0.8293051359516616`, matched-placebo raw sign accuracy
`0.7915407854984894`, and a frozen raw gap
`0.03776435045317217 < 0.05`; the sign-labelled rows are `1038` positive and
`286` negative (`78.4%` positive). Development-only balanced accuracies by
fixed seed are informed `[0.6076, 0.7227, 0.7047]` and placebo
`[0.5584, 0.5970, 0.5807]`. The raw R6 predicate is therefore failed; the
balanced values do not rescue it.

Also treat as project inputs: R6 had a separate composition replay-digest/
runtime defect; the first C1/C2 target-generation attempt failed before
physics at the wrong `_network_snapshot` module level and has a tested
correction/relaunch in progress; the current five-arm runner is an injected-
callback admission/receipt skeleton rather than a complete physical path; and
a fresh Astra Ultra read-only direction was `CONTINUE_LCSRS_FRESH_GATE` with
no automatic CSE/EC promotion, one possible prospective fresh TRAIN gate with
raw plus balanced-sign reporting, and no second metric revision if it fails.

The frozen method uses a two-user current-slot four-profile LC-SRS teacher and
deployment `Q1 + Q2 + Q3` under one native mask and one argmax. There is no
coordinator, auction, joint decoder, iterative repair, fallback, or TEST.
The Fable CSE “joint exact” claim is specifically under scrutiny: a
within-configuration identity such as `sum_u share_u(x) = P^N(x)` may not imply
exactness when shares are evaluated on different unilateral branches. Do not
promote CSE or EC from plausibility alone.

No project action is authorized. Do not run or propose commands that train,
simulate, launch a rollout, open TEST, mutate the repository, or tune R6
thresholds/formulas/seeds/horizons/scales after outcomes. Do not invent an
unbounded candidate family. A source or paper may support a principle; it
cannot alter the frozen project authority without a new pre-outcome contract.

## Primary-literature requirements

Use only original, primary sources for substantive claims: original journal or
conference papers, original technical reports, official standards, or
first-party method papers. Surveys, textbooks, blog posts, search-result
snippets, and tertiary summaries may orient the search but may not support a
conclusion. For every major claim, record title, authors, venue/publisher,
year, DOI or stable publisher URL, the exact scope of the result, and any
important limitation. Prefer sources that are accessible and independently
checkable. Do not use a source merely because its title resembles a project
term.

Search and reconcile these four required lanes:

### 1. Imbalance-aware surrogate and gate metrics

Research primary work on balanced accuracy, macro-averaged sensitivity/
specificity, class-weighted or cost-sensitive classification, prevalence shift,
calibration, ROC/PR interpretation, and clustered or hierarchical validation.
Answer when a positive-heavy sign label makes raw accuracy misleading, when
balanced accuracy is a valid estimand rather than a post-hoc rescue, how
placebo comparisons and denominators should be defined, and how a metric must
be registered before outcomes. Address whether a balanced-sign metric should
be primary, co-primary, or secondary while raw accuracy remains visible.

### 2. Decentralized credit assignment for shared costs and externalities

Research original work on difference rewards, counterfactual baselines,
COMA-like marginal credit, value decomposition/residual learning, decentralized
execution with centralized training, congestion/interference externalities,
and shared-cost allocation. Identify assumptions needed for a local learner's
target to represent a global scalar objective. Distinguish exact identities,
unbiased estimators, useful shaping signals, and heuristics. Discuss
simultaneous actions, nonstationarity, stale backgrounds, double counting, and
off-policy counterfactual leakage.

### 3. Shapley and current-slot coalition residuals

Research primary Shapley/cooperative-game and potential-game work relevant to
two-player coalition residuals, marginal contribution, cost sharing, and local
coalition games. Analyze the difference between (a) a Shapley identity for one
explicit current-slot game evaluated on matched profiles and (b) summing
separately evaluated unilateral counterfactual branches. State whether a
within-configuration cost-conservation identity can establish a simultaneous
deployment potential. Relate this distinction to LC-SRS and to the Fable CSE
claim without accepting either merely by name.

### 4. Validation and pre-registration design

Research primary methodological work on clustered/world-level holdouts,
leave-one-group-out validation, leakage-resistant placebo construction,
common-random-number comparisons, nested model selection, preregistered
estimands, multiplicity, sequential stopping, and development-to-confirmatory
boundaries. Focus on designs that can distinguish a genuine held-out signal
from class imbalance, repeated physical worlds, seed pseudo-replication,
placebo mismatch, or an implementation receipt defect.

## Required synthesis back to the package

After the literature review, answer these questions separately:

1. Does the literature support using a balanced-sign estimand prospectively
   after the R6 raw predicate failed, if raw accuracy remains reported and no
   second metric revision is allowed? Give a formula-level definition and
   failure-proof denominators, or explain why not.
2. Is the current LC-SRS four-profile identity scientifically legitimate for
   its scoped current-slot teacher, and what does it not prove about learned
   Q3, simultaneous deployment, population EE, or FULL-versus-ablation
   efficacy?
3. Does the literature support CSE or EC as an automatically promoted route?
   If not, specify the exact proof/physical test missing. Do not call a
   same-configuration conservation identity a summed-unilateral exact
   potential without justification.
4. What is the smallest exact next contract: fixed candidate/formula,
   comparator arms, unopened TRAIN worlds, lineages/seeds, raw and balanced
   estimands, physical/composition/service predicates, placebo and leakage
   checks, compute class, and a hard stop with no second metric revision?
5. What evidence would falsify the three-head thesis or show that the problem
   is metric imbalance, state/interface insufficiency, composition failure,
   or a runtime/receipt defect instead?

Limit candidate proposals to at most three materially distinct alternatives,
ranked before any new outcome. Do not propose a post-outcome sign reversal,
scale change, threshold relaxation, seed/rung selection, or hybrid of CSE/EC
and LC-SRS. Do not prescribe episode-policy training at this gate. Classify a
future multi-world simulator/rollout projected above about 30 minutes as
**heavy** and route it to the Ubuntu server under separate authorization.

## Evidence discipline and response format

Maintain a compact claim-to-source ledger. Label each material statement as
one of:

- `LITERATURE-SUPPORTED PRINCIPLE`
- `PROJECT-COPIED FACT`
- `PROJECT-HANDOFF FACT`
- `INFERENCE`
- `PROPOSAL`

Never merge literature evidence with project evidence. Clearly mark where a
bridge from a paper to this simulator is an inference. Say when a source is
not sufficient to establish the project claim.

Return 2,200–3,200 words with these sections:

1. Direct answer and decision context
2. Research method and source-quality limits
3. Imbalance-aware metrics and prospective-gate design
4. Credit assignment, shared externalities, and decentralized execution
5. Shapley/current-slot residual analysis and the CSE boundary
6. Validation-design synthesis mapped to this package
7. Ranked candidate dispositions (at most three)
8. One formula-complete next contract and falsification rules
9. Claim-to-source ledger
10. Remaining uncertainty and final decision

Cite primary sources inline with stable DOI/publisher links. Do not cite
search-result pages or tertiary summaries. Do not claim that the package's
development signs prove learned efficacy, physical superiority, or deployment
readiness. Do not run training, simulation, TEST, or project file actions.

The final line must contain exactly one token from this set, with no code
fence, punctuation, explanation, or text after it:

`CONTINUE_LCSRS_FRESH_GATE`

`PROMOTE_CSE_FAST_ROUTE`

`PROMOTE_EC_FAST_ROUTE`

`STOP_AND_REDESIGN_C3`
