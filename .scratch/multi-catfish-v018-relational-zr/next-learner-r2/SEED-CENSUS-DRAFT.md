# V0.18 learned-Q3 candidate seed census (draft)

Status: `DRAFT_NOT_FROZEN_NO_OUTCOME_OPENED`.

Candidate allocation:

- TRAIN worlds: `2026120501`, `2026120502`, `2026120503`, `2026120504`
- VALIDATION worlds: `2026120505`, `2026120506`, `2026120507`
- learner initialization seeds: `2026120511`, `2026120512`, `2026120513`
- frozen source lineages remain: `2026092101`, `2026092102`, `2026092103`

On 2026-09-04 (Asia/Taipei), the exact candidate values were searched before
any V0.18 learned-Q3 source or learner outcome was opened.

Local repository census:

```text
rg -n --hidden -g '!.git/**' '202612050[1-7]|202612051[1-3]' .
exit=1; stdout empty
```

Ubuntu-server census across `/home/sat/mcrl-*` textual source and receipt
files:

```text
grep -R -n -E --exclude-dir=.git --include='*.md' --include='*.json' \
  --include='*.py' --include='*.sh' \
  '202612050[1-7]|202612051[1-3]' /home/sat/mcrl-*
exit=1; stdout empty
```

Interpretation: no prior textual occurrence was found in either census. These
values remain candidates until a complete learned-Q3 contract, run config, and
code manifest are frozen. This draft alone authorizes no source harvest,
learner update, TEST access, or episode training.
