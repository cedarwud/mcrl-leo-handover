# Controller adjudication — where Phi sits, and whether the ACM correction may be printed
Recorded 2026-09-09, server clock about 08:45 UTC. Two questions raised by the symbol-table merge (conflict C-01) and the thesis merge (open question O-1). Both are decided here so the paper text is unblocked.

## 1. C-01 — Phi is not inside the score that the decomposition uses
The sources were reported as contradicting each other. They do not. **My own documents were wrong and the sealed v1.5 is right.** The executed code settles it:

* `run_v025_matrix_probe.py::_objective` returns `bits - eta_ref * joules` for a selection profile. There is no `Phi` term.
* The probe's coordinator ranking is `objective(config, profile) = _objective(profile, calibration) + kappa * _phi_for(incumbent, config, ...)`, that is the score plus the **transition-priced** signalling term.
* The probe's own defect notes state it in the same words: the interaction decomposition, and therefore `Psi`, is built on `F = B - eta*E` with `Phi` carried separately, while the selection objective is `G = F + kappa*Phi`.

**Ruling.** The operative definitions are:

| symbol | definition | used by |
|---|---|---|
| `F` | `B - eta_ref * E` | the score decomposition, `d_i` and `Psi_A` |
| `G` | `F + kappa * Phi(incumbent -> candidate)` | the coordinator's ranking and the service-guarded search |

Every controller document of mine that wrote `F = B - eta_ref*E - Phi` is corrected by this ruling, including the decomposition summary and probe-split amendment 1. The sealed declarations are **not** amended; v1.5 already says this.

**One consequence I got wrong, and it matters for the probe.** My neighbourhood declaration argued that at a certified iterated unilateral optimum every `d_i <= 0`. That holds for the marginals of the objective the unilateral search actually optimises, which is `G`. It does **not** follow for `F`-marginals when the `Phi` terms differ across candidates. The probe already reports both censuses separately and counts the anchors carrying any positive `d_i^F`, so no run is invalidated, but the argument in my declaration is narrower than I wrote it. The blind-spot critique in that declaration is unaffected: it concerns which users are enumerated, not which objective ranks them.

**One item left open for confirmation, not assumed.** `network_objective` receives `kappa` and may price an outcome-level quality term inside `F` for an evaluated profile, which would be distinct from the transition-level `Phi` added in `G`. That must be confirmed against the function body before the method section is finalised. Until confirmed, the paper says only what the table above states.

## 2. O-1 — the ACM correction's paired verification is a validity certificate and may be printed
The question was whether the paired before-and-after comparison of the ACM correction may appear in the paper, or whether it is a result that must wait for the matrix.

**Ruling: it is a validity certificate and may be printed**, in the same category as the independent link-budget closure ledger, subject to three conditions.

It qualifies because it compares two *implementations of the same declared physics* on identical profiles and identical powers, one carrying a confirmed defect and one not. It makes no statement about C1, C2 or C3, about any arm, comparator or policy, and it selects nothing. Withholding it would be worse than printing it: the paper would silently rest on a corrected engine while omitting the evidence that the correction was needed and was made.

**Conditions.**
1. It is reported as an **implementation difference**, never as system performance. The corrected pooled figure is not the system's energy efficiency and must never be quoted as such.
2. Its provenance is stated in the same sentence: a paired quarantined smoke on a development world with two anchors, identical base profiles and powers, not a formal world and not a claim-bearing run.
3. The deviation register carries a record that the defect was **found and fixed**, with its timing, and with the explicit exclusion of every pre-correction development number from every later comparison. The thesis merge already drafts this as entry D-11 and section 5.2.4; that structure is accepted.

The four placeholder slots in section 5.2.4 may therefore be filled with the paired availability and pooled-efficiency figures, under those conditions.

## 3. What this does not decide
Nothing here authorises any run, changes any threshold, sign, seed, horizon, price or acceptance rule, or creates a gate. The open question of whether the abstract and the concluding chapter carry the owner's settled wording rather than a drafted substitute is **not** decided here and remains with the owner.
