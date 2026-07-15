# Controller comparison — mid demand (u1800/fw3000), 1800s, 3 seeds (11/13/47)

All 12 runs complete (362 state rows, 31 decisions each), watchdog-guarded, warmup 300s, mean over seeds.
Repo = clone 0e07c1c, calibration v2 (unmodified). Metric = mean over seeds vs no-control.

## Performance

| controller | TTT (veh-h) | vs nc | stopped (veh-h) | vs nc | mean_speed (kph) | vs nc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no-control | 620.2 | — | 318.0 | — | 23.89 | — |
| wu | 620.2 | +0.0% | 318.0 | +0.0% | 23.89 | +0.0% |
| **pfo** | **609.4** | **-1.7%** | **291.8** | **-8.2%** | **25.47** | **+6.6%** |
| stackelberg-wu-metered | 622.8 | +0.4% | 320.6 | +0.8% | 23.75 | -0.6% |

## Control activation (summed over 93 decisions/controller)

| controller | metering_active | vsl_active | N_UF*_max | signal green_times |
| --- | ---: | ---: | ---: | --- |
| no-control | 0 | 0 | 0 | fixed 57s (baseline) |
| wu | 0 | 0 | 0 | **fixed 57s = identical to no-control** |
| pfo | 0 | 0 | 0 | **varied (45/45/45/51/51/63...) — retimes signals** |
| stackelberg-wu-metered | 23 | 0 | 3302 | fixed 57s (does NOT retime) |

## Findings

1. **PFO is the best and the only effective controller**: TTT -1.7%, stopped -8.2%, mean speed +6.6%.
   Its benefit comes entirely from URBAN signal retiming (green_times differ per approach). It applies
   no ramp metering / VSL — correct, because the freeway is free-flowing.
2. **WU is effectively a no-op**: WuDistributedController returns the baseline fixed 57s green times
   (byte-identical traffic to no-control: +0.0% on every metric). It is not producing differentiated
   urban signal control in this VISSIM integration. Needs investigation.
3. **stackelberg-wu-metered meters counterproductively**: it is the only controller whose leader sets
   N_UF* (max 3302) and activates ramp metering (23/93 decisions). But it does NOT retime signals
   (green=57) and its ramp metering slightly HURTS (TTT +0.4%, speed -0.6%) because the freeway is
   uncongested — restricting freeway inflow only builds ramp queues with no mainline benefit. Classic
   "leader activates control where there is no congestion to relieve" for a free-flowing freeway.
4. Consistent with all prior runs: the bottleneck is URBAN, the freeway is uncongested, so urban signal
   control (PFO) is what helps and freeway control (metering/VSL) is at best idle, at worst harmful.

## Next-step candidates

- Investigate why WU produces baseline-equal signal control (wu urban follower output -> VBS green_times).
- For stackelberg-wu-metered: gate ramp metering on freeway congestion (only meter when a freeway
  segment is at/above critical density), so the leader does not meter a free-flowing freeway.
- To exercise freeway control meaningfully, a freeway-congesting demand (e.g. fw_eb_heavy at higher
  volume) is needed; at symmetric mid demand the freeway never congests.
