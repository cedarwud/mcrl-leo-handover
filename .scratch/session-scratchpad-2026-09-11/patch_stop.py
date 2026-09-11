"""Parameterise the EXACT93 stopping analysis by seed index; nothing else changes."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="ascii")


def replace_once(old: str, new: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"patch point matched {count} times: {old[:60]!r}")
    text = text.replace(old, new)


replace_once(
    '''and the objective component is unaffected.
"""''',
    '''and the objective component is unaffected.

SEEDPAR copy (2026-09-11): identical rule, tolerances, metrics and objective.
Only two things differ from the EXACT93 original: ``--seed-index`` selects the
declared ``V025_LEARNER/seed/{i}`` domain (default 1, the original's value),
and the runner module used for ``load_corpus`` is the byte-identical v2 copy in
the SEEDPAR workspace.
"""''',
)
replace_once(
    '''WORKSPACE = Path("/home/sat/mcrl-v025-exact93-ws")
RUNNER = WORKSPACE / "scripts/run_stagec_training_v2.py"
CORPUS = WORKSPACE / "artifacts/exact-label-corpus-93-20260910"''',
    '''WORKSPACE = Path("/home/sat/mcrl-v025-seedpar-ws")
RUNNER = WORKSPACE / "scripts/run_stagec_training_v2.py"
CORPUS = Path("/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910")''',
)
replace_once(
    '''SEED_DOMAIN = "V025_LEARNER/seed/1"
''',
    '''SEED_DOMAIN = "V025_LEARNER/seed/1"  # default; overridden by --seed-index
''',
)
replace_once(
    '''    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
''',
    '''    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed-index", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.seed_index <= 16:
        raise SystemExit("--seed-index must be in 1..16")
    global SEED_DOMAIN
    SEED_DOMAIN = f"V025_LEARNER/seed/{args.seed_index}"
''',
)
path.write_text(text, encoding="ascii")
print("patched", path)
