# V0.19 normalized learned-Q3 seed census

Status: `FROZEN_BEFORE_OUTCOME`.

Frozen allocation:

- TRAIN worlds: `2026120701`, `2026120702`, `2026120703`, `2026120704`
- VALIDATION worlds: `2026120705`, `2026120706`, `2026120707`
- learner initialization seeds: `2026120711`, `2026120712`, `2026120713`
- row-schedule seeds: `2026120721`, `2026120722`, `2026120723`
- frozen source lineages remain: `2026092101`, `2026092102`, `2026092103`

On 2026-09-04 (Asia/Taipei), the proposed values will be searched before any
V0.19 learned-Q3 source or learner outcome is opened.

Local repository census (executed before draft freeze):

```text
rg -n --hidden -g '!.git/**' '202612070[1-7]|202612071[1-3]|202612072[1-3]' .
exit=1; stdout empty
```

The operative local search excluded the current V0.19 lane so that this draft's
self-references could not create a false collision:

```text
rg -n --hidden -g '!.git/**' \
  -g '!.scratch/multi-catfish-v019-relational-zr-normalized/**' \
  '202612070[1-7]|202612071[1-3]|202612072[1-3]' .
exit=1; stdout empty
```

Ubuntu-server census across `/home/sat/mcrl-*` textual source and receipt
files (executed before any V0.19 fresh source harvest):

```text
grep -R -n -E --exclude-dir=.git --include='*.md' --include='*.json' \
  --include='*.py' --include='*.sh' \
  '202612070[1-7]|202612071[1-3]|202612072[1-3]' /home/sat/mcrl-*
exit=1; stdout empty
```

Interpretation: no prior outcome-bearing or independent textual occurrence was
found in either census. The searches must be repeated after syncing the final
code/contract into its isolated server checkout and before opening any fresh
outcome. This frozen census authorizes only the declared source gate; it
authorizes no TEST access, episode training, physical EE claim, or 9000-episode
run.
