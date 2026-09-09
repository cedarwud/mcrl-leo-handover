You are advising on experiment design. Answer from reasoning and from any code or documents you choose to read in this workspace; no run is authorised and nothing sealed may be modified.

`DIAGNOSTIC_NOT_CLAIM`. This is a design consultation. Do not change any constant, threshold, sign, seed, horizon, price, guard or acceptance rule, and do not modify sealed artefacts, frozen manifests or the contract.

# The system

A LEO satellite handover simulator. At each decision anchor a bounded set-level selector chooses a joint change to several users' beam associations. The pipeline is: an iterated unilateral best-response search runs to a certified fixed point; a hand-written rule set generates a bounded catalogue of joint perturbations **around that fixed point**, with the fixed point itself retained as a fallback; the catalogue is ranked and the best is taken. Three learned components supply the quantities used in that ranking. The headline metric is pooled energy efficiency, total bits over total joules.

# The owner's stated acceptance requirement

Each of the three components must individually improve pooled energy efficiency over a control. Adding two or three components will interact, so the magnitudes will not simply add, but every subset must remain positive, and the ordering must hold:

> FULL  >  (any two components)  >  control

# What the sealed contract currently provides

The primary experiment declares six arms: FULL; three leave-one-out arms in which one named route is trained on a **neutral source** while all routes are retained, updated and deployed; an all-neutral control; and an external geometry-only baseline. The panel is six arms by twelve learner seeds by two worlds per training date over about 160 dates. A relative margin of +0.5 % with a bootstrap lower bound is the declared materiality threshold. There is a separate contract clause requiring FULL to beat a unilateral-equipped comparator, not only the leave-one-out arms.

# Facts you should weigh

- Every arm shares the same non-learned unilateral prefix, which is worth about **+442 %** in pooled efficiency over the geometry-only baseline. The entire span between the certified unilateral fixed point and an exhaustive bounded joint search is about **+0.51 %** under corrected physics.
- A leave-one-out arm can select a **worse** coalition than the fallback, because ranking uses predicted scores. One pilot measured a leave-one-out gap of **+15.6 %**, far larger than the joint-search span.
- The score is currently a sum of per-user deviation terms plus an interaction correction. At coalition size 100 those are **+480.1** and **−440.1**, producing **+40.0** — a roughly tenfold cancellation.
- The source paper the three-component design derives from uses **two** ablation styles: full-minus-one, and single-component-only against a basic baseline. It prescribes no margin, and its weakest component contributes about **0.6 %**.

# What I want from you

Do not assume any particular design is correct, including any you infer I favour. Answer these:

1. **Is the owner's requirement well-posed as stated?** If "individually improve over a control" is ambiguous between more than one experiment, name each reading and say which is the scientifically meaningful one and why.
2. **Which arms would actually test it?** Say precisely what should be run and what each arm's reference should be. If the existing six arms already answer it, say so and explain how. If arms must be added, name them and say what they hold fixed.
3. **What could make the result uninterpretable?** In particular: a large full-minus-one gap that comes from the leave-one-out arm degenerating rather than from the component adding value; the shared prefix making the "beats control" half trivially true for every arm; multiplicity across three simultaneous requirements; and any confound you find that I have not listed.
4. **Is there a cheaper design that answers the same question?** The panel already costs six arms by twelve seeds; adding arms is a large increase. Consider whether some arms can share computation, whether fewer seeds suffice for an ordering test than for a margin test, and whether any arm is redundant.
5. **What would you refuse to conclude** even if every ordering held with a comfortable margin?

Be blunt and specific. If you think the requirement should be changed rather than tested as stated, say so and give the reason — but distinguish clearly between "this is not measurable as stated" and "I would have designed it differently".

Write your answer as a single self-contained note and print it in full as your final message. Lead with a one-paragraph answer to question 1.
