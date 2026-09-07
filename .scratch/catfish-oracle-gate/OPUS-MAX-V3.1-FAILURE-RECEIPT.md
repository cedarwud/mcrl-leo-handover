# Opus Max v3.1 failure-adjudication receipt

Date: 2026-08-26

Status: unavailable. No review prose was delivered, so no fresh scientific or
design verdict is attributed to Opus Max.

## Frozen review inputs

- `V3.1-FAILURE-BRIEF-FOR-OPUS.md` SHA-256:
  `3c5151c185c3f4275c6d78e106c270d53d907d49d54d3f7470c2ad8cc9d0c327`.
- `OPUS-MAX-V3.1-FAILURE-PROMPT.md` SHA-256:
  `7f794ae2df5444d2e6a2a00172a235ab916587521116098dd29db9b35e40db37`.
- Browser, code execution, edits, training, and subagents were forbidden.

## Attempts

1. The current `agy` wrapper rejected alias `opus` with effort `max` before a
   request was sent because that wrapper now accepts only low/medium/high.
2. Direct Claude CLI, model alias `opus`, effort `max`, plan/read-only mode:
   session `404824b7-3ebe-4c02-8bbf-7575b5da55bf` returned `Request timed out`
   after 178,789 ms with zero input, output, thinking, or cost.
3. Direct Claude CLI, explicit `claude-opus-4-6-thinking`, effort `max`,
   plan/read-only mode: session `a612616d-d62c-4042-9f3c-e6d9312a27ef`
   returned `Request timed out` after 179,376 ms with zero input, output,
   thinking, or cost.

The frozen v3.1 result, deterministic verifier, exploratory failure diagnosis,
and separate local reviewer remain the only new adjudication evidence. Earlier
completed Opus reviews are prior design evidence and must not be represented as
a fresh review of this held-out failure.
