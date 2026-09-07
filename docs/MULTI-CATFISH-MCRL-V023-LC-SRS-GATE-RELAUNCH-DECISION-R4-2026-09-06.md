# Multi-Catfish MCRL V0.23 LC-SRS gate relaunch decision R4

Date: 2026-09-06  
Status: **R4 AUTHORIZED ONLY AFTER ISOLATED WORLD REPLAY AND RESEAL**

## 1. R3 disposition

R3 is an invalid execution receipt, not a scientific C3 outcome.  TRAIN world
`2026121705` completed the source stage, but world `2026121706` stopped inside
`CoalitionResidualC3Result.verify()` before any learner fit or composition
result was produced.  The R3 checkout, logs, `SOURCE_PASS`, and `FAILED` marker
must be retained and must not be resumed or interpreted as negative LC-SRS
evidence.

The isolated unchanged-code replay reproduced the failure with

```text
lhs       = 0x1.d4cafd2191000p+22
rhs       = 0x1.d4cafd2192000p+22
residual  = -0x1.0000000000000p-18 bit
tolerance = 0x1.d4cafd2192000p-20 bit
```

The absolute residual is `3.814697265625e-06` bit.  It is an IEEE-754
roundoff residue from cancellation of large physical delta-domain terms, not
a material failure of the coalition bookkeeping identity.

## 2. Root cause and bounded repair

The R3 verifier scaled its roundoff tolerance only from the two small final
identity sides.  That scale omits the larger rate-delta and energy-priced
intermediate operands that are actually rounded before they cancel.

R4 retains the existing coefficient `1024 * eps` and changes only the scale
supplied to it.  The scale is the finite sum of the absolute delta-domain,
energy-priced, and derived identity operands used to form the two sides.  The
large common reference totals are excluded because they cancel before the
identity is formed.  Every stored component is still independently
recomputed and checked before this final roundoff guard, so material field
corruption remains fail-closed.

This is a numerical-integrity repair.  It does **not** change the LC-SRS
teacher target, coalition, interaction allocation, Q3 values, multiplier,
lambda, kappa, worlds, draws, source selection, learner, loss, checkpoint
lineage, composition rule, service guard, or acceptance thresholds.

## 3. Required prelaunch evidence

R4 may proceed only after all of the following hold:

1. the deterministic physical-scale cancellation regression is red under the
   R3 guard and green under the R4 guard;
2. forged material component values still fail closed;
3. the complete focused W181--W205 suite passes;
4. 10,000 deterministic physical-scale valid identities produce no false
   failures;
5. `PREFLIGHT-MANIFEST.json` and its digest bind this decision, the exact R4
   implementation, and the exact tests, and preflight passes locally and on
   the Ubuntu server; and
6. a fresh isolated replay of TRAIN world `2026121706`, with the scientific
   inputs unchanged from R3, completes its source artifact and verifier.

Items 1--5 authorize only the isolated replay.  The full eight-world Gate may
launch only after item 6 passes.  If the replay fails, the controller must
stop and classify the new failure before any full rerun.

## 4. R4 execution boundary

The isolated replay and any later full Gate must use fresh server roots and
fresh tmux names containing `20260906-r4`; neither may reuse an R3 output.
The full Gate retains the frozen eight TRAIN worlds
`2026121705--2026121712`, three student seeds, 32 matched draws, source
parallelism 2, fit parallelism 4, composition parallelism 2, and CPU device.

R4 remains an offline C3 source-to-learner/composition development gate.  It
does not authorize TEST, episode-policy training, efficacy claims, or any
change to C1 or C2.  A Gate token is development evidence, not policy efficacy.
