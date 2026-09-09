# Seal integrity check (Claude Sonnet 5, mechanical): verify every sealed artefact and produce the authority table

You are running headless. Work in `/home/sat/mcrl-hub-copy`. For every file under `.scratch/multi-catfish-v025-physics-successor/` and `.scratch/multi-catfish-v023-controller-handoff-20260907/` (and their subdirectories) that has a `.sha256` sidecar, or whose name contains DECLARATION, AMENDMENT, ERRATUM, CONTRACT, LADDER, DECISION or SEAL:
1. recompute the sha256 and compare with the sidecar (report MATCH / MISMATCH / NO-SIDECAR);
2. record the file's mode as recorded in git (read-only intent) and its size and last-modified date;
3. build one table ordered by date: artefact, version, sha256 (first 16), sidecar status, what it supersedes or amends, and one line of what it fixes;
4. list, separately: any sealed artefact modified after its sidecar was written; any amendment that references a sha256 that does not match the current file; any decision file that contradicts a later one (compare only the explicit numbered items with the same subject, and quote both).
Print the table and the three lists as your final message. Do not modify any file. Do not summarise beyond what the files say.
