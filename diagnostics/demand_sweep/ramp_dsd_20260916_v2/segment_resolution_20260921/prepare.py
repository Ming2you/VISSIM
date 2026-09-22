"""Native spatial audit and a port-exclusive, parent-preserving test mesh.

No INPX, demand, control, coefficients or original results are changed.
"""
from pathlib import Path
import bisect, copy, csv, hashlib, json, math, sys
from collections import Counter
import numpy as np

B=Path(__file__).resolve().parent; H=B.parent; K=H/'cohort_dynamics_20260920'
ROOT=H.parents[2]; sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lever_mechanisms_20260921 import analyze as native

def save(p,x):
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def table(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def mesh(geometry,max_m,branch_guard_m=0.):
    g=copy.deepcopy(geometry); g['cells']=[];g['bounds']={};maps={};ports=[]
    for road in geometry['chains']:
        maps[road]=[];g['bounds'][road]=[0.]
        for parent in [r for r in geometry['cells'] if r['road']==road]:
            ps=sorted([p for p in geometry['boundaries'] if p['road']==road and
                p['kind'] in ('ramp','offramp') and parent['start_m']<=p['chain_pos_m']<parent['end_m']],key=lambda x:x['chain_pos_m'])
            # Put a boundary BETWEEN two close ports; never construct the
            # 2.8m road between them as a separate numerical cell.
            cuts=[parent['start_m']]+[(a['chain_pos_m']+b['chain_pos_m'])/2 for a,b in zip(ps,ps[1:])]+[parent['end_m']]
            edges=[cuts[0]]
            for a,b in zip(cuts,cuts[1:]):
                count=math.ceil((b-a)/max_m) if ps else 1
                edges.extend(a+(b-a)*j/count for j in range(1,count+1))
            if branch_guard_m:
                # The installed10643 branch model further splits its host
                # cell at the port. Protect BOTH internal ODE lengths, not
                # just the externally reported cell length.
                for port in ps:
                    if port['connector']!=10643:continue
                    x=port['chain_pos_m']
                    for j in range(1,len(edges)-1):
                        if abs(edges[j]-x)<branch_guard_m:
                            options=[z for z in (x-branch_guard_m,x+branch_guard_m)
                                if edges[j-1]+40<z<edges[j+1]-40 and z not in cuts]
                            assert options,'No feasible branch-aware mesh boundary'
                            edges[j]=min(options,key=lambda z:abs(z-edges[j]))
            for a,b in zip(edges,edges[1:]):
                i=len(maps[road]);r=copy.deepcopy(parent);pieces=[]
                # Preserve the original observer's contiguous chain geometry;
                # raw INPX lengths differ from rounded chain offsets by <1mm.
                cursor=parent['start_m']
                for link in parent['physical_pieces']:
                    length=max(0.,min(b,cursor+link['length_m'])-max(a,cursor))
                    if length>1e-8:pieces.append(dict(link=link['link'],length_m=length,lanes=link['lanes']))
                    cursor+=link['length_m']
                assert abs(sum(p['length_m'] for p in pieces)-(b-a))<1e-7
                r.update(cell=i,start_m=a,end_m=b,length_km=(b-a)/1000,
                    lane_km=sum(p['length_m']*p['lanes'] for p in pieces)/1000,physical_pieces=pieces,parent_cell=parent['cell'])
                g['cells'].append(r);g['bounds'][road].append(b);maps[road].append(parent['cell'])
        for p in g['boundaries']:
            if p['road']!=road:continue
            i=min(len(maps[road])-1,bisect.bisect_right(g['bounds'][road],p['chain_pos_m'])-1)
            if p['from_cell'] is not None:p['from_cell']=i
            if p['to_cell'] is not None:p['to_cell']=i
            if p['kind'] in ('ramp','offramp'):
                cell=next(r for r in g['cells'] if r['road']==road and r['cell']==i)
                assert cell['start_m']<p['chain_pos_m']<cell['end_m'], 'Port fell exactly on a cell boundary'
                ports.append(dict(road=road,connector=p['connector'],kind=p['kind'],old_cell=maps[road][i],new_cell=i,
                    position_m=p['chain_pos_m'],start_m=cell['start_m'],end_m=cell['end_m'],length_m=cell['length_km']*1000))
    assert len(ports)==16 and max(Counter((p['road'],p['new_cell']) for p in ports).values())==1
    for road in maps:
        assert abs(sum(r['lane_km'] for r in g['cells'] if r['road']==road)-sum(r['lane_km'] for r in geometry['cells'] if r['road']==road))<1e-8
    return g,maps,ports

def bins(geometry,size):
    rows=[]
    for c in [r for r in geometry['cells'] if r['road']=='FW_E']:
        count=1 if size==0 else math.ceil(c['length_km']*1000/size)
        for j in range(count):rows.append(dict(cell=c['cell'],start=c['start_m']+(c['end_m']-c['start_m'])*j/count,
            end=c['start_m']+(c['end_m']-c['start_m'])*(j+1)/count))
    return rows

def main():
    g=native.G; candidate,mapping,ports=mesh(g,200.)
    save(B/'geometry_200.json',candidate);save(B/'parent_map.json',mapping);table(B/'ports.csv',ports)
    metadata=dict(cells={r:len(m) for r,m in mapping.items()},min_length_m=min(c['length_km']*1000 for c in candidate['cells']),
        max_ports_per_cell=1,physical_geometry_unchanged=True,original_boundaries_retained=True)
    save(B/'geometry_validation.json',metadata)
    print('Geometry',metadata,flush=True)
    specs={str(size):bins(g,size) for size in (0,250,100,50)}
    proofs=native.load(H/'lever_mechanisms_20260921/v2/extraction.json')['results'];receipts={}
    observed={};initial=None;origins={};summaries=[]
    for arm in ('none_s23','rm_ramp_s23','vsl_s23'):
        arrays={s:{k:np.zeros((752,len(bs),4),dtype=np.float64) for k in ('n','mom','slow','stop')} for s,bs in specs.items()}
        ends={s:[b['end'] for b in bs] for s,bs in specs.items()};proof={};last={};origin={};prefix=0
        for t,frame in native.native(ROOT/proofs[arm]['proof']['path'],proof):
            ti=t-2249;loc={vid:native.locate(r) for vid,r in frame.items()};loc={vid:p for vid,p in loc.items() if p is not None}
            if arm=='none_s23' and t<=2400:
                for vid,r in frame.items():
                    if r.link in native.ON:origin[vid]=r.link
                if t==2400:
                    initial=[dict(vehicle=vid,link=r.link,lane=r.lane,position_m=r.pos,speed_kmh=r.speed,
                        road=next((road for road,chain in g['chains'].items() if any(p['link']==r.link for p in chain)),None),
                        origin=origin.get(vid)) for vid,r in frame.items()]
                    save(B/'initial_2400.json',initial)
            for s,bs in specs.items():
                a=arrays[s]
                for vid,(c,x) in loc.items():
                    car=frame[vid];i=bisect.bisect_right(ends[s],x);lane=car.lane-1
                    a['n'][ti,i,lane]+=1;a['mom'][ti,i,lane]+=car.speed
                    a['slow'][ti,i,lane]+=car.speed<30;a['stop'][ti,i,lane]+=car.speed<5
            # Initial state is checked against the already verified native
            # state hash by the original proof, not against a different seed.
        assert proof['file_sha256']==proofs[arm]['proof']['file_sha256']
        receipts[arm]=proof
        for s,bs in specs.items():
            for ti in range(752):
                assert arrays[s]['n'][ti].sum()==arrays['0']['n'][ti].sum()
                assert abs(arrays[s]['mom'][ti].sum()-arrays['0']['mom'][ti].sum())<1e-6
            np.savez_compressed(B/f'{arm}_{s}.npz',**arrays[s])
        print('Native spatial aggregates finished',arm,flush=True)
    save(B/'bins.json',specs);save(B/'sources.json',receipts)

if __name__=='__main__':main()
