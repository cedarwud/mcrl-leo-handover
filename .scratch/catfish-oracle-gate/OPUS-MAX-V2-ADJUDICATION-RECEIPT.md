# Opus Max v2 adjudication receipt

Date: 2026-08-26

Status: unavailable. No review prose was delivered, so no scientific or design
verdict is attributed to Opus Max from these attempts.

## Frozen review inputs

- `V2-RESULT-BRIEF-FOR-OPUS.md` SHA-256:
  `da0bec8fabe8ec9ebc317c3b5c65a66ddab94dcf8c44a45cc9a231c94f8bde77`
- `OPUS-MAX-V2-ADJUDICATION-PROMPT.md` SHA-256:
  `44caa6a3d3115042caf6d7ec1f444a1946e86a31bbfc0553232e07cd06d236a0`
- `state-only-confirmation-derived-v2.json` SHA-256:
  `742837883aec098c766fa5504e51ff5e3e9eb5bdee09de818059eeb1071e3cab`
- Requested route: Claude alias `opus`, canonical response metadata
  `claude-opus-5`, effort `max`.
- Browser disabled. The first attempt allowed only `Read` and `Grep`; the
  second attempt was self-contained and allowed no tools.

## Attempts

1. Session `91722489-7f56-4701-b5c3-e614dd955d3b` was interrupted after no
   user-visible response for more than four minutes. Its terminal receipt then
   reported `aborted_streaming`, 19 turns, 30 input tokens, 79,704 cache-create
   tokens, 898,870 cache-read tokens, 18,648 output tokens including 13,194
   thinking tokens, USD 1.712825, no web requests, and no permission denials.
   It stopped at a tool-use boundary and delivered no review prose.
2. Resume was unavailable because the first request used no session
   persistence.
3. A self-contained, no-tools attempt used only
   `V2-RESULT-BRIEF-FOR-OPUS.md`. Session
   `7b77ee47-4ae3-4e89-be12-c761b6282230` ended after 186,101 ms with
   `Request timed out`, zero input/output tokens, and zero cost.

The verified v2 numerical receipt and the separate local reviewer audit remain
valid evidence. They must stay distinct from a fresh Opus verdict.
