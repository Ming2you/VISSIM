# Fixed-command network arms: static preparation

Three isolated experimental networks are prepared in `diagnostics/fixed_beta300v3_network_arms_v1`. Static validation is complete; **all three arms remain `run_ready=false`**. No VISSIM, COM, MPC, FZP scan, original-network edit, or runtime/config mutation was performed.

Subsequent read-only validation of the parent's saved original-network COM capture is recorded separately in `diagnostics/native_settings_validation.json/md`: 80 settings and nine product probabilities are exact. This closes the original RelFlow-default uncertainty, while modified-network native loading and vehicle eligibility remain unverified. The original v1 generated manifest and outputs were not changed. After preparation, the parent-authorized removal of unnecessary approval wording changed only the design MD input pin; its historical/current hashes are recorded in the new sidecar. The successful producer `--verify` result below predates that document change, and repeating it now correctly rejects that historical pin difference.

The background path inspection confirms that `#data#개포동 Test-bed.jpg` exists beside the original INPX but is absent beside all three copied INPX files. Its local 2D image reference is consequently unresolved in these packages. The separate absolute TRLAB Downloads PNG was already absent on this host. A separately versioned asset-complete package or explicitly recorded equivalent resolution is needed for 2D inspection. No visual or simulation effect has been inferred from static path checks alone.

| Arm | Only permitted network change | INPX SHA256 |
|---|---|---|
| `baseline` | None; original bytes copied | `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317` |
| `lcd10635_2000` | Connector 10635 `lnChgDist="1000"` to `"2000"`; exactly one byte differs | `660796ec04b2528ae05751b0fbbd1dc2b07ff4dfd52be53c6053d281cf7300ab` |
| `upstream1135` | Replace upstream routes 1123:2, 1124:1, 1125:1 with nine product routes; remove decision 1135 | `04b966aa54de28567e4c03548ed0bc734359f4f09ac282b7e8e9a40ed1cb6e3b` |

The manifest SHA256 is `18322b5ca49afe57b59baf271afdc8a3fc1cd850b711f2027afdedd656846030`. Its input pins include the original INPX, route audit and peer evidence, fixed-command design/profile, source action JSON/CSV, current runner/VBS/adapter, selected signal plan, generator, and all 42 referenced SIG files. Clock-cache code is outside this static preparation contract.

## Exact route transformation

New IDs 4, 5, 6 are absent from each original parent's sibling set and consistently correspond to old downstream 1135 routes 2, 3, 4. Six untouched sibling routes retain their complete original bytes.

| Parent route | Old weight / parent total | New 4 / 5 / 6 weights | New probabilities within parent |
|---|---|---|---|
| 1123:2 | 10 / 12 | 6 / 2 / 2 | 1/2, 1/6, 1/6 |
| 1124:1 | 6 / 8 | 3.6 / 1.2 / 1.2 | 9/20, 3/20, 3/20 |
| 1125:1 | 6 / 8 | 3.6 / 1.2 / 1.2 | 9/20, 3/20, 3/20 |

Each row preserves `P(parent turn) × (3/5, 1/5, 1/5)` exactly using rational arithmetic. Empty native `relFlow` is interpreted as weight 1 for this XML calculation; native COM confirmation remains required. New routes retain the original parent attributes and exact ordered prefix, then append the selected downstream suffix through link 68. The three final destination link/position strings come directly from 1135:2/3/4: 120 at 2272.2977955121637 m, 123 at 179.06973212909716 m, and 2 at 2289.1984998704838 m.

All affected decisions retain `allVehTypes=true`, `STATIC`, `combineStaRoutDec=true`, blank route formula, and the sole static interval beginning at 0. Unchanged XML includes driving behavior, look-ahead settings, lane-change distances outside the separate distance arm, all inputs, and all other decisions. Source 69, decision 1134, and late connector 10703 are checked byte-for-byte in every arm.

## Validation and scope

