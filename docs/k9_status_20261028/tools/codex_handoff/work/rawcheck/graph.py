import xml.etree.ElementTree as ET, json
P = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/network/sdmpc31_sdmpc8100_s29.inpx"
root = ET.parse(P).getroot()
pred = {}; length = {}
for l in root.find("links").findall("link"):
    no = l.get("no")
    f = l.find("fromLinkEndPt"); t = l.find("toLinkEndPt")
    if f is not None:
        fl = f.get("lane").split()[0]; tl = t.get("lane").split()[0]
        pred.setdefault(no, set()).add(fl)
        pred.setdefault(tl, set()).add(no)
    # length from geometry points
    pts = [(float(p.get("x")), float(p.get("y"))) for p in l.iter("point3D")] or [(float(p.get("x")), float(p.get("y"))) for p in l.iter("linkPolyPt")]
    L = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        L += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    length[no] = L
json.dump(dict(pred={k: sorted(v) for k, v in pred.items()}, length=length), open("graph_64cf.json", "w"))
inp = json.load(open("inputs_64cf.json", encoding="utf-8"))
inlinks = {v["link"]: k for k, v in inp.items()}
for x in ["1210012103", "1220012001", "199", "10350", "1220009503", "10269", "10319", "10359", "10381", "10585", "1210008203", "10584"]:
    chain = []
    cur = [x]; seen = set()
    for hop in range(4):
        nxt = []
        for c in cur:
            for p in pred.get(c, []):
                if p in seen: continue
                seen.add(p); nxt.append(p)
        hit = [p for p in nxt if p in inlinks]
        if hit:
            chain.append((hop + 1, [(h, inlinks[h], round(length.get(h, 0), 1)) for h in hit])); break
        cur = nxt
    print(x, "len", round(length.get(x, 0), 1), "pred", sorted(pred.get(x, [])), "->", chain)
print("input link lengths:", {k: round(length.get(v["link"], 0), 1) for k, v in inp.items()})
