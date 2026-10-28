# N34 (read-only): inpx facts around link 129 / 10490 and meter signal heads. Usage: python -B n3_inpx.py <inpx> <out.json>
import sys, json, hashlib, math
import xml.etree.ElementTree as ET
inpx, out = sys.argv[1], sys.argv[2]
raw = open(inpx, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
r = ET.fromstring(raw)
links = {}
for ln in r.iter('link'):
    no = int(ln.get('no'))
    pts = [(float(q.get('x')), float(q.get('y'))) for q in ln.iter('linkPolyPoint')]
    L = sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1))
    fr = ln.find('fromLinkEndPt'); to = ln.find('toLinkEndPt')
    nl = len(ln.find('lanes').findall('lane')) if ln.find('lanes') is not None else None
    links[no] = dict(len=L, lanes=nl, fr=fr.get('lane') if fr is not None else None, frpos=float(fr.get('pos')) if fr is not None else None,
                     to=to.get('lane') if to is not None else None, topos=float(to.get('pos')) if to is not None else None)
res = {'inpx': inpx, 'sha256': sha}
# connectors into / out of key links
KEY = {32, 129, 127, 10491, 26, 31}
conns = []
for no, v in links.items():
    if v['fr']:
        a = int(v['fr'].split()[0]); b = int(v['to'].split()[0])
        if a in KEY or b in KEY:
            conns.append({'no': no, 'from': v['fr'], 'frpos': v['frpos'], 'to': v['to'], 'topos': v['topos'], 'len': round(v['len'], 1), 'lanes': v['lanes']})
res['connectors'] = conns
# vehicle inputs on key links
vin = []
for vi in r.iter('vehicleInput'):
    if vi.get('link') and int(vi.get('link')) in KEY | {74}:
        vols = [(x.get('timeInt'), x.get('volume')) for x in vi.iter('vehicleInputVehicleVolume')]
        vin.append({'no': vi.get('no'), 'name': vi.get('name'), 'link': vi.get('link'), 'vols': vols})
res['vehicle_inputs'] = vin
# static routing decisions on key links or with routes passing 10490 / 10482 / 129
decs = []
for dec in r.iter('vehicleRoutingDecisionStatic'):
    L = int(dec.get('link'))
    routes = []
    hit = L in KEY
    for rt in dec.iter('vehicleRouteStatic'):
        ls = [x.get('key') for x in rt.iter('intObjectRef')]
        rf = rt.get('relFlow')
        routes.append({'no': rt.get('no'), 'dest': rt.get('destLink'), 'destPos': rt.get('destPos'), 'relFlow': rf, 'seq': ls})
        if rt.get('destLink') in ('10490', '129', '127', '10482') or any(x in ('10490', '129', '10778', '10777') for x in ls):
            hit = True
    if hit:
        decs.append({'no': dec.get('no'), 'name': dec.get('name'), 'link': L, 'pos': dec.get('pos'), 'allVehTypes': dec.get('allVehTypes'), 'routes': routes})
res['routing_decisions'] = decs
# meter signal heads (SC 9101..9108) and SC1001 heads on 127
heads = []
for sh in r.iter('signalHead'):
    sg = sh.get('sg') or ''
    sc = sg.split()[0] if sg else ''
    lane = sh.get('lane') or ''
    lk = int(lane.split()[0]) if lane else None
    if sc.startswith('91') or lk in (127, 129, 32, 10490, 10482):
        heads.append({'no': sh.get('no'), 'sg': sg, 'lane': lane, 'pos': float(sh.get('pos'))})
res['signal_heads'] = heads
res['links'] = {str(k): {'len': round(links[k]['len'], 2), 'lanes': links[k]['lanes'], 'fr': links[k]['fr'], 'to': links[k]['to']}
                for k in [32, 129, 127, 10491, 10490, 10482, 10778, 10777, 10484, 10480, 10639, 10681, 10646, 10644, 26, 31, 70, 68]}
json.dump(res, open(out, 'w', encoding='utf-8'), indent=1)
print(json.dumps({k: res[k] for k in ('vehicle_inputs', 'signal_heads')}, indent=0)[:4000])
for d in decs:
    print('DEC', d['no'], d['name'], 'link', d['link'], 'pos', d['pos'])
    for rt in d['routes']:
        print('   r', rt['no'], 'dest', rt['dest'], 'rf', rt['relFlow'], 'seq', rt['seq'][:12])
for c in conns:
    print('CONN', c)
