# Four-arm actual actuation audit

All four completed 3000 s. No FZP was read. Command exposure summaries use [900,3000); the command at 3000 has zero traffic exposure.

| Arm | LDP samples | Meter clock mismatches | VSL readbacks | Initial/changed SG writes | Independent LSA |
|---|---:|---:|---:|---:|---|
| none | 432000 | 0 | 5544 | 8 | FAIL: 8 missing COM events |
| vsl | 432000 | 0 | 5544 | 8 | FAIL: 8 missing COM events |
| rm | 432000 | 0 | 5544 | 278 | FAIL: 278 missing COM events |
| both | 432000 | 0 | 5544 | 338 | FAIL: 338 missing COM events |

The 25 selected LDP files cover 17 native urban controllers (136 SG) and 8 meters over 1..3000 s. Eight meter SG are compared against actual command clocks (23992 samples), with immediate initial/write readbacks independently required. Native urban states match exactly across arms for 1..3000 s. Twenty-five other LDP files are outside this selected controller audit.
VSL audit uses actual application readbacks at 66 DSD × 4 vehicle classes × 21 commands = 5544 records per run. Signal CSV is not used as a substitute for native execution evidence.
All recorded LDP/readback/LSA/action CSV SHA pins were rechecked and native LDP coverage reparsed. JSON command values equal their actual CSV values.

Warmup selected snapshots and head observation windows at 1,150,300,450,600,750,900 s identical: True. Only head-window config_sha256 was excluded within the compared payload; top-level run/network provenance was not compared. Continuous FZP and hidden state equality are outside this audit.

## none

| VSL zone | Command changes (s:kph) | Exposure 900..3000 (s) |
|---|---|---|
| FW_E__seg0 | 1:100 | {'100': 2100} |
| FW_E__seg10 | 1:100 | {'100': 2100} |
| FW_E__seg15 | 1:100 | {'100': 2100} |
| FW_E__seg5 | 1:100 | {'100': 2100} |
| FW_W__seg0 | 1:100 | {'100': 2100} |
| FW_W__seg10 | 1:100 | {'100': 2100} |
| FW_W__seg15 | 1:100 | {'100': 2100} |
| FW_W__seg5 | 1:100 | {'100': 2100} |

| Meter | Min–max green | Max occupancy % | >15% decisions | Changes (s:g) |
|---|---:|---:|---:|---|
| RM_C10480 | 10–10 | 12.377 | 0 | 1:10 |
| RM_C10482 | 10–10 | 7.734 | 0 | 1:10 |
| RM_C10646 | 10–10 | 6.534 | 0 | 1:10 |
| RM_C10644 | 10–10 | 6.159 | 0 | 1:10 |
| RM_C10639 | 10–10 | 22.943 | 7 | 1:10 |
| RM_C10681 | 10–10 | 5.670 | 0 | 1:10 |
| RM_C10490 | 10–10 | 8.194 | 0 | 1:10 |
| RM_C10484 | 10–10 | 7.531 | 0 | 1:10 |

## vsl

| VSL zone | Command changes (s:kph) | Exposure 900..3000 (s) |
|---|---|---|
| FW_E__seg0 | 1:100 | {'100': 2100} |
| FW_E__seg10 | 1:100 | {'100': 2100} |
| FW_E__seg15 | 1:100 | {'100': 2100} |
| FW_E__seg5 | 1:100, 3000:60 (zero exposure) | {'100': 2100} |
| FW_W__seg0 | 1:100, 1050:60 | {'100': 150, '60': 1950} |
| FW_W__seg10 | 1:100 | {'100': 2100} |
| FW_W__seg15 | 1:100 | {'100': 2100} |
| FW_W__seg5 | 1:100, 1350:60, 1500:100, 1650:60 | {'100': 600, '60': 1500} |

