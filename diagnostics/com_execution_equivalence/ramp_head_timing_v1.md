Completed execution timing; no physical-equivalence verdict.

Failed old signal r01 is excluded. Only explicitly supplied successful receipts are consumed.

codex_com_ramp_head_old_s13_1200_r01

Wrapper wall: 303.216743 s; terminal 1200 s; STEPWISE_PHYSICAL_HEAD_OBSERVATION.

| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |
|---|---:|---:|
| startup.load_net | 9.281250 | 1 |
| startup.demand | 2.125000 | 1 |
| startup.demand.volume_before_read | 0.031250 | 204 |
| startup.demand.volume_set | 0.859375 | 204 |
| startup.demand.volume_after_read | 0.929688 | 204 |
| startup.control_setup | 0.156250 | 1 |
| startup.head_init | 0.070313 | 1 |
| sim.first_step | 1.046875 | 1 |
| sim.step | 20.656250 | 1199 |
| decision.total | 17.671875 | 9 |
| state.json | 3.718750 | 9 |
| decision.python | 10.562500 | 9 |
| action.apply | 3.335938 | 9 |
| head.capture | 181.679688 | 1200 |
| head.history | 25.031250 | 1200 |
| head.seal | 3.460938 | 1200 |
| scan.vehicles | 77.273438 | 1250 |
| head.signal_capture | 107.898438 | 2400 |
| signals.runtime | 0.007813 | 1200 |
| rampmeters.runtime | 9.531250 | 1200 |
| signals.readback | 4.640625 | 1199 |
| log.state_csv | 3.460938 | 41 |

Actual simulation call total: 21.703125 s (first + subsequent calls only).

| Counted COM site; not total COM inventory | Count |
|---|---:|
| com.input_volume.read | 408 |
| com.input_volume.setter | 204 |
| com.vehicle.physical_bulk_returned | 4800 |
| com.sg.head_owner_read | 136800 |
| com.sg.head_read | 136800 |
| com.vehicle.route_bulk_returned | 36 |
| com.vsl.setter | 2376 |
| com.vsl.checked_read | 2376 |
| com.sg.setter | 9672 |
| com.sg.apply_read | 9672 |
| com.sg.persistence_read | 9592 |

Largest demand gap: input 114 interval 1-1 DONE (line 27) → input 114 interval 1-2 BEGIN (line 28): 0.010000 s.
Whole demand 2.125000 s; before reads 0.031250, setter/error handling 0.859375, after reads 0.929688 s. The gap does not isolate a single getter.

codex_com_ramp_head_new_s13_1200_r01

Wrapper wall: 304.112369 s; terminal 1200 s; STEPWISE_PHYSICAL_HEAD_OBSERVATION.

| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |
|---|---:|---:|
| startup.load_net | 8.445313 | 1 |
| startup.demand | 2.789063 | 1 |
| startup.demand.volume_before_read | 0.101563 | 204 |
| startup.demand.volume_set | 0.992188 | 204 |
| startup.demand.volume_after_read | 1.101563 | 204 |
| startup.control_setup | 0.156250 | 1 |
| startup.head_init | 0.070313 | 1 |
| sim.first_step | 0.835938 | 1 |
| sim.step | 20.476563 | 1199 |
| decision.total | 17.476563 | 9 |
| state.json | 3.625000 | 9 |
| decision.python | 10.562500 | 9 |
| action.apply | 3.234375 | 9 |
| head.capture | 177.523438 | 1200 |
| head.history | 24.820313 | 1200 |
| head.seal | 3.593750 | 1200 |
| scan.vehicles | 76.632813 | 1250 |
| head.signal_capture | 104.390625 | 2400 |
| signals.runtime | 0.007813 | 1200 |
| rampmeters.runtime | 0.765625 | 1200 |
| signals.readback | 0.335938 | 98 |
| log.state_csv | 3.421875 | 41 |

Actual simulation call total: 21.312501 s (first + subsequent calls only).

| Counted COM site; not total COM inventory | Count |
|---|---:|
| com.input_volume.read | 408 |
| com.input_volume.setter | 204 |
| com.vehicle.physical_bulk_returned | 4800 |
| com.sg.head_owner_read | 136800 |
| com.sg.head_read | 136800 |
| com.vehicle.route_bulk_returned | 36 |
| com.vsl.setter | 2376 |
| com.vsl.checked_read | 2376 |
| com.sg.setter | 728 |
| com.sg.apply_read | 728 |
| com.sg.persistence_read | 784 |

