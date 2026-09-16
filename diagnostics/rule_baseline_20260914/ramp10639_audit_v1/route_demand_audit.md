# RM10639 configured destination demand audit

Runs: NC rule100_none3000_s13_v1; RM rule100_rm3000_s13_v2.

**Finding:** The configured destination demand is small: input1101 on link69 sends 3/(12+1+3+0.25)=12/65 to route1134:3, following69→10637→70→10639→2. It implies **72.3 expected source-generated vehicles during900–3000s**. This is not the same cohort as66 measured ramp crossings in the same clock window.

| Source interval (s) | Input1101 (veh/h) | Desired10639 (veh/h) | Expected origin vehicles inside900–3000 |
|---|---:|---:|---:|
| 0–900 | 467.0 | 86.215 | 0.000 |
| 900–1800 | 666.5 | 123.046 | 30.762 |
| 1800–2700 | 700.0 | 129.231 | 32.308 |
| 2700–3600 | 600.0 | 110.769 | 9.231 |
| 3600–4500 | 467.0 | 86.215 | 0.000 |
| 4500–5400 | 333.5 | 61.569 | 0.000 |

Evidence and limits:

- Both actual run recording XMLs have identical1133/1134/1140 route subtrees. The only explicit static route containing10639 is1134:3. Input1101 is the only input on69/70, and69 has no incoming connector.
- Selected runtime multiplier is0.5 in both launch.json files; all six input1101 startup BEGIN/DONE pairs agree with the table above. Stored recording INPX keeps pre-COM input volumes; do not read those as runtime demand. The log does not print each1101 after-readback value.
- Empty relFlow on1134:2 is interpreted as implicit1 by the existing canonical parser/completed route audit. No fresh COM readback was performed here.
- Link70 also accepts10638 from freeway link120. Its1133:2 complete route selects city exit10776, so road70 occupancy is not ramp10639 destination demand.
- Downstream1140 exists at70@67.915m, but all its routes select10776 and none10639. Presence alone is not evidence that a valid1134:3 route is overwritten. Parent separately inspected native vehicle-route persistence.
- No FZP scan, simulation, model evaluation, source/configuration change or process intervention in this audit.

Full XML identities, startup evidence and expected-demand arithmetic: route_demand_audit.json.