| Meter | Min–max green | Max occupancy % | >15% decisions | Changes (s:g) |
|---|---:|---:|---:|---|
| RM_C10480 | 10–10 | 14.335 | 0 | 1:10 |
| RM_C10482 | 10–10 | 8.585 | 0 | 1:10 |
| RM_C10646 | 10–10 | 6.609 | 0 | 1:10 |
| RM_C10644 | 10–10 | 5.990 | 0 | 1:10 |
| RM_C10639 | 10–10 | 21.757 | 5 | 1:10 |
| RM_C10681 | 10–10 | 5.366 | 0 | 1:10 |
| RM_C10490 | 10–10 | 8.145 | 0 | 1:10 |
| RM_C10484 | 10–10 | 7.945 | 0 | 1:10 |

## rm

| VSL zone | Command changes (s:kph) | Exposure 900..3000 (s) |
|---|---|---|
| FW_E__seg0 | 1:100 | {'100': 2100} |
| FW_E__seg10 | 1:100 | {'100': 2100} |
| FW_E__seg15 | 1:100 | {'100': 2100} |
| FW_E__seg5 | 1:100 | {'100': 2100} |
| FW_W__seg0 | 1:100 | {'100': 2100} |
| FW_W__seg10 | 1:100 | {'100': 2100} |
| FW_W__seg15 | 1:100 | {'100': 2100} |
| FW_W__seg5 | 1:100 | {'100': 2100} |

| Meter | Min–max green | Max occupancy % | >15% decisions | Changes (s:g) |
|---|---:|---:|---:|---|
| RM_C10480 | 10–10 | 12.160 | 0 | 1:10 |
| RM_C10482 | 10–10 | 7.734 | 0 | 1:10 |
| RM_C10646 | 10–10 | 6.942 | 0 | 1:10 |
| RM_C10644 | 10–10 | 6.159 | 0 | 1:10 |
| RM_C10639 | 2–10 | 33.542 | 7 | 1:10, 1650:9, 2400:7, 2550:5, 2700:3, 2850:2 |
| RM_C10681 | 10–10 | 5.498 | 0 | 1:10 |
| RM_C10490 | 10–10 | 8.084 | 0 | 1:10 |
| RM_C10484 | 10–10 | 8.587 | 0 | 1:10 |

## both

| VSL zone | Command changes (s:kph) | Exposure 900..3000 (s) |
|---|---|---|
| FW_E__seg0 | 1:100 | {'100': 2100} |
| FW_E__seg10 | 1:100 | {'100': 2100} |
| FW_E__seg15 | 1:100 | {'100': 2100} |
| FW_E__seg5 | 1:100, 3000:60 (zero exposure) | {'100': 2100} |
| FW_W__seg0 | 1:100, 1050:60 | {'100': 150, '60': 1950} |
| FW_W__seg10 | 1:100 | {'100': 2100} |
| FW_W__seg15 | 1:100 | {'100': 2100} |
| FW_W__seg5 | 1:100, 1350:60, 1500:100, 1650:60 | {'100': 600, '60': 1500} |

| Meter | Min–max green | Max occupancy % | >15% decisions | Changes (s:g) |
|---|---:|---:|---:|---|
| RM_C10480 | 8–10 | 18.840 | 2 | 1:10, 2700:8, 3000:9 (zero exposure) |
| RM_C10482 | 10–10 | 8.541 | 0 | 1:10 |
| RM_C10646 | 10–10 | 6.761 | 0 | 1:10 |
| RM_C10644 | 10–10 | 6.258 | 0 | 1:10 |
| RM_C10639 | 5–10 | 25.622 | 6 | 1:10, 1650:8, 1800:7, 1950:8, 2700:7, 2850:5, 3000:3 (zero exposure) |
| RM_C10681 | 10–10 | 5.513 | 0 | 1:10 |
| RM_C10490 | 10–10 | 8.145 | 0 | 1:10 |
| RM_C10484 | 10–10 | 7.687 | 0 | 1:10 |

Full per-decision occupancy, raw/bounded ALINEA request, next integrator, actual green, model service ceiling and CSV encoding are in actuation_review.json. The target15% and gain70 veh/h per percentage-point per meter lane are exploratory, not calibrated critical occupancy/capacity. Open meters with occupancy below15% are expected policy outputs; near-threshold changes may remain inside a discrete green deadband. GREEN commands do not guarantee a desired measured throughput.