The generator preserves every source byte outside explicit non-overlapping replacement spans. Each validation JSON records source/output offsets, hashes and sizes of the preserved spans, plus before/after edit payloads. Reversing the recorded route edits reconstructs the complete original INPX exactly. An independent XML structure comparison removes only the declared changes before requiring equality of the rest of the document.

Every new ordered route is checked against actual connector source/target roads, valid lane ranges, road/connector geometry, monotonically ordered positions, final destination position, vehicle-class declarations, and interval scope. Road-to-road lane continuity reports distinguish a connector's valid lane mapping from a required intervening lane change. In particular, 66→10633 reaches lane 4 of link 68, whereas 10681 accepts lanes 1–2. The validator reports that required maneuver; it does not certify that a vehicle can complete it in traffic. Structural coverage verifies that 68's incoming connectors are exactly 10625/10629/10633 and that no native input begins on 68. It does not prove all vehicles at 1135 previously accepted one of the selected parent routes.

Eight focused stdlib tests passed in 0.863 seconds. They cover the one-byte distance change, exact probability products/IDs, full raw-byte reconstruction, explicit lane-change limitation, and rejection of duplicate IDs, class/interval changes, unreviewed weights, disconnected paths, invalid lane ranges, invalid destination positions, and unsafe output directories. A separate `--verify` pass compared the complete 133-file set and bytes against an in-memory rebuild; `source_changes=[]`.

There are 42 byte-identical SIG copies per arm, one INPX and one validation JSON per arm, and one top-level manifest. The original 95 MB visual background image is intentionally not packaged; its original XML reference is retained. VISSIG DLLs, standard executable/model assets and existing absolute visual references remain dependencies of the original host. This is an isolated experimental network package, not a standalone VISSIM installation.

## Commands and remaining launch gates

Run these commands from the review worktree with the configured Python runtime:

```powershell
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -m unittest diagnostics.test_fixed_beta300v3_network_arms -v
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -m diagnostics.prepare_fixed_beta300v3_network_arms --verify
```

The generator without `--verify` creates a new directory and refuses any existing destination. An independent reproduction can use `--output diagnostics/<new-name>`; it does not overwrite an existing experiment. Changing any pinned input makes verification fail, so later runtime/source changes must be recorded as a new experiment provenance rather than silently overwriting this manifest.

Before launch, the parent must validate the fixed-command writer and native loading for each arm. The route arm additionally requires native readback of RelFlow defaults/values, Combine and look-ahead behavior, selected-route IDs and intervals, and eligible vehicle coverage at the replaced decision. Preserve the exact seed13 warmup and actual β300-v3 900 command/CSV; the 1050 optimized command is not part of this frozen intervention. Use the existing experiment design for launch/readback gates. The current canonical model and calibration network-SHA contracts must not be relabeled to these modified networks.

Preserved conditional probabilities do not promise identical same-seed vehicle destinations. Combine/look-ahead is already enabled, and earlier route declaration is not proof of improved lane access. Connector 10635 is the city route toward 47 implicated by vehicle 4725; it is separate from the on-ramp route experiment. Its distance-only arm leaves emergency-stop distance and 45-second diffusion/removal settings unchanged.

## Files for review

- `diagnostics/prepare_fixed_beta300v3_network_arms.py` — stdlib producer/validator; SHA256 `99a8a912688a5a2ab25d2894bf3c0527f8700da464c8e7607c9a59e58fd0a42c`.
- `diagnostics/test_fixed_beta300v3_network_arms.py` — eight focused static tests; SHA256 `48779934f2cd623ab8bc191c19d94e4ec9b414bc92dd42786cb60e24ddf5f0d5`.
- `diagnostics/fixed_beta300v3_network_arms_v1/` — manifest and exact 132 listed generated artifacts; do not add unrelated files inside this verified tree.
- This handoff is outside the generated tree so the original experiment manifest remains unchanged.
