# DR-3 — Survey: reported results, baselines and demonstration-guided RL in satellite resource allocation

*Optional context: `00-EVIDENCE-LEDGER.md` describes one project. It is background only —
every factual claim in your report must come from the literature.*

## Research question

Establish what the LEO/NTN beam-handover and resource-allocation literature actually
**reports** — metrics, magnitudes, baselines, and how multi-objective rewards are handled —
and whether **demonstration-guided reinforcement learning** has been applied in this domain.

## Scope

Reinforcement learning for beam management, beam hopping, user-to-beam or user-to-satellite
association, and handover in LEO / NTN satellite systems. Include adjacent wireless
resource-allocation work where the objective is energy efficiency. Include the
demonstration-guided RL literature only where it is applied to wireless or satellite
systems.

**Source bar**: peer-reviewed journals and conferences, and arXiv preprints with citations.
Every numeric claim carries a paper and its table or figure. **Recency**: 2018-present,
with earlier work included where it defines a standard baseline.

## Deliverable

### A. Reported results table

One row per paper, columns: **venue and year** · **system and constellation assumptions** ·
**objective optimised** · **EE definition used** (bits/J, bits/Hz/J, ratio of sums, mean of
per-user ratios, or unstated) · **reported EE magnitude** · **baselines compared against** ·
**whether any trivial rule baseline outperformed the learned method** · **handover rate and
service metrics reported, if any**.

Aim for breadth — twenty or more papers if the field supports it — so the distribution of
reported magnitudes and baseline practice is visible.

### B. Baseline practice

- How often is the comparator a **trivial rule** (max-SINR / max-RSRP / nearest-satellite /
  greedy / random), and how often is a non-learned baseline reported as **winning** on the
  paper's own primary metric?
- Which baselines does this field treat as **mandatory**? Is there a de facto standard set?
- Is it common for papers to report the non-learned comparator at all, or is the comparison
  usually learned-versus-learned?

### C. Multi-objective handling

- Is **fixed linear scalarisation** of several reward terms the norm in this literature?
  Collect the weight vectors that are actually used and how they are chosen (tuned,
  declared, cited, unexplained).
- Is there published **criticism** of fixed scalarisation for energy-efficiency objectives
  specifically — e.g. showing that no single weighting orders configurations correctly, or
  that a scalarisation can be anti-aligned with its own declared endpoint? Cite it.
- Is **constrained** RL (maximise one objective subject to bounds on others) used in this
  domain, and how are the bounds chosen?

### D. Demonstration-guided RL in wireless and satellite systems

- Has DQfD, offline RL, advantage-weighted regression, guide-policy bootstrapping, or
  constrained RL from demonstrations been applied to wireless resource allocation, beam
  management or handover? For each case: **what was the demonstrator** (human, prior
  policy, optimisation solver, heuristic rule), **what was reported as the gain**, and
  **what baseline it was measured against**.
- Specifically collect cases where the demonstrator is an **optimisation solver or a
  heuristic rule** rather than a human or a prior learned policy. What is this called in
  this literature?
- Collect any case where the demonstrator is **expert on one objective while violating a
  constraint or performing badly on another**, in any domain. What is the reported
  treatment?

### E. The "catfish" line

An RIS/CDRL paper describes a training-time mechanism called "catfish": an external solver
seeds a catfish replay memory, experiences are separated by an energy-efficiency threshold,
two agents carry different discount factors, batches are mixed periodically ~70/30, and a
competitive reward `r^C = r + eta(r^CF − r^M)` is applied.

- Does this line have **any independent replication, citation, or follow-up** — by other
  groups, in other domains, or in later work by the same authors? Report the citation
  count and who cites it.
- The competitive-reward term cites "SASR / Shen et al." Establish **what that citation
  refers to**, or report that it does not resolve to any paper.
- Is "catfish effect" used as a mechanism name elsewhere in the reinforcement-learning
  literature, and does it denote the same thing?

### F. Negative and diagnostic results

Collect precedents in wireless or satellite RL for papers whose primary contribution is a
**negative or diagnostic** result — for example, that a learned method fails to beat a
simple baseline, or that a commonly used reward formulation is misspecified. Note the venue
and how the result was framed.

## Format

Tables by section, then the reference list. Where the field's reporting practice is
inconsistent, describe the inconsistency rather than averaging over it.
