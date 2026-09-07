# Fable clean-room challenger lane

This directory contains copies from the separate Claude Fable 5.1
FABLE-CLEANROOM route of the parallel-design adjudication. The lane is now
integrated into the package's main START-HERE.md and CHATGPT-REVIEW-PROMPT.md;
there is no separate follow-up prompt.

Everything here is development evidence: six TRAIN worlds, oracle Q2 surfaces,
no learned Q2, no TEST, and no episode training. Nothing in this directory is
shared project authority.

## Reading order

1. FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md
2. oracle/stage1b-report.md
3. contracts/
4. census/census-report.md
5. audit/
6. receipt.json and RECEIPT-DIR-MANIFEST.sha256

The challenger runner/report source is copied under oracle/, and the census
scripts are copied under census/ so a reviewer can inspect the method. The two
Stage 1b result JSON files and the census result are exposed under the package
root's evidence/ directory.

RECEIPT-DIR-MANIFEST.sha256 is the preserved manifest for the complete original
challenger artifact, including large files not copied here. The root
MANIFEST.sha256 is the authoritative integrity manifest for this assembled
review package.

Important: the O-arm is the Fable lane's reading of OPS-3, not an outcome from
the current exact source/runtime/ee_axis_ops3_live.py adapter. Read
../INTEGRATION-VERIFICATION.md before using that number.
