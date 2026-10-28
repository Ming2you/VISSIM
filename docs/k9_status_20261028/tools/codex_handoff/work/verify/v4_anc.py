# VERIFY: 64cf static routes vs v2nc / v3c3 (read only)
import xml.etree.ElementTree as ET, re
P = {"64cf": "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx",
     "v2nc": "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/net/v2nc.inpx",
     "v3c3": "D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx"}
def dec(p):
    r = ET.parse(p).getroot()
    return {e.get("no"): re.sub(r"\s+", "", ET.tostring(e, encoding="unicode")) for e in r.iter("vehicleRoutingDecisionStatic")}, \
           {e.get("no"): re.sub(r"\s+", "", ET.tostring(e, encoding="unicode")) for e in r.iter("desSpeedDistribution")}, \
           {e.get("no"): (e.get("lane"), e.get("pos")) for e in r.iter("desSpeedDecision")}, \
           {e.get("no"): re.sub(r"\s+", "", ET.tostring(e, encoding="unicode")) for e in r.iter("vehicleInput")}
D = {k: dec(v) for k, v in P.items()}
for other in ["v2nc", "v3c3"]:
    a, b = D["64cf"], D[other]
    rd = [k for k in set(a[0]) | set(b[0]) if a[0].get(k) != b[0].get(k)]
    sd = [k for k in set(a[1]) | set(b[1]) if a[1].get(k) != b[1].get(k)]
    dd = [k for k in set(a[2]) | set(b[2]) if a[2].get(k) != b[2].get(k)]
    vd = [k for k in set(a[3]) | set(b[3]) if a[3].get(k) != b[3].get(k)]
    print(f"64cf vs {other}: routing decisions differing/missing {len(rd)}; DSD dists {sorted(sd)}; DSD decisions {sorted(dd, key=int)}; inputs {sorted(vd)}")
