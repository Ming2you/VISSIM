# FW g9: actual execution confirmed

Run `codex_native_clock_fw080_u050_fw9_v1` completed1050 seconds; owned PID45292 exited. Bounded native evidence audit took about0.53 seconds, without FZP/model reads or production edits.

Both actual action CSVs at900 and1050 contain213 physical rows exactly matching the pinned preflight after excluding metadata. Compared with the completed open-v2 run, only RM_C10646 and RM_C10644, physical SG9103:1 and9104:1, differ: green10→9 and rate900→810. Urban and VSL command fields remain identical.

Actual native LDP after application, t901–1050, shows each target meter GREEN135 seconds and AMBER15 seconds, with RED0. AMBER occurs exactly at910,920,…,1050. All other six meters remain GREEN throughout. The t900 frame precedes the new application and remains GREEN, so the inclusive900–1050 target totals are136 GREEN and15 AMBER. All1,208 inclusive meter state samples match their application clock.

Urban native LDP900–1050 matches source `.sig(t)` for all20,536 samples, with zero mismatches. VSL has2,112 successful immediate readbacks:66 DSDs ×4 vehicle classes ×8 application times, all requested and read back at120 km/h.

The command/LDP execution gate passes. Native LSA remains independently failing:5,681 native events and555 of575 actual COM events missing. No events were synthesized or substituted.

The g9 command creates9 seconds GREEN plus1 second AMBER, with no RED interval. Its encoded rate810 is not evidence of a10% actual capacity or flow reduction; the separate trajectory/discharge comparison must establish any traffic effect.

Detailed ordered CSV differences, native state counts/timestamps, VSL counts and source pins are in `native_fw9_v1_actual_execution_audit.json`.
