# Actual optimizer t900 consumer alignment

PASS: the installed main decision was consumed by the canonical VBS with fake COM. All 213 original CSV rows survived the reader unchanged; 17 signal axes and 122 SG windows match the final action and selected mainline plan. The independently calculated t900 event matches all 144 requested/readback states (136 urban SGs and 8 meter SGs), with zero mismatches.

The producer records phase refinement before scoring (57 changed phase values), outer-return equality, meter finalization before scoring, and writer/scored meter equality. The cached meter context and four realized group rates match the final action. All eight physical meters request 10 s green. Each CSV rate is 900 veh/h = 10 s × nominal 900 veh/h / 10 s. This is an equivalent command rate, not measured throughput. R_F_W's model group rate is 1599.747393 veh/h while its two physical meters are fully open; the existing measured-table prediction and the two nominal CSV rates are distinct quantities.

All 44 final model VSL values and 66 mapped DSD rows are 120 km/h; the canonical setter checks classes 10, 20, 30 and 70, and the action log records matching 10/70 readback for all 66 rows. Thirteen optimizer-selected nonzero offsets were accepted under experiment mode. Production writes remain zero and promotion remains NOT_EVALUATED.

This establishes the stored finalization/serialization/consumer chain, using runtime assertions for the scored phase and RM vector. It does not independently reconstruct the optimizer cost, provide a VSL scoring-vector hash, prove live actuator authority, or validate later event/failure paths. No VISSIM or optimizer was rerun and all audited input hashes remained unchanged. The first sandboxed WSH attempt was denied access to its settings; the separate authorized WSH retry exited 0.

Evidence: `optimizer900_actuation_alignment.json`, `optimizer900_consumer_20260910_wsh/result.json`, `actionFile.csv`, `signalTraceFile.csv`, and the original preflight manifest.
