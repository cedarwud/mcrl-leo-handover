# Multi-Catfish C3 V0.3 formula-first census receipt

Date: 2026-08-31  
Status: **single-seed physics-opportunity evidence; no training/efficacy claim**

## Frozen inputs

- design: `MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`;
- source checkpoint: episode 8999, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`;
- evaluation seed: `2026082401`;
- users: `100`;
- reference calibration: 10 steps, \(\Delta t=30.08\) s,
  \(\lambda_0=84994621.12635651\) bits/J;
- census: 10 live Main steps, two sealed focal users per step, every physical
  alternative at each selected anchor;
- execution: preview-only `evaluate_actions`; no replay, update, checkpoint, or
  candidate action committed.

Raw receipt:
`.scratch/ee-axis-redesign/c3-focal-nonfocal-oracle-pilot-v03-r1.json`  
SHA-256:
`b6d08acf5a0ed9921d72cb23bf3dd90f5c194a326dfda42ce8f3cb6a69f43883`

## Results

| Quantity | Value |
|---|---:|
| Anchors | 20 |
| Evaluated unilateral candidates | 498 |
| Service-safe candidates | 473 |
| Anchors with positive C3 action headroom | 15/20 (75.0%) |
| Service-safe candidates with \(\zeta_3>0\) | 277/473 (58.56%) |
| Service-safe candidates with total surplus \(\zeta_1+\zeta_3>0\) | 143/473 (30.23%) |
| Candidates with nonzero energy mediation | 342/473 (72.30%) |
| Spearman correlation, \(\zeta_1\) vs \(\zeta_3\) | -0.0256 |
| Affine \(R^2\), predict \(\zeta_3\) from \(\zeta_1\) | 0.000264 |
| Maximum identical-branch target magnitude | 0 bits |
| Maximum accounting residual | \(7.63\times10^{-6}\) bits |

Among the 15 positive-headroom anchors, the C3-enabled system-surplus gain over
the C1-only choice ranged from `4.04e8` to `1.34e10` bits; the median was
`3.50e9` bits for the sampled 30.08-s opening interval.

## Adjudication

This census is a **GO only for C3 pair-dataset implementation**: C3 has
unilateral physical opportunity, changes the oracle-best action at many
anchors, and is not an affine duplicate of C1 in this sample. While training
remains `NO-GO`, it does not authorize a learnability pilot. It is also not a
GO for an EE-improvement claim because it uses one evaluation seed, an
exploratory anchor sample, and an oracle rather than a learned Q3. Multi-seed
preregistered headroom and matched Main-only ablation remain required.
