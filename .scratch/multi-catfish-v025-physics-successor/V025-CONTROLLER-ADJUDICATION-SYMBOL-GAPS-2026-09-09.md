# Controller adjudication — the four symbol gaps that block chapters 4 and 5
Recorded 2026-09-09. The unified symbol table registered four sealed concepts that have no glyph. All four are decided here. The binding constraint reported by the collision audit is that every unused Greek capital forms a case-pair with a live lowercase, so no free Greek capital exists, and multi-letter subscripts are forbidden by the table's own rules.

**The governing principle for all four: do not introduce a new letter. Use the superscript-marker mechanism the table already uses**, so each new symbol inherits an existing letter's meaning and adds a qualifier. This keeps the alphabet closed and makes every new glyph readable from its base letter.

## G-01 — C2's continuation value: `Ω^c`
The score is `Ω` in the table. C2 is the declared continuation of that score over the forecast horizon, so it is a qualified score, not a new quantity. The table already carries `Ω^q_0` through `Ω^q_3` for the four per-arm ranking keys, so the superscript slot on `Ω` is the established place for a score qualifier.

`Ω^c` denotes the declared continuation value. Chinese row text: **`Ω^c`　C2 的宣告延續值；於預測視野上對 `Ω` 的延續，非新量。**

Note the constraint the sealed rules place on it: v1.9 item 5 fixes that with a unique immediate maximiser, a tie-break-only continuation cannot change the selected profile, so the set-level C2 marginal is expected to be zero by construction and that is an admissible result. `Ω^c` must never be presented as if a non-zero marginal were required of it.

## G-02 — candidate-refresh period: `N^r`
Bare `N` carries six meanings in the table and cannot take a seventh. `N` already disambiguates by superscript, as in `N^a_s` for the active-beam count, so `N^r` follows the existing pattern.

`N^r = 4`. Chinese row text: **`N^r`　候選刷新週期，`N^r = 4`；為候選集重建的間隔，**不是** dwell。**

The second clause is not optional. v1.2 item 7 names it a candidate-refresh period specifically to stop it being read as a dwell time, and the paper must carry that distinction wherever the symbol appears.

## G-03 — standby: `P^s` for the power, and no glyph for the fraction
Two different rulings, because the two items are not alike.

**The standby power gets a glyph:** `P^s`. The table's power family already disambiguates by superscript, as in `P^N` for the network total, and `P_idle` is a forbidden multi-letter subscript.

**The standby fraction does not.** `f` is unavailable, being both the shared scorer and the carrier-frequency subscript, and the fraction appears in exactly one place, a settings table, under a treatment that may not reach the chapter-5 figures at all. Writing it as the numeric constant `1/12` in prose costs the reader nothing and adds no collision risk. A symbol invented for a single table entry is a liability, not a convenience.

Chinese row text: **`P^s`　standby 功率；standby 時間比例以數值 1/12 於文中敘述，不設字形。**

## G-04 — pairwise cross-gain: `H^x_{u,j}`
This is the important one, because contract v1.2 item 2 explicitly requires the C3 encoder to receive **pairwise** cross-gains and forbids giving it only a scalar interference summary. Without a glyph the paper cannot state its own C3 input contract.

The table writes the composite wanted-link gain as `H·G^T`, and it already uses `x` as the marker for "cross" in `I^x`, the cross-beam interference term. So the cross-gain reuses both conventions.

`H^x_{u,j}` is the composite channel gain from aggressor beam `j` to user `u`, that is the path term times the transmit antenna gain evaluated at the off-axis angle from beam `j` toward user `u`. The wanted link stays `H·G^T` and is not renamed. Interference is then written `I_u = Σ_{j ≠ b(u)} p_j · H^x_{u,j}`, which makes the C3 encoder's declared input the vector of `H^x_{u,j}` over the affected beams rather than the scalar `I_u`.

Chinese row text: **`H^x_{u,j}`　自干擾波束 `j` 至使用者 `u` 的成對交叉增益（路徑項乘上 `j` 朝 `u` 之離軸角上的發射天線增益）；C3 編碼器的宣告輸入為受影響波束上的 `H^x_{u,j}` 向量，非純量 `I_u`。**

This choice is supported by the headroom diagnostic, which found that 98.879 % of a victim's interference arrives from an adjacent beam on its own satellite and that a single aggressor carries 74.251 % of it. A scalar summary discards exactly the structure that makes coordination actionable, which is presumably why the contract forbade it.

## One prior uncertainty now closed
The collision audit recorded that conflict C-01, the exact definition of `G`, could only be inferred from prose because the server was unreachable. It is now settled from the executed source, which was recovered through the local sync: `F = B − η_ref·E` with no signalling term, and `G = F + κ·Φ` where `Φ` prices the incumbent-to-candidate transition. See `V025-CONTROLLER-ADJUDICATION-SCORE-AND-CERTIFICATE-2026-09-09.md`. The audit's uncertainty marker on C-01 may be removed.

## Standing
This adjudication fixes notation only. It changes no threshold, sign, seed, horizon, price, acceptance rule or claim condition, authorises no run, and creates no gate.
