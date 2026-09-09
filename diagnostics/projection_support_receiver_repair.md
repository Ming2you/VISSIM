The stopped beta0 run at1050 seconds exposed one unassigned physical vehicle on connector10421. The corrected data assigns that vehicle once to `storage:SC5_to_SC11`; the observed and modeled initial Ω stock are both2083 vehicles. Initial entry, exit and event counts remain zero. The original exception is reproduced if10421 is put back into the unresolved set.

The physical path is `1220019201 →10421→1220014000`. SC5 SG4 heads are at243.17–243.28m on the source road, before the connector entrance at248.79m. Native route1023:2 uses this exact triplet. The active canonical movement `SC5_N_SC102_to_S_SC11` receives into `SC5_to_SC11`, which is also supported by the actual destination road. At1050 the recorded vehicle5600 is already45.68m along10421. The legacy source-road storage `SC102_to_SC5` therefore describes a location the vehicle has already left. The projection restores the receiving stock; it does not replay the earlier inward boundary crossing.

All45 previously unresolved links were reviewed against the pinned Ver2 network, native route triplets and actual merged-model receivers. Only16 have sufficient evidence for a unique receiving stock:

| Physical connector | Existing receiving storage |
|---|---|
| 10119,10698 | SC1001_W_out |
| 10366,10372,10376 | SC11_to_SC5 |
| 10367,10374,10378 | SC11_to_SC1 |
| 10419 | SC5_to_SC101 |
| 10421,10426 | SC5_to_SC11 |
| 10532,10537 | SC101_to_SC5 |
| 10561,10568 | SC1_to_SC11 |
| 10570 | SC1005_to_SC107 |

The16 additions change neither ownership, Ω membership, model movement definitions nor flow probabilities. Existing support mappings are preserved. The count of additional support entries increases from170 to186. All16 had zero observed vehicles in the first controlled900-second snapshot.

Fourteen additions are downstream of the source signal. Connectors10366 and10426 instead leave before the source-road signal heads; they are native unsignalled turn bypasses. Their observed vehicles have already entered the connector and have a unique modeled receiving storage. This initial-stock repair does **not** establish that the existing movement signal-service approximation represents those bypasses correctly.

Twenty-nine physical links remain explicit unresolved cases:14 roads with unresolved origin/route identity,11 connectors without a unique accepted-movement proof, and4 connectors with known shared-route receiver conflicts. The shared conflicts are10610/10611 and10627/10634; a legacy triplet alone is insufficient to resolve their actual bypass cohorts. Any positive observation on any remaining link still raises the exact offending link ID. No nearest storage, zero allocation or equal split is introduced.

Validation uses current production imports. Nine tests passed in32.610 seconds: actual1050 projection, reproduction of the old exception, each of29 positive unresolved cases, all31 pure-n7 snapshots from900 through5400, one synthetic vehicle on each of186 reviewed supports, and existing-data/OFF behavior. Every one of the32 actual snapshots has exactly zero difference between observed Ω vehicles and initialized model Ω stock; each row in `projection_support_receiver_regression.json` includes the run, snapshot path and original byte SHA. Independent reviews by both other agents confirmed actual10421 storage, physical receivers, entry0 and retained ambiguity checks. Parent's separate actual1050 full-main preflight passed in115.295406 seconds with unchanged source/input hashes; this report's unit/projection checks do not claim a completed new live VISSIM experiment.

The support raw SHA changes from `46965a1b605b71f707400fe6eb70c06ac17e997c7fa7c0051eb9225492d515f1` to `366e6c4c99e0ed311aef4fb7eb718d6adfb62edad71772d1440f113d9607c174`. The original45-link proof and each proposed receiver's source geometry, signal heads, native routes, model specification and original coverage row are retained in `unresolved_projection_support_review.json`. Network SHA remains `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`.

For a checkout without the recorded run directory, run:

```powershell
python -m diagnostics.run_receiver_fixture_tests
```

This restores the separate187,207-byte `fixtures/receiver_turns_v1.zip` into a fresh `.review-fixtures/receiver-<id>` subtree. It preserves raw1050, actual preceding900 action, original run manifest and a replay configuration as four byte-hashed files. The replay configuration consumes the reviewed current support data; it is not a claim that the failed run used the new support. Relocated copies change only whole absolute path strings, using the already-tested fixture restorer. Existing `control_area_v1.zip` and its historical validation remain unchanged.

The isolated subprocess blocks reads/listing of the original `evaluation/runs` and git subprocesses. Actual1050, original-defect reproduction and all29 unresolved-link guards passed with no forbidden accesses in3.687 seconds including test loading (`receiver_fixture_validation.json`). The full31 historical snapshot test remains an additional integration check requiring those actual files; the minimal archive does not claim to contain them.

The historical `build_area_projection_coverage.py` is now guarded against replacing this16-receiver revision with its earlier170/45 result. The original45-link review generator refuses to overwrite its existing pinned proof. These diagnostic safeguards change no runtime inputs or production Python.
