Completed execution timing; no physical-equivalence verdict.

Failed old signal r01 is excluded. Only explicitly supplied successful receipts are consumed.

codex_com_closed_loop_head_old_s13_1050_r01

Wrapper wall: 563.374051 s; terminal 1050 s; STEPWISE_PHYSICAL_HEAD_OBSERVATION.

| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |
|---|---:|---:|
| startup.load_net | 9.843750 | 1 |
| startup.demand | 2.203125 | 1 |
| startup.demand.volume_before_read | 0.078125 | 204 |
| startup.demand.volume_set | 0.867188 | 204 |
| startup.demand.volume_after_read | 0.937500 | 204 |
| startup.control_setup | 0.187500 | 1 |
| startup.head_init | 0.078125 | 1 |
| sim.first_step | 1.039063 | 1 |
| sim.step | 18.757813 | 1049 |
| decision.total | 282.492188 | 8 |
| state.json | 3.468750 | 8 |
| decision.python | 275.828125 | 8 |
| action.apply | 3.125000 | 8 |
| head.capture | 144.406250 | 1050 |
| head.history | 20.554688 | 1050 |
| head.seal | 2.976563 | 1050 |
| scan.vehicles | 62.304688 | 1058 |
| head.signal_capture | 83.273438 | 2100 |
| signals.runtime | 27.460938 | 1050 |
| rampmeters.runtime | 8.539063 | 1050 |
| signals.readback | 20.453125 | 1049 |

Actual simulation call total: 19.796876 s (first + subsequent calls only).

| Counted COM site; not total COM inventory | Count |
|---|---:|
| com.input_volume.read | 408 |
| com.input_volume.setter | 204 |
| com.vehicle.physical_bulk_returned | 4200 |
| com.sg.head_owner_read | 144586 |
| com.sg.head_read | 103650 |
| com.vehicle.route_bulk_returned | 32 |
| com.vsl.setter | 2112 |
| com.vsl.checked_read | 2112 |
| com.sg.setter | 29000 |
| com.sg.apply_read | 29000 |
| com.sg.persistence_read | 28792 |

Largest demand gap: input 1105 interval 1-6 DONE (line 411) → input 1106 interval 1-1 BEGIN (line 412): 0.020000 s.
Whole demand 2.203125 s; before reads 0.078125, setter/error handling 0.867188, after reads 0.937500 s. The gap does not isolate a single getter.

codex_com_closed_loop_head_new_s13_1050_r01

Wrapper wall: 522.399851 s; terminal 1050 s; STEPWISE_PHYSICAL_HEAD_OBSERVATION.

| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |
|---|---:|---:|
| startup.load_net | 9.664063 | 1 |
| startup.demand | 2.250000 | 1 |
| startup.demand.volume_before_read | 0.101563 | 204 |
| startup.demand.volume_set | 0.828125 | 204 |
| startup.demand.volume_after_read | 0.976563 | 204 |
| startup.control_setup | 0.156250 | 1 |
| startup.head_init | 0.078125 | 1 |
| sim.first_step | 0.914063 | 1 |
| sim.step | 18.421875 | 1049 |
| decision.total | 280.687500 | 8 |
| state.json | 3.320313 | 8 |
| decision.python | 274.242188 | 8 |
| action.apply | 3.046875 | 8 |
| head.capture | 153.640625 | 1050 |
| head.history | 21.335938 | 1050 |
| head.seal | 3.398438 | 1050 |
| scan.vehicles | 62.437500 | 1058 |
| head.signal_capture | 92.187500 | 2100 |
| signals.runtime | 2.867188 | 1050 |
| rampmeters.runtime | 0.085938 | 1050 |
| signals.readback | 0.593750 | 70 |

Actual simulation call total: 19.335938 s (first + subsequent calls only).

| Counted COM site; not total COM inventory | Count |
|---|---:|
| com.input_volume.read | 408 |
| com.input_volume.setter | 204 |
| com.vehicle.physical_bulk_returned | 4200 |
| com.sg.head_owner_read | 120341 |
| com.sg.head_read | 119169 |
| com.vehicle.route_bulk_returned | 32 |
| com.vsl.setter | 2112 |
| com.vsl.checked_read | 2112 |
| com.sg.setter | 550 |
| com.sg.apply_read | 550 |
| com.sg.persistence_read | 694 |

Largest demand gap: input 1096 interval 1-6 DONE (line 301) → input 1097 interval 1-1 BEGIN (line 302): 0.020000 s.
Whole demand 2.250000 s; before reads 0.101563, setter/error handling 0.828125, after reads 0.976563 s. The gap does not isolate a single getter.

| Matched bucket | New − old seconds | New − old count |
|---|---:|---:|
| action.apply | -0.078125 | 0 |
| com.input_volume.read | 0.0 | 0 |
| com.input_volume.setter | 0.0 | 0 |
| com.sg.apply_read | 0.0 | -28450 |
| com.sg.head_owner_read | 0.0 | -24245 |
| com.sg.head_read | 0.0 | 15519 |
| com.sg.persistence_read | 0.0 | -28098 |
| com.sg.setter | 0.0 | -28450 |
| com.vehicle.physical_bulk_returned | 0.0 | 0 |
| com.vehicle.route_bulk_returned | 0.0 | 0 |
| com.vsl.checked_read | 0.0 | 0 |
| com.vsl.setter | 0.0 | 0 |
| decision.python | -1.5859370000000013 | 0 |
| decision.total | -1.8046879999999987 | 0 |
| head.capture | 9.234375 | 0 |
| head.history | 0.78125 | 0 |
| head.seal | 0.421875 | 0 |
| head.signal_capture | 8.914062000000001 | 0 |
| rampmeters.runtime | -8.453125 | 0 |
| scan.vehicles | 0.13281200000000126 | 0 |
| signals.readback | -19.859375 | -979 |
| signals.runtime | -24.59375 | 0 |
| sim.first_step | -0.1250000000000001 | 0 |
| sim.step | -0.33593799999999874 | 0 |
| startup.control_setup | -0.03125 | 0 |
| startup.demand | 0.046875 | 0 |
| startup.demand.volume_after_read | 0.03906299999999996 | 0 |
| startup.demand.volume_before_read | 0.023438 | 0 |
| startup.demand.volume_set | -0.03906299999999996 | 0 |
| startup.head_init | 0.0 | 0 |
| startup.load_net | -0.17968699999999949 | 0 |
| state.json | -0.14843699999999993 | 0 |

Wrapper wall delta: -40.974200 s. No stable speedup estimate is certified.

| Derived wall remainder (not a pure speedup) | Old seconds | New seconds | New − old seconds |
|---|---:|---:|---:|
| excluding_demand_after_read | 562.436551 | 521.423288 | -41.013263 |
| excluding_whole_demand | 561.170926 | 520.149851 | -41.021075 |
| excluding_load_and_whole_demand | 551.327176 | 510.485788 | -40.841388 |

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
