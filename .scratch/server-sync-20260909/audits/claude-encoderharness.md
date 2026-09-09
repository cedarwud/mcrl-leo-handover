You are doing pure engineering plumbing on a critical path. Work in the current directory. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. **No training run and no policy run is authorised by this task.** You are building the ability to run one later, not running one. Change no constant, threshold, sign, seed, horizon, price, service guard or acceptance rule, and do not modify any sealed artefact or frozen manifest. Leave `PILOT_PRIMITIVE_SOURCE_FALLBACK` exactly as you find it.

# Why this exists

Two separate investigations are about to conclude that the per-user feature encoders in `src/mcrl/stagec_v025/state.py` are missing information their targets depend on. Whatever they recommend, the project will need to measure a repaired encoder against the current one under otherwise identical conditions. Today the encoder is effectively hardcoded through the row-building and training path, so that measurement would take hours of replumbing at exactly the moment it is most urgent.

Your job is to remove that delay in advance, **without committing to any particular repair**.

# Deliverables

**D1 — find the seam.** Trace, with `file:line` citations, every place the 16-scalar and 22-scalar feature vectors are constructed, their widths asserted, persisted, read back, and consumed by the scalar heads. Include the row builders, any serialization schema or width constant, the training entry points, and the evaluation arms. Produce a short map. If a width is baked into a serialized artefact schema, say so explicitly and name it — that is exactly the kind of thing that turns a one-line change into a day.

**D2 — introduce a named encoder-variant seam.** Add a mechanism by which the encoder in use is selected by an explicit named variant, defaulting to the **current production encoder with byte-identical output**. Requirements:
- the default path must produce rows byte-identical to today's; prove it with a test that builds rows both ways on real anchors and compares exact bytes;
- the variant name must be recorded in whatever provenance or manifest the rows already carry, so a row can never be silently misattributed to the wrong encoder;
- adding a variant must not require touching the training code, the evaluation arms, or any schema constant;
- feature width must be discovered from the variant, not assumed, everywhere it is currently assumed.

**D3 — register one throwaway proof variant.** Register a single variant named `IDENTITY_PLUS_ZERO` that appends one always-zero scalar to each vector. It is scientifically meaningless on purpose: it exists only to prove the seam works end to end without prejudging any real repair. Show that rows build, persist, read back and train-step under it, and that the width change propagates without any other edit.

**D4 — a comparison runner.** Provide one command that runs the existing training-and-evaluation pipeline twice, once per named encoder variant, over identical anchors, seeds and arms, and emits a side-by-side table. Demonstrate it on the **smallest** configuration that exercises every code path — one world, two anchors, one seed, a handful of epochs. That demonstration is a smoke test of the plumbing and must be labelled as such; it is not evidence about any encoder.

**D5** — state plainly what you did not do, and any place where the seam is still leaky.

# Rules

- Write tests first where practical; the byte-identity test in D2 is the one that matters most.
- Do not refactor beyond what the seam needs. A small, boring, reviewable change is the goal.
- If introducing the seam would require touching a sealed artefact or frozen manifest, STOP and report that instead of doing it.
- Report the exact commands you ran and their output.

Write `ENCODER-VARIANT-SEAM-2026-09-10.md` in this workspace root and print it in full as your final message, leading with one line: whether the seam is in place and whether default output is byte-identical.
