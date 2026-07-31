# P-Stack Decision Calibration Comparison

warmup_sec = 0, sim_period_sec = 1800, seed = 13

decision_v1 disabled the hidden PFO incumbent and relaxed the ramp-release guard.
decision_balanced keeps PFO incumbent disabled and terminal-cost scoring active, but restores a higher queue-risk ramp-release floor.
decision_balanced_postguard keeps decision_balanced and adds a post-guard no-control safety score check before action commit.

| demand | control | TTT veh-h | delta vs NC | delta vs GT | stopped veh-h | mean speed | mean ramp meter rate (vph) | PFO selected | terminal penalty | postguard gap | postguard fb | fp mismatch max | recalib rate | release before -> after |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 155w | no_control | 311.846 | +0.000% | -0.000% | 68.031 | 51.292 | 825.5 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.000->0.000 |
| 155w | combined_pfoinc | 312.623 | +0.249% | +0.249% | 68.796 | 51.164 | 809.5 | 1.000 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.000->0.000 |
| 155w | no_pfoinc | 311.691 | -0.050% | -0.050% | 67.515 | 51.358 | 776.3 | 0.000 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.000->0.000 |
| 155w | guarded | 311.848 | +0.000% | +0.000% | 68.032 | 51.292 | 823.9 | 1.000 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.981->0.998 |
| 155w | guarded_terminal | 311.848 | +0.000% | +0.000% | 68.032 | 51.292 | 823.9 | 1.000 | 18.421 | 0.000 | 0.000 | 0 | 0.000 | 0.981->0.998 |
| 155w | decision_v1 | 311.666 | -0.058% | -0.058% | 67.417 | 51.336 | 782.8 | 0.000 | 39.519 | 0.000 | 0.000 | 0 | 0.000 | 0.939->0.948 |
| 155w | decision_balanced | 312.589 | +0.238% | +0.238% | 68.293 | 51.154 | 799.0 | 0.000 | 39.593 | 0.000 | 0.000 | 0 | 0.000 | 0.939->0.968 |
| 155w | decision_balanced_postguard | 312.589 | +0.238% | +0.238% | 68.293 | 51.154 | 799.0 | 0.000 | 39.593 | 0.020 | 0.000 | 0 | 0.000 | 0.939->0.968 |
| 190w | no_control | 468.782 | +0.000% | -0.562% | 154.544 | 41.754 | 825.5 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.000->0.000 |
| 190w | combined_pfoinc | 479.764 | +2.343% | +1.768% | 164.074 | 40.803 | 603.9 | 0.545 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.000->0.000 |
| 190w | no_pfoinc | 497.635 | +6.155% | +5.558% | 174.653 | 39.708 | 557.8 | 0.000 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.000->0.000 |
| 190w | guarded | 471.431 | +0.565% | +0.000% | 156.693 | 41.576 | 820.7 | 1.000 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.830->0.994 |
| 190w | guarded_terminal | 471.431 | +0.565% | +0.000% | 156.693 | 41.576 | 820.7 | 1.000 | 26.297 | 0.000 | 0.000 | 0 | 0.000 | 0.830->0.994 |
| 190w | decision_v1 | 480.536 | +2.507% | +1.931% | 163.668 | 40.943 | 784.5 | 0.000 | 57.058 | 0.000 | 0.000 | 0 | 0.000 | 0.856->0.947 |
| 190w | decision_balanced | 470.521 | +0.371% | -0.193% | 154.757 | 41.684 | 806.5 | 0.000 | 56.345 | 0.000 | 0.000 | 0 | 0.000 | 0.897->0.976 |
| 190w | decision_balanced_postguard | 470.521 | +0.371% | -0.193% | 154.757 | 41.684 | 806.5 | 0.000 | 56.345 | 0.040 | 0.000 | 0 | 0.000 | 0.897->0.976 |
| 220w | no_control | 620.492 | +0.000% | -0.241% | 242.868 | 34.828 | 825.5 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.000->0.000 |
| 220w | combined_pfoinc | 636.490 | +2.578% | +2.331% | 255.950 | 33.707 | 603.6 | 0.455 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.000->0.000 |
| 220w | no_pfoinc | 650.690 | +4.867% | +4.614% | 267.400 | 33.499 | 493.5 | 0.000 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.000->0.000 |
| 220w | guarded | 621.990 | +0.242% | +0.000% | 241.939 | 34.730 | 804.6 | 0.545 | 0.000 | 0.000 | 0.000 | 3 | 1.000 | 0.742->0.972 |
| 220w | guarded_terminal | 621.990 | +0.242% | +0.000% | 241.939 | 34.730 | 804.6 | 0.545 | 37.418 | 0.000 | 0.000 | 0 | 0.000 | 0.742->0.972 |
| 220w | decision_balanced | 622.331 | +0.296% | +0.055% | 244.407 | 34.739 | 804.7 | 0.000 | 80.345 | 0.000 | 0.000 | 0 | 0.000 | 0.875->0.974 |
| 220w | decision_balanced_postguard | 622.331 | +0.296% | +0.055% | 244.407 | 34.739 | 804.7 | 0.000 | 80.345 | 0.085 | 0.000 | 0 | 0.000 | 0.875->0.974 |

Notes:
- decision_v1 was not run for 220w because 190w already showed the relaxed guard was over-holding queues.
- NC = no_control; GT = guarded_terminal.
- postguard gap is the mean terminal-score gap: guarded action score minus guarded no-control score. Positive means the committed action was predicted worse than no-control; fallback only triggers above the configured margin.
- Fingerprint mismatch/recalib are zero for guarded_terminal, decision_balanced, and decision_balanced_postguard because the current calibration fingerprint override is active.
