Completed execution timing; no physical-equivalence verdict.

Failed old signal r01 is excluded. Only explicitly supplied successful receipts are consumed.

codex_com_signal_head_old_s13_1200_r02

Wrapper wall: 461.835149 s; terminal 1200 s; STEPWISE_PHYSICAL_HEAD_OBSERVATION.

| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |
|---|---:|---:|
| startup.load_net | 8.234375 | 1 |
| startup.demand | 105.187500 | 1 |
| startup.demand.volume_before_read | 0.515625 | 204 |
| startup.demand.volume_set | 1.554688 | 204 |
| startup.demand.volume_after_read | 101.476563 | 204 |
| startup.control_setup | 0.140625 | 1 |
| startup.head_init | 0.070313 | 1 |
| sim.first_step | 0.890625 | 1 |
| sim.step | 19.679688 | 1199 |
| decision.total | 18.164063 | 9 |
| state.json | 3.546875 | 9 |
| decision.python | 10.554688 | 9 |
| action.apply | 3.984375 | 9 |
| head.capture | 152.710938 | 1200 |
| head.history | 25.617188 | 1200 |
| head.seal | 3.437500 | 1200 |
| scan.vehicles | 76.789063 | 1250 |
| head.signal_capture | 79.507813 | 2400 |
| signals.runtime | 52.523438 | 1200 |
| rampmeters.runtime | 8.804688 | 1200 |
| signals.readback | 35.648438 | 1199 |
| log.state_csv | 3.421875 | 41 |

Actual simulation call total: 20.570313 s (first + subsequent calls only).

| Counted COM site; not total COM inventory | Count |
|---|---:|
| com.input_volume.read | 408 |
| com.input_volume.setter | 204 |
| com.vehicle.physical_bulk_returned | 4800 |
| com.sg.head_owner_read | 186436 |
| com.sg.head_read | 104700 |
| com.vehicle.route_bulk_returned | 36 |
| com.vsl.setter | 2376 |
| com.vsl.checked_read | 2376 |
| com.sg.setter | 50608 |
| com.sg.apply_read | 50608 |
| com.sg.persistence_read | 50392 |

Largest demand gap: input 1082 interval 1-4 DONE (line 189) → input 1082 interval 1-5 BEGIN (line 190): 101.680000 s.
Whole demand 105.187500 s; before reads 0.515625, setter/error handling 1.554688, after reads 101.476563 s. The gap does not isolate a single getter.

codex_com_signal_head_new_s13_1200_r01

Wrapper wall: 302.330683 s; terminal 1200 s; STEPWISE_PHYSICAL_HEAD_OBSERVATION.

| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |
|---|---:|---:|
| startup.load_net | 7.632813 | 1 |
| startup.demand | 2.218750 | 1 |
| startup.demand.volume_before_read | 0.054688 | 204 |
| startup.demand.volume_set | 0.906250 | 204 |
| startup.demand.volume_after_read | 0.882813 | 204 |
| startup.control_setup | 0.179688 | 1 |
| startup.head_init | 0.078125 | 1 |
| sim.first_step | 0.890625 | 1 |
| sim.step | 20.882813 | 1199 |
| decision.total | 18.984375 | 9 |
| state.json | 3.898438 | 9 |
| decision.python | 10.960938 | 9 |
| action.apply | 4.078125 | 9 |
| head.capture | 181.328125 | 1200 |
| head.history | 24.578125 | 1200 |
| head.seal | 3.640625 | 1200 |
| scan.vehicles | 76.703125 | 1250 |
| head.signal_capture | 108.031250 | 2400 |
| signals.runtime | 5.671875 | 1200 |
| rampmeters.runtime | 0.070313 | 1200 |
| signals.readback | 1.054688 | 143 |
| log.state_csv | 3.484375 | 41 |

Actual simulation call total: 21.773438 s (first + subsequent calls only).

| Counted COM site; not total COM inventory | Count |
|---|---:|
| com.input_volume.read | 408 |
| com.input_volume.setter | 204 |
| com.vehicle.physical_bulk_returned | 4800 |
| com.sg.head_owner_read | 137839 |
| com.sg.head_read | 135857 |
| com.vehicle.route_bulk_returned | 36 |
| com.vsl.setter | 2376 |
| com.vsl.checked_read | 2376 |
| com.sg.setter | 876 |
| com.sg.apply_read | 876 |
| com.sg.persistence_read | 1186 |

Largest demand gap: input 194 interval 1-6 DONE (line 49) → input 282 interval 1-1 BEGIN (line 50): 0.020000 s.
Whole demand 2.218750 s; before reads 0.054688, setter/error handling 0.906250, after reads 0.882813 s. The gap does not isolate a single getter.

| Matched bucket | New − old seconds | New − old count |
|---|---:|---:|
| action.apply | 0.09375 | 0 |
| com.input_volume.read | 0.0 | 0 |
| com.input_volume.setter | 0.0 | 0 |
| com.sg.apply_read | 0.0 | -49732 |
| com.sg.head_owner_read | 0.0 | -48597 |
| com.sg.head_read | 0.0 | 31157 |
| com.sg.persistence_read | 0.0 | -49206 |
| com.sg.setter | 0.0 | -49732 |
| com.vehicle.physical_bulk_returned | 0.0 | 0 |
| com.vehicle.route_bulk_returned | 0.0 | 0 |
| com.vsl.checked_read | 0.0 | 0 |
| com.vsl.setter | 0.0 | 0 |
| decision.python | 0.40625 | 0 |
| decision.total | 0.8203120000000013 | 0 |
| head.capture | 28.617187 | 0 |
| head.history | -1.0390629999999987 | 0 |
| head.seal | 0.203125 | 0 |
| head.signal_capture | 28.523437 | 0 |
| log.state_csv | 0.0625 | 0 |
| rampmeters.runtime | -8.734375 | 0 |
| scan.vehicles | -0.08593799999999874 | 0 |
| signals.readback | -34.59375 | -1056 |
| signals.runtime | -46.851563 | 0 |
| sim.first_step | 0.0 | 0 |
| sim.step | 1.203125 | 0 |
| startup.control_setup | 0.03906299999999999 | 0 |
| startup.demand | -102.96875 | 0 |
| startup.demand.volume_after_read | -100.59375 | 0 |
| startup.demand.volume_before_read | -0.460937 | 0 |
| startup.demand.volume_set | -0.6484380000000001 | 0 |
| startup.head_init | 0.0078119999999999995 | 0 |
| startup.load_net | -0.6015620000000004 | 0 |
| state.json | 0.35156300000000007 | 0 |

Wrapper wall delta: -159.504466 s. No stable speedup estimate is certified.

| Derived wall remainder (not a pure speedup) | Old seconds | New seconds | New − old seconds |
|---|---:|---:|---:|
| excluding_demand_after_read | 360.358586 | 301.447870 | -58.910716 |
| excluding_whole_demand | 356.647649 | 300.111933 | -56.535716 |
| excluding_load_and_whole_demand | 348.413274 | 292.479120 | -55.934154 |

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
