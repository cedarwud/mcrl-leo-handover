### Internal Consistency Review: V2 Launch Bundle

#### 1. Hard-coded SHA-256 & Sidecars
- **Actual File Hashes:**
  - `V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md`: `e258bab0b56af919a95d9ac2340de1d29b6cbd5a4cd4107ec22d5511e8f687f9`
  - `V023-100E-MODEL-CONFIG.json`: `81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7`
  - `V023-100E-POST-R7-PROVIDER-CONFIG.json`: `24110f0365831bc4d8ec17f818a51024d9bbca962a4e7019721f54ef6ada9cba`
- Sidecars match `<sha>  <basename>\n` exactly.
- [`preflight_v023_100e_source_training.py:35,38,41`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py#L35-L41): All match.
- [`verify_v023_100e_source_training.py:56,59,62`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/verify_v023_100e_source_training.py#L56-L62): All match.
- [`sync_launch_v023_100e_source_training_server.sh:124-126`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L124-L126) (`expected` dict): All match.
- [`sync_launch_v023_100e_source_training_server.sh:51,53`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L51-L53): **DEFECTS**. Top-level variables contain stale hashes from before the V2 contract update.

#### 2. Server Paths
- All server paths (`r7_root`, `target_root`, `server_root` checkout, `output_root`, `tmux_session`) are consistent across contract, provider config, verifier `EXPECTED_PROVIDER_CONFIG`, and launcher guards.
- No stale references to `r1`, `d40-r4`, or `ops3-r4` exist (only referenced in negative regression assertions in tests).

#### 3. Schema Strings
- Preflight writes `multi-catfish-mcrl-v023-100e-source-training-preflight-v2` and input binding `...-input-binding`.
- Both verifier ([`verify_v023_100e_source_training.py:45,82`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/verify_v023_100e_source_training.py#L45-L82)) and launcher receipt validation ([`sync_launch_v023_100e_source_training_server.sh:362,386`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L362-L386)) expect identical schema strings.

#### 4. Launcher Startup Acknowledgement & Escaping
- Bounded wait loop ([`sync_launch_v023_100e_source_training_server.sh:509-516`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L509-L516)) checks both marker and tmux session across 24 iterations (120 s max) and dies on failure.
- Remote argv unpacking matches ssh argument list (12 args at line 348; 16 args at line 409).
- Heredoc f-string escaping: **DEFECT** on [`sync_launch_v023_100e_source_training_server.sh:476`](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L476). Inside `body = f'''...'''`, `+ "\n")` expands to a raw newline inside the generated python heredoc (`<<'PYSTART'`), causing `SyntaxError: unterminated string literal` when the controller executes Python. (Compare line 454 which correctly uses `+ "\\n")`).

#### 5. Launch Manifest & Frozen Pin
- Manifest lists all 13 required entries demanded by both launcher and verifier.
- Frozen pin matches manifest sha256 (`321528a44c3e6afc8f2c255d3f4ee2d41bd1aebedf42e4042b9c3b32a2b52262`).
- `build_v023_100e_launch_manifest.py --check` passes cleanly.

#### 6. Test Assertions
- `test_v023_100e_source_training_server.py` (15 tests) and `test_v023_one_epoch_provider_diagnostic.py` (4 tests) pass with current paths and tokens.

#### 7. Additional Checks
- No duplicate dict keys found.
- No dead variables found.
- Fixing the launcher defects below will require regenerating the manifest and frozen pin.

---

### Concrete Defects

1. **[.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh:51](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L51)**
   - **Defect**: Stale contract SHA-256 passed to remote preflight/controller checks (`611cc2fbfb2e7cb49bc07ae056f7329f39406abd6795c492826dddf845922b12`).
   - **Exact Fix**:
     ```bash
     expected_contract_sha256=e258bab0b56af919a95d9ac2340de1d29b6cbd5a4cd4107ec22d5511e8f687f9
     ```

2. **[.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh:53](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L53)**
   - **Defect**: Stale provider config SHA-256 passed to remote preflight/controller checks (`c925bb37533c010929550565dd22f728ccfe1b7a999673a0044857bc2f2dd967`).
   - **Exact Fix**:
     ```bash
     expected_provider_config_sha256=24110f0365831bc4d8ec17f818a51024d9bbca962a4e7019721f54ef6ada9cba
     ```

3. **[.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh:476](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh#L476)**
   - **Defect**: Single backslash in `+ "\n")` inside Python f-string expands to a raw newline inside the generated bash controller's embedded Python `PYSTART` script, causing an unhandled `SyntaxError: unterminated string literal` when writing the startup marker.
   - **Exact Fix**:
     ```bash
     data = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\\n").encode("ascii")
     ```

4. **[.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-LAUNCH-MANIFEST.sha256](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-LAUNCH-MANIFEST.sha256)** & **[V023-100E-LAUNCH-MANIFEST-FROZEN.sha256](file:///home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-LAUNCH-MANIFEST-FROZEN.sha256)**
   - **Defect**: Cascading drift. After applying fixes 1–3 to `sync_launch_v023_100e_source_training_server.sh`, the launch manifest and frozen pin will drift until rebuilt.
   - **Exact Fix**: Run `python3 .scratch/multi-catfish-v023-100e-screen-preoutcome-v2/build_v023_100e_launch_manifest.py --write`.

VERDICT: DEFECTS_FOUND
AGY_EXIT=0
MODIFIED_BY_AGY=no
