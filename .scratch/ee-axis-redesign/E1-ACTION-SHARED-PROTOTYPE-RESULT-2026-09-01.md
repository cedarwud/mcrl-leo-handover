# E1 action-shared scorer prototype result (validation only)

Status: non-authoritative diagnostic; held-out test and EE endpoint remain unopened.

## Boundary

- Source: frozen E1 train/validation batches only.
- Test split opened: `false`.
- Physical C1/C2/C3 definitions: unchanged.
- Pairwise targets, normalization, loss, three independent Q functions, and
  initialization seeds: unchanged.
- Only prototype change: replace the 228-to-28 free-output MLP with one shared
  scalar scorer applied to each action's eight slot-aligned features plus the
  four global temporal features (`12 -> 100 -> 50 -> 50 -> 1`).
- Prototype script: `/tmp/e1_action_shared_screen.py`.
- Prototype script SHA-256:
  `c403e8093e2495e4d75e9d4c7a57d2ccb867302946c57a1c6dc081d31736b9a5`.

## Mean validation result across three initialization seeds

`ratio` is model MAE divided by the stronger of the frozen action-only and
constant-zero baselines. Lower is better. `skill = 1 - ratio`.

| Updates | Route | Ratio | Skill | Train-to-validation action-main-effect fraction |
|---:|:---:|---:|---:|---:|
| 0 | C1 | 1.016501 | -0.016501 | -0.015814 |
| 0 | C2 | 0.992283 | 0.007717 | 0.059456 |
| 0 | C3 | 1.026034 | -0.026034 | 0.049072 |
| 3 | C1 | 0.943996 | 0.056004 | -0.079956 |
| 3 | C2 | 0.962136 | 0.037864 | 0.105105 |
| 3 | C3 | 0.962278 | 0.037722 | 0.132710 |
| 10 | C1 | 0.853078 | 0.146922 | -0.104209 |
| 10 | C2 | 0.912742 | 0.087258 | 0.152358 |
| 10 | C3 | 0.980900 | 0.019100 | 0.056186 |
| 30 | C1 | 0.728873 | 0.271127 | -0.149053 |
| 30 | C2 | 0.900429 | 0.099571 | 0.215536 |
| 30 | C3 | 0.975001 | 0.024999 | 0.000768 |
| 100 | C1 | 0.713773 | 0.286227 | -0.141911 |
| 100 | C2 | 1.095987 | -0.095987 | 0.003517 |
| 100 | C3 | 0.976883 | 0.023117 | -0.071592 |
| 300 | C1 | 0.709948 | 0.290052 | -0.096125 |
| 300 | C2 | 0.911017 | 0.088983 | 0.028269 |
| 300 | C3 | 1.099082 | -0.099082 | -0.027163 |
| 1000 | C1 | 0.904657 | 0.095343 | -0.032867 |
| 1000 | C2 | 1.119792 | -0.119792 | 0.042448 |
| 1000 | C3 | 1.250147 | -0.250147 | -0.038271 |

At common rung 30 every route is better than the stronger baseline in every
initialization:

| Initialization | C1 skill | C2 skill | C3 skill |
|---:|---:|---:|---:|
| 2026091101 | 0.274668 | 0.092675 | 0.042980 |
| 2026091102 | 0.266711 | 0.107312 | 0.016623 |
| 2026091103 | 0.272001 | 0.098726 | 0.015393 |

## Narrow interpretation

The prototype removes the observed free action-slot shortcut and shows
state-conditioned train-to-validation signal for C1, C2, and C3 on the same
common rung. It does not establish held-out instrument validity, EE benefit,
or Catfish ablation efficacy. The sealed test must remain unopened until the
learner change is reviewed, implemented, and resealed.
