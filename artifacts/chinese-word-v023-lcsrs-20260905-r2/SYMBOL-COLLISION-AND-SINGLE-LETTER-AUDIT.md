---
audit_id: v023-symbol-collision-single-letter-20260905
status: PASS_WITH_EXPLICIT_HISTORICAL_BOUNDARY
scope:
  live_sources:
    - mc-modqn-base.md
    - ch4-method.md
    - ch5-experimental-result.md
    - ch6-conclusion.md
  active_table: active-symbol-table-v023-20260905.md
  baseline_table: artifacts/chinese-word-r1-symbols-20260905-r1/active-symbol-table-r1-20260905.md
  historical_sections: active_table_sections_10.8_10.9_10.12
commands:
  forbidden_subscript_scan: "rg -n -o --pcre2 '(?:_|\\^)(?:\\{)?(ref|src|dst|beam|sat|own|nf|joint|base|cand|main)(?:\\})?' live_sources active_table"
  composite_scan: "rg -n -o --pcre2 '(?<!\\\\)[_^]\\{[^}\\\\n]+\\}' ch4-method.md"
---

# V0.23 symbol collision and single-letter audit

## Verdict

The V0.23 paper-visible additions use one-letter or one-number atomic
subscript/superscript components. Composite indices such as \(u,s,v\),
\(3,i\), and \(i,a,r\) are explicitly composed of atomic letters/numbers.
The old V0.3 notation remains only in the table's sections 10.8, 10.9, and
10.12, each marked historical/retired; it is not an active V0.23 claim.

## Added active symbols

| symbol | role | atomic-index check | collision decision |
|---|---|---|---|
| \(x^0,x^1,x^2,x^c\) | matched profiles 00, 10, 01, 11 | numeric or one-letter superscript | \(c\) also denotes a candidate slot; profile meaning is scoped to \(x^c\) and stated in prose |
| \(B_u(x)\) | user delivered bits in profile \(x\) | one-letter user index \(u\) | \(B^w\) remains bandwidth; function argument \(x\) separates profile bits |
| \(E(x)\) | current-slot network energy | no index | legacy \(E\) episode count is confined to unchanged Chapter 5; function argument \(x\) identifies profile energy |
| \(G(x)\) | common network surplus | no index | \(G^T\) and \(G^R\) remain physical gains; \(G(x)\) is explicitly profile surplus |
| \(\lambda\) | frozen bits-per-joule multiplier | no index | not a new long-form index; distinct from legacy prose and no post-outcome price |
| \(\kappa\) | shared output scale | no index | introduced only for normalized teacher target |
| \(\eta^N\) | Main network ratio-of-sums EE | one-letter superscript \(N\) | distinct from link display \(\eta_{u,s,v}\) and legacy PA \(\eta_0\) |
| \(C_1,C_2,C_3\) | C1/C2/C3 route labels | one numeric suffix | route labels, not multi-letter indices |
| \(Q_1,Q_2,Q_3\) | exactly three independent Q surfaces | one numeric suffix | no \(Q_j^M/Q_j^F\) active claim |
| \(\ell_i,e_i,d_i\) | LC-SRS local, externality, and partial terms | one-letter index \(i\) | \(d\) is local term label here; physical distance remains \(d_{u,s,v}\) |
| \(\Psi_B,\Psi_E,\Psi\) | bits interaction, energy interaction, fixed-\(\lambda\) surplus | one-letter suffixes \(B,E\) | no prose-like suffix |
| \(z_{3,i},y_i\) | paper target and normalized target | numeric plus one-letter atomic indices | \(z_{s,v}\) remains beam activation only in Chapter 3 |
| \(c_{ia},t_{iar},m_{iar}\) | action context, relation token, relation/action mask | \(i,a,r\) are each one-letter | no ref/src/dst index; \(c\) slot/profile context is stated |
| \(f,F_i(a)\) | shared scorer and masked token aggregate | one-letter index \(i\) | \(F(\theta,\theta_3)\) remains physical pattern; function context separates |
| \(Q_{3,i}(a)\) | reference-centred scalar C3 surface | numeric plus one-letter atomic index | no pair-name or multi-letter head |
| \(a_i^0,a_u^\star(t)\) | detached reference and Main action | numeric or star superscript; one-letter \(i/u\) | reference is never encoded as a multi-letter ref subscript |
| \(\mathcal A_u^+(t)\) | native safe action set | one-letter \(u\), single \(+\) | avoids multi-letter safe superscript |

## Collision audit

| collision | paper treatment | status |
|---|---|---|
| \(c\) candidate index versus \(x^c\) coalition profile | Candidate \(c\) appears with \(\mathcal C\) or \(b_u(c,t)\); profile \(x^c\) is defined as 11 in the two-user teacher subsection | resolved by local scope |
| \(B\) profile bits versus \(B^w\) bandwidth | \(B_u(x)\) always has user index and profile argument; \(B^w\) remains the Chapter-3 bandwidth symbol | resolved by function/upper-script context |
| \(E(x)\) network energy versus legacy \(E\) episode count | \(E(x)\) is only the profile energy in Ch4; unchanged Ch5 retains its stale setting as provenance | explicit known stale boundary |
| \(G(x)\) surplus versus \(G^T,G^R\) gains | profile argument \(x\) and superscripted physical gains are distinct | resolved |
| \(F_i(a)\) token aggregate versus \(F(\theta,\theta_3)\) antenna pattern | arguments and index context distinguish learner aggregate from physical function | resolved |
| \(d_i\) LC-SRS partial term versus \(d_{u,s,v}\) slant range | pair-member index versus physical-link indices | resolved |
| \(z_{3,i}\) teacher target versus \(z_{s,v}\) beam activation | numeric-plus-member index versus satellite/beam indices; scopes are Ch4 versus Ch3 | resolved |
| \(i\) ordered pair member versus generic user \(u\) | \(i\in\{1,2\}\) is declared only inside LC-SRS; \(u\) remains the generic system user index | resolved |
| \(\lambda\) and \(\kappa\) versus existing physical symbols | both are declared once in the active C3 method section and are not overloaded with long-form indices | resolved |

## Multi-letter subscript/superscript search results

The forbidden-token scan over the live method sources and the active table
returned zero matches for every prohibited multi-letter index in both
subscript and superscript positions:

| pattern | result |
|---|---:|
| ref | 0 |
| src | 0 |
| dst | 0 |
| beam | 0 |
| sat | 0 |
| own | 0 |
| nf | 0 |
| joint | 0 |
| base | 0 |
| cand | 0 |
| main | 0 |

The composite scan of the new Ch4 source returned these non-atomic-looking
braced forms; each is either a permitted sequence of single-letter/numeric
indices, a quantifier, or a description-only operator label:

| form(s) found | classification |
|---|---|
| _{u,s,v}, _{u,c}, _{3,i}, _{ia}, _{iar} | permitted composite indices; every component is one letter or one number |
| _{i=1}, _{u\in\mathcal U}, _{\substack{...}} | summation/constraint syntax, not a prose-like symbol index |
| ^{0}, ^{1}, ^{2}, ^{c}, ^{+}, ^{67} | permitted one-number/one-letter/single-operator superscripts |
| _{\mathrm{ReLU}} | description-only architecture label, not an indexed variable |

The unchanged Chapter-3 block necessarily contains its established physical
three-index notation \(u,s,v\); this audit does not rewrite or reclassify the
Chapter-3 scientific formulas. Chapter 5 is byte-for-byte unchanged and is
reported separately as known stale provenance.
