# Rejected V0.15-R contract R1 receipt

Status: `REJECTED_BEFORE_SOURCE_ACCESS`

The preserved file `REJECTED-PREOUTCOME-LAYOUT-R1.md` has SHA-256
`6d526cd52df9c42341ac54b77770cee64a112667dad16b9c3897651a116568e4`.

R1 placed the complete 287-dimensional V0.14 state before the three new
action-aligned blocks while also requiring the unchanged V0.14 ActionSet
scorer to interpret the first `13 * 28` coordinates as local features and the
last seven as global features. Those requirements are incompatible: the old
seven globals would be parsed as local inputs and the last seven power-gap
coordinates as globals.

No V0.15-R TRAIN or VALIDATION source world, learner, episode, or TEST split
was opened under R1. R2 changes only the state-vector ordering to preserve the
feature-major scorer contract. It does not change a feature formula, target,
seed, threshold, update count, or acceptance criterion.
