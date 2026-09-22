# Selected FW80 urban90 — native RM/VSL comparison

User-selected canonical traffic scenario,2026-09-22. Baseline completed NC9000 seed23 is referenced in selected_scenario.json; source hash86af2ac85090e34bd3725c6e50230c356d1c2ffdd93ac5cf693c8167f074a83c. No demand/routing/geometry/native urban signal changes. Final4500s demand continues to9000.

Finite queue:RM9000, VSL9000, both9000; reuse completed NC.8ALINEA meters (target15%, gain70veh/h/pct/lane; RG10s,min2,max10,+/-2s/update).8ruleVSL zones with60/80/120 speed distribution IDs.900s control start,150s decisions. SimRes10, FZP5s. Native LDP+command/readback gate, native errors retained; no plant/MPC/live vehicle census or performance analysis. Rule parameters remain exploratory, not newly optimized for this demand.

18unit tests passed; prepared physical sections and all snapshot hashes checked. Only existing preparer terminal choices and existing queue/plot labels were extended; controller/actuator timing unchanged. Automatic per-run east heatmaps after completion, no simultaneous heavy analysis. The preceding old queue stays stopped and its automation paused. STOP in THIS directory prevents later jobs; failure logs are preserved, no automatic retry. Read queue_status.json and PID creation identities before intervening.
