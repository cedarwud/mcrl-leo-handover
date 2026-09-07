# Prompt templates for the next controller steps (usable from the server session)

Each file is a complete prompt. Fill the `<<…>>` fields, then dispatch:
- astra (read-only adjudication): `codex exec --model gpt-6-astra --config 'model_reasoning_effort="ultra"' --sandbox read-only --output-last-message <out.md> "$(cat <prompt>)"` (ultra only for the science-level gates named below; `high` otherwise).
- codex implementation: `codex exec --model gpt-5.6-sol --config 'model_reasoning_effort="high"' --sandbox workspace-write --output-last-message <out.md> "$(cat <prompt>)"`.
- Claude operator: Agent tool (general-purpose, opus) with the prompt as the task.
Always launch CLIs detached (`setsid nohup … </dev/null > log 2>&1; echo CODEX_EXIT=$? >> log`) and wait with Monitor.

| file | when | model |
|---|---|---|
| `astra-ultra-f1-r2-adjudication.md` | F1 r2 receipt exists (`/home/sat/mcrl-v023-c3-contingency-f1-20260907-r2/receipt.json`) | gpt-6-astra **ultra** |
| `astra-ultra-stagea-go-check.md` | V2-synthetic rerun is clean end-to-end after fix pass 5 | gpt-6-astra **ultra** |
| `operator-chunking-server-acceptance.md` | stage-C chunking implementation verified + committed | Claude operator (opus) |
| `operator-early-baseline-start.md` | addendum + stage-C code sealed, acceptance passed, astra check green | Claude operator (opus) |