Largest demand gap: input 1033 interval 1-4 DONE (line 105) → input 1033 interval 1-5 BEGIN (line 106): 0.300000 s.
Whole demand 2.789063 s; before reads 0.101563, setter/error handling 0.992188, after reads 1.101563 s. The gap does not isolate a single getter.

| Matched bucket | New − old seconds | New − old count |
|---|---:|---:|
| action.apply | -0.10156300000000007 | 0 |
| com.input_volume.read | 0.0 | 0 |
| com.input_volume.setter | 0.0 | 0 |
| com.sg.apply_read | 0.0 | -8944 |
| com.sg.head_owner_read | 0.0 | 0 |
| com.sg.head_read | 0.0 | 0 |
| com.sg.persistence_read | 0.0 | -8808 |
| com.sg.setter | 0.0 | -8944 |
| com.vehicle.physical_bulk_returned | 0.0 | 0 |
| com.vehicle.route_bulk_returned | 0.0 | 0 |
| com.vsl.checked_read | 0.0 | 0 |
| com.vsl.setter | 0.0 | 0 |
| decision.python | 0.0 | 0 |
| decision.total | -0.19531200000000126 | 0 |
| head.capture | -4.15625 | 0 |
| head.history | -0.21093700000000126 | 0 |
| head.seal | 0.13281199999999993 | 0 |
| head.signal_capture | -3.5078129999999987 | 0 |
| log.state_csv | -0.03906300000000007 | 0 |
| rampmeters.runtime | -8.765625 | 0 |
| scan.vehicles | -0.640625 | 0 |
| signals.readback | -4.304687 | -1101 |
| signals.runtime | 0.0 | 0 |
| sim.first_step | -0.21093700000000004 | 0 |
| sim.step | -0.17968700000000126 | 0 |
| startup.control_setup | 0.0 | 0 |
| startup.demand | 0.6640630000000001 | 0 |
| startup.demand.volume_after_read | 0.1718750000000001 | 0 |
| startup.demand.volume_before_read | 0.070313 | 0 |
| startup.demand.volume_set | 0.13281299999999996 | 0 |
| startup.head_init | 0.0 | 0 |
| startup.load_net | -0.8359369999999995 | 0 |
| state.json | -0.09375 | 0 |

Wrapper wall delta: 0.895626 s. No stable speedup estimate is certified.

| Derived wall remainder (not a pure speedup) | Old seconds | New seconds | New − old seconds |
|---|---:|---:|---:|
| excluding_demand_after_read | 302.287055 | 303.010806 | 0.723751 |
| excluding_whole_demand | 301.091743 | 301.323306 | 0.231563 |
| excluding_load_and_whole_demand | 291.810493 | 292.877993 | 1.067500 |

Interpretation limits:

- Wall is wrapper started->finished: startup, run, watchdog polling, exit observation and cleanup are included. It is not simulation-only or CPU time.
- PERF uses VBScript Timer wall seconds with midnight rollover; rounding/resolution limits small buckets. com.* sec=0 is an untimed count, not zero COM latency.
- Nested buckets must not be summed as exclusive wall time. startup.demand contains before/set/after; decision.total contains state.json/python/action.apply; head.capture contains scan.vehicles and signal capture; head.seal also contains signal capture. Vehicle scan is also called by state/log writers.
- Counted COM scope is only named instrumentation sites. It excludes enumeration/GetAll, object resolution, uninstrumented ownership/count/time getters, error-path attempts and other COM calls. Returned bulk counters are not vehicle counts.
- DONE->next BEGIN demand gaps include prior after-read, bookkeeping and next before-read. They localize a wait interval, not a single getter duration. Only the aggregate after-read PERF bucket identifies its total measured time.
- No independently timed postprocessing bucket exists here. Report it as unavailable; do not recover it by summing nested buckets or subtracting their sum from wall.
- Both arms use the same source/VSL sidecar and RW_PERF=1. Allowed switch differences are SG readback cadence and write-on-change only. Savings are conservative for the SG loop and do not separately estimate removed legacy VSL summary reads.
- Timing and source/config provenance do not certify identical physical commands, observations or trajectories. Use the separate completed pair verifier; no FZP/LSA/ERR/state payload is consumed here.
- One old/new pair is a descriptive observation, not a stable speedup benchmark. A startup readback wait can dominate wall independently of the SG-loop change.
