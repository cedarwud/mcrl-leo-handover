**FIX_FIRST: 1 blocker, 3 majors, 0 minors.** Counts exclude fixed findings; L5/N1 describe one defect.

Read-only, offline audit. HEAD advanced concurrently from `cdf2dd5` to `28facda`; the three audited packages remained unchanged from `1e6310e`. No source edits, network or SSH; test writes stayed under the permitted TMPDIR.

References: **L** = successor-launch directory; **F** = factory-v3 Python file; **FT** = factory test; **O/M** = runner-directory orchestrator/model. Within L: **B** = binder, **G** = manifest builder, **C** = common, **P** = preflight, **Dg** = diagnostic, **W** = formal wrapper, **V** = verifier, **S** = sync shell, **T** = launch test. Filenames are those specified in the request.

| id | file:line | severity | finding | exact fix |
|---|---|---|---|---|
| 03 | F:451,772,821 | — | **FIXED.** Mandatory derived graph has 45 modules, including all four `lcsrs_c3` donors; exact manifest membership and loaded origins authenticated. | None. |
| 04 | F:532,545,555 | — | **FIXED.** Actual contract, sealed declaration, predecessor, PREREG and TLE identity authenticated. | None. |
| 08 | FT:107,384 | MAJOR | **PARTIAL.** Constants/worlds now come from producer authorities; learner fixture still obtains its expected closure from the consumer’s own graph function. | Independently derive fixture closure; test omitted transitive dependencies against that independent expectation. |
| L1 | B:184; G:59 | — | **FIXED.** Factory-owned closure; duplicate paths assigned once. | None. |
| L2 | C:337; O:319 | — | **FIXED.** Digests avoid token scanning; semantic fields are scanned; authenticated donor metadata exempted. | None. |
| L3 | B:290,366; C:325 | BLOCKER | **PARTIAL.** All eight placeholders receive dispositions, but three Stage-C bindings remain deferred despite the bundle existing. Any nonempty deferral reason passes. | Bind and authenticate Stage-C runner/verifier code manifests before diagnostic/Stage A; reject these deferrals at freeze/preflight. |
| L4 | P:274,304; W:140; V:394 | — | **FIXED.** Learner/r8 digest semantics aligned; wrapper invokes stock verified completion; reconstruction receives configuration digests. | None. |
| L5 | V:193,198,226,243 | MAJOR* | **PARTIAL.** Original non-formal/no-reconstruction bypasses closed; remaining authority gap is N1. | Apply N1. |
| L6 | C:241,252; G:66; S:150 | — | **FIXED** for missing coverage. All 246 paths covered once; synchronization is a documented superset, **not equality**. | Preserve necessary bundle additions; test exact expected union and correct the verification report’s equality claim. |
| L7 | P:131,178; S:171 | — | **FIXED.** Seven behavioural checks, finite timings and six identity comparisons gate tmux launch. | None. |
| A | B:62,83; T:100 | — | **FIXED.** Dirty flag excludes generated bundle outputs; clean-tree write/check regression passes. | None. |
| B | C:240; T:81 | — | **FIXED.** Closure ordering checked as strings. | None. |
| D | F:76; O:46; P:96 | — | **FIXED.** Formal identity set imported from factory; preflight invokes orchestrator authentication before update 0. | None; no duplicated hand-written formal 22-field list found. |
| E | O:319,345; F:799 | — | **FIXED.** Mandatory C3-named donor files no longer trigger semantic rejection. | None. |
| R1 | M:173; O:266,379,466 | MAJOR | **PARTIAL.** Non-formal identity branch added, but generic model still mandates formal seed and shared authentication still mandates budget 100. | Keep formal seed/budget restrictions at formal admission; validate explicitly non-formal configuration separately. |
| N1 | W:50; V:243; T:219,305 | MAJOR* | **NEW evidence:** passing positive test supplies preflight without launch-manifest/bindings hashes or output root. Verifier reconstructs successfully without authenticating those freeze authorities. | Require these fields, authenticate referenced launch manifest/execution bindings, and compare requested root before updates and during independent verification; add omission/substitution negatives. |

The three deferrals **must be resolved before Stage A, including its one-epoch diagnostic**, not merely before Stage C. Contract §6 lines 155–159, §9 lines 182–196, and the sealed declaration explicitly require this. Stage-C’s later bindings to produced Stage-A exports can wait; predetermined code/configuration cannot.

No file-level self-digest or reciprocal hash dependency found: binder excludes generated outputs, launch manifest excludes itself/sidecar, and output `COMPLETE` authenticates an external manifest. Git commit/tree plus dirty flag are recorded; current dirty state is true.

Diagnostic Dg:173–198 recomputes pair/gauge/total loss using saved pre-update Q2 weights and rejects post-update-weight substitution; export/reload and exact continuation follow. The launcher binds its receipt to preflight before creating tmux.

The exact requested pytest command, with `TMPDIR=/home/u24/papers/mcrl-leo-handover/.scratch/.tmp-astra`, returned **exit 0: 37 passed**—launch 15, factory 12, runner 10.

Both current manifest checks pass: Stage-A `8b020cd2…`, Stage-C `62180dbd…`. Contrary to the anticipated drift, Stage-A currently has **zero changed manifest members**. Its 258 payload paths cover all 246 closure paths; adding its external manifest/sidecar makes **260 synchronized files**. The three generated freeze inputs are still absent.

After fixes and r8 sealing, freeze in this order:

1. Stabilize checkout/HEAD; authenticate Stage-C code manifest/pin, scientific authority and attached review.
2. **Bind:** rederive learner manifest, provider config/sidecar, execution bindings/sidecar—including current git identity, r8 receipts and Stage-C code bindings.
3. **Manifest:** regenerate launch manifest/sidecar after those files exist; run both `--check` modes.
4. **Preflight:** synchronize authenticated inputs; create fresh server `PREFLIGHT-RECEIPT.json`/sidecar.
5. **Diagnostic:** regenerate scratch checkpoint and diagnostic receipt/sidecars; require behavioural and identity gates.
6. **Launch:** start formal wrapper, then independent verifier/sealer.

Any intervening code/authority change invalidates downstream derivations. Existing scientific declaration bytes remain sealed.

ASTRA_THIRD_AUDIT=1/3/0
ASTRA_STAGEA_LAUNCH=FIX_FIRST