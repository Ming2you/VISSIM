"""K8 g2 (= sc1001eb g1_inpx.py with only the INPX path -> v3c3 NC fit seeds and the output path changed).
Outputs links/connectors/heads/route decisions/detectors touching links 26,127,129,32,10491,10481,10777,10778,10490 and their neighbours.
Also verifies the relevant elements are byte-identical across the 5 fit seeds."""
import xml.etree.ElementTree as ET, json, math, hashlib, sys, ctypes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import k8common as c  # noqa: E402
_ap = c.add_nc3(c.parser(__doc__))
c.apply(_ap.parse_args())
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
OUT = c.OUT / 'opt1v2' / 'out' / 'g2_inpx_v3c3.json'
OUT.parent.mkdir(parents=True, exist_ok=True)
SEEDS = (31, 41, 43, 47, 53)
CORE = {127, 129, 32, 10491, 10481, 10777, 10778, 10490}


def plen(el):
    pts = el.find('geometry/linkPolyPts')
    if pts is None:
        pts = el.find('geometry/points3D')
    if pts is None:
        return None
    P = [(float(p.get('x')), float(p.get('y'))) for p in pts]
    return sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1))


def parse(seed):
    path = str(c.NC3 / f's{seed}_v3c3nc' / 'prepared' / 'network' / f'baseline_s{seed}_v3c3nc.inpx')
    root = ET.parse(path).getroot()
    links = {}
    for l in root.iter('link'):
        no = int(l.get('no'))
        fr = l.find('fromLinkEndPt'); to = l.find('toLinkEndPt')
        lanes = l.find('lanes')
        links[no] = dict(no=no, name=l.get('name'), nlanes=len(lanes) if lanes is not None else None,
                         widths=[ln.get('width') for ln in lanes] if lanes is not None else None,
                         length_poly=plen(l), behav=l.get('linkBehavType'), lnChgDist=l.get('lnChgDist'),
                         emergStopDist=l.get('emergStopDist'),
                         frm=(fr.get('lane'), float(fr.get('pos'))) if fr is not None else None,
                         to=(to.get('lane'), float(to.get('pos'))) if to is not None else None)
    rel = set(CORE)
    for no, d in links.items():
        if d['frm'] is not None:
            fl = int(d['frm'][0].split()[0]); tl = int(d['to'][0].split()[0])
            if fl in CORE or tl in CORE:
                rel.add(no); rel.add(fl); rel.add(tl)
    heads = []
    for h in root.iter('signalHead'):
        ln = int(h.get('lane').split()[0])
        if ln in rel or h.get('sg', '').startswith('1001 '):
            heads.append(dict(no=h.get('no'), lane=h.get('lane'), pos=float(h.get('pos')), sg=h.get('sg'), type=h.get('type')))
    rds = []
    for tag in ('vehicleRoutingDecisionStatic', 'staticVehicleRoutingDecision'):
        for rd in root.iter(tag):
            ln = int(rd.get('link'))
            if ln in rel or ln == 26:
                routes = []
                for r in rd.iter('vehicleRouteStatic'):
                    lseq = r.find('linkSeq')
                    seq = [int(x.get('key')) for x in lseq] if lseq is not None else []
                    routes.append(dict(no=r.get('no'), relFlow=r.get('relFlow'), destLink=r.get('destLink'), destPos=r.get('destPos'), seq=seq))
                rds.append(dict(no=rd.get('no'), link=ln, pos=float(rd.get('pos')), allVeh=rd.get('allVehTypes'), routes=routes, attrs={k: v for k, v in rd.attrib.items() if k not in ('no', 'link', 'pos')}))
    sc = None
    for c in root.iter('signalController'):
        if c.get('no') == '1001':
            sc = dict(c.attrib)
            sc['sgs'] = [dict(g.attrib) for g in c.iter('signalGroup')]
    dets = []
    for d in root.iter('detector'):
        ln = int(d.get('lane').split()[0])
        if ln in rel:
            dets.append(dict(no=d.get('no'), lane=d.get('lane'), pos=d.get('pos'), length=d.get('length'), name=d.get('name')))
    pr = []
    for p in root.iter('priorityRule'):
        txt = ET.tostring(p, encoding='unicode')
        if any(f'lane="{x} ' in txt for x in CORE):
            pr.append(txt[:600])
    cz = []
    for z in root.iter('conflictArea'):
        l1 = int(z.get('link1')); l2 = int(z.get('link2'))
        if l1 in rel or l2 in rel:
            cz.append(dict(z.attrib))
    sub = {k: links[k] for k in sorted(rel) if k in links}
    return dict(links=sub, heads=heads, rds=rds, sc1001=sc, detectors=dets, priority=pr, conflicts=cz)


res = {}
for s in SEEDS:
    res[s] = parse(s)
    print(s, 'links', len(res[s]['links']), 'heads', len(res[s]['heads']), 'rds', len(res[s]['rds']), flush=True)
h = {s: hashlib.sha256(json.dumps(res[s], sort_keys=True).encode()).hexdigest()[:12] for s in SEEDS}
print('per-seed extract sha', h)
json.dump(dict(seed31=res[31], extract_sha=h), open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
