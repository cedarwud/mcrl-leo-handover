TASK_EXIT=DONE

The offline real-artifact dry-run passed end to end. The review checkout remained clean and unchanged.

### Selected artifact

Input root:

`/home/sat/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z/physical-evaluation-output`

Candidate assessment:

- Selected V4 rehearsal: one matching 100-episode checkpoint/rung, four arms, 400 receipts, no terminal `result.json`.
- `mcrl-v023-stageC-CHUNK-ACCEPTANCE-NONFORMAL-20260907T185925Z`: six small BASELINE-only chunk checkpoints, but no rungs or result; incompatible with the renderer’s root contract.
- Other discovered rehearsal roots were Stage A, Stage B, two-route, or shard artifacts rather than Stage-C physical-evaluation roots.

Thus the selected V4 artifact was the most complete renderable Stage-C-shaped rehearsal root available.

### Renderer

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/sat/modqn-paper-exploration/.venv/lib/python3.13/site-packages:/home/sat/mcrl-v023-review-stagec/src \
TMPDIR=/home/sat/mcrl-v023-review-stagec/.tmp \
MPLCONFIGDIR=/home/sat/mcrl-v023-figure-dryrun-20260908/.mplconfig \
/home/sat/mcrl-leo-handover/.venv/bin/python \
.scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py \
--input-root /home/sat/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z/physical-evaluation-output \
--output-dir /home/sat/mcrl-v023-figure-dryrun-20260908/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z \
--allow-nonformal \
--additive-panels
```

Exit status: `0`

Stdout:

```json
{"figures": 8, "output_dir": "/home/sat/mcrl-v023-figure-dryrun-20260908/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z"}
```

Stderr: empty.

No renderer refusal occurred, so no engineering fix is needed. For context, incompatible roots lacking matched histories would be rejected at [render_v023_development_curves.py:628](/home/sat/mcrl-v023-review-stagec/.scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py:628); the minimal fix would be producer-side generation of matching contiguous checkpoint and rung files, not weakening the loader.

### Produced files

Output directory: [mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z](/home/sat/mcrl-v023-figure-dryrun-20260908/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z)

| File | Size |
|---|---:|
| `FIGURE-MANIFEST.json` | 2,244 bytes |
| `root-01-ee.png` | 98,049 bytes |
| `root-01-ee.pdf` | 25,657 bytes |
| `root-01-service.png` | 92,274 bytes |
| `root-01-service.pdf` | 24,944 bytes |
| `root-01-paired.png` | 97,553 bytes |
| `root-01-paired.pdf` | 25,693 bytes |
| `root-01-additive.png` | 106,219 bytes |
| `root-01-additive.pdf` | 26,163 bytes |

PNG metadata:

- EE, service, and paired: 1312×768, 8-bit RGBA, sRGB, non-interlaced.
- Additive: 1680×736, 8-bit RGBA, sRGB, non-interlaced.
- All contain a PNG text chunk and approximately 160-DPI physical-resolution metadata.

Figure contents, descriptively:

- `ee`: pooled ratio-of-sums energy efficiency against cumulative episodes for FULL2, DROP_C1, DROP_C2, and BASELINE.
- `service`: pooled served fraction for the four arms, including the fixed BASELINE ±0.001 margin band.
- `paired`: matched-world pooled energy-efficiency differences against BASELINE for the three learned arms, with descriptive 95% bootstrap bands.
- `additive`: two panels showing cumulative delivered bits and cumulative energy for all four arms.

All figures visibly carry `REHEARSAL — NOT A RESULT` and the development-only disclosure. No scientific interpretation of the plotted values was performed.

### Manifest

Top-level keys:

```text
code_sha256
figures
input_roots
nonformal_watermark
receipt_count
schema
split_label
```

Important values:

- `schema`: `multi-catfish-mcrl-v023-ch5-development-figure-manifest-v1`
- `split_label`: `TRAIN development`
- `receipt_count`: `400`
- `nonformal_watermark`: `REHEARSAL — NOT A RESULT`
- `figures`: eight path/SHA-256 records
- `input_roots`: one record with 24 keys, including:
  - `actual_rung_coverage: [100]`
  - `completed_boundary: 100`
  - `planned_maximum_episodes: 9000`
  - `rung_count: 1`
  - `rung_range: [100, 100]`
  - `formal: false`
  - four arms
  - authenticated checkpoint/rung digests
  - plan, renderer, and root digests
  - `result_3000_sha256: null`

Manifest: [FIGURE-MANIFEST.json](/home/sat/mcrl-v023-figure-dryrun-20260908/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z/FIGURE-MANIFEST.json)

### Figure tests

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/sat/modqn-paper-exploration/.venv/lib/python3.13/site-packages:/home/sat/mcrl-v023-review-stagec/src \
TMPDIR=/home/sat/mcrl-v023-review-stagec/.tmp \
MPLCONFIGDIR=/home/sat/mcrl-v023-figure-dryrun-20260908/.mplconfig \
/home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q -p no:cacheprovider \
.scratch/multi-catfish-v023-ch5-figure-pipeline
```

Result: exit `0`; 18 displayed test items passed (`[100%]`). Stderr was empty.

Final repository state:

```text
## review/stagec-r3
```

No repository edits or commits were made.