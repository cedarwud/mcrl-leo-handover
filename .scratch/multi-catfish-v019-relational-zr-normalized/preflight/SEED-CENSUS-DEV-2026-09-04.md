# V0.19 normalized-Q3 preflight development-seed census

Status: `RECORDED_BEFORE_PREFLIGHT_OUTCOME`

This census reserves one development initialization seed and one independent
batch-schedule seed for the TRAIN-only preflight.  They are not the V0.18
formal learner-gate initialization identities (`2026120511`--`2026120513`)
and are not any V0.18 TRAIN/VALIDATION world identity.

Reserved development identities:

- initialization seed: `2026120491`
- schedule seed: `2026120492`

The local repository census was run before this file was written:

```text
command: rg -n --hidden -g '!.git/**' '(2026120491|2026120492)' .
exit: 1
stdout: empty (no matches)
```

This is a reservation census, not a claim about the server filesystem.  The
preflight runner rechecks the exact seed values from this contract before
opening any TRAIN source bytes.  It does not read VALIDATION or TEST to do so.

The formal V0.18 identities remain historical and are not reused as the
development learner seed.  No observed preflight result may change either
reserved value.

The learner also uses the predeclared source lineage `2026092101` only.  All
three lineages are authenticated first, but a single Q3 learner is never
trained across incompatible Q1/Q2 background bindings.
