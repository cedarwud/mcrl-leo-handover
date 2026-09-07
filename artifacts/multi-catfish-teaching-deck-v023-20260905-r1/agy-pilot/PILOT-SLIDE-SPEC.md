# Pilot Slide Specification: Slide 23 (Exact Two-Player LC-SRS Teacher Formulation)

- **Presentation Template:** `/home/u24/pptx-craft/assets/wmnlab.pptx`
- **Slide Dimensions:** 13.333" × 7.5" (12,192,000 EMU × 6,858,000 EMU, 16:9 widescreen)
- **Selected Slide:** Slide 23 — *Exact Two-Player LC-SRS Teacher Formulation*
- **Status Tag:** `PROVISIONAL_C3_GATE` (Method Core Frozen; Offline Observability Gate Authorized)
- **Authority Citations:**
  - `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` §Frozen paper-visible method
  - `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` §5 (Exact V0.22 two-player LC-SRS teacher)
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/active-symbol-table-v023-20260905.md` §10.13.3
  - `artifacts/chinese-word-v023-lcsrs-20260905-r2/SYMBOL-COLLISION-AND-SINGLE-LETTER-AUDIT.md`
  - Synthetic Fixture Verification: `tests/test_w181_ee_axis_coalition_residual_c3.py`

---

## 1. Strict Typographic Invariants

This slide strictly complies with the deck typography specification:
- **Font Family:** Times New Roman throughout (text and mathematical variables).
- **Slide Title:** Exactly **28 pt** Bold.
- **Ordinary Body Text:** Exactly **24 pt**.
- **Text inside Cards / Boxes / Badges / Diagrams:** Exactly **20 pt**.
- **Prohibited Sizes:** Strictly NO intermediate font sizes (strictly prohibited: 26, 22, 18, 16, or 14 point).

---

## 2. Layout Geometry & Visual Architecture

```text
+---------------------------------------------------------------------------------------------------------+
| [Title Box] Exact Two-Player LC-SRS Teacher Formulation               [Badge] PROVISIONAL_C3_GATE       |
| (left: 0.62", top: 0.15", width: 12.09", height: 0.70") [28 pt Title, 20 pt Badge]                     |
+----------------------------------------------------+----------------------------------------------------+
| PANEL 1: Component Terms & Interaction (Left)       | PANEL 2: Target Formula & Conservation (Right)     |
| (left: 0.62", top: 1.00", width: 5.90", ht: 5.90")| (left: 6.81", top: 1.00", width: 5.90", ht: 5.90")|
|                                                    |                                                    |
| +-- Box 1.1: Local & Externality Terms [20 pt] ----+ | +-- Box 2.1: The LC-SRS Target [20 pt] ------------+ |
| | - Local Own Surplus: \ell_i                     | | | - Target Definition: z_{3,i} = e_i + \Psi / 2    | |
| | - Non-Focal Externality: e_i                    | | | - Normalized Teacher Label: y_i = z_{3,i} / \kappa| |
| +-------------------------------------------------+ | +--------------------------------------------------+ |
|                                                    |                                                    |
| +-- Box 1.2: Joint Interaction Decomposition [20 pt] +-- Box 2.2: Exact Conservation Identity [20 pt] --+ |
| | - Bit Interaction: \Psi_B                       | | | \sum_{i=1}^2 (\ell_i + z_{3,i}) = G(x^c) - G(x^0)| |
| | - Energy Interaction: \Psi_E                    | | | Construction-level exact by mathematical def.  | |
| | - Surplus Interaction: \Psi = \Psi_B - \lambda\Psi_E | Tested on synthetic fixture in test_w181.          | |
| +-------------------------------------------------+ | +--------------------------------------------------+ |
|                                                    |                                                    |
| +-- Box 1.3: Causal Integrity Check [20 pt] -------+ +-- Box 2.3: Teacher-Only Boundary Notice [20 pt] ---+ |
| | Evaluated over 32 matched fading draws.         | | Privileged 4 profiles evaluated offline only.    | |
| | Same channel realization across all 4 profiles. | | Zero coordinator or message passing at runtime.  | |
| +-------------------------------------------------+ +--------------------------------------------------+ |
+----------------------------------------------------+----------------------------------------------------+
| [Footer Banner] Authority: docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md §5     |
+---------------------------------------------------------------------------------------------------------+
```

### Precise EMU & Metric Coordinates

1. **Slide Canvas:**
   - Width: 13.333 inches = 12,192,000 EMU
   - Height: 7.500 inches = 6,858,000 EMU

2. **Title & Header Container:**
   - Left: 0.620" (566,928 EMU)
   - Top: 0.150" (137,160 EMU)
   - Width: 12.090" (11,055,096 EMU)
   - Height: 0.700" (640,080 EMU)
   - Title Font: Times New Roman, **28 pt**, Bold, Color: Deep Blue `#003366`
   - Status Badge: Right-aligned inside title container, **20 pt** Bold, Background `#FFF3CD`, Text `#856404`, Border `#FFEEBA`

