# SC1004 counterfactual preparation paused

Paused before config generation or execution after the user prioritized three-arm no-control5400 comparison. No counterfactual config, action CSV, adapter execution, model or COM run was produced.

The intended immutable base was diagnostics/fixed_beta300v3_900_signal_profile/config.json, retaining the original beta300v3 action900 (213 physical rows) and baseline network. The canonical diagnostic_signal_profile already accepts the requested two modifications.

- A: relative_offset_sec.SC1004 = +18.75; writer offset56.25→75. Phase greens remain p1=21.999,p2=22.667,p3=70.667,p4=22.667.
- B: green_delta_sec.SC1004_p3 = −18 and SC1004_p4 = +18; relative offset remains0 (writer56.25). New p3=52.667,p4=40.667; sum green138 and cycle150 remain unchanged.

Read-only plan inspection: SC1004 phase order p2,p1,p3,p4; each phase has3seconds clearance. p4 serves SG1/SG5. Baseline SG5 plan window[124.333,147), global first post900 window[968.083,990.750), integer first GREEN969. A shifts this to[949.333,972.000), integer first GREEN950. B changes it to[950.083,990.750), integer first GREEN951. These are hand-derived continuous/1-second clock expectations from the recorded rows and formula pos=(simSec+offset) mod150, not an executed new oracle or native readback.

Other SCs, VSL, meters, warmup and baseline network were intended to stay unchanged; that proposal has not been materialized or validated. Resume only after the higher-priority no-control5400 comparison.
