"""Apply the single v3 capability (--seed-indices) to a byte copy of runner v2."""
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
    '''carries no scientific authority.
"""''',
    '''carries no scientific authority.

v3 (SEEDPAR 2026-09-11) adds exactly one capability to runner v2:
``--seed-indices`` selects a subset of the same declared
``V025_LEARNER/seed/{1..N}`` list so that seeds can run in separate processes.
Each selected seed keeps its identity and derivation; the fixture gate still
runs on declared seed index 1; schedule, architecture, arms, corpus contract,
checkpoint format and cadence are unchanged.
"""''',
)

replace_once(
    '''        help="number of V025_LEARNER/seed/{1..N} domains; v1.1 requires 16",
    )
    return parser''',
    '''        help="number of V025_LEARNER/seed/{1..N} domains; v1.1 requires 16",
    )
    parser.add_argument(
        "--seed-indices", default=None,
        help=(
            "v3: comma-separated, strictly increasing 1-based indices into the declared "
            "V025_LEARNER/seed/{1..N} list to train in this process (e.g. 2,3); "
            "default trains every declared seed, exactly as v2"
        ),
    )
    return parser''',
)

replace_once(
    '''    if args.seeds <= 0:
        parser.error("--seeds must be positive")
''',
    '''    if args.seeds <= 0:
        parser.error("--seeds must be positive")
    if args.seed_indices is None:
        args.seed_index_list = tuple(range(1, args.seeds + 1))
    else:
        try:
            indices = tuple(int(part) for part in args.seed_indices.split(","))
        except ValueError:
            parser.error("--seed-indices must be comma-separated integers")
        if (
            not indices
            or list(indices) != sorted(set(indices))
            or indices[0] < 1
            or indices[-1] > args.seeds
        ):
            parser.error(f"--seed-indices must be strictly increasing values in 1..{args.seeds}")
        args.seed_index_list = indices
''',
)

replace_once(
    '''    seeds = tuple(seed_from_domain(f"V025_LEARNER/seed/{index}") for index in range(1, args.seeds + 1))
''',
    '''    seeds = tuple(seed_from_domain(f"V025_LEARNER/seed/{index}") for index in range(1, args.seeds + 1))
    trained_seeds = tuple(seeds[index - 1] for index in args.seed_index_list)
''',
)

replace_once(
    '''        "amendment_v1_1_seed_count": AMENDED_SEED_COUNT,
''',
    '''        "amendment_v1_1_seed_count": AMENDED_SEED_COUNT,
        "v3_seed_subset": {
            "seed_indices_trained": list(args.seed_index_list),
            "seed_list_trained": list(trained_seeds),
            "seed_domains_trained": [f"V025_LEARNER/seed/{index}" for index in args.seed_index_list],
            "fixture_gate_seed_index": 1,
            "note": (
                "seed_list/seed_domains/seed_count_actually_used above are the full declared "
                "list, as in v2; this process trains only seed_list_trained, each with its "
                "declared identity and derivation"
            ),
        },
''',
)

replace_once(
    '''    training = train_requested(
        batches, output, seeds, args.epochs, args.checkpoint_cadence,''',
    '''    training = train_requested(
        batches, output, trained_seeds, args.epochs, args.checkpoint_cadence,''',
)

path.write_text(text, encoding="ascii")
print("patched", path)
