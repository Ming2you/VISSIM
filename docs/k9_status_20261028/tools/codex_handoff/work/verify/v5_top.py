# VERIFY: top-level group equality 64cf vs v3c3 (read only)
import xml.etree.ElementTree as ET, re, hashlib, os, glob
A = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx"
B = "D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx"
ra, rb = ET.parse(A).getroot(), ET.parse(B).getroot()
ca = {c.tag: re.sub(r"\s+", "", ET.tostring(c, encoding="unicode")) for c in ra}
cb = {c.tag: re.sub(r"\s+", "", ET.tostring(c, encoding="unicode")) for c in rb}
tags = sorted(set(ca) | set(cb))
same = [t for t in tags if ca.get(t) == cb.get(t)]
diff = [t for t in tags if ca.get(t) != cb.get(t)]
print("top-level groups", len(tags), "same", len(same), "differ", len(diff), diff)
for t in ["signalControllers", "dataCollectionPoints", "dataCollectionMeasurements"]:
    print(t, len(list(ra.find(t))) if ra.find(t) is not None else None, len(list(rb.find(t))) if rb.find(t) is not None else None)
def sigs(d):
    return {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in glob.glob(d + "/*.sig")}
sa = sigs(os.path.dirname(A)); sb = sigs(os.path.dirname(B))
print(".sig files", len(sa), len(sb), "common", len(set(sa) & set(sb)), "same bytes", sum(1 for k in set(sa) & set(sb) if sa[k] == sb[k]))
