import xml.etree.ElementTree as ET, json, hashlib
P = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/network/sdmpc31_sdmpc8100_s29.inpx"
print("sha", hashlib.sha256(open(P, "rb").read()).hexdigest())
root = ET.parse(P).getroot()
ti = {}
for t in root.iter("timeInterval"):
    ti[t.get("no")] = t.attrib
vi = root.find("vehicleInputs")
out = {}
for v in vi.findall("vehicleInput"):
    no = v.get("no"); link = v.get("link")
    vols = []
    for tv in v.iter("timeIntervalVehVolume"):
        vols.append(dict(tv.attrib))
    out[no] = dict(name=v.get("name"), link=link, anm=v.get("anmFlag"), vols=vols)
print(len(out))
k0 = list(out)[0]; print(k0, json.dumps(out[k0], ensure_ascii=False)[:800])
from collections import Counter
print(Counter(o["link"] for o in out.values()).most_common(5))
print(sorted({tv.get("volType") for o in out.values() for tv in o["vols"]}))
# timeInterval sets for vehicle inputs
tis = [t for t in root.iter("timeIntervalSet")]
for s in tis:
    print("set", s.attrib, [(t.get("no"), t.get("start")) for t in s.iter("timeInterval")][:12])
json.dump(out, open("inputs_64cf.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
# links lengths
L = {}
for l in root.find("links").findall("link"):
    geo = l.find("geometry")
    L[l.get("no")] = dict(name=l.get("name"), conn=l.find("fromLinkEndPt") is not None)
print("links", len(L), "connectors", sum(1 for x in L.values() if x["conn"]))
