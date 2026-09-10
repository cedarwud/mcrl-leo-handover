# Where the EE actually lives — the layer map, after today's deflations

**2026-09-10 10:20 UTC.** Every figure carries reference / information class / estimand /
numerator. A figure that cannot carry all four is not listed.

## The map

| layer | size | reference | information | numerator | owned by a learned route? |
|---|---:|---|---|---|---|
| carrier incumbent -> one-shot per-user best response | **`~+400%`** | carrier incumbent | nominal, exact surplus | pooled EE | **No.** Head-independent argmax |
| one-shot -> converged unilateral fixed point | remainder to `+664%` (`SEALED`) / `+451%` (`MARGIN_Q`) | carrier incumbent | nominal | pooled EE | **No.** 45-65 s of search |
| fixed point -> bounded joint optimum | **`+0.899%`** (8 anchors) / **`+1.29%`** (20 anchors) | **correctly-paired unilateral fixed point** | nominal, strict clearance | pooled **demand-capped** | **C3's natural home** |
| fixed assignment, control law (power/mode) | **`+1.93%`** under corrected `STRICT`; `+82.78%` under defective `SEALED` | declared control law | **non-causal, best-known search** | demand-capped | **No route** |
| route 2 (persistence) | **no EE measurement of any kind** | — | — | — | C2, and v1.9 §5 declares its set-level marginal zero by construction |

## What changed today in this map

**The control-law pillar deflated.** It was quoted at `+119%` / `+134%` on the capacity
numerator. Under the demand cap it is **`+1.93%`** on the corrected `STRICT` rule. The
`+82.78%` figure belongs to `SEALED`, the **defective** provisioning rule under which
**0 of 800** user-anchors attain the target, so the cap binds nothing. That number describes
a broken regime, not available headroom.

`SWEEP-fable` predicted this before `CTRLCAP` reported: *"STRICT demand-capped gain in the
low single digits or less; SEALED larger because 0/800 attained."* Both halves correct. That
audit predicted an unrun measurement, which is the strongest evidence of its reliability
available.

## The consequence for the claim

Two of the three large numbers that appeared to sit outside the learned routes are now gone:
the multi-start `9.87%` was an order statistic under the defective rule, and the control law
is `+1.93%` once corrected and capped. **The one large thing that remains is the per-user
best-response step**, and it is reached by a plain exact-surplus argmax with no head at all.

So the question the three routes must answer is **not** "does this system have headroom". It
is: **after the head-independent best-response step, is there room that belongs to learning?**

The only measurement of that question in existence is
`FULL - ALL_NEUTRAL_CONTROL = -0.01745324091886997`
*ref: `ALL_NEUTRAL_CONTROL` · info: as-run panel smoke · estimand: relative pooled-EE marginal
· numerator: pooled EE* — identical under both provisioning rules, and **negative**. It was
measured on the surrogate corpus with the defective 12-effective-dimension feature schema, so
it is not final; but it is the only reading of the actual question that exists.

## What is running to change that

| job | question | why it can settle something alone |
|---|---|---|
| `SCHEMA2` | a repaired Q1 schema: elevation added, dead slots repaired, effective dimension recorded | `C1REAL`'s "informational ceiling" verdict is confounded with the defect |
| `C2REAL` | is the declared C2 target learnable at all | if not, route 2 is finished as declared, with no corpus, no panel, no EE run |
| `C3REAL` (queued) | same, for the residual head | same |
| `EXACTGEN2` | exact-path corpus, physics serialised separately from the feature view | needed under every branch, and the separation stops a feature change forcing a regeneration |
| `OBJMISMATCH` | are the certified endpoints locally optimal under the reported objective | independent half of the residual-sign question |

**None of these needs `D1` decided first**, and none needs the others.
