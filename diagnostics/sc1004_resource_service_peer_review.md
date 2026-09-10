# SC1004 shared service prior: independent bounded review

No blocking correctness issue was found in the reviewed train-only prior or its unapplied consumer patch. Production files and the patch were not changed. No VISSIM, optimizer, held endpoint, or full-FZP rerun was performed by this reviewer.

The saved crossing CSV independently reproduces train/holdout/full event counts **566 / (50, 52) / 668** using the declared strictly interior event brackets. The selected value is **566 / 1350 × 3600 = 1509.333333 veh/h**. The full-period **668 / 1620 × 3600 = 1484.444444** is retained only as evidence. Neither held window enters the selected numerator or GREEN denominator. All listed calibration source hashes match the reviewed files.

Train count566 exceeds unique IDs565 because ID11350 crossed via lane1 at2034–2035 and again via lane3 at2628–2629. Both records directly enter10634,594 seconds apart. This is a repeat resource visit, not two heads counting one crossing. Service counts may include repeat visits; this is separate from vehicle completion accounting.

The patch replaces the same service value in the three existing movement-capacity views and in each corresponding route turn. The runtime's connector key10634 provides one common service limit; `limit_intended_batch` allocates that remaining limit, and `receive_accepted` debits only accepted flow. The value is not multiplied by three lanes or three model aliases. Unchanged config, no-prior metadata, movement betas, capacities outside these three movements, and finite storage were compared in the focused tests.

The validator checks the pinned calibration, network, exact source/target, three upstream native heads, selected SC/phase, all model members, native clock, train windows, per-event GREEN bracket, duplicates, exposure arithmetic and finite positive rate. The existing uncertainty claim is appropriate: this is an offline achieved-discharge lower bound for a shared hard cap, not a saturation estimate, not a confidence interval, and not a prediction that the same discharge is feasible under every receiving condition. Seed14 validation remains pending. The two holdout observed counts are evidence withheld from fitting; this review does not independently re-establish whole-model holdout improvement.

Validation: `python -X utf8 -m unittest diagnostics.test_sc1004_resource_service -v` —5 tests PASS in1.969s. The tests include absent-option exact equivalence, geometry/holdout/duplicate/exposure/NaN rejection, shared partial-GREEN budget and candidate-copy isolation. Saved CSV classification was re-counted independently without invoking a writer.

Reviewed raw SHA256:

- `diagnostics/prepare_sc1004_resource_service.py`: `fdb33ac1ab5951f3a23c0fad318723c23be8b0b964dcfe996924a09a6ce6e7c2`
- `diagnostics/prepare_sc1004_resource_service_patch.py`: `84314711ff265b1bb987bf0e94c9e1e2bec8464d600224149beb9e86284a2d08`
- `diagnostics/sc1004_resource_service_calibration.json`: `a58e6650daad7d7783cf8d7e8202a50e92415658932b370af1ae1211443bbb94`
- `diagnostics/test_sc1004_resource_service.py`: `4a60ee676974117a6b62b9fc401e7dde6993545ee06626e8b0f499786af66f28`
- `evaluation/controllers/route_choice_corridor.py`: `8cf448e27ae9069569f07c7ace1a7156775d44b3515b1632bf268966234ab8c0`
