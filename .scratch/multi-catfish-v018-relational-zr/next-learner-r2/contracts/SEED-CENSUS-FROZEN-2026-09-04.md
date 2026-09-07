# V0.18 learned-Q3 frozen seed census

Status: `FROZEN_BEFORE_OUTCOME`.

Frozen allocation:

- TRAIN worlds: `2026120501`, `2026120502`, `2026120503`, `2026120504`
- VALIDATION worlds: `2026120505`, `2026120506`, `2026120507`
- learner initialization seeds: `2026120511`, `2026120512`, `2026120513`
- frozen source lineages remain: `2026092101`, `2026092102`, `2026092103`

On 2026-09-04 (Asia/Taipei), the exact frozen values were searched before
any V0.18 learned-Q3 source or learner outcome was opened.

Local repository census:

```text
rg -n --hidden -g '!.git/**' '202612050[1-7]|202612051[1-3]' .
exit=1; stdout empty
```

Immediately before freeze, the search was repeated while excluding the
current pre-registration directory and its provisional web-agent copy:

```text
rg -n --hidden -g '!.git/**' \
  -g '!.scratch/multi-catfish-v018-relational-zr/next-learner-r2/**' \
  -g '!artifacts/multi-catfish-v018-web-agent-package-20260904-r1/**' \
  '202612050[1-7]|202612051[1-3]' .
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

The repeated Ubuntu-server census found only the already copied
pre-registration, census, and mock-test self-references under
`/home/sat/mcrl-v018-learned-q3-smoke-20260904-r1/`. Excluding that known
pre-outcome checkout, no occurrence was found in any other `/home/sat/mcrl-*`
root:

```text
grep -R -n -E --exclude-dir=.git --exclude-dir=.venv \
  --include='*.md' --include='*.json' --include='*.py' --include='*.sh' \
  '202612050[1-7]|202612051[1-3]' /home/sat/mcrl-* 2>/dev/null \
  | grep -v '^/home/sat/mcrl-v018-learned-q3-smoke-20260904-r1/'
exit=1; stdout empty
```

Interpretation: no prior outcome-bearing or independent textual occurrence was
found in either repeated census. These values are frozen with the learned-Q3
contract and code manifest. This receipt authorizes no TEST access, episode
training, physical EE claim, or 9000-episode run.
