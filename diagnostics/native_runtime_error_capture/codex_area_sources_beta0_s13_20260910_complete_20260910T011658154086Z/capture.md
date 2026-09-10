# Native error complete capture
Run: codex_area_sources_beta0_s13_20260910; run ID: 329913b3a1a747948d4b5196242254c5.
Explicit removals: 386; Ω {'outside': 205, 'inside': 181}; inside terminal removals: 0.
Runtime warning categories: {'ignored_static_routing': 232, 'ignored_desired_speed': 160, 'lane_change_removal': 386, 'duplicate_travel_time_section_start': 649, 'route_next_link_not_found': 17, 'simulation_stop_prompt_answer': 1, 'unfinished_vehicle_input': 3, 'signal_controller_dll_error_notice': 1}.
Raw runtime bytes: 296590; complete-line prefix: 296590; partial tail: 0.

| Interval | Native removals | Inside | Cached unknown | Exact ID join |
|---|---:|---:|---:|---:|
| [900, 1050] | 4 | 1 | 4 | 1 |
| [1200, 1350] | 4 | 0 | 1 | 0 |
| [3300, 3450] | 11 | 5 | 11 | 5 |

A prefix omits unflushed/later native warnings; use complete capture after SIM_DONE.
A locked empty DLL log is reported as unreadable, not asserted to be a captured empty file.
Explicit lane-change removal is not an outward crossing. Interior loss already excluded from TD can reduce TTT and truncate congestion.
No vehicle-ID blacklist is created. Earlier observed outward crossings by a later-removed vehicle remain valid TD; only the deletion disappearance is classified here.
No terminal24/120 native removal in this captured prefix means no demonstrated contamination of that terminal inference by these warnings; it does not prove future warnings absent.
No measurement or production code was changed; duplicate travel-time-section warnings are separate records, not vehicle removals.
Network/run manifest and times support association, but native ERR has no embedded run ID. This is not a cryptographic native-run binding.
