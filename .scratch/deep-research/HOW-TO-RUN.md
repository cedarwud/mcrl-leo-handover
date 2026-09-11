# How to run this — three separate conversations, two pastes each

**Three conversations, not one.** DR-1, DR-2 and DR-3 interrogate three different
literatures; mixing them in one thread makes every answer shallower and lets the model
carry one topic's assumptions into another.

Everything you need is in `ready-to-paste/`. Nothing else gets pasted.

## Conversation 1 — the architecture question (run this first)

| | paste | mode |
|---|---|---|
| round 1 | `ready-to-paste/PASTE-DR-1-RATIO-OBJECTIVE-RL.md` | **Deep Research** |
| round 2 | `ready-to-paste/PASTE-ASK-1-RATIO-OBJECTIVE-RL.md` | **normal chat, same conversation** |

## Conversation 2 — the physics question

| | paste | mode |
|---|---|---|
| round 1 | `ready-to-paste/PASTE-DR-2-LEO-HANDOVER-PHYSICS-PROVENANCE.md` | **Deep Research** |
| round 2 | `ready-to-paste/PASTE-ASK-2-LEO-HANDOVER-PHYSICS-PROVENANCE.md` | **normal chat, same conversation** |

## Conversation 3 — the contribution question

| | paste | mode |
|---|---|---|
| round 1 | `ready-to-paste/PASTE-DR-3-COMPETITIVE-LANDSCAPE.md` | **Deep Research** |
| round 2 | `ready-to-paste/PASTE-ASK-3-COMPETITIVE-LANDSCAPE.md` | **normal chat, same conversation** |

That is the whole procedure. Six pastes, three threads.

## Why round 2 is short

The `PASTE-DR-*` files already contain the context ledger, so by round 2 the conversation
holds both the ledger and the model's own research report. `PASTE-ASK-*` therefore only
carries the decision to be made.

## The source files

`00-EVIDENCE-LEDGER.md` and `10-FOLLOWUP-REASONING-PROMPTS.md` are the sources the
`ready-to-paste/` files were built from. **You never paste those two directly** — edit them
and rebuild if the evidence changes.

Rebuild after editing:

```
cd .scratch/deep-research
for n in 1 2 3; do f=$(ls DR-$n-*.md); \
  { cat 00-EVIDENCE-LEDGER.md; printf '\n\n---\n\n'; cat "$f"; } \
  > "ready-to-paste/PASTE-DR-$n-$(echo $f | sed "s/^DR-$n-//")"; done
```

(The ledger header and the per-file "optional context" lines are then trimmed by hand, or
re-run the same edit that produced the current files.)

## If only one can be run

**Conversation 1.** It decides what gets built, and it is the one where two independent
cross-model reviews converged on a recommendation without a citation between them.

## Order note

Round 2 of a conversation is worth much more after its round 1 has actually returned.
Do not paste `PASTE-ASK-n` before the Deep Research report for that thread is complete.
