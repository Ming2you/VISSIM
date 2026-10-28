# VERIFY_NEXT: FW_E mainline chain from inpx geometry (read-only). Usage: python -B vn_inpx_chain.py <inpx> <out.json>
import sys, json, math, hashlib
import xml.etree.ElementTree as ET

inpx, out = sys.argv[1], sys.argv[2]
raw = open(inpx, 'rb').read()
sha = hashlib.sha256(raw).hexdigest()
root = ET.fromstring(raw)
links = {}
for ln in root.iter('link'):
    no = int(ln.get('no'))
    pts = [(float(p.get('x')), float(p.get('y'))) for p in ln.iter('linkPolyPoint')]
    L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
    fr = ln.find('fromLinkEndPt'); to = ln.find('toLinkEndPt')
    nl = len(ln.find('lanes').findall('lane')) if ln.find('lanes') is not None else None
    links[no] = {'len2d': L, 'lanes': nl,
                 'from': (int(fr.get('lane').split()[0]), float(fr.get('pos'))) if fr is not None else None,
                 'to': (int(to.get('lane').split()[0]), float(to.get('pos'))) if to is not None else None}
seq = [74, 10699, 2, 10613, 119, 10702, 24]
chain = {74: 0.0}
chain_sumlen = {74: 0.0}
for i in range(1, len(seq), 2):
    a, c, b = seq[i - 1], seq[i], seq[i + 1]
    ca = links[c]
    assert ca['from'][0] == a and ca['to'][0] == b, (a, c, b, ca)
    chain[c] = chain[a] + ca['from'][1]
    chain[b] = chain[c] + ca['len2d'] - ca['to'][1]
    chain_sumlen[c] = chain_sumlen[a] + links[a]['len2d']
    chain_sumlen[b] = chain_sumlen[c] + ca['len2d']
merges = {}
for m in [10639, 10681, 10490, 10484, 10481, 10483, 10643, 10682]:
    x = links.get(m)
    if x is None: continue
    tl, tp = x['to']; fl, fp = x['from']
    merges[m] = {'from': [fl, fp], 'to': [tl, tp], 'len2d': x['len2d'], 'lanes': x['lanes'],
                 'chain_to_geom': (chain[tl] + tp) if tl in chain else None,
                 'chain_from_geom': (chain[fl] + fp) if fl in chain else None}
res = {'inpx': inpx, 'sha256': sha,
       'mainline': {str(k): {'len2d': links[k]['len2d'], 'lanes': links[k]['lanes'], 'chain_start_geom': chain[k],
                             'chain_start_sumlen': chain_sumlen[k]} for k in seq},
       'ramps': {str(k): v for k, v in merges.items()}}
json.dump(res, open(out, 'w', encoding='utf-8'), indent=1)
print(json.dumps(res['mainline'], indent=1))
print(json.dumps({k: (v['chain_to_geom'], v['chain_from_geom'], v['lanes']) for k, v in res['ramps'].items()}, indent=1))
