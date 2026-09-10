# Native error complete capture
Run: codex_contract_observed_nc_s13_1050_v2_20260910; run ID: 787fedf55fc1494b820d8e2665c2c925.
Explicit removals: 10; Ω {'outside': 5, 'inside': 5}; inside terminal removals: 0.
Runtime warning categories: {'ignored_static_routing': 28, 'ignored_desired_speed': 22, 'lane_change_removal': 10, 'duplicate_travel_time_section_start': 23, 'simulation_stop_prompt_answer': 1, 'unfinished_vehicle_input': 1, 'signal_controller_dll_error_notice': 1}.
Raw runtime bytes: 16171; complete-line prefix: 16171; partial tail: 0.

| Interval | Native removals | Inside | Cached unknown | Exact ID join |
|---|---:|---:|---:|---:|

A prefix omits unflushed/later native warnings; use complete capture after SIM_DONE.
A locked empty DLL log is reported as unreadable, not asserted to be a captured empty file.
Explicit lane-change removal is not an outward crossing. Interior loss already excluded from TD can reduce TTT and truncate congestion.
No vehicle-ID blacklist is created. Earlier observed outward crossings by a later-removed vehicle remain valid TD; only the deletion disappearance is classified here.
No terminal24/120 native removal in this captured prefix means no demonstrated contamination of that terminal inference by these warnings; it does not prove future warnings absent.
No measurement or production code was changed; duplicate travel-time-section warnings are separate records, not vehicle removals.
Network/run manifest and times support association, but native ERR has no embedded run ID. This is not a cryptographic native-run binding.
