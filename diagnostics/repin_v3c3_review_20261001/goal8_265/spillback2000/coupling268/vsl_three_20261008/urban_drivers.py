"""Read cached matched snapshots and sparse detector totals; no simulation calls."""
from pathlib import Path
import csv, hashlib, json, math, xml.etree.ElementTree as ET
import numpy as np
from urban_diagnostic import RUNS, ROOT

OUT=Path(__file__).parent/'urban_diagnostic_to6150'
z=np.load(OUT/'link_arrays.npz'); times=z['times']; links=list(z['links'])
lanes=json.loads((OUT/'lane_stocks.json').read_text(encoding='utf-8'))
commands=json.loads((OUT/'commands.json').read_text(encoding='utf-8'))
detpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/obs150/obs150_detectors_v2.csv'
dets=list(csv.DictReader(detpath.open(encoding='utf-8-sig')))
periods=[(900,1800),(1800,3000),(3000,4500),(4500,6150),(900,6150)]
out=[]; captures=[]; lane_totals=[]; proof={}
network=RUNS['head47']/'network/sdmpc31_sdmpc8100_s29.inpx'
root=ET.parse(network).getroot(); nodes={int(x.get('no')):x for x in root.findall('.//links/link')}
edges=[]
for x in nodes.values():
    a=x.find('fromLinkEndPt'); b=x.find('toLinkEndPt')
    if a is not None and b is not None and (int(a.get('lane').split()[0]) in [52,66,68] or int(b.get('lane').split()[0]) in [52,66,68]):
        edges.append(dict(connector=int(x.get('no')),source=a.attrib,destination=b.attrib))
for label,run in RUNS.items():
    decisions=next(run.glob('decisions_*')); states={}
    for t in [900,1800,3000,4500,6150]:
        f=decisions/f'state_{t:06d}.json';raw=f.read_bytes();proof[str(f)]=hashlib.sha256(raw).hexdigest()
        states[t]=json.loads(raw)['obs150']['detectors_cum']
    for a,b in periods:
        sig=[r for r in commands[label]['signals'] if r['sc']==1004 and a<=r['time']<b]
        rm=[r['green'] for r in commands[label]['rm'] if r['ramp']==10681 and a<=r['time']<b]
        flows=[]
        for link in [52,66,10681]:
            for lane in range(1,5):
                ds=[d for d in dets if int(d['link'])==link and int(d['lane'])==lane and d['role'] in ['head','meter_head']]
                if ds: flows.append(dict(link=link,lane=lane,passages=sum(states[b][d['dcm_no']]-states[a][d['dcm_no']] for d in ds)))
        out.append(dict(run=label,start=a,end=b,sc1004_mean_phase_green=np.mean([r['greens'] for r in sig],axis=0).tolist() if sig else None,
                        rm10681_mean_green=float(np.mean(rm)) if rm else None,rm10681_two_second_blocks=sum(g<=2 for g in rm),head_passages=flows))
    for t in [1800,2400,3000,3300,4500,5700,6150]:
        j=list(times).index(t)
        captures.append(dict(run=label,time=t,links={str(n):dict(n=int(z[label+'_stock'][j,links.index(n)]),stopped=int(z[label+'_stopped'][j,links.index(n)])) for n in [52,66,68,10681]}))
    for link in [52,66,68]:
        node=nodes[link]; pts=[(float(x.get('x')),float(x.get('y'))) for x in node.findall('.//linkPolyPoint')]
        length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        for lane in range(1,5):
            rows={r['time']:r for r in lanes if r['run']==label and r['link']==link and r['lane']==lane}
            ns=np.array([rows.get(t,{}).get('n',0) for t in times]); stops=np.array([rows.get(t,{}).get('stopped',0) for t in times])
            tails=[r['tail_pos'] for r in rows.values() if r['tail_pos'] is not None]
            lane_totals.append(dict(run=label,link=link,lane=lane,TTT=float(np.trapezoid(ns,times)/3600),stopped_residence=float(np.trapezoid(stops,times)/3600),
                                    max_stopped=int(max(stops)),furthest_stopped_from_end_m=length-min(tails) if tails else 0))
    # All physical city links and ramp connectors together: coarse-grid sensitivity.
    cached_dir=ROOT/'diagnostics/repin_v3c3_review_20261001/goal8_265/interim_verified_to6150'
    # Reuse the recorded overall partition by subtracting geometric freeway links.
geo=json.loads((ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json').read_text(encoding='utf-8-sig'))
fw={int(x['link']) for chain in geo['chains'].values() for x in chain}
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
area=json.loads((ROOT/'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json').read_text(encoding='utf-8-sig'))
membership=physical_membership_from_ledger(area)
idx=[j for j,l in enumerate(links) if membership[str(l)] and l not in fw]
coarse=[i for i,t in enumerate(times) if t in (0,1,6150) or t%300==0]
coarse_ttt={r:float(np.trapezoid(z[r+'_stock'][coarse][:,idx].sum(axis=1),times[coarse])/3600) for r in RUNS}
result=dict(periods=out,lane_totals=lane_totals,snapshots=captures,topology=edges,coarse_300s_urban_TTT=coarse_ttt,source_sha256=proof)
(OUT/'drivers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(periods=[r for r in out if r['run'] in ['head47','coupling268']],
lane_totals=[r for r in lane_totals if r['run'] in ['head47','coupling268']],
snapshots=[r for r in captures if r['run'] in ['head47','coupling268']],coarse=coarse_ttt),ensure_ascii=False))
