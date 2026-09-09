# Controller finding — the cross-gain repair landed, and its own diagnostic weakens my hypothesis
Recorded 2026-09-09. `PILOT_NOT_CLAIM`.

## What was repaired
The pairwise cross-gain terms now reach the interaction head as an ordered block of up to 32 directed pairs, canonically sorted by source and target beam key, with the summed magnitude of any omitted pair carried as an explicit residual so nothing is lost silently. The existing scalar fields are untouched, so old receipts remain comparable. Schema versions were bumped and shard loading now reports the expected and actual version triplets instead of a bare error.

The acceptance test T2 was rewritten to the specification the sealed amendment actually gave. It constructs a pair that is identical in **every** scalar feature, including the forbidden `interference_summary`, whose exact objective deltas have opposite signs. With the pair block present the head predicts opposite signs; with the block emptied the two canonical payloads are asserted **byte-identical**, so no model whatsoever can separate them. That is an impossibility proof rather than an observation that one model failed.

## The result that does not support my hypothesis
A five-fold ridge diagnostic on all 180 existing coalition rows, with the exact interaction as the response:

| encoder inputs | held-out R² |
|---|---:|
| old scalar features only | **0.6519** |
| old scalars plus the ordered pair block | **0.6406** |

Adding the pair block **does not improve** the fit; it is 1.13 percentage points worse.

I have said all day that the collapsed features were why the head could not see the mechanism. On this corpus that is **not** demonstrated. The old scalars are far from uninformative: a linear model explains about 65 % of held-out variance from them alone.

## Both results are true and they do not conflict
T2 proves the old representation admits a **collision**: two physically distinct cases with opposite-signed targets that it cannot distinguish. That is a proof of insufficiency, and it stands.

The ridge diagnostic says that on **these 180 rows** such collisions are not frequent enough to cost linear predictive power. And those 180 rows are **all of coalition size two**, carrying between 2 and 12 cross-gain pairs each. Pairwise structure is exactly what one would expect to matter at three members and above, and the corpus contains none.

So the honest reading is: the repair is necessary and correct, but it has not yet been shown to be sufficient or even helpful, and it cannot be until a corpus exists that contains the sizes where the structure bites.

## Consequence for priority
I had ranked feature collapse as the first defect. The evidence now ranks **corpus coverage first and features second**. Repairing the features while the corpus remains size-two-only would, on this measurement, change nothing.

The corpus regeneration is therefore the critical path, and it must deliver both the missing sizes and a much larger row count: the interaction component has 180 rows against 176,223 for the per-user components, a ratio near one to a thousand.

## Standing
No threshold, sign, seed, horizon, price, service guard or acceptance rule changed. Nothing here may enter the paper.
