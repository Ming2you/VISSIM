# Fixed upstream VSL experiment (prepared 2026-09-10)

The experiment changes FW_E zone heads 0 and 5 at t=900. All other heads
remain at 120 km/h. Cells inherit their head value, so the actual lowered DSD
locations are E0/E2/E5/E7. It does not require a two-branch FD: the plant response
tests whether an upstream speed cap can change the subsequent bottleneck flow.
These arms inherit n7 without modifying or calibrating its numerical parameters.

## Files and integration

- `evaluation/controllers/diagnostic_profile.py`: validates configured heads,
  their physical DSD presence, and the intersection of configured candidates and
  the VBS runner's actual allowed speed-distribution IDs. The empty profile is
  the 120 baseline. All cell keys are explicitly expanded for the CSV writer.
- `diagnostics/diagnostic_profile.patch`: apply only after the live n7 run ends.
  Adds `diagnostic-vsl-profile` to the canonical adapter and VBS runner. An invalid
  profile raises instead of falling back to another controller. Only this alias
  bypasses policy/post-guard optimizers; predictions remain available.
- `diagnostics/vsl_profile_config_80.json`, `_100.json`, `_120.json`: small n7
  overlays, not additional adapter copies. Use the same network, demand, seed,
  mapping, VBS config and horizon as the no-control comparison.

Runner options are `-Controller diagnostic-vsl-profile -ControlStartSec 900
-WarmupController no-control`, without `-ForceStepwise`. Set `-Tuning` to one
of the profile config paths. Existing VBS configuration must be the n21 config
that lists the 66 physical DSD rows. The VBS internally supplies
`--diagnostic-allowed-vsl-speeds`; direct offline adapter calls need that argument.

## What remains fixed

The profile suppresses all city signal/SG rows. Its physical meter writer uses
the full 10-second green with rate 900 for every one of the 8 mapped meters.
The existing COM initialization, write and persistence-check paths are retained.
This exactly matches the recorded n7 no-control meter commands at t=1 and t=900.

Do not infer the COM-controlled meter aspect from `.lsa`: the no-control run's
`.lsa` has a t=1 native-program `off` event, while the immediate and 30-second
post-step COM readbacks are GREEN all the way to t=5400 (1,440 persistence
checks passed). Readback evidence takes priority for a COM-owned SG. The `.lsa`
still describes the native city programs because this experiment never takes
city SG ownership.

## Validation and run evidence

`python diagnostics/test_diagnostic_profile.py -v`: 7 tests passed. Includes
the real adapter main pipeline, patched only in memory, for 80/100/120, forbidden
policy/optimizer/write-back hooks, every real VSL CSV row, every full-open meter,
invalid heads/speeds, and the real VBS static scheduler under a COM-free mock.
The scheduler issues decisions at t=1 and t=900, logs t=900 before actuation, and
continues interval logging through the end. The native-ownership readback mock
rejects a city SG that has been taken by COM. On sandboxed Windows, cscript may
need execution outside the sandbox to read its own settings; the mock never
creates VISSIM COM.

`python scripts/verify_parameters.py diagnostics/vsl_profile_config_80.json`
(likewise `_100` and `_120`): all three passed. `git apply --check
diagnostics/diagnostic_profile.patch` passed before integration.

After each real run, require zero decision/action/COM/signal failures and inspect:

1. `action_*.csv`: exactly 66 VSL and 8 meter rows per decision; no signal rows.
   At t=900 E0/E2/E5/E7 have the selected cap; all other DSDs have 120. VSL
   readback must match the requested values. The existing writer verifies
   speed-distribution classes 10/20/30/70; the recorded field contains 10 and 70.
2. `decisions_*/signal_readback.csv`: all 8 meters remain GREEN in actual
   post-step readback, not only in the requested action CSV.
3. Run log `PROFILE_NATIVE_SIGNAL_READBACK` at t=1/900/end: positive checked
   count, `non_native=0 missing=0`. This is a direct read of city ContrByCOM,
   not a signal command. Any mismatch increments SIGNAL_FAILURES.
4. Reuse `scripts/analyze_actuation.py` to compare actual meter readbacks and
   the native city phase curves with the no-control run. No plant improvement
   is claimed until these actuation checks and the subsequent traffic response
   have both been measured.
