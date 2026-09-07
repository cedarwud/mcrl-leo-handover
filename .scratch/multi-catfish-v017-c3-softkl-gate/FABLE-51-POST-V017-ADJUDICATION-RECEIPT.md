# Fable 5.1 post-V0.17 structural adjudication receipt

Status: REVIEW RECEIPT, NOT AUTHORITY, NOT A RUN CONTRACT.

Date: 2026-09-04 (Asia/Taipei)

Invocation family:

```text
claude -p "<bounded prompt>" --model fable --effort max \
  --output-format json --dangerously-skip-permissions
```

## Transport history

- A trivial health check completed as `FABLE_READY` using canonical model
  `claude-fable-5-1`.
- Three prompts that asked the model to read local evidence timed out before
  inference with zero input and output tokens. They are operational failures,
  not scientific judgments.
- A decision-only prompt with verified facts inlined completed successfully.

## Successful decision-only response

- Claude session: `b6bec7fb-52e7-4d87-9be9-5f596fd8d322`
- Request UUID: `9250c2d7-f735-4a74-810c-d107ab5045a8`
- Result: `GO_ANALYTIC_C3_GATE`

The first response returned only the required route token. A follow-up in the
same session asked whether this meant a permanent analytic deployment head or a
diagnostic gate before a learned relational Q3.

## Successful clarification

- Claude session: `b6bec7fb-52e7-4d87-9be9-5f596fd8d322`
- Request UUID: `017f8b13-9563-450b-bd92-60f1a703159f`
- Final token: `ANALYTIC_DIAGNOSTIC_THEN_RELATIONAL`

Fable's clarified judgment was:

1. A permanent analytic Q3 violates the invariant that Q3 is a learned Q
   network.
2. A parameter-free nominal decoder may be used only as a source-side
   identifiability diagnostic. It must never enter the deployment path.
3. If that diagnostic passes, exactly one victim-relational learned Q3 attempt
   may follow using the same permitted predecision variables and unchanged ZR
   algebra.
4. Exact causal compatibility must match the oracle compatibility for every
   legal action with zero tolerance.
5. Any diagnostic or learner-gate failure must structurally stop this C3 route;
   no tuning, extra features, target replacement, or second relational variant.

## Root adjudication of one proposed detail

Fable proposed evaluating the analytic diagnostic on the same four TRAIN worlds
whose V0.13 oracle outcomes are already known. That detail is not adopted: the
decoder and route were designed after those outcomes were opened, so those
worlds cannot provide a clean pre-outcome direction screen. The executable gate
must use newly frozen TRAIN worlds and seeds, with its contract hashed before
outcomes are opened.

## Combined fresh-gate follow-up

- Claude session: `b6bec7fb-52e7-4d87-9be9-5f596fd8d322`
- Request UUID: `770b0eb7-a7ce-4beb-9a09-2c20b43a933e`
- Result: `PATCH_COMBINED_FRESH_GATE`

Fable agreed that a new-world three-arm gate (`BASE`, `EXACT_ZR`,
`NOMINAL_ZR`) is cleaner and that the exact arm is needed as a positive control
in the learned-Q2 context. It required three patches now reflected in the draft
contract:

1. replace literal zero service loss by a preregistered noninferiority margin;
2. distinguish exact-target failure from nominal-observability failure and
   forbid seed/lineage replacement after either;
3. make exact causal-compatibility proof a prerequisite before arms run and
   freeze any later learner to the nominal decoder's input set.
