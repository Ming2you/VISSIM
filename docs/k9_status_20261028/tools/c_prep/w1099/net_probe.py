# net_probe.py — v3c3 망(.inpx)에서 FW_W 입구 둘레 객체를 읽기만 함 (탐색용)
import sys, xml.etree.ElementTree as ET, json
p = sys.argv[1]
tree = ET.parse(p); root = tree.getroot()
def tag(e): return e.tag.split('}')[-1]
links = {}
for ln in root.iter():
    if tag(ln) == 'link':
        no = int(ln.get('no'))
        d = {k: ln.get(k) for k in ('name','linkBehavType','displayType','isConn','level','lnChgDistDistrDef','lnChgDist')}
        lanes = [l for l in ln.iter() if tag(l) == 'lane']
        d['n_lanes'] = len(lanes)
        d['lane_widths'] = [l.get('width') for l in lanes]
        fl = [x for x in ln if tag(x) == 'fromLinkEndPt']; tl = [x for x in ln if tag(x) == 'toLinkEndPt']
        d['from'] = fl[0].get('lane') if fl else None
        d['fromPos'] = fl[0].get('pos') if fl else None
        d['to'] = tl[0].get('lane') if tl else None
        d['toPos'] = tl[0].get('pos') if tl else None
        # geometry length
        pts = [x for x in ln.iter() if tag(x) == 'point3D']
        import math
        L = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            L += math.hypot(float(b.get('x'))-float(a.get('x')), float(b.get('y'))-float(a.get('y')))
        d['poly_len'] = round(L, 1)
        links[no] = d
json.dump({str(k): v for k, v in links.items()}, open(sys.argv[2], 'w'), indent=0)
print(len(links))
