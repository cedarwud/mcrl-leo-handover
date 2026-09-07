# Thesis ch3 — three-color frequency-reuse fidelity fix (HANDOFF)

**Status:** PENDING (USER-approved as a separate-session task, 2026-07-03).
**Why deferred:** load-bearing formula edit to the oral-defense-core Chinese thesis
that touches the SYSTEM MODEL (needs a new coloring-configuration passage) + three
equations, and codex cross-model verification was unavailable (quota hit) at the time
the conf paper was fixed. Do NOT hand-run this without codex G6 + a `build_ris.sh` +
MS-Word check.

## The gap (grounded, code-verified)

`thesis-mc/mc-modqn-base.md` ch3 models the channel with **full-band reuse and
full interference**, but the env (which produces every J_w number in ch5) uses
**three-color frequency reuse**:

| quantity | thesis ch3 (current) | env code (authority) |
|---|---|---|
| candidate bandwidth (3.16) | `W = B_sys / Û_{u,s,v}` | `b_alloc = bandwidth_hz / 3`, then `/load` — i.e. `(B_sys/3)/U` |
| intra-sat interference (3.13) | sum over ALL `v'∈V\{v}` | co-channel only (same color) |
| inter-sat interference (3.14) | sum over ALL `s'≠s, v'∈V` | co-channel only (same color) |
| noise (3.15) | `N_0 W_{u,s,v}` | `N_0 · b_alloc · NF` (b_alloc = B/3) |

**Env authority:** `src/modqn_paper_reproduction/env/family_b_step.py`
- rate `~line 740`: `thr = self.config.b_alloc_hz / load * log2(1+sinr)`
- `b_alloc_hz` property (`~line 103`): `return self.bandwidth_hz / 3`
- co-channel interference `~lines 645-722`: `color_sums` grouped by `self.grid.colors`, then
  `co_sum = color_sums[u, l, colors]` — only same-color active beams contribute.
- `_noise_power_w` (`~line 605`): `N_0 · b_alloc_hz · NF`.
- coloring: `family_b_step.py:76` `cell_coloring = "(q-r) mod 3"`.

**The conf paper `conf-demo/mccrl-paper.md` is ALREADY fixed** (commit `d26dcec`→`e69d864`);
thesis should mirror that exact treatment. Conf forms (authoritative target):
- eq(2) SINR denominator interference sums over `𝓘_{s,v}(t)` = active beams sharing the color of `(s,v)`.
- eq(3) rate `R = B_c / U_{s,v} · log2(1+γ)`, with `B_c = B_sys/3`.
- noise `σ² = N_0 · B_c · F_NF`.

## Exact edits (mirror the conf, keep thesis notation Û + intra/inter split)

1. **System model (§3.1, near the beam/cell-activation passage, ~line 156):** add ONE short
   passage defining the three-color reuse: cells are colored by `(q−r) mod 3`; same-color
   cells/beams share a frequency sub-band and interfere, different colors are orthogonal.
   Define the co-channel set, e.g. `𝓒(s,v) = { active (s',v') : color(s',v')=color(s,v) }`.
   Without this, the co-channel interference sums below have no defined index set.
2. **eq(3.13) intra:** restrict the sum to same-color beams:
   `I_intra = Σ_{v'∈V\{v}, color(s,v')=color(s,v)} z p h`.
3. **eq(3.14) inter:** restrict to same-color:
   `I_inter = Σ_{s'≠s} Σ_{v': color(s',v')=color(s,v)} z p h`.
4. **eq(3.16) bandwidth:** introduce the per-color band. Either
   `W_{u,s,v} = (B_sys/3) / Û_{u,s,v}` or define `B_c = B_sys/3` and write `W = B_c/Û`.
   Add a clause: `B_c = B_sys/3` is the per-color bandwidth under three-color reuse.
5. **eq(3.15) prose:** note `N_0 W_{u,s,v}` is the noise over the per-color band (consistent
   with the new W). No structural change to (3.15) itself.
6. **§5.1 experimental setup:** confirm the system bandwidth value (env `BANDWIDTH_HZ = 500 MHz`
   → per-color `B_c ≈ 166.7 MHz`). If §5.1 currently states 500 MHz as the served bandwidth,
   clarify it is the SYSTEM bandwidth and each color gets B/3.

## Cross-reference safety (verified 2026-07-03)

Eq numbers (3.13/3.14/3.15/3.16) must NOT change — they are referenced by number at
`mc-modqn-base.md` lines 156, 200, 262, 327, 371 (and eq 3.27 candidate-EE reuses 3.16/3.17).
Editing the equation BODIES while keeping the numbers preserves every cross-reference.
§4.4 (decode) and §5.x do not re-derive these; they cite by number.

## Verification steps (do all)

1. codex G6 (cross-model, high effort) on the ch3 diff: verify the co-channel sums, `B_c=B_sys/3`,
   and noise are faithful to `family_b_step.py`, and that the new coloring passage is self-consistent.
2. `bash thesis-mc/tools/build_ris.sh` → open `scratch/conversion-test/mc-thesis-ris.docx` in **MS Word**
   (not LibreOffice) to confirm the edited equations (3.13/3.14/3.16) render with correct `\tag` numbers
   and the three-color passage flows.
3. Re-check §4.4 / §5.1 read consistently after the edit.

## Provenance
- Discovered during the conf-demo reviewer-harvest pass (2026-07-03) when aligning conf eq(2)/(3) to
  the env; conf fixed, thesis flagged. See memory `project_ieee_6page_paper_2026-07-02.md`.
- G1 `modqn.py` / EUV env are READ-ONLY; this is a thesis-text edit only, no code/env change.
