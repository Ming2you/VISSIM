# Actuation authority and response calibration - 220w 600s

Demand: urban=1430 vph, freeway=3721 vph, seed=13, control_interval=180s, pulse=none.
Baseline is a forced fixed controller: VSL 120 kph, signals 57/57, D ramp green 10s, F ramp monitor/always-green.

| case | TTT veh-h | delta TTT | stopped veh-h | delta stopped | mean speed | VSL | D green | F green | signal major/minor | pred abs err | readback ok |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed57 | 134.961 | +0.00% | 31.701 | +0.00% | 46.921 | 120.0 | 10.0 | 10.0 | 57.0/57.0 | 188.9 | 1.00 |
| ramp_hold | 137.807 | +2.11% | 34.242 | +8.01% | 45.781 | 120.0 | 1.0 | 10.0 | 57.0/57.0 | 186.3 | 1.00 |
| vsl80 | 141.269 | +4.67% | 32.936 | +3.89% | 44.164 | 80.0 | 10.0 | 10.0 | 57.0/57.0 | 233.9 | 1.00 |
| signal_major | 149.568 | +10.82% | 53.999 | +70.34% | 40.907 | 120.0 | 10.0 | 10.0 | 75.0/25.0 | 190.8 | 1.00 |
| signal_minor | 148.975 | +10.38% | 58.767 | +85.38% | 40.682 | 120.0 | 10.0 | 10.0 | 25.0/75.0 | 106.3 | 1.00 |
| combined_strong | 154.932 | +14.80% | 54.126 | +70.74% | 38.715 | 80.0 | 1.0 | 10.0 | 75.0/25.0 | 244.8 | 1.00 |

Response slopes are approximate one-factor deltas from the fixed57 baseline:

| actuator | command change | TTT response | stopped response | interpretation |
|---|---:|---:|---:|---|
| ramp_hold | D green 10s -> 1s | 2.846 veh-h (+2.11%) | 2.540 veh-h (+8.01%) | ramp authority is strong but harmful under this demand. |
| vsl80 | VSL 120 -> 80 kph | 6.308 veh-h (+4.67%) | 1.235 veh-h (+3.89%) | VSL command is accepted; benefit must come from a targeted policy, not blanket speed reduction. |
| signal_major | signal 57/57 -> 75/25 | 14.607 veh-h (+10.82%) | 22.297 veh-h (+70.34%) | major-axis split is physically influential. |
| signal_minor | signal 57/57 -> 25/75 | 14.014 veh-h (+10.38%) | 27.065 veh-h (+85.38%) | minor-axis split is also influential and directionally worse here. |
| combined_strong | VSL80 + D hold + 75/25 | 19.971 veh-h (+14.80%) | 22.425 veh-h (+70.74%) | combined authority is high but over-restrictive. |

Notes:
- `readback ok` treats numeric VSL readbacks as exact command matches and signal/ramp `stored` as accepted.
- F ramp remains guarded as monitor/always-green because its physical metering fit is marked invalid in the active calibration.
- These are authority diagnostics, not optimized policies.
