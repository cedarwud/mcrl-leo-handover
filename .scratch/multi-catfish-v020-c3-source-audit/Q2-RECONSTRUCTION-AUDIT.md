# V0.14 compact Q2 state reconstruction audit

This is a source-only diagnostic. It reads the representative TRAIN shard
`artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/source-panel/shards/2026108001-2026092101/source.npz`, decodes its 448-dimensional feature-major `q2_states`, and compares the reconstructed uncentered OPS3 `z2` surface with the saved `q2_target_bits`. No simulator, TLE propagation, training, or test split was opened.

The implementation is [`reconstruct_v014_q2_from_state.py`](reconstruct_v014_q2_from_state.py). It uses the canonical `pa_efficiency` and `supply_power_w` helpers. For an existing beam, the required marginal is

```text
supply(max(background_power, required_power)) - supply(background_power)
```

For a new beam it is the required beam supply plus `P_cir`, plus `P_BB` only
when the satellite was inactive. The recovered rate is

```text
(BEAM_BANDWIDTH_HZ / (1 + background_load)) * log1p_sinr / ln(2)
```

where `background_load = 100 * state[background_load_feature]`. The horizon is
`min(3, 10 - 1 - step_index)`.

## Representative result

The shard has 1,000 rows and 26,425 legal row/action entries. Its metadata
receipt matches the NPZ bytes, declares `TRAIN`, and declares
`test_split_opened: false`.

| metric on legal entries | max | median | p95 |
|---|---:|---:|---:|
| absolute error (bits) | 1,551.546 | 32.224 | 380.029 |
| relative error, nonzero targets only | 1.74264e-4 | 1.02269e-8 | 1.75389e-7 |
| error / maximum absolute target scale | 7.19617e-8 | 1.49455e-9 | 1.76260e-8 |

There are 2,793 legal entries with an exactly zero saved target; relative error
for those entries is undefined and is excluded from the second row. The
maximum absolute saved target magnitude is 2.15607e10 bits, so the observed
absolute error is consistent with float32 feature quantization; no missing
OPS3 term is indicated by this audit. Terminal rows (`step_index=9`, horizon
zero) reconstruct exactly as the all-zero target surface.

## Lambda repricing

The script emits
`q2-repriced-target-lambda-half.npy` for
`lambda_new = 0.5 * 0x1.443a8f481639ap+26`. Repricing uses the recovered
components directly:

```text
z2(lambda') = z2(lambda)
                 - (lambda' - lambda) * mean_h[chi_h * interval * dP_h]
```

The direct and affine forms agree within `3.815e-6` bits (floating-point
evaluation noise), with no new physics call.

## Scientific boundary

Under the frozen V0.14 contract—100 users, ten physical steps, 28 native
actions, canonical OPS3 constants, and the existing feature-major schema—the
compact state contains every quantity needed for linear lambda repricing:
rate (`log1p(SINR)` plus frozen load), persistence/outage, required power, and
the beam/satellite indicators needed for the network-power delta. The result
is not bit-identical because the deployable features are float32, and it does
not justify repricing a changed geometry, population normalization, policy,
or physics model. For those changes, source physics must be regenerated.
