# V0.23 chapter-5 TRAIN-development figure pipeline

This package renders deterministic, headless development curves from the
physical-evaluation runner's authenticated 100-episode checkpoint/rung chain.
It is ready before the first evaluation receipt exists and does not modify an
evaluation root.

The figures are descriptive `TRAIN development` views of cumulative physical
receipts: pooled ratio-of-sums energy efficiency, pooled served fraction with
the fixed `0.001` BASELINE margin band, and matched-world pooled differences
against BASELINE with a descriptive 95% bootstrap band.  The optional fourth
figure shows the additive delivered-bit and energy sums underlying the pooled
ratio.  Every figure carries the receipt claim ceiling and authenticated root
digest in its footer.

These figures are not held-out evaluation, hypothesis tests, p-values, causal
proof, deployment evidence, or a basis for choosing formulas, arms, seeds,
horizons, thresholds, budgets, or stopping rules.  A terminal `result.json`,
when present, is authenticated and cross-checked but does not change plotting
semantics.  A root explicitly marked nonformal (or named rehearsal/nonformal)
is refused unless `--allow-nonformal` is supplied; all of its figures then show
`REHEARSAL — NOT A RESULT`.

## Commands

The project virtual environment does not currently vendor Matplotlib.  On the
current checkout, expose the OS-packaged scientific stack explicitly:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages ./.venv/bin/python \
  .scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py \
  --input-root /path/to/physical-evaluation-root \
  --output-dir /path/to/absent-figure-output
```

Add a later compatible root and the additive panels with:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages ./.venv/bin/python \
  .scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py \
  --input-root /path/to/four-arm-root \
  --additional-root /path/to/later-root \
  --output-dir /path/to/absent-figure-output \
  --additive-panels
```

For a rehearsal root, add `--allow-nonformal`.  Each root is rendered as its
own figure set (`root-01-*`, `root-02-*`) so identically named arms from
different experiments are never silently merged.

Run the focused tests exactly as follows:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages ./.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-ch5-figure-pipeline
```

The output directory must not exist.  A successful run writes PNG and PDF
files plus `FIGURE-MANIFEST.json`, which binds input-root digests, authenticated
input files, receipt/rung coverage, renderer SHA-256, and every figure SHA-256.