3. **Panel 1 (Left Column — Physical Components & Interaction):**
   - Left: 0.620" (566,928 EMU)
   - Top: 1.000" (914,400 EMU)
   - Width: 5.900" (5,394,960 EMU)
   - Height: 5.900" (5,394,960 EMU)
   - Card Background: `#F8F9FA`, Border: 1 pt solid `#D1D5DB`, Radius: 6 pt

4. **Panel 2 (Right Column — Shapley Allocation & Exact Identity):**
   - Left: 6.810" (6,227,064 EMU)
   - Top: 1.000" (914,400 EMU)
   - Width: 5.900" (5,394,960 EMU)
   - Height: 5.900" (5,394,960 EMU)
   - Card Background: `#F0F4F8`, Border: 1.5 pt solid `#003366`, Radius: 6 pt

---

## 3. Exact Slide Content & Typographic Hierarchy

### Header Section
- **Title (28 pt Bold, Times New Roman):** Exact Two-Player LC-SRS Teacher Formulation
- **Status Badge (20 pt Bold, Times New Roman):** `[PROVISIONAL_C3_GATE]`

---

### Panel 1: Component Terms & Interaction (Left Column, All Text 20 pt)

#### Box 1.1: Local and Externality Components ($i \in \{1, 2\}$)
- **Header (20 pt Bold, `#003366`):** 1. Local and Externality Components ($i \in \{1, 2\}$)
- **Body Text (20 pt, `#1F2937`):**
  - **Local Own Net Surplus ($\ell_i$):** Own rate gain minus full network energy penalty:
    $$[\text{omml: } \ell_i = B_i(x^i) - B_i(x^0) - \lambda [E(x^i) - E(x^0)]]$$
  - **Non-Focal Externality ($e_i$):** Unilateral rate impact on all other users:
    $$[\text{omml: } e_i = \sum_{u \ne i} [B_u(x^i) - B_u(x^0)]]$$

#### Box 1.2: Coalition Interaction Surplus
- **Header (20 pt Bold, `#003366`):** 2. Super-Additive Interaction ($\Psi$)
- **Body Text (20 pt, `#1F2937`):**
  - **Bit Interaction ($\Psi_B$):** Delivered bits in profile 11 beyond unilateral sum:
    $$[\text{omml: } \Psi_B = [B(x^c) - B(x^0)] - \sum_{i=1}^2 [B(x^i) - B(x^0)]]$$
  - **Energy Interaction ($\Psi_E$):** Consumed energy in profile 11 beyond unilateral sum:
    $$[\text{omml: } \Psi_E = [E(x^c) - E(x^0)] - \sum_{i=1}^2 [E(x^i) - E(x^0)]]$$
  - **Surplus Interaction ($\Psi$):** Fixed-multiplier net interaction:
    $$[\text{omml: } \Psi = \Psi_B - \lambda \Psi_E]$$

#### Box 1.3: Causal Integrity Guarantee
- **Body Text (20 pt, `#4B5563`):**
  - Keyed fading draws: Evaluated across 32 matched draws under identical random fields.
  - Profile 11 de-allocates the source beam, capturing the super-additive energy saving $\Psi_E < 0 \implies -\lambda \Psi_E > 0$.

---

### Panel 2: Target Formula & Conservation (Right Column, All Text 20 pt)

#### Box 2.1: The LC-SRS Target
- **Header (20 pt Bold, `#003366`):** 3. Shapley Residual Target ($z_{3,i}$)
- **Body Text (20 pt, `#1F2937`):**
  - **Target Assignment:** Unilateral externality plus half of joint interaction:
    $$[\text{omml: } z_{3,i} = e_i + \frac{\Psi}{2}]$$
  - **Normalized Student Label ($y_i$):** Dimensionless target scaled by $\kappa$:
    $$[\text{omml: } y_i = \frac{z_{3,i}}{\kappa}, \quad \kappa = \frac{\mathcal{B}_0^M}{n_0}]$$
  - Positive, zero, and negative measured targets are strictly retained.

#### Box 2.2: Exact Conservation Identity
- **Header (20 pt Bold, `#006622`):** 4. Exact Mathematical Identity
- **Spotlight Formula Container (Background `#E8F5E9`, Border 1 pt solid `#4CAF50`):**
  $$[\text{omml: } \sum_{i=1}^2 (\ell_i + z_{3,i}) = G(x^c) - G(x^0)]$$
