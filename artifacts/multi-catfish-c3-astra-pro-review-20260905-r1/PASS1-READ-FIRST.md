# Pass 1 neutral entry — reconstruct before reading prior conclusions

This package concerns a three-head, one-action reinforcement-learning method for LEO multi-beam handover. The fixed design boundary is:

- exactly three Q functions and three training-time Catfish source mechanisms;
- one shared native safe mask;
- one unweighted deployment score `Q1 + Q2 + Q3` and one Main action;
- one final ratio-of-sums energy-efficiency objective;
- no deployment coordinator, auction, vote, joint decoder, or post-training override.

Do not open `START-HERE.md`, `CROSS-MODEL-STATE.md`, or reviewer files `evidence/01-*`, `evidence/08-*`, `evidence/10-*`, and `evidence/11-*` during pass 1. They contain interpretations that can anchor the review.

For pass 1, use only:

1. `EVIDENCE-MAP.md` as a file locator, ignoring its status prose where possible;
2. raw JSON files `evidence/02-*` through `evidence/07-*` and, when present, `evidence/09-*`;
3. current gate contracts `contracts/02-*` and `contracts/03-*`;
4. source files needed to reconstruct a concrete formula, action, or leakage claim;
5. `SOURCE-NOTES.md` for the limits of the copied code.

Before pass 2, record a provisional causal graph, evidence ceiling, discrepancy list, and decision. In pass 2, read the excluded interpretation files and explicitly identify agreements, disagreements, and findings absent from all prior reviews. Prior confident wording is not authority.