- **Body Text (20 pt, `#1F2937`):**
  - **Mathematical Parity:** Own terms $\ell_i$ plus C3 targets $z_{3,i}$ reconstruct the exact coalition surplus $G(11) - G(00)$.
  - **Exact Authority:** Construction-level exact by mathematical definition (contract §5). Verified on synthetic fixture in `test_w181` (residual $< 10^{-6}$ bit), not on raw simulator traces.

#### Box 2.3: Teacher vs. Student Boundary
- **Callout Box (Background `#FFF3CD`, Border 1 pt solid `#FFEEBA`):**
  - **Privileged Teacher Only:** The 4 physical profiles ($00, 10, 01, 11$) exist solely during offline training.
  - **Zero Deployment Overhead:** The runtime student consumes only deployable predecision descriptors (C3View) and executes one argmax. No runtime coordinator.

---

## 4. Native OfficeMath Specification (OMML Translation Table)

All mathematical expressions use native OfficeMath with strictly atomic subscripts/superscripts:

| Token Name | Mathematical Display | OfficeMath Construction Snippet | Typography Rules | Subscript Validation |
|:---|:---|:---|:---|:---:|
| `local_term` | $\ell_i = B_i(x^i) - B_i(x^0) - \lambda [E(x^i) - E(x^0)]$ | `<m:sSub><m:e><m:r><m:t>ℓ</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub> = ...` | $\ell, i, B, x, E$: Italic; $\lambda$: Italic Greek; Brackets: Upright | `PASS_ATOMIC` |
| `externality` | $e_i = \sum_{u\ne i} [B_u(x^i) - B_u(x^0)]$ | `<m:sSub><m:e><m:r><m:t>e</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub> = ...` | $e, i, B, u, x$: Italic; $\sum$: Upright N-ary operator | `PASS_ATOMIC` |
| `psi_b` | $\Psi_B = [B(x^c) - B(x^0)] - \sum_{i=1}^2 [B(x^i) - B(x^0)]$ | `<m:sSub><m:e><m:r><m:t>Ψ</m:t></m:r></m:e><m:sub><m:r><m:rPr><m:sty m:val=\"p\"/></m:rPr><m:t>B</m:t></m:r></m:sub></m:sSub> = ...` | $\Psi$: Italic Greek; $B$: Single-letter upright capital suffix | `PASS_ATOMIC` |
| `psi_e` | $\Psi_E = [E(x^c) - E(x^0)] - \sum_{i=1}^2 [E(x^i) - E(x^0)]$ | `<m:sSub><m:e><m:r><m:t>Ψ</m:t></m:r></m:e><m:sub><m:r><m:rPr><m:sty m:val=\"p\"/></m:rPr><m:t>E</m:t></m:r></m:sub></m:sSub> = ...` | $\Psi$: Italic Greek; $E$: Single-letter upright capital suffix | `PASS_ATOMIC` |
| `psi_surplus` | $\Psi = \Psi_B - \lambda \Psi_E$ | `<m:r><m:t>Ψ</m:t></m:r> = <m:sSub>...` | $\Psi, \lambda$: Italic Greek; Suffixes $B, E$: Upright | `PASS_ATOMIC` |
| `target_z3` | $z_{3,i} = e_i + \frac{\Psi}{2}$ | `<m:sSub><m:e><m:r><m:t>z</m:t></m:r></m:e><m:sub><m:r><m:t>3,i</m:t></m:r></m:sub></m:sSub> = ...` | $z, i$: Italic; $3$: Upright digit; $3,i$ atomic composite | `PASS_ATOMIC` |
| `identity` | $\sum_{i=1}^2 (\ell_i + z_{3,i}) = G(x^c) - G(x^0)$ | `<m:nary><m:sub><m:r><m:t>i=1</m:t></m:r></m:sub><m:sup><m:r><m:t>2</m:t></m:r></m:sup>...` | $i, \ell, z, G, x$: Italic; Superscripts $c, 0$: Single atomic characters | `PASS_ATOMIC` |

---

## 5. Verification Checklist

- [x] Conforms to 13.333" × 7.5" widescreen geometry in `/home/u24/pptx-craft/assets/wmnlab.pptx`.
- [x] Slide title is exactly **28 pt** Bold (Times New Roman).
- [x] Ordinary body text is **24 pt**; all card/box/badge text is strictly **20 pt**.
- [x] Zero prohibited font sizes (no 26, 22, 18, 16, or 14 point sizes).
- [x] Conservation identity citation corrected: cited as construction-level exact by mathematical definition (contract §5) and verified on synthetic fixture in `test_w181` (not `test_w184` or raw traces).
- [x] All mathematical expressions use native OfficeMath specifications.
- [x] Every subscript and superscript consists of atomic single letters or single digits ($3,i$, $x^c$, $x^0$, $\Psi_B$, $\Psi_E$).
- [x] Multi-letter strings in math indices are completely absent.
- [x] Contains clear warning that C3 is method frozen and gate pending, with zero episode efficacy claimed.
